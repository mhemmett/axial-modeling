# Data provenance

The article and supplement provide the model specification. This project does
not use datasets, numerical series, model output, code, plotting scripts, or
figure files supplied with the publication. It does not digitize published
plots. The user authorized independent BPR observations from the Ocean
Observatories Initiative (OOI) for model checking.

## Historical uncabled BPR records

The user also authorized raw-depth observations from independent, uncabled
Axial BPR deployments that cover the 1998 and 2011 eruptions. The selected
records come from two long-term Marine Geoscience Data System (MGDS) archives:
the Fox 1997–1998 deployments ([10.1594/IEDA/322344](https://doi.org/10.1594/IEDA/322344))
and the Chadwick–Nooner 2009–2011 deployments
([10.1594/IEDA/322282](https://doi.org/10.1594/IEDA/322282)). These archive
entries are cited by Cabaniss et al. (2020), but the BPR measurements were
recorded during earlier, independent deployments. This authorization covers
only the original uncorrected `Depth` or `RawDep` instrument channels. It does
not cover any Cabaniss data product, processed time series, model output, code,
or figure.

Run `python data/fetch_historical_bpr.py` to inspect the selected archive
records without downloading them. Add `--download` to retrieve the four raw
deployment files and write a manifest with archive IDs, retrieval time, file
IDs, sizes, and SHA-256 checksums. The downloader requests the center and
south BPR records spanning each eruption. Source archives remain under ignored
`data/raw/historical_bpr/` and must not be committed.

Run `python data/process_historical_bpr.py` to read only `Depth` (1998 and
south 2011) or `RawDep` (2011 center), aggregate UTC samples to daily medians,
and write relative uplift series under ignored `data/processed/historical_bpr/`.
The source sampling interval is 15 seconds. Positive relative uplift is
calculated as the first-day raw depth minus the daily raw-depth median. The
processor does not read the archived SPOTL-detided, low-pass-filtered, or
drift-corrected columns. Daily medians reduce tidal variability but do not
remove tides or instrument drift. The short event-window changes are apparent
vertical changes, not calibrated uplift histories.

Run `python scripts/historical_bpr_mogi_check.py` to compare the south-BPR
response with a Mogi prediction from the center BPR over each full shared
deployment record and the focused eruption window. This first-principles
spatial check uses the deployment coordinates in the BPR station log, an
assumed 4 km source depth, 0.7 km radius, 60 GPa Young's modulus, and Poisson
ratio 0.25. Its CSV, JSON, and figure outputs are generated from the raw
channels and remain subject to the source archive's CC BY-NC-SA 3.0 license.
They are not a historical viscoelastic hindcast or a reproduction of a
Cabaniss data product. Full-record comparisons retain instrument drift and
tides, so they measure spatial agreement rather than calibrated uplift.

## OOI bottom-pressure records

The fetcher requests OOI's `BOTSFLU-DAYDEPTH` product for two Bottom Pressure
and Tilt instruments: Central Caldera (`RS03CCAL-MJ03F-05-BOTPTA301`) and
Eastern Caldera (`RS03ECAL-MJ03E-06-BOTPTA302`). OOI describes this daily series
as a 24-hour mean depth derived from detided 15-second pressure averages and
corrected for pressure-sensor drift using remotely operated vehicle (ROV)
measurements. The product is delivered as signed depth in meters, with uplift
positive. See the [OOI product description](https://oceanobservatories.org/data-product/botsflu/)
and [instrument locations](https://oceanobservatories.org/instrument-series/botpta/).

Run `python data/fetch_bpr.py` to print the public OOI ERDDAP requests. Add
`--download` to retrieve daily records and a manifest containing query URLs,
row counts, retrieval time, and checksums. The default date range begins in
2014 and ends today; actual deployment coverage starts in August 2014 at
Central Caldera and September 2014 at Eastern Caldera. The compressed
responses remain under ignored `data/raw/ooi_bpr/` and must not be committed.

Run `python data/process_bpr.py PATH_TO_FILE.csv.gz` to convert signed depth to
relative uplift from the first available daily sample while preserving the
OOI aggregate quality flag. OOI reports this flag as `NOT_EVALUATED` for the
downloaded daily series; the workflow retains that status and does not treat
it as a pass. Processed observations remain under ignored `data/processed/`.

After processing both sites, run `make bpr-observation-plot` to write
`figures/ooi_bpr_relative_uplift.png` and `.pdf`. The two records use separate
first-sample baselines; the plot retains and labels their OOI aggregate quality
codes. This observation-only plot covers available data from 2014 onward and
does not include eruption markers or earthquake counts.

Run `make bpr-mogi-check` to infer the analytical Mogi pressure change from the
Central series and compare its Eastern-site prediction. This is a point-source
elastic diagnostic with explicit assumptions, not the paper's ellipsoidal
viscoelastic model; see [`docs/bpr_mogi_check.md`](../docs/bpr_mogi_check.md).

Run `make ooi-maxwell-ellipsoid-check` to calculate a coarse PyLith ellipsoid
compliance, infer a monthly pressure history from Central uplift, and apply it
to a one-branch Maxwell forward check. The command requires processed Central
and Eastern OOI records. Its summary and aligned monthly observations remain
under ignored `data/processed/`; see
[`pylith/step09_ooi_maxwell_history/README.md`](../pylith/step09_ooi_maxwell_history/README.md)
for the method and current limitations.

OOI coverage does not extend to the 1998 and 2011 eruptions; the authorized raw
uncabled BPR channels add short event-window checks for those events. OOI can
check the 2014–present part of the modeled surface-deformation history, subject
to unresolved validation of the underlying model physics. Earthquake catalogs,
bathymetry, and lava-flow source records remain outside the authorized inputs.
