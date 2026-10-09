#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${ROOT}/envs/axial-modeling/bin/python"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

bash "${ROOT}/scripts/ellipsoid_unit_response.sh"

PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}" \
    "${PYTHON}" "${ROOT}/scripts/ellipsoid_bpr_check.py"
