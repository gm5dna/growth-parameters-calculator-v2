# Phase 2: Visualisation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add interactive growth charts — four chart types (height, weight, BMI, OFC) with centile curves, current measurement plotting, age range selection with intelligent defaults, and mid-parental height display on height charts.

**Architecture:** Backend `POST /chart-data` endpoint calls rcpchgrowth `create_chart()` and flattens its multi-segment output into a simple `[{centile, sds, data: [{x, y}]}]` array. Frontend `static/charts.js` fetches and caches this data, renders via Chart.js 4.x (CDN), handles tab switching, age range filtering, measurement point overlay, and MPH annotation. Chart section added to `index.html` below results, toggled via "Show Growth Charts" button.

**Tech Stack:** Chart.js 4.x (CDN), chartjs-plugin-annotation (CDN, for MPH display), existing Flask/rcpchgrowth backend

**Specs:** `spec/PRD_03_GROWTH_CHARTS.md`

---

## Phase 2 Scope

**In scope:**
- `/chart-data` POST endpoint returning flattened centile curve data
- All four chart types: height, weight, BMI, OFC
- 9 centile curves (0.4th–99.6th) with graduated styling
- Current measurement point plotting
- Tab interface to switch chart type
- Age range selection with intelligent defaults (per PRD-03 §4.1)
- MPH horizontal line + target range on height chart
- Chart data caching (fetch once per reference/method/sex combo)
- Responsive canvas resize

**Deferred:**
- Previous measurements plotting → Phase 3
- Bone age plotting → Phase 3
- Chart PNG download → Phase 4
- Dark mode chart colours → Phase 4

---

## File Map

| File | Responsibility | New/Modify |
|------|---------------|------------|
| `utils.py` | Add `get_chart_data()` — flatten rcpchgrowth `create_chart()` output | Modify |
| `app.py` | Add `POST /chart-data` route | Modify |
| `templates/index.html` | Add chart section (button, tabs, age range radios, canvas) + Chart.js CDN | Modify |
| `static/style.css` | Add chart section styles (tabs, canvas container, age range) | Modify |
| `static/charts.js` | All chart logic: fetch, cache, render, tabs, age range, measurement plotting, MPH | Create |
| `static/script.js` | Hook chart rendering after successful calculation | Modify |
| `tests/test_utils.py` | Add tests for `get_chart_data()` | Modify |
| `tests/test_endpoints.py` | Add tests for `/chart-data` endpoint | Modify |
| `tests/test_chart_integration.py` | End-to-end chart data workflow tests | Create |

---

### Task 1: Backend get_chart_data Function

**Files:**
- Modify: `utils.py`
- Modify: `tests/test_utils.py`

The rcpchgrowth `create_chart()` returns a list of segment dicts. Each segment has a nested structure: `segment_name → sex → measurement_method → [centile_lines]`. UK-WHO has 4 segments (preterm, infant, child, uk90_child); Turner and Trisomy-21 have 1 segment; CDC has 3 segments (fenton, infant, child). We must flatten these into a unified list of 9 centile lines with merged data points.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_utils.py`:

```python
from utils import get_chart_data


