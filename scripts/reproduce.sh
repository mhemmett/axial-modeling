#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_PREFIX="${ROOT}/envs/axial-modeling"
PYLITH_DIST="${ROOT}/pylith/pylith-5.0.2-linux-x86_64"
OOI_START_DATE="${OOI_START_DATE:-2014-01-01}"
OOI_END_DATE="${OOI_END_DATE:-$(date -u +%F)}"
RAW_DIR="${ROOT}/data/raw/ooi_bpr"
start_seconds="${SECONDS}"
git_revision="$(git -C "${ROOT}" rev-parse HEAD)"
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

central_raw="${RAW_DIR}/central_botsflu-daydepth_${OOI_START_DATE}_${OOI_END_DATE}.csv.gz"
east_raw="${RAW_DIR}/east_botsflu-daydepth_${OOI_START_DATE}_${OOI_END_DATE}.csv.gz"

conda run --prefix "${ENV_PREFIX}" python "${ROOT}/data/fetch_bpr.py" \
    --start "${OOI_START_DATE}" \
    --end "${OOI_END_DATE}" \
    --download
conda run --prefix "${ENV_PREFIX}" python "${ROOT}/data/process_bpr.py" "${central_raw}"
conda run --prefix "${ENV_PREFIX}" python "${ROOT}/data/process_bpr.py" "${east_raw}"
conda run --prefix "${ENV_PREFIX}" python "${ROOT}/data/fetch_historical_bpr.py" \
    --download \
    --accept-mgds-terms

make -j1 -C "${ROOT}" \
    smoke \
    maxwell-restart \
    thermal-material-smoke \
    thermal-cross-mesh-smoke \
    thermal-model \
    thermal-mesh-sensitivity \
    thermal-property-slices \
    model-setup-schematic \
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
    bpr-observation-plot \
    bpr-mogi-check \
    bpr-historical-check \
    historical-early-bpr-spatial-check \
    bpr-archive-crosscheck \
    historical-generalized-maxwell-check \
    historical-post-2011-bpr-check \
    historical-post-2017-bpr-check \
    historical-ooi-bpr-holdouts \
    historical-bpr-maxwell-pressure-inversion \
    historical-four-case-bpr-calibration \
    ooi-maxwell-pressure-inversion \
    ooi-maxwell-ellipsoid-check \
    ooi-eq16-hydrothermal-maxwell-check \
    ooi-maxwell-history-plot \
    test \
    lint \
    report
elapsed_seconds="$((SECONDS - start_seconds))"

printf 'Reproduction checkpoint completed at revision %s (%s tree) in %s s.\n' \
    "${git_revision}" "${working_tree}" "${elapsed_seconds}"
