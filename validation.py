"""Input validation — server-side is authoritative."""
from datetime import date, datetime

from constants import (
    MIN_WEIGHT_KG, MAX_WEIGHT_KG,
    MIN_HEIGHT_CM, MAX_HEIGHT_CM,
    MIN_OFC_CM, MAX_OFC_CM,
    MIN_GESTATION_WEEKS, MAX_GESTATION_WEEKS,
    VALID_REFERENCES, DEFAULT_REFERENCE, VALID_SEXES,
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


def validate_gestation(weeks, days):
    """Validate gestation. Returns (weeks, days) tuple or None if not provided."""
    if weeks is None and days is None:
        return None
    if weeks is None:
        raise ValidationError(
            "Gestation weeks is required when days are provided.",
            ErrorCodes.INVALID_GESTATION,
        )
    try:
        weeks = int(weeks)
    except (TypeError, ValueError):
        raise ValidationError(
            "Gestation weeks must be a whole number.",
            ErrorCodes.INVALID_GESTATION,
        )
    if weeks < MIN_GESTATION_WEEKS or weeks > MAX_GESTATION_WEEKS:
        raise ValidationError(
            f"Gestation weeks must be between {MIN_GESTATION_WEEKS} and {MAX_GESTATION_WEEKS}.",
            ErrorCodes.INVALID_GESTATION,
        )
    if days is None:
        days = 0
    try:
        days = int(days)
    except (TypeError, ValueError):
        raise ValidationError(
            "Gestation days must be a whole number.",
            ErrorCodes.INVALID_GESTATION,
        )
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
