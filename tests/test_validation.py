"""Tests for validation module."""
import pytest
from datetime import date
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


class TestValidateWeight:
    def test_valid_weight(self):
        assert validate_weight(12.5) == 12.5

    def test_none_returns_none(self):
        assert validate_weight(None) is None

    def test_below_minimum(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_weight(0.05)
        assert exc_info.value.code == "ERR_004"

    def test_above_maximum(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_weight(301.0)
        assert exc_info.value.code == "ERR_004"

    def test_non_numeric_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_weight("abc")
        assert exc_info.value.code == "ERR_004"

    def test_boundary_minimum(self):
        assert validate_weight(0.1) == 0.1

    def test_boundary_maximum(self):
        assert validate_weight(300.0) == 300.0


class TestValidateHeight:
    def test_valid_height(self):
        assert validate_height(85.3) == 85.3

    def test_none_returns_none(self):
        assert validate_height(None) is None

    def test_below_minimum(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_height(5.0)
        assert exc_info.value.code == "ERR_005"

    def test_above_maximum(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_height(260.0)
        assert exc_info.value.code == "ERR_005"


class TestValidateOfc:
    def test_valid_ofc(self):
        assert validate_ofc(48.2) == 48.2

    def test_none_returns_none(self):
        assert validate_ofc(None) is None

    def test_below_minimum(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_ofc(5.0)
        assert exc_info.value.code == "ERR_006"

    def test_above_maximum(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_ofc(110.0)
        assert exc_info.value.code == "ERR_006"


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
