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

INTERPOLATED_ONSET_TIME_TOLERANCE_S = 0.01


def _has_connected_shear_path(
    stress_voigt_pa: np.ndarray,
    tetrahedra: np.ndarray,
    cavity_cells: np.ndarray,
    surface_cells: np.ndarray,
    *,
    cohesion_pa: float,
    friction_angle_deg: float,
    pore_pressure_pa: float,
) -> bool:
    """Return whether one stress field has a cavity-to-surface shear path."""
    stress = stress_voigt_to_tensor_pa(stress_voigt_pa)
    yield_pa = mohr_coulomb_yield_pa(
        stress,
        cohesion_pa=cohesion_pa,
        friction_angle_deg=friction_angle_deg,
        pore_pressure_pa=pore_pressure_pa,
    )
    return bool(
        find_connected_failure_path(
            tetrahedra, yield_pa >= 0.0, cavity_cells, surface_cells
        ).size
    )


def _interpolate_first_path_onset(
    vertices_m: np.ndarray,
    tetrahedra: np.ndarray,
    stress_history_voigt_pa: np.ndarray,
    time_s: np.ndarray,
    path_at_records: list[bool],
    *,
    cohesion_pa: float,
    friction_angle_deg: float,
    pore_pressure_pa: float,
) -> dict[str, Any] | None:
    """Bracket the first sampled path transition using linear stress interpolation."""
    if not any(path_at_records):
        return None
    if path_at_records[0]:
        return {
            "time_s": float(time_s[0]),
            "last_no_path_time_s": None,
            "first_path_time_s": float(time_s[0]),
            "lower_record_index": 0,
            "upper_record_index": 0,
        }

    left_index = next(
        index
        for index, (left_path, right_path) in enumerate(
            zip(path_at_records[:-1], path_at_records[1:], strict=True)
        )
        if not left_path and right_path
    )
    boundaries = box_cavity_boundary_cells(vertices_m, tetrahedra)
    cavity_cells = boundaries["cavity"]
    surface_cells = boundaries["top"]
    if cavity_cells.size == 0 or surface_cells.size == 0:
        raise ValueError("mesh must contain cavity and top surface boundary cells")

    lower_time_s = float(time_s[left_index])
    upper_time_s = float(time_s[left_index + 1])
    start_stress = stress_history_voigt_pa[left_index]
    end_stress = stress_history_voigt_pa[left_index + 1]
    for _ in range(48):
        middle_time_s = lower_time_s + (upper_time_s - lower_time_s) / 2.0
        fraction = (middle_time_s - time_s[left_index]) / (
            time_s[left_index + 1] - time_s[left_index]
        )
        middle_stress = start_stress + fraction * (end_stress - start_stress)
        middle_has_path = _has_connected_shear_path(
            middle_stress,
            tetrahedra,
            cavity_cells,
            surface_cells,
            cohesion_pa=cohesion_pa,
            friction_angle_deg=friction_angle_deg,
            pore_pressure_pa=pore_pressure_pa,
        )
        if middle_has_path:
            upper_time_s = middle_time_s
        else:
            lower_time_s = middle_time_s
        if upper_time_s - lower_time_s <= INTERPOLATED_ONSET_TIME_TOLERANCE_S:
            break

    return {
        "time_s": lower_time_s + (upper_time_s - lower_time_s) / 2.0,
        "last_no_path_time_s": lower_time_s,
        "first_path_time_s": upper_time_s,
        "lower_record_index": left_index,
        "upper_record_index": left_index + 1,
    }


