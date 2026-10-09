#!/usr/bin/env bash
# Source this file to activate the repo-local Conda environment and PyLith.
_axial_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${PYLITH_NODES:-8}" != 8 ]]; then
    echo "This project runs PyLith with exactly 8 MPI ranks." >&2
    return 2 2>/dev/null || exit 2
fi
if ! ulimit -S -v 4194304 || ! ulimit -H -v 4194304; then
    echo "Could not set the 4 GiB per-process address-space limit." >&2
    return 2 2>/dev/null || exit 2
fi
if ! command -v conda >/dev/null 2>&1; then
    for _axial_conda_hook in \
        "${HOME}/miniconda3/etc/profile.d/conda.sh" \
        "${HOME}/anaconda3/etc/profile.d/conda.sh"; do
        if [[ -f "${_axial_conda_hook}" ]]; then
            # shellcheck source=/dev/null
            source "${_axial_conda_hook}"
            break
        fi
    done
fi

if ! command -v conda >/dev/null 2>&1; then
    echo "Conda is unavailable; initialize Conda before sourcing scripts/activate.sh." >&2
    return 1 2>/dev/null || exit 1
fi

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "${_axial_root}/envs/axial-modeling" || return 1 2>/dev/null || exit 1
_axial_pylith="${_axial_root}/pylith/pylith-5.0.2-linux-x86_64"
if [[ ! -f "${_axial_pylith}/setup.sh" ]]; then
    echo "PyLith is not installed; run make install-pylith." >&2
    return 1 2>/dev/null || exit 1
fi
cd "${_axial_pylith}" || return 1 2>/dev/null || exit 1
# PyLith's setup script expects the current directory to be its distribution root.
source setup.sh
cd "${_axial_root}" || return 1 2>/dev/null || exit 1
export PYLITH_NODES=8
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
unset _axial_root _axial_conda_hook _axial_pylith
