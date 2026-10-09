"""Compare Cabaniss-rate loading and basal support with bounded static solves."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import h5py
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from winkler_foundation_check import STEP_DIR, run_check  # noqa: E402

from axialstress.failure_analysis import analyze_stress_history  # noqa: E402
from axialstress.winkler import (  # noqa: E402
    area_stiffness_pa_per_m_from_asthenosphere_density,
    lithostatic_traction_pa_from_layers,
)

OUTPUT_PATH = ROOT / "data" / "processed" / "tectonic_boundary_sensitivity.json"
ASTHENOSPHERE_DENSITY_KG_M3 = 3_300.0
CRUST_DENSITY_KG_M3 = 2_700.0
CRUST_THICKNESS_M = 6_000.0
MANTLE_DENSITY_KG_M3 = 3_300.0
MANTLE_THICKNESS_M = 4_000.0
GRAVITY_M_S2 = 9.81
STIFFNESS_PA_PER_M = area_stiffness_pa_per_m_from_asthenosphere_density(
    ASTHENOSPHERE_DENSITY_KG_M3,
    GRAVITY_M_S2,
)
LITHOSTATIC_REFERENCE_TRACTION_PA = lithostatic_traction_pa_from_layers(
    (
        (CRUST_DENSITY_KG_M3, CRUST_THICKNESS_M),
        (MANTLE_DENSITY_KG_M3, MANTLE_THICKNESS_M),
    ),
    GRAVITY_M_S2,
)
PRESSURE_LEVELS_MPA = (12.0, 13.0, 14.0)
THRESHOLD_PRESSURES_MPA = tuple(np.arange(0.0, 14.0001, 0.1))
COHESION_PA = 1.0e6
TENSILE_STRENGTH_PA = 2.5e6


def _read_state(stem: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read mesh and final Cauchy stress for a PyLith boundary case."""
    domain_path = STEP_DIR / "output" / f"{stem}-domain.h5"
    material_path = STEP_DIR / "output" / f"{stem}-material.h5"
    with h5py.File(domain_path, "r") as domain:
        vertices = np.asarray(domain["geometry/vertices"], dtype=float)
        tetrahedra = np.asarray(domain["viz/topology/cells"], dtype=np.int64)
    with h5py.File(material_path, "r") as material:
        stress = np.asarray(material["cell_fields/cauchy_stress"][-1], dtype=float)
    if stress.shape != (len(tetrahedra), 6):
        raise ValueError(f"stress cell count does not match mesh for {stem}")
    if not all(np.all(np.isfinite(field)) for field in (vertices, stress)):
        raise ValueError(f"non-finite mesh or stress values in {stem}")
    return vertices, tetrahedra, stress


def _run_pair(
    *,
    tectonic_velocity_mm_per_year_per_face: float,
    cavity_pressure_mpa: float,
) -> tuple[dict[str, Any], dict[str, tuple[np.ndarray, ...]]]:
    """Solve the fixed-base reference and the illustrative Winkler case."""
    summary = run_check(
        STIFFNESS_PA_PER_M,
        tectonic_velocity_mm_per_year_per_face=(
            tectonic_velocity_mm_per_year_per_face
        ),
        cavity_pressure_mpa=cavity_pressure_mpa,
        nodes=8,
    )
    if summary.get("converged") is not True:
        raise RuntimeError("Winkler outer iteration did not converge")
    states = {
        "fixed_base": _read_state("fixed-base"),
        "winkler": _read_state("winkler"),
    }
    return summary, states