class TestGetChartData:
    def test_uk_who_height_male(self):
        result = get_chart_data("uk-who", "height", "male")
        assert isinstance(result, list)
        assert len(result) == 9  # cole-nine-centiles
        # Check centile values present
        centile_values = [line["centile"] for line in result]
        assert 0.4 in centile_values
        assert 50 in centile_values or 50.0 in centile_values
        assert 99.6 in centile_values

    def test_centile_line_structure(self):
        result = get_chart_data("uk-who", "height", "male")
        line = result[0]
        assert "centile" in line
        assert "sds" in line
        assert "data" in line
        assert isinstance(line["data"], list)
        assert len(line["data"]) > 0

    def test_data_point_structure(self):
        result = get_chart_data("uk-who", "height", "male")
        point = result[0]["data"][0]
        assert "x" in point
        assert "y" in point
        assert isinstance(point["x"], (int, float))
        assert isinstance(point["y"], (int, float))

    def test_data_points_span_full_age_range(self):
        result = get_chart_data("uk-who", "height", "male")
        median = [line for line in result if line["centile"] == 50][0]
        x_values = [p["x"] for p in median["data"]]
        assert min(x_values) < 0  # preterm data starts before 0
        assert max(x_values) >= 20  # goes to 20 years

    def test_no_none_y_values(self):
        result = get_chart_data("uk-who", "height", "male")
        for line in result:
            for point in line["data"]:
                assert point["y"] is not None

    def test_data_sorted_by_age(self):
        result = get_chart_data("uk-who", "height", "male")
        for line in result:
            x_values = [p["x"] for p in line["data"]]
            assert x_values == sorted(x_values)

    def test_turner_syndrome(self):
        result = get_chart_data("turners-syndrome", "height", "female")
        assert len(result) == 9
        assert len(result[0]["data"]) > 0

    def test_trisomy_21(self):
        result = get_chart_data("trisomy-21", "height", "male")
        assert len(result) == 9

    def test_cdc_weight(self):
        result = get_chart_data("cdc", "weight", "male")
        assert len(result) == 9

    def test_weight_method(self):
        result = get_chart_data("uk-who", "weight", "female")
        assert len(result) == 9

    def test_bmi_method(self):
        result = get_chart_data("uk-who", "bmi", "male")
        assert len(result) == 9

    def test_ofc_method(self):
        result = get_chart_data("uk-who", "ofc", "female")
        assert len(result) == 9
```

- [ ] **Step 2: Run test to verify it fails**

```bash
source venv/bin/activate
python -m pytest tests/test_utils.py::TestGetChartData -v
```

Expected: FAIL — `ImportError: cannot import name 'get_chart_data'`

- [ ] **Step 3: Write the implementation**

Add to `utils.py`:

```python
from rcpchgrowth import create_chart


