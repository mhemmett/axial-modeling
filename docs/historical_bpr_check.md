# Historical raw BPR checks

Raw Axial bottom-pressure records add independent event observations where the
Ocean Observatories Initiative (OOI) record does not reach. The 1997–98 WC81
and WC82A records span the January 1998 eruption, and the NeMO Center and South
records span April 2011. These observations extend cross-checking without
importing paper-associated pressure histories or corrections.

## Source selection

The National Centers for Environmental Information (NCEI) archives WC81,
WC82A, and WC82B as 15-second raw absolute pressure in dbar. WC81 is at the
caldera center; WC82A is south of the center. Processing converts each pressure
anomaly to vertical displacement with a hydrostatic approximation, using
seawater density `1025 kg/m³` and gravity `9.80665 m/s²`. The Marine
Geoscience Data System (MGDS) archive for IEDA/322282 contains original and
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

The 2011 Center change calibrates two static elastic spatial checks, with South
held out. The written spherical Mogi benchmark (`a = 0.7 km`, `d = 4 km`,
`E = 60 GPa`, assumed `ν = 0.25`) predicts `−1.406 m` at South, a residual of
`−0.381 m`. Its fitted pressure change is `−3.43 GPa`, which shows that this
small-source benchmark cannot represent the observed eruption-scale motion at
these assumptions.

The 2,761-tetrahedron PyLith ellipsoid unit response fits Center with
`−71.97 MPa` and predicts `−0.356 m` at South, leaving a `−1.431 m` residual.
This is a substantial spatial mismatch for the current static setup. The
ellipsoid mesh is not converged, the check omits viscoelastic memory, and the
raw daily means retain ocean and instrument effects. It does not establish a
failure of the full temperature-dependent model.

The 1998 event now has two raw station records for a spatial observation check.
The event-window comparison is not a corrected deformation estimate, and the
current elastic model diagnostics still use the 2011 Center-to-South pair. The
`make bpr-historical-check` target writes the event-centered figure, daily
CSVs, event summary, and model diagnostics under ignored
`data/processed/axial_historical_bpr/`. Raw downloads remain under ignored
`data/raw/axial_bpr/`.
