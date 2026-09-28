"""Tests for calculations module."""
from datetime import date

import pytest

from calculations import (
    calculate_age_in_years,
    calculate_boyd_bsa,
    calculate_calendar_age,
    calculate_cbnf_bsa,
    calculate_gh_dose,
    calculate_height_velocity,
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
    """Correction stops at the CORRECTED birthday (RCPCH date-age-calculations)."""

    BIRTH = date(2024, 1, 1)

    def test_term_baby_no_correction(self):
        assert should_apply_gestation_correction(self.BIRTH, date(2024, 7, 1), 38) is False

    def test_none_gestation_no_correction(self):
        assert should_apply_gestation_correction(self.BIRTH, date(2024, 7, 1), None) is False

    def test_before_edd_still_corrected(self):
        # 28+0 born 2024-01-01: EDD 2024-03-25; 2024-02-01 is before EDD.
        assert should_apply_gestation_correction(self.BIRTH, date(2024, 2, 1), 28) is True

    def test_34wk_first_corrected_birthday(self):
        # 34+0: EDD = 2024-02-12, so 1st corrected birthday = 2025-02-12.
        assert should_apply_gestation_correction(self.BIRTH, date(2025, 2, 11), 34) is True
        assert should_apply_gestation_correction(self.BIRTH, date(2025, 2, 12), 34) is False

    def test_28wk_second_corrected_birthday(self):
        # 28+0: EDD = 2024-03-25, so 2nd corrected birthday = 2026-03-25.
        assert should_apply_gestation_correction(self.BIRTH, date(2026, 3, 24), 28) is True
        assert should_apply_gestation_correction(self.BIRTH, date(2026, 3, 25), 28) is False

    def test_28wk_past_first_birthday_still_corrected(self):
        assert should_apply_gestation_correction(self.BIRTH, date(2025, 6, 1), 28) is True

    def test_31_plus_6_vs_32_plus_0(self):
        # ~1.5 y corrected: 31+6 is "<32" (2-year rule), 32+0 is the 1-year rule.
        on = date(2025, 8, 1)
        assert should_apply_gestation_correction(self.BIRTH, on, 31, 6) is True
        assert should_apply_gestation_correction(self.BIRTH, on, 32, 0) is False

    def test_36_plus_6_vs_37_plus_0(self):
        on = date(2024, 6, 1)
        assert should_apply_gestation_correction(self.BIRTH, on, 36, 6) is True
        assert should_apply_gestation_correction(self.BIRTH, on, 37, 0) is False


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

    def test_above_maximum_clamps_to_top_value(self):
        # Above the cBNF table (90 kg -> 2.2 m2) we clamp rather than
        # extrapolate: extrapolation produced impossible areas (~5.35 m2 at
        # the 300 kg cap) that then drove the GH dose calculation.
        assert calculate_cbnf_bsa(100.0) == 2.2
        assert calculate_cbnf_bsa(300.0) == 2.2

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
    def test_initial_dose_from_bsa(self):
        result = calculate_gh_dose(0.58)
        assert result["initial_daily_dose"] == 0.6
