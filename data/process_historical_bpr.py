"""Reduce independent raw Axial BPR depths to daily observational records."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import io
import json
import math
import statistics
import tarfile
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import TextIO

from axialstress.historical_bpr_check import EVENT_WINDOWS

if __package__:
    from .fetch_historical_bpr import ARCHIVES, RawBPRFile
else:
    from fetch_historical_bpr import ARCHIVES, RawBPRFile

UTC = dt.UTC


def _depth_column(fieldnames: list[str] | None) -> str:
    """Select only the archive's uncorrected pressure-derived depth field."""
    if not fieldnames:
        raise ValueError("BPR file has no CSV header")
    names = {name.strip().lower(): name for name in fieldnames}
    for candidate in ("rawdep", "depth"):
        if candidate in names:
            return names[candidate]
    raise ValueError(f"no raw depth field in BPR header: {fieldnames}")


def read_daily_raw_depth(
    stream: TextIO,
) -> tuple[list[dict[str, str | int | float]], int, str]:
    """Return UTC daily median depth, sample count, and selected raw field."""
    reader = csv.DictReader(stream)
    if reader.fieldnames is None:
        raise ValueError("BPR file is empty")
    date_column = next(
        (name for name in reader.fieldnames if name.strip().lower() == "date"), None
    )
    depth_column = _depth_column(reader.fieldnames)
    if date_column is None:
        raise ValueError(f"BPR file has no date field: {reader.fieldnames}")

    samples_by_day: dict[dt.date, list[float]] = defaultdict(list)
    total_rows = 0
    for row in reader:
        total_rows += 1
        try:
            timestamp = dt.datetime.strptime(
                row[date_column].strip(), "%m/%d/%Y %H:%M:%S"
            ).replace(tzinfo=UTC)
            depth_m = float(row[depth_column].strip())
        except (AttributeError, KeyError, ValueError):
            continue
        if math.isfinite(depth_m):
            samples_by_day[timestamp.date()].append(depth_m)
    if not samples_by_day:
        raise ValueError("BPR file contains no finite raw-depth observations")

    daily_depth = [
        {
            "time_utc": day.isoformat(),
            "daily_median_raw_depth_m": statistics.median(values),
            "sample_count": len(values),
        }
        for day, values in sorted(samples_by_day.items())
    ]
    return daily_depth, total_rows, depth_column


def summarize_event_change(
    daily_depth: Iterable[dict[str, str | int | float]], event: str
) -> dict[str, object]:
    """Estimate an event-window vertical step from raw-depth daily medians."""
    windows = EVENT_WINDOWS[event]
    rows = list(daily_depth)
    dates = [dt.date.fromisoformat(str(row["time_utc"])) for row in rows]
    pre = [
        float(row["daily_median_raw_depth_m"])
        for row, day in zip(rows, dates, strict=True)
        if windows["pre_start"] <= day < windows["pre_end"]
    ]
    post = [
        float(row["daily_median_raw_depth_m"])
        for row, day in zip(rows, dates, strict=True)
        if windows["post_start"] <= day < windows["post_end"]
    ]
    summary: dict[str, object] = {
        "pre_window_utc": [windows["pre_start"].isoformat(), windows["pre_end"].isoformat()],
        "post_window_utc": [
            windows["post_start"].isoformat(),
            windows["post_end"].isoformat(),
        ],
        "pre_daily_records": len(pre),
        "post_daily_records": len(post),
    }
    if len(pre) >= 3 and len(post) >= 3:
        pre_depth_m = statistics.median(pre)
        post_depth_m = statistics.median(post)
        summary["pre_median_raw_depth_m"] = pre_depth_m
        summary["post_median_raw_depth_m"] = post_depth_m
        summary["apparent_uplift_change_m"] = pre_depth_m - post_depth_m
    else:
        summary["apparent_uplift_change_m"] = None
    return summary


