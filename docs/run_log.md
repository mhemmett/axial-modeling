# Numerical run log

Each run entry records the code revision, configuration, command, runtime, and
validation outcome. Generated meshes, solver logs, and HDF5 output remain local
and ignored by Git; this file stores run metadata and summary metrics only.

## Measure the fixed-base depth effect on ellipsoid response

| Field | Value |
| --- | --- |
| Code revision | `1938e93` |
| Command | `make ellipsoid-base-depth-sensitivity` |
| Runtime | 15.12 s for three mesh builds and PyLith unit-load solves |
| Configuration | Fixed 40 × 40 km lateral extent; base depths 20, 30, and 40 km; station points embedded in the top surface; 3,500-tetrahedron cap |
| Mesh sizes | 2,601, 2,774, and 2,869 tetrahedra; Central/Eastern sampling distance is below `10⁻⁶ m` for each mesh |
| 20 km compliance | Central `0.0131185 m/MPa`; Eastern `0.00170903 m/MPa` |
| 30 km compliance | Central `0.0139764 m/MPa` (`+6.54%` versus 20 km); Eastern `0.00158431 m/MPa` (`−7.30%`) |
| 40 km compliance | Central `0.0129421 m/MPa` (`−1.34%` versus 20 km); Eastern `0.00178869 m/MPa` (`+4.66%`) |
| Validation | The bounded target completed; `make test` passed with 107 tests; `make lint` and `git diff --check` passed; `make report` compiled the 19-page PDF. |
| Interpretation | Compliance varies nonmonotonically across independently generated, nonnested meshes. The sweep does not establish domain convergence or equivalence to a Winkler foundation. |

The coordinates are embedded as top-surface mesh vertices, removing the
hundreds-of-metres sampling offsets in the earlier exploratory sequence. This
isolates station interpolation error but does not make the depth meshes nested
or resolve their discretization differences.

## Carry the 1998 event stress state through the South BPR follow-up

| Field | Value |
| --- | --- |
| Code revision | `9f06ac8` |
| Command | `make historical-generalized-maxwell-1998-continuous-check` |
| Runtime | About 40 s including unit response, material build, and one PyLith run |
| Inputs | Original NCEI `seafloor_pressure_abs_raw [dbar]` channels for WC81 Center and WC82A/WC82B South; no paper-associated observations or results |
| Pressure history | 309 Center records from 1997-10-03 through 1998-08-07; terminal inferred pressure held constant for 270 days through the final South record on 1999-05-04 |
| South source alignment | Eight overlapping daily records; mean baseline offset `−0.825 m`; aligned overlap RMSE `0.000 m`; duplicate dates use WC82A |
| PyLith history | 83 saved records at seven-day intervals; 2,761 tetrahedra |
| Event holdout | 309 paired days; Center RMSE `0.186 m`; South RMSE `0.503 m`, bias `+0.329 m`, and correlation `0.995` |
| Follow-up holdout | 270 days from 1998-08-08 to 1999-05-04; South RMSE `0.063 m`, bias `−0.050 m`, and correlation `−0.369` |
| Validation | The bounded Make target completed; `make test` passed with 104 tests, `make lint` passed, and the report build is recorded with this change |
| Interpretation | The follow-up model remains nearly flat under constant terminal pressure. Its low RMSE and negative correlation do not show predictive skill; raw ocean variability, independent sensor baselines, synthetic branches, and nonconverged compliance remain unresolved. |

The South deployment files are both original raw NCEI series. Their eight-day
overlap permits alignment of independent baselines without applying a tide,
drift, or paper-derived correction. The terminal-load continuation is an
explicit assumption because the Center instrument stopped recording before
the South station.

## Carry the 2011 event stress state through the replacement BPR deployment

| Field | Value |
| --- | --- |
| Code revision | `c4fd94e` plus the continuous follow-up implementation in the working tree |
| Command | `make historical-generalized-maxwell-2011-continuous-check` |
| Runtime | 64 s including the static unit response, material build, and one PyLith run |
| Inputs | Original MGDS IEDA/322282 `RawDep` Center and `Depth` South channels; no paper-produced data |
| Pressure transition | Center records end on 2011-07-26 and restart on 2011-07-31; the second instrument is independently baselined and pressure is held constant through the five-day gap |
| PyLith history | 1,064 Center pressure records from 2010-09-05 to 2013-08-13; 154 saved stress records at seven-day intervals; 2,761 tetrahedra |
| Event holdout | 314 paired days through 2011-07-25; South RMSE `0.680 m`, bias `+0.371 m`, and correlation `0.997` |
| Follow-up holdout | 731 paired days from 2011-07-31 to 2013-08-09; South RMSE `1.246 m`, bias `−1.217 m`, and correlation `0.991` |
| Failure proxy | The cavity-to-surface path is first bracketed at about 17.61 days. Maximum cavity tension on a saved path record is `71.10 MPa`; tensile strength remains unset. |
| Validation | The 64 s Make target completed; `make test` passed with 102 tests, `make lint` passed, `make report` compiled the 19-page report, and `git diff --check` passed |
| Interpretation | The follow-up correlation coexists with a large Southern bias. The pressure reset, static nonconverged compliance, synthetic branches, independent instrument baselines, and uncorrected raw channels prevent interpreting this as a calibrated post-eruption hindcast. |

The two South windows are compared against their own first paired daily sample;
the model state is continuous across the instrument transition.
An initial `timeout 300 make historical-generalized-maxwell-check` attempt
attached this long solve to the seven existing windows and reached the outer
timeout before the new solve completed. The continuous run was separated into
its own target and then completed within its individual five-minute PyLith
limit.

## Evaluate the joint tensile and shear condition

| Field | Value |
| --- | --- |
| Code revision | `7e5bb9f` plus the joint-criterion implementation in the working tree |
| Commands | `timeout 300 make historical-generalized-maxwell-check`; `timeout 300 make ooi-maxwell-ellipsoid-check` |
| Runtime | Approximately 210 s for seven historical windows; 60.3 s for the OOI inversion |
| Failure inputs | Historical and OOI saved stress histories; `1 MPa` cohesion, `25°` friction angle used directly, and zero pore pressure; no tensile strength assigned |
| Historical threshold envelope | Maximum cavity tension at a saved connected-path record is 6.08 MPa (1995–96), 94.0 MPa (1998), 32.3 MPa (2003–05), 14.2 MPa (2005–07), 11.0 MPa (2007–09), 71.1 MPa (2011), and 58.3 MPa (2011–13) |
| OOI threshold envelope | Maximum cavity tension at a saved connected-path record is 63.97 MPa at 270 days |
| Validation | `make test` passed with 100 tests; `make lint` passed; `make report` compiled the 17-page report; `git diff --check` passed |
| Interpretation | Strengths in `(58.3221, 71.0951] MPa`, based on unrounded output values, separate the two event windows from the five quiet windows only in this saved-record check. Synthetic branch properties, static-compliance pressure inversion, zero pore pressure, raw uncorrected channels, and nonconverged compliance prevent interpreting this interval as a physical tensile strength. |

No tensile strength was selected. The joint condition is evaluated only at
saved PyLith records; no interpolation or integration is performed between
them.

## Bounded station-region ellipsoid refinement

| Field | Value |
| --- | --- |
| Code revision | `4db05a5` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make ellipsoid-mesh-sensitivity` |
| Configuration | 40 × 40 × 20 km box, 6 × 3 × 1 km cavity, fixed 1 MPa load; local station-region sizes of 1,000 and 900 m with cavity/far-field sizes fixed at 1,200/10,000 m |
| Runtime | 17.19 s for three mesh builds and PyLith unit-pressure solves |
| Meshes | 2,761, 3,124, and 3,325 linear tetrahedra; each case stays below the 3,500-element cap |
| Result | Central/Eastern compliance is 0.0318994/0.00345580, 0.0225148/0.00230768, and 0.0233475/0.00249709 m/MPa. From 1,000 to 900 m local size, compliance changes by 3.7% at Central and 8.2% at Eastern. |
| Validation | Not converged to the 5% criterion. All PyLith solves completed within 300 s; `make test` passed with 64 tests and Ruff passed. No observations were used. |
| Interpretation | This setup-budget refinement still leaves the Eastern response outside tolerance, while the coarser-to-1,000 m changes exceed 29% at both stations. Ellipsoid pressure and spatial comparisons remain provisional. |

Mesh files, solver outputs, and the machine-readable summary remain ignored.

## Integrated reproduction on the historical ellipsoid branch

| Field | Value |
| --- | --- |
| Code revision | `70f5a630ad66228fc7eed3b85c1a5c4a40aab8c7` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make reproduce OOI_END_DATE=2026-10-09` |
| Configuration | Completed the reproduction targets listed in [`reproduction.md`](reproduction.md); OOI observations end 2026-09-30 |
| Runtime | 505 s for thermal and mechanics workflows, OOI and historical BPR checks, figures, tests, lint, and report validation |
| Inputs | OOI Central: 3,955 daily rows; Eastern: 4,029 rows. The workflow also read the existing raw NCEI and MGDS historical deployment inputs; no Cabaniss-associated data products or results were used. |
| Validation | All reproduction targets completed; `make test` passed with 64 tests, Ruff passed, and the nine-page report was up to date. |
| Interpretation | This integrated run validates the current workflow and its independent BPR checks. The thermal-to-mechanics workflow remains one-way, elastic pressure fits are provisional diagnostics, and the full coupled reproduction remains incomplete. |

Raw downloads, processed series, and solver outputs remain ignored local files.
The seven regenerated PDFs had identical extracted text and file sizes to their
committed versions; their timestamp-only metadata changes were discarded.

## Bounded end-to-end reproduction checkpoint

