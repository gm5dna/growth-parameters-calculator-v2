# Phase 1: Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working MVP — Flask backend with `/calculate` endpoint, basic responsive form, results display with centiles/SDS for weight, height, OFC, BMI, and mid-parental height.

**Architecture:** Stateless Flask SPA. Backend modules (constants, validation, calculations, models, utils) feed into a single `/calculate` POST route. Frontend is vanilla JS/CSS with a Jinja2 template. rcpchgrowth library handles all growth reference calculations — never implement these manually. No database, no auth.

**Tech Stack:** Python 3.12, Flask 3.0, rcpchgrowth 4.4.1, pytest, Jest, vanilla JS/CSS

**Specs:** `spec/PRD_01_PRODUCT_OVERVIEW.md`, `spec/PRD_02_CORE_CALCULATOR.md`, `spec/PRD_05_USER_EXPERIENCE.md`, `spec/PRD_06_TECHNICAL_ARCHITECTURE.md`

---

## File Map

| File | Responsibility | New/Modify |
|------|---------------|------------|
| `requirements.txt` | Production Python deps | Create |
| `requirements-dev.txt` | Test/dev Python deps | Create |
| `runtime.txt` | Python version for Render | Create |
| `package.json` | Jest config, npm scripts | Create |
| `.gitignore` | Git ignores | Create |
| `.python-version` | pyenv local version | Create |
| `constants.py` | All thresholds, ranges, error codes | Create |
| `validation.py` | ValidationError, input validators | Create |
| `calculations.py` | Age calculation, gestation correction check | Create |
| `models.py` | rcpchgrowth Measurement wrapper, SDS validation, result extraction | Create |
| `utils.py` | MPH, norm_cdf, response formatting | Create |
| `app.py` | Flask app, routes (GET /, POST /calculate, GET /health) | Create |
| `templates/index.html` | Jinja2 SPA shell — form, results, disclaimer | Create |
| `static/style.css` | Light mode theme, responsive layout, form/result styling | Create |
| `static/validation.js` | Client-side field validation | Create |
| `static/script.js` | Form submission, results display, localStorage persistence | Create |
| `tests/__init__.py` | Package init | Create |
| `tests/conftest.py` | pytest fixtures (app, client) | Create |
| `tests/test_constants.py` | Constants module tests | Create |
| `tests/test_validation.py` | Validation module tests | Create |
| `tests/test_calculations.py` | Age/gestation calculation tests | Create |
| `tests/test_models.py` | Measurement wrapper tests | Create |
| `tests/test_utils.py` | MPH, norm_cdf, response formatting tests | Create |
| `tests/test_endpoints.py` | Flask route integration tests | Create |

---

### Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `runtime.txt`
- Create: `package.json`
- Create: `.gitignore`
- Create: `.python-version`

- [ ] **Step 1: Initialise git repo**

```bash
cd "/Users/stuart/Documents/working/coding/growth app v2"
git init
```

- [ ] **Step 2: Create .gitignore**

```gitignore
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
venv/
.venv/
node_modules/
.pytest_cache/
.coverage
htmlcov/
*.egg
.DS_Store
```

- [ ] **Step 3: Create .python-version**

```
3.12
```

- [ ] **Step 4: Install Python 3.12 via pyenv if needed and create venv**

```bash
pyenv install 3.12 --skip-existing
cd "/Users/stuart/Documents/working/coding/growth app v2"
pyenv local 3.12
python3 -m venv venv
source venv/bin/activate
```

Verify: `python --version` should show `Python 3.12.x`.

- [ ] **Step 5: Create requirements.txt**

```
Flask>=3.0.0,<4.0.0
rcpchgrowth>=4.0.0
python-dateutil>=2.8.0
```

Note: ReportLab, Pillow, flask-limiter deferred to Phase 4 (export/rate-limiting). Keep deps minimal for MVP.

- [ ] **Step 6: Create requirements-dev.txt**

```
-r requirements.txt
pytest>=8.0.0
pytest-cov>=5.0.0
```

- [ ] **Step 7: Create runtime.txt**

```
python-3.12.8
```

- [ ] **Step 8: Install Python dependencies**

```bash
source venv/bin/activate
pip install -r requirements-dev.txt
```

Verify: `python -c "from rcpchgrowth import Measurement; print('OK')"` should print OK.

- [ ] **Step 9: Create package.json**

```json
{
  "name": "growth-parameters-calculator",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "test": "jest",
    "test:coverage": "jest --coverage"
  },
  "devDependencies": {
    "jest": "^29.0.0",
    "jest-environment-jsdom": "^29.0.0"
  },
  "jest": {
    "testEnvironment": "jsdom",
    "roots": ["<rootDir>/tests/js"]
  }
}
```

- [ ] **Step 10: Install npm dependencies**

```bash
npm install
```

- [ ] **Step 11: Commit**

```bash
git add .gitignore .python-version requirements.txt requirements-dev.txt runtime.txt package.json package-lock.json
git commit -m "chore: project setup with Python 3.12, Flask, rcpchgrowth, Jest"
```

---

### Task 2: Constants Module

**Files:**
- Create: `constants.py`
- Test: `tests/test_constants.py`

- [ ] **Step 1: Write the test**

Create `tests/__init__.py` (empty file) and `tests/test_constants.py`:

```python
"""Tests for constants module."""
from constants import (
    MIN_AGE_YEARS, MAX_AGE_YEARS,
    SDS_WARNING_LIMIT, SDS_HARD_LIMIT, BMI_SDS_HARD_LIMIT,
    MIN_WEIGHT_KG, MAX_WEIGHT_KG,
    MIN_HEIGHT_CM, MAX_HEIGHT_CM,
    MIN_OFC_CM, MAX_OFC_CM,
    MIN_GESTATION_WEEKS, MAX_GESTATION_WEEKS, PRETERM_THRESHOLD_WEEKS,
    VALID_REFERENCES, DEFAULT_REFERENCE, VALID_SEXES,
    VALID_MEASUREMENT_METHODS,
    ErrorCodes,
)


def test_age_limits():
    assert MIN_AGE_YEARS == 0.0
    assert MAX_AGE_YEARS == 25.0


def test_sds_thresholds():
    assert SDS_WARNING_LIMIT == 4.0
    assert SDS_HARD_LIMIT == 8.0
    assert BMI_SDS_HARD_LIMIT == 15.0


def test_measurement_ranges():
    assert MIN_WEIGHT_KG == 0.1
    assert MAX_WEIGHT_KG == 300.0
    assert MIN_HEIGHT_CM == 10.0
    assert MAX_HEIGHT_CM == 250.0
    assert MIN_OFC_CM == 10.0
    assert MAX_OFC_CM == 100.0


def test_gestation_constants():
    assert MIN_GESTATION_WEEKS == 22
    assert MAX_GESTATION_WEEKS == 44
    assert PRETERM_THRESHOLD_WEEKS == 37


def test_valid_references():
    assert "uk-who" in VALID_REFERENCES
    assert "turners-syndrome" in VALID_REFERENCES
    assert "trisomy-21" in VALID_REFERENCES
    assert "cdc" in VALID_REFERENCES
    assert DEFAULT_REFERENCE == "uk-who"


def test_valid_sexes():
    assert VALID_SEXES == {"male", "female"}


def test_valid_measurement_methods():
    assert "height" in VALID_MEASUREMENT_METHODS
    assert "weight" in VALID_MEASUREMENT_METHODS
    assert "ofc" in VALID_MEASUREMENT_METHODS
    assert "bmi" in VALID_MEASUREMENT_METHODS


def test_error_codes_exist():
    assert ErrorCodes.INVALID_DATE_FORMAT == "ERR_001"
    assert ErrorCodes.INVALID_DATE_RANGE == "ERR_002"
    assert ErrorCodes.MISSING_MEASUREMENT == "ERR_003"
    assert ErrorCodes.INVALID_WEIGHT == "ERR_004"
    assert ErrorCodes.INVALID_HEIGHT == "ERR_005"
    assert ErrorCodes.INVALID_OFC == "ERR_006"
    assert ErrorCodes.INVALID_GESTATION == "ERR_007"
    assert ErrorCodes.SDS_OUT_OF_RANGE == "ERR_008"
    assert ErrorCodes.CALCULATION_ERROR == "ERR_009"
    assert ErrorCodes.INVALID_INPUT == "ERR_010"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_constants.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'constants'`

