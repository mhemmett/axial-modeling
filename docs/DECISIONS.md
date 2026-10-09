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
Their Venus-specific density contrast and gravity do not supply Axial values.
The Axial supplement also gives an effective spring formula whose units are
total stiffness, which requires conversion before use as distributed PyLith
traction. Current runs therefore retain a fixed base and label it as a
substitute. Implement the spring only after selecting an Axial density contrast
and initializing a consistent prestress state.

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
