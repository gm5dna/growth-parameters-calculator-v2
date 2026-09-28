"""Application constants — thresholds, ranges, error codes."""

# Age limits
# MAX_AGE_YEARS is the absolute request cap — not a reference age range.
# Each growth reference declares its own supported age span via the
# REFERENCE_CAPABILITIES matrix below.
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
MIN_BONE_AGE_YEARS = 0.0
MAX_BONE_AGE_YEARS = 20.0

# Gestation
MIN_GESTATION_WEEKS = 22
MAX_GESTATION_WEEKS = 44

# Valid values
VALID_REFERENCES = {"uk-who", "turners-syndrome", "trisomy-21", "cdc", "who", "trisomy-21-aap"}
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
    UNSUPPORTED_REFERENCE = "ERR_011"


# cBNF BSA lookup table: (weight_kg, bsa_m2). Full BNFC 'Body surface area in
# children' table (derived from the Boyd equation), 0.5 kg steps to 10 kg then
# 1 kg steps to 90 kg; verified against bnfc.nice.org.uk on 28/09/2026.
# Values between rows are linearly interpolated.
CBNF_BSA_TABLE = [
    (1, 0.1), (1.5, 0.13), (2, 0.16), (2.5, 0.19), (3, 0.21), (3.5, 0.24), (4, 0.26),
    (4.5, 0.28), (5, 0.3), (5.5, 0.32), (6, 0.34), (6.5, 0.36), (7, 0.38), (7.5, 0.4),
    (8, 0.42), (8.5, 0.44), (9, 0.46), (9.5, 0.47), (10, 0.49), (11, 0.53), (12, 0.56),
    (13, 0.59), (14, 0.62), (15, 0.65), (16, 0.68), (17, 0.71), (18, 0.74), (19, 0.77),
    (20, 0.79), (21, 0.82), (22, 0.85), (23, 0.87), (24, 0.9), (25, 0.92), (26, 0.95),
    (27, 0.97), (28, 1.0), (29, 1.0), (30, 1.1), (31, 1.1), (32, 1.1), (33, 1.1),
    (34, 1.1), (35, 1.2), (36, 1.2), (37, 1.2), (38, 1.2), (39, 1.3), (40, 1.3),
    (41, 1.3), (42, 1.3), (43, 1.3), (44, 1.4), (45, 1.4), (46, 1.4), (47, 1.4),
    (48, 1.4), (49, 1.5), (50, 1.5), (51, 1.5), (52, 1.5), (53, 1.5), (54, 1.6),
    (55, 1.6), (56, 1.6), (57, 1.6), (58, 1.6), (59, 1.7), (60, 1.7), (61, 1.7),
    (62, 1.7), (63, 1.7), (64, 1.7), (65, 1.8), (66, 1.8), (67, 1.8), (68, 1.8),
    (69, 1.8), (70, 1.9), (71, 1.9), (72, 1.9), (73, 1.9), (74, 1.9), (75, 1.9),
    (76, 2.0), (77, 2.0), (78, 2.0), (79, 2.0), (80, 2.0), (81, 2.0), (82, 2.1),
    (83, 2.1), (84, 2.1), (85, 2.1), (86, 2.1), (87, 2.1), (88, 2.2), (89, 2.2),
    (90, 2.2),
]

# Growth hormone dosing
GH_STANDARD_DOSE_MG_M2_WEEK = 7.0

# Height velocity
VELOCITY_MIN_INTERVAL_DAYS = 122  # approximately 4 months

# Upper bounds on client-supplied nested lists. These are validated as bounded
# lists of objects before iteration so a malformed or oversized payload returns
# a structured 400 rather than a 500 or an expensive run.
MAX_PREVIOUS_MEASUREMENTS = 50
MAX_BONE_AGE_ASSESSMENTS = 20

# Bone age
BONE_AGE_WINDOW_DAYS = 30.44  # approximately 1 month
VALID_BONE_AGE_STANDARDS = {"gp", "tw3"}


# Reference × sex × method × age capability matrix.
# Mirrors rcpchgrowth's reference_data_absent() rules so unsupported combinations
# can be rejected with a structured error before hitting the library.
# method_age_overrides is keyed by "<method>" or "<method>_<sex>" (sex-specific
# wins) and clamps the generic (min_age, max_age) for that method.
REFERENCE_CAPABILITIES = {
    "uk-who": {
        "sexes": {"male", "female"},
        "methods": {"height", "weight", "ofc", "bmi"},
        "min_age": -0.33,  # ~23 weeks gestation
        "max_age": 20.0,
        # Lower bounds mirror rcpchgrowth uk_who.py reference_data_absent() and
        # constants/age_constants.py: TWENTY_FIVE_WEEKS_GESTATION (length) and
        # FORTY_TWO_WEEKS_GESTATION (BMI, i.e. 14 days of age).
        "method_age_overrides": {
            "height": (-(40 * 7 - 25 * 7) / 365.25, 20.0),  # 25 weeks gestation
            "bmi": (14 / 365.25, 20.0),  # 42 weeks gestation = 14 days of age
            "ofc_male": (-0.33, 18.0),
            "ofc_female": (-0.33, 17.0),
        },
    },
    "turners-syndrome": {
        "sexes": {"female"},
        "methods": {"height"},
        "min_age": 1.0,
        "max_age": 20.0,
    },
    "trisomy-21": {
        "sexes": {"male", "female"},
        "methods": {"height", "weight", "ofc", "bmi"},
        "min_age": 0.0,
        "max_age": 20.0,
        "method_age_overrides": {
            "bmi": (0.0, 18.82),
            "ofc": (0.0, 18.0),
        },
    },
    "cdc": {
        "sexes": {"male", "female"},
        "methods": {"height", "weight", "ofc", "bmi"},
        "min_age": 0.0,
        "max_age": 20.0,
        "method_age_overrides": {
            "ofc": (0.0, 3.0),
            "bmi": (2.0, 20.0),
        },
    },
    # WHO 2006/2007 standards (rcpchgrowth who.py): no preterm data; weight
    # stops at 10y, OFC at 5y 1m (1856 days), height/BMI run to 19y.
    "who": {
        "sexes": {"male", "female"},
        "methods": {"height", "weight", "ofc", "bmi"},
        "min_age": 0.0,
        "max_age": 19.0,
        "method_age_overrides": {
            "weight": (0.0, 10.0),
            "ofc": (0.0, 1856 / 365.25),
        },
    },
    # Zemel 2015 US Down syndrome charts (rcpchgrowth trisomy_21_aap.py):
    # height/OFC from 1 month, BMI from 2y, everything to 20y.
    "trisomy-21-aap": {
        "sexes": {"male", "female"},
        "methods": {"height", "weight", "ofc", "bmi"},
        "min_age": 0.0,
        "max_age": 20.0,
        "method_age_overrides": {
            "height": (0.083, 20.0),
            "ofc": (0.083, 20.0),
            "bmi": (2.0, 20.0),
        },
    },
}
