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

Galgana et al. describe the Winkler restoring traction as proportional to
vertical basal displacement, with a separate offset for lithostatic prestress.
Their Venus-specific density contrast does not supply an Axial value. The
supplement's `s = rho V g / Zdisp` is a total spring constant; dividing by the
base area converts it to distributed traction stiffness. With the provisional
Axial upper-edifice density of 2,700 kg/m^3, directed 10 km depth,
9.81 m/s^2 gravity, and `Zdisp = 1e-10 m`, this gives `2.65e18 Pa/m`. Its ratio
to the rough elastic scale `E/H` is `5.30e11–1.32e12` across 50–20 GPa, so it
behaves like a fixed base for displacement response. It does not establish
the Galgana coefficient or the lithostatic prestress offset. PyLith's
documented Neumann condition
accepts prescribed tractions and does not calculate traction from current
displacement. A separate static outer-iteration diagnostic now verifies the
traction sign and solver coupling with an illustrative spring. Retain the
fixed-base substitute in pressure calibration until Axial stiffness and
prestress are specified and the response is validated. See
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
