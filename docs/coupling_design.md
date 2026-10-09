# Thermomechanical coupling design

## Evidence from the written method

The supplement solves steady-state heat conduction with `Q = 0`, then uses
temperature-dependent viscosity and Young's modulus in the mechanical model.
It does not define a heat source from strain, stress, viscous dissipation, or
reservoir pressurization. The source-supported thermal calculation therefore
does not receive a mechanical feedback term. Adding one would change the
scientific model and requires a separate physical specification.

The current roadmap asks for a coupled core that advances thermal state and
updates mechanics. That is stricter than the feedback described in the
available written formulation. The project will preserve this discrepancy
instead of inventing a heat-production law to satisfy the implementation
target. A fully two-way run cannot be called a paper reproduction without a
written basis for its return coupling.

## PyLith interface evidence

PyLith 5.0.2 accepts material properties and initial values for material state
variables through the material auxiliary-field spatial database when a run is
initialized. Its documented Maxwell models accept viscosity parameters and
track viscous-strain state variables, and `OutputPhysics` can write state
variables alongside stress and strain. PyLith's documented time-dependent
spatial databases apply to boundary-condition values; the material interface
does not document a runtime callback for replacing temperature-dependent
properties during a solve.

This leaves two implementation paths to investigate:

1. A staggered external driver can solve a thermal increment, write a new
   material database, run PyLith over a mechanical increment, and transfer the
   final displacement and Maxwell state into the next run's initial databases.
   The same-mesh transfer now matches a continuous PyLith solve in the bounded
   case described below. A separate restart swaps in a synthetic material
   database generated from a uniform 1200 °C field with Eqs. 15 and 16. Its
   viscous strain at the one-second segment boundary matches the transferred
   state exactly, and its final displacement differs by 50.08% from the
   uniform-property run. The boundary snapshot is checked for viscous strain;
   displacement response is compared at two seconds. Synthetic cross-mesh
   point sampling is now verified, but transfer of a physical temperature
   history and properties that vary during a solve remain unverified.
2. A custom material integration can update properties inside PyLith. This
   requires a supported extension interface or a separately built extension
   compatible with the provided binary. The project must not rebuild PyLith or
   PETSc from source.

The property laws and one-dimensional solver in `src/axialstress/thermal.py`
are verification components. `src/axialstress/thermal_fem.py` solves steady
conduction on linear tetrahedra with Dirichlet temperatures and Picard updates
for temperature-dependent conductivity. Its manufactured tests verify the
linear-geotherm and uniform-source limits. The `thermal-model` workflow now
applies this operator to the ellipsoidal-reservoir mesh for constant and
temperature-dependent conductivity. It fixes the reservoir at 1200 °C and
extends a 30 °C/km geotherm to the bottom and four side faces because their
thermal conditions are unspecified. These outer-face values are explicit
modeling assumptions, not measured boundary data. The output is a thermal
field only; the workflow does not yet feed that field into a mechanical solve.

`src/axialstress/material_database.py` maps nodal temperatures to cell-centered
Maxwell material properties. It applies the Arrhenius viscosity and derives
wave speeds from caller-supplied Young's modulus, density, and Poisson ratio.
The cross-mesh smoke case first transfers a manufactured affine temperature
field with `1.14e-13` °C maximum error. It then solves the written hydrothermal
model on a 3,060-tetrahedron ellipsoid mesh and samples temperature at the
2,761 cell centers of a distinct mechanics mesh. All target samples are finite
and span 8.769–1,066.240 °C. PyLith accepts the mapped material database and
produces finite stress and viscous strain in a bounded two-second solve, with
peak stress `1.75811e7 Pa`. The smoke case uses a depth-varying 35 GPa reference
modulus, density 2,800 kg/m³, and Poisson ratio 0.25; it does not apply Eq. 16,
which remains internally inconsistent. This verifies transfer of a physical
steady temperature field to an initial mechanical solve, not conservative
transfer, thermal-mechanical time stepping, or temperature-dependent
elasticity.

`write_generalized_maxwell_database` writes PyLith's three-branch viscosity,
shear-fraction, and branch-state fields. The Step 12 smoke solves the steady
zero-source temperature field with Eq. 22 conductivity, scales three synthetic
branch reference viscosities with Eq. 15, and advances a two-year PyLith run.
The Arrhenius material values vary by cell, but the thermal field remains
fixed during mechanics. This verifies one-way transfer through all three
branches; it does not resolve the paper's branch fractions or relaxation
spectrum, or implement runtime temperature updates or feedback.

