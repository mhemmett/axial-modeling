"""Check 1987–1996 raw NCEI BPR overlaps with PyLith ellipsoid compliance."""

from __future__ import annotations

import json
import math
import re
import shlex
import shutil
import statistics
import subprocess
import sys
import time
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

import gmsh

from axialstress.bpr_mogi_calibration import (
    CENTRAL_CALDERA_LAT_LON_DEG,
    local_east_north_offset_m,
)
from axialstress.ellipsoid_bpr_calibration import read_ellipsoid_unit_response
from axialstress.historical_bpr import (
    DEPLOYMENTS,
    EARLIER_NCEI_DEPLOYMENTS,
    MINIMUM_WINDOW_DAYS,
    Deployment,
    process_deployment,
)

ROOT = Path(__file__).resolve().parents[1]
STEP_DIR = ROOT / "pylith" / "step05_ellipsoid_elastic"
PYLITH_ROOT = ROOT / "pylith" / "pylith-5.0.2-linux-x86_64"
OUTPUT_PATH = ROOT / "data" / "processed" / "axial_historical_bpr" / "early_ncei_spatial_check.json"
MAX_TETRAHEDRA = 4_500
DEPLOYMENT_PAIRS = (
    ("1993_1994", "wc51_1993", "wc61_1994"),
    ("1995_1996_wc69", "wc68_1995", "wc69_1995"),
    ("1995_1996_wc67", "wc68_1995", "wc67_1995"),
)
EARLY_DEPLOYMENTS = tuple(
    item
    for item in DEPLOYMENTS
    if item.slug in {row[0] for row in EARLIER_NCEI_DEPLOYMENTS}
)


def _tail(path: Path, lines: int = 20) -> str:
    """Return the final solver-log lines when a bounded solve fails."""
    return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])


def _coordinate(deployment: Deployment) -> tuple[float, float]:
    """Return the station's local east/north position relative to the source."""
    return local_east_north_offset_m(
        deployment.latitude,
        deployment.longitude,
        origin_latitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[0],
        origin_longitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[1],
    )


def _mesh_has_station_vertices(mesh_path: Path, deployments: tuple[Deployment, ...]) -> bool:
    """Check that every requested coordinate is a top-surface mesh vertex."""
    gmsh.initialize()
    try:
        gmsh.open(str(mesh_path))
        top_faces = []
        for dimension, physical_tag in gmsh.model.getPhysicalGroups(2):
            if gmsh.model.getPhysicalName(dimension, physical_tag) == "top":
                top_faces.extend(
                    int(tag)
                    for tag in gmsh.model.getEntitiesForPhysicalGroup(dimension, physical_tag)
                )
        node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
        coordinate_by_tag = {
            int(tag): (float(coordinates[3 * index]), float(coordinates[3 * index + 1]))
            for index, tag in enumerate(node_tags)
        }
        top_node_tags: set[int] = set()
        for face in top_faces:
            _, _, element_nodes = gmsh.model.mesh.getElements(2, face)
            for nodes in element_nodes:
                top_node_tags.update(int(tag) for tag in nodes)
        top_coordinates = [coordinate_by_tag[tag] for tag in top_node_tags]
        return all(
            min(math.hypot(x - east_m, y - north_m) for x, y in top_coordinates) <= 1.0e-6
            for east_m, north_m in (_coordinate(item) for item in deployments)
        )
    finally:
        gmsh.finalize()


