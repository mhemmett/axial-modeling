# Historical raw BPR checks

Raw Axial bottom-pressure records add independent observations where the Ocean
Observatories Initiative (OOI) record does not reach. Ten NCEI deployments
extend the raw history to 1987, and a three-station overlap in 1995–96 adds a
pre-eruption spatial check. The 1997–98 WC81 and WC82A records span the January
1998 eruption, and the NeMO Center and South records span April 2011. Additional
Center and South deployments extend the raw time series through June 2022. The
raw comparison workflow uses original pressure channels. A separate 1998/2011
event calibration uses MGDS predicted-tide observations and MPR drift
corrections where available; it excludes all Cabaniss model output.

## Source selection

The National Centers for Environmental Information (NCEI) archives ten raw
Axial deployments from 1987–96 as absolute pressure in dbar. WC09–WC32 (1987–92)
have 56.25-second sampling; WC51–WC69 (1993–96) have 15-second sampling. Raw
file headers provide deployment dates and coordinates. WC67, WC68, and WC69
overlap from 21 July 1995 through 22 June 1996; WC68 is used as the Center and
WC69 as the South holdout. The archive also contains WC81, WC82A, and WC82B
from 1997–99, plus two center deployments from 2000–02. Those later NCEI
records use 15-second raw absolute pressure. WC81 and the 2000–02 instruments
were at the caldera center; WC82A was south of the center. MGDS supplies raw
channels for deployments from 2002 through 2022. The processor reads only the
original `Depth`, `RawDep`, `RawDepth`, or `RawDepth(m)` column and excludes
detided, filtered, and pressure-drift-corrected columns. For the later subset
it fetches UIDs 1186167–1186175, 2415279, 2415281, 2415283, and 2845422–2845424.
The 2017–18 miniBPR and NeMO North/West raw channels are retained as spatial
holdouts against OOI Central. The selected 2003–17 UIDs are recorded in the
fetch manifest. UID 896872
duplicates NCEI coverage. UID 896873 supplies the NeMO 2002–04 Center record;
its file labels the raw-depth field `DriftCorrRawDep`, but the station details
state that measured drift correction was zero and left raw-depth values
unchanged. This single documented exception uses only that field and excludes
`DriftCorrSpotlDep` and `DriftCorrLPFDep`. The record spans 20 July 2002 to
18 July 2004 at 45.95252° N, 130.01017° W. The official
[MGDS file listing](https://www.marine-geo.org/tools/search/Files.php?data_set_uid=22282)
records its date range and zero-drift note. Processing converts each pressure
anomaly to vertical displacement with a hydrostatic approximation, using
seawater density `1025 kg/m³` and gravity `9.80665 m/s²`.
The Marine Geoscience Data System (MGDS) archive for IEDA/322282 contains
original and derived columns together. The check reads only original raw
channels from selected 2002–22 deployments. The 2002–04 Center record overlaps
the later Center and South deployments only from September 2003 through July
2004; its earlier daily record has no simultaneous spatial holdout. Later
moored records use 15-second `RawDep`; the 2020–22 miniBPR records use
100-second `RawDepth(m)`.
Their source notes identify the 2017–18 Center channel as unstable after a
mid-record offset, so it appears only in the deployment-context plot and does
not drive a model check. MiniBPR timestamps may include archive clock-drift
adjustments, while the selected raw pressure channels retain tides and do not
use pressure-drift, tide, or filter corrections.

MGDS IEDA/322344 separately archives the 1997–98 WC81/VSM1 Center and
WC82/VSM2 South records. Its `Depth` column contains original 15-second
pressure observations converted from psi to meters with the archive's
0.67 m/psi factor. The source comparison reads only `Depth`; it excludes
`SpotlDetidedDepth` and `LPFDetidedDepth`. These duplicate archive copies of the
same physical instruments already represented by NCEI WC81, WC82A, and WC82B,
so they check channel handling and do not add station coverage. MGDS IEDA/322344
is cited at [doi:10.1594/IEDA/322344](https://doi.org/10.1594/IEDA/322344).

The MGDS record includes Cabaniss et al. among its related publications. The
selected fields are original instrument pressure channels converted to depth
by the archive; no data product, correction, numerical result, or figure
created for that paper enters this analysis. MGDS requires
citation of the contributing investigators and repository, and distributes the
archive under CC BY-NC-SA 3.0. NCEI source links, MGDS DOI, exact channels,
retrieval checksums, and ignored local file paths are recorded by
`data/fetch_historical_bpr.py`.

The source citations are National Oceanic and Atmospheric Administration
(2005), *Deep-Ocean Assessment and Reporting of Tsunamis (DART)*, NOAA/NCEI,
doi:[10.7289/V5F18WNS](https://doi.org/10.7289/V5F18WNS), and Chadwick, W., et
al. (2023), *Processed Bottom Pressure Recorder data from uncabled instruments
deployed at Axial Seamount*, MGDS,
doi:[10.1594/IEDA/322282](https://doi.org/10.1594/IEDA/322282).
Fox, C. G. (2016), *Processed Bottom Pressure Recorder data from uncabled
instruments deployed at Axial Seamount on the Juan de Fuca Ridge*, MGDS,
doi:[10.1594/IEDA/322344](https://doi.org/10.1594/IEDA/322344).

The archive cross-check pairs MGDS Fox Center with NCEI WC81 for 309 days and
Fox South with NCEI WC82A for 365 days. Relative-uplift correlations round to
`1.000000`; RMSE is `0.050 m` at Center and `0.016 m` at South. The 8-day
WC82B overlap has `0.0003 m` RMSE but is too short for a strong comparison.
The Fox archive's 1998 event-window changes are `−3.212 m` at Center and
`−1.102 m` at South, compared with `−3.289 m` and `−1.128 m` from NCEI. The
approximately 2.3% amplitude difference is consistent with the different
pressure-to-depth conversion factors; the traces otherwise closely track each
other. This validates archive handling for the same physical sensors and does
not add station coverage.

## Raw instrument coverage during the 1998 and 2011 eruptions

An inventory audit of the public [NCEI Axial raw BPR catalog](https://www.ngdc.noaa.gov/thredds/catalog/dart_bpr/rawdata/axial_seamount/catalog.html)
and both MGDS Axial archives found no additional event-time raw series to add.
For January 1998, the NCEI catalog lists WC81 at Center and WC82A/WC82B from
the same South VSM2. WC81 and WC82A span the eruption; WC82B begins afterward
and is used as the South follow-up. The two 1997–98 MGDS Fox files are archive
copies of those same Center and South instruments, already used for the raw
channel cross-check above.

For April 2011, the MGDS IEDA/322282 inventory lists only the NeMO 2009–11
South and 2010–11 Center raw BPR files across the eruption. Both are already
included in the event and continuous checks. The NeMO 2011–13 Center/South
records provide post-eruption follow-up and are checked separately. NOAA's
[2011 cruise report](https://www.pmel.noaa.gov/eoi/nemo/nemo11-cruise-report.pdf)
records three pre-eruption moorings, but the NeMO2009 Middle BPR could not be
enabled and was suspected to be buried in new lava. No raw time-series file for
that instrument appears in the MGDS inventory. Thus, there is no additional
public raw BPR time series for either event window in these source archives.
The coverage audit uses deployment inventory and cruise status only; it does
not use Cabaniss et al. observations, corrections, results, or figures.

## Processing and model checks

The processor averages original raw measurements by UTC day and requires at
least 75% of the samples expected from each deployment's sampling interval.
For each event, it references
relative elevation to the median depth on days −7 through −1, then compares
that baseline with the median on days +8 through +14. NOAA/PMEL event accounts
set the reference dates: 25 January 1998 and 6 April 2011. No tides, ocean
variability, pressure drift, or data gaps are corrected; the output is an
event-scale observation check, not a corrected long-term deformation history.

WC81 shows a `−3.289 m` relative-elevation change across the 1998 event
windows, and WC82A shows `−1.128 m`. The smaller South response is 34% of the
Center response in these raw event windows. The 2011 raw channels show
`−2.296 m` at Center and `−1.788 m` at South. WC82B starts after the 1998 event
and supplies post-eruption context, not an independent measurement of that
eruption.

## Subdaily raw event checks

The subdaily check reads the original 15-second raw channel from the same four
Center/South instruments and aggregates samples into UTC-hour medians. An hour
is retained when it contains at least 75% of its expected samples. Each
instrument uses its median depth over days −7 through −1 as an independent
baseline; the figure overlays the existing daily means across a 43-day window.
No tide, filter, ocean, or drift correction is applied.

Each station contributes 1,032 hourly bins, including 168 valid hours in both
the baseline and days +8 through +14 comparison windows. The hourly-median
changes are `−3.328 m` at 1998 Center and `−1.159 m` at 1998 South, compared
with daily-mean changes of `−3.289 m` and `−1.128 m`. The 2011 hourly changes
are `−2.401 m` at Center and `−1.894 m` at South, versus daily values of
`−2.296 m` and `−1.788 m`. The differences of 0.031–0.106 m quantify
aggregation sensitivity while the traces retain large tidal and other
short-period variations. Date markers show only the event day; these records
do not estimate an eruption hour or identify a precursor.

Run `make historical-bpr-subdaily-event-check` to regenerate the hourly CSVs,
JSON summary, and
[`historical_bpr_subdaily_eruption_windows.png`](../figures/historical_bpr_subdaily_eruption_windows.png).
Hourly data remain ignored under `data/processed/axial_historical_bpr/`; the
figure uses original NCEI and MGDS channels and contains no publication-derived
data.

Each eruption has a Center-to-South check using separate raw BPR deployments.
For 1998, the spherical Mogi benchmark (`a = 0.7 km`, `d = 4 km`, `E = 60 GPa`,
assumed `ν = 0.25`) fits WC81 with `−4.91 GPa` and predicts `−1.549 m` at
WC82A; the held-out residual is `+0.421 m`. For 2011, the same benchmark fits
the Center record with `−3.43 GPa` and predicts `−1.406 m` at South, leaving a
`−0.381 m` residual. These large fitted pressures show that the point-source
benchmark is not a physically calibrated eruption-scale model at these
assumptions.

The 2,761-tetrahedron PyLith ellipsoid unit response fits WC81 with
`−103.09 MPa` and predicts `−0.253 m` at WC82A, leaving a `−0.875 m` residual.
For 2011, it fits Center with `−71.97 MPa` and predicts `−0.356 m` at South,
leaving a `−1.431 m` residual. Both predictions miss the held-out event change
substantially. The ellipsoid mesh is not converged, the checks omit
viscoelastic memory, and the raw daily means retain ocean and instrument
effects. These static results do not establish a failure of the full
temperature-dependent model.

## Full-overlap raw Mogi check

The daily time-series check extends each spatial comparison across the shared
Center and South deployment interval. It references both stations to their
median raw depth over the same seven pre-eruption days, fits a static elastic
Mogi pressure to each Center daily value, and predicts the held-out South
value. It uses all valid paired daily means; it does not remove tides, ocean
variability, or sensor drift and does not include viscoelastic memory.

The 1998 WC81/WC82A pair spans 309 valid days from 3 October 1997 through
7 August 1998. Its South prediction has a `0.305 m` RMSE, `+0.252 m` mean bias,
and `0.996` correlation. The Center-fit pressure ranges from `−4.939 GPa` to
`+0.077 GPa`. The 2011 NeMO pair spans 314 valid days from 5 September 2010
through 25 July 2011. Its South prediction has a `0.205 m` RMSE, `−0.150 m`
mean bias, and `0.999` correlation; Center-fit pressure ranges from
`−3.492 GPa` to `+0.112 GPa`.

The high correlations mainly reflect the shared eruption-scale step and do not
offset the residual biases or the multi-gigapascal fitted pressure changes.
These values are uncorrected raw-channel diagnostics under an assumed source
geometry, not a calibrated pressure history or eruption forecast. The target
writes aligned CSVs, JSON summaries, and the two-panel plot under ignored
`data/processed/axial_historical_bpr/`.

## Pre-1998 raw BPR check

The WC68 Center and WC69 South overlap contains 338 paired daily means from
21 July 1995 through 22 June 1996. Using the first seven shared days as the
baseline, the static Mogi fit has 0.155 m South RMSE, +0.138 m bias, and 0.876
correlation; its fitted pressure ranges from −54.8 to +260.5 MPa. The static
PyLith ellipsoid check has 0.180 m RMSE, +0.159 m bias, and 0.876 correlation;
its fitted pressure ranges from −1.151 to +5.472 MPa.

The uncorrected records retain a slow South trend that neither static fit
captures. Ocean variability, sensor drift, and the nonconverged ellipsoid mesh
limit interpretation. This interval extends temporal and spatial checking
before the 1998 eruption; it is not a corrected inflation history or a
forecast. WC67 is included in the separate deployment-context plot but not in
the two-station fits.

## Inter-eruption raw BPR checks

The NeMO 2002–04 Center record adds 729 usable daily means from 20 July 2002
through 17 July 2004. Its South spatial holdout begins on 5 September 2003,
when the NeMO 2003–05 South deployment starts; the overlap contains 317 paired
days through 17 July 2004. The daily static Mogi check has `0.235 m` South
RMSE, `+0.228 m` bias, and `0.550` correlation, with fitted pressure from
`−81.4` to `+208.0 MPa`. The PyLith ellipsoid check has `0.258 m` RMSE,
`+0.251 m` bias, and `0.550` correlation, with pressure from `−1.71` to
`+4.37 MPa`. The raw record before September 2003 has no simultaneous South
holdout.

Six primary station pairs extend the static spatial check into intervals
outside the eruption windows. The WC68/WC69 pair covers 1995–96; the MGDS pairs
cover 2002–04, 2003–05, 2005–07, 2007–09, and 2011–13. Each pair uses the first seven
shared valid days as its baseline, fits daily pressure from the Center channel,
and predicts the held-out South channel. The 2003–05 pair spans 614 paired days
from 5 September 2003 through 10 May 2005; its South RMSE is `0.134 m`, bias is
`+0.113 m`, and correlation is `0.709`. The Center-fit pressure ranges from
`−0.036` to `+0.892 GPa`.

The 2005–07 NeMO Center/South 1 pair spans 810 paired days from 12 May 2005
through 8 August 2007. The South prediction has `0.135 m` RMSE, `+0.118 m`
bias, and `0.966` correlation; Center-fit pressure ranges from `−0.085` to
`+0.414 GPa`.

The 2007–09 pair combines the 2007–10 Center deployment and the 2005–09 South 2
deployment. Their overlap contains 572 paired days from 16 August 2007 through
15 March 2009. The South prediction has `0.156 m` RMSE, `+0.136 m` bias, and
`−0.123` correlation; the fitted pressure ranges from `−0.282` to `+0.336 GPa`.
The 2011–13 Center and South pair contains 731 paired days from 31 July 2011
through 9 August 2013. Its South prediction has `0.387 m` RMSE, `+0.363 m` bias,
and `0.993` correlation; fitted pressure ranges from `−0.138` to `+1.462 GPa`.

The large residual biases and fitted pressure magnitudes show that these
uncorrected multi-year records do not calibrate a static elastic Mogi source.
The high 2011–13 correlation does not remove the bias. WC67, held out from the
WC68 Center fit over 338 paired days, has `0.015 m` RMSE, `−0.003 m` bias, and
`0.943` correlation under the static Mogi model. NeMO South 1, held out from the
2007–10 Center fit over 667 paired days through 18 June 2009, has `0.272 m`
RMSE, `+0.238 m` bias, and `−0.325` correlation. Tides, oceanographic
variability, and sensor drift remain in the raw channels, so the checks document
data coverage and model sensitivity rather than deformation histories. The
eight-panel plot, aligned CSVs, and JSON summaries remain under the ignored
`data/processed/axial_historical_bpr/` directory.

## Full-overlap PyLith ellipsoid checks

The same Center-to-South overlaps also use the 2,761-tetrahedron PyLith unit
response. Each day, the Center record sets pressure through its local vertical
compliance and the South station remains held out. The first seven shared valid
days define the reference at both stations. The 2002–04 pair has 317 days,
`0.258 m` South RMSE, `+0.251 m` bias, and `0.550` correlation; inferred
pressure ranges from `−1.71` to `+4.37 MPa`. The 2003–05 pair has 614 days,
0.257 m South RMSE, `+0.252 m` bias, and `0.709` correlation; inferred pressure
ranges from `−0.746` to `18.735 MPa`. The 2005–07 pair has 810 days, 0.166 m
RMSE, `+0.142 m` bias, and `0.966` correlation, with pressure from `−1.782`
to `8.691 MPa`. The 2007–09 pair has 572 days, 0.124 m RMSE, `+0.104 m` bias,
and `−0.123` correlation, with pressure from `−5.917` to `7.052 MPa`. The
2011–13 pair has 731 days, 0.614 m RMSE, `+0.551 m` bias, and `0.993`
correlation, with pressure from `−2.888` to `30.714 MPa`.

These static elastic predictions omit viscoelastic memory, tides, ocean
variability, and sensor drift. The high 2011–13 correlation coexists with a
large positive bias, and the 2007–09 held-out series is weakly anticorrelated.
WC67 has `0.028 m` RMSE, `+0.013 m` bias, and `0.943` correlation; the additional
NeMO South 1 overlap has `0.244 m` RMSE, `+0.211 m` bias, and `−0.325`
correlation. The mesh response is not converged, so these are spatial
diagnostics rather than calibrated pressure histories. The eight-panel
comparison figure is tracked at
`figures/historical_ellipsoid_deployment_checks.png`; aligned rows and summaries
remain under the ignored `data/processed/axial_historical_bpr/` directory.

## Three-branch generalized Maxwell event checks

The generalized Maxwell extension drives the three-branch PyLith model with a
daily pressure history inferred from each raw Center deployment, then compares
the resulting Center and held-out South uplift against paired daily records.
The 1998 WC81/WC82A pair contains 309 days from 3 October 1997 through 7 August
1998. Center RMSE is `0.186 m` with `−0.132 m` bias and `0.999` correlation;
South RMSE is `0.503 m` with `+0.329 m` bias and `0.995` correlation. The
2011 NeMO pair contains 314 days from 5 September 2010 through 25 July 2011.
Center RMSE is `0.114 m` with `−0.061 m` bias and `0.998` correlation; South
RMSE is `0.680 m` with `+0.371 m` bias and `0.997` correlation.

For each pair, the first shared daily sample defines zero displacement and
pressure is inferred from the static PyLith Center compliance. The pressure
ranges from `−94.4` to `+11.0 MPa` in 1998 and `−72.8` to `+2.9 MPa` in 2011.
The forward solve uses three synthetic branch reference viscosities
`[1.0e18, 5.0e17, 2.0e18] Pa·s` and shear fractions `[0.25, 0.25, 0.25]`,
with the steady Eq. 14/Eq. 22 temperature field and Eq. 15 viscosity scaling.
These values exercise PyLith's three-branch path; they do not specify or
calibrate the paper's missing branch spectrum.

The high correlations reflect the shared event-scale signal, while the held-out
South biases remain substantial. Daily raw channels retain tides, ocean
variability, and instrument drift; the static compliance is not mesh-converged.
This is a provisional forward diagnostic, not a calibrated hindcast or forecast.
The tracked figure is `figures/historical_generalized_maxwell_bpr_check.png`;
solver output, aligned daily records, and summaries remain under ignored
`pylith/step13_historical_generalized_maxwell_bpr/` and
`data/processed/axial_historical_bpr/` paths.

## Maxwell-kernel pressure checks across the 1998 and 2011 eruptions

The historical pressure inversion uses only the original raw NCEI WC81/WC82A
pressure channel for 1998 and the original MGDS NeMO `RawDep` Center and
`Depth` South channels for 2011. It fits each Center series through a PyLith
one-branch Maxwell ramp-response kernel and reserves its paired South record
as a spatial holdout. Daily means require the existing 75% coverage threshold;
shared valid days are linearly interpolated to a uniform weekly grid. Neither
deployment is tide-corrected, detided, filtered, or drift-corrected. The
selected MGDS fields are original instrument channels; other archive fields
remain excluded.

The 1998 WC81/WC82A pair contains 309 paired daily records from 3 October 1997
through 7 August 1998. Center RMSE is `0.093 m` with `0.998` correlation;
South holdout RMSE is `0.535 m`, bias is `+0.362 m`, and correlation is
`0.995`. Inferred pressure spans `−107.4` to `+12.0 MPa`. The 2011 NeMO pair
contains 314 paired records from 5 September 2010 through 25 July 2011. Center
RMSE is `0.125 m` with `0.992` correlation; South holdout RMSE is `0.713 m`,
bias is `+0.385 m`, and correlation is `0.991`. Inferred pressure spans
`−71.6` to `+3.6 MPa`.

For both intervals, direct PyLith histories reproduce kernel superposition to
relative L2 error below `0.13%`. The close Central fit is expected because
pressure is fit to that record. The Southern biases and large pressure
amplitudes show that this assumed one-branch model and coarse, nonconverged
mesh do not establish a physical pressure history. High correlations largely
reflect the shared eruption-scale deflation. The GCV smoothness prior and
uniform rheology remain assumptions. The comparison plot is
`figures/historical_maxwell_pressure_inversion.png`; processed records and
summaries remain local under
`data/processed/axial_historical_bpr/maxwell_pressure_inversion/`.

All twelve saved stress histories are also postprocessed at every output with a
provisional Mohr–Coulomb proxy (`1 MPa` cohesion, `25°` friction angle used
directly as `phi`, and zero pore pressure), without applying a tensile cutoff
to the shear path. A cavity-to-top path appears within 196 days of the
independently zeroed start in every interval: in 46/49 records for 1995–96,
30/46 for 2002–04, 44/44 for 1998, 83/88 for 2003–05, 71/117 for 2005–07,
68/83 for 2007–09,
30/47 for 2011, 105/106 for 2011–13, 96/102 for 2013–15, 97/98 for 2015–17,
98/106 for 2018–20, and 16/93 for 2020–22. Linear stress interpolation brackets
first path onset at day 25.38 for 2003–05, day 195.84 for 2005–07, day 67.86
for 2007–09, and day 17.61 for 2011. The path is already present in the first
saved record (day 7) for 1995–96, 1998, 2011–13, and 2015–17. The 2018–20
and 2020–22 paths first appear at 21 and 35 days.
Because the same proxy connects the cavity and surface in both eruption and
inter-eruption windows, it does not distinguish eruption timing. Synthetic
rheology, zero pore pressure, and the missing tensile cutoff make these
exploratory threshold diagnostics, not eruption predictions. Per-record
yielded-cell counts, path flags, and cavity tensile stresses are written to
ignored CSVs alongside the JSON summaries.

The written failure condition also requires tensile failure at the reservoir.
No tensile strength is specified, so each record leaves the joint-condition
flag null. Instead, each history reports maximum cavity tension at a saved
record that also has a connected shear path. These values are 6.08 MPa for
1995–96, 94.0 MPa for 1998, 32.3 MPa for 2003–05, 14.2 MPa for 2005–07,
11.0 MPa for 2007–09, 71.1 MPa for 2011, and 58.3 MPa for 2011–13. Under this
diagnostic alone, strengths in `(58.3221, 71.0951] MPa` (from unrounded output
values) would yield a saved joint-condition record in both eruption windows
and none in the ten inter-eruption windows. This conditional interval depends on
synthetic branch properties, static-compliance pressure inversion, zero pore
pressure, the direct 25° friction interpretation, raw uncorrected observations,
and an unconverged mesh; it does not estimate physical tensile strength. The
joint condition is evaluated only at saved PyLith records and is not
interpolated in time.

## Continuous raw BPR check across the 2011 eruption and follow-up

The 2011 event check now carries one generalized Maxwell state from the
September 2010 Center/South overlap through the August 2013 replacement
Center/South deployment. Both Center instruments are at the same reported
location, but their records do not overlap: the 2010–11 file ends on 26 July
2011 and the 2011–13 file begins on 31 July. The run differences each raw
Center series from its own first valid day, offsets the second pressure segment
to the first segment's terminal value, and holds that pressure constant across
the five-day gap. It does not splice or interpolate observed values through
the gap. Each South comparison keeps its deployment-specific baseline.

The check reads only MGDS IEDA/322282 original `RawDep` Center and `Depth`
South channels. It uses the same synthetic three-branch rheology and
mesh-sensitive static compliance as the historical deployment windows. Over the
314 paired event days, held-out South RMSE is `0.680 m`, bias is `+0.371 m`,
and correlation is `0.997`. The 731-day follow-up pair has `1.246 m` RMSE,
`−1.217 m` bias, and `0.991` correlation. The Center fit for the follow-up
segment has `0.043 m` RMSE. The follow-up correlation reflects a shared slow
trend despite the large South bias; it does not establish a calibrated pressure
history or post-eruption prediction.

The continuous stress history has 154 saved records at seven-day intervals.
The current Mohr–Coulomb proxy first connects the cavity and surface at about
day 17.61, while tensile strength remains unspecified. Raw ocean variability
and sensor drift, independent instrument baselines, the assumed pressure
continuity, synthetic branches, zero pore pressure, and unconverged compliance
limit interpretation. The new tracked plot is
`figures/historical_generalized_maxwell_2011_continuous_bpr_check.png`; its
processed series and summary remain ignored under
`data/processed/axial_historical_bpr/`.

## Continuous raw NCEI check across the 1998 eruption and follow-up

The WC81 Center record drives one three-branch Maxwell history from 3 October
1997 through 7 August 1998, spanning the January eruption. The raw WC82 South
archive continues through 4 May 1999 in two files with eight overlapping daily
records. Each file is first referenced to its own first valid day; the second
segment is offset by the mean uplift difference over their shared days. Their
aligned overlap RMSE is `0.000 m`, and dates are taken from the first segment
where both files report a value.

Only the NCEI original `seafloor_pressure_abs_raw [dbar]` channel is used for
WC81 and both WC82 files. WC81 provides 309 pressure records. After its final
record, inferred Center pressure is held constant through 4 May 1999, a
270-day terminal-load continuation. This runs the Maxwell state forward while
the WC82 South station remains observed; it does not infer unrecorded Center
pressure. The raw archive is [NCEI BPR DOI 10.7289/V5F18WNS](https://doi.org/10.7289/V5F18WNS).

Through the Center interval, Center RMSE is `0.186 m`; the South holdout has
`0.503 m` RMSE, `+0.329 m` bias, and `0.995` correlation. From 8 August 1998
through 4 May 1999, the separately zeroed South holdout has `0.063 m` RMSE,
`−0.050 m` bias, and `−0.369` correlation. The follow-up RMSE is small because
both the model and the short-period raw record stay near the new baseline;
negative correlation shows that this is not evidence of predictive skill.

The continuous history has 83 saved stress records at seven-day intervals on
a 2,761-tetrahedron mesh. Synthetic branch parameters, static nonconverged
compliance, a constant terminal pressure, raw ocean variability, and sensor
drift limit interpretation. No paper-associated observations, corrections,
values, figures, or model results are used. The tracked plot is
`figures/historical_generalized_maxwell_1998_continuous_bpr_check.png`; aligned
series and the run summary remain ignored under
`data/processed/axial_historical_bpr/`.

## Three-branch deployment-overlap checks

Ten additional Center/South pairs extend the same forward diagnostic from
1995 through 2022, with each interval kept separate across deployment gaps.
The new 2002–04 Center/South overlap contains 317 paired days from
5 September 2003 through 17 July 2004. The Center fit uses a static PyLith
compliance and infers pressure from `−1.40` to `+4.68 MPa`. Center residuals
have `0.030 m` RMSE, `+0.007 m` bias, and `0.734` correlation; the held-out
South residuals have `0.658 m` RMSE, `−0.655 m` bias, and `0.366` correlation.
The provisional Mohr–Coulomb path first appears between saved outputs at about
53.6 days, while the first saved path is at day 56. This threshold diagnostic
uses synthetic branch values and is not an eruption-onset estimate.
For 1995–96 WC68/WC69, South RMSE is `0.183 m`, bias is `−0.161 m`, and
correlation is `0.793`. For 2003–05, the values are `0.651 m`, `−0.649 m`, and
`0.660`. The 2005–07 NeMO Center/South 1 overlap adds 810 paired days from
2005-05-12 through 2007-08-08; South RMSE is `0.157 m`, bias is `−0.135 m`,
and correlation is `0.958`. For 2007–09 the values are `0.123 m`, `−0.101 m`,
and `−0.355`. The 2011–13 pair has `1.242 m` South RMSE and `−1.214 m` bias
despite `0.991` correlation. The 2013–15 South 2 check has `0.358 m` RMSE,
`−0.089 m` bias, and `0.991` correlation; its held-out South 1 record has
`1.096 m` RMSE. The 2015–17 South 2 check has `0.265 m` RMSE, `−0.245 m`
bias, and `0.973` correlation. In each interval, Center RMSE is smaller because Center drives
the inferred pressure; those residuals are not independent validation.

The raw 2003–05 and 2011–13 South series retain large offsets and trends that
the Center-forced model does not reproduce. The negative 2007–09 correlation
also shows that an event-scale fit does not transfer uniformly across records.
All ten runs use the same synthetic branch values and mesh-sensitive static
compliance as the eruption windows. They add temporal coverage for model
checking, but do not recover continuous inter-eruption deformation or calibrate
the branch spectrum. The tracked interval comparison is
`figures/historical_generalized_maxwell_deployment_bpr_check.png`; report-sized
1995–2009, 2011–2017, and 2018–2022 subsets are also tracked. Their gaps are
not interpolated.

The 2018–20 Center/South 2 pair has 741 paired days from 22 August 2018 through
2 September 2020. The held-out South RMSE is `0.105 m`, bias is `−0.096 m`, and
correlation is `0.787`. The 2020–22 Center/South 1 miniBPR pair has 648 paired
days from 12 September 2020 through 21 June 2022; its South RMSE is `0.043 m`,
bias is `−0.017 m`, and correlation is `0.788`. Raw variability remains in
both records, and the 100-second miniBPR samples are averaged to daily means
using their own cadence. The 2017–18 unstable Center is excluded from model
forcing. Pressure remains provisional because static compliance is
unconverged and the Maxwell branches are synthetic.

Two further original raw channels add independent spatial checks without
changing those Center-driven solves. WC67 is held out from the 1995–96 WC68
run for 338 paired days; its RMSE, bias, and correlation are `0.036 m`,
`−0.021 m`, and `0.685`. NeMO South 1 is held out from the 2007–09 Center run
for the 572 days shared with the primary overlap; its metrics are `0.221 m`,
`−0.191 m`, and `−0.506`. WC67 has smaller absolute residuals but only
moderate correlation; the second South record is anticorrelated. Both channels
are original NCEI/MGDS raw observations rather than Cabaniss-associated
derived products.
Their local prediction CSVs are included in the processed-output workflow, and
the tracked deployment figure overlays their observed and modeled series.

The 1998 event has two raw station records for a spatial observation check.
Raw NCEI records add deployment context from 1987 through 2002, while the MGDS
channels add context through 2022. The 1995–96, 2002–04, 2003–05, 2005–07,
2007–09, and 2011–13 paired Center/South intervals add spatial checks. The tracked
deployment-context plot zeroes every deployment
independently; raw tides, ocean variability, and sensor drift remain, so its
segments do not define corrected inter-eruption deformation. The event-window
comparisons are also uncorrected. The `make bpr-historical-check` target writes
event-centered, multi-year, and deployment-overlap model-check figures, daily
CSVs, event summaries, and Mogi and ellipsoid diagnostics for both eruptions
and six additional Center-to-South pairs. Daily CSVs and diagnostics remain under ignored
`data/processed/axial_historical_bpr/`. Raw downloads remain under ignored
`data/raw/axial_bpr/`.

## Supplemental raw spatial holdouts, 2015–22

The MGDS IEDA/322282 archive adds 19 other station records in three later
deployment windows. Processing reads only each instrument's original `Depth`,
`RawDep`, or `RawDepth(m)` field. The 15-second moored records and 100-second
miniBPR records are reduced to daily means using their own cadence; tide, ocean, and
instrument drift corrections are not applied. These are raw-data checks and do
not use Cabaniss et al. observations, corrections, figures, or model results.
The supplementary download selects UIDs 1109490–1109495, 2415276–2415278,
2415280, 2415282, and 2845425–2845432 from the [MGDS file
listing](https://www.marine-geo.org/tools/search/Files.php?data_set_uid=22282)
and is recorded in the local manifest with the archive checksum.

Six miniBPR holdouts share the 2015–17 Center/South 2 model window of 687 days,
28 August 2015 through 14 July 2017. Their RMSE, bias, and correlation are:
AX-302 Trevi `0.211/−0.189/0.984 m`, AX-307 Magnesia West
`0.496/−0.465/0.994 m`, AX-308 South 1 `0.280/−0.256/0.982 m` over 605
days, AX-106 Ashes `0.705/−0.666/0.993 m`, AX-303 Marker 33
`0.213/−0.190/0.942 m`, and AX-105 South Pillow Mound
`0.293/−0.255/0.544 m`. The AX-105 source filename mentions an offset, but the
analysis reads unmodified `RawDep` and applies no offset or drift correction.

The 2018–20 interval adds three miniBPR holdouts and the NeMO West Rim raw
channel. AX-307 Magnesia West, AX-302 Trevi, and AX-105 South Pillow Mound cover
310, 308, and 302 paired days, respectively; their RMSE/bias/correlation are
`0.118/−0.096/0.792 m`, `0.034/−0.016/0.778 m`, and
`0.039/+0.012/0.138 m`. West Rim covers 739 days and has
`0.346/+0.305/−0.267 m`; MGDS reports no MPR-based drift estimate, so this
remains a low-confidence raw comparison. The North record is excluded because
its archived coordinates conflict with the MGDS note locating it about 2 km
NNW of Center.

Six 2020–22 holdouts span 641–648 paired days. AX-105 South Pillow Mound has
`0.180/+0.174/0.174 m`; AX-302 Trevi, `0.031/−0.014/0.722 m`; AX-104 Bag
City, `0.047/+0.031/0.554 m`; AX-307 Magnesia West,
`0.031/−0.002/0.791 m`; BPR East, `0.132/+0.109/−0.163 m`; and BPR North,
`0.486/−0.483/0.680 m`. Drift remains unknown for the two full-size BPRs, so
their raw pressure-depth series retain it. AX-303 Marker 33 is processed for
deployment context but excluded from metrics because MGDS documents high noise
from 18 June 2021 to 12 January 2022. BPR West is likewise excluded because
MGDS attributes its strong deflationary signal to sediment-site instability.

The per-window plots are
`figures/historical_generalized_maxwell_2015_2017_bpr_check.png`,
`figures/historical_generalized_maxwell_2018_2020_bpr_check.png`, and
`figures/historical_generalized_maxwell_2020_2022_bpr_check.png`; the grouped
2018–22 figure overlays all scored stations. Each holdout and its Center
comparison use their first shared date as a separate zero. The pressure history
still comes only from the primary Center deployment. These raw spatial residuals
vary substantially by station and retain instrument drift and ocean variability;
they are diagnostics under synthetic Maxwell branches and nonconverged static
compliance, not calibrated model predictions.

## Raw 2017–18 station checks against OOI Central

Six additional MGDS deployments overlap OOI Central from 16 July 2017 through
22 August 2018. The four miniBPR records use the original `RawDepth` channel;
the NeMO North and West records use the original `Depth` channel. Each series
and the OOI Central daily uplift are zeroed on their first shared day. A static
elastic PyLith ellipsoid response scales Central uplift to each station using
the compliance at its recorded coordinates. OOI aggregate quality codes remain
in the paired daily output without filtering. The comparison applies no tide,
ocean, or instrument-drift correction and uses no data product associated with
Cabaniss et al.

| Held-out station | Paired days | Primary days | RMSE (m) | Bias (m) | Correlation |
| --- | ---: | ---: | ---: | ---: | ---: |
| AX-303 Marker 33 | 387 | 387 | 0.475 | −0.445 | 0.958 |
| AX-105 South Pillow Mound | 385 | 368 | 0.575 | −0.497 | 0.883 |
| AX-302 Trevi | 389 | 389 | 0.106 | −0.092 | 0.961 |
| AX-307 Magnesia West | 386 | 386 | 0.474 | −0.453 | 0.976 |
| NeMO North | 383 | 383 | 0.341 | −0.333 | 0.944 |
| NeMO West | 388 | 388 | 0.341 | +0.309 | −0.890 |

For AX-105, primary metrics omit 25 November–11 December 2017, when MGDS
reports repeated raw-depth offsets and unrealistic changes. The full record has
0.565 m RMSE, −0.486 m bias, and 0.879 correlation. MGDS also notes a replaced
raw sample at AX-303; its original values are retained. Estimated miniBPR drift
corrections are unavailable in the selected raw channels, while the North and
West moored BPRs have no MPR-based drift estimates. High correlations at
AX-303 and AX-307 accompany residuals near half a meter, while NeMO West moves
in the opposite direction from the model prediction. These residuals show
unresolved raw-sensor and spatial-model differences, not calibrated deformation.

The plot and daily paired output are generated by
`make historical-ooi-bpr-holdouts`. The tracked figure is
`figures/ooi_2017_2018_raw_bpr_holdouts.png`; CSV and JSON results remain under
the ignored `data/processed/axial_historical_bpr/` directory. The observations
are original IEDA/322282 channels and retain its CC BY-NC-SA 3.0 attribution and
terms.

## Pressure-calibrated four-rheology comparisons for 1998 and 2011

The four-case comparison fits each rheology to raw Center BPR uplift and checks
South as a spatial holdout for both eruption windows. The 1998 pair contains
309 daily samples from 3 October 1997 through 7 August 1998, using raw NCEI
absolute-pressure channels at WC81 Center and WC82A South. Its 44 intervals
are each 7 days. The 2011 pair contains 314 daily samples from 5 September
2010 through 25 July 2011, using raw MGDS `RawDep` at NeMO Center and `Depth`
at NeMO South. Its 46 intervals are each 7.0217 days. Each event and rheology
has an independent GCV-smoothed pressure history. Both Center fits include
eruption deflation and post-eruption BPR data, so failure-path timing is
retrospective rather than an independent eruption prediction.

In 1998, Center RMSE is 0.0925–0.0927 m across the four cases. South RMSE
ranges from 0.519 to 0.530 m, with +0.350 to +0.359 m bias and correlations
near 0.997. Fitted pressure minima range from −94.8 MPa for elasticity to
−44.4 MPa for hydrothermal Maxwell. A connected path is present at the first
saved 7-day record in all four cases, but the thermal Maxwell path does not
persist in every saved record. These records bound proxy onset at or before
the first output; they do not resolve timing relative to the 25 January
eruption.

In 2011, Center RMSE is 0.124 m and South RMSE ranges from 0.704 to 0.717 m,
with about +0.38 m bias and correlations near 0.99. Fitted pressure minima
range from −72 MPa in the elastic case to about −34 MPa in the two
temperature-dependent cases. Direct Maxwell histories reproduce the response
kernels to below 0.22% relative L2 error at both stations in both event
windows.

The provisional 2011 connected-path onset is about 35 days for elasticity, 38
days for constant-property Maxwell, and 205 days for both temperature-
dependent cases, measured from 5 September 2010. The temperature-dependent
paths first appear about eight days before the observed 6 April 2011 eruption,
but this timing is not an independent hindcast because the fitted pressure
record contains eruption deflation. The synthetic branch spectrum, Eq. 16
trend conflict, nonconverged compliance, unmodeled Winkler foundation, and
raw ocean and sensor effects keep these results diagnostic. The plots are
`figures/historical_four_case_bpr_calibration_1998.png` and
`figures/historical_four_case_bpr_calibration.png`; aligned series and case
summaries remain ignored under the matching directories in `data/processed/`.
The 1998 MGDS Fox archive duplicates the NCEI instruments and adds no station.
These raw fits use only original raw channels; the separate corrected event
workflow below uses MGDS observation-correction fields. Cabaniss model outputs
and published figure values are excluded from both workflows.

## Tide- and drift-corrected event observations

A separate event workflow applies MGDS observation corrections to the four
1998 and 2011 station records. It aggregates the archive's predicted-tide
fields and uses the combined predicted-tide/MPR-drift field where available;
it does not apply the archive's low-pass filter. The 1998 Fox Center and South
series use `SpotlDetidedDepth`, so neither has an MPR drift estimate. In 2011,
Center uses `DriftCorrSpotlDep` with tide and MPR drift correction, while South
uses `SpotlDetidedDepth` with tide correction only. All four series retain
non-tidal ocean variability. Their separate channel names and correction
components are written to the ignored processed-data summary.

The corrected inputs provide 309 paired daily samples for 1998 and 314 for
2011. Center RMSE is 0.115 m across the four rheologies in 1998 and 0.104 m in
2011. South holdout RMSE is 0.657–0.670 m in 1998, with +0.544 to +0.554 m
bias, and 0.719–0.731 m in 2011, with +0.401 to +0.409 m bias. Each pressure
history is fitted separately to Center, and both fits include the eruption
deflation and later observations. These are retrospective model checks, not
independent eruption predictions. The large South residuals persist after the
archive corrections and expose a spatial mismatch in this coarse model.

The corrected runs retain the 2,761-tetrahedron nonconverged mesh, synthetic
Maxwell branches, assumed thermal boundaries, provisional failure parameters,
and fixed-base/lateral-roller boundaries without the written Winkler
foundation. Corrected pressure amplitudes therefore remain diagnostic. Run
`make historical-four-case-corrected-bpr-calibration` to regenerate both
figures from MGDS IEDA/322344 for 1998 and IEDA/322282 for 2011. MGDS
distributes these records under CC BY-NC-SA 3.0. No Cabaniss model outputs,
paper-reported outcomes, or publication figure values enter the workflow.
