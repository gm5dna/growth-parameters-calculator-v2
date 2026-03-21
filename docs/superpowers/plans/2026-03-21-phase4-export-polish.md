# Phase 4: Export & Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Production-ready application — PDF report export, clipboard copy, chart PNG download, dark mode theme, and rate limiting.

**Architecture:** PDF generation uses ReportLab server-side via a new `pdf_utils.py` module and `POST /export-pdf` endpoint (rate-limited with flask-limiter). Clipboard copy uses a new `static/clipboard.js` that formats results as plain clinical text. Chart download is client-side canvas-to-PNG. Dark mode uses CSS custom properties with `[data-theme="dark"]` selector, toggle in header, localStorage persistence, and Chart.js colour updates.

**Tech Stack:** ReportLab (PDF), Pillow (image handling), flask-limiter (rate limiting), existing Chart.js 4.x

**Specs:** `spec/PRD_07_EXPORT_REPORTING.md`, `spec/PRD_05_USER_EXPERIENCE.md` (§4 Theme System)

---

## Phase 4 Scope

**In scope:**
- PDF report generation (ReportLab, A4, all sections per PRD-07 §3.2)
- `POST /export-pdf` endpoint with rate limiting (10/minute)
- Clipboard copy with plain text clinical format (PRD-07 §4.2)
- Chart PNG download at 2x resolution
- Copy/Export PDF buttons in results header
- Download Chart button in charts header
- Dark mode CSS variables + toggle + chart colour updates
- Toast notifications for copy/export feedback

**Deferred (future):**
- PWA/service worker/offline support
- FHIR/HL7 integration

---

## File Map

| File | Responsibility | Action |
|------|---------------|--------|
| `requirements.txt` | Add ReportLab, Pillow, flask-limiter | Modify |
| `pdf_utils.py` | GrowthReportPDF class — ReportLab PDF generation | Create |
| `app.py` | Add `POST /export-pdf` route with rate limiting | Modify |
| `static/clipboard.js` | formatResultsAsText, copyResultsToClipboard | Create |
| `static/charts.js` | Add downloadChart function, dark mode colour updates | Modify |
| `static/script.js` | Wire export buttons, dark mode toggle, toast helper | Modify |
| `static/style.css` | Add dark mode variables, export button styles, theme toggle | Modify |
| `templates/index.html` | Add theme toggle, export buttons, download button, clipboard.js script | Modify |
| `tests/test_pdf.py` | PDF generation tests | Create |
| `tests/test_endpoints.py` | /export-pdf endpoint tests | Modify |
| `tests/js/clipboard.test.js` | Clipboard formatting tests | Create |
| `tests/test_export_integration.py` | End-to-end export tests | Create |

---

### Task 1: Dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add ReportLab, Pillow, flask-limiter**

Update `requirements.txt`:
```
Flask>=3.0.0,<4.0.0
rcpchgrowth>=4.0.0
python-dateutil>=2.8.0
reportlab>=4.0.0
Pillow>=10.0.0
flask-limiter>=3.0.0
```

- [ ] **Step 2: Install**

```bash
source venv/bin/activate
pip install -r requirements.txt
python -c "from reportlab.lib.pagesizes import A4; from flask_limiter import Limiter; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add ReportLab, Pillow, flask-limiter dependencies"
```

---

### Task 2: PDF Generation Module

**Files:**
- Create: `pdf_utils.py`
- Create: `tests/test_pdf.py`

The `GrowthReportPDF` class generates a complete clinical report PDF using ReportLab.

- [ ] **Step 1: Write the failing test**

Create `tests/test_pdf.py`:

```python
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
        patient_info = {
            "sex": "female",
            "birth_date": "2021-01-01",
            "measurement_date": "2023-01-01",
            "reference": "uk-who",
        }
        pdf = GrowthReportPDF(results, patient_info)
        buffer = pdf.generate()
        assert buffer.read()[:5] == b"%PDF-"

    def test_with_chart_images(self, sample_results, sample_patient_info):
        # Minimal valid 1x1 white PNG as base64
        import base64
        tiny_png = base64.b64encode(
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
            b'\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00'
            b'\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        ).decode()
        chart_images = {"height": f"data:image/png;base64,{tiny_png}"}
        pdf = GrowthReportPDF(sample_results, sample_patient_info, chart_images)
        buffer = pdf.generate()
        assert buffer.read()[:5] == b"%PDF-"

    def test_with_previous_measurements(self, sample_results, sample_patient_info):
        sample_results["previous_measurements"] = [
            {
                "date": "2022-06-15",
                "age": 2.0,
                "height": {"value": 88.0, "centile": 50.0, "sds": 0.0},
                "weight": {"value": 12.0, "centile": 45.0, "sds": -0.13},
            },
        ]
        pdf = GrowthReportPDF(sample_results, sample_patient_info)
        buffer = pdf.generate()
        assert buffer.read()[:5] == b"%PDF-"

    def test_with_warnings(self, sample_results, sample_patient_info):
        sample_results["validation_messages"] = [
            "SDS is very extreme (+4.5 SDS). Please verify measurement accuracy."
        ]
        pdf = GrowthReportPDF(sample_results, sample_patient_info)
        buffer = pdf.generate()
        assert buffer.read()[:5] == b"%PDF-"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_pdf.py -v
```

