"""Measure source-value Maxwell response sensitivity to mechanical time step."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import h5py
import numpy as np
import source_value_maxwell_cases as maxwell

from axialstress.failure_analysis import analyze_stress_field
from axialstress.paper_bpr import file_sha256
from axialstress.surface_interpolation import interpolate_triangular_surface

ROOT = Path(__file__).resolve().parents[1]
BPR_OUTPUT = ROOT / "data" / "processed" / "source_value_bpr_failure_2011_2015"
BASIS = ROOT / "data" / "processed" / "refined_elastic_basis_400m"
STEP_SECONDS = (604_800.0, 86_400.0, 21_600.0, 3_600.0, 1_800.0)


def _central_uplift(path: Path) -> float:
    """Sample final PyLith vertical displacement at the caldera origin."""
    with h5py.File(path, "r") as surface:
        vertices = np.asarray(surface["geometry/vertices"], dtype=float)
        triangles = np.asarray(surface["viz/topology/cells"], dtype=np.int64)
        displacement = np.asarray(surface["vertex_fields/displacement"][-1], dtype=float)
    return float(
        interpolate_triangular_surface(vertices, triangles, displacement, (0.0, 0.0))[2]
    )


def main() -> None:
    """Save seven-day ramp stress and uplift changes across five step sizes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bpr-output", type=Path, default=BPR_OUTPUT)
    parser.add_argument("--basis-dir", type=Path, default=BASIS)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    args.bpr_output = args.bpr_output.resolve()
    args.basis_dir = args.basis_dir.resolve()
    output_dir = (
        args.output_dir.resolve()
        if args.output_dir is not None
        else args.bpr_output / "time_step_sweep"
    )
    if output_dir.exists() and any(output_dir.iterdir()) and not args.overwrite:
        raise FileExistsError(f"output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    bpr_summary = json.loads((args.bpr_output / "summary.json").read_text(encoding="utf-8"))
    if bpr_summary.get("status") != "conditional_bpr_failure_reconstruction_temporally_unresolved":
        raise ValueError("BPR output has an unexpected reconstruction status")
    mesh_path = args.basis_dir / "axial_ellipsoid.msh"
    equilibrium_path = args.basis_dir / "fixed-base-equilibrium-material.h5"
    if bpr_summary["mesh_sha256"] != file_sha256(mesh_path) or bpr_summary[
        "equilibrium_sha256"
    ] != file_sha256(equilibrium_path):
        raise ValueError("time-step sweep basis differs from the BPR reconstruction")
    results = {}
    material_hashes = {}
    for case in ("thermal_maxwell", "hydrothermal_maxwell"):
        material_path = args.bpr_output / "materials" / f"{case}.spatialdb"
        material_hash = file_sha256(material_path)
        if bpr_summary["cases"][case]["material_sha256"] != material_hash:
            raise ValueError(f"material map changed after the {case} BPR run")
        material_hashes[case] = material_hash
        response_by_step = {}
        stress_by_step = {}
        first_vertices = None
        first_cells = None
        for step_s in STEP_SECONDS:
            step_label = f"{step_s:g}s"
            run_dir = output_dir / "runs" / case / step_label
            maxwell._write_run(
                run_dir,
                mesh_path,
                material_path,
                elapsed_seconds=np.asarray([0.0, 7.0 * maxwell.SECONDS_PER_DAY]),
                pressure_mpa=np.asarray([0.0, 1.0]),
                time_step_s=step_s,
            )
            maxwell._run_pylith(run_dir)
            times_s, vertices, cells, stress = maxwell._read_stress(
                run_dir / "output" / "maxwell-material.h5"
            )
            if not np.isclose(times_s[-1], 7.0 * maxwell.SECONDS_PER_DAY, atol=0.01):
                raise ValueError(f"{case} did not end at day seven with step {step_s}")
            if first_vertices is None:
                first_vertices, first_cells = vertices, cells
            elif not np.array_equal(vertices, first_vertices) or not np.array_equal(
                cells, first_cells
            ):
                raise ValueError(f"{case} PyLith time-step meshes differ")
            reference = maxwell._reference_stress(equilibrium_path, vertices, cells)
            final_stress = stress[-1]
            record = analyze_stress_field(
                vertices,
                cells,
                reference + final_stress,
                cohesion_pa=1.0e6,
                friction_angle_deg=25.0,
                pore_pressure_pa=0.0,
                tensile_strength_pa=0.0,
            )
            uplift_m = _central_uplift(run_dir / "output" / "maxwell-surface.h5")
            stress_by_step[step_label] = final_stress
            response_by_step[step_label] = {
                "time_step_s": step_s,
                "step_to_shortest_maxwell_time_ratio": (
                    step_s / bpr_summary["cases"][case]["minimum_maxwell_time_s"]
                ),
                "saved_steps": len(times_s),
                "central_uplift_m_per_mpa": uplift_m,
                "final_cavity_principal_stress_pa": record[
                    "maximum_cavity_principal_stress_pa"
                ],
                "final_connected_shear_path": record["cavity_to_surface_shear_path_found"],
                "final_incremental_stress_l2_pa": float(np.linalg.norm(final_stress)),
            }
            print(f"{case}: finished {step_label} ({len(times_s)} steps)", flush=True)
        finest_label = f"{STEP_SECONDS[-1]:g}s"
        reference_stress = stress_by_step[finest_label]
        reference_uplift = response_by_step[finest_label]["central_uplift_m_per_mpa"]
        for step_label, response in response_by_step.items():
            response["stress_relative_l2_difference_from_1800s"] = float(
                np.linalg.norm(stress_by_step[step_label] - reference_stress)
                / np.linalg.norm(reference_stress)
            )
            response["central_uplift_relative_difference_from_1800s"] = float(
                (response["central_uplift_m_per_mpa"] - reference_uplift)
                / reference_uplift
            )
        results[case] = response_by_step
    summary = {
        "method": "seven-day one-megapascal ramp with fixed source-value Maxwell materials",
        "status": "short_window_time_step_sensitivity_not_full_history_convergence",
        "paper_output_data_used": False,
        "mesh_sha256": file_sha256(mesh_path),
        "equilibrium_sha256": file_sha256(equilibrium_path),
        "material_sha256_by_case": material_hashes,
        "pressure_ramp_mpa": [0.0, 1.0],
        "pressure_ramp_days": [0.0, 7.0],
        "reference_step_s": STEP_SECONDS[-1],
        "cases": results,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {output_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
