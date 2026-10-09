# Native PyLith workflow

The PyLith 5.0.2 Linux x86_64 binary tarball is installed beneath this
directory. The project does not build PyLith or PETSc from source. Verify the
binary with `make pylith-version`; `make install-pylith` checks the supplied
tarball's pinned SHA-256 before extracting it when needed.

The repository-local Conda environment is used for Gmsh, Python postprocessing,
tmux, and development tools. PyLith uses the Python and libraries bundled with
its binary distribution. Activate both with `source scripts/activate.sh` after
creating the Conda environment.

The bounded simulation sequence covers `step00_elastic_cavity`, the step 01
Maxwell restart check, the step 02 synthetic Mogi benchmark, and the step 03
steady thermal field. Run `make mogi-benchmark` to compare the PyLith elastic
surface displacement with its analytical reference, or `make thermal-model`
to solve baseline and hydrothermal temperature fields on the ellipsoidal
reservoir mesh. The step 03 run saves mesh-aligned NumPy archives and logs
under `step03_steady_thermal/output/`; these files and generated meshes are
ignored by Git. Its lateral and basal temperatures extend the background
geotherm as an explicit assumption. The thermal field is not yet coupled to a
mechanical solve.

The OOI ellipsoid diagnostics extend the same setup through the 2014–2026
pressure record. Run `make ooi-maxwell-ellipsoid-check` for the uniform
one-branch baseline or `make ooi-eq16-hydrothermal-maxwell-check` for a
one-way steady thermal-property diagnostic. Neither command reproduces the
full coupled model; both retain the nonconverged mesh and provisional failure
assumptions documented in [`../docs/KNOWN_ISSUES.md`](../docs/KNOWN_ISSUES.md).
