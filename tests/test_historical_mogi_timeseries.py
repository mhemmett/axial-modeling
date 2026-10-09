"""Synthetic checks for daily Center-fit, South-held-out Mogi comparisons."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from axialstress.bpr_mogi_calibration import local_east_north_offset_m
from axialstress.historical_mogi_timeseries import (
    compare_center_to_south_timeseries,
    mogi_vertical_response_per_pa,
)


def test_recovers_synthetic_daily_mogi_response_across_full_overlap() -> None:
    eruption_date = date(1998, 1, 11)
    center_location = (45.957, -130.0006)
    south_location = (45.9306, -129.9832)
    east_offset_m, north_offset_m = local_east_north_offset_m(
        south_location[0],
        south_location[1],
        origin_latitude_deg=center_location[0],
        origin_longitude_deg=center_location[1],
    )
    center_response = mogi_vertical_response_per_pa(0.0, 0.0)
    south_response = mogi_vertical_response_per_pa(east_offset_m, north_offset_m)

    center_depth = {}
    south_depth = {}
    for day_offset in range(-10, 11):
        day = eruption_date + timedelta(days=day_offset)
        pressure_pa = 0.0 if day_offset < 0 else day_offset * 1.0e6
        center_depth[day] = 1500.0 - pressure_pa * center_response
        south_depth[day] = 1550.0 - pressure_pa * south_response

    rows, summary = compare_center_to_south_timeseries(
        center_depth,
        south_depth,
        eruption_date=eruption_date,
        center_lat_lon_deg=center_location,
        south_lat_lon_deg=south_location,
    )

    assert len(rows) == 21
    assert summary["baseline_paired_day_count"] == 7
    assert summary["paired_daily_sample_count"] == 21
    assert summary["south_rmse_m"] == pytest.approx(0.0, abs=1.0e-12)
    assert summary["south_correlation"] == pytest.approx(1.0)
    assert rows[-1]["center_fit_pressure_change_pa"] == pytest.approx(10.0e6)


def test_requires_shared_pre_event_baseline() -> None:
    eruption_date = date(2011, 4, 6)
    days = [eruption_date + timedelta(days=offset) for offset in (-7, -6, -5, 0)]
    depths = {day: 1500.0 for day in days}

    with pytest.raises(ValueError, match="shared pre-event baseline"):
        compare_center_to_south_timeseries(
            depths,
            depths,
            eruption_date=eruption_date,
            center_lat_lon_deg=(45.95, -130.0),
            south_lat_lon_deg=(45.93, -130.0),
        )
