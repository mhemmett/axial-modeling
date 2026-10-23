# Axial Seamount BPR-to-stress modeling

Use Center bottom-pressure data and PyLith to evaluate an Axial failure threshold.

[![CI](https://github.com/mhemmett/axial-modeling/actions/workflows/ci.yml/badge.svg)](https://github.com/mhemmett/axial-modeling/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Axial Seamount's deformation history can constrain subsurface loading, but the
stress conditions that trigger eruptions remain uncertain.
Cabaniss et al. (2020) modeled 22 years of seafloor deformation with
three-dimensional finite elements to examine pressure-driven failure in the
host rock ([paper](https://doi.org/10.1038/s41598-020-67043-0)). This repository replaces
the paper's COMSOL model with PyLith and makes each equation, parameter,
assumption, numerical output, and postprocessed failure criterion inspectable.
The project follows the paper's method and documents assumptions where inputs
are missing or contradictory. The paper and supplement provide model
specifications and numerical comparison targets;
author code, COMSOL files, and model fields are not used. Historical Center BPR
records drive the current event-window diagnostics and a deployment-aware
2011–2015 pressure fit. A gravity-equilibrated elastic stress screen reports
a conditional threshold; a converged threshold remains to be calculated. The reported
12–14 MPa temperature-dependent eruption overpressure is a target, not a fit
constraint. See the [method reconstruction](docs/method_reconstruction.md),
[plan](ROADMAP.md), and [panel comparison record](docs/figure_reproduction.md).

## Installation

The server's active workflow is native Linux: PyLith 5.0.2 is extracted from the
provided x86_64 binary tarball into `pylith/`, and the project environment lives
at `envs/axial-modeling`. The environment specification includes Python 3.12,
the Gmsh 4.15.2 Python API, tmux, NumPy, SciPy, h5py, PyMuPDF, PyYAML, pytest,
and Ruff. PyLith uses
its bundled Python and libraries; do not build PyLith or PETSc from source.

```bash
make env
make install-pylith
source scripts/activate.sh
make pylith-version
```

The local tarball checksum is recorded in `pylith/SHA256SUMS`. PyLith publishes
its Linux binaries on the [official downloads page](https://geodynamics.org/resources/pylith/supportingdocs/);
installation instructions are in the
[PyLith 5.0.2 manual](https://pylith.readthedocs.io/en/v5.0.2/user/install/index.html).
On this server the provided Gmsh library also needs `libGLU.so.1`; the Conda
environment installs the user-space Gmsh dependencies.

## Quick start

Generate the coarse cavity mesh, run the one-step 10 MPa PyLith solve, and
validate positive surface uplift and HDF5 stress output:

```bash
make smoke
```

The generator writes `pylith/step00_elastic_cavity/mesh/axial_box.msh`. PyLith
writes displacement and stress files under
`pylith/step00_elastic_cavity/output/`. The smoke script wraps the solve in
`timeout 300` and checks that peak uplift falls between 0.01 m and 10 m. Its
output records the measured runtime and uplift.

## Resource limits

Run model computations through the Make targets. Each recipe inherits at
most eight logical CPUs, one thread per numerical library, and a 4 GiB
address-space limit per process. Recipes run serially. A watchdog samples
process-tree resident memory and host memory every 0.2 s and stops its command
if either reaches 60% of host RAM. Host use is measured as total minus
available memory. Local resource records are written under `data/processed/`.
The sampling interval is recorded; the watchdog is not a kernel aggregate
memory limit. PyLith solves remain bounded by `timeout 300`.

## Reconstruct Center pressure

Run `make paper-bpr-fetch` to inspect the missing-file source request. After
obtaining the cited archives, run `make paper-bpr`, `make
ellipsoid-unit-response`, and `make method-reconstruction`. The last target
saves a conditional 2011–2015 elastic pressure history and observation
residuals under `data/processed/method_reconstruction_2011_2015/`. It does not
yield a stress-failure threshold. See the [method record](docs/method_reconstruction.md)
for the baseline, gap sensitivity, and limits. `make reproduction-status`
reports the stricter exact-paper requirements; `make reproduce` stops on those
unresolved requirements. The [source audit](docs/source_audit.md) compares
published specifications with the current implementation.

Run `make method-failure-screen` to refit pressure on the gravity-equilibrated
PyLith mesh and evaluate tensile plus connected Mohr–Coulomb failure. The
result under `data/processed/method_failure_screen_2011_2015/` is a conditional
elastic screen because the cavity mesh, viscoelastic memory, and datum gaps
remain unresolved.
Run `make method-mesh-refinement` to repeat the elastic screen on three finer
cavity meshes. The [method record](docs/method_reconstruction.md#elastic-mesh-refinement)
reports the pressure and failure-path changes; the finest result is still a
conditional estimate.

Run `make method-source-maxwell` after mesh refinement to write the
source-value temperature-dependent and hydrothermal Maxwell maps and measure
their short-window time-step sensitivity. Run `make method-source-bpr-failure`
to fit each case's PyLith surface response to the Center BPR record, then
`make method-source-threshold` to scan its final fitted stress state. The
[thermal method record](docs/method_reconstruction.md#source-value-thermal-maxwell-cases)
reports the numerical results and unresolved modulus, Maxwell-spectrum, and
time-integration limits. A uniform-viscosity case requires an explicit
`--uniform-viscosity-pa-s` argument to the Python scripts because the paper
does not supply that value.

Start an interactive terminal that retains the project environment with:

```bash
make tmux
```

The named tmux session is `axial-modeling`; detach with `Ctrl-b`, then `d`.
To run development checks, use `make test` and `make lint`.

## Figure 1 map

Print the authorized source URLs with `make figure1-sources`. Fetch the MGDS records with
`python data/fetch_figure1_sources.py --download --accept-mgds-terms`; raw files remain
local and ignored.

Run `make figure1-map` to write the regional map in PNG and PDF formats. The MMR/SMR
traces are project-derived velocity proxies, not official migrated outlines. Source records
and method are documented in `data/README.md` and `docs/figure_reproduction.md`.

Run `make winkler-scale` to reproduce the basal spring unit conversion and compare its
stiffness with the project-directed elastic scale. It reports the Cabaniss
supplement's very stiff spring benchmark, the regional Juan de Fuca finite
Galgana coefficient, and the layered lithostatic reference traction.

Run `make winkler-foundation-check` to compare a fixed base with an iterated
elastic Winkler boundary on the same mesh using a regional finite-spring
prior. The command writes a JSON summary under `data/processed/` and PyLith
fields under `pylith/step16_winkler_foundation/output/`. It initializes gravity,
a linear lithostatic reference stress, hydrostatic cavity pressure, and the
288.414 MPa basal prestress before applying pressure or tectonic increments.
The density is homogenized to 2,940 kg/m³ to preserve the integrated load from
6 km of 2,700 kg/m³ crust over 4 km of 3,300 kg/m³ mantle; the intermediate
depth profile is approximate. The 32,373 Pa/m spring coefficient and column
densities are regional priors, not Axial measurements. Mesh convergence
remains open.

## Methods

The target study treats the magma reservoir as a pressurized ellipsoidal void
measuring 6 km × 3 km × 1 km, centered 1.6 km below the seafloor. It calibrates
pressure against BPR uplift and compares non-temperature-dependent elastic and
viscoelastic hosts with two temperature-dependent viscoelastic models. The
fourth configuration represents hydrothermal circulation as greater thermal
conductivity in the brittle crust. See [the written model specification](docs/model_specification.md),
[structured paper summary](docs/paper_summary.md), and
[parameter provenance](docs/parameters.yaml) and
[iteration priors and convergence standard](docs/iteration_parameters.md).

The current model uses a project-directed 50 km × 50 km domain from seafloor to
10 km depth. Coordinates are x east, y north, and z up. Both ellipsoid mesh
generators orient the 6 km major axis N30°W with no dip. The current thermal
mechanics map decreases Young's modulus linearly from 50 GPa at 0 °C to
20 GPa at 1200 °C; the target table instead lists 25 GPa for the ductile
modulus, and its printed temperature function remains inconsistent with that
description. Reservoir pressure is applied as traction on the cavity boundary;
a separate fluid mesh is not used.


The paper defines a model as eruptible at first tensile failure along the
reservoir boundary; it defines eruption when that failure coincides with a
through-going Mohr–Coulomb path to the surface. The project calculates these
criteria from model stress as provisional indicators. The paper's verification
uses analytical and finite-element compatibility checks but defines no
numerical error threshold. BPR residuals are model-performance diagnostics,
not the convergence test; a stable model may retain imperfect BPR alignment.
The written thermal
method solves a steady temperature field and uses it to set mechanical
properties; it specifies no mechanics-to-heat feedback term. The retained
prototype code uses short 1998 and 2011 Center deployment windows. The paper
hindcasts the 2011 and 2015 eruptions over the preceding inflation cycles.
That cycle calculation remains incomplete. PyLith capabilities and open
design questions are recorded in
[COMSOL to PyLith](docs/comsol_to_pylith.md).

## Inputs and outputs

The [data notes](data/README.md) document the NCEI and MGDS historical BPR
archives and processing. Run `python data/fetch_historical_bpr.py --download
--accept-mgds-terms` to retrieve the authorized source records. Only Center
records enter the current pressure calibrations. Raw files and processed
observations remain local and untracked. Published numerical results are
comparison targets; model calibration uses Center BPR observations.

PyLith writes HDF5 solution fields and material fields, with displacement in
`vertex_fields/displacement` and Cauchy stress in `cell_fields/cauchy_stress`.
`axialstress.io` reads these arrays, and the smoke check uses the top-boundary
vertical displacement as its uplift measure. Positive uplift within 0.01–10 m
is a coarse-model sanity check rather than a paper fit.

## Repository layout

- `docs/` — paper extraction, parameter sources, model mapping, decisions,
  unresolved issues, and the panel reproduction record.
- `data/` — historical BPR retrieval, local observation processing, and provenance.
- `meshing/` — Gmsh box-with-ellipsoid generator.
- `pylith/` — native binary location and staged PyLith input files.
- `src/axialstress/` — HDF5 reader, failure proxies, and thermal verification.
- `tests/` — synthetic stress-tensor checks that do not require PyLith.
- `.github/workflows/ci.yml` — Python, YAML, and configuration checks without a
  PyLith download.

## Status and citation

The native environment and PyLith binary are installed. Bounded elastic and
provisional Maxwell runs complete under the eight-rank and per-process memory
limits. The current short deployment windows do not reproduce the paper's full
inflation cycles or stress histories. The supplementary equations, parameter
tables, and figure captions have been extracted from the publisher-served PDF;
the publisher-linked file retains a manuscript footer, as confirmed on
23 October 2026. Its printed ambiguities remain unresolved. The target paper's
box dimensions and numerical
convergence thresholds are unreported; the project uses a 50 km × 50 km × 10 km
box. Several strength and rheology values, mesh-converged compliance, the
continuous-cycle solver, manuscript panels, and the final failure threshold
remain incomplete. The paper's cited processed Center BPR archives are
eligible observation inputs;
published quantitative results are comparison targets. Open limitations are tracked
in [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md), and scientific choices are
recorded in [docs/DECISIONS.md](docs/DECISIONS.md). Run commands, revisions,
configuration hashes, runtime, and smoke metrics are listed in
[the numerical run log](docs/run_log.md).

Please cite both this repository and the source study:

> Cabaniss, H. E., Gregg, P. M., Nooner, S. L., and Chadwick, W. W. (2020).
> Triggering of eruptions at Axial Seamount, Juan de Fuca Ridge. *Scientific
> Reports*, 10, 10219. [https://doi.org/10.1038/s41598-020-67043-0](https://doi.org/10.1038/s41598-020-67043-0).

Repository citation metadata is in [CITATION.cff](CITATION.cff). This project
uses the MIT License; see [LICENSE](LICENSE).