def get_chart_data(reference, measurement_method, sex):
    """Fetch centile curve data from rcpchgrowth and flatten into a simple list.

    rcpchgrowth create_chart() returns a list of segment dicts. Each segment
    has structure: {segment_name: {sex: {method: [centile_lines]}}}. UK-WHO
    has 4 segments; other references have 1-3. We merge data points from
    matching centile lines across all segments into a unified flat list.

    Returns:
        list of dicts: [{centile, sds, data: [{x, y}]}, ...] — 9 centile lines
    """
    raw = create_chart(
        reference=reference,
        centile_format="cole-nine-centiles",
        measurement_method=measurement_method,
        sex=sex,
    )

    # Collect centile lines from all segments, keyed by centile value
    merged = {}  # centile_value -> {centile, sds, data: []}

    for segment in raw:
        for segment_name, sex_data in segment.items():
            if sex not in sex_data:
                continue
            method_data = sex_data[sex]
            if measurement_method not in method_data:
                continue
            centile_lines = method_data[measurement_method]

            for line in centile_lines:
                centile_val = line["centile"]
                if centile_val not in merged:
                    merged[centile_val] = {
                        "centile": centile_val,
                        "sds": round(float(line["sds"]), 2),
                        "data": [],
                    }
                if not line.get("data"):
                    continue  # Some segments return data=None (e.g. BMI preterm)
                for point in line["data"]:
                    if point["y"] is not None:
                        merged[centile_val]["data"].append({
                            "x": round(float(point["x"]), 4),
                            "y": round(float(point["y"]), 4),
                        })

    # Sort each centile's data by age (x), then sort centile lines by centile value
    result = []
    for centile_val in sorted(merged.keys()):
        entry = merged[centile_val]
        entry["data"].sort(key=lambda p: p["x"])
        result.append(entry)

    return result
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_utils.py::TestGetChartData -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add utils.py tests/test_utils.py
git commit -m "feat: add get_chart_data function to flatten rcpchgrowth centile curves"
```

---

### Task 2: Backend /chart-data Endpoint

**Files:**
- Modify: `app.py`
- Modify: `tests/test_endpoints.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_endpoints.py`:

```python
class TestChartDataEndpoint:
    def test_basic_chart_data(self, client):
        payload = {
            "reference": "uk-who",
            "measurement_method": "height",
            "sex": "male",
        }
        response = client.post(
            "/chart-data",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "centiles" in data
        assert len(data["centiles"]) == 9

    def test_chart_data_centile_structure(self, client):
        payload = {"reference": "uk-who", "measurement_method": "weight", "sex": "female"}
        response = client.post("/chart-data", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        centile_line = data["centiles"][0]
        assert "centile" in centile_line
        assert "sds" in centile_line
        assert "data" in centile_line
        assert len(centile_line["data"]) > 0
        point = centile_line["data"][0]
        assert "x" in point
        assert "y" in point

    def test_chart_data_missing_sex(self, client):
        payload = {"reference": "uk-who", "measurement_method": "height"}
        response = client.post("/chart-data", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400

    def test_chart_data_missing_method(self, client):
        payload = {"reference": "uk-who", "sex": "male"}
        response = client.post("/chart-data", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400

    def test_chart_data_invalid_reference(self, client):
        payload = {"reference": "invalid", "measurement_method": "height", "sex": "male"}
        response = client.post("/chart-data", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400

    def test_chart_data_defaults_reference(self, client):
        payload = {"measurement_method": "height", "sex": "male"}
        response = client.post("/chart-data", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200

    def test_chart_data_bmi(self, client):
        payload = {"reference": "uk-who", "measurement_method": "bmi", "sex": "female"}
        response = client.post("/chart-data", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
        assert len(response.get_json()["centiles"]) == 9

    def test_chart_data_ofc(self, client):
        payload = {"reference": "uk-who", "measurement_method": "ofc", "sex": "male"}
        response = client.post("/chart-data", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_endpoints.py::TestChartDataEndpoint -v
```

Expected: FAIL — 404 (route doesn't exist yet).

- [ ] **Step 3: Write the implementation**

Add to `app.py`, after the `/calculate` route. Also add `get_chart_data` to the utils import and add `VALID_MEASUREMENT_METHODS` to the constants import:

```python
@app.route("/chart-data", methods=["POST"])
def chart_data():
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify(format_error_response(
            "Request body must be valid JSON.", ErrorCodes.INVALID_INPUT
        )), 400

    try:
        sex = validate_sex(data.get("sex"))
        reference = validate_reference(data.get("reference"))

        measurement_method = data.get("measurement_method")
        if not measurement_method or measurement_method not in VALID_MEASUREMENT_METHODS:
            raise ValidationError(
                f"measurement_method must be one of: {', '.join(sorted(VALID_MEASUREMENT_METHODS))}.",
                ErrorCodes.INVALID_INPUT,
            )

        centiles = get_chart_data(reference, measurement_method, sex)

        return jsonify({"success": True, "centiles": centiles}), 200

    except ValidationError as e:
        return jsonify(format_error_response(e.message, e.code)), 400
    except Exception as e:
        logger.error("Chart data error: %s", str(e))
        return jsonify(format_error_response(str(e), ErrorCodes.CALCULATION_ERROR)), 400
```

Update the imports at the top of `app.py`:
- Add `VALID_MEASUREMENT_METHODS` to the `from constants import` line
- Add `get_chart_data` to the `from utils import` line

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_endpoints.py::TestChartDataEndpoint -v
```

Expected: All PASS.

- [ ] **Step 5: Run full backend suite**

```bash
python -m pytest -v
```

Expected: All tests PASS (existing + new).

- [ ] **Step 6: Commit**

```bash
git add app.py tests/test_endpoints.py
git commit -m "feat: add /chart-data endpoint for centile curve data"
```

---

### Task 3: HTML Chart Section and Chart CSS

**Files:**
- Modify: `templates/index.html`
- Modify: `static/style.css`

Add the chart UI elements to the HTML and the corresponding styles. No JS logic yet.

- [ ] **Step 1: Add Chart.js CDN to index.html**

Add at the bottom of `<body>`, **before** the existing `validation.js` script tag (so Chart.js loads before our scripts but doesn't block HTML parsing):

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3/dist/chartjs-plugin-annotation.min.js"></script>
```

- [ ] **Step 2: Add chart section to index.html**

Insert after the `</section>` closing tag of `resultsSection`, before the toast div:

```html
<!-- Show Charts button (appears after calculation) -->
<button type="button" class="btn-show-charts" id="showChartsBtn" hidden>
    <span class="material-symbols-outlined" aria-hidden="true">show_chart</span>
    Show Growth Charts
</button>

<!-- Charts section -->
<section class="charts-section" id="chartsSection" hidden>
    <div class="charts-header">
        <h2>Growth Charts</h2>
        <button type="button" class="btn-icon" id="closeChartsBtn" aria-label="Close charts">
            <span class="material-symbols-outlined" aria-hidden="true">close</span>
        </button>
    </div>

    <!-- Chart type tabs -->
    <div class="chart-tabs" role="tablist" aria-label="Chart type">
        <button type="button" class="chart-tab active" role="tab" data-chart="height" aria-selected="true">Height</button>
        <button type="button" class="chart-tab" role="tab" data-chart="weight" aria-selected="false">Weight</button>
        <button type="button" class="chart-tab" role="tab" data-chart="bmi" aria-selected="false">BMI</button>
        <button type="button" class="chart-tab" role="tab" data-chart="ofc" aria-selected="false">OFC</button>
    </div>

    <!-- Age range selector -->
    <div class="age-range-selector" id="ageRangeSelector" role="radiogroup" aria-label="Age range">
        <!-- Populated dynamically by charts.js -->
    </div>

    <!-- Chart loading indicator -->
    <div class="chart-loading" id="chartLoading" hidden>
        <div class="spinner"></div>
        <p>Loading chart data...</p>
    </div>

    <!-- Chart canvas -->
    <div class="chart-container">
        <canvas id="growthChart" aria-label="Growth chart" role="img"></canvas>
    </div>

    <!-- Screen reader description -->
    <div id="chartDescription" class="sr-only" aria-live="polite"></div>
</section>
```

- [ ] **Step 3: Add charts.js script tag**

Add before the closing `</body>`, after `script.js`:

```html
<script src="{{ url_for('static', filename='charts.js') }}"></script>
```

- [ ] **Step 4: Add chart CSS to style.css**

Append to `static/style.css`:

```css
/* ================================================================ */
/*  Charts                                                          */
/* ================================================================ */

.btn-show-charts {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 24px auto 0;
  padding: 12px 24px;
  background: var(--bg-primary);
  border: 1px solid var(--accent-primary);
  color: var(--accent-primary);
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.btn-show-charts:hover {
  background: var(--accent-primary);
  color: #fff;
}

.charts-section {
  background: var(--bg-primary);
  border-radius: 12px;
  padding: 24px;
  margin-top: 24px;
  border: 1px solid var(--border-color);
}

.charts-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.charts-header h2 { margin: 0; }

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  color: var(--text-secondary);
  transition: background 0.15s;
}

.btn-icon:hover { background: var(--bg-secondary); }

/* Chart type tabs */
.chart-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  border-bottom: 2px solid var(--border-color);
  padding-bottom: 0;
}

.chart-tab {
  padding: 10px 20px;
  background: none;
  border: none;
  border-bottom: 3px solid transparent;
  margin-bottom: -2px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}

.chart-tab:hover { color: var(--text-primary); }

.chart-tab.active {
  color: var(--accent-primary);
  border-bottom-color: var(--accent-primary);
}

/* Age range selector */
.age-range-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.age-range-selector label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: 1px solid var(--border-color);
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.age-range-selector label:has(input:checked) {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
  color: #fff;
}

.age-range-selector input[type="radio"] {
  display: none;
}

/* Chart container */
.chart-container {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 10;
  min-height: 300px;
}

.chart-container canvas {
  width: 100% !important;
  height: 100% !important;
}

/* Chart loading */
.chart-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 0;
  color: var(--text-secondary);
}

.chart-loading .spinner {
  width: 32px;
  height: 32px;
  border-width: 3px;
  border-color: var(--border-color);
  border-top-color: var(--accent-primary);
  margin-bottom: 12px;
}

/* Screen reader only */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* Responsive */
@media (max-width: 480px) {
  .chart-tabs { overflow-x: auto; }
  .chart-tab { padding: 8px 14px; font-size: 13px; }
  .chart-container { aspect-ratio: 4 / 3; min-height: 250px; }
}
```

- [ ] **Step 5: Verify template still renders**

```bash
python -m pytest tests/test_endpoints.py::TestIndexEndpoint -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add templates/index.html static/style.css
git commit -m "feat: add chart section HTML and CSS with tabs, age range, canvas"
```

---

### Task 4: charts.js — Data Fetching, Caching, and Core Rendering

**Files:**
- Create: `static/charts.js`

This is the main chart module. This task covers: fetching chart data from `/chart-data`, caching it, and rendering centile curves on a Chart.js canvas with correct styling.

- [ ] **Step 1: Create static/charts.js**

Must implement:

1. **Chart data cache** — object keyed by `"${reference}|${method}|${sex}"`, stores centile arrays
2. **`fetchChartData(reference, method, sex)`** — checks cache, fetches from `/chart-data` if not cached, returns centile array
3. **`renderChart(centiles, ageRange, measurement, chartType)`** — creates/updates Chart.js instance with:
   - 9 line datasets for centile curves with graduated styling per PRD-03 §3.2:
     - 0.4th, 99.6th: 1px line, 20% opacity of `#6b7280`
     - 2nd, 9th, 91st, 98th: 1px line, 40% opacity
     - 25th, 75th: 1.5px line, 60% opacity
     - 50th: 2px line, 100% opacity, colour `#1e40af`
   - Centile curve labels on the right side of chart (use Chart.js annotation or custom plugin)
   - X-axis: Age (years), Y-axis: measurement unit (cm, kg, kg/m², cm)
   - Data filtered to selected age range
   - No animation on data update (only on initial render)
4. **`destroyChart()`** — destroy existing Chart.js instance to prevent memory leaks
5. **`filterDataToRange(centiles, minAge, maxAge)`** — filter data points to selected age range

Centile line styling configuration:

```javascript
const CENTILE_STYLES = {
  0.4:  { width: 1,   opacity: 0.2  },
  2:    { width: 1,   opacity: 0.4  },
  9:    { width: 1,   opacity: 0.4  },
  25:   { width: 1.5, opacity: 0.6  },
  50:   { width: 2,   opacity: 1.0  },
  75:   { width: 1.5, opacity: 0.6  },
  91:   { width: 1,   opacity: 0.4  },
  98:   { width: 1,   opacity: 0.4  },
  99.6: { width: 1,   opacity: 0.2  },
};
```

Chart.js line colour: use `rgba(107, 114, 128, opacity)` for all lines except 50th which uses `#1e40af`.

Y-axis label per chart type:

```javascript
const Y_AXIS_LABELS = {
  height: 'Height / Length (cm)',
  weight: 'Weight (kg)',
  bmi: 'BMI (kg/m²)',
  ofc: 'Head Circumference (cm)',
};
```

Chart.js config essentials:
- `type: 'line'`
- `options.responsive: true`
- `options.maintainAspectRatio: false`
- `options.scales.x.type: 'linear'`, title "Age (years)"
- `options.scales.y.type: 'linear'`
- `options.plugins.legend.display: false` (we use custom centile labels instead)
- `options.plugins.tooltip.enabled: false` (tooltip only for measurement points, handled in Task 6)
- `options.elements.point.radius: 0` (no points on centile curves)
- Datasets: `tension: 0.4` for smooth curves, `fill: false`

- [ ] **Step 2: Verify no JS syntax errors**

```bash
node --check static/charts.js
```

Expected: No output (no syntax errors).

- [ ] **Step 3: Commit**

```bash
git add static/charts.js
git commit -m "feat: add charts.js with data fetching, caching, and centile curve rendering"
```

---

### Task 5: Chart Tabs, Age Range Selection, and Intelligent Defaults

**Files:**
- Modify: `static/charts.js`
- Modify: `static/script.js`

Wire up the UI: chart tab switching, age range radio buttons, intelligent default selection, and the show/close chart buttons.

- [ ] **Step 1: Add age range configuration to charts.js**

```javascript
const AGE_RANGES = {
  height: [
    { label: '0–2 years', min: -0.5, max: 2 },
    { label: '0–4 years', min: -0.5, max: 4 },
    { label: '0–18 years', min: -0.5, max: 18 },
    { label: '2–18 years', min: 2, max: 18 },
    { label: '8–20 years', min: 8, max: 20 },
  ],
  weight: [
    { label: '0–2 years', min: -0.5, max: 2 },
    { label: '0–4 years', min: -0.5, max: 4 },
    { label: '0–18 years', min: -0.5, max: 18 },
    { label: '8–20 years', min: 8, max: 20 },
  ],
  bmi: [
    { label: '0–4 years', min: -0.5, max: 4 },
    { label: '2–18 years', min: 2, max: 18 },
    { label: '0–18 years', min: -0.5, max: 18 },
  ],
  ofc: [
    { label: '0–2 years', min: -0.5, max: 2 },
    { label: '0–18 years', min: -0.5, max: 18 },
  ],
};
```

- [ ] **Step 2: Add intelligent default selection function**

```javascript
function getDefaultAgeRange(chartType, ageYears, hasParentalHeights) {
  // Per PRD-03 §4.1
  switch (chartType) {
    case 'height':
      if (ageYears < 2) return 0;       // 0-2
      if (ageYears < 4) return 1;       // 0-4
      return hasParentalHeights ? 3 : 2; // 2-18 or 0-18
    case 'weight':
      if (ageYears < 2) return 0;
      if (ageYears < 4) return 1;
      return 2;                          // 0-18
    case 'bmi':
      if (ageYears < 4) return 0;       // 0-4
      if (ageYears < 10) return 1;      // 2-18
      return 2;                          // 0-18 (per PRD-03 §4.1)
    case 'ofc':
      if (ageYears < 2) return 0;       // 0-2
      return 1;                          // 0-18
    default:
      return 0;
  }
}
```

- [ ] **Step 3: Add tab switching and age range rendering**

Functions needed in `charts.js`:
- **`initChartControls()`** — attach click listeners to `.chart-tab` buttons and `#closeChartsBtn`
- **`switchChartType(chartType)`** — update active tab, rebuild age range radios, select default, trigger re-render
- **`renderAgeRangeSelector(chartType)`** — populate `#ageRangeSelector` with radio buttons for the chart type's available ranges, attach change listeners
- **`onAgeRangeChange()`** — re-render chart with new range

- [ ] **Step 4: Hook chart display into script.js**

Add to `static/script.js` in the `displayResults` function, after showing the results section:

```javascript
// Show "Show Growth Charts" button
const showChartsBtn = document.getElementById('showChartsBtn');
if (showChartsBtn) showChartsBtn.removeAttribute('hidden');
```

Store the latest results and payload as `var` (not `let`) so they are accessible from `charts.js` which loads as a separate `<script>` tag in the same page:

```javascript
// At top of script.js, after STORAGE_KEY — use var for cross-script access
var lastResults = null;
var lastPayload = null;
```

In `displayResults`, before the return:
```javascript
lastResults = results;
lastPayload = gatherFormData();
```

In `resetForm`, clear them:
```javascript
lastResults = null;
lastPayload = null;
// Hide chart section
const chartsSection = document.getElementById('chartsSection');
if (chartsSection) chartsSection.setAttribute('hidden', '');
const showChartsBtn = document.getElementById('showChartsBtn');
if (showChartsBtn) showChartsBtn.setAttribute('hidden', '');
```

Export `lastResults` and `lastPayload` for charts.js access.

- [ ] **Step 5: Add showCharts entry point in charts.js**

```javascript
async function showCharts() {
  const chartsSection = document.getElementById('chartsSection');
  const showChartsBtn = document.getElementById('showChartsBtn');
  if (chartsSection) chartsSection.removeAttribute('hidden');
  if (showChartsBtn) showChartsBtn.setAttribute('hidden', '');

  // Get context from script.js
  const reference = lastPayload?.reference || 'uk-who';
  const sex = lastPayload?.sex;
  const ageYears = lastResults?.age_years || 0;
  const hasParentalHeights = !!lastResults?.mid_parental_height;

  // Default to height chart
  switchChartType('height');
  chartsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
```

Attach event listeners on DOMContentLoaded:
```javascript
document.addEventListener('DOMContentLoaded', function() {
  initChartControls();
  const showChartsBtn = document.getElementById('showChartsBtn');
  if (showChartsBtn) showChartsBtn.addEventListener('click', showCharts);
});
```

- [ ] **Step 6: Verify manually**

```bash
source venv/bin/activate
python app.py
```

Open browser, enter a calculation, click "Show Growth Charts". Verify:
- Charts section appears with tabs
- Age range radios appear
- Centile curves render on the canvas

- [ ] **Step 7: Commit**

```bash
git add static/charts.js static/script.js
git commit -m "feat: add chart tabs, age range selection with intelligent defaults"
```

---

### Task 6: Measurement Plotting and MPH Display

**Files:**
- Modify: `static/charts.js`

Add the current measurement point as a scatter overlay on the chart, and display MPH line + target range on the height chart.

- [ ] **Step 1: Add measurement point to chart**

Function `getMeasurementPoint(chartType, results)`:
- Returns `{x: ageYears, y: value}` or null if the measurement type isn't in results
- Uses corrected age if gestation correction was applied
- Maps chartType to results key: `height→height.value`, `weight→weight.value`, `bmi→bmi.value`, `ofc→ofc.value`

Add a scatter dataset to the Chart.js config in `renderChart`:
```javascript
{
  type: 'scatter',
  label: 'Current measurement',
  data: [point],
  pointRadius: 8,
  pointBackgroundColor: '#2563eb',
  pointBorderColor: '#ffffff',
  pointBorderWidth: 2,
  pointHoverRadius: 10,
}
```

- [ ] **Step 2: Add MPH display on height chart**

Only displayed when:
- `chartType === 'height'`
- `lastResults.mid_parental_height` exists
- Age range includes adult height (max >= 18)

Use the chartjs-plugin-annotation to draw:
1. A dashed horizontal line at MPH value from x=17 to x=20
2. A shaded box from target_range_lower to target_range_upper, same x range

Annotation config:
```javascript
options.plugins.annotation = {
  annotations: {
    mphLine: {
      type: 'line',
      yMin: mph.mid_parental_height,
      yMax: mph.mid_parental_height,
      xMin: 17,
      xMax: 20,
      borderColor: 'rgba(124, 58, 237, 0.8)',
      borderWidth: 2,
      borderDash: [6, 4],
      label: {
        display: true,
        content: 'MPH: ' + mph.mid_parental_height + ' cm',
        position: 'start',
        font: { size: 11 },
        backgroundColor: 'rgba(124, 58, 237, 0.1)',
        color: '#7c3aed',
      },
    },
    mphRange: {
      type: 'box',
      xMin: 17,
      xMax: 20,
      yMin: mph.target_range_lower,
      yMax: mph.target_range_upper,
      backgroundColor: 'rgba(124, 58, 237, 0.08)',
      borderWidth: 0,
    },
  },
};
```

- [ ] **Step 3: Add tooltip for measurement point**

Add a units map and a display name map at the top of charts.js:

```javascript
const CHART_UNITS = { height: 'cm', weight: 'kg', bmi: 'kg/m\u00B2', ofc: 'cm' };
const CHART_DISPLAY_NAMES = { height: 'Height', weight: 'Weight', bmi: 'BMI', ofc: 'Head Circumference' };
```

Enable Chart.js tooltip only for the scatter dataset (measurement point):
```javascript
options.plugins.tooltip = {
  enabled: true,
  filter: function(tooltipItem) {
    return tooltipItem.dataset.type === 'scatter';
  },
  callbacks: {
    title: function() { return ''; },
    label: function(context) {
      const point = context.raw;
      const measurement = lastResults[currentChartType];
      const name = CHART_DISPLAY_NAMES[currentChartType] || currentChartType;
      const unit = CHART_UNITS[currentChartType] || '';
      return [
        'Age: ' + point.x.toFixed(2) + ' years',
        name + ': ' + point.y + ' ' + unit,
        'Centile: ' + (measurement?.centile?.toFixed(1) || 'N/A') + '%',
        'SDS: ' + (measurement?.sds >= 0 ? '+' : '') + (measurement?.sds?.toFixed(2) || 'N/A'),
      ];
    },
  },
};
```

- [ ] **Step 4: Add centile labels on right side of chart**

Use a Chart.js plugin to draw centile labels at the rightmost point of each centile curve:

```javascript
const centileLabelPlugin = {
  id: 'centileLabels',
  afterDatasetsDraw(chart) {
    const ctx = chart.ctx;
    ctx.save();
    chart.data.datasets.forEach(function(dataset, i) {
      if (dataset.type === 'scatter' || !dataset.centileLabel) return;
      const meta = chart.getDatasetMeta(i);
      if (!meta.visible) return;
      const lastPoint = meta.data[meta.data.length - 1];
      if (!lastPoint) return;
      ctx.fillStyle = '#6b7280';
      ctx.font = '10px -apple-system, sans-serif';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText(dataset.centileLabel, lastPoint.x + 4, lastPoint.y);
    });
    ctx.restore();
  },
};
```

Register it: `Chart.register(centileLabelPlugin);`

Add `centileLabel` property to each centile dataset: `centileLabel: String(centile.centile)`.

Add right padding to the chart for labels: `options.layout = { padding: { right: 40 } };`

- [ ] **Step 5: Verify manually**

Start the dev server, calculate for a 5-year-old with height + parental heights. Verify:
- Height chart shows centile curves with graduated line weights
- Blue dot at the child's age/height position
- Centile labels on right side
- MPH purple dashed line + shaded range at age 17-20
- Tooltip on hover over measurement point
- Switch to weight/BMI/OFC tabs — curves render, measurement point shows

- [ ] **Step 6: Commit**

```bash
git add static/charts.js
git commit -m "feat: add measurement plotting, MPH display, centile labels, tooltips"
```

---

### Task 7: Chart Integration Tests and Final Verification

**Files:**
- Create: `tests/test_chart_integration.py`

- [ ] **Step 1: Write integration tests**

```python
"""Integration tests for chart data workflows."""
import json
import pytest


class TestChartDataWorkflows:
    def test_chart_data_all_methods(self, client):
        """All four measurement methods return valid chart data."""
        for method in ["height", "weight", "bmi", "ofc"]:
            payload = {"reference": "uk-who", "measurement_method": method, "sex": "male"}
            response = client.post("/chart-data", data=json.dumps(payload), content_type="application/json")
            assert response.status_code == 200, f"Failed for {method}"
            data = response.get_json()
            assert data["success"] is True
            assert len(data["centiles"]) == 9

    def test_chart_data_all_references(self, client):
        """All references return chart data for their supported methods."""
        cases = [
            ("uk-who", "height", "male"),
            ("uk-who", "weight", "female"),
            ("turners-syndrome", "height", "female"),
            ("trisomy-21", "height", "male"),
            ("cdc", "weight", "male"),
        ]
        for ref, method, sex in cases:
            payload = {"reference": ref, "measurement_method": method, "sex": sex}
            response = client.post("/chart-data", data=json.dumps(payload), content_type="application/json")
            assert response.status_code == 200, f"Failed for {ref}/{method}/{sex}"

    def test_chart_data_consistency_with_calculate(self, client):
        """Chart data age range covers the child's age from /calculate."""
        # Calculate for a 3-year-old
        calc_payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "height": 96.0,
        }
        calc_resp = client.post("/calculate", data=json.dumps(calc_payload), content_type="application/json")
        calc_data = calc_resp.get_json()
        child_age = calc_data["results"]["age_years"]

        # Get chart data
        chart_payload = {"reference": "uk-who", "measurement_method": "height", "sex": "male"}
        chart_resp = client.post("/chart-data", data=json.dumps(chart_payload), content_type="application/json")
        chart_data = chart_resp.get_json()

        # Verify chart data covers the child's age
        median = [c for c in chart_data["centiles"] if c["centile"] == 50][0]
        x_values = [p["x"] for p in median["data"]]
        assert min(x_values) < child_age
        assert max(x_values) > child_age

    def test_chart_data_centile_values(self, client):
        """Verify the 9 cole-nine-centile values."""
        payload = {"reference": "uk-who", "measurement_method": "height", "sex": "female"}
        response = client.post("/chart-data", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        centile_values = sorted([c["centile"] for c in data["centiles"]])
        expected = [0.4, 2, 9, 25, 50, 75, 91, 98, 99.6]
        assert centile_values == expected
```

- [ ] **Step 2: Run integration tests**

```bash
python -m pytest tests/test_chart_integration.py -v
```

Expected: All PASS.

- [ ] **Step 3: Run full test suite**

```bash
python -m pytest -v && npx jest
```

Expected: All backend and frontend tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_chart_integration.py
git commit -m "test: add chart data integration tests"
```

- [ ] **Step 5: Manual browser verification**

```bash
python app.py
```

Test the complete flow:
1. Enter male, DOB 2018-06-15, measurement date 2023-06-15, height 110, weight 20, OFC 52
2. Add maternal height 165, paternal height 178
3. Click Calculate — results appear
4. Click "Show Growth Charts" — height chart appears by default
5. Verify: centile curves with graduated line weights, blue measurement dot, MPH line + range
6. Switch age range — chart re-renders with filtered data
7. Click Weight tab — weight chart renders, measurement dot moves to weight value
8. Click BMI tab — BMI chart renders
9. Click OFC tab — OFC chart renders
10. Click Close — charts section hides
