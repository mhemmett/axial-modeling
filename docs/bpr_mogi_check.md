# OOI-constrained elastic Mogi check

The Central Caldera daily uplift record can set a time-varying pressure change
for the written spherical-source Mogi benchmark, while the Eastern Caldera
record checks that source's spatial prediction. This is an elastic diagnostic
for the authorized 2014–present OOI interval; it does not reproduce the target
viscoelastic reservoir model.

For source radius `a`, depth `d`, horizontal range `r`, and pressure change
`ΔP`, the implementation uses the written Mogi relation

`u_z = ΔP a³ c d / (r² + d²)^(3/2)`,

where `c = (3K + 4G) / (2G(3K + G))`. It derives `G` and `K` from the written
analytical benchmark's `E = 60 GPa` and an explicit `ν = 0.25` assumption. The
benchmark lists a 0.7 km source radius and 4 km depth; it does not state
Poisson's ratio.

The source axis is assumed to lie at the Central BPR location. OOI dataset
metadata report Central at `45.954850° N, 130.008772° W` and Eastern at
`45.939888° N, 129.974113° W`. The code projects those nearby coordinates to a
local east–north plane, giving Eastern one horizontal offset from the assumed
source axis. The coordinates come from the official [Central](https://erddap.dataexplorer.oceanobservatories.org/erddap/tabledap/ooi-rs03ccal-mj03f-05-botpta301.html)
and [Eastern](https://erddap.dataexplorer.oceanobservatories.org/erddap/tabledap/ooi-rs03ecal-mj03e-06-botpta302.html)
OOI ERDDAP records.

Each processed series is re-referenced to the first common finite daily sample.
At each common date, the code inverts Central uplift for `ΔP` and predicts
Eastern uplift from that same pressure. Thus the Central curve is a calibration
fit by construction; Eastern is the held-out spatial check. Quality flags are
retained but not filtered because the available daily records report code 2,
`NOT_EVALUATED`.

Run `make bpr-mogi-check` after fetching and processing both authorized OOI
series. The command writes a PNG and PDF under `figures/` and local CSV and JSON
diagnostics under ignored `data/processed/`. It uses no paper-supplied
observations, published figure values, or author outputs.

The pressure history is an instantaneous elastic Mogi proxy with a point-source
geometry, a Central-centered location assumption, and a chosen Poisson's ratio.
It contains no Maxwell relaxation, temperature-dependent properties, or
ellipsoidal-reservoir response. A mismatch at Eastern therefore tests this
limited spatial model, not the full Axial Seamount stress-threshold method.
