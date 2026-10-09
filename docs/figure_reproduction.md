# Figure-by-figure reproduction record

This is the live record for all figures and caption-described panels in
Cabaniss et al. (2020) and its supplement. Written specifications and all six
supplementary figure captions have been extracted. No panel is currently
independently reproduced. Independent OOI observations cover part of Fig. 2's
time series from 2014 onward, and raw historical BPR checks add deployments
from 1987 through 2022. Published figure panels and their plotted values have
not been inspected or used as model inputs.

## Provenance rules

Allowed scientific specifications are the paper, its supplementary materials,
and other written descriptions of the model. Do not consult or use the
authors’ code, model outputs, plotting scripts, data products produced for the
paper, or figure files. Do not digitize plots. Published figures may be
inspected after the implementation produces results, only to assess visual
agreement. Any such image in the report must be labelled “published reference”
and displayed separately from project-generated output.

Independent OOI bottom-pressure-recorder (BPR) records and original raw BPR
channels from earlier Axial deployments are authorized for model checking. Do
not use pressure histories, corrections, values, figures, or other data
products produced for the paper, even when an archive also cites it. OOI's
daily depth product covers Central and Eastern Caldera from 2014 onward and
retains its quality flags; raw historical channels provide event checks for
1998 and 2011. Earthquake catalogs, bathymetry, and lava-flow source records
remain outside the authorized inputs. Use synthetic data only for software
verification, never as a substitute for observational input in a manuscript
comparison.

## Status definitions

| Status | Required evidence |
| --- | --- |
| Not reproduced | No project-generated numerical panel exists, or required input or method is unavailable, or the attempt failed. State which case applies. |
| Partially reproduced | Project-generated data reproduce only part of the plotted quantity, time span, conditions, or spatial domain. Identify the coverage and gap. |
| Independently reproduced | The plotted data came from this implementation, the required methods and inputs are documented, and numerical comparison supports the match. |
| Schematic | A conceptual redraw only. Label it as a schematic; it is not a reproduced numerical result. |

The publisher's supplementary captions identify Figs. S1–S6 but do not provide
subpanel letters. Their rows below therefore record each figure and every
quantity named in its caption without inferring a visual panel layout. Under
the provenance rule, inspect any panel layout only after project-generated
results exist.

## Main article inventory

Commands shown as pending are not implemented yet. Replace them with exact,
working commands and output paths after each panel has a data generator and
plotting script. Record the configuration hash or revision alongside each run.

