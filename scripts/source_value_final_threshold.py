"""Bracket conditional final-state failure from fitted Maxwell stress fields."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import h5py
import numpy as np

from axialstress.failure_analysis import analyze_stress_history
from axialstress.paper_bpr import file_sha256

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "source_value_bpr_failure_2011_2015"
STRENGTHS_PA = (0.0, 0.1e6, 2.5e6)


def _read_final_stress(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read the final PyLith Cauchy stress and identical-mesh identifiers."""
    with h5py.File(path, "r") as material:
        vertices = np.asarray(material["geometry/vertices"], dtype=float)
        cells = np.asarray(material["viz/topology/cells"], dtype=np.int64)
        stress = np.asarray(material["cell_fields/cauchy_stress"][-1], dtype=float)
    if stress.shape != (len(cells), 6) or not np.all(np.isfinite(stress)):
        raise ValueError(f"invalid final PyLith stress in {path}")
    return vertices, cells, stress


def _joint(record: dict[str, object], strength_pa: float) -> bool:
    """Require cavity tension above strength and a connected yielded path."""
    principal = float(record["maximum_cavity_principal_stress_pa"])
    tension = principal > 0.0 if strength_pa == 0.0 else principal >= strength_pa
    return tension and bool(record["cavity_to_surface_shear_path_found"])


def _scan(
    vertices: np.ndarray,
    cells: np.ndarray,
    reference: np.ndarray,
    increment: np.ndarray,
    nominal_pressure_mpa: float,
    pressure_mpa: np.ndarray,
) -> list[dict[str, object]]:
    """Evaluate final stress after uniformly scaling the fitted pressure path."""
    trial_stress = reference[np.newaxis] + (
        pressure_mpa[:, np.newaxis, np.newaxis]
        / nominal_pressure_mpa
        * increment[np.newaxis]
    )
    analysis = analyze_stress_history(
        vertices,
        cells,
        trial_stress,
        pressure_mpa,
        cohesion_pa=1.0e6,
        friction_angle_deg=25.0,
        pore_pressure_pa=0.0,
    )
    return analysis["records"]