- [ ] **Step 3: Write constants.py**

```python
"""Application constants — thresholds, ranges, error codes."""

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

# Valid values
VALID_REFERENCES = {"uk-who", "turners-syndrome", "trisomy-21", "cdc"}
DEFAULT_REFERENCE = "uk-who"
VALID_SEXES = {"male", "female"}
VALID_MEASUREMENT_METHODS = {"height", "weight", "ofc", "bmi"}


class ErrorCodes:
    INVALID_DATE_FORMAT = "ERR_001"
    INVALID_DATE_RANGE = "ERR_002"
    MISSING_MEASUREMENT = "ERR_003"
    INVALID_WEIGHT = "ERR_004"
    INVALID_HEIGHT = "ERR_005"
    INVALID_OFC = "ERR_006"
    INVALID_GESTATION = "ERR_007"
    SDS_OUT_OF_RANGE = "ERR_008"
    CALCULATION_ERROR = "ERR_009"
    INVALID_INPUT = "ERR_010"
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_constants.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add constants.py tests/__init__.py tests/test_constants.py
git commit -m "feat: add constants module with thresholds, ranges, error codes"
```

---

### Task 3: Validation Module

**Files:**
- Create: `validation.py`
- Test: `tests/test_validation.py`

- [ ] **Step 1: Write the test**

```python
"""Tests for validation module."""
import pytest
from datetime import date
from validation import (
    ValidationError,
    validate_date,
    validate_weight,
    validate_height,
    validate_ofc,
    validate_gestation,
    validate_sex,
    validate_reference,
    validate_at_least_one_measurement,
)


class TestValidationError:
    def test_has_message_and_code(self):
        err = ValidationError("bad input", "ERR_001")
        assert err.message == "bad input"
        assert err.code == "ERR_001"
        assert str(err) == "bad input"


class TestValidateDate:
    def test_valid_date_string(self):
        result = validate_date("2023-06-15", "birth_date")
        assert result == date(2023, 6, 15)

    def test_invalid_format(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_date("15/06/2023", "birth_date")
        assert exc_info.value.code == "ERR_001"

    def test_future_date_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_date("2099-01-01", "birth_date")
        assert exc_info.value.code == "ERR_002"

    def test_empty_string_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_date("", "birth_date")
        assert exc_info.value.code == "ERR_001"

    def test_none_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_date(None, "birth_date")
        assert exc_info.value.code == "ERR_001"


class TestValidateWeight:
    def test_valid_weight(self):
        assert validate_weight(12.5) == 12.5

    def test_none_returns_none(self):
        assert validate_weight(None) is None

    def test_below_minimum(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_weight(0.05)
        assert exc_info.value.code == "ERR_004"

    def test_above_maximum(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_weight(301.0)
        assert exc_info.value.code == "ERR_004"

    def test_non_numeric_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_weight("abc")
        assert exc_info.value.code == "ERR_004"

    def test_boundary_minimum(self):
        assert validate_weight(0.1) == 0.1

    def test_boundary_maximum(self):
        assert validate_weight(300.0) == 300.0


class TestValidateHeight:
    def test_valid_height(self):
        assert validate_height(85.3) == 85.3

    def test_none_returns_none(self):
        assert validate_height(None) is None

    def test_below_minimum(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_height(5.0)
        assert exc_info.value.code == "ERR_005"

    def test_above_maximum(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_height(260.0)
        assert exc_info.value.code == "ERR_005"


class TestValidateOfc:
    def test_valid_ofc(self):
        assert validate_ofc(48.2) == 48.2

    def test_none_returns_none(self):
        assert validate_ofc(None) is None

    def test_below_minimum(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_ofc(5.0)
        assert exc_info.value.code == "ERR_006"

    def test_above_maximum(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_ofc(110.0)
        assert exc_info.value.code == "ERR_006"


class TestValidateGestation:
    def test_valid_gestation(self):
        weeks, days = validate_gestation(34, 3)
        assert weeks == 34
        assert days == 3

    def test_none_returns_none(self):
        assert validate_gestation(None, None) is None

    def test_days_defaults_to_zero(self):
        weeks, days = validate_gestation(38, None)
        assert weeks == 38
        assert days == 0

    def test_below_minimum_weeks(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_gestation(20, 0)
        assert exc_info.value.code == "ERR_007"

    def test_above_maximum_weeks(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_gestation(45, 0)
        assert exc_info.value.code == "ERR_007"

    def test_invalid_days(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_gestation(34, 7)
        assert exc_info.value.code == "ERR_007"


class TestValidateSex:
    def test_valid_male(self):
        assert validate_sex("male") == "male"

    def test_valid_female(self):
        assert validate_sex("female") == "female"

    def test_invalid_sex(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_sex("other")
        assert exc_info.value.code == "ERR_010"

    def test_none_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_sex(None)
        assert exc_info.value.code == "ERR_010"


class TestValidateReference:
    def test_valid_reference(self):
        assert validate_reference("uk-who") == "uk-who"

    def test_none_defaults(self):
        assert validate_reference(None) == "uk-who"

    def test_invalid_reference(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_reference("invalid")
        assert exc_info.value.code == "ERR_010"


class TestValidateAtLeastOneMeasurement:
    def test_weight_only(self):
        validate_at_least_one_measurement(weight=12.5)

    def test_height_only(self):
        validate_at_least_one_measurement(height=85.3)

    def test_ofc_only(self):
        validate_at_least_one_measurement(ofc=48.2)

    def test_none_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_at_least_one_measurement()
        assert exc_info.value.code == "ERR_003"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_validation.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'validation'`

- [ ] **Step 3: Write validation.py**