| Panel | Quantity and written specification | Data command | Plot command | Current status and comparison record |
| --- | --- | --- | --- | --- |
| Fig. 1a | Bathymetry, 2011/2015 lava-flow outlines, earthquakes, reservoir outlines, and instrument locations. Caption identifies third-party mapped and catalog data; inputs are prohibited here. | Not available under provenance rules | Not available | Not reproduced. Do not rebuild from source records or copy the published panel. |
| Fig. 1b | Geological setting and model geometry, thermal/property slices, boundaries, and tectonic loading. Model schematic is separable from numerical results. | Written geometry and boundary specification | `make model-setup-schematic` → `figures/model_setup_schematic.png` | Schematic only. It shows the project fallback 40 × 40 × 20 km domain, specified reservoir geometry, boundary labels, and unresolved tectonic face-rate split. It does not include geological source records or numerical results. |
| Fig. 2 | Center-BPR inflation/deflation history with eruption markers and earthquake counts. Caption identifies measured histories and event data. | `make bpr-observation-plot`; `make bpr-historical-check`; `make historical-generalized-maxwell-check`; `make historical-post-2011-bpr-check`; `make historical-post-2017-bpr-check`; `make historical-early-bpr-spatial-check` | OOI: `figures/ooi_bpr_relative_uplift.png`; raw deployments: `figures/historical_bpr_deployment_context.png`; generalized Maxwell event and overlap checks: `figures/historical_generalized_maxwell_bpr_check.png`, `figures/historical_generalized_maxwell_deployment_bpr_check.png`, `figures/historical_generalized_maxwell_deployment_bpr_check_1995_2009.png`, `figures/historical_generalized_maxwell_deployment_bpr_check_2011_2017.png`, `figures/historical_generalized_maxwell_deployment_bpr_check_2018_2022.png` | Partial independent record. Original raw NCEI channels add deployments from 1987–2002 and MGDS channels add deployments from 2003–2022; OOI covers 2014 onward. The 1987–1996 NCEI check adds three spatial holdouts. Generalized Maxwell checks cover nine paired windows from 1995–2022 plus the 1998/2011 eruption deployments; raw channels retain separate baselines, tides, ocean variability, and instrument drift, while compliance remains unconverged. The unstable 2017–18 Center channel is shown for context and excluded from model forcing. Earthquake counts, continuous inter-deployment histories, and the paper's model comparison are absent. No publication-produced observations or results were used. |
| Fig. 3 / non-TD elastic configuration | The caption describes 2-D slices of Young's modulus, viscosity, thermal gradient, and thermal conductivity for this rheology. The caption does not expose subpanel IDs or layout. | `TBD: coupled model command` | `TBD: figure script` | Not reproduced. This is a configuration-level inventory entry, not a claim that Fig. 3 has an (a) panel. Expand into one row per visible numerical panel after written panel metadata are recovered. |
| Fig. 3 / non-TD viscoelastic configuration | Property and thermal-field slices for this rheology; exact subpanel set and layout are not stated in the available caption text. | `make maxwell-ellipsoid-smoke` for the one-branch solver diagnostic | `TBD: figure script` | Not reproduced. The smoke checks constant-property Maxwell state evolution but does not implement the generalized rheology or produce the property and thermal slices. |
| Fig. 3 / temperature-dependent viscoelastic configuration | Temperature-dependent property and thermal-field slices; exact subpanel set and layout are not stated in the available caption text. | `make thermal-maxwell-ellipsoid-smoke`; `make eq16-maxwell-ellipsoid-smoke` | `TBD: figure script` | Not reproduced. The Eq. 16 run is a printed-equation diagnostic; the intended modulus trend remains unresolved. The smokes do not implement the generalized branch spectrum or produce the full figure slices. |
| Fig. 3 / temperature-dependent viscoelastic plus hydrothermal configuration | Property and thermal-field slices with enhanced brittle-crust conductivity; exact subpanel set and layout are not stated in the available caption text. | `make thermal-model` | `make thermal-property-slices` → `figures/thermal_property_slices.png` | Partially reproduced as a y=0 finite-thickness slice for the hydrothermal case, showing Eq. 15 viscosity, Eq. 16 modulus as printed, Eq. 22 conductivity, and the computed thermal gradient. The side and base geotherm is an explicit assumption; Eq. 16 conflicts with its stated limits, the generalized branch spectrum is unavailable, and three-dimensional figure slices remain incomplete. |
| Fig. 4a | Modeled reservoir overpressure histories calibrated against measured surface deformation, with eruption timing and the reported band. | `make bpr-historical-check`; `make ellipsoid-bpr-check`; `make ellipsoid-mesh-sensitivity`; `make historical-bpr-maxwell-pressure-inversion`; `make ooi-maxwell-ellipsoid-check`; `make ooi-maxwell-pressure-inversion`; `make ooi-eq16-hydrothermal-maxwell-check`; `make ooi-maxwell-history-plot`; `make historical-generalized-maxwell-check`; `make historical-post-2011-bpr-check`; `make historical-post-2017-bpr-check`; `make historical-generalized-maxwell-1998-continuous-check`; `make historical-generalized-maxwell-2011-continuous-check` | Raw BPR context: `figures/historical_bpr_deployment_context.png`; generalized Maxwell event and deployment checks: `figures/historical_generalized_maxwell_bpr_check.png`, `figures/historical_generalized_maxwell_deployment_bpr_check.png`, `figures/historical_generalized_maxwell_deployment_bpr_check_1995_2009.png`, `figures/historical_generalized_maxwell_deployment_bpr_check_2011_2017.png`, `figures/historical_generalized_maxwell_deployment_bpr_check_2018_2022.png`, `figures/historical_generalized_maxwell_1998_continuous_bpr_check.png`, `figures/historical_generalized_maxwell_2011_continuous_bpr_check.png`; diagnostics under ignored `data/processed/axial_historical_bpr/` and `data/processed/`; `figures/historical_ellipsoid_deployment_checks.png`; `figures/ooi_maxwell_failure_history.png`; `figures/ooi_maxwell_viscoelastic_inversion.png`; `figures/historical_maxwell_pressure_inversion.png` | Not reproduced. Static and three-branch checks cover 1998 and 2011 event records, a 1995–96 NCEI spatial holdout, MGDS deployment overlaps through 2022, and OOI records from 2014–2026. The new 2013–15 South 2, 2015–17 South 2, 2018–20 South 2, and 2020–22 miniBPR South 1 checks have RMSE values of `0.358`, `0.265`, `0.105`, and `0.043 m`; the 2013–15 South 1 holdout has `1.096 m` RMSE. These windows retain separate baselines and produce provisional pressure changes as large as `−50.7` to `+26.7 MPa`. Continuous 1998 and 2011 runs carry event stress states into later raw South records; each assumes constant pressure after its Center record ends or across the 2011 five-day gap. The one-branch Maxwell-kernel inversions fit Central uplift with `0.093 m` (1998) and `0.125 m` (2011) RMSE and hold South out (`0.535 m` and `0.713 m` RMSE). The nonconverged mesh and assumed smoothness prior leave pressure provisional. These checks do not recover the full pressure history, four rheologies, eruption timing, or the reported band. No publication-produced observations or results were used. |
| Fig. 4b | Modeled reservoir volume increase and observed deformation histories for eruption cycles. | `TBD: model and calibration command` | `TBD: figure script` | Not reproduced. Requires documented calibration inputs; no curve digitization. |
| Fig. 5a | 1998–2011 cycle failure slice at the model-predicted eruption time for one rheology; tensile and Mohr–Coulomb failure. Rheology mapping pending written-source extraction. | `make ellipsoid-failure-progression-smoke` for a two-year, constant-load threshold diagnostic | `TBD: figure script` | Not reproduced. The smoke has no cavity-to-surface shear path, uses assumed rheology and boundary conditions, and does not simulate the 1998–2011 cycle or generate the figure slice. |
| Fig. 5b | 1998–2011 cycle failure slice at the model-predicted eruption time for one rheology; exact mapping pending. | `TBD: model/failure command` | `TBD: figure script` | Not reproduced. |
| Fig. 5c | 1998–2011 cycle failure slice at the model-predicted eruption time for one rheology; exact mapping pending. | `TBD: model/failure command` | `TBD: figure script` | Not reproduced. |
| Fig. 5d | 1998–2011 cycle failure slice at the model-predicted eruption time for one rheology; exact mapping pending. | `TBD: model/failure command` | `TBD: figure script` | Not reproduced. |
| Fig. 5e | 1998–2011 cycle failure slice at the model-predicted eruption time for one rheology; exact mapping pending. | `TBD: model/failure command` | `TBD: figure script` | Not reproduced. |
| Fig. 5f | 1998–2011 cycle failure slice for one rheology at the observed 2011 eruption time; exact mapping pending. | `TBD: model/failure command` | `TBD: figure script` | Not reproduced. |
| Fig. 5g | 1998–2011 cycle failure slice for one rheology at the observed 2011 eruption time; exact mapping pending. | `TBD: model/failure command` | `TBD: figure script` | Not reproduced. |
| Fig. 5h | 1998–2011 cycle failure slice for one rheology at the observed 2011 eruption time; exact mapping pending. | `TBD: model/failure command` | `TBD: figure script` | Not reproduced. |
| Fig. 5i | 1998–2011 cycle failure slice for one rheology at the observed 2011 eruption time; exact mapping pending. | `TBD: model/failure command` | `TBD: figure script` | Not reproduced. |
| Fig. 5j | 1998–2011 cycle failure slice for one rheology at the observed 2011 eruption time; exact mapping pending. | `TBD: model/failure command` | `TBD: figure script` | Not reproduced. |
| Fig. 5k | 2011–2015 cycle failure slice at the model-predicted eruption time for one rheology; tensile and Mohr–Coulomb failure. Rheology mapping pending. | `TBD: model/failure command` | `TBD: figure script` | Not reproduced. Compare event state, spatial pattern, and failure connectivity after implementation. |
| Fig. 5l | 2011–2015 cycle failure slice at the model-predicted eruption time for one rheology; exact mapping pending. | `TBD: model/failure command` | `TBD: figure script` | Not reproduced. |
| Fig. 5m | 2011–2015 cycle failure slice at the model-predicted eruption time for one rheology; exact mapping pending. | `TBD: model/failure command` | `TBD: figure script` | Not reproduced. |
| Fig. 5n | 2011–2015 cycle failure slice at the model-predicted eruption time for one rheology; exact mapping pending. | `TBD: model/failure command` | `TBD: figure script` | Not reproduced. |
| Fig. 5o | 2011–2015 cycle failure slice at the model-predicted eruption time for one rheology; exact mapping pending. | `TBD: model/failure command` | `TBD: figure script` | Not reproduced. |
| Fig. 5p | 2011–2015 cycle failure slice for one rheology at the observed 2015 eruption time; exact mapping pending. | `TBD: model/failure command` | `TBD: figure script` | Not reproduced. |
| Fig. 5q | 2011–2015 cycle failure slice for one rheology at the observed 2015 eruption time; exact mapping pending. | `TBD: model/failure command` | `TBD: figure script` | Not reproduced. |
| Fig. 5r | 2011–2015 cycle failure slice for one rheology at the observed 2015 eruption time; exact mapping pending. | `TBD: model/failure command` | `TBD: figure script` | Not reproduced. |
| Fig. 5s | 2011–2015 cycle failure slice for one rheology at the observed 2015 eruption time; exact mapping pending. | `TBD: model/failure command` | `TBD: figure script` | Not reproduced. |
| Fig. 5t | 2011–2015 cycle failure slice for one rheology at the observed 2015 eruption time; exact mapping pending. | `TBD: model/failure command` | `TBD: figure script` | Not reproduced. |
| Fig. 6a–d | Four-stage conceptual mechanism diagram. This is not a numerical result. | Not applicable | `TBD: optional schematic script` | Schematic only if redrawn; label clearly and exclude from reproduction counts. |

