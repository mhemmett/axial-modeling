"""Screen BPR-fitted pressure against gravity-equilibrated PyLith stress."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

import h5py
import numpy as np

from axialstress.failure_analysis import analyze_stress_history
from axialstress.paper_bpr import file_sha256
from axialstress.topology import box_cavity_boundary_cells

ROOT = Path(__file__).resolve().parents[1]
STEP_OUTPUT = ROOT / "pylith/step16_winkler_foundation/output"
FIT_DIR = ROOT / "data/processed/method_reconstruction_2011_2015_gravity_fixed"
STRENGTHS_PA = (0.0, 0.1e6, 2.5e6)


def _read_stress(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read mesh coordinates, tetrahedra, and final Cauchy stress in pascals."""
    with h5py.File(path, "r") as material:
        vertices = np.asarray(material["geometry/vertices"], dtype=float)
        tetrahedra = np.asarray(material["viz/topology/cells"], dtype=np.int64)
        stress = np.asarray(material["cell_fields/cauchy_stress"][-1], dtype=float)
    if (
        tetrahedra.ndim != 2
        or tetrahedra.shape[1] != 4
        or stress.shape != (len(tetrahedra), 6)
        or not np.all(np.isfinite(vertices))
        or not np.all(np.isfinite(stress))
    ):
        raise ValueError(f"invalid PyLith stress state in {path}")
    return vertices, tetrahedra, stress


def _joint(record: dict, strength_pa: float) -> bool:
    """Require positive tensile stress and a connected shear-yield path."""
    principal = float(record["maximum_cavity_principal_stress_pa"])
    tensile = principal > 0.0 if strength_pa == 0.0 else principal >= strength_pa
    return bool(tensile and record["cavity_to_surface_shear_path_found"])


def _first_joint(records: list[dict], strength_pa: float) -> int | None:
    """Return the first saved record satisfying both failure conditions."""
    return next(
        (index for index, record in enumerate(records) if _joint(record, strength_pa)), None
    )