```python
"""Input validation — server-side is authoritative."""
from datetime import date, datetime

from constants import (
    MIN_WEIGHT_KG, MAX_WEIGHT_KG,
    MIN_HEIGHT_CM, MAX_HEIGHT_CM,
    MIN_OFC_CM, MAX_OFC_CM,
    MIN_GESTATION_WEEKS, MAX_GESTATION_WEEKS,
    VALID_REFERENCES, DEFAULT_REFERENCE, VALID_SEXES,
    ErrorCodes,
)


class ValidationError(Exception):
    """Validation error with human-readable message and error code."""

    def __init__(self, message, code):
        self.message = message
        self.code = code
        super().__init__(message)


def validate_date(value, field_name):
    """Parse and validate a date string (YYYY-MM-DD). Returns datetime.date."""
    if not value or not isinstance(value, str):
        raise ValidationError(
            f"{field_name} is required and must be in YYYY-MM-DD format.",
            ErrorCodes.INVALID_DATE_FORMAT,
        )
    try:
        parsed = datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError(
            f"{field_name} must be in YYYY-MM-DD format.",
            ErrorCodes.INVALID_DATE_FORMAT,
        )
    if parsed > date.today():
        raise ValidationError(
            f"{field_name} cannot be in the future.",
            ErrorCodes.INVALID_DATE_RANGE,
        )
    return parsed


def _validate_numeric_range(value, min_val, max_val, name, error_code):
    """Validate an optional numeric field. Returns float or None."""
    if value is None or value == "":
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValidationError(
            f"{name} must be a number.",
            error_code,
        )
    if value < min_val or value > max_val:
        raise ValidationError(
            f"{name} must be between {min_val} and {max_val}.",
            error_code,
        )
    return value


def validate_weight(value):
    return _validate_numeric_range(
        value, MIN_WEIGHT_KG, MAX_WEIGHT_KG, "Weight", ErrorCodes.INVALID_WEIGHT
    )


def validate_height(value):
    return _validate_numeric_range(
        value, MIN_HEIGHT_CM, MAX_HEIGHT_CM, "Height", ErrorCodes.INVALID_HEIGHT
    )


def validate_ofc(value):
    return _validate_numeric_range(
        value, MIN_OFC_CM, MAX_OFC_CM, "Head circumference", ErrorCodes.INVALID_OFC
    )


def validate_gestation(weeks, days):
    """Validate gestation. Returns (weeks, days) tuple or None if not provided."""
    if weeks is None and days is None:
        return None
    if weeks is None:
        raise ValidationError(
            "Gestation weeks is required when days are provided.",
            ErrorCodes.INVALID_GESTATION,
        )
    try:
        weeks = int(weeks)
    except (TypeError, ValueError):
        raise ValidationError(
            "Gestation weeks must be a whole number.",
            ErrorCodes.INVALID_GESTATION,
        )
    if weeks < MIN_GESTATION_WEEKS or weeks > MAX_GESTATION_WEEKS:
        raise ValidationError(
            f"Gestation weeks must be between {MIN_GESTATION_WEEKS} and {MAX_GESTATION_WEEKS}.",
            ErrorCodes.INVALID_GESTATION,
        )
    if days is None:
        days = 0
    try:
        days = int(days)
    except (TypeError, ValueError):
        raise ValidationError(
            "Gestation days must be a whole number.",
            ErrorCodes.INVALID_GESTATION,
        )
    if days < 0 or days > 6:
        raise ValidationError(
            "Gestation days must be between 0 and 6.",
            ErrorCodes.INVALID_GESTATION,
        )
    return weeks, days


def validate_sex(value):
    if not value or value not in VALID_SEXES:
        raise ValidationError(
            "Sex must be 'male' or 'female'.",
            ErrorCodes.INVALID_INPUT,
        )
    return value


def validate_reference(value):
    if value is None:
        return DEFAULT_REFERENCE
    if value not in VALID_REFERENCES:
        raise ValidationError(
            f"Reference must be one of: {', '.join(sorted(VALID_REFERENCES))}.",
            ErrorCodes.INVALID_INPUT,
        )
    return value


def validate_at_least_one_measurement(weight=None, height=None, ofc=None):
    if weight is None and height is None and ofc is None:
        raise ValidationError(
            "At least one measurement (weight, height, or head circumference) is required.",
            ErrorCodes.MISSING_MEASUREMENT,
        )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_validation.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add validation.py tests/test_validation.py
git commit -m "feat: add validation module with all input validators"
```

---

### Task 4: Calculations Module

**Files:**
- Create: `calculations.py`
- Test: `tests/test_calculations.py`

Phase 1 scope: age calculation and gestation correction decision only. BSA, height velocity, and GH dose are Phase 3.

- [ ] **Step 1: Write the test**

```python
"""Tests for calculations module."""
import pytest
from datetime import date
from calculations import (
    calculate_age_in_years,
    calculate_calendar_age,
    should_apply_gestation_correction,
)


class TestCalculateAgeInYears:
    def test_one_year(self):
        age = calculate_age_in_years(date(2022, 1, 1), date(2023, 1, 1))
        assert abs(age - 1.0) < 0.01

    def test_newborn(self):
        age = calculate_age_in_years(date(2023, 6, 15), date(2023, 6, 16))
        assert age > 0
        assert age < 0.01

    def test_same_day_birth_measurement(self):
        """Birth weight scenario — age is 0."""
        age = calculate_age_in_years(date(2023, 6, 15), date(2023, 6, 15))
        assert age == 0.0

    def test_five_years(self):
        age = calculate_age_in_years(date(2018, 3, 1), date(2023, 3, 1))
        assert abs(age - 5.0) < 0.02

    def test_measurement_before_birth_raises(self):
        with pytest.raises(ValueError):
            calculate_age_in_years(date(2023, 6, 15), date(2023, 6, 14))


class TestCalculateCalendarAge:
    def test_simple_years_months_days(self):
        result = calculate_calendar_age(date(2020, 1, 15), date(2023, 6, 27))
        assert result["years"] == 3
        assert result["months"] == 5
        assert result["days"] == 12

    def test_newborn(self):
        result = calculate_calendar_age(date(2023, 6, 15), date(2023, 6, 16))
        assert result["years"] == 0
        assert result["months"] == 0
        assert result["days"] == 1

    def test_exact_birthday(self):
        result = calculate_calendar_age(date(2020, 6, 15), date(2023, 6, 15))
        assert result["years"] == 3
        assert result["months"] == 0
        assert result["days"] == 0


class TestShouldApplyGestationCorrection:
    def test_term_baby_no_correction(self):
        assert should_apply_gestation_correction(38, 0.5) is False

    def test_preterm_32_36_under_one_year(self):
        assert should_apply_gestation_correction(34, 0.5) is True

    def test_preterm_32_36_over_one_year(self):
        assert should_apply_gestation_correction(34, 1.5) is False

    def test_very_preterm_under_two_years(self):
        assert should_apply_gestation_correction(28, 1.5) is True

    def test_very_preterm_over_two_years(self):
        assert should_apply_gestation_correction(28, 2.5) is False

    def test_none_gestation_no_correction(self):
        assert should_apply_gestation_correction(None, 0.5) is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_calculations.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write calculations.py**

```python
"""Calculations — age, gestation correction. BSA/velocity/GH added in Phase 3."""
from datetime import date
from dateutil.relativedelta import relativedelta

