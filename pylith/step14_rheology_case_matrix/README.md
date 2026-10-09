# Four-case rheology solver matrix

This bounded integration check runs the four written rheology configurations
under one common synthetic cavity load. It verifies that the thermal fields,
cellwise material properties, PyLith histories, and independent Maxwell stress
reconstruction work together. It does not calibrate pressure or reproduce an
eruption threshold.

Run it from the repository root with:

```sh
make rheology-case-matrix
```

The driver creates one 2,761-tetrahedron ellipsoid mesh, solves the written
steady thermal model for baseline and hydrothermal conductivity, and runs four
PyLith cases over two years with a constant 1 MPa cavity pressure. Each case
uses 25 saved stress records. The generalized Maxwell cases use three
synthetic branches with reference viscosities of `1e18`, `5e17`, and `2e18`
Pa s, branch modulus fractions of `0.25`, density of `2800 kg/m3`, and
Poisson's ratio of `0.25`. The failure proxy uses `1 MPa` cohesion, a `25°`
friction angle applied directly as `phi`, zero pore pressure, and no tensile
strength.

The matrix covers non-temperature-dependent elasticity, non-temperature-
dependent generalized Maxwell rheology, temperature-dependent generalized
Maxwell rheology, and the hydrothermal temperature-dependent case. The last
two use Eq. 16 as printed, solely as a diagnostic because its temperature
trend conflicts with the written brittle and ductile definitions. Thermal
boundaries are 0°C at the surface, 1200°C at the reservoir, and 30°C/km at the
sides and base. A fixed base with lateral roller boundaries approximates the
support; the specified Winkler foundation is not represented.

All four cases reached the two-year endpoint. The three Maxwell outputs
reconstruct PyLith Cauchy stress with relative L2 errors of `2.03e-16`,
`2.47e-16`, and `2.77e-16`. The minimum Maxwell relaxation time is `1e8 s`
without temperature-dependent properties and `1.5e8 s` in both temperature-
dependent cases; the `2.592e6 s` output interval is below one fifth of each.
No case develops a cavity-to-surface path under this shared load. The generated
JSON summary is written to the ignored
`data/processed/rheology_case_matrix_summary.json`; PyLith files use a
temporary directory.

These results test code paths only. The synthetic branch spectrum, common
load, incomplete boundary treatment, and diagnostic Eq. 16 law prevent
physical interpretation. The matrix uses no BPR observations or paper-
associated data and does not resolve pressure history, material calibration,
or the full four-case failure comparison.