def _criterion_records(
    vertices: np.ndarray,
    tetrahedra: np.ndarray,
    equilibrium_stress: np.ndarray,
    pressure_stress: np.ndarray,
    tectonic_stress: np.ndarray,
) -> dict[str, Any]:
    """Evaluate pressure levels relative to gravity/prestress equilibrium."""
    records: dict[str, Any] = {}
    pressures = np.asarray(THRESHOLD_PRESSURES_MPA, dtype=float)
    stress_history = np.stack(
        [
            equilibrium_stress
            + pressure * (pressure_stress - equilibrium_stress)
            + (tectonic_stress - equilibrium_stress)
            for pressure in pressures
        ]
    )
    time_s = np.arange(1, len(pressures) + 1, dtype=float)
    criteria = (
        ("friction_angle_25_deg", {"friction_angle_deg": 25.0}),
        ("literal_friction_coefficient_25", {"friction_coefficient": 25.0}),
    )
    for name, friction in criteria:
        analysis = analyze_stress_history(
            vertices,
            tetrahedra,
            stress_history,
            time_s,
            cohesion_pa=COHESION_PA,
            pore_pressure_pa=0.0,
            tensile_strength_pa=TENSILE_STRENGTH_PA,
            **friction,
        )
        pressure_record_by_value = {
            round(float(pressure), 8): record
            for pressure, record in zip(
                pressures, analysis["records"], strict=True
            )
        }
        joint_onset = next(
            (
                float(pressure)
                for pressure, record in zip(
                    pressures, analysis["records"], strict=True
                )
                if record["joint_eruption_criterion_met"]
            ),
            None,
        )
        records[name] = {
            "joint_criterion_onset_mpa_at_0_1_mpa_resolution": joint_onset,
            "pressure_resolution_mpa": 0.1,
            "at_paper_thresholds": [
                {
                    "pressure_mpa": pressure,
                    "cavity_to_surface_shear_path_found": bool(
                        pressure_record_by_value[round(pressure, 8)][
                            "cavity_to_surface_shear_path_found"
                        ]
                    ),
                    "reservoir_tensile_failure": bool(
                        pressure_record_by_value[round(pressure, 8)][
                            "reservoir_tensile_failure"
                        ]
                    ),
                    "joint_criterion_met": bool(
                        pressure_record_by_value[round(pressure, 8)][
                            "joint_eruption_criterion_met"
                        ]
                    ),
                    "mohr_coulomb_yield_cell_count": int(
                        pressure_record_by_value[round(pressure, 8)][
                            "mohr_coulomb_shear_yield_cell_count"
                        ]
                    ),
                    "maximum_cavity_tensile_stress_mpa": float(
                        pressure_record_by_value[round(pressure, 8)][
                            "maximum_cavity_tensile_stress_pa"
                        ]
                        / 1.0e6
                    ),
                }
                for pressure in PRESSURE_LEVELS_MPA
            ],
        }
    return records


