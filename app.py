"""Flask application — routes and orchestration."""
import os
import logging

from flask import Flask, render_template, request, jsonify
from dateutil.relativedelta import relativedelta

from constants import ErrorCodes, MAX_AGE_YEARS
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
    should_apply_gestation_correction,
)
from models import create_measurement, validate_measurement_sds, extract_measurement_result
from utils import calculate_mid_parental_height, format_error_response, format_success_response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


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
            results["bmi"] = bmi_extracted

        # Mid-parental height
        mph = calculate_mid_parental_height(
            data.get("maternal_height"),
            data.get("paternal_height"),
            sex,
        )
        if mph:
            results["mid_parental_height"] = mph

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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
