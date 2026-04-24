"""Input validation — server-side is authoritative."""
import math
from datetime import date, datetime

from constants import (
    DEFAULT_REFERENCE,
    MAX_BONE_AGE_YEARS,
    MAX_GESTATION_WEEKS,
    MAX_HEIGHT_CM,
    MAX_OFC_CM,
    MAX_PARENT_HEIGHT_CM,
    MAX_WEIGHT_KG,
    MIN_BONE_AGE_YEARS,
    MIN_GESTATION_WEEKS,
    MIN_HEIGHT_CM,
    MIN_OFC_CM,
    MIN_PARENT_HEIGHT_CM,
    MIN_WEIGHT_KG,
    REFERENCE_CAPABILITIES,
    VALID_BONE_AGE_STANDARDS,
    VALID_REFERENCES,
    VALID_SEXES,
    ErrorCodes,
)


class ValidationError(Exception):
    """Validation error with human-readable message and error code."""

    def __init__(self, message, code):
        self.message = message
        self.code = code
        super().__init__(message)


def validate_date(value, field_name):
    """Parse and validate a date string (YYYY-MM-DD). Returns datetime.date."""
    if not value or not isinstance(value, str):
        raise ValidationError(
            f"{field_name} is required and must be in YYYY-MM-DD format.",
            ErrorCodes.INVALID_DATE_FORMAT,
        )
    try:
        parsed = datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError(
            f"{field_name} must be in YYYY-MM-DD format.",
            ErrorCodes.INVALID_DATE_FORMAT,
        )
    if parsed > date.today():
        raise ValidationError(
            f"{field_name} cannot be in the future.",
            ErrorCodes.INVALID_DATE_RANGE,
        )
    return parsed


def _validate_numeric_range(value, min_val, max_val, name, error_code):
    """Validate an optional numeric field. Returns float or None."""
    if value is None or value == "":
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValidationError(
            f"{name} must be a number.",
            error_code,
        )
    if not math.isfinite(value):
        raise ValidationError(
            f"{name} must be a finite number.",
            error_code,
        )
    if value < min_val or value > max_val:
        raise ValidationError(
            f"{name} must be between {min_val} and {max_val}.",
            error_code,
        )
    return value


def validate_weight(value):
    return _validate_numeric_range(
        value, MIN_WEIGHT_KG, MAX_WEIGHT_KG, "Weight", ErrorCodes.INVALID_WEIGHT
    )


def validate_height(value):
    return _validate_numeric_range(
        value, MIN_HEIGHT_CM, MAX_HEIGHT_CM, "Height", ErrorCodes.INVALID_HEIGHT
    )


def validate_ofc(value):
    return _validate_numeric_range(
        value, MIN_OFC_CM, MAX_OFC_CM, "Head circumference", ErrorCodes.INVALID_OFC
    )


def _to_whole_number(value, field_label):
    """Coerce a gestation field to int, rejecting non-whole numbers.

    `int(22.7)` truncates silently in Python, so JSON numbers like 22.7 would
    otherwise pass through `int()` unchallenged. Force a round-trip check.
    """
    if isinstance(value, bool):  # bool is a subclass of int — reject explicitly
        raise ValidationError(
            f"{field_label} must be a whole number.",
            ErrorCodes.INVALID_GESTATION,
        )
    try:
        as_float = float(value)
    except (TypeError, ValueError):
        raise ValidationError(
            f"{field_label} must be a whole number.",
            ErrorCodes.INVALID_GESTATION,
        )
    if not math.isfinite(as_float) or not as_float.is_integer():
        raise ValidationError(
            f"{field_label} must be a whole number.",
            ErrorCodes.INVALID_GESTATION,
        )
    return int(as_float)


