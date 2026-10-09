# Roadmap

The project will independently recreate the results of Cabaniss et al. (2020),
“Triggering of eruptions at Axial Seamount, Juan de Fuca Ridge,” using PyLith in
place of COMSOL. The deliverable is an auditable model, numerical outputs and
plots generated from those outputs, and a compiled report with its LaTeX source.
The workflow will use the paper, its supplement, and other written model
descriptions as scientific specifications. It will not use the authors’ source
code, simulation outputs, plotting scripts, source datasets, or figure files,
and it will not digitize plotted curves. Published figures may be viewed only
for visual comparison after independent results exist.

## Phase 0 — Project initiation and provenance

Scaffold the repository, record known model parameters and unresolved values,
document the COMSOL-to-PyLith translation, and establish a panel inventory. The
repository-local `axial-modeling` Conda environment and native PyLith 5.0.2
binary are installed. The generated Gmsh 4.1 mesh and one-step elastic-cavity
solve pass the bounded smoke check. The repository is published, with follow-on
work delivered through reviewable pull requests. This phase is complete; see
[`docs/KNOWN_ISSUES.md`](docs/KNOWN_ISSUES.md) for remaining scientific and
implementation gaps.

## Phase 1 — Written specification and figure inventory

Extract equations, parameter values, initial conditions, boundary conditions,
time histories, and numerical methods from the article, supplementary text,
and other written descriptions. Record each value with a source location and
confidence. Mark unavailable values as unresolved instead of inferring them
silently. Inventory main and supplementary figures from captions and text. The
article and publisher-served supplement are transcribed in
[`docs/paper_summary.md`](docs/paper_summary.md),
[`docs/model_specification.md`](docs/model_specification.md),
[`docs/parameters.yaml`](docs/parameters.yaml), and
[`docs/figure_reproduction.md`](docs/figure_reproduction.md). The supplement
PDF carries a “Confidential manuscript submitted” footer; its extracted values
may reflect a pre-publication version. Captions identify Supplementary Figs.
S1–S6 but do not state subpanel letters. The written-specification phase is
complete for the equations and parameter values stated in the written sources.
The lettered-panel inventory remains open where captions omit subpanel IDs;
those layouts stay unviewed until project results exist for a valid comparison.

The user has authorized independent OOI records and original raw BPR channels
from earlier Axial deployments for model checking. This permission excludes
pressure histories, corrections, values, figures, or other data products
produced for the paper, even when an archive also cites it. Earthquake,
bathymetry, lava-flow, and other source records remain outside the authorized
inputs. OOI coverage begins in 2014, so raw historical BPR channels supply
checks for the 1998 and 2011 events and inter-eruption deployment checks through
2013. Model-generated quantities will never be inferred from digitized
published plots.

## Phase 2 — Coupled solver design and numerical verification

Specify and implement the coupled thermomechanical workflow with PyLith as the
mechanics engine and a Julia or C++ coupling core that advances thermal state,
updates temperature-dependent properties, and coordinates mechanics steps. If
PyLith cannot exchange temperature-dependent properties and thermal state at
the required time steps through a verified interface, implement and validate a
PyLith extension for that exchange.
The target physics include the four published rheology configurations,
hydrothermal heat-transport treatment, reservoir pressure loading, the
published boundary conditions, and the postprocessed tensile and Mohr–Coulomb
failure criteria. Do not describe a one-way spatial-property preprocessing
approximation as a complete coupled model.

Document governing equations, units, parameters, initial and boundary
conditions, discretization, time integration, convergence settings, and every
assumption needed to close omissions in the written specification. Verify
components with analytical or manufactured limiting cases, conservation and
dimensional checks, and mesh and time-step refinement. Record expected,
alternative, and null outcomes. A model component or panel remains partial when
the available specification does not determine its inputs or physics.