from constants import PRETERM_THRESHOLD_WEEKS


def calculate_age_in_years(birth_date, measurement_date):
    """Calculate decimal age in years. Allows age=0 (same-day, e.g. birth weight)."""
    if measurement_date < birth_date:
        raise ValueError("Measurement date must not be before birth date.")
    return (measurement_date - birth_date).days / 365.25


def calculate_calendar_age(birth_date, measurement_date):
    """Calculate age as years, months, days dict."""
    delta = relativedelta(measurement_date, birth_date)
    return {
        "years": delta.years,
        "months": delta.months,
        "days": delta.days,
    }


def should_apply_gestation_correction(gestation_weeks, age_years):
    """Determine whether gestation correction should be applied.

    Correction applies when:
    - Gestation < 37 weeks AND
    - 32-36 weeks: until age 1 year
    - < 32 weeks: until age 2 years
    """
    if gestation_weeks is None or gestation_weeks >= PRETERM_THRESHOLD_WEEKS:
        return False
    if gestation_weeks >= 32:
        return age_years < 1.0
    return age_years < 2.0
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_calculations.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add calculations.py tests/test_calculations.py
git commit -m "feat: add calculations module with age and gestation correction"
```

---

### Task 5: Models Module

**Files:**
- Create: `models.py`
- Test: `tests/test_models.py`

This wraps the rcpchgrowth `Measurement` class. These tests hit the real library — they are integration tests by nature, not mocked.

- [ ] **Step 1: Write the test**

```python
"""Tests for models module — wraps rcpchgrowth Measurement."""
import pytest
from datetime import date
from models import create_measurement, validate_measurement_sds, extract_measurement_result


class TestCreateMeasurement:
    def test_height_measurement(self):
        result = create_measurement(
            sex="male",
            birth_date=date(2020, 1, 1),
            measurement_date=date(2023, 6, 15),
            measurement_method="height",
            observation_value=95.0,
            reference="uk-who",
        )
        assert result is not None
        calc = result["measurement_calculated_values"]
        assert calc["corrected_sds"] is not None
        assert calc["corrected_centile"] is not None

    def test_weight_measurement(self):
        result = create_measurement(
            sex="female",
            birth_date=date(2021, 3, 10),
            measurement_date=date(2023, 3, 10),
            measurement_method="weight",
            observation_value=12.0,
            reference="uk-who",
        )
        calc = result["measurement_calculated_values"]
        assert isinstance(calc["corrected_sds"], float)

    def test_ofc_measurement(self):
        result = create_measurement(
            sex="male",
            birth_date=date(2022, 6, 1),
            measurement_date=date(2023, 6, 1),
            measurement_method="ofc",
            observation_value=47.0,
            reference="uk-who",
        )
        calc = result["measurement_calculated_values"]
        assert calc["corrected_sds"] is not None

    def test_with_gestation(self):
        result = create_measurement(
            sex="female",
            birth_date=date(2022, 9, 1),
            measurement_date=date(2023, 3, 1),
            measurement_method="weight",
            observation_value=6.5,
            reference="uk-who",
            gestation_weeks=32,
            gestation_days=3,
        )
        dates = result["measurement_dates"]
        assert dates["chronological_decimal_age"] != dates["corrected_decimal_age"]


class TestValidateMeasurementSds:
    def test_normal_sds_no_warning(self):
        warnings = validate_measurement_sds(0.5, "weight")
        assert warnings == []

    def test_warning_threshold(self):
        warnings = validate_measurement_sds(4.5, "height")
        assert len(warnings) == 1
        assert "extreme" in warnings[0].lower()

    def test_hard_limit_raises(self):
        with pytest.raises(ValueError, match="exceeds acceptable range"):
            validate_measurement_sds(8.5, "weight")

    def test_bmi_higher_hard_limit(self):
        # BMI allows up to ±15 SDS
        warnings = validate_measurement_sds(10.0, "bmi")
        assert len(warnings) == 1  # warning but no rejection

    def test_bmi_hard_limit_raises(self):
        with pytest.raises(ValueError, match="exceeds acceptable range"):
            validate_measurement_sds(16.0, "bmi")

    def test_negative_sds_warning(self):
        warnings = validate_measurement_sds(-5.0, "height")
        assert len(warnings) == 1


class TestExtractMeasurementResult:
    def test_extracts_value_centile_sds(self):
        result = create_measurement(
            sex="male",
            birth_date=date(2020, 1, 1),
            measurement_date=date(2023, 6, 15),
            measurement_method="height",
            observation_value=95.0,
            reference="uk-who",
        )
        extracted = extract_measurement_result(result, 95.0)
        assert extracted["value"] == 95.0
        assert "centile" in extracted
        assert "sds" in extracted
        assert isinstance(extracted["centile"], float)
        assert isinstance(extracted["sds"], float)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_models.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write models.py**

```python
"""Wrapper around rcpchgrowth Measurement — never call the library directly from routes."""
from rcpchgrowth import Measurement

from constants import SDS_WARNING_LIMIT, SDS_HARD_LIMIT, BMI_SDS_HARD_LIMIT


def create_measurement(sex, birth_date, measurement_date, measurement_method,
                       observation_value, reference, gestation_weeks=0,
                       gestation_days=0):
    """Create an rcpchgrowth Measurement and return the result dict.

    rcpchgrowth treats gestation_weeks=0 as term (40 weeks).
    """
    m = Measurement(
        sex=sex,
        birth_date=birth_date,
        observation_date=measurement_date,
        measurement_method=measurement_method,
        observation_value=observation_value,
        reference=reference,
        gestation_weeks=gestation_weeks or 0,
        gestation_days=gestation_days or 0,
    )
    return m.measurement


def validate_measurement_sds(sds, measurement_method):
    """Check SDS against warning/hard limits. Returns list of warning strings.

    Raises ValueError if SDS exceeds hard limit.
    """
    if sds is None:
        return []

    hard_limit = BMI_SDS_HARD_LIMIT if measurement_method == "bmi" else SDS_HARD_LIMIT
    abs_sds = abs(sds)

    if abs_sds > hard_limit:
        raise ValueError(
            f"SDS ({sds:.1f}) exceeds acceptable range "
            f"(\u00b1{hard_limit} SDS). Please check measurement accuracy."
        )

    warnings = []
    if abs_sds > SDS_WARNING_LIMIT:
        warnings.append(
            f"SDS is very extreme ({sds:+.1f} SDS). "
            f"Please verify measurement accuracy."
        )
    return warnings


def extract_measurement_result(measurement_dict, observation_value):
    """Extract value, centile, and SDS from a Measurement result dict."""
    calc = measurement_dict["measurement_calculated_values"]
    return {
        "value": observation_value,
        "centile": calc["corrected_centile"],
        "sds": calc["corrected_sds"],
    }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_models.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add models.py tests/test_models.py
git commit -m "feat: add models module wrapping rcpchgrowth Measurement"
```

---

### Task 6: Utils Module

**Files:**
- Create: `utils.py`
- Test: `tests/test_utils.py`

Phase 1 scope: MPH calculation, norm_cdf, response formatting. Chart data helper is Phase 2.

