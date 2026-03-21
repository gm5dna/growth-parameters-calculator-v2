# PRD 06: Technical Architecture

## Document Information
- **Version:** 1.0
- **Last Updated:** January 2026
- **Related PRD:** PRD-01 Product Overview

---

## 1. Overview

This PRD defines the technical architecture, technology stack, API design, code organization, testing strategy, and deployment requirements for the Growth Parameters Calculator.

---

## 2. Technology Stack

### 2.1 Backend

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Runtime | Python | 3.12.x | Server-side logic |
| Framework | Flask | 3.0.0 | Web server, routing |
| Growth Library | rcpchgrowth | Latest | Validated calculations |
| PDF Generation | ReportLab | Latest | PDF reports |
| Date Handling | python-dateutil | Latest | Date calculations |
| Rate Limiting | Flask-Limiter | Latest | API protection (optional) |

### 2.2 Frontend

| Component | Technology | Purpose |
|-----------|------------|---------|
| JavaScript | Vanilla JS | No framework overhead |
| Charts | Chart.js 4.x | Interactive growth charts |
| Icons | Material Symbols | UI icons |
| CSS | Vanilla CSS | Custom styling |

### 2.3 Infrastructure

| Component | Technology | Purpose |
|-----------|------------|---------|
| Hosting | Render.com | Auto-deploy from git |
| Static Files | Flask static | Served by application |
| SSL | Render managed | HTTPS |

---

## 3. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT (Browser)                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   HTML      │  │    CSS      │  │     JavaScript          │ │
│  │ (Jinja2)    │  │ (style.css) │  │ script.js, validation.js│ │
│  │             │  │             │  │ clipboard.js            │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│                              │                                   │
│                              │ fetch() / XHR                     │
│                              ▼                                   │
├─────────────────────────────────────────────────────────────────┤
│                         FLASK SERVER                             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                      app.py (Routes)                         ││
│  │  GET /           → index.html (SPA)                         ││
│  │  POST /calculate → Growth calculations                      ││
│  │  POST /chart-data → Centile curve data                      ││
│  │  POST /export-pdf → PDF generation                          ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                   │
│  ┌───────────────────────────┼───────────────────────────────┐  │
│  │                     Business Logic                         │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐   │  │
│  │  │ validation.py│ │calculations.py│ │    models.py      │   │  │
│  │  │ Input checks │ │ Age, BSA, etc│ │ Measurement wrap  │   │  │
│  │  └──────────────┘ └──────────────┘ └──────────────────┘   │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐   │  │
│  │  │  utils.py    │ │ constants.py │ │   pdf_utils.py    │   │  │
│  │  │ MPH, charts  │ │ Thresholds   │ │ PDF generation    │   │  │
│  │  └──────────────┘ └──────────────┘ └──────────────────┘   │  │
│  └───────────────────────────┬───────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    rcpchgrowth Library                       ││
│  │  • Measurement class (SDS, centiles)                        ││
│  │  • chronological_decimal_age()                              ││
│  │  • corrected_decimal_age()                                  ││
│  │  • mid_parental_height()                                    ││
│  │  • create_chart() (centile curves)                          ││
│  │  • percentage_median_bmi()                                  ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. File Structure

