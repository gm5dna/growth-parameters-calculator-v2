# Phase 3: Advanced Features — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add full clinical functionality — basic/advanced mode toggle, previous measurements with height velocity, bone age assessment, BSA, GH dose calculator, preterm gestation correction UI, reference selection, and BMI percentage of median.

**Architecture:** Mode toggle controls visibility of advanced-only sections via CSS class `.advanced-only`. Backend `calculations.py` extended with BSA (Boyd + cBNF), height velocity, and GH dose functions. The `/calculate` endpoint extended to accept `previous_measurements` and `bone_age_assessments` arrays, process them through rcpchgrowth, and return enriched results including velocity, BSA, GH dose, and BMI % median. Frontend adds collapsible table UIs for previous measurements and bone age, a GH dose adjuster widget, and plots historical data on charts.

**Tech Stack:** Existing Flask/rcpchgrowth backend, vanilla JS/CSS frontend, Chart.js 4.x

**Specs:** `spec/PRD_04_ADVANCED_FEATURES.md`

---

## Phase 3 Scope

**In scope:**
- Basic/Advanced mode toggle with localStorage persistence
- Gestation input fields (UI — backend already accepts gestation)
- Growth reference selector dropdown (UI — backend already accepts reference)
- BSA calculation (Boyd formula + cBNF lookup table)
- GH dose calculator (visibility, adjuster, 3 dose formats)
- Previous measurements table with add/delete/CSV import/export
- Previous measurements backend processing (SDS/centile per measurement)
- Height velocity calculation
- Bone age assessment table with add/delete
- Bone age backend processing (height-for-bone-age SDS/centile)
- BMI percentage of median in results
- Previous measurements on growth charts (scatter points)
- Bone age marker on height chart (diamond at bone_age, height)

**Deferred to Phase 4:**
- PDF export, clipboard copy, chart download
- Dark mode
- PWA/offline support

---

## File Map

| File | Responsibility | Action |
|------|---------------|--------|
| `calculations.py` | Add BSA (Boyd+cBNF), height velocity, GH dose | Modify |
| `app.py` | Extend `/calculate` for previous measurements, bone age, BSA, GH, BMI %median | Modify |
| `constants.py` | Add cBNF lookup table, GH standard dose, velocity minimum interval | Modify |
| `templates/index.html` | Add mode toggle, gestation, reference, previous measurements, bone age, GH sections | Modify |
| `static/style.css` | Add advanced-only, collapsible section, table, GH adjuster styles | Modify |
| `static/script.js` | Mode toggle logic, advanced form gathering, new result cards, previous measurements + bone age table management, GH dose adjuster, CSV import/export | Modify |
| `static/charts.js` | Plot previous measurements + bone age marker on charts | Modify |
| `tests/test_calculations.py` | BSA, velocity, GH dose tests | Modify |
| `tests/test_endpoints.py` | Extended /calculate tests | Modify |
| `tests/test_advanced_integration.py` | End-to-end advanced feature tests | Create |

---

### Task 1: Constants for Advanced Features

**Files:**
- Modify: `constants.py`
- Modify: `tests/test_constants.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_constants.py`:

```python
from constants import (
    CBNF_BSA_TABLE,
    GH_STANDARD_DOSE_MG_M2_WEEK,
    GH_DOSE_STEP_MG,
    VELOCITY_MIN_INTERVAL_DAYS,
    BONE_AGE_WINDOW_DAYS,
    VALID_BONE_AGE_STANDARDS,
)


def test_cbnf_bsa_table():
    assert isinstance(CBNF_BSA_TABLE, list)
    assert len(CBNF_BSA_TABLE) == 9
    # First entry: 1 kg -> 0.10 m²
    assert CBNF_BSA_TABLE[0] == (1, 0.10)
    # Last entry: 90 kg -> 2.2 m²
    assert CBNF_BSA_TABLE[-1] == (90, 2.2)


def test_gh_constants():
    assert GH_STANDARD_DOSE_MG_M2_WEEK == 7.0
    assert GH_DOSE_STEP_MG == 0.025


def test_velocity_constants():
    assert VELOCITY_MIN_INTERVAL_DAYS == 122  # ~4 months


def test_bone_age_constants():
    assert BONE_AGE_WINDOW_DAYS == 30.44  # ~1 month
    assert "gp" in VALID_BONE_AGE_STANDARDS
    assert "tw3" in VALID_BONE_AGE_STANDARDS
```

- [ ] **Step 2: Run test to verify it fails**

```bash
source venv/bin/activate && python -m pytest tests/test_constants.py -k "cbnf or gh_const or velocity_const or bone_age_const" -v
```

- [ ] **Step 3: Add constants to constants.py**

```python
# cBNF BSA lookup table: (weight_kg, bsa_m2)
CBNF_BSA_TABLE = [
    (1, 0.10),
    (2, 0.16),
    (5, 0.30),
    (10, 0.49),
    (20, 0.79),
    (30, 1.1),
    (50, 1.5),
    (70, 1.9),
    (90, 2.2),
]

# Growth hormone dosing
GH_STANDARD_DOSE_MG_M2_WEEK = 7.0
GH_DOSE_STEP_MG = 0.025

# Height velocity
VELOCITY_MIN_INTERVAL_DAYS = 122  # approximately 4 months

# Bone age
BONE_AGE_WINDOW_DAYS = 30.44  # approximately 1 month
VALID_BONE_AGE_STANDARDS = {"gp", "tw3"}
```

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add constants.py tests/test_constants.py
git commit -m "feat: add constants for BSA, GH dosing, velocity, bone age"
```

---

### Task 2: BSA Calculations

**Files:**
- Modify: `calculations.py`
- Modify: `tests/test_calculations.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_calculations.py`:

```python
from calculations import calculate_boyd_bsa, calculate_cbnf_bsa
import math


class TestCalculateBoydBsa:
    def test_typical_child(self):
        # 20 kg, 110 cm — expected ~0.78 m²
        bsa = calculate_boyd_bsa(20.0, 110.0)
        assert 0.7 < bsa < 0.9
        assert isinstance(bsa, float)

    def test_infant(self):
        # 3.5 kg, 50 cm
        bsa = calculate_boyd_bsa(3.5, 50.0)
        assert 0.1 < bsa < 0.3

    def test_adolescent(self):
        # 60 kg, 165 cm
        bsa = calculate_boyd_bsa(60.0, 165.0)
        assert 1.5 < bsa < 1.8

    def test_returns_two_decimal_places(self):
        bsa = calculate_boyd_bsa(20.0, 110.0)
        assert bsa == round(bsa, 2)