| Field | Value |
| --- | --- |
| Code revision | `151251c159b2a078c2a23331802e86d71af8ebd6` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make reproduce OOI_END_DATE=2026-10-09` |
| Configuration | Rebuilt each target listed in [`reproduction.md`](reproduction.md), using OOI dates 2014-01-01 through 2026-10-09; available observations end 2026-09-30 |
| Runtime | 327 s including OOI retrieval, processing, all component runs, plotting, tests, lint, and report compilation |
| OOI inputs | Central: 3,955 daily rows, SHA-256 `817b7a61cb32a7a95fd81b554a400ef2cf0d2a2ddc9ddf591592de7201f0f53f`; Eastern: 4,029 daily rows, SHA-256 `78a895b48fb43217887d4f75759f2dbe3b3a9d21fe545a626da35182c99e91a7`; aggregate QC code `2` retained |
| Maxwell result | One-branch OOI run produced 147 stress records; Central RMSE was 1.096 m, Eastern RMSE was 0.195 m, and the assumed Mohr–Coulomb path first appeared at 60 days |
| Mesh result | Ellipsoid compliance remained outside the 5% tolerance across all tested refinements; convergence was not established |
| Validation | All component commands completed; `make test` passed with 55 tests, Ruff passed, and `make report` produced an eight-page PDF. |
| Interpretation | This checkpoint regenerates verified components and OOI-only diagnostics. It does not implement the complete coupled model or reproduce eruption forecasts. No publication-supplied observations, numerical outputs, or figure data were used. |

The local OOI manifest retains both request URLs and these uncompressed-response
hashes. Raw records and numerical solver outputs remain ignored by Git.

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

## Ellipsoid Maxwell stress-threshold progression

| Field | Value |
| --- | --- |
| Code revision | `72ca738` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make ellipsoid-failure-progression-smoke` |
| Configuration | Two-year one-branch Maxwell model; constant 1 MPa cavity overpressure; `C = 1 MPa`, `phi = 25°` applied directly, and zero pore pressure |
| Runtime | 12.4 s for mesh generation, PyLith solve, and stress-history analysis |
| Mesh | 2,761 linear tetrahedra; 666 nodes; 40 km × 40 km × 20 km domain |
| Result | The 25 saved stress records span 2,592,000 to 63,115,200 s. Raw Mohr–Coulomb shear-yield cells increase from 8 to 12; no record contains a face-connected cavity-to-surface path. Maximum cavity-adjacent tensile principal stress rises from 1.962 to 2.645 MPa. |
| Validation | Passed. Every record contains 2,761 cells and strictly increasing time; the history reports no connected path. `make test` passed with 35 tests; `make lint` passed. |
| Interpretation | This is a stress-postprocessing diagnostic under assumed one-branch rheology, load, zero pore pressure, and fixed base. The tensile value is a threshold to compare with a future strength choice, which remains unspecified. Mesh convergence, event-specific loading, and an observed or calibrated eruption threshold remain untested. No observations or paper-reported results were used. |

The machine-readable history remains under ignored
`data/processed/ellipsoid-failure-progression.json`; PyLith mesh and fields
remain under ignored `pylith/step06_maxwell_ellipsoid/` paths.

## Synthetic failure-progression smoke check

| Field | Value |
| --- | --- |
| Code revision | `c93ab77` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; NumPy 2.x |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make failure-progression-smoke` |
| Configuration | Same synthetic Mogi case and diagnostic strengths as the failure-connectivity smoke check |
| Runtime | 12.88 s for the bounded PyLith solve and single-record progression analysis |
| Mesh | 3,191 linear tetrahedra |
| Result | PyLith wrote one stress record at 1 s. The history output reported no cavity-to-surface path and returned `null` for the first path time. A synthetic three-record unit test verified a path transition at 1 s. |
| Validation | Passed. `make test` passed with 35 tests; `make lint` passed; the all-times CLI reported the output record and path summary consistently. |
| Interpretation | The PyLith smoke file contains one time record, so this run checks HDF5 history reading but does not demonstrate evolving failure in a PyLith time series. The transition behavior is verified with a synthetic stress history. No OOI observations or paper-reported results were used. |

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

## Fixed-grid Mogi comparison

| Field | Value |
| --- | --- |
| Code revision | `c195cf2` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API; PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make mogi-benchmark` |
| Configuration | Synthetic 200 m radius spherical cavity at 2 km depth, 10 MPa inflation, and uniform elastic host properties; surface output interpolated to a fixed 41 × 41 grid spanning ±6 km |
| Runtime | 7.58 s for mesh generation, the bounded PyLith solve, and comparison |
| Mesh | 3,191 linear tetrahedra; 975 volume vertices |
| Result | Peak sampled uplift was `6.22485e-4 m`; the interpolated-axis error was 33.602%, and the fixed-grid vector L2 error was 40.446%. |
| Validation | Passed. The interpolation recovered a synthetic linear vector field exactly in unit tests, rejected points outside the mesh, and produced finite positive PyLith uplift. `make test` passed with 29 tests; `make lint` passed. |
| Interpretation | Fixed sample coordinates make comparisons independent of surface-node locations. The coarse finite-domain mismatch remains too large for quantitative validation; mesh and domain convergence have not been established. All cases are synthetic; no BPR observations or publication-supplied results were used. |

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
| Code revision | `0d435e7` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make ooi-maxwell-ellipsoid-check` |
| Configuration | 2014–2026 OOI monthly pressure history on the 2,761-tetrahedron ellipsoid; postprocess each of 147 Cauchy-stress records with `C = 1 MPa`, `phi = 25°` used directly, and zero pore pressure |
| Runtime | 60.36 s for static calibration, 12.07-year Maxwell run, failure postprocessing, and validation; PyLith steps are bounded by 300 s |
| Result | Mohr–Coulomb yield cells range from 55 to 685. A face-connected cavity-to-top path occurs in 146 records, first at 5,184,000 s (60 days). Maximum cavity tensile stress is 63.97 MPa; the tensile cutoff is not applied. |
| Interpolated onset | Linear interpolation of stress between the 30- and 60-day records estimates the first path at 2,766,143.03 s (32.02 days); bisection returns a numerical bracket narrower than 0.01 s. The stress path is assumed linear and the connectivity transition monotonic within that interval; no PyLith integration occurs between saved records. |
| Validation | Passed. Failure analysis covers all 147 strictly increasing stress records; PyLith reached 380,851,200 s and wrote finite stress and viscous strain. `make test` passed with 57 tests; `make lint` passed. |
| Interpretation | This is an OOI-only threshold diagnostic, not a hindcast or eruption prediction. The 60-day saved-record path and 32.02-day interpolated estimate depend on nonconverged static compliance, an assumed friction-angle interpretation, zero pore pressure, one Maxwell branch, and linear stress interpolation. OOI does not cover the 1998 or 2011 cycles; no publication data were used. |

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

## Hydrothermal-field Maxwell integration check

| Field | Value |
| --- | --- |
| Code revision | `aeaa66f` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API; PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make thermal-maxwell-smoke` |
| Configuration | Hydrothermal steady field with Arrhenius viscosity; explicit smoke values of 35 GPa Young's modulus, 2,800 kg/m³ density, and 0.25 Poisson ratio; fixed 10 MPa cavity traction for 2 s |
| Runtime | 12.66 s for mesh generation, both thermal solves, material-database creation, and PyLith |
| Mesh | 2,761 linear tetrahedra; 666 vertices |
| Result | Cell viscosities ranged from `1.80476e13` to `9.62582e30 Pa s` and matched the Arrhenius law evaluated from the archived temperatures. PyLith completed at 2 s with finite fields, peak Cauchy stress `1.71789e7 Pa`, and peak viscous strain `2.89708e-4`. Reordered PyLith vertices and cell centroids matched the thermal mesh after coordinate sorting. |
| Validation | Passed. `make test` passed with 31 tests, `make lint` passed, and the full `make thermal-maxwell-smoke` workflow passed. |
| Interpretation | Verifies one-way transfer of the computed steady temperature field into PyLith's initial Maxwell material properties. The modulus, density, and Poisson ratio are explicit smoke assumptions; temperature stays fixed during mechanics. No OOI observations or publication-supplied model results were used. This is not a coupled historical model. |

The generated material database and HDF5 outputs remain under ignored
`pylith/step04_thermal_maxwell/output/`.

## Same-mesh Maxwell material-property restart

