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
Maxwell restart check, and the step 02 synthetic Mogi benchmark. Run
`make mogi-benchmark` to compare the PyLith elastic surface displacement with
the analytical reference. Generated meshes and HDF5 outputs are ignored by
Git.
