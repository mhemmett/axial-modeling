# Figure-by-figure reproduction record

This is the live record for all figures and caption-described panels in
Cabaniss et al. (2020) and its supplement. Written specifications and all six
supplementary figure captions have been extracted. No panel is currently
independently reproduced. The figures themselves and their plotted values have
not been inspected or used as model inputs.

## Provenance rules

Allowed scientific specifications are the paper, its supplementary materials,
and other written descriptions of the model. Do not consult or use the
authors’ code, model outputs, plotting scripts, source datasets, or figure
files. Do not digitize plots. Published figures may be inspected after the
implementation produces results, only to assess visual agreement. Any such
image in the report must be labelled “published reference” and displayed
separately from project-generated output.

Independent OOI bottom-pressure-recorder (BPR) records are authorized for model
checking. Do not use datasets supplied with or cited by the paper. OOI's daily
depth product covers Central and Eastern Caldera from 2014 onward and retains
its quality flags; it does not cover the 1998 and 2011 events. Earthquake
catalogs, bathymetry, and lava-flow source records remain outside the authorized
inputs. Use synthetic data only for software verification, never as a
substitute for observational input in a manuscript comparison.

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
| Fig. 1b | Geological setting and model geometry, thermal/property slices, boundaries, and tectonic loading. Model schematic is separable from numerical results. | `TBD: project model/mesh command` | `TBD: project schematic script` | Schematic only if redrawn from the written specification; do not count it as a model-result panel. Geometry and property fields require Phase 1 parameter extraction. |
| Fig. 2 | Center-BPR inflation/deflation history with eruption markers and earthquake counts. Caption identifies measured histories and event data. | `python data/fetch_bpr.py --download` | `TBD: observation/model plot script` | Partial comparison is possible for OOI observations from 2014 onward. The pre-2014 record and earthquake counts are unavailable from authorized inputs; model output has not yet been compared. |
| Fig. 3 / non-TD elastic configuration | The caption describes 2-D slices of Young's modulus, viscosity, thermal gradient, and thermal conductivity for this rheology. The caption does not expose subpanel IDs or layout. | `TBD: coupled model command` | `TBD: figure script` | Not reproduced. This is a configuration-level inventory entry, not a claim that Fig. 3 has an (a) panel. Expand into one row per visible numerical panel after written panel metadata are recovered. |
| Fig. 3 / non-TD viscoelastic configuration | Property and thermal-field slices for this rheology; exact subpanel set and layout are not stated in the available caption text. | `TBD: coupled model command` | `TBD: figure script` | Not reproduced. Configuration-level entry; split into actual panel IDs during inventory completion. |
| Fig. 3 / temperature-dependent viscoelastic configuration | Temperature-dependent property and thermal-field slices; exact subpanel set and layout are not stated in the available caption text. | `TBD: coupled model command` | `TBD: figure script` | Not reproduced. Configuration-level entry; split into actual panel IDs during inventory completion. |
| Fig. 3 / temperature-dependent viscoelastic plus hydrothermal configuration | Property and thermal-field slices with enhanced brittle-crust conductivity; exact subpanel set and layout are not stated in the available caption text. | `TBD: coupled model command` | `TBD: figure script` | Not reproduced. Configuration-level entry; split into actual panel IDs during inventory completion. |
| Fig. 4a | Modeled reservoir overpressure histories calibrated against measured surface deformation, with eruption timing and the reported 12–14 MPa band. | `TBD: model and calibration command` | `TBD: figure script` | Not reproduced. OOI permits calibration checks from 2014 onward; the earlier pressure history and complete eruption cycles are unavailable from authorized inputs. |
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
| Supplementary Fig. S1 | Two-dimensional slices through the three-dimensional model space showing Young's modulus, viscosity, thermal gradient, and thermal conductivity for all four rheologies; the reservoir appears in the upper left of each slice. Subpanel letters are not given in the caption. | `TBD: coupled model command` | `TBD: figure script` | Not reproduced. Values and field equations are recorded in `docs/parameters.yaml`; no panel-level layout is inferred from the unviewed image. |
| Supplementary Fig. S2 | Effect of hydrothermal circulation on the location of the brittle–ductile transition. | `TBD: coupled model command` | `TBD: figure script` | Not reproduced. Compare transition depth and distance from the reservoir after the coupled thermal model is verified. |
| Supplementary Fig. S3 | Benchmark compatibility among the Mogi elastic analytical solution, the Del Negro viscoelastic analytical solution, the Gregg et al. 2D FEM, and the Cabaniss et al. 3D FEM; also compares Winkler and roller base conditions. | `TBD: analytical and FEM benchmark command` | `TBD: figure script` | Not reproduced. The comparison requires independently generated analytical and numerical results; author outputs and plotted values are excluded. |
| Supplementary Fig. S4 | Surface displacement response to Winkler-foundation spring stiffness compared with an elastic roller base; agreement persists until stiffness is weakened by about six orders of magnitude. | `TBD: boundary-condition benchmark command` | `TBD: figure script` | Not reproduced. PyLith has no native Winkler foundation; validate an implementation or a documented substitute before comparison. |
| Supplementary Fig. S5 | Three-dimensional model setup: 30 °C/km background geotherm, 0 °C surface, 1200 °C reservoir boundary, steady-state thermal structure, Winkler base, roller sides, and opposing prescribed velocities representing 60 mm/year ridge extension. | `TBD: model configuration command` | `TBD: optional schematic script` | Not reproduced. A redraw may be labelled schematic; the 60 mm/year full-rate face convention remains unresolved against Table S1's -20 to 20 mm/year prescribed-velocity range. |
| Supplementary Fig. S6 | Reservoir overpressure required to reproduce deformation at the Center BPR for the tested reservoir geometries and rheologies. | `TBD: calibration command` | `TBD: figure script` | Not reproduced. OOI allows a calibration check from 2014 onward, but missing pre-2014 observations and unresolved model inputs prevent the full published comparison. |

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
