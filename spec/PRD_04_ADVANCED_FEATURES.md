# PRD 04: Advanced Clinical Features

## Document Information
- **Version:** 1.0
- **Last Updated:** January 2026
- **Related PRD:** PRD-01 Product Overview, PRD-02 Core Calculator

---

## 1. Overview

This PRD defines advanced clinical features that extend beyond basic growth calculations, including height velocity, bone age assessment, body surface area, growth hormone dosing, and previous measurements management.

---

## 2. Basic/Advanced Mode Toggle

### 2.1 Purpose
Allow users to switch between a simplified interface (basic mode) and full feature set (advanced mode).

### 2.2 Basic Mode Features
- Sex selection
- Birth date and measurement date
- Weight, height, OFC inputs
- Parental heights
- Results display (centiles, SDS)
- Growth charts

### 2.3 Advanced Mode Additional Features
- Growth reference selection
- Gestation input
- Previous measurements table
- Bone age assessments
- Height velocity calculation
- GH treatment checkbox
- BSA display
- GH dose calculator
- BMI percentage of median

### 2.4 Implementation
- Toggle switch in header
- CSS classes to show/hide advanced sections
- Persist preference in localStorage
- Default to basic mode

---

## 3. Previous Measurements

### 3.1 Purpose
Track growth trajectory over time and enable height velocity calculation.

### 3.2 Data Structure
```json
{
  "date": "YYYY-MM-DD",
  "height": 82.5,
  "weight": 11.2,
  "ofc": 47.8
}
```

### 3.3 UI Components

#### Collapsed State (Default)
- Single "Add Previous Measurement" button
- Expands section when clicked

#### Expanded State
- Table showing all entered measurements:
  | Date | Height (cm) | Weight (kg) | OFC (cm) | Actions |
  |------|-------------|-------------|----------|---------|
- "Add Another Measurement" button
- Delete button for each row
- CSV Import/Export buttons

### 3.4 Validation Rules
| Rule | Constraint |
|------|------------|
| Date | Must be before current measurement date |
| At least one | Must have height, weight, or OFC |
| Numeric ranges | Same as current measurements |

### 3.5 Processing
For each previous measurement:
- Calculate age at that date
- Calculate SDS and centile for each measurement
- Include in chart plotting

### 3.6 CSV Import/Export

#### CSV Format
```csv
date,height,weight,ofc
2025-06-15,78.2,9.8,46.5
2025-03-10,72.1,8.5,45.2
```

#### Import Behavior
- Parse CSV file
- Validate all rows
- Add valid rows to table
- Show errors for invalid rows
- Merge with existing entries (no duplicates by date)

#### Export Behavior
- Generate CSV from current table data
- Download as file: `previous-measurements.csv`

---

## 4. Height Velocity

### 4.1 Purpose
Calculate yearly growth rate to assess growth patterns and monitor treatment response.

### 4.2 Requirements
| Requirement | Specification |
|-------------|---------------|
| Minimum interval | 4 months (122 days) |
| Current height | Required |
| Previous height | Required (from previous measurements) |
| Unit | cm/year |

### 4.3 Calculation
```
interval_days = current_date - previous_date
height_diff = current_height - previous_height
velocity = (height_diff / interval_days) * 365.25
```

### 4.4 Display
```
Height Velocity: 6.8 cm/year
(based on measurement from 2025-06-15)
```

### 4.5 Error Messages
| Condition | Message |
|-----------|---------|
| No previous height | "Height velocity requires a previous height measurement" |
| Interval < 4 months | "Height velocity requires at least 4 months between measurements (current interval: X.X months)" |
| Previous date ≥ current | "Previous measurement date must be before current measurement date" |

### 4.6 Selection Logic
If multiple previous height measurements exist:
1. Filter to those > 4 months before current
2. Sort by date (most recent first)
3. Use most recent valid measurement

---

## 5. Bone Age Assessment

### 5.1 Purpose
Plot height against skeletal maturity (bone age) rather than chronological age.

### 5.2 Supported Standards
| Standard | Code | Description |
|----------|------|-------------|
| Greulich-Pyle | gp | Traditional atlas method |
| TW3 | tw3 | Tanner-Whitehouse 3 method |

### 5.3 Data Structure
```json
{
  "date": "YYYY-MM-DD",
  "bone_age": 8.5,
  "standard": "tw3"
}
```

### 5.4 UI Components

