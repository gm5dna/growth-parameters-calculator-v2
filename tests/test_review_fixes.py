"""Tests for the code-review fixes.

Covers corrected-age cut-off, warn-and-skip, H5, M1-M5, L2-L5, L13, SDS
boundaries and the top-level error handlers.
"""
import pytest

from calculations import calculate_height_velocity
from constants import REFERENCE_CAPABILITIES

BASE = {"sex": "male", "birth_date": "2020-01-01", "measurement_date": "2026-01-01"}


def _calc(client, **extra):
    return client.post("/calculate", json={**BASE, **extra})


class TestSdsBoundaries:
    """Pin the strict '>' comparisons at the warning and hard limits."""

    def test_warning_limit_is_exclusive(self):
        from models import validate_measurement_sds
        assert validate_measurement_sds(4.0, "height") == []
        assert len(validate_measurement_sds(4.01, "height")) == 1

    def test_hard_limit_is_exclusive(self):
        from models import SdsOutOfRangeError, validate_measurement_sds
        assert len(validate_measurement_sds(8.0, "height")) == 1
        assert len(validate_measurement_sds(-8.0, "weight")) == 1
        with pytest.raises(SdsOutOfRangeError):
            validate_measurement_sds(8.01, "height")

    def test_bmi_hard_limit(self):
        from models import SdsOutOfRangeError, validate_measurement_sds
        assert len(validate_measurement_sds(15.0, "bmi")) == 1
        with pytest.raises(SdsOutOfRangeError):
            validate_measurement_sds(15.01, "bmi")


class TestBoneAgeWarnings:
    def test_extreme_bone_age_sds_warns_and_returns(self, client):
        r = _calc(client, height=115, bone_age_assessments=[{"date": "2026-01-01", "bone_age": 0.5}])
        assert r.status_code == 200
        res = r.get_json()["results"]
        assert "bone_age_height" in res
        assert any("outside ±8 SDS; check bone age and height" in m for m in res["validation_messages"])

    def test_advisory_bone_age_sds(self, client):
        r = _calc(client, height=120, bone_age_assessments=[{"date": "2026-01-01", "bone_age": 3}])
        res = r.get_json()["results"]
        assert r.status_code == 200
        assert any("very extreme" in m for m in res["validation_messages"])
        assert not any("outside" in m for m in res["validation_messages"])

    def test_unsupported_reference_skips_bone_age(self, client):
        r = client.post("/calculate", json={
            "sex": "female", "birth_date": "2020-01-01", "measurement_date": "2026-01-01",
            "height": 110, "reference": "turners-syndrome",
            "bone_age_assessments": [{"date": "2026-01-01", "bone_age": 0.5}],
        })
        assert r.status_code == 200
        res = r.get_json()["results"]
        assert "bone_age_height" not in res
        assert any("Height for bone age not calculated" in m for m in res["validation_messages"])


class TestPreviousMeasurements:
    def test_extreme_previous_sds_warns_and_skips(self, client):
        r = _calc(client, height=115, previous_measurements=[{"date": "2025-01-01", "height": 30}])
        assert r.status_code == 200
        res = r.get_json()["results"]
        assert "previous_measurements" not in res
        assert "height_velocity" not in res
        assert any("2025-01-01" in m and "excluded" in m for m in res["validation_messages"])

    def test_extreme_previous_does_not_mask_valid_one(self, client):
        r = _calc(client, height=115, previous_measurements=[
            {"date": "2025-01-01", "height": 30},
            {"date": "2025-06-01", "height": 108},
        ])
        res = r.get_json()["results"]
        assert [p["date"] for p in res["previous_measurements"]] == ["2025-06-01"]
        assert res["height_velocity"]["based_on_date"] == "2025-06-01"

    def test_padded_previous_date_velocity(self, client):
        r = _calc(client, height=115, previous_measurements=[{"date": " 2025-01-01 ", "height": 108}])
        assert r.status_code == 200
        hv = r.get_json()["results"]["height_velocity"]
        assert hv["value"] == pytest.approx(7.0, abs=0.1)
        assert hv["based_on_date"] == "2025-01-01"

    def test_preterm_corrected_age_on_previous(self, client):
        r = client.post("/calculate", json={
            "sex": "male", "birth_date": "2025-01-01", "measurement_date": "2026-01-01",
            "gestation_weeks": 30, "gestation_days": 0, "weight": 8.0,
            "previous_measurements": [
                {"date": "2025-02-01", "weight": 1.6},   # before EDD 2025-03-12
                {"date": "2025-06-01", "weight": 5.0},
            ],
        })
        assert r.status_code == 200
        prev = {p["date"]: p for p in r.get_json()["results"]["previous_measurements"]}
        assert "corrected_age" not in prev["2025-02-01"]
        assert prev["2025-06-01"]["corrected_age"] == pytest.approx(81 / 365.25, abs=1e-3)


