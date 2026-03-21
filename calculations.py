"""Calculations — age, gestation correction. BSA/velocity/GH added in Phase 3."""
import math
from datetime import date
from dateutil.relativedelta import relativedelta

from constants import PRETERM_THRESHOLD_WEEKS, CBNF_BSA_TABLE


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
