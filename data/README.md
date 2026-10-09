# Data provenance

The article and supplement provide the model specification. This project does
not use datasets, numerical series, model output, code, plotting scripts, or
figure files supplied with the publication. It does not digitize published
plots. Independent bottom-pressure recorder (BPR) observations from the Ocean
Observatories Initiative (OOI), NOAA/NCEI, and NOAA/PMEL deployments support
model checking.

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

## Historical Axial BPR records

Historical deployments extend the independent pressure check across the January
1998 and April 2011 eruptions and add Center and South records from 2003–13.
The National Centers for Environmental Information (NCEI) archive provides the
WC81, WC82A, and WC82B 1997–99 raw pressure records, plus center deployments
from 2000–02, as 15-second absolute pressure in dbar. The Marine Geoscience Data
System (MGDS) archive provides selected 15-second Center and South deployments
from 2003–13. MGDS groups original channels with derived channels in a processed
archive; the workflow reads only each deployment's original `Depth` or `RawDep`
channel. It excludes detided, low-pass-filtered, and drift-corrected columns.
The selected MGDS data UIDs are 896874–896884. UID 896872 duplicates the
2000–02 NCEI coverage, and UID 896873 provides only a drift-corrected field, so
both are excluded. See the
[NCEI BPR inventory](https://www.ngdc.noaa.gov/hazard/bpr/), [NCEI raw archive
DOI](https://doi.org/10.7289/V5F18WNS), and [MGDS data DOI
10.1594/IEDA/322282](https://doi.org/10.1594/IEDA/322282).

The MGDS archive lists Cabaniss et al. among related publications. The selected
fields are original pressure-derived depth channels recorded by BPRs deployed
between 2003 and 2013; no data product, correction, value, or figure produced
for that paper enters the analysis. The MGDS data citation and CC BY-NC-SA 3.0
terms are retained in the downloaded archive. Any redistribution of derived
MGDS observations must credit the contributing investigators and MGDS and
preserve the share-alike terms.

Run `python data/fetch_historical_bpr.py` to print source locations. Add
`--download --ncei-only` to retrieve the ignored NCEI records without
requesting MGDS data. Add `--download --accept-mgds-terms` to retrieve all
archives; that flag submits MGDS's research-use acceptance, which requires
adequate citation to the contributing scientists and MGDS. The manifest keeps
checksums for downloaded records. Raw records and derived files remain under
ignored `data/raw/axial_bpr/` and `data/processed/axial_historical_bpr/`.

Run `python data/process_historical_bpr.py` to average each 15-second raw
channel by UTC day. A day is retained for displacement analysis when at least
75% of its 5,760 expected samples are present. NCEI dbar anomalies convert to
meters with `10,000 Pa / (1,025 kg m⁻³ × 9.80665 m s⁻²)`; MGDS raw-depth values
are already in meters. Positive uplift is a decrease in pressure-derived depth.
The processing does not remove tides, oceanographic variability, or instrument
drift, so long-term slopes are not interpreted as deformation.

Run `make bpr-historical-check` to repeat processing, calculate static Mogi and
PyLith ellipsoid checks for the 1998 and 2011 Center-to-South event changes,
and fit daily Mogi predictions across shared deployment intervals in
2003–05, 2007–09, 2009–11, and 2011–13. The event checks use the median daily
depth on days −7 through −1 and compare it with days +8 through +14. The
eruption-interval fit uses both stations' shared seven-day pre-eruption
baseline. Other paired intervals use the first seven paired daily means as a
baseline. Each fit predicts South from the daily Center value. Neither check
corrects tides, ocean variability, or instrument drift; the Mogi check also
omits viscoelastic memory. The context plot zeroes each deployment independently
and is not a corrected deformation history. Figures, daily CSVs, and model
diagnostics are written under ignored
`data/processed/axial_historical_bpr/`. Eruption dates come from NOAA/PMEL's
[1998 event account](https://pmel.noaa.gov/eoi/nemo/explorer/concepts/the98eruption.html)
and [2011 Axial site record](https://axial.ceoas.oregonstate.edu/axial_site.html).
The source and model limitations are detailed in
[`docs/historical_bpr_check.md`](../docs/historical_bpr_check.md).

Earthquake catalogs, bathymetry, and lava-flow source records remain outside
the authorized inputs.
