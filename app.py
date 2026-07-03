"""Flask application — routes and orchestration."""
import logging
import os
import re
from datetime import datetime as dt
from datetime import timedelta

from flask import Flask, jsonify, render_template, request, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from calculations import (
    MeasurementDateError,
    calculate_age_in_years,
    calculate_boyd_bsa,
    calculate_calendar_age,
    calculate_cbnf_bsa,
    calculate_gh_dose,
    calculate_height_velocity,
    expected_delivery_date,
    should_apply_gestation_correction,
)
from constants import (
    BONE_AGE_WINDOW_DAYS,
    MAX_AGE_YEARS,
    MAX_BONE_AGE_ASSESSMENTS,
    MAX_PREVIOUS_MEASUREMENTS,
    VALID_MEASUREMENT_METHODS,
    VELOCITY_MIN_INTERVAL_DAYS,
    ErrorCodes,
)
from models import (
    SdsOutOfRangeError,
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
    validate_object_list,
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

_RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    # Shared Redis storage in multi-worker prod; memory:// is fine for single
    # worker / dev. Configure with RATELIMIT_STORAGE_URI.
    storage_uri=_RATELIMIT_STORAGE_URI,
)


def _configured_worker_count():
    """Best-effort read of the Gunicorn worker count from the environment.

    Gunicorn honours WEB_CONCURRENCY and the --workers flag (surfaced via
    GUNICORN_CMD_ARGS). We only need to know whether it is >1 so we can warn
    that in-memory rate-limit state is not shared across workers.
    """
    web_concurrency = os.environ.get("WEB_CONCURRENCY")
    if web_concurrency and web_concurrency.isdigit():
        return int(web_concurrency)
    cmd_args = os.environ.get("GUNICORN_CMD_ARGS", "")
    match = re.search(r"--workers[= ](\d+)", cmd_args)
    if match:
        return int(match.group(1))
    return None


def _warn_if_ratelimit_storage_unsafe():
    """Warn when in-memory rate-limit storage is paired with multiple workers.

    ``memory://`` is per-process, so with N Gunicorn workers the effective
    limit is ~N× the configured value and resets whenever a worker restarts —
    silently weakening the DoS protection on /calculate, /chart-data and
    /export-pdf. Operators running >1 worker must set RATELIMIT_STORAGE_URI to
    a shared backend (e.g. redis://).
    """
    if not _RATELIMIT_STORAGE_URI.startswith("memory://"):
        return
    workers = _configured_worker_count()
    if workers is not None and workers > 1:
        logger.warning(
            "Rate limiting uses in-memory storage but %d workers are configured; "
            "limits are per-worker and not shared. Set RATELIMIT_STORAGE_URI to a "
            "shared backend (e.g. redis://) for correct multi-worker rate limiting.",
            workers,
        )


_warn_if_ratelimit_storage_unsafe()

# Per-endpoint limits. Both calculation endpoints run an rcpchgrowth lookup
# that dominates per-request cost, so we apply the same env-tunable cap.
_CALC_RATE_LIMIT = os.environ.get("CALC_RATE_LIMIT", "30 per minute")
_PDF_RATE_LIMIT = os.environ.get("PDF_RATE_LIMIT", "10 per minute")

# Allow-list for client-supplied `patient_info` on /export-pdf. Today the PDF
# renderer reads only the four server-authoritative fields (sex, birth_date,
# measurement_date, reference), so this set is deliberately empty: the client
# cannot contribute any patient_info key. Extend this set as new display-only
# fields are added to the PDF (e.g. {"patient_name", "clinician"}).
_ALLOWED_CLIENT_PATIENT_INFO_KEYS = frozenset()

# Cap on the number of chart images accepted per export. Each image goes
# through PIL + ReportLab synchronously; without a count cap an attacker can
# submit many small invalid images inside a single <10 MB request body.
_MAX_CHART_IMAGES = int(os.environ.get("MAX_CHART_IMAGES", 10))

# Only these chart keys are embedded in the PDF. Any other client-supplied key
# is discarded (without logging the raw key, which could carry accidental PHI)
# rather than turned into a chart label.
_ALLOWED_CHART_KEYS = frozenset({"height", "weight", "bmi", "ofc"})


@app.errorhandler(413)
def request_entity_too_large(_error):
    return jsonify(format_error_response(
        "Request body is too large.", ErrorCodes.INVALID_INPUT
    )), 413


