"""Check raw historical BPR overlaps against a static PyLith ellipsoid response."""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from axialstress.bpr_mogi_calibration import local_east_north_offset_m
from axialstress.ellipsoid_bpr_calibration import read_ellipsoid_unit_response
from axialstress.historical_bpr import DAILY_HEADER, DEPLOYMENTS, PROCESSED_DIR
from axialstress.historical_ellipsoid_timeseries import (
    compare_center_to_south_ellipsoid_timeseries,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SURFACE = (
    ROOT
    / "pylith"
    / "step05_ellipsoid_elastic"
    / "output"
    / "ellipsoid-surface.h5"
)
DEPLOYMENT_PAIRS = {
    "1995_1996": ("wc68_1995", "wc69_1995"),
    "1995_1996_wc67": ("wc68_1995", "wc67_1995"),
    "2003_2005": ("nemo_2003_2005_center", "nemo_2003_2005_south"),
    "2005_2007": ("nemo_2004_2007_center", "nemo_2005_2007_south1"),
    "2007_2009": ("nemo_2007_2010_center", "nemo_2005_2009_south2"),
    "2007_2009_south1": ("nemo_2007_2010_center", "nemo_2007_2009_south1"),
    "2011_2013": ("nemo_2011_2013_center", "nemo_2011_2013_south"),
}


def read_valid_daily_depths(path: Path) -> dict[date, float]:
    """Read complete daily equivalent depths from original raw channels."""
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != DAILY_HEADER:
            raise ValueError(f"unexpected daily BPR schema in {path}")
        depths = {}
        for row_number, row in enumerate(reader, start=2):
            if not row["relative_uplift_m"]:
                continue
            try:
                day = date.fromisoformat(row["time_utc"][:10])
                depth_m = float(row["equivalent_depth_m"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid daily BPR row {row_number} in {path}") from exc
            if not math.isfinite(depth_m):
                raise ValueError(f"nonfinite daily BPR depth at row {row_number} in {path}")
            depths[day] = depth_m
    return depths


def write_comparison(
    name: str,
    center_slug: str,
    south_slug: str,
    deployments: dict,
    surface_hdf5: Path,
    output_dir: Path,
) -> dict[str, object]:
    """Write a Center-fit, South-held-out ellipsoid deployment comparison."""
    center = deployments[center_slug]
    south = deployments[south_slug]
    east_offset_m, north_offset_m = local_east_north_offset_m(
        south.latitude,
        south.longitude,
        origin_latitude_deg=center.latitude,
        origin_longitude_deg=center.longitude,
    )
    center_response, south_response = read_ellipsoid_unit_response(
        surface_hdf5,
        central_xy_m=(0.0, 0.0),
        east_xy_m=(east_offset_m, north_offset_m),
    )
    rows, summary = compare_center_to_south_ellipsoid_timeseries(
        read_valid_daily_depths(output_dir / f"{center_slug}.daily.csv"),
        read_valid_daily_depths(output_dir / f"{south_slug}.daily.csv"),
        center_unit_response_m_per_mpa=float(center_response[2]),
        south_unit_response_m_per_mpa=float(south_response[2]),
    )
    summary.update(
        {
            "comparison": name,
            "center_station": center.station,
            "south_station": south.station,
            "center_raw_channel": center.raw_channel,
            "south_raw_channel": south.raw_channel,
            "daily_data_source": "original raw NCEI or MGDS BPR channels",
            "south_offset_east_m": east_offset_m,
            "south_offset_north_m": north_offset_m,
            "surface_response_hdf5": str(surface_hdf5),
            "youngs_modulus_pa": 50.0e9,
            "poisson_ratio_assumed": 0.25,
            "reservoir_dimensions_km": [6.0, 3.0, 1.0],
            "reservoir_center_depth_km": 1.6,
            "mesh_tetrahedra": 2761,
            "publication_observations_or_results_used": False,
        }
    )
    csv_path = output_dir / f"historical_ellipsoid_deployments_{name}.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    json_path = output_dir / f"historical_ellipsoid_deployments_{name}.json"
    json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote {csv_path} and {json_path}")
    return summary


def plot_comparisons(output_dir: Path, figure_dir: Path, deployments: dict) -> tuple[Path, Path]:
    """Plot observed South uplift with its daily static Center-fit prediction."""
    figure, axes = plt.subplots(
        len(DEPLOYMENT_PAIRS),
        1,
        figsize=(11.5, 3.3 * len(DEPLOYMENT_PAIRS)),
        constrained_layout=True,
    )
    colors = {"observed": "#0072B2", "predicted": "#D55E00"}
    for axis, (name, (center_slug, south_slug)) in zip(
        axes, DEPLOYMENT_PAIRS.items(), strict=True
    ):
        path = output_dir / f"historical_ellipsoid_deployments_{name}.csv"
        with path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        times = [date.fromisoformat(row["time_utc"][:10]) for row in rows]
        observed = [float(row["south_observed_uplift_m"]) for row in rows]
        predicted = [float(row["south_predicted_uplift_m"]) for row in rows]
        axis.plot(times, observed, color=colors["observed"], linewidth=0.75, label="South observed")
        axis.plot(
            times,
            predicted,
            color=colors["predicted"],
            linewidth=0.95,
            label="South predicted from Center fit",
        )
        center = deployments[center_slug]
        south = deployments[south_slug]
        axis.set_title(f"{name.replace('_', '–')}: {center.station}; {south.station}")
        axis.set_ylabel("Relative elevation (m; up positive)")
        axis.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        axis.grid(True, color="#D9D9D9", linewidth=0.55)
        axis.legend(frameon=False, loc="best")
    axes[-1].set_xlabel("Date (UTC)")
    figure.suptitle(
        "Static elastic PyLith ellipsoid checks across raw non-OOI BPR deployments\n"
        "First seven paired days set the baseline; no tide or drift correction"
    )
    figure.autofmt_xdate()
    figure.text(
        0.5,
        -0.012,
        "Sources: NCEI DART raw BPR archive (doi:10.7289/V5F18WNS); "
        "MGDS IEDA/322282 (Chadwick and Nooner, 2015), CC BY-NC-SA 3.0.",
        ha="center",
        fontsize=7,
    )
    figure_dir.mkdir(parents=True, exist_ok=True)
    stem = figure_dir / "historical_ellipsoid_deployment_checks"
    png_path = stem.with_suffix(".png")
    pdf_path = stem.with_suffix(".pdf")
    figure.savefig(png_path, dpi=220, bbox_inches="tight")
    figure.savefig(pdf_path, bbox_inches="tight")
    plt.close(figure)
    return png_path, pdf_path


def main() -> None:
    """Compare PyLith unit responses with longer original raw BPR overlaps."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--surface-hdf5",
        type=Path,
        default=DEFAULT_SURFACE,
        help="1 MPa PyLith ellipsoid unit-response surface",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROCESSED_DIR,
        help="directory with ignored daily series and comparison outputs",
    )
    parser.add_argument(
        "--figure-dir",
        type=Path,
        default=ROOT / "figures",
        help="directory for the tracked PNG and PDF comparison figure",
    )
    args = parser.parse_args()
    if not args.surface_hdf5.exists():
        raise FileNotFoundError(
            f"missing PyLith surface response {args.surface_hdf5}; "
            "run make ellipsoid-unit-response first"
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    deployments = {deployment.slug: deployment for deployment in DEPLOYMENTS}
    for name, (center_slug, south_slug) in DEPLOYMENT_PAIRS.items():
        write_comparison(
            name,
            center_slug,
            south_slug,
            deployments,
            args.surface_hdf5,
            args.output_dir,
        )
    png_path, pdf_path = plot_comparisons(args.output_dir, args.figure_dir, deployments)
    print(f"wrote {png_path} and {pdf_path}")


if __name__ == "__main__":
    main()