- [ ] **Step 3: Write pdf_utils.py**

```python
"""PDF report generation using ReportLab. A4 page size always."""
import base64
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak,
)


class GrowthReportPDF:
    """Generate a growth parameters report as PDF."""

    def __init__(self, results, patient_info, chart_images=None):
        self.results = results
        self.patient_info = patient_info
        self.chart_images = chart_images or {}
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        self.styles.add(ParagraphStyle(
            name="ReportTitle",
            parent=self.styles["Heading1"],
            fontSize=18,
            spaceAfter=6,
            textColor=colors.HexColor("#1e40af"),
        ))
        self.styles.add(ParagraphStyle(
            name="SectionTitle",
            parent=self.styles["Heading2"],
            fontSize=12,
            spaceBefore=12,
            spaceAfter=6,
            textColor=colors.HexColor("#1e40af"),
        ))
        self.styles.add(ParagraphStyle(
            name="Disclaimer",
            parent=self.styles["Normal"],
            fontSize=8,
            textColor=colors.grey,
            spaceBefore=12,
        ))

    def generate(self):
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        story = []
        self._add_header(story)
        self._add_patient_info(story)
        self._add_measurements_table(story)
        self._add_additional_parameters(story)
        self._add_warnings(story)
        self._add_chart_images(story)
        self._add_previous_measurements(story)
        self._add_disclaimer(story)

        doc.build(story, onFirstPage=self._page_footer, onLaterPages=self._page_footer)
        buffer.seek(0)
        return buffer

    def _add_header(self, story):
        story.append(Paragraph("GROWTH PARAMETERS REPORT", self.styles["ReportTitle"]))
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        ref = self.patient_info.get("reference", "uk-who").upper()
        story.append(Paragraph(f"Generated: {now} | Reference: {ref}", self.styles["Normal"]))
        story.append(Spacer(1, 12))

    def _add_patient_info(self, story):
        story.append(Paragraph("PATIENT INFORMATION", self.styles["SectionTitle"]))
        r = self.results
        pi = self.patient_info
        age_cal = r.get("age_calendar", {})
        age_str = f"{age_cal.get('years', 0)}y {age_cal.get('months', 0)}m {age_cal.get('days', 0)}d"
        data = [
            ["Sex:", pi.get("sex", "").capitalize()],
            ["Date of Birth:", pi.get("birth_date", "")],
            ["Age:", f"{r.get('age_years', ''):.2f} years ({age_str})"],
            ["Measurement Date:", pi.get("measurement_date", "")],
        ]
        if r.get("gestation_correction_applied"):
            corr = r.get("corrected_age_years", "")
            data.append(["Corrected Age:", f"{corr:.2f} years" if isinstance(corr, (int, float)) else str(corr)])
        t = Table(data, colWidths=[4.5 * cm, 12 * cm])
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 8))

    def _add_measurements_table(self, story):
        story.append(Paragraph("MEASUREMENTS", self.styles["SectionTitle"]))
        header = ["Parameter", "Value", "Centile", "SDS"]
        rows = [header]
        units = {"weight": "kg", "height": "cm", "ofc": "cm", "bmi": "kg/m\u00B2"}
        labels = {"weight": "Weight", "height": "Height", "bmi": "BMI", "ofc": "OFC"}
        for method in ["weight", "height", "bmi", "ofc"]:
            m = self.results.get(method)
            if not m:
                continue
            unit = units.get(method, "")
            value_str = f"{m['value']} {unit}" if unit else str(m["value"])
            centile = f"{m['centile']:.1f}%" if m.get("centile") is not None else "N/A"
            sds_val = m.get("sds")
            sds = f"{sds_val:+.2f}" if sds_val is not None else "N/A"
            rows.append([labels.get(method, method), value_str, centile, sds])

        if len(rows) > 1:
            t = Table(rows, colWidths=[3.5 * cm, 4 * cm, 3.5 * cm, 3.5 * cm])
            t.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f4ff")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(t)
        story.append(Spacer(1, 8))

    def _add_additional_parameters(self, story):
        r = self.results
        params = []
        if r.get("bsa"):
            params.append(f"Body Surface Area ({r['bsa']['method']}): {r['bsa']['value']} m\u00B2")
        if r.get("height_velocity") and r["height_velocity"].get("value") is not None:
            params.append(f"Height Velocity: {r['height_velocity']['value']} cm/year")
        mph = r.get("mid_parental_height")
        if mph:
            params.append(
                f"Mid-Parental Height: {mph['mid_parental_height']} cm "
                f"({mph['target_range_lower']}\u2013{mph['target_range_upper']} cm)"
            )
        if r.get("bone_age_height"):
            ba = r["bone_age_height"]
            params.append(f"Bone Age: {ba['bone_age']} years (Height for BA centile: {ba['centile']:.1f}%)")
        if r.get("gh_dose"):
            gh = r["gh_dose"]
            if gh.get("initial_daily_dose"):
                params.append(f"GH Initial Dose: {gh['initial_daily_dose']} mg/day")
        if not params:
            return
        story.append(Paragraph("ADDITIONAL PARAMETERS", self.styles["SectionTitle"]))
        for p in params:
            story.append(Paragraph(f"\u2022 {p}", self.styles["Normal"]))
        story.append(Spacer(1, 8))

    def _add_warnings(self, story):
        warnings = self.results.get("validation_messages", [])
        if not warnings:
            return
        story.append(Paragraph("WARNINGS", self.styles["SectionTitle"]))
        for w in warnings:
            story.append(Paragraph(f"\u26a0 {w}", self.styles["Normal"]))
        story.append(Spacer(1, 8))

    def _add_chart_images(self, story):
        if not self.chart_images:
            return
        story.append(Paragraph("GROWTH CHARTS", self.styles["SectionTitle"]))
        for chart_type in ["height", "weight", "bmi", "ofc"]:
            img_data = self.chart_images.get(chart_type)
            if not img_data:
                continue
            try:
                # Strip data URL prefix
                if "," in img_data:
                    img_data = img_data.split(",", 1)[1]
                img_bytes = base64.b64decode(img_data)
                img_buffer = BytesIO(img_bytes)
                img = Image(img_buffer, width=15 * cm, height=10 * cm, kind="proportional")
                story.append(img)
                story.append(Spacer(1, 8))
            except Exception:
                continue

    def _add_previous_measurements(self, story):
        prev = self.results.get("previous_measurements", [])
        if not prev:
            return
        story.append(PageBreak())
        story.append(Paragraph("PREVIOUS MEASUREMENTS", self.styles["SectionTitle"]))
        header = ["Date", "Age (yrs)", "Height", "Weight", "OFC"]
        rows = [header]
        for pm in prev:
            row = [
                pm.get("date", ""),
                f"{pm.get('age', ''):.2f}" if isinstance(pm.get("age"), (int, float)) else "",
            ]
            for method in ["height", "weight", "ofc"]:
                m = pm.get(method)
                if m:
                    row.append(f"{m['value']}")
                else:
                    row.append("")
            rows.append(row)

        if len(rows) > 1:
            t = Table(rows, colWidths=[3 * cm, 2.5 * cm, 3 * cm, 3 * cm, 3 * cm])
            t.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f4ff")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(t)

    def _add_disclaimer(self, story):
        story.append(Spacer(1, 24))
        story.append(Paragraph(
            "DISCLAIMER: This report is generated by the Growth Parameters Calculator "
            "using the RCPCH Growth Charts API. All calculations should be verified and "
            "interpreted by qualified healthcare professionals. This tool is for educational "
            "and research purposes only.",
            self.styles["Disclaimer"],
        ))

    def _page_footer(self, canvas, doc):
        """Draw page footer. Uses deferred page count for 'Page X of Y'."""
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        # Placeholder — will be replaced by NumberedCanvas approach below
        canvas.drawRightString(
            A4[0] - 2 * cm, 1.2 * cm,
            f"Page {canvas.getPageNumber()}"
        )
        canvas.restoreState()
```

