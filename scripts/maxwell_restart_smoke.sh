#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STEP_DIR="${ROOT}/pylith/step01_maxwell_restart"
OUTPUT_DIR="${STEP_DIR}/output"
LOG_DIR="${OUTPUT_DIR}"
PYLITH_ROOT="${ROOT}/pylith/pylith-5.0.2-linux-x86_64"
PYTHON="${ROOT}/envs/axial-modeling/bin/python"

mkdir -p "${OUTPUT_DIR}"
python "${ROOT}/meshing/axial_box_ellipsoid.py" \
    --output "${STEP_DIR}/mesh/axial_box.msh"

cd "${PYLITH_ROOT}"
source setup.sh
cd "${STEP_DIR}"

run_pylith() {
    local config="$1"
    local log_path="${LOG_DIR}/${config%.cfg}.log"
    if ! timeout 300 pylith --nodes=8 "${config}" >"${log_path}" 2>&1; then
        tail -n 50 "${log_path}"
        return 1
    fi
}

run_pylith step01_single.cfg
run_pylith step01_split.cfg
PYTHONHOME="" PYTHONPATH="${ROOT}/src" "${PYTHON}" \
    "${ROOT}/src/axialstress/pylith_restart.py" \
    "${OUTPUT_DIR}/first-domain.h5" \
    "${OUTPUT_DIR}/first-material.h5" \
    --output-dir "${OUTPUT_DIR}" \
    --prefix restart

PYTHONHOME="" PYTHONPATH="${ROOT}/src" "${PYTHON}" - "${ROOT}" "${OUTPUT_DIR}" <<'PY'
from pathlib import Path
import sys

import h5py
import numpy as np

root = Path(sys.argv[1])
output = Path(sys.argv[2])
sys.path.insert(0, str(root / "src"))

from axialstress.material_database import write_temperature_dependent_maxwell_database

with h5py.File(output / "first-domain.h5", "r") as solution, h5py.File(
    output / "first-material.h5", "r"
) as material:
    vertices = np.asarray(solution["geometry/vertices"], dtype=float)
    tetrahedra = np.asarray(material["viz/topology/cells"], dtype=np.int64)

write_temperature_dependent_maxwell_database(
    output / "material_update.spatialdb",
    vertices,
    tetrahedra,
    np.full(len(vertices), 1200.0),
    33.333333333e9,
    density_kg_m3=2800.0,
    poisson_ratio=0.25,
)

configuration = (root / "pylith/step01_maxwell_restart/step01_restart.cfg").read_text(
    encoding="utf-8"
)
replacements = (
    ("problem.defaults.name = step01_restart", "problem.defaults.name = step01_material_update"),
    (
        "db_A.description = Constant Maxwell material properties",
        "db_A.description = Eq. 15 and Eq. 16 Maxwell property update",
    ),
    (
        "db_A.iohandler.filename = material_properties.spatialdb",
        "db_A.query_type = nearest\n"
        "db_A.iohandler.filename = output/material_update.spatialdb",
    ),
    (
        "observers.observer.writer.filename = output/restart-material.h5",
        "observers.observer.writer.filename = output/material-update-material.h5",
    ),
    (
        "writer.filename = output/restart-domain.h5",
        "writer.filename = output/material-update-domain.h5",
    ),
    (
        "writer.filename = output/restart-surface.h5",
        "writer.filename = output/material-update-surface.h5",
    ),
)
for old, new in replacements:
    if configuration.count(old) != 1:
        raise SystemExit(f"expected one occurrence of restart setting: {old}")
    configuration = configuration.replace(old, new)
time_dependent_section = "[pylithapp.timedependent]\n"
if configuration.count(time_dependent_section) != 1:
    raise SystemExit("could not find the PyLith time-dependent configuration section")
configuration = configuration.replace(
    time_dependent_section,
    time_dependent_section + "notify_observers_ic = True\n",
)
(output / "step01_material_update.cfg").write_text(configuration, encoding="utf-8")
PY

run_pylith step01_restart.cfg
if ! timeout 300 pylith --nodes=8 "${OUTPUT_DIR}/step01_material_update.cfg" \
    >"${LOG_DIR}/material-update.log" 2>&1; then
    tail -n 50 "${LOG_DIR}/material-update.log"
    exit 1
fi

PYTHONHOME="" "${PYTHON}" - "${OUTPUT_DIR}" <<'PY'
from pathlib import Path
import sys

import h5py
import numpy as np

