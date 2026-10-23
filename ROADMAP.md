# Reproduction roadmap

This project independently reproduces Cabaniss et al. (2020) with PyLith in
place of COMSOL. The scientific target is the paper's deformation history,
reservoir pressure and volume changes, stress evolution, failure fields, and
eruption timing. Published numerical results are reproduction targets; they
must not be used to tune unreported parameters until the independent model
predicts them.

The model will use the paper's Center bottom-pressure-recorder (BPR) history
and the four stated rheologies. The implementation may use
the paper and supplement as specifications and numerical references, but it
will not use author code, COMSOL model files, or author-generated model fields.
Report any value that must be inferred because the written source omits it.

## Reproduction sequence

1. Extract the equations, parameter values, BPR forcing, geometry, boundary
conditions, and reported outputs from the article and supplement. Record
conflicts such as the printed temperature-dependent modulus equation and the
friction-angle notation before choosing an implementation.
2. Build the PyLith model with the reported ellipsoid, thermal properties,
four rheologies, tectonic loading, lateral rollers, and basal Winkler
foundation. Reproduce the Mogi, Del Negro, finite-element, and foundation
benchmarks described in the supplement.
3. Apply the Center BPR pressure history across the reported eruption cycles.
Calculate pressure, volume change, stress, and the joint tensile and
through-going Mohr–Coulomb criterion from saved PyLith fields.
4. Refine mesh and time step until displacement, cavity stress, path
   connectivity, and failure onset are stable. Compare the resulting
   temperature-dependent eruption pressure with the paper's reported range of
   12–14 MPa; do not use that range as a calibration constraint.
5. Recreate the numerical panels from project outputs and compare their
quantities with the paper's reported values. State agreement, discrepancy,
and unresolved assumptions for every panel.

## Current blockers

The current implementation has not reproduced the reported failure threshold.
Ellipsoid compliance remains mesh-sensitive, the production pressure fits use
a fixed base, and the static Winkler solve accepts a large initial residual
while tighter solver settings fail. The failure-path onset also shifts with
time-step refinement and paths appear and disappear. Maxwell branch
properties, the modulus law, the friction convention, and several boundary
conditions remain unresolved. The current failure histories use assumed
properties and do not establish an eruption prediction. See
[`docs/KNOWN_ISSUES.md`](docs/KNOWN_ISSUES.md),
[`docs/iteration_parameters.md`](docs/iteration_parameters.md), and
[`docs/run_log.md`](docs/run_log.md) for measured cases and next checks.

## Reproducible delivery

The report and figure inventory must distinguish paper-specified values,
project assumptions, and solver settings. `make reproduce` will be narrowed to
the core model, its numerical verification, Center-BPR forcing, and the
paper-result comparisons. Raw observations and generated PyLith fields remain
local and untracked; source code, configurations, project figures, and the
LaTeX report remain versioned.