class TestCalculateCbnfBsa:
    def test_exact_table_value(self):
        assert calculate_cbnf_bsa(10.0) == 0.49

    def test_interpolation_between_values(self):
        # Between 10 kg (0.49) and 20 kg (0.79)
        # At 15 kg: 0.49 + (15-10)/(20-10) * (0.79-0.49) = 0.49 + 0.15 = 0.64
        bsa = calculate_cbnf_bsa(15.0)
        assert abs(bsa - 0.64) < 0.01

    def test_minimum_weight(self):
        bsa = calculate_cbnf_bsa(1.0)
        assert bsa == 0.10

    def test_below_minimum_clamps(self):
        bsa = calculate_cbnf_bsa(0.5)
        assert bsa == 0.10

    def test_above_maximum_extrapolates(self):
        # Above 90 kg — should still return a value
        bsa = calculate_cbnf_bsa(100.0)
        assert bsa > 2.2

    def test_returns_two_decimal_places(self):
        bsa = calculate_cbnf_bsa(15.0)
        assert bsa == round(bsa, 2)
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Write implementation**

Add to `calculations.py`:

```python
import math
from constants import CBNF_BSA_TABLE


def calculate_boyd_bsa(weight_kg, height_cm):
    """Calculate BSA using the Boyd formula.

    BSA = 0.0003207 × height^0.3 × weight_g^(0.7285 - 0.0188 × log10(weight_g))
    Used when both weight and height are available.
    """
    weight_g = weight_kg * 1000
    exponent = 0.7285 - 0.0188 * math.log10(weight_g)
    bsa = 0.0003207 * (height_cm ** 0.3) * (weight_g ** exponent)
    return round(bsa, 2)


def calculate_cbnf_bsa(weight_kg):
    """Calculate BSA using the cBNF lookup table with linear interpolation.

    Used when only weight is available (no height).
    """
    table = CBNF_BSA_TABLE

    # Clamp to minimum
    if weight_kg <= table[0][0]:
        return table[0][1]

    # Extrapolate above maximum
    if weight_kg >= table[-1][0]:
        w1, b1 = table[-2]
        w2, b2 = table[-1]
        slope = (b2 - b1) / (w2 - w1)
        return round(b2 + slope * (weight_kg - w2), 2)

    # Linear interpolation
    for i in range(len(table) - 1):
        w1, b1 = table[i]
        w2, b2 = table[i + 1]
        if w1 <= weight_kg <= w2:
            fraction = (weight_kg - w1) / (w2 - w1)
            return round(b1 + fraction * (b2 - b1), 2)

    return table[-1][1]  # fallback
```

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add calculations.py tests/test_calculations.py
git commit -m "feat: add BSA calculations (Boyd formula + cBNF lookup)"
```

---

### Task 3: Height Velocity and GH Dose Calculations

**Files:**
- Modify: `calculations.py`
- Modify: `tests/test_calculations.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_calculations.py`:

```python
from calculations import calculate_height_velocity, calculate_gh_dose


class TestCalculateHeightVelocity:
    def test_typical_velocity(self):
        # 6 cm growth over 365 days = 6.0 cm/year
        result = calculate_height_velocity(106.0, 100.0, 365)
        assert result["value"] is not None
        assert abs(result["value"] - 6.0) < 0.1
        assert result["message"] is None

    def test_interval_too_short(self):
        result = calculate_height_velocity(101.0, 100.0, 90)
        assert result["value"] is None
        assert "at least 4 months" in result["message"]

    def test_no_previous_height(self):
        result = calculate_height_velocity(100.0, None, 365)
        assert result["value"] is None
        assert "requires a previous height" in result["message"]

    def test_no_current_height(self):
        result = calculate_height_velocity(None, 100.0, 365)
        assert result["value"] is None

    def test_rounds_to_one_decimal(self):
        result = calculate_height_velocity(107.3, 100.0, 365)
        assert result["value"] == round(result["value"], 1)


class TestCalculateGhDose:
    def test_basic_dose_calculation(self):
        result = calculate_gh_dose(0.6, 0.58, 20.0)
        assert "mg_per_day" in result
        assert result["mg_per_day"] == 0.6
        assert "mg_per_week" in result
        assert abs(result["mg_per_week"] - 4.2) < 0.01
        assert "mg_m2_week" in result
        assert "mcg_kg_day" in result

    def test_mg_m2_week(self):
        # 0.6 mg/day * 7 / 0.58 m² = 7.24 mg/m²/week
        result = calculate_gh_dose(0.6, 0.58, 20.0)
        expected = (0.6 * 7) / 0.58
        assert abs(result["mg_m2_week"] - round(expected, 1)) < 0.2

    def test_mcg_kg_day(self):
        # (0.6 * 1000) / 20 = 30.0 mcg/kg/day
        result = calculate_gh_dose(0.6, None, 20.0)
        assert abs(result["mcg_kg_day"] - 30.0) < 0.1

    def test_no_bsa_omits_mg_m2(self):
        result = calculate_gh_dose(0.6, None, 20.0)
        assert result["mg_m2_week"] is None

    def test_initial_dose_from_bsa(self):
        result = calculate_gh_dose(None, 0.58, 20.0)
        # Standard: 7 mg/m²/week → daily = 7 * 0.58 / 7 = 0.58, rounded to 0.1
        assert result["initial_daily_dose"] == 0.6
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Write implementation**

Add to `calculations.py`:

