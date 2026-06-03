"""Integration tests for advanced clinical features."""
import json


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


class TestHeightVelocitySelection:
    def test_uses_older_valid_height_when_newest_is_too_recent(self, client):
        """A too-recent previous height must not mask an older valid one.

        Newest previous height is ~1 month before the current measurement
        (below the 4-month minimum); an older one is ~13 months before.
        Velocity must be computed from the older, valid measurement.
        """
        payload = {
            "sex": "male",
            "birth_date": "2015-06-15",
            "measurement_date": "2023-06-15",
            "height": 125.0,
            "previous_measurements": [
                {"date": "2023-05-15", "height": 124.0},  # ~1 month — too recent
                {"date": "2022-05-15", "height": 117.0},  # ~13 months — valid
            ],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        assert data["success"] is True
        hv = data["results"]["height_velocity"]
        assert hv["value"] is not None
        assert hv["based_on_date"] == "2022-05-15"

    def test_message_when_no_previous_height_is_old_enough(self, client):
        """When every previous height is too recent, surface the interval message."""
        payload = {
            "sex": "male",
            "birth_date": "2015-06-15",
            "measurement_date": "2023-06-15",
            "height": 125.0,
            "previous_measurements": [
                {"date": "2023-05-15", "height": 124.0},  # ~1 month only
            ],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        assert data["success"] is True
        hv = data["results"]["height_velocity"]
        assert hv["value"] is None
        assert "4 months" in hv["message"]


class TestNestedPayloadValidation:
    def test_previous_measurements_not_a_list_returns_400(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "height": 96.0,
            "previous_measurements": "not-a-list",
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400
        body = response.get_json()
        assert body["success"] is False
        assert body["error_code"] == "ERR_010"

    def test_bone_age_assessments_not_a_list_returns_400(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2015-06-15",
            "measurement_date": "2023-06-15",
            "height": 125.0,
            "bone_age_assessments": "not-a-list",
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400
        assert response.get_json()["error_code"] == "ERR_010"

    def test_previous_measurements_non_object_entry_returns_400(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "height": 96.0,
            "previous_measurements": ["just-a-string"],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400
        assert response.get_json()["error_code"] == "ERR_010"

    def test_too_many_previous_measurements_returns_400(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "height": 96.0,
            "previous_measurements": [
                {"date": "2022-01-01", "height": 90.0} for _ in range(51)
            ],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400
        assert response.get_json()["error_code"] == "ERR_010"
