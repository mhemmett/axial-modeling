# Numerical run log

Each run entry records the code revision, configuration, command, runtime, and
validation outcome. Generated meshes, solver logs, and HDF5 output remain local
and ignored by Git; this file stores run metadata and summary metrics only.

## PyLith elastic-cavity toolchain check

| Field | Value |
| --- | --- |
| Code revision | `835ec48e073daf42fd331188ed3b2b7e332e0170` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make smoke` |
| Configuration | `pylith/step00_elastic_cavity/step00.cfg` and `pylithapp.cfg` at the recorded revision |
| Runtime | 4 s |
| Mesh | 2,761 linear tetrahedra; 666 nodes; 40 km × 40 km × 20 km fallback box |
| Result | Maximum vertical surface displacement: 0.364047 m |
| Validation | Passed. Required displacement and Cauchy-stress HDF5 fields were present, and peak uplift was within the 0.01–10 m smoke range. |
| Interpretation | Toolchain and elastic response check only; this is not a calibrated model or reproduced manuscript panel. |

The run's repository configuration is identified by its commit. SHA-256 values
below allow the input state to be checked without retaining generated outputs.

| Input | SHA-256 |
| --- | --- |
| `environment.yml` | `1b48f00551d8c3873b725b2005db42dc50b66e0a09c6f379a0abe4497d8003b8` |
| `meshing/axial_box_ellipsoid.py` | `a45ca077e59db722a417108e4da23ecb6a6ce79b50d033172e016d027e60c5ba` |
| `pylith/step00_elastic_cavity/step00.cfg` | `da2589e3de186b73b8f4874dad1e1154ba07ee0b4f6c0321c5bc4a6f998d8989` |
| `pylith/step00_elastic_cavity/pylithapp.cfg` | `81bb8e97a1a008e3a16784c7510e318bfa3ca5163cef5904bbb50fd9cd9b99bc` |
| `pylith/step00_elastic_cavity/bc_cavity.spatialdb` | `20cfdbab233236b6d63e7736162c4d4b3c8e667804638f66c7f9baafd596e126` |
| `pylith/step00_elastic_cavity/mat_elastic.spatialdb` | `3e244c478f19812e3367088470c2ed3791d51b88afd3fccd4e66ba5a84ab6de1` |

At the same code revision, `make test` passed with four tests and `make lint`
reported no findings.

## OOI bottom-pressure intake

| Field | Value |
| --- | --- |
| Code revision | `6de3f2e` |
| Source | OOI public ERDDAP, `BOTSFLU-DAYDEPTH`, Central and Eastern Caldera BOTPT instruments |
| Command | `python data/fetch_bpr.py --start 2014-01-01 --end 2026-10-08 --download` |
| Runtime | 2.2 s |
| Central coverage | 3,955 daily records, 2014-08-31 to 2026-09-30; aggregate QC `NOT_EVALUATED` for all records |
| Eastern coverage | 4,029 daily records, 2014-09-05 to 2026-09-30; aggregate QC `NOT_EVALUATED` for all records |
| Local processing | `python data/process_bpr.py PATH_TO_FILE.csv.gz`; outputs remain under ignored `data/processed/` |
| Relative uplift | By 2026-09-30, +0.660889 m at Central and +0.204590 m at Eastern relative to each instrument's first available daily sample |
| Validation | Both compressed downloads had the expected ERDDAP columns, nonempty data, complete provenance manifests, and matching record counts. QC flags were retained, not treated as passes. |
| Limitation | This OOI daily product already includes tide removal and periodic sensor-drift corrections. It does not cover the 1998 or 2011 eruptions. No datasets supplied with or cited by the paper were used. |

The local manifest records each request URL and the SHA-256 of its uncompressed
ERDDAP response. The observations remain local and are excluded from Git.

## Same-mesh PyLith Maxwell restart check

| Field | Value |
| --- | --- |
| Code revision | `80ac3b6` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make maxwell-restart` |
| Configuration | `pylith/step01_maxwell_restart/step01_single.cfg`, `step01_split.cfg`, and `step01_restart.cfg` |
| Runtime | 18.12 s for mesh generation and three bounded PyLith solves |
| Mesh | 2,761 linear tetrahedra; 666 nodes; same generated box mesh for all runs |
| Result | Restarted run reached 2 s; normalized maximum differences were `1.612e-8` for displacement, stress, and viscous strain and `1.613e-8` for total strain. |
| Validation | Passed. The continuous run and two-segment run agreed below the configured `5e-7` tolerance for all four fields. `make test` passed with 18 tests; `make lint` passed. |
| Interpretation | Verifies same-mesh displacement and linear Maxwell state transfer for constant properties and a fixed 10 MPa cavity load. This is a restart test, not the temperature-dependent or historical model. No paper-supplied or paper-cited BPR records were used. |