```python
from constants import VELOCITY_MIN_INTERVAL_DAYS, GH_STANDARD_DOSE_MG_M2_WEEK


def calculate_height_velocity(current_height, previous_height, interval_days):
    """Calculate height velocity in cm/year.

    Returns dict with 'value' (float or None) and 'message' (str or None).
    """
    if current_height is None or previous_height is None:
        return {
            "value": None,
            "message": "Height velocity requires a previous height measurement." if previous_height is None and current_height is not None else None,
        }

    if interval_days < VELOCITY_MIN_INTERVAL_DAYS:
        months = round(interval_days / 30.44, 1)
        return {
            "value": None,
            "message": f"Height velocity requires at least 4 months between measurements (current interval: {months} months).",
        }

    height_diff = current_height - previous_height
    velocity = (height_diff / interval_days) * 365.25
    return {
        "value": round(velocity, 1),
        "message": None,
    }


def calculate_gh_dose(daily_dose_mg, bsa, weight_kg):
    """Calculate GH dose in multiple formats.

    If daily_dose_mg is None, calculates initial dose from standard (7 mg/m²/week).
    """
    result = {
        "mg_per_day": None,
        "mg_per_week": None,
        "mg_m2_week": None,
        "mcg_kg_day": None,
        "initial_daily_dose": None,
    }

    # Calculate initial dose if not provided
    if daily_dose_mg is None and bsa is not None:
        initial = (GH_STANDARD_DOSE_MG_M2_WEEK * bsa) / 7
        result["initial_daily_dose"] = round(initial, 1)
        return result

    if daily_dose_mg is None:
        return result

    result["mg_per_day"] = daily_dose_mg
    result["mg_per_week"] = round(daily_dose_mg * 7, 2)

    if bsa is not None:
        result["mg_m2_week"] = round((daily_dose_mg * 7) / bsa, 1)

    if weight_kg is not None:
        result["mcg_kg_day"] = round((daily_dose_mg * 1000) / weight_kg, 1)

    return result
```

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add calculations.py tests/test_calculations.py
git commit -m "feat: add height velocity and GH dose calculations"
```

---

### Task 4: Extend /calculate — Previous Measurements Processing

**Files:**
- Modify: `app.py`
- Modify: `tests/test_endpoints.py`

Extend the `/calculate` endpoint to accept and process `previous_measurements` array. For each previous measurement, calculate age and SDS/centile. Also calculate height velocity from the most recent valid previous height.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_endpoints.py`:

```python
class TestCalculateWithPreviousMeasurements:
    def test_previous_measurements_processed(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "height": 96.0,
            "previous_measurements": [
                {"date": "2022-12-15", "height": 91.0},
                {"date": "2022-06-15", "height": 86.0},
            ],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        prev = data["results"]["previous_measurements"]
        assert len(prev) == 2
        assert "age" in prev[0]
        assert "height" in prev[0]
        assert "centile" in prev[0]["height"]
        assert "sds" in prev[0]["height"]

    def test_height_velocity_calculated(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "height": 96.0,
            "previous_measurements": [
                {"date": "2022-06-15", "height": 88.0},
            ],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        velocity = data["results"]["height_velocity"]
        assert velocity["value"] is not None
        assert velocity["value"] > 0

    def test_velocity_interval_too_short(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "height": 96.0,
            "previous_measurements": [
                {"date": "2023-05-15", "height": 95.5},
            ],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        velocity = data["results"]["height_velocity"]
        assert velocity["value"] is None
        assert velocity["message"] is not None

    def test_no_previous_measurements_no_velocity(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "height": 96.0,
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        assert "height_velocity" not in data["results"] or data["results"].get("height_velocity") is None

    def test_previous_measurement_invalid_date_skipped(self, client):
        """Previous measurement with date after current measurement should be skipped."""
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "height": 96.0,
            "previous_measurements": [
                {"date": "2024-01-01", "height": 100.0},  # Future — skip
                {"date": "2022-06-15", "height": 88.0},   # Valid
            ],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        assert data["success"] is True
        prev = data["results"]["previous_measurements"]
        assert len(prev) == 1  # Only the valid one
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Write implementation**

In `app.py`, add processing of `previous_measurements` inside the `/calculate` route, after the existing measurement processing block. Import `calculate_height_velocity` from `calculations` and `validate_date` for date parsing.

The logic:
1. Extract `previous_measurements` list from request data (default empty list)
2. For each entry: parse date, validate it's before measurement_date, validate measurements
3. For each valid measurement in each entry, create an rcpchgrowth Measurement and extract SDS/centile
4. Calculate height velocity: filter previous heights with >4 month interval, use most recent valid one
5. Add `previous_measurements` and `height_velocity` to results

Key code pattern for processing each previous measurement:
```python
processed_prev = []
for entry in data.get("previous_measurements", []):
    try:
        prev_date = validate_date(entry.get("date"), "previous measurement date")
        if prev_date >= measurement_date:
            continue  # Skip future dates
        prev_age = calculate_age_in_years(birth_date, prev_date)
        prev_result = {"date": entry["date"], "age": round(prev_age, 4)}
        for method in ["height", "weight", "ofc"]:
            value = entry.get(method)
            if value is not None:
                value = float(value)
                m = create_measurement(
                    sex=sex, birth_date=birth_date, measurement_date=prev_date,
                    measurement_method=method, observation_value=value,
                    reference=reference, gestation_weeks=gestation_weeks,
                    gestation_days=gestation_days,
                )
                prev_result[method] = extract_measurement_result(m, value)
        processed_prev.append(prev_result)
    except (ValidationError, ValueError, Exception):
        continue  # Skip invalid entries silently

results["previous_measurements"] = processed_prev
```

For height velocity:
```python
if height is not None and processed_prev:
    valid_prev_heights = [
        p for p in processed_prev
        if "height" in p and (measurement_date - validate_date(p["date"], "d")).days >= VELOCITY_MIN_INTERVAL_DAYS
    ]
    valid_prev_heights.sort(key=lambda p: p["date"], reverse=True)
    if valid_prev_heights:
        most_recent = valid_prev_heights[0]
        interval = (measurement_date - datetime.strptime(most_recent["date"], "%Y-%m-%d").date()).days
        velocity = calculate_height_velocity(height, most_recent["height"]["value"], interval)
        velocity["based_on_date"] = most_recent["date"]
        results["height_velocity"] = velocity
    else:
        # Check if there are any previous heights at all (just with short interval)
        any_prev_heights = [p for p in processed_prev if "height" in p]
        if any_prev_heights:
            most_recent = sorted(any_prev_heights, key=lambda p: p["date"], reverse=True)[0]
            interval = (measurement_date - datetime.strptime(most_recent["date"], "%Y-%m-%d").date()).days
            velocity = calculate_height_velocity(height, most_recent["height"]["value"], interval)
            velocity["based_on_date"] = most_recent["date"]
            results["height_velocity"] = velocity
