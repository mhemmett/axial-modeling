# Axial Seamount stress-threshold replication

Independent recreation of Cabaniss et al. (2020) with PyLith and a documented,
coupled model workflow for Axial Seamount.

[![CI](https://github.com/mhemmett/axial-modeling/actions/workflows/ci.yml/badge.svg)](https://github.com/mhemmett/axial-modeling/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Axial Seamount's deformation history allowed researchers to forecast its 2015
eruption, but the stress conditions that trigger eruption remain uncertain.
Cabaniss et al. (2020) modeled 22 years of seafloor deformation with
three-dimensional finite elements and found a 12–14 MPa reservoir-overpressure
threshold across temperature-dependent rheologies ([paper](https://doi.org/10.1038/s41598-020-67043-0)). This repository replaces
the paper's COMSOL model with PyLith and makes each equation, parameter,
assumption, numerical output, and postprocessed failure criterion inspectable.
The end goal is a coupled thermomechanical implementation, generated manuscript
panels, and a compiled report with its LaTeX source. The project does not use
author code, model outputs, plotting scripts, publication-produced data
products, or figure files, and it never digitizes published plots. Independent
OOI records and original raw BPR channels from earlier Axial deployments are
permitted for model checking; this excludes pressure histories, corrections,
values, or figures produced for the paper. See the
[reproduction plan](ROADMAP.md) and
[panel-by-panel record](docs/figure_reproduction.md). The repository now runs a
bounded solver and thermal-property checks, raw BPR comparisons, and a compiled
progress report. No manuscript numerical panel has been independently
reproduced; the current outputs remain diagnostics under documented assumptions.

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
pylith --version
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

Start an interactive terminal that retains the project environment with:

```bash
make tmux
```

The named tmux session is `axial-modeling`; detach with `Ctrl-b`, then `d`.
To run development checks, use `make test` and `make lint`.

## Methods

The target study treats the magma reservoir as a pressurized ellipsoidal void
measuring 6 km × 3 km × 1 km, centered 1.6 km below the seafloor. It calibrates
pressure against BPR uplift and compares non-temperature-dependent elastic and
viscoelastic hosts with two temperature-dependent viscoelastic models. The
fourth configuration represents hydrothermal circulation as greater thermal
conductivity in the brittle crust. See [the written model specification](docs/model_specification.md),
[structured paper summary](docs/paper_summary.md), and
[parameter provenance](docs/parameters.yaml).


The paper defines a model as eruptible at first tensile failure along the
reservoir boundary; it defines eruption when that failure coincides with a
through-going Mohr–Coulomb path to the surface. The project calculates these
criteria from model stress as provisional indicators. The written thermal
method solves a steady temperature field and uses it to set mechanical
properties; it specifies no mechanics-to-heat feedback term. All four
rheology code paths run, including a raw 2011 Center-calibrated comparison
with South held out. That fit includes observed eruption deflation and later
records, so its failure timing is retrospective. PyLith capabilities and open
design questions are recorded in
[COMSOL to PyLith](docs/comsol_to_pylith.md).

## Inputs and outputs

The [data notes](data/README.md) document daily OOI records and raw BPR channels
from earlier Axial deployments. Run `python data/fetch_bpr.py --download` to
retrieve the Central and Eastern Caldera OOI series. Use
`python data/fetch_historical_bpr.py --download --accept-mgds-terms` to retrieve
the authorized NCEI and MGDS source records through 2022. Raw files and
processed observations remain local and untracked. The project excludes data
products, corrections, numerical values, and figures produced for Cabaniss et
al. (2020); the historical workflow reads only original raw pressure or
pressure-derived depth channels from those archives.

PyLith writes HDF5 solution fields and material fields, with displacement in
`vertex_fields/displacement` and Cauchy stress in `cell_fields/cauchy_stress`.
`axialstress.io` reads these arrays, and the smoke check uses the top-boundary
vertical displacement as its uplift measure. Positive uplift within 0.01–10 m
is a coarse-model sanity check rather than a paper fit.

## Repository layout

- `docs/` — paper extraction, parameter sources, model mapping, decisions,
  unresolved issues, and the panel reproduction record.
- `data/` — OOI BPR retrieval, local observation processing, and provenance.
- `meshing/` — Gmsh box-with-ellipsoid generator.
- `pylith/` — native binary location and staged PyLith input files.
- `src/axialstress/` — HDF5 reader, failure proxies, and thermal verification.
- `tests/` — synthetic stress-tensor checks that do not require PyLith.
- `.github/workflows/ci.yml` — Python, YAML, and configuration checks without a
  PyLith download.

## Status and citation

The native environment, PyLith binary, and smoke solve are operational, and
the repository is published on GitHub. The four-case 2011 raw BPR comparison
fits Center with 0.124 m RMSE and yields 0.704–0.717 m RMSE at held-out South;
the fitted pressure and failure assumptions remain provisional. Additional
historical windows and more complete cycle modeling remain in progress. The
supplementary equations, parameter
tables, and figure captions have been extracted from the publisher-served PDF;
the file carries a “Confidential manuscript submitted” footer and may reflect a
pre-publication version. Model-box dimensions, observational time series,
several strength and rheology values, mesh-converged compliance, the full-cycle
solver, manuscript panels, and the final report remain incomplete. Independent OOI
records and original raw BPR channels are permitted inputs; publication-
produced data products are excluded. Open limitations are tracked
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