```
growth-parameters-calculator/
├── app.py                    # Flask routes and orchestration
├── constants.py              # Configuration constants
├── validation.py             # Input validation logic
├── calculations.py           # Age, BSA, velocity calculations
├── models.py                 # rcpchgrowth Measurement wrapper
├── utils.py                  # MPH, chart data, helpers
├── pdf_utils.py              # PDF report generation
├── requirements.txt          # Production dependencies
├── requirements-dev.txt      # Development/test dependencies
├── runtime.txt               # Python version for hosting
├── package.json              # Node.js/Jest configuration
│
├── static/
│   ├── script.js            # Main frontend logic
│   ├── validation.js        # Client-side validation
│   ├── clipboard.js         # Clipboard formatting
│   ├── style.css            # Stylesheet
│   ├── favicon.svg          # Favicon
│   └── site.webmanifest     # PWA manifest
│
├── templates/
│   └── index.html           # Jinja2 template (SPA shell)
│
├── tests/
│   ├── conftest.py          # pytest fixtures
│   ├── test_endpoints.py    # API endpoint tests
│   ├── test_models.py       # Measurement tests
│   ├── test_calculations.py # Calculation tests
│   ├── test_validation.py   # Validation tests
│   ├── test_utils.py        # Utility function tests
│   ├── test_workflows.py    # Integration tests
│   ├── test_error_paths.py  # Error handling tests
│   └── js/
│       ├── validation.test.js
│       ├── clipboard.test.js
│       └── script.test.js
│
├── docs/                     # GitHub Pages documentation
│   ├── index.html
│   └── style.css
│
└── documentation/            # Technical documentation
    ├── PRD_*.md              # Product requirement docs
    ├── TESTING.md            # Testing guide
    └── TESTING_GUIDELINES.md # Test conventions
```

---

## 5. Module Responsibilities

### 5.1 app.py
- Flask application initialization
- Route definitions
- Request parsing
- Response formatting
- Error handling
- Rate limiting configuration

### 5.2 constants.py
```python
# Age limits
MIN_AGE_YEARS = 0.0
MAX_AGE_YEARS = 25.0

# SDS thresholds
SDS_WARNING_LIMIT = 4.0
SDS_HARD_LIMIT = 8.0
BMI_SDS_HARD_LIMIT = 15.0

# Measurement ranges
MIN_WEIGHT_KG = 0.1
MAX_WEIGHT_KG = 300.0
MIN_HEIGHT_CM = 10.0
MAX_HEIGHT_CM = 250.0
MIN_OFC_CM = 10.0
MAX_OFC_CM = 100.0

# Gestation
MIN_GESTATION_WEEKS = 22
MAX_GESTATION_WEEKS = 44
PRETERM_THRESHOLD_WEEKS = 37

# Error codes
class ErrorCodes:
    INVALID_DATE_FORMAT = "ERR_001"
    # ...
```

### 5.3 validation.py
- `ValidationError` exception class
- `validate_date()` - Date format and range
- `validate_weight()` - Weight range
- `validate_height()` - Height range
- `validate_ofc()` - OFC range
- `validate_gestation()` - Gestation range
- `validate_at_least_one_measurement()`

### 5.4 calculations.py
- `calculate_age_in_years()` - Chronological age
- `should_apply_gestation_correction()` - Correction decision
- `calculate_corrected_age()` - Corrected age
- `calculate_boyd_bsa()` - BSA with Boyd formula
- `calculate_cbnf_bsa()` - BSA with lookup table
- `calculate_height_velocity()` - Growth velocity
- `calculate_gh_dose()` - GH dose formats

### 5.5 models.py
- `create_measurement()` - Measurement factory
- `validate_measurement_sds()` - SDS validation
- `extract_measurement_result()` - Result formatting

### 5.6 utils.py
- `norm_cdf()` - Normal distribution CDF
- `calculate_mid_parental_height()` - MPH calculation
- `calculate_percentage_median_bmi()` - BMI % median
- `get_chart_data()` - Centile curve data
- `format_error_response()` - Error formatting
- `format_success_response()` - Success formatting

### 5.7 pdf_utils.py
- `GrowthReportPDF` class
- Page layout and styling
- Section generation
- Chart image embedding
- PDF buffer generation

---

## 6. API Design

### 6.1 Endpoints Summary

| Method | Endpoint | Purpose | Rate Limit |
|--------|----------|---------|------------|
| GET | / | Serve SPA | None |
| POST | /calculate | Growth calculations | Default |
| POST | /chart-data | Centile curves | Default |
| POST | /export-pdf | PDF generation | 10/minute |