# Conservative Content-Security-Policy. Chart.js + its annotation plugin are
# self-hosted under /static/vendor/, so script-src stays strict ('self'). The
# Google Fonts stylesheet (loaded from fonts.googleapis.com) pulls font files
# from fonts.gstatic.com. All CSS now lives in style.css (no inline <style> or
# style attributes in markup — JS uses CSSOM, which CSP does not gate), so
# style-src no longer needs 'unsafe-inline'.
_CSP_POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data:",
    "connect-src 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
])


@app.after_request
def _set_security_headers(response):
    response.headers.setdefault("Content-Security-Policy", _CSP_POLICY)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


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

    # Gestation actually passed to rcpchgrowth for the current measurement.
    # rcpchgrowth always reads the corrected-age centile/SDS when a preterm
    # gestation is supplied (for UK-WHO/Turner/Trisomy-21 it never resets to
    # chronological), so we must withhold gestation once correction no longer
    # applies — otherwise a child past the 1-/2-year cutoff, or a term
    # gestation entered for reference, would be reported on corrected age.
    # Passing 0 makes corrected == chronological, so extract_measurement_result
    # returns the chronological figures.
    calc_gestation_weeks = gestation_weeks if correction_applied else 0
    calc_gestation_days = gestation_days if correction_applied else 0

    # Effective age for reference support lookups: corrected when applicable,
    # since rcpchgrowth performs its internal centile lookup against the
    # corrected age in that case. A very preterm infant measured before its
    # expected delivery date has a NEGATIVE corrected age but valid preterm
    # reference data, so compute directly rather than via calculate_age_in_years
    # (which forbids the edd-after-measurement ordering).
    if correction_applied:
        edd = expected_delivery_date(birth_date, gestation_weeks, gestation_days)
        effective_age_years = (measurement_date - edd).days / 365.25
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
            gestation_weeks=calc_gestation_weeks,
            gestation_days=calc_gestation_days,
        )
        extracted = extract_measurement_result(measurement_result, value, method)
        all_warnings.extend(validate_measurement_sds(extracted["sds"], method))
        results[method] = extracted

        if correction_applied and "corrected_age_years" not in results:
            dates = measurement_result["measurement_dates"]
            results["corrected_age_years"] = round(dates["corrected_decimal_age"], 4)
            # rcpchgrowth returns corrected_calendar_age as a string;
            # compute a dict to match our API contract (PRD-02 section 8.1)
            edd = expected_delivery_date(birth_date, gestation_weeks, gestation_days)
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
                gestation_weeks=calc_gestation_weeks,
                gestation_days=calc_gestation_days,
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
    previous_measurements = validate_object_list(
        data.get("previous_measurements"),
        "previous_measurements",
        MAX_PREVIOUS_MEASUREMENTS,
    )
    processed_prev = []
    for entry in previous_measurements:
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
        prev_correction = gestation_weeks > 0 and should_apply_gestation_correction(
            gestation_weeks, prev_age
        )
        # Mirror the current-measurement handling: only feed gestation to
        # rcpchgrowth (and therefore report corrected centile/SDS) while
        # correction still applies for this previous date.
        prev_calc_weeks = gestation_weeks if prev_correction else 0
        prev_calc_days = gestation_days if prev_correction else 0
        if prev_correction:
            edd = expected_delivery_date(birth_date, gestation_weeks, gestation_days)
            corrected_prev_age = (prev_date - edd).days / 365.25
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
                gestation_weeks=prev_calc_weeks,
                gestation_days=prev_calc_days,
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
            # PRD-04 §4.6: use the most recent previous height that is at least
            # the minimum interval away — a too-recent measurement must not mask
            # an older valid one. Sort newest-first, then prefer the newest
            # entry that clears VELOCITY_MIN_INTERVAL_DAYS.
            prev_with_height.sort(key=lambda p: p["date"], reverse=True)
            dated = [
                (p, (measurement_date - dt.strptime(p["date"], "%Y-%m-%d").date()).days)
                for p in prev_with_height
            ]
            eligible = [(p, d) for p, d in dated if d >= VELOCITY_MIN_INTERVAL_DAYS]
            # Fall back to the closest measurement only when none qualify, so
            # calculate_height_velocity can surface the real (too-short) interval.
            chosen, interval = eligible[0] if eligible else dated[0]
            velocity = calculate_height_velocity(
                height, chosen["height"]["value"], interval
            )
            velocity["based_on_date"] = chosen["date"]
            results["height_velocity"] = velocity

    bone_age_assessments = validate_object_list(
        data.get("bone_age_assessments"),
        "bone_age_assessments",
        MAX_BONE_AGE_ASSESSMENTS,
    )
    bone_age_result = None

    if bone_age_assessments and height is not None:
        # Prefer the assessment closest to the current measurement date so the
        # first successfully-processed entry is the most clinically relevant one
        # (ideally within the ±1 month plotting window). Entries with an
        # unparseable date sort last; validate_date still rejects them if reached.
        def _proximity(ba):
            try:
                d = dt.strptime(ba.get("date", ""), "%Y-%m-%d").date()
            except (ValueError, TypeError):
                return float("inf")
            return abs((measurement_date - d).days)

        bone_age_assessments = sorted(bone_age_assessments, key=_proximity)
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
                # Skip this single assessment but record WHY — masking an
                # rcpchgrowth contract change or arithmetic error behind the
                # generic "could not be processed" warning makes clinical
                # failures undiagnosable.
                logger.exception("Bone age assessment processing failed; skipping entry")
                continue

        # Only publish bone_age_height when the loop actually produced a
        # result. If every assessment tripped a non-ValidationError path
        # (typically an rcpchgrowth internal failure), surface that clearly
        # via validation_messages rather than writing a null field.
        if bone_age_result is not None:
            results["bone_age_height"] = bone_age_result
        else:
            all_warnings.append("Bone age assessment could not be processed.")
        # Echo only the recognised fields back — never reflect arbitrary
        # client-supplied keys (which could carry PHI) into the response.
        results["bone_age_assessments"] = [
            {
                "date": ba.get("date"),
                "bone_age": ba.get("bone_age"),
                "standard": ba.get("standard"),
            }
            for ba in bone_age_assessments
        ]

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
    if isinstance(e, (SdsOutOfRangeError, MeasurementDateError)):
        # Typed, clinician-facing ValueErrors carry their own error code and a
        # safe message — surface them directly.
        return format_error_response(str(e), e.code), 400
    if isinstance(e, ValueError):
        # An unexpected ValueError (e.g. from a library internal) — do not leak
        # its raw message to the client; log it and return a generic error.
        logger.exception("Unexpected ValueError in calculation")
        return format_error_response(
            "Calculation failed. Please check your inputs and try again.",
            ErrorCodes.CALCULATION_ERROR,
        ), 400
    logger.exception("Unhandled calculation error")
    return (
        format_error_response(
            "Calculation failed. Please check your inputs and try again.",
            ErrorCodes.CALCULATION_ERROR,
        ),
        500,
    )


