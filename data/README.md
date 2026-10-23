# Observation inputs

The model uses Center bottom-pressure-recorder (BPR) observations from the
archives cited by Cabaniss et al. The archives include detided, drift-corrected,
and low-pass depth fields in meters. These processed observations are eligible
inputs. The paper's modeled pressure and failure values remain comparison
targets. The exact source field and cross-deployment reference levels used
in the paper are not reported in the current method record.

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

The NCEI and MGDS source records retain their archive metadata and terms.
`make paper-bpr` copies hourly values from eight locally available Center
files under the cited Fox and Chadwick/Nooner dataset DOIs. The source
format notes identify missing Fox low-pass values as zero placeholders;
these are omitted. The export records the original field, checksum, time,
source row, and gaps. No cross-deployment datum adjustment is applied, and
the paper's channel selection remains unverified. See
[`docs/reproduction.md`](../docs/reproduction.md) for the workflow and
[`docs/KNOWN_ISSUES.md`](../docs/KNOWN_ISSUES.md) for remaining model limits.
