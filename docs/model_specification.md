# Written model specification

This document records the equations and numerical setup stated in Cabaniss et
al. (2020) and the publisher-served supplementary information. It does not
fill gaps with values inferred from published plots. The supplementary PDF
carries a “Confidential manuscript submitted” footer, so the supplement
transcription may describe a pre-publication version. Parameter values and
source locations are indexed in [`parameters.yaml`](parameters.yaml); figure
eligibility is tracked in [`figure_reproduction.md`](figure_reproduction.md).

Sources: [main article](https://doi.org/10.1038/s41598-020-67043-0) and
[publisher-served supplementary information](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41598-020-67043-0/MediaObjects/41598_2020_67043_MOESM1_ESM.pdf).
Equation numbers below are those printed in the supplement.

## Elastic and viscoelastic benchmarks

The supplement gives the Mogi displacement for a spherical source as

$$
U_x = \frac{\Delta P a^3 x}{r^3}
      \frac{3K+4G}{2G(3K+G)}, \qquad
U_z = \frac{\Delta P a^3 d}{r^3}
      \frac{3K+4G}{2G(3K+G)}. \tag{1–2}
$$

Here, `a` is source radius, `d` is depth to its center, `r` is radial distance
from the source midpoint, and `G` and `K` are shear and bulk moduli. Table S1
sets `a = 0.7 km`, `d = 4 km`, and analytical Young's modulus `E = 60 GPa`.
The supplement defines `G = E/[2(1 + nu)]` and `K = E/[3(1 - 2 nu)]`; its
table does not provide `nu`.

The non-temperature-dependent generalized Maxwell relaxation times are

$$
\tau_0 = \frac{\eta}{G_0\mu_1}, \qquad
\tau_1 = \frac{3K+G_0}{3K+G_0\mu_0}\tau_0, \qquad
\tau_2 = \frac{\tau_0}{\mu_0}. \tag{3–5}
$$

The supplement defines `mu0` and `mu1` as fractional moduli but does not report
their values. It gives the transformed shear modulus and response function as

$$
\tilde{\mu}(s) =
\frac{s(\mu_0+\mu_1)G_0 + \mu_0\mu_1G_0^2/\eta}
     {s+\mu_1G_0/\eta}, \tag{6}
$$

$$
\tilde{A}(s) =
\frac{3K+4\tilde{\mu}(s)}
     {(2s\tilde{\mu}(s))(3K+4\tilde{\mu}(s))}. \tag{7}
$$

Equation 7 is transcribed as printed; its matching numerator and denominator
factor appears to cancel. Verify this expression against a final-version
source before using it in code. The inverse transform printed as Eq. 8 is

$$
\begin{aligned}
A(t) = \frac{1}{2G_0}\Bigg[&
\frac{3K+4G_0\mu_0}{\mu_0(3K+G_0\mu_0)} \\
&-\frac{3\eta G_0^2
e^{-\left(\frac{G_0\mu_1(3K+G_0\mu_0)}{\eta(3K+G_0)}\right)t}}
{\eta(3K+G_0\mu_0)(3K+G_0)}(1-\mu_0) \\
&-\left(\frac{1}{\mu_0}-1\right)
e^{-\left(\frac{G_0\mu_0\mu_1}{\eta}\right)t}
\Bigg].
\end{aligned}
\qquad \text{(8)}
$$

The time-dependent viscoelastic displacement is the geometric factor in Eqs. 1
and 2 multiplied by `A(t)`. The supplement says this recovers the elastic
solution at `t = 0`.

For the finite-element formulation, the supplement states

$$
\frac{d\epsilon}{dt} \propto \frac{\sigma}{\eta}
  + \frac{1}{G}\frac{d\sigma}{dt}, \tag{9}
$$

$$
G = \frac{E}{2(1+\nu)}, \tag{10}
$$

$$
\sigma = 2G\left(\mu_0\epsilon + \sum_{i=0}^{j}\mu_i q_i\right),
\qquad \sum_{i=0}^{j}\mu_i=1, \tag{11–12}
$$

$$
\dot{q}_i + \frac{q_i}{\tau_i} = \dot{\epsilon}. \tag{13}
$$

Equation 9 uses a proportionality sign and does not state the proportionality
factor. Equation 11's sum and leading `mu0` are transcribed as shown in the
supplement; the branch convention requires confirmation before implementation.
The supplement describes a generalized Maxwell model with multiple branches,
but does not give its fractional moduli or complete relaxation spectrum.

## Temperature-dependent properties

The thermal field is calculated at steady state:

$$
\nabla\cdot(k\nabla T) = -Q, \qquad Q=0. \tag{14}
$$

Temperature-dependent viscosity and Young's modulus are

$$
\eta_{TD} = A_D\exp\!\left(\frac{E_A}{R_gT}\right), \tag{15}
$$

$$
E_{TD} = E_D +
\frac{E_B}{1+C_S\exp\!\left(A_S(1-T/T_{max})\right)}. \tag{16}
$$

With the positive values `AS = 12` and `CS = 5`, Eq. 16 as printed makes
modulus rise from approximately `ED = 25 GPa` at low temperature toward
`ED + EB = 75 GPa` at high temperature. The text and Table S1 instead describe
`ED = 25 GPa` as the ductile modulus and `EB = 50 GPa` as the brittle modulus.
This is an unresolved source inconsistency, so the equation must not be silently
reversed or treated as a verified transition law.

For the current four-case reproduction, the project owner specified a
50 km × 50 km horizontal domain, a 0–10 km depth interval, and a temperature-
dependent Young's modulus spanning 20–50 GPa. The implementation applies
`E(T) = 50 − 30 clip(T/1200, 0, 1)` GPa, with `T` in degrees Celsius. This
linear interpolation is an explicit project assumption informed by that
direction; it does not resolve the source's Eq. 16 inconsistency. The reservoir
is an ellipsoidal void loaded by normal pressure traction on its cavity surface.
Coordinates use x east, y north, and z up. The primary ellipsoid's major axis
strikes N30°W, with zero dip; both production mesh generators rotate the
ellipsoid to this orientation before subtracting it from the box. The PyLith
model does not include a separate fluid finite-element volume.

Equations 17 and 18 convert that modulus to shear and bulk moduli:

$$
G_{TD}=\frac{E_{TD}}{2(1+\nu)}, \qquad
K_{TD}=\frac{E_{TD}}{3(1-2\nu)}. \tag{17–18}
$$

The temperature-dependent Maxwell times are

$$
\tau_{0TD}=\frac{\eta_{TD}}{G_{0TD}\mu_1}, \qquad
\tau_{1TD}=\frac{3K_{TD}+G_{TD}}
                      {3K_{TD}+G_{TD}\mu_0}\tau_{0TD}, \qquad
\tau_{2TD}=\frac{\tau_{0TD}}{\mu_0}. \tag{19–21}
$$

Table S1 gives `AD = 10^9 Pa s`, `EA = 1.2×10^5 J/mol`, `Rg = 8.3114
J/(mol K)`, `ED = 25 GPa`, `EB = 50 GPa`, `AS = 12`, and `CS = 5`. Equation 15
requires absolute temperature. Equation 16 calls `Tmax` the magma-chamber
temperature; Table S1 reuses `Tmax = 600 °C` for the hydrothermal cutoff, so
the code must represent these as separate parameters. The supplement gives a
1200 °C reservoir boundary and a 30 °C/km background geotherm with a 0 °C
surface.

For the hydrothermal case, effective conductivity is

$$
k = k_0 + k_0(Nu-1)
  \exp\!\left(A(1-T/T_{max})\right)
  \exp\!\left(A(1-z/z_{max})\right). \tag{22}
$$

Table S1 gives `k0 = 3 W/(m K)`, `Nu = 8`, `A = 0.75`, cutoff temperature
`Tmax = 600 °C`, and cutoff depth `zmax = 6 km`. Table S1 labels `Q = 0` with
units of °C, although Eq. 14 describes volumetric heat production. Preserve
the zero and flag the table's unit error.

## Loading, boundaries, and failure

The supplement prescribes roller conditions on lateral faces and a Winkler
spring foundation at the base. It gives spring stiffness as

$$
s = \frac{\rho V g}{Z_{disp}}, \tag{23}
$$

where `rho` is overlying-block density, `V` is model-box volume, and `g` is
gravity. The benchmark uses `Zdisp = 10^-10 m`. The project box is 50 km ×
50 km × 10 km; the paper does not state its box dimensions or the value of
`rho`. Axial gravity measurements give 2,700 kg/m³ for the uppermost volcano,
which supplies a provisional density prior but does not constrain the full
10 km column. Using that value gives an area stiffness of
`2.6487 × 10^18 Pa/m` after dividing Eq. 23 by the 50 km × 50 km base area.
Production mechanics still use a fixed base; a separate diagnostic outer
iteration is documented below. No comparison with Cabaniss model outputs is
permitted.

Galgana et al. (2011, §2.2) describe a buoyant Winkler force at the base, and
Le Corvec et al. (2015, Eq. 5) write its restoring term as
`rho_asthenosphere g w`. Their separate offset balances the layered
lithostatic load, `g (rho_c T_c + rho_m T_m)`. With positive-up `z`, the global
traction is `t_z = −k_W u_z + t_z0`, where `k_W = rho_asthenosphere g` and
`t_z0` is the positive-up basal support traction. PyLith's local normal on the
bottom face points downward.

For Axial, the regional Juan de Fuca ridge gravity model uses 2,700 kg/m³
crust, 3,300 kg/m³ upper mantle, and a 6 km crustal thickness. We use these as
a regional prior, extend the crust to 6 km, and assign the remaining 4 km of
the project box to mantle. With `g = 9.81 m/s²`, this gives a finite spring
coefficient of `32,373 Pa/m` and a lithostatic reference traction of
`288.414 MPa` upward (or `−288.414 MPa` in bottom-normal coordinates). The
Axial gravity survey reports local low-density volcanic material, so these
regional values are a starting calibration rather than a direct measurement
of the entire Axial column. [Marjanović et al. (2011)](https://doi.org/10.1029/2010GC003439),
[Hildebrand et al. (1990)](https://doi.org/10.1029/JB095iB08p12751).

The supplement's `s = rho V g / Zdisp` has units of total stiffness (N/m),
whereas PyLith's distributed boundary traction requires area stiffness (Pa/m).
Dividing by the 50 km × 50 km basal area gives `k = rho H g / Zdisp`. For the
provisional 2,700 kg/m³ density, 10 km depth, 9.81 m/s² gravity, and
`Zdisp = 10⁻¹⁰ m`, this yields `2.65 × 10¹⁸ Pa/m`. Its ratio to
the rough elastic scale `E/H` is `5.30 × 10¹¹`–`1.32 × 10¹²` across the
project-directed 50–20 GPa modulus range. A 1 MPa basal traction at this
stiffness corresponds to `3.78 × 10⁻¹³ m` displacement. These scale checks
show that the supplement coefficient is effectively a fixed base under these
assumptions; they do not establish that it is equivalent to Galgana's
density-contrast foundation.

PyLith 5.0.2's documented [`NeumannTimeDependent` condition](https://pylith.readthedocs.io/en/v5.0.2/user/physics/bc/time-dependent.html)
uses prescribed spatial and temporal traction parameters and does not evaluate
traction from the solved displacement. The static diagnostic therefore uses
an outer iteration to update traction from basal displacement. It compares a
fixed base with the regional finite-spring prior on one mesh. Its stress fields
are incremental about a lithostatic reference: the calibrated absolute
prestress is recorded but is not applied without a matching gravity and
initial-stress equilibrium solve. Main pressure-calibration runs retain a
fixed base pending that equilibrium implementation.
`make winkler-scale` reproduces both calibrations, and
`make winkler-foundation-check` writes the static solver results and compliance
figure.

Source: [Galgana, McGovern, and Grosfils (2011), §2.2](https://doi.org/10.1029/2010JE003654).

The pressure load on the reservoir boundary is

$$
\mathrm{MagmaLd} = \Delta P + \rho_r g z, \tag{24}
$$

where `Delta P` is reservoir pressure change and `rho_r` is host-rock density.
The supplement says it integrates the reservoir boundary to calculate volume
change and flux but does not supply the complete pressure-time history or
coupling schedule.

The stated Mohr–Coulomb criterion is

$$
\tau = C + f\sigma_n. \tag{25}
$$

Table S1 gives cohesion `C = 10^6 Pa` and calls `f = 25°` an internal friction
angle, although Eq. 25 uses `f` as a coefficient. It does not state whether to
use the angle directly, its tangent, or another conversion. The postprocessing
therefore compares the tabulated 25° used directly as `phi` against a literal
dimensionless `f = 25`, converted to `phi = arctan(f)`. This sensitivity
quantifies the ambiguity but does not resolve the source notation. The
supplement defines an eruptible state by tensile failure at the reservoir
boundary and a modeled eruption by that tensile failure together with a
through-going Mohr–Coulomb path from the reservoir to the surface. It does not
list a tensile-strength value.

The article states a 60 mm/year full ridge-spreading rate for its tectonic
experiments. Table S1 lists `Pv` from -20 to 20 mm/year, and Fig. S5 shows
opposing boundary velocities without stating their numerical split. The
article and supplement therefore do not determine one per-face loading value.

## Numerical method and unavailable inputs

The written method uses three-dimensional COMSOL Multiphysics 5.4 finite
elements, with the four rheologies listed above. It benchmarks elastic
displacement against Mogi, viscoelastic response against Del Negro, and finite
elements against earlier two- and three-dimensional models. Supplementary
Figs. S3 and S4 compare the Winkler base with an elastic roller base. These
comparisons, along with the analytical and prior finite-element benchmarks,
are the paper's stated verification standard. The paper gives no numerical
error tolerance or mesh/time refinement rule, so the project will not claim a
paper-defined percentage threshold. Numerical convergence will mean that the
independent benchmark responses remain compatible as the mesh is refined and
that PyLith completes the selected static or time-dependent solves with finite
fields and stable solver residuals. BPR misfit remains a model-performance
diagnostic, not a numerical convergence criterion. The supplement does not
state mesh spacing, element count, time-step control, nonlinear or linear
tolerances, or the values of all Maxwell branches.

The 22-year BPR record constrains pressure and volume change. Independently
archived raw BPR observations and their documented tide/drift corrections are
allowed inputs, but the paper's modeled pressure/stress histories, eruption
predictions, and plotted model values are excluded. Other implementation gaps
include Poisson ratio, full-depth host-rock density, tensile strength, and
exact definitions of Table S3 depth. Axial literature supplies iteration
priors for Poisson ratio and upper-edifice density, but neither replaces the
target study's missing model inputs.
The deep partial reservoir is described at 2.6 km in prose and 2.8 km in Table
S3. These values remain separate source entries until an authoritative written
source resolves them.
