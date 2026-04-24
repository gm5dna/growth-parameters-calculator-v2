"""Tests for utils module."""
from utils import (
    calculate_mid_parental_height,
    format_error_response,
    format_success_response,
    get_chart_data,
    norm_cdf,
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


class TestGetChartData:
    def test_uk_who_height_male(self):
        result = get_chart_data("uk-who", "height", "male")
        assert isinstance(result, list)
        assert len(result) == 9  # cole-nine-centiles
        centile_values = [line["centile"] for line in result]
        assert 0.4 in centile_values
        assert 50 in centile_values or 50.0 in centile_values
        assert 99.6 in centile_values

    def test_centile_line_structure(self):
        result = get_chart_data("uk-who", "height", "male")
        line = result[0]
        assert "centile" in line
        assert "sds" in line
        assert "data" in line
        assert isinstance(line["data"], list)
        assert len(line["data"]) > 0

    def test_data_point_structure(self):
        result = get_chart_data("uk-who", "height", "male")
        point = result[0]["data"][0]
        assert "x" in point
        assert "y" in point
        assert isinstance(point["x"], (int, float))
        assert isinstance(point["y"], (int, float))

    def test_data_points_span_full_age_range(self):
        result = get_chart_data("uk-who", "height", "male")
        median = [line for line in result if line["centile"] == 50][0]
        x_values = [p["x"] for p in median["data"]]
        assert min(x_values) < 0  # preterm data starts before 0
        assert max(x_values) >= 20  # goes to 20 years

    def test_no_none_y_values(self):
        result = get_chart_data("uk-who", "height", "male")
        for line in result:
            for point in line["data"]:
                assert point["y"] is not None

    def test_data_sorted_by_age(self):
        result = get_chart_data("uk-who", "height", "male")
        for line in result:
            x_values = [p["x"] for p in line["data"]]
            assert x_values == sorted(x_values)

    def test_turner_syndrome(self):
        result = get_chart_data("turners-syndrome", "height", "female")
        assert len(result) == 9
        assert len(result[0]["data"]) > 0

    def test_trisomy_21(self):
        result = get_chart_data("trisomy-21", "height", "male")
        assert len(result) == 9

    def test_cdc_weight(self):
        result = get_chart_data("cdc", "weight", "male")
        assert len(result) == 9

    def test_weight_method(self):
        result = get_chart_data("uk-who", "weight", "female")
        assert len(result) == 9

    def test_bmi_method(self):
        result = get_chart_data("uk-who", "bmi", "male")
        assert len(result) == 9

    def test_ofc_method(self):
        result = get_chart_data("uk-who", "ofc", "female")
        assert len(result) == 9
