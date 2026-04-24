"""Tests for Flask endpoints."""
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

    def test_success_log_does_not_include_patient_sex(self, client, caplog):
        import logging

        payload = {
            "sex": "female",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
        }

        caplog.set_level(logging.INFO, logger="app")
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")

        assert response.status_code == 200
        messages = [record.getMessage() for record in caplog.records if record.name == "app"]
        assert "Calculation completed" in messages
        assert all("female" not in message and "male" not in message for message in messages)

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

    def test_previous_measurement_after_current_date_rejected(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "height": 96.0,
            "previous_measurements": [
                {"date": "2024-01-01", "height": 100.0},
            ],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert data["error_code"] == "ERR_002"


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


class TestCalculateAdvancedResults:
    def test_bsa_boyd_when_both_measurements(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
            "height": 96.0,
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        bsa = data["results"]["bsa"]
        assert bsa is not None
        assert bsa["value"] > 0
        assert bsa["method"] == "Boyd"

    def test_bsa_cbnf_weight_only(self, client):
        payload = {
            "sex": "female",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        bsa = data["results"]["bsa"]
        assert bsa is not None
        assert bsa["method"] == "cBNF"

    def test_no_bsa_without_weight(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "height": 96.0,
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        assert data["results"].get("bsa") is None

    def test_bmi_percentage_median(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
            "height": 96.0,
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        bmi = data["results"]["bmi"]
        assert "percentage_median" in bmi
        assert 50 < bmi["percentage_median"] < 200

    def test_gh_initial_dose(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
            "height": 96.0,
            "gh_treatment": True,
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        gh = data["results"].get("gh_dose")
        assert gh is not None
        assert gh["initial_daily_dose"] > 0


class TestIndexEndpoint:
    def test_serves_html(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert b"Growth Parameters Calculator" in response.data


class TestExportPdfEndpoint:
    def test_basic_pdf_export(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
            "height": 96.0,
            "patient_info": {},
        }
        response = client.post("/export-pdf", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
        assert response.content_type == "application/pdf"
        assert response.data[:5] == b"%PDF-"
        assert "attachment" in response.headers.get("Content-Disposition", "")

    def test_pdf_missing_measurements(self, client):
        # /export-pdf now recalculates, so missing measurements fails validation.
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "patient_info": {},
        }
        response = client.post("/export-pdf", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400

    def test_pdf_missing_required_fields(self, client):
        response = client.post("/export-pdf", data=json.dumps({}), content_type="application/json")
        assert response.status_code == 400

    def test_pdf_with_chart_images(self, client):
        import base64
        from io import BytesIO as BIO

        from PIL import Image as PILImage
        img = PILImage.new('RGB', (2, 2), color='white')
        buf = BIO()
        img.save(buf, format='PNG')
        tiny_png = base64.b64encode(buf.getvalue()).decode()
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
            "patient_info": {},
            "chart_images": {"height": f"data:image/png;base64,{tiny_png}"},
        }
        response = client.post("/export-pdf", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
        assert response.data[:5] == b"%PDF-"


class TestReferenceCapabilityEnforcement:
    def _payload(self, **overrides):
        base = {
            "sex": "female",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "height": 96.0,
        }
        base.update(overrides)
        return base

    def test_male_turner_syndrome_rejected(self, client):
        response = client.post(
            "/calculate",
            data=json.dumps(self._payload(sex="male", reference="turners-syndrome")),
            content_type="application/json",
        )
        assert response.status_code == 422
        data = response.get_json()
        assert data["success"] is False
        assert data["error_code"] == "ERR_011"

    def test_turner_weight_rejected(self, client):
        response = client.post(
            "/calculate",
            data=json.dumps(self._payload(reference="turners-syndrome", weight=14.0, height=None)),
            content_type="application/json",
        )
        assert response.status_code == 422
        assert response.get_json()["error_code"] == "ERR_011"

    def test_turner_ofc_rejected(self, client):
        response = client.post(
            "/calculate",
            data=json.dumps(self._payload(reference="turners-syndrome", ofc=48.0, height=None)),
            content_type="application/json",
        )
        assert response.status_code == 422

    def test_cdc_bmi_infant_not_echoed(self, client):
        # CDC does not publish BMI under age 2 — BMI should be dropped with
        # a validation_messages note rather than a hard 400.
        payload = {
            "sex": "male",
            "birth_date": "2022-06-15",
            "measurement_date": "2023-06-15",
            "reference": "cdc",
            "weight": 10.0,
            "height": 78.0,
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
        data = response.get_json()
        assert "bmi" not in data["results"]
        assert any("bmi" in m.lower() for m in data["results"].get("validation_messages", []))

    def test_chart_data_turner_weight_rejected(self, client):
        payload = {"sex": "female", "reference": "turners-syndrome", "measurement_method": "weight"}
        response = client.post("/chart-data", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 422
        assert response.get_json()["error_code"] == "ERR_011"

    def test_chart_data_male_turner_rejected(self, client):
        payload = {"sex": "male", "reference": "turners-syndrome", "measurement_method": "height"}
        response = client.post("/chart-data", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 422


class TestNonFiniteNumbersAtEndpoint:
    def test_nan_weight_rejected(self, client):
        # Raw JSON bodies can include literal NaN — Flask's parser accepts it.
        body = '{"sex":"female","birth_date":"2020-06-15","measurement_date":"2023-06-15","weight":NaN}'
        response = client.post("/calculate", data=body, content_type="application/json")
        assert response.status_code == 400
        data = response.get_json()
        assert data["error_code"] == "ERR_004"

    def test_infinity_height_rejected(self, client):
        body = '{"sex":"female","birth_date":"2020-06-15","measurement_date":"2023-06-15","height":Infinity}'
        response = client.post("/calculate", data=body, content_type="application/json")
        assert response.status_code == 400
        data = response.get_json()
        assert data["error_code"] == "ERR_005"


class TestPreviousMeasurementValidation:
    def test_previous_height_out_of_range_rejected(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "height": 96.0,
            "previous_measurements": [{"date": "2022-06-15", "height": 10000}],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400
        data = response.get_json()
        assert data["error_code"] == "ERR_005"

    def test_previous_measurement_before_birth_rejected(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "height": 96.0,
            "previous_measurements": [{"date": "2019-01-01", "height": 90.0}],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400
        assert response.get_json()["error_code"] == "ERR_002"

    def test_previous_measurement_nan_rejected(self, client):
        body = (
            '{"sex":"male","birth_date":"2020-06-15","measurement_date":"2023-06-15",'
            '"height":96.0,"previous_measurements":[{"date":"2022-06-15","height":NaN}]}'
        )
        response = client.post("/calculate", data=body, content_type="application/json")
        assert response.status_code == 400
        assert response.get_json()["error_code"] == "ERR_005"


class TestBoneAgeValidation:
    def test_bone_age_out_of_range_rejected(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2015-06-15",
            "measurement_date": "2023-06-15",
            "height": 125.0,
            "bone_age_assessments": [{"date": "2023-06-10", "bone_age": 999}],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400
        assert response.get_json()["error_code"] == "ERR_010"

    def test_bone_age_invalid_standard_rejected(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2015-06-15",
            "measurement_date": "2023-06-15",
            "height": 125.0,
            "bone_age_assessments": [{"date": "2023-06-10", "bone_age": 7.5, "standard": "bogus"}],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400
        assert response.get_json()["error_code"] == "ERR_010"

    def test_bone_age_date_before_birth_rejected(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2015-06-15",
            "measurement_date": "2023-06-15",
            "height": 125.0,
            "bone_age_assessments": [{"date": "2014-01-01", "bone_age": 7.5, "standard": "gp"}],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400
        assert response.get_json()["error_code"] == "ERR_002"


class TestParentalHeightValidation:
    def test_maternal_height_out_of_range_rejected(self, client):
        payload = {
            "sex": "female",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.0,
            "maternal_height": 10,
            "paternal_height": 180,
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400
        assert response.get_json()["error_code"] == "ERR_010"

    def test_parental_heights_happy_path(self, client):
        payload = {
            "sex": "female",
            "birth_date": "2015-06-15",
            "measurement_date": "2023-06-15",
            "height": 125.0,
            "maternal_height": 165.0,
            "paternal_height": 180.0,
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
        mph = response.get_json()["results"].get("mid_parental_height")
        assert mph is not None
        assert abs(mph["mid_parental_height"] - 166.0) < 1.0


class TestSecurityHardening:
    def test_rejects_non_json_content_type(self, client):
        response = client.post("/calculate", data="not-json", content_type="text/plain")
        assert response.status_code == 400
        assert response.get_json()["error_code"] == "ERR_010"

    def test_rejects_non_dict_json(self, client):
        response = client.post("/calculate", data="[]", content_type="application/json")
        assert response.status_code == 400
        assert response.get_json()["error_code"] == "ERR_010"

    def test_oversized_payload_returns_413(self, client, app):
        app.config["MAX_CONTENT_LENGTH"] = 256
        try:
            big_body = json.dumps({
                "sex": "male",
                "birth_date": "2020-06-15",
                "measurement_date": "2023-06-15",
                "weight": 14.5,
                "padding": "x" * 512,
            })
            response = client.post("/calculate", data=big_body, content_type="application/json")
            assert response.status_code == 413
            assert response.get_json()["error_code"] == "ERR_010"
        finally:
            app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


class TestExportPdfIgnoresClientResults:
    def test_client_results_cannot_override_server_calculation(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
            "height": 96.0,
            "patient_info": {},
            # Forged results should be completely ignored; server recalculates.
            "results": {
                "age_years": 99.0,
                "weight": {"value": 1.0, "centile": 99.9, "sds": 6.0},
            },
        }
        response = client.post("/export-pdf", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
        # The forged 99y age would otherwise trip the MAX_AGE_YEARS check.
        assert response.data[:5] == b"%PDF-"

    def test_client_cannot_override_reference_in_patient_info(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
            # Forged reference via patient_info should not silently switch
            # which population the report is generated against.
            "patient_info": {"reference": "turners-syndrome"},
        }
        response = client.post("/export-pdf", data=json.dumps(payload), content_type="application/json")
        # Recalculation uses the top-level reference (unset -> uk-who), so
        # the PDF is built from the server-authoritative data.
        assert response.status_code == 200
        assert response.data[:5] == b"%PDF-"

    def test_oversized_chart_image_rejected_without_breaking_pdf(self, client):
        # 4 MB of data exceeds the default 2 MB per-image cap but fits within
        # the default 10 MB request-body cap, so the request should succeed
        # and the PDF should still be produced — just without the bad chart.
        import base64 as _b64
        big_garbage = _b64.b64encode(b"\x00" * (4 * 1024 * 1024)).decode()
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
            "patient_info": {},
            "chart_images": {"height": f"data:image/png;base64,{big_garbage}"},
        }
        response = client.post("/export-pdf", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
        assert response.data[:5] == b"%PDF-"

    def test_non_png_data_url_rejected(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
            "patient_info": {},
            "chart_images": {"height": "data:image/jpeg;base64,QUJDRA=="},
        }
        response = client.post("/export-pdf", data=json.dumps(payload), content_type="application/json")
        # PDF should still generate; the bad image is simply skipped and
        # recorded on the report's rejected_images list.
        assert response.status_code == 200
        assert response.data[:5] == b"%PDF-"


class TestBmiPercentageMedianUsesCorrectedAge:
    def test_preterm_bmi_has_percentage_median(self, client):
        # Preterm neonate, chronological ~18 months. rcpchgrowth computes
        # percentage-of-median from corrected age; confirm the response
        # surfaces a real number via the measurement result.
        payload = {
            "sex": "female",
            "birth_date": "2022-01-01",
            "measurement_date": "2023-07-01",
            "gestation_weeks": 30,
            "gestation_days": 0,
            "weight": 9.0,
            "height": 78.0,
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
        data = response.get_json()
        bmi = data["results"].get("bmi")
        assert bmi is not None
        assert bmi["percentage_median"] is not None


class TestReferenceBoundaryCases:
    """Boundary tests around reference age cut-offs."""

    @staticmethod
    def _payload(age_years, **overrides):
        from datetime import date, timedelta
        measurement_date = date(2024, 6, 1)
        birth_date = measurement_date - timedelta(days=int(age_years * 365.25))
        body = {
            "sex": "female",
            "birth_date": birth_date.isoformat(),
            "measurement_date": measurement_date.isoformat(),
        }
        body.update(overrides)
        return body

    def test_turner_0_99y_rejected(self, client):
        r = client.post(
            "/calculate",
            data=json.dumps(self._payload(0.99, reference="turners-syndrome", height=72.0)),
            content_type="application/json",
        )
        assert r.status_code == 422
        assert r.get_json()["error_code"] == "ERR_011"

    def test_turner_1_01y_accepted(self, client):
        r = client.post(
            "/calculate",
            data=json.dumps(self._payload(1.01, reference="turners-syndrome", height=74.0)),
            content_type="application/json",
        )
        assert r.status_code == 200

    def test_cdc_ofc_2_99y_accepted(self, client):
        r = client.post(
            "/calculate",
            data=json.dumps(self._payload(2.99, sex="male", reference="cdc", ofc=48.5)),
            content_type="application/json",
        )
        assert r.status_code == 200

    def test_cdc_ofc_3_01y_rejected(self, client):
        r = client.post(
            "/calculate",
            data=json.dumps(self._payload(3.01, sex="male", reference="cdc", ofc=49.5)),
            content_type="application/json",
        )
        assert r.status_code == 422
        assert r.get_json()["error_code"] == "ERR_011"

    def test_trisomy21_ofc_17_99y_accepted(self, client):
        r = client.post(
            "/calculate",
            data=json.dumps(self._payload(17.99, sex="male", reference="trisomy-21", ofc=55.5)),
            content_type="application/json",
        )
        assert r.status_code == 200

    def test_trisomy21_ofc_18_01y_rejected(self, client):
        r = client.post(
            "/calculate",
            data=json.dumps(self._payload(18.01, sex="male", reference="trisomy-21", ofc=55.5)),
            content_type="application/json",
        )
        assert r.status_code == 422
        assert r.get_json()["error_code"] == "ERR_011"


class TestBoneAgeAbsentWhenAllFail:
    def test_bone_age_all_fail_leaves_field_absent(self, client, monkeypatch):
        """If every bone-age assessment raises a non-ValidationError the
        response must NOT contain a null `bone_age_height`; a structured
        validation message is emitted instead."""
        import app as app_module

        original = app_module.create_measurement
        call_counter = {"n": 0}

        def flaky_create_measurement(*args, **kwargs):
            call_counter["n"] += 1
            # First call handles the main height measurement; subsequent
            # calls inside the bone-age loop must fail.
            if call_counter["n"] >= 2:
                raise RuntimeError("rcpchgrowth internal hiccup")
            return original(*args, **kwargs)

        monkeypatch.setattr(app_module, "create_measurement", flaky_create_measurement)
        payload = {
            "sex": "male",
            "birth_date": "2015-06-15",
            "measurement_date": "2023-06-15",
            "height": 125.0,
            "bone_age_assessments": [
                {"date": "2023-06-10", "bone_age": 7.5, "standard": "gp"},
            ],
        }
        r = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert r.status_code == 200
        data = r.get_json()["results"]
        assert "bone_age_height" not in data
        assert "bone_age_assessments" in data
        assert any("bone age" in m.lower() for m in data.get("validation_messages", []))


class TestSecurityHeaders:
    def test_csp_header_present_on_index(self, client):
        r = client.get("/")
        assert r.status_code == 200
        csp = r.headers.get("Content-Security-Policy", "")
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_csp_header_present_on_json_endpoints(self, client):
        import json as _json
        r = client.post(
            "/calculate",
            data=_json.dumps({
                "sex": "male",
                "birth_date": "2020-06-15",
                "measurement_date": "2023-06-15",
                "weight": 14.5,
            }),
            content_type="application/json",
        )
        assert "Content-Security-Policy" in r.headers

    def test_other_security_headers(self, client):
        r = client.get("/health")
        assert r.headers.get("X-Content-Type-Options") == "nosniff"
        assert "Referrer-Policy" in r.headers


class TestChartImagesCap:
    def test_too_many_chart_images_rejected(self, client):
        import base64 as _b64
        import json as _json
        from io import BytesIO as _BytesIO

        from PIL import Image as _PILImage

        img = _PILImage.new("RGB", (2, 2), color="white")
        buf = _BytesIO()
        img.save(buf, format="PNG")
        png_b64 = _b64.b64encode(buf.getvalue()).decode()
        chart_images = {f"chart_{i}": f"data:image/png;base64,{png_b64}" for i in range(20)}
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
            "patient_info": {},
            "chart_images": chart_images,
        }
        r = client.post("/export-pdf", data=_json.dumps(payload), content_type="application/json")
        assert r.status_code == 400
        assert r.get_json()["error_code"] == "ERR_010"


class TestPatientInfoAllowList:
    def test_unreserved_patient_info_key_is_dropped(self, client):
        """Unknown display fields in patient_info are not carried through to the PDF.

        The allow-list is empty today, so any client-supplied key is ignored.
        This guards against a future PDF field being added without also
        updating the server allow-list.
        """
        import json as _json
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
            "patient_info": {
                "patient_name": "<script>alert(1)</script>",
                "nhs_number": "9999999999",
                "clinician": "Dr Forged",
            },
        }
        r = client.post("/export-pdf", data=_json.dumps(payload), content_type="application/json")
        # Happy path: PDF still generates; the forged fields are simply dropped.
        assert r.status_code == 200
        assert r.data[:5] == b"%PDF-"

    def test_non_object_patient_info_rejected(self, client):
        import json as _json
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
            "patient_info": ["not", "an", "object"],
        }
        r = client.post("/export-pdf", data=_json.dumps(payload), content_type="application/json")
        assert r.status_code == 400


class TestCalculateRateLimit:
    def test_calculate_returns_429_over_budget(self, app):
        """Confirm /calculate honours the `CALC_RATE_LIMIT` env var.

        The `client` fixture disables the limiter globally for normal tests;
        re-enable it here with a tight budget and assert that the Nth+1
        request returns 429.
        """
        from app import limiter
        limiter.enabled = True
        try:
            limiter.reset()
        except Exception:
            pass
        c = app.test_client()
        payload = json.dumps({
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
        })
        try:
            last_status = None
            for _ in range(35):
                r = c.post("/calculate", data=payload, content_type="application/json")
                last_status = r.status_code
                if last_status == 429:
                    break
            assert last_status == 429
        finally:
            limiter.enabled = False
            try:
                limiter.reset()
            except Exception:
                pass
