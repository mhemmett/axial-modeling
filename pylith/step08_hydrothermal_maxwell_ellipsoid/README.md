# Step 08: hydrothermal conductivity and Maxwell viscosity

This diagnostic solves steady heat conduction with the temperature- and
depth-dependent conductivity in Eq. 22, then transfers the written Arrhenius
viscosity in Eq. 15 to a PyLith Maxwell run. The tetrahedral finite-element
solver updates conductivity by Picard iteration until the temperature field
converges.

The run uses the same zero-source, 0 °C top, 1200 °C cavity, and 30 °C/km
side/base boundary assumptions as Step 07. Equation 22 uses `k0 = 3 W/(m K)`,
`Nu = 8`, `A = 0.75`, a 600 °C cutoff, and a 6 km cutoff depth. PyLith holds
Young's modulus at 50 GPa, Poisson's ratio at 0.25, and density at 2700 kg/m³.
The thermal solution is transferred once; deformation and viscous heating do
not update temperature.

`make eq16-hydrothermal-maxwell-ellipsoid-smoke` evaluates the printed Eq. 16
modulus on the same field as a source-conflict diagnostic. See
[`../step10_eq16_modulus_diagnostic/README.md`](../step10_eq16_modulus_diagnostic/README.md)
for its interpretation.

Run `make hydrothermal-maxwell-ellipsoid-smoke`. Meshes, temperature fields,
material databases, and solver outputs remain local and untracked. The check
uses no observations or paper-reported results and does not reproduce the
coupled hydrothermal rheology.
