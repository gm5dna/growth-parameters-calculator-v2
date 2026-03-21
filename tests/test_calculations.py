"""Tests for calculations module."""
import pytest
from datetime import date
from calculations import (
    calculate_age_in_years,
    calculate_calendar_age,
    should_apply_gestation_correction,
)


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
