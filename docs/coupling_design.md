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
   displacement response is compared at two seconds. Spatial interpolation to
   a different mesh remains unverified.
2. A custom material integration can update properties inside PyLith. This
   requires a supported extension interface or a separately built extension
   compatible with the provided binary. The project must not rebuild PyLith or
   PETSc from source.

The property laws and one-dimensional solver in `src/axialstress/thermal.py`
are verification components. `src/axialstress/thermal_fem.py` now solves the
steady conduction weak form on linear tetrahedra with caller-supplied Dirichlet
temperatures and Picard updates for temperature-dependent conductivity. Its
manufactured tests verify the linear-geotherm and uniform-source limits. The
operator does not choose the three-dimensional model boundaries, load a
production thermal field, or run a coupled simulation.

`src/axialstress/material_database.py` maps nodal temperatures to cell-centered
Maxwell material properties. It applies the Arrhenius viscosity and derives
wave speeds from caller-supplied Young's modulus, density, and Poisson ratio.
The smoke case first solves a manufactured affine temperature field on the
2,761-tetrahedron mesh, matching the analytic field within `5e-13` °C. PyLith
then accepts the resulting synthetic spatial database and produces finite
stress. The modulus remains explicit because Eq. 16 is internally
inconsistent; the smoke case does not apply that equation. This verifies the
thermal-to-material-to-mechanics data path for an initial mechanical solve, not
thermal-mechanical time stepping or temperature-dependent elasticity.

`src/axialstress/benchmarks.py` evaluates the analytical Mogi spherical-source
displacement on an elastic half-space. Synthetic checks cover center uplift,
radial symmetry, and linear pressure scaling. A bounded PyLith comparison on
3,191 linear tetrahedra produces positive surface uplift and a surface-vector
L2 error of 37.2% relative to the reference. The nearest-axis displacement is
0.626 mm, 33.2% below the analytical value. This coarse result checks the
source sign, units, and numerical path; it does not establish mesh convergence
or validate a production source geometry.

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
nearest-axis error, so mesh refinement remains necessary before using the
comparison as a quantitative validation.

The restart checks use nearest-point spatial-database queries at vertices and
tetrahedron centroids on the same mesh, under fixed 10 MPa cavity traction.
The material-database swap uses Eqs. 15 and 16 at uniform 1200 °C and confirms
the initial viscous-strain state and changed final response. Cross-mesh
interpolation and a time-varying thermal solve remain unverified.

The 3D thermal boundary conditions, model-box extent, Poisson ratio, full
Maxwell spectrum, modulus-law inconsistency, and mechanics-to-thermal return
term are unresolved. OOI BPR records support a comparison from 2014 onward but
do not cover the 1998 and 2011 events. These gaps limit historical hindcasts
and a complete coupled-model claim.

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
