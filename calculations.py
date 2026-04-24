"""Calculations — age, gestation correction. BSA/velocity/GH added in Phase 3."""
import math

from dateutil.relativedelta import relativedelta

from constants import (
    CBNF_BSA_TABLE,
    GH_STANDARD_DOSE_MG_M2_WEEK,
    PRETERM_THRESHOLD_WEEKS,
    VELOCITY_MIN_INTERVAL_DAYS,
)


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


def calculate_boyd_bsa(weight_kg, height_cm):
    """Calculate BSA using the Boyd formula.

    BSA = 0.0003207 x height^0.3 x weight_g^(0.7285 - 0.0188 x log10(weight_g))
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

    if weight_kg <= table[0][0]:
        return table[0][1]

    if weight_kg >= table[-1][0]:
        w1, b1 = table[-2]
        w2, b2 = table[-1]
        slope = (b2 - b1) / (w2 - w1)
        return round(b2 + slope * (weight_kg - w2), 2)

    for i in range(len(table) - 1):
        w1, b1 = table[i]
        w2, b2 = table[i + 1]
        if w1 <= weight_kg <= w2:
            fraction = (weight_kg - w1) / (w2 - w1)
            return round(b1 + fraction * (b2 - b1), 2)

    return table[-1][1]


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

    If daily_dose_mg is None, calculates initial dose from standard (7 mg/m2/week).
    """
    result = {
        "mg_per_day": None,
        "mg_per_week": None,
        "mg_m2_week": None,
        "mcg_kg_day": None,
        "initial_daily_dose": None,
    }

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