```

Also import `VELOCITY_MIN_INTERVAL_DAYS` from constants and `datetime` from the standard library.

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Run full suite**

```bash
python -m pytest -v
```

- [ ] **Step 6: Commit**

```bash
git add app.py tests/test_endpoints.py
git commit -m "feat: process previous measurements and height velocity in /calculate"
```

---

### Task 5: Extend /calculate — Bone Age Processing

**Files:**
- Modify: `app.py`
- Modify: `tests/test_endpoints.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_endpoints.py`:

```python
class TestCalculateWithBoneAge:
    def test_bone_age_processed(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2015-06-15",
            "measurement_date": "2023-06-15",
            "height": 125.0,
            "bone_age_assessments": [
                {"date": "2023-06-10", "bone_age": 7.5, "standard": "gp"},
            ],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
        data = response.get_json()
        ba = data["results"]["bone_age_height"]
        assert ba is not None
        assert ba["bone_age"] == 7.5
        assert ba["within_window"] is True
        assert "centile" in ba
        assert "sds" in ba

    def test_bone_age_outside_window(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2015-06-15",
            "measurement_date": "2023-06-15",
            "height": 125.0,
            "bone_age_assessments": [
                {"date": "2023-01-01", "bone_age": 7.0, "standard": "tw3"},
            ],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        ba = data["results"]["bone_age_height"]
        assert ba["within_window"] is False

    def test_bone_age_no_height(self, client):
        """Bone age without height — should not produce height-for-bone-age."""
        payload = {
            "sex": "male",
            "birth_date": "2015-06-15",
            "measurement_date": "2023-06-15",
            "weight": 25.0,
            "bone_age_assessments": [
                {"date": "2023-06-10", "bone_age": 7.5, "standard": "gp"},
            ],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        assert data["results"].get("bone_age_height") is None

    def test_no_bone_age(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2015-06-15",
            "measurement_date": "2023-06-15",
            "height": 125.0,
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        assert data["results"].get("bone_age_height") is None
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Write implementation**

Add bone age processing in `/calculate` route. Import `BONE_AGE_WINDOW_DAYS` from constants.

Logic:
1. Extract `bone_age_assessments` from request
2. For each assessment, check if `within_window` (date within ±30.44 days of measurement_date)
3. If height provided and a bone age is within window, calculate height-for-bone-age:
   - Create synthetic birth date: `measurement_date - timedelta(days=bone_age * 365.25)`
   - Create rcpchgrowth Measurement with synthetic birth date → get SDS/centile for height at bone age
4. Return `bone_age_height` with bone_age, assessment_date, standard, height, centile, sds, within_window
5. Return `bone_age_assessments` array (pass-through for frontend)

```python
bone_age_assessments = data.get("bone_age_assessments", [])
bone_age_result = None

if bone_age_assessments and height is not None:
    for ba in bone_age_assessments:
        try:
            ba_date = datetime.strptime(ba["date"], "%Y-%m-%d").date()
            ba_value = float(ba["bone_age"])
            ba_standard = ba.get("standard", "gp")
            days_diff = abs((measurement_date - ba_date).days)
            within_window = days_diff <= BONE_AGE_WINDOW_DAYS

            # Calculate height-for-bone-age using synthetic birth date
            from datetime import timedelta
            synthetic_birth = measurement_date - timedelta(days=ba_value * 365.25)
            ba_measurement = create_measurement(
                sex=sex, birth_date=synthetic_birth,
                measurement_date=measurement_date,
                measurement_method="height",
                observation_value=height,
                reference=reference,
            )
            ba_extracted = extract_measurement_result(ba_measurement, height)

            bone_age_result = {
                "bone_age": ba_value,
                "assessment_date": ba["date"],
                "standard": ba_standard,
                "height": height,
                "centile": ba_extracted["centile"],
                "sds": ba_extracted["sds"],
                "within_window": within_window,
            }
            break  # Use the first valid assessment
        except Exception:
            continue

results["bone_age_height"] = bone_age_result
results["bone_age_assessments"] = bone_age_assessments
```

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_endpoints.py
git commit -m "feat: process bone age assessments in /calculate"
```

---

### Task 6: Extend /calculate — BSA, GH Dose, BMI % Median

**Files:**
- Modify: `app.py`
- Modify: `tests/test_endpoints.py`

Wire BSA, GH dose initial calculation, and BMI percentage of median into the /calculate response.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_endpoints.py`:

```python
class TestCalculateAdvancedResults:
    def test_bsa_boyd_when_both_measurements(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
            "height": 96.0,
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        bsa = data["results"]["bsa"]
        assert bsa is not None
        assert bsa["value"] > 0
        assert bsa["method"] == "Boyd"

    def test_bsa_cbnf_weight_only(self, client):
        payload = {
            "sex": "female",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        bsa = data["results"]["bsa"]
        assert bsa is not None
        assert bsa["method"] == "cBNF"

    def test_no_bsa_without_weight(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "height": 96.0,
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        assert data["results"].get("bsa") is None

    def test_bmi_percentage_median(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
            "height": 96.0,
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        bmi = data["results"]["bmi"]
        assert "percentage_median" in bmi
        assert 50 < bmi["percentage_median"] < 200

    def test_gh_initial_dose(self, client):
        payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "weight": 14.5,
            "height": 96.0,
            "gh_treatment": True,
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        gh = data["results"].get("gh_dose")
        assert gh is not None
        assert gh["initial_daily_dose"] > 0
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Write implementation**

Add to the `/calculate` route in `app.py`, after the BMI block.

Import `calculate_boyd_bsa`, `calculate_cbnf_bsa`, `calculate_gh_dose` from `calculations`.

For BMI % median, use `rcpchgrowth.percentage_median_bmi`:
```python
from rcpchgrowth import percentage_median_bmi
```

BSA logic:
```python
bsa_result = None
bsa_value = None
if weight is not None:
    if height is not None:
        bsa_value = calculate_boyd_bsa(weight, height)
        bsa_result = {"value": bsa_value, "method": "Boyd"}
    else:
        bsa_value = calculate_cbnf_bsa(weight)
        bsa_result = {"value": bsa_value, "method": "cBNF"}
    results["bsa"] = bsa_result
```

BMI % median (add to the existing BMI block):
```python
# After bmi_extracted is created
try:
    pct_median = percentage_median_bmi(
        reference=reference,
        age=age_years,
        actual_bmi=bmi_value,
        sex=sex,
    )
    bmi_extracted["percentage_median"] = round(pct_median, 1)
except Exception:
    bmi_extracted["percentage_median"] = None
```

GH dose (only when `gh_treatment` flag is set):
```python
if data.get("gh_treatment") and bsa_value is not None:
    gh = calculate_gh_dose(None, bsa_value, weight)
    results["gh_dose"] = gh
```

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Run full suite**

```bash
python -m pytest -v
```

- [ ] **Step 6: Commit**

```bash
git add app.py tests/test_endpoints.py
git commit -m "feat: add BSA, GH dose, BMI % median to /calculate response"
```

---

### Task 7: Basic/Advanced Mode Toggle

**Files:**
- Modify: `templates/index.html`
- Modify: `static/style.css`
- Modify: `static/script.js`

Add the mode toggle switch in the header, `.advanced-only` CSS class, and JS toggle logic with localStorage persistence.

- [ ] **Step 1: Add toggle switch to index.html header**

Add after the `<h1>` in the header:
```html
<div class="mode-toggle-wrapper">
    <label class="mode-toggle" for="modeToggle">
        <span class="mode-label">Basic</span>
        <input type="checkbox" id="modeToggle" aria-label="Toggle advanced mode">
        <span class="toggle-slider"></span>
        <span class="mode-label">Advanced</span>
    </label>
</div>
```

- [ ] **Step 2: Add advanced-only sections to index.html**

Add these new form sections marked with `class="advanced-only"`:

1. **Reference selector** (after sex fieldset):
```html
<fieldset class="form-section advanced-only">
    <legend>Growth Reference</legend>
    <select id="reference" name="reference" aria-label="Growth reference">
        <option value="uk-who" selected>UK-WHO</option>
        <option value="turners-syndrome">Turner Syndrome</option>
        <option value="trisomy-21">Trisomy 21</option>
        <option value="cdc">CDC (US)</option>
    </select>
</fieldset>
```

2. **Gestation inputs** (after measurement date fields, inside the form-grid):
```html
<div class="form-field advanced-only">
    <label for="gestationWeeks">Gestation</label>
    <div class="gestation-inputs">
        <input type="number" id="gestationWeeks" name="gestation_weeks" min="22" max="44" step="1" placeholder="Weeks" aria-label="Gestation weeks">
        <span class="unit">wk</span>
        <span>+</span>
        <input type="number" id="gestationDays" name="gestation_days" min="0" max="6" step="1" placeholder="Days" aria-label="Gestation days">
        <span class="unit">d</span>
    </div>
    <span class="field-error" id="gestationError" role="alert"></span>
</div>
```

3. **GH treatment checkbox** (before parental heights):
```html
<fieldset class="form-section advanced-only">
    <label class="checkbox-label">
        <input type="checkbox" id="ghTreatment" name="gh_treatment">
        <span>Child is on growth hormone treatment</span>
    </label>
</fieldset>
```

- [ ] **Step 3: Add CSS for mode toggle and advanced-only**

```css
/* Mode toggle */
.mode-toggle-wrapper { display: flex; justify-content: flex-end; margin-bottom: 8px; }
.mode-toggle { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.mode-label { font-size: 13px; font-weight: 600; color: var(--text-secondary); }
.toggle-slider {
    width: 44px; height: 24px;
    background: var(--border-color);
    border-radius: 12px;
    position: relative;
    transition: background 0.2s;
}
.toggle-slider::after {
    content: '';
    position: absolute; top: 2px; left: 2px;
    width: 20px; height: 20px;
    background: white; border-radius: 50%;
    transition: transform 0.2s;
}
#modeToggle { display: none; }
#modeToggle:checked + .toggle-slider { background: var(--accent-primary); }
#modeToggle:checked + .toggle-slider::after { transform: translateX(20px); }

/* Advanced-only sections hidden in basic mode */
body:not(.advanced-mode) .advanced-only { display: none; }

/* Gestation inputs */
.gestation-inputs { display: flex; align-items: center; gap: 6px; }
.gestation-inputs input { width: 70px; }

/* Checkbox label */
.checkbox-label { display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 14px; }
.checkbox-label input[type="checkbox"] { width: 18px; height: 18px; }
```

- [ ] **Step 4: Add JS toggle logic to script.js**

Add mode toggle handling:
```javascript
function handleModeToggle() {
    var toggle = document.getElementById('modeToggle');
    if (toggle.checked) {
        document.body.classList.add('advanced-mode');
    } else {
        document.body.classList.remove('advanced-mode');
    }
    debouncedSave();
}
```

In DOMContentLoaded, add:
```javascript
var modeToggle = document.getElementById('modeToggle');
if (modeToggle) modeToggle.addEventListener('change', handleModeToggle);
```

Update `saveFormState` to include mode, gestation, reference, ghTreatment.
Update `restoreFormState` to restore them.
Update `resetForm` to remove `advanced-mode` class and uncheck toggle.
Update `gatherFormData` to include gestation_weeks, gestation_days, reference, gh_treatment.
Update `resetForm` to also: hide `#ghCalculator`, reset `currentGhDose = 0`, `currentBsa = null`, `currentWeightKg = null`, collapse any expanded collapsible sections.

- [ ] **Step 5: Verify**

```bash
node --check static/script.js
python -m pytest tests/test_endpoints.py::TestIndexEndpoint -v
```

- [ ] **Step 6: Commit**

```bash
git add templates/index.html static/style.css static/script.js
git commit -m "feat: add basic/advanced mode toggle with gestation, reference, GH checkbox"
```

---

### Task 8: Previous Measurements Frontend

**Files:**
- Modify: `templates/index.html`
- Modify: `static/style.css`
- Modify: `static/script.js`

Add collapsible previous measurements table with add/delete rows and CSV import/export.

- [ ] **Step 1: Add HTML for previous measurements section**

Add as `class="form-section advanced-only"` before the parental heights fieldset:

```html
<fieldset class="form-section advanced-only collapsible-section" id="prevMeasurementsSection">
    <div class="collapsible-header" id="prevMeasurementsToggle">
        <span class="material-symbols-outlined" aria-hidden="true">add</span>
        <span>Add Previous Measurement</span>
    </div>
    <div class="collapsible-content" id="prevMeasurementsContent" hidden>
        <div class="collapsible-title-row">
            <legend>Previous Measurements <span class="optional">(Optional)</span></legend>
            <button type="button" class="btn-icon collapsible-close" aria-label="Close section">
                <span class="material-symbols-outlined" aria-hidden="true">close</span>
            </button>
        </div>
        <table class="data-table" id="prevMeasurementsTable">
            <thead>
                <tr>
                    <th>Date</th><th>Height (cm)</th><th>Weight (kg)</th><th>OFC (cm)</th><th></th>
                </tr>
            </thead>
            <tbody id="prevMeasurementsBody"></tbody>
        </table>
        <div class="table-actions">
            <button type="button" class="btn-small" id="addPrevMeasurement">
                <span class="material-symbols-outlined" aria-hidden="true">add</span> Add Another
            </button>
            <button type="button" class="btn-small" id="importCsvBtn">
                <span class="material-symbols-outlined" aria-hidden="true">upload</span> Import CSV
            </button>
            <button type="button" class="btn-small" id="exportCsvBtn">
                <span class="material-symbols-outlined" aria-hidden="true">download</span> Export CSV
            </button>
            <input type="file" id="csvFileInput" accept=".csv" hidden>
        </div>
    </div>
</fieldset>
```

- [ ] **Step 2: Add table and collapsible CSS**

```css
/* Collapsible sections */
.collapsible-header {
    display: flex; align-items: center; gap: 8px;
    padding: 12px; cursor: pointer; color: var(--accent-primary);
    font-weight: 600; font-size: 14px;
}
.collapsible-header:hover { opacity: 0.8; }
.collapsible-title-row { display: flex; justify-content: space-between; align-items: center; }
.collapsible-title-row legend { margin-bottom: 12px; }
.collapsible-close { flex-shrink: 0; }

/* Data tables */
.data-table { width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 12px; }
.data-table th { text-align: left; padding: 8px; border-bottom: 2px solid var(--border-color); font-weight: 600; font-size: 12px; text-transform: uppercase; color: var(--text-secondary); }
.data-table td { padding: 6px 8px; border-bottom: 1px solid var(--border-color); }
.data-table input { padding: 6px 8px; font-size: 14px; border: 1px solid var(--border-color); border-radius: 4px; width: 100%; }
.data-table .btn-delete { background: none; border: none; cursor: pointer; color: var(--error-color); padding: 4px; }

.table-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.btn-small { display: inline-flex; align-items: center; gap: 4px; padding: 6px 12px; font-size: 13px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-primary); cursor: pointer; }
.btn-small:hover { background: var(--bg-secondary); }
```

- [ ] **Step 3: Add JS for previous measurements table management**

Add to `script.js`:

- `addPrevMeasurementRow()` — append a new empty row to `#prevMeasurementsBody`
- `deletePrevMeasurementRow(button)` — remove the row
- `getPreviousMeasurements()` — read all rows, return array of `{date, height, weight, ofc}` (skip empty rows)
- `importCsv(file)` — parse CSV, populate table rows
- `exportCsv()` — generate CSV from table, trigger download
- Toggle handler: clicking `#prevMeasurementsToggle` shows/hides `#prevMeasurementsContent` and adds first row if empty
- Update `gatherFormData` to include `previous_measurements: getPreviousMeasurements()`
- Update `saveFormState`/`restoreFormState` to include previous measurements
- Update `resetForm` to clear the table

Each row HTML:
```javascript
'<tr>' +
'<td><input type="date" class="prev-date"></td>' +
'<td><input type="number" class="prev-height" step="0.1" min="10" max="250"></td>' +
'<td><input type="number" class="prev-weight" step="0.01" min="0.1" max="300"></td>' +
'<td><input type="number" class="prev-ofc" step="0.1" min="10" max="100"></td>' +
'<td><button type="button" class="btn-delete" onclick="deletePrevMeasurementRow(this)" aria-label="Delete row"><span class="material-symbols-outlined">delete</span></button></td>' +
'</tr>'
```

- [ ] **Step 4: Verify**

```bash
node --check static/script.js
python -m pytest tests/test_endpoints.py::TestIndexEndpoint -v
```

- [ ] **Step 5: Commit**

```bash
git add templates/index.html static/style.css static/script.js
git commit -m "feat: add previous measurements table with CSV import/export"
```

---

### Task 9: Bone Age Frontend

**Files:**
- Modify: `templates/index.html`
- Modify: `static/script.js`

Add collapsible bone age assessment table.

- [ ] **Step 1: Add HTML for bone age section**

Add as `class="form-section advanced-only collapsible-section"` after previous measurements:

```html
<fieldset class="form-section advanced-only collapsible-section" id="boneAgeSection">
    <div class="collapsible-header" id="boneAgeToggle">
        <span class="material-symbols-outlined" aria-hidden="true">add</span>
        <span>Add Bone Age Assessment</span>
    </div>
    <div class="collapsible-content" id="boneAgeContent" hidden>
        <div class="collapsible-title-row">
            <legend>Bone Age Assessments <span class="optional">(Optional)</span></legend>
            <button type="button" class="btn-icon collapsible-close" aria-label="Close section">
                <span class="material-symbols-outlined" aria-hidden="true">close</span>
            </button>
        </div>
        <table class="data-table" id="boneAgeTable">
            <thead>
                <tr><th>Assessment Date</th><th>Bone Age (years)</th><th>Standard</th><th></th></tr>
            </thead>
            <tbody id="boneAgeBody"></tbody>
        </table>
        <div class="table-actions">
            <button type="button" class="btn-small" id="addBoneAge">
                <span class="material-symbols-outlined" aria-hidden="true">add</span> Add Another
            </button>
        </div>
    </div>
</fieldset>
```

- [ ] **Step 2: Add JS for bone age table management**

Similar pattern to previous measurements:
- `addBoneAgeRow()` — add row with date input, bone age number input, standard dropdown (gp/tw3), delete button
- `deleteBoneAgeRow(button)` — remove row
- `getBoneAgeAssessments()` — read rows, return `[{date, bone_age, standard}]`
- Toggle handler for expand/collapse
- Update `gatherFormData` to include `bone_age_assessments: getBoneAgeAssessments()`
- Update save/restore/reset for bone age data

Each row:
```javascript
'<tr>' +
'<td><input type="date" class="ba-date"></td>' +
'<td><input type="number" class="ba-age" step="0.1" min="0" max="20"></td>' +
'<td><select class="ba-standard"><option value="gp">Greulich-Pyle</option><option value="tw3">TW3</option></select></td>' +
'<td><button type="button" class="btn-delete" onclick="deleteBoneAgeRow(this)" aria-label="Delete row"><span class="material-symbols-outlined">delete</span></button></td>' +
'</tr>'
```

- [ ] **Step 3: Commit**

```bash
git add templates/index.html static/script.js
git commit -m "feat: add bone age assessment table UI"
```

---

### Task 10: GH Dose Calculator Frontend + Results Display Updates

**Files:**
- Modify: `templates/index.html`
- Modify: `static/style.css`
- Modify: `static/script.js`

Add the GH dose adjuster widget in the results area. Also update `displayResults` to show BSA, height velocity, bone age, GH dose, and BMI % median.

- [ ] **Step 1: Add GH dose calculator HTML**

Add inside `#resultsSection`, after the results grid:

```html
<div class="gh-calculator advanced-only" id="ghCalculator" hidden>
    <h3>Growth Hormone Dose Calculator</h3>
    <div class="gh-adjuster">
        <label>Daily Dose:</label>
        <button type="button" class="btn-small" id="ghDecrease" aria-label="Decrease dose">-</button>
        <span id="ghDoseValue">0.0</span> mg/day
        <button type="button" class="btn-small" id="ghIncrease" aria-label="Increase dose">+</button>
    </div>
    <div class="gh-results" id="ghResults"></div>
</div>
```

- [ ] **Step 2: Add GH calculator CSS**

```css
.gh-calculator { margin-top: 16px; padding: 16px; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; }
.gh-calculator h3 { margin: 0 0 12px; font-size: 16px; }
.gh-adjuster { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.gh-adjuster .btn-small { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: 700; }
#ghDoseValue { font-size: 20px; font-weight: 700; min-width: 40px; text-align: center; }
.gh-results { font-size: 14px; color: var(--text-secondary); }
.gh-results div { margin-bottom: 4px; }
```

- [ ] **Step 3: Update displayResults in script.js**

Extend `displayResults` to render new result cards:

**BSA card** (if `results.bsa` present):
```javascript
if (results.bsa) {
    resultsGrid.appendChild(createResultCard(
        'BODY SURFACE AREA',
        results.bsa.value + ' m\u00B2',
        ['Method: ' + results.bsa.method]
    ));
}
```

**Height velocity card** (if `results.height_velocity` present):
```javascript
if (results.height_velocity && results.height_velocity.value !== null) {
    var velSubs = [];
    if (results.height_velocity.based_on_date) {
        velSubs.push('Based on measurement from ' + results.height_velocity.based_on_date);
    }
    resultsGrid.appendChild(createResultCard(
        'HEIGHT VELOCITY',
        results.height_velocity.value + ' cm/year',
        velSubs
    ));
} else if (results.height_velocity && results.height_velocity.message) {
    // Show message as a note, not a card
}
```

**BMI % median** (extend existing BMI card):
```javascript
// In the BMI card creation, add:
if (meas.percentage_median !== null && meas.percentage_median !== undefined) {
    subs.push('% Median: ' + meas.percentage_median.toFixed(1) + '%');
}
```

**Bone age card** (if `results.bone_age_height` present):
```javascript
if (results.bone_age_height) {
    var ba = results.bone_age_height;
    var subs = [
        'Standard: ' + (ba.standard === 'gp' ? 'Greulich-Pyle' : 'TW3'),
        'Height for bone age centile: ' + formatCentile(ba.centile),
        'Height for bone age SDS: ' + formatSds(ba.sds),
    ];
    if (!ba.within_window) subs.push('Outside ±1 month window');
    resultsGrid.appendChild(createResultCard(
        'BONE AGE',
        ba.bone_age + ' years',
        subs
    ));
}
```

**GH dose calculator** (if `results.gh_dose` present):
```javascript
if (results.gh_dose && results.gh_dose.initial_daily_dose !== null) {
    var ghCalc = document.getElementById('ghCalculator');
    if (ghCalc) {
        ghCalc.hidden = false;
        currentGhDose = results.gh_dose.initial_daily_dose;
        updateGhDisplay();
    }
}
```

- [ ] **Step 4: Add GH dose adjuster JS**

```javascript
var currentGhDose = 0;
var currentBsa = null;
var currentWeightKg = null;

function updateGhDisplay() {
    document.getElementById('ghDoseValue').textContent = currentGhDose.toFixed(1);
    var resultsDiv = document.getElementById('ghResults');
    var mgWeek = (currentGhDose * 7).toFixed(1);
    var lines = [];
    if (currentBsa) lines.push('= ' + ((currentGhDose * 7) / currentBsa).toFixed(1) + ' mg/m\u00B2/week');
    if (currentWeightKg) lines.push('= ' + ((currentGhDose * 1000) / currentWeightKg).toFixed(1) + ' mcg/kg/day');
    resultsDiv.innerHTML = lines.map(function(l) { return '<div>' + l + '</div>'; }).join('');
}

// Wire up +/- buttons INSIDE the existing DOMContentLoaded handler:
var ghIncBtn = document.getElementById('ghIncrease');
var ghDecBtn = document.getElementById('ghDecrease');
if (ghIncBtn) ghIncBtn.addEventListener('click', function() {
    currentGhDose = Math.round((currentGhDose + 0.025) * 1000) / 1000;
    updateGhDisplay();
});
if (ghDecBtn) ghDecBtn.addEventListener('click', function() {
    currentGhDose = Math.max(0, Math.round((currentGhDose - 0.025) * 1000) / 1000;
    updateGhDisplay();
});
```

Store BSA and weight when displaying results:
```javascript
if (results.bsa) currentBsa = results.bsa.value;
if (lastPayload && lastPayload.weight) currentWeightKg = lastPayload.weight;
```

- [ ] **Step 5: Commit**

```bash
git add templates/index.html static/style.css static/script.js
git commit -m "feat: add GH dose calculator UI and advanced result cards"
```

---

### Task 11: Previous Measurements on Charts

**Files:**
- Modify: `static/charts.js`

Plot previous measurement data points on charts as smaller, muted scatter points.

- [ ] **Step 1: Add previous measurements to chart rendering**

In `charts.js`, modify `renderChart` (or the dataset-building flow):

```javascript
function getPreviousMeasurementPoints(chartType) {
    if (!lastResults || !lastResults.previous_measurements) return [];
    return lastResults.previous_measurements
        .filter(function(pm) { return pm[chartType] && pm[chartType].value !== undefined; })
        .map(function(pm) { return { x: pm.age, y: pm[chartType].value }; });
}
```

Add a scatter dataset after the current measurement point:
```javascript
var prevPoints = getPreviousMeasurementPoints(chartType);
if (prevPoints.length > 0) {
    datasets.push({
        type: 'scatter',
        label: 'Previous measurements',
        data: prevPoints,
        pointRadius: 6,
        pointBackgroundColor: '#9ca3af',
        pointBorderColor: '#ffffff',
        pointBorderWidth: 1,
        pointHoverRadius: 8,
    });
}
```

- [ ] **Step 2: Add bone age marker on height chart**

```javascript
function getBoneAgePoint() {
    if (!lastResults || !lastResults.bone_age_height) return null;
    var ba = lastResults.bone_age_height;
    if (!ba.within_window || !ba.height) return null;
    return { x: ba.bone_age, y: ba.height };
}
```

Add diamond-shaped scatter dataset (only on height chart):
```javascript
if (chartType === 'height') {
    var baPoint = getBoneAgePoint();
    if (baPoint) {
        datasets.push({
            type: 'scatter',
            label: 'Bone age',
            data: [baPoint],
            pointRadius: 8,
            pointBackgroundColor: '#f59e0b',
            pointBorderColor: '#ffffff',
            pointBorderWidth: 2,
            pointStyle: 'rectRot',  // Diamond shape
            pointHoverRadius: 10,
        });
    }
}
```

- [ ] **Step 3: Update tooltip to handle previous measurement points**

Extend the tooltip filter and label callback to also show data for previous measurement and bone age points.

- [ ] **Step 4: Commit**

```bash
git add static/charts.js
git commit -m "feat: plot previous measurements and bone age marker on charts"
```

---

### Task 12: Integration Tests and Final Verification

**Files:**
- Create: `tests/test_advanced_integration.py`

- [ ] **Step 1: Write integration tests**

```python
"""Integration tests for advanced clinical features."""
import json
import pytest


class TestAdvancedFeatures:
    def test_full_advanced_workflow(self, client):
        """Complete advanced calculation: all measurements, previous, bone age, GH."""
        payload = {
            "sex": "male",
            "birth_date": "2015-06-15",
            "measurement_date": "2023-06-15",
            "weight": 25.0,
            "height": 125.0,
            "ofc": 52.0,
            "maternal_height": 165.0,
            "paternal_height": 178.0,
            "reference": "uk-who",
            "gh_treatment": True,
            "previous_measurements": [
                {"date": "2022-06-15", "height": 118.0, "weight": 22.0},
                {"date": "2021-06-15", "height": 111.0},
            ],
            "bone_age_assessments": [
                {"date": "2023-06-10", "bone_age": 7.5, "standard": "gp"},
            ],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        assert data["success"] is True
        r = data["results"]

        # Core results
        assert "weight" in r
        assert "height" in r
        assert "bmi" in r
        assert "ofc" in r
        assert "mid_parental_height" in r

        # BSA
        assert r["bsa"]["method"] == "Boyd"
        assert r["bsa"]["value"] > 0

        # BMI % median
        assert r["bmi"]["percentage_median"] is not None

        # Previous measurements
        assert len(r["previous_measurements"]) == 2
        assert "height" in r["previous_measurements"][0]

        # Height velocity
        assert r["height_velocity"]["value"] is not None

        # Bone age
        assert r["bone_age_height"]["within_window"] is True
        assert r["bone_age_height"]["centile"] is not None

        # GH dose
        assert r["gh_dose"]["initial_daily_dose"] > 0

    def test_bsa_cbnf_fallback(self, client):
        """Weight only — should use cBNF for BSA."""
        payload = {
            "sex": "female",
            "birth_date": "2020-01-01",
            "measurement_date": "2023-01-01",
            "weight": 14.0,
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        assert data["results"]["bsa"]["method"] == "cBNF"

    def test_trisomy_21_with_previous(self, client):
        """Trisomy 21 reference with previous measurements."""
        payload = {
            "sex": "male",
            "birth_date": "2018-01-01",
            "measurement_date": "2023-01-01",
            "height": 100.0,
            "reference": "trisomy-21",
            "previous_measurements": [
                {"date": "2022-01-01", "height": 93.0},
            ],
        }
        response = client.post("/calculate", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        assert data["success"] is True
        assert len(data["results"]["previous_measurements"]) == 1
        assert data["results"]["height_velocity"]["value"] is not None
```

- [ ] **Step 2: Run integration tests**

```bash
python -m pytest tests/test_advanced_integration.py -v
```

- [ ] **Step 3: Run full suite**

```bash
python -m pytest -v && npx jest
```

- [ ] **Step 4: Commit**

```bash
git add tests/test_advanced_integration.py
git commit -m "test: add advanced features integration tests"
```

- [ ] **Step 5: Manual browser verification**

Start dev server and test:
1. Toggle to Advanced mode — gestation, reference, previous measurements, bone age sections appear
2. Select Turner Syndrome reference
3. Add gestation 34+3
4. Add 2 previous measurements
5. Add bone age assessment
6. Check GH treatment box
7. Calculate — verify all result cards: BSA, velocity, bone age, GH dose, BMI %median
8. Show charts — verify previous measurement dots and bone age diamond marker
9. Toggle back to Basic mode — advanced sections hide
10. Reset — everything clears
