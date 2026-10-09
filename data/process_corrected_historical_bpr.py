"""Write corrected observation series for the 1998 and 2011 BPR events."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from axialstress.historical_bpr_corrections import (
    CORRECTED_ERUPTION_DEPLOYMENTS,
    PROCESSED_CORRECTED_DIR,
    write_corrected_daily_csv,
)


def main() -> None:
    """Aggregate tide-corrected MGDS channels and available MPR drift corrections."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=PROCESSED_CORRECTED_DIR)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    processed = {}
    for deployment in CORRECTED_ERUPTION_DEPLOYMENTS:
        output_path = args.output_dir / f"{deployment.slug}.daily.csv"
        channel, components, observations = write_corrected_daily_csv(
            deployment, output_path
        )
        processed[deployment.slug] = {
            "station": deployment.station,
            "archive": deployment.archive,
            "source_file": str(deployment.path),
            "original_channel": deployment.raw_channel,
            "corrected_source_channel": channel,
            "correction_components": components,
            "unit": deployment.raw_unit,
            "first_day_utc": observations[0].day.isoformat(),
            "last_day_utc": observations[-1].day.isoformat(),
            "calendar_days": len(observations),
            "usable_days": sum(
                row.relative_uplift_m is not None for row in observations
            ),
            "daily_csv": str(output_path),
        }
        print(
            f"{deployment.station}: {processed[deployment.slug]['usable_days']} "
            f"covered days; {channel} ({components})"
        )

    summary = {
        "processed_utc": datetime.now(UTC).isoformat(),
        "method": (
            "daily arithmetic means of MGDS predicted-tide-corrected observation "
            "channels; use MPR drift-corrected tide channels where available"
        ),
        "model_output_used": False,
        "low_pass_filter_applied": False,
        "minimum_daily_coverage_fraction": 0.75,
        "deployments": processed,
        "limitations": [
            "1997–1998 archive provides predicted-tide correction without an MPR drift estimate",
            "2011 South provides predicted-tide correction without an MPR drift estimate",
            "tide and drift corrections do not remove non-tidal ocean variability",
            "archive processing remains distinct from Cabaniss model output",
        ],
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {summary_path}")


if __name__ == "__main__":
    main()
