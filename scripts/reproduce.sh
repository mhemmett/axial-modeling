#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
conda run --prefix "${ROOT}/envs/axial-modeling" \
    python "${ROOT}/scripts/reproduction_status.py" --require-complete
