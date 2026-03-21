# PRD 02: Core Calculator Functionality

## Document Information
- **Version:** 1.0
- **Last Updated:** January 2026
- **Related PRD:** PRD-01 Product Overview

---

## 1. Overview

This PRD defines the core calculation features of the Growth Parameters Calculator, including age calculations, anthropometric measurements, and growth reference data processing.

---

## 2. Age Calculation

### 2.1 Chronological Age

#### Requirements
- Calculate age from date of birth to measurement date
- Express age as both:
  - **Decimal years** (e.g., 2.45 years) - for calculations
  - **Calendar age** (e.g., 2 years, 5 months, 12 days) - for display

#### Formula
```
decimal_age = (measurement_date - birth_date).days / 365.25
```

#### Validation Rules
| Rule | Constraint |
|------|------------|
| Maximum age | 25 years |
| Minimum age | > 0 (measurement must be after birth) |
| Future dates | Rejected for both birth and measurement dates |
| Date format | YYYY-MM-DD (ISO 8601) |

### 2.2 Corrected Age (Preterm Infants)

#### When to Apply Correction
Correction applies when:
- Gestation < 37 weeks, AND
- Age thresholds based on prematurity:

| Gestation | Correction Duration |
|-----------|---------------------|
| 32-36 weeks | Until age 1 year |
| < 32 weeks | Until age 2 years |

#### Correction Formula
```
expected_due_date = birth_date + (40 weeks - actual_gestation)
corrected_age = measurement_date - expected_due_date
```

#### Display Requirements
When correction is applied, show BOTH:
- Chronological age
- Corrected age (clearly labeled)

---

## 3. Anthropometric Measurements

### 3.1 Weight

| Property | Specification |
|----------|---------------|
| Unit | Kilograms (kg) |
| Minimum | 0.1 kg |
| Maximum | 300 kg |
| Precision | Up to 2 decimal places |

#### Output
- Centile (0.4th to 99.6th)
- SDS (Z-score)

### 3.2 Height/Length

| Property | Specification |
|----------|---------------|
| Unit | Centimeters (cm) |
| Minimum | 10 cm |
| Maximum | 250 cm |
| Precision | Up to 1 decimal place |

#### Notes
- **Length**: Measured lying down (infants < 2 years)
- **Height**: Measured standing (children ≥ 2 years)
- The rcpchgrowth library handles the length/height transition automatically

#### Output
- Centile (0.4th to 99.6th)
- SDS (Z-score)

### 3.3 Head Circumference (OFC)

| Property | Specification |
|----------|---------------|
| Unit | Centimeters (cm) |
| Minimum | 10 cm |
| Maximum | 100 cm |
| Precision | Up to 1 decimal place |

#### Clinical Context
- OFC primarily measured in children < 2 years
- Continues to be relevant for children with neurological concerns

#### Output
- Centile (0.4th to 99.6th)
- SDS (Z-score)

### 3.4 Body Mass Index (BMI)

#### Calculation
```
BMI = weight_kg / (height_m)²
BMI = weight_kg / (height_cm / 100)²
```

#### Requirements
- Auto-calculated when both weight AND height are provided
- Not calculated if either measurement is missing

#### Output
- BMI value (1 decimal place)
- Centile (0.4th to 99.6th)
- SDS (Z-score)
- Percentage of median (advanced mode)

---

## 4. SDS (Z-Score) Validation

### 4.1 Warning Thresholds

| Measurement | Warning | Hard Limit (Reject) |
|-------------|---------|---------------------|
| Weight | ±4 SDS | ±8 SDS |
| Height | ±4 SDS | ±8 SDS |
| OFC | ±4 SDS | ±8 SDS |
| BMI | ±4 SDS | ±15 SDS |

### 4.2 Warning Behavior

**Advisory Warning (±4 to ±8 SDS)**:
- Display warning message
- Allow calculation to proceed
- Message: "SDS is very extreme (>±4 SDS). Please verify measurement accuracy."

**Hard Rejection (>±8 SDS)**:
- Return error
- Do not display results
- Message: "SDS exceeds acceptable range (±8 SDS). Please check measurement accuracy."

### 4.3 Rationale
- Values beyond ±8 SDS are almost certainly measurement errors
- BMI has higher threshold due to greater natural variation

---

## 5. Growth References

### 5.1 UK-WHO (Default)

| Property | Value |
|----------|-------|
| Age Range | 0-20 years |
| Composition | WHO Standards (0-4y) + UK 1990 (4-20y) |
| Populations | General UK pediatric population |

### 5.2 Turner Syndrome

| Property | Value |
|----------|-------|
| Age Range | 1-20 years |
| Population | Confirmed Turner syndrome (45,X) |
| Sex | Female only |

### 5.3 Trisomy 21 (Down Syndrome)

| Property | Value |
|----------|-------|
| Age Range | 0-18 years |
| Population | Confirmed Trisomy 21 |
| Sex | Male and female |

### 5.4 CDC (US Reference)

| Property | Value |
|----------|-------|
| Age Range | 0-20 years |
| Population | US pediatric population |
| Use Case | Extended BMI calculations for obesity |

---

## 6. Mid-Parental Height (MPH)

### 6.1 Calculation

