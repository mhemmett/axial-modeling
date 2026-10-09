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
modulus or viscosity as native constitutive laws. The initial scaffold proposed
gridded properties from a steady or separate geotherm as a practical interim
approximation. That approximation omits the fully coupled temperature-mechanics
feedback and is superseded as the final project target by the expanded
independent-recreation scope. It may be used for verification or comparison,
but it cannot be reported as the completed coupled model.

## D005 — Apply failure criteria after the PyLith solve

Tensile and Mohr–Coulomb failure will be evaluated from the Cauchy stress output
in `axialstress.failure`. The stress output will not feed back into PyLith as
damage or plastic strain. Connectivity diagnostics report raw Mohr–Coulomb yield
paths because the written method does not specify tensile strength; those paths
are not eruption thresholds. The unresolved friction-angle convention is
recorded with each analysis rather than treated as a source-defined choice.

## D006 — Require a coupled solver for the final model

The final implementation must represent the coupled thermal and mechanical
feedback described in the written scientific specification. PyLith will solve
the mechanics, coordinated by a Julia or C++ coupling core that advances
thermal state and temperature-dependent properties. Implement a verified PyLith
extension if its existing interfaces cannot exchange state at the required
time steps. Document equations, data exchange, and limiting-case validation.
This decision supersedes the one-way thermal preprocessing plan in the initial
scaffold. See [`ROADMAP.md`](../ROADMAP.md) and
[`comsol_to_pylith.md`](comsol_to_pylith.md).
