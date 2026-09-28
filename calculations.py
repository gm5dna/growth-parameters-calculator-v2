"""Calculations — age, gestation correction. BSA/velocity/GH added in Phase 3."""
import math

from dateutil.relativedelta import relativedelta

from constants import (
    CBNF_BSA_TABLE,
    GH_STANDARD_DOSE_MG_M2_WEEK,
    VELOCITY_MIN_INTERVAL_DAYS,
    ErrorCodes,
)


class MeasurementDateError(ValueError):
    """Raised when a measurement date precedes the birth date.

    Subclasses ValueError for backwards compatibility, but carries the
    INVALID_DATE_RANGE code so the HTTP layer can map it without inspecting
    the message text.
    """

    code = ErrorCodes.INVALID_DATE_RANGE


def calculate_age_in_years(birth_date, measurement_date):
    """Calculate decimal age in years. Allows age=0 (same-day, e.g. birth weight)."""
    if measurement_date < birth_date:
        raise MeasurementDateError("Measurement date must not be before birth date.")
    return (measurement_date - birth_date).days / 365.25


def calculate_calendar_age(birth_date, measurement_date):
    """Calculate age as years, months, days dict."""
    delta = relativedelta(measurement_date, birth_date)
    return {
        "years": delta.years,
        "months": delta.months,
        "days": delta.days,
    }


def expected_delivery_date(birth_date, gestation_weeks, gestation_days):
    """Return the would-be term (40-week) birth date for a baby born before 40 weeks.

    A baby born at gestation_weeks+gestation_days reaches term this many
    weeks/days after its actual birth date; corrected age is measured from
    this EDD.
    """
    return birth_date + relativedelta(weeks=(40 - gestation_weeks), days=-gestation_days)


def library_corrected_age(reference, birth_date, on_date, gestation_weeks, gestation_days=0):
    """Decimal age rcpchgrowth will use: corrected for gestation at every age (RCPCH).

    Mirrors rcpchgrowth.Measurement for the reference-support check, incl. its
    CDC/WHO exceptions (37-42 wk treated as term; preterm correction stops at
    corrected age 2). Negative for very preterm infants before their EDD.
    """
    age = (on_date - birth_date).days / 365.25
    if not gestation_weeks:
        return age
    corrected = (on_date - expected_delivery_date(birth_date, gestation_weeks, gestation_days)).days / 365.25
    if reference in ("cdc", "who") and (
        (corrected >= 2 and gestation_weeks < 37) or 37 <= gestation_weeks <= 42
    ):
        return age
    return corrected


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

    # Clamp to the top tabulated value rather than extrapolating. The cBNF
    # table only covers 1-90 kg; linear extrapolation beyond it produced
    # physiologically impossible areas (e.g. ~5.35 m2 at 300 kg) that then
    # drove the GH initial-dose calculation. Weight-only BSA above the table
    # is unusual (height is normally present); returning the top value is
    # safer than fabricating one outside the validated domain.
    if weight_kg >= table[-1][0]:
        return table[-1][1]

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


def calculate_gh_dose(bsa):
    """Calculate the initial GH daily dose from the standard (7 mg/m2/week)."""
    return {"initial_daily_dose": round((GH_STANDARD_DOSE_MG_M2_WEEK * bsa) / 7, 1)}
