"""Tests for PDF generation."""
from io import BytesIO

import pytest

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


class TestDecodeChartImage:
    """Direct unit tests for `_decode_chart_image` edge cases.

    These cover paths that are otherwise only exercised end-to-end via
    `/export-pdf`, and pin the decompression-bomb guard in place.
    """

    @staticmethod
    def _valid_png_data_url(size=(10, 10)):
        import base64

        from PIL import Image as PILImage
        img = PILImage.new("RGB", size, color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

    def test_valid_png_returns_image_and_bytes(self):
        from pdf_utils import _decode_chart_image
        img, raw = _decode_chart_image(self._valid_png_data_url())
        assert img.format == "PNG"
        assert len(raw) > 0

    def test_non_png_prefix_rejected(self):
        from pdf_utils import _decode_chart_image
        with pytest.raises(ValueError, match="PNG data URLs"):
            _decode_chart_image("data:image/jpeg;base64,/9j/4AAQ")

    def test_non_string_rejected(self):
        from pdf_utils import _decode_chart_image
        with pytest.raises(ValueError, match="PNG data URLs"):
            _decode_chart_image(None)

    def test_malformed_base64_rejected(self):
        from pdf_utils import _decode_chart_image
        with pytest.raises(ValueError, match="base64"):
            _decode_chart_image("data:image/png;base64,not!!base64")

    def test_bytes_exceeding_cap_rejected(self, monkeypatch):
        import base64

        import pdf_utils
        # Shrink the cap so we can exercise the check cheaply.
        monkeypatch.setattr(pdf_utils, "MAX_CHART_IMAGE_BYTES", 64)
        payload = "data:image/png;base64," + base64.b64encode(b"\x00" * 256).decode()
        with pytest.raises(ValueError, match="KB limit"):
            pdf_utils._decode_chart_image(payload)

    def test_wrong_magic_but_valid_base64_rejected(self):
        import base64

        from pdf_utils import _decode_chart_image
        # Base64-encoded JPEG magic — bytes decode but fail the PNG signature check.
        payload = "data:image/png;base64," + base64.b64encode(b"\xff\xd8\xff\xe0garbage" * 4).decode()
        with pytest.raises(ValueError, match="valid PNG"):
            _decode_chart_image(payload)

    def test_oversized_dimensions_rejected_without_decompression(self):
        """A PNG IHDR declaring huge dimensions must be rejected BEFORE pixels decode.

        We build a minimal PNG with IHDR claiming 10 000 × 10 000 and truncated IDAT
        chunks. If dimensions were checked after `img.load()`, this would either
        exhaust memory or raise OSError; instead it must raise the dimension-limit
        ValueError cleanly.
        """
        import base64
        import struct
        import zlib

        from pdf_utils import _decode_chart_image

        def _chunk(tag, data):
            return (
                struct.pack(">I", len(data))
                + tag
                + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
            )

        sig = b"\x89PNG\r\n\x1a\n"
        ihdr = struct.pack(">IIBBBBB", 10000, 10000, 8, 2, 0, 0, 0)
        # A plausible IDAT with a few bytes of zlib-compressed data.
        idat = zlib.compress(b"\x00" * 64)
        png = sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")
        payload = "data:image/png;base64," + base64.b64encode(png).decode()
        with pytest.raises(ValueError, match="dimension limit"):
            _decode_chart_image(payload)

    def test_truncated_png_rejected(self):
        """A valid PNG header followed by garbage IDAT should raise decode errors."""
        import base64

        from pdf_utils import _decode_chart_image

        sig = b"\x89PNG\r\n\x1a\n"
        payload = "data:image/png;base64," + base64.b64encode(sig + b"garbage" * 4).decode()
        with pytest.raises(ValueError):
            _decode_chart_image(payload)
