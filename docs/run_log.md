# Numerical run record

This log keeps bounded evidence relevant to the PyLith reproduction. Raw
observations, meshes, generated fields, and per-run data remain under ignored
local directories.

## Current implementation evidence

| Check | Result | Interpretation |
| --- | --- | --- |
| Corrected elastic cavity smoke | 2,499 tetrahedra; 0.296 m peak uplift. | PyLith reads the mesh and writes finite displacement and stress fields. |
| Mogi compatibility | Current 2,995-element case: 44.9% vector-field error and 55.9% center error. A nearby refined case: 42.7% and 54.2%. | The nonnested mesh sequence does not establish convergence. |
| Thermal mesh sensitivity | Sampled temperature changes reach 324 °C near the reservoir between bounded meshes. | The nonnested meshes do not establish a volume-norm convergence rate. |
| Finite Winkler solve | Regional spring prior is 32,373 Pa/m. Initial SNES residual is 5.40e3 and is accepted at iteration zero under a 1.00e4 tolerance. | Tighter settings previously failed in KSP. The main pressure calibration still uses a fixed base. |
| Static failure screen | No connected reservoir-to-surface path at 12–14 MPa under the current proxy for either basal treatment. | The reported failure threshold remains unreproduced. |

## Reproduction interpretation

The current four-case pressure script uses one Center BPR history per event.
The 1998 and 2011 event-window fits include observed eruption deflation and
later observations, so they are retrospective diagnostics. The Maxwell branch
values, modulus mapping, friction interpretation, pore pressure, and tensile
strength remain unresolved or assumed. No stable failure onset has been
established.

Run `make reproduce` to rebuild the component checks, benchmarks, Center BPR
event calibrations, time-step refinement, and report. Add the revision,
runtime, solver output, mesh identity, and comparison values to this file when
recording a new reproduction checkpoint.
