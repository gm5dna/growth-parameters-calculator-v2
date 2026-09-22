"""Tests for validation module."""
import functools
from datetime import date

import pytest

from validation import (
    PARENT_HEIGHT_LIMITS,
    ValidationError,
    validate_at_least_one_measurement,
    validate_bone_age,
    validate_bone_age_standard,
    validate_date,
    validate_gestation,
    validate_height,
    validate_ofc,
    validate_parent_height,
    validate_reference,
    validate_reference_supports,
    validate_sex,
    validate_weight,
)


class TestValidationError:
    def test_has_message_and_code(self):
        err = ValidationError("bad input", "ERR_001")
        assert err.message == "bad input"
        assert err.code == "ERR_001"
        assert str(err) == "bad input"


class TestValidateDate:
    def test_valid_date_string(self):
        result = validate_date("2023-06-15", "birth_date")
        assert result == date(2023, 6, 15)

    def test_invalid_format(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_date("15/06/2023", "birth_date")
        assert exc_info.value.code == "ERR_001"

    def test_future_date_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_date("2099-01-01", "birth_date")
        assert exc_info.value.code == "ERR_002"

    def test_empty_string_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_date("", "birth_date")
        assert exc_info.value.code == "ERR_001"

    def test_none_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_date(None, "birth_date")
        assert exc_info.value.code == "ERR_001"


@pytest.mark.parametrize(
    "validator, valid_value, too_low, too_high, error_code",
    [
        (validate_weight, 12.5, 0.05, 301.0, "ERR_004"),
        (validate_height, 85.3, 5.0, 260.0, "ERR_005"),
        (validate_ofc, 48.2, 5.0, 110.0, "ERR_006"),
        (
            functools.partial(validate_parent_height, parent_label="Maternal"),
            170.5,
            50,
            300,
            "ERR_010",
        ),
    ],
    ids=["weight", "height", "ofc", "parent_height"],
)
class TestRangeValidatorsShared:
    """Shared shape for the simple min/max numeric validators."""

    def test_valid_value_returns_float(self, validator, valid_value, too_low, too_high, error_code):
        assert validator(valid_value) == valid_value

    def test_none_returns_none(self, validator, valid_value, too_low, too_high, error_code):
        assert validator(None) is None

    def test_below_minimum_raises(self, validator, valid_value, too_low, too_high, error_code):
        with pytest.raises(ValidationError) as exc_info:
            validator(too_low)
        assert exc_info.value.code == error_code

    def test_above_maximum_raises(self, validator, valid_value, too_low, too_high, error_code):
        with pytest.raises(ValidationError) as exc_info:
            validator(too_high)
        assert exc_info.value.code == error_code


class TestValidateWeight:
    """Cases unique to validate_weight, not covered by the shared shape."""

    def test_non_numeric_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_weight("abc")
        assert exc_info.value.code == "ERR_004"

    def test_boundary_minimum(self):
        assert validate_weight(0.1) == 0.1

    def test_boundary_maximum(self):
        assert validate_weight(300.0) == 300.0


class TestValidateGestation:
    def test_valid_gestation(self):
        weeks, days = validate_gestation(34, 3)
        assert weeks == 34
        assert days == 3

    def test_none_returns_none(self):
        assert validate_gestation(None, None) is None

    def test_days_defaults_to_zero(self):
        weeks, days = validate_gestation(38, None)
        assert weeks == 38
        assert days == 0

    def test_below_minimum_weeks(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_gestation(20, 0)
        assert exc_info.value.code == "ERR_007"

    def test_above_maximum_weeks(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_gestation(45, 0)
        assert exc_info.value.code == "ERR_007"

    def test_invalid_days(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_gestation(34, 7)
        assert exc_info.value.code == "ERR_007"

    @pytest.mark.parametrize("bad_weeks", [22.7, 36.5, 37.9, "22.7", "36.5"])
    def test_rejects_non_integer_float_weeks(self, bad_weeks):
        with pytest.raises(ValidationError) as exc_info:
            validate_gestation(bad_weeks, 0)
        assert exc_info.value.code == "ERR_007"
        assert "whole number" in exc_info.value.message.lower()

    @pytest.mark.parametrize("bad_days", [2.5, "2.5"])
    def test_rejects_non_integer_float_days(self, bad_days):
        with pytest.raises(ValidationError):
            validate_gestation(34, bad_days)

    def test_accepts_whole_float(self):
        # 38.0 is a whole number and should pass.
        weeks, days = validate_gestation(38.0, 0.0)
        assert weeks == 38
        assert days == 0

    def test_rejects_boolean(self):
        # bool is a Python int subclass; reject explicitly.
        with pytest.raises(ValidationError):
            validate_gestation(True, 0)
        # `days=False` is only evaluated when weeks are valid.
        with pytest.raises(ValidationError):
            validate_gestation(34, True)

    def test_rejects_non_finite_weeks(self):
        with pytest.raises(ValidationError):
            validate_gestation(float("nan"), 0)
        with pytest.raises(ValidationError):
            validate_gestation(float("inf"), 0)


class TestValidateSex:
    def test_valid_male(self):
        assert validate_sex("male") == "male"

    def test_valid_female(self):
        assert validate_sex("female") == "female"

    def test_invalid_sex(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_sex("other")
        assert exc_info.value.code == "ERR_010"

    def test_none_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_sex(None)
        assert exc_info.value.code == "ERR_010"


class TestValidateReference:
    def test_valid_reference(self):
        assert validate_reference("uk-who") == "uk-who"

    def test_none_defaults(self):
        assert validate_reference(None) == "uk-who"

    def test_invalid_reference(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_reference("invalid")
        assert exc_info.value.code == "ERR_010"


class TestValidateAtLeastOneMeasurement:
    def test_weight_only(self):
        validate_at_least_one_measurement(weight=12.5)

    def test_height_only(self):
        validate_at_least_one_measurement(height=85.3)

    def test_ofc_only(self):
        validate_at_least_one_measurement(ofc=48.2)

    def test_none_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_at_least_one_measurement()
        assert exc_info.value.code == "ERR_003"


class TestNonFiniteNumbers:
    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf"), "NaN", "Infinity", "-Infinity"])
    def test_weight_rejects_non_finite(self, bad):
        with pytest.raises(ValidationError) as exc_info:
            validate_weight(bad)
        assert exc_info.value.code == "ERR_004"
        assert "finite" in exc_info.value.message.lower()

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), "NaN", "1e999"])
    def test_height_rejects_non_finite(self, bad):
        with pytest.raises(ValidationError):
            validate_height(bad)

    def test_ofc_rejects_nan(self):
        with pytest.raises(ValidationError):
            validate_ofc(float("nan"))


class TestValidateParentHeight:
    def test_limits_derived_from_rcpchgrowth(self):
        # UK-WHO adult height at -/+8 SDS, rounded inwards. A change here means
        # the library's reference data or MPH limits moved — check before accepting.
        assert PARENT_HEIGHT_LIMITS == {"Maternal": (115.4, 211.9), "Paternal": (121.6, 233.0)}

    def test_limits_are_sex_specific(self):
        assert validate_parent_height(233.0, "Paternal") == 233.0
        with pytest.raises(ValidationError):
            validate_parent_height(233.0, "Maternal")

    """Cases unique to validate_parent_height, not covered by the shared shape."""

    def test_empty_string_returns_none(self):
        assert validate_parent_height("", "Paternal") is None

    def test_rejects_non_finite(self):
        with pytest.raises(ValidationError):
            validate_parent_height(float("nan"), "Maternal")


class TestValidateBoneAge:
    def test_valid_bone_age(self):
        assert validate_bone_age(12.0) == 12.0

    def test_none_rejected(self):
        with pytest.raises(ValidationError):
            validate_bone_age(None)

    def test_negative_rejected(self):
        with pytest.raises(ValidationError):
            validate_bone_age(-1)

    def test_above_maximum_rejected(self):
        with pytest.raises(ValidationError):
            validate_bone_age(999)

    def test_non_finite_rejected(self):
        with pytest.raises(ValidationError):
            validate_bone_age(float("inf"))


class TestValidateBoneAgeStandard:
    def test_valid_gp(self):
        assert validate_bone_age_standard("gp") == "gp"

    def test_valid_tw3(self):
        assert validate_bone_age_standard("tw3") == "tw3"

    def test_default_on_empty(self):
        assert validate_bone_age_standard(None) == "gp"
        assert validate_bone_age_standard("") == "gp"

    def test_invalid_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_bone_age_standard("other")
        assert exc_info.value.code == "ERR_010"


class TestValidateReferenceSupports:
    def test_turner_male_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_reference_supports("turners-syndrome", "male", "height", 10.0)
        assert exc_info.value.code == "ERR_011"

    def test_turner_weight_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_reference_supports("turners-syndrome", "female", "weight", 10.0)
        assert exc_info.value.code == "ERR_011"
        assert "weight" in exc_info.value.message.lower()

    def test_turner_ofc_rejected(self):
        with pytest.raises(ValidationError):
            validate_reference_supports("turners-syndrome", "female", "ofc", 5.0)

    def test_turner_height_female_1y_ok(self):
        validate_reference_supports("turners-syndrome", "female", "height", 1.0)

    def test_turner_under_1y_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_reference_supports("turners-syndrome", "female", "height", 0.5)
        assert exc_info.value.code == "ERR_011"

    def test_cdc_ofc_above_3y_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_reference_supports("cdc", "male", "ofc", 5.0)
        assert exc_info.value.code == "ERR_011"

    def test_cdc_bmi_below_2y_rejected(self):
        with pytest.raises(ValidationError):
            validate_reference_supports("cdc", "female", "bmi", 1.0)

    def test_trisomy21_ofc_18_1y_rejected(self):
        with pytest.raises(ValidationError):
            validate_reference_supports("trisomy-21", "male", "ofc", 18.5)

    def test_uk_who_female_ofc_above_17_rejected(self):
        with pytest.raises(ValidationError):
            validate_reference_supports("uk-who", "female", "ofc", 17.5)

    def test_uk_who_male_ofc_17_5_ok(self):
        # Male upper threshold is 18y, so 17.5 should be accepted.
        validate_reference_supports("uk-who", "male", "ofc", 17.5)

    def test_uk_who_happy_path(self):
        validate_reference_supports("uk-who", "male", "height", 10.0)
        validate_reference_supports("uk-who", "female", "weight", 5.0)
        validate_reference_supports("uk-who", "male", "bmi", 10.0)

    def test_age_none_skips_age_check(self):
        # sex/method still validated even with age=None.
        validate_reference_supports("uk-who", "male", "height", None)
        with pytest.raises(ValidationError):
            validate_reference_supports("turners-syndrome", "male", "height", None)

    def test_unknown_reference_raises(self):
        with pytest.raises(ValidationError):
            validate_reference_supports("unknown", "male", "height", 10.0)


class TestWhoAndTrisomy21AapSupport:
    def test_who_height_18y_ok(self):
        validate_reference_supports("who", "male", "height", 18.0)

    def test_who_weight_above_10y_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_reference_supports("who", "female", "weight", 10.5)
        assert exc_info.value.code == "ERR_011"

    def test_who_ofc_above_5y_rejected(self):
        with pytest.raises(ValidationError):
            validate_reference_supports("who", "male", "ofc", 6.0)

    def test_who_preterm_rejected(self):
        with pytest.raises(ValidationError):
            validate_reference_supports("who", "male", "weight", -0.1)

    def test_who_above_19y_rejected(self):
        with pytest.raises(ValidationError):
            validate_reference_supports("who", "male", "height", 19.5)

    def test_t21_aap_height_10y_ok(self):
        validate_reference_supports("trisomy-21-aap", "female", "height", 10.0)

    def test_t21_aap_ofc_19y_ok(self):
        validate_reference_supports("trisomy-21-aap", "male", "ofc", 19.0)

    def test_t21_aap_bmi_below_2y_rejected(self):
        with pytest.raises(ValidationError):
            validate_reference_supports("trisomy-21-aap", "male", "bmi", 1.0)

    def test_t21_aap_height_below_1_month_rejected(self):
        with pytest.raises(ValidationError):
            validate_reference_supports("trisomy-21-aap", "female", "height", 0.05)

    def test_t21_aap_weight_newborn_ok(self):
        validate_reference_supports("trisomy-21-aap", "female", "weight", 0.01)
