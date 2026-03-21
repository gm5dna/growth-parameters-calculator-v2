"""Flask application — routes and orchestration."""
import os
import logging
from datetime import datetime as dt, timedelta

from flask import Flask, render_template, request, jsonify, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dateutil.relativedelta import relativedelta

from constants import ErrorCodes, MAX_AGE_YEARS, VALID_MEASUREMENT_METHODS, BONE_AGE_WINDOW_DAYS
from validation import (
    ValidationError,
    validate_date,
    validate_weight,
    validate_height,
    validate_ofc,
    validate_gestation,
    validate_sex,
    validate_reference,
    validate_at_least_one_measurement,
)
from calculations import (
    calculate_age_in_years,
    calculate_calendar_age,
    calculate_height_velocity,
    should_apply_gestation_correction,
    calculate_boyd_bsa,
    calculate_cbnf_bsa,
    calculate_gh_dose,
)
from rcpchgrowth import percentage_median_bmi
from models import create_measurement, validate_measurement_sds, extract_measurement_result
from utils import calculate_mid_parental_height, format_error_response, format_success_response, get_chart_data
from pdf_utils import GrowthReportPDF

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri="memory://",
)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200


@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify(format_error_response(
            "Request body must be valid JSON.", ErrorCodes.INVALID_INPUT
        )), 400

    try:
        # Validate required fields
        sex = validate_sex(data.get("sex"))
        birth_date = validate_date(data.get("birth_date"), "birth_date")
        measurement_date = validate_date(data.get("measurement_date"), "measurement_date")
        reference = validate_reference(data.get("reference"))

        # Validate optional measurements
        weight = validate_weight(data.get("weight"))
        height = validate_height(data.get("height"))
        ofc = validate_ofc(data.get("ofc"))
        validate_at_least_one_measurement(weight=weight, height=height, ofc=ofc)

        # Validate gestation
        gestation_result = validate_gestation(
            data.get("gestation_weeks"), data.get("gestation_days")
        )
        gestation_weeks = gestation_result[0] if gestation_result else 0
        gestation_days = gestation_result[1] if gestation_result else 0

        # Age calculation
        age_years = calculate_age_in_years(birth_date, measurement_date)
        if age_years > MAX_AGE_YEARS:
            raise ValidationError(
                f"Age ({age_years:.1f} years) exceeds maximum of {MAX_AGE_YEARS} years.",
                ErrorCodes.INVALID_DATE_RANGE,
            )
        age_calendar = calculate_calendar_age(birth_date, measurement_date)

        # Gestation correction
        correction_applied = should_apply_gestation_correction(
            gestation_weeks if gestation_weeks > 0 else None,
            age_years,
        )

        # Build results
        results = {
            "age_years": round(age_years, 4),
            "age_calendar": age_calendar,
            "gestation_correction_applied": correction_applied,
            "validation_messages": [],
        }

        # Process each measurement
        all_warnings = []
        for method, value in [("weight", weight), ("height", height), ("ofc", ofc)]:
            if value is None:
                continue
            measurement_result = create_measurement(
                sex=sex,
                birth_date=birth_date,
                measurement_date=measurement_date,
                measurement_method=method,
                observation_value=value,
                reference=reference,
                gestation_weeks=gestation_weeks,
                gestation_days=gestation_days,
            )
            extracted = extract_measurement_result(measurement_result, value)
            warnings = validate_measurement_sds(extracted["sds"], method)
            all_warnings.extend(warnings)
            results[method] = extracted

            # Extract corrected age from first measurement if correction applied
            if correction_applied and "corrected_age_years" not in results:
                dates = measurement_result["measurement_dates"]
                corrected_decimal = dates["corrected_decimal_age"]
                results["corrected_age_years"] = round(corrected_decimal, 4)
                # rcpchgrowth returns corrected_calendar_age as a string;
                # compute a dict to match our API contract (PRD-02 section 8.1)
                edd = birth_date + relativedelta(weeks=(40 - gestation_weeks), days=-gestation_days)
                results["corrected_age_calendar"] = calculate_calendar_age(edd, measurement_date)

        # Auto-calculate BMI when both weight and height are present
        if weight is not None and height is not None:
            bmi_value = round(weight / ((height / 100) ** 2), 1)
            bmi_result = create_measurement(
                sex=sex,
                birth_date=birth_date,
                measurement_date=measurement_date,
                measurement_method="bmi",
                observation_value=bmi_value,
                reference=reference,
                gestation_weeks=gestation_weeks,
                gestation_days=gestation_days,
            )
            bmi_extracted = extract_measurement_result(bmi_result, bmi_value)
            bmi_warnings = validate_measurement_sds(bmi_extracted["sds"], "bmi")
            all_warnings.extend(bmi_warnings)
            try:
                pct_median = percentage_median_bmi(
                    reference=reference,
                    age=age_years,
                    actual_bmi=bmi_value,
                    sex=sex,
                )
                bmi_extracted["percentage_median"] = round(pct_median, 1)
            except Exception:
                bmi_extracted["percentage_median"] = None
            results["bmi"] = bmi_extracted

        # BSA
        bsa_result = None
        bsa_value = None
        if weight is not None:
            if height is not None:
                bsa_value = calculate_boyd_bsa(weight, height)
                bsa_result = {"value": bsa_value, "method": "Boyd"}
            else:
                bsa_value = calculate_cbnf_bsa(weight)
                bsa_result = {"value": bsa_value, "method": "cBNF"}
            results["bsa"] = bsa_result

        # GH dose (only when gh_treatment flag is set and BSA calculable)
        if data.get("gh_treatment") and bsa_value is not None:
            gh = calculate_gh_dose(None, bsa_value, weight)
            results["gh_dose"] = gh

        # Mid-parental height
        mph = calculate_mid_parental_height(
            data.get("maternal_height"),
            data.get("paternal_height"),
            sex,
        )
        if mph:
            results["mid_parental_height"] = mph

        # Process previous measurements
        processed_prev = []
        for entry in data.get("previous_measurements", []):
            try:
                prev_date_str = entry.get("date", "")
                prev_date = validate_date(prev_date_str, "previous measurement date")
                if prev_date >= measurement_date:
                    continue  # Skip dates at or after current measurement
                prev_age = calculate_age_in_years(birth_date, prev_date)
                prev_result = {"date": prev_date_str, "age": round(prev_age, 4)}
                # Add corrected age if correction applies at THIS measurement's age
                # (each previous measurement checks independently against age cutoffs)
                if gestation_weeks > 0 and should_apply_gestation_correction(gestation_weeks, prev_age):
                    edd = birth_date + relativedelta(weeks=(40 - gestation_weeks), days=-gestation_days)
                    corrected_prev_age = calculate_age_in_years(edd, prev_date)
                    if corrected_prev_age >= 0:
                        prev_result["corrected_age"] = round(corrected_prev_age, 4)
                for method in ["height", "weight", "ofc"]:
                    value = entry.get(method)
                    if value is not None:
                        value = float(value)
                        m = create_measurement(
                            sex=sex, birth_date=birth_date,
                            measurement_date=prev_date,
                            measurement_method=method,
                            observation_value=value,
                            reference=reference,
                            gestation_weeks=gestation_weeks,
                            gestation_days=gestation_days,
                        )
                        prev_result[method] = extract_measurement_result(m, value)
                processed_prev.append(prev_result)
            except (ValidationError, ValueError, Exception):
                continue  # Skip invalid entries silently

        if processed_prev:
            results["previous_measurements"] = processed_prev

        # Calculate height velocity
        if height is not None and processed_prev:
            prev_with_height = [
                p for p in processed_prev if "height" in p
            ]
            if prev_with_height:
                # Sort by date descending (most recent first)
                prev_with_height.sort(key=lambda p: p["date"], reverse=True)
                most_recent = prev_with_height[0]
                prev_date_obj = dt.strptime(most_recent["date"], "%Y-%m-%d").date()
                interval = (measurement_date - prev_date_obj).days
                velocity = calculate_height_velocity(
                    height, most_recent["height"]["value"], interval
                )
                velocity["based_on_date"] = most_recent["date"]
                results["height_velocity"] = velocity

        # Process bone age assessments
        bone_age_assessments = data.get("bone_age_assessments", [])
        bone_age_result = None

        if bone_age_assessments and height is not None:
            for ba in bone_age_assessments:
                try:
                    ba_date_str = ba.get("date", "")
                    ba_date = dt.strptime(ba_date_str, "%Y-%m-%d").date()
                    ba_value = float(ba["bone_age"])
                    ba_standard = ba.get("standard", "gp")
                    days_diff = abs((measurement_date - ba_date).days)
                    within_window = days_diff <= BONE_AGE_WINDOW_DAYS

                    synthetic_birth = measurement_date - timedelta(days=ba_value * 365.25)
                    ba_measurement = create_measurement(
                        sex=sex,
                        birth_date=synthetic_birth,
                        measurement_date=measurement_date,
                        measurement_method="height",
                        observation_value=height,
                        reference=reference,
                    )
                    ba_extracted = extract_measurement_result(ba_measurement, height)

                    bone_age_result = {
                        "bone_age": ba_value,
                        "assessment_date": ba_date_str,
                        "standard": ba_standard,
                        "height": height,
                        "centile": ba_extracted["centile"],
                        "sds": ba_extracted["sds"],
                        "within_window": within_window,
                    }
                    break
                except Exception:
                    continue

            results["bone_age_height"] = bone_age_result
            results["bone_age_assessments"] = bone_age_assessments

        results["validation_messages"] = all_warnings

        logger.info("Calculation completed for %s", sex)
        return jsonify(format_success_response(results)), 200

    except ValidationError as e:
        return jsonify(format_error_response(e.message, e.code)), 400
    except ValueError as e:
        msg = str(e)
        # Distinguish date errors from SDS errors
        if "birth" in msg.lower() or "date" in msg.lower():
            code = ErrorCodes.INVALID_DATE_RANGE
        else:
            code = ErrorCodes.SDS_OUT_OF_RANGE
        return jsonify(format_error_response(msg, code)), 400
    except Exception as e:
        logger.error("Calculation error: %s", str(e))
        return jsonify(format_error_response(str(e), ErrorCodes.CALCULATION_ERROR)), 400


