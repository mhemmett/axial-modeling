"""Audit observed OOI Central Caldera daily depth and relative uplift."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "raw" / "ooi_center_daily"
OUTPUT = ROOT / "data" / "processed" / "ooi_center_daily"


def main() -> None:
    """Write observed uplift relative to the deepest post-2015 daily value."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=INPUT)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    manifest_path = input_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("paper_model_output_used") is not False:
        raise ValueError("OOI input provenance is incomplete")
    records = []
    for item in manifest["files"]:
        path = input_dir / item["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"OOI downloaded file changed: {path}")
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != (
                "time",
                "botsflu_daydepth",
                "botsflu_daydepth_qc_agg",
            ):
                raise ValueError("OOI input columns changed")
            next(reader)  # ERDDAP units row.
            rows = list(reader)
        if len(rows) != item["record_count"]:
            raise ValueError(f"OOI count changed: {path}")
        for row in rows:
            when = date.fromisoformat(row["time"][:10])
            depth = float(row["botsflu_daydepth"])
            flag = int(row["botsflu_daydepth_qc_agg"])
            if not -2000.0 < depth < -1000.0 or flag not in (1, 2):
                raise ValueError(f"OOI depth or quality flag requires review: {when}")
            records.append((when, depth, flag))
    records.sort()
    if len({row[0] for row in records}) != len(records):
        raise ValueError("OOI daily depth has duplicate dates")
    if not records or records[0][0] > date(2015, 4, 25):
        raise ValueError("OOI post-eruption baseline is unavailable")
    baseline_window = [row for row in records if date(2015, 4, 25) <= row[0] < date(2015, 5, 9)]
    if len(baseline_window) < 7:
        raise ValueError("OOI 2015 post-eruption baseline lacks seven daily values")
    baseline = min(baseline_window, key=lambda row: row[1])
    selected = [row for row in records if row[0] >= baseline[0]]
    gaps = [
        {
            "first_missing_day": (prior[0] + timedelta(days=1)).isoformat(),
            "last_missing_day": (later[0] - timedelta(days=1)).isoformat(),
            "missing_days": (later[0] - prior[0]).days - 1,
        }
        for prior, later in zip(selected[:-1], selected[1:], strict=True)
        if (later[0] - prior[0]).days > 1
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    series_path = output_dir / "center_relative_uplift.csv"
    with series_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("time_utc", "daily_depth_m", "uplift_from_2015_baseline_m", "qartod_flag"))
        writer.writerows(
            (when.isoformat(), depth, depth - baseline[1], flag) for when, depth, flag in selected
        )
    summary = {
        "method": "OOI BOTSFLU-DAYDEPTH depth difference from observed post-eruption deepest day",
        "paper_model_output_used": False,
        "source_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "source_url": manifest["data_url"],
        "product_url": manifest["product_url"],
        "retrieved_utc": manifest["retrieved_utc"],
        "baseline_date_utc": baseline[0].isoformat(),
        "baseline_depth_m": baseline[1],
        "last_observed_date_utc": selected[-1][0].isoformat(),
        "last_observed_uplift_m": selected[-1][1] - baseline[1],
        "record_count": len(selected),
        "qartod_flags": {str(flag): sum(row[2] == flag for row in selected) for flag in (1, 2)},
        "missing_day_count": sum(item["missing_days"] for item in gaps),
        "gaps": gaps,
        "series_sha256": hashlib.sha256(series_path.read_bytes()).hexdigest(),
        "limits": (
            "OOI daily depth is detided and corrected for pressure-sensor drift, "
            "but QARTOD flag 2 means not evaluated; missing days remain unfilled. "
            "The first post-eruption depth maximum sets an assumed zero-uplift datum."
        ),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(selected)} observed daily values through {selected[-1][0]}")


if __name__ == "__main__":
    main()