def analyze_stress_field(
    vertices_m: np.ndarray,
    tetrahedra: np.ndarray,
    stress_voigt_pa: np.ndarray,
    *,
    cohesion_pa: float,
    friction_angle_deg: float,
    pore_pressure_pa: float,
    tensile_strength_pa: float | None = None,
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
    if tensile_strength_pa is not None and (
        not np.isfinite(tensile_strength_pa) or tensile_strength_pa < 0.0
    ):
        raise ValueError("tensile_strength_pa must be finite and nonnegative")
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
    reservoir_tensile_failure = (
        tensile_threshold_pa >= tensile_strength_pa
        if tensile_strength_pa is not None
        else None
    )
    joint_eruption_criterion = (
        bool(reservoir_tensile_failure and path.size)
        if reservoir_tensile_failure is not None
        else None
    )
    return {
        "cell_count": int(len(cells)),
        "cavity_adjacent_cell_count": int(len(cavity_cells)),
        "top_surface_adjacent_cell_count": int(len(surface_cells)),
        "mohr_coulomb_shear_yield_cell_count": int(np.count_nonzero(shear_yield_cells)),
        "cavity_to_surface_shear_path_found": bool(path.size),
        "cavity_to_surface_path_cell_indices": path.tolist(),
        "maximum_cavity_tensile_stress_pa": tensile_threshold_pa,
        "assumed_tensile_strength_pa": (
            float(tensile_strength_pa) if tensile_strength_pa is not None else None
        ),
        "reservoir_tensile_failure": reservoir_tensile_failure,
        "joint_eruption_criterion_met": joint_eruption_criterion,
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
    tensile_strength_pa: float | None = None,
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
        tensile_strength_pa=tensile_strength_pa,
    )
    summary["final_time_s"] = time_s
    return summary


def analyze_stress_history(
    vertices_m: np.ndarray,
    tetrahedra: np.ndarray,
    stress_history_voigt_pa: np.ndarray,
    time_s: np.ndarray,
    *,
    cohesion_pa: float,
    friction_angle_deg: float,
    pore_pressure_pa: float,
    tensile_strength_pa: float | None = None,
) -> dict[str, Any]:
    """Analyze each recorded stress field and locate the first connected path.

    Parameters
    ----------
    vertices_m : array_like
        Mesh coordinates in meters, with shape ``(nvertices, 3)``.
    tetrahedra : array_like
        Zero-based tetrahedron indices, with shape ``(ncells, 4)``.
    stress_history_voigt_pa : array_like
        PyLith stress records ordered ``xx, yy, zz, xy, yz, xz`` with shape
        ``(ntimes, ncells, 6)``.
    time_s : array_like
        Record times in seconds, with one strictly increasing value per record.
    cohesion_pa : float
        Mohr–Coulomb cohesion in pascals.
    friction_angle_deg : float
        Friction angle in degrees, applied directly as ``phi``.
    pore_pressure_pa : float
        Isotropic pore pressure in pascals.

    Returns
    -------
    dict[str, Any]
        Per-record stress and path diagnostics, plus the first recorded time
        with a cavity-to-surface path or ``None`` if no record has one.
    """
    stresses = np.asarray(stress_history_voigt_pa, dtype=float)
    times = np.asarray(time_s, dtype=float).reshape(-1)
    cells = np.asarray(tetrahedra)
    if stresses.ndim != 3 or stresses.shape[1:] != (len(cells), 6):
        raise ValueError("stress_history_voigt_pa must have shape (ntimes, ncells, 6)")
    if len(times) != len(stresses) or len(times) == 0:
        raise ValueError("time_s must contain one value per stress record")
    if not np.all(np.isfinite(times)) or np.any(np.diff(times) <= 0.0):
        raise ValueError("time_s values must be finite and strictly increasing")

    records = []
    path_at_records = []
    first_path_time_s = None
    for time_value, stress_record in zip(times, stresses, strict=True):
        record = analyze_stress_field(
            vertices_m,
            cells,
            stress_record,
            cohesion_pa=cohesion_pa,
            friction_angle_deg=friction_angle_deg,
            pore_pressure_pa=pore_pressure_pa,
            tensile_strength_pa=tensile_strength_pa,
        )
        record["time_s"] = float(time_value)
        if record["cavity_to_surface_shear_path_found"] and first_path_time_s is None:
            first_path_time_s = float(time_value)
        path_at_records.append(record["cavity_to_surface_shear_path_found"])
        records.append(record)

    interpolated_onset = _interpolate_first_path_onset(
        vertices_m,
        cells,
        stresses,
        times,
        path_at_records,
        cohesion_pa=cohesion_pa,
        friction_angle_deg=friction_angle_deg,
        pore_pressure_pa=pore_pressure_pa,
    )
    path_records = [
        record for record in records if record["cavity_to_surface_shear_path_found"]
    ]
    maximum_joint_tensile_threshold_pa = (
        max(record["maximum_cavity_tensile_stress_pa"] for record in path_records)
        if path_records
        else None
    )
    maximum_joint_threshold_time_s = (
        next(
            record["time_s"]
            for record in path_records
            if record["maximum_cavity_tensile_stress_pa"]
            == maximum_joint_tensile_threshold_pa
        )
        if maximum_joint_tensile_threshold_pa is not None
        else None
    )
    first_joint_candidate_time_s = next(
        (
            record["time_s"]
            for record in records
            if record["joint_eruption_criterion_met"] is True
        ),
        None,
    )

    return {
        "record_count": len(records),
        "first_cavity_to_surface_shear_path_time_s": first_path_time_s,
        "first_cavity_to_surface_shear_path_interpolated_time_s": (
            interpolated_onset["time_s"] if interpolated_onset is not None else None
        ),
        "interpolated_path_bracket": interpolated_onset,
        "interpolation_method": (
            "linear Cauchy-stress interpolation and bisection within the first "
            "adjacent saved-record pair that brackets path onset"
        ),
        "interpolation_limitation": (
            "The path indicator is assumed to change monotonically within the "
            "bracketing interval; no PyLith time integration is performed "
            "between saved records."
        ),
        "assumed_tensile_strength_pa": (
            float(tensile_strength_pa) if tensile_strength_pa is not None else None
        ),
        "first_joint_eruption_criterion_record_time_s": first_joint_candidate_time_s,
        "maximum_tensile_strength_with_a_saved_connected_path_pa": (
            maximum_joint_tensile_threshold_pa
        ),
        "time_of_maximum_tensile_strength_with_a_saved_connected_path_s": (
            maximum_joint_threshold_time_s
        ),
        "joint_criterion_interpolation": (
            "not performed; joint tensile and connected-path state is evaluated "
            "only at saved PyLith records"
        ),
        "records": records,
    }


def analyze_pylith_material_history(
    material_h5_path: str | Path,
    *,
    cohesion_pa: float,
    friction_angle_deg: float,
    pore_pressure_pa: float,
    tensile_strength_pa: float | None = None,
) -> dict[str, Any]:
    """Analyze every recorded Cauchy stress field in a PyLith material file."""
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
        stress_history = np.asarray(material["cell_fields/cauchy_stress"], dtype=float)
        time_s = np.asarray(material["time"], dtype=float)
    return analyze_stress_history(
        vertices,
        cells,
        stress_history,
        time_s,
        cohesion_pa=cohesion_pa,
        friction_angle_deg=friction_angle_deg,
        pore_pressure_pa=pore_pressure_pa,
        tensile_strength_pa=tensile_strength_pa,
    )


def main() -> None:
    """Write failure-threshold diagnostics from a PyLith material output."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--material-h5", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cohesion-pa", type=float, required=True)
    parser.add_argument("--friction-angle-deg", type=float, required=True)
    parser.add_argument("--pore-pressure-pa", type=float, required=True)
    parser.add_argument(
        "--tensile-strength-pa",
        type=float,
        help="evaluate the joint eruption criterion at this tensile strength",
    )
    parser.add_argument(
        "--all-times",
        action="store_true",
        help="analyze all saved stress records instead of only the final record",
    )
    args = parser.parse_args()
    analyzer = (
        analyze_pylith_material_history
        if args.all_times
        else analyze_pylith_material_file
    )
    summary = analyzer(
        args.material_h5,
        cohesion_pa=args.cohesion_pa,
        friction_angle_deg=args.friction_angle_deg,
        pore_pressure_pa=args.pore_pressure_pa,
        tensile_strength_pa=args.tensile_strength_pa,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
