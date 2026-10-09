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
The postprocessor therefore accepts either an angle `phi` or a dimensionless
coefficient `f`; for the latter it evaluates the same principal-stress formula
with `phi = arctan(f)`. The angle case applies 25° directly, while a literal
coefficient case uses `f = 25` (equivalent to about 87.71°). These cases expose
the effect of the notation ambiguity without selecting a preferred reading.
Pore pressure enters the effective stress for shear yield. The report also
gives the largest tensile principal stress among cavity-adjacent cells as a
candidate tensile-strength threshold. The source does not supply tensile
strength, so the smoke case does not apply a tensile cutoff to the shear path
or claim an eruption threshold.

Run `make failure-connectivity-smoke` to generate the synthetic Mogi stress
field and analyze it with cohesion `1 MPa`, `phi = 25°`, and zero pore pressure.
The command writes `pylith/step02_mogi_benchmark/output/failure-analysis.json`,
which remains ignored by Git. This checks the HDF5 reader, boundary extraction,
yield calculation, and connectivity search on a synthetic spherical-cavity
case. It does not use OOI observations or paper-reported results, and it does
not validate a calibrated Axial Seamount failure threshold.

Pass `--all-times` to analyze every saved PyLith Cauchy-stress record. The JSON
contains a result for each strictly increasing output time and the first
recorded time with a connected path. It also estimates onset between the first
adjacent no-path/path records by linearly interpolating Cauchy stress and
bisecting the path indicator. The result includes the bracketing records and
assumes the path indicator changes monotonically within that interval; no
PyLith integration is performed between saved records. The synthetic
progression test verifies the interpolated onset against the analytic
single-cell threshold.

`make ellipsoid-failure-progression-smoke` applies the postprocessor to 25
saved records from a two-year ellipsoid Maxwell diagnostic. With `C = 1 MPa`,
`phi = 25°`, and zero pore pressure, 8–12 cells yield but no record has a
cavity-to-top path. The maximum cavity tensile stress rises from 1.962 to
2.645 MPa. These values are candidate thresholds under a one-branch viscosity,
constant 1 MPa load, and fixed-base setup; they do not predict an eruption.

`make ooi-maxwell-ellipsoid-check` applies both friction interpretations to
each stress record in the OOI-driven ellipsoid Maxwell forward check and saves
their per-record yield counts and connected-path onset times in
`friction_criterion_sensitivity` in the processed JSON. Its angle case uses
`C = 1 MPa`, `phi = 25°`, and zero pore pressure. Its coefficient case uses
`C = 1 MPa`, `f = 25`, and zero pore pressure. The pre-existing
`failure_threshold_diagnostic` retains the angle-case fields for compatibility.
The angle case finds a path in 146 of 147 records, first at 60 days, with a
maximum of 685 yield cells; interpolation estimates onset at 32.02 days. The
literal coefficient case finds a path in all 147 records, including the first
saved record at 30 days, and reaches 1,345 yield cells. Since that case has no
earlier saved no-path record, its onset is not bracketed. The angle-case
interpolation assumes a monotonic transition within the bracketing interval;
neither onset is a PyLith time-integrated result. Neither scenario applies the
tensile cutoff, and the coefficient case's equivalent angle is extreme. These
diagnostics remain provisional because static compliance is not mesh-converged
and the inferred pressure history is not recalibrated to the viscoelastic
model. OOI coverage begins in 2014, so this does not evaluate the 1998 or 2011
failure cycles.

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
