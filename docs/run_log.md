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
| Cavity volume integration, 23 October 2026 | The original Gmsh cavity has 138 triangles and a 6.13530618 × 10⁹ m³ polyhedral volume. The ideal 6 × 3 × 1 km ellipsoid is 9.42477796 × 10⁹ m³. PyLith's boundary output has 142 triangles and eight non-manifold edges. One prototype step produces 270,384.46 m³ geometric volume change versus 270,383.17 m³ first-order change. | The integration code maps PyLith displacement to the original closed Gmsh boundary. The 34.90% reference-volume deficit rules out this coarse mesh for Fig. 4b. |
| Processed Center archive export, 23 October 2026 | Eight locally available source files yielded 133,149 on-hour depth samples. Fox's missing LPF values were omitted, and gaps and file checksums were recorded. Peak observed host memory use was 7.96% with eight assigned CPUs. | The export preserves source observations separately. A common deployment datum and the paper's channel choice are still unverified. |
| Cavity geometry refinement, 23 October 2026 | Gmsh near-cavity sizes 1,200, 1,000, 700, 400, and 250 m produced 2,499, 2,879, 4,248, 8,224, and 15,423 tetrahedra. Polyhedral cavity volumes are 6.1353, 6.3182, 7.7372, 9.0180, and 9.2627 × 10⁹ m³, against the ideal 9.4248 × 10⁹ m³. | Signed volume deficits fall from 34.90% to 32.96%, 17.91%, 4.32%, and 1.72%. This is geometry-only refinement; no refined PyLith displacement or stress result exists. Meshes and checksum reports remain ignored under `data/processed/geometry_refinement/`. |

The geometry sweep used `meshing/axial_ellipsoid_bpr.py` with
`--lc-far 10000` and each listed `--lc-near` value on the prototype
50 × 50 × 10 km box. `scripts/cavity_geometry_report.py` calculated every
polyhedral volume from the generated Gmsh cavity faces. No paper output
curve entered the calculation.

## Reproduction interpretation

The current four-case pressure script uses one Center BPR history per event.
The 1998 and 2011 event-window fits include observed eruption deflation and
later observations, so they are retrospective diagnostics. The Maxwell branch
values, modulus mapping, friction interpretation, pore pressure, and tensile
strength remain unresolved or assumed. No stable failure onset has been
established.

`make reproduction-status` reports the source requirements. `make reproduce`
stops until the paper's full experiment is implemented. Add the revision,
runtime, solver output, mesh identity, and comparison values to this file
when recording a new reproduction checkpoint.
