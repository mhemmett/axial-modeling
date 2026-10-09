# Reproduction checkpoint

`make reproduce` rebuilds the currently implemented numerical checks, model
setup schematic, thermal property slices, OOI and historical BPR figures, and
the compiled progress report. It is a bounded checkpoint for the available
components. It also runs a shared-load smoke matrix for the four written
rheology configurations and four-case raw BPR calibrations for the 1998 and
2011 event windows. A continuous eruption-cycle calibration remains open.

The target creates the repository Conda environment and extracts PyLith 5.0.2
when they are absent. A fresh checkout therefore needs Conda, the local PyLith
5.0.2 archive and checksum file described in the installation instructions,
and `latexmk`. The run fetches OOI `BOTSFLU-DAYDEPTH` records for Central and
Eastern Caldera, original NCEI BPR records from 1987–2002, and MGDS records
from 2002–22. These raw records add intermittent coverage across the 1998 and
2011 events, deployment overlaps through 2022, and a pre-1998 spatial
comparison. MGDS retrieval accepts its research-use terms. Processing reads
original `Depth`, `RawDep`, `RawDepth`, and `RawDepth(m)` pressure channels, plus
the NeMO 2002–04 `DriftCorrRawDep` field whose documented zero correction leaves it
unchanged. It excludes detided, filtered, and paper-produced values. The
unstable 2017–18 Center channel appears in raw context only and does not drive a
model check. Six other MGDS stations from 2017–18 are compared with OOI Central
through a static ellipsoid response as uncorrected spatial holdouts. The
workflow retains the OOI aggregate quality code and writes raw downloads and
processed series under ignored `data/raw/` and `data/processed/` paths. Run
`make historical-ooi-bpr-holdouts` to rebuild their plot and daily diagnostics.

From the repository root, run:

```sh
make reproduce
```

By default, the observation request starts on 2014-01-01 and ends on the
current UTC date. The 9 October 2026 checkpoint requested data through that
date and received complete daily observations through 30 September. Pass a
fixed end date to repeat a historical request:

```sh
make reproduce OOI_END_DATE=2026-10-09
```

The fetch manifest records request URLs, retrieval time, row counts, and
uncompressed-response checksums. OOI may revise its archive, so matching date
ranges alone do not guarantee identical input bytes; compare the recorded
checksums when reproducing an earlier run.

The workflow runs each implemented component check: elastic and Maxwell
restart cases, same-mesh and physical cross-mesh thermal-to-material transfer,
steady thermal fields, a three-mesh hydrothermal sensitivity check, and the
hydrothermal property slice, ellipsoid Maxwell smoke cases, a synthetic
three-branch generalized Maxwell check, and a four-case common-load solver
matrix. The matrix checks elastic, generalized
Maxwell, temperature-dependent Maxwell, and hydrothermal temperature-dependent
Maxwell runs over a shared 2,761-tetrahedron mesh and two-year constant 1 MPa
load. Its three Maxwell stress histories are independently reconstructed from
PyLith strain and material fields. The synthetic branch properties and the
printed Eq. 16 modulus law are diagnostics; this matrix does not fit BPR
pressure or eruption thresholds. See
[`step14_rheology_case_matrix/README.md`](../pylith/step14_rheology_case_matrix/README.md)
for assumptions and results. `make historical-four-case-bpr-calibration`
also fits all four cases independently to the original raw 1998 WC81 and 2011
NeMO Center channels, holds WC82A and NeMO South out, and analyzes saved
failure states. Both bounded windows include observed eruption deflation in
the Center fit, so their path histories are not independent timing
predictions. See
[`step15_historical_four_case_bpr/README.md`](../pylith/step15_historical_four_case_bpr/README.md)
for assumptions and results. The remaining checks include two-year failure
progression, temperature/property variants, the Mogi benchmark and
domain sensitivity, synthetic failure progression,
ellipsoid mesh sensitivity, OOI pressure-history cases, a Central-fitted
Maxwell-kernel pressure inversion with an Eastern holdout, raw historical 1998
and 2011 Maxwell-kernel inversions with South holdouts, historical 1998 and
2011 static and three-branch generalized Maxwell BPR checks, and Center/South
deployment checks through 2022. The 2013–15 window includes an extra South 1
holdout. It also generates the model
setup schematic and transfers a solved hydrothermal field into a bounded
PyLith Maxwell solve. Historical deployment checks use the same static PyLith
ellipsoid unit response for Center-fit and South-held-out daily comparisons.
The sequence carries synthetic three-branch states from the 1998 and 2011 event
windows into subsequent raw deployment records through May 1999 and August 2013.
A 270-day terminal-pressure hold extends the 1998 Center record; a five-day
constant-pressure hold bridges the 2011 Center deployments. These assumed holds
make the follow-up comparisons diagnostic rather than a calibrated continuous
eruption-cycle reconstruction.
The three-branch diagnostic covers 1998 and 2011 event windows plus ten paired
deployment intervals from 1995 through 2022, preserving gaps between records.
The reproduction sequence also runs the static raw NCEI BPR check for ten
1987–1996 deployments. Its three overlap holdouts extend the pre-eruption
spatial comparison, while single-station fits remain calibration only and do
not form a continuous or pressure-calibrated history.
The workflow also compares the original 1997–98 Fox `Depth` archive against
the matching NCEI raw-pressure records, without including processed channel
products.
The workflow then runs the Python test suite, Ruff, and the report build. PyLith
outputs and processed data remain local. The generated PNG and PDF figures and
the report PDF are tracked project artifacts. The command reports its Git
revision and elapsed runtime; append those values and the resulting validation
summary to [`run_log.md`](run_log.md) when recording a release run.

The thermal mesh check runs Eq. 14 with Eq. 22 conductivity on three
independently generated ellipsoid meshes capped below 3,500 tetrahedra. It
compares a finite set of common host-rock probes and does not establish spatial
convergence; see [`thermal_mesh_sensitivity.md`](thermal_mesh_sensitivity.md)
for the configuration and interpretation.

The OOI-driven Maxwell calculations use one assumed Maxwell branch. The kernel
inversion fits Central uplift, but pressure scale and spatial prediction
remain provisional because its smoothness prior, material properties, and
ellipsoid mesh are assumptions. The written thermal equation specifies zero
heat production and no mechanical feedback. The two-event four-case
comparison now evaluates raw pressure fits and saved failure states, but
mesh-converged compliance and missing source parameters remain unresolved.
Synthetic branch spectra, large fitted pressure excursions, post-eruption
fits, and the nonconverged mesh do not evaluate the reported continuous
failure progression. The project still lacks calibrated material parameters
and a continuous pressure history through either eruption cycle.
Until the governing return-coupling law and missing source parameters are
resolved, this procedure must not be described as a complete reproduction.
