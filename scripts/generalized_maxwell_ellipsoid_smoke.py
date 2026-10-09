"""Build or validate a synthetic PyLith generalized Maxwell smoke case."""

from __future__ import annotations

import argparse
from pathlib import Path

import h5py
import numpy as np

from axialstress.generalized_maxwell import (
    generalized_maxwell_relaxation_times_s,
    reconstruct_generalized_maxwell_stress_pa,
)
from axialstress.material_database import write_generalized_maxwell_database
from axialstress.thermal_model import _read_gmsh_tetrahedral_mesh

YOUNGS_MODULUS_PA = 50.0e9
DENSITY_KG_M3 = 2800.0
POISSON_RATIO = 0.25
VISCOSITY_PA_S_BY_BRANCH = np.array([1.0e18, 5.0e17, 2.0e18])
SHEAR_RATIO_BY_BRANCH = np.array([0.25, 0.25, 0.25])
END_TIME_S = 63_115_200.0
STRESS_RECONSTRUCTION_RELATIVE_TOLERANCE = 1.0e-12


def build_material_database(mesh_path: Path, database_path: Path) -> int:
    """Write synthetic three-branch properties for the generated Gmsh mesh."""
    vertices, tetrahedra, _ = _read_gmsh_tetrahedral_mesh(mesh_path)
    write_generalized_maxwell_database(
        database_path,
        vertices,
        tetrahedra,
        YOUNGS_MODULUS_PA,
        density_kg_m3=DENSITY_KG_M3,
        poisson_ratio=POISSON_RATIO,
        viscosity_pa_s_by_branch=VISCOSITY_PA_S_BY_BRANCH,
        shear_modulus_ratio_by_branch=SHEAR_RATIO_BY_BRANCH,
    )
    return len(tetrahedra)


def check_solution(database_path: Path, material_path: Path) -> None:
    """Check PyLith accepted all branches and wrote finite state and stress."""
    database = np.atleast_2d(np.loadtxt(database_path, comments="#", skiprows=13))
    if database.ndim != 2 or database.shape[1] != 36:
        raise SystemExit(f"material database has unexpected shape {database.shape}")
    if not np.all(np.isfinite(database)):
        raise SystemExit("material database contains non-finite values")
    expected_branches = np.concatenate((VISCOSITY_PA_S_BY_BRANCH, SHEAR_RATIO_BY_BRANCH))
    if not np.allclose(database[:, 6:12], expected_branches[np.newaxis, :]):
        raise SystemExit("material database branch viscosities or fractions changed")
    if np.any(database[:, 12:] != 0.0):
        raise SystemExit("initial generalized Maxwell strains must be zero")

    with h5py.File(material_path, "r") as material:
        output_times_s = np.asarray(material["time"], dtype=float).reshape(-1)
        stress_history_pa = np.asarray(
            material["cell_fields/cauchy_stress"], dtype=float
        )
        strain_history = np.asarray(material["cell_fields/cauchy_strain"], dtype=float)
        state_fields = [
            name
            for name in material["cell_fields"]
            if name.startswith("viscous_strain")
        ]
        state_histories = [
            np.asarray(material[f"cell_fields/{name}"], dtype=float)
            for name in state_fields
        ]
        number_of_cells = len(material["viz/topology/cells"])
    final_time_s = float(output_times_s[-1])
    if not np.isclose(final_time_s, END_TIME_S, rtol=0.0, atol=1.0e-6):
        raise SystemExit(f"PyLith ended at {final_time_s:g} s, expected {END_TIME_S:g} s")
    if number_of_cells != len(database):
        raise SystemExit("PyLith output cell count differs from the material database")
    expected_stress_shape = (len(output_times_s), number_of_cells, 6)
    if stress_history_pa.shape != expected_stress_shape:
        raise SystemExit(f"PyLith stress has unexpected shape {stress_history_pa.shape}")
    if strain_history.shape != expected_stress_shape:
        raise SystemExit(f"PyLith strain has unexpected shape {strain_history.shape}")
    if not np.all(np.isfinite(stress_history_pa)) or np.max(np.abs(stress_history_pa)) <= 0.0:
        raise SystemExit("PyLith stress is zero or non-finite")
    if not state_histories or any(
        not np.all(np.isfinite(state)) for state in state_histories
    ):
        raise SystemExit("PyLith generalized Maxwell state is missing or non-finite")
    if len(state_histories) != 1 or state_histories[0].shape != (
        len(output_times_s),
        number_of_cells,
        18,
    ):
        raise SystemExit("PyLith output must contain three six-component branch states")
    state_by_branch = state_histories[0].reshape(
        len(output_times_s), number_of_cells, 3, 6
    )
    branch_magnitudes = np.max(np.abs(state_by_branch[-1]), axis=(0, 2))
    if np.any(branch_magnitudes <= 0.0):
        raise SystemExit("one or more generalized Maxwell branches did not evolve")

    predicted_stress_pa = reconstruct_generalized_maxwell_stress_pa(
        strain_history,
        state_by_branch,
        YOUNGS_MODULUS_PA,
        POISSON_RATIO,
        SHEAR_RATIO_BY_BRANCH,
    )
    stress_relative_error = float(
        np.linalg.norm(predicted_stress_pa - stress_history_pa)
        / np.linalg.norm(stress_history_pa)
    )
    if stress_relative_error > STRESS_RECONSTRUCTION_RELATIVE_TOLERANCE:
        raise SystemExit(
            "PyLith stress does not match the independent constitutive "
            f"reconstruction: relative error={stress_relative_error:.3e}"
        )

    relaxation_times_s = generalized_maxwell_relaxation_times_s(
        YOUNGS_MODULUS_PA,
        POISSON_RATIO,
        VISCOSITY_PA_S_BY_BRANCH,
        SHEAR_RATIO_BY_BRANCH,
    )
    maximum_step_s = float(np.max(np.diff(output_times_s)))
    stable_step_limit_s = float(np.min(relaxation_times_s) / 5.0)
    if maximum_step_s > stable_step_limit_s:
        raise SystemExit(
            f"PyLith output step {maximum_step_s:g} s exceeds the stable "
            f"one-fifth relaxation-time limit {stable_step_limit_s:g} s"
        )

    print(
        "Generalized Maxwell smoke passed at t = 63,115,200 s; "
        f"cells={number_of_cells}; state fields={state_fields}; "
        f"peak stress={np.max(np.abs(stress_history_pa[-1])):.6g} Pa; "
        f"branch peak viscous strains={branch_magnitudes.tolist()}; "
        f"stress reconstruction relative error={stress_relative_error:.3e}; "
        f"maximum step={maximum_step_s:.6g} s; "
        f"minimum relaxation time={np.min(relaxation_times_s):.6g} s."
    )


def main() -> None:
    """Build branch material properties or validate the completed smoke run."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build", help="write the synthetic material database")
    build.add_argument("--mesh", type=Path, required=True)
    build.add_argument("--database", type=Path, required=True)
    check = subparsers.add_parser("check", help="validate PyLith material output")
    check.add_argument("--database", type=Path, required=True)
    check.add_argument("--material", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "build":
        args.database.parent.mkdir(parents=True, exist_ok=True)
        cell_count = build_material_database(args.mesh, args.database)
        print(f"Wrote generalized Maxwell properties for {cell_count} tetrahedra.")
    else:
        check_solution(args.database, args.material)


if __name__ == "__main__":
    main()
