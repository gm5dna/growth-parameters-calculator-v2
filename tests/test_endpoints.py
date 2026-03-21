"""Tests for Flask endpoints."""
import pytest
import json


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"


class TestCalculateEndpoint:
    def test_basic_calculation(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
            "height": 96.0,
            "ofc": 50.0,
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        results = data["results"]
        assert abs(results["age_years"] - 3.0) < 0.02
        assert results["age_calendar"]["years"] == 3
        assert "weight" in results
        assert "height" in results
        assert "ofc" in results
        assert results["weight"]["value"] == 14.5
        assert isinstance(results["weight"]["sds"], float)
        assert isinstance(results["weight"]["centile"], float)
        assert "bmi" in results
        assert results["bmi"]["value"] > 0

    def test_weight_only(self, client):
        payload = {"sex": "female", "birth_date": "2021-01-01", "measurement_date": "2023-01-01", "weight": 12.0}
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "weight" in data["results"]
        assert "bmi" not in data["results"]

    def test_missing_all_measurements(self, client):
        payload = {"sex": "male", "birth_date": "2020-01-01", "measurement_date": "2023-01-01"}
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert data["error_code"] == "ERR_003"

    def test_missing_sex(self, client):
        payload = {"birth_date": "2020-01-01", "measurement_date": "2023-01-01", "weight": 14.0}
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400

    def test_invalid_date_format(self, client):
        payload = {"sex": "male", "birth_date": "15/06/2020", "measurement_date": "2023-06-15", "weight": 14.0}
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400
        data = response.get_json()
        assert data["error_code"] == "ERR_001"

    def test_with_parental_heights(self, client):
        payload = {"sex": "male", "birth_date": "2020-06-15", "measurement_date": "2023-06-15", "height": 96.0, "maternal_height": 165.0, "paternal_height": 178.0}
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
        data = response.get_json()
        mph = data["results"]["mid_parental_height"]
        assert mph["mid_parental_height"] == 178.0

    def test_with_gestation(self, client):
        payload = {"sex": "female", "birth_date": "2022-09-01", "measurement_date": "2023-03-01", "weight": 6.5, "gestation_weeks": 32, "gestation_days": 3}
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
        data = response.get_json()
        results = data["results"]
        assert results["gestation_correction_applied"] is True
        assert "corrected_age_years" in results

    def test_different_reference(self, client):
        payload = {"sex": "female", "birth_date": "2015-01-01", "measurement_date": "2023-01-01", "height": 120.0, "reference": "turners-syndrome"}
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200

    def test_measurement_before_birth_returns_error(self, client):
        payload = {"sex": "male", "birth_date": "2023-06-15", "measurement_date": "2023-06-14", "weight": 3.5}
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400
        data = response.get_json()
        assert data["error_code"] == "ERR_002"

    def test_empty_body_returns_error(self, client):
        response = client.post("/calculate", data="{}", content_type="application/json")
        assert response.status_code == 400


class TestChartDataEndpoint:
    def test_basic_chart_data(self, client):
        payload = {
            "reference": "uk-who",
            "measurement_method": "height",
            "sex": "male",
        }
        response = client.post(
            "/chart-data",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "centiles" in data
        assert len(data["centiles"]) == 9

    def test_chart_data_centile_structure(self, client):
        payload = {"reference": "uk-who", "measurement_method": "weight", "sex": "female"}
        response = client.post("/chart-data", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        centile_line = data["centiles"][0]
        assert "centile" in centile_line
        assert "sds" in centile_line
        assert "data" in centile_line
        assert len(centile_line["data"]) > 0
        point = centile_line["data"][0]
        assert "x" in point
        assert "y" in point

    def test_chart_data_missing_sex(self, client):
        payload = {"reference": "uk-who", "measurement_method": "height"}
        response = client.post("/chart-data", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400

    def test_chart_data_missing_method(self, client):
        payload = {"reference": "uk-who", "sex": "male"}
        response = client.post("/chart-data", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400

    def test_chart_data_invalid_reference(self, client):
        payload = {"reference": "invalid", "measurement_method": "height", "sex": "male"}
        response = client.post("/chart-data", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400

    def test_chart_data_defaults_reference(self, client):
        payload = {"measurement_method": "height", "sex": "male"}
        response = client.post("/chart-data", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200

    def test_chart_data_bmi(self, client):
        payload = {"reference": "uk-who", "measurement_method": "bmi", "sex": "female"}
        response = client.post("/chart-data", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
        assert len(response.get_json()["centiles"]) == 9

    def test_chart_data_ofc(self, client):
        payload = {"reference": "uk-who", "measurement_method": "ofc", "sex": "male"}
        response = client.post("/chart-data", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200


class TestCalculateWithPreviousMeasurements:
    def test_previous_measurements_processed(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "height": 96.0,
            "previous_measurements": [
                {"date": "2022-12-15", "height": 91.0},
                {"date": "2022-06-15", "height": 86.0},
            ],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        prev = data["results"]["previous_measurements"]
        assert len(prev) == 2
        assert "age" in prev[0]
        assert "height" in prev[0]
        assert "centile" in prev[0]["height"]
        assert "sds" in prev[0]["height"]

    def test_height_velocity_calculated(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "height": 96.0,
            "previous_measurements": [
                {"date": "2022-06-15", "height": 88.0},
            ],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        velocity = data["results"]["height_velocity"]
        assert velocity["value"] is not None
        assert velocity["value"] > 0
        assert "based_on_date" in velocity

    def test_velocity_interval_too_short(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "height": 96.0,
            "previous_measurements": [
                {"date": "2023-05-15", "height": 95.5},
            ],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        velocity = data["results"]["height_velocity"]
        assert velocity["value"] is None
        assert velocity["message"] is not None

    def test_no_previous_measurements_no_velocity(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "height": 96.0,
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        assert "height_velocity" not in data["results"] or data["results"].get("height_velocity") is None

    def test_previous_measurement_invalid_date_skipped(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "height": 96.0,
            "previous_measurements": [
                {"date": "2024-01-01", "height": 100.0},
                {"date": "2022-06-15", "height": 88.0},
            ],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        assert data["success"] is True
        prev = data["results"]["previous_measurements"]
        assert len(prev) == 1


class TestCalculateWithBoneAge:
    def test_bone_age_processed(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2015-06-15",
            "measurement_date": "2023-06-15",
            "height": 125.0,
            "bone_age_assessments": [
                {"date": "2023-06-10", "bone_age": 7.5, "standard": "gp"},
            ],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
        data = response.get_json()
        ba = data["results"]["bone_age_height"]
        assert ba is not None
        assert ba["bone_age"] == 7.5
        assert ba["within_window"] is True
        assert "centile" in ba
        assert "sds" in ba

    def test_bone_age_outside_window(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2015-06-15",
            "measurement_date": "2023-06-15",
            "height": 125.0,
            "bone_age_assessments": [
                {"date": "2023-01-01", "bone_age": 7.0, "standard": "tw3"},
            ],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        ba = data["results"]["bone_age_height"]
        assert ba["within_window"] is False

    def test_bone_age_no_height(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2015-06-15",
            "measurement_date": "2023-06-15",
            "weight": 25.0,
            "bone_age_assessments": [
                {"date": "2023-06-10", "bone_age": 7.5, "standard": "gp"},
            ],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        assert data["results"].get("bone_age_height") is None

    def test_no_bone_age(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2015-06-15",
            "measurement_date": "2023-06-15",
            "height": 125.0,
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        assert data["results"].get("bone_age_height") is None


class TestIndexEndpoint:
    def test_serves_html(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert b"Growth Parameters Calculator" in response.data
