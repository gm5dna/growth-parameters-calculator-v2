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
