"""Measure short PyLith pressure-to-stress responses for source-value rheologies."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
from pathlib import Path

import h5py
import historical_pylith as historical
import numpy as np

from axialstress.failure_analysis import analyze_stress_history
from axialstress.material_database import write_single_maxwell_database
from axialstress.paper_bpr import file_sha256
from axialstress.thermal import (
    evaluate_eq16_youngs_modulus_pa,
    temperature_dependent_viscosity_pa_s,
)
from axialstress.thermal_model import _read_gmsh_tetrahedral_mesh, solve_written_thermal_model

ROOT = Path(__file__).resolve().parents[1]
STEP_DIR = ROOT / "pylith" / "step06_maxwell_ellipsoid"
PYLITH_ROOT = ROOT / "pylith" / "pylith-5.0.2-linux-x86_64"
FINE_BASIS = ROOT / "data" / "processed" / "refined_elastic_basis_150m"
MESH = FINE_BASIS / "axial_ellipsoid.msh"
EQUILIBRIUM = FINE_BASIS / "fixed-base-equilibrium-material.h5"
OUTPUT = ROOT / "data" / "processed" / "source_value_maxwell_cases"
DENSITY_KG_M3 = 2940.0
POISSON_RATIO = 0.25
ELASTIC_MODULUS_PA = 50.0e9
SECONDS_PER_DAY = 86_400.0


def _write_run(
    run_dir: Path,
    mesh_path: Path,
    material_path: Path,
    *,
    elapsed_seconds: np.ndarray,
    pressure_mpa: np.ndarray,
    time_step_s: float,
) -> None:
    """Configure one time-dependent pressure history for single-branch PyLith."""
    (run_dir / "mesh").mkdir(parents=True, exist_ok=True)
    (run_dir / "output").mkdir(parents=True, exist_ok=True)
    shutil.copy2(mesh_path, run_dir / "mesh" / "axial_ellipsoid.msh")
    shutil.copy2(material_path, run_dir / "material_initial.spatialdb")
    shutil.copy2(STEP_DIR / "bc_zero.spatialdb", run_dir / "bc_zero.spatialdb")
    historical._write_cavity_database(run_dir / "bc_cavity.spatialdb")
    historical._write_pressure_history(
        run_dir / "pressure.timedb",
        elapsed_seconds,
        pressure_mpa,
        support_interval_s=time_step_s,
    )
    config = (STEP_DIR / "step06.cfg").read_text(encoding="utf-8")
    config, end_count = re.subn(
        r"(?m)^end_time\s*=.*$", f"end_time = {elapsed_seconds[-1]:.12g}*s", config
    )
    config, dt_count = re.subn(
        r"(?m)^initial_dt\s*=.*$",
        f"initial_dt = {time_step_s:.12g}*s",
        config,
    )
    if end_count != 1 or dt_count != 1:
        raise ValueError("single-branch Maxwell time settings were not found")
    cavity_line = "db_auxiliary_field.iohandler.filename = bc_cavity.spatialdb"
    if config.count(cavity_line) != 1:
        raise ValueError("single-branch Maxwell cavity database was not found")
    config = config.replace(
        cavity_line,
        "use_time_history = True\n"
        f"{cavity_line}\n"
        "time_history = spatialdata.spatialdb.TimeHistory\n"
        "time_history.description = Prescribed cavity pressure history\n"
        "time_history.filename = pressure.timedb",
    )
    (run_dir / "step06.cfg").write_text(config, encoding="utf-8")
    app = (STEP_DIR / "pylithapp.cfg").read_text(encoding="utf-8")
    if app.count("db_auxiliary_field.iohandler.filename = material_initial.spatialdb") != 1:
        raise ValueError("single-branch Maxwell material database was not found")
    app = app.replace(
        "db_auxiliary_field.iohandler.filename = material_initial.spatialdb",
        "db_auxiliary_field.query_type = nearest\n"
        "db_auxiliary_field.iohandler.filename = material_initial.spatialdb",
    )
    (run_dir / "pylithapp.cfg").write_text(app, encoding="utf-8")


def _run_pylith(run_dir: Path) -> None:
    """Run one bounded eight-rank PyLith Maxwell pressure history."""
    command = (
        f"cd {shlex.quote(str(PYLITH_ROOT))} && source setup.sh && "
        f"cd {shlex.quote(str(run_dir))} && timeout 300 pylith --nodes=8 step06.cfg"
    )
    log_path = run_dir / "output" / "pylith.log"
    with log_path.open("w", encoding="utf-8") as log:
        completed = subprocess.run(
            ["bash", "-lc", command],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if completed.returncode:
        tail = "\n".join(log_path.read_text(encoding="utf-8").splitlines()[-40:])
        raise RuntimeError(f"PyLith Maxwell run failed ({completed.returncode}):\n{tail}")


def _read_stress(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Read PyLith stress history and its geometry in SI units."""
    with h5py.File(path, "r") as material:
        times_s = np.asarray(material["time"], dtype=float).reshape(-1)
        vertices = np.asarray(material["geometry/vertices"], dtype=float)
        cells = np.asarray(material["viz/topology/cells"], dtype=np.int64)
        stress = np.asarray(material["cell_fields/cauchy_stress"], dtype=float)
    if stress.shape != (len(times_s), len(cells), 6) or not np.all(np.isfinite(stress)):
        raise ValueError(f"invalid PyLith Cauchy stress in {path}")
    return times_s, vertices, cells, stress


