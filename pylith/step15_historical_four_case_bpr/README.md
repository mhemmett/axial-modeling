# Four-rheology pressure calibration against raw 2011 BPR records

This bounded comparison fits each written rheology case to the original raw
NeMO Center bottom-pressure-recorder (BPR) channel, holds NeMO South out, and
tracks the provisional Mohr–Coulomb path through the 2011 event. It tests the
four pressure-to-failure code paths on one historical window; it does not
reproduce an eruption forecast.

Run the comparison from the repository root with:

```sh
make historical-four-case-bpr-calibration
```

The command uses 314 paired raw MGDS daily samples from 5 September 2010
through 25 July 2011. It interpolates the shared overlap to 46 uniform
7.02-day pressure intervals. Each rheology is calibrated independently to
Center uplift with a second-difference Tikhonov penalty selected by
generalized cross-validation. South remains a spatial holdout. The calibrated
Center history includes the observed eruption deflation and later records, so
the failure onset is not an independent eruption-time prediction.

The four cases are static elasticity, constant-property three-branch Maxwell,
baseline-conductivity temperature-dependent Maxwell, and hydrothermal
temperature-dependent Maxwell. The Maxwell branch viscosities, modulus
fractions, density, and Poisson ratio are explicit synthetic assumptions.
The last two cases apply Eq. 16 as printed and Eq. 15 viscosity on a steady
thermal field. The 2,761-tetrahedron mesh is not converged; fixed-base and
lateral-roller boundaries omit the written Winkler foundation. Failure uses
1 MPa cohesion, a 25-degree friction angle applied directly as `phi`, zero pore
pressure, and no tensile cutoff.

The four Center fits have about 0.124 m RMSE. South holdout RMSE ranges from
0.704 to 0.717 m, with a positive bias near 0.38 m. Fitted pressure reaches
−72 MPa in the elastic case and −34 MPa in the temperature-dependent cases.
The first interpolated path occurs at about 35 days for elasticity, 38 days
for constant-property Maxwell, and 205 days for both temperature-dependent
cases. These estimates vary with the assumed rheology and remain diagnostics
because the fit uses post-eruption data, pressure is not measured, and the
failure parameters and compliance are unresolved.

The driver writes the comparison plot to
`figures/historical_four_case_bpr_calibration.png` and its PDF companion.
CSV series, material maps, thermal fields, PyLith configurations and outputs,
and a detailed JSON summary remain under ignored
`data/processed/historical_four_case_bpr_calibration/`. A rerun replaces that
generated output directory; use `--output-dir` for a separate retained run.
Direct execution accepts `--mesh`, `--elastic-surface`, `--elastic-material`,
`--output-dir`, and `--figure-stem` path options.

All observation inputs are original raw `RawDep` and `Depth` channels; no
Cabaniss-associated pressure history, correction, result, or figure data enters
the workflow. See [`docs/failure_analysis.md`](../../docs/failure_analysis.md)
and [`docs/run_log.md`](../../docs/run_log.md) for detailed methods and limits.