### 6.2 Request/Response Format
- Content-Type: `application/json`
- Character encoding: UTF-8
- Date format: ISO 8601 (YYYY-MM-DD)

### 6.3 Error Response Structure
```json
{
  "success": false,
  "error": "Human-readable error message",
  "error_code": "ERR_XXX"
}
```

### 6.4 Success Response Structure
```json
{
  "success": true,
  "results": {
    // ... calculation results
  }
}
```

### 6.5 HTTP Status Codes

| Code | Usage |
|------|-------|
| 200 | Successful request |
| 400 | Validation error, bad request |
| 429 | Rate limit exceeded |
| 500 | Server error |

---

## 7. Frontend Architecture

### 7.1 JavaScript Modules

#### script.js (~970 lines)
- Form submission handling
- Results display
- Chart rendering
- Mode toggle
- Form state persistence
- Dark mode management
- Previous measurements table
- Bone age table
- GH dose calculator

#### validation.js (~200 lines)
- Client-side validation functions
- Real-time field validation
- Error message generation

#### clipboard.js (~370 lines)
- Results formatting for clipboard
- Clinical text generation
- Copy functionality

### 7.2 State Management
- No external state library
- DOM as source of truth for form data
- localStorage for persistence
- Global variables for chart state

### 7.3 Event Handling
```javascript
// Form submission
document.getElementById('growthForm').addEventListener('submit', handleSubmit);

// Mode toggle
document.getElementById('modeToggle').addEventListener('change', handleModeChange);

// Theme toggle
document.getElementById('themeToggle').addEventListener('click', toggleTheme);

// Debounced auto-save
formInputs.forEach(input => input.addEventListener('input', debouncedSave));
```

---

## 8. Data Flow

### 8.1 Calculation Flow

```
1. User enters data in form
2. Client-side validation runs
3. If valid, POST to /calculate
4. Server validates input
5. Server creates rcpchgrowth Measurements
6. Server calculates derived values (BSA, velocity, etc.)
7. Server validates SDS ranges
8. Server returns JSON response
9. Client updates results display
10. Client enables chart viewing
```

### 8.2 Chart Data Flow

```
1. User clicks "Show Growth Charts"
2. Client requests chart data (POST /chart-data)
3. Server calls rcpchgrowth create_chart()
4. Server returns centile curve data
5. Client renders chart with Chart.js
6. Client overlays measurement points
```

### 8.3 PDF Export Flow

```
1. User clicks "Export PDF"
2. Client captures chart images (canvas.toDataURL)
3. Client sends results + patient info + images
4. Server generates PDF with ReportLab
5. Server returns PDF binary
6. Browser downloads file
```

---

## 9. Security Considerations

### 9.1 Input Validation
- Server-side validation is authoritative
- Client-side validation for UX only
- Type checking on all inputs
- Range validation on all measurements
- Date validation (no future dates)

### 9.2 Rate Limiting
```python
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

@app.route('/export-pdf')
@limiter.limit("10 per minute")
def export_pdf():
    ...
```

### 9.3 No Data Persistence
- Stateless design
- No database
- No session storage on server
- No PHI retained

### 9.4 Content Security
- No user-generated content displayed
- JSON responses properly encoded
- PDF generation uses safe templating

---

## 10. Error Handling

### 10.1 Server-Side Errors
```python
try:
    # Calculation logic
except ValidationError as e:
    return jsonify({
        'success': False,
        'error': e.message,
        'error_code': e.code
    }), 400
except Exception as e:
    return jsonify({
        'success': False,
        'error': str(e)
    }), 400
```

### 10.2 Client-Side Errors
```javascript
try {
    const response = await fetch('/calculate', { ... });
    const data = await response.json();

    if (!data.success) {
        showError(data.error);
        return;
    }

    displayResults(data.results);
} catch (error) {
    showError('Network error. Please check your connection.');
}
```

---

