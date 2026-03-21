# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Paediatric Growth Parameters Calculator — a stateless, single-page web application for NHS clinicians to calculate growth centiles, SDS (Z-scores), and related parameters using validated RCPCH reference data. Privacy by design: no database, no PHI retention.

Full specifications live in `spec/PRD_01` through `PRD_07`.

## Tech Stack

- **Backend:** Python 3.12, Flask 3.0, rcpchgrowth library, ReportLab (PDF), python-dateutil
- **Frontend:** Vanilla JS, Vanilla CSS, Chart.js 4.x (CDN), Material Symbols icons
- **Testing:** pytest (backend), Jest (frontend)
- **Deployment:** Render.com, auto-deploy from main branch

## Project Structure (Target)

```
app.py              # Flask routes and orchestration
constants.py        # Thresholds, ranges, error codes
validation.py       # Server-side input validation
calculations.py     # Age, BSA, velocity, GH dose calculations
models.py           # rcpchgrowth Measurement wrapper
utils.py            # MPH, chart data, response formatting
pdf_utils.py        # ReportLab PDF generation (GrowthReportPDF class)
static/
  script.js         # Main frontend logic (~970 lines)
  validation.js     # Client-side validation
  clipboard.js      # Clipboard formatting and copy
  style.css         # All styles, light/dark theme via CSS variables
templates/
  index.html        # Jinja2 SPA shell
tests/
  conftest.py       # pytest fixtures (app, client, live_server)
  test_*.py         # Backend tests by module
  js/               # Jest frontend tests
```

## Build & Run Commands

```bash
# Setup
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
npm install

# Run development server
python app.py                    # Serves on PORT (default 8080)

# Backend tests
pytest -v                        # All tests
pytest -k "test_calculate"       # Single test/pattern
pytest --cov=.                   # With coverage

# Frontend tests
npm test                         # All Jest tests
npm run test:coverage            # With coverage

# Full suite
pytest && npm test
```

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Serve SPA |
| POST | `/calculate` | Growth calculations (core) |
| POST | `/chart-data` | Centile curve data for charts |
| POST | `/export-pdf` | PDF report generation (rate-limited: 10/min) |
| GET | `/health` | Health check |

All POST endpoints accept/return `application/json`. Errors return `{ "success": false, "error": "...", "error_code": "ERR_XXX" }`.

## Architecture Decisions

- **rcpchgrowth library is mandatory** — never implement growth calculations manually. All SDS, centile, MPH, and centile curve generation must go through this validated library.
- **Server-side validation is authoritative** — client-side validation exists for UX only. Never trust client input.
- **No database** — stateless by design. Form state uses localStorage on the client.
- **Vanilla JS, no framework** — performance and simplicity. DOM is source of truth for form data, global variables for chart state.
- **Server-side PDF generation** — ReportLab on the backend; chart images sent as base64 from canvas.
- **A4 page size** for all PDF output.

## Key Domain Concepts

- **SDS** (Standard Deviation Score / Z-score): distance from population mean. Warning at +/-4, hard reject at +/-8 (BMI: +/-15).
- **Growth references**: UK-WHO (default, 0-20y), Turner Syndrome (female only, 1-20y), Trisomy 21 (0-18y), CDC (US, 0-20y).
- **Centile lines**: 0.4, 2, 9, 25, 50, 75, 91, 98, 99.6.
- **Gestation correction**: applied for preterm (<37 weeks) — until age 1 if 32-36 weeks, until age 2 if <32 weeks.
- **MPH** (Mid-Parental Height): `(maternal + paternal) / 2 +/- 6.5cm` (+ for males, - for females). Target range +/-8.5cm.
- **BSA**: Boyd formula when both weight+height available; cBNF lookup table when weight only.
- **Height velocity**: requires >=4 months between measurements. Uses most recent valid previous height.
- **Basic/Advanced mode**: basic mode hides reference selection, gestation, previous measurements, bone age, GH calculator, BSA, BMI % median.

## Implementation Phases

1. **Foundation** — project structure (PRD-06), core calculations (PRD-02), basic UI (PRD-05), deploy MVP
2. **Visualisation** — chart-data endpoint, Chart.js integration, centile curves, measurement plotting (PRD-03)
3. **Advanced Features** — previous measurements, height velocity, bone age, BSA, GH calculator, preterm correction (PRD-04)
4. **Export & Polish** — PDF export, clipboard copy, chart download, dark mode, PWA, testing (PRD-07)

## Clinical Safety Rules

- Display clear warnings for extreme SDS values (>+/-4 SDS advisory, >+/-8 SDS hard rejection)
- Prominent disclaimer banner on the app (dismissible but returns on refresh)
- All measurement values must pass range validation (see `constants.py` thresholds in PRD-06 §5.2)
- Never display clinical results without proper validation
- PDF reports must include disclaimer text
