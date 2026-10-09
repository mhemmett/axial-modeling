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

## One-branch Maxwell response on the ellipsoid mesh

| Field | Value |
| --- | --- |
| Code revision | `c50286a` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make maxwell-ellipsoid-smoke` |
| Configuration | Two-year constant 1 MPa cavity overpressure; E = 50 GPa, ν = 0.25, density = 2800 kg/m³, and uniform viscosity = 10¹⁸ Pa·s |
| Runtime | 16.3 s for mesh generation, 25 Maxwell time steps, and output checks |
| Mesh | 2,761 linear tetrahedra; 666 nodes; 40 km × 40 km × 20 km domain |
| Result | The assumed Maxwell time is 5.0 × 10⁷ s (1.584 years). Central uplift grows monotonically from 0.0325674 to 0.0614660 m; Eastern uplift grows from 0.00350400 to 0.00542360 m. Peak absolute stress is 2.635 MPa and final peak viscous strain is 1.922 × 10⁻⁵. |
| Validation | Passed. PyLith reached 63,115,200 s, wrote 25 output steps with finite stress and nonzero viscous strain, and maintained monotone Central creep. `make test` passed with 38 tests; `make lint` passed. |
| Interpretation | Verifies one-branch, constant-property PyLith Maxwell state evolution under a held load. Viscosity and Poisson ratio are test assumptions; the run is neither the written generalized temperature-dependent rheology nor a BPR calibration. No observations or paper-reported results were used. |

## Steady thermal field to Arrhenius Maxwell viscosity

| Field | Value |
| --- | --- |
| Code revision | `248c726` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make thermal-maxwell-ellipsoid-smoke` |
| Configuration | Zero-source steady conduction with k = 3 W/(m K), 0 °C top, 1200 °C cavity, and 30 °C/km on sides and base; Eq. 15 cell-centered viscosity; constant E = 50 GPa, ν = 0.25, density = 2800 kg/m³ |
| Runtime | 17.6 s for mesh generation, thermal solve, PyLith integration, and output checks |
| Mesh | 2,761 linear tetrahedra; 666 nodes; 40 km × 40 km × 20 km domain |
| Result | Thermal iteration converged in two steps with relative change `4.737e-17`; temperature ranges from 0 to 1200 °C. Cell viscosity ranges from `1.805e13` to `8.355e29 Pa s`. Over 25 Maxwell steps, Central uplift grows from 0.0861553 to 0.1067421 m and Eastern uplift from 0.0130602 to 0.0187106 m. The largest Central one-step decrease is `1.537e-5 m`. |
| Validation | Passed as a one-way material-transfer smoke. PyLith reached 63,115,200 s and wrote finite stress and nonzero viscous strain. `make test` passed with 38 tests; `make lint` passed. |
| Interpretation | Verifies the steady thermal solve, written Arrhenius viscosity law, cell-centered SimpleDB, and PyLith Maxwell state path. It assumes a side/base geotherm extension and constant modulus; it does not implement feedback, hydrothermal conductivity, generalized Maxwell branches, or BPR calibration. No observations or paper-reported results were used. |

The machine-readable property and response summary remains local under ignored
`data/processed/thermal_maxwell_ellipsoid_summary.json`.

## Hydrothermal conductivity to Arrhenius Maxwell viscosity

| Field | Value |
| --- | --- |
| Code revision | `b3f9499` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make hydrothermal-maxwell-ellipsoid-smoke` |
| Configuration | Zero-source steady conduction with Eq. 22 (`k0 = 3 W/(m K)`, `Nu = 8`, `A = 0.75`, `Tmax = 600 °C`, `zmax = 6 km`); Eq. 15 cell-centered viscosity; constant E = 50 GPa, ν = 0.25, density = 2800 kg/m³ |
| Boundaries | 0 °C top, 1200 °C cavity, and 30 °C/km on sides and base; extending the geotherm to these faces is an explicit assumption |
| Runtime | 15.3 s for mesh generation, nonlinear thermal solve, PyLith integration, and output checks |
| Mesh | 2,761 linear tetrahedra; 666 nodes; 40 km × 40 km × 20 km domain |
| Result | Picard iteration converged in 10 steps with relative change `6.421e-10`; temperature ranges from 0 to 1200 °C. Cell conductivity ranges from 7.214 to 91.098 W/(m K), and viscosity ranges from `1.805e13` to `9.626e30 Pa s`. Over 25 Maxwell steps, Central uplift grows from 0.0825896 to 0.1079805 m and Eastern uplift from 0.0109800 to 0.0154222 m. |
| Validation | Passed as a one-way material-transfer smoke. PyLith reached 63,115,200 s and wrote finite stress and nonzero viscous strain. `make test` passed with 39 tests; `make lint` passed. |
| Interpretation | Verifies the Eq. 22 nonlinear thermal solve, written Eq. 15 viscosity law, cell-centered material database, and PyLith Maxwell state path. It holds modulus constant and does not update thermal state from deformation or viscous heating; it is not a coupled-model or figure reproduction. No observations or paper-reported results were used. |

The machine-readable property and response summary remains local under ignored
`data/processed/hydrothermal_maxwell_ellipsoid_summary.json`.

## OOI pressure-history Maxwell forward check

| Field | Value |
| --- | --- |
| Code revision | `91c2d00` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make ooi-maxwell-ellipsoid-check` |
| Configuration | Static 1 MPa ellipsoid response calibrates monthly Central OOI uplift; the inferred pressure history drives a one-branch Maxwell model with E = 50 GPa, ν = 0.25, and η = 10¹⁸ Pa·s |
| Runtime | 61.6 s for mesh generation, static calibration, 12.07-year Maxwell run, and output checks; each PyLith invocation is bounded by 300 s |
| Inputs | 3,927 common finite Central and Eastern OOI records from 2014-09-05 to 2026-09-30; aggregate QC code `2` retained without filtering |
| Mesh | 2,761 linear tetrahedra; 143 monthly pressure samples; largest sample gap is 122 days |
| Result | Static Central compliance is 0.0318994 m/MPa and inferred pressure ranges from −60.98 to 21.05 MPa. The Maxwell run writes 147 records through 380,851,200 s. Central RMSE is 1.096 m (correlation 0.787); Eastern RMSE is 0.195 m (correlation 0.922). Peak absolute stress is 116.4 MPa and final peak viscous strain is 4.215 × 10⁻⁴. |
| Validation | Passed. PyLith reached the requested end time and wrote finite nonzero stress and viscous strain. `make test` passed with 40 tests; `make lint` passed. |
| Interpretation | This is an OOI-only forward diagnostic, not a reproduction of Fig. 4a or the full coupled model. The coarse static compliance is not mesh-converged, so pressure amplitudes and displacement errors remain provisional. Pressure was not recalibrated to the viscoelastic response. No paper-supplied observations, publication results, or figure values were used. |

