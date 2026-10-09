# Reproduction checkpoint

`make reproduce` rebuilds the currently implemented numerical checks, OOI and
historical BPR figures, and the compiled progress report. It fetches independent
Ocean Observatories Initiative (OOI) records and authorized original raw BPR
channels from earlier Axial deployments. It is a bounded checkpoint for the
available components; it does not run a complete coupled model or reproduce
the manuscript's eruption forecasts.

The target creates the repository Conda environment and extracts PyLith 5.0.2
when they are absent. A fresh checkout therefore needs Conda, the local PyLith
5.0.2 archive and checksum file described in the installation instructions,
and `latexmk`. The run fetches OOI `BOTSFLU-DAYDEPTH` records for Central and
Eastern Caldera, NCEI raw absolute-pressure records, and an MGDS archive for
the 2011 Center and South deployments. Historical processing reads the NCEI
`seafloor_pressure_abs_raw` channel and the original MGDS `RawDep` and `Depth`
channels; it excludes detided, filtered, drift-corrected, and paper-produced
data products.
The run retains the OOI aggregate quality code and writes raw downloads and
processed series under ignored `data/raw/` and `data/processed/` paths.

From the repository root, run:

```sh
make reproduce
```

By default, the observation request starts on 2014-01-01 and ends on the
current UTC date. Pass a fixed end date to repeat a historical request:

```sh
make reproduce OOI_END_DATE=2026-10-08
```

The fetch manifest records request URLs, retrieval time, row counts, and
uncompressed-response checksums. OOI may revise its archive, so matching date
ranges alone do not guarantee identical input bytes; compare the recorded
checksums when reproducing an earlier run.

The workflow runs the elastic and Maxwell restart cases, thermal-to-material
transfer, steady thermal fields, ellipsoid Maxwell smoke cases, two-year
failure progression, temperature/property variants, the Mogi benchmark,
synthetic failure progression, mesh sensitivity, OOI pressure-history cases,
and OOI plotting scripts. It also runs a temperature-dependent three-branch
Maxwell smoke test, rebuilds the hydrothermal field, transfers it into a
bounded PyLith solve, and checks raw BPR event changes and spatial responses
for 1998 and 2011. The workflow then runs the Python test suite, Ruff, and the
report build. PyLith outputs, processed data, and historical event figures
remain local. The OOI PNG and PDF figures and report PDF are tracked project
artifacts. The command reports its Git revision and elapsed runtime; append
those values and the resulting validation summary to
[`run_log.md`](run_log.md) when recording a release run.

The OOI-driven Maxwell calculation remains one-way, uses a single assumed
Maxwell branch, and inherits the nonconverged ellipsoid compliance. The
three-branch smoke uses synthetic branch fractions and reference viscosities,
with a fixed steady temperature field. The written thermal equation specifies
zero heat production and no mechanical feedback. Until the governing
return-coupling law and missing source parameters are resolved, this procedure
must not be described as a complete reproduction.
