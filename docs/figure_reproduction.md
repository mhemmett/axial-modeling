# Figure-by-figure reproduction record

This is the live record for all numerical panels in Cabaniss et al. (2020) and
its supplement. It starts as an inventory and must be completed as source
specifications are extracted and model results become available. No panel is
currently independently reproduced. Article panel descriptions below come from
the published text and captions; the published images and plotted values were
not used as model inputs.

## Provenance rules

Allowed scientific specifications are the paper, its supplementary materials,
and other written descriptions of the model. Do not consult or use the
authors’ code, model outputs, plotting scripts, source datasets, or figure
files. Do not digitize plots. Published figures may be inspected after the
implementation produces results, only to assess visual agreement. Any such
image in the report must be labelled “published reference” and displayed
separately from project-generated output.

Raw bottom-pressure-recorder records, earthquake catalogs, bathymetry, and lava
flow source records are not project inputs under this rule. A panel depending
on those records can be reproduced only if the written article or supplement
contains enough numerical values to reconstruct the plotted quantities without
digitization. Cite the records in provenance notes when relevant, but do not
fetch them. Use synthetic data only for software verification, never as a
substitute for observational input in a manuscript comparison.

## Status definitions

| Status | Required evidence |
| --- | --- |
| Not reproduced | No project-generated numerical panel exists, or required input or method is unavailable, or the attempt failed. State which case applies. |
| Partially reproduced | Project-generated data reproduce only part of the plotted quantity, time span, conditions, or spatial domain. Identify the coverage and gap. |
| Independently reproduced | The plotted data came from this implementation, the required methods and inputs are documented, and numerical comparison supports the match. |
| Schematic | A conceptual redraw only. Label it as a schematic; it is not a reproduced numerical result. |

The panel inventory can use “not yet inventoried” for supplement panels whose
IDs and captions have not been extracted. This is an inventory status, not a
scientific reproduction claim. Assign every supplementary panel its own row
before closing the inventory phase.

## Main article inventory

Commands shown as pending are not implemented yet. Replace them with exact,
working commands and output paths after each panel has a data generator and
plotting script. Record the configuration hash or revision alongside each run.

| Panel | Quantity and written specification | Data command | Plot command | Current status and comparison record |
| --- | --- | --- | --- | --- |
| Fig. 1a | Bathymetry, 2011/2015 lava-flow outlines, earthquakes, reservoir outlines, and instrument locations. Caption identifies third-party mapped and catalog data; inputs are prohibited here. | Not available under provenance rules | Not available | Not reproduced. Do not rebuild from source records or copy the published panel. |
| Fig. 1b | Geological setting and model geometry, thermal/property slices, boundaries, and tectonic loading. Model schematic is separable from numerical results. | `TBD: project model/mesh command` | `TBD: project schematic script` | Schematic only if redrawn from the written specification; do not count it as a model-result panel. Geometry and property fields require Phase 1 parameter extraction. |
| Fig. 2 | Center-BPR inflation/deflation history with eruption markers and earthquake counts. Caption identifies measured histories and event data. | Not available under provenance rules | Not available | Not reproduced unless allowed written sources give the complete numerical series. Do not fetch or digitize. |
| Fig. 3 / non-TD elastic configuration | The caption describes 2-D slices of Young's modulus, viscosity, thermal gradient, and thermal conductivity for this rheology. The caption does not expose subpanel IDs or layout. | `TBD: coupled model command` | `TBD: figure script` | Not reproduced. This is a configuration-level inventory entry, not a claim that Fig. 3 has an (a) panel. Expand into one row per visible numerical panel after written panel metadata are recovered. |
| Fig. 3 / non-TD viscoelastic configuration | Property and thermal-field slices for this rheology; exact subpanel set and layout are not stated in the available caption text. | `TBD: coupled model command` | `TBD: figure script` | Not reproduced. Configuration-level entry; split into actual panel IDs during inventory completion. |
| Fig. 3 / temperature-dependent viscoelastic configuration | Temperature-dependent property and thermal-field slices; exact subpanel set and layout are not stated in the available caption text. | `TBD: coupled model command` | `TBD: figure script` | Not reproduced. Configuration-level entry; split into actual panel IDs during inventory completion. |
| Fig. 3 / temperature-dependent viscoelastic plus hydrothermal configuration | Property and thermal-field slices with enhanced brittle-crust conductivity; exact subpanel set and layout are not stated in the available caption text. | `TBD: coupled model command` | `TBD: figure script` | Not reproduced. Configuration-level entry; split into actual panel IDs during inventory completion. |
| Fig. 4a | Modeled reservoir overpressure histories calibrated against measured surface deformation, with eruption timing and the reported 12–14 MPa band. | `TBD: model and calibration command` | `TBD: figure script` | Not reproduced. Full time-series calibration is blocked by the no-source-data rule unless written numerical inputs suffice. Compare threshold and event timing numerically if independent inputs are available. |
| Fig. 4b | Modeled reservoir volume increase and observed deformation histories for eruption cycles. | `TBD: model and calibration command` | `TBD: figure script` | Not reproduced. Requires documented calibration inputs; no curve digitization. |
| Fig. 5a | 1998–2011 cycle failure slice at the model-predicted eruption time for one rheology; tensile and Mohr–Coulomb failure. Rheology mapping pending written-source extraction. | `TBD: model/failure command` | `TBD: figure script` | Not reproduced. Compare event state, spatial pattern, and failure connectivity after implementation. |
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

The article text references Supplementary Fig. S1 for the complete model-space
and S2 for the brittle–ductile transition. Their captions, all panel IDs, and
any additional supplementary figures have not yet been extracted from the
supplementary document. This is a known inventory gap, not evidence that those
panels are inapplicable.

| Panel | Quantity and written specification | Data command | Plot command | Current status and comparison record |
| --- | --- | --- | --- | --- |
| Supplementary Fig. S1, each panel | Complete model-space; panel-level quantities and layout pending access to and extraction of the supplement text. | `TBD` | `TBD` | Not yet inventoried; no panel reproduced. |
| Supplementary Fig. S2, each panel | Brittle–ductile transition response; panel-level quantities and layout pending supplement extraction. | `TBD` | `TBD` | Not yet inventoried; no panel reproduced. |
| Other supplementary figures, each panel | Inventory pending extraction of all written supplementary captions. | `TBD` | `TBD` | Not yet inventoried; no panel reproduced. |

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