def _run_unit_response(deployments: tuple[Deployment, ...]) -> tuple[int, dict[str, float]]:
    """Build one station-focused mesh and solve a 1 MPa PyLith load."""
    if not (PYLITH_ROOT / "setup.sh").is_file():
        raise SystemExit("PyLith is not installed; run make install-pylith first")
    with TemporaryDirectory(prefix="axial-early-bpr-") as temporary:
        run_dir = Path(temporary)
        (run_dir / "mesh").mkdir()
        (run_dir / "output").mkdir()
        for filename in (
            "step05.cfg",
            "pylithapp.cfg",
            "bc_cavity.spatialdb",
            "bc_zero.spatialdb",
            "mat_elastic.spatialdb",
        ):
            shutil.copy2(STEP_DIR / filename, run_dir / filename)

        mesh_path = run_dir / "mesh" / "axial_ellipsoid.msh"
        mesh_log = run_dir / "output" / "mesh.log"
        mesh_command = [
            sys.executable,
            str(ROOT / "meshing" / "axial_ellipsoid_bpr.py"),
            "--output",
            str(mesh_path),
            "--lc-near",
            "1200",
            "--lc-far",
            "10000",
            "--max-tetrahedra",
            str(MAX_TETRAHEDRA),
            "--station-refinement-size",
            "300",
        ]
        for deployment in deployments:
            mesh_command.extend(
                [
                    "--embed-station-coordinate",
                    f"{deployment.latitude},{deployment.longitude}",
                ]
            )
        with mesh_log.open("w", encoding="utf-8") as log:
            mesh_result = subprocess.run(
                mesh_command,
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
        mesh_output = mesh_log.read_text(encoding="utf-8", errors="replace")
        if mesh_result.returncode:
            raise RuntimeError(f"Gmsh mesh build failed:\n{mesh_output[-2_000:]}")
        match = re.search(r"Wrote .*: (\d+) tetrahedra", mesh_output)
        if match is None:
            raise RuntimeError(f"mesh count missing from {mesh_log}")
        tetrahedra = int(match.group(1))
        if tetrahedra > MAX_TETRAHEDRA:
            raise RuntimeError(f"mesh exceeded its {MAX_TETRAHEDRA}-tetrahedron cap")
        if not _mesh_has_station_vertices(mesh_path, deployments):
            raise RuntimeError("one or more BPR coordinates are absent from the top mesh")

        solver_log = run_dir / "output" / "pylith.log"
        solver_command = (
            f"cd {shlex.quote(str(PYLITH_ROOT))} && source setup.sh && "
            f"cd {shlex.quote(str(run_dir))} && timeout 300 pylith step05.cfg"
        )
        with solver_log.open("w", encoding="utf-8") as log:
            completed = subprocess.run(
                ["bash", "-lc", solver_command],
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
        if completed.returncode:
            raise RuntimeError(f"PyLith unit-response solve failed:\n{_tail(solver_log)}")

        surface = run_dir / "output" / "ellipsoid-surface.h5"
        compliance = {}
        for deployment in deployments:
            station_xy = _coordinate(deployment)
            response, _ = read_ellipsoid_unit_response(surface, central_xy_m=station_xy)
            compliance[deployment.slug] = float(response[2])
        return tetrahedra, compliance


def _compare_pair(
    fit: Deployment,
    holdout: Deployment,
    fit_depth: dict[date, float],
    holdout_depth: dict[date, float],
    compliance: dict[str, float],
) -> dict[str, object]:
    """Fit static pressure at one raw BPR and predict an overlapping holdout."""
    common_days = sorted(fit_depth.keys() & holdout_depth.keys())
    if len(common_days) < MINIMUM_WINDOW_DAYS:
        raise ValueError(f"{fit.station} and {holdout.station} have too few overlapping days")
    baseline_days = common_days[:7]
    fit_reference_m = statistics.median(fit_depth[day] for day in baseline_days)
    holdout_reference_m = statistics.median(holdout_depth[day] for day in baseline_days)
    pressure = [
        (fit_reference_m - fit_depth[day]) / compliance[fit.slug]
        for day in common_days
    ]
    observed = [holdout_reference_m - holdout_depth[day] for day in common_days]
    predicted = [value * compliance[holdout.slug] for value in pressure]
    residuals = [obs - pred for obs, pred in zip(observed, predicted, strict=True)]
    observed_mean = statistics.fmean(observed)
    predicted_mean = statistics.fmean(predicted)
    covariance = statistics.fmean(
        (obs - observed_mean) * (pred - predicted_mean)
        for obs, pred in zip(observed, predicted, strict=True)
    )
    observed_variance = statistics.pvariance(observed)
    predicted_variance = statistics.pvariance(predicted)
    correlation = (
        covariance / math.sqrt(observed_variance * predicted_variance)
        if observed_variance > 0.0 and predicted_variance > 0.0
        else None
    )
    return {
        "fit_station_slug": fit.slug,
        "fit_station": fit.station,
        "holdout_station_slug": holdout.slug,
        "holdout_station": holdout.station,
        "overlap_start_utc": common_days[0].isoformat(),
        "overlap_end_utc": common_days[-1].isoformat(),
        "paired_daily_samples": len(common_days),
        "baseline_days": [baseline_days[0].isoformat(), baseline_days[-1].isoformat()],
        "fit_compliance_m_per_mpa": compliance[fit.slug],
        "holdout_compliance_m_per_mpa": compliance[holdout.slug],
        "fitted_pressure_min_mpa": min(pressure),
        "fitted_pressure_max_mpa": max(pressure),
        "holdout_rmse_m": math.sqrt(statistics.fmean(value**2 for value in residuals)),
        "holdout_bias_m": statistics.fmean(residuals),
        "holdout_correlation": correlation,
    }


def main() -> None:
    """Run raw-only overlap checks spanning the 1987–1996 NCEI BPR archive."""
    started = time.perf_counter()
    tetrahedra, compliance = _run_unit_response(EARLY_DEPLOYMENTS)
    observations = {item.slug: process_deployment(item) for item in EARLY_DEPLOYMENTS}
    daily = {
        slug: {
            row.day: row.equivalent_depth_m
            for row in rows
            if row.relative_uplift_m is not None
        }
        for slug, rows in observations.items()
    }
    deployments = {item.slug: item for item in EARLY_DEPLOYMENTS}
    pairs = []
    for name, fit_slug, holdout_slug in DEPLOYMENT_PAIRS:
        result = _compare_pair(
            deployments[fit_slug],
            deployments[holdout_slug],
            daily[fit_slug],
            daily[holdout_slug],
            compliance,
        )
        result["comparison"] = name
        pairs.append(result)

    coverage = []
    for item in EARLY_DEPLOYMENTS:
        rows = observations[item.slug]
        valid = [row for row in rows if row.relative_uplift_m is not None]
        baseline_depth_m = statistics.median(
            row.equivalent_depth_m for row in valid[:7]
        )
        pressure_change_mpa = [
            (baseline_depth_m - row.equivalent_depth_m) / compliance[item.slug]
            for row in valid
        ]
        coverage.append(
            {
                "station_slug": item.slug,
                "station": item.station,
                "raw_channel": item.raw_channel,
                "source_file": item.filename,
                "latitude_deg": item.latitude,
                "longitude_deg": item.longitude,
                "first_valid_day": valid[0].day.isoformat(),
                "last_valid_day": valid[-1].day.isoformat(),
                "valid_daily_samples": len(valid),
                "unit_compliance_m_per_mpa": compliance[item.slug],
                "single_station_fit_pressure_min_mpa": min(pressure_change_mpa),
                "single_station_fit_pressure_max_mpa": max(pressure_change_mpa),
                "single_station_fit_is_independent_validation": False,
            }
        )

    result = {
        "method": (
            "static PyLith ellipsoid fit at original raw NCEI BPRs with overlapping "
            "deployments held out"
        ),
        "source": "NOAA/NCEI original seafloor_pressure_abs_raw [dbar] only",
        "publication_associated_data_used": False,
        "time_coverage": [coverage[0]["first_valid_day"], coverage[-1]["last_valid_day"]],
        "mesh_tetrahedra": tetrahedra,
        "mesh_station_points_embedded": True,
        "mesh_tetrahedron_cap": MAX_TETRAHEDRA,
        "runtime_seconds": time.perf_counter() - started,
        "domain_dimensions_km": [40, 40, 20],
        "material_assumptions": {
            "youngs_modulus_pa": 50.0e9,
            "poisson_ratio": 0.25,
            "reservoir_dimensions_km": [6.0, 3.0, 1.0],
            "reservoir_center_depth_km": 1.6,
        },
        "deployment_coverage": coverage,
        "overlap_checks": pairs,
        "limitations": [
            "static elasticity omits viscoelastic memory",
            "daily raw means retain ocean tides, ocean variability, and instrument drift",
            "each deployment has an independent baseline, not a continuous deformation series",
            "most 1987–1993 deployments lack simultaneous BPR holdouts",
            "the independently generated mesh is station-focused but not mesh-converged",
            "pressure fits use the calibration station and are not physical pressure estimates",
        ],
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
