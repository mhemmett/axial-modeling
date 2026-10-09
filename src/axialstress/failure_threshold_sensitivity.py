"""Measure Mohr–Coulomb path and tensile-threshold sensitivity in saved runs."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np

from axialstress.failure import stress_voigt_to_tensor_pa
from axialstress.topology import TetrahedralFaceGraph, box_cavity_boundary_cells


def analyze_failure_threshold_grid(
    vertices_m: np.ndarray,
    tetrahedra: np.ndarray,
    stress_history_voigt_pa: np.ndarray,
    time_s: np.ndarray,
    *,
    cohesion_pa_values: Iterable[float],
    friction_angle_deg_values: Iterable[float],
    pore_pressure_pa_values: Iterable[float],
    face_graph: TetrahedralFaceGraph | None = None,
) -> list[dict[str, Any]]:
    """Evaluate saved-record connectivity and joint-threshold envelopes.

    Parameters
    ----------
    vertices_m : array_like
        Tetrahedral coordinates in meters, with shape ``(nvertices, 3)``.
    tetrahedra : array_like
        Zero-based cell connectivity, with shape ``(ncells, 4)``.
    stress_history_voigt_pa : array_like
        PyLith Cauchy stress records ordered ``xx, yy, zz, xy, yz, xz`` in
        pascals, with shape ``(ntimes, ncells, 6)``.
    time_s : array_like
        Strictly increasing PyLith output times in seconds.
    cohesion_pa_values : iterable of float
        Diagnostic cohesion values in pascals.
    friction_angle_deg_values : iterable of float
        Diagnostic friction angles applied directly as ``phi``.
    pore_pressure_pa_values : iterable of float
        Diagnostic isotropic pore pressures in pascals.
    face_graph : TetrahedralFaceGraph, optional
        Cached face adjacency for this exact mesh. Supplying it avoids rebuilding
        topology for each window in a shared-mesh analysis.

    Returns
    -------
    list of dict
        One result per parameter combination. The maximum cavity tensile stress
        is taken only over saved records with a cavity-to-top shear path.

    Notes
    -----
    This postprocessing sweep does not modify PyLith stress or infer physical
    rock strengths. Parameter values are diagnostic scenarios unless sourced
    independently; interpolated path transitions are not evaluated.
    """
    vertices = np.asarray(vertices_m, dtype=float)
    cells = np.asarray(tetrahedra, dtype=np.int64)
    stresses = np.asarray(stress_history_voigt_pa, dtype=float)
    times = np.asarray(time_s, dtype=float).reshape(-1)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not np.all(np.isfinite(vertices)):
        raise ValueError("vertices_m must be a finite array with shape (nvertices, 3)")
    if cells.ndim != 2 or cells.shape[1] != 4 or len(cells) == 0:
        raise ValueError("tetrahedra must have shape (ncells, 4)")
    if stresses.ndim != 3 or stresses.shape[1:] != (len(cells), 6):
        raise ValueError("stress history must have shape (ntimes, ncells, 6)")
    if len(times) != len(stresses) or len(times) == 0:
        raise ValueError("time_s must contain one value per stress record")
    if not np.all(np.isfinite(times)) or np.any(np.diff(times) <= 0.0):
        raise ValueError("time_s values must be finite and strictly increasing")
    if face_graph is None:
        face_graph = TetrahedralFaceGraph(cells)
    elif not np.array_equal(face_graph.tetrahedra, cells):
        raise ValueError("cached face graph does not match the tetrahedral mesh")

    cohesion_values = _validated_values(cohesion_pa_values, "cohesion", minimum=0.0)
    friction_values = _validated_values(
        friction_angle_deg_values, "friction angle", minimum=0.0, maximum=90.0
    )
    pore_values = _validated_values(pore_pressure_pa_values, "pore pressure", minimum=0.0)

    boundaries = box_cavity_boundary_cells(vertices, cells)
    cavity_cells = boundaries["cavity"]
    top_cells = boundaries["top"]
    if cavity_cells.size == 0 or top_cells.size == 0:
        raise ValueError("mesh must contain cavity and top surface boundary cells")

    stress_tensors = stress_voigt_to_tensor_pa(stresses)
    principal_tension_positive_pa = np.linalg.eigvalsh(stress_tensors)
    minimum_tension_pa = principal_tension_positive_pa[..., 0]
    maximum_tension_pa = principal_tension_positive_pa[..., -1]
    cavity_tension_pa = np.maximum(
        0.0, np.max(maximum_tension_pa[:, cavity_cells], axis=1)
    )
    # With tension-positive PyLith stresses, compression-positive effective
    # principal values are -lambda_max and -lambda_min after pore pressure.
    sigma_3_base_pa = -maximum_tension_pa
    sigma_1_base_pa = -minimum_tension_pa

    results = []
    for cohesion_pa in cohesion_values:
        for friction_angle_deg in friction_values:
            friction_rad = np.deg2rad(friction_angle_deg)
            sin_friction = np.sin(friction_rad)
            cohesion_term_pa = 2.0 * cohesion_pa * np.cos(friction_rad)
            for pore_pressure_pa in pore_values:
                sigma_3_pa = sigma_3_base_pa - pore_pressure_pa
                sigma_1_pa = sigma_1_base_pa - pore_pressure_pa
                yield_pa = (
                    sigma_1_pa
                    - sigma_3_pa
                    - (sigma_1_pa + sigma_3_pa) * sin_friction
                    - cohesion_term_pa
                )
                path_count = 0
                first_path_time_s = None
                maximum_tensile_threshold_pa = None
                for index, record_yield_pa in enumerate(yield_pa):
                    path = face_graph.find_connected_failure_path(
                        record_yield_pa >= 0.0, cavity_cells, top_cells
                    )
                    if path.size:
                        path_count += 1
                        if first_path_time_s is None:
                            first_path_time_s = float(times[index])
                        record_threshold_pa = float(cavity_tension_pa[index])
                        maximum_tensile_threshold_pa = (
                            record_threshold_pa
                            if maximum_tensile_threshold_pa is None
                            else max(maximum_tensile_threshold_pa, record_threshold_pa)
                        )
                results.append(
                    {
                        "cohesion_pa": float(cohesion_pa),
                        "friction_angle_deg": float(friction_angle_deg),
                        "pore_pressure_pa": float(pore_pressure_pa),
                        "record_count": int(len(times)),
                        "path_record_count": path_count,
                        "path_record_fraction": float(path_count / len(times)),
                        "first_path_time_s": first_path_time_s,
                        "maximum_tensile_strength_with_saved_path_pa": (
                            maximum_tensile_threshold_pa
                        ),
                    }
                )
    return results


def _validated_values(
    values: Iterable[float],
    name: str,
    *,
    minimum: float,
    maximum: float | None = None,
) -> tuple[float, ...]:
    """Return finite, unique, nonempty values within declared bounds."""
    array = tuple(float(value) for value in values)
    if not array or any(not np.isfinite(value) or value < minimum for value in array):
        raise ValueError(f"{name} values must be finite and at least {minimum:g}")
    if maximum is not None and any(value >= maximum for value in array):
        raise ValueError(f"{name} values must be less than {maximum:g}")
    if len(set(array)) != len(array):
        raise ValueError(f"{name} values must be unique")
    return array
