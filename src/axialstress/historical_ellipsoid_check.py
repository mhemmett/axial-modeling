"""Compare raw historical BPR event changes with a PyLith ellipsoid response."""

from __future__ import annotations

import math


def compare_center_to_south_event(
    center_uplift_m: float,
    south_uplift_m: float,
    *,
    center_unit_response_m_per_mpa: float,
    south_unit_response_m_per_mpa: float,
    east_offset_m: float,
    north_offset_m: float,
) -> dict[str, float | str | bool]:
    """Fit pressure at Center and predict an event change at South."""
    values = (
        center_uplift_m,
        south_uplift_m,
        center_unit_response_m_per_mpa,
        south_unit_response_m_per_mpa,
        east_offset_m,
        north_offset_m,
    )
    if not all(math.isfinite(value) for value in values):
        raise ValueError("ellipsoid event inputs must be finite")
    if center_unit_response_m_per_mpa <= 0.0:
        raise ValueError("center unit response must be positive")

    pressure_change_mpa = center_uplift_m / center_unit_response_m_per_mpa
    south_prediction_m = pressure_change_mpa * south_unit_response_m_per_mpa
    return {
        "method": "static PyLith ellipsoid pressure fit at Center with South held out",
        "center_observed_relative_uplift_m": center_uplift_m,
        "south_observed_relative_uplift_m": south_uplift_m,
        "south_predicted_relative_uplift_m": south_prediction_m,
        "south_residual_m": south_uplift_m - south_prediction_m,
        "inferred_pressure_change_mpa": pressure_change_mpa,
        "center_unit_response_m_per_mpa": center_unit_response_m_per_mpa,
        "south_unit_response_m_per_mpa": south_unit_response_m_per_mpa,
        "south_offset_east_m": east_offset_m,
        "south_offset_north_m": north_offset_m,
        "south_horizontal_distance_m": math.hypot(east_offset_m, north_offset_m),
        "center_is_calibration_site": True,
        "south_is_held_out_site": True,
        "publication_observations_used": False,
        "limitations": [
            "static elasticity omits viscoelastic memory",
            "unit response uses a coarse, nonconverged mesh",
            "station offsets use the Center BPR as the source-axis origin",
        ],
    }
