# Step 12: three-branch generalized Maxwell material

PyLith's generalized Maxwell rheology provides three viscous branches and an
equilibrium spring, which can represent time-dependent shear relaxation beyond
the one-branch smoke case. This step verifies the cell-centered material
database and PyLith state path on the 2,761-tetrahedron ellipsoid mesh. It does
not set the paper's rheology: the branch fractions and relaxation spectrum are
not reported in the written specification.

Run `bash scripts/generalized_maxwell_ellipsoid_smoke.sh` from the repository
root. The command generates a mesh, writes a synthetic material database,
advances a constant 1 MPa cavity load for two years, and checks the resulting
stress and branch-state fields. Mesh files, logs, material databases, and HDF5
output remain under this step's ignored `mesh/` and `output/` directories.

The smoke uses `E = 50 GPa`, `ν = 0.25`, density `2800 kg/m³`, branch
viscosities `[1.0e18, 5.0e17, 2.0e18] Pa·s`, and shear fractions `[0.25, 0.25,
0.25]`. These synthetic values leave a 0.25 equilibrium-spring fraction and
exercise all three PyLith branches; none is adopted as a paper parameter. With
the implied `G = 20 GPa`, the shortest relaxation time is `1.0e8 s`. The
30-day time step stays below PyLith's one-fifth relaxation-time limit.

The verified run reached `63,115,200 s` on 2,761 tetrahedra, with peak stress
`1.81 MPa` and peak viscous strains of `1.88e-5`, `1.43e-5`, and `2.15e-5` in
branches one through three. These finite nonzero fields confirm that PyLith
accepted and advanced each supplied branch.

The checker reconstructs Cauchy stress at all 25 saved times from the total
strain and three viscous-strain branches. Its relative L2 difference from
PyLith stress is `2.03e-16`. It also checks the largest saved interval,
`2.592e6 s`, against one-fifth of the shortest `1.0e8 s` relaxation time, the
stability limit documented by PyLith 5.0.2. These checks establish consistency
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
