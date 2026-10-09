"""Run four bounded rheology cases under a shared synthetic cavity load."""

from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import h5py
import numpy as np
from scipy.spatial import cKDTree

from axialstress.failure_analysis import analyze_stress_history
from axialstress.generalized_maxwell import (
    generalized_maxwell_relaxation_times_s,
    reconstruct_generalized_maxwell_stress_pa,
)
from axialstress.material_database import (
    write_elastic_database,
    write_generalized_maxwell_database,
    write_temperature_dependent_generalized_maxwell_database,
)
from axialstress.thermal import temperature_range_youngs_modulus_pa
from axialstress.thermal_model import (
    _read_gmsh_tetrahedral_mesh,
    solve_written_thermal_model,
)

ROOT = Path(__file__).resolve().parents[1]
PYLITH_ROOT = ROOT / "pylith" / "pylith-5.0.2-linux-x86_64"
ELASTIC_STEP = ROOT / "pylith" / "step05_ellipsoid_elastic"
MAXWELL_STEP = ROOT / "pylith" / "step12_generalized_maxwell_ellipsoid"
SUMMARY_PATH = ROOT / "data" / "processed" / "rheology_case_matrix_summary.json"
MODEL_DATA_PATH = ROOT / "data" / "processed" / "rheology_case_matrix_model_data.npz"

YOUNGS_MODULUS_PA = 50.0e9
DENSITY_KG_M3 = 2800.0
POISSON_RATIO = 0.25
REFERENCE_VISCOSITY_PA_S_BY_BRANCH = np.array([1.0e18, 5.0e17, 2.0e18])
SHEAR_RATIO_BY_BRANCH = np.array([0.25, 0.25, 0.25])
REFERENCE_TEMPERATURE_C = 1200.0
END_TIME_S = 63_115_200.0
TIME_STEP_S = 2_592_000.0
COHESION_PA = 1.0e6
FRICTION_ANGLE_DEG = 25.0
STRESS_RECONSTRUCTION_TOLERANCE = 1.0e-12


def _generate_mesh(mesh_path: Path, log_path: Path) -> int:
    """Generate the shared ellipsoid mesh and return its tetrahedron count."""
    mesh_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "meshing" / "axial_ellipsoid_bpr.py"),
                "--output",
                str(mesh_path),
            ],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )
    match = re.search(r"Wrote .*: (\d+) tetrahedra", log_path.read_text(encoding="utf-8"))
    if match is None:
        raise RuntimeError(f"mesh count missing from {log_path}")
    return int(match.group(1))


def _run_pylith(run_dir: Path, config_name: str, log_name: str) -> None:
    """Run one bounded PyLith case and include its log tail on failure."""
    log_path = run_dir / "output" / log_name
    command = (
        f"cd {shlex.quote(str(PYLITH_ROOT))} && source setup.sh && "
        f"cd {shlex.quote(str(run_dir))} && "
        f"timeout 300 pylith {shlex.quote(config_name)}"
    )
    with log_path.open("w", encoding="utf-8") as log:
        completed = subprocess.run(
            ["bash", "-lc", command],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if completed.returncode:
        tail = "\n".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-50:])
        raise RuntimeError(f"PyLith case failed ({config_name}):\n{tail}")


def _case_directories(root: Path, case_name: str) -> tuple[Path, Path, Path]:
    """Create mesh and output directories for one case."""
    run_dir = root / case_name
    mesh_dir = run_dir / "mesh"
    output_dir = run_dir / "output"
    mesh_dir.mkdir(parents=True)
    output_dir.mkdir()
    return run_dir, mesh_dir, output_dir


def _read_material_database(path: Path) -> np.ndarray:
    """Read the numeric rows from a PyLith ASCII material database."""
    values = np.atleast_2d(np.loadtxt(path, comments="#", skiprows=13))
    if values.ndim != 2 or values.shape[1] != 36 or not np.all(np.isfinite(values)):
        raise RuntimeError(f"unexpected generalized Maxwell database in {path}")
    return values