## 11. Testing Strategy

### 11.1 Backend Tests (pytest)

| Category | Tests | Coverage Target |
|----------|-------|-----------------|
| Endpoints | 35+ | All routes |
| Models | 30+ | Measurement creation |
| Calculations | 30+ | All formulas |
| Validation | 25+ | All validators |
| Utils | 23+ | Helper functions |
| Workflows | 20+ | E2E scenarios |
| Error paths | 50+ | Edge cases |

### 11.2 Frontend Tests (Jest)

| Category | Tests | Coverage |
|----------|-------|----------|
| validation.js | 30+ | All validators |
| clipboard.js | 25+ | All formatters |
| script.js | 20+ | Key functions |

### 11.3 Test Fixtures
```python
# conftest.py
@pytest.fixture
def app():
    """Create application for testing."""
    return Flask(__name__)

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

@pytest.fixture
def live_server(app):
    """Start live server for E2E tests."""
    ...
```

### 11.4 Running Tests
```bash
# Backend
pytest -v                    # All tests
pytest --cov=.               # With coverage
pytest -k "test_calculate"   # Specific tests

# Frontend
npm test                     # All tests
npm run test:coverage        # With coverage

# Full suite
pytest && npm test
```

---

## 12. Deployment

### 12.1 Render.com Configuration

```yaml
# render.yaml (implicit)
services:
  - type: web
    name: growth-parameters-calculator
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python app.py
```

### 12.2 Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| PORT | Server port | 8080 |
| PYTHON_VERSION | Runtime version | 3.12.8 |

### 12.3 Deployment Flow
```
1. Developer pushes to main branch
2. Render detects push
3. Render installs dependencies
4. Render starts application
5. Health check passes
6. Traffic routed to new deployment
```

### 12.4 Files Required

**requirements.txt** (production only):
```
Flask>=3.0.0
rcpchgrowth>=4.0.0
python-dateutil>=2.8.0
reportlab>=4.0.0
Pillow>=10.0.0
flask-limiter>=3.0.0
```

**runtime.txt**:
```
python-3.12.8
```

---

## 13. Performance Optimization

### 13.1 Server-Side
- Stateless design (no session overhead)
- rcpchgrowth calculations are fast
- PDF generation is rate-limited
- No database queries

### 13.2 Client-Side
- Vanilla JS (no framework bundle)
- Chart.js loaded from CDN
- Debounced event handlers
- Lazy chart loading

### 13.3 Asset Optimization
- Minified CSS in production
- Gzipped responses (Render default)
- Browser caching for static files

---

## 14. Monitoring & Logging

### 14.1 Logging
```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"Calculation request received: {request.json.get('sex')}")
logger.error(f"Calculation error: {str(e)}")
```

### 14.2 Health Check
```python
@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200
```

### 14.3 Render Monitoring
- View logs in Render dashboard
- Set up alerts for errors
- Monitor response times

---

## 15. Development Workflow

### 15.1 Local Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
npm install

# Run development server
python app.py
```

### 15.2 Pre-Commit Checklist
- [ ] All tests pass (`pytest && npm test`)
- [ ] No new linting errors
- [ ] Code reviewed
- [ ] Documentation updated if needed

### 15.3 Git Workflow
- Main branch is production
- Feature branches for development
- PR required for main
- Auto-deploy on merge to main

---

## 16. Acceptance Criteria

### 16.1 Architecture
- [ ] All modules follow single responsibility
- [ ] No circular dependencies
- [ ] Clear separation of concerns

### 16.2 API
- [ ] All endpoints documented
- [ ] Consistent error responses
- [ ] Rate limiting in place

### 16.3 Testing
- [ ] >90% backend test coverage on critical paths
- [ ] >80% frontend test coverage
- [ ] All tests pass in CI

### 16.4 Deployment
- [ ] Auto-deploy from git works
- [ ] Zero-downtime deployments
- [ ] Rollback capability
