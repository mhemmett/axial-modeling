# Step 05: elastic ellipsoid unit response

This bounded solve calculates the static surface displacement from a 1 MPa
overpressure on the written 6 km × 3 km × 1 km reservoir geometry. The uniform
elastic host uses a 50 GPa Young's modulus, Poisson ratio 0.25, and density
2,700 kg/m³. The paper does not specify all elastic properties, domain
dimensions, or base conditions, so these are setup assumptions.

Run `make ellipsoid-unit-response` to generate the mesh and PyLith fields used
by the Center BPR pressure calibration. The generated mesh and HDF5 files
remain local under `pylith/step05_ellipsoid_elastic/`.

Run `make ellipsoid-mesh-sensitivity` to compare the unit response at fixed
surface locations across global mesh resolutions and local refinements. The
current cases do not meet the 5% compliance-change criterion. Run
`make ellipsoid-base-depth-sensitivity` to compare fixed-base domain depths;
its independently generated meshes are nonnested and do not establish domain
convergence.

This unit-response check supports numerical convergence of the Center BPR
pressure scale. It does not evaluate another observation station, represent a
temperature-dependent rheology, or establish an eruption threshold.
