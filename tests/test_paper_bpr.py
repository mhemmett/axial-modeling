"""Check source-value preservation and missing observations in BPR exports."""

import csv
import gzip
from dataclasses import replace

import pytest

from axialstress.paper_bpr import (
    CANDIDATE_PROCESSED_CENTER_SOURCES,
    export_hourly_observations,
)


def make_source(tmp_path, rows, channel="LPFDetidedDepth"):
    path = tmp_path / "observations.csv.gz"
    with gzip.open(path, "wt") as stream:
        stream.write(f"Date,{channel}\n" + "\n".join(rows) + "\n")
    source = CANDIDATE_PROCESSED_CENTER_SOURCES[0]
    return replace(source, deployment=replace(source.deployment, archive=str(tmp_path),
                                             filename=path.name))


def test_preserves_observations_and_reports_gaps_without_zero_filling(tmp_path):
    source = make_source(tmp_path, [
        "01/25/1998 00:00:00,1500.123",
        "01/25/1998 00:00:15,0.000",
        "01/25/1998 01:00:00,0.000",
        "01/25/1998 02:00:00,1503.456",
    ])
    output = tmp_path / "export.csv"
    record = export_hourly_observations(source, output)
    with output.open() as stream:
        rows = list(csv.DictReader(stream))
    assert [row["observed_depth_m"] for row in rows] == ["1500.123", "1503.456"]
    assert [row["source_row"] for row in rows] == ["2", "5"]
    assert record["gaps"][0]["missing_hourly_samples"] == 1
    assert record["missing_zero_values_on_hour"] == 1
    assert record["common_datum_verified"] is False
    assert len(record["source_sha256"]) == 64


def test_rejects_missing_field_instead_of_substituting_raw_pressure(tmp_path):
    source = make_source(tmp_path, ["01/25/1998 00:00:00,1500.0"], channel="Depth")
    with pytest.raises(ValueError, match="missing source channel"):
        export_hourly_observations(source, tmp_path / "export.csv")


def test_rejects_out_of_order_source_times(tmp_path):
    source = make_source(tmp_path, [
        "01/25/1998 02:00:00,1500.0", "01/25/1998 00:00:00,1501.0",
    ])
    with pytest.raises(ValueError, match="not increasing"):
        export_hourly_observations(source, tmp_path / "export.csv")


def test_records_missing_processed_samples_after_last_valid_hour(tmp_path):
    source = make_source(tmp_path, [
        "01/25/1998 00:00:00,1500.0",
        "01/25/1998 01:00:00,0.000",
        "01/25/1998 02:00:00,0.000",
    ])
    record = export_hourly_observations(source, tmp_path / "export.csv")
    assert record["samples"] == 1
    assert record["trailing_missing_hourly_samples"] == 2
    assert record["source_last_hour_utc"] == "1998-01-25T02:00:00+00:00"
