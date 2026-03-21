"""Utility functions — MPH, norm_cdf, response formatting.

Chart data helper added in Phase 2.
"""
import math

from rcpchgrowth import create_chart, mid_parental_height, mid_parental_height_z


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
