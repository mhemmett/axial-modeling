# Step 07: steady thermal field to PyLith Maxwell viscosity

This smoke test solves steady conduction on the ellipsoid mesh, evaluates the
written Arrhenius viscosity law at tetrahedron centroids, and supplies the
resulting cell-centered properties to a PyLith Maxwell run. The thermal setup
uses zero internal heat production, a 3 W/(m K) conductivity, 0 °C top,
1200 °C cavity, and a 30 °C/km geotherm on the sides and base. Extending the
geotherm to those faces is an explicit boundary assumption.

PyLith uses uniform E = 50 GPa, ν = 0.25, and density = 2700 kg/m³. The printed
temperature-dependent modulus equation remains unresolved, so this check varies
viscosity only. It is a one-way thermal-to-material smoke test; it does not
feed deformation or viscous heating back into the thermal solution and does
not implement the paper's generalized Maxwell branches.

Run `make thermal-maxwell-ellipsoid-smoke`. Meshes, temperature fields,
material databases, and solver outputs remain local and untracked. No OOI
observations or paper-reported results are used.