def run_grid() -> dict[str, Any]:
    """Run pressure and tectonic basis fields, then evaluate their sums."""
    basis: dict[str, dict[str, tuple[np.ndarray, ...]]] = {}
    check_summaries: list[dict[str, Any]] = []

    pressure_summary, pressure_states = _run_pair(
        tectonic_velocity_mm_per_year_per_face=0.0,
        cavity_pressure_mpa=1.0,
    )
    check_summaries.append(pressure_summary)
    for treatment, state in pressure_states.items():
        basis[f"{treatment}:pressure"] = state
    equilibrium_states = {
        treatment: _read_state(f"{stem}-equilibrium")
        for treatment, stem in (
            ("fixed_base", "fixed-base"),
            ("winkler", "winkler"),
        )
    }
    for treatment, state in equilibrium_states.items():
        basis[f"{treatment}:equilibrium"] = state

    for velocity in (20.0, 30.0):
        summary, tectonic_states = _run_pair(
            tectonic_velocity_mm_per_year_per_face=velocity,
            cavity_pressure_mpa=0.0,
        )
        check_summaries.append(summary)
        for treatment, state in tectonic_states.items():
            basis[f"{treatment}:tectonic:{velocity:g}"] = state

    cases: list[dict[str, Any]] = []
    for velocity in (0.0, 20.0, 30.0):
        for treatment in ("fixed_base", "winkler"):
            pressure_state = basis[f"{treatment}:pressure"]
            vertices, tetrahedra, pressure_stress = pressure_state
            equilibrium_state = basis[f"{treatment}:equilibrium"]
            equilibrium_vertices, equilibrium_tetrahedra, equilibrium_stress = (
                equilibrium_state
            )
            if not np.array_equal(vertices, equilibrium_vertices) or not np.array_equal(
                tetrahedra, equilibrium_tetrahedra
            ):
                raise ValueError("equilibrium and pressure solves used different meshes")
            if velocity == 0.0:
                tectonic_stress = equilibrium_stress
            else:
                tectonic_state = basis[f"{treatment}:tectonic:{velocity:g}"]
                tectonic_vertices, tectonic_tetrahedra, tectonic_stress = tectonic_state
                if not np.array_equal(vertices, tectonic_vertices) or not np.array_equal(
                    tetrahedra, tectonic_tetrahedra
                ):
                    raise ValueError("basis solves did not use an identical mesh")
            cases.append(
                {
                    "basal_treatment": treatment,
                    "tectonic_per_face_velocity_mm_per_year": velocity,
                    "full_spreading_rate_mm_per_year": 2.0 * velocity,
                    "criteria": _criterion_records(
                        vertices,
                        tetrahedra,
                        equilibrium_stress,
                        pressure_stress,
                        tectonic_stress,
                    ),
                }
            )

    result: dict[str, Any] = {
        "method": (
            "linear static elasticity; pressure and one-year tectonic increments "
            "are superposed on the PyLith gravity/lithostatic equilibrium stress"
        ),
        "tectonic_loading_direction": (
            "project +x/east; its geographic ridge-normal azimuth is unresolved"
        ),
        "geometry": "50 km x 50 km x 10 km with the Axial ellipsoidal cavity",
        "mesh_tetrahedra": int(basis["fixed_base:pressure"][2].shape[0]),
        "mpi_ranks": 8,
        "per_process_address_space_limit_gib": 4,
        "solver_timeout_seconds": 300,
        "basal_cases": {
            "fixed_base": (
                "paper's very stiff Winkler limit, represented by zero "
                "vertical displacement"
            ),
            "winkler": {
                "area_stiffness_pa_per_m": STIFFNESS_PA_PER_M,
                "stiffness_basis": (
                    "Galgana k_W = rho_asthenosphere * g; regional Juan de Fuca "
                    "upper-mantle density"
                ),
                "status": "literature-calibrated regional prior for Axial",
                "prestress_global_up_pa": LITHOSTATIC_REFERENCE_TRACTION_PA,
                "prestress_basis": (
                    "6 km crust at 2700 kg/m3 plus 4 km mantle at "
                    "3300 kg/m3, multiplied by 9.81 m/s2"
                ),
                "prestress_application": (
                    "gravity and linear lithostatic reference stress are solved "
                    "with matching hydrostatic cavity and basal tractions; the "
                    "equilibrium stress is retained in absolute failure checks"
                ),
                "incremental_traction_offset": (
                    "the calibrated prestress initializes the Neumann spring "
                    "iteration; convergence is measured against the incremental "
                    "spring traction, not the absolute prestress"
                ),
            },
        },
        "loading_cases": [
            {
                "per_face_velocity_mm_per_year": velocity,
                "full_spreading_rate_mm_per_year": 2.0 * velocity,
                "one_year_displacement_magnitude_per_face_mm": velocity,
            }
            for velocity in (0.0, 20.0, 30.0)
        ],
        "failure_parameters": {
            "cohesion_mpa": COHESION_PA / 1.0e6,
            "pore_pressure_mpa": 0.0,
            "tensile_strength_mpa": TENSILE_STRENGTH_PA / 1.0e6,
            "friction_interpretations": ["phi=25 degrees", "literal f=25"],
            "pressure_levels_mpa": list(PRESSURE_LEVELS_MPA),
            "onset_search_resolution_mpa": 0.1,
        },
        "cases": cases,
        "winkler_outer_iteration_solves": [
            {
                "tectonic_per_face_velocity_mm_per_year": item[
                    "tectonic_loading"]["per_face_velocity_mm_per_year"],
                "cavity_pressure_mpa": item["cavity_overpressure_mpa"],
                "iterations": len(item["iterations"]),
                "converged": item["converged"],
                "final_max_traction_residual_pa": item["iterations"][-1][
                    "max_abs_traction_residual_pa"
                ],
            }
            for item in check_summaries
        ],
        "pressure_only_surface_compliance_mm_per_mpa": {
            treatment: {
                "central": float(
                    pressure_summary[
                        "fixed_base_central_vertical_compliance_m_per_mpa"
                        if treatment == "fixed_base"
                        else "central_vertical_compliance_m_per_mpa"
                    ]
                    * 1_000.0
                ),
                "eastern": float(
                    pressure_summary[
                        "fixed_base_east_vertical_compliance_m_per_mpa"
                        if treatment == "fixed_base"
                        else "east_vertical_compliance_m_per_mpa"
                    ]
                    * 1_000.0
                ),
            }
            for treatment in ("fixed_base", "winkler")
        },
        "limitations": [
            "static elastic boundary sensitivity, not the two-year Maxwell model",
            "one-year imposed displacement is used to represent the published velocity",
            "the regional mantle density is a prior, not an Axial-depth measurement",
            "the equilibrium uses a depth-averaged density for the layered 10 km column",
            "pressure levels use linear superposition of static elastic stress fields",
            "the mesh is not converged; failure parameters retain the prior screening assumptions",
        ],
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    result = run_grid()
    print(json.dumps(result, indent=2))
    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
