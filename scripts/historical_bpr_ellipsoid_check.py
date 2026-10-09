"""Check raw 1998 and 2011 BPR changes against a PyLith ellipsoid response."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from axialstress.bpr_mogi_calibration import local_east_north_offset_m
from axialstress.ellipsoid_bpr_calibration import read_ellipsoid_unit_response
from axialstress.historical_bpr import DEPLOYMENTS, PROCESSED_DIR
from axialstress.historical_ellipsoid_check import compare_center_to_south_event

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SURFACE = (
    ROOT
    / "pylith"
    / "step05_ellipsoid_elastic"
    / "output"
    / "ellipsoid-surface.h5"
)
EVENT_PAIRS = {
    "1998": (
        "1998-01-25",
        "wc81_1997",
        "wc82a_1997",
        "NCEI raw absolute-pressure channels",
    ),
    "2011": (
        "2011-04-06",
        "nemo_2010_2011_center",
        "nemo_2009_2011_south",
        "uncorrected MGDS RawDep and Depth channels",
    ),
}


def main() -> None:
    """Fit the static ellipsoid response at Center for both event pairs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summary",
        type=Path,
        default=PROCESSED_DIR / "summary.json",
        help="daily raw BPR processing summary JSON",
    )
    parser.add_argument(
        "--surface-hdf5",
        type=Path,
        default=DEFAULT_SURFACE,
        help="1 MPa PyLith ellipsoid unit-response surface",
    )
    parser.add_argument(
        "--event",
        choices=("all", *EVENT_PAIRS),
        default="all",
        help="event to check (default: all available event pairs)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROCESSED_DIR,
        help="directory for ignored event JSON files",
    )
    args = parser.parse_args()
    if not args.surface_hdf5.exists():
        raise FileNotFoundError(
            f"missing PyLith surface response {args.surface_hdf5}; "
            "run make ellipsoid-unit-response first"
        )
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    deployments = {item.slug: item for item in DEPLOYMENTS}
    changes_by_key = {
        (row["eruption_date_utc"], row["station"]): row
        for row in summary["event_window_changes"]
    }
    events = EVENT_PAIRS if args.event == "all" else {args.event: EVENT_PAIRS[args.event]}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for event_name, (event_date, center_slug, south_slug, data_source) in events.items():
        center = deployments[center_slug]
        south = deployments[south_slug]
        center_change = changes_by_key.get((event_date, center.station))
        south_change = changes_by_key.get((event_date, south.station))
        if center_change is None or south_change is None:
            raise ValueError(f"{event_name} Center and South raw BPR event changes are required")

        east_offset_m, north_offset_m = local_east_north_offset_m(
            south.latitude,
            south.longitude,
            origin_latitude_deg=center.latitude,
            origin_longitude_deg=center.longitude,
        )
        center_response, south_response = read_ellipsoid_unit_response(
            args.surface_hdf5,
            central_xy_m=(0.0, 0.0),
            east_xy_m=(east_offset_m, north_offset_m),
        )
        result = compare_center_to_south_event(
            center_change["post_minus_pre_relative_uplift_m"],
            south_change["post_minus_pre_relative_uplift_m"],
            center_unit_response_m_per_mpa=float(center_response[2]),
            south_unit_response_m_per_mpa=float(south_response[2]),
            east_offset_m=east_offset_m,
            north_offset_m=north_offset_m,
        )
        result["eruption_date_utc"] = event_date
        result["center_station"] = center.station
        result["south_station"] = south.station
        result["event_pre_window_utc"] = center_change["pre_window_utc"]
        result["event_post_window_utc"] = center_change["post_window_utc"]
        result["daily_data_source"] = data_source
        result["tide_or_drift_correction_applied"] = False
        result["surface_response_hdf5"] = str(args.surface_hdf5)
        result["youngs_modulus_pa"] = 50.0e9
        result["poisson_ratio_assumed"] = 0.25
        result["reservoir_dimensions_km"] = [6.0, 3.0, 1.0]
        result["reservoir_center_depth_km"] = 1.6
        result["mesh_tetrahedra"] = 2761
        output = args.output_dir / f"historical_ellipsoid_{event_name}.json"
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        print(f"wrote {output}")


if __name__ == "__main__":
    main()
