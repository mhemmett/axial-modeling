# Decisions

## D001 — Run PyLith natively in the repository

The project uses the provided PyLith 5.0.2 Linux binary extracted under
`pylith/` and a Conda environment at `envs/axial-modeling`. This follows the
owner's setup direction. Docker's client is present but its daemon is
inaccessible to this account; no Apptainer or Singularity binary is available.

## D002 — Use the project-directed model extent

The written supplement gives reservoir geometries but no model-box dimensions.
The project owner has directed a 50 × 50 km horizontal box extending from the
seafloor to 10 km depth. Both cavity-mesh generators use this extent; the
parameter record distinguishes this project instruction from a
paper-specified value.

## D003 — Keep the Winkler base explicit in PyLith comparisons

Galgana et al. describe a restoring basal force proportional to asthenosphere
density, gravity, and vertical displacement, with a separate offset for
lithostatic prestress. Regional Juan de Fuca gravity models use 3,300 kg/m^3
upper-mantle density and a 6 km crust; their along-axis starting model uses
2,700 kg/m^3 crustal density. Applying those values to the owner-directed
10 km box gives `k_W = 32,373 Pa/m` and a layered basal support reference of
`288.414 MPa` upward. These are regional priors, not Axial column measurements.
The supplement's `s = rho V g / Zdisp` remains a separate benchmark: dividing
by the base area gives `2.65e18 Pa/m` under the provisional upper-edifice
density assumption, effectively the fixed-base limit. PyLith's documented
Neumann condition accepts prescribed tractions and does not calculate
traction from current displacement. The static outer-iteration diagnostic
uses the regional finite coefficient and initializes gravity and the absolute
reference stress with a homogeneous `2940 kg/m^3` column density. This
preserves the integrated `288.414 MPa` basal load from the layered regional
prior while approximating its intermediate depth profile. Pressure and
tectonic increments are evaluated on that equilibrium. Keep the production
pressure-calibration base fixed until the finite-spring response is validated
against mesh and analytical benchmarks. See
[`winkler.py`](../src/axialstress/winkler.py), `make winkler-scale`, and
`make winkler-foundation-check`.

## D004 — Record the PyLith temperature-coupling limitation

PyLith's documented bulk rheologies do not expose temperature-dependent Young's
modulus or viscosity as native constitutive laws. The written method instead
supports a steady heat solve followed by spatial mapping of temperature-derived
properties into PyLith. The project owner specified a 20–50 GPa modulus range
for the current four-case run, implemented as a linear decrease from 50 GPa at
0 °C to 20 GPa at 1200 °C. This interpolation is a project assumption while
Eq. 16 remains inconsistent with its brittle and ductile labels. The source
does not specify mechanics-to-thermal feedback or the generalized Maxwell
branch spectrum.

## D005 — Apply failure criteria after the PyLith solve

Tensile and Mohr–Coulomb failure will be evaluated from the Cauchy stress output
in `axialstress.failure`. The stress output will not feed back into PyLith as
damage or plastic strain. Connectivity diagnostics report raw Mohr–Coulomb yield
paths because the written method does not specify tensile strength; those paths
are not eruption thresholds. The unresolved friction-angle convention is
recorded with each analysis rather than treated as a source-defined choice.

## D006 — Couple steady thermal properties to mechanics

The written method solves a steady thermal field, then uses temperature to set
mechanical properties. It specifies no mechanics-to-heat return term. The
implementation will verify the thermal solve, property mapping, and resulting
PyLith response as one temperature-to-mechanics workflow. It will not add an
unsupported feedback law or require runtime property updates unless an allowed
written source specifies them. See [`ROADMAP.md`](../ROADMAP.md) and
[`comsol_to_pylith.md`](comsol_to_pylith.md).

## D007 — Orient the ellipsoid to the reported Axial strike

The supplementary geometry describes a horizontal reservoir striking N30°W.
Both project mesh generators use x east, y north, and z up, so the ellipsoid's
long axis is rotated 120° counterclockwise from east before the cavity cut.
The 50 km × 50 km × 10 km project box remains fixed by owner direction.

## D008 — Use the paper's verification categories without inventing a threshold

The target study reports analytical and finite-element compatibility checks
and a Winkler-versus-roller comparison, but gives no numerical convergence
tolerance or mesh/time refinement rule. Project convergence will follow those
verification categories, using independent references and project-generated
outputs. BPR misfit will assess model performance separately. See
[`iteration_parameters.md`](iteration_parameters.md).