- [ ] **Step 1: Write the test**

```python
"""Tests for utils module."""
import pytest
import math
from utils import (
    norm_cdf,
    calculate_mid_parental_height,
    format_error_response,
    format_success_response,
)


class TestNormCdf:
    def test_zero_gives_fifty_percent(self):
        assert abs(norm_cdf(0) - 50.0) < 0.01

    def test_positive_sds(self):
        result = norm_cdf(1.0)
        assert abs(result - 84.13) < 0.5

    def test_negative_sds(self):
        result = norm_cdf(-1.0)
        assert abs(result - 15.87) < 0.5

    def test_extreme_positive(self):
        result = norm_cdf(4.0)
        assert result > 99.99

    def test_extreme_negative(self):
        result = norm_cdf(-4.0)
        assert result < 0.01


class TestCalculateMidParentalHeight:
    def test_male_mph(self):
        result = calculate_mid_parental_height(165.0, 178.0, "male")
        # rcpchgrowth formula: (165 + 178 + 13) / 2 = 178.0
        # Algebraically equivalent to PRD formula: (165 + 178) / 2 + 6.5 = 178.0
        assert result["mid_parental_height"] == 178.0
        assert result["target_range_lower"] == 178.0 - 8.5
        assert result["target_range_upper"] == 178.0 + 8.5
        assert "mid_parental_height_sds" in result
        assert "mid_parental_height_centile" in result

    def test_female_mph(self):
        result = calculate_mid_parental_height(165.0, 178.0, "female")
        # rcpchgrowth: (165 + 178 - 13) / 2 = 165.0
        assert result["mid_parental_height"] == 165.0
        assert result["target_range_lower"] == 165.0 - 8.5
        assert result["target_range_upper"] == 165.0 + 8.5

    def test_returns_none_when_missing_maternal(self):
        assert calculate_mid_parental_height(None, 178.0, "male") is None

    def test_returns_none_when_missing_paternal(self):
        assert calculate_mid_parental_height(165.0, None, "male") is None

    def test_sds_and_centile_are_floats(self):
        result = calculate_mid_parental_height(165.0, 178.0, "male")
        assert isinstance(result["mid_parental_height_sds"], float)
        assert isinstance(result["mid_parental_height_centile"], float)
        assert 0 < result["mid_parental_height_centile"] < 100


class TestFormatErrorResponse:
    def test_structure(self):
        resp = format_error_response("Something went wrong", "ERR_001")
        assert resp["success"] is False
        assert resp["error"] == "Something went wrong"
        assert resp["error_code"] == "ERR_001"


class TestFormatSuccessResponse:
    def test_structure(self):
        results = {"age_years": 2.45}
        resp = format_success_response(results)
        assert resp["success"] is True
        assert resp["results"] == {"age_years": 2.45}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_utils.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write utils.py**

```python
"""Utility functions — MPH, norm_cdf, response formatting.

Chart data helper added in Phase 2.
"""
import math

from rcpchgrowth import mid_parental_height, mid_parental_height_z


def norm_cdf(z):
    """Convert a Z-score to a centile (0-100) using the normal CDF."""
    return (1.0 + math.erf(z / math.sqrt(2.0))) / 2.0 * 100.0


def calculate_mid_parental_height(maternal_height, paternal_height, sex):
    """Calculate mid-parental height with SDS, centile, and target range.

    Returns dict or None if either parent height is missing.
    Uses rcpchgrowth for MPH value (Tanner formula: (m+p+/-13)/2, algebraically
    equivalent to PRD formula (m+p)/2 +/- 6.5) and regression-based SDS.
    Target range: MPH +/- 8.5cm per PRD-02 section 6.2.
    """
    if maternal_height is None or paternal_height is None:
        return None

    maternal_height = float(maternal_height)
    paternal_height = float(paternal_height)

    mph = mid_parental_height(
        maternal_height=maternal_height,
        paternal_height=paternal_height,
        sex=sex,
    )
    mph_sds = mid_parental_height_z(
        maternal_height=maternal_height,
        paternal_height=paternal_height,
        reference="uk-who",
    )

    return {
        "mid_parental_height": round(mph, 1),
        "mid_parental_height_sds": round(mph_sds, 2),
        "mid_parental_height_centile": round(norm_cdf(mph_sds), 1),
        "target_range_lower": round(mph - 8.5, 1),
        "target_range_upper": round(mph + 8.5, 1),
    }


def format_error_response(message, error_code):
    return {
        "success": False,
        "error": message,
        "error_code": error_code,
    }


def format_success_response(results):
    return {
        "success": True,
        "results": results,
    }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_utils.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add utils.py tests/test_utils.py
git commit -m "feat: add utils module with MPH, norm_cdf, response formatting"
```

---

### Task 7: Flask App, Test Fixtures, and /calculate Endpoint

**Files:**
- Create: `tests/conftest.py`
- Create: `app.py`
- Create: `templates/index.html`
- Test: `tests/test_endpoints.py`

This is the core route that ties all backend modules together. We create conftest.py and app.py in the same task since conftest imports app.

- [ ] **Step 0: Write tests/conftest.py**

```python
"""Shared pytest fixtures."""
import pytest
import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def app():
    """Create Flask application for testing."""
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()
```

This is the core route that ties all backend modules together.

- [ ] **Step 1: Write the test**

```python
"""Tests for Flask endpoints."""
import pytest
import json


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"