#### Collapsed State (Default)
- Single "Add Bone Age Assessment" button

#### Expanded State
- Table showing assessments:
  | Assessment Date | Bone Age | Standard | Actions |
  |-----------------|----------|----------|---------|
- Bone age input: Years with decimal (e.g., 8.5)
- Standard dropdown: Greulich-Pyle / TW3
- Delete button for each row

### 5.5 Plotting Eligibility
Bone age is plotted on height chart ONLY if:
- Assessment date is within ±1 month (30.44 days) of measurement date
- Height is provided

### 5.6 Height-for-Bone-Age Calculation
```python
# Create synthetic birth date where "age" at measurement = bone age
synthetic_birth_date = measurement_date - bone_age_in_days

# Create measurement with synthetic birth date
measurement = Measurement(
    birth_date=synthetic_birth_date,
    observation_date=measurement_date,
    observation_value=height,
    ...
)
# This gives SDS/centile for height at bone age
```

### 5.7 Display
Results include:
- Height for bone age centile
- Height for bone age SDS
- Indicator on height chart

---

## 6. Body Surface Area (BSA)

### 6.1 Purpose
Calculate BSA for medication dosing (especially chemotherapy, growth hormone).

### 6.2 Calculation Methods

#### Boyd Formula (Preferred)
Used when BOTH weight and height are available.
```
BSA = 0.0003207 × height^0.3 × weight_g^(0.7285 - 0.0188 × log10(weight_g))
```
Where:
- height in cm
- weight_g = weight in grams

#### cBNF Lookup Table
Used when ONLY weight is available.

| Weight (kg) | BSA (m²) |
|-------------|----------|
| 1 | 0.10 |
| 2 | 0.16 |
| 5 | 0.30 |
| 10 | 0.49 |
| 20 | 0.79 |
| 30 | 1.1 |
| 50 | 1.5 |
| 70 | 1.9 |
| 90 | 2.2 |

For weights between table values: linear interpolation

### 6.3 Display
```
Body Surface Area (Boyd): 0.58 m²
```
or
```
Body Surface Area (cBNF): 0.55 m²
```

Include method used in label.

---

## 7. Growth Hormone (GH) Dose Calculator

### 7.1 Purpose
Help calculate and adjust GH doses for children on growth hormone therapy.

### 7.2 Visibility
Only displayed when:
- Advanced mode is enabled
- "Child is on growth hormone treatment" checkbox is checked
- BSA is calculable (weight provided)

### 7.3 Standard Dose
```
Standard dose: 7 mg/m²/week
```

### 7.4 Calculator Components

#### Input
- Daily dose adjuster with +/- buttons
- Step: 0.025 mg increments
- Minimum: 0 mg

#### Display
```
Daily Dose: [0.6] mg/day [-][+]
= 5.8 mg/m²/week
= 28.5 mcg/kg/day
```

### 7.5 Calculations
```
mg_per_week = daily_dose × 7
mg_m2_week = mg_per_week / BSA
mcg_kg_day = (daily_dose × 1000) / weight_kg
```

### 7.6 Initialization
When calculation completes:
```
initial_daily_dose = (7 × BSA) / 7  # Standard dose
Round to nearest 0.1 mg
```

---

## 8. BMI Percentage of Median

### 8.1 Purpose
Express BMI as percentage of the median (50th centile) value for age and sex. Useful for malnutrition assessment.

### 8.2 Calculation
```
percentage_median = (actual_BMI / median_BMI) × 100
```

Where median_BMI is the 50th centile value for:
- Age (decimal years)
- Sex
- Growth reference

### 8.3 Clinical Interpretation

| % of Median | Interpretation |
|-------------|----------------|
| < 70% | Severe malnutrition |
| 70-80% | Moderate malnutrition |
| 80-90% | Mild malnutrition |
| 90-110% | Normal nutritional status |
| > 120% | Overweight/obesity |

### 8.4 Display
```
BMI: 17.2 (SDS: +0.68, Centile: 75.3%)
% Median: 105.2%
```

---

## 9. Collapsible Sections

### 9.1 Purpose
Reduce visual clutter by hiding optional input sections until needed.

### 9.2 Sections to Collapse

| Section | Default State | Expand Trigger |
|---------|---------------|----------------|
| Previous Measurements | Collapsed | Click "Add Previous Measurement" |
| Bone Age Assessment | Collapsed | Click "Add Bone Age Assessment" |

