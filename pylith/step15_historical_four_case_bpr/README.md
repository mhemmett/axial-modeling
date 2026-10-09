# Four-rheology pressure calibration against raw 1998 and 2011 BPR records

This bounded comparison fits each written rheology case to original raw
Center bottom-pressure-recorder (BPR) channels, holds South out, and tracks
provisional Mohr–Coulomb paths across the 1998 and 2011 eruption windows. It
checks pressure-to-failure code paths; it does not produce an eruption forecast.

Run the comparison from the repository root with:

```sh
make historical-four-case-bpr-calibration
```

The command runs both event windows. The 1998 calibration uses 309 paired raw
NCEI daily samples from 3 October 1997 through 7 August 1998 and 44 uniform
7-day pressure intervals. The 2011 calibration uses 314 paired raw MGDS daily
samples from 5 September 2010 through 25 July 2011 and 46 uniform 7.02-day
pressure intervals. WC81 and NeMO Center are the respective calibration sites;
WC82A and NeMO South are held out. Each case fits Center uplift with a
second-difference Tikhonov penalty selected by generalized cross-validation.
Both Center histories include observed eruption deflation and later records,
so neither failure history independently predicts eruption time.

The four cases are static elasticity, constant-property three-branch Maxwell,
baseline-conductivity temperature-dependent Maxwell, and hydrothermal
temperature-dependent Maxwell. The Maxwell branch viscosities, modulus
fractions, density, and Poisson ratio are explicit synthetic assumptions.
The last two cases apply Eq. 16 as printed and Eq. 15 viscosity on a steady
thermal field. The 2,761-tetrahedron mesh is not converged; fixed-base and
lateral-roller boundaries omit the written Winkler foundation. Failure uses
1 MPa cohesion, a 25-degree friction angle applied directly as `phi`, zero pore
pressure, and no tensile cutoff.

For 1998, Center RMSE is about 0.093 m and held-out South RMSE ranges from
0.519 to 0.531 m, with a positive bias of 0.350–0.359 m. For 2011, Center
RMSE is about 0.124 m and held-out South RMSE ranges from 0.704 to 0.717 m,
with a positive bias near 0.38 m. Fitted pressure minima reach −94.8 MPa in
the 1998 elastic case and −72.0 MPa in the 2011 elastic case. All four 1998
cases already show a connected path at the first saved 7-day record. In 2011,
the interpolated path onset ranges from about 35 to 205 days after the start
of the shared record. These histories remain diagnostics because Center fits
include post-eruption data, pressure is not measured, and the failure
parameters and compliance are unresolved.

The driver writes separate plots, summaries, and CSV series for each event;
figures use the matching `_1998` or `_2011` suffix. Generated PyLith outputs,
material maps, thermal fields, and detailed JSON summaries remain under the
matching ignored directories in `data/processed/`. Reruns replace these
generated directories. Direct execution accepts `--event {1998,2011}` and
the `--mesh`, `--elastic-surface`, `--elastic-material`, `--output-dir`, and
`--figure-stem` path options.

The 1998 inputs are NCEI raw absolute-pressure channels in dbar; 2011 uses
MGDS `RawDep` and `Depth` channels. The 1998 MGDS Fox archive is a duplicate
of the NCEI instruments and is not counted as additional station coverage.
No Cabaniss-associated pressure history, correction, result, or figure data
enters the workflow. See
[`docs/failure_analysis.md`](../../docs/failure_analysis.md) and
[`docs/run_log.md`](../../docs/run_log.md) for detailed methods and limits.