| Field | Value |
| --- | --- |
| Code revision | `d762e9e87716d4bd7a5806ab7185f74b68c9d088` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make maxwell-restart` |
| Configuration | Continuous 0–2 s run, unchanged-property 0–1 s and 1–2 s restart, and a separate 1–2 s restart with Eq. 15 and Eq. 16 properties from a uniform 1200 °C field; fixed 10 MPa cavity load |
| Runtime | 20.7 s for mesh generation and four bounded PyLith solves; each solver call uses a 300 s timeout |
| Mesh | 2,761 linear tetrahedra; 666 nodes; same mesh for every segment |
| Result | The unchanged-property restart differs from the continuous run by `1.612e-8` for displacement, Cauchy stress, total strain, and viscous strain at 2 s. In the updated-property restart, viscous strain at 1 s has zero relative error; final displacement differs from the uniform-property run by `50.08%`. |
| Validation | Passed. All PyLith runs reached their requested end times and wrote finite fields. `make test` passed with 50 tests; `make lint`, `bash -n scripts/maxwell_restart_smoke.sh`, and `git diff --check` passed. |
| Interpretation | Verifies same-mesh state transfer and replacement of the material database between segments. The uniform 1200 °C state is synthetic and tests the interface; it does not model thermal evolution or mechanical feedback. The boundary snapshot is checked for viscous strain, while displacement is compared at 2 s. No OOI observations or publication data were used. |

Generated meshes, material databases, logs, and HDF5 output remain local under
the ignored `pylith/step01_maxwell_restart/output/` directory.

## OOI Maxwell response and failure-history diagnostic figure

| Field | Value |
| --- | --- |
| Code revision | `89a4d6c` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Matplotlib 3.11.2 |
| Command | `make ooi-maxwell-history-plot` |
| Inputs | 143 monthly common-finite OOI samples from 2014-09-05 through 2026-09-30; aggregate QC code `2` retained without filtering; maximum gap is 122 days. The figure reads the saved 147-record Maxwell and failure histories. |
| Result | Central Maxwell uplift RMSE is 1.096 m (correlation 0.787); Eastern RMSE is 0.195 m (correlation 0.922). The static elastic pressure fit spans −60.98 to 21.05 MPa. A cavity-to-top Mohr–Coulomb path occurs in 146 of 147 records, first at 60 days; maximum cavity tensile stress is 63.97 MPa. |
| Output | `figures/ooi_maxwell_failure_history.png` and `.pdf`; three panels show OOI and Maxwell uplift, inferred pressure, and failure diagnostics. |
| Validation | Passed. The plot checks input columns, finite values, increasing times, and alignment of all 147 failure records with the Maxwell output. `make test` passed with 55 tests; `make lint` passed. |
| Interpretation | OOI-only diagnostic using a static elastic Central compliance fit and a one-branch Maxwell response. The large Central mismatch, coarse nonconverged mesh, retained QC code, 25° direct friction-angle convention, zero pore pressure, and omitted tensile cutoff limit interpretation. No paper publication observations, results, or figure values were used. |

## Consolidated reproduction checkpoint

| Field | Value |
| --- | --- |
| Code revision | `3e5de0a1ce372a652cabe1427f4e530f2a5ca1b3` |
| Command | `make reproduce OOI_END_DATE=2026-10-09` |
| Runtime | 347 s for the bounded PyLith and thermal workflows, OOI processing and checks, figures, tests, lint, and report build |
| Working tree | The source matched this revision; four tracked PDF plots had been regenerated by the preceding checkpoint and were recommitted after this run. |
| OOI inputs | Public OOI `BOTSFLU-DAYDEPTH`; Central: 3,955 daily rows, SHA-256 `817b7a61cb32a7a95fd81b554a400ef2cf0d2a2ddc9ddf591592de7201f0f53f`; Eastern: 4,029 rows, SHA-256 `78a895b48fb43217887d4f75759f2dbe3b3a9d21fe545a626da35182c99e91a7`. Both series contain records through 2026-09-30. Aggregate QC code `2` was retained without filtering. |
| Thermal-to-Maxwell check | Passed. The computed hydrothermal field mapped to the 2,761-cell PyLith mesh; the 2 s solve wrote finite fields with peak stress `1.71789e7 Pa` and peak viscous strain `2.89708e-4`. |
| Validation | All listed workflow targets completed. `make test` passed with 56 tests; Ruff passed; the report build was up to date. |
| Limitations | Ellipsoid compliance mesh convergence remains unestablished. The OOI Maxwell and failure calculations remain diagnostic one-way checks with assumed rheology and failure parameters, not a complete coupled reproduction. Only independent OOI records were used; no paper-associated BPR data, publication results, or figure values were used. |

## Temperature-dependent generalized Maxwell material check

| Field | Value |
| --- | --- |
| Code revision | `0da8f49a7d1a09cccac93f4079fc2d7306f1f6d0` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `timeout 300 bash scripts/generalized_maxwell_ellipsoid_smoke.sh` |
| Configuration | Zero-source Eq. 14 thermal field with Eq. 22 conductivity and Eq. 15 viscosity; synthetic three-branch reference viscosities at 1200 °C, three 0.25 shear fractions, fixed 1 MPa cavity load over two years |
| Boundaries | 0 °C top, 1200 °C reservoir, and 30 °C/km geotherm on the side faces and base; outer temperatures close unspecified thermal boundaries |
| Runtime | 13.94 s for mesh generation, hydrothermal solve, material database, bounded PyLith solve, and output checks |
| Mesh | 2,761 linear tetrahedra |
| Thermal result | Picard iteration converged in 10 steps with relative change `6.196e-10`; temperature ranges from 0–1200 °C |
| Material result | Branch viscosity ranges are `[1.0e18, 5.334e35]`, `[5.0e17, 2.667e35]`, and `[2.0e18, 1.067e36] Pa s` for branches one through three; each varies with temperature according to Eq. 15 |
| Mechanical result | PyLith reached `63,115,200 s`, with peak stress `1.66934e6 Pa` and peak branch viscous strains `[2.01097e-5, 2.01025e-5, 2.01134e-5]` |
| Validation | Passed. `make test` passed with 60 tests; `make lint`, `bash -n scripts/generalized_maxwell_ellipsoid_smoke.sh`, and `git diff --check` passed. |
| Interpretation | Verifies one-way mapping of a steady hydrothermal field into three cellwise Arrhenius Maxwell branches. Reference viscosities and shear fractions are synthetic, the full spectrum and modulus law remain unresolved, and thermal feedback is not implemented. Mesh convergence remains unestablished; no BPR observations or publication data were used. |

The four tracked OOI PDF plots were regenerated. Raw downloads, processed
series, and solver outputs remain ignored local files.

## Historical raw BPR event checks

| Field | Value |
| --- | --- |
| Code revision | `aab9204` |
| Command | `make bpr-historical-check` |
| Inputs | NCEI WC82A raw pressure, SHA-256 `1e33b9e560998d4cec9d6d77257aa3fd8226dbc2778ddce0eb550265d6cef10d`; NCEI WC82B raw pressure, SHA-256 `dfc022228a453b5eeea7ed3dc69847eba73a8f1cabe6c9a476429062f206a2bf`; MGDS IEDA/322282 Center and South archive, SHA-256 `9aedf9b300f91d64516d72a2ad6d2d26a28393a1bf9e1a2f38e348b8a7357f36` |
| Processing | 15-second raw channels averaged by UTC day; at least 75% sample coverage; daily event medians on days −7 to −1 and +8 to +14; no tide or drift correction |
| Event observations | WC82A 1998 change: `−1.128 m`; 2011 Center: `−2.296 m`; 2011 South: `−1.788 m` (relative elevation, up positive) |
| Static ellipsoid check | 2,761 tetrahedra; Center calibration gives `−71.968 MPa`; South prediction `−0.356 m`, observed `−1.788 m`, residual `−1.431 m` |
| Mogi check | `E = 60 GPa`, assumed `ν = 0.25`, `a = 0.7 km`, `d = 4 km`; inferred pressure `−3.427 GPa`; South prediction `−1.406 m`, residual `−0.381 m` |
| Validation | `make bpr-historical-check` completed; `make lint` and `git diff --check` passed. |
| Interpretation | Raw event-scale records show subsidence in both eruption windows. The static ellipsoid misses much of the 2011 South displacement, while the small-source Mogi fit requires a very large pressure change. Both checks omit viscoelastic memory; the ellipsoid mesh is not converged, and raw daily means retain tidal and ocean variability. Neither result validates or rejects the full temperature-dependent model. |

Raw data, daily means, summary files, and figures remain under ignored
`data/raw/axial_bpr/` and `data/processed/axial_historical_bpr/`. The source
selection and MGDS attribution are recorded in [`historical_bpr_check.md`](historical_bpr_check.md).

## Historical raw BPR check with WC81

| Field | Value |
| --- | --- |
| Code revision | `0066347` |
| Command | `make bpr-historical-check` |
| Inputs | NCEI WC81 raw pressure, SHA-256 `537c259ded381c2c9309c2e249d99dff675a0d45494d1c43460fcc91e5ca3d39`; WC82A and WC82B raw pressure, unchanged checksums above; MGDS IEDA/322282 Center and South archive, unchanged checksum above |
| Processing | 15-second raw channels averaged by UTC day; at least 75% sample coverage; event medians on days −7 to −1 and +8 to +14; no tide or drift correction |
| Event observations | WC81 Center: `−3.289 m`; WC82A South: `−1.128 m`; 2011 Center: `−2.296 m`; 2011 South: `−1.788 m` (relative elevation, up positive) |
| Validation | Historical check completed; `make test` passed with 56 tests; `make lint`, the NCEI-only fetcher dry run, and `git diff --check` passed. |
| Interpretation | The raw 1998 South response is 34% of the Center response in these event windows, adding a two-station observation check. The event-window changes remain uncorrected estimates; static elastic model diagnostics still use the 2011 pair, and the mesh remains unconverged. |

WC81 and its checksum are recorded in the ignored local manifest. The updated
event figure and daily values remain local alongside the prior records.

## Historical Center-to-South checks for both eruptions

| Field | Value |
| --- | --- |
| Code revision | `1a5a4688a6e9af1bbd2cfc6f9ab6a82a1f6f3405` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `timeout 300 make bpr-historical-check` |
| Configuration | Fit the Center station for each eruption's uncorrected daily event change; predict WC82A for 1998 and NeMO South for 2011 using the static Mogi benchmark and PyLith ellipsoid unit response |
| Event observations | 1998 WC81 `−3.289 m`, WC82A `−1.128 m`; 2011 Center `−2.296 m`, South `−1.788 m` (relative elevation, up positive) |
| Mogi result | 1998 pressure fit `−4.909 GPa`, WC82A prediction `−1.549 m`, residual `+0.421 m`; 2011 pressure fit `−3.427 GPa`, South prediction `−1.406 m`, residual `−0.381 m` |
| Ellipsoid result | 2,761 tetrahedra; 1998 fit `−103.092 MPa`, WC82A prediction `−0.253 m`, residual `−0.875 m`; 2011 fit `−71.968 MPa`, South prediction `−0.356 m`, residual `−1.431 m` |
| Runtime | 37.5 s for mesh generation, bounded PyLith unit response, daily aggregation, four spatial predictions, and figures |
| Validation | Passed. `make test` passed with 57 tests; `make lint`, Python compilation, and `git diff --check` passed. |
| Interpretation | Both static models miss the held-out raw event displacements, especially the PyLith ellipsoid predictions. The Mogi fits require multi-gigapascal pressure changes. Raw daily data are uncorrected, the ellipsoid mesh is not converged, and both models omit viscoelastic memory; these checks do not validate or reject the full model. No data products or results associated with Cabaniss et al. were used. |

Model summaries and raw/processed observations remain local under ignored
`data/processed/axial_historical_bpr/` and `data/raw/axial_bpr/`.

## Full-overlap historical BPR Mogi checks

| Field | Value |
| --- | --- |
| Code revision | `50fcdfcf29dbe4c015ac8cea5551a27f6f5923cd` |
| Command | `timeout 300 make bpr-historical-check` |
| Inputs | Original NCEI `seafloor_pressure_abs_raw` and MGDS `RawDep`/`Depth` channels; processed into UTC daily means with at least 75% sample coverage. No derived paper-associated channels were used. |
| Configuration | Static elastic Mogi model with `E = 60 GPa`, assumed `ν = 0.25`, source radius `0.7 km`, and depth `4 km`; both stations use a shared seven-day pre-event baseline. Center calibrates each day and South remains held out. |
| 1998 interval | WC81/WC82A: 309 paired days from 1997-10-03 through 1998-08-07; South RMSE `0.305 m`, bias `+0.252 m`, correlation `0.996`; fitted pressure range `−4.939` to `+0.077 GPa`. |
| 2011 interval | NeMO Center/South: 314 paired days from 2010-09-05 through 2011-07-25; South RMSE `0.205 m`, bias `−0.150 m`, correlation `0.999`; fitted pressure range `−3.492` to `+0.112 GPa`. |
| Runtime | 37.5 s for the bounded PyLith unit response, raw daily aggregation, event and full-overlap model checks, and figures |
| Validation | Passed. `make test` passed with 59 tests; `make lint` and `git diff --check` passed. |
| Interpretation | High correlations reflect the shared eruption-scale change but do not remove the biases or multi-gigapascal pressure requirements. These uncorrected raw-channel comparisons omit ocean variability, instrument drift, and viscoelastic memory. They are diagnostic checks, not a calibrated pressure history or eruption forecast. No Cabaniss-associated data products or results were used. |

Aligned daily CSVs, summaries, and figures remain local under ignored
`data/processed/axial_historical_bpr/`.

## Inter-eruption raw BPR deployment checks

| Field | Value |
| --- | --- |
| Code revision | `dcc8819` |
| Command | `timeout 300 make bpr-historical-check` |
| Inputs | Five NCEI raw files and MGDS IEDA/322282 UIDs 896874–896884. The selected MGDS archive is 374,400,512 bytes with SHA-256 `48cfd20330d98a1dc73a1b5b6f82be7870f266ac61be574f5d7df1090c0f8feb`. |
| Processing | Sixteen deployments span 1997-10-03 through 2013-08-14, with gaps between instrument records; 10,356 daily means pass the 75% coverage threshold. Only original `Depth` and `RawDep` fields are read. |
| 2003–05 interval | 614 paired days from 2003-09-05 through 2005-05-10; South RMSE `0.134 m`, bias `+0.113 m`, correlation `0.709`; fitted pressure range `−0.036` to `+0.892 GPa`. |
| 2007–09 interval | 572 paired days from 2007-08-16 through 2009-03-15; South RMSE `0.156 m`, bias `+0.136 m`, correlation `−0.123`; fitted pressure range `−0.282` to `+0.336 GPa`. |
| 2011–13 interval | 731 paired days from 2011-07-31 through 2013-08-09; South RMSE `0.387 m`, bias `+0.363 m`, correlation `0.993`; fitted pressure range `−0.138` to `+1.462 GPa`. |
| Runtime | 129.73 s for the bounded PyLith unit response, raw daily aggregation, event checks, deployment-overlap checks, and figures |
| Validation | Passed. `make test` passed with 61 tests; Ruff passed; `make report` produced an eight-page PDF. The generated deployment and Mogi figures were visually checked. |
| Interpretation | These raw-channel diagnostics retain tides, ocean variability, and instrument drift, and the static elastic model omits viscoelastic memory. Large biases and fitted pressure ranges prevent calibration claims; the intervals extend independent checks rather than produce corrected deformation histories. No paper-produced data products or results were used. |

The ignored MGDS source archive and derived daily series remain under
`data/raw/axial_bpr/` and `data/processed/axial_historical_bpr/`.

## Integrated reproduction after historical deployment checks

| Field | Value |
| --- | --- |
| Code revision | `d62bea8` |
| Command | `make reproduce OOI_END_DATE=2026-10-08` |
| Runtime | 494 s for the bounded PyLith and thermal workflows, OOI processing and checks, historical raw BPR checks, figures, tests, lint, and report build |
| Working tree | Source matched `d62bea8` at run start. Seven tracked artifacts were regenerated: five PDFs and two PNGs. |
| OOI inputs | Public `BOTSFLU-DAYDEPTH`; Central: 3,955 daily rows; Eastern: 4,029 rows; both contain records through 2026-09-30. Aggregate QC code `2` was retained without filtering. |
| Historical inputs | NCEI raw channels and original MGDS `Depth`/`RawDep` channels, including UIDs 896874–896884; 16 deployments and 10,356 usable daily means span 1997-10-03 through 2013-08-14 with deployment gaps. No Cabaniss-associated data products or results were used. |
| OOI checks | Static Mogi held-out East RMSE `0.0594 m`, correlation `0.995`; static ellipsoid held-out East RMSE `0.221 m`, correlation `0.995`. One-branch Maxwell runs completed for uniform and Eq. 16/hydrothermal properties; both remain forward diagnostics with provisional static pressure calibration. |
| Historical checks | 1998 and 2011 event checks and 2003–05, 2007–09, and 2011–13 Center-to-South checks completed on raw channels. Their fitted pressure histories remain static-elastic diagnostics and are not eruption predictions. |
| Validation | All reproduction targets completed. `make test` passed with 61 tests; Ruff passed; the report compiled to eight pages. |
| Limitations | Ellipsoid compliance mesh convergence remains unestablished. Raw channels retain ocean variability and instrument drift, and the thermal-to-mechanics workflow remains one-way. The full coupled reproduction is incomplete. |

Raw downloads, daily series, and solver outputs remain ignored local files.

## Rebuild with hydrothermal property slices

| Field | Value |
| --- | --- |
| Base revision | `51c1cce`; the validated feature source was committed as `6d4367b` after the run. |
| Command | `make reproduce OOI_END_DATE=2026-10-08` |
| Runtime | 499 s for the thermal, mechanics, OOI and historical BPR checks, figures, tests, lint, and report build |
| OOI inputs | Public `BOTSFLU-DAYDEPTH`; Central: 3,955 daily rows; Eastern: 4,029 rows; both contain records through 2026-09-30. Aggregate QC code `2` was retained without filtering. |
| Historical inputs | Original NCEI and MGDS `Depth`/`RawDep` channels; 16 deployments and 10,356 usable daily means span 1997-10-03 through 2013-08-14 with gaps. No Cabaniss-associated data products or results were used. |
| Thermal solve | The hydrothermal field converged in 10 Picard iterations with relative change `6.196e-10` and relative energy imbalance `1.151e-11`. The new midplane projection uses cell centers within `0.7 km` of `y = 0`. |
| Validation | All reproduction targets completed. `make test` passed with 61 tests; Ruff passed; the updated report compiled to nine pages. |
| Limitations | The slice covers one hydrothermal temperature-dependent configuration. It shows Eq. 16 as printed despite the unresolved modulus inconsistency; the other rheologies and generalized branch spectrum are unavailable. The side and basal geotherm remains an explicit assumption, and the plot is a finite-thickness cell-center projection rather than an exact plane interpolation. |

The hydrothermal property figure and updated report are tracked. Raw BPR
downloads, processed series, and solver fields remain in ignored local paths.

## Rebuild with model setup schematic

| Field | Value |
| --- | --- |
| Base revision | `60cf4cc`; the validated schematic source was committed as `d1d7c81` after the run. |
| Command | `make reproduce OOI_END_DATE=2026-10-08` |
| Runtime | 504 s for the thermal, mechanics, OOI and historical BPR checks, figures, tests, lint, and report build |
| OOI inputs | Public `BOTSFLU-DAYDEPTH`; Central: 3,955 daily rows; Eastern: 4,029 rows; both contain records through 2026-09-30. Aggregate QC code `2` was retained without filtering. |
| Historical inputs | Original NCEI and MGDS `Depth`/`RawDep` channels; 16 deployments and 10,356 usable daily means span 1997-10-03 through 2013-08-14 with gaps. No Cabaniss-associated data products or results were used. |
| Schematic | Generated a geometry and boundary diagram for the 40 × 40 × 20 km project fallback box and 6 × 3 × 1 km reservoir at 1.6 km center depth. The drawing labels the side/basal geotherm as an assumption, Winkler stiffness as unresolved, and the 60 mm/year full spreading rate without assigning a face split. |
| Validation | All reproduction targets completed. `make test` passed with 61 tests; Ruff passed; the report compiled to nine pages. |
| Limitations | The schematic is not a numerical result or a reproduction of the published image. Model extent, thermal side and base conditions, absolute Winkler stiffness, and tectonic face-rate split remain unresolved. |

The schematic and report are tracked artifacts. Raw BPR downloads, processed
series, and solver fields remain in ignored local paths.

## PyLith ellipsoid checks across historical deployments

| Field | Value |
| --- | --- |
| Code revision | `bb5cdac` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `timeout 300 make bpr-historical-check` |
| Inputs | Original NCEI raw pressure and MGDS `Depth`/`RawDep` channels; 16 deployments and 10,356 usable daily means from 1997-10-03 through 2013-08-14. No paper-associated corrections, observations, or results were used. |
| Configuration | Daily Center fit and South holdout using the 1 MPa PyLith ellipsoid response, `E = 50 GPa`, assumed `ν = 0.25`, and 2,761 tetrahedra. First seven paired days define each deployment baseline. |
| 2003–05 interval | 614 paired days; South RMSE `0.257 m`, bias `+0.252 m`, correlation `0.709`; fitted pressure `−0.746` to `18.735 MPa`. |
| 2007–09 interval | 572 paired days; South RMSE `0.124 m`, bias `+0.104 m`, correlation `−0.123`; fitted pressure `−5.917` to `7.052 MPa`. |
| 2011–13 interval | 731 paired days; South RMSE `0.614 m`, bias `+0.551 m`, correlation `0.993`; fitted pressure `−2.888` to `30.714 MPa`. |
| Runtime | 126 s for PyLith unit response, raw daily aggregation, event and overlap checks, and figures |
| Validation | `make test` passed with 64 tests; Ruff passed; `make report` produced a nine-page PDF; `git diff --check` passed. |
| Interpretation | The static ellipsoid comparison adds three longer spatial checks. High correlation during 2011–13 coexists with a large positive residual bias; the 2007–09 prediction is weakly anticorrelated. The mesh is not converged, and raw channels retain tides, ocean variability, and sensor drift. These outputs are diagnostics, not calibrated pressure histories or eruption forecasts. |

The deployment figure and report are tracked. Daily comparison rows, summaries,
raw records, and PyLith outputs remain under ignored local paths.

## Five-level ellipsoid mesh sensitivity

| Field | Value |
| --- | --- |
| Code revision | `dcdca3d` |
| Environment | Conda `envs/axial-modeling`; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make ellipsoid-mesh-sensitivity` (run twice) |
| Configuration | Fixed cavity and far-field sizes of 1,200 m and 10,000 m; local station-region sizes of 1,100, 1,000, 950, and 900 m; maximum 3,500 tetrahedra per mesh; Central and Eastern surface compliance sampled from the 1 MPa elastic response |
| Results | Coarse: 2,761 tetrahedra, Central/Eastern `0.0318994/0.00345580 m/MPa`; 1,100 m: 3,031, `0.0240399/0.00198816`; 1,000 m: 3,124, `0.0225148/0.00230768`; 950 m: 3,053, `0.0359864/0.00364735`; 900 m: 3,325, `0.0233475/0.00249709` |
| Fine-step changes | From 1,000 to 950 m: Central/Eastern `+59.8%/+58.1%`; from 950 to 900 m: `−35.1%/−31.5%`. The meshes are generated independently, are not guaranteed to be nested, and element count is not monotonic in target size. |
| Repeatability | A second full run reproduced all five counts and compliance values exactly. |
| Runtime | 28.28 s and 28.35 s for the two five-case runs |
| Interpretation | Compliance convergence is not established. None of the adjacent local-refinement pairs meets the 5% tolerance at both stations; the irregular response makes pressure and spatial-error estimates provisional. No observational data were used. |
| Validation | `make test` passed (64 tests), `make lint` passed, `make report` rebuilt the 10-page report, and `git diff --check` passed. |