def _run_elastic_case(root: Path, mesh_path: Path) -> dict[str, object]:
    """Run non-temperature-dependent elasticity at the common constant load."""
    run_dir, mesh_dir, output_dir = _case_directories(root, "non_td_elastic")
    shutil.copy2(mesh_path, mesh_dir / mesh_path.name)
    for filename in ("pylithapp.cfg", "step05.cfg", "bc_cavity.spatialdb", "bc_zero.spatialdb"):
        shutil.copy2(ELASTIC_STEP / filename, run_dir / filename)

    vertices, tetrahedra, _ = _read_gmsh_tetrahedral_mesh(mesh_path)
    write_elastic_database(
        run_dir / "mat_elastic.spatialdb",
        vertices,
        tetrahedra,
        YOUNGS_MODULUS_PA,
        density_kg_m3=DENSITY_KG_M3,
        poisson_ratio=POISSON_RATIO,
    )
    config_path = run_dir / "step05.cfg"
    config = config_path.read_text(encoding="utf-8")
    config = config.replace("initial_dt = 1.0*s", f"initial_dt = {TIME_STEP_S:g}*s")
    config = config.replace("end_time = 1.0*s", f"end_time = {END_TIME_S:g}*s")
    config_path.write_text(config, encoding="utf-8")
    _run_pylith(run_dir, "step05.cfg", "pylith.log")

    material_path = output_dir / "ellipsoid-material.h5"
    with h5py.File(material_path, "r") as material:
        times_s = np.asarray(material["time"], dtype=float).reshape(-1)
        stress = np.asarray(material["cell_fields/cauchy_stress"], dtype=float)
        vertices = np.asarray(material["geometry/vertices"], dtype=float)
        cells = np.asarray(material["viz/topology/cells"], dtype=np.int64)
    if times_s.size < 2 or not np.isclose(times_s[-1], END_TIME_S, rtol=0.0, atol=1.0e-3):
        raise RuntimeError("elastic PyLith history did not reach the shared end time")
    if stress.shape != (len(times_s), len(cells), 6) or not np.all(np.isfinite(stress)):
        raise RuntimeError("elastic PyLith stress history is missing or non-finite")

    failure = analyze_stress_history(
        vertices,
        cells,
        stress,
        times_s,
        cohesion_pa=COHESION_PA,
        friction_angle_deg=FRICTION_ANGLE_DEG,
        pore_pressure_pa=0.0,
    )
    maximum_cavity_tensile_stress_pa = max(
        record["maximum_cavity_tensile_stress_pa"] for record in failure["records"]
    )
    return {
        "case": "non-temperature-dependent elastic",
        "rheology": "isotropic linear elasticity",
        "temperature_property_mapping": False,
        "mesh_tetrahedra": len(cells),
        "output_records": len(times_s),
        "end_time_s": float(times_s[-1]),
        "maximum_absolute_cauchy_stress_pa": float(np.max(np.abs(stress))),
        "first_cavity_to_surface_path_time_s": failure[
            "first_cavity_to_surface_shear_path_time_s"
        ],
        "maximum_cavity_tensile_stress_pa": maximum_cavity_tensile_stress_pa,
    }


def _prepare_generalized_case(
    run_dir: Path,
    mesh_path: Path,
    vertices: np.ndarray,
    tetrahedra: np.ndarray,
    temperature_archive: Path,
    *,
    temperature_dependent: bool,
) -> tuple[np.ndarray, np.ndarray, Path]:
    """Write an assumption-labeled generalized Maxwell material database."""
    with np.load(temperature_archive, allow_pickle=False) as thermal:
        temperature_c = np.asarray(thermal["temperature_c"], dtype=float)
        thermal_cells = np.asarray(thermal["tetrahedra"], dtype=np.int64)
    if not np.array_equal(thermal_cells, tetrahedra):
        raise RuntimeError("thermal and mechanical mesh connectivity differs")
    cell_temperature_c = temperature_c[tetrahedra].mean(axis=1)
    youngs_modulus_pa = (
        temperature_range_youngs_modulus_pa(cell_temperature_c)
        if temperature_dependent
        else np.full(len(tetrahedra), YOUNGS_MODULUS_PA)
    )
    database_path = run_dir / "output" / "genmaxwell-material.spatialdb"
    if temperature_dependent:
        write_temperature_dependent_generalized_maxwell_database(
            database_path,
            vertices,
            tetrahedra,
            temperature_c,
            youngs_modulus_pa,
            density_kg_m3=DENSITY_KG_M3,
            poisson_ratio=POISSON_RATIO,
            reference_viscosity_pa_s_by_branch=REFERENCE_VISCOSITY_PA_S_BY_BRANCH,
            reference_temperature_c=REFERENCE_TEMPERATURE_C,
            shear_modulus_ratio_by_branch=SHEAR_RATIO_BY_BRANCH,
        )
    else:
        write_generalized_maxwell_database(
            database_path,
            vertices,
            tetrahedra,
            youngs_modulus_pa,
            density_kg_m3=DENSITY_KG_M3,
            poisson_ratio=POISSON_RATIO,
            viscosity_pa_s_by_branch=REFERENCE_VISCOSITY_PA_S_BY_BRANCH,
            shear_modulus_ratio_by_branch=SHEAR_RATIO_BY_BRANCH,
        )
    return temperature_c, youngs_modulus_pa, database_path


