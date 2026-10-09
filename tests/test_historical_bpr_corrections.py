"""Synthetic checks for permitted archive tide and drift corrections."""

from __future__ import annotations

import csv
import gzip
from dataclasses import replace
from datetime import date

import pytest

from axialstress import historical_bpr
from axialstress.historical_bpr import FOX_1997_1998_DEPLOYMENTS
from axialstress.historical_bpr_corrections import (
    NoCorrectedChannelError,
    process_corrected_deployment,
)


def _write_two_day_file(path, header, rows_per_day=4320):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        for day, raw, drift, tide, combined in (
            ("09/05/2010", 1500.2, 1500.0, 1500.0, 1499.0),
            ("09/06/2010", 1502.2, 1502.0, 1501.0, 1500.0),
        ):
            for sample in range(rows_per_day):
                elapsed_s = sample * 15
                writer.writerow(
                    (
                        f"{day} {elapsed_s // 3600:02d}:"
                        f"{(elapsed_s % 3600) // 60:02d}:{elapsed_s % 60:02d}",
                        raw,
                        drift,
                        tide,
                        combined,
                    )
                )


def test_corrected_deployment_prefers_combined_tide_and_drift_channel(
    tmp_path, monkeypatch
):
    deployment = replace(
        next(
            item
            for item in FOX_1997_1998_DEPLOYMENTS
            if item.slug == "fox_wc81_1997_center"
        ),
        filename="center.txt.gz",
        archive="mgds",
    )
    monkeypatch.setattr(historical_bpr, "RAW_DIR", tmp_path)
    deployment = replace(deployment, archive="test")
    _write_two_day_file(
        tmp_path / "test" / deployment.filename,
        ("Date", "RawDep", "DriftCorrRawDep", "SpotlDep", "DriftCorrSpotlDep"),
    )

    channel, components, rows = process_corrected_deployment(deployment)

    assert channel == "DriftCorrSpotlDep"
    assert components == "predicted tide and MPR-based drift"
    assert [row.day for row in rows] == [date(2010, 9, 5), date(2010, 9, 6)]
    assert rows[0].relative_uplift_m == 0.0
    assert rows[1].relative_uplift_m == pytest.approx(-1.0)
    assert all(row.sample_count == 4320 for row in rows)


def test_ncei_raw_pressure_has_no_corrected_archive_channel():
    from axialstress.historical_bpr import DEPLOYMENTS

    deployment = next(item for item in DEPLOYMENTS if item.slug == "wc81_1997")
    with pytest.raises(NoCorrectedChannelError, match="original NCEI"):
        process_corrected_deployment(deployment)
