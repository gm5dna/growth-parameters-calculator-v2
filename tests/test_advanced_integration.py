"""Integration tests for advanced clinical features."""
import json
import pytest


class TestAdvancedFeatures:
    def test_full_advanced_workflow(self, client):
        """Complete advanced calculation: all measurements, previous, bone age, GH."""
        payload = {
            "sex": "male",
            "birth_date": "2015-06-15",
            "measurement_date": "2023-06-15",
            "weight": 25.0,
            "height": 125.0,
            "ofc": 52.0,
            "maternal_height": 165.0,
            "paternal_height": 178.0,
            "reference": "uk-who",
            "gh_treatment": True,
            "previous_measurements": [
                {"date": "2022-06-15", "height": 118.0, "weight": 22.0},
                {"date": "2021-06-15", "height": 111.0},
            ],
            "bone_age_assessments": [
                {"date": "2023-06-10", "bone_age": 7.5, "standard": "gp"},
            ],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        assert data["success"] is True
        r = data["results"]

        # Core results
        assert "weight" in r
        assert "height" in r
        assert "bmi" in r
        assert "ofc" in r
        assert "mid_parental_height" in r

        # BSA
        assert r["bsa"]["method"] == "Boyd"
        assert r["bsa"]["value"] > 0

        # BMI % median
        assert r["bmi"]["percentage_median"] is not None

        # Previous measurements
        assert len(r["previous_measurements"]) == 2
        assert "height" in r["previous_measurements"][0]

        # Height velocity
        assert r["height_velocity"]["value"] is not None

        # Bone age
        assert r["bone_age_height"]["within_window"] is True
        assert r["bone_age_height"]["centile"] is not None

        # GH dose
        assert r["gh_dose"]["initial_daily_dose"] > 0

    def test_bsa_cbnf_fallback(self, client):
        """Weight only — should use cBNF for BSA."""
        payload = {
            "sex": "female",
            "birth_date": "2020-01-01",
            "measurement_date": "2023-01-01",
            "weight": 14.0,
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        assert data["results"]["bsa"]["method"] == "cBNF"

    def test_trisomy_21_with_previous(self, client):
        """Trisomy 21 reference with previous measurements."""
        payload = {
            "sex": "male",
            "birth_date": "2018-01-01",
            "measurement_date": "2023-01-01",
            "height": 100.0,
            "reference": "trisomy-21",
            "previous_measurements": [
                {"date": "2022-01-01", "height": 93.0},
            ],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        assert data["success"] is True
        assert len(data["results"]["previous_measurements"]) == 1
        assert data["results"]["height_velocity"]["value"] is not None
