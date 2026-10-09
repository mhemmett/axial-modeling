# Reproduction checkpoint

`make reproduce` rebuilds the currently implemented numerical checks, four
OOI-only figures, and the compiled progress report from independent Ocean
Observatories Initiative (OOI) bottom-pressure records. It is a bounded
checkpoint for the available components; it does not run a complete coupled
model or reproduce the manuscript's eruption forecasts.

The target creates the repository Conda environment and extracts PyLith 5.0.2
when they are absent. A fresh checkout therefore needs Conda, the local PyLith
5.0.2 archive and checksum file described in the installation instructions,
and `latexmk`. The run fetches only OOI `BOTSFLU-DAYDEPTH` records for Central
and Eastern Caldera. It retains the OOI aggregate quality code and writes raw
downloads and processed series under ignored `data/raw/` and
`data/processed/` paths.

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

The workflow runs each implemented component check: elastic and Maxwell
restart cases, thermal-to-material transfer, steady thermal fields, the
ellipsoid Maxwell smoke cases, two-year failure progression, and
temperature/property variants, the Mogi benchmark, synthetic failure
progression, ellipsoid mesh sensitivity, both OOI pressure-history cases, and
the OOI plotting scripts. It then runs the Python test suite, Ruff, and the
report build. PyLith outputs and processed data remain local. The generated
PNG and PDF figures and the report PDF are tracked project artifacts. The
command reports its Git revision and elapsed runtime; append those values and
the resulting validation summary to [`run_log.md`](run_log.md) when recording
a release run.

The OOI-driven Maxwell calculation remains one-way, uses a single assumed
Maxwell branch, and inherits the nonconverged ellipsoid compliance. The written
thermal equation specifies zero heat production and no mechanical feedback.
Until the governing return-coupling law and missing source parameters are
resolved, this procedure must not be described as a complete reproduction.
