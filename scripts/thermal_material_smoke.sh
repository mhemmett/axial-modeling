#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STEP_DIR="${ROOT}/pylith/step01_maxwell_restart"
OUTPUT_DIR="${STEP_DIR}/output"
MESH_PATH="${STEP_DIR}/mesh/axial_box.msh"
PYLITH_ROOT="${ROOT}/pylith/pylith-5.0.2-linux-x86_64"
PYTHON="${ROOT}/envs/axial-modeling/bin/python"

mkdir -p "${OUTPUT_DIR}"
python "${ROOT}/meshing/axial_box_ellipsoid.py" --output "${MESH_PATH}"

"${PYTHON}" - "${STEP_DIR}" "${MESH_PATH}" <<'PY'
from pathlib import Path
import sys

import gmsh
import numpy as np

from axialstress.material_database import write_temperature_dependent_maxwell_database
from axialstress.thermal_fem import solve_steady_temperature_tetrahedral

step_dir = Path(sys.argv[1])
mesh_path = Path(sys.argv[2])
output = step_dir / "output"
gmsh.initialize()
try:
    gmsh.open(str(mesh_path))
    node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
    vertices = coordinates.reshape(-1, 3)
    indices = {int(tag): index for index, tag in enumerate(node_tags)}
    element_types, _, element_nodes = gmsh.model.mesh.getElements(3)
    tetrahedra = []
    for element_type, node_tags_for_type in zip(
        element_types, element_nodes, strict=True
    ):
        _, dimension, order, node_count, _, _ = gmsh.model.mesh.getElementProperties(
            int(element_type)
        )
        if dimension == 3 and order == 1 and node_count == 4:
            tagged_cells = node_tags_for_type.reshape(-1, 4)
            tetrahedra.extend(
                [[indices[int(tag)] for tag in cell] for cell in tagged_cells]
            )
    boundary_node_tags = set()
    for dimension, physical_tag in gmsh.model.getPhysicalGroups(2):
        if dimension != 2:
            continue
        for entity_tag in gmsh.model.getEntitiesForPhysicalGroup(dimension, physical_tag):
            surface_tags, _, _ = gmsh.model.mesh.getNodes(
                dimension, int(entity_tag), includeBoundary=True
            )
            boundary_node_tags.update(int(tag) for tag in surface_tags)
finally:
    gmsh.finalize()

cells = np.asarray(tetrahedra, dtype=np.int64)
depth_m = float(np.max(vertices[:, 2])) - vertices[:, 2]
analytic_temperature_c = 250.0 + 0.002 * vertices[:, 0] + 0.001 * vertices[:, 1]
analytic_temperature_c -= 0.003 * vertices[:, 2]
boundary_indices = {indices[tag] for tag in boundary_node_tags}
boundary_temperature_c = {
    index: float(analytic_temperature_c[index]) for index in boundary_indices
}
thermal_solution = solve_steady_temperature_tetrahedral(
    vertices,
    cells,
    depth_m,
    boundary_temperature_c,
    conductivity=lambda temperature, depth: 3.0,
)
temperature_c = thermal_solution.temperature_c
temperature_error_c = float(np.max(np.abs(temperature_c - analytic_temperature_c)))
if temperature_error_c > 1.0e-5:
    raise SystemExit(f"manufactured thermal field error {temperature_error_c:.3e} °C")
cell_depth_m = depth_m[cells].mean(axis=1)
youngs_modulus_pa = 35.0e9 * (1.0 + 0.1 * cell_depth_m / max(depth_m))
write_temperature_dependent_maxwell_database(
    output / "thermal_material.spatialdb",
    vertices,
    cells,
    temperature_c,
    youngs_modulus_pa,
    density_kg_m3=2700.0,
    poisson_ratio=0.25,
)

config = (step_dir / "step01_single.cfg").read_text(encoding="utf-8")
config = config.replace(
    "db_auxiliary_field.iohandler.filename = material_initial.spatialdb",
    "db_auxiliary_field.query_type = nearest\n"
    "db_auxiliary_field.iohandler.filename = output/thermal_material.spatialdb",
)
config = config.replace(
    "output/single-material.h5", "output/thermal-material-material.h5"
)
config = config.replace("output/single-domain.h5", "output/thermal-material-domain.h5")
config = config.replace("output/single-surface.h5", "output/thermal-material-surface.h5")
(output / "thermal_material.cfg").write_text(config, encoding="utf-8")
print(
    "Solved a manufactured thermal field on "
    f"{len(cells)} tetrahedra in {thermal_solution.iterations} iteration(s); "
    f"maximum temperature error = {temperature_error_c:.3e} °C."
)
PY

cd "${PYLITH_ROOT}"
source setup.sh
cd "${STEP_DIR}"
if ! timeout 300 pylith --nodes=8 output/thermal_material.cfg >"${OUTPUT_DIR}/thermal_material.log" 2>&1; then
    tail -n 50 "${OUTPUT_DIR}/thermal_material.log"
    exit 1
fi

"${PYTHON}" - "${OUTPUT_DIR}" <<'PY'
from pathlib import Path
import sys

import h5py
import numpy as np

output = Path(sys.argv[1])
material_path = output / "thermal-material-material.h5"
with h5py.File(material_path, "r") as material:
    stress = np.asarray(material["cell_fields/cauchy_stress"][-1], dtype=float)
    viscous_strain = np.asarray(material["cell_fields/viscous_strain"][-1], dtype=float)
    final_time = float(np.asarray(material["time"]).reshape(-1)[-1])

if not np.isclose(final_time, 2.0, rtol=0.0, atol=1.0e-12):
    raise SystemExit(f"PyLith ended at {final_time:g} s, expected 2 s")
if not np.all(np.isfinite(stress)) or not np.all(np.isfinite(viscous_strain)):
    raise SystemExit("PyLith wrote non-finite material fields")
if np.max(np.abs(stress)) <= 0.0:
    raise SystemExit("PyLith material response is zero")

print(
    "Thermal material database smoke test passed at t = 2 s; "
    f"peak stress = {np.max(np.abs(stress)):.6g} Pa."
)
PY
