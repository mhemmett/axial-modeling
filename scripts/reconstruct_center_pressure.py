"""Fit a conditional 2011–2015 Center pressure history from cited BPR data."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

import h5py
import numpy as np

from axialstress.coordinates import (
    CENTRAL_CALDERA_LAT_LON_DEG,
    local_east_north_offset_m,
)
from axialstress.deployment_pressure import (
    DepthObservation,
    fit_deployment_relative_pressure,
)
from axialstress.paper_bpr import CANDIDATE_PROCESSED_CENTER_SOURCES, file_sha256
from axialstress.surface_interpolation import interpolate_triangular_surface

ROOT = Path(__file__).resolve().parents[1]
START_UTC = datetime(2011, 4, 13, tzinfo=UTC)
PREVIOUS_ERUPTION_UTC = datetime(2011, 4, 6, tzinfo=UTC)
ERUPTION_UTC = datetime(2015, 4, 24, tzinfo=UTC)
SOURCE_SLUGS = (
    "nemo_2010_2011_center",
    "nemo_2011_2013_center",
    "nemo_2013_2015_center",
)


def _grid(step_days: int) -> list[datetime]:
    """Return weekly or coarser UTC knots before the 2015 eruption."""
    if step_days < 1:
        raise ValueError("grid step must be at least one day")
    times = []
    current = START_UTC
    while current < ERUPTION_UTC:
        times.append(current)
        current += timedelta(days=step_days)
    return times


def _load_observations(
    processed_dir: Path, times: list[datetime]
) -> tuple[list[DepthObservation], list[dict[str, object]], dict[str, object]]:
    """Select only source observations at exact inversion-grid timestamps."""
    summary = json.loads((processed_dir / "summary.json").read_text(encoding="utf-8"))
    if summary.get("status") != "observations_exported":
        raise ValueError("processed BPR source export is incomplete")
    entries = {item["deployment"]: item for item in summary["deployments"]}
    grid_index = {when: index for index, when in enumerate(times)}
    records = []
    used_sources = []
    post_eruption_peak: tuple[float, datetime] | None = None
    for slug in SOURCE_SLUGS:
        entry = entries[slug]
        source = next(
            item for item in CANDIDATE_PROCESSED_CENTER_SOURCES if item.deployment.slug == slug
        )
        path = processed_dir / f"{slug}.hourly.csv"
        if (
            entry["source_channel"] != source.channel
            or entry["source_doi"] != source.doi
            or entry["source_sha256"] != file_sha256(source.deployment.path)
            or entry["output_sha256"] != file_sha256(path)
        ):
            raise ValueError(f"source provenance changed for {slug}; rerun make paper-bpr")
        selected = 0
        with path.open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                when = datetime.fromisoformat(row["time_utc"])
                depth_m = float(row["observed_depth_m"])
                if (
                    slug == SOURCE_SLUGS[0]
                    and PREVIOUS_ERUPTION_UTC <= when < PREVIOUS_ERUPTION_UTC + timedelta(days=14)
                    and (post_eruption_peak is None or depth_m > post_eruption_peak[0])
                ):
                    post_eruption_peak = (depth_m, when)
                index = grid_index.get(when)
                if index is not None:
                    records.append(DepthObservation(slug, index, depth_m))
                    selected += 1
        if selected < 2:
            raise ValueError(f"fewer than two grid observations for {slug}")
        used_sources.append(
            {
                "deployment": slug,
                "source_doi": entry["source_doi"],
                "source_channel": entry["source_channel"],
                "source_sha256": entry["source_sha256"],
                "processed_sha256": entry["output_sha256"],
                "selected_observations": selected,
                "latitude_longitude_deg": entry["source_coordinates_lat_lon_deg"],
            }
        )
    if post_eruption_peak is None or post_eruption_peak[1] >= START_UTC:
        raise ValueError("the chosen inflation baseline does not follow observed deflation")
    return (
        records,
        used_sources,
        {
            "maximum_depth_m": post_eruption_peak[0],
            "maximum_depth_time_utc": post_eruption_peak[1].isoformat(),
            "window_start_utc": PREVIOUS_ERUPTION_UTC.isoformat(),
            "window_end_utc": (PREVIOUS_ERUPTION_UTC + timedelta(days=14)).isoformat(),
        },
    )


def _static_compliance(surface_path: Path) -> dict[str, float]:
    """Sample PyLith's one-megapascal uplift at each BPR location."""
    with h5py.File(surface_path, "r") as surface:
        vertices = np.asarray(surface["geometry/vertices"], dtype=float)
        triangles = np.asarray(surface["viz/topology/cells"], dtype=np.int64)
        displacement = np.asarray(surface["vertex_fields/displacement"][-1], dtype=float)
    if displacement.shape != vertices.shape or not np.all(np.isfinite(displacement)):
        raise ValueError("static PyLith surface displacement is invalid")
    result = {}
    for source in CANDIDATE_PROCESSED_CENTER_SOURCES:
        slug = source.deployment.slug
        if slug not in SOURCE_SLUGS:
            continue
        east_m, north_m = local_east_north_offset_m(
            source.deployment.latitude,
            source.deployment.longitude,
            origin_latitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[0],
            origin_longitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[1],
        )
        value = float(
            interpolate_triangular_surface(vertices, triangles, displacement, (east_m, north_m))[2]
        )
        if not np.isfinite(value) or value <= 0.0:
            raise ValueError(f"nonpositive PyLith compliance at {slug}")
        result[slug] = value
    return result


