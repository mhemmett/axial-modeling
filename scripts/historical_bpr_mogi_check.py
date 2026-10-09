"""Check 2011 raw BPR event changes against an elastic Mogi spatial prediction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from axialstress.historical_bpr import DEPLOYMENTS, PROCESSED_DIR
from axialstress.historical_mogi_check import compare_center_to_south_event


def main() -> None:
    """Calibrate the 2011 center observation and predict the South station."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summary",
        type=Path,
        default=PROCESSED_DIR / "summary.json",
        help="daily raw BPR processing summary JSON",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROCESSED_DIR / "historical_mogi_2011.json",
        help="local JSON output path",
    )
    args = parser.parse_args()
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    changes = {
        row["station"]: row
        for row in summary["event_window_changes"]
        if row["eruption_date_utc"] == "2011-04-06"
    }
    center = next(item for item in DEPLOYMENTS if item.slug == "nemo_2010_2011_center")
    south = next(item for item in DEPLOYMENTS if item.slug == "nemo_2009_2011_south")
    if center.station not in changes or south.station not in changes:
        raise ValueError("2011 Center and South raw BPR event changes are required")

    result = compare_center_to_south_event(
        changes[center.station]["post_minus_pre_relative_uplift_m"],
        changes[south.station]["post_minus_pre_relative_uplift_m"],
        center_lat_lon_deg=(center.latitude, center.longitude),
        south_lat_lon_deg=(south.latitude, south.longitude),
    )
    result["eruption_date_utc"] = "2011-04-06"
    result["event_pre_window_utc"] = changes[center.station]["pre_window_utc"]
    result["event_post_window_utc"] = changes[center.station]["post_window_utc"]
    result["daily_data_source"] = "uncorrected MGDS RawDep and Depth channels"
    result["tide_or_drift_correction_applied"] = False
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
