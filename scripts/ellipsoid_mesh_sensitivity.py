"""Measure mesh sensitivity of the PyLith ellipsoid BPR compliance response."""

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

import gmsh
import numpy as np

from axialstress.bpr_mogi_calibration import (
    CENTRAL_CALDERA_LAT_LON_DEG,
    EAST_CALDERA_LAT_LON_DEG,
    local_east_north_offset_m,
)
from axialstress.ellipsoid_bpr_calibration import read_ellipsoid_unit_response

ROOT = Path(__file__).resolve().parents[1]
STEP_DIR = ROOT / "pylith" / "step05_ellipsoid_elastic"
PYLITH_ROOT = ROOT / "pylith" / "pylith-5.0.2-linux-x86_64"
OUTPUT_PATH = ROOT / "data" / "processed" / "ellipsoid_mesh_sensitivity.json"
MESH_VARIANTS = (
    ("coarse", 1_200.0, 10_000.0, None, None),
    ("stations-800", 1_200.0, 10_000.0, None, 800.0),
    ("stations-600", 1_200.0, 10_000.0, None, 600.0),
    ("stations-400", 1_200.0, 10_000.0, None, 400.0),
    ("stations-300", 1_200.0, 10_000.0, None, 300.0),
    ("stations-200", 1_200.0, 10_000.0, None, 200.0),
    ("stations-150", 1_200.0, 10_000.0, None, 150.0),
    ("stations-100", 1_200.0, 10_000.0, None, 100.0),
    ("stations-50", 1_200.0, 10_000.0, None, 50.0),
    ("stations-25", 1_200.0, 10_000.0, None, 25.0),
)
MAX_TETRAHEDRA = 3_500
COMPLIANCE_RELATIVE_TOLERANCE = 0.05


def _tail(path: Path, lines: int = 20) -> str:
    """Return the last lines of a solver log for actionable failures."""
    return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])


def _nearest_station_surface_vertex_distances(mesh_path: Path) -> tuple[float, float]:
    """Measure the nearest top-surface vertex to each BPR sample location."""
    gmsh.initialize()
    try:
        gmsh.open(str(mesh_path))
        top_faces: list[int] = []
        for dimension, physical_tag in gmsh.model.getPhysicalGroups(2):
            if gmsh.model.getPhysicalName(dimension, physical_tag) == "top":
                top_faces.extend(
                    int(tag)
                    for tag in gmsh.model.getEntitiesForPhysicalGroup(
                        dimension, physical_tag
                    )
                )
        if not top_faces:
            raise ValueError(f"mesh has no top physical group: {mesh_path}")
        node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
        coordinates = np.asarray(coordinates, dtype=float).reshape(-1, 3)
        coordinate_by_tag = {
            int(tag): coordinates[index]
            for index, tag in enumerate(node_tags)
        }
        top_node_tags: set[int] = set()
        for face in top_faces:
            _, _, element_nodes = gmsh.model.mesh.getElements(2, face)
            for nodes in element_nodes:
                top_node_tags.update(int(tag) for tag in nodes)
        if not top_node_tags:
            raise ValueError(f"top physical group has no mesh nodes: {mesh_path}")
        top_coordinates = np.asarray(
            [coordinate_by_tag[tag] for tag in sorted(top_node_tags)],
            dtype=float,
        )
    finally:
        gmsh.finalize()

    station_coordinates = (
        CENTRAL_CALDERA_LAT_LON_DEG,
        EAST_CALDERA_LAT_LON_DEG,
    )
    distances: list[float] = []
    for latitude_deg, longitude_deg in station_coordinates:
        east_m, north_m = local_east_north_offset_m(
            latitude_deg,
            longitude_deg,
            origin_latitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[0],
            origin_longitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[1],
        )
        horizontal_distance_m = np.linalg.norm(
            top_coordinates[:, :2] - (east_m, north_m), axis=1
        )
        distances.append(float(np.min(horizontal_distance_m)))
    return distances[0], distances[1]