Figure 3's caption describes property fields by rheology but does not identify
each subplot in text. Its four rows above are provisional configuration groups,
not manuscript panel IDs; complete the panel-level inventory only from written
supplemental descriptions or explicit caption metadata. The Fig. 5 caption
groups a–e and k–o at model-predicted eruption times, and f–j and p–t at
observed eruption times. The exact rheology assigned to each letter must be
transcribed from written descriptions; do not infer missing assignments from
plotted color or geometry.

## Supplementary inventory

The publisher-served supplement contains six figure captions. Its PDF pages
carry a “Confidential manuscript submitted” footer, so this transcription is
attributed to that publisher-served copy and may reflect a pre-publication
version. No figure page or plotted data has been inspected.

| Figure | Quantity and written specification | Data command | Plot command | Current status and comparison record |
| --- | --- | --- | --- | --- |
| Supplementary Fig. S1 | Two-dimensional slices through the three-dimensional model space showing Young's modulus, viscosity, thermal gradient, and thermal conductivity for all four rheologies; the reservoir appears in the upper left of each slice. Subpanel letters are not given in the caption. | `make thermal-model` | `make thermal-property-slices` → `figures/thermal_property_slices.png` | Partially reproduced for one hydrothermal temperature-dependent configuration on a y=0 finite-thickness slice. The other rheologies, full model slices, and exact panel layout remain unavailable; Eq. 16 is shown as printed and conflicts with its stated modulus limits. |
| Supplementary Fig. S2 | Effect of hydrothermal circulation on the location of the brittle–ductile transition. | `TBD: thermal-property model command` | `TBD: figure script` | Not reproduced. Compare transition depth and distance from the reservoir after the thermal-property workflow and transition definition are verified. |
| Supplementary Fig. S3 | Benchmark compatibility among the Mogi elastic analytical solution, the Del Negro viscoelastic analytical solution, the Gregg et al. 2D FEM, and the Cabaniss et al. 3D FEM; also compares Winkler and roller base conditions. | `TBD: analytical and FEM benchmark command` | `TBD: figure script` | Not reproduced. The comparison requires independently generated analytical and numerical results; author outputs and plotted values are excluded. |
| Supplementary Fig. S4 | Surface displacement response to Winkler-foundation spring stiffness compared with an elastic roller base; agreement persists until stiffness is weakened by about six orders of magnitude. | `make ellipsoid-base-depth-sensitivity` | No comparison plot | Not reproduced. A 20/30/40 km fixed-base depth sweep gives nonmonotonic BPR compliance changes on nonnested meshes and does not establish convergence or equivalence to the Winkler foundation. |
| Supplementary Fig. S5 | Three-dimensional model setup: 30 °C/km background geotherm, 0 °C surface, 1200 °C reservoir boundary, steady-state thermal structure, Winkler base, roller sides, and opposing prescribed velocities representing 60 mm/year ridge extension. | Written geometry and boundary specification | `make model-setup-schematic` → `figures/model_setup_schematic.png` | Schematic only. The plot labels 30 °C/km side and basal temperatures as project assumptions, the 40 × 40 × 20 km box as a fallback, and the per-face spreading rate as unresolved. It does not reproduce the numerical thermal field. |
| Supplementary Fig. S6 | Reservoir overpressure required to reproduce deformation at the Center BPR for the tested reservoir geometries and rheologies. | `make ellipsoid-bpr-check`; `make ellipsoid-mesh-sensitivity` | `figures/ooi_ellipsoid_elastic_calibration.png` | Not reproduced. Global and local refinements do not establish mesh-converged compliance; the tested rheologies and pre-2014 pressure history are not modeled. |

## Required record for each panel

When a panel is attempted, replace each pending field with:

1. the exact quantity, units, domain, and time shown;
2. allowed source document, page/section/table, and parameter keys;
3. input provenance and whether any observational series is unavailable;
4. exact command that writes the numerical data and its saved output path;
5. exact command that plots those saved data and its output path;
6. software revision, configuration identifier, and validation checks;
7. current status, numerical comparison measures, discrepancies, and failed attempts.

The final LaTeX report will include this record. Every plotted numerical panel
must be traceable from a report figure to a plotting script, saved model output,
run configuration, and written scientific specification.