@app.route("/chart-data", methods=["POST"])
def chart_data():
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify(format_error_response(
            "Request body must be valid JSON.", ErrorCodes.INVALID_INPUT
        )), 400

    try:
        sex = validate_sex(data.get("sex"))
        reference = validate_reference(data.get("reference"))

        measurement_method = data.get("measurement_method")
        if not measurement_method or measurement_method not in VALID_MEASUREMENT_METHODS:
            raise ValidationError(
                f"measurement_method must be one of: {', '.join(sorted(VALID_MEASUREMENT_METHODS))}.",
                ErrorCodes.INVALID_INPUT,
            )

        centiles = get_chart_data(reference, measurement_method, sex)

        return jsonify({"success": True, "centiles": centiles}), 200

    except ValidationError as e:
        return jsonify(format_error_response(e.message, e.code)), 400
    except Exception as e:
        logger.error("Chart data error: %s", str(e))
        return jsonify(format_error_response(str(e), ErrorCodes.CALCULATION_ERROR)), 400


@app.route("/export-pdf", methods=["POST"])
@limiter.limit("10 per minute")
def export_pdf():
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify(format_error_response("Request body must be valid JSON.", ErrorCodes.INVALID_INPUT)), 400

    results = data.get("results")
    patient_info = data.get("patient_info")

    if not results:
        return jsonify(format_error_response("Results data is required.", ErrorCodes.INVALID_INPUT)), 400
    if not patient_info:
        return jsonify(format_error_response("Patient information is required.", ErrorCodes.INVALID_INPUT)), 400

    try:
        chart_images = data.get("chart_images", {})
        pdf = GrowthReportPDF(results, patient_info, chart_images)
        buffer = pdf.generate()

        filename = f"growth-report-{dt.now().strftime('%Y-%m-%d-%H%M%S')}.pdf"

        return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=filename)
    except Exception as e:
        logger.error("PDF generation error: %s", str(e))
        return jsonify(format_error_response("PDF generation failed. Please try again.", ErrorCodes.CALCULATION_ERROR)), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
