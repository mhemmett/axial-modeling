"""Build or validate a synthetic PyLith generalized Maxwell smoke case."""

from __future__ import annotations

import argparse
from pathlib import Path

import h5py
import numpy as np

from axialstress.material_database import (
    write_temperature_dependent_generalized_maxwell_database,
)
from axialstress.thermal import temperature_dependent_viscosity_pa_s
from axialstress.thermal_model import (
    _read_gmsh_tetrahedral_mesh,
    solve_written_thermal_model,
)

YOUNGS_MODULUS_PA = 50.0e9
DENSITY_KG_M3 = 2800.0
POISSON_RATIO = 0.25
REFERENCE_VISCOSITY_PA_S_BY_BRANCH = np.array([1.0e18, 5.0e17, 2.0e18])
SHEAR_RATIO_BY_BRANCH = np.array([0.25, 0.25, 0.25])
REFERENCE_TEMPERATURE_C = 1200.0
END_TIME_S = 63_115_200.0


def build_material_database(
    mesh_path: Path,
    database_path: Path,
    temperature_archive_path: Path,
) -> tuple[int, float, float]:
    """Write three-branch properties from a steady synthetic temperature field."""
    vertices, tetrahedra, _ = _read_gmsh_tetrahedral_mesh(mesh_path)
    iterations, relative_change, minimum, maximum, *_ = solve_written_thermal_model(
        mesh_path,
        temperature_archive_path,
        hydrothermal=True,
    )
    with np.load(temperature_archive_path, allow_pickle=False) as archive:
        if not np.array_equal(vertices, archive["vertices_m"]):
            raise SystemExit("thermal archive vertices do not match the PyLith mesh")
        if not np.array_equal(tetrahedra, archive["tetrahedra"]):
            raise SystemExit("thermal archive cells do not match the PyLith mesh")
        temperature_c = archive["temperature_c"]
    write_temperature_dependent_generalized_maxwell_database(
        database_path,
        vertices,
        tetrahedra,
        temperature_c,
        YOUNGS_MODULUS_PA,
        density_kg_m3=DENSITY_KG_M3,
        poisson_ratio=POISSON_RATIO,
        reference_viscosity_pa_s_by_branch=REFERENCE_VISCOSITY_PA_S_BY_BRANCH,
        reference_temperature_c=REFERENCE_TEMPERATURE_C,
        shear_modulus_ratio_by_branch=SHEAR_RATIO_BY_BRANCH,
    )
    print(
        f"Hydrothermal temperature solve converged in {iterations} iterations; "
        f"relative change={relative_change:.3e}; temperature=[{minimum:.3f}, "
        f"{maximum:.3f}] °C."
    )
    return len(tetrahedra), minimum, maximum


def check_solution(
    database_path: Path,
    material_path: Path,
    temperature_archive_path: Path,
) -> None:
    """Check thermal branch viscosities and PyLith state and stress output."""
    database = np.atleast_2d(np.loadtxt(database_path, comments="#", skiprows=13))
    if database.ndim != 2 or database.shape[1] != 36:
        raise SystemExit(f"material database has unexpected shape {database.shape}")
    if not np.all(np.isfinite(database)):
        raise SystemExit("material database contains non-finite values")
    with np.load(temperature_archive_path, allow_pickle=False) as archive:
        temperatures = archive["temperature_c"]
        tetrahedra = archive["tetrahedra"]
    cell_temperature_c = temperatures[tetrahedra].mean(axis=1)
    viscosity_factor = temperature_dependent_viscosity_pa_s(cell_temperature_c) / (
        temperature_dependent_viscosity_pa_s(REFERENCE_TEMPERATURE_C)
    )
    expected_viscosities = (
        REFERENCE_VISCOSITY_PA_S_BY_BRANCH[:, np.newaxis]
        * viscosity_factor[np.newaxis, :]
    )
    if not np.allclose(database[:, 6:9], expected_viscosities.T, rtol=1.0e-12):
        raise SystemExit("material database viscosities do not match the thermal field")
    expected_ratios = np.broadcast_to(SHEAR_RATIO_BY_BRANCH, (len(database), 3))
    if not np.allclose(database[:, 9:12], expected_ratios):
        raise SystemExit("material database branch fractions changed")
    if not np.all(np.ptp(database[:, 6:9], axis=0) > 0.0):
        raise SystemExit("temperature-dependent branch viscosities are not spatially variable")
    if np.any(database[:, 12:] != 0.0):
        raise SystemExit("initial generalized Maxwell strains must be zero")

    with h5py.File(material_path, "r") as material:
        final_time_s = float(np.asarray(material["time"]).reshape(-1)[-1])
        stress = np.asarray(material["cell_fields/cauchy_stress"][-1], dtype=float)
        state_fields = [
            name
            for name in material["cell_fields"]
            if name.startswith("viscous_strain")
        ]
        states = [
            np.asarray(material[f"cell_fields/{name}"][-1], dtype=float)
            for name in state_fields
        ]
        number_of_cells = len(material["viz/topology/cells"])
    if not np.isclose(final_time_s, END_TIME_S, rtol=0.0, atol=1.0e-6):
        raise SystemExit(f"PyLith ended at {final_time_s:g} s, expected {END_TIME_S:g} s")
    if number_of_cells != len(database):
        raise SystemExit("PyLith output cell count differs from the material database")
    if not np.all(np.isfinite(stress)) or np.max(np.abs(stress)) <= 0.0:
        raise SystemExit("PyLith stress is zero or non-finite")
    if not states or any(not np.all(np.isfinite(state)) for state in states):
        raise SystemExit("PyLith generalized Maxwell state is missing or non-finite")
    if len(states) != 1 or states[0].shape != (number_of_cells, 18):
        raise SystemExit("PyLith output must contain three six-component branch states")
    branch_magnitudes = np.max(np.abs(states[0].reshape(number_of_cells, 3, 6)), axis=(0, 2))
    if np.any(branch_magnitudes <= 0.0):
        raise SystemExit("one or more generalized Maxwell branches did not evolve")

    print(
        "Generalized Maxwell smoke passed at t = 63,115,200 s; "
        f"cells={number_of_cells}; state fields={state_fields}; "
        f"peak stress={np.max(np.abs(stress)):.6g} Pa; "
        f"temperature=[{np.min(temperatures):.3f}, {np.max(temperatures):.3f}] °C; "
        f"branch viscosities=[{np.min(database[:, 6:9], axis=0).tolist()}, "
        f"{np.max(database[:, 6:9], axis=0).tolist()}] Pa*s; "
        f"branch peak viscous strains={branch_magnitudes.tolist()}."
    )


def main() -> None:
    """Build branch material properties or validate the completed smoke run."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build", help="write the synthetic material database")
    build.add_argument("--mesh", type=Path, required=True)
    build.add_argument("--database", type=Path, required=True)
    build.add_argument("--temperature-archive", type=Path, required=True)
    check = subparsers.add_parser("check", help="validate PyLith material output")
    check.add_argument("--database", type=Path, required=True)
    check.add_argument("--material", type=Path, required=True)
    check.add_argument("--temperature-archive", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "build":
        args.database.parent.mkdir(parents=True, exist_ok=True)
        cell_count, _, _ = build_material_database(
            args.mesh,
            args.database,
            args.temperature_archive,
        )
        print(
            "Wrote temperature-dependent generalized Maxwell properties "
            f"for {cell_count} tetrahedra."
        )
    else:
        check_solution(args.database, args.material, args.temperature_archive)


if __name__ == "__main__":
    main()
