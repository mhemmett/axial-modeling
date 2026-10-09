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
Maxwell restart check, the step 02 synthetic Mogi benchmark, the step 03
steady thermal field, and the step 04 thermal-to-Maxwell smoke case. Run
`make mogi-benchmark` to compare PyLith's elastic surface displacement with
its analytical reference, `make thermal-model` to solve baseline and
hydrothermal temperature fields, or `make thermal-maxwell-smoke` to transfer
the hydrothermal field into a bounded PyLith Maxwell solve. Step 03 saves
mesh-aligned NumPy archives and logs under
`step03_steady_thermal/output/`; step 04 saves its material database and HDF5
outputs under `step04_thermal_maxwell/output/`. Generated meshes and outputs
are ignored by Git. The lateral and basal thermal values extend the background
geotherm as an explicit assumption. The thermal field remains fixed during
mechanics and mechanics does not feed heat back into the thermal solve.

Run `make thermal-cross-mesh-smoke` to transfer a manufactured affine
temperature field from a six-tetrahedron source mesh to the bounded mechanics
mesh, write its Maxwell material database, and complete a two-second PyLith
solve. This verifies spatial transfer and database use; the source field is
synthetic and does not represent Axial thermal conditions.

The OOI ellipsoid diagnostics extend the same setup through the 2014–2026
pressure record. Run `make ooi-maxwell-ellipsoid-check` for the uniform
one-branch baseline or `make ooi-eq16-hydrothermal-maxwell-check` for a
one-way steady thermal-property diagnostic. Neither command reproduces the
full coupled model; both retain the nonconverged mesh and provisional failure
assumptions documented in [`../docs/KNOWN_ISSUES.md`](../docs/KNOWN_ISSUES.md).

Run `make historical-four-case-bpr-calibration` for the 2011 raw Center/South
pressure-calibrated comparison across all four written rheologies. Its
Center fit includes the observed eruption deflation, so the South validation
and failure-path times are retrospective diagnostics. See
[`step15_historical_four_case_bpr/README.md`](step15_historical_four_case_bpr/README.md)
for assumptions and output locations.