### 9.3 Behavior
- Clicking add button expands section
- Section remains expanded once data is entered
- Can collapse manually (X or close button)
- State persists during session

### 9.4 Visual Treatment
```
┌─ Collapsed ────────────────────────────────┐
│  [+] Add Previous Measurement              │
└────────────────────────────────────────────┘

┌─ Expanded ─────────────────────────────────┐
│  Previous Measurements (Optional)      [×] │
│  ┌──────────────────────────────────────┐  │
│  │ Date | Height | Weight | OFC | Del   │  │
│  │ ...  | ...    | ...    | ... | 🗑️    │  │
│  └──────────────────────────────────────┘  │
│  [+ Add Another] [Import CSV] [Export CSV] │
└────────────────────────────────────────────┘
```

---

## 10. Form State Persistence

### 10.1 Purpose
Prevent data loss when page is refreshed or browser is closed.

### 10.2 Saved Fields
- Sex selection
- Birth date
- Measurement date
- Weight, height, OFC
- Gestation weeks/days
- Parental heights
- Previous measurements
- Bone age assessments
- Mode preference (basic/advanced)

### 10.3 Storage
- Use localStorage
- Key: `growthCalculatorFormState`
- Update on any input change (debounced)

### 10.4 Restoration
On page load:
1. Check for saved state
2. Restore all field values
3. Expand sections if they contain data
4. Apply saved mode preference

### 10.5 Reset Behavior
Reset button should:
- Clear all form fields
- Clear localStorage
- Collapse expanded sections
- Return to basic mode

---

## 11. Keyboard Shortcuts

### 11.1 Implemented Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+Enter | Calculate |
| Escape | Reset form |
| Ctrl+C | Copy results (when results visible) |

### 11.2 Display
Show keyboard hints next to buttons:
```
[Calculate] (Ctrl+Enter)
[Reset] (Esc)
```

---

## 12. API Extensions

### 12.1 Previous Measurements in Request
```json
{
  "previous_measurements": [
    {
      "date": "2025-06-15",
      "height": 82.5,
      "weight": 11.2,
      "ofc": 47.8
    }
  ]
}
```

### 12.2 Previous Measurements in Response
```json
{
  "previous_measurements": [
    {
      "date": "2025-06-15",
      "age": 1.25,
      "height": {
        "value": 82.5,
        "centile": 50.2,
        "sds": 0.01
      },
      "weight": {...},
      "ofc": {...}
    }
  ],
  "height_velocity": {
    "value": 12.5,
    "message": null
  }
}
```

### 12.3 Bone Age in Request
```json
{
  "bone_age_assessments": [
    {
      "date": "2026-01-15",
      "bone_age": 8.5,
      "standard": "tw3"
    }
  ]
}
```

### 12.4 Bone Age in Response
```json
{
  "bone_age_height": {
    "bone_age": 8.5,
    "assessment_date": "2026-01-15",
    "standard": "tw3",
    "height": 125.5,
    "centile": 45.2,
    "sds": -0.12,
    "within_window": true
  },
  "bone_age_assessments": [...]
}
```

---

## 13. Acceptance Criteria

### 13.1 Mode Toggle
- [ ] Toggle switches between basic and advanced modes
- [ ] Advanced sections hidden in basic mode
- [ ] Mode preference persists

### 13.2 Previous Measurements
- [ ] Can add multiple previous measurements
- [ ] Table displays correctly
- [ ] Can delete individual rows
- [ ] CSV import works
- [ ] CSV export works
- [ ] Values processed in calculation response

### 13.3 Height Velocity
- [ ] Calculates correctly when requirements met
- [ ] Shows appropriate error messages
- [ ] Uses most recent valid previous height

### 13.4 Bone Age
- [ ] Can add multiple assessments
- [ ] Standard selection works
- [ ] Plots on chart when within time window
- [ ] Height for bone age calculated correctly

### 13.5 BSA
- [ ] Boyd formula used when both weight/height available
- [ ] cBNF lookup used when only weight available
- [ ] Method indicated in display

### 13.6 GH Dose
- [ ] Only visible when treatment checkbox checked
- [ ] Adjuster buttons work correctly
- [ ] All three dose formats displayed
- [ ] Initial dose set from standard

### 13.7 Form Persistence
- [ ] Form state saves automatically
- [ ] State restored on page load
- [ ] Reset clears saved state