@app.route("/calculate", methods=["POST"])
@limiter.limit(_CALC_RATE_LIMIT)
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
    logger.info("Calculation completed")
    return jsonify(format_success_response(results)), 200


@app.route("/chart-data", methods=["POST"])
@limiter.limit(_CALC_RATE_LIMIT)
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
@limiter.limit(_PDF_RATE_LIMIT)
def export_pdf():
    try:
        data = _parse_json_request()
    except ValidationError as e:
        return jsonify(format_error_response(e.message, e.code)), 400

    # Validate the export-only fields (shape + count) BEFORE the expensive
    # rcpchgrowth recalculation, so a malformed or oversized chart payload is
    # rejected cheaply rather than after a full calculation pass.
    # patient_info is optional and display-only. An absent key or explicit null
    # means "not provided" (consistent with how every other optional field is
    # treated); any other non-dict value is malformed and rejected. Plain
    # `or {}` was wrong here — it let a falsy [] slip past the type check.
    client_patient = data.get("patient_info")
    if client_patient is None:
        client_patient = {}
    elif not isinstance(client_patient, dict):
        return jsonify(format_error_response(
            "patient_info must be an object.", ErrorCodes.INVALID_INPUT
        )), 400

    chart_images = data.get("chart_images", {})
    if not isinstance(chart_images, dict):
        return jsonify(format_error_response(
            "chart_images must be an object.", ErrorCodes.INVALID_INPUT
        )), 400
    # Count-cap the raw payload first (bounds work regardless of key names),
    # then discard any key that is not a known chart type.
    if len(chart_images) > _MAX_CHART_IMAGES:
        return jsonify(format_error_response(
            f"At most {_MAX_CHART_IMAGES} chart images are allowed per export.",
            ErrorCodes.INVALID_INPUT,
        )), 400
    chart_images = {k: v for k, v in chart_images.items() if k in _ALLOWED_CHART_KEYS}

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
    # Merge only allow-listed display fields from the client — never the four
    # safety-critical keys (sex, birth_date, measurement_date, reference),
    # which are always the server-recomputed values.
    for key in _ALLOWED_CLIENT_PATIENT_INFO_KEYS:
        if key in client_patient:
            patient[key] = client_patient[key]

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