The current OOI checkpoint remains a one-way diagnostic rather than the
coupled solver required here. It applies the steady Eq. 14 temperature field,
Eq. 22 hydrothermal conductivity, Eq. 15 viscosity, and Eq. 16 as printed to
the OOI pressure history; the same cellwise modulus is used for static
calibration and Maxwell mechanics. Eq. 16 still conflicts with the written
brittle and ductile definitions, and the model still lacks thermal feedback,
the generalized branch spectrum, and a mesh-converged compliance field.
The generalized Maxwell implementation now also runs bounded 1998 and 2011
raw-BPR forward checks with synthetic branch parameters. Those comparisons
exercise historical loading and a held-out South station, but their pressure
inversion uses the same mesh-sensitive static compliance and does not resolve
the rheology. Four additional paired deployments extend these checks across
1995–2013 while retaining gaps between instruments and deployment windows.
Two further raw channels add spatial checks at WC67 in 1995–96 and NeMO South
1 in 2007–09 without contributing to the corresponding Center pressure fits.
All six historical stress windows also receive a provisional Mohr–Coulomb
connectivity check. With the current synthetic rheology and `1 MPa` cohesion,
`25°` friction angle, and zero pore pressure, a cavity-to-surface path appears
within 68 days in every window, including the four inter-eruption intervals.
The path is present in the first 1998 output and first appears around day 17.61
in the 2011 run. This shows that the current threshold setup does not
distinguish eruption timing; tensile strength, pore pressure, and the branch
spectrum remain unresolved.

## Phase 3 — Model implementation and saved numerical output

Implement the model incrementally, retaining small verification cases before
the full domain. Save versioned configuration and machine-readable numerical
outputs needed by plotting scripts. Record each run command, code revision,
configuration, runtime, and validation result in
[`docs/run_log.md`](docs/run_log.md). Keep mesh and run sizes within server
limits; never run a parameter sweep without a scoped plan.

The step00 pressurized elastic cavity now runs as a toolchain smoke test only.
It does not count as a reproduction of a manuscript panel or as a completed
coupled model. Later steps will advance from this baseline to coupled thermal
and mechanical behavior, historical loading, and failure progression.

## Phase 4 — Figure generation and comparison

Attempt each numerical panel in the main article and supplementary materials
where the written specification permits. Generate each panel from saved output
of this implementation using tracked plotting scripts. Keep conceptual diagrams
separate and label any redraw as a schematic. A panel is “independently
reproduced” only when plotted data came from this implementation and the
comparison record supports that status. Use “partially reproduced” when only
some quantities, intervals, or conditions are recovered, and “not reproduced”
when required inputs or methods are unavailable or an attempt fails.

For each eligible panel, compare numerical ranges, timing, spatial patterns, and
available scales with the published description or, after generating results,
the published figure viewed solely as a reference. Explain discrepancies and
failed attempts. Update the panel record with exact data-generation and plotting
commands, source parameters, comparison measures, status, and provenance.

## Phase 5 — Report and clean rebuild

Write a LaTeX report that includes the implementation and validation, generated
figures, the panel-by-panel record, and a candid account of reproduced,
partially reproduced, and unreproduced results. Label any manuscript image used
for visual comparison as a published reference and distinguish it visually
from model output. Commit the `.tex` source and compiled PDF. Provide one clean
documented `make reproduce` procedure that builds the model, regenerates
numerical data and figures, and compiles the report; run that procedure and
record its outcome.

The first report and `make reproduce` checkpoint are available in the current
review series. The checkpoint rebuilds the verified components, OOI checks,
and raw historical BPR diagnostics, but it does not build the complete coupled
model. Phase 5 remains open until the full model, its supported panels, and a
clean end-to-end run are available; see [`docs/reproduction.md`](docs/reproduction.md)
for the current scope.

## Phase 6 — Public release

Publish the code, configurations, plotting scripts, permitted generated data,
LaTeX source, and compiled report to the `mhemmett/axial-modeling` GitHub
repository. The repository is public; this phase remains open until the final
versioned project release includes its environment report, validation outcome,
panel statuses, and known limitations. Do not publish restricted inputs,
credentials, or data prohibited by the provenance rules.
