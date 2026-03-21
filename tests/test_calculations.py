"""Tests for calculations module."""
import pytest
from datetime import date
from calculations import (
    calculate_age_in_years,
    calculate_calendar_age,
    should_apply_gestation_correction,
    calculate_boyd_bsa,
    calculate_cbnf_bsa,
)
from calculations import calculate_height_velocity, calculate_gh_dose


class TestCalculateAgeInYears:
    def test_one_year(self):
        age = calculate_age_in_years(date(2022, 1, 1), date(2023, 1, 1))
        assert abs(age - 1.0) < 0.01

    def test_newborn(self):
        age = calculate_age_in_years(date(2023, 6, 15), date(2023, 6, 16))
        assert age > 0
        assert age < 0.01

    def test_same_day_birth_measurement(self):
        """Birth weight scenario — age is 0."""
        age = calculate_age_in_years(date(2023, 6, 15), date(2023, 6, 15))
        assert age == 0.0

    def test_five_years(self):
        age = calculate_age_in_years(date(2018, 3, 1), date(2023, 3, 1))
        assert abs(age - 5.0) < 0.02

    def test_measurement_before_birth_raises(self):
        with pytest.raises(ValueError):
            calculate_age_in_years(date(2023, 6, 15), date(2023, 6, 14))


class TestCalculateCalendarAge:
    def test_simple_years_months_days(self):
        result = calculate_calendar_age(date(2020, 1, 15), date(2023, 6, 27))
        assert result["years"] == 3
        assert result["months"] == 5
        assert result["days"] == 12

    def test_newborn(self):
        result = calculate_calendar_age(date(2023, 6, 15), date(2023, 6, 16))
        assert result["years"] == 0
        assert result["months"] == 0
        assert result["days"] == 1

    def test_exact_birthday(self):
        result = calculate_calendar_age(date(2020, 6, 15), date(2023, 6, 15))
        assert result["years"] == 3
        assert result["months"] == 0
        assert result["days"] == 0


class TestShouldApplyGestationCorrection:
    def test_term_baby_no_correction(self):
        assert should_apply_gestation_correction(38, 0.5) is False

    def test_preterm_32_36_under_one_year(self):
        assert should_apply_gestation_correction(34, 0.5) is True

    def test_preterm_32_36_over_one_year(self):
        assert should_apply_gestation_correction(34, 1.5) is False

    def test_very_preterm_under_two_years(self):
        assert should_apply_gestation_correction(28, 1.5) is True

    def test_very_preterm_over_two_years(self):
        assert should_apply_gestation_correction(28, 2.5) is False

    def test_none_gestation_no_correction(self):
        assert should_apply_gestation_correction(None, 0.5) is False


class TestCalculateBoydBsa:
    def test_typical_child(self):
        bsa = calculate_boyd_bsa(20.0, 110.0)
        assert 0.7 < bsa < 0.9
        assert isinstance(bsa, float)

    def test_infant(self):
        bsa = calculate_boyd_bsa(3.5, 50.0)
        assert 0.1 < bsa < 0.3

    def test_adolescent(self):
        bsa = calculate_boyd_bsa(60.0, 165.0)
        assert 1.5 < bsa < 1.8

    def test_returns_two_decimal_places(self):
        bsa = calculate_boyd_bsa(20.0, 110.0)
        assert bsa == round(bsa, 2)


class TestCalculateCbnfBsa:
    def test_exact_table_value(self):
        assert calculate_cbnf_bsa(10.0) == 0.49

    def test_interpolation_between_values(self):
        bsa = calculate_cbnf_bsa(15.0)
        assert abs(bsa - 0.64) < 0.01

    def test_minimum_weight(self):
        assert calculate_cbnf_bsa(1.0) == 0.10

    def test_below_minimum_clamps(self):
        assert calculate_cbnf_bsa(0.5) == 0.10

    def test_above_maximum_extrapolates(self):
        bsa = calculate_cbnf_bsa(100.0)
        assert bsa > 2.2

    def test_returns_two_decimal_places(self):
        bsa = calculate_cbnf_bsa(15.0)
        assert bsa == round(bsa, 2)


class TestCalculateHeightVelocity:
    def test_typical_velocity(self):
        result = calculate_height_velocity(106.0, 100.0, 365)
        assert result["value"] is not None
        assert abs(result["value"] - 6.0) < 0.1
        assert result["message"] is None

    def test_interval_too_short(self):
        result = calculate_height_velocity(101.0, 100.0, 90)
        assert result["value"] is None
        assert "at least 4 months" in result["message"]

    def test_no_previous_height(self):
        result = calculate_height_velocity(100.0, None, 365)
        assert result["value"] is None
        assert "requires a previous height" in result["message"]

    def test_no_current_height(self):
        result = calculate_height_velocity(None, 100.0, 365)
        assert result["value"] is None

    def test_rounds_to_one_decimal(self):
        result = calculate_height_velocity(107.3, 100.0, 365)
        assert result["value"] == round(result["value"], 1)


class TestCalculateGhDose:
    def test_basic_dose_calculation(self):
        result = calculate_gh_dose(0.6, 0.58, 20.0)
        assert result["mg_per_day"] == 0.6
        assert abs(result["mg_per_week"] - 4.2) < 0.01
        assert "mg_m2_week" in result
        assert "mcg_kg_day" in result

    def test_mg_m2_week(self):
        result = calculate_gh_dose(0.6, 0.58, 20.0)
        expected = (0.6 * 7) / 0.58
        assert abs(result["mg_m2_week"] - round(expected, 1)) < 0.2

    def test_mcg_kg_day(self):
        result = calculate_gh_dose(0.6, None, 20.0)
        assert abs(result["mcg_kg_day"] - 30.0) < 0.1

    def test_no_bsa_omits_mg_m2(self):
        result = calculate_gh_dose(0.6, None, 20.0)
        assert result["mg_m2_week"] is None

    def test_initial_dose_from_bsa(self):
        result = calculate_gh_dose(None, 0.58, 20.0)
        assert result["initial_daily_dose"] == 0.6
