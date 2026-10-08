# Repository Guidelines

## Project Structure

- `src/axialstress/` contains PyLith HDF5 readers, failure proxies, and the
  deferred thermal-property writer.
- `tests/` contains synthetic stress-state tests that do not need PyLith.
- `meshing/` contains the Gmsh box-and-ellipsoid generator.
- `pylith/` contains native installation instructions and simulation inputs.
- `docs/` records paper parameters, decisions, implementation gaps, and issues.
- `data/` documents BPR provenance and provides a dry-run-first fetch helper.
- `scripts/` contains environment activation and the bounded PyLith smoke test.

The extracted PyLith binary, Conda environment, raw observations, meshes, and
simulation output are local files and must remain untracked.

## Build and Development

Use the repository-local `axial-modeling` Conda environment. From the repository
root, run `make env`, `make install-pylith`, and `source scripts/activate.sh`.
Use `make tmux` for an interactive session, `make smoke` for the bounded
elastic-cavity solve, `make test` for unit tests, and `make lint` for Ruff.
PyLith and PETSc are installed from the provided binary tarball; do not compile
them from source.

## Style and Testing

Ruff enforces Python imports and common correctness checks. Configuration uses
Gmsh 4.x physical groups and PyLith `.cfg` files. Tests use pytest and synthetic
stress tensors; numerical simulations should stay below a few thousand
elements during setup and must run under `timeout 300`.

## Git and Writing

Use the per-feature commit plan for project initiation. Before editing README,
documentation, commit messages, or docstrings, read `STYLE.md`. Preserve its
repository prose conventions. Pull requests should summarize the scientific
motivation, changes, validation, and known limitations.

## Security and Configuration

Do not commit credentials, SSH keys, tokens, downloaded BPR data, or local
machine configuration. Keep environment variables and local caches outside
tracked source files.