def main() -> None:
    """Save conditional pressure thresholds and event-time stress states."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fit-dir", type=Path, default=FIT_DIR)
    parser.add_argument("--step-output", type=Path, default=STEP_OUTPUT)
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "data/processed/method_failure_screen_2011_2015"
    )
    parser.add_argument("--maximum-pressure-mpa", type=float, default=100.0)
    parser.add_argument("--pressure-step-mpa", type=float, default=0.5)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()) and not args.overwrite:
        raise FileExistsError(f"output directory is not empty: {args.output_dir}")
    if (
        not np.isfinite(args.maximum_pressure_mpa)
        or not np.isfinite(args.pressure_step_mpa)
        or args.maximum_pressure_mpa <= 0.0
        or args.pressure_step_mpa <= 0.0
    ):
        raise ValueError("pressure scan bounds must be finite and positive")

    fit_summary_path = args.fit_dir / "summary.json"
    fit_summary = json.loads(fit_summary_path.read_text(encoding="utf-8"))
    if fit_summary.get("status") != "conditional_pressure_history_not_failure_threshold":
        raise ValueError("input pressure fit has an unexpected status")
    surface_path = args.step_output / "fixed-base-surface.h5"
    if fit_summary["static_surface_sha256"] != file_sha256(surface_path):
        raise ValueError("pressure fit and stress basis do not use the same PyLith surface")
    basis_summary_path = ROOT / "data/processed/winkler_foundation_check.json"
    basis_summary = json.loads(basis_summary_path.read_text(encoding="utf-8"))
    if (
        basis_summary.get("converged") is not True
        or basis_summary.get("cavity_overpressure_mpa") != 1.0
        or basis_summary["tectonic_loading"]["per_face_velocity_mm_per_year"] != 0.0
        or basis_summary["lithostatic_equilibrium_diagnostics"][
            "fixed-base_max_displacement_m"
        ] > 1.0e-9
    ):
        raise ValueError("PyLith basis must be a converged one-megapascal pressure case")

    reference_path = args.step_output / "fixed-base-equilibrium-material.h5"
    loaded_path = args.step_output / "fixed-base-material.h5"
    vertices, cells, reference_stress = _read_stress(reference_path)
    loaded_vertices, loaded_cells, loaded_stress = _read_stress(loaded_path)
    if not np.array_equal(vertices, loaded_vertices) or not np.array_equal(cells, loaded_cells):
        raise ValueError("equilibrium and pressure stress fields have different meshes")
    if len(cells) != basis_summary["mesh_tetrahedra"]:
        raise ValueError("PyLith basis summary has a different mesh size")
    boundaries = box_cavity_boundary_cells(vertices, cells)
    boundary_overlap = np.intersect1d(boundaries["cavity"], boundaries["top"])
    if boundary_overlap.size:
        raise ValueError("one or more cells touch both cavity and seafloor boundaries")
    unit_increment = loaded_stress - reference_stress

    with (args.fit_dir / "pressure_history.csv").open(encoding="utf-8", newline="") as stream:
        pressure_rows = list(csv.DictReader(stream))
    dates = [datetime.fromisoformat(row["time_utc"]) for row in pressure_rows]
    if len(dates) < 2 or any(
        left >= right for left, right in zip(dates[:-1], dates[1:], strict=True)
    ):
        raise ValueError("pressure fit times must increase")
    elapsed_s = np.asarray([(date - dates[0]).total_seconds() for date in dates])
    pressure_columns = {
        "0.1": "pressure_weight_0p1_mpa",
        "1.0": "pressure_change_mpa",
        "10.0": "pressure_weight_10_mpa",
    }

    scan_pressures = np.arange(
        0.0,
        args.maximum_pressure_mpa + args.pressure_step_mpa / 2.0,
        args.pressure_step_mpa,
    )
    scan_stress = reference_stress[None, :, :] + (
        scan_pressures[:, None, None] * unit_increment[None, :, :]
    )
    scan = analyze_stress_history(
        vertices,
        cells,
        scan_stress,
        scan_pressures,
        cohesion_pa=1.0e6,
        friction_angle_deg=25.0,
        pore_pressure_pa=0.0,
    )
    scan_results = {}
    for strength_pa in STRENGTHS_PA:
        index = _first_joint(scan["records"], strength_pa)
        scan_results[f"{strength_pa / 1.0e6:g}"] = {
            "tensile_strength_mpa": strength_pa / 1.0e6,
            "first_joint_pressure_mpa": float(scan_pressures[index]) if index is not None else None,
            "last_without_joint_pressure_mpa": (
                float(scan_pressures[index - 1]) if index is not None and index > 0 else None
            ),
            "first_joint_path_cell_count": (
                len(scan["records"][index]["cavity_to_surface_path_cell_indices"])
                if index is not None
                else None
            ),
        }

    histories = {}
    for weight, column in pressure_columns.items():
        pressure = np.asarray([float(row[column]) for row in pressure_rows])
        stress = reference_stress[None, :, :] + pressure[:, None, None] * unit_increment[None, :, :]
        analysis = analyze_stress_history(
            vertices,
            cells,
            stress,
            elapsed_s,
            cohesion_pa=1.0e6,
            friction_angle_deg=25.0,
            pore_pressure_pa=0.0,
        )
        histories[weight] = {
            "last_preeruption_pressure_mpa": float(pressure[-1]),
            "last_preeruption_principal_stress_mpa": (
                analysis["records"][-1]["maximum_cavity_principal_stress_pa"] / 1.0e6
            ),
            "last_preeruption_connected_path": analysis["records"][-1][
                "cavity_to_surface_shear_path_found"
            ],
            "strength_cases": {},
        }
        for strength_pa in STRENGTHS_PA:
            index = _first_joint(analysis["records"], strength_pa)
            histories[weight]["strength_cases"][f"{strength_pa / 1.0e6:g}"] = {
                "first_joint_time_utc": dates[index].isoformat() if index is not None else None,
                "first_joint_fitted_pressure_mpa": (
                    float(pressure[index]) if index is not None else None
                ),
            }

    summary = {
        "method": "static elastic PyLith stress superposition on gravity equilibrium",
        "status": "conditional_coarse_mesh_failure_screen",
        "paper_output_data_used": False,
        "fit_summary_sha256": file_sha256(fit_summary_path),
        "fixed_base_surface_sha256": file_sha256(surface_path),
        "equilibrium_material_sha256": file_sha256(reference_path),
        "one_mpa_material_sha256": file_sha256(loaded_path),
        "mesh_tetrahedra": len(cells),
        "cavity_adjacent_cells": len(boundaries["cavity"]),
        "surface_adjacent_cells": len(boundaries["top"]),
        "cells_touching_cavity_and_surface": int(boundary_overlap.size),
        "model_assumptions": {
            "initial_pressure_change_mpa": 0.0,
            "equilibrium_density_kg_m3": basis_summary["equilibrium_density_kg_m3"],
            "youngs_modulus_pa": basis_summary["youngs_modulus_pa"],
            "poisson_ratio": basis_summary["poisson_ratio"],
            "basal_treatment": "fixed base; approximation to the paper's stiff Eq. 23 spring",
            "cohesion_pa": 1.0e6,
            "friction_angle_deg": 25.0,
            "pore_pressure_pa": 0.0,
            "tensile_strength_pa": list(STRENGTHS_PA),
            "tectonic_loading": "none",
        },
        "pressure_scan_maximum_mpa": float(scan_pressures[-1]),
        "pressure_scan_step_mpa": args.pressure_step_mpa,
        "first_connected_shear_path_pressure_mpa": (
            scan["first_cavity_to_surface_shear_path_time_s"]
        ),
        "interpolated_shear_path_pressure_mpa": (
            scan["first_cavity_to_surface_shear_path_interpolated_time_s"]
        ),
        "pressure_scan": scan_results,
        "bpr_histories": histories,
        "limitations": [
            "This is an elastic, coarse-mesh screen; stress-path and pressure "
            "convergence are untested.",
            "The post-2011 zero-change state omits inherited pressure and viscoelastic stress.",
            "Unknown BPR deployment offsets make the inferred pressure history gap-sensitive.",
            "Density, tensile strength, pore pressure, and stiffness are conditional choices.",
        ],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "summary.json"
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": summary["status"],
                "pressure_scan": scan_results,
                "bpr_histories": histories,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
