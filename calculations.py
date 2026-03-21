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
