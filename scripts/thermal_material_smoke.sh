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
finally:
    gmsh.finalize()

cells = np.asarray(tetrahedra, dtype=np.int64)
depth_m = float(np.max(vertices[:, 2])) - vertices[:, 2]
temperature_c = 150.0 + 0.01 * depth_m
cell_depth_m = depth_m[cells].mean(axis=1)
youngs_modulus_pa = 35.0e9 * (1.0 + 0.1 * cell_depth_m / max(depth_m))
write_temperature_dependent_maxwell_database(
    output / "thermal_material.spatialdb",
    vertices,
    cells,
    temperature_c,
    youngs_modulus_pa,
    density_kg_m3=2800.0,
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
    "Wrote synthetic thermal material database for "
    f"{len(cells)} tetrahedra; T = {temperature_c.min():.1f}–"
    f"{temperature_c.max():.1f} °C."
)
PY

cd "${PYLITH_ROOT}"
source setup.sh
cd "${STEP_DIR}"
if ! timeout 300 pylith output/thermal_material.cfg >"${OUTPUT_DIR}/thermal_material.log" 2>&1; then
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
