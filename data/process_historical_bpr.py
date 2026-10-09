"""Aggregate uncorrected non-OOI Axial BPR observations into daily means."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from axialstress.historical_bpr import (
    DEPLOYMENTS,
    METERS_PER_DBAR,
    MINIMUM_DAILY_COVERAGE,
    PROCESSED_DIR,
    event_window_change,
    write_daily_csv,
)


def main() -> None:
    """Write ignored daily data products and event-window diagnostics."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROCESSED_DIR,
        help="directory for ignored daily series and summary JSON",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    processed = {}
    event_changes = []
    for deployment in DEPLOYMENTS:
        path = args.output_dir / f"{deployment.slug}.daily.csv"
        observations = write_daily_csv(deployment, path)
        usable = sum(row.relative_uplift_m is not None for row in observations)
        processed[deployment.slug] = {
            "station": deployment.station,
            "source_file": str(deployment.path),
            "raw_channel": deployment.raw_channel,
            "raw_unit": deployment.raw_unit,
            "latitude": deployment.latitude,
            "longitude": deployment.longitude,
            "first_day_utc": observations[0].day.isoformat(),
            "last_day_utc": observations[-1].day.isoformat(),
            "calendar_days": len(observations),
            "usable_days": usable,
            "daily_csv": str(path),
        }
        print(
            f"{deployment.station}: {usable} usable of {len(observations)} UTC days; "
            f"{observations[0].day} to {observations[-1].day}; channel {deployment.raw_channel}"
        )
        if deployment.eruption_date is not None:
            change = event_window_change(
                observations,
                deployment.eruption_date,
                deployment.station,
            )
            event_changes.append(change)
            print(
                f"  event-window relative elevation change: "
                f"{change['post_minus_pre_relative_uplift_m']:.3f} m "
                f"(up positive; {change['pre_valid_days']} pre days, "
                f"{change['post_valid_days']} post days)"
            )

    summary = {
        "processed_utc": datetime.now(UTC).isoformat(),
        "processing": {
            "sampling_interval_s": 15,
            "daily_aggregation": "arithmetic mean of raw 15-second samples by UTC date",
            "minimum_daily_coverage_fraction": MINIMUM_DAILY_COVERAGE,
            "event_pre_window_days": [-7, -1],
            "event_post_window_days": [8, 14],
            "event_window_statistic": "median of complete daily depth means",
            "pressure_conversion_m_per_dbar": METERS_PER_DBAR,
            "pressure_conversion_assumed_water_density_kg_m3": 1025.0,
            "pressure_conversion_gravity_m_s2": 9.80665,
            "excluded_channels": [
                "detided depth",
                "low-pass filtered depth",
                "drift-corrected depth",
            ],
        },
        "deployments": processed,
        "event_window_changes": event_changes,
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"wrote event summary to {summary_path}")


if __name__ == "__main__":
    main()
