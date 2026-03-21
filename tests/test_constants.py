"""Tests for constants module."""
from constants import (
    MIN_AGE_YEARS, MAX_AGE_YEARS,
    SDS_WARNING_LIMIT, SDS_HARD_LIMIT, BMI_SDS_HARD_LIMIT,
    MIN_WEIGHT_KG, MAX_WEIGHT_KG,
    MIN_HEIGHT_CM, MAX_HEIGHT_CM,
    MIN_OFC_CM, MAX_OFC_CM,
    MIN_GESTATION_WEEKS, MAX_GESTATION_WEEKS, PRETERM_THRESHOLD_WEEKS,
    VALID_REFERENCES, DEFAULT_REFERENCE, VALID_SEXES,
    VALID_MEASUREMENT_METHODS,
    ErrorCodes,
    CBNF_BSA_TABLE,
    GH_STANDARD_DOSE_MG_M2_WEEK,
    GH_DOSE_STEP_MG,
    VELOCITY_MIN_INTERVAL_DAYS,
    BONE_AGE_WINDOW_DAYS,
    VALID_BONE_AGE_STANDARDS,
)


def test_age_limits():
    assert MIN_AGE_YEARS == 0.0
    assert MAX_AGE_YEARS == 25.0


def test_sds_thresholds():
    assert SDS_WARNING_LIMIT == 4.0
    assert SDS_HARD_LIMIT == 8.0
    assert BMI_SDS_HARD_LIMIT == 15.0


def test_measurement_ranges():
    assert MIN_WEIGHT_KG == 0.1
    assert MAX_WEIGHT_KG == 300.0
    assert MIN_HEIGHT_CM == 10.0
    assert MAX_HEIGHT_CM == 250.0
    assert MIN_OFC_CM == 10.0
    assert MAX_OFC_CM == 100.0


def test_gestation_constants():
    assert MIN_GESTATION_WEEKS == 22
    assert MAX_GESTATION_WEEKS == 44
    assert PRETERM_THRESHOLD_WEEKS == 37


def test_valid_references():
    assert "uk-who" in VALID_REFERENCES
    assert "turners-syndrome" in VALID_REFERENCES
    assert "trisomy-21" in VALID_REFERENCES
    assert "cdc" in VALID_REFERENCES
    assert DEFAULT_REFERENCE == "uk-who"


def test_valid_sexes():
    assert VALID_SEXES == {"male", "female"}


def test_valid_measurement_methods():
    assert "height" in VALID_MEASUREMENT_METHODS
    assert "weight" in VALID_MEASUREMENT_METHODS
    assert "ofc" in VALID_MEASUREMENT_METHODS
    assert "bmi" in VALID_MEASUREMENT_METHODS


def test_error_codes_exist():
    assert ErrorCodes.INVALID_DATE_FORMAT == "ERR_001"
    assert ErrorCodes.INVALID_DATE_RANGE == "ERR_002"
    assert ErrorCodes.MISSING_MEASUREMENT == "ERR_003"
    assert ErrorCodes.INVALID_WEIGHT == "ERR_004"
    assert ErrorCodes.INVALID_HEIGHT == "ERR_005"
    assert ErrorCodes.INVALID_OFC == "ERR_006"
    assert ErrorCodes.INVALID_GESTATION == "ERR_007"
    assert ErrorCodes.SDS_OUT_OF_RANGE == "ERR_008"
    assert ErrorCodes.CALCULATION_ERROR == "ERR_009"
    assert ErrorCodes.INVALID_INPUT == "ERR_010"


def test_cbnf_bsa_table():
    assert isinstance(CBNF_BSA_TABLE, list)
    assert len(CBNF_BSA_TABLE) == 9
    assert CBNF_BSA_TABLE[0] == (1, 0.10)
    assert CBNF_BSA_TABLE[-1] == (90, 2.2)


def test_gh_constants():
    assert GH_STANDARD_DOSE_MG_M2_WEEK == 7.0
    assert GH_DOSE_STEP_MG == 0.025


def test_velocity_constants():
    assert VELOCITY_MIN_INTERVAL_DAYS == 122


def test_bone_age_constants():
    assert BONE_AGE_WINDOW_DAYS == 30.44
    assert "gp" in VALID_BONE_AGE_STANDARDS
    assert "tw3" in VALID_BONE_AGE_STANDARDS