def main() -> None:
    """Write bounded final-state failure brackets for each source-value case."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=INPUT)
    parser.add_argument("--maximum-pressure-mpa", type=float, default=200.0)
    parser.add_argument("--pressure-step-mpa", type=float, default=0.5)
    args = parser.parse_args()
    if (
        not np.isfinite(args.maximum_pressure_mpa)
        or not np.isfinite(args.pressure_step_mpa)
        or args.maximum_pressure_mpa <= 0.0
        or args.pressure_step_mpa <= 0.0
    ):
        raise ValueError("pressure scan bounds must be finite and positive")
    summary_path = args.input_dir / "summary.json"
    source_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if source_summary.get("status") != (
        "conditional_bpr_failure_reconstruction_temporally_unresolved"
    ):
        raise ValueError("input BPR reconstruction has an unexpected status")
    equilibrium_path = (
        ROOT / "data" / "processed" / "refined_elastic_basis_400m"
        / "fixed-base-equilibrium-material.h5"
    )
    if source_summary["equilibrium_sha256"] != file_sha256(equilibrium_path):
        raise ValueError("gravity equilibrium input changed after BPR reconstruction")
    reference_vertices, reference_cells, reference = _read_final_stress(
        equilibrium_path
    )
    case_results = {}
    for name, case in source_summary["cases"].items():
        forward_path = (
            args.input_dir / "runs" / name / "bpr_pressure" / "output" / "maxwell-material.h5"
        )
        if case["forward_material_sha256"] != file_sha256(forward_path):
            raise ValueError(f"PyLith forward stress changed for {name}")
        vertices, cells, increment = _read_final_stress(forward_path)
        if not np.array_equal(vertices, reference_vertices) or not np.array_equal(
            cells, reference_cells
        ):
            raise ValueError(f"Maxwell and equilibrium meshes differ for {name}")
        series_path = args.input_dir / case["pressure_failure_csv"]
        with series_path.open(encoding="utf-8", newline="") as stream:
            final_row = list(csv.DictReader(stream))[-1]
        nominal_pressure_mpa = float(final_row["pressure_change_mpa"])
        if nominal_pressure_mpa <= 0.0 or not np.isclose(
            nominal_pressure_mpa,
            case["last_preeruption_pressure_mpa_by_weight"]["1.0"],
        ):
            raise ValueError(f"invalid fitted final pressure for {name}")
        pressures = np.arange(
            0.0,
            args.maximum_pressure_mpa + args.pressure_step_mpa / 2.0,
            args.pressure_step_mpa,
        )
        records = _scan(
            vertices, cells, reference, increment, nominal_pressure_mpa, pressures
        )
        strength_results = {}
        for strength_pa in STRENGTHS_PA:
            flags = [_joint(record, strength_pa) for record in records]
            if any(left and not right for left, right in zip(flags[:-1], flags[1:], strict=True)):
                raise ValueError(f"final-state joint failure is nonmonotonic for {name}")
            index = next((index for index, flag in enumerate(flags) if flag), None)
            if index is None or index == 0:
                strength_results[f"{strength_pa / 1.0e6:g}"] = {
                    "last_without_joint_pressure_mpa": None,
                    "first_joint_pressure_mpa": (
                        float(pressures[0]) if index == 0 else None
                    ),
                }
                continue
            refined_step = args.pressure_step_mpa / 10.0
            refined_pressures = np.arange(
                pressures[index - 1], pressures[index] + refined_step / 2.0, refined_step
            )
            refined = _scan(
                vertices, cells, reference, increment, nominal_pressure_mpa,
                refined_pressures,
            )
            refined_index = next(
                (i for i, record in enumerate(refined) if _joint(record, strength_pa)), None
            )
            if refined_index is None or refined_index == 0:
                raise ValueError(f"refined pressure scan did not bracket {name}")
            strength_results[f"{strength_pa / 1.0e6:g}"] = {
                "last_without_joint_pressure_mpa": float(
                    refined_pressures[refined_index - 1]
                ),
                "first_joint_pressure_mpa": float(refined_pressures[refined_index]),
                "first_joint_pressure_scale_relative_to_fit": float(
                    refined_pressures[refined_index] / nominal_pressure_mpa
                ),
                "first_joint_path_cells": len(
                    refined[refined_index]["cavity_to_surface_path_cell_indices"]
                ),
                "first_joint_cavity_principal_stress_pa": refined[refined_index][
                    "maximum_cavity_principal_stress_pa"
                ],
            }
        case_results[name] = {
            "nominal_final_pressure_mpa": nominal_pressure_mpa,
            "source_series_sha256": file_sha256(series_path),
            "maximum_scan_cavity_principal_stress_pa": records[-1][
                "maximum_cavity_principal_stress_pa"
            ],
            "maximum_scan_connected_shear_path": records[-1][
                "cavity_to_surface_shear_path_found"
            ],
            "strength_brackets": strength_results,
        }
        print(f"{name}: {strength_results['0']}", flush=True)
    output = {
        "method": "scale the entire fitted PyLith pressure path and assess its final stress state",
        "status": "conditional_final_state_failure_threshold_not_temporally_converged",
        "paper_output_data_used": False,
        "source_summary_sha256": file_sha256(summary_path),
        "pressure_scan_mpa": [0.0, args.maximum_pressure_mpa, args.pressure_step_mpa],
        "refined_step_mpa": args.pressure_step_mpa / 10.0,
        "cohesion_pa": 1.0e6,
        "friction_angle_deg": 25.0,
        "pore_pressure_pa_assumption": 0.0,
        "tensile_strength_pa_assumptions": list(STRENGTHS_PA),
        "cases": case_results,
    }
    output_path = args.input_dir / "final_state_failure_threshold.json"
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
