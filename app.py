"""Flask application — routes and orchestration."""
import logging
import os
from datetime import datetime as dt
from datetime import timedelta

from dateutil.relativedelta import relativedelta
from flask import Flask, jsonify, render_template, request, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from calculations import (
    calculate_age_in_years,
    calculate_boyd_bsa,
    calculate_calendar_age,
    calculate_cbnf_bsa,
    calculate_gh_dose,
    calculate_height_velocity,
    should_apply_gestation_correction,
)
from constants import BONE_AGE_WINDOW_DAYS, MAX_AGE_YEARS, VALID_MEASUREMENT_METHODS, ErrorCodes
from models import (
    UnsupportedCalculationError,
    create_measurement,
    extract_measurement_result,
    validate_measurement_sds,
)
from pdf_utils import GrowthReportPDF
from utils import (
    calculate_mid_parental_height,
    format_error_response,
    format_success_response,
    get_chart_data,
)
from validation import (
    ValidationError,
    validate_at_least_one_measurement,
    validate_bone_age,
    validate_bone_age_standard,
    validate_date,
    validate_gestation,
    validate_height,
    validate_ofc,
    validate_reference,
    validate_reference_supports,
    validate_sex,
    validate_weight,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Cap request bodies to protect /export-pdf in particular, which accepts
# base64-encoded chart images. Override with MAX_UPLOAD_BYTES in env.
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_UPLOAD_BYTES", 10 * 1024 * 1024))

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    # Shared Redis storage in multi-worker prod; memory:// is fine for single
    # worker / dev. Configure with RATELIMIT_STORAGE_URI.
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
)


@app.errorhandler(413)
def request_entity_too_large(_error):
    return jsonify(format_error_response(
        "Request body is too large.", ErrorCodes.INVALID_INPUT
    )), 413


def _parse_json_request():
    """Parse a JSON request body, enforcing that it is an object."""
    if not request.is_json:
        raise ValidationError(
            "Request body must be JSON with Content-Type: application/json.",
            ErrorCodes.INVALID_INPUT,
        )
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError(
            "Request body must be a JSON object.",
            ErrorCodes.INVALID_INPUT,
        )
    return data


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200


