# Historical raw BPR checks

Raw Axial bottom-pressure records add independent observations where the Ocean
Observatories Initiative (OOI) record does not reach. The 1997–98 WC81 and
WC82A records span the January 1998 eruption, and the NeMO Center and South
records span April 2011. Additional Center and South deployments extend the
raw time series through 2013 and provide spatial checks during 2003–05, 2007–09,
and 2011–13. The analysis does not use paper-produced pressure histories or
corrections.

## Source selection

The National Centers for Environmental Information (NCEI) archives WC81,
WC82A, and WC82B as 15-second raw absolute pressure in dbar. The archive also
contains two center deployments from 2000–02, which extend post-1998 temporal
context without spanning another eruption. WC81 and the 2000–02 instruments
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

The processor averages 15-second raw measurements by UTC day and requires at
least 75% of the 5,760 expected daily samples. For each event, it references
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

## Inter-eruption raw BPR checks

Three additional station pairs extend the static spatial check into intervals
outside the eruption windows. Each pair uses the first seven shared valid days
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

The 1998 event has two raw station records for a spatial observation check.
The 2000–13 NCEI and MGDS records extend the raw deployment context between
eruptions; paired Center and South channels add spatial checks in 2003–05,
2007–09, and 2011–13. The multi-year context plot zeroes every deployment
independently; raw tides, ocean variability, and sensor drift remain, so its
segments do not define corrected inter-eruption deformation. The event-window
comparisons are also uncorrected. The `make bpr-historical-check` target writes
event-centered, multi-year, and deployment-overlap model-check figures, daily
CSVs, event summaries, and Mogi and ellipsoid diagnostics for both eruptions
and the three additional Center-to-South pairs under ignored
`data/processed/axial_historical_bpr/`. Raw downloads remain under ignored
`data/raw/axial_bpr/`.
