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


# cBNF BSA lookup table: (weight_kg, bsa_m2)
CBNF_BSA_TABLE = [
    (1, 0.10),
    (2, 0.16),
    (5, 0.30),
    (10, 0.49),
    (20, 0.79),
    (30, 1.1),
    (50, 1.5),
    (70, 1.9),
    (90, 2.2),
]

# Growth hormone dosing
GH_STANDARD_DOSE_MG_M2_WEEK = 7.0
GH_PEN_DEVICES = [
    {"id": "norditropin-5",  "label": "Norditropin FlexPro 5 mg",  "step": 0.025, "min": 0.025, "max": 2.0},
    {"id": "norditropin-10", "label": "Norditropin FlexPro 10 mg", "step": 0.05,  "min": 0.05,  "max": 4.0},
    {"id": "norditropin-15", "label": "Norditropin FlexPro 15 mg", "step": 0.1,   "min": 0.1,   "max": 8.0},
    {"id": "surepal-5",      "label": "Omnitrope SurePal 5",       "step": 0.1,   "min": 0.1,   "max": 2.4},
    {"id": "surepal-10",     "label": "Omnitrope SurePal 10",      "step": 0.1,   "min": 0.1,   "max": 4.8},
    {"id": "surepal-15",     "label": "Omnitrope SurePal 15",      "step": 0.1,   "min": 0.1,   "max": 7.2},
]

# Height velocity
VELOCITY_MIN_INTERVAL_DAYS = 122  # approximately 4 months

# Bone age
BONE_AGE_WINDOW_DAYS = 30.44  # approximately 1 month
VALID_BONE_AGE_STANDARDS = {"gp", "tw3"}