The Step 12 checker independently reconstructs Cauchy stress from saved total
strain and all three branch states using PyLith's Eqs. 88–90. Across 25 saved
times in the temperature-dependent case, its relative L2 difference from
PyLith stress is `1.99e-16`. The largest saved interval is `2.592e6 s`, below
one-fifth of the minimum cellwise `1.0e8 s` relaxation time. This confirms consistency of the material database, state
fields, and stress output under the documented update rule; it does not verify
time-step convergence or determine the paper's missing spectrum. See the
[PyLith 5.0.2 generalized Maxwell formulation](https://pylith.readthedocs.io/en/v5.0.2/user/governingeqns/elasticity/bulk-rheologies/linear-genmaxwell.html).

The historical extension drives the same three-branch material with raw
Center pressure histories inferred through static ellipsoid compliance for the
1998 and 2011 deployment overlaps. It predicts Center and held-out South daily
uplift, using first-common-day zeroing and synthetic branch viscosities and
fractions. This tests the historical loading path against separate raw
stations across the 1998 and 2011 eruptions and four additional 1995–2013
deployment overlaps. Event-window South biases are `+0.329 m` and `+0.371 m`;
the 2011–13 overlap has `1.242 m` RMSE and `−1.214 m` bias despite `0.991`
correlation. Pressure spans reach `−94.4` and `−72.8 MPa`, and static
compliance remains mesh-sensitive. Raw records are uncorrected for tides,
ocean variability, and drift. The checks extend temporal coverage but remain
forward diagnostics, not hindcasts or forecasts.

`src/axialstress/benchmarks.py` evaluates the analytical Mogi spherical-source
displacement on an elastic half-space. Synthetic checks cover center uplift,
radial symmetry, and linear pressure scaling. A bounded PyLith comparison on
3,191 linear tetrahedra samples the surface field on a fixed 41 × 41 grid by
triangle interpolation. The interpolated-axis error is 33.6%, and the
fixed-grid vector L2 error is 40.4% relative to the reference. This coarse
result checks the source sign, units, and numerical path; it does not establish
mesh convergence or validate a production source geometry.

## Verification sequence

First, test the extracted viscosity and conductivity functions against their
limiting values and unit conversions. The printed modulus relation is kept in
an explicitly named diagnostic function because it conflicts with the stated
brittle and ductile modulus values; it is not suitable for a production run.
Second, verify steady conduction against analytical 1D solutions and a
manufactured variable-conductivity case. Third, write and read a Maxwell state
through PyLith's auxiliary databases across two one-second runs. On the 2,761
tetrahedron mesh, displacement, Cauchy stress, total strain, and viscous strain
at two seconds agree with a continuous run to a maximum normalized difference
of `1.612e-8`. A separate material-database swap carries viscous strain across
the segment boundary with zero relative error and changes final displacement
by 50.08% against the uniform-property run. The swap uses a synthetic uniform
1200 °C field; it verifies database replacement, not a physical temperature
history or thermal feedback. Lastly, compare PyLith's elastic response with the
Mogi reference on a bounded mesh. The 3,191-tetrahedron case retains a 33.2%
nearest-axis error, 33.6% interpolated-axis error, and 40.4% fixed-grid vector
L2 error. Increasing horizontal half-width and bottom depth from 8 km to 12 km
raises vector error to 58.0% and reduces peak uplift by 61.4%. These
independently generated meshes are not nested, so the comparison does not
isolate boundary effects. Both remain too inaccurate for quantitative
validation, and domain and mesh convergence remain necessary.

The restart checks use nearest-point spatial-database queries at vertices and
tetrahedron centroids on the same mesh, under fixed 10 MPa cavity traction.
The material-database swap uses Eqs. 15 and 16 at uniform 1200 °C and confirms
the initial viscous-strain state and changed final response. The step 04 smoke
case also checks transfer of the computed steady hydrothermal temperature
field into cell-centered PyLith viscosity on the same mesh. The cross-mesh
smoke uses tetrahedral barycentric coordinates to sample source temperature at
mechanics element centers. Its affine manufactured case checks interpolation
accuracy; the physical hydrothermal case confirms mesh coverage and PyLith
database use. Points outside the thermal mesh fail explicitly. Neither check
establishes conservative transfer. Time-varying properties and
mechanics-to-thermal feedback remain unverified.

The 3D thermal boundary conditions, model-box extent, Poisson ratio, full
Maxwell spectrum, modulus-law inconsistency, and mechanics-to-thermal return
term are unresolved. OOI BPR records support comparisons from 2014 onward;
uncorrected historical BPR channels provide event-window checks for 1998 and
2011, not the continuous multiyear histories needed for the full hindcasts.
These gaps limit the historical model and a complete coupled-model claim.

## PyLith references

- [Initial conditions, PyLith 5.0.2](https://pylith.readthedocs.io/en/v5.0.2/user/problems/problems.html):
  initial material state variables are supplied in material auxiliary-field
  databases.
- [Elasticity auxiliary fields, PyLith 5.0.2](https://pylith.readthedocs.io/en/v5.0.2/user/physics/materials/elasticity.html):
  lists Maxwell properties and viscous-strain state variables.
- [Output, PyLith 5.0.2](https://pylith.readthedocs.io/en/v5.0.2/user/problems/output.html):
  describes HDF5 output and solution/state observers.
- [Time-dependent boundary conditions, PyLith 5.0.2](https://pylith.readthedocs.io/en/v5.0.2/user/physics/bc/time-dependent.html):
  describes time-dependent boundary data; this interface does not apply to
  material properties.