The exporter samples displacement at mesh vertices and viscous and total strain
at tetrahedron centroids. The restart reads those values with nearest-point
queries. Cross-mesh interpolation and temperature-dependent material updates
remain unverified.

## Synthetic failure-threshold and connectivity smoke check

| Field | Value |
| --- | --- |
| Code revision | `4e602f1` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; NumPy 2.x |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make failure-connectivity-smoke` |
| Configuration | Synthetic 200 m radius spherical cavity at 2 km depth, 10 MPa inflation, `C = 1 MPa`, friction angle passed directly as `phi = 25°`, and zero pore pressure |
| Runtime | 9.98 s for the bounded PyLith solve and failure postprocessing |
| Mesh | 3,191 linear tetrahedra; 1,035 cavity-adjacent cells and 128 top-adjacent cells |
| Result | 1,500 cells met the raw Mohr–Coulomb yield condition. No face-connected path reached the top. Maximum cavity-adjacent tensile principal stress was `7.48574e6 Pa`. |
| Validation | Passed. The analysis read finite stress at 1 s, identified both boundaries, and wrote the JSON summary. `make test` passed with 31 tests; `make lint` passed. |
| Interpretation | Synthetic postprocessing check only. Tensile strength is unspecified, so no tensile cutoff was applied to the shear path. Directly treating 25° as `phi` resolves an ambiguous source notation for this diagnostic only. No OOI observations or paper-reported results were used. |

The machine-readable summary remains under the ignored
`pylith/step02_mogi_benchmark/output/` directory. It reports diagnostic stress
and connectivity values, not a calibrated eruption threshold.

## Tetrahedral steady heat solver verification

| Field | Value |
| --- | --- |
| Code revision | `6445d71` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; SciPy 1.18.1 |
| Command | `make test` and `make lint` |
| Configuration | Synthetic 3 × 3 × 3 nodal cube with 48 linear tetrahedra; boundary values and material properties are test fixtures. |
| Runtime | 0.51 s for 22 tests; Ruff completed successfully. |
| Result | Recovered a linear 10–110 °C profile to `1e-10` °C, the 0.5 °C midpoint for uniform volumetric heating, and a finite converged variable-conductivity solution. |
| Validation | Passed. The linear and source cases match their one-dimensional analytical solutions; boundary temperatures remain prescribed in all cases. |
| Interpretation | Verifies the finite-element operator and Picard iteration only. It does not assign Axial model boundaries or supply a full three-dimensional thermal field. |

## Thermal-to-material-to-mechanics smoke check

| Field | Value |
| --- | --- |
| Code revision | `c9e9a7b` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make thermal-material-smoke` |
| Configuration | `pylith/step01_maxwell_restart/step01_single.cfg` with manufactured affine temperatures, constant thermal conductivity, and a generated cell-centered material database |
| Runtime | 8.16 s for mesh generation, thermal solve, database creation, and the PyLith solve |
| Mesh | 2,761 linear tetrahedra; 666 nodes |
| Result | The finite-element solve matched its affine analytical temperature field to `4.547e-13` °C; PyLith reached 2 s and wrote finite stress and viscous-strain fields, with peak absolute stress `1.68912e7 Pa`. |
| Validation | Passed. The synthetic temperature ranged from 190 to 370 °C; the explicitly supplied modulus varied by depth. `make test` passed with 24 tests, and `make lint` passed. |
| Interpretation | Verifies the synthetic thermal-to-property-to-mechanics data path and cell-centered SimpleDB exchange. Prescribed temperatures cover every boundary, including the cavity, for a manufactured solution; this does not verify Axial boundary conditions or coupled thermal-mechanical feedback. |

