#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_PREFIX="${ROOT}/envs/axial-modeling"
PYLITH_DIST="${ROOT}/pylith/pylith-5.0.2-linux-x86_64"
start_seconds="${SECONDS}"
git_revision="$(git -C "${ROOT}" rev-parse HEAD)"
case "${REPRODUCE_SKIP_TESTS:-0}" in
    0) validation_targets=(test lint report) ;;
    1) validation_targets=(lint report) ;;
    *) echo "REPRODUCE_SKIP_TESTS must be 0 or 1." >&2; exit 2 ;;
esac
if [[ -z "$(git -C "${ROOT}" status --porcelain)" ]]; then
    working_tree="clean"
else
    working_tree="dirty"
fi

if [[ ! -x "${ENV_PREFIX}/bin/python" ]]; then
    make -C "${ROOT}" env
fi

if [[ ! -f "${PYLITH_DIST}/setup.sh" ]]; then
    make -C "${ROOT}" install-pylith
fi

case "${REPRODUCE_SKIP_FETCH:-0}" in
    0)
        conda run --prefix "${ENV_PREFIX}" python "${ROOT}/data/fetch_historical_bpr.py" \
            --download \
            --accept-mgds-terms
        ;;
    1)
        if [[ ! -f "${ROOT}/data/raw/axial_bpr/manifest.json" ]]; then
            echo "Cannot skip data retrieval; missing historical BPR manifest." >&2
            exit 2
        fi
        echo "Using previously downloaded historical BPR observations."
        ;;
    *)
        echo "REPRODUCE_SKIP_FETCH must be 0 or 1." >&2
        exit 2
        ;;
esac

make -j1 -C "${ROOT}" \
    smoke \
    maxwell-restart \
    thermal-material-smoke \
    thermal-cross-mesh-smoke \
    thermal-model \
    thermal-mesh-sensitivity \
    thermal-maxwell-smoke \
    maxwell-ellipsoid-smoke \
    generalized-maxwell-check \
    rheology-case-matrix \
    ellipsoid-failure-progression-smoke \
    thermal-maxwell-ellipsoid-smoke \
    hydrothermal-maxwell-ellipsoid-smoke \
    eq16-maxwell-ellipsoid-smoke \
    eq16-hydrothermal-maxwell-ellipsoid-smoke \
    mogi-benchmark \
    mogi-domain-sensitivity \
    failure-connectivity-smoke \
    failure-progression-smoke \
    ellipsoid-mesh-sensitivity \
    winkler-foundation-check \
    ellipsoid-unit-response \
    historical-bpr-daily \
    historical-four-case-bpr-calibration \
    historical-failure-time-refinement \
    "${validation_targets[@]}"
elapsed_seconds="$((SECONDS - start_seconds))"

printf 'Reproduction checkpoint completed at revision %s (%s tree) in %s s.\n' \
    "${git_revision}" "${working_tree}" "${elapsed_seconds}"
