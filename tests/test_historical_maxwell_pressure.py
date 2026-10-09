"""Tests for raw historical BPR Maxwell pressure histories."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pytest

from axialstress.historical_maxwell_pressure import (
    prepare_historical_maxwell_history,
    read_raw_daily_depths,
)


def _daily_csv(path, rows: list[str]) -> None:
    path.write_text(
        "time_utc,raw_channel_mean,raw_channel_unit,equivalent_depth_m,"
        "relative_uplift_m,sample_count,coverage_fraction\n"
        + "\n".join(rows)
        + "\n",
        encoding="utf-8",
    )


def test_read_raw_daily_depths_keeps_only_covered_original_channel_rows(tmp_path) -> None:
    path = tmp_path / "station.csv"
    _daily_csv(
        path,
        [
            "1998-01-01T00:00:00Z,2000,dbar,1000,0,5760,1.0",
            "1998-01-02T00:00:00Z,2001,dbar,1001,,100,0.01736111",
            "1998-01-03T00:00:00Z,2002,dbar,1002,-2,5000,0.86805556",
        ],
    )

    depths = read_raw_daily_depths(path, expected_unit="dbar")

    assert depths == {date(1998, 1, 1): 1000.0, date(1998, 1, 3): 1002.0}


def test_read_raw_daily_depths_rejects_derived_or_unexpected_units(tmp_path) -> None:
    path = tmp_path / "station.csv"
    _daily_csv(
        path,
        [f"1998-01-{day:02d}T00:00:00Z,1,filtered,1000,0,5760,1.0" for day in range(1, 6)],
    )

    with pytest.raises(ValueError, match="original BPR channel"):
        read_raw_daily_depths(path, expected_unit="dbar")


def test_prepare_history_aligns_deployments_and_uses_zero_baseline() -> None:
    start = date(2011, 1, 1)
    center = {start + timedelta(days=day): 100.0 - day * 0.01 for day in range(30)}
    south = {
        start + timedelta(days=day): 200.0 - day * 0.004
        for day in range(2, 30)
    }

    history = prepare_historical_maxwell_history(
        center,
        south,
        center_station="Raw Center",
        south_station="Raw South",
        center_lat_lon_deg=(45.95, -130.01),
        south_lat_lon_deg=(45.93, -130.00),
    )

    assert history.times_utc[0].date() == start + timedelta(days=2)
    assert history.times_utc[-1].date() == start + timedelta(days=29)
    assert history.paired_daily_samples == 28
    assert history.maximum_observation_gap_days == 1
    assert history.center_uplift_m[0] == pytest.approx(0.0)
    assert history.south_uplift_m[0] == pytest.approx(0.0)
    assert history.time_step_s == pytest.approx(27 * 86400 / 5)
    assert np.all(np.diff(history.elapsed_years) > 0.0)


def test_prepare_history_requires_common_coverage() -> None:
    day = date(1998, 1, 1)
    center = {day + timedelta(days=index): 1.0 for index in range(4)}
    south = {day + timedelta(days=index + 8): 1.0 for index in range(4)}

    with pytest.raises(ValueError, match="five paired raw BPR days"):
        prepare_historical_maxwell_history(
            center,
            south,
            center_station="Center",
            south_station="South",
            center_lat_lon_deg=(45.9, -130.0),
            south_lat_lon_deg=(45.8, -130.0),
        )