Add a `NumberedCanvas` inner class to handle "Page X of Y" (ReportLab two-pass technique):

```python
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas


class NumberedCanvas(Canvas):
    """Canvas subclass that tracks pages and draws 'Page X of Y' footers."""

    def __init__(self, *args, **kwargs):
        Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        Canvas.showPage(self)

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.grey)
            self.drawRightString(
                A4[0] - 2 * cm, 1.2 * cm,
                f"Page {self._pageNumber} of {num_pages}"
            )
            Canvas.showPage(self)
        Canvas.save(self)
```

Update the `generate()` method to use `NumberedCanvas`:
```python
doc.build(story, canvasmaker=NumberedCanvas)
```

Remove the `onFirstPage` and `onLaterPages` callbacks from `doc.build()`.
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_pdf.py -v
```

- [ ] **Step 5: Commit**

```bash
git add pdf_utils.py tests/test_pdf.py
git commit -m "feat: add PDF report generation with ReportLab"
```

---

### Task 3: /export-pdf Endpoint with Rate Limiting

**Files:**
- Modify: `app.py` (add route + flask-limiter setup)
- Modify: `tests/test_endpoints.py` (add TestExportPdfEndpoint class)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_endpoints.py`:

```python
class TestExportPdfEndpoint:
    def test_basic_pdf_export(self, client):
        payload = {
            "results": {
                "age_years": 3.0,
                "age_calendar": {"years": 3, "months": 0, "days": 0},
                "gestation_correction_applied": False,
                "weight": {"value": 14.5, "centile": 50.1, "sds": 0.03},
                "height": {"value": 96.0, "centile": 25.5, "sds": -0.67},
                "validation_messages": [],
            },
            "patient_info": {
                "sex": "male",
                "birth_date": "2020-06-15",
                "measurement_date": "2023-06-15",
                "reference": "uk-who",
            },
        }
        response = client.post("/export-pdf", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
        assert response.content_type == "application/pdf"
        assert response.data[:5] == b"%PDF-"
        assert "attachment" in response.headers.get("Content-Disposition", "")

    def test_pdf_missing_results(self, client):
        payload = {"patient_info": {"sex": "male"}}
        response = client.post("/export-pdf", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400

    def test_pdf_missing_patient_info(self, client):
        payload = {"results": {"age_years": 3.0, "validation_messages": []}}
        response = client.post("/export-pdf", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400

    def test_pdf_with_chart_images(self, client):
        import base64
        tiny_png = base64.b64encode(
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
            b'\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00'
            b'\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        ).decode()
        payload = {
            "results": {
                "age_years": 3.0,
                "age_calendar": {"years": 3, "months": 0, "days": 0},
                "gestation_correction_applied": False,
                "weight": {"value": 14.5, "centile": 50.1, "sds": 0.03},
                "validation_messages": [],
            },
            "patient_info": {"sex": "male", "birth_date": "2020-06-15", "measurement_date": "2023-06-15", "reference": "uk-who"},
            "chart_images": {"height": f"data:image/png;base64,{tiny_png}"},
        }
        response = client.post("/export-pdf", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
        assert response.data[:5] == b"%PDF-"
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Write implementation**

Add to `app.py`:

1. Import flask-limiter and set it up:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
```

