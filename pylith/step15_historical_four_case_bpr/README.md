# Four-rheology pressure calibration against raw 1998 and 2011 BPR records

This bounded comparison fits each written rheology case to original raw
Center bottom-pressure-recorder (BPR) channels, holds South out, and tracks
provisional Mohr–Coulomb paths across the 1998 and 2011 eruption windows. It
checks pressure-to-failure code paths; it does not produce an eruption forecast.

Run the comparison from the repository root with:

```sh
make historical-four-case-bpr-calibration
```

PyLith uses one MPI rank by default. Set `PYLITH_NODES=8` before the make
command to run its model solves on eight ranks.

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
The last two cases use the project-directed linear Young's modulus map from
50 GPa at 0 °C to 20 GPa at 1200 °C, clipped at both endpoints, and Eq. 15
viscosity on a steady thermal field. The 2,269-tetrahedron mesh is not
converged; fixed-base and
lateral-roller boundaries omit the written Winkler foundation. Failure uses
1 MPa cohesion, a 25-degree friction angle applied directly as `phi`, zero pore
pressure, and no tensile cutoff.

For 1998, Center RMSE is 0.0926 m and held-out South RMSE ranges from 0.489 to
0.534 m, with a positive bias of 0.327–0.362 m. For 2011, Center RMSE is
0.1244 m and held-out South RMSE ranges from 0.694 to 0.732 m, with a positive
bias of 0.373–0.397 m. Fitted pressure minima reach −95.0 MPa in the 1998
elastic case and −72.2 MPa in the 2011 elastic case. The three Maxwell cases
show a connected path at the first saved 7-day record in 1998. In 2011, the
constant-property Maxwell path begins at about 38.5 days and the two
temperature-dependent paths at about 193.6–193.8 days after the shared record
start; static elasticity has no time-dependent path estimate in this workflow.
These histories remain diagnostics because Center fits include post-eruption
data, pressure is not measured, and the failure parameters and compliance are
unresolved.

The tide- and drift-corrected workflow is run with
`PYLITH_NODES=8 make historical-four-case-corrected-bpr-calibration`. It gives
Center RMSE of 0.1154 m (1998) and 0.1045 m (2011), with held-out South RMSE
of 0.632–0.680 m and 0.709–0.745 m. The eight-rank setting is recorded in the
PyLith logs; the raw calibration above used the default single rank.

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