The machine-readable result is ignored under `data/processed/`; no raw BPR
observations or paper-associated outputs were used in this mesh-only check.

## Extend raw Axial BPR coverage to 1987

| Field | Value |
| --- | --- |
| Code revision | `569aa39` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make bpr-historical-check` |
| Inputs | Ten added NCEI raw BPR deployments from 1987–96, plus the existing NCEI and original MGDS channels. Across 26 deployments, 13,711 usable daily means span 1987-09-23 through 2013-08-14, with deployment gaps. The first five added records use 56.25-second sampling; the other five use 15-second sampling. |
| 1995–96 overlap | WC68 Center / WC69 South; 338 paired days. Static Mogi: South RMSE `0.155 m`, bias `+0.138 m`, correlation `0.876`, fitted pressure `−54.8` to `+260.5 MPa`. Static PyLith ellipsoid: RMSE `0.180 m`, bias `+0.159 m`, correlation `0.876`, fitted pressure `−1.151` to `+5.472 MPa`. |
| 1998 and 2011 events | Existing raw event estimates were reproduced: 1998 WC81/WC82A `−3.289/−1.128 m`; 2011 Center/South `−2.296/−1.788 m`, uplift positive. |
| Runtime | 146.03 s for mesh response, raw daily aggregation, event and overlap checks, and figures |
| Figures | `figures/historical_bpr_deployment_context.png` and PDF show separate deployment baselines from 1987–2013; the tracked four-panel PyLith ellipsoid comparison now includes the 1995–96 overlap. |
| Validation | `make test` passed (65 tests), `make lint` passed, `make report` rebuilt the 10-page PDF, and `git diff --check` passed. |
| Interpretation | The 1995–96 raw South trend is not captured by either static fit. The data extend temporal and spatial checks before the 1998 eruption, but independent baselines, tides, ocean variability, and instrument drift prevent treating this as a corrected continuous deformation history. No paper-produced data or results were used. |

Raw NCEI downloads, daily CSVs, and model summaries remain ignored under
`data/raw/axial_bpr/` and `data/processed/axial_historical_bpr/`.

## Cross-mesh thermal property transfer

| Field | Value |
| --- | --- |
| Code revision | `ec8175f` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make thermal-cross-mesh-smoke` |
| Configuration | Synthetic affine temperature field on a six-tetrahedron box source mesh; mapped to mechanics element centers on the 40 × 40 × 20 km ellipsoid mesh. The source mesh deliberately does not represent the reservoir thermal geometry. |
| Result | 2,761 mechanics tetrahedra received barycentric point samples. Maximum difference from the analytic affine temperature was `1.137e-13 °C`. |
| PyLith result | Two-second Maxwell solve completed with finite Cauchy stress and viscous strain; peak stress was `1.68912e7 Pa`. |
| Runtime | 8.29 s, including Gmsh mesh generation and PyLith |
| Validation | `make test` passed with 68 tests; `make lint`, `make report` (11-page PDF), `bash -n scripts/thermal_cross_mesh_smoke.sh scripts/reproduce.sh`, and `git diff --check` passed. |
| Interpretation | This verifies source-mesh point location, affine-field interpolation, material-database generation, and PyLith consumption of mapped properties. It does not validate a physical field transfer, a conservative transfer, time-varying material updates, or two-way thermal-mechanical feedback. No observations or paper-produced data were used. |

