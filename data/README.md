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

## OOI Central Caldera after 2015

The public Ocean Observatories Initiative (OOI) MJ03F bottom-pressure and tilt
instrument reports daily mean seafloor depth as `BOTSFLU-DAYDEPTH`. OOI states
that this product is detided and corrected for pressure-sensor drift using
annual or biennial field measurements. Use `make ooi-center-fetch` to print
the public ERDDAP requests. Retrieve them with
`make ooi-center-fetch OOI_FETCH_ARGS='--download --stop 2026-10-24'`, then
run `make ooi-center-process`. The raw yearly CSV files, request URLs, and
SHA-256 manifest remain untracked under `data/raw/ooi_center_daily/`.

The processor sets zero uplift at the deepest observed daily value within
25 April–8 May 2015. It writes recorded depth differences and a gap inventory
under `data/processed/ooi_center_daily/`. It does not fill missing days.
The downloaded daily values carry QARTOD flag 2, meaning not evaluated.
The [OOI product description](https://oceanobservatories.org/data-product/botsflu/)
and [Central Caldera dataset](https://erddap.dataexplorer.oceanobservatories.org/erddap/info/ooi-rs03ccal-mj03f-05-botpta301/index.html)
document the source and units. This observed input may constrain a PyLith
pressure history; it is not a measured reservoir pressure.

## Provenance and limits

The NCEI and MGDS source records retain their archive metadata and terms.
`make paper-bpr-fetch` first prints the source inventory and terms for the
processed 2000–2002 Center file. Retrieve it with
`make paper-bpr-fetch PAPER_BPR_FETCH_ARGS='--download --accept-mgds-terms'`.
The file remains local under `data/raw/axial_bpr/` with its archive manifest.

`make paper-bpr` copies on-hour values from nine locally available Center
files under the cited Fox and Chadwick/Nooner dataset DOIs. The source
format notes identify missing Fox low-pass values as zero placeholders. The
2000–2002 file also has 239 zero low-pass hours at its end, adjacent to finite
raw depths; the export records these as missing. It records the original field,
checksum, time, source row, and gaps. No cross-deployment datum adjustment is
applied, and the paper's channel selection remains unverified. See
[`docs/reproduction.md`](../docs/reproduction.md) for the workflow and
[`docs/KNOWN_ISSUES.md`](../docs/KNOWN_ISSUES.md) for remaining model limits.
