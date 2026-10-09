# Hydrothermal temperature mesh sensitivity

The steady hydrothermal field converges in its Picard iteration, but that
iteration does not establish spatial accuracy. `make thermal-mesh-sensitivity`
solves the written zero-source heat equation with Eq. 22 conductivity on three
independently generated ellipsoid meshes and compares temperature at common
points in the host rock.

These historical runs used the 40 × 40 × 20 km setup box, before the project
geometry was corrected to 50 × 50 × 10 km. They used a 6 × 3 × 1 km reservoir
centered 1.6 km below the surface, a far-field mesh size of 10 km, a 30 °C/km
geotherm on all six outer faces, and a 1200 °C reservoir boundary. The
outer-face geotherm remains an assumption because lateral and basal thermal
conditions are not specified. The requested near-size parameter changed from
1200 to 1150 to 1100 m; all historical meshes remained below 3,500
tetrahedra. Rerun this mesh sensitivity on the corrected project geometry
before using its spatial-error values.

The analysis interpolates the nodal temperatures at 24 points along the
vertical profile `x = 5 km, y = 0` and 81 points on the `z = −2.5 km` plane.
All 105 points lie in the host rock. The comparison reports the root-mean-square
(RMSE), median, 95th-percentile, and maximum absolute temperature change for
each adjacent mesh pair. These finite probes do not define a volume-weighted
norm.

| Near-size parameter (m) | Tetrahedra | Picard iterations | Relative energy imbalance |
| ---: | ---: | ---: | ---: |
| 1200 | 2,761 | 10 | `1.15e-11` |
| 1150 | 2,941 | 10 | `1.00e-11` |
| 1100 | 3,060 | 10 | `1.60e-11` |

For the 1200-to-1150 m pair, probe RMSE is 13.45 °C, the 95th-percentile
absolute change is 34.05 °C, and the maximum is 64.61 °C. For 1150-to-1100 m,
the corresponding values are 35.55 °C, 36.96 °C, and 324.29 °C. The largest
change occurs at `(-3, 0, -2.5) km`, near the reservoir edge. The finer mesh
pair therefore does not approach a stable probe field under this unstructured
meshing sequence.

These runs establish nonlinear and heat-balance convergence on each mesh, not
spatial convergence. The tetrahedral meshes are not nested, the common-probe
metrics are sensitive to local gradients, and the outer thermal boundaries
remain assumptions. The result identifies thermal spatial resolution near the
reservoir as an open model check; it does not validate a failure threshold or
use BPR observations or publication-produced data.

Mesh generation at a 1300 m near-size produced no volume tetrahedra because it
did not resolve the thin reservoir. The Gmsh helper now raises an error for an
empty volume mesh instead of reporting that case as a successful zero-element
mesh.

The tracked plot is [`../figures/thermal_mesh_sensitivity.png`](../figures/thermal_mesh_sensitivity.png).
The mesh files, solved fields, and machine-readable JSON summary remain
ignored under `pylith/step03_steady_thermal/` and `data/processed/`.