class TestCalculateEndpoint:
    def test_basic_calculation(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
            "height": 96.0,
            "ofc": 50.0,
        }
        response = client.post(
            "/calculate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        results = data["results"]

        # Age
        assert abs(results["age_years"] - 3.0) < 0.02
        assert results["age_calendar"]["years"] == 3

        # Measurements present
        assert "weight" in results
        assert "height" in results
        assert "ofc" in results
        assert results["weight"]["value"] == 14.5
        assert isinstance(results["weight"]["sds"], float)
        assert isinstance(results["weight"]["centile"], float)

        # BMI auto-calculated
        assert "bmi" in results
        assert results["bmi"]["value"] > 0

    def test_weight_only(self, client):
        payload = {
            "sex": "female",
            "birth_date": "2021-01-01",
            "measurement_date": "2023-01-01",
            "weight": 12.0,
        }
        response = client.post(
            "/calculate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "weight" in data["results"]
        assert "bmi" not in data["results"]  # No height, so no BMI

    def test_missing_all_measurements(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-01-01",
            "measurement_date": "2023-01-01",
        }
        response = client.post(
            "/calculate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert data["error_code"] == "ERR_003"

    def test_missing_sex(self, client):
        payload = {
            "birth_date": "2020-01-01",
            "measurement_date": "2023-01-01",
            "weight": 14.0,
        }
        response = client.post(
            "/calculate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_invalid_date_format(self, client):
        payload = {
            "sex": "male",
            "birth_date": "15/06/2020",
            "measurement_date": "2023-06-15",
            "weight": 14.0,
        }
        response = client.post(
            "/calculate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["error_code"] == "ERR_001"

    def test_with_parental_heights(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "height": 96.0,
            "maternal_height": 165.0,
            "paternal_height": 178.0,
        }
        response = client.post(
            "/calculate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        mph = data["results"]["mid_parental_height"]
        assert mph["mid_parental_height"] == 178.0

    def test_with_gestation(self, client):
        payload = {
            "sex": "female",
            "birth_date": "2022-09-01",
            "measurement_date": "2023-03-01",
            "weight": 6.5,
            "gestation_weeks": 32,
            "gestation_days": 3,
        }
        response = client.post(
            "/calculate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        results = data["results"]
        assert results["gestation_correction_applied"] is True
        assert "corrected_age_years" in results

    def test_different_reference(self, client):
        payload = {
            "sex": "female",
            "birth_date": "2015-01-01",
            "measurement_date": "2023-01-01",
            "height": 120.0,
            "reference": "turners-syndrome",
        }
        response = client.post(
            "/calculate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200

    def test_measurement_before_birth_returns_error(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2023-06-15",
            "measurement_date": "2023-06-14",
            "weight": 3.5,
        }
        response = client.post(
            "/calculate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["error_code"] == "ERR_002"

    def test_empty_body_returns_error(self, client):
        response = client.post(
            "/calculate",
            data="{}",
            content_type="application/json",
        )
        assert response.status_code == 400


class TestIndexEndpoint:
    def test_serves_html(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert b"Growth Parameters Calculator" in response.data
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_endpoints.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: Create templates directory and minimal index.html**

Create `templates/index.html` with a minimal placeholder (full UI is Task 8):

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Growth Parameters Calculator</title>
</head>
<body>
    <h1>Growth Parameters Calculator</h1>
    <p>Loading...</p>
</body>
</html>
```

- [ ] **Step 4: Write app.py**

```python
"""Flask application — routes and orchestration."""
import os
import logging

from flask import Flask, render_template, request, jsonify

from constants import ErrorCodes, MAX_AGE_YEARS
from validation import (
    ValidationError,
    validate_date,
    validate_weight,
    validate_height,
    validate_ofc,
    validate_gestation,
    validate_sex,
    validate_reference,
    validate_at_least_one_measurement,
)
from calculations import (
    calculate_age_in_years,
    calculate_calendar_age,
    should_apply_gestation_correction,
)
from models import create_measurement, validate_measurement_sds, extract_measurement_result
from utils import calculate_mid_parental_height, format_error_response, format_success_response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200


@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify(format_error_response(
            "Request body must be valid JSON.", ErrorCodes.INVALID_INPUT
        )), 400

    try:
        # Validate required fields
        sex = validate_sex(data.get("sex"))
        birth_date = validate_date(data.get("birth_date"), "birth_date")
        measurement_date = validate_date(data.get("measurement_date"), "measurement_date")
        reference = validate_reference(data.get("reference"))

        # Validate optional measurements
        weight = validate_weight(data.get("weight"))
        height = validate_height(data.get("height"))
        ofc = validate_ofc(data.get("ofc"))
        validate_at_least_one_measurement(weight=weight, height=height, ofc=ofc)

        # Validate gestation
        gestation_result = validate_gestation(
            data.get("gestation_weeks"), data.get("gestation_days")
        )
        gestation_weeks = gestation_result[0] if gestation_result else 0
        gestation_days = gestation_result[1] if gestation_result else 0

        # Age calculation
        age_years = calculate_age_in_years(birth_date, measurement_date)
        if age_years > MAX_AGE_YEARS:
            raise ValidationError(
                f"Age ({age_years:.1f} years) exceeds maximum of {MAX_AGE_YEARS} years.",
                ErrorCodes.INVALID_DATE_RANGE,
            )
        age_calendar = calculate_calendar_age(birth_date, measurement_date)

        # Gestation correction
        correction_applied = should_apply_gestation_correction(
            gestation_weeks if gestation_weeks > 0 else None,
            age_years,
        )

        # Build results
        results = {
            "age_years": round(age_years, 4),
            "age_calendar": age_calendar,
            "gestation_correction_applied": correction_applied,
            "validation_messages": [],
        }

        # Add corrected age if applicable
        if correction_applied:
            # rcpchgrowth calculates corrected age internally — we get it from
            # the first measurement result below. For now, store the flag.
            pass

        # Process each measurement
        all_warnings = []
        for method, value in [("weight", weight), ("height", height), ("ofc", ofc)]:
            if value is None:
                continue
            measurement_result = create_measurement(
                sex=sex,
                birth_date=birth_date,
                measurement_date=measurement_date,
                measurement_method=method,
                observation_value=value,
                reference=reference,
                gestation_weeks=gestation_weeks,
                gestation_days=gestation_days,
            )
            extracted = extract_measurement_result(measurement_result, value)
            warnings = validate_measurement_sds(extracted["sds"], method)
            all_warnings.extend(warnings)
            results[method] = extracted

            # Extract corrected age from first measurement if correction applied
            if correction_applied and "corrected_age_years" not in results:
                dates = measurement_result["measurement_dates"]
                corrected_decimal = dates["corrected_decimal_age"]
                results["corrected_age_years"] = round(corrected_decimal, 4)
                # rcpchgrowth returns corrected_calendar_age as a string;
                # compute a dict to match our API contract (PRD-02 §8.1)
                from dateutil.relativedelta import relativedelta
                edd = birth_date + relativedelta(weeks=(40 - gestation_weeks), days=-gestation_days)
                results["corrected_age_calendar"] = calculate_calendar_age(edd, measurement_date)

        # Auto-calculate BMI when both weight and height are present
        if weight is not None and height is not None:
            bmi_value = round(weight / ((height / 100) ** 2), 1)
            bmi_result = create_measurement(
                sex=sex,
                birth_date=birth_date,
                measurement_date=measurement_date,
                measurement_method="bmi",
                observation_value=bmi_value,
                reference=reference,
                gestation_weeks=gestation_weeks,
                gestation_days=gestation_days,
            )
            bmi_extracted = extract_measurement_result(bmi_result, bmi_value)
            bmi_warnings = validate_measurement_sds(bmi_extracted["sds"], "bmi")
            all_warnings.extend(bmi_warnings)
            results["bmi"] = bmi_extracted

        # Mid-parental height
        mph = calculate_mid_parental_height(
            data.get("maternal_height"),
            data.get("paternal_height"),
            sex,
        )
        if mph:
            results["mid_parental_height"] = mph

        results["validation_messages"] = all_warnings

        logger.info("Calculation completed for %s", sex)
        return jsonify(format_success_response(results)), 200

    except ValidationError as e:
        return jsonify(format_error_response(e.message, e.code)), 400
    except ValueError as e:
        msg = str(e)
        # Distinguish date errors from SDS errors
        if "birth" in msg.lower() or "date" in msg.lower():
            code = ErrorCodes.INVALID_DATE_RANGE
        else:
            code = ErrorCodes.SDS_OUT_OF_RANGE
        return jsonify(format_error_response(msg, code)), 400
    except Exception as e:
        logger.error("Calculation error: %s", str(e))
        return jsonify(format_error_response(str(e), ErrorCodes.CALCULATION_ERROR)), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_endpoints.py -v
```

Expected: All PASS.

- [ ] **Step 6: Run the full backend suite**

```bash
pytest -v
```

Expected: All tests across all test files PASS.

- [ ] **Step 7: Commit**

```bash
git add app.py templates/index.html tests/conftest.py tests/test_endpoints.py
git commit -m "feat: add Flask app with /calculate endpoint, health check, index route"
```

---

### Task 8: HTML Template

**Files:**
- Modify: `templates/index.html`

Build the full SPA shell: disclaimer banner, form (sex, dates, measurements, parental heights), results area, error display. No charts section (Phase 2), no advanced-mode fields (Phase 3), no copy/export buttons (Phase 4).

- [ ] **Step 1: Replace templates/index.html with the full form**

Key structural requirements from PRD-05:
- Material Symbols icon font from Google Fonts CDN
- System font stack: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, ...`
- Container max-width 900px, centred
- Dismissible disclaimer banner at top
- Sex selection as styled radio buttons (44px touch targets)
- Date inputs for DOB and measurement date
- Number inputs for weight (kg), height (cm), OFC (cm)
- Number inputs for maternal height (cm) and paternal height (cm), labelled "(Optional)"
- Calculate and Reset buttons
- Hidden error display div (`.error`)
- Hidden results section (`.results`) with result cards grid
- Footer with disclaimer text
- All inputs have `id`, `name`, `aria-label`, and associated `<label>`
- Form `id="growthForm"`
- Inline validation error spans beneath each field

The HTML should be ~200-250 lines. Reference PRD-05 sections 3, 5, 7, 8, 10, 13, 14, 15 for exact layout, ARIA labels, and icon names.

Link `static/style.css`, `static/validation.js`, and `static/script.js`.

- [ ] **Step 2: Verify the template renders**

```bash
source venv/bin/activate
python -c "from app import app; client = app.test_client(); r = client.get('/'); print(r.status_code, 'growthForm' in r.data.decode())"
```

Expected: `200 True`

- [ ] **Step 3: Commit**

```bash
git add templates/index.html
git commit -m "feat: add full SPA HTML template with form and results layout"
```

---

### Task 9: CSS Stylesheet

**Files:**
- Create: `static/style.css`

Implement light mode only (dark mode is Phase 4). Reference PRD-05 sections 4.1, 5, 6, 7, 8, 9, 11, 12, 15 for exact values.

- [ ] **Step 1: Write static/style.css**

Must include:
- CSS custom properties (`:root` variables) from PRD-05 §4.1
- System font stack from PRD-05 §15.1
- Typography scale from PRD-05 §15.2
- Container: `max-width: 900px; margin: 0 auto; padding: 0 16px`
- Form grid: 2-column on desktop (>768px), single column on mobile
- Input styling from PRD-05 §5.1 (padding, border-radius, focus ring, 16px font to prevent iOS zoom)
- Radio button styling with 44px touch targets
- Primary button gradient from PRD-05 §6.1
- Secondary button from PRD-05 §6.2
- Results container from PRD-05 §7.1
- Result card grid from PRD-05 §7.2-7.3
- Error display from PRD-05 §8.1
- Warning display from PRD-05 §7.4
- Disclaimer banner from PRD-05 §13.3
- Spinner keyframes from PRD-05 §11.3
- Toast from PRD-05 §12.4
- Responsive breakpoints from PRD-05 §9.1 (480px, 768px)
- `prefers-reduced-motion` from PRD-05 §10.5
- `.show` utility class for toggling visibility

Target: ~300-400 lines.

- [ ] **Step 2: Verify CSS loads**

```bash
pytest tests/test_endpoints.py::TestIndexEndpoint -v
```

Expected: PASS (page still renders).

- [ ] **Step 3: Commit**

```bash
git add static/style.css
git commit -m "feat: add CSS stylesheet with light theme, responsive layout"
```

---

### Task 10: Client-Side Validation

**Files:**
- Create: `static/validation.js`
- Test: `tests/js/validation.test.js`

- [ ] **Step 1: Write the test**

Create `tests/js/validation.test.js`:

```javascript
const {
  validateDate,
  validateWeight,
  validateHeight,
  validateOfc,
  validateSex,
  validateAtLeastOneMeasurement,
} = require('../../static/validation');

describe('validateDate', () => {
  test('accepts valid YYYY-MM-DD', () => {
    expect(validateDate('2023-06-15')).toBeNull();
  });

  test('rejects empty string', () => {
    expect(validateDate('')).toBeTruthy();
  });

  test('rejects invalid format', () => {
    expect(validateDate('15/06/2023')).toBeTruthy();
  });

  test('rejects future date', () => {
    expect(validateDate('2099-01-01')).toBeTruthy();
  });
});

describe('validateWeight', () => {
  test('accepts valid weight', () => {
    expect(validateWeight('12.5')).toBeNull();
  });

  test('accepts empty (optional)', () => {
    expect(validateWeight('')).toBeNull();
  });

  test('rejects below minimum', () => {
    expect(validateWeight('0.05')).toBeTruthy();
  });

  test('rejects above maximum', () => {
    expect(validateWeight('301')).toBeTruthy();
  });

  test('rejects non-numeric', () => {
    expect(validateWeight('abc')).toBeTruthy();
  });
});

describe('validateHeight', () => {
  test('accepts valid height', () => {
    expect(validateHeight('95.0')).toBeNull();
  });

  test('accepts empty', () => {
    expect(validateHeight('')).toBeNull();
  });

  test('rejects below minimum', () => {
    expect(validateHeight('5')).toBeTruthy();
  });
});

describe('validateOfc', () => {
  test('accepts valid ofc', () => {
    expect(validateOfc('48.2')).toBeNull();
  });

  test('rejects above maximum', () => {
    expect(validateOfc('110')).toBeTruthy();
  });
});

describe('validateSex', () => {
  test('accepts male', () => {
    expect(validateSex('male')).toBeNull();
  });

  test('accepts female', () => {
    expect(validateSex('female')).toBeNull();
  });

  test('rejects empty', () => {
    expect(validateSex('')).toBeTruthy();
  });
});

describe('validateAtLeastOneMeasurement', () => {
  test('passes with weight', () => {
    expect(validateAtLeastOneMeasurement('12', '', '')).toBeNull();
  });

  test('fails with no measurements', () => {
    expect(validateAtLeastOneMeasurement('', '', '')).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
npm test -- tests/js/validation.test.js
```

Expected: FAIL — module not found.

- [ ] **Step 3: Write static/validation.js**

```javascript
/**
 * Client-side validation — for UX only. Server-side validation is authoritative.
 * Each function returns null if valid, or an error message string if invalid.
 */

function validateDate(value) {
  if (!value || typeof value !== 'string') return 'Date is required.';
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return 'Date must be in YYYY-MM-DD format.';
  const parsed = new Date(value + 'T00:00:00');
  if (isNaN(parsed.getTime())) return 'Invalid date.';
  if (parsed > new Date()) return 'Date cannot be in the future.';
  return null;
}

function validateNumericRange(value, min, max, name) {
  if (value === '' || value === null || value === undefined) return null;
  const num = parseFloat(value);
  if (isNaN(num)) return name + ' must be a number.';
  if (num < min || num > max) return name + ' must be between ' + min + ' and ' + max + '.';
  return null;
}

function validateWeight(value) {
  return validateNumericRange(value, 0.1, 300, 'Weight');
}

function validateHeight(value) {
  return validateNumericRange(value, 10, 250, 'Height');
}

function validateOfc(value) {
  return validateNumericRange(value, 10, 100, 'Head circumference');
}

function validateSex(value) {
  if (!value || (value !== 'male' && value !== 'female')) return 'Please select sex.';
  return null;
}

function validateAtLeastOneMeasurement(weight, height, ofc) {
  if ((!weight || weight === '') && (!height || height === '') && (!ofc || ofc === '')) {
    return 'At least one measurement is required.';
  }
  return null;
}

// Export for Node.js (Jest) — no-op in browser
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    validateDate,
    validateWeight,
    validateHeight,
    validateOfc,
    validateSex,
    validateAtLeastOneMeasurement,
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
npm test -- tests/js/validation.test.js
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add static/validation.js tests/js/validation.test.js
git commit -m "feat: add client-side validation with Jest tests"
```

---

### Task 11: Frontend Script

**Files:**
- Create: `static/script.js`

Phase 1 scope: form submission via fetch, results display, error display, disclaimer dismiss, form state persistence with localStorage, keyboard shortcut (Ctrl+Enter). No charts, no mode toggle, no copy/export, no previous measurements.

- [ ] **Step 1: Write static/script.js**

Must implement:

1. **`handleSubmit(event)`** — prevent default, gather form data into JSON, POST to `/calculate`, call `displayResults` or `showError`
2. **`displayResults(results)`** — show `.results` section, create result cards for age, weight, height, BMI, OFC, MPH (each only if present in response), show validation warnings
3. **`showError(message)`** — show `.error` div with message, hide results
4. **`clearError()`** — hide error div
5. **`dismissDisclaimer()`** — hide disclaimer, save to localStorage
6. **`saveFormState()`** — debounced, saves all form field values to localStorage key `growthCalculatorFormState`
7. **`restoreFormState()`** — on DOMContentLoaded, restore saved field values
8. **`resetForm()`** — clear all fields, clear localStorage, hide results/errors
9. **Keyboard shortcut** — Ctrl+Enter triggers form submit
10. **Event listeners** — form submit, reset button, disclaimer dismiss, input change (debounced save)

Key patterns from PRD-05/06:
- `document.getElementById('growthForm').addEventListener('submit', handleSubmit)`
- Use `fetch('/calculate', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) })`
- Result cards use `.result-item` class with `.result-label`, `.result-value`, `.result-sub` children
- Debounce: 500ms delay for auto-save
- Format centile with 1 decimal, SDS with 2 decimals and +/- sign
- Display age as "X years, Y months, Z days" from `age_calendar`

Target: ~250-300 lines.

- [ ] **Step 2: Manually test in browser**

```bash
source venv/bin/activate
python app.py
```

Open `http://localhost:8080` in a browser. Enter: Male, DOB 2020-06-15, measurement date 2023-06-15, weight 14.5, height 96.0. Click Calculate. Verify results appear with centiles and SDS values.

- [ ] **Step 3: Commit**

```bash
git add static/script.js
git commit -m "feat: add frontend script with form submission, results display, localStorage"
```

---

### Task 12: Integration Smoke Test

**Files:**
- Create: `tests/test_workflows.py`

End-to-end tests verifying the full request/response cycle with realistic clinical scenarios.

- [ ] **Step 1: Write the test**

```python
"""Integration tests — full clinical workflows."""
import json
import pytest


class TestTypicalWorkflow:
    """Realistic clinical scenarios."""

    def test_three_year_old_male_full_measurements(self, client):
        """Typical well-child check: 3-year-old boy, all measurements."""
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
            "height": 96.0,
            "ofc": 50.0,
            "maternal_height": 165.0,
            "paternal_height": 178.0,
        }
        response = client.post(
            "/calculate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        data = response.get_json()
        assert data["success"] is True
        r = data["results"]

        # All measurement types present
        for key in ["weight", "height", "ofc", "bmi", "mid_parental_height"]:
            assert key in r, f"Missing {key}"

        # BMI auto-calculated correctly
        expected_bmi = round(14.5 / (0.96 ** 2), 1)
        assert r["bmi"]["value"] == expected_bmi

        # MPH for male: (165 + 178) / 2 + 6.5 = 178.0
        assert r["mid_parental_height"]["mid_parental_height"] == 178.0

        # No warnings for normal values
        assert r["validation_messages"] == []

    def test_preterm_infant_with_gestation(self, client):
        """Preterm infant — should apply gestation correction."""
        payload = {
            "sex": "female",
            "birth_date": "2022-09-01",
            "measurement_date": "2023-03-01",
            "weight": 6.5,
            "gestation_weeks": 30,
            "gestation_days": 0,
        }
        response = client.post(
            "/calculate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        data = response.get_json()
        assert data["success"] is True
        assert data["results"]["gestation_correction_applied"] is True

    def test_turner_syndrome_female(self, client):
        """Turner syndrome — female-only, height-only reference."""
        payload = {
            "sex": "female",
            "birth_date": "2015-01-01",
            "measurement_date": "2023-01-01",
            "height": 115.0,
            "reference": "turners-syndrome",
        }
        response = client.post(
            "/calculate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        data = response.get_json()
        assert data["success"] is True
        assert "height" in data["results"]

    def test_height_only_no_bmi(self, client):
        """Only height provided — BMI should not be calculated."""
        payload = {
            "sex": "male",
            "birth_date": "2018-03-01",
            "measurement_date": "2023-03-01",
            "height": 110.0,
        }
        response = client.post(
            "/calculate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        data = response.get_json()
        assert data["success"] is True
        assert "bmi" not in data["results"]
        assert "height" in data["results"]
```

- [ ] **Step 2: Run the integration tests**

```bash
pytest tests/test_workflows.py -v
```

Expected: All PASS.

- [ ] **Step 3: Run the full test suite**

```bash
pytest -v && npm test
```

Expected: All backend and frontend tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_workflows.py
git commit -m "test: add integration workflow tests for clinical scenarios"
```

---

### Task 13: Final Verification

- [ ] **Step 1: Run full test suite with coverage**

```bash
pytest --cov=. --cov-report=term-missing -v
npm test -- --coverage
```

Verify backend coverage is reasonable (>80% on core modules).

- [ ] **Step 2: Start dev server and manually test**

```bash
python app.py
```

Open `http://localhost:8080`. Test:
1. Enter male, DOB 2020-06-15, measurement date 2023-06-15, weight 14.5, height 96.0, OFC 50.0
2. Click Calculate — results should appear with centiles/SDS
3. Add maternal height 165, paternal height 178, recalculate — MPH section should appear
4. Click Reset — form should clear, results should hide
5. Refresh page — form state should be restored from localStorage
6. Press Ctrl+Enter — should trigger calculate

- [ ] **Step 3: Commit any fixes**

If any issues found, fix and commit.

- [ ] **Step 4: Tag the milestone**

```bash
git tag v0.1.0-phase1-foundation
```
