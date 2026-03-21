"""Tests for PDF generation."""
import pytest
from io import BytesIO
from pdf_utils import GrowthReportPDF


@pytest.fixture
def sample_results():
    return {
        "age_years": 3.0,
        "age_calendar": {"years": 3, "months": 0, "days": 0},
        "gestation_correction_applied": False,
        "weight": {"value": 14.5, "centile": 50.1, "sds": 0.03},
        "height": {"value": 96.0, "centile": 25.5, "sds": -0.67},
        "bmi": {"value": 15.7, "centile": 75.3, "sds": 0.68, "percentage_median": 105.2},
        "ofc": {"value": 50.0, "centile": 45.7, "sds": -0.11},
        "mid_parental_height": {
            "mid_parental_height": 178.0,
            "target_range_lower": 169.5,
            "target_range_upper": 186.5,
            "mid_parental_height_sds": 0.45,
            "mid_parental_height_centile": 67.3,
        },
        "bsa": {"value": 0.62, "method": "Boyd"},
        "validation_messages": [],
    }


@pytest.fixture
def sample_patient_info():
    return {
        "sex": "male",
        "birth_date": "2020-06-15",
        "measurement_date": "2023-06-15",
        "reference": "uk-who",
    }


class TestGrowthReportPDF:
    def test_generates_pdf_buffer(self, sample_results, sample_patient_info):
        pdf = GrowthReportPDF(sample_results, sample_patient_info)
        buffer = pdf.generate()
        assert isinstance(buffer, BytesIO)
        content = buffer.read()
        assert len(content) > 0
        assert content[:5] == b"%PDF-"

    def test_generates_without_optional_fields(self):
        results = {
            "age_years": 2.0,
            "age_calendar": {"years": 2, "months": 0, "days": 0},
            "gestation_correction_applied": False,
            "weight": {"value": 12.0, "centile": 40.0, "sds": -0.25},
            "validation_messages": [],
        }
        patient_info = {"sex": "female", "birth_date": "2021-01-01", "measurement_date": "2023-01-01", "reference": "uk-who"}
        pdf = GrowthReportPDF(results, patient_info)
        buffer = pdf.generate()
        assert buffer.read()[:5] == b"%PDF-"

    def test_with_chart_images(self, sample_results, sample_patient_info):
        import base64
        from io import BytesIO as _BytesIO
        from PIL import Image as PILImage
        # Create a valid 2x2 PNG using Pillow
        img = PILImage.new("RGB", (2, 2), color=(255, 255, 255))
        img_buf = _BytesIO()
        img.save(img_buf, format="PNG")
        tiny_png = base64.b64encode(img_buf.getvalue()).decode()
        chart_images = {"height": f"data:image/png;base64,{tiny_png}"}
        pdf = GrowthReportPDF(sample_results, sample_patient_info, chart_images)
        buffer = pdf.generate()
        assert buffer.read()[:5] == b"%PDF-"

    def test_with_previous_measurements(self, sample_results, sample_patient_info):
        sample_results["previous_measurements"] = [
            {"date": "2022-06-15", "age": 2.0, "height": {"value": 88.0, "centile": 50.0, "sds": 0.0}, "weight": {"value": 12.0, "centile": 45.0, "sds": -0.13}},
        ]
        pdf = GrowthReportPDF(sample_results, sample_patient_info)
        buffer = pdf.generate()
        assert buffer.read()[:5] == b"%PDF-"

    def test_with_warnings(self, sample_results, sample_patient_info):
        sample_results["validation_messages"] = ["SDS is very extreme (+4.5 SDS). Please verify measurement accuracy."]
        pdf = GrowthReportPDF(sample_results, sample_patient_info)
        buffer = pdf.generate()
        assert buffer.read()[:5] == b"%PDF-"
