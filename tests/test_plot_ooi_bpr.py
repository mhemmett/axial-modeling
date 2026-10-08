"""Synthetic checks for the independent OOI BPR observation plot."""

from datetime import UTC, datetime

import numpy as np
import pytest
from scripts.plot_ooi_bpr import plot_series

from axialstress.bpr_observations import BprSeries, read_processed_bpr_series


def _write_processed_series(path, rows: list[str]) -> None:
    path.write_text(
        "time_utc,signed_depth_m,relative_uplift_m,ooi_qc_aggregate\n"
        + "\n".join(rows)
        + "\n",
        encoding="utf-8",
    )


def test_reads_utc_dates_uplift_and_unmodified_qc_codes(tmp_path) -> None:
    source = tmp_path / "central.csv"
    _write_processed_series(
        source,
        [
            "2014-08-31T00:00:00Z,-1510.25,0,2",
            "2014-09-01T00:00:00Z,-1510.26,0.01,2",
        ],
    )

    series = read_processed_bpr_series("central", source)

    assert len(series.times_utc) == 2
    np.testing.assert_array_equal(series.uplift_m, [0.0, 0.01])
    assert series.quality_codes == ("2", "2")


def test_rejects_nonincreasing_timestamps(tmp_path) -> None:
    source = tmp_path / "central.csv"
    _write_processed_series(
        source,
        [
            "2014-09-01T00:00:00Z,-1510.26,0.01,2",
            "2014-08-31T00:00:00Z,-1510.25,0,2",
        ],
    )

    with pytest.raises(ValueError, match="strictly increasing"):
        read_processed_bpr_series("central", source)


def test_plot_writes_png_and_pdf(tmp_path) -> None:
    central = BprSeries(
        "central",
        (
            datetime(2014, 8, 31, tzinfo=UTC),
            datetime(2014, 9, 1, tzinfo=UTC),
        ),
        np.array([0.0, 0.01]),
        ("2", "2"),
    )
    east = BprSeries(
        "east",
        central.times_utc,
        np.array([0.0, 0.02]),
        ("2", "2"),
    )

    png_path, pdf_path = plot_series(central, east, tmp_path / "bpr")

    assert png_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert pdf_path.read_bytes().startswith(b"%PDF")
