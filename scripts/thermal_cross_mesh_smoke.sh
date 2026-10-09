#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STEP_DIR="${ROOT}/pylith/step01_maxwell_restart"
OUTPUT_DIR="${STEP_DIR}/output"
MESH_PATH="${STEP_DIR}/mesh/axial_box.msh"
THERMAL_MESH_PATH="${OUTPUT_DIR}/axial_thermal.msh"
PYLITH_ROOT="${ROOT}/pylith/pylith-5.0.2-linux-x86_64"
PYTHON="${ROOT}/envs/axial-modeling/bin/python"

mkdir -p "${OUTPUT_DIR}"
python "${ROOT}/meshing/axial_box_ellipsoid.py" --output "${MESH_PATH}"
python "${ROOT}/meshing/axial_box_ellipsoid.py" \
    --output "${THERMAL_MESH_PATH}" --lc-far 16000 --lc-near 1100

"${PYTHON}" - "${STEP_DIR}" "${MESH_PATH}" "${THERMAL_MESH_PATH}" <<'PY'
from pathlib import Path
import sys

import gmsh
import numpy as np

from axialstress.material_database import write_maxwell_database_from_thermal_archive
from axialstress.thermal_fem import solve_steady_temperature_tetrahedral
from axialstress.thermal_model import solve_written_thermal_model
from axialstress.tetrahedral_interpolation import interpolate_tetrahedral_field

step_dir = Path(sys.argv[1])
mesh_path = Path(sys.argv[2])
thermal_mesh_path = Path(sys.argv[3])
output = step_dir / "output"
def read_mesh(path: Path) -> tuple[np.ndarray, np.ndarray]:
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.open(str(path))
        node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
        vertices = np.asarray(coordinates, dtype=float).reshape(-1, 3)
        indices = {int(tag): index for index, tag in enumerate(node_tags)}
        element_types, _, element_nodes = gmsh.model.mesh.getElements(3)
        cells = []
        for element_type, node_tags_for_type in zip(
            element_types, element_nodes, strict=True
        ):
            _, dimension, order, node_count, _, _ = gmsh.model.mesh.getElementProperties(
                int(element_type)
            )
            if dimension == 3:
                if order != 1 or node_count != 4:
                    raise ValueError("mesh requires first-order tetrahedra")
                cells.extend(
                    [indices[int(tag)] for tag in cell]
                    for cell in node_tags_for_type.reshape(-1, 4)
                )
    finally:
        gmsh.finalize()
    return vertices, np.asarray(cells, dtype=np.int64)


mechanics_vertices, mechanics_cells = read_mesh(mesh_path)
source_mesh_vertices, source_mesh_cells = read_mesh(thermal_mesh_path)
if not len(mechanics_cells) or not len(source_mesh_cells):
    raise ValueError("both meshes must contain tetrahedra")
if max(len(mechanics_cells), len(source_mesh_cells)) > 3500:
    raise ValueError("cross-mesh smoke meshes must stay below 3,500 tetrahedra")
if np.array_equal(mechanics_vertices, source_mesh_vertices) and np.array_equal(
    mechanics_cells, source_mesh_cells
):
    raise ValueError("thermal and mechanics meshes must be distinct")

# A six-tetrahedron box supplies an affine manufactured field on a deliberately
# different mesh. This checks transfer mechanics, not Axial thermal physics.
thermal_vertices = np.array(
    [
        [-25_000.0, -25_000.0, -20_000.0],
        [25_000.0, -25_000.0, -20_000.0],
        [-25_000.0, 25_000.0, -20_000.0],
        [25_000.0, 25_000.0, -20_000.0],
        [-25_000.0, -25_000.0, 0.0],
        [25_000.0, -25_000.0, 0.0],
        [-25_000.0, 25_000.0, 0.0],
        [25_000.0, 25_000.0, 0.0],
    ]
)
thermal_cells = np.array(
    [
        [0, 1, 3, 7],
        [0, 1, 5, 7],
        [0, 4, 5, 7],
        [0, 4, 6, 7],
        [0, 2, 6, 7],
        [0, 2, 3, 7],
    ],
    dtype=np.int64,
)
analytic_temperature_c = (
    250.0
    + 0.002 * thermal_vertices[:, 0]
    + 0.001 * thermal_vertices[:, 1]
    - 0.003 * thermal_vertices[:, 2]
)
thermal_solution = solve_steady_temperature_tetrahedral(
    thermal_vertices,
    thermal_cells,
    -thermal_vertices[:, 2],
    dict(enumerate(analytic_temperature_c)),
    conductivity=lambda temperature, depth: 3.0,
)
if not np.array_equal(thermal_solution.temperature_c, analytic_temperature_c):
    raise SystemExit("thermal source mesh did not retain the manufactured field")