def _run_generalized_case(
    root: Path,
    mesh_path: Path,
    thermal_archive: Path,
    *,
    case_name: str,
    thermal_description: str,
    temperature_dependent: bool,
) -> dict[str, object]:
    """Run a three-branch material under the shared constant pressure."""
    run_dir, mesh_dir, output_dir = _case_directories(root, case_name)
    shutil.copy2(mesh_path, mesh_dir / mesh_path.name)
    shutil.copy2(MAXWELL_STEP / "pylithapp.cfg", run_dir / "pylithapp.cfg")
    shutil.copy2(MAXWELL_STEP / "generalized_maxwell.cfg", run_dir / "generalized_maxwell.cfg")
    shutil.copy2(ELASTIC_STEP / "bc_cavity.spatialdb", run_dir / "bc_cavity.spatialdb")
    shutil.copy2(ELASTIC_STEP / "bc_zero.spatialdb", run_dir / "bc_zero.spatialdb")
    config_path = run_dir / "generalized_maxwell.cfg"
    config = config_path.read_text(encoding="utf-8")
    config = config.replace(
        "../step06_maxwell_ellipsoid/bc_cavity.spatialdb", "bc_cavity.spatialdb"
    )
    config = config.replace(
        "../step06_maxwell_ellipsoid/bc_zero.spatialdb", "bc_zero.spatialdb"
    )
    config_path.write_text(config, encoding="utf-8")

    vertices, tetrahedra, _ = _read_gmsh_tetrahedral_mesh(mesh_path)
    temperature_c, expected_modulus_pa, database_path = _prepare_generalized_case(
        run_dir,
        mesh_path,
        vertices,
        tetrahedra,
        thermal_archive,
        temperature_dependent=temperature_dependent,
    )
    _run_pylith(run_dir, "generalized_maxwell.cfg", "pylith.log")

    material_path = output_dir / "genmaxwell-material.h5"
    database = _read_material_database(database_path)
    with h5py.File(material_path, "r") as material:
        times_s = np.asarray(material["time"], dtype=float).reshape(-1)
        stress = np.asarray(material["cell_fields/cauchy_stress"], dtype=float)
        strain = np.asarray(material["cell_fields/cauchy_strain"], dtype=float)
        viscous_strain = np.asarray(material["cell_fields/viscous_strain"], dtype=float)
        model_vertices = np.asarray(material["geometry/vertices"], dtype=float)
        cells = np.asarray(material["viz/topology/cells"], dtype=np.int64)
    pylith_centroids = model_vertices[cells].mean(axis=1)
    database_distances, database_rows = cKDTree(database[:, :3]).query(pylith_centroids)
    if (
        len(np.unique(database_rows)) != len(cells)
        or np.max(database_distances) > 1.0e-6
    ):
        raise RuntimeError("material database centroids do not match PyLith output cells")
    database = database[database_rows]
    expected_modulus_pa = expected_modulus_pa[database_rows]
    if len(cells) != len(database):
        raise RuntimeError("PyLith cells do not match the material database rows")
    if not np.isclose(times_s[-1], END_TIME_S, rtol=0.0, atol=1.0e-3):
        raise RuntimeError("generalized Maxwell history did not reach the shared end time")
    if stress.shape != (len(times_s), len(cells), 6) or strain.shape != stress.shape:
        raise RuntimeError("generalized Maxwell stress or strain shape is unexpected")
    if viscous_strain.shape != (len(times_s), len(cells), 18):
        raise RuntimeError("PyLith output must contain three six-component branch states")
    if not all(np.all(np.isfinite(field)) for field in (stress, strain, viscous_strain)):
        raise RuntimeError("generalized Maxwell output contains non-finite values")

    density = database[:, 3]
    shear_velocity_m_s = database[:, 4] * 1000.0
    modulus_from_wave_speeds_pa = 2.0 * (1.0 + POISSON_RATIO) * density * shear_velocity_m_s**2
    if not np.allclose(modulus_from_wave_speeds_pa, expected_modulus_pa, rtol=1.0e-10):
        raise RuntimeError("written PyLith wave speeds do not recover input modulus")
    viscosity_by_branch = database[:, 6:9].T
    fractions_by_branch = database[:, 9:12].T
    state_by_branch = viscous_strain.reshape(len(times_s), len(cells), 3, 6)
    reconstructed_stress = reconstruct_generalized_maxwell_stress_pa(
        strain,
        state_by_branch,
        modulus_from_wave_speeds_pa,
        POISSON_RATIO,
        fractions_by_branch.T,
    )
    stress_error = float(
        np.linalg.norm(reconstructed_stress - stress)
        / max(np.linalg.norm(stress), np.finfo(float).eps)
    )
    if stress_error > STRESS_RECONSTRUCTION_TOLERANCE:
        debug_dir = ROOT / "data" / "processed" / "rheology_case_matrix_failed_run"
        if debug_dir.exists():
            shutil.rmtree(debug_dir)
        debug_dir.mkdir(parents=True)
        shutil.copytree(run_dir, debug_dir / "case")
        shutil.copy2(mesh_path, debug_dir / "mesh.msh")
        shutil.copy2(thermal_archive, debug_dir / "temperature.npz")
        raise RuntimeError(
            "independent stress reconstruction error is "
            f"{stress_error:.3e}; debug files copied to {debug_dir}"
        )

    relaxation_times_s = generalized_maxwell_relaxation_times_s(
        modulus_from_wave_speeds_pa,
        POISSON_RATIO,
        viscosity_by_branch,
        fractions_by_branch,
    )
    maximum_step_s = float(np.max(np.diff(times_s)))
    minimum_relaxation_time_s = float(np.min(relaxation_times_s))
    if maximum_step_s > minimum_relaxation_time_s / 5.0:
        raise RuntimeError("PyLith output interval exceeds the one-fifth relaxation limit")

    failure = analyze_stress_history(
        model_vertices,
        cells,
        stress,
        times_s,
        cohesion_pa=COHESION_PA,
        friction_angle_deg=FRICTION_ANGLE_DEG,
        pore_pressure_pa=0.0,
    )
    maximum_cavity_tensile_stress_pa = max(
        record["maximum_cavity_tensile_stress_pa"] for record in failure["records"]
    )
    return {
        "case": thermal_description,
        "rheology": "three-branch generalized Maxwell with synthetic fractions and viscosities",
        "temperature_dependent_viscosity": temperature_dependent,
        "youngs_modulus_law": (
            "linear 50-to-20 GPa project interpolation"
            if temperature_dependent
            else "constant 50 GPa"
        ),
        "temperature_c_range": [float(np.min(temperature_c)), float(np.max(temperature_c))],
        "youngs_modulus_gpa_range": [
            float(np.min(modulus_from_wave_speeds_pa) / 1.0e9),
            float(np.max(modulus_from_wave_speeds_pa) / 1.0e9),
        ],
        "viscosity_pa_s_range": [
            float(np.min(viscosity_by_branch)),
            float(np.max(viscosity_by_branch)),
        ],
        "mesh_tetrahedra": len(cells),
        "output_records": len(times_s),
        "end_time_s": float(times_s[-1]),
        "maximum_output_step_s": maximum_step_s,
        "minimum_relaxation_time_s": minimum_relaxation_time_s,
        "stress_reconstruction_relative_l2_error": stress_error,
        "maximum_absolute_cauchy_stress_pa": float(np.max(np.abs(stress))),
        "first_cavity_to_surface_path_time_s": failure[
            "first_cavity_to_surface_shear_path_time_s"
        ],
        "maximum_cavity_tensile_stress_pa": maximum_cavity_tensile_stress_pa,
        "thermal_archive": thermal_archive.name,
    }