def perform_calculation(data):
    """Run the authoritative growth calculation from a raw input payload.

    Both /calculate and /export-pdf use this — the export endpoint must not
    trust any `results` sent by the client.
    Raises ValidationError / UnsupportedCalculationError / ValueError on bad
    input; callers are responsible for mapping to HTTP status codes.
    """
    sex = validate_sex(data.get("sex"))
    birth_date = validate_date(data.get("birth_date"), "birth_date")
    measurement_date = validate_date(data.get("measurement_date"), "measurement_date")
    reference = validate_reference(data.get("reference"))

    weight = validate_weight(data.get("weight"))
    height = validate_height(data.get("height"))
    ofc = validate_ofc(data.get("ofc"))
    validate_at_least_one_measurement(weight=weight, height=height, ofc=ofc)

    gestation_result = validate_gestation(
        data.get("gestation_weeks"), data.get("gestation_days")
    )
    gestation_weeks = gestation_result[0] if gestation_result else 0
    gestation_days = gestation_result[1] if gestation_result else 0

    age_years = calculate_age_in_years(birth_date, measurement_date)
    if age_years > MAX_AGE_YEARS:
        raise ValidationError(
            f"Age ({age_years:.1f} years) exceeds maximum of {MAX_AGE_YEARS} years.",
            ErrorCodes.INVALID_DATE_RANGE,
        )
    age_calendar = calculate_calendar_age(birth_date, measurement_date)

    correction_applied = should_apply_gestation_correction(
        gestation_weeks if gestation_weeks > 0 else None,
        age_years,
    )

    # Effective age for reference support lookups: corrected when applicable,
    # since rcpchgrowth performs its internal centile lookup against the
    # corrected age in that case.
    if correction_applied:
        edd = birth_date + relativedelta(weeks=(40 - gestation_weeks), days=-gestation_days)
        effective_age_years = calculate_age_in_years(edd, measurement_date)
    else:
        effective_age_years = age_years

    results = {
        "age_years": round(age_years, 4),
        "age_calendar": age_calendar,
        "gestation_correction_applied": correction_applied,
        "validation_messages": [],
    }

    all_warnings = []
    for method, value in [("weight", weight), ("height", height), ("ofc", ofc)]:
        if value is None:
            continue
        validate_reference_supports(reference, sex, method, effective_age_years)
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
        extracted = extract_measurement_result(measurement_result, value, method)
        all_warnings.extend(validate_measurement_sds(extracted["sds"], method))
        results[method] = extracted

        if correction_applied and "corrected_age_years" not in results:
            dates = measurement_result["measurement_dates"]
            results["corrected_age_years"] = round(dates["corrected_decimal_age"], 4)
            # rcpchgrowth returns corrected_calendar_age as a string;
            # compute a dict to match our API contract (PRD-02 section 8.1)
            edd = birth_date + relativedelta(weeks=(40 - gestation_weeks), days=-gestation_days)
            results["corrected_age_calendar"] = calculate_calendar_age(edd, measurement_date)

    # Auto-calculate BMI when both weight and height are present.
    # Skip silently when the selected reference does not support BMI for
    # this sex/age — the primary height/weight calculations are already in
    # `results`, and forcing a 400 would deny otherwise-valid output.
    if weight is not None and height is not None:
        try:
            validate_reference_supports(reference, sex, "bmi", effective_age_years)
        except ValidationError as e:
            all_warnings.append(e.message)
        else:
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
            bmi_extracted = extract_measurement_result(bmi_result, bmi_value, "bmi")
            all_warnings.extend(validate_measurement_sds(bmi_extracted["sds"], "bmi"))
            calc_values = bmi_result["measurement_calculated_values"]
            pct_median = calc_values.get("corrected_percentage_median_bmi")
            if pct_median is None:
                pct_median = calc_values.get("chronological_percentage_median_bmi")
            bmi_extracted["percentage_median"] = (
                round(pct_median, 1) if pct_median is not None else None
            )
            results["bmi"] = bmi_extracted

    bsa_value = None
    if weight is not None:
        if height is not None:
            bsa_value = calculate_boyd_bsa(weight, height)
            results["bsa"] = {"value": bsa_value, "method": "Boyd"}
        else:
            bsa_value = calculate_cbnf_bsa(weight)
            results["bsa"] = {"value": bsa_value, "method": "cBNF"}

    if data.get("gh_treatment") and bsa_value is not None:
        results["gh_dose"] = calculate_gh_dose(None, bsa_value, weight)

    mph = calculate_mid_parental_height(
        data.get("maternal_height"),
        data.get("paternal_height"),
        sex,
    )
    if mph:
        results["mid_parental_height"] = mph

    # Previous measurements — same validation as the current measurement so
    # trend/velocity calculations can't be driven by clinically impossible values.
    prev_validators = {
        "height": validate_height,
        "weight": validate_weight,
        "ofc": validate_ofc,
    }
    processed_prev = []
    for entry in data.get("previous_measurements", []):
        prev_date_str = entry.get("date", "")
        prev_date = validate_date(prev_date_str, "previous measurement date")
        if prev_date >= measurement_date:
            raise ValidationError(
                "Previous measurement date must be before the current measurement date.",
                ErrorCodes.INVALID_DATE_RANGE,
            )
        if prev_date < birth_date:
            raise ValidationError(
                "Previous measurement date cannot be before the date of birth.",
                ErrorCodes.INVALID_DATE_RANGE,
            )
        prev_age = calculate_age_in_years(birth_date, prev_date)
        prev_result = {"date": prev_date_str, "age": round(prev_age, 4)}
        if gestation_weeks > 0 and should_apply_gestation_correction(gestation_weeks, prev_age):
            edd = birth_date + relativedelta(weeks=(40 - gestation_weeks), days=-gestation_days)
            corrected_prev_age = calculate_age_in_years(edd, prev_date)
            if corrected_prev_age >= 0:
                prev_result["corrected_age"] = round(corrected_prev_age, 4)
            prev_effective_age = corrected_prev_age
        else:
            prev_effective_age = prev_age
        for method, validator in prev_validators.items():
            raw_value = entry.get(method)
            if raw_value is None or raw_value == "":
                continue
            value = validator(raw_value)
            validate_reference_supports(reference, sex, method, prev_effective_age)
            m = create_measurement(
                sex=sex,
                birth_date=birth_date,
                measurement_date=prev_date,
                measurement_method=method,
                observation_value=value,
                reference=reference,
                gestation_weeks=gestation_weeks,
                gestation_days=gestation_days,
            )
            extracted = extract_measurement_result(m, value, method)
            all_warnings.extend(validate_measurement_sds(extracted["sds"], method))
            prev_result[method] = extracted
        processed_prev.append(prev_result)

    if processed_prev:
        results["previous_measurements"] = processed_prev

    if height is not None and processed_prev:
        prev_with_height = [p for p in processed_prev if "height" in p]
        if prev_with_height:
            prev_with_height.sort(key=lambda p: p["date"], reverse=True)
            most_recent = prev_with_height[0]
            prev_date_obj = dt.strptime(most_recent["date"], "%Y-%m-%d").date()
            interval = (measurement_date - prev_date_obj).days
            velocity = calculate_height_velocity(
                height, most_recent["height"]["value"], interval
            )
            velocity["based_on_date"] = most_recent["date"]
            results["height_velocity"] = velocity

    bone_age_assessments = data.get("bone_age_assessments", [])
    bone_age_result = None

    if bone_age_assessments and height is not None:
        for ba in bone_age_assessments:
            try:
                ba_date_str = ba.get("date", "")
                ba_date = validate_date(ba_date_str, "bone age assessment date")
                ba_value = validate_bone_age(ba.get("bone_age"))
                ba_standard = validate_bone_age_standard(ba.get("standard"))
                if ba_date < birth_date:
                    raise ValidationError(
                        "Bone age assessment date cannot be before the date of birth.",
                        ErrorCodes.INVALID_DATE_RANGE,
                    )
                days_diff = abs((measurement_date - ba_date).days)
                within_window = days_diff <= BONE_AGE_WINDOW_DAYS

                synthetic_birth = measurement_date - timedelta(days=ba_value * 365.25)
                if synthetic_birth > measurement_date:
                    raise ValidationError(
                        "Bone age implies a future synthetic birth date.",
                        ErrorCodes.INVALID_INPUT,
                    )
                validate_reference_supports(reference, sex, "height", ba_value)
                ba_measurement = create_measurement(
                    sex=sex,
                    birth_date=synthetic_birth,
                    measurement_date=measurement_date,
                    measurement_method="height",
                    observation_value=height,
                    reference=reference,
                )
                ba_extracted = extract_measurement_result(ba_measurement, height, "height")

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
            except (ValidationError, UnsupportedCalculationError):
                raise
            except Exception:
                continue

        results["bone_age_height"] = bone_age_result
        results["bone_age_assessments"] = bone_age_assessments

    results["validation_messages"] = all_warnings
    results["_patient"] = {
        "sex": sex,
        "birth_date": birth_date.isoformat(),
        "measurement_date": measurement_date.isoformat(),
        "reference": reference,
    }
    return results


