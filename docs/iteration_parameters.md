# Iteration parameters and convergence standard

The first numerical goal is a stable PyLith implementation of the written
Cabaniss et al. (2020) model. Independent Axial literature supplies useful
starting values for a few missing inputs, but it does not determine every
parameter in the target model. These candidates are recorded for controlled
iteration, not as calibrated values. No Cabaniss model output, plotted result,
or eruption prediction is used as a numerical target.

## Geometry and fixed project setup

Use a 50 km × 50 km × 10 km box, with the seafloor at `z = 0` and the base at
`z = -10 km`. Coordinates are `x` east, `y` north, and `z` up. The primary
6 km × 3 km × 1 km ellipsoid is centered 1.6 km below the seafloor, has no dip,
and strikes N30°W. Both production mesh generators now rotate its long axis
120° counterclockwise from east before cutting the cavity. These values come
from the project direction and the target paper's written geometry.

## Candidate starting values

| Missing or uncertain input | Starting choice for iteration | Evidence and limit |
|---|---|---|
| Poisson ratio | `ν = 0.25`; check `0.20` and `0.30` after the baseline runs | Slead et al. use `ν = 0.25` with `E = 70 GPa` and `G = 30 GPa` in an independent Axial deformation model. Their elastic source model differs from Cabaniss et al.; the outer values are sensitivity checks, not Axial measurements. [Slead et al. (2024)](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2023JB028414) |
| Host density for gravity and pressure loading | Start at `2700 kg/m³`; bracket `2550–2850 kg/m³` | Axial seafloor gravity gives an average `2700 kg/m³` for the uppermost volcano and indicates a low-density region beneath the summit with contrast of at least `150 kg/m³`. The measurement does not resolve a 10 km bulk column; the bracket is a sensitivity envelope, not a measured range. [Hildebrand et al. (1990)](https://agupubs.onlinelibrary.wiley.com/doi/abs/10.1029/JB095iB08p12751) |
| Constant viscosity in the non-temperature-dependent viscoelastic case | Sweep `10^16`, `10^18`, and `10^19 Pa s` | Nooner and Chadwick report `10^16 Pa s` for a localized partial-melt region that produces a short-timescale reinflation response; that value is not a whole-host measurement. The higher two values are log-spaced trial points. At `G = 10–20 GPa`, the resulting single-branch Maxwell times span about 6 days to 32 years. [Nooner and Chadwick (2009)](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2008GC002315) |
| Generalized Maxwell branch fractions | For the first three-branch run, retain the existing software-check fractions `[0.25, 0.25, 0.25]` and the resulting `0.25` equilibrium fraction; then test fraction sensitivity | No Axial study found here reports Cabaniss's missing branch fractions or relaxation spectrum. This is an explicitly numerical placeholder already used by the project, not a literature-derived rheology. First establish elastic and one-branch stability so branch fractions do not obscure the baseline. |
| Tensile cutoff used by failure postprocessing | Use zero tensile strength for the literal “any tensile failure” criterion; separately report `0.1–2.5 MPa` sensitivity | Cabaniss defines tensile failure but supplies no strength. A volcanic-rock review reports field-scale basalt estimates of `0.1–2.5 MPa`; this is a proxy range and does not set PyLith solver convergence. [Heap et al. (2021)](https://link.springer.com/article/10.1007/s00445-021-01447-2) |
| Friction coefficient in the Mohr–Coulomb proxy | Interpret the table's `25°` as an angle and start with `f = tan(25°) = 0.466` | The paper's table labels `f` as an angle while Eq. 25 uses a coefficient. The tangent conversion is the standard angle-to-coefficient interpretation, but the source does not state it. This changes failure postprocessing, not equilibrium convergence. |
| Tectonic velocity at opposing sides | Use `-20/+20 mm/year` for the table-based run; compare `-30/+30 mm/year` if treating the stated `60 mm/year` full spreading rate as a symmetric split | Table S1 gives `Pv = -20..20 mm/year`; the main text reports `60 mm/year` full spreading and the schematic does not state the per-face split. Keep these as distinct loading cases rather than blend them. |
| Winkler spring coefficient | Start at `32,373 Pa/m` for the finite Galgana spring; retain `2.6487 × 10^18 Pa/m` as the separate Cabaniss supplement benchmark | The finite value uses regional upper-mantle density `3300 kg/m³` and `g = 9.81 m/s²`. The Cabaniss coefficient follows Eq. 23 with `Zdisp = 10^-10 m` and the provisional `2700 kg/m³` density. |
| Basal lithostatic reference traction | Start at `288.414 MPa` upward on the base | Integrate 6 km of 2700 kg/m³ crust and 4 km of 3300 kg/m³ mantle over the project 10 km depth. This regional prior must be initialized with matching gravity and initial stress before it enters absolute failure stresses. |
| Thermal conditions away from the reservoir | Keep zero heat production and the `30 °C/km` background geotherm on the surface, base, and lateral faces as the first documented setup | The paper gives a steady thermal method and background gradient, but does not fully state every exterior thermal boundary condition. Applying the gradient on all non-reservoir faces remains an explicit project assumption. |
| Temperature-dependent elastic modulus | Preserve the target table endpoints `EB = 50 GPa` and `ED = 25 GPa`; do not treat the printed Eq. 16 as resolved | As printed with the listed positive parameters, Eq. 16 conflicts with the brittle/ductile descriptions. The existing 50-to-20 GPa project map remains a separate assumption and must be reconciled before it is called a paper reproduction. |

The target article and supplement do not provide the full-depth density,
Poisson ratio, complete Maxwell spectrum, tensile strength, thermal boundary
details, per-face spreading split, mesh resolution, time-step rule, or solver
tolerances. The Axial sources above narrow some choices but do not fill all of
these gaps. The paper's Eq. 15 does provide an Arrhenius viscosity law for the
temperature-dependent cases, so use its published constants with temperature
converted to kelvin; do not replace them with the constant-viscosity sweep.

The first solver-stable candidate uses `E = 50 GPa`, `ν = 0.25`, and
`ρ = 2700 kg/m³`. Its one-branch check uses `η = 10^18 Pa s`; its three-branch
check uses reference viscosities `[10^18, 5×10^17, 2×10^18] Pa s` and
fractions `[0.25, 0.25, 0.25]`. The two-year PyLith runs complete with finite
stress and branch state, and the steady thermal iteration converges. This is
a stable coarse-mesh starting set, not a mesh-convergence result or a complete
validation of the target Winkler boundary and missing Maxwell spectrum.

## What counts as convergence

Cabaniss et al. describe compatibility checks against the Mogi elastic
solution, the Del Negro viscoelastic solution, prior finite-element models,
and a Winkler-versus-roller base comparison ([paper and supplement](https://doi.org/10.1038/s41598-020-67043-0)). The paper does not state a percentage
error threshold, mesh refinement ratio, timestep control, or algebraic solver
tolerance. We will use the same verification categories where independent
references are available, without using Cabaniss model fields or plotted
values: benchmark surface responses should remain compatible as the mesh is
refined, and each selected PyLith solve should complete with finite
displacement, stress, and material fields and stable solver residuals.

The Mogi check now uses the Table S1 analytical source inputs (`a = 0.7 km`,
`d = 4 km`, and `E = 60 GPa`), with `ν = 0.25` from later Axial literature.
On the project-directed 50 km × 50 km × 10 km domain, the same-far-field
100/75/65 m near-source sequence reduces vector L2 error from `49.8%` to
`44.9%` to `42.7%`; center error falls from `59.5%` to `55.9%` to `54.2%`.
Peak uplift still changes `8.5%` from the middle to fine mesh, so this is not
mesh convergence. A larger benchmark depth also reduces error but changes the
domain. The paper sets no percentage cutoff for either check.

BPR residuals measure how well this simple model represents independent
observations; they do not determine whether the numerical solution converged.
We expect imperfect BPR alignment because the model simplifies Axial's
reservoir and crust. Use BPR data to assess physical performance after the
elastic and viscoelastic benchmark checks pass. All runs remain within the
project's eight-rank and per-process memory limits.

The initial Poisson-ratio, viscosity, and failure-pressure grid is summarized
in [`parameter_grid_screening.md`](parameter_grid_screening.md). That screen
shows that these values alone do not explain the analytical mismatch or the
difference from the paper's 12–14 MPa eruption overpressure.