After `app = Flask(__name__)`:
```python
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri="memory://",
    enabled=True,  # Disabled in test via config
)
```

No `default_limits` — rate limiting only applies to `/export-pdf` via the per-route decorator.

Also update `tests/conftest.py` to disable rate limiting during tests:
```python
flask_app.config["RATELIMIT_ENABLED"] = False
```
Add this line inside the `app()` fixture, after `flask_app.config["TESTING"] = True`.

2. Import pdf_utils:
```python
from pdf_utils import GrowthReportPDF
```

3. Add the route:
```python
@app.route("/export-pdf", methods=["POST"])
@limiter.limit("10 per minute")
def export_pdf():
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify(format_error_response(
            "Request body must be valid JSON.", ErrorCodes.INVALID_INPUT
        )), 400

    results = data.get("results")
    patient_info = data.get("patient_info")

    if not results:
        return jsonify(format_error_response(
            "Results data is required.", ErrorCodes.INVALID_INPUT
        )), 400
    if not patient_info:
        return jsonify(format_error_response(
            "Patient information is required.", ErrorCodes.INVALID_INPUT
        )), 400

    try:
        chart_images = data.get("chart_images", {})
        pdf = GrowthReportPDF(results, patient_info, chart_images)
        buffer = pdf.generate()

        from flask import send_file
        from datetime import datetime as dt
        filename = f"growth-report-{dt.now().strftime('%Y-%m-%d-%H%M%S')}.pdf"

        return send_file(
            buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        logger.error("PDF generation error: %s", str(e))
        return jsonify(format_error_response(
            "PDF generation failed. Please try again.", ErrorCodes.CALCULATION_ERROR
        )), 400
```

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_endpoints.py
git commit -m "feat: add /export-pdf endpoint with rate limiting"
```

---

### Task 4: Clipboard Copy Module

**Files:**
- Create: `static/clipboard.js`
- Create: `tests/js/clipboard.test.js`

- [ ] **Step 1: Write the failing test**

Create `tests/js/clipboard.test.js`:

```javascript
const { formatResultsAsText } = require('../../static/clipboard');