def main() -> None:
    """Save observed Center differences and conditional PyLith pressure fits."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step-days", type=int, default=7)
    parser.add_argument(
        "--processed-dir", type=Path, default=ROOT / "data/processed/paper_center_bpr"
    )
    parser.add_argument(
        "--surface",
        type=Path,
        default=ROOT / "pylith/step05_ellipsoid_elastic/output/ellipsoid-surface.h5",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "data/processed/method_reconstruction_2011_2015"
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()) and not args.overwrite:
        raise FileExistsError(f"output directory is not empty: {args.output_dir}")
    times = _grid(args.step_days)
    observations, sources, deflation_peak = _load_observations(args.processed_dir, times)
    compliance = _static_compliance(args.surface)
    operators = {
        slug: np.diag(np.asarray([0.0] + [value] * (len(times) - 1)))
        for slug, value in compliance.items()
    }
    baseline = operators[SOURCE_SLUGS[0]]
    fits = {
        str(weight): fit_deployment_relative_pressure(
            baseline,
            observations,
            curvature_weight=weight,
            deployment_response=operators,
        )
        for weight in (0.1, 1.0, 10.0)
    }
    selected = fits["1.0"]
    support = Counter(item.time_index for item in observations)
    by_deployment = {
        slug: sorted(
            (item for item in observations if item.deployment == slug),
            key=lambda item: item.time_index,
        )
        for slug in SOURCE_SLUGS
    }
    deployment_changes = []
    for slug, items in by_deployment.items():
        uplift_change_m = items[0].depth_m - items[-1].depth_m
        deployment_changes.append(
            {
                "deployment": slug,
                "first_grid_time_utc": times[items[0].time_index].isoformat(),
                "last_grid_time_utc": times[items[-1].time_index].isoformat(),
                "observed_uplift_change_m": uplift_change_m,
                "static_elastic_pressure_change_mpa": uplift_change_m / compliance[slug],
            }
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    series_path = args.output_dir / "pressure_history.csv"
    with series_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            (
                "time_utc",
                "pressure_change_mpa",
                "pressure_weight_0p1_mpa",
                "pressure_weight_10_mpa",
                "source_observations_on_grid",
            )
        )
        for index, when in enumerate(times):
            writer.writerow(
                (
                    when.isoformat(),
                    selected.pressure_mpa[index],
                    fits["0.1"].pressure_mpa[index],
                    fits["10.0"].pressure_mpa[index],
                    support[index],
                )
            )
    residual_path = args.output_dir / "observation_fit.csv"
    with residual_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            (
                "deployment",
                "time_utc",
                "observed_relative_uplift_m",
                "modeled_relative_uplift_m",
                "residual_m",
            )
        )
        for label, index, observed, modeled in zip(
            selected.observation_deployments,
            selected.observation_time_indices,
            selected.observed_relative_uplift_m,
            selected.predicted_relative_uplift_m,
            strict=True,
        ):
            writer.writerow(
                (label, times[index].isoformat(), observed, modeled, modeled - observed)
            )
    summary = {
        "method": "deployment-relative elastic PyLith pressure inversion",
        "status": "conditional_pressure_history_not_failure_threshold",
        "paper_output_data_used": False,
        "cycle_start_utc": START_UTC.isoformat(),
        "previous_eruption_utc": PREVIOUS_ERUPTION_UTC.isoformat(),
        "start_selection": (
            "13 April 2011, after the maximum processed Center depth "
            "within 14 days of the 2011 eruption"
        ),
        "post_eruption_depth_maximum": deflation_peak,
        "last_grid_time_utc": times[-1].isoformat(),
        "eruption_utc": ERUPTION_UTC.isoformat(),
        "grid_step_days": args.step_days,
        "initial_pressure_change_mpa_assumption": 0.0,
        "curvature_weights": [0.1, 1.0, 10.0],
        "selected_curvature_weight": 1.0,
        "source_observations": sources,
        "static_surface_file": str(args.surface),
        "static_surface_sha256": file_sha256(args.surface),
        "site_compliance_m_per_mpa": compliance,
        "selected_fit_rmse_m": selected.rmse_m,
        "selected_design_rank": selected.design_rank,
        "pressure_parameter_count": len(times) - 1,
        "unidentified_pressure_dimensions_without_curvature": (
            len(times) - 1 - selected.design_rank
        ),
        "grid_points_without_source_observations": len(times) - len(support),
        "deployment_observed_changes": deployment_changes,
        "last_preeruption_pressure_mpa_by_weight": {
            weight: float(fit.pressure_mpa[-1]) for weight, fit in fits.items()
        },
        "pressure_range_mpa": [
            float(np.min(selected.pressure_mpa)),
            float(np.max(selected.pressure_mpa)),
        ],
        "limitations": [
            "Each deployment is referenced to its first selected observation; "
            "cross-deployment datums are not assigned.",
            "Unobserved gap pressure depends on the curvature weight and initial state.",
            "The static PyLith response uses a coarse, mechanically unconverged "
            "cavity mesh and fixed base.",
            "The pressure history cannot define an absolute lithostatic stress "
            "or a failure threshold.",
        ],
        "pressure_history_csv": series_path.name,
        "observation_fit_csv": residual_path.name,
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                key: summary[key]
                for key in (
                    "status",
                    "selected_fit_rmse_m",
                    "selected_design_rank",
                    "pressure_parameter_count",
                    "pressure_range_mpa",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
