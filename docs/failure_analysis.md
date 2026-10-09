# Failure-threshold postprocessing

The written method identifies an eruptible state with tensile failure at the
reservoir and a modeled eruption with a connected Mohr–Coulomb path from the
reservoir to the surface. This diagnostic applies those definitions to a
completed PyLith stress field; it does not alter the mechanical solution.

`axialstress.failure` converts PyLith stress components ordered `xx, yy, zz,
xy, yz, xz` into symmetric tensors using the tensile-positive convention. Its
Mohr–Coulomb yield function uses compression-positive effective principal
stresses, cohesion `C`, and friction angle `phi`:

`F = sigma_1 - sigma_3 - (sigma_1 + sigma_3) sin(phi) - 2 C cos(phi)`.

Cells with `F >= 0` count as shear-yield cells. `axialstress.topology`
identifies tetrahedra touching the box boundaries and the remaining interior
boundary, treated as the cavity. It then searches for a path across failed
tetrahedra that share triangular faces. Edge-only and vertex-only contact do
not count as connected.

The source calls `f = 25°` an internal friction angle, but its printed
criterion multiplies `f` by normal stress as though `f` were a coefficient.
The smoke case uses 25° directly as `phi`; this is an explicit diagnostic
convention, not a resolved interpretation of the source. Pore pressure enters
the effective stress for shear yield. The report also gives the largest
tensile principal stress among cavity-adjacent cells as a candidate tensile
strength threshold. The source does not supply tensile strength, so the smoke
case does not apply a tensile cutoff to the shear path or claim an eruption
threshold.

Run `make failure-connectivity-smoke` to generate the synthetic Mogi stress
field and analyze it with cohesion `1 MPa`, `phi = 25°`, and zero pore pressure.
The command writes `pylith/step02_mogi_benchmark/output/failure-analysis.json`,
which remains ignored by Git. This checks the HDF5 reader, boundary extraction,
yield calculation, and connectivity search on a synthetic spherical-cavity
case. It does not use OOI observations or paper-reported results, and it does
not validate a calibrated Axial Seamount failure threshold.
