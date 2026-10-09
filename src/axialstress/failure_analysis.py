"""Postprocess PyLith stress fields for failure thresholds and connectivity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import h5py
import numpy as np

from axialstress.failure import mohr_coulomb_yield_pa, stress_voigt_to_tensor_pa
from axialstress.topology import box_cavity_boundary_cells, find_connected_failure_path


def analyze_stress_field(
    vertices_m: np.ndarray,
    tetrahedra: np.ndarray,
    stress_voigt_pa: np.ndarray,
    *,
    cohesion_pa: float,
    friction_angle_deg: float,
    pore_pressure_pa: float,
) -> dict[str, Any]:
    """Calculate tensile threshold and Mohr–Coulomb path indicators.

    The shear-yield path is evaluated before applying a tensile cutoff because
    tensile strength is unresolved in the written model. The cavity tensile
    value reports the strength at which at least one cavity-adjacent cell
    would reach tensile failure.
    """
    vertices = np.asarray(vertices_m, dtype=float)
    cells = np.asarray(tetrahedra, dtype=np.int64)
    stress_voigt = np.asarray(stress_voigt_pa, dtype=float)
    if stress_voigt.shape != (len(cells), 6):
        raise ValueError("stress_voigt_pa must have shape (ncells, 6)")
    stress = stress_voigt_to_tensor_pa(stress_voigt)
    boundaries = box_cavity_boundary_cells(vertices, cells)
    cavity_cells = boundaries["cavity"]
    surface_cells = boundaries["top"]
    if cavity_cells.size == 0 or surface_cells.size == 0:
        raise ValueError("mesh must contain cavity and top surface boundary cells")

    yield_pa = mohr_coulomb_yield_pa(
        stress,
        cohesion_pa=cohesion_pa,
        friction_angle_deg=friction_angle_deg,
        pore_pressure_pa=pore_pressure_pa,
    )
    shear_yield_cells = yield_pa >= 0.0
    path = find_connected_failure_path(
        cells, shear_yield_cells, cavity_cells, surface_cells
    )
    cavity_principal_stress = np.linalg.eigvalsh(stress[cavity_cells])
    tensile_threshold_pa = max(0.0, float(np.max(cavity_principal_stress[:, -1])))
    return {
        "cell_count": int(len(cells)),
        "cavity_adjacent_cell_count": int(len(cavity_cells)),
        "top_surface_adjacent_cell_count": int(len(surface_cells)),
        "mohr_coulomb_shear_yield_cell_count": int(np.count_nonzero(shear_yield_cells)),
        "cavity_to_surface_shear_path_found": bool(path.size),
        "cavity_to_surface_path_cell_indices": path.tolist(),
        "maximum_cavity_tensile_stress_pa": tensile_threshold_pa,
        "cohesion_pa": float(cohesion_pa),
        "friction_angle_deg": float(friction_angle_deg),
        "friction_interpretation": "friction_angle_deg is used directly as phi",
        "pore_pressure_pa": float(pore_pressure_pa),
        "tensile_cutoff_applied_to_shear_path": False,
    }


def analyze_pylith_material_file(
    material_h5_path: str | Path,
    *,
    cohesion_pa: float,
    friction_angle_deg: float,
    pore_pressure_pa: float,
) -> dict[str, Any]:
    """Analyze the final stress field in a PyLith material HDF5 file."""
    with h5py.File(material_h5_path, "r") as material:
        required = (
            "geometry/vertices",
            "viz/topology/cells",
            "cell_fields/cauchy_stress",
            "time",
        )
        missing = [name for name in required if name not in material]
        if missing:
            raise ValueError(f"PyLith material file is missing datasets: {missing}")
        vertices = np.asarray(material["geometry/vertices"], dtype=float)
        cells = np.asarray(material["viz/topology/cells"], dtype=np.int64)
        stress = np.asarray(material["cell_fields/cauchy_stress"][-1], dtype=float)
        time_s = float(np.asarray(material["time"]).reshape(-1)[-1])
    summary = analyze_stress_field(
        vertices,
        cells,
        stress,
        cohesion_pa=cohesion_pa,
        friction_angle_deg=friction_angle_deg,
        pore_pressure_pa=pore_pressure_pa,
    )
    summary["final_time_s"] = time_s
    return summary


def main() -> None:
    """Write failure-threshold diagnostics from a PyLith material output."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--material-h5", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cohesion-pa", type=float, required=True)
    parser.add_argument("--friction-angle-deg", type=float, required=True)
    parser.add_argument("--pore-pressure-pa", type=float, required=True)
    args = parser.parse_args()
    summary = analyze_pylith_material_file(
        args.material_h5,
        cohesion_pa=args.cohesion_pa,
        friction_angle_deg=args.friction_angle_deg,
        pore_pressure_pa=args.pore_pressure_pa,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
