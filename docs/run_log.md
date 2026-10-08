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

## OOI relative-uplift observation plot

| Field | Value |
| --- | --- |
| Code revision | `0bf4ac9` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Matplotlib 3.11.2 |
| Command | `make bpr-observation-plot` |
| Inputs | Processed authorized OOI daily BPR files for Central and Eastern Caldera; both retain aggregate QC code `2` (`NOT_EVALUATED`) |
| Runtime | 3.43 s for parsing 7,984 records and writing PNG and PDF outputs |
| Result | Central contains 3,955 records from 2014-08-31 through 2026-09-30 and ends at `+0.660889 m`; Eastern contains 4,029 records from 2014-09-05 through 2026-09-30 and ends at `+0.204590 m`, each relative to its own first sample. |
| Validation | Passed. `make test` passed with 30 tests; `make lint` passed; both output files were opened and checked, and the PNG was visually inspected. |
| Interpretation | Observation-only partial coverage relevant to Fig. 2. The plot has no eruption markers, earthquake counts, pre-2014 series, or model prediction, and it is not a reproduction of the published figure. No paper-supplied observations or figure values were used. |

The PNG and PDF are tracked at `figures/ooi_bpr_relative_uplift.*`. Raw and
processed observation files remain local and ignored.

## OOI-calibrated elastic Mogi spatial check

| Field | Value |
| --- | --- |
| Code revision | `53ff790` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Matplotlib 3.11.2 |
| Command | `make bpr-mogi-check` |
| Inputs | 3,927 common finite Central and Eastern OOI daily BPR observations, 2014-09-05 to 2026-09-30; aggregate QC code `2` (`NOT_EVALUATED`) retained without filtering |
| Configuration | Elastic Mogi source: `E = 60 GPa`, assumed `ν = 0.25`, radius 0.7 km, depth 4 km; source axis assumed at Central BPR |
| Runtime | 3.77 s to align observations, infer pressure, score Eastern uplift, and write plot outputs |
| Geometry | Eastern BPR is 2,679.3 m east and 1,663.7 m south of Central in the local equirectangular projection |
| Result | The inferred pressure change ranges from `-2.9621 GPa` to `+1.0552 GPa`. The Eastern held-out prediction has `0.05944 m` RMSE, `20.54%` relative L2 error, and `0.9954` correlation. |
| Validation | Passed. Synthetic Mogi observations recovered the known pressure and Eastern response to numerical precision. `make test` passed with 32 tests; `make lint` passed. |
| Interpretation | The central trace is fitted by construction; the Eastern trace tests only this instantaneous elastic point-source geometry. The pressure scale shows that the Mogi proxy cannot serve as the historical pressure model. It omits the target ellipsoid, viscoelastic relaxation, and temperature-dependent material response. No paper-supplied observations, published results, or figure values were used. |

The diagnostic plot is tracked at `figures/ooi_mogi_calibration.*`. The aligned
time series and summary JSON remain local under ignored `data/processed/`.

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

## PyLith ellipsoid compliance check against independent OOI BPRs

