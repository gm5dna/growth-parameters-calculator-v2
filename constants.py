"""Application constants — thresholds, ranges, error codes."""

# Age limits
MIN_AGE_YEARS = 0.0
MAX_AGE_YEARS = 25.0

# SDS thresholds
SDS_WARNING_LIMIT = 4.0
SDS_HARD_LIMIT = 8.0
BMI_SDS_HARD_LIMIT = 15.0

# Measurement ranges
MIN_WEIGHT_KG = 0.1
MAX_WEIGHT_KG = 300.0
MIN_HEIGHT_CM = 10.0
MAX_HEIGHT_CM = 250.0
MIN_OFC_CM = 10.0
MAX_OFC_CM = 100.0

# Gestation
MIN_GESTATION_WEEKS = 22
MAX_GESTATION_WEEKS = 44
PRETERM_THRESHOLD_WEEKS = 37

# Valid values
VALID_REFERENCES = {"uk-who", "turners-syndrome", "trisomy-21", "cdc"}
DEFAULT_REFERENCE = "uk-who"
VALID_SEXES = {"male", "female"}
VALID_MEASUREMENT_METHODS = {"height", "weight", "ofc", "bmi"}


class ErrorCodes:
    INVALID_DATE_FORMAT = "ERR_001"
    INVALID_DATE_RANGE = "ERR_002"
    MISSING_MEASUREMENT = "ERR_003"
    INVALID_WEIGHT = "ERR_004"
    INVALID_HEIGHT = "ERR_005"
    INVALID_OFC = "ERR_006"
    INVALID_GESTATION = "ERR_007"
    SDS_OUT_OF_RANGE = "ERR_008"
    CALCULATION_ERROR = "ERR_009"
    INVALID_INPUT = "ERR_010"