def validate_gestation(weeks, days):
    """Validate gestation. Returns (weeks, days) tuple or None if not provided."""
    if weeks is None and days is None:
        return None
    if weeks is None:
        raise ValidationError(
            "Gestation weeks is required when days are provided.",
            ErrorCodes.INVALID_GESTATION,
        )
    weeks = _to_whole_number(weeks, "Gestation weeks")
    if weeks < MIN_GESTATION_WEEKS or weeks > MAX_GESTATION_WEEKS:
        raise ValidationError(
            f"Gestation weeks must be between {MIN_GESTATION_WEEKS} and {MAX_GESTATION_WEEKS}.",
            ErrorCodes.INVALID_GESTATION,
        )
    days = 0 if days is None else _to_whole_number(days, "Gestation days")
    if days < 0 or days > 6:
        raise ValidationError(
            "Gestation days must be between 0 and 6.",
            ErrorCodes.INVALID_GESTATION,
        )
    return weeks, days


def validate_sex(value):
    if not value or value not in VALID_SEXES:
        raise ValidationError(
            "Sex must be 'male' or 'female'.",
            ErrorCodes.INVALID_INPUT,
        )
    return value


def validate_reference(value):
    if value is None:
        return DEFAULT_REFERENCE
    if value not in VALID_REFERENCES:
        raise ValidationError(
            f"Reference must be one of: {', '.join(sorted(VALID_REFERENCES))}.",
            ErrorCodes.INVALID_INPUT,
        )
    return value


def validate_at_least_one_measurement(weight=None, height=None, ofc=None):
    if weight is None and height is None and ofc is None:
        raise ValidationError(
            "At least one measurement (weight, height, or head circumference) is required.",
            ErrorCodes.MISSING_MEASUREMENT,
        )


def validate_parent_height(value, parent_label):
    """Validate a parental height in cm. Returns float or None."""
    if value is None or value == "":
        return None
    return _validate_numeric_range(
        value,
        MIN_PARENT_HEIGHT_CM,
        MAX_PARENT_HEIGHT_CM,
        f"{parent_label} height",
        ErrorCodes.INVALID_INPUT,
    )


def validate_bone_age(value):
    """Validate a bone-age value in years. Returns float."""
    if value is None or value == "":
        raise ValidationError(
            "Bone age is required for an assessment.",
            ErrorCodes.INVALID_INPUT,
        )
    return _validate_numeric_range(
        value,
        MIN_BONE_AGE_YEARS,
        MAX_BONE_AGE_YEARS,
        "Bone age",
        ErrorCodes.INVALID_INPUT,
    )


def validate_bone_age_standard(value):
    """Validate the bone-age standard. Returns the normalised value."""
    if value is None or value == "":
        return "gp"
    if value not in VALID_BONE_AGE_STANDARDS:
        raise ValidationError(
            f"Bone age standard must be one of: {', '.join(sorted(VALID_BONE_AGE_STANDARDS))}.",
            ErrorCodes.INVALID_INPUT,
        )
    return value


def validate_reference_supports(reference, sex, measurement_method, age_years):
    """Confirm (reference, sex, method, age) is a supported combination.

    Raises ValidationError(UNSUPPORTED_REFERENCE) when unsupported.
    Safe to call even when age_years is None (only sex/method are checked).
    """
    caps = REFERENCE_CAPABILITIES.get(reference)
    if caps is None:
        # validate_reference() should have rejected this earlier; guard anyway.
        raise ValidationError(
            f"Reference '{reference}' is not supported.",
            ErrorCodes.UNSUPPORTED_REFERENCE,
        )
    if sex not in caps["sexes"]:
        raise ValidationError(
            f"The {reference} reference does not support {sex} patients.",
            ErrorCodes.UNSUPPORTED_REFERENCE,
        )
    if measurement_method not in caps["methods"]:
        raise ValidationError(
            f"The {reference} reference does not support {measurement_method} measurements.",
            ErrorCodes.UNSUPPORTED_REFERENCE,
        )
    if age_years is None:
        return
    overrides = caps.get("method_age_overrides", {})
    method_limits = overrides.get(f"{measurement_method}_{sex}") or overrides.get(measurement_method)
    min_age, max_age = method_limits if method_limits else (caps["min_age"], caps["max_age"])
    if age_years < min_age or age_years > max_age:
        raise ValidationError(
            f"The {reference} reference does not support {measurement_method} at age "
            f"{age_years:.2f} years (supported range {min_age}–{max_age} years).",
            ErrorCodes.UNSUPPORTED_REFERENCE,
        )
