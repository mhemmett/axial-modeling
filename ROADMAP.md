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

The no-source-data rule limits any panel requiring raw BPR, earthquake,
bathymetry, lava-flow, or other source records. Such a panel can be reproduced
only if its numerical inputs are provided in an allowed written source. The
project will not fetch those records to fill gaps. Model-generated quantities
will never be inferred from digitized published plots.

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

## Phase 6 — Public release

Publish the code, configurations, plotting scripts, permitted generated data,
LaTeX source, and compiled report to the `mhemmett/axial-modeling` GitHub
repository. The repository is public; this phase remains open until the final
versioned project release includes its environment report, validation outcome,
panel statuses, and known limitations. Do not publish restricted inputs,
credentials, or data prohibited by the provenance rules.
