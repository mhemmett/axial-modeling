# Historical raw BPR checks

Raw Axial bottom-pressure records add independent observations where the Ocean
Observatories Initiative (OOI) record does not reach. Ten NCEI deployments
extend the raw history to 1987, and a three-station overlap in 1995–96 adds a
pre-eruption spatial check. The 1997–98 WC81 and WC82A records span the January
1998 eruption, and the NeMO Center and South records span April 2011. Additional
Center and South deployments extend the raw time series through 2013. The
analysis does not use paper-produced pressure histories or corrections.

## Source selection

The National Centers for Environmental Information (NCEI) archives ten raw
Axial deployments from 1987–96 as absolute pressure in dbar. WC09–WC32 (1987–92)
have 56.25-second sampling; WC51–WC69 (1993–96) have 15-second sampling. Raw
file headers provide deployment dates and coordinates. WC67, WC68, and WC69
overlap from 21 July 1995 through 22 June 1996; WC68 is used as the Center and
WC69 as the South holdout. The archive also contains WC81, WC82A, and WC82B
from 1997–99, plus two center deployments from 2000–02. Those later NCEI
records use 15-second raw absolute pressure. WC81 and the 2000–02 instruments
were at the caldera center; WC82A was south of the center. The MGDS archive
supplies additional raw Center and South channels for deployments between 2003
and 2013. Its archive files combine original fields with derived fields; the
processor reads only the specified original `Depth` or `RawDep` column. It
excludes detided, filtered, and drift-corrected columns. The selected MGDS data
UIDs are 896874–896884. UID 896872 duplicates NCEI coverage, and UID 896873
contains no uncorrected raw-depth field; both are omitted. Processing converts
each pressure anomaly to vertical displacement with a hydrostatic
approximation, using seawater density `1025 kg/m³` and gravity `9.80665 m/s²`.
The Marine Geoscience Data System (MGDS) archive for IEDA/322282 contains
original and derived columns together. The check reads only `Depth` or `RawDep`
from each selected 2003–13 deployment. It does not read detided,
low-pass-filtered, or drift-corrected channels.

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

Four station pairs extend the static spatial check into intervals outside the
eruption windows. The WC68/WC69 pair covers 1995–96; the other three pairs use
the 2003–05, 2007–09, and 2011–13 MGDS deployments. Each pair uses the first seven shared valid days
as its baseline, fits daily pressure from the Center channel, and predicts the
held-out South channel. The 2003–05 pair spans 614 paired days from 5 September
2003 through 10 May 2005; its South RMSE is `0.134 m`, bias is `+0.113 m`, and
correlation is `0.709`. The Center-fit pressure ranges from `−0.036` to
`+0.892 GPa`.

The 2007–09 pair combines the 2007–10 Center deployment and the 2005–09 South 2
deployment. Their overlap contains 572 paired days from 16 August 2007 through
15 March 2009. The South prediction has `0.156 m` RMSE, `+0.136 m` bias, and
`−0.123` correlation; the fitted pressure ranges from `−0.282` to `+0.336 GPa`.
The 2011–13 Center and South pair contains 731 paired days from 31 July 2011
through 9 August 2013. Its South prediction has `0.387 m` RMSE, `+0.363 m` bias,
and `0.993` correlation; fitted pressure ranges from `−0.138` to `+1.462 GPa`.

The large residual biases and fitted pressure magnitudes show that these
uncorrected multi-year records do not calibrate a static elastic Mogi source.
The high 2011–13 correlation does not remove the bias. Tides, oceanographic
variability, and sensor drift remain in the raw channels, so the checks document
data coverage and model sensitivity rather than deformation histories. The
three-panel plot, aligned CSVs, and JSON summaries remain under the ignored
`data/processed/axial_historical_bpr/` directory.

## Full-overlap PyLith ellipsoid checks

The same Center-to-South overlaps also use the 2,761-tetrahedron PyLith unit
response. Each day, the Center record sets pressure through its local vertical
compliance and the South station remains held out. The first seven shared valid
days define the reference at both stations. The 2003–05 pair has 614 days,
0.257 m South RMSE, `+0.252 m` bias, and `0.709` correlation; inferred pressure
ranges from `−0.746` to `18.735 MPa`. The 2007–09 pair has 572 days, 0.124 m
RMSE, `+0.104 m` bias, and `−0.123` correlation, with pressure from `−5.917`
to `7.052 MPa`. The 2011–13 pair has 731 days, 0.614 m RMSE, `+0.551 m` bias,
and `0.993` correlation, with pressure from `−2.888` to `30.714 MPa`.

These static elastic predictions omit viscoelastic memory, tides, ocean
variability, and sensor drift. The high 2011–13 correlation coexists with a
large positive bias, and the 2007–09 held-out series is weakly anticorrelated.
The mesh response is not converged, so these are spatial diagnostics rather than
calibrated pressure histories. The comparison figure is tracked at
`figures/historical_ellipsoid_deployment_checks.png`; aligned rows and summaries
remain under the ignored `data/processed/axial_historical_bpr/` directory.

The 1998 event has two raw station records for a spatial observation check.
Raw NCEI records add deployment context from 1987 through 2002, while the MGDS
channels add context from 2003 through 2013. The 1995–96, 2003–05, 2007–09, and
2011–13 paired Center/South intervals add static spatial checks. The tracked
deployment-context plot zeroes every deployment
independently; raw tides, ocean variability, and sensor drift remain, so its
segments do not define corrected inter-eruption deformation. The event-window
comparisons are also uncorrected. The `make bpr-historical-check` target writes
event-centered, multi-year, and deployment-overlap model-check figures, daily
CSVs, event summaries, and Mogi and ellipsoid diagnostics for both eruptions
and the four additional Center-to-South pairs. Daily CSVs and diagnostics remain under ignored
`data/processed/axial_historical_bpr/`. Raw downloads remain under ignored
`data/raw/axial_bpr/`.
