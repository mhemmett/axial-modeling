"""Fit Center BPR loading with source-value Maxwell PyLith response kernels."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import h5py
import numpy as np
import reconstruct_center_pressure as center
import source_value_maxwell_cases as maxwell

from axialstress.coordinates import CENTRAL_CALDERA_LAT_LON_DEG, local_east_north_offset_m
from axialstress.deployment_pressure import fit_deployment_relative_pressure
from axialstress.failure_analysis import analyze_stress_history
from axialstress.material_database import write_single_maxwell_database
from axialstress.maxwell_pressure_inversion import ramp_response_operator
from axialstress.paper_bpr import CANDIDATE_PROCESSED_CENTER_SOURCES, file_sha256
from axialstress.surface_interpolation import interpolate_triangular_surface
from axialstress.thermal_model import _read_gmsh_tetrahedral_mesh

ROOT = Path(__file__).resolve().parents[1]
BASIS = ROOT / "data" / "processed" / "refined_elastic_basis_400m"
OUTPUT = ROOT / "data" / "processed" / "source_value_bpr_failure_2011_2015"


def _surface_responses(
    path: Path, expected_times_s: np.ndarray
) -> dict[str, np.ndarray]:
    """Sample saved PyLith uplift at each Center deployment coordinate."""
    with h5py.File(path, "r") as surface:
        times_s = np.asarray(surface["time"], dtype=float).reshape(-1)
        vertices = np.asarray(surface["geometry/vertices"], dtype=float)
        triangles = np.asarray(surface["viz/topology/cells"], dtype=np.int64)
        displacement = np.asarray(surface["vertex_fields/displacement"], dtype=float)
    if times_s.shape != expected_times_s.shape or not np.allclose(
        times_s, expected_times_s, rtol=0.0, atol=0.01
    ):
        raise ValueError("PyLith output does not match the Center BPR pressure grid")
    responses = {}
    for source in CANDIDATE_PROCESSED_CENTER_SOURCES:
        slug = source.deployment.slug
        if slug not in center.SOURCE_SLUGS:
            continue
        east_m, north_m = local_east_north_offset_m(
            source.deployment.latitude,
            source.deployment.longitude,
            origin_latitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[0],
            origin_longitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[1],
        )
        responses[slug] = np.asarray(
            [
                interpolate_triangular_surface(
                    vertices, triangles, field, (east_m, north_m)
                )[2]
                for field in displacement
            ]
        )
    if set(responses) != set(center.SOURCE_SLUGS):
        raise ValueError("surface response is missing a Center deployment")
    return responses


def _pressure_operators(
    response_by_deployment: dict[str, np.ndarray], count: int
) -> dict[str, np.ndarray]:
    """Embed causal PyLith ramp operators in a zero-pressure baseline grid."""
    operators = {}
    for slug, response in response_by_deployment.items():
        if response.shape != (count - 1,):
            raise ValueError("unit ramp response length differs from BPR grid")
        operator = np.zeros((count, count))
        operator[1:, 1:] = ramp_response_operator(response)
        operators[slug] = operator
    return operators


def _failure_summary(
    material_path: Path, equilibrium_path: Path
) -> tuple[np.ndarray, list[dict[str, object]]]:
    """Add the identical-mesh gravity equilibrium and assess each saved state."""
    times_s, vertices, cells, stress = maxwell._read_stress(material_path)
    reference = maxwell._reference_stress(equilibrium_path, vertices, cells)
    analysis = analyze_stress_history(
        vertices,
        cells,
        stress + reference[np.newaxis],
        times_s,
        cohesion_pa=1.0e6,
        friction_angle_deg=25.0,
        pore_pressure_pa=0.0,
    )
    return times_s, analysis["records"]


def main() -> None:
    """Save self-consistent BPR fits and conditional failure histories."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--basis-dir", type=Path, default=BASIS)
    parser.add_argument(
        "--processed-dir", type=Path, default=ROOT / "data/processed/paper_center_bpr"
    )
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--uniform-viscosity-pa-s", type=float)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    args.basis_dir = args.basis_dir.resolve()
    args.processed_dir = args.processed_dir.resolve()
    args.output_dir = args.output_dir.resolve()
    if args.output_dir.exists() and any(args.output_dir.iterdir()) and not args.overwrite:
        raise FileExistsError(f"output directory is not empty: {args.output_dir}")
    if args.uniform_viscosity_pa_s is not None and (
        not np.isfinite(args.uniform_viscosity_pa_s) or args.uniform_viscosity_pa_s <= 0.0
    ):
        raise ValueError("uniform viscosity must be finite and positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    mesh_path = args.basis_dir / "axial_ellipsoid.msh"
    equilibrium_path = args.basis_dir / "fixed-base-equilibrium-material.h5"
    vertices, cells, _ = _read_gmsh_tetrahedral_mesh(mesh_path)
    dates = center._grid(7)
    observations, sources, deflation_peak = center._load_observations(
        args.processed_dir, dates
    )
    elapsed_s = np.asarray([(date - dates[0]).total_seconds() for date in dates])
    time_step_s = 7.0 * maxwell.SECONDS_PER_DAY
    if not np.allclose(np.diff(elapsed_s), time_step_s, rtol=0.0, atol=0.01):
        raise ValueError("BPR grid must have equal seven-day intervals")
    cases = ["thermal_maxwell", "hydrothermal_maxwell"]
    if args.uniform_viscosity_pa_s is not None:
        cases.insert(0, "constant_maxwell")
    results = {}
    for case in cases:
        modulus, viscosity, properties = maxwell._case_properties(
            case,
            mesh_path,
            args.output_dir,
            vertices,
            cells,
            args.uniform_viscosity_pa_s,
        )
        material_db = args.output_dir / "materials" / f"{case}.spatialdb"
        material_db.parent.mkdir(parents=True, exist_ok=True)
        write_single_maxwell_database(
            material_db,
            vertices,
            cells,
            modulus,
            viscosity,
            density_kg_m3=maxwell.DENSITY_KG_M3,
            poisson_ratio=maxwell.POISSON_RATIO,
        )
        unit_dir = args.output_dir / "runs" / case / "unit_ramp"
        maxwell._write_run(
            unit_dir,
            mesh_path,
            material_db,
            elapsed_seconds=elapsed_s,
            pressure_mpa=np.concatenate(([0.0], np.ones(len(dates) - 1))),
            time_step_s=time_step_s,
        )
        maxwell._run_pylith(unit_dir)
        responses = _surface_responses(
            unit_dir / "output" / "maxwell-surface.h5", elapsed_s[1:]
        )
        operators = _pressure_operators(responses, len(dates))
        fits = {
            str(weight): fit_deployment_relative_pressure(
                operators[center.SOURCE_SLUGS[0]],
                observations,
                curvature_weight=weight,
                deployment_response=operators,
            )
            for weight in (0.1, 1.0, 10.0)
        }
        fit = fits["1.0"]
        forward_dir = args.output_dir / "runs" / case / "bpr_pressure"
        maxwell._write_run(
            forward_dir,
            mesh_path,
            material_db,
            elapsed_seconds=elapsed_s,
            pressure_mpa=fit.pressure_mpa,
            time_step_s=time_step_s,
        )
        maxwell._run_pylith(forward_dir)
        modeled = _surface_responses(
            forward_dir / "output" / "maxwell-surface.h5", elapsed_s[1:]
        )
        fit_operator = operators[center.SOURCE_SLUGS[0]]
        predicted = fit_operator @ fit.pressure_mpa
        actual = np.concatenate(([0.0], modeled[center.SOURCE_SLUGS[0]]))
        superposition_error = float(
            np.linalg.norm(actual - predicted)
            / max(np.linalg.norm(actual), np.finfo(float).eps)
        )
        if superposition_error > 0.02:
            raise ValueError(f"{case} forward PyLith run failed linear superposition")
        stress_times_s, failure = _failure_summary(
            forward_dir / "output" / "maxwell-material.h5", equilibrium_path
        )
        if not np.allclose(stress_times_s, elapsed_s[1:], rtol=0.0, atol=0.01):
            raise ValueError("PyLith stress times differ from the BPR grid")
        series_path = args.output_dir / f"{case}_pressure_failure.csv"
        with series_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(
                (
                    "time_utc",
                    "pressure_change_mpa",
                    "pressure_weight_0p1_mpa",
                    "pressure_weight_10_mpa",
                    "center_uplift_m",
                    "maximum_cavity_principal_stress_pa",
                    "connected_shear_path",
                    "joint_failure_zero_tensile_strength",
                )
            )
            for index, record in enumerate(failure, start=1):
                principal = float(record["maximum_cavity_principal_stress_pa"])
                path = bool(record["cavity_to_surface_shear_path_found"])
                writer.writerow(
                    (
                        dates[index].isoformat(),
                        fit.pressure_mpa[index],
                        fits["0.1"].pressure_mpa[index],
                        fits["10.0"].pressure_mpa[index],
                        actual[index],
                        principal,
                        path,
                        principal > 0.0 and path,
                    )
                )
        first_joint = next(
            (
                index
                for index, record in enumerate(failure, start=1)
                if float(record["maximum_cavity_principal_stress_pa"]) > 0.0
                and record["cavity_to_surface_shear_path_found"]
            ),
            None,
        )
        results[case] = {
            "property_notes": properties,
            "material_sha256": file_sha256(material_db),
            "youngs_modulus_range_pa": [float(modulus.min()), float(modulus.max())],
            "viscosity_range_pa_s": [float(viscosity.min()), float(viscosity.max())],
            "minimum_maxwell_time_s": float(
                np.min(viscosity * 2.0 * (1.0 + maxwell.POISSON_RATIO) / modulus)
            ),
            "time_step_s": time_step_s,
            "time_step_to_shortest_maxwell_time_ratio": float(
                time_step_s
                / np.min(viscosity * 2.0 * (1.0 + maxwell.POISSON_RATIO) / modulus)
            ),
            "fit_rmse_m": fit.rmse_m,
            "fit_design_rank": fit.design_rank,
            "forward_superposition_relative_l2_error": superposition_error,
            "last_preeruption_pressure_mpa_by_weight": {
                weight: float(item.pressure_mpa[-1]) for weight, item in fits.items()
            },
            "first_sampled_joint_failure_utc": (
                dates[first_joint].isoformat() if first_joint is not None else None
            ),
            "first_sampled_joint_failure_pressure_mpa": (
                float(fit.pressure_mpa[first_joint]) if first_joint is not None else None
            ),
            "last_cavity_principal_stress_pa": float(
                failure[-1]["maximum_cavity_principal_stress_pa"]
            ),
            "last_connected_shear_path": bool(
                failure[-1]["cavity_to_surface_shear_path_found"]
            ),
            "unit_surface_sha256": file_sha256(
                unit_dir / "output" / "maxwell-surface.h5"
            ),
            "forward_material_sha256": file_sha256(
                forward_dir / "output" / "maxwell-material.h5"
            ),
            "pressure_failure_csv": series_path.name,
        }
        print(f"{case}: BPR RMSE {fit.rmse_m:.4g} m", flush=True)
    summary = {
        "method": "deployment-relative BPR fit to source-value PyLith Maxwell kernels",
        "status": "conditional_bpr_failure_reconstruction_temporally_unresolved",
        "paper_output_data_used": False,
        "cycle_start_utc": dates[0].isoformat(),
        "last_grid_time_utc": dates[-1].isoformat(),
        "eruption_utc": center.ERUPTION_UTC.isoformat(),
        "post_2011_deflation_peak": deflation_peak,
        "source_observations": sources,
        "mesh_tetrahedra": len(cells),
        "mesh_sha256": file_sha256(mesh_path),
        "equilibrium_sha256": file_sha256(equilibrium_path),
        "initial_pressure_change_mpa_assumption": 0.0,
        "density_kg_m3_assumption": maxwell.DENSITY_KG_M3,
        "poisson_ratio_assumption": maxwell.POISSON_RATIO,
        "one_branch_maxwell_assumption": True,
        "basal_treatment": "fixed base and gravity-equilibrated elastic reference stress",
        "initial_viscous_strain_assumption": 0.0,
        "constant_viscosity_case_requires_explicit_input": args.uniform_viscosity_pa_s is None,
        "curvature_weights": [0.1, 1.0, 10.0],
        "cases": results,
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": summary["status"], "cases": list(results)}, indent=2))


if __name__ == "__main__":
    main()