def _handle_calculation_exception(e):
    """Map exception classes from perform_calculation to (body, status)."""
    if isinstance(e, ValidationError):
        status = 422 if e.code == ErrorCodes.UNSUPPORTED_REFERENCE else 400
        return format_error_response(e.message, e.code), status
    if isinstance(e, UnsupportedCalculationError):
        return format_error_response(e.message, e.code), 422
    if isinstance(e, ValueError):
        msg = str(e)
        if "birth" in msg.lower() or "date" in msg.lower():
            code = ErrorCodes.INVALID_DATE_RANGE
        else:
            code = ErrorCodes.SDS_OUT_OF_RANGE
        return format_error_response(msg, code), 400
    logger.exception("Unhandled calculation error")
    return (
        format_error_response(
            "Calculation failed. Please check your inputs and try again.",
            ErrorCodes.CALCULATION_ERROR,
        ),
        500,
    )


@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        data = _parse_json_request()
    except ValidationError as e:
        return jsonify(format_error_response(e.message, e.code)), 400

    try:
        results = perform_calculation(data)
    except Exception as e:
        body, status = _handle_calculation_exception(e)
        return jsonify(body), status

    # _patient is only needed by /export-pdf; strip it from the public response.
    results.pop("_patient", None)
    logger.info("Calculation completed for %s", data.get("sex"))
    return jsonify(format_success_response(results)), 200


