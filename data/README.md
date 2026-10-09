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
1998 and April 2011 eruptions and add raw BPR coverage from 1987–2022. The
National Centers for Environmental Information (NCEI) archive provides ten
1987–96 deployments, the WC81, WC82A, and WC82B 1997–99 records, and two center
deployments from 2000–02 as raw absolute pressure in dbar. WC09–WC32 (1987–92)
use 56.25-second samples; WC51 onward uses 15-second samples. The Marine
Geoscience Data System (MGDS) archive provides selected 15-second Center and South deployments
from 2002–17. MGDS groups original channels with derived channels in a processed
archive; the workflow reads only each deployment's original `Depth` or `RawDep`
channel. It excludes detided, low-pass-filtered, and pressure-drift-corrected
columns, except for the 2002–04 Center record whose metadata states that the
drift correction was zero and left `DriftCorrRawDep` unchanged from its raw
depth. The processor excludes that record's tide-subtracted and filtered
columns.
The selected MGDS data UIDs are 896874–896887, 1109496, and 1109497. UIDs
896885–896887 add three 2013–15 instruments; 1109496 and 1109497 add the
2015–17 Center and South 2 instruments. UID 896872 duplicates the 2000–02 NCEI
coverage. UID 896873 adds the NeMO 2002–04 Center deployment. Its file exposes
`DriftCorrRawDep`; MGDS states the zero drift correction left that original
depth channel unchanged. This adds Center observations from July 2002, while a
spatial South holdout begins in September 2003. The official
[MGDS file listing](https://www.marine-geo.org/tools/search/Files.php?data_set_uid=22282)
records the dates, coordinates, channel note, and source DOI. See the
[NCEI BPR inventory](https://www.ngdc.noaa.gov/hazard/bpr/), [NCEI raw archive
DOI](https://doi.org/10.7289/V5F18WNS), and [MGDS data DOI
10.1594/IEDA/322282](https://doi.org/10.1594/IEDA/322282).

The 2017–22 MGDS subset adds moored BPR records sampled every 15 seconds and
miniBPR records sampled every 100 seconds. It fetches UIDs 1186171, 1186173,
1186175, 2415279, 2415281, 2415283, and 2845422–2845424. Processing reads only
the original moored `RawDep` or miniBPR `RawDepth(m)` channel, which retains
tides. Some miniBPR timestamps include archive clock-drift adjustments; those
do not change the raw pressure channel. The 2017–18 Center pressure record has
a mid-deployment instrument offset documented in its source notes. It appears
in the context plot but is excluded from model forcing. The fetch helper
supports `--post-2017-only` for this subset and preserves other records in the
local provenance manifest.

The separate MGDS Fox archive IEDA/322344 supplies 15-second Center and South
`Depth` channels for the 1997–98 WC81/VSM1 and WC82/VSM2 instruments. This is
an archive-source check against NCEI raw pressure from the same two instruments,
not additional station coverage. Relative-uplift correlations are effectively
1.000 over 309 Center days and 365 South days; cross-source RMSE is 0.050 m and
0.016 m, respectively. MGDS reports that `Depth` is original pressure converted
from psi to meters at 0.67 m/psi. Processing excludes `SpotlDetidedDepth` and
`LPFDetidedDepth`; it does not use paper-associated pressure products or values.
See the [Fox archive DOI 10.1594/IEDA/322344](https://doi.org/10.1594/IEDA/322344).

The MGDS archives list Cabaniss et al. among related publications. The selected
fields are original pressure-derived depth channels, including the 1997–98 Fox
archive's `Depth` series; no data product, correction, value, or figure produced
for that paper enters the analysis. The MGDS data citations and CC BY-NC-SA 3.0
terms are retained in the downloaded archives. Any redistribution of derived
MGDS observations must credit the contributing investigators and MGDS and
preserve the share-alike terms.

Run `python data/fetch_historical_bpr.py` to print source locations. Add
`--download --ncei-only` to retrieve the ignored NCEI records without
requesting MGDS data. Add `--download --accept-mgds-terms` to retrieve all
archives; that flag submits MGDS's research-use acceptance, which requires
adequate citation to the contributing scientists and MGDS. The manifest keeps
checksums for downloaded records. Raw records and derived files remain under
ignored `data/raw/axial_bpr/` and `data/processed/axial_historical_bpr/`.
Add `--2002-only` with those options to retrieve only UID 896873 while
preserving other entries in the local provenance manifest.

Run `make bpr-archive-crosscheck` to compare the original Fox `Depth` channels
with the matching NCEI records. The command writes its checksum-bearing summary
under `data/processed/axial_historical_bpr/`.

Run `python data/process_historical_bpr.py` to average each raw channel by UTC
day. A day is retained for displacement analysis when at least 75% of the
samples expected from that deployment's cadence are present. NCEI dbar anomalies convert to
meters with `10,000 Pa / (1,025 kg m⁻³ × 9.80665 m s⁻²)`; MGDS raw-depth values
are already in meters. Positive uplift is a decrease in pressure-derived depth.
The processing does not remove tides, oceanographic variability, or instrument
drift, so long-term slopes are not interpreted as deformation.

Run `make bpr-historical-check` to repeat processing, calculate static Mogi and
PyLith ellipsoid checks for the 1998 and 2011 Center-to-South event changes,
and fit daily Center-to-South predictions across the 1995–96, 2002–04,
2003–05,
2005–07, 2007–09, and 2011–13 overlaps. The event checks use the median daily
depth on days −7 through −1 and compare it with days +8 through +14. The
eruption-interval fit uses both stations' shared seven-day pre-eruption
baseline. Other paired intervals use the first seven paired daily means as a
baseline. WC67 and NeMO South 1 add held-out checks in 1995–96 and 2007–09.
Each fit predicts a held-out station from the daily Center value. Neither check
corrects tides, ocean variability, or instrument drift; the Mogi check also
omits viscoelastic memory. The context plot zeroes each deployment independently
and is not a corrected deformation history. Daily CSVs and model diagnostics
are written under ignored `data/processed/axial_historical_bpr/`. The tracked
`figures/historical_bpr_deployment_context.png` and PDF show deployment coverage
from 1987–2022. Eruption dates come from NOAA/PMEL's
[1998 event account](https://pmel.noaa.gov/eoi/nemo/explorer/concepts/the98eruption.html)
and [2011 Axial site record](https://axial.ceoas.oregonstate.edu/axial_site.html).
The source and model limitations are detailed in
[`docs/historical_bpr_check.md`](../docs/historical_bpr_check.md).

Run `make historical-bpr-maxwell-pressure-inversion` to infer pressure from
the original raw WC81 Center and WC82A South channels across the 1998 eruption
and the NeMO 2010–2011 Center and 2009–2011 South channels across the 2011
eruption. It reads only NCEI's `seafloor_pressure_abs_raw [dbar]` and the
original MGDS `RawDep` or `Depth` field. Daily means require at least 75%
coverage; paired daily uplift is interpolated to a uniform weekly grid. A
PyLith one-branch Maxwell response kernel fits each Center series and holds
South out. The tracked plot is
`figures/historical_maxwell_pressure_inversion.png`; aligned inputs, inversion
summaries, and model records remain under ignored
`data/processed/axial_historical_bpr/maxwell_pressure_inversion/`. This
diagnostic does not use publication-associated observations, corrections, or
outputs. It does not remove tides, ocean variability, or instrument drift.

Run `make historical-generalized-maxwell-2011-continuous-check` to carry the
2011 event stress history through the 2011–13 replacement BPR pair. The Center
deployment files do not overlap and have a five-day gap; the diagnostic holds
inferred pressure constant across that gap and resets the observation baseline
for each instrument. It reads original MGDS `RawDep` Center and `Depth` South
channels and checks both South deployments as spatial holdouts. The pressure
transition, branch properties, raw channel effects, and mesh remain
limitations; this is not a calibrated eruption hindcast.

Run `make historical-post-2011-bpr-check` to extend the raw deployment
comparisons through 2017 using original MGDS `RawDep` channels. The 2013–15
Center fit checks South 2 over 709 paired days and holds South 1 out over 711
days. Their RMSE values are 0.358 m and 1.096 m; the South 1 bias is −0.988 m.
The separate 2015–17 Center/South 2 check spans 687 paired days and has 0.265 m
RMSE with −0.245 m bias. These records overlap the OOI era, but each raw sensor
has an independent baseline and retains tides, ocean variability, and drift.
The pressure ranges inferred from static compliance reach −50.7 to +26.7 MPa
in 2013–15 and 0 to +20.8 MPa in 2015–17. These remain provisional diagnostics
on a nonconverged mesh with synthetic Maxwell branches; the high correlations
do not validate the inferred pressure scale.
The tracked combined interval figure and two report-sized subsets show the
seven windows through 2017 without interpolating across deployment gaps.

Run `make historical-post-2017-bpr-check` for the 2018–20 moored pair and the
2020–22 miniBPR pair. The checks contain 741 and 648 paired days; held-out South
RMSE is 0.105 m and 0.043 m, respectively. Both runs use the same synthetic
three-branch rheology and static compliance as the earlier checks. Compliance
is not mesh-converged, and raw channels retain ocean variability, so these
comparisons expand coverage without calibrating pressure or branch properties.
The tracked `figures/historical_generalized_maxwell_deployment_bpr_check_2018_2022.png`
shows both windows. The expanded combined plot has nine deployment windows and
leaves gaps unfilled.

Run `make historical-generalized-maxwell-1998-continuous-check` to carry the
1998 event stress state from the WC81 Center record through the WC82 South
record ending in May 1999. This target reads only NCEI's original
`seafloor_pressure_abs_raw [dbar]` channel. The two WC82 South files overlap
for eight daily records; the diagnostic aligns their independently zeroed
uplift series using the mean difference over that raw overlap. WC81 ends on
7 August 1998, so its final inferred pressure is held constant for the
remaining 270 days. This assumption preserves viscoelastic memory for a
post-eruption South check, but does not supply missing Center observations or
produce a calibrated hindcast. Source archive: [NCEI raw BPR archive,
DOI 10.7289/V5F18WNS](https://doi.org/10.7289/V5F18WNS). The plot is tracked;
aligned daily comparisons and run summaries remain ignored under
`data/processed/axial_historical_bpr/`.

Run `make historical-early-bpr-spatial-check` to check original NCEI raw
pressure channels from ten earlier deployments spanning September 1987 through
June 1996. The target embeds each BPR coordinate in one bounded PyLith mesh,
fits static pressure at one station, and predicts overlapping instruments for
the August–September 1994 and 1995–96 records. The 1987–93 single-instrument
fits extend the modeled time coverage but are calibration only; these records
do not form a continuous deformation series. The summary is written to ignored
`data/processed/axial_historical_bpr/early_ncei_spatial_check.json`. Inputs are
limited to NCEI's original `seafloor_pressure_abs_raw [dbar]` channel; no
detided, filtered, drift-corrected, or paper-associated data products are used.

The context figure and tracked historical ellipsoid comparison contain derived
values from MGDS IEDA/322282, including the post-2011 deployments through 2022.
The report also summarizes the 1997–98 comparison from IEDA/322344. These
data-bearing artifacts are distributed under CC
BY-NC-SA 3.0, separately from the repository's MIT software license; source
attribution is included in their captions and here.

Earthquake catalogs, bathymetry, and lava-flow source records remain outside
the authorized inputs.
