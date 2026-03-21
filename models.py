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