The source archive, mesh, material database, and PyLith output remain ignored
under `pylith/step01_maxwell_restart/`.

## Bounded Mogi domain and mesh sensitivity

| Field | Value |
| --- | --- |
| Code revision | `eb79174` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make mogi-domain-sensitivity` |
| Configuration | Two linear spherical-cavity cases; fixed 12 km far-field and 20 m near-source target sizes, 10 MPa pressure, and identical 41 × 41 Mogi comparison grid. Each PyLith invocation is bounded by 300 s. |
| Baseline | 8 km horizontal half-width and 8 km bottom depth; 3,191 tetrahedra; peak sampled uplift `0.622485 mm`; interpolated-axis error `33.602%`; vector L2 error `40.446%`. |
| Expanded domain | 12 km horizontal half-width and 12 km bottom depth; 2,784 tetrahedra; peak sampled uplift `0.240522 mm`; interpolated-axis error `74.597%`; vector L2 error `58.047%`. |
| Runtime | 11.66 s for both mesh builds, PyLith solves, and comparisons |
| Validation | `make test` passed with 68 tests; `make lint`, shell syntax checks, `make report` (11-page PDF), and `git diff --check` passed. |
| Interpretation | Peak uplift falls 61.4% in the expanded run, but meshes are independently generated and nonnested. These cases expose unresolved mesh and domain sensitivity; they do not isolate boundary effects or validate the Mogi response quantitatively. No observations or paper-generated values were used. |

Generated meshes, HDF5 fields, and case logs remain ignored under
`pylith/step02_mogi_benchmark/output/`.

## Physical hydrothermal field transfer across meshes

| Field | Value |
| --- | --- |
| Code revision | `dca8a87` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `make thermal-cross-mesh-smoke` |
| Configuration | Written steady hydrothermal model solved on a 3,060-tetrahedron ellipsoid mesh; mapped by barycentric point sampling to 2,761 mechanics tetrahedra on a separately generated mesh. Outer boundaries use the assumed 30 °C/km geotherm; reservoir boundary is 1,200 °C. |
| Runtime | 9.03 s, including two mesh builds, thermal solve, database generation, and bounded PyLith solve |
| Thermal result | Picard iteration converged in 10 steps. Transferred mechanics-cell temperatures span 8.769–1,066.240 °C. A separate affine manufactured-field check retains a maximum interpolation error of `1.137e-13 °C`. |
| PyLith result | The mapped material database completed a two-second Maxwell solve with finite stress and viscous strain; peak stress was `1.75811e7 Pa`. The smoke case assumes a depth-varying 35 GPa reference modulus, density `2,800 kg/m³`, and Poisson ratio `0.25`; it does not apply the inconsistent printed Eq. 16. |
| Validation | `make test` passed (68 tests), `make lint`, shell syntax checks, and `git diff --check` passed. The physical source and mechanics meshes each stay below the 3,500-tetrahedron setup cap; the PyLith run is bounded by 300 s. |
| Interpretation | This verifies transfer of an actual solved steady field into an initial mechanics solve. It does not establish conservative transfer, time-varying properties, mesh convergence, or two-way thermal-mechanical feedback. No BPR observations or paper-associated data were used. |

The thermal source mesh, material database, and solver outputs remain ignored
under `pylith/step01_maxwell_restart/output/`.

## Cross-check original 1998 BPR archive channels

| Field | Value |
| --- | --- |
| Code revision | `4d735bb` |
| Environment | Conda `envs/axial-modeling`; Python 3.12 |
| Command | `make bpr-archive-crosscheck` |
| Inputs | MGDS Fox IEDA/322344 archive, 26,330,112 bytes, SHA-256 `afaabde737186c331696ad5bec1ffc071ecb0e90daaddf52b3e2792474df8da7`; original `Depth` values only, with detided and low-pass-filtered columns excluded. |
| Runtime | 15.15 s for source parsing, daily aggregation, event-window checks, and comparisons |
| Center comparison | 309 shared days, 1997-10-03 through 1998-08-07; relative-uplift correlation `0.999999999996`, RMSE `0.04956 m`, and MGDS-minus-NCEI bias `+0.03722 m`. |
| South comparison | 365 shared days, 1997-10-03 through 1998-10-02; correlation `0.999999999942`, RMSE `0.01648 m`, and bias `+0.01215 m`. A separate 8-day WC82B overlap has `0.00026 m` RMSE but is too short for a strong comparison. |
| Event values | Fox raw `Depth`: Center `−3.212 m`, South `−1.102 m`. NCEI raw pressure: Center `−3.289 m`, South `−1.128 m`. The roughly 2.3% amplitude difference is consistent with the archives' different pressure-to-depth conversion factors. |
| Validation | `make test` passed (70 tests), `make lint`, the historical fetcher dry run, report compilation (11 pages), shell syntax checks, and `git diff --check` passed. |
| Interpretation | The two archives record the same physical BPRs and closely matching uplift signals. This checks raw-channel parsing and units; it adds no independent station coverage. No Cabaniss-associated observations, corrections, model outputs, or figure values were used. |

The raw MGDS archive and local JSON comparison remain ignored under
`data/raw/axial_bpr/mgds/` and `data/processed/axial_historical_bpr/`.
## Three-branch generalized Maxwell constitutive output check

| Field | Value |
| --- | --- |
| Code revision | `e7b9b68` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `timeout 300 bash scripts/generalized_maxwell_ellipsoid_smoke.sh` |
| Configuration | Two-year constant 1 MPa cavity load; `E = 50 GPa`, `ν = 0.25`, synthetic viscosities `[1.0e18, 5.0e17, 2.0e18] Pa s`, and shear fractions `[0.25, 0.25, 0.25]` |
| Mesh and output | 2,761 tetrahedra; 25 saved time records; final time `63,115,200 s` |
| Constitutive check | Reconstructed Cauchy stress from total strain and branch state using PyLith Eqs. 88–90; relative L2 error `2.029e-16` over all cells, tensor components, and saved times. |
| Step-size check | Maximum saved interval `2.592e6 s`; shortest relaxation time `1.0e8 s`; documented one-fifth limit `2.0e7 s`. |
| Mechanical result | Peak stress `1.80755 MPa`; peak branch viscous strains `1.875e-5`, `1.435e-5`, and `2.149e-5`. |
| Runtime | 13.6 s for mesh generation, database creation, PyLith, and output verification |
| Validation | `make test` passed with 63 tests; Ruff, shell syntax, and `git diff --check` passed. |
| Interpretation | The reconstruction verifies consistency among material fractions, PyLith branch state, strain, and Cauchy stress. The time-step check verifies the documented stability bound. Neither result establishes temporal convergence or the paper's missing relaxation spectrum; all branch values remain synthetic. |

The run's mesh, logs, material database, and HDF5 output remain ignored under
`pylith/step12_generalized_maxwell_ellipsoid/`.

## Temperature-dependent three-branch stress reconstruction

| Field | Value |
| --- | --- |
| Code revision | `0ddab53` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `timeout 300 bash scripts/generalized_maxwell_ellipsoid_smoke.sh` |
| Configuration | Zero-source steady Eq. 14 field with Eq. 22 conductivity and Eq. 15 cellwise viscosity; three synthetic branch reference viscosities at 1200 °C; fixed 1 MPa cavity load for two years |
| Mesh and thermal result | 2,761 tetrahedra; Picard iteration converged in 10 steps with relative change `6.196e-10`; temperatures span 0–1200 °C. |
| Constitutive check | Reconstructed Cauchy stress from saved total strain and all three branch states over 25 output times; relative L2 error `1.991e-16`. |
| Step-size check | Maximum saved interval `2.592e6 s`; shortest cellwise relaxation time `1.0e8 s`; one-fifth limit `2.0e7 s`. |
| Mechanical result | PyLith reached `63,115,200 s`; peak stress `1.66934 MPa`; branch peak viscous strains were `2.011e-5`, `2.010e-5`, and `2.011e-5`. |
| Runtime | 13.6 s for mesh generation, hydrothermal solve, material database, PyLith, and output verification |
| Validation | `make test` passed with 66 tests; Ruff, shell syntax, and `git diff --check` passed. |
| Interpretation | The independent reconstruction confirms consistency among the thermal material database, branch states, strain, and PyLith stress. The step-size check is below the documented stability limit. The test does not establish temporal convergence or the paper's missing relaxation spectrum; branch reference values remain synthetic. |

The mesh, thermal archive, logs, material database, and HDF5 output remain
ignored under `pylith/step12_generalized_maxwell_ellipsoid/`.

## Temperature-dependent Maxwell time-step refinement

| Field | Value |
| --- | --- |
| Code revision | `b5e6328` |
| Environment | Conda `envs/axial-modeling`; Python 3.12; Gmsh 4.15.2 Python API |
| Solver | PyLith 5.0.2; PETSc 3.25.4 |
| Command | `scripts/generalized_maxwell_timestep_refinement.sh` |
| Configuration | Same 2,761-cell mesh, hydrothermal temperature field, material database, and two-year 1 MPa cavity load; time step changed from 30 to 15 days |
| Output records | 25 at 30 days and 49 at 15 days; both reach `63,115,200 s` |
| Final-field change | Coarse-to-fine relative L2 change is 1.82% for Cauchy stress, 8.77% for viscous strain, and 0.917% for displacement |
| Constitutive check | Stress reconstruction relative error is `1.991e-16` at 30 days and `1.964e-16` at 15 days; both steps are below the `2.0e7 s` one-fifth relaxation-time limit |
| Validation | `make test` passed with 66 tests; `make lint`, shell syntax, and `git diff --check` passed. |
| Interpretation | The paired runs quantify temporal sensitivity for this synthetic case. They do not establish temporal convergence, because only two step sizes were compared, and they do not address mesh convergence or the unresolved paper rheology. No BPR observations or publication data were used. |

The refinement script preserves the 30-day output and writes 15-day results to
separate ignored files under `pylith/step12_generalized_maxwell_ellipsoid/`.


## Integrated clean rebuild with fixed-date OOI selection

| Field | Value |
| --- | --- |
| Code revision | `44674770a4a212963e1900628895e770578ff29b` (integrated historical BPR and temperature-dependent generalized Maxwell branches) |
| Command | `make reproduce OOI_END_DATE=2026-10-08` |
| Runtime | 411 s for OOI and historical BPR retrieval and processing, bounded thermal and PyLith checks, figures, tests, lint, and report compilation |
| OOI inputs | Public `BOTSFLU-DAYDEPTH`; Central: 3,955 rows; Eastern: 4,029 rows. Both processed series end on 2026-09-30, and aggregate QC code `2` was retained. Downstream checks selected the newly processed `_2026-10-08` files. |
| Historical inputs | NCEI raw absolute-pressure channels and original MGDS `RawDep` and `Depth` channels; derived and paper-produced products were excluded. |
| Generalized Maxwell check | The hydrothermal temperature solve converged in 10 iterations at relative change `6.196e-10`; the 2,761-cell PyLith solve reached `63,115,200 s` with finite state fields in all three branches. |
| Validation | Passed. `make test` passed with 62 tests, Ruff passed, and the eight-page report compiled. The tracked OOI figures and report PDF were regenerated. |
| Interpretation | The integrated rebuild covers the currently implemented checks; it does not provide the required thermomechanical feedback, a resolved generalized branch spectrum, or mesh-converged compliance. The OOI and historical checks remain diagnostics, not eruption forecasts. No Cabaniss-associated data products or results were used. |

Raw downloads, processed observations, meshes, and solver output remain in
ignored local paths.

## Consolidated full rebuild on the review branch

| Field | Value |
| --- | --- |
| Source revision at run start | `2d3b989` |
| Command | `make reproduce OOI_END_DATE=2026-10-08` |
| Runtime | 590 s for raw OOI and historical BPR retrieval and processing, bounded thermal and PyLith checks, figures, tests, lint, and report compilation |
| OOI inputs | Public `BOTSFLU-DAYDEPTH`; Central: 3,955 rows; Eastern: 4,029 rows. Both end on 2026-09-30; aggregate QC code `2` was retained without filtering. |
| Historical inputs | 26 NCEI/MGDS deployments produced 13,711 usable daily means across 1987–2013. Processing used original absolute-pressure, `Depth`, and `RawDep` channels only; the separate Fox 1997–98 `Depth` archive cross-check also completed. |
| Generalized Maxwell check | The hydrothermal field converged in 10 iterations; the 2,761-cell, three-branch PyLith run reached `63,115,200 s`. Reconstructed stress agreed with PyLith to relative L2 error `1.937e-16`. |
| Historical event checks | 1998 WC81/WC82A relative-elevation changes were `−3.289/−1.128 m`; 2011 Center/South changes were `−2.296/−1.788 m`. The Fox archive cross-check completed with center and south RMSE `0.0496/0.0165 m`. |
| Validation | All reproduction targets completed. `make test` passed with 82 tests; `make lint` passed; the report compiled to 11 pages. |
| Interpretation | The integrated checks still use one-way thermal properties and nonconverged ellipsoid compliance. Historical series retain ocean variability and instrument drift. These checks do not complete the coupled model or produce eruption forecasts; no Cabaniss-associated products or results were used. |

Raw downloads, processed time series, meshes, and solver outputs remain ignored
local files.

## Historical three-branch Maxwell checks against raw BPR records

| Field | Value |
| --- | --- |
| Source revision at run start | `9e32545cc0daef36de4978d112e986fa7c71bfd3` (historical three-branch driver and Make integration; documentation changes were in progress) |
| Command | `make reproduce OOI_END_DATE=2026-10-08` |
| Runtime | 632 s for OOI and historical BPR retrieval and processing, bounded thermal and PyLith checks, figures, tests, lint, and report compilation |
| OOI inputs | Central: 3,955 rows; Eastern: 4,029 rows; 3,927 common finite daily records through 2026-09-30. Aggregate QC code `2` was retained. |
| Historical inputs | 26 NCEI/MGDS deployments yielded 13,711 usable daily means. The checks used original raw absolute pressure, `Depth`, or `RawDep` channels; no Cabaniss-produced histories, corrections, results, or figures were used. |
| 1998 three-branch check | WC81/WC82A: 309 paired days from 1997-10-03 to 1998-08-07; center RMSE/bias `0.186/−0.132 m`; South RMSE/bias/correlation `0.503/+0.329 m/0.995`; inferred pressure `−94.385` to `+10.952 MPa`. |
| 2011 three-branch check | NeMO Center/South: 314 paired days from 2010-09-05 to 2011-07-25; center RMSE/bias `0.114/−0.061 m`; South RMSE/bias/correlation `0.680/+0.371 m/0.997`; inferred pressure `−72.795` to `+2.908 MPa`. |
| Maxwell setup | 2,761 tetrahedra; synthetic reference branch viscosities `[1e18, 5e17, 2e18] Pa·s` and shear fractions `[0.25, 0.25, 0.25]`; maximum output interval `604,800 s`, below one-fifth of the `1e8 s` minimum relaxation time. |
| Validation | All reproduction targets completed. `make test` passed with 85 tests; `make lint` passed; the report compiled to 12 pages. The report PDF and historical comparison figure were generated. |
| Interpretation | The daily raw observations retain ocean variability and instrument drift. Pressure uses static, nonconverged elastic compliance, and branch values are synthetic. The results test a forward loading path; they do not calibrate rheology or produce a hindcast or forecast. |

Raw downloads, processed time series, meshes, and solver outputs remain ignored
local files.

## Extend generalized Maxwell checks across historical deployment overlaps

| Field | Value |
| --- | --- |
| Source revision at run start | `e5c3584` (deployment-overlap extension was in the working tree) |
| Command | `make historical-generalized-maxwell-check` |
| Runtime | Approximately 118 s for mesh/compliance preparation, thermal material generation, and six bounded PyLith runs |
| Additional intervals | WC68/WC69: 338 paired days in 1995–96; NeMO Center/South: 614 days in 2003–05, 572 days in 2007–09, and 731 days in 2011–13. Each deployment has an independent first-day baseline; gaps are not interpolated. |
| Held-out South checks | RMSE/bias/correlation: 1995–96 `0.183/−0.161 m/0.793`; 2003–05 `0.651/−0.649 m/0.660`; 2007–09 `0.123/−0.101 m/−0.355`; 2011–13 `1.242/−1.214 m/0.991`. |
| Time-step check | Each run used a maximum output step of `604,800 s`, below one-fifth of the `1e8 s` minimum branch relaxation time. A constant-pressure endpoint support sample prevents round-off from truncating the PyLith time-history query; model runs still end on the final observed day. |
| Validation | All six PyLith runs completed. `make test lint` passed with 86 tests and Ruff clean; shell syntax and `git diff --check` passed. `make report` compiled the updated report to 14 pages. |
| Interpretation | The Center-fit South prediction varies from weakly anticorrelated to high-correlation with large bias. Synthetic branch values and mesh-sensitive static compliance remain limiting assumptions; the additional intervals extend checks but do not calibrate rheology. |

Raw downloads, processed time series, meshes, and solver outputs remain ignored
local files.

## Historical Mohr--Coulomb checks on three-branch eruption runs

| Field | Value |
| --- | --- |
| Source revision at run start | `1e0313b` on `historical-generalized-maxwell-check` |
| Command | `make historical-generalized-maxwell-check` |
| Runtime | 183 s for static compliance, thermal properties, and six bounded PyLith runs |
| Failure proxy | Per saved stress record for 1998 and 2011; cohesion `1 MPa`, friction angle `25°` used directly as `phi`, zero pore pressure, and no tensile cutoff |
| 1998 path | A cavity-to-top path is present in all 44 records; the first saved output is day 7, so onset is bounded at or before day 7. Maximum saved yielded-cell count is 803. |
| 2011 path | First saved path is at day 21; linear interpolation estimates onset at day 17.61. A path is present in 30 of 47 records; maximum saved yielded-cell count is 716. |
| Validation | All six PyLith runs completed; `make test` passed with 86 tests; `make lint` passed; `make report` compiled the 14-page report. |
| Interpretation | The proxy connects the cavity and surface well before either eruption under synthetic branch properties. The first-record 1998 path only bounds onset, and the 2011 interpolation does not integrate PyLith between outputs. These are exploratory thresholds, not eruption timing predictions. Only original raw BPR channels were used; no paper-produced data products were used. |

Per-record path flags, yielded-cell counts, and cavity tensile stresses are
stored in ignored event CSVs under `data/processed/axial_historical_bpr/`.

## Extend stress-threshold checks across the raw BPR windows

| Field | Value |
| --- | --- |
| Source revision at run start | `0a8baf5` (six-window stress-analysis extension in the working tree) |
| Command | `make historical-generalized-maxwell-check` |
| Runtime | 193 s for compliance, thermal properties, and six bounded PyLith runs |
| Inputs | Original raw NCEI absolute-pressure channels and MGDS `Depth`/`RawDep` channels; no publication-associated data products |
| Failure proxy | Per saved stress record in all six windows; cohesion `1 MPa`, `25°` friction angle used directly as `phi`, zero pore pressure, and no tensile cutoff |
| Path records | 1995–96: `46/49`, first path by day 7; 1998: `44/44`, first path by day 7; 2003–05: `83/88`, interpolated onset day 25.38; 2007–09: `68/83`, onset day 67.86; 2011: `30/47`, onset day 17.61; 2011–13: `105/106`, first path by day 7. |
| Validation | All six PyLith runs completed; `make test` passed with 86 tests; `make lint` passed; `make report` compiled the updated 14-page report. |
| Interpretation | The same proxy path appears within 68 days in all windows, including four inter-eruption intervals. Synthetic branch properties and the other threshold assumptions do not distinguish eruption timing. The interpolated values assume linear stress change between records and do not integrate PyLith within the interval. |

The per-record path histories remain in ignored CSVs under
`data/processed/axial_historical_bpr/`.

## Add two raw BPR stations as independent spatial holdouts

| Field | Value |
| --- | --- |
| Source revision at run start | `0fce94a` (additional station checks in the working tree) |
| Command | `make historical-generalized-maxwell-check` |
| Runtime | 192 s for compliance, thermal properties, and six bounded PyLith runs |
| Additional observations | Original NCEI WC67 for 1995–96; original MGDS NeMO South 1 over the 572-day 2007–09 model window. Neither is used in its window's Center pressure history. |
| WC67 prediction | 338 paired days; RMSE `0.036 m`, bias `−0.021 m`, correlation `0.685`. |
| NeMO South 1 prediction | 572 paired days; RMSE `0.221 m`, bias `−0.191 m`, correlation `−0.506`. |
| Validation | All six PyLith runs completed; `make test` passed with 86 tests; `make lint` passed; the report and deployment comparison figure were regenerated. |
| Interpretation | WC67 has smaller absolute residuals but only moderate correlation; the alternative 2007–09 South record is anticorrelated and biased. The independent raw stations show that spatial transfer varies by deployment; they do not calibrate the rheology. No publication-associated data products were used. |

The additional station series are written to ignored CSVs, included in each
window's JSON summary, and overlaid in the tracked deployment comparison plot.

## Integrated clean rebuild with expanded raw BPR checks

| Field | Value |
| --- | --- |
| Source revision | `d46232ca5e2252d9675f631e58d509ae59736f4d` |
| Command | `make reproduce OOI_END_DATE=2026-10-08` |
| Runtime | 774 s for raw data retrieval and processing, bounded PyLith checks, figures, tests, lint, and report compilation |
| OOI inputs | Central: 3,955 daily rows; Eastern: 4,029 rows. Both series end on 2026-09-30; aggregate quality code `2` (`NOT_EVALUATED`) is retained. |
| Historical inputs | Original raw NCEI pressure and MGDS `Depth`/`RawDep` channels from 26 deployments. The WC67 and NeMO South 1 holdouts are included; no publication-associated products are used. |
| Model checks | Six three-branch BPR windows from 1995 through 2013 completed, with two additional held-out stations. The 1998 and 2011 event overlaps completed, as did the multi-year OOI checks. |
| Validation | The starting tree was clean; all reproduction targets completed; `make test` passed with 86 tests; Ruff passed; the 14-page report compiled. |
| Interpretation | Static ellipsoid compliance remains unconverged, thermal properties remain one-way, and Maxwell branches are synthetic. The checks expand observation coverage but do not calibrate eruption timing or complete the coupled model. No Cabaniss-associated data products were used. |

Raw downloads, processed observations, meshes, and solver outputs remain in
ignored local directories.

## Add the 2005--07 raw BPR overlap

| Field | Value |
| --- | --- |
| Source revision at run start | `9022da0` (2005–07 interval added in the working tree) |
| Command | `make historical-generalized-maxwell-check` |
| Runtime | 205 s for compliance, thermal properties, and seven bounded PyLith runs |
| Inputs | Original MGDS NeMO Center `RawDep` and South 1 `Depth` channels; no Cabaniss-associated products |
| Observation window | 810 paired valid days from 2005-05-12 through 2007-08-08; each deployment retains its independent instrument, with pressure zeroed on the first shared valid day. |
| Held-out South prediction | RMSE `0.157 m`, bias `−0.135 m`, correlation `0.958`. |
| Failure proxy | 71 of 117 saved stress records have a cavity-to-surface path; the first interpolated path occurs at day 195.84 under the existing `1 MPa`, `25°`, zero-pore-pressure proxy, without tensile cutoff. |
| Validation | All seven PyLith runs completed; `make test` passed with 86 tests; `make lint` passed; `make report` compiled the updated 14-page report. |
| Interpretation | This interval extends raw BPR model checking from 2005 into 2007. The deployment-local baseline, static-compliance pressure inversion, and synthetic branch values remain provisional; the path diagnostic does not establish eruption timing. |

The comparison series and stress-history CSV remain in the ignored
`data/processed/axial_historical_bpr/` directory.

## Invert OOI pressure with a Maxwell response kernel

| Field | Value |
| --- | --- |
| Source revision at run start | `071f6e0` with the pressure-inversion implementation in the working tree |
| Command | `make ooi-maxwell-pressure-inversion` |
| Runtime | 107 s for static ellipsoid calibration, two bounded Maxwell runs, inversion, and plotting |
| Inputs | 3,927 independent OOI Central/Eastern daily records from 2014-09-05 through 2026-09-30; aggregate QC code `2` retained; 143 monthly common-finite means interpolated to 148 uniform pressure knots |
| Inversion | Central-fitted one-branch Maxwell ramp kernel; second-difference Tikhonov penalty selected by generalized cross-validation; inferred pressure ranges from `−60.4` to `+11.8 MPa` |
| Fit and holdout | Central RMSE `0.00495 m`, correlation `0.99997`; Eastern RMSE `0.225 m`, correlation `0.9835` |
| Kernel check | Direct PyLith relative L2 error is `0.000283` at Central and `0.000799` at Eastern; both bounded runs completed |
| Failure proxy | 55 Mohr–Coulomb yield cells at the first output, then a cavity-to-surface path by day 60; interpolated onset is about day 32.2 under `1 MPa` cohesion, `25°` friction, and zero pore pressure, without tensile cutoff |
| Outputs | `figures/ooi_maxwell_viscoelastic_inversion.png` and PDF; processed CSV and JSON remain ignored under `data/processed/` |
| Interpretation | The kernel reproduces its linear PyLith response and fits Central uplift closely, but the Eastern residual and extreme inferred pressure leave the physical pressure scale unresolved. The one-branch rheology, smoothing prior, monthly interpolation, and nonconverged mesh remain assumptions. No Cabaniss-associated observations, corrections, outputs, or figure values were used. |

The new comparison figure was visually checked. The report includes it as a
project diagnostic, not as a reproduction of a manuscript panel.

## Invert raw BPR event histories with Maxwell response kernels

| Field | Value |
| --- | --- |
| Source revision at run start | `fb3f41a` with the raw-history inversion implementation in the working tree |
| Command | `make historical-bpr-maxwell-pressure-inversion` |
| Runtime | 78 s for two paired event inversions, four bounded PyLith runs, and plotting; raw daily means were current |
| Inputs | 309 raw NCEI WC81/WC82A paired days in 1997–98 and 314 raw MGDS NeMO Center/South paired days in 2010–11; original `seafloor_pressure_abs_raw`, `RawDep`, and `Depth` channels only |
| Sampling | Daily means with at least 75% coverage; 1998 uses a 7.00-day grid and 2011 a 7.02-day grid; maximum paired-data gaps are 1 and 7 days |
| 1998 fit and holdout | WC81 Center RMSE `0.093 m`, correlation `0.998`; WC82A South RMSE `0.535 m`, bias `+0.362 m`, correlation `0.995`; inferred pressure `−107.4` to `+12.0 MPa` |
| 2011 fit and holdout | NeMO Center RMSE `0.125 m`, correlation `0.992`; NeMO South RMSE `0.713 m`, bias `+0.385 m`, correlation `0.991`; inferred pressure `−71.6` to `+3.6 MPa` |
| Kernel check | Center/South relative L2 errors are `0.000340`/`0.001281` for 1998 and `0.000343`/`0.000570` for 2011 |
| Outputs | `figures/historical_maxwell_pressure_inversion.png` and PDF; per-event daily series and JSON remain ignored under `data/processed/axial_historical_bpr/maxwell_pressure_inversion/` |
| Validation | Both unit-ramp and inferred-history runs completed for each event; all 97 unit tests passed; Ruff passed; the 17-page report compiled; the figure was visually checked |
| Interpretation | The response kernels reproduce direct PyLith output, and each Central fit captures the eruption-scale deflation. Held-out South biases and inferred pressures show that mesh, rheology, and smoothing assumptions do not calibrate a physical pressure history. No publication-produced observations, corrections, outputs, or figure values were used. |

MGDS-derived plotted values retain the source archive's CC BY-NC-SA 3.0 terms
and attribution to William Chadwick, Scott Nooner, and MGDS.

## Extend static deployment checks through 2007

| Field | Value |
| --- | --- |
| Source revision at run start | `f8c3916` |
| Command | `make bpr-historical-check` |
| Runtime | 135 s for ellipsoid unit response, raw daily processing, event checks, and five deployment overlaps |
| Inputs | Original NCEI raw pressure and MGDS `Depth`/`RawDep` channels; no paper-produced data |
| New observation window | NeMO Center/South 1, 810 paired valid days from 2005-05-12 through 2007-08-08 |
| Static Mogi check | South RMSE `0.135 m`, bias `+0.118 m`, correlation `0.966`; Center-fit pressure ranges from `−0.085` to `+0.414 GPa`. |
| Static ellipsoid check | South RMSE `0.166 m`, bias `+0.142 m`, correlation `0.966`; Center-fit pressure ranges from `−1.782` to `8.691 MPa`. |
| Validation | `make bpr-historical-check` completed; `make test` passed with 86 tests; Ruff passed; `make report` compiled the 14-page report. |
| Interpretation | Static checks use a seven-day deployment baseline and retain ocean variability and instrument drift. The pressure fit is not a calibrated eruption history. |

The aligned comparison CSVs and JSON summaries remain in the ignored
`data/processed/axial_historical_bpr/` directory.

## Check two additional raw stations with static models

| Field | Value |
| --- | --- |
| Source revision at run start | `8cb933f` |
| Commands | `scripts/historical_bpr_mogi_deployments.py`; `scripts/historical_bpr_ellipsoid_deployments.py` |
| Runtime | 2.4 s for the two static comparison scripts run in parallel |
| Inputs | Original raw NCEI WC67 and MGDS NeMO South 1 channels, held out from their Center fits |
| WC67 comparison | 338 paired days in 1995–96. Mogi RMSE/bias/correlation are `0.015 m`/`−0.003 m`/`0.943`; ellipsoid values are `0.028 m`/`+0.013 m`/`0.943`. |
| NeMO South 1 comparison | 667 paired days through 2009-06-18. Mogi RMSE/bias/correlation are `0.272 m`/`+0.238 m`/`−0.325`; ellipsoid values are `0.244 m`/`+0.211 m`/`−0.325`. |
| Validation | Both static comparison scripts completed; `make test` passed with 86 tests; Ruff passed; `make report` compiled the 14-page report. |
| Interpretation | These spatial predictions use Center-fit pressure and the same raw, uncorrected daily channels as the generalized Maxwell checks. WC67 residuals are small; NeMO South 1 is anticorrelated. Neither static model includes viscoelastic memory. |

The tracked ellipsoid figure shows all seven held-out station comparisons. The
aligned comparison files remain under the ignored
`data/processed/axial_historical_bpr/` directory.

## Localize ellipsoid mesh refinement around BPR sampling sites

| Field | Value |
| --- | --- |
| Source revision at run start | `d288768` with station-box meshing and the expanded sensitivity sequence in the working tree |
| Command | `timeout 300 make ellipsoid-mesh-sensitivity` |
| Runtime | 50.14 s for ten bounded unit-pressure mesh and PyLith runs |
| Configuration | 40 × 40 × 20 km domain, 6 × 3 × 1 km ellipsoid, fixed 1 MPa traction; 1,200 m cavity-near and 10,000 m far-field sizes; two 1,200 × 1,200 × 300 m surface boxes centered at the Central and Eastern sample coordinates; station-box mesh sizes from 800 to 25 m |
| Results | The baseline mesh has 2,761 tetrahedra and Central/Eastern compliance `0.0318994/0.00345580 m/MPa`. Station-box meshes have 2,586–2,664 tetrahedra; their compliance ranges are `0.0117940–0.0139307 m/MPa` at Central and `0.00123705–0.00161727 m/MPa` at Eastern. |
| Fine-step changes | Compliance changes between the 50 and 25 m station boxes are `+0.080%` at Central and `−0.039%` at Eastern. The preceding 100-to-50 m Eastern change is `+6.55%`, while the 150-to-100 m change is `+19.85%`. |
| Sampling proximity | In the 25 m target mesh, the nearest top-surface vertices are 138.6 m from Central and 101.7 m from Eastern; the target size does not guarantee that the exact interpolation locations are resolved. |
| Validation | All ten PyLith solves wrote finite surface responses; every mesh stayed below 2,700 tetrahedra. `make test` passed with 97 tests, `make lint` passed, and `make report` compiled the 17-page report. `git diff --check` passed. No observations were used. |
| Interpretation | Refining only the sampling neighborhoods changes the baseline compliance by −63.0% at Central and −54.7% at Eastern. The final pair is close, but the intervening changes, sampling-point offsets, and independently generated, nonnested meshes do not establish convergence. Pressure and spatial errors remain provisional. |

The summary remains under ignored `data/processed/`; mesh files and PyLith
outputs were temporary.