def _reference_stress(
    reference_path: Path, vertices: np.ndarray, cells: np.ndarray
) -> np.ndarray:
    """Require an identical mesh before adding lithostatic equilibrium stress."""
    _, reference_vertices, reference_cells, reference = _read_stress(reference_path)
    if not np.array_equal(vertices, reference_vertices) or not np.array_equal(
        cells, reference_cells
    ):
        raise ValueError("Maxwell and equilibrium stress fields use different cell ordering")
    return reference[-1]


def _case_properties(
    case: str,
    mesh_path: Path,
    output_dir: Path,
    vertices: np.ndarray,
    cells: np.ndarray,
    uniform_viscosity_pa_s: float | None,
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Map only source equations or an explicit uniform viscosity to cells."""
    if case not in {"constant_maxwell", "thermal_maxwell", "hydrothermal_maxwell"}:
        raise ValueError(f"unknown Maxwell case: {case}")
    if case == "constant_maxwell":
        if uniform_viscosity_pa_s is None:
            raise ValueError("constant Maxwell viscosity must be supplied explicitly")
        modulus = np.full(len(cells), ELASTIC_MODULUS_PA)
        viscosity = np.full(len(cells), uniform_viscosity_pa_s)
        return modulus, viscosity, {
            "modulus_law": "uniform Table S1 brittle modulus",
            "viscosity_law": "explicit user input; absent from Table S1",
            "uniform_viscosity_pa_s": uniform_viscosity_pa_s,
        }

    hydrothermal = case == "hydrothermal_maxwell"
    archive = output_dir / f"{case}_temperature.npz"
    thermal = solve_written_thermal_model(mesh_path, archive, hydrothermal=hydrothermal)
    with np.load(archive, allow_pickle=False) as saved:
        thermal_vertices = np.asarray(saved["vertices_m"], dtype=float)
        thermal_cells = np.asarray(saved["tetrahedra"], dtype=np.int64)
        temperature_c = np.asarray(saved["temperature_c"], dtype=float)
    if not np.array_equal(vertices, thermal_vertices) or not np.array_equal(
        cells, thermal_cells
    ):
        raise ValueError("thermal and mechanics tetrahedra do not match")
    cell_temperature_c = temperature_c[cells].mean(axis=1)
    modulus = evaluate_eq16_youngs_modulus_pa(cell_temperature_c)
    viscosity = temperature_dependent_viscosity_pa_s(cell_temperature_c)
    return modulus, viscosity, {
        "modulus_law": "supplement Eq. 16, literally as printed",
        "modulus_conflict": "increases with temperature, contrary to brittle/ductile labels",
        "viscosity_law": "supplement Eq. 15 with Table S1 constants and kelvin conversion",
        "conductivity_law": "supplement Eq. 22" if hydrothermal else "Table S1 k0",
        "thermal_outer_boundary_assumption": "30 C/km on all external faces",
        "thermal_iterations": thermal[0],
        "thermal_relative_change": thermal[1],
        "cell_temperature_range_c": [
            float(cell_temperature_c.min()),
            float(cell_temperature_c.max()),
        ],
        "temperature_archive_sha256": file_sha256(archive),
    }


def main() -> None:
    """Save material maps and two-step-size pressure-to-stress diagnostics."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=Path, default=MESH)
    parser.add_argument("--equilibrium", type=Path, default=EQUILIBRIUM)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--uniform-viscosity-pa-s", type=float)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    args.mesh = args.mesh.resolve()
    args.equilibrium = args.equilibrium.resolve()
    args.output_dir = args.output_dir.resolve()
    if args.output_dir.exists() and any(args.output_dir.iterdir()) and not args.overwrite:
        raise FileExistsError(f"output directory is not empty: {args.output_dir}")
    if args.uniform_viscosity_pa_s is not None and (
        not np.isfinite(args.uniform_viscosity_pa_s) or args.uniform_viscosity_pa_s <= 0.0
    ):
        raise ValueError("uniform viscosity must be finite and positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    vertices, cells, _ = _read_gmsh_tetrahedral_mesh(args.mesh)
    case_names = ["thermal_maxwell", "hydrothermal_maxwell"]
    if args.uniform_viscosity_pa_s is not None:
        case_names.insert(0, "constant_maxwell")
    cases = {}
    for case in case_names:
        modulus, viscosity, property_notes = _case_properties(
            case,
            args.mesh,
            args.output_dir,
            vertices,
            cells,
            args.uniform_viscosity_pa_s,
        )
        material_path = args.output_dir / f"{case}.spatialdb"
        write_single_maxwell_database(
            material_path,
            vertices,
            cells,
            modulus,
            viscosity,
            density_kg_m3=DENSITY_KG_M3,
            poisson_ratio=POISSON_RATIO,
        )
        step_results = {}
        stress_at_day_14 = {}
        for step_days in (7, 1):
            run_dir = args.output_dir / "runs" / case / f"dt_{step_days}d"
            _write_run(
                run_dir,
                args.mesh,
                material_path,
                elapsed_seconds=np.asarray([0.0, 7.0, 14.0]) * SECONDS_PER_DAY,
                pressure_mpa=np.asarray([0.0, 1.0, 1.0]),
                time_step_s=step_days * SECONDS_PER_DAY,
            )
            _run_pylith(run_dir)
            times_s, output_vertices, output_cells, stress = _read_stress(
                run_dir / "output" / "maxwell-material.h5"
            )
            if not np.isclose(times_s[-1], 14 * SECONDS_PER_DAY, atol=0.01):
                raise ValueError("Maxwell run ended before day 14")
            reference = _reference_stress(
                args.equilibrium, output_vertices, output_cells
            )
            total_stress = stress + reference[np.newaxis]
            analysis = analyze_stress_history(
                output_vertices,
                output_cells,
                total_stress,
                times_s,
                cohesion_pa=1.0e6,
                friction_angle_deg=25.0,
                pore_pressure_pa=0.0,
            )
            stress_at_day_14[step_days] = stress[-1]
            step_results[f"{step_days}d"] = {
                "saved_steps": len(times_s),
                "day_14_peak_abs_incremental_stress_pa": float(
                    np.max(np.abs(stress[-1]))
                ),
                "day_14_maximum_cavity_principal_stress_pa": analysis["records"][-1][
                    "maximum_cavity_principal_stress_pa"
                ],
                "day_14_connected_shear_path": analysis["records"][-1][
                    "cavity_to_surface_shear_path_found"
                ],
                "material_output_sha256": file_sha256(
                    run_dir / "output" / "maxwell-material.h5"
                ),
            }
        difference = stress_at_day_14[7] - stress_at_day_14[1]
        denominator = np.linalg.norm(stress_at_day_14[1])
        relative_difference = float(np.linalg.norm(difference) / denominator)
        cases[case] = {
            "material_sha256": file_sha256(material_path),
            "youngs_modulus_range_pa": [float(modulus.min()), float(modulus.max())],
            "viscosity_range_pa_s": [float(viscosity.min()), float(viscosity.max())],
            "maxwell_time_range_s": [
                float(np.min(viscosity * 2.0 * (1.0 + POISSON_RATIO) / modulus)),
                float(np.max(viscosity * 2.0 * (1.0 + POISSON_RATIO) / modulus)),
            ],
            "property_notes": property_notes,
            "steps": step_results,
            "day_14_stress_relative_l2_step_difference": relative_difference,
        }
        print(f"{case}: day-14 7d-vs-1d stress difference {relative_difference:.4g}", flush=True)
    summary = {
        "method": "source-value single-branch Maxwell material and 14-day PyLith pressure response",
        "status": "temporal_resolution_diagnostic_not_bpr_failure_threshold",
        "paper_output_data_used": False,
        "mesh_sha256": file_sha256(args.mesh),
        "equilibrium_sha256": file_sha256(args.equilibrium),
        "mesh_tetrahedra": len(cells),
        "pressure_ramp_mpa": [0.0, 1.0, 1.0],
        "pressure_ramp_days": [0.0, 7.0, 14.0],
        "density_kg_m3_assumption": DENSITY_KG_M3,
        "poisson_ratio_assumption": POISSON_RATIO,
        "one_branch_maxwell_assumption": True,
        "baseline_stress": (
            "PyLith gravity-equilibrated fixed-base elastic reference on the identical mesh"
        ),
        "initial_viscous_strain_assumption": 0.0,
        "cases": cases,
        "omitted_constant_viscosity_case": args.uniform_viscosity_pa_s is None,
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": summary["status"], "cases": list(cases)}, indent=2))


if __name__ == "__main__":
    main()
