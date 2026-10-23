"""Screen 1998–2011 archived Center BPR loading with elastic PyLith stress."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import h5py
import numpy as np
import source_value_historical_cycle_failure as historical

from axialstress.coordinates import CENTRAL_CALDERA_LAT_LON_DEG, local_east_north_offset_m
from axialstress.deployment_pressure import fit_deployment_relative_pressure
from axialstress.failure_analysis import analyze_stress_history
from axialstress.paper_bpr import CANDIDATE_PROCESSED_CENTER_SOURCES, file_sha256
from axialstress.surface_interpolation import interpolate_triangular_surface

ROOT = Path(__file__).resolve().parents[1]
BASIS = ROOT / "data/processed/refined_elastic_basis_400m"
OUTPUT = ROOT / "data/processed/elastic_bpr_failure_1998_2011"


def main() -> None:
    """Fit deployment-relative depths and screen every saved elastic stress state."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observation-dir", type=Path, default=historical.OBS)
    parser.add_argument("--basis-dir", type=Path, default=BASIS)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    basis_dir = args.basis_dir.resolve()
    output_dir = args.output_dir.resolve()
    dates, observations, provenance = historical._observations(args.observation_dir.resolve())
    basis_path = basis_dir / "basis_summary.json"
    basis = json.loads(basis_path.read_text(encoding="utf-8"))
    reference_path = basis_dir / "fixed-base-equilibrium-material.h5"
    loaded_path = basis_dir / "fixed-base-material.h5"
    surface_path = basis_dir / "fixed-base-surface.h5"
    if basis.get("paper_output_data_used") is not False or any(
        basis["output_sha256"][path.name] != file_sha256(path)
        for path in (reference_path, loaded_path, surface_path)
    ):
        raise ValueError("elastic PyLith basis or its provenance changed")
    with h5py.File(surface_path, "r") as surface:
        surface_vertices = np.asarray(surface["geometry/vertices"], dtype=float)
        triangles = np.asarray(surface["viz/topology/cells"], dtype=np.int64)
        displacement = np.asarray(surface["vertex_fields/displacement"][-1], dtype=float)
    registry = {item.deployment.slug: item for item in CANDIDATE_PROCESSED_CENTER_SOURCES}
    operators = {}
    compliance = {}
    for slug in historical.SLUGS:
        station = registry[slug].deployment
        site = local_east_north_offset_m(
            station.latitude,
            station.longitude,
            origin_latitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[0],
            origin_longitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[1],
        )
        value = float(
            interpolate_triangular_surface(surface_vertices, triangles, displacement, site)[2]
        )
        if value <= 0.0:
            raise ValueError(f"nonpositive elastic uplift compliance for {slug}")
        compliance[slug] = value
        operators[slug] = np.diag([0.0] + [value] * (len(dates) - 1))
    fit = fit_deployment_relative_pressure(
        operators[historical.SLUGS[0]],
        observations,
        curvature_weight=1.0,
        deployment_response=operators,
    )
    with h5py.File(reference_path, "r") as material:
        vertices = np.asarray(material["geometry/vertices"], dtype=float)
        cells = np.asarray(material["viz/topology/cells"], dtype=np.int64)
        reference = np.asarray(material["cell_fields/cauchy_stress"][-1], dtype=float)
    with h5py.File(loaded_path, "r") as material:
        if not np.array_equal(vertices, material["geometry/vertices"][:]) or not np.array_equal(
            cells, material["viz/topology/cells"][:]
        ):
            raise ValueError("elastic basis meshes differ")
        loaded = np.asarray(material["cell_fields/cauchy_stress"][-1], dtype=float)
    stress = (
        reference[np.newaxis]
        + fit.pressure_mpa[:, np.newaxis, np.newaxis] * (loaded - reference)[np.newaxis]
    )
    elapsed_s = np.arange(len(dates), dtype=float) * 7.0 * 86400.0
    analysis = analyze_stress_history(
        vertices,
        cells,
        stress,
        elapsed_s,
        cohesion_pa=1.0e6,
        friction_angle_deg=25.0,
        pore_pressure_pa=0.0,
    )
    records = analysis["records"]
    output_dir.mkdir(parents=True, exist_ok=True)
    series_path = output_dir / "pressure_failure.csv"
    with series_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            (
                "time_utc",
                "pressure_change_mpa",
                "maximum_cavity_principal_stress_pa",
                "connected_shear_path",
                "joint_failure_zero_tensile_strength",
            )
        )
        for date, pressure_mpa, record in zip(dates, fit.pressure_mpa, records, strict=True):
            principal = float(record["maximum_cavity_principal_stress_pa"])
            path = bool(record["cavity_to_surface_shear_path_found"])
            writer.writerow(
                (date.isoformat(), pressure_mpa, principal, path, principal > 0.0 and path)
            )
    first = next(
        (
            i
            for i, record in enumerate(records)
            if record["maximum_cavity_principal_stress_pa"] > 0.0
            and record["cavity_to_surface_shear_path_found"]
        ),
        None,
    )
    result = {
        "method": "archived Center deployment-relative static elastic PyLith pressure fit",
        "status": "conditional_mesh_resolution_failure_screen",
        "paper_output_data_used": False,
        "observation_provenance": provenance,
        "basis_summary_sha256": file_sha256(basis_path),
        "mesh_tetrahedra": basis["mesh_tetrahedra"],
        "gravity_reference_sha256": file_sha256(reference_path),
        "one_mpa_stress_sha256": file_sha256(loaded_path),
        "one_mpa_surface_sha256": file_sha256(surface_path),
        "cycle_start_utc": dates[0].isoformat(),
        "last_grid_utc": dates[-1].isoformat(),
        "observed_eruption_utc": historical.LAST_UTC.isoformat(),
        "selected_weekly_observations": len(observations),
        "fit_rmse_m": fit.rmse_m,
        "fit_design_rank": fit.design_rank,
        "static_compliance_m_per_mpa": compliance,
        "first_sampled_joint_failure_utc": dates[first].isoformat() if first is not None else None,
        "first_sampled_joint_failure_pressure_mpa": float(fit.pressure_mpa[first])
        if first is not None
        else None,
        "first_joint_path_cell_indices": list(
            map(int, records[first]["cavity_to_surface_path_cell_indices"])
        )
        if first is not None
        else [],
        "last_pressure_mpa": float(fit.pressure_mpa[-1]),
        "last_cavity_principal_stress_pa": float(records[-1]["maximum_cavity_principal_stress_pa"]),
        "series_sha256": file_sha256(series_path),
        "limitations": (
            "The 1998–2000 observation gap and separate deployment datums leave the "
            "fitted pressure in gaps dependent on curvature smoothing. The stress "
            "screen requires comparison across cavity mesh resolutions."
        ),
    }
    (output_dir / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["first_sampled_joint_failure_utc"], result["last_pressure_mpa"])


if __name__ == "__main__":
    main()