def process_file(
    archive_path: Path,
    source_file: RawBPRFile,
    output_dir: Path,
) -> dict[str, object]:
    """Write one daily raw-depth series and return its local provenance."""
    with tarfile.open(archive_path, "r:*") as archive:
        member = next(
            (
                candidate
                for candidate in archive
                if Path(candidate.name).name.removesuffix(".gz") == source_file.filename
            ),
            None,
        )
        if member is None:
            raise ValueError(f"{source_file.filename} is absent from {archive_path}")
        compressed_stream = archive.extractfile(member)
        if compressed_stream is None:
            raise ValueError(f"could not read {member.name} in {archive_path}")
        with gzip.GzipFile(fileobj=compressed_stream) as gzipped:
            with io.TextIOWrapper(gzipped, encoding="utf-8", newline="") as text_stream:
                daily, rows_read, raw_column = read_daily_raw_depth(text_stream)

    baseline_depth_m = float(daily[0]["daily_median_raw_depth_m"])
    for row in daily:
        row["relative_uplift_from_first_day_m"] = (
            baseline_depth_m - float(row["daily_median_raw_depth_m"])
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{source_file.event}_{source_file.site}_daily_raw_depth.csv"
    columns = (
        "time_utc",
        "daily_median_raw_depth_m",
        "relative_uplift_from_first_day_m",
        "sample_count",
    )
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(daily)

    event_change = summarize_event_change(daily, source_file.event)
    first_time = str(daily[0]["time_utc"])
    last_time = str(daily[-1]["time_utc"])
    finite_samples = sum(int(row["sample_count"]) for row in daily)
    return {
        "source_archive": source_file.archive,
        "dataset_uid": source_file.dataset_uid,
        "dataset_doi": source_file.dataset_doi,
        "source_file_uid": source_file.file_uid,
        "source_filename": source_file.filename,
        "site": source_file.site,
        "event": source_file.event,
        "latitude_deg": source_file.latitude_deg,
        "longitude_deg": source_file.longitude_deg,
        "raw_depth_column": raw_column,
        "input_rows": rows_read,
        "finite_raw_depth_samples": finite_samples,
        "skipped_rows": rows_read - finite_samples,
        "daily_records": len(daily),
        "first_day_utc": first_time,
        "last_day_utc": last_time,
        "output_file": str(output_path),
        "event_window_change": event_change,
        "processing": (
            "UTC daily median; uplift is negative raw-depth change; "
            "no tide or drift correction"
        ),
    }


def process_all(
    input_dir: Path,
    output_dir: Path,
    archives: Iterable[str],
) -> list[dict[str, object]]:
    """Process selected deployment files from the local MGDS tar archives."""
    results = []
    for archive_name in archives:
        archive_path = input_dir / f"axial-bpr-{archive_name}.tar"
        if not archive_path.is_file():
            raise FileNotFoundError(f"missing {archive_path}; run the historical BPR fetcher")
        for source_file in ARCHIVES[archive_name]["files"]:
            result = process_file(archive_path, source_file, output_dir)
            results.append(result)
    return results


def main() -> None:
    """Create daily raw-depth CSV files and an event-window summary manifest."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archives",
        nargs="+",
        choices=tuple(ARCHIVES),
        default=tuple(ARCHIVES),
        help="historical BPR archives to process (default: both eruption records)",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "raw" / "historical_bpr",
        help="directory containing fetched MGDS tar files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "processed" / "historical_bpr",
        help="directory for ignored daily summaries",
    )
    args = parser.parse_args()
    results = process_all(args.input_dir, args.output_dir, args.archives)
    manifest = {
        "source": "MGDS Axial uncabled BPR records",
        "source_data_used": "uncorrected raw-depth channel only",
        "excluded_source_data": "tide-detided and drift-corrected channels and paper outputs",
        "created_utc": dt.datetime.now(UTC).isoformat(),
        "records": results,
    }
    manifest_path = args.output_dir / "processing_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for result in results:
        change = result["event_window_change"]["apparent_uplift_change_m"]
        print(
            f"{result['event']} {result['site']}: {result['daily_records']} daily records, "
            f"event-window apparent uplift change={change} m"
        )
    print(f"processing manifest: {manifest_path}")


if __name__ == "__main__":
    main()
