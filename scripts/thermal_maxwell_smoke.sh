#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
THERMAL_DIR="${ROOT}/pylith/step03_steady_thermal"
STEP_DIR="${ROOT}/pylith/step01_maxwell_restart"
OUTPUT_DIR="${ROOT}/pylith/step04_thermal_maxwell/output"
PYLITH_ROOT="${ROOT}/pylith/pylith-5.0.2-linux-x86_64"
PYTHON="${ROOT}/envs/axial-modeling/bin/python"
THERMAL_ARCHIVE="${THERMAL_DIR}/output/steady_thermal_hydrothermal.npz"
MATERIAL_DB="${OUTPUT_DIR}/hydrothermal_material.spatialdb"
MATERIAL_H5="${OUTPUT_DIR}/hydrothermal-material.h5"
DOMAIN_H5="${OUTPUT_DIR}/hydrothermal-domain.h5"
SURFACE_H5="${OUTPUT_DIR}/hydrothermal-surface.h5"
CONFIG="${STEP_DIR}/thermal_maxwell_generated.cfg"

mkdir -p "${OUTPUT_DIR}"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON}" -m axialstress.material_database \
    --thermal-archive "${THERMAL_ARCHIVE}" \
    --output "${MATERIAL_DB}" \
    --youngs-modulus-pa 35000000000 \
    --density-kg-m3 2800 \
    --poisson-ratio 0.25 \
    --dorn-parameter-pa-s 1000000000 \
    --activation-energy-j-mol 120000 \
    --gas-constant-j-mol-k 8.3114

"${PYTHON}" - "${STEP_DIR}" "${CONFIG}" "${MATERIAL_DB}" "${MATERIAL_H5}" "${DOMAIN_H5}" "${SURFACE_H5}" <<'PY'
from pathlib import Path
import sys

step_dir, config_path, material_db, material_h5, domain_h5, surface_h5 = map(
    Path, sys.argv[1:]
)
config = (step_dir / "step01_single.cfg").read_text(encoding="utf-8")
overrides = f"""

[pylithapp.problem.mesh_initializer.phases.read_mesh]
reader.filename = ../step03_steady_thermal/mesh/axial_box.msh

[pylithapp.problem.materials.elastic]
db_auxiliary_field.query_type = nearest
db_auxiliary_field.iohandler.filename = ../step04_thermal_maxwell/output/{material_db.name}
observers.observer.writer.filename = ../step04_thermal_maxwell/output/{material_h5.name}

[pylithapp.problem.solution_observers.domain]
writer.filename = ../step04_thermal_maxwell/output/{domain_h5.name}

[pylithapp.problem.solution_observers.ground_surface]
writer.filename = ../step04_thermal_maxwell/output/{surface_h5.name}
"""
config_path.write_text(config + overrides, encoding="utf-8")
PY

LOG="${OUTPUT_DIR}/thermal_maxwell.log"
(
    cd "${PYLITH_ROOT}"
    source setup.sh
    cd "${STEP_DIR}"
    if ! timeout 300 pylith "${CONFIG}" >"${LOG}" 2>&1; then
        tail -n 50 "${LOG}"
        exit 1
    fi
)

PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}" \
    "${PYTHON}" - "${THERMAL_ARCHIVE}" "${MATERIAL_DB}" "${MATERIAL_H5}" <<'PY'
from pathlib import Path
import sys

import h5py
import numpy as np

from axialstress.thermal import temperature_dependent_viscosity_pa_s

thermal_path, database_path, material_path = map(Path, sys.argv[1:])
with np.load(thermal_path, allow_pickle=False) as thermal:
    vertices = np.asarray(thermal["vertices_m"], dtype=float)
    temperature = np.asarray(thermal["temperature_c"], dtype=float)
    cells = np.asarray(thermal["tetrahedra"], dtype=np.int64)
    cell_temperature = temperature[cells].mean(axis=1)
thermal_centroids = vertices[cells].mean(axis=1)
database = np.atleast_2d(np.loadtxt(database_path, comments="#", skiprows=13))
expected_viscosity = temperature_dependent_viscosity_pa_s(cell_temperature)
if database.shape != (len(cells), 19):
    raise SystemExit(
        f"material database has shape {database.shape}, expected {(len(cells), 19)}"
    )
if not np.allclose(database[:, 6], expected_viscosity, rtol=1.0e-12, atol=0.0):
    raise SystemExit("material database viscosities do not match the thermal field")
if np.max(database[:, 6]) / np.min(database[:, 6]) < 1.0e6:
    raise SystemExit("material database does not preserve thermal viscosity contrast")
with h5py.File(material_path, "r") as material:
    final_time = float(np.asarray(material["time"]).reshape(-1)[-1])
    pylith_vertices = np.asarray(material["geometry/vertices"], dtype=float)
    pylith_cells = np.asarray(material["viz/topology/cells"], dtype=np.int64)
    stress = np.asarray(material["cell_fields/cauchy_stress"][-1], dtype=float)
    viscous_strain = np.asarray(material["cell_fields/viscous_strain"][-1], dtype=float)
if pylith_vertices.shape != vertices.shape or pylith_cells.shape != cells.shape:
    raise SystemExit("PyLith changed the number of mesh vertices or cells")

def sort_rows(rows: np.ndarray) -> np.ndarray:
    return rows[np.lexsort((rows[:, 2], rows[:, 1], rows[:, 0]))]

pylith_centroids = pylith_vertices[pylith_cells].mean(axis=1)
if not np.allclose(sort_rows(pylith_vertices), sort_rows(vertices), rtol=0.0, atol=1.0e-8):
    raise SystemExit("PyLith used different vertices from the thermal solution")
if not np.allclose(
    sort_rows(pylith_centroids), sort_rows(thermal_centroids), rtol=0.0, atol=1.0e-8
):
    raise SystemExit("PyLith used different cells from the thermal solution")

if not np.isclose(final_time, 2.0, rtol=0.0, atol=1.0e-12):
    raise SystemExit(f"PyLith ended at {final_time:g} s, expected 2 s")
if not np.all(np.isfinite(stress)) or not np.all(np.isfinite(viscous_strain)):
    raise SystemExit("PyLith wrote non-finite Maxwell fields")
if np.max(np.abs(stress)) <= 0.0:
    raise SystemExit("PyLith material response is zero")
if stress.shape[0] != len(cells) or viscous_strain.shape[0] != len(cells):
    raise SystemExit("PyLith fields do not cover every thermal-mesh cell")
if np.max(temperature) - np.min(temperature) < 100.0:
    raise SystemExit("thermal field has insufficient temperature variation")

print(
    "Hydrothermal-field Maxwell smoke test passed at t = 2 s; "
    f"temperature=[{np.min(temperature):.6g}, {np.max(temperature):.6g}] °C; "
    f"viscosity=[{np.min(database[:, 6]):.6g}, {np.max(database[:, 6]):.6g}] Pa s; "
    f"peak stress={np.max(np.abs(stress)):.6g} Pa; "
    f"peak viscous strain={np.max(np.abs(viscous_strain)):.6g}."
)
PY
