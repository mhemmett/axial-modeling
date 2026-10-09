# Step 13: historical three-branch Maxwell BPR check

The historical check tests whether PyLith's three-branch loading path can
follow raw Center and South bottom-pressure recorder (BPR) histories across the
1998 and 2011 Axial eruptions and four additional deployment overlaps spanning
1995–2013. It drives pressure inferred from Center uplift and evaluates the
South deployment as a held-out observation. The run uses original raw channels
only; it does not use paper-produced histories, corrections, model results, or
figures. The branch parameters and pressure inversion are provisional
assumptions, so these are forward diagnostics rather than calibrated hindcasts.
Mesh convergence, raw-record corrections, and the paper's generalized branch
spectrum remain unresolved.

## Installation

From the repository root, create the project environment and install the
provided PyLith binary if they are absent:

```sh
make env
make install-pylith
source scripts/activate.sh
```

The workflow uses the repository's Python 3.12 Conda environment, Gmsh 4.x
Python API, PyLith 5.0.2, and its bundled PETSc. PyLith and PETSc are used from
the provided binary distribution.

## Quick start

From the repository root, run:

```sh
make historical-generalized-maxwell-check
```

The target regenerates the 2,761-tetrahedron ellipsoid mesh, builds the steady
hydrothermal three-branch material database, and runs one bounded PyLith solve
for each of six paired intervals. It reads processed daily series generated
from raw archives; if the 1998 Center daily file is absent, it processes the
locally cached raw records. The eruption pairs are WC81 Center/WC82A South and
NeMO 2010–11 Center/NeMO 2009–11 South. The additional overlaps are WC68/WC69
in 1995–96, NeMO Center/South in 2003–05, NeMO 2007–10 Center/2005–09 South 2,
and NeMO Center/South in 2011–13. Outputs include two tracked figures and local
CSV/JSON diagnostics.

## Usage

The Make target supplies the mesh and material database to
`scripts/historical_generalized_maxwell_bpr_check.py`. Direct invocation
requires `--mesh PATH` and `--material-database PATH`; optional paths are
`--elastic-surface PATH` (the Step 05 static unit response), `--output-dir PATH`
(the processed-data directory), and `--figure-stem PATH` (the tracked figure
basename).

## Method and inputs

Each pair uses the first shared daily sample as its zero reference. Static
ellipsoid compliance converts Center uplift to pressure; the resulting daily
pressure is applied as a PyLith time history. Surface uplift is interpolated
at the Center and South coordinates and compared with paired raw daily means.
The material field uses the steady zero-source Eq. 14/Eq. 22 thermal solution
and Eq. 15 viscosity scaling. Reference branch viscosities are
`[1.0e18, 5.0e17, 2.0e18] Pa·s`; shear fractions are `[0.25, 0.25, 0.25]`.
These synthetic values exercise the generalized Maxwell interface and do not
represent a recovered paper spectrum.

The workflow reads only original NCEI raw absolute-pressure channels or the
original MGDS `Depth`/`RawDep` fields after daily aggregation. It does not
apply tide, ocean-variability, or sensor-drift corrections. The static
ellipsoid response is not mesh-converged, and the inferred pressure becomes
large because the daily series is referenced to its first common sample.
The implementation uses PyLith's documented
[three-branch formulation](https://pylith.readthedocs.io/en/v5.0.2/user/governingeqns/elasticity/bulk-rheologies/linear-genmaxwell.html).
Archive citations, channel selection, and retrieval provenance are recorded in
[`docs/historical_bpr_check.md`](../../docs/historical_bpr_check.md) and
[`data/README.md`](../../data/README.md).

## Outputs and validation

The tracked event and interval figures are
`figures/historical_generalized_maxwell_bpr_check.png` and
`figures/historical_generalized_maxwell_deployment_bpr_check.png`, each with a
PDF counterpart. The deployment figure also overlays WC67 and NeMO South 1 as
additional held-out raw BPR stations. PyLith meshes, material databases, HDF5
outputs, aligned daily comparisons, and JSON summaries remain local under this
directory and `data/processed/axial_historical_bpr/`. Each comparison CSV
contains its UTC date, inferred pressure, observed and modeled uplift, and
residuals; the JSON summary records metrics, branch assumptions, and
limitations. Synthetic unit tests check daily alignment, interpolation,
metrics, and invalid inputs.
The integrated `make reproduce` workflow runs this target, the unit suite,
Ruff, and the report build.

For all six historical windows, each JSON summary also records a Mohr–Coulomb
diagnostic at every saved stress record, using provisional `1 MPa` cohesion,
`25°` friction angle used directly as `phi`, and zero pore pressure. The shear path
is evaluated without a tensile cutoff. A separate ignored CSV stores
yielded-cell counts, cavity-to-top path flags, and maximum cavity tensile
stress for each stress record. The proxy produces a path within 68 days in
all six windows from 1995 through 2013, including the four intervals without
an eruption. The current threshold assumptions therefore do not distinguish
eruption timing. See
[`docs/historical_bpr_check.md`](../../docs/historical_bpr_check.md) for the
assumptions and interpretation.

The 1995–96 WC68-forced run also checks raw WC67, and the 2007–09 Center-forced
run checks NeMO South 1 over the primary model window. Neither additional
station contributes to its pressure history. WC67 has `0.036 m` RMSE and
`0.685` correlation; NeMO South 1 has `0.221 m` RMSE and `−0.506` correlation.

For the event runs, held-out South RMSE is `0.503 m` for 1998 and `0.680 m`
for 2011, with positive biases of `0.329 m` and `0.371 m`. Deployment-overlap
RMSE ranges from `0.123 m` to `1.242 m`; the 2011–13 correlation is `0.991`
despite `−1.214 m` bias. These residuals, unresolved rheology, and uncorrected
observations preclude interpreting correlation as calibration or forecast
skill.

## Repository layout and attribution

- `scripts/historical_generalized_maxwell_bpr_check.py` builds event and
  deployment forcing, runs PyLith, samples station predictions, and writes the
  comparison plots.
- `src/axialstress/historical_generalized_maxwell.py` aligns observations and
  computes pressure histories and residual metrics.
- `tests/test_historical_generalized_maxwell.py` checks the synthetic data
  alignment and comparison calculations.
- `data/README.md` and `docs/historical_bpr_check.md` record NOAA/NCEI and MGDS
  source attribution and applicable data terms.

The repository software is licensed under [MIT](../../LICENSE). MGDS-derived
raw channels and figures retain the archive's CC BY-NC-SA 3.0 terms and source
citations; the BPR provenance documents provide the attribution.
