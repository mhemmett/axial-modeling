"""Check raw 2011 BPR event changes against a PyLith ellipsoid response."""

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


def main() -> None:
    """Calibrate the static ellipsoid response at Center and predict South."""
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
        "--output",
        type=Path,
        default=PROCESSED_DIR / "historical_ellipsoid_2011.json",
        help="local JSON output path",
    )
    args = parser.parse_args()
    if not args.surface_hdf5.exists():
        raise FileNotFoundError(
            f"missing PyLith surface response {args.surface_hdf5}; "
            "run make ellipsoid-unit-response first"
        )
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
        changes[center.station]["post_minus_pre_relative_uplift_m"],
        changes[south.station]["post_minus_pre_relative_uplift_m"],
        center_unit_response_m_per_mpa=float(center_response[2]),
        south_unit_response_m_per_mpa=float(south_response[2]),
        east_offset_m=east_offset_m,
        north_offset_m=north_offset_m,
    )
    result["eruption_date_utc"] = "2011-04-06"
    result["event_pre_window_utc"] = changes[center.station]["pre_window_utc"]
    result["event_post_window_utc"] = changes[center.station]["post_window_utc"]
    result["daily_data_source"] = "uncorrected MGDS RawDep and Depth channels"
    result["tide_or_drift_correction_applied"] = False
    result["surface_response_hdf5"] = str(args.surface_hdf5)
    result["youngs_modulus_pa"] = 50.0e9
    result["poisson_ratio_assumed"] = 0.25
    result["reservoir_dimensions_km"] = [6.0, 3.0, 1.0]
    result["reservoir_center_depth_km"] = 1.6
    result["mesh_tetrahedra"] = 2761
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
