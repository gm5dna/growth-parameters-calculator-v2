# Growth Parameters Calculator

A stateless, single-page web application for NHS clinicians to calculate paediatric growth centiles, SDS (Z-scores), and related clinical parameters using validated RCPCH reference data.

**Privacy by design** — no database, no patient data retention. All calculations happen per-request and nothing is stored server-side.

## Features

- **Growth centiles and SDS** for weight, height, head circumference (OFC), and BMI using the [rcpchgrowth](https://github.com/rcpch/rcpchgrowth-python) library
- **Multiple growth references** — UK-WHO (default), Turner Syndrome, Trisomy 21, CDC
- **Interactive growth charts** with centile curves (0.4th–99.6th), measurement plotting, and mid-parental height display
- **Previous measurements** tracking with CSV import/export and height velocity calculation
- **Bone age assessment** with height-for-bone-age centile/SDS
- **Body surface area** (Boyd formula + cBNF lookup fallback)
- **Growth hormone dose calculator** with adjustable daily dose and three output formats
- **BMI percentage of median** for nutritional status assessment
- **Preterm gestation correction** (automatic based on gestational age)
- **PDF report export** with embedded growth charts, measurement tables, and clinical summary
- **Clipboard copy** — one-click plain text clinical summary for pasting into EHR/notes
- **Chart PNG download** at 2x resolution
- **Dark/light theme** with system preference detection
- **Basic/Advanced mode** — progressive disclosure of clinical features
- **Responsive design** — mobile-first, works on phones, tablets, and desktops

## Screenshots

*Run the app locally to see it in action — see [Quick Start](#quick-start) below.*

## Quick Start

### Prerequisites

- Python 3.12
- Node.js (for running frontend tests only)

### Setup

```bash
# Clone the repository
git clone https://github.com/gm5dna/growth-parameters-calculator-v2.git
cd growth-parameters-calculator-v2

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
npm install

# Run the development server
python app.py
```

Open **http://localhost:8080** in your browser.

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Serve the single-page application |
| GET | `/health` | Health check |
| POST | `/calculate` | Growth calculations (core) |
| POST | `/chart-data` | Centile curve data for charts |
| POST | `/export-pdf` | PDF report generation (rate-limited: 10/min) |

All POST endpoints accept and return `application/json`. Errors return `{ "success": false, "error": "...", "error_code": "ERR_XXX" }`.

### Example: Calculate

```bash
curl -X POST http://localhost:8080/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "sex": "male",
    "birth_date": "2020-06-15",
    "measurement_date": "2023-06-15",
    "weight": 14.5,
    "height": 96.0,
    "ofc": 50.0,
    "maternal_height": 165.0,
    "paternal_height": 178.0
  }'
```

## Running Tests

```bash
# Backend tests
source venv/bin/activate
python -m pytest -v                    # All tests
python -m pytest --cov=. -v            # With coverage
python -m pytest -k "test_calculate"   # Single test/pattern

# Frontend tests
npm test                               # All Jest tests
npm run test:coverage                  # With coverage

# Full suite
python -m pytest -v && npm test
```

**Current test suite:** 177 backend tests (97% coverage), 33 frontend tests.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.12, Flask 3.x |
| Growth calculations | [rcpchgrowth](https://pypi.org/project/rcpchgrowth/) (RCPCH validated) |
| PDF generation | ReportLab |
| Rate limiting | flask-limiter |
| Frontend | Vanilla JS, Vanilla CSS |
| Charts | Chart.js 4.x + chartjs-plugin-annotation |
| Icons | Material Symbols |
| Backend tests | pytest |
| Frontend tests | Jest |

## Project Structure

```
app.py                  Flask routes and orchestration
calculations.py         Age, BSA, velocity, GH dose calculations
constants.py            Thresholds, ranges, error codes
models.py               rcpchgrowth Measurement wrapper
utils.py                MPH, chart data, response formatting
validation.py           Server-side input validation
pdf_utils.py            ReportLab PDF generation
static/
  script.js             Main frontend logic
  charts.js             Chart.js integration and chart management
  clipboard.js          Clipboard formatting and copy
  validation.js         Client-side validation
  style.css             All styles, light/dark theme via CSS variables
templates/
  index.html            Jinja2 SPA shell
tests/
  conftest.py           pytest fixtures
  test_*.py             Backend tests (11 files)
  js/                   Jest frontend tests (2 files)
```

## Growth References

| Reference | Age Range | Population |
|-----------|-----------|------------|
| UK-WHO | 0–20 years | General UK (default) |
| Turner Syndrome | 1–20 years | 45,X females |
| Trisomy 21 | 0–20 years | Down syndrome |
| CDC | 0–20 years | US population |

## Clinical Safety

This is an **experimental** application for **educational and research purposes only**. It should **not** be used for clinical decision-making without independent verification.

- SDS values beyond +/-4 trigger advisory warnings
- SDS values beyond +/-8 are rejected (BMI: +/-15)
- A disclaimer banner is displayed prominently on every page load
- PDF reports include disclaimer text
- All calculations use the clinically validated [rcpchgrowth](https://growth.rcpch.ac.uk/) library from RCPCH

## Deployment

The application is configured for deployment on [Render.com](https://render.com):

```bash
# runtime.txt specifies Python version
python-3.12.8

# Start command
python app.py
```

The app reads `PORT` from the environment (default 8080).

## Acknowledgements

- [Royal College of Paediatrics and Child Health (RCPCH)](https://www.rcpch.ac.uk/) for the rcpchgrowth library and UK-WHO growth references
- [Chart.js](https://www.chartjs.org/) for the charting library
