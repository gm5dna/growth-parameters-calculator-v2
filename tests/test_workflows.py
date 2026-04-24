"""Integration tests — full clinical workflows."""
import json


class TestTypicalWorkflow:
    """Realistic clinical scenarios."""

    def test_three_year_old_male_full_measurements(self, client):
        """Typical well-child check: 3-year-old boy, all measurements."""
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
            "height": 96.0,
            "ofc": 50.0,
            "maternal_height": 165.0,
            "paternal_height": 178.0,
        }
        response = client.post(
            "/calculate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        data = response.get_json()
        assert data["success"] is True
        r = data["results"]

        # All measurement types present
        for key in ["weight", "height", "ofc", "bmi", "mid_parental_height"]:
            assert key in r, f"Missing {key}"

        # BMI auto-calculated correctly
        expected_bmi = round(14.5 / (0.96 ** 2), 1)
        assert r["bmi"]["value"] == expected_bmi

        # MPH for male: (165 + 178) / 2 + 6.5 = 178.0
        assert r["mid_parental_height"]["mid_parental_height"] == 178.0

        # No warnings for normal values
        assert r["validation_messages"] == []

    def test_preterm_infant_with_gestation(self, client):
        """Preterm infant — should apply gestation correction."""
        payload = {
            "sex": "female",
            "birth_date": "2022-09-01",
            "measurement_date": "2023-03-01",
            "weight": 6.5,
            "gestation_weeks": 30,
            "gestation_days": 0,
        }
        response = client.post(
            "/calculate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        data = response.get_json()
        assert data["success"] is True
        assert data["results"]["gestation_correction_applied"] is True

    def test_turner_syndrome_female(self, client):
        """Turner syndrome — female-only, height-only reference."""
        payload = {
            "sex": "female",
            "birth_date": "2015-01-01",
            "measurement_date": "2023-01-01",
            "height": 115.0,
            "reference": "turners-syndrome",
        }
        response = client.post(
            "/calculate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        data = response.get_json()
        assert data["success"] is True
        assert "height" in data["results"]

    def test_height_only_no_bmi(self, client):
        """Only height provided — BMI should not be calculated."""
        payload = {
            "sex": "male",
            "birth_date": "2018-03-01",
            "measurement_date": "2023-03-01",
            "height": 110.0,
        }
        response = client.post(
            "/calculate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        data = response.get_json()
        assert data["success"] is True
        assert "bmi" not in data["results"]
        assert "height" in data["results"]
