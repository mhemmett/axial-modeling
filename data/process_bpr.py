"""Convert OOI signed BPR depth into relative uplift, retaining QC flags."""

from __future__ import annotations

import argparse
import csv
import gzip
import math
from collections.abc import Iterable
from pathlib import Path


def relative_uplift(depth_m: Iterable[float]) -> list[float]:
    """Return signed vertical displacement from the first finite depth value."""
    values = [float(value) for value in depth_m]
    finite = [value for value in values if math.isfinite(value)]
    if not finite:
        raise ValueError("depth series contains no finite values")
    baseline = finite[0]
    return [value - baseline if math.isfinite(value) else math.nan for value in values]


def read_daily_depth(path: Path) -> list[dict[str, str]]:
    """Read an OOI ERDDAP CSV response with its variable and unit header."""
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError(f"empty OOI data file: {path}") from exc
        expected = [
            "time (UTC)",
            "botsflu_daydepth (m)",
            "botsflu_daydepth_qc_agg",
        ]
        if header != expected:
            raise ValueError(f"unexpected OOI CSV header in {path}: {header}")
        rows = []
        for row in reader:
            if len(row) != len(expected):
                raise ValueError(f"malformed OOI row in {path}: {row}")
            rows.append(dict(zip(("time", "depth_m", "qc_aggregate"), row, strict=True)))
    if not rows:
        raise ValueError(f"OOI data file has no records: {path}")
    return rows


def process_file(source: Path, destination: Path) -> int:
    """Write a relative-uplift CSV and return the number of data rows."""
    rows = read_daily_depth(source)
    depths = [float(row["depth_m"]) for row in rows]
    uplift = relative_uplift(depths)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            ["time_utc", "signed_depth_m", "relative_uplift_m", "ooi_qc_aggregate"]
        )
        for row, displacement in zip(rows, uplift, strict=True):
            writer.writerow(
                [
                    row["time"],
                    row["depth_m"],
                    f"{displacement:.12g}",
                    row["qc_aggregate"],
                ]
            )
    return len(rows)


def main() -> None:
    """Parse input and output paths and write a relative-uplift series."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="gzipped OOI ERDDAP CSV response")
    parser.add_argument(
        "--output",
        type=Path,
        help="output CSV path (default: ignored data/processed directory)",
    )
    args = parser.parse_args()
    output = args.output or (
        Path(__file__).resolve().parent
        / "processed"
        / f"{args.input.name.removesuffix('.csv.gz')}.relative-uplift.csv"
    )
    row_count = process_file(args.input, output)
    print(f"wrote {row_count} records to {output}")


if __name__ == "__main__":
    main()