| Field | Value |
| --- | --- |
| Code revision | `5db5799` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make ellipsoid-bpr-check` |
| Configuration | `pylith/step05_ellipsoid_elastic/step05.cfg`; 6 km × 3 km × 1 km reservoir centered 1.6 km below the surface; 1 MPa unit load; E = 50 GPa, ν = 0.25 assumed, and density = 2800 kg/m³ |
| Runtime | 9 s for mesh generation, the bounded PyLith solve, and OOI calibration |
| Mesh | 2,761 linear tetrahedra; 666 nodes; 40 km × 40 km × 20 km domain |
| Observations | 3,927 common finite daily Central and Eastern OOI records from 2014-09-05 through 2026-09-30; quality code 2 retained without filtering |
| Result | On the 2,761-tetrahedron mesh, unit-load vertical compliance is 0.0318994 m/MPa at Central and 0.00345580 m/MPa at Eastern. The associated Central-calibrated pressure range is −62.21 to 22.16 MPa; Eastern holdout RMSE is 0.22098 m, relative L2 error is 76.36%, and correlation is 0.9954. |
| Validation | Solver execution passed. PyLith reached the configured 1 s output time and wrote finite nonzero Cauchy stress. `make test` passed with 38 tests; `make lint` passed. |
| Interpretation | Central is fitted by construction, but the mesh sensitivity below shows that neither compliance nor the Eastern amplitude comparison is converged. Treat the pressure series and spatial error as provisional. This static model also omits viscoelastic memory and temperature-dependent properties. Only independent OOI observations were used; paper-supplied observations, published results, and figure values were excluded. |

The tracked comparison plot is `figures/ooi_ellipsoid_elastic_calibration.*`.
The aligned observations and summary remain local under ignored
`data/processed/`.

## Static ellipsoid mesh sensitivity check

| Field | Value |
| --- | --- |
| Code revision | `fe62d93` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make ellipsoid-mesh-sensitivity` |
| Configuration | Four static unit-pressure solves with near/far mesh sizes of 1,200/10,000 m, 900/7,500 m, 750/6,500 m, and 600/5,000 m |
| Runtime | 25.9 s for four bounded PyLith solves and mesh generation |
| Mesh | 2,761, 3,680, 4,582, and 5,863 linear tetrahedra; up to 1,287 nodes |
| Result | Central compliance was 0.0318994, 0.0246855, 0.0376595, and 0.0514839 m/MPa. Eastern compliance was 0.00345580, 0.00272401, 0.00387436, and 0.00596645 m/MPa. Consecutive changes ranged from 21.2% to 54.0%. |
| Validation | Not passed for convergence. The declared 5% consecutive-compliance tolerance was exceeded at all three refinements. Four PyLith runs completed under the 300 s per-solve bound. No observations were used. |
| Interpretation | The current meshes do not support a stable station compliance. The coarse-grid OOI pressure calibration and Eastern holdout comparison above are provisional and must not be interpreted as a physical mismatch until mesh refinement stabilizes the response. |

The machine-readable sensitivity summary remains local under ignored
`data/processed/ellipsoid_mesh_sensitivity.json`.

## Local ellipsoid mesh refinement check

| Field | Value |
| --- | --- |
| Code revision | `0221672` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make ellipsoid-mesh-sensitivity` |
| Configuration | Added box-refined meshes with x = −3.5 to 4.5 km, y = −2.2 to 2.2 km, and depth = 0 to 3 km; local sizes are 750 m and 500 m with a 2 km transition layer |
| Runtime | 40.9 s for four global and two local bounded PyLith solves |
| Mesh | Local cases contain 4,044 and 6,772 linear tetrahedra; the maximum element count across all six cases is 6,772 |
| Result | The 750 m case gives 0.0391472 m/MPa at Central and 0.00390707 m/MPa at Eastern. Refining to 500 m changes these to 0.0566056 and 0.00687863 m/MPa, increases of 44.6% and 76.1%. |
| Validation | Not passed for convergence. The 5% consecutive-compliance tolerance is exceeded for both station responses. All six PyLith solves completed below the 300 s per-solve limit; no observations were used. |
| Interpretation | Local refinement does not yet stabilize either BPR compliance. Pressure and Eastern-fit values inferred from the elastic ellipsoid remain provisional; a mesh-converged response is still required before spatial misfit can be interpreted. |

## Mixed cavity and local mesh refinement check

| Field | Value |
| --- | --- |
| Code revision | `53cea03` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make ellipsoid-mesh-sensitivity` |
| Configuration | Seven mesh cases: four global refinements, two local-box sizes, and one 600 m cavity refinement combined with a 750 m local box |
| Runtime | 46.0 s for seven bounded PyLith solves and mesh generation |
| Mesh | Mixed case contains 5,435 tetrahedra; maximum across the seven cases is 6,772 |
| Result | The mixed case gives 0.0536898 m/MPa at Central and 0.00619138 m/MPa at Eastern. Relative to the 750 m local-box case, the mixed refinement changes Central and Eastern compliance by 37.1% and 58.5%. |
| Validation | Not passed for convergence. The 5% tolerance remains exceeded for every tested comparison group. All seven solves completed below the 300 s per-solve limit; no observations were used. |
| Interpretation | Combining cavity and local refinement still does not stabilize compliance. The coarse-grid OOI calibration and spatial comparison remain provisional. |
