# Method-consistent PyLith reconstruction

Axial's bottom-pressure-recorder (BPR) record constrains seafloor uplift, but
the subsurface pressure and stress are model results. **The project will infer
reservoir loading from Center BPR observations and calculate a conditional
failure threshold from converged PyLith stress fields.** Cabaniss et al.
([2020](https://doi.org/10.1038/s41598-020-67043-0)) provide the geometry,
four rheology classes, thermal laws, and tensile plus through-going
Mohr–Coulomb failure sequence. Their numerical pressure and failure curves
serve only as comparisons. The reconstruction may use stated assumptions where
their input specification is incomplete. Every such assumption must accompany
the output it affects. The first completed step fits a post-2011 pressure
history to processed Center observations without joining unknown instrument
datums. It uses a measured PyLith surface response and records the sensitivity
of unobserved intervals to pressure smoothing. A matching elastic mechanics
solve now combines gravity, reference stress, and cavity pressure to screen
failure. Three source-value Maxwell cases and their 2011–2015 pressure and
volume histories are calculated. The elastic result
constrains deployment-relative pressure changes and gives a conditional
failure pressure; neither calculation is mesh-converged.
A stable threshold requires both reservoir tensile failure and a connected
Mohr–Coulomb path in the modeled stress field. If those conditions remain
sensitive to observation gaps or unresolved material properties, the result
will be a bounded conditional estimate rather than a single eruption value.

## Observation-to-pressure baseline

`make paper-bpr` exports candidate processed Center channels from the two
[cited archives](source_audit.md#observation-handling). `make
method-reconstruction` selects the original on-hour observations at seven-day
UTC grid points from 13 April 2011 through 22 April 2015. The chosen start
follows the 2011 eruption deflation maximum in the processed Center record:
1513.092 m at 12:00 UTC on 11 April 2011, within the 14 days after the
eruption. The next observed eruption was on 24 April 2015. The grid stops
before that event. The exported BPR values have already been filtered by their
archives; the script does not create new observations or interpolate gaps.

Each deployment has an unknown absolute depth datum. The inverse problem
therefore fits the change in depth from that deployment's first selected
sample. Depth decreases correspond to uplift. A one-megapascal elastic PyLith
solve gives the surface displacement at each recorded instrument coordinate.
The pressure-to-uplift operator uses that response. The first pressure change
is set to zero on 13 April 2011. A squared second-difference penalty fills
pressure values that the observation differences cannot identify. The nominal
dimensionless penalty is 1; 0.1 and 10 expose sensitivity. These are project
choices, not parameters reported by Cabaniss et al. Neither their predicted
pressure nor their failure pressure enters the fit.

The first local output under `data/processed/method_reconstruction_2011_2015/`
contains the source digests, pressure history, and observation-level residuals.
With the currently exported files and the existing coarse elastic PyLith
response, the three deployment-relative uplift changes are 0.606, 0.608, and
1.133 m. Their static elastic pressure equivalents are 21.9, 21.9, and
39.8 MPa. The nominal fit has 0.0222 m root-mean-square residual. Five of
210 pressure parameters lack independent constraints in the observation
design. The last pre-eruption pressure changes are 61.8, 73.4, and 83.3 MPa
for penalties 0.1, 1, and 10. This range measures sensitivity to one
regularization choice; it is neither an uncertainty interval nor a tested
eruption threshold. The pressure values also depend on the zero-change
baseline and fixed-base, coarse-mesh elastic response. A finer mechanics
solution and source-channel review may change them.

## Conditional elastic stress screen

`make method-failure-screen` reruns the cited BPR export and bounded PyLith
gravity/reference-stress and one-megapascal cavity cases. It refits pressure
with the surface response from the same 2,505-tetrahedron mesh used for stress.
The cavity traction includes lithostatic pressure plus the pressure change,
as in supplement Eq. 24. The fixed base approximates the paper's extremely
stiff Eq. 23 spring. The reference state uses a 2,940 kg/m³ depth-averaged
density, 9.81 m/s² gravity, 50 GPa Young's modulus, and Poisson ratio 0.25.
The modulus is Table S1's brittle end member. Poisson ratio and the density
profile are project assumptions. Ridge-normal tectonic loading and
viscoelastic memory are absent from this elastic case.

The screen adds each fitted pressure change times the PyLith one-megapascal
stress increment to the gravity-equilibrated Cauchy stress. A reservoir cell
must have positive maximum principal stress for zero tensile strength; the
alternate cutoffs are 0.1 and 2.5 MPa. Through-going Mohr–Coulomb failure
requires a face-connected path from the cavity to the seafloor with 1 MPa
cohesion, 25° friction angle, and zero pore pressure. Cohesion and friction
angle come from Table S1; the tensile and pore-pressure choices are stated
assumptions. The first pressure scan spans 0–100 MPa at 0.5 MPa increments,
independent of the published failure pressure.

On this mesh, joint failure first occurs in the 17.5–18.0 MPa bracket with
zero or 0.1 MPa tensile strength. A 2.5 MPa cutoff moves the bracket to
19.0–19.5 MPa. A connected shear path first appears near 15.37 MPa, before
the zero-strength tensile threshold. Cabaniss et al. report those conditions
as coincident in their modeled eruption state. The detected path has only
three tetrahedra, although no cell touches both cavity and seafloor. Its
short length reinforces the need for mesh refinement. The three BPR smoothing
choices give last pre-2015 pressure
changes of 45.1, 53.5, and 60.7 MPa. Their nominal zero-strength joint
crossings occur between August 2011 and February 2012, before the observed
2015 eruption. The nominal pressure fit has 0.0222 m root-mean-square BPR
residual. The values are local model outputs under
`data/processed/method_failure_screen_2011_2015/`; the file records checksums
for the fit and both stress states. These early crossings show that this
elastic assumption set does not reproduce 2015 timing. They do not establish
a reliable Axial threshold: the mesh under-resolves cavity shape, and the
temperature-dependent cases, time integration, initial viscoelastic state,
and parameter sensitivity remain unresolved.

## Elastic mesh refinement

`make method-mesh-refinement` repeats the gravity-equilibrated fixed-base
calculation at 400, 250, and 150 m near-cavity mesh sizes. These spacings
reduce the cavity's polyhedral volume error; they were chosen as geometric
refinements, without using a published pressure or failure result. Each run
uses the same cited BPR observations, constitutive choices, and failure
criterion. The command preserves the three PyLith basis fields, pressure fits,
failure summaries, and a checksum-verified comparison under `data/processed/`.
Each PyLith solve uses eight ranks and `timeout 300`.

| Near-cavity size | Tetrahedra | Cavity volume deficit | Nominal pre-2015 pressure | First shear path | Joint pressure bracket, zero strength | Path cells |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 400 m | 8,192 | 4.32% | 23.54 MPa | 12.52 MPa | 13.00–13.05 MPa | 7 |
| 250 m | 15,491 | 1.72% | 21.95 MPa | 12.28 MPa | 12.25–12.30 MPa | 12 |
| 150 m | 33,980 | 0.66% | 21.46 MPa | 12.07 MPa | 12.05–12.10 MPa | 17 |

The table uses 0.05 MPa joint-failure brackets refined from a 0.5 MPa scan.
From 250 to 150 m, the last pre-eruption pressure changes by 0.49 MPa and
the first shear-path pressure by about 0.20 MPa. The path also gains five
cells. Mechanical convergence is therefore not established. The nominal
150 m BPR history crosses joint failure on 21 November 2012, still well
before the 2015 eruption. Although its pressure bracket overlaps the
published temperature-dependent range, this run is elastic and its timing
disagrees. That overlap does not establish a reproduction or justify tuning
another input toward the published result.

## Source-value thermal Maxwell cases

Run `make method-mesh-refinement` first to generate the local 400 m and 150 m
gravity-equilibrated basis files. `make method-source-maxwell` maps the
supplement's steady thermal laws onto the 150 m near-cavity mesh, writes
one-branch Maxwell properties, and
compares a 14-day PyLith pressure ramp at seven-day and one-day mechanical
steps. The baseline thermal case uses `k0 = 3 W/(m K)`. The hydrothermal case
uses Eq. 22 with `Nu = 8`, `A = 0.75`, `Tmax = 600 °C`, and `zmax = 6 km`.
Both use zero heat production, a 1200 °C cavity, and the 30 °C/km external
geotherm. The lateral and basal geotherm remains an explicit boundary
assumption. Eq. 15 uses `AD = 10^9 Pa s`, `EA = 1.2 × 10^5 J/mol`, and
`Rg = 8.3114 J/(mol K)`, with kelvin at the exponential. The modulus is
Eq. 16 literally as printed, with Table S1's `ED = 25 GPa`, `EB = 50 GPa`,
`AS = 12`, and `CS = 5`. That equation increases modulus with temperature,
contrary to the supplement's brittle and ductile labels. The property maps
therefore test one documented reading of the source equation; they do not
resolve its conflict with the accompanying text.

On the 33,980-tetrahedron mesh, Eq. 16 gives 25.0–33.3 GPa. Eq. 15 gives
minimum cell viscosity of 1.80 × 10^13 Pa s and minimum Maxwell time of
1,354 s in both thermal cases. The seven-day mechanical step is about 447
times that minimum. At day 14, the incremental stress fields differ by
2.34% for baseline conduction and 1.77% for hydrothermal conduction in
relative L2 norm between seven-day and one-day steps. These are measured
short-window step sensitivities, not temporal convergence of the four-year
BPR history.
Repeating the same 14-day comparison on the 8,192-tetrahedron BPR mesh gives
2.03%, 2.11%, and 1.84% for uniform, thermal, and hydrothermal Maxwell cases,
respectively.
The 400 m repeat uses:

```bash
make method-source-maxwell METHOD_SOURCE_MAXWELL_ARGS='--mesh data/processed/refined_elastic_basis_400m/axial_ellipsoid.msh --equilibrium data/processed/refined_elastic_basis_400m/fixed-base-equilibrium-material.h5 --output-dir data/processed/source_value_maxwell_cases_400m'
```

`make method-source-time-steps` reuses the BPR-fit material maps on the 400 m
mesh. It applies the same linear 0–1 MPa pressure ramp over seven days at
seven-day, one-day, six-hour, one-hour, and 30-minute PyLith steps. The finest
step is still about 1.33 times the shortest cell Maxwell time. The sweep
measures the final stress field and central surface compliance against that
30-minute result; it cannot establish convergence of the four-year BPR fit.
Relative final incremental stress differences from the 30-minute result are
6.75%, 1.62%, 1.55%, and 1.58% for the thermal case at seven-day, one-day,
six-hour, and one-hour steps. They are 8.41%, 6.52%, 6.30%, and 4.69% for
the hydrothermal case. The nonmonotonic sequence and the shortest-step to
Maxwell-time ratio prevent a convergence claim.

`make method-source-bpr-failure` uses the 400 m near-cavity mesh and fits
each Maxwell case's PyLith unit-ramp uplift to the same deployment-relative
2011–2015 Center BPR observations. It forwards each fitted pressure history
through PyLith and adds the gravity-equilibrated reference stress on the
identical mesh before checking reservoir tension and a face-connected
Mohr–Coulomb path. The fit uses the same three stated curvature weights as
the project's elastic baseline. Outputs preserve the material maps, source hashes,
PyLith stress files, fitted pressure series, and failure flags locally under
`data/processed/`.

`make method-source-threshold` scales each complete fitted pressure path and
checks its final PyLith stress state from 0 to 200 MPa. The scan uses only
local PyLith results; the published failure pressure does not set its inputs.
The final-state bracket is a mathematical continuation of the fitted loading
shape, not a calibrated eruption pressure. The same 1 MPa cohesion and 25°
friction angle apply as in the elastic screen. Zero, 0.1, and 2.5 MPa tensile
strength cases share each bracket because the connected shear path controls
this particular scan.

| Case | BPR fit RMSE | Last pre-2015 fitted pressure | Final cavity principal stress | Connected path at fitted pressure | Final-state joint bracket |
| --- | ---: | ---: | ---: | --- | ---: |
| Uniform Maxwell | 0.02287 m | 0.805 MPa | −18.93 MPa | No | 12.40–12.45 MPa |
| Thermal Maxwell | 0.02218 m | 3.16 MPa | −21.28 MPa | No | 150.05–150.10 MPa |
| Hydrothermal Maxwell | 0.02222 m | 5.02 MPa | −22.09 MPa | No | 139.15–139.20 MPa |

These results use 8,192 tetrahedra and a zero post-2011 pressure-change
baseline. Each observation design has rank 205 for 210 pressure parameters;
the remaining five dimensions depend on curvature smoothing. The
fitted-pressure ranges across the three smoothing weights are 0.583–0.862 MPa,
2.59–3.62 MPa, and 4.12–5.77 MPa, respectively. The zero-strength joint
brackets require about 15.5, 47.5, and 27.7 times the fitted final pressures.
At those scales, PyLith reports cavity principal tensions of about 261, 832,
and 417 MPa, respectively, and paths of six, nine, and eight cells. The
uniform case's numerical bracket overlaps the paper's 12–14 MPa
temperature-dependent result, but it has the wrong rheology, requires 15.5
times its BPR-fitted loading, and never reaches joint failure in the fitted
history. It is not a reproduction. Extrapolating the linear
model that far exceeds what the BPR loading constrains. These brackets are
therefore numerical diagnostics, not physical eruption thresholds. None of the
fitted cases reaches the paper's joint failure condition before the observed
2015 eruption under the present assumptions.

The source-volume target integrates each saved PyLith cavity displacement
field over the matching Gmsh cavity faces. The last first-order volume changes
are 0.02281, 0.04300, and 0.03995 km³ for uniform, thermal, and hydrothermal
Maxwell cases, respectively. These are calculated changes relative to the
initial meshed cavity, not digitized paper outputs. The source-figure3 target
plots property sections in the paper's Figure 3 layout. The source-figure4
target plots fitted pressure, calculated volume, and separate actual BPR
deployment segments in its Figure 4 layout. The generated PDF and PNG files
live under figures/. Their report captions identify model choices and
observation datums. The report follows the
[Lipovsky academic style guide](https://github.com/bradlipovsky/vdv-damage/blob/main/brad-lipovsky-academic-style-guide.md)
at the owner's request.
The modeled pressure drop near the 2013 deployment change is chosen across
unresolved instrument datums. It is not a continuous observed deflation
record, and the associated calculated volume drop inherits that ambiguity.

PyLith's one-branch Maxwell law is a reconstruction choice. The paper describes
a generalized Maxwell spectrum but does not publish its branch fractions.
Its Figure 3 explicitly labels the non-temperature-dependent viscoelastic
viscosity as `10^16 Pa s`, although Table S1 omits it. Figure 3's uniform
Young's modulus color is consistent with 60 GPa, which Table S1 lists for
the analytical solution; applying 60 GPa to the FEM remains a documented
figure-reading choice. The zero initial viscous strain, Poisson ratio 0.25,
2,940 kg/m³ density, fixed base, and added reference equilibrium stress are
also choices that must be varied before using the calculation as a stable
failure threshold. Seven-day BPR steps are longer than the shortest
source-value relaxation time near the hot reservoir. The run reports the
time-step ratio and its short-window comparison; a four-year fitted failure
time remains preliminary until temporal convergence is shown. The thermal
property conflict, unpublished Maxwell spectrum, unresolved initial
overpressure, and narrow connected paths remain additional barriers to an
independent failure-threshold estimate.

## Route to a failure threshold

First, retain deployment-specific observations and quantify pressure
sensitivity to the unobserved intervals and initial state. A fit with large
gap sensitivity cannot identify a unique pressure at the 2015 event. Second,
extend the elastic screen to the paper's remaining rheology classes in PyLith
using the documented
temperature, geometry, gravity, cavity loading, lateral rollers, and basal
spring prescription. Inputs absent or contradictory in the paper must be
fixed before looking at its model outputs and varied over stated ranges.
Third, recompute the Center pressure operator for each rheology and forward
run its fitted loading. Inspect saved cavity-wall displacement for volume
change and saved cell stress for tensile failure at the reservoir and a
connected Mohr–Coulomb path to the seafloor. Report the first time both
conditions hold and the corresponding fitted pressure, with mesh, timestep,
initial-state, datum-gap, and strength sensitivity. Do not label a threshold
stable until those numerical and assumption sensitivities are resolved.

A threshold near the published value would support this set of PyLith
assumptions. A different stable threshold would identify a model difference
worth explaining. If gap or material sensitivity remains broad, the BPR
record alone does not support a single stress-failure pressure. These outcomes
all clarify how far BPR data can constrain volcanic failure at Axial.
