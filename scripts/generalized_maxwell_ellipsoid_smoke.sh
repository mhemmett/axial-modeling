#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STEP_DIR="${ROOT}/pylith/step12_generalized_maxwell_ellipsoid"
OUTPUT_DIR="${STEP_DIR}/output"
PYLITH_ROOT="${ROOT}/pylith/pylith-5.0.2-linux-x86_64"
PYTHON="${ROOT}/envs/axial-modeling/bin/python"

mkdir -p "${OUTPUT_DIR}"
if ! "${PYTHON}" "${ROOT}/meshing/axial_ellipsoid_bpr.py" \
    --output "${STEP_DIR}/mesh/axial_ellipsoid.msh" >"${OUTPUT_DIR}/mesh.log" 2>&1; then
    tail -n 40 "${OUTPUT_DIR}/mesh.log"
    exit 1
fi

export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON}" "${ROOT}/scripts/generalized_maxwell_ellipsoid_smoke.py" build \
    --mesh "${STEP_DIR}/mesh/axial_ellipsoid.msh" \
    --database "${OUTPUT_DIR}/genmaxwell-material.spatialdb"

LOG="${OUTPUT_DIR}/pylith.log"
(
    cd "${PYLITH_ROOT}"
    source setup.sh
    cd "${STEP_DIR}"
    if ! timeout 300 pylith generalized_maxwell.cfg >"${LOG}" 2>&1; then
        tail -n 50 "${LOG}"
        exit 1
    fi
)

"${PYTHON}" "${ROOT}/scripts/generalized_maxwell_ellipsoid_smoke.py" check \
    --database "${OUTPUT_DIR}/genmaxwell-material.spatialdb" \
    --material "${OUTPUT_DIR}/genmaxwell-material.h5"