class TestVelocityInterval:
    def test_121_vs_122_days(self):
        assert calculate_height_velocity(100, 95, 121)["value"] is None
        assert calculate_height_velocity(100, 95, 122)["value"] is not None


class TestGestationCutoffEndpoint:
    def test_correction_flag_at_corrected_birthday(self, client):
        # 34+0 born 2024-01-01: 1st corrected birthday 2025-02-12.
        def flag(day):
            r = client.post("/calculate", json={
                "sex": "male", "birth_date": "2024-01-01", "measurement_date": day,
                "gestation_weeks": 34, "gestation_days": 0, "weight": 10.0,
            })
            assert r.status_code == 200
            return r.get_json()["results"]["gestation_correction_applied"]
        assert flag("2025-02-11") is True
        assert flag("2025-02-12") is False


class TestInputTypeGuards:
    @pytest.mark.parametrize("field,value", [
        ("sex", ["male"]), ("sex", {"a": 1}), ("reference", ["uk-who"]), ("reference", {"a": 1}),
    ])
    def test_non_string_sex_reference_is_400(self, client, field, value):
        r = _calc(client, weight=20, **{field: value})
        assert r.status_code == 400

    @pytest.mark.parametrize("value", [["gp"], {"a": 1}])
    def test_non_string_bone_age_standard_is_400(self, client, value):
        r = _calc(client, height=115, bone_age_assessments=[
            {"date": "2026-01-01", "bone_age": 5, "standard": value}])
        assert r.status_code == 400

    @pytest.mark.parametrize("value", [["height"], {"a": 1}])
    def test_chart_data_method_non_string_is_400(self, client, value):
        r = client.post("/chart-data", json={"sex": "male", "reference": "uk-who", "measurement_method": value})
        assert r.status_code == 400

    @pytest.mark.parametrize("field", ["weight", "height", "ofc"])
    def test_bool_measurement_rejected(self, client, field):
        r = _calc(client, **{field: True})
        assert r.status_code == 400


class TestReferenceLimits:
    def test_uk_who_height_lower_bound(self):
        lo, hi = REFERENCE_CAPABILITIES["uk-who"]["method_age_overrides"]["height"]
        assert lo == pytest.approx(-105 / 365.25)
        assert hi == 20.0

    def test_uk_who_bmi_lower_bound(self):
        assert REFERENCE_CAPABILITIES["uk-who"]["method_age_overrides"]["bmi"][0] == pytest.approx(14 / 365.25)

    def test_24_week_height_gets_range_message(self, client):
        # Born 24+0, measured on the birth date: before 25 weeks -> 422 range message.
        r = client.post("/calculate", json={
            "sex": "male", "birth_date": "2025-01-01", "measurement_date": "2025-01-01",
            "gestation_weeks": 24, "gestation_days": 0, "height": 32,
        })
        assert r.status_code == 422
        assert "does not support height" in r.get_json()["error"]


