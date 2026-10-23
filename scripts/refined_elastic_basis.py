"""Save a refined gravity-equilibrated fixed-base PyLith pressure basis."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import h5py
import numpy as np
import winkler_foundation_check as foundation

from axialstress.cavity_volume import (
    enclosed_volume_m3,
    orient_closed_cavity,
    read_gmsh_cavity_surface,
)
from axialstress.paper_bpr import file_sha256

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data/processed/refined_elastic_basis_400m"


def _read_material(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read final PyLith tetrahedral stress with finite-value validation."""
    with h5py.File(path, "r") as material:
        vertices = np.asarray(material["geometry/vertices"], dtype=float)
        cells = np.asarray(material["viz/topology/cells"], dtype=np.int64)
        stress = np.asarray(material["cell_fields/cauchy_stress"][-1], dtype=float)
    if stress.shape != (len(cells), 6) or not np.all(np.isfinite(stress)):
        raise ValueError(f"invalid PyLith material field: {path}")
    return vertices, cells, stress


def main() -> None:
    """Run three bounded PyLith solves and preserve their refined basis fields."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lc-near-m", type=float, default=400.0)
    parser.add_argument("--max-tetrahedra", type=int, default=20_000)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if not np.isfinite(args.lc_near_m) or args.lc_near_m <= 0.0:
        raise ValueError("near-cavity mesh size must be finite and positive")
    if args.max_tetrahedra < 1:
        raise ValueError("tetrahedron limit must be positive")
    if args.output_dir.exists() and any(args.output_dir.iterdir()) and not args.overwrite:
        raise FileExistsError(f"output directory is not empty: {args.output_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    mesh_path = foundation.STEP_DIR / "mesh/axial_ellipsoid.msh"
    mesh_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "timeout",
        "300",
        sys.executable,
        str(ROOT / "meshing/axial_ellipsoid_bpr.py"),
        "--output",
        str(mesh_path),
        "--lc-near",
        str(args.lc_near_m),
        "--max-tetrahedra",
        str(args.max_tetrahedra),
        "--mark-base-anchor",
    ]
    mesh_log = args.output_dir / "mesh.log"
    with mesh_log.open("w", encoding="utf-8") as stream:
        result = subprocess.run(
            command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=False
        )
    if result.returncode:
        raise RuntimeError(
            "refined Gmsh generation failed:\n"
            + "\n".join(mesh_log.read_text(encoding="utf-8", errors="replace").splitlines()[-30:])
        )

    bottom, _, base_area_m2, anchor = foundation._read_bottom_mesh(mesh_path)
    equilibrium = foundation._prepare_lithostatic_equilibrium(8, bottom, anchor)
    foundation._write_cavity_pressure_database(
        foundation.OUTPUT_DIR / "cavity-pressure.spatialdb", 1.0
    )
    foundation._run_pylith(8, "fixed_base.cfg")
    foundation._validate_stress(foundation.OUTPUT_DIR / "fixed-base-material.h5")

    copied = {}
    for name in (
        "fixed-base-equilibrium-material.h5",
        "fixed-base-material.h5",
        "fixed-base-surface.h5",
    ):
        destination = args.output_dir / name
        shutil.copy2(foundation.OUTPUT_DIR / name, destination)
        copied[name] = file_sha256(destination)
    mesh_copy = args.output_dir / "axial_ellipsoid.msh"
    shutil.copy2(mesh_path, mesh_copy)
    vertices, cells, reference_stress = _read_material(
        args.output_dir / "fixed-base-equilibrium-material.h5"
    )
    loaded_vertices, loaded_cells, loaded_stress = _read_material(
        args.output_dir / "fixed-base-material.h5"
    )
    if not np.array_equal(vertices, loaded_vertices) or not np.array_equal(cells, loaded_cells):
        raise ValueError("refined equilibrium and pressure meshes do not match")
    if np.max(np.abs(loaded_stress - reference_stress)) <= 0.0:
        raise ValueError("one-megapascal load did not change the PyLith stress")

    cavity_vertices, cavity_faces = read_gmsh_cavity_surface(mesh_copy)
    cavity_volume_m3 = enclosed_volume_m3(
        cavity_vertices, orient_closed_cavity(cavity_vertices, cavity_faces)
    )
    ideal_volume_m3 = np.pi * 6_000.0 * 3_000.0 * 1_000.0 / 6.0
    summary = {
        "method": "refined fixed-base gravity and one-megapascal PyLith basis",
        "converged": True,
        "convergence_scope": "individual gravity and pressure solves; not mesh convergence",
        "mechanical_mesh_convergence_established": False,
        "mesh_tetrahedra": len(cells),
        "mesh_sha256": file_sha256(mesh_copy),
        "mesh_lc_near_m": args.lc_near_m,
        "mesh_max_tetrahedra": args.max_tetrahedra,
        "cavity_faces": len(cavity_faces),
        "cavity_volume_m3": cavity_volume_m3,
        "ideal_ellipsoid_volume_m3": ideal_volume_m3,
        "relative_cavity_volume_difference": (cavity_volume_m3 - ideal_volume_m3) / ideal_volume_m3,
        "base_area_m2": base_area_m2,
        "cavity_overpressure_mpa": 1.0,
        "tectonic_loading": {"per_face_velocity_mm_per_year": 0.0},
        "equilibrium_density_kg_m3": foundation.EFFECTIVE_COLUMN_DENSITY_KG_M3,
        "youngs_modulus_pa": 50.0e9,
        "poisson_ratio": 0.25,
        "lithostatic_equilibrium_diagnostics": equilibrium,
        "output_sha256": copied,
        "paper_output_data_used": False,
        "limitations": [
            "The fixed base approximates the paper's very stiff Eq. 23 spring.",
            "The density profile is a regional prior, and the elastic material is uniform.",
            "A second refined level is needed to assess failure-path convergence.",
        ],
    }
    (args.output_dir / "basis_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "mesh_tetrahedra": summary["mesh_tetrahedra"],
                "relative_cavity_volume_difference": summary["relative_cavity_volume_difference"],
                "equilibrium": equilibrium,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
