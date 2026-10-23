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
failure. Thermal and viscoelastic cases remain. The present elastic result
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
