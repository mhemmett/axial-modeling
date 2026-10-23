# Four-rheology Center BPR pressure calibration

This bounded calculation fits each stated rheology to a Center BPR event
history and evaluates the saved PyLith stress fields. The paper's reported
12--14 MPa temperature-dependent eruption overpressure is a comparison target;
the inversion does not use it as a constraint.

Run both event windows from the repository root with:

```sh
make historical-four-case-bpr-calibration
```

The command covers the 1998 WC81 and 2011 NeMO Center records. It interpolates
each Center history to a uniform seven-day grid, fits pressure with a
second-difference Tikhonov penalty selected by generalized cross-validation,
and runs elasticity, constant-property Maxwell, temperature-dependent
Maxwell, and hydrothermal Maxwell cases. Both records include eruption
deflation and later observations, so the calculated failure histories are
retrospective diagnostics rather than independent predictions of eruption
timing.

The Maxwell branch viscosities and fractions are synthetic. The
temperature-dependent cases use a project-assumed linear Young's modulus map
from 50 GPa at 0 $^\circ$C to 20 GPa at 1200 $^\circ$C because the printed
Eq. 16 conflicts with its stated brittle and ductile limits. The current mesh
is not converged, the pressure calibration uses a fixed base rather than the
written Winkler foundation, and the failure calculation uses assumed cohesion,
friction, and pore pressure without a tensile cutoff.

The command writes Center uplift, fitted pressure, and saved failure-path
series beneath ignored `data/processed/` directories. It writes PNG and PDF
calibration figures under `figures/`. Corrected Center observations can be
processed with `make historical-bpr-corrected-daily` and selected with
`--corrected-observations` when invoking the script directly. Neither raw nor
corrected event fits establish the continuous 22-year reproduction.

The governing equations, parameter sources, and known limits are recorded in
[`docs/model_specification.md`](../../docs/model_specification.md),
[`docs/parameters.yaml`](../../docs/parameters.yaml), and
[`docs/KNOWN_ISSUES.md`](../../docs/KNOWN_ISSUES.md).