## Analytical Mogi reference checks

| Field | Value |
| --- | --- |
| Code revision | `0368796` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; NumPy 2.x |
| Command | `make test` and `make lint` |
| Configuration | Synthetic spherical source and elastic moduli; no observation series or published result values. |
| Runtime | 0.46 s for 27 tests; Ruff completed successfully. |
| Result | The implementation returned radial half-space displacement, positive center uplift for inflation, and linear scaling with pressure change. |
| Validation | Passed. Synthetic center uplift matched the closed-form expression; symmetry and pressure-scaling tests passed. |
| Interpretation | Adds an analytical reference function. PyLith mesh convergence against the spherical-source solution remains unverified. |

## PyLith Mogi elastic benchmark

| Field | Value |
| --- | --- |
| Code revision | `63d466d` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make mogi-benchmark` |
| Configuration | Synthetic 200 m radius spherical cavity at 2 km depth, 10 MPa inflation, and uniform elastic host properties |
| Runtime | 7 s for mesh generation, the bounded PyLith solve, and comparison |
| Mesh | 3,191 linear tetrahedra in a 16 km × 16 km × 8 km domain |
| Result | Peak uplift was `6.258e-4 m`. At the surface vertex 15.6 m from the axis, PyLith uplift was `6.258e-4 m` versus `9.374e-4 m` analytically; relative error was 33.2%. The surface-vector L2 error was 37.2%. |
| Validation | Passed the positive-inflation check and the 50% coarse-mesh error bound. `make test` passed with 27 tests; `make lint` passed. |
| Interpretation | Verifies the PyLith source, boundary, and output path against the analytical half-space reference at coarse resolution. The 33.2% nearest-axis error does not establish mesh convergence or quantitative model validation. All values are synthetic; no BPR observations or paper-reported results were used. |

## Three-dimensional steady thermal field

| Field | Value |
| --- | --- |
| Code revision | `3df964a` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API; SciPy 1.18.1 |
| Command | `make thermal-model` |
| Configuration | 40 km × 40 km × 20 km box, ellipsoidal reservoir 6 km × 3 km × 1 km at 1.6 km depth, zero heat production; baseline and temperature-dependent conductivity cases |
| Runtime | 3.68 s for mesh generation and both solves |
| Mesh | 2,761 linear tetrahedra; 666 vertices |
| Result | The baseline converged in 2 iterations with a maximum free-node residual of `3.609e-8 W` and relative heat-balance error `5.328e-17`. The hydrothermal case converged in 10 iterations with a maximum free-node residual of `1.245e-2 W` and relative heat-balance error `1.151e-11`. Both fields span 0–1200 °C because those values are prescribed on the boundaries. |
| Validation | Passed. Net boundary heat rates were `-2.980e-8 W` and `-9.928e-2 W`; the small imbalance is consistent with the reported relative errors. The archived hydrothermal field has conductivity from 7.21 to 91.10 W/(m K). |
| Interpretation | Establishes a converged three-dimensional thermal field on the project mesh. Extending the background geotherm to all exterior faces is an explicit boundary assumption. This thermal-only calculation has not been coupled to PyLith mechanics; no BPR observations or publication-supplied model results were used. |