The summary and aligned model/observation series remain local under ignored
`data/processed/ooi_maxwell_ellipsoid_summary.json` and
`data/processed/ooi_maxwell_ellipsoid_timeseries.csv`.

## Printed Eq. 16 Maxwell property diagnostic

| Field | Value |
| --- | --- |
| Code revision | `c018609` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Commands | `make eq16-maxwell-ellipsoid-smoke`; `make eq16-hydrothermal-maxwell-ellipsoid-smoke` |
| Configuration | Two-year constant 1 MPa load; Eq. 15 viscosity and Eq. 16 modulus evaluated at cell temperatures; uniform density 2800 kg/m³ and assumed ν = 0.25 |
| Runtime | 17.9 s wall time for both bounded runs executed concurrently; each generated 25 Maxwell records |
| Mesh | 2,761 linear tetrahedra per run; 0–1200 °C field with 0 °C top, 1200 °C cavity, and 30 °C/km side/base extension |
| Result | The printed equation gives 25.00–33.33 GPa across the cell temperatures. With constant conductivity, Central uplift is 0.15138 to 0.21078 m and the largest one-step decrease is 2.90 × 10⁻⁵ m. With Eq. 22 conductivity, Central uplift is 0.14488 to 0.21110 m and is monotone; conductivity is 7.214–91.098 W/(m K). Peak stress is 4.292 MPa and 3.517 MPa, respectively. |
| Validation | Both PyLith runs reached 63,115,200 s and produced finite stress and nonzero viscous strain. `make test` passed with 41 tests; `make lint` passed. |
| Interpretation | PyLith accepts the heterogeneous modulus database, but Eq. 16 as printed increases modulus over the model's temperature range, contrary to the stated hot, ductile modulus. This diagnostic does not resolve the source conflict or reproduce a figure; thermal properties are transferred once and feedback is disabled. No observations or publication data were used. |

The machine-readable summaries remain local under ignored
`data/processed/eq16_maxwell_ellipsoid_summary.json` and
`data/processed/eq16_hydrothermal_maxwell_ellipsoid_summary.json`.

## Targeted ellipsoid compliance refinement

| Field | Value |
| --- | --- |
| Code revision | `c018609` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | Direct calls to `scripts.ellipsoid_mesh_sensitivity._run_mesh_variant`; the per-run element cap was raised in memory to 10,000–15,000 for these exploratory cases |
| Configuration | 40 × 40 × 20 km domain; 1 MPa elastic cavity load; 12 km far-field size except the first 10 km case; mesh near-size or local-box refinement varied as listed |
| Runtime | 9.8–11.4 s per mesh and static PyLith solve; each solver call used the 300 s timeout |
| Station-box refinement | The 600 m near / 500 m local case with 12 km far size repeated identically: 7,557 tetrahedra, 0.057945 m/MPa Central, and 0.006625 m/MPa Eastern. Refining its local box from 500→450→400 m changed Central compliance by +3.5% then +3.0%, and Eastern by −4.1% then +3.7%. |
| Cavity refinement | At a fixed 500 m local box and 12 km far size, changing cavity near-size from 600→500→450→400→350→300 m produced Central compliance 0.057945, 0.057376, 0.058817, 0.062682, 0.064188, and 0.069134 m/MPa; Eastern compliance was 0.006625, 0.006625, 0.006576, 0.007120, 0.006885, and 0.007379 m/MPa. Adjacent changes exceed 5% at 450→400 m and 350→300 m. |
| Mesh | The distinct candidates contain 7,475–13,412 tetrahedra; the repeated case confirms deterministic output for the same Gmsh settings. |
| Validation | All static solves completed and wrote finite unit-pressure surface responses. No observations were used. The cavity-refinement sequence does not establish convergence; at fixed 500 m local resolution, 600→300 m refinement changes Central compliance by 19.3% and Eastern by 11.4%. |
| Interpretation | Refining the BPR-region box alone approaches the 5% consecutive-change tolerance, but cavity resolution remains influential and non-monotone. The current mesh suite is still insufficient for stable OOI pressure calibration. These exploratory element counts exceed the repository's ordinary setup-mesh target and are not part of the default seven-case command. |

