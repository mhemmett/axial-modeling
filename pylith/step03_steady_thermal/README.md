# Three-dimensional steady thermal field

The step 03 workflow solves the zero-source steady conduction equation on the
ellipsoidal-reservoir tetrahedral mesh. It runs a constant-conductivity
baseline and a temperature-dependent hydrothermal conductivity case.

Run `make thermal-model` from the repository root. The script generates the
mesh and saves `steady_thermal_baseline.npz` and
`steady_thermal_hydrothermal.npz` with their solver logs under `output/`.
Each archive contains vertices, tetrahedra, nodal and cell-centered
temperatures, cell conductivity, prescribed boundary values, and convergence
and heat-balance diagnostics. Generated files remain local and untracked.

The mesh is a 40 km × 40 km × 20 km box with a 6 km × 3 km × 1 km ellipsoidal
reservoir centered 1.6 km below the surface. The reservoir surface is fixed at
1200 °C. The 30 °C/km background geotherm is applied on the top, bottom, and
four lateral faces. Extending it to the bottom and lateral faces is an
explicit assumption because those thermal boundary conditions are not fully
specified. The hydrothermal case uses the written conductivity law; the
baseline uses constant conductivity of 3 W/(m K). Both use zero internal heat
production.

The tetrahedral solver checks the free-node residual and integrated boundary
heat balance after convergence. These fields are thermal-only inputs for later
model development; this step does not update PyLith material properties or
solve mechanics.