manufactured_archive = output / "cross-mesh-manufactured-thermal.npz"
np.savez_compressed(
    manufactured_archive,
    vertices_m=thermal_vertices,
    tetrahedra=thermal_cells,
    temperature_c=thermal_solution.temperature_c,
)
mechanics_centroids = mechanics_vertices[mechanics_cells].mean(axis=1)
mapped_temperature = interpolate_tetrahedral_field(
    thermal_vertices,
    thermal_cells,
    thermal_solution.temperature_c,
    mechanics_centroids,
)
expected_temperature = (
    250.0
    + 0.002 * mechanics_centroids[:, 0]
    + 0.001 * mechanics_centroids[:, 1]
    - 0.003 * mechanics_centroids[:, 2]
)
temperature_error_c = float(np.max(np.abs(mapped_temperature - expected_temperature)))
if temperature_error_c > 1.0e-9:
    raise SystemExit(f"cross-mesh affine-field error {temperature_error_c:.3e} °C")

cell_depth_m = -mechanics_centroids[:, 2]
youngs_modulus_pa = 35.0e9 * (1.0 + 0.1 * cell_depth_m / 20_000.0)
thermal_archive = output / "cross-mesh-physical-thermal.npz"
thermal_statistics = solve_written_thermal_model(
    thermal_mesh_path, thermal_archive, hydrothermal=True
)
with np.load(thermal_archive, allow_pickle=False) as archive:
    physical_temperature = np.asarray(archive["temperature_c"], dtype=float)
    source_tetrahedra = np.asarray(archive["tetrahedra"], dtype=np.int64)
physical_cell_temperature = interpolate_tetrahedral_field(
    source_mesh_vertices,
    source_tetrahedra,
    physical_temperature,
    mechanics_centroids,
)
if not np.all(np.isfinite(physical_cell_temperature)):
    raise SystemExit("physical temperature transfer contains non-finite values")
material_path = write_maxwell_database_from_thermal_archive(
    thermal_archive,
    output / "cross-mesh-material.spatialdb",
    youngs_modulus_pa,
    density_kg_m3=2700.0,
    poisson_ratio=0.25,
    mechanics_vertices_m=mechanics_vertices,
    mechanics_tetrahedra=mechanics_cells,
)
if not material_path.is_file():
    raise SystemExit("cross-mesh Maxwell material database was not written")

config = (step_dir / "step01_single.cfg").read_text(encoding="utf-8")
config = config.replace(
    "db_auxiliary_field.iohandler.filename = material_initial.spatialdb",
    "db_auxiliary_field.query_type = nearest\n"
    "db_auxiliary_field.iohandler.filename = output/cross-mesh-material.spatialdb",
)
config = config.replace("output/single-material.h5", "output/cross-mesh-material.h5")
config = config.replace("output/single-domain.h5", "output/cross-mesh-domain.h5")
config = config.replace("output/single-surface.h5", "output/cross-mesh-surface.h5")
(output / "cross-mesh-material.cfg").write_text(config, encoding="utf-8")
print(
    f"Manufactured-field error = {temperature_error_c:.3e} °C. Solved the "
    f"hydrothermal field on {len(source_tetrahedra)} source tetrahedra in "
    f"{thermal_statistics[0]} Picard iterations, then mapped it to "
    f"{len(mechanics_cells)} mechanics tetrahedra; target temperatures span "
    f"{physical_cell_temperature.min():.3f}–{physical_cell_temperature.max():.3f} °C."
)
PY

cd "${PYLITH_ROOT}"
source setup.sh
cd "${STEP_DIR}"
if ! timeout 300 pylith --nodes=8 output/cross-mesh-material.cfg >"${OUTPUT_DIR}/cross-mesh-material.log" 2>&1; then
    tail -n 50 "${OUTPUT_DIR}/cross-mesh-material.log"
    exit 1
fi

"${PYTHON}" - "${OUTPUT_DIR}" <<'PY'
from pathlib import Path
import sys

import h5py
import numpy as np

output = Path(sys.argv[1])
material_path = output / "cross-mesh-material.h5"
with h5py.File(material_path, "r") as material:
    stress = np.asarray(material["cell_fields/cauchy_stress"][-1], dtype=float)
    viscous_strain = np.asarray(material["cell_fields/viscous_strain"][-1], dtype=float)
    final_time = float(np.asarray(material["time"]).reshape(-1)[-1])

if not np.isclose(final_time, 2.0, rtol=0.0, atol=1.0e-12):
    raise SystemExit(f"PyLith ended at {final_time:g} s, expected 2 s")
if not np.all(np.isfinite(stress)) or not np.all(np.isfinite(viscous_strain)):
    raise SystemExit("PyLith wrote non-finite fields from the mapped database")
if np.max(np.abs(stress)) <= 0.0:
    raise SystemExit("PyLith material response is zero")

print(
    "Cross-mesh thermal-to-Maxwell smoke test passed at t = 2 s; "
    f"peak stress = {np.max(np.abs(stress)):.6g} Pa."
)
PY