**For Males:**
```
MPH = (maternal_height + paternal_height) / 2 + 6.5 cm
```

**For Females:**
```
MPH = (maternal_height + paternal_height) / 2 - 6.5 cm
```

### 6.2 Target Range
```
Target Range = MPH ± 8.5 cm
```

This represents approximately ±2 SDS from the mid-parental height.

### 6.3 Input Requirements
| Property | Specification |
|----------|---------------|
| Units | Centimeters (cm) OR feet/inches |
| Conversion | 1 inch = 2.54 cm |
| Required | Both parents OR neither |

### 6.4 Output
- Mid-parental height (cm)
- MPH SDS (Z-score)
- MPH centile
- Target range (lower - upper bounds in cm)

---

## 7. Gestation Input

### 7.1 Fields
| Field | Type | Range |
|-------|------|-------|
| Weeks | Integer | 22-44 |
| Days | Integer | 0-6 |

### 7.2 Validation
- Weeks is required if any gestation data provided
- Days is optional (defaults to 0)
- Total gestation must be 22+0 to 44+6

### 7.3 Display
Format: `XX weeks + X days` (e.g., "34 weeks + 3 days")

---

## 8. API Specification

### 8.1 Calculate Endpoint

**POST /calculate**

#### Request Body
```json
{
  "sex": "male" | "female",
  "birth_date": "YYYY-MM-DD",
  "measurement_date": "YYYY-MM-DD",
  "weight": 12.5,
  "height": 85.3,
  "ofc": 48.2,
  "reference": "uk-who",
  "gestation_weeks": 34,
  "gestation_days": 3,
  "maternal_height": 165.0,
  "paternal_height": 178.0
}
```

#### Required Fields
- `sex`
- `birth_date`
- `measurement_date`
- At least ONE of: `weight`, `height`, `ofc`

#### Response (Success)
```json
{
  "success": true,
  "results": {
    "age_years": 2.45,
    "age_calendar": {
      "years": 2,
      "months": 5,
      "days": 12
    },
    "gestation_correction_applied": true,
    "corrected_age_years": 2.32,
    "corrected_age_calendar": {
      "years": 2,
      "months": 3,
      "days": 28
    },
    "weight": {
      "value": 12.5,
      "centile": 50.12,
      "sds": 0.03
    },
    "height": {
      "value": 85.3,
      "centile": 25.45,
      "sds": -0.67
    },
    "bmi": {
      "value": 17.2,
      "centile": 75.32,
      "sds": 0.68,
      "percentage_median": 105.2
    },
    "ofc": {
      "value": 48.2,
      "centile": 45.67,
      "sds": -0.11
    },
    "mid_parental_height": {
      "mid_parental_height": 178.5,
      "mid_parental_height_sds": 0.45,
      "mid_parental_height_centile": 67.3,
      "target_range_lower": 170.0,
      "target_range_upper": 187.0
    },
    "validation_messages": []
  }
}
```

#### Response (Error)
```json
{
  "success": false,
  "error": "Error message description",
  "error_code": "ERR_001"
}
```

### 8.2 Error Codes

| Code | Description |
|------|-------------|
| ERR_001 | Invalid date format |
| ERR_002 | Invalid date range |
| ERR_003 | Missing measurement |
| ERR_004 | Invalid weight |
| ERR_005 | Invalid height |
| ERR_006 | Invalid OFC |
| ERR_007 | Invalid gestation |
| ERR_008 | SDS out of range |
| ERR_009 | Calculation error |
| ERR_010 | Invalid input |

---

## 9. Calculation Library Integration

### 9.1 rcpchgrowth Library

The application MUST use the `rcpchgrowth` Python library for:
- Age calculations (`chronological_decimal_age`, `corrected_decimal_age`)
- Measurement creation and SDS calculation (`Measurement` class)
- Mid-parental height (`mid_parental_height`, `mid_parental_height_z`)
- Centile curve data (`create_chart`)

### 9.2 Library Usage Example
```python
from rcpchgrowth import Measurement

measurement = Measurement(
    sex='male',
    birth_date=birth_date,
    observation_date=measurement_date,
    measurement_method='height',
    observation_value=85.3,
    reference='uk-who',
    gestation_weeks=34,
    gestation_days=3
)

# Access calculated values
calc = measurement.measurement['measurement_calculated_values']
centile = calc['corrected_centile']
sds = calc['corrected_sds']
```

---

## 10. Acceptance Criteria

### 10.1 Age Calculation
- [ ] Calculates decimal age correctly
- [ ] Displays calendar age (years/months/days)
- [ ] Applies gestation correction when appropriate
- [ ] Shows both chronological and corrected ages when correction applied

### 10.2 Measurements
- [ ] Calculates SDS for weight, height, OFC
- [ ] Auto-calculates BMI when both weight and height provided
- [ ] Validates measurement ranges
- [ ] Displays warnings for extreme SDS values
- [ ] Rejects values beyond hard limits

### 10.3 Mid-Parental Height
- [ ] Calculates MPH correctly for both sexes
- [ ] Accepts input in cm or feet/inches
- [ ] Displays target range

### 10.4 References
- [ ] Supports UK-WHO, Turner, Trisomy-21, CDC
- [ ] Applies correct reference based on selection
