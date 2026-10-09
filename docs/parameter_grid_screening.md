# Initial parameter-grid screening

This screening separates analytical compatibility from the eruption-pressure
comparison. The paper's `12–14 MPa` value is the reservoir overpressure
boundary condition at modeled eruption. It denotes reservoir overpressure,
while the paper separately reports widespread Mohr–Coulomb failure before
modeled eruptions. See the Results and Fig. 4a in [Cabaniss et al. (2020)](https://doi.org/10.1038/s41598-020-67043-0).

The pressure range is an external comparison. The grid does not choose
parameters to force agreement with it. The threshold depends on the modeled
reservoir geometry and depth, so the comparison must retain the project
geometry and disclose differences in loading and boundary conditions.

## Elastic analytical comparison

The Table S1 spherical source inputs were held fixed (`a = 0.7 km`, `d = 4 km`,
`E = 60 GPa`, `ΔP = 10 MPa`) in the project `50 × 50 × 10 km` box. The same
2,995-tetrahedron mesh and fixed-grid samples were used at each Poisson ratio.
The analytical reference used the corresponding bulk and shear moduli for
each value.

| Poisson ratio | Peak sampled uplift | Center relative error | Fixed-grid vector L2 error |
| ---: | ---: | ---: | ---: |
| 0.20 | 3.583 mm | 55.62% | 44.44% |
| 0.25 | 3.493 mm | 55.86% | 44.87% |
| 0.30 | 3.355 mm | 56.52% | 45.81% |

The plausible Poisson-ratio sweep barely changes the mismatch. The separate
mesh sweep reduces error as the source mesh is refined, but the peak response
still shifts by 8.5% from the 75 m to 65 m mesh. Analytical compatibility and
mesh convergence remain unestablished; no numerical pass threshold is
specified by the paper.

## Maxwell pressure-threshold screen

The 50 km × 50 km × 10 km ellipsoid model used `E = 50 GPa`, `ν = 0.25`,
`ρ = 2700 kg/m³`, a constant 1 MPa cavity load for two years, a fixed base, and
roller sides. Single-branch viscosities were `10^17`, `10^18`, and `10^19 Pa s`.
The `10^17 Pa s` case used a 10-day time step to stay below one-fifth of its
Maxwell relaxation time; the other cases used 30-day steps. Each PyLith run
used eight MPI ranks, a 4 GiB address-space cap per process, and a 300 s
timeout.

For each viscosity, final-record Cauchy stress from the linear 1 MPa run was
scaled by trial pressure. This is exact for the same linear Maxwell model and
pressure time shape. The search used `C = 1 MPa`, zero pore pressure, a 2.5 MPa
tensile cutoff, and both interpretations of the paper's ambiguous friction
entry: `φ = 25°` and literal coefficient `f = 25`. A pressure bisection located
the final-record joint onset of reservoir tensile failure and a connected
cavity-to-surface shear path.

| Viscosity | Joint onset, `φ = 25°` | Joint onset, `f = 25` | Joint criterion at 12, 13, and 14 MPa |
| ---: | ---: | ---: | --- |
| `10^17 Pa s` | 2.209 MPa | 0.588 MPa | Met at all three pressures |
| `10^18 Pa s` | 2.317 MPa | 1.172 MPa | Met at all three pressures |
| `10^19 Pa s` | 2.253 MPa | 1.406 MPa | Met at all three pressures |

At `η = 10^18 Pa s`, the tensile-strength sensitivity is:

| Tensile strength | Joint onset, `φ = 25°` | Joint onset, `f = 25` |
| ---: | ---: | ---: |
| 0 MPa | 2.317 MPa | 0.082 MPa |
| 0.5 MPa | 2.317 MPa | 0.234 MPa |
| 1.5 MPa | 2.317 MPa | 0.703 MPa |
| 2.5 MPa | 2.317 MPa | 1.172 MPa |

This screen places joint failure well below 12–14 MPa for both friction
interpretations. Varying uniform viscosity over two orders of magnitude does
not close the gap. The result is a two-year held-load stress screen, not a
reproduction of Cabaniss's eruption timing or pressure history. It excludes
tectonic loading, the paper's Winkler base response and prestress, the
temperature-dependent rheologies, and damage or plastic feedback. The tensile
cutoff is a sensitivity value from independent basalt literature, not a
Cabaniss parameter.

Density was held at its 2,700 kg/m³ starter value because these quasi-static
pressure runs omit body-force gravity; density does not change this stress
screen. Young's modulus was fixed to the Table S1 value for the Mogi test. In
the homogeneous, traction-driven linear-elastic cases, changing Young's
modulus rescales displacement but does not provide an independent stress
threshold parameter.

## Implications for the next grid

The screened parameters do not explain the analytical mismatch or pressure
threshold difference. Keep `ν = 0.25` and `η = 10^18 Pa s` as baseline values
while the next grid tests model ingredients that alter the stress field:

- Apply the Table S1 opposing-face velocity range (`−20/+20 mm/year`) and the
  symmetric interpretation of the reported 60 mm/year full spreading rate
  (`−30/+30 mm/year`) as separate cases.
- Compare the paper's Winkler foundation formulation with the fixed-base
  substitute, including an explicit account of basal prestress.
- Repeat the failure-pressure screen for the temperature-dependent and
  hydrothermal material maps after their spatial response is stable.
- Continue same-domain mesh refinement within the project element cap and
  report response changes alongside the analytical errors.

Treat the 12–14 MPa range as a model comparison, not a target for arbitrary
parameter tuning. Report the critical pressure and failure fields for every
grid point so any agreement can be traced to the physical assumptions that
produce it.
