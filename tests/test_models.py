"""Tests for models module — wraps rcpchgrowth Measurement."""
from datetime import date

import pytest

from models import create_measurement, extract_measurement_result, validate_measurement_sds


class TestCreateMeasurement:
    def test_height_measurement(self):
        result = create_measurement(
            sex="male",
            birth_date=date(2020, 1, 1),
            measurement_date=date(2023, 6, 15),
            measurement_method="height",
            observation_value=95.0,
            reference="uk-who",
        )
        assert result is not None
        calc = result["measurement_calculated_values"]
        assert calc["corrected_sds"] is not None
        assert calc["corrected_centile"] is not None

    def test_weight_measurement(self):
        result = create_measurement(
            sex="female",
            birth_date=date(2021, 3, 10),
            measurement_date=date(2023, 3, 10),
            measurement_method="weight",
            observation_value=12.0,
            reference="uk-who",
        )
        calc = result["measurement_calculated_values"]
        assert isinstance(calc["corrected_sds"], float)

    def test_ofc_measurement(self):
        result = create_measurement(
            sex="male",
            birth_date=date(2022, 6, 1),
            measurement_date=date(2023, 6, 1),
            measurement_method="ofc",
            observation_value=47.0,
            reference="uk-who",
        )
        calc = result["measurement_calculated_values"]
        assert calc["corrected_sds"] is not None

    def test_with_gestation(self):
        result = create_measurement(
            sex="female",
            birth_date=date(2022, 9, 1),
            measurement_date=date(2023, 3, 1),
            measurement_method="weight",
            observation_value=6.5,
            reference="uk-who",
            gestation_weeks=32,
            gestation_days=3,
        )
        dates = result["measurement_dates"]
        assert dates["chronological_decimal_age"] != dates["corrected_decimal_age"]


class TestValidateMeasurementSds:
    def test_normal_sds_no_warning(self):
        warnings = validate_measurement_sds(0.5, "weight")
        assert warnings == []

    def test_warning_threshold(self):
        warnings = validate_measurement_sds(4.5, "height")
        assert len(warnings) == 1
        assert "extreme" in warnings[0].lower()

    def test_hard_limit_raises(self):
        with pytest.raises(ValueError, match="exceeds acceptable range"):
            validate_measurement_sds(8.5, "weight")

    def test_bmi_higher_hard_limit(self):
        # BMI allows up to ±15 SDS
        warnings = validate_measurement_sds(10.0, "bmi")
        assert len(warnings) == 1  # warning but no rejection

    def test_bmi_hard_limit_raises(self):
        with pytest.raises(ValueError, match="exceeds acceptable range"):
            validate_measurement_sds(16.0, "bmi")

    def test_negative_sds_warning(self):
        warnings = validate_measurement_sds(-5.0, "height")
        assert len(warnings) == 1


class TestExtractMeasurementResult:
    def test_extracts_value_centile_sds(self):
        result = create_measurement(
            sex="male",
            birth_date=date(2020, 1, 1),
            measurement_date=date(2023, 6, 15),
            measurement_method="height",
            observation_value=95.0,
            reference="uk-who",
        )
        extracted = extract_measurement_result(result, 95.0)
        assert extracted["value"] == 95.0
        assert "centile" in extracted
        assert "sds" in extracted
        assert isinstance(extracted["centile"], float)
        assert isinstance(extracted["sds"], float)

    def test_none_result_raises_unsupported(self):
        import pytest

        from models import UnsupportedCalculationError
        fake_dict = {
            "measurement_calculated_values": {
                "corrected_centile": None,
                "corrected_sds": None,
            }
        }
        with pytest.raises(UnsupportedCalculationError):
            extract_measurement_result(fake_dict, 95.0, "height")