def _run_mesh_variant(
    name: str,
    lc_near: float,
    lc_far: float,
    local_refinement_size: float | None,
    station_refinement_size: float | None,
    domain_depth_m: float = 20_000.0,
    embed_station_points: bool = False,
) -> dict[str, float | int | str | bool | None]:
    """Build and solve one mesh in a temporary directory."""
    with TemporaryDirectory(prefix=f"axial-ellipsoid-{name}-") as temporary:
        run_dir = Path(temporary)
        (run_dir / "mesh").mkdir()
        (run_dir / "output").mkdir()
        for filename in (
            "step05.cfg",
            "pylithapp.cfg",
            "bc_cavity.spatialdb",
            "bc_zero.spatialdb",
            "mat_elastic.spatialdb",
        ):
            shutil.copy2(STEP_DIR / filename, run_dir / filename)

        mesh_log = run_dir / "output" / "mesh.log"
        mesh_command = [
            sys.executable,
            str(ROOT / "meshing" / "axial_ellipsoid_bpr.py"),
            "--output",
            str(run_dir / "mesh" / "axial_ellipsoid.msh"),
            "--lc-near",
            str(lc_near),
            "--lc-far",
            str(lc_far),
            "--max-tetrahedra",
            str(MAX_TETRAHEDRA),
            "--domain-depth-m",
            str(domain_depth_m),
        ]
        if local_refinement_size is not None:
            mesh_command.extend(
                ["--local-refinement-size", str(local_refinement_size)]
            )
        if station_refinement_size is not None:
            mesh_command.extend(
                ["--station-refinement-size", str(station_refinement_size)]
            )
        if embed_station_points:
            mesh_command.append("--embed-station-points")
        with mesh_log.open("w", encoding="utf-8") as log:
            subprocess.run(
                mesh_command,
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
            )
        mesh_output = mesh_log.read_text(encoding="utf-8")
        match = re.search(r"Wrote .*: (\d+) tetrahedra", mesh_output)
        if match is None:
            raise RuntimeError(f"mesh count missing from {mesh_log}")
        tetrahedra = int(match.group(1))
        center_vertex_distance_m, east_vertex_distance_m = (
            _nearest_station_surface_vertex_distances(
                run_dir / "mesh" / "axial_ellipsoid.msh"
            )
        )
        if embed_station_points and max(
            center_vertex_distance_m, east_vertex_distance_m
        ) > 1.0e-6:
            raise ValueError("embedded BPR station locations are absent from the top mesh")

        solver_log = run_dir / "output" / "pylith.log"
        solver_command = (
            f"cd {shlex.quote(str(PYLITH_ROOT))} && source setup.sh && "
            f"cd {shlex.quote(str(run_dir))} && "
            "timeout 300 pylith --nodes=8 step05.cfg"
        )
        with solver_log.open("w", encoding="utf-8") as log:
            completed = subprocess.run(
                ["bash", "-lc", solver_command],
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
        if completed.returncode:
            raise RuntimeError(f"PyLith {name} solve failed:\n{_tail(solver_log)}")

        central, east = read_ellipsoid_unit_response(
            run_dir / "output" / "ellipsoid-surface.h5"
        )
        return {
            "name": name,
            "domain_depth_m": domain_depth_m,
            "embed_station_points": embed_station_points,
            "refinement_mode": (
                "station-box"
                if station_refinement_size
                else "local-box" if local_refinement_size else "global"
            ),
            "lc_near_m": lc_near,
            "lc_far_m": lc_far,
            "local_refinement_size_m": local_refinement_size,
            "station_refinement_size_m": station_refinement_size,
            "tetrahedra": tetrahedra,
            "central_nearest_surface_vertex_distance_m": center_vertex_distance_m,
            "east_nearest_surface_vertex_distance_m": east_vertex_distance_m,
            "central_compliance_m_per_mpa": float(central[2]),
            "east_compliance_m_per_mpa": float(east[2]),
        }


def main() -> None:
    """Run the bounded station-region mesh check and write JSON."""
    if not (PYLITH_ROOT / "setup.sh").is_file():
        raise SystemExit("PyLith is not installed; run make install-pylith first")
    started = time.perf_counter()
    results = [
        _run_mesh_variant(name, lc_near, lc_far, local_size, station_size)
        for name, lc_near, lc_far, local_size, station_size in MESH_VARIANTS
    ]
    result_by_name = {str(result["name"]): result for result in results}
    comparison_groups = {
        "surface_station_refinement": [
            result_by_name[name]
            for name in (
                "coarse",
                "stations-800",
                "stations-600",
                "stations-400",
                "stations-300",
                "stations-200",
                "stations-150",
                "stations-100",
                "stations-50",
                "stations-25",
            )
        ]
    }
    changes = []
    for group in comparison_groups.values():
        for previous, current in zip(group, group[1:], strict=False):
            for field in (
                "central_compliance_m_per_mpa",
                "east_compliance_m_per_mpa",
            ):
                change = float(current[field]) / float(previous[field]) - 1.0
                current[f"{field}_relative_change"] = change
                changes.append(abs(change))
    summary = {
        "method": "static elastic unit-pressure compliance mesh sensitivity",
        "compliance_relative_tolerance": COMPLIANCE_RELATIVE_TOLERANCE,
        "mesh_convergence_status": (
            "within_tolerance"
            if all(change <= COMPLIANCE_RELATIVE_TOLERANCE for change in changes)
            else "not_established"
        ),
        "comparison_groups": {
            name: [result["name"] for result in group]
            for name, group in comparison_groups.items()
        },
        "runtime_seconds": round(time.perf_counter() - started, 2),
        "variants": results,
        "observations_used": False,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
