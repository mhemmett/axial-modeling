"""Tests for parsing and reducing raw Axial BPR depth channels."""

from __future__ import annotations

import io

import pytest
from data.process_historical_bpr import read_daily_raw_depth

from axialstress.historical_bpr_check import mogi_vertical_response_ratio


def test_daily_reduction_selects_only_the_uncorrected_raw_depth_column() -> None:
    stream = io.StringIO(
        "Date,RawDep,DriftCorrRawDep,SpotlDep\n"
        "01/20/1998 00:00:00,1500.0,1600.0,1700.0\n"
        "01/20/1998 12:00:00,1502.0,1602.0,1702.0\n"
        "01/21/1998 00:00:00,1499.0,1599.0,1699.0\n"
    )

    daily, total_rows, raw_column = read_daily_raw_depth(stream)

    assert total_rows == 3
    assert raw_column == "RawDep"
    assert [row["time_utc"] for row in daily] == ["1998-01-20", "1998-01-21"]
    assert [row["daily_median_raw_depth_m"] for row in daily] == [1501.0, 1499.0]
    assert [row["sample_count"] for row in daily] == [2, 1]


def test_daily_reduction_rejects_files_without_raw_depth() -> None:
    stream = io.StringIO("Date,DriftCorrRawDep,SpotlDep\n01/20/1998 00:00:00,1,2\n")

    with pytest.raises(ValueError, match="no raw depth field"):
        read_daily_raw_depth(stream)


def test_mogi_spatial_ratio_is_one_at_source_and_decreases_with_offset() -> None:
    source = (45.95, -130.0)
    central_ratio = mogi_vertical_response_ratio(source, source)
    south_ratio = mogi_vertical_response_ratio((45.93, -129.98), source)

    assert central_ratio == pytest.approx(1.0)
    assert 0.0 < south_ratio < central_ratio
