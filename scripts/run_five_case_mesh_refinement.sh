#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRATCH_DIR="${1:-/tmp/axial-150m-runs}"
mkdir -p "${SCRATCH_DIR}"
exec 9>"${SCRATCH_DIR}/.run.lock"
if ! flock -n 9; then
    echo "A 150 m reconstruction already holds ${SCRATCH_DIR}/.run.lock" >&2
    exit 75
fi
PYTHON_BIN="${ROOT_DIR}/envs/axial-modeling/bin/python"
BASIS_DIR="${ROOT_DIR}/data/processed/refined_elastic_basis_150m"
SOURCE_DIR="${SCRATCH_DIR}/source_value_bpr_failure_2011_2015_150m"
HISTORICAL_DIR="${SCRATCH_DIR}/source_value_bpr_failure_1998_2011_150m"
POST_DIR="${SCRATCH_DIR}/source_value_ooi_failure_2015_present_150m"
export PYTHONPATH="${ROOT_DIR}/src:${ROOT_DIR}/scripts:${ROOT_DIR}/envs/axial-modeling/lib/python3.12/site-packages"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export AXIAL_RESUME_COMPLETED_RUNS=1

if [[ ! -f "${SOURCE_DIR}/summary.json" ]]; then
    "${PYTHON_BIN}" "${ROOT_DIR}/scripts/source_value_bpr_failure.py" \
        --basis-dir "${BASIS_DIR}" --output-dir "${SOURCE_DIR}" --overwrite
fi
timeout 3600 "${PYTHON_BIN}" "${ROOT_DIR}/scripts/elastic_historical_cycle_failure.py" \
    --basis-dir "${BASIS_DIR}" \
    --step-days 7 \
    --output-dir "${SCRATCH_DIR}/elastic_bpr_failure_1998_2011_150m"

for case in constant_maxwell thermal_maxwell hydrothermal_maxwell; do
    "${PYTHON_BIN}" "${ROOT_DIR}/scripts/source_value_historical_cycle_failure.py" \
        --source-dir "${SOURCE_DIR}" --basis-dir "${BASIS_DIR}" \
        --output-dir "${HISTORICAL_DIR}" --case "${case}" --step-days 7
    "${PYTHON_BIN}" "${ROOT_DIR}/scripts/source_value_ooi_failure.py" \
        --source-dir "${SOURCE_DIR}" --basis-dir "${BASIS_DIR}" \
        --output-dir "${POST_DIR}" --case "${case}" --step-days 7
    for cycle in 1998-2011 2011-2015; do
        fit_dir="${HISTORICAL_DIR}"
        if [[ "${cycle}" == "2011-2015" ]]; then
            fit_dir="${SOURCE_DIR}"
        fi
        "${PYTHON_BIN}" "${ROOT_DIR}/scripts/source_value_event_states.py" \
            --cycle "${cycle}" --case "${case}" \
            --source-dir "${SOURCE_DIR}" --basis-dir "${BASIS_DIR}" \
            --fit-dir "${fit_dir}" \
            --output-dir "${SCRATCH_DIR}/source_value_event_states_${cycle//-/_}_150m"
    done
done

for cycle in 1998-2011 2011-2015 post-2015; do
    fit_dir="${HISTORICAL_DIR}"
    if [[ "${cycle}" == "2011-2015" ]]; then
        fit_dir="${SOURCE_DIR}"
    elif [[ "${cycle}" == "post-2015" ]]; then
        fit_dir="${POST_DIR}"
    fi
    "${PYTHON_BIN}" "${ROOT_DIR}/scripts/source_value_tectonic_failure.py" \
        --cycle "${cycle}" --source-dir "${SOURCE_DIR}" \
        --basis-dir "${BASIS_DIR}" --fit-dir "${fit_dir}" \
        --output-dir "${SCRATCH_DIR}/source_value_tectonic_${cycle//-/_}_150m"
done
