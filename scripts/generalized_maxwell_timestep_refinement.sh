#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STEP_DIR="${ROOT}/pylith/step12_generalized_maxwell_ellipsoid"
OUTPUT_DIR="${STEP_DIR}/output"
PYLITH_ROOT="${ROOT}/pylith/pylith-5.0.2-linux-x86_64"
PYTHON="${ROOT}/envs/axial-modeling/bin/python"
REFINED_CONFIG="${OUTPUT_DIR}/generalized_maxwell_15day.cfg"
REFINED_H5="${OUTPUT_DIR}/genmaxwell-material-15day.h5"
REFINED_LOG="${OUTPUT_DIR}/pylith-15day.log"

for input in \
    "${OUTPUT_DIR}/genmaxwell-material.spatialdb" \
    "${OUTPUT_DIR}/genmaxwell-material.h5" \
    "${OUTPUT_DIR}/hydrothermal-temperature.npz"; do
    if [[ ! -f "${input}" ]]; then
        echo "Missing ${input}; run scripts/generalized_maxwell_ellipsoid_smoke.sh first." >&2
        exit 1
    fi
done

"${PYTHON}" - "${STEP_DIR}/generalized_maxwell.cfg" "${REFINED_CONFIG}" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1]).read_text()
source = source.replace(
    "step12_generalized_maxwell_ellipsoid", "step12_generalized_maxwell_15day"
)
source = source.replace("initial_dt = 2592000.0*s", "initial_dt = 1296000.0*s")
source += """

[pylithapp.problem.solution_observers.domain]
writer.filename = output/genmaxwell-domain-15day.h5

[pylithapp.problem.solution_observers.ground_surface]
writer.filename = output/genmaxwell-surface-15day.h5

[pylithapp.problem.materials.elastic.observers.observer.writer]
filename = output/genmaxwell-material-15day.h5
"""
Path(sys.argv[2]).write_text(source)
PY

(
    cd "${PYLITH_ROOT}"
    source setup.sh
    cd "${STEP_DIR}"
    if ! timeout 300 pylith --nodes=8 "${REFINED_CONFIG}" >"${REFINED_LOG}" 2>&1; then
        tail -n 60 "${REFINED_LOG}"
        exit 1
    fi
)

export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON}" "${ROOT}/scripts/generalized_maxwell_ellipsoid_smoke.py" check \
    --database "${OUTPUT_DIR}/genmaxwell-material.spatialdb" \
    --material "${OUTPUT_DIR}/genmaxwell-material.h5" \
    --temperature-archive "${OUTPUT_DIR}/hydrothermal-temperature.npz"
"${PYTHON}" "${ROOT}/scripts/generalized_maxwell_ellipsoid_smoke.py" check \
    --database "${OUTPUT_DIR}/genmaxwell-material.spatialdb" \
    --material "${REFINED_H5}" \
    --temperature-archive "${OUTPUT_DIR}/hydrothermal-temperature.npz"
"${PYTHON}" "${ROOT}/scripts/compare_generalized_maxwell_timesteps.py" \
    --coarse "${OUTPUT_DIR}/genmaxwell-material.h5" \
    --fine "${REFINED_H5}"
