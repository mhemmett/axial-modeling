# Decisions

## D001 — Run PyLith natively in the repository

The project uses the provided PyLith 5.0.2 Linux binary extracted under
`pylith/` and a Conda environment at `envs/axial-modeling`. This follows the
owner's setup direction. Docker's client is present but its daemon is
inaccessible to this account; no Apptainer or Singularity binary is available.

## D002 — Use a documented fallback mesh extent

The publisher-served supplement gives reservoir geometries but no model-box
dimensions. The Phase 0 generator therefore defaults to the requested
40 × 40 × 20 km box and records that size as an inferred project assumption.
Replace it only when an allowed written source specifies the model-box extent.

## D003 — Replace the Winkler base in PyLith

PyLith does not list an elastic-foundation base condition among its native
boundary conditions. Phase 1 will use a fixed base and extend the domain until
surface displacement converges. A compliant layer or iterated traction database
would add calibration parameters without evidence from the available paper text.

## D004 — Record the PyLith temperature-coupling limitation

PyLith's documented bulk rheologies do not expose temperature-dependent Young's
modulus or viscosity as native constitutive laws. The written method instead
supports a steady heat solve followed by spatial mapping of temperature-derived
properties into PyLith. A verified workflow must test that mapping and the
resulting mechanics solve; the source does not specify mechanics-to-thermal
feedback. The property handoff is not sufficient by itself to complete the four
rheology comparisons or resolve the missing modulus and branch parameters.

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
