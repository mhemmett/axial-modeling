# Step 12: three-branch generalized Maxwell material

PyLith's generalized Maxwell rheology provides three viscous branches and an
equilibrium spring, which can represent time-dependent shear relaxation beyond
the one-branch smoke case. This step verifies the cell-centered material
database and PyLith state path on the 2,761-tetrahedron ellipsoid mesh. It does
not set the paper's rheology: the branch fractions and relaxation spectrum are
not reported in the written specification.

Run `bash scripts/generalized_maxwell_ellipsoid_smoke.sh` from the repository
root. The command generates a 2,761-tetrahedron mesh, solves the zero-source
steady thermal equation with Eq. 22 conductivity, writes a temperature-dependent
three-branch material database, then advances a constant 1 MPa cavity load for
two years. It checks both the Arrhenius material fields and the resulting
stress and branch states. Mesh files, logs, the thermal archive, material
database, and HDF5 output remain under this step's ignored `mesh/` and
`output/` directories.

The thermal field uses `Q = 0`, the default Eq. 22 conductivity parameters,
0 °C at the surface, 1200 °C at the reservoir, and a 30 °C/km geotherm on the
four side faces and base. Those outer-face temperatures close unspecified
thermal boundaries as an explicit setup assumption. The smoke uses `E =
50 GPa`, `ν = 0.25`, density `2800 kg/m³`, synthetic branch reference
viscosities `[1.0e18, 5.0e17, 2.0e18] Pa·s` at 1200 °C, and shear fractions
`[0.25, 0.25, 0.25]`. Eq. 15 scales each branch's reference viscosity by the
same cellwise Arrhenius factor. The reference viscosities and fractions leave
a 0.25 equilibrium-spring fraction and exercise all three PyLith branches;
they are not paper parameters. With the implied `G = 20 GPa`, the shortest
reference relaxation time is `1.0e8 s`. The 30-day time step stays below
PyLith's one-fifth relaxation-time limit.

The verified thermal solve converged in 10 Picard iterations with relative
change `6.196e-10` and temperatures from 0 to 1200 °C. PyLith reached
`63,115,200 s`, with peak stress `1.67 MPa`, spatial viscosities from
`5.0e17` to `1.07e36 Pa·s`, and peak viscous strains near `2.01e-5` in each
branch. These finite nonzero fields confirm that PyLith accepted the mapped
temperature field and advanced all supplied branches.

The checker reconstructs Cauchy stress at all 25 saved times from the total
strain and three viscous-strain branches. Its relative L2 difference from
PyLith stress is `1.99e-16`. It also checks the largest saved interval,
`2.592e6 s`, against one-fifth of the shortest cellwise `1.0e8 s` relaxation
time, the stability limit documented by PyLith 5.0.2. These checks establish consistency
between PyLith's output fields and the configured constitutive law; they do not
measure time-step convergence or identify the paper's unspecified branch
spectrum.

PyLith 5.0.2 documents three Maxwell branches, branch viscosities, fractional
shear moduli, and branch-specific viscous-strain state fields in its
[generalized Maxwell formulation](https://pylith.readthedocs.io/en/v5.0.2/user/governingeqns/elasticity/bulk-rheologies/linear-genmaxwell.html)
and [elasticity auxiliary-field table](https://pylith.readthedocs.io/en/v5.0.2/user/physics/materials/elasticity.html).
The writer requires positive branch fractions whose sum does not exceed one;
the remainder is the equilibrium spring. The paper's fractional moduli,
viscosities, and mapping to PyLith's branches remain unresolved, so this smoke
validates software support only.