All generated meshes, logs, and HDF5 outputs were temporary and remain absent
from the repository.

## OOI Maxwell failure-threshold progression

| Field | Value |
| --- | --- |
| Code revision | `c143908` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make ooi-maxwell-ellipsoid-check` |
| Configuration | 2014–2026 OOI monthly pressure history on the 2,761-tetrahedron ellipsoid; postprocess each of 147 Cauchy-stress records with `C = 1 MPa`, `phi = 25°` used directly, and zero pore pressure |
| Runtime | 65.9 s for static calibration, 12.07-year Maxwell run, failure postprocessing, and validation; PyLith steps are bounded by 300 s |
| Result | Mohr–Coulomb yield cells range from 55 to 685. A face-connected cavity-to-top path occurs in 146 records, first at 5,184,000 s (60 days). Maximum cavity tensile stress is 63.97 MPa; the tensile cutoff is not applied. |
| Validation | Passed. Failure analysis covers all 147 strictly increasing stress records; PyLith reached 380,851,200 s and wrote finite stress and viscous strain. `make test` passed with 49 tests; `make lint` passed. |
| Interpretation | This is an OOI-only threshold diagnostic, not a hindcast or eruption prediction. The 60-day path and tensile value depend on nonconverged static compliance, an assumed friction-angle interpretation, zero pore pressure, and a single Maxwell branch. OOI does not cover the 1998 or 2011 cycles; no publication data were used. |

The threshold series is included in ignored
`data/processed/ooi_maxwell_ellipsoid_summary.json`; HDF5 stress fields remain
temporary.

## OOI hydrothermal Eq. 16 failure diagnostic

| Field | Value |
| --- | --- |
| Code revision | `296d827` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make ooi-eq16-hydrothermal-maxwell-check` |
| Configuration | Zero-source steady Eq. 14 field with Eq. 22 conductivity, Eq. 15 viscosity, and Eq. 16 modulus as printed; the same cellwise modulus is used by static pressure calibration and the one-branch Maxwell solve |
| Boundaries | 0 °C top, 1200 °C cavity, and 30 °C/km geotherm on the sides and base; `E` uses a magma temperature of 1200 °C; density = 2800 kg/m³ and ν = 0.25 are setup assumptions |
| Runtime | 60.65 s for mesh generation, thermal field, static calibration, 12.07-year Maxwell run, and failure analysis; each PyLith invocation is bounded by 300 s |
| Inputs | 143 monthly common-finite OOI samples from 2014-09-05 to 2026-09-30; largest sample gap is 122 days; aggregate QC code `2` retained without filtering |
| Mesh | 2,761 linear tetrahedra; 147 Maxwell stress records |
| Thermal result | Picard iteration converged in 10 steps with relative change `6.421e-10`. Temperature ranges from 0–1200 °C, conductivity from 7.214–91.098 W/(m K), modulus from 25.00–33.33 GPa, and viscosity from `1.805e13`–`9.626e30 Pa s`. |
| Mechanical result | Static compliance is 0.0679954 m/MPa and inferred pressure ranges from −28.61 to 9.87 MPa. Central RMSE is 1.260 m (correlation 0.995); Eastern RMSE is 0.04990 m (correlation 0.988). Peak absolute stress is 74.18 MPa. A cavity-to-top Mohr–Coulomb path appears in 87 of 147 records, first at a saved time of 90 days; maximum cavity tensile stress is 52.36 MPa. |
| Validation | Passed. Thermal iteration converged, PyLith reached 380,851,200 s, and all 147 stress records were analyzed. The full suite passed with 50 tests; `make lint` passed. No publication observations or results were used. |
| Interpretation | This OOI-only diagnostic applies the printed Eq. 16 law consistently in the static and Maxwell runs; that law still makes modulus rise with temperature, contrary to the written brittle and ductile descriptions. The mesh is not converged, the failure convention uses `C = 1 MPa`, `phi = 25°` directly and zero pore pressure, tensile strength is unknown, and temperature receives no mechanical or viscous-heating feedback. It is not an eruption prediction or reproduction of a manuscript panel. |

The summary and aligned series remain local under ignored
`data/processed/ooi_eq16_hydrothermal_maxwell_summary.json` and
`data/processed/ooi_eq16_hydrothermal_maxwell_timeseries.csv`; meshes, logs,
and HDF5 fields are temporary.