@app.route("/chart-data", methods=["POST"])
def chart_data():
    try:
        data = _parse_json_request()
    except ValidationError as e:
        return jsonify(format_error_response(e.message, e.code)), 400

    try:
        sex = validate_sex(data.get("sex"))
        reference = validate_reference(data.get("reference"))

        measurement_method = data.get("measurement_method")
        if not measurement_method or measurement_method not in VALID_MEASUREMENT_METHODS:
            raise ValidationError(
                f"measurement_method must be one of: {', '.join(sorted(VALID_MEASUREMENT_METHODS))}.",
                ErrorCodes.INVALID_INPUT,
            )

        # Reject unsupported reference/sex/method combinations with a structured
        # error instead of returning `{centiles: []}` from rcpchgrowth.
        validate_reference_supports(reference, sex, measurement_method, None)

        centiles = get_chart_data(reference, measurement_method, sex)

        return jsonify({"success": True, "centiles": centiles}), 200

    except ValidationError as e:
        status = 422 if e.code == ErrorCodes.UNSUPPORTED_REFERENCE else 400
        return jsonify(format_error_response(e.message, e.code)), status
    except Exception:
        logger.exception("Unhandled chart data error")
        return jsonify(format_error_response(
            "Chart data could not be retrieved.", ErrorCodes.CALCULATION_ERROR
        )), 500


@app.route("/export-pdf", methods=["POST"])
@limiter.limit("10 per minute")
def export_pdf():
    try:
        data = _parse_json_request()
    except ValidationError as e:
        return jsonify(format_error_response(e.message, e.code)), 400

    # Always recalculate server-side — the PDF must not be driven by
    # anything the client could tamper with. Any `results` key in the
    # payload is ignored.
    try:
        results = perform_calculation(data)
    except Exception as e:
        body, status = _handle_calculation_exception(e)
        return jsonify(body), status

    patient = results.pop("_patient", None)
    if patient is None:
        return jsonify(format_error_response(
            "Patient information is required.", ErrorCodes.INVALID_INPUT
        )), 400
    # Allow the client to add non-safety-critical display metadata
    # (name/identifier/clinician); reject anything that would override the
    # authoritative values computed here.
    client_patient = data.get("patient_info") or {}
    for reserved in ("sex", "birth_date", "measurement_date", "reference"):
        client_patient.pop(reserved, None)
    patient.update(client_patient)

    chart_images = data.get("chart_images", {})
    if not isinstance(chart_images, dict):
        return jsonify(format_error_response(
            "chart_images must be an object.", ErrorCodes.INVALID_INPUT
        )), 400

    try:
        pdf = GrowthReportPDF(results, patient, chart_images)
        buffer = pdf.generate()
        filename = f"growth-report-{dt.now().strftime('%Y-%m-%d-%H%M%S')}.pdf"
        return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=filename)
    except ValidationError as e:
        return jsonify(format_error_response(e.message, e.code)), 400
    except Exception:
        logger.exception("PDF generation error")
        return jsonify(format_error_response(
            "PDF generation failed. Please try again.", ErrorCodes.CALCULATION_ERROR
        )), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_DEBUG") == "1"
    # Debug mode exposes the Werkzeug interactive debugger — never bind it to
    # a public interface. Production always runs under gunicorn (see Dockerfile).
    host = "127.0.0.1" if debug else "0.0.0.0"
    app.run(host=host, port=port, debug=debug)