class TestBsaClamp:
    def test_weight_only_above_table_warns(self, client):
        r = client.post("/calculate", json={
            "sex": "male", "birth_date": "2008-01-01", "measurement_date": "2026-01-01", "weight": 150,
        })
        assert r.status_code == 200
        msgs = r.get_json()["results"]["validation_messages"]
        assert any("clamped" in m for m in msgs)

    def test_weight_only_inside_table_no_warning(self, client):
        r = _calc(client, weight=20)
        assert not any("clamped" in m for m in r.get_json()["results"]["validation_messages"])


class TestGhSelectedDose:
    PAYLOAD = {**BASE, "weight": 20, "height": 115, "gh_treatment": True}

    @staticmethod
    def _text(results):
        from pdf_utils import GrowthReportPDF
        story = []
        GrowthReportPDF(results, {})._add_additional_parameters(story)
        return " ".join(p.text for p in story if hasattr(p, "text"))

    def test_pdf_uses_selected_dose(self):
        text = self._text({"gh_dose": {"initial_daily_dose": 1.4, "selected_daily_dose_mg": 1.5}})
        assert "Selected daily dose (pen-rounded): 1.50 mg/day" in text
        assert "10.50 mg/week" in text

    def test_pdf_default_without_selected(self):
        assert "GH initial dose" in self._text({"gh_dose": {"initial_daily_dose": 1.4}})

    def test_export_accepts_valid_dose(self, client):
        r = client.post("/export-pdf", json={**self.PAYLOAD, "gh_selected_daily_dose_mg": 1.5})
        assert r.status_code == 200
        assert r.data[:5] == b"%PDF-"

    @pytest.mark.parametrize("bad", [True, 0, -1, 20.5, "1.5", [1], float("nan"), float("inf")])
    def test_export_rejects_bad_dose(self, client, bad):
        r = client.post("/export-pdf", json={**self.PAYLOAD, "gh_selected_daily_dose_mg": bad})
        assert r.status_code == 400

    def test_export_accepts_upper_bound(self, client):
        r = client.post("/export-pdf", json={**self.PAYLOAD, "gh_selected_daily_dose_mg": 20})
        assert r.status_code == 200


class TestSecurityAndRateLimit:
    def test_x_frame_options(self, client):
        assert client.get("/health").headers["X-Frame-Options"] == "DENY"

    def test_separate_buckets_per_cf_connecting_ip(self, app):
        from app import limiter
        limiter.enabled = True
        try:
            limiter.reset()
            c = app.test_client()
            payload = {**BASE, "weight": 20}
            last = None
            for _ in range(31):
                last = c.post("/calculate", json=payload, headers={"CF-Connecting-IP": "203.0.113.1"})
            assert last.status_code == 429
            other = c.post("/calculate", json=payload, headers={"CF-Connecting-IP": "203.0.113.2"})
            assert other.status_code == 200
        finally:
            limiter.enabled = False
            limiter.reset()


class TestTopLevelErrorHandlers:
    SECRET = "SECRET-INTERNAL-DETAIL"

    @pytest.mark.parametrize("path", ["/calculate", "/export-pdf"])
    @pytest.mark.parametrize("exc,status", [(ValueError, 400), (RuntimeError, 500)])
    def test_unexpected_exceptions_do_not_leak(self, client, monkeypatch, path, exc, status):
        def boom(_data):
            raise exc(self.SECRET)
        monkeypatch.setattr("app.perform_calculation", boom)
        r = client.post(path, json={**BASE, "weight": 20})
        assert r.status_code == status
        assert r.get_json()["error_code"] == "ERR_009"
        assert self.SECRET not in r.get_data(as_text=True)

    @pytest.mark.parametrize("path", ["/calculate", "/export-pdf"])
    def test_validation_error_maps_to_400(self, client, monkeypatch, path):
        from validation import ValidationError

        def boom(_data):
            raise ValidationError("Bad thing", "ERR_010")
        monkeypatch.setattr("app.perform_calculation", boom)
        r = client.post(path, json={**BASE, "weight": 20})
        assert r.status_code == 400
        assert r.get_json()["error_code"] == "ERR_010"
