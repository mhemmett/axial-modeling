# Observation inputs

The model calibration uses original Center bottom-pressure-recorder (BPR)
observations from NCEI and MGDS deployments. These records provide the
historical forcing needed to reproduce the paper's pressure, stress, and
failure results. Published pressure and failure values are comparison targets;
they are not model inputs.

## Historical BPR archives

Run `python data/fetch_historical_bpr.py` to print the NCEI and MGDS source
locations. Add `--download --accept-mgds-terms` to download the authorized raw
archives. The helper records request metadata and checksums in
`data/raw/axial_bpr/manifest.json`. Raw data and processed daily series remain
local and untracked.

Run `python data/process_historical_bpr.py` to convert each supported raw
channel into daily means. A daily value is retained when at least 75% of its
expected samples are present. The processor records the selected channel,
units, sample count, coverage, and source file in
`data/processed/axial_historical_bpr/summary.json`.

The historical four-case model uses Center deployment records for the 1998
and 2011 event windows. It starts each window at its first covered Center
observation and interpolates onto a uniform seven-day pressure grid. Raw and
corrected Center inputs remain separate; use
`make historical-bpr-corrected-daily` to process the MGDS predicted-tide and
available MPR drift-corrected channels.

## Provenance and limits

The NCEI and MGDS source records retain their archive metadata and terms. MGDS
derived low-pass channels are not used as model forcing. Tide and drift
corrections are observation preprocessing and do not supply modeled pressure
or stress. The event-window fits include eruption deflation and therefore
cannot independently predict eruption timing. See
[`docs/reproduction.md`](../docs/reproduction.md) for the workflow and
[`docs/KNOWN_ISSUES.md`](../docs/KNOWN_ISSUES.md) for remaining model limits.