describe('formatResultsAsText', () => {
  const baseResults = {
    age_years: 3.0,
    age_calendar: { years: 3, months: 0, days: 0 },
    gestation_correction_applied: false,
    weight: { value: 14.5, centile: 50.1, sds: 0.03 },
    height: { value: 96.0, centile: 25.5, sds: -0.67 },
    bmi: { value: 15.7, centile: 75.3, sds: 0.68, percentage_median: 105.2 },
    ofc: { value: 50.0, centile: 45.7, sds: -0.11 },
    validation_messages: [],
  };
  const baseInfo = { sex: 'male', reference: 'uk-who' };

  test('includes header', () => {
    const text = formatResultsAsText(baseResults, baseInfo);
    expect(text).toContain('GROWTH PARAMETERS');
  });

  test('includes age', () => {
    const text = formatResultsAsText(baseResults, baseInfo);
    expect(text).toContain('Age: 3.00 years');
  });

  test('includes reference', () => {
    const text = formatResultsAsText(baseResults, baseInfo);
    expect(text).toContain('Reference: UK-WHO');
  });

  test('includes weight with centile and SDS', () => {
    const text = formatResultsAsText(baseResults, baseInfo);
    expect(text).toContain('Weight: 14.5 kg');
    expect(text).toContain('Centile: 50.1%');
    expect(text).toContain('SDS: +0.03');
  });

  test('includes height', () => {
    const text = formatResultsAsText(baseResults, baseInfo);
    expect(text).toContain('Height: 96.0 cm');
  });

  test('includes BMI with percentage median', () => {
    const text = formatResultsAsText(baseResults, baseInfo);
    expect(text).toContain('BMI: 15.7');
    expect(text).toContain('% Median: 105.2%');
  });

  test('includes OFC', () => {
    const text = formatResultsAsText(baseResults, baseInfo);
    expect(text).toContain('Head Circumference (OFC): 50.0 cm');
  });

  test('includes MPH when present', () => {
    const results = {
      ...baseResults,
      mid_parental_height: {
        mid_parental_height: 178.0,
        target_range_lower: 169.5,
        target_range_upper: 186.5,
      },
    };
    const text = formatResultsAsText(results, baseInfo);
    expect(text).toContain('Mid-Parental Height: 178.0 cm');
    expect(text).toContain('Target Range: 169.5-186.5 cm');
  });

  test('includes BSA when present', () => {
    const results = { ...baseResults, bsa: { value: 0.62, method: 'Boyd' } };
    const text = formatResultsAsText(results, baseInfo);
    expect(text).toContain('Body Surface Area: 0.62');
    expect(text).toContain('Boyd');
  });

  test('includes height velocity when present', () => {
    const results = { ...baseResults, height_velocity: { value: 6.8 } };
    const text = formatResultsAsText(results, baseInfo);
    expect(text).toContain('Height Velocity: 6.8 cm/year');
  });

  test('omits missing sections', () => {
    const minimal = {
      age_years: 2.0,
      age_calendar: { years: 2, months: 0, days: 0 },
      weight: { value: 12.0, centile: 40.0, sds: -0.25 },
      validation_messages: [],
    };
    const text = formatResultsAsText(minimal, baseInfo);
    expect(text).not.toContain('Height:');
    expect(text).not.toContain('BMI:');
    expect(text).not.toContain('Mid-Parental Height');
    expect(text).not.toContain('BSA');
  });

  test('includes warnings when present', () => {
    const results = {
      ...baseResults,
      validation_messages: ['SDS is very extreme (+4.5 SDS).'],
    };
    const text = formatResultsAsText(results, baseInfo);
    expect(text).toContain('WARNINGS');
    expect(text).toContain('extreme');
  });

  test('includes footer', () => {
    const text = formatResultsAsText(baseResults, baseInfo);
    expect(text).toContain('Generated by Growth Parameters Calculator');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
npx jest tests/js/clipboard.test.js
```

- [ ] **Step 3: Write static/clipboard.js**

```javascript
/**
 * Clipboard formatting — plain text clinical summary.
 * Each function is for UX; server-side data is authoritative.
 */

function formatResultsAsText(results, patientInfo) {
  var lines = [];
  lines.push('GROWTH PARAMETERS');
  lines.push('=================');
  lines.push('Age: ' + (results.age_years !== undefined ? results.age_years.toFixed(2) : 'N/A') + ' years' +
    (results.age_calendar ? ' (' + results.age_calendar.years + 'y ' + results.age_calendar.months + 'm ' + results.age_calendar.days + 'd)' : ''));
  lines.push('Reference: ' + (patientInfo.reference || 'uk-who').toUpperCase());
  lines.push('');

  if (results.gestation_correction_applied && results.corrected_age_years !== undefined) {
    lines.push('Corrected Age: ' + results.corrected_age_years.toFixed(2) + ' years');
    lines.push('');
  }

  var measurements = [
    { key: 'weight', label: 'Weight', unit: 'kg' },
    { key: 'height', label: 'Height', unit: 'cm' },
    { key: 'bmi', label: 'BMI', unit: '' },
    { key: 'ofc', label: 'Head Circumference (OFC)', unit: 'cm' },
  ];
  measurements.forEach(function(m) {
    var data = results[m.key];
    if (!data) return;
    var valueStr = m.unit ? data.value + ' ' + m.unit : String(data.value);
    lines.push(m.label + ': ' + valueStr);
    if (data.centile !== null && data.centile !== undefined) {
      lines.push('  Centile: ' + data.centile.toFixed(1) + '%');
    }
    if (data.sds !== null && data.sds !== undefined) {
      lines.push('  SDS: ' + (data.sds >= 0 ? '+' : '') + data.sds.toFixed(2));
    }
    if (m.key === 'bmi' && data.percentage_median !== null && data.percentage_median !== undefined) {
      lines.push('  % Median: ' + data.percentage_median.toFixed(1) + '%');
    }
    lines.push('');
  });

  if (results.mid_parental_height) {
    var mph = results.mid_parental_height;
    lines.push('Mid-Parental Height: ' + mph.mid_parental_height + ' cm');
    lines.push('  Target Range: ' + mph.target_range_lower + '-' + mph.target_range_upper + ' cm');
    lines.push('');
  }

  if (results.height_velocity && results.height_velocity.value !== null) {
    lines.push('Height Velocity: ' + results.height_velocity.value + ' cm/year');
    lines.push('');
  }

  if (results.bsa) {
    lines.push('Body Surface Area: ' + results.bsa.value + ' m\u00B2 (' + results.bsa.method + ')');
    lines.push('');
  }

  if (results.bone_age_height) {
    var ba = results.bone_age_height;
    lines.push('Bone Age: ' + ba.bone_age + ' years (' + (ba.standard === 'gp' ? 'Greulich-Pyle' : 'TW3') + ')');
    lines.push('');
  }

  if (results.gh_dose && results.gh_dose.initial_daily_dose) {
    lines.push('GH Initial Dose: ' + results.gh_dose.initial_daily_dose + ' mg/day');
    lines.push('');
  }

  var warnings = results.validation_messages || [];
  if (warnings.length > 0) {
    lines.push('WARNINGS');
    lines.push('--------');
    warnings.forEach(function(w) { lines.push(w); });
    lines.push('');
  }

  lines.push('Generated by Growth Parameters Calculator');

  return lines.join('\n');
}

async function copyResultsToClipboard(results, patientInfo) {
  var text = formatResultsAsText(results, patientInfo);
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    // Fallback
    var textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand('copy');
      return true;
    } catch (e) {
      return false;
    } finally {
      document.body.removeChild(textarea);
    }
  }
}

// Export for Node.js (Jest)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { formatResultsAsText, copyResultsToClipboard };
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
npx jest tests/js/clipboard.test.js
```

- [ ] **Step 5: Commit**

```bash
git add static/clipboard.js tests/js/clipboard.test.js
git commit -m "feat: add clipboard copy with clinical text formatting"
```

---

### Task 5: Chart PNG Download

**Files:**
- Modify: `static/charts.js` (add downloadChart function)

- [ ] **Step 1: Add downloadChart to charts.js**

```javascript
function downloadChart() {
    if (!currentChart) return;
    var canvas = document.getElementById('growthChart');
    if (!canvas) return;

    var chartType = currentChartType || 'chart';
    var date = new Date().toISOString().split('T')[0];
    var filename = 'growth-chart-' + chartType + '-' + date + '.png';

    // Create high-res export canvas (2x for Retina)
    var scale = 2;
    var exportCanvas = document.createElement('canvas');
    exportCanvas.width = canvas.width * scale;
    exportCanvas.height = canvas.height * scale;

    var ctx = exportCanvas.getContext('2d');
    ctx.scale(scale, scale);
    ctx.drawImage(canvas, 0, 0);

    // Trigger download
    var link = document.createElement('a');
    link.download = filename;
    link.href = exportCanvas.toDataURL('image/png');
    link.click();
}
```

Also add a function to capture chart images for PDF export (all 4 charts):

```javascript
async function captureChartImages() {
    var images = {};
    var reference = (typeof lastPayload !== 'undefined' && lastPayload) ? lastPayload.reference || 'uk-who' : 'uk-who';
    var sex = (typeof lastPayload !== 'undefined' && lastPayload) ? lastPayload.sex : 'male';

    for (var i = 0; i < ['height', 'weight', 'bmi', 'ofc'].length; i++) {
        var type = ['height', 'weight', 'bmi', 'ofc'][i];
        try {
            var centiles = await fetchChartData(reference, type, sex);
            var ranges = AGE_RANGES[type] || [];
            var ageYears = (typeof lastResults !== 'undefined' && lastResults) ? lastResults.age_years || 0 : 0;
            var hasParentalHeights = (typeof lastResults !== 'undefined' && lastResults) ? !!lastResults.mid_parental_height : false;
            var defaultIdx = getDefaultAgeRange(type, ageYears, hasParentalHeights);
            var ageRange = ranges[defaultIdx] || ranges[0];

            renderChart(centiles, ageRange, type);
            var canvas = document.getElementById('growthChart');
            if (canvas) {
                images[type] = canvas.toDataURL('image/png');
            }
        } catch (e) {
            // Skip failed charts
        }
    }

    // Restore current chart type
    if (currentChartType) {
        switchChartType(currentChartType);
    }

    return images;
}
```

- [ ] **Step 2: Verify**

```bash
node --check static/charts.js
```

- [ ] **Step 3: Commit**

```bash
git add static/charts.js
git commit -m "feat: add chart PNG download and chart image capture for PDF"
```

---

### Task 6: Export Buttons UI and Wiring

**Files:**
- Modify: `templates/index.html` (add Copy/Export PDF buttons, Download Chart button, theme toggle, clipboard.js script)
- Modify: `static/style.css` (add export button styles)
- Modify: `static/script.js` (wire buttons, toast helper, PDF export handler)

- [ ] **Step 1: Add buttons to index.html**

**Results header** — replace the plain `<h2>Results</h2>` in `#resultsSection` with:
```html
<div class="results-header">
    <h2>Results</h2>
    <div class="results-actions">
        <button type="button" class="btn-copy" id="copyResultsBtn" aria-label="Copy results to clipboard" title="Copy results">
            <span class="material-symbols-outlined" aria-hidden="true">content_copy</span> Copy
        </button>
        <button type="button" class="btn-export-pdf" id="exportPdfBtn" aria-label="Export results as PDF" title="Export PDF">
            <span class="material-symbols-outlined" aria-hidden="true">picture_as_pdf</span> Export PDF
        </button>
    </div>
</div>
```

**Charts header** — add a Download Chart button next to the Close button in `.charts-header`:
```html
<div class="charts-header-actions">
    <button type="button" class="btn-small" id="downloadChartBtn" aria-label="Download current chart as PNG" title="Download Chart">
        <span class="material-symbols-outlined" aria-hidden="true">download</span> Download
    </button>
    <button type="button" class="btn-icon" id="closeChartsBtn" aria-label="Close charts">
        <span class="material-symbols-outlined" aria-hidden="true">close</span>
    </button>
</div>
```

**Theme toggle** — add to the header, before the mode toggle:
```html
<button type="button" class="btn-icon theme-toggle" id="themeToggle" aria-label="Toggle dark mode">
    <span class="material-symbols-outlined" id="themeIcon">dark_mode</span>
</button>
```

**Script tag** — add clipboard.js BETWEEN validation.js and script.js (since script.js calls `copyResultsToClipboard` from clipboard.js). The final order must be: Chart.js CDN → annotation plugin CDN → validation.js → **clipboard.js** → script.js → charts.js:
```html
<script src="{{ url_for('static', filename='clipboard.js') }}"></script>
```

- [ ] **Step 2: Add CSS for export buttons and theme toggle**

```css
/* Results header */
.results-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 8px; }
.results-header h2 { margin: 0; }
.results-actions { display: flex; gap: 8px; }

/* Export buttons */
.btn-copy, .btn-export-pdf {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 8px 16px; border-radius: 6px; font-size: 14px;
    cursor: pointer; transition: background 0.15s; border: none;
}
.btn-copy {
    background: var(--bg-secondary); border: 1px solid var(--border-color); color: var(--text-primary);
}
.btn-copy:hover { background: var(--border-color); }
.btn-export-pdf { background: var(--accent-primary); color: white; }
.btn-export-pdf:hover { opacity: 0.9; }
.btn-export-pdf:disabled { opacity: 0.6; cursor: wait; }

/* Charts header actions */
.charts-header-actions { display: flex; align-items: center; gap: 8px; }

/* Theme toggle */
.theme-toggle { margin-right: 8px; }
```

- [ ] **Step 3: Wire up buttons in script.js**

Add toast helper:
```javascript
function showToast(message) {
    var toastEl = document.getElementById('toast');
    if (!toastEl) return;
    toastEl.textContent = message;
    toastEl.hidden = false;
    toastEl.classList.add('show');
    setTimeout(function() {
        toastEl.classList.remove('show');
        setTimeout(function() { toastEl.hidden = true; }, 300);
    }, 3000);
}
```

Add copy handler:
```javascript
async function handleCopyResults() {
    if (!lastResults) return;
    var patientInfo = {
        sex: lastPayload ? lastPayload.sex : '',
        reference: lastPayload ? lastPayload.reference || 'uk-who' : 'uk-who',
    };
    var success = await copyResultsToClipboard(lastResults, patientInfo);
    showToast(success ? 'Results copied to clipboard' : 'Copy failed — please copy manually');
}
```

Add PDF export handler:
```javascript
async function handleExportPdf() {
    if (!lastResults || !lastPayload) return;
    var btn = document.getElementById('exportPdfBtn');
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner" aria-hidden="true"></span> Generating PDF\u2026'; }

    try {
        var chartImages = typeof captureChartImages === 'function' ? await captureChartImages() : {};
        var payload = {
            results: lastResults,
            patient_info: {
                sex: lastPayload.sex,
                birth_date: lastPayload.birth_date,
                measurement_date: lastPayload.measurement_date,
                reference: lastPayload.reference || 'uk-who',
            },
            chart_images: chartImages,
        };

        var response = await fetch('/export-pdf', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            var errData = await response.json().catch(function() { return {}; });
            showToast(errData.error || 'PDF generation failed.');
            return;
        }

        var blob = await response.blob();
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = 'growth-report-' + new Date().toISOString().split('T')[0] + '.pdf';
        a.click();
        URL.revokeObjectURL(url);
        showToast('PDF downloaded');
    } catch (err) {
        showToast('Network error. Please try again.');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<span class="material-symbols-outlined" aria-hidden="true">picture_as_pdf</span> Export PDF';
        }
    }
}
```

Event listeners (add to DOMContentLoaded):
```javascript
var copyBtn = document.getElementById('copyResultsBtn');
if (copyBtn) copyBtn.addEventListener('click', handleCopyResults);
var pdfBtn = document.getElementById('exportPdfBtn');
if (pdfBtn) pdfBtn.addEventListener('click', handleExportPdf);
var dlChartBtn = document.getElementById('downloadChartBtn');
if (dlChartBtn) dlChartBtn.addEventListener('click', function() { if (typeof downloadChart === 'function') downloadChart(); });
```

- [ ] **Step 4: Verify**

```bash
node --check static/script.js
python -m pytest -v && npx jest
```

- [ ] **Step 5: Commit**

```bash
git add templates/index.html static/style.css static/script.js
git commit -m "feat: add export buttons, PDF export handler, clipboard copy wiring"
```

---

### Task 7: Dark Mode

**Files:**
- Modify: `static/style.css` (add dark mode CSS variables + chart colours)
- Modify: `static/script.js` (add theme toggle logic with localStorage + system preference detection)
- Modify: `static/charts.js` (update chart colours on theme change)

- [ ] **Step 1: Add dark mode CSS variables to style.css**

Add after the `:root` light mode variables:

```css
[data-theme="dark"] {
    --bg-primary: #1f2937;
    --bg-secondary: #111827;
    --text-primary: #f3f4f6;
    --text-secondary: #9ca3af;
    --accent-primary: #3b82f6;
    --accent-secondary: #60a5fa;
    --border-color: #374151;
    --error-color: #ef4444;
    --warning-color: #fbbf24;
    --success-color: #34d399;
}
```

Also add chart-specific dark mode overrides:
```css
[data-theme="dark"] .chart-container canvas { filter: none; }
[data-theme="dark"] .btn-show-charts { background: var(--bg-secondary); }
[data-theme="dark"] .btn-copy { background: var(--bg-primary); color: var(--text-primary); }
```

- [ ] **Step 2: Add theme toggle JS to script.js**

```javascript
function initTheme() {
    var saved = null;
    try { saved = localStorage.getItem('growthCalcTheme'); } catch(e) {}
    if (saved) {
        document.documentElement.setAttribute('data-theme', saved);
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.setAttribute('data-theme', 'dark');
    }
    updateThemeIcon();
}

function toggleTheme() {
    var current = document.documentElement.getAttribute('data-theme');
    var next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try { localStorage.setItem('growthCalcTheme', next); } catch(e) {}
    updateThemeIcon();
    // Re-render chart if visible to pick up new colours
    if (currentChart && typeof loadAndRenderChart === 'function') {
        loadAndRenderChart();
    }
}

function updateThemeIcon() {
    var icon = document.getElementById('themeIcon');
    if (!icon) return;
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    icon.textContent = isDark ? 'light_mode' : 'dark_mode';
}
```

Call `initTheme()` early in DOMContentLoaded (before restoreFormState).

Wire up theme toggle button:
```javascript
var themeBtn = document.getElementById('themeToggle');
if (themeBtn) themeBtn.addEventListener('click', toggleTheme);
```

Also add Ctrl+C keyboard shortcut to the existing `handleKeyboardShortcuts` function in script.js. Add this BEFORE the existing Ctrl+Enter handler:
```javascript
// Ctrl+C: copy results (only when results visible and focus not on text input)
if (event.key === 'c' && (event.ctrlKey || event.metaKey)) {
    var activeTag = document.activeElement ? document.activeElement.tagName : '';
    var resultsVisible = resultsSection && !resultsSection.hidden;
    if (resultsVisible && activeTag !== 'INPUT' && activeTag !== 'TEXTAREA' && activeTag !== 'SELECT') {
        event.preventDefault();
        handleCopyResults();
        return;
    }
}
```

- [ ] **Step 3: Update chart colours for dark mode in charts.js**

Add a helper that reads current theme:
```javascript
function getChartColors() {
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    return {
        centileLine: isDark ? '#9ca3af' : '#6b7280',
        median: isDark ? '#60a5fa' : '#1e40af',
        currentMarker: isDark ? '#3b82f6' : '#2563eb',
        previousMarker: isDark ? '#6b7280' : '#9ca3af',
        gridColor: isDark ? '#374151' : '#e5e7eb',
        textColor: isDark ? '#e5e7eb' : '#374151',
    };
}
```

Update `buildCentileDatasets` and `renderChart` to use `getChartColors()` instead of hardcoded colour values for:
- Centile line colours (use `chartColors.centileLine` at opacity)
- 50th centile colour (use `chartColors.median`)
- Current measurement marker (use `chartColors.currentMarker`)
- Previous measurement marker (use `chartColors.previousMarker`)
- Axis grid and text colours in the Chart.js config

- [ ] **Step 4: Verify**

```bash
node --check static/script.js && node --check static/charts.js
python -m pytest -v && npx jest
```

- [ ] **Step 5: Commit**

```bash
git add static/style.css static/script.js static/charts.js
git commit -m "feat: add dark mode with theme toggle and chart colour updates"
```

---

### Task 8: Integration Tests and Final Verification

**Files:**
- Create: `tests/test_export_integration.py`

- [ ] **Step 1: Write integration tests**

```python
"""Integration tests for export and polish features."""
import json
import base64
import pytest


class TestExportWorkflows:
    def test_full_pdf_export_workflow(self, client):
        """Calculate then export PDF with all data."""
        # First calculate
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

        # Then export PDF
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
        assert len(pdf_resp.data) > 1000  # Non-trivial PDF

    def test_all_endpoints_still_work(self, client):
        """Verify no regressions across all endpoints."""
        # Health
        assert client.get("/health").status_code == 200

        # Index
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Growth Parameters Calculator" in resp.data

        # Calculate
        calc = client.post("/calculate", data=json.dumps({
            "sex": "female", "birth_date": "2021-01-01",
            "measurement_date": "2023-01-01", "weight": 12.0,
        }), content_type="application/json")
        assert calc.status_code == 200

        # Chart data
        chart = client.post("/chart-data", data=json.dumps({
            "reference": "uk-who", "measurement_method": "height", "sex": "female",
        }), content_type="application/json")
        assert chart.status_code == 200
```

- [ ] **Step 2: Run integration tests**

```bash
python -m pytest tests/test_export_integration.py -v
```

- [ ] **Step 3: Run full suite with coverage**

```bash
python -m pytest --cov=. --cov-report=term-missing -v
npx jest --coverage
```

- [ ] **Step 4: Commit**

```bash
git add tests/test_export_integration.py
git commit -m "test: add export and polish integration tests"
```

- [ ] **Step 5: Manual browser verification**

Start dev server and test:
1. Calculate with full data
2. Click Copy — toast appears, paste into text editor to verify format
3. Click Export PDF — PDF downloads with all sections
4. Show Charts → click Download Chart — PNG downloads
5. Toggle dark mode — UI and chart colours update
6. Toggle back to light mode
7. Refresh — theme preference persists
8. Test in Advanced mode with previous measurements and bone age

- [ ] **Step 6: Tag the release**

```bash
git tag v1.0.0-phase4-complete
git push && git push --tags
```
