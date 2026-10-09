# Thermal-field Maxwell smoke case

The step 04 workflow transfers the computed hydrothermal temperature field to
PyLith as cell-centered Maxwell material properties. It exercises the
temperature-to-viscosity path on the same tetrahedral mesh used by the thermal
solve, then advances a bounded two-second cavity-loading case.

Run `make thermal-maxwell-smoke` from the repository root. The target first
rebuilds the baseline and hydrothermal fields with `make thermal-model`, then
writes a material database and PyLith HDF5 outputs under `output/`. Generated
meshes, databases, configuration, logs, and HDF5 files remain local and
untracked.

Viscosity follows the written Arrhenius equation. The smoke run explicitly
sets Young's modulus to 35 GPa, density to 2,700 kg/m³, and Poisson ratio to
0.25 because the written model leaves the latter two material inputs
unspecified and its temperature-dependent modulus equation conflicts with
its description. The Arrhenius values are `AD = 10^9 Pa s`, `EA = 120 kJ/mol`,
and `Rg = 8.3114 J/(mol K)`. The two-second, 10 MPa cavity case is a software
verification input, not an observation fit or historical result.

This is a one-way transfer from a steady thermal solution to mechanics. It
does not update temperature during the PyLith run, implement the unresolved
temperature-dependent modulus, or return mechanical heating to the thermal
equation. It is an integration check, not a complete coupled model.
