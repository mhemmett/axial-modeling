#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STEP_DIR="${ROOT}/pylith/step03_steady_thermal"
MESH_PATH="${STEP_DIR}/mesh/axial_box.msh"
OUTPUT_DIR="${STEP_DIR}/output"
PYTHON="${ROOT}/envs/axial-modeling/bin/python"

mkdir -p "${OUTPUT_DIR}"
if ! "${PYTHON}" "${ROOT}/meshing/axial_box_ellipsoid.py" \
    --output "${MESH_PATH}" >"${OUTPUT_DIR}/mesh.log" 2>&1; then
    tail -n 40 "${OUTPUT_DIR}/mesh.log"
    exit 1
fi

run_case() {
    local name="$1"
    shift
    if ! timeout 300 env "PYTHONPATH=${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}" \
        "${PYTHON}" -m axialstress.thermal_model \
        --mesh "${MESH_PATH}" \
        --output "${OUTPUT_DIR}/steady_thermal_${name}.npz" \
        "$@" >"${OUTPUT_DIR}/thermal_${name}.log" 2>&1; then
        tail -n 40 "${OUTPUT_DIR}/thermal_${name}.log"
        return 1
    fi
    cat "${OUTPUT_DIR}/thermal_${name}.log"
}

run_case baseline
run_case hydrothermal --hydrothermal
