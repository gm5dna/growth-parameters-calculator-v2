"""Tests for utils module."""
import pytest
import math
from utils import (
    norm_cdf,
    calculate_mid_parental_height,
    format_error_response,
    format_success_response,
)


class TestNormCdf:
    def test_zero_gives_fifty_percent(self):
        assert abs(norm_cdf(0) - 50.0) < 0.01

    def test_positive_sds(self):
        result = norm_cdf(1.0)
        assert abs(result - 84.13) < 0.5

    def test_negative_sds(self):
        result = norm_cdf(-1.0)
        assert abs(result - 15.87) < 0.5

    def test_extreme_positive(self):
        result = norm_cdf(4.0)
        assert result > 99.99

    def test_extreme_negative(self):
        result = norm_cdf(-4.0)
        assert result < 0.01


class TestCalculateMidParentalHeight:
    def test_male_mph(self):
        result = calculate_mid_parental_height(165.0, 178.0, "male")
        # rcpchgrowth formula: (165 + 178 + 13) / 2 = 178.0
        # Algebraically equivalent to PRD formula: (165 + 178) / 2 + 6.5 = 178.0
        assert result["mid_parental_height"] == 178.0
        assert result["target_range_lower"] == 178.0 - 8.5
        assert result["target_range_upper"] == 178.0 + 8.5
        assert "mid_parental_height_sds" in result
        assert "mid_parental_height_centile" in result

    def test_female_mph(self):
        result = calculate_mid_parental_height(165.0, 178.0, "female")
        # rcpchgrowth: (165 + 178 - 13) / 2 = 165.0
        assert result["mid_parental_height"] == 165.0
        assert result["target_range_lower"] == 165.0 - 8.5
        assert result["target_range_upper"] == 165.0 + 8.5

    def test_returns_none_when_missing_maternal(self):
        assert calculate_mid_parental_height(None, 178.0, "male") is None

    def test_returns_none_when_missing_paternal(self):
        assert calculate_mid_parental_height(165.0, None, "male") is None

    def test_sds_and_centile_are_floats(self):
        result = calculate_mid_parental_height(165.0, 178.0, "male")
        assert isinstance(result["mid_parental_height_sds"], float)
        assert isinstance(result["mid_parental_height_centile"], float)
        assert 0 < result["mid_parental_height_centile"] < 100


class TestFormatErrorResponse:
    def test_structure(self):
        resp = format_error_response("Something went wrong", "ERR_001")
        assert resp["success"] is False
        assert resp["error"] == "Something went wrong"
        assert resp["error_code"] == "ERR_001"


class TestFormatSuccessResponse:
    def test_structure(self):
        results = {"age_years": 2.45}
        resp = format_success_response(results)
        assert resp["success"] is True
        assert resp["results"] == {"age_years": 2.45}
