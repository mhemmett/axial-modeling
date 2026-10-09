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

Pass `--all-times` to analyze every saved PyLith Cauchy-stress record. The JSON
contains a result for each strictly increasing output time and the first
recorded time with a connected path. This is limited by the solver's output
sampling: it does not locate a transition between saved records. The synthetic
progression test verifies a path that appears in a later record; the current
one-second PyLith smoke output contains only one record.

`make ooi-maxwell-ellipsoid-check` applies the same postprocessor to each
stress record in the OOI-driven ellipsoid Maxwell forward check. The current
2,761-tetrahedron run finds a cavity-to-top path in 146 of 147 records, first
at 5,184,000 s (60 days), using `C = 1 MPa`, `phi = 25°` directly, and zero
pore pressure. The maximum cavity tensile stress is 63.97 MPa; no tensile
cutoff is applied because tensile strength is unspecified. The result is
provisional because the static compliance is not mesh-converged and the
inferred pressure history is not recalibrated to the viscoelastic model. OOI
coverage begins in 2014, so this does not evaluate the 1998 or 2011 cycles.

`make ooi-eq16-hydrothermal-maxwell-check` repeats the OOI failure diagnostic
with a steady Eq. 14 temperature field, Eq. 22 conductivity, Eq. 15 viscosity,
and Eq. 16 modulus as printed. It uses the same cellwise modulus for the static
pressure calibration and the Maxwell run. The 2,761-tetrahedron run finds a
cavity-to-top path in 87 of 147 records, first at 7,776,000 s (90 days), with a
maximum cavity tensile stress of 52.36 MPa. Modulus ranges from 25.00 to
33.33 GPa, while viscosity ranges from `1.805e13` to `9.626e30 Pa s`.

This variant remains provisional: Eq. 16 still reverses the stated temperature
trend, the mesh compliance is not converged, the Maxwell model has one branch,
and the temperature field is not updated from deformation or viscous heating.
It uses no paper-supplied observations or publication outputs and does not
evaluate the 1998 or 2011 cycles.