def run_matrix(summary_path: Path = SUMMARY_PATH) -> dict[str, object]:
    """Run elastic and three generalized Maxwell material cases."""
    if not (PYLITH_ROOT / "setup.sh").is_file():
        raise SystemExit("PyLith is not installed; run make install-pylith first")
    started = time.perf_counter()
    with TemporaryDirectory(prefix="axial-rheology-matrix-") as temporary:
        work_dir = Path(temporary)
        mesh_path = work_dir / "mesh" / "axial_ellipsoid.msh"
        mesh_count = _generate_mesh(mesh_path, work_dir / "mesh.log")
        baseline_temperature = work_dir / "temperature-baseline.npz"
        hydrothermal_temperature = work_dir / "temperature-hydrothermal.npz"
        baseline_metrics = solve_written_thermal_model(
            mesh_path, baseline_temperature, hydrothermal=False
        )
        hydrothermal_metrics = solve_written_thermal_model(
            mesh_path, hydrothermal_temperature, hydrothermal=True
        )
        vertices, tetrahedra, _ = _read_gmsh_tetrahedral_mesh(mesh_path)
        cases = [
            _run_elastic_case(work_dir / "cases", mesh_path),
            _run_generalized_case(
                work_dir / "cases",
                mesh_path,
                baseline_temperature,
                case_name="non_td_viscoelastic",
                thermal_description="non-temperature-dependent viscoelastic",
                temperature_dependent=False,
            ),
            _run_generalized_case(
                work_dir / "cases",
                mesh_path,
                baseline_temperature,
                case_name="td_viscoelastic",
                thermal_description="temperature-dependent viscoelastic",
                temperature_dependent=True,
            ),
            _run_generalized_case(
                work_dir / "cases",
                mesh_path,
                hydrothermal_temperature,
                case_name="td_hydrothermal_viscoelastic",
                thermal_description=(
                    "temperature-dependent hydrothermal viscoelastic"
                ),
                temperature_dependent=True,
            ),
        ]
        with np.load(baseline_temperature, allow_pickle=False) as baseline:
            baseline_temperature_c = np.asarray(baseline["temperature_c"], dtype=float)
            baseline_conductivity_w_mk = np.asarray(
                baseline["cell_conductivity_w_mk"], dtype=float
            )
        with np.load(hydrothermal_temperature, allow_pickle=False) as hydrothermal:
            hydrothermal_temperature_c = np.asarray(
                hydrothermal["temperature_c"], dtype=float
            )
            hydrothermal_conductivity_w_mk = np.asarray(
                hydrothermal["cell_conductivity_w_mk"], dtype=float
            )
        MODEL_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            MODEL_DATA_PATH,
            vertices_m=vertices,
            tetrahedra=tetrahedra,
            baseline_temperature_c=baseline_temperature_c,
            baseline_conductivity_w_mk=baseline_conductivity_w_mk,
            hydrothermal_temperature_c=hydrothermal_temperature_c,
            hydrothermal_conductivity_w_mk=hydrothermal_conductivity_w_mk,
        )
    summary: dict[str, object] = {
        "purpose": (
            "bounded solver integration check across the four written "
            "rheology configurations"
        ),
        "observation_data_used": False,
        "paper_publication_data_used": False,
        "common_cavity_pressure_pa": 1.0e6,
        "pressure_history": "constant 1 MPa load from the common initial time",
        "common_end_time_s": END_TIME_S,
        "common_time_step_s": TIME_STEP_S,
        "domain_dimensions_km": {"x": 50.0, "y": 50.0, "depth": 10.0},
        "mesh_tetrahedra": mesh_count,
        "boundary_condition": (
            "fixed base with lateral roller boundaries; "
            "Winkler response not represented"
        ),
        "shared_synthetic_maxwell_properties": {
            "reference_viscosity_pa_s_by_branch": REFERENCE_VISCOSITY_PA_S_BY_BRANCH.tolist(),
            "shear_modulus_ratio_by_branch": SHEAR_RATIO_BY_BRANCH.tolist(),
            "reference_temperature_c": REFERENCE_TEMPERATURE_C,
            "density_kg_m3": DENSITY_KG_M3,
            "poisson_ratio": POISSON_RATIO,
        },
        "thermal_solves": {
            "baseline_iterations": baseline_metrics[0],
            "baseline_relative_change": baseline_metrics[1],
            "baseline_temperature_c_range": [baseline_metrics[2], baseline_metrics[3]],
            "hydrothermal_iterations": hydrothermal_metrics[0],
            "hydrothermal_relative_change": hydrothermal_metrics[1],
            "hydrothermal_temperature_c_range": [hydrothermal_metrics[2], hydrothermal_metrics[3]],
            "boundary_assumption": (
                "0 C surface, 1200 C reservoir, 30 C/km on side and basal boundaries"
            ),
        },
        "youngs_modulus_mapping": {
            "law": (
                "linear decrease from 50 GPa at 0 C to 20 GPa at 1200 C; "
                "clipped to those endpoint values"
            ),
            "source": "project-owner model setup direction",
            "printed_eq16_used": False,
        },
        "figure3_model_data_path": str(MODEL_DATA_PATH.relative_to(ROOT)),
        "failure_proxy": {
            "cohesion_pa": COHESION_PA,
            "friction_angle_deg_used_directly_as_phi": FRICTION_ANGLE_DEG,
            "pore_pressure_pa": 0.0,
            "tensile_strength_assigned": False,
        },
        "cases": cases,
        "interpretation": (
            "The shared load isolates solver and property-map behavior. The modulus "
            "interpolation is a project assumption within the requested 20–50 GPa "
            "range; generalized Maxwell branches remain synthetic. These cases do "
            "not calibrate pressure or reproduce eruption thresholds."
        ),
        "runtime_seconds": round(time.perf_counter() - started, 2),
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    """Run and print the four-case solver matrix summary."""
    summary = run_matrix()
    print(json.dumps(summary, indent=2))
    print(f"wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
