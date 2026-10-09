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

## Tectonic loading and basal support sensitivity

The paper applies 60 mm/year of full spreading orthogonal to the Juan de Fuca
Ridge; Table S1 lists prescribed velocities from −20 to 20 mm/year, and Fig. S5
places opposing velocities on opposite vertical faces. I therefore compared
zero loading, ±20 mm/year per face (40 mm/year full rate), and ±30 mm/year per
face (60 mm/year full rate). The project x faces carry the prescribed
displacement, with the 20 and 30 mm/year velocities represented by one year of
static displacement. The exact geographic azimuth of those project faces has
not been reconciled with the ridge-normal direction in the paper.

Each loading case was combined with the same pressure-only stress field by
linear superposition. The basal cases were a vertically fixed base, which
represents the paper's very stiff spring limit, and a finite `32,373 Pa/m`
Winkler spring. The finite coefficient uses `k_W = rho_asthenosphere * g`
with the regional Juan de Fuca upper-mantle density of `3,300 kg/m³`. Its
`288.414 MPa` lithostatic reference traction uses 6 km of 2,700 kg/m³ crust
above 4 km of 3,300 kg/m³ mantle. The reference traction is recorded but not
directly applied because these solves are incremental and do not include the
matching gravity/initial-stress equilibrium. The joint criterion used `C = 1 MPa`, zero
pore pressure, `2.5 MPa` tensile strength, and both friction interpretations.
The pressure onset was searched in `0.1 MPa` increments on the 2,505-tetrahedron
elastic mesh.

| Basal treatment | Full spreading rate | Joint onset, `φ = 25°` | Joint onset, literal `f = 25` |
| --- | ---: | ---: | ---: |
| Fixed base | 0 mm/year | 2.3 MPa | 1.5 MPa |
| Winkler, `32,373 Pa/m` | 0 mm/year | 2.3 MPa | 1.5 MPa |
| Fixed base | 40 mm/year | 2.2 MPa | 1.5 MPa |
| Winkler, `32,373 Pa/m` | 40 mm/year | 2.2 MPa | 1.5 MPa |
| Fixed base | 60 mm/year | 2.2 MPa | 1.5 MPa |
| Winkler, `32,373 Pa/m` | 60 mm/year | 2.2 MPa | 1.5 MPa |

All six cases met both joint criteria at 12, 13, and 14 MPa. The tested
tectonic rates shift the friction-angle onset by one search increment at most;
the finite spring does not shift onset at this resolution. Under the 1 MPa
pressure-only solve, Winkler support raises Central vertical compliance from
`27.374` to `27.836 mm/MPa` (`+1.69%`) and Eastern compliance from `2.500` to
`2.943 mm/MPa` (`+17.72%`). The pressure basis converged in three outer solves;
the two tectonic bases converged in two solves. Their final maximum traction
residuals were `0.060 Pa`, `0.015 Pa`, and `0.023 Pa`.

This is a stable static elastic boundary sensitivity, not the two-year Maxwell
failure-history calculation. The coefficient is a regional prior, and
absolute lithostatic stress still needs an equilibrated gravity/initial-stress
solve. Linear superposition makes the pressure sweep efficient, but the result
does not establish equivalence to Cabaniss's temperature-dependent model or a
mesh-converged eruption threshold. The paper's 12–14 MPa value remains a
reservoir overpressure at eruption, not a local failure strength. Run
`make tectonic-boundary-sensitivity` to regenerate the ignored summary at
`data/processed/tectonic_boundary_sensitivity.json`.

## Implications for the next grid

The screened parameters do not explain the analytical mismatch or pressure
threshold difference. Keep `ν = 0.25` and `η = 10^18 Pa s` as baseline values
while the next grid tests model ingredients that alter the stress field:

- Repeat tectonic and basal comparisons in the two-year Maxwell solve and
  reconcile the geographic azimuth of the model faces with ridge-normal
  extension.
- Initialize the calibrated lithostatic reference stress with a matching
  gravity and prestress equilibrium solve before comparing absolute failure
  stresses.
- Repeat the failure-pressure screen for the temperature-dependent and
  hydrothermal material maps after their spatial response is stable.
- Continue same-domain mesh refinement within the project element cap and
  report response changes alongside the analytical errors.

Treat the 12–14 MPa range as a model comparison, not a target for arbitrary
parameter tuning. Report the critical pressure and failure fields for every
grid point so any agreement can be traced to the physical assumptions that
produce it.
