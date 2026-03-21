"""Integration tests for export and polish features."""
import json
import base64
import pytest
from PIL import Image as PILImage
from io import BytesIO


class TestExportWorkflows:
    def test_full_pdf_export_workflow(self, client):
        """Calculate then export PDF with all data."""
        calc_payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
            "height": 96.0,
            "ofc": 50.0,
            "maternal_height": 165.0,
            "paternal_height": 178.0,
        }
        calc_resp = client.post("/calculate", data=json.dumps(calc_payload), content_type="application/json")
        calc_data = calc_resp.get_json()
        assert calc_data["success"] is True

        pdf_payload = {
            "results": calc_data["results"],
            "patient_info": {
                "sex": "male",
                "birth_date": "2020-06-15",
                "measurement_date": "2023-06-15",
                "reference": "uk-who",
            },
        }
        pdf_resp = client.post("/export-pdf", data=json.dumps(pdf_payload), content_type="application/json")
        assert pdf_resp.status_code == 200
        assert pdf_resp.data[:5] == b"%PDF-"

    def test_pdf_with_advanced_results(self, client):
        """PDF export with previous measurements, bone age, BSA."""
        calc_payload = {
            "sex": "male",
            "birth_date": "2015-06-15",
            "measurement_date": "2023-06-15",
            "weight": 25.0,
            "height": 125.0,
            "maternal_height": 165.0,
            "paternal_height": 178.0,
            "gh_treatment": True,
            "previous_measurements": [
                {"date": "2022-06-15", "height": 118.0, "weight": 22.0},
            ],
            "bone_age_assessments": [
                {"date": "2023-06-10", "bone_age": 7.5, "standard": "gp"},
            ],
        }
        calc_resp = client.post("/calculate", data=json.dumps(calc_payload), content_type="application/json")
        calc_data = calc_resp.get_json()

        pdf_payload = {
            "results": calc_data["results"],
            "patient_info": {"sex": "male", "birth_date": "2015-06-15", "measurement_date": "2023-06-15", "reference": "uk-who"},
        }
        pdf_resp = client.post("/export-pdf", data=json.dumps(pdf_payload), content_type="application/json")
        assert pdf_resp.status_code == 200
        assert pdf_resp.data[:5] == b"%PDF-"
        assert len(pdf_resp.data) > 1000

    def test_pdf_with_chart_images(self, client):
        """PDF export with embedded chart images."""
        img = PILImage.new('RGB', (100, 100), color='white')
        buf = BytesIO()
        img.save(buf, format='PNG')
        png_b64 = base64.b64encode(buf.getvalue()).decode()

        pdf_payload = {
            "results": {
                "age_years": 3.0,
                "age_calendar": {"years": 3, "months": 0, "days": 0},
                "gestation_correction_applied": False,
                "weight": {"value": 14.5, "centile": 50.1, "sds": 0.03},
                "validation_messages": [],
            },
            "patient_info": {"sex": "male", "birth_date": "2020-06-15", "measurement_date": "2023-06-15", "reference": "uk-who"},
            "chart_images": {
                "height": f"data:image/png;base64,{png_b64}",
                "weight": f"data:image/png;base64,{png_b64}",
            },
        }
        pdf_resp = client.post("/export-pdf", data=json.dumps(pdf_payload), content_type="application/json")
        assert pdf_resp.status_code == 200
        assert pdf_resp.data[:5] == b"%PDF-"

    def test_all_endpoints_still_work(self, client):
        """Verify no regressions across all endpoints."""
        assert client.get("/health").status_code == 200

        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Growth Parameters Calculator" in resp.data

        calc = client.post("/calculate", data=json.dumps({
            "sex": "female", "birth_date": "2021-01-01",
            "measurement_date": "2023-01-01", "weight": 12.0,
        }), content_type="application/json")
        assert calc.status_code == 200

        chart = client.post("/chart-data", data=json.dumps({
            "reference": "uk-who", "measurement_method": "height", "sex": "female",
        }), content_type="application/json")
        assert chart.status_code == 200