output = Path(sys.argv[1])
fields = (
    ("single-domain.h5", "restart-domain.h5", "vertex_fields/displacement"),
    ("single-material.h5", "restart-material.h5", "cell_fields/cauchy_stress"),
    ("single-material.h5", "restart-material.h5", "cell_fields/cauchy_strain"),
    ("single-material.h5", "restart-material.h5", "cell_fields/viscous_strain"),
)
tolerance = 5.0e-7

for single_name, restart_name, field in fields:
    with h5py.File(output / single_name, "r") as single, h5py.File(
        output / restart_name, "r"
    ) as restarted:
        single_time = float(np.asarray(single["time"]).reshape(-1)[-1])
        restart_time = float(np.asarray(restarted["time"]).reshape(-1)[-1])
        if not np.isclose(single_time, 2.0, rtol=0.0, atol=1.0e-12):
            raise SystemExit(f"continuous run ended at {single_time:g} s")
        if not np.isclose(restart_time, 2.0, rtol=0.0, atol=1.0e-12):
            raise SystemExit(f"restarted run ended at {restart_time:g} s")
        expected = np.asarray(single[field][-1], dtype=float)
        actual = np.asarray(restarted[field][-1], dtype=float)
        if expected.shape != actual.shape:
            raise SystemExit(f"{field} shapes differ: {expected.shape} != {actual.shape}")
        scale = max(float(np.max(np.abs(expected))), np.finfo(float).tiny)
        relative_error = float(np.max(np.abs(actual - expected)) / scale)
        if not np.isfinite(relative_error) or relative_error > tolerance:
            raise SystemExit(
                f"{field} relative error {relative_error:.3e} exceeds {tolerance:.1e}"
            )
        print(f"{field}: relative error {relative_error:.3e}")

print("Maxwell same-mesh restart check passed at t = 2 s.")

with h5py.File(output / "first-domain.h5", "r") as first_solution, h5py.File(
    output / "first-material.h5", "r"
) as first_material, h5py.File(
    output / "material-update-domain.h5", "r"
) as updated_solution, h5py.File(
    output / "material-update-material.h5", "r"
) as updated_material, h5py.File(
    output / "single-domain.h5", "r"
) as single_solution:
    first_time = float(np.asarray(first_solution["time"]).reshape(-1)[-1])
    updated_times = np.asarray(updated_solution["time"], dtype=float).reshape(-1)
    material_times = np.asarray(updated_material["time"], dtype=float).reshape(-1)
    if not np.isclose(first_time, 1.0, rtol=0.0, atol=1.0e-12):
        raise SystemExit(f"first material segment ended at {first_time:g} s")
    if not np.array_equal(updated_times, [1.0, 2.0]) or not np.array_equal(
        material_times, [1.0, 2.0]
    ):
        raise SystemExit(
            "material-update observers must include the transferred state at 1 s "
            "and the updated solution at 2 s"
        )

    expected_viscous_strain = np.asarray(
        first_material["cell_fields/viscous_strain"][-1], dtype=float
    )
    initialized_viscous_strain = np.asarray(
        updated_material["cell_fields/viscous_strain"][0], dtype=float
    )
    scale = max(float(np.max(np.abs(expected_viscous_strain))), np.finfo(float).tiny)
    state_error = float(
        np.max(np.abs(initialized_viscous_strain - expected_viscous_strain)) / scale
    )
    if not np.isfinite(state_error) or state_error > tolerance:
        raise SystemExit(
            f"updated-run initial viscous-strain relative error {state_error:.3e} "
            f"exceeds {tolerance:.1e}"
        )
    print(f"updated-run initial viscous strain: relative error {state_error:.3e}")

    baseline_displacement = np.asarray(
        single_solution["vertex_fields/displacement"][-1], dtype=float
    )
    updated_displacement = np.asarray(
        updated_solution["vertex_fields/displacement"][-1], dtype=float
    )
    scale = max(float(np.max(np.abs(baseline_displacement))), np.finfo(float).tiny)
    material_response_change = float(
        np.max(np.abs(updated_displacement - baseline_displacement)) / scale
    )
    if material_response_change <= 1.0e-2:
        raise SystemExit(
            "updated material properties did not produce a measurable "
            "final-displacement change"
        )
    if not np.all(np.isfinite(updated_displacement)):
        raise SystemExit("updated Maxwell displacement contains non-finite values")
    print(
        "Eq. 15/16 material update changed final displacement relative to the "
        f"uniform-property run by {material_response_change:.3e}"
    )
PY
