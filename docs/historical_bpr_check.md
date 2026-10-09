# Historical raw BPR checks

Raw Axial bottom-pressure records add independent event observations where the
Ocean Observatories Initiative (OOI) record does not reach. The 1997–98 WC81
and WC82A records span the January 1998 eruption, and the NeMO Center and South
records span April 2011. These observations extend cross-checking without
importing paper-associated pressure histories or corrections.

## Source selection

The National Centers for Environmental Information (NCEI) archives WC81,
WC82A, and WC82B as 15-second raw absolute pressure in dbar. The archive also
contains two center deployments from 2000–02, which extend post-1998 temporal
context without spanning another eruption. WC81 and the 2000–02 instruments
were at the caldera center; WC82A was south of the center. Processing converts
each pressure anomaly to vertical displacement with a hydrostatic
approximation, using seawater density `1025 kg/m³` and gravity `9.80665 m/s²`.
The Marine Geoscience Data System (MGDS) archive for IEDA/322282 contains original and
derived columns together. The check reads only `Depth` from the 2009–11 South
file and `RawDep` from the 2010–11 Center file. It does not read detided,
low-pass-filtered, or drift-corrected channels.

The MGDS record includes Cabaniss et al. among its related publications. The
selected fields are instrument pressure channels collected during 2009–11 and
converted to depth by the archive; no data product, correction, numerical
result, or figure created for that paper enters this analysis. MGDS requires
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

The 1998 event has two raw station records for a spatial observation check.
The 2000–02 NCEI records extend the timeline after the 1998 event, and the raw
2011 channels span the second event. The multi-year context plot zeroes every
deployment independently; raw tides, ocean variability, and sensor drift
remain, so its segments do not define corrected inter-eruption deformation.
The event-window comparisons are also uncorrected. The
`make bpr-historical-check` target writes event-centered and multi-year figures,
daily CSVs, the event summary, and Mogi and ellipsoid diagnostics for both
Center-to-South pairs under ignored
`data/processed/axial_historical_bpr/`. Raw downloads remain under ignored
`data/raw/axial_bpr/`.
