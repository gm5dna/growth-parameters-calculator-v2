"""Integration tests for export and polish features."""
import base64
import json
from io import BytesIO

from PIL import Image as PILImage


class TestExportWorkflows:
    def test_full_pdf_export_workflow(self, client):
        """Submit the measurement payload; the server recalculates server-side."""
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
            "height": 96.0,
            "ofc": 50.0,
            "maternal_height": 165.0,
            "paternal_height": 178.0,
            "patient_info": {},
        }
        pdf_resp = client.post("/export-pdf", data=json.dumps(payload), content_type="application/json")
        assert pdf_resp.status_code == 200
        assert pdf_resp.data[:5] == b"%PDF-"

    def test_pdf_with_advanced_results(self, client):
        """Advanced features (previous, bone age, BSA) are recalculated for the PDF."""
        payload = {
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
            "patient_info": {},
        }
        pdf_resp = client.post("/export-pdf", data=json.dumps(payload), content_type="application/json")
        assert pdf_resp.status_code == 200
        assert pdf_resp.data[:5] == b"%PDF-"
        assert len(pdf_resp.data) > 1000

    def test_pdf_with_chart_images(self, client):
        """PDF export with embedded chart images."""
        img = PILImage.new('RGB', (100, 100), color='white')
        buf = BytesIO()
        img.save(buf, format='PNG')
        png_b64 = base64.b64encode(buf.getvalue()).decode()

        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
            "patient_info": {},
            "chart_images": {
                "height": f"data:image/png;base64,{png_b64}",
                "weight": f"data:image/png;base64,{png_b64}",
            },
        }
        pdf_resp = client.post("/export-pdf", data=json.dumps(payload), content_type="application/json")
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
