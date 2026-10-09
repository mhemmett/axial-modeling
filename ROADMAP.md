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
June 2022, including several overlaps with OOI. Model-generated quantities
will never be inferred from digitized published plots.

## Phase 2 — Coupled solver design and numerical verification

Implement the written thermomechanical method with PyLith as the mechanics
engine. The specification solves steady heat conduction with `Q = 0`, then
assigns temperature-dependent Young's modulus and viscosity to the mechanical
model; the hydrothermal case changes conductivity in that heat solve. It states
no mechanics-to-heat return term. The target is therefore temperature-to-
mechanics property coupling, not an invented two-way feedback law. A verified
driver may coordinate the thermal solve, material database, and PyLith run; a
runtime property-update extension is needed only if an allowed written source
requires time-varying thermal properties.

The target physics include the four written rheology configurations,
hydrothermal heat-transport treatment, reservoir pressure loading, specified
boundary conditions, and postprocessed tensile and Mohr–Coulomb failure
criteria. A spatial-property handoff counts as coupling only when the written
steady heat solution and its temperature-based properties are used by the
matching mechanical case. Document unresolved constitutive laws and boundary
conditions as model limitations.

Document governing equations, units, parameters, initial and boundary
conditions, discretization, time integration, convergence settings, and every
assumption needed to close omissions in the written specification. Verify
components with analytical or manufactured limiting cases, conservation and
dimensional checks, and mesh and time-step refinement. Record expected,
alternative, and null outcomes. A model component or panel remains partial when
the available specification does not determine its inputs or physics.

The current OOI checkpoint applies a steady Eq. 14 temperature field,
Eq. 22 hydrothermal conductivity, Eq. 15 viscosity, and Eq. 16 as printed to
diagnostic pressure histories; the same cellwise modulus is used for static
calibration and Maxwell mechanics. A new common-load smoke matrix runs all four
written rheology configurations and independently reconstructs the three
Maxwell stress histories. This verifies the solver and property handoffs, but
does not complete the pressure-calibrated four-case comparison. Eq. 16 still
conflicts with the written brittle and ductile definitions, and the model
lacks the specified branch spectrum and a mesh-converged compliance field.
The generalized Maxwell implementation now also runs bounded 1998 and 2011
raw-BPR forward checks with synthetic branch parameters. Those comparisons
exercise historical loading and a held-out South station, but their pressure
inversion uses the same mesh-sensitive static compliance and does not resolve
the rheology. Ten additional paired deployments extend these checks across
1995–2022 while retaining gaps between instruments and deployment windows.
Three further raw channels add spatial checks at WC67 in 1995–96 and NeMO
South 1 in 2007–09 and 2013–15 without contributing to the corresponding
Center pressure fits.
All twelve historical stress windows also receive a provisional Mohr–Coulomb
connectivity check. With the current synthetic rheology and `1 MPa` cohesion,
`25°` friction angle, and zero pore pressure, a cavity-to-surface path appears
within 196 days in every window, including the ten inter-eruption intervals.
The 2013–15 and 2015–17 paths appear at about day 34.75 and by the first saved
day; the 2018–20 and 2020–22 paths first appear at days 21 and 35.
The path is present in the first 1998 output and first appears around day 17.61
in the 2011 run. This shows that the current threshold setup does not
distinguish eruption timing. The written joint tensile-plus-shear condition is
now evaluated without assigning tensile strength. Maximum cavity tension at a
saved connected-path record is 94.0 MPa in 1998, 71.1 MPa in 2011, and at most
58.3 MPa in any inter-eruption window. Using unrounded output values, the
interval (58.3221, 71.0951] MPa would separate these event and quiet windows
for these saved records only; it is not a calibrated strength range. Pore
pressure, tensile strength, the branch spectrum, and mesh-converged compliance
remain unresolved.

The 2011 raw-BPR check now carries one three-branch Maxwell stress history from
the September 2010 Center/South overlap through August 2013. It joins two
original MGDS Center deployments across their five-day nonoverlapping
transition by holding inferred pressure at its last measured value, then tests
the event and follow-up South records against their own deployment baselines.
Held-out South RMSE is 0.680 m during the event overlap and 1.246 m through
2013; the follow-up correlation of 0.991 coexists with a −1.217 m bias. These
raw series extend model checking after the eruption, but the result retains
synthetic branches, an assumed pressure transition, uncorrected channels, and
nonconverged compliance.

The 1998 raw NCEI check also carries the three-branch Maxwell state from the
October 1997 Center/South overlap through May 1999. It drives pressure with the
original WC81 Center channel through August 1998, then holds terminal inferred
pressure constant while the WC82 South record continues. The WC82 archive
segments align over eight shared days; the post-Center South comparison has
0.063 m RMSE but a negative 0.369 correlation because the modeled trend is
nearly flat while the raw follow-up retains short-period variability. This is
a constant-load continuation, not a post-eruption hindcast.

The raw-data checks now also sample ten original NCEI deployments from 1987–96
at embedded surface vertices. Three overlaps provide spatial holdouts: one
43-day WC51/WC61 comparison and two WC68-fit comparisons against WC69 and
WC67 through June 1996. Their RMSE values are 0.020, 0.183, and 0.038 m. The
standalone 1987–93 pressure fits reach +294 MPa, showing that drift-affected
single-station trends cannot calibrate physical pressure with this
nonconverged static mesh. These observations extend checks before the 1998
eruption but do not establish a continuous pre-eruption pressure history.

Original MGDS raw channels now add Center, South 1, and South 2 records from
2013–15, followed by Center/South 2 in 2015–17 and 2018–20, and a Center/South 1
miniBPR pair in 2020–22. The 709-day
2013–15 Center fit predicts South 2 with 0.358 m RMSE; its independent South 1
holdout has 1.096 m RMSE and −0.988 m bias. The 2015–17 South 2 holdout has
0.265 m RMSE and −0.245 m bias over 687 paired days. Both windows have high
correlation, but inferred pressure reaches −50.7 to +26.7 MPa in 2013–15 and
0 to +20.8 MPa in 2015–17. The 2018–20 and 2020–22 held-out South RMSE values
are 0.105 m and 0.043 m. These raw-channel checks extend the post-2011 record
and overlap the OOI era; separate sensor baselines, ocean variability, drift,
synthetic branches, and unconverged compliance keep them diagnostic.

A separate OOI-only diagnostic now infers pressure from a PyLith one-branch
Maxwell ramp-response kernel, fitting Central uplift and checking Eastern as
a holdout. The direct-history run agrees with kernel superposition to below
0.1% relative L2 error at both sites. Central RMSE is 0.00495 m and Eastern
RMSE is 0.225 m, with inferred pressure from −60.4 to +11.8 MPa. This closes
the mismatch between a static pressure fit and a viscoelastic forward response
for this assumed material, but it does not establish a physical pressure scale:
the one-branch rheology, GCV smoothness prior, monthly interpolation, and
nonconverged compliance remain provisional.

The same response-kernel method now checks original raw BPR pairs across the
1998 WC81/WC82A and 2011 NeMO Center/South eruption windows. Central RMSE is
0.093 m and 0.125 m; held-out South RMSE is 0.535 m and 0.713 m. The inferred
pressure minima are −107 MPa and −72 MPa, while kernel superposition errors
remain below 0.13%. This extends the temporal check with allowed raw channels,
but does not calibrate pressure or rheology: the raw records retain ocean and
instrument variability, the mesh is not converged, and the synthetic
one-branch properties remain assumptions.

An additional surface-localized mesh check refines Central and Eastern BPR
sampling neighborhoods while keeping each unit-pressure mesh below 2,700
tetrahedra. The final 50-to-25 m step changes compliance by less than 0.1% at
both sites, but earlier Eastern changes reach 19.8% and element counts are not
monotone. At the 25 m target, the nearest surface vertices remain 139 m from
Central and 102 m from Eastern. This bounded sequence does not establish mesh
convergence, so pressure scales and spatial errors remain provisional.

A bounded fixed-base depth check now compares 20, 30, and 40 km domains with
the Central and Eastern coordinates embedded as top-surface vertices. All
three meshes remain below 2,900 tetrahedra, but compliance varies
nonmonotonically across the independently generated meshes. The sequence does
not establish domain convergence or equivalence to the unspecified Winkler
foundation; both remain open model gaps.

## Phase 3 — Model implementation and saved numerical output

Implement the model incrementally, retaining small verification cases before
the full domain. Save versioned configuration and machine-readable numerical
outputs needed by plotting scripts. Record each run command, code revision,
configuration, runtime, and validation result in
[`docs/run_log.md`](docs/run_log.md). Keep mesh and run sizes within server
limits; never run a parameter sweep without a scoped plan.

The step00 pressurized elastic cavity now runs as a toolchain smoke test only.
It does not count as a reproduction of a manuscript panel or as a completed
project model. Later steps add the verified thermal-property handoff,
historical loading, four rheology configurations, and failure progression.

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
review series. A clean end-to-end run completed at revision `745022e` in 1,396
seconds, rebuilding verified components, OOI checks, raw historical BPR
diagnostics through 2022, the early NCEI spatial check, and the common-load
four-case solver matrix. The run confirms that this documented checkpoint
executes from a clean tree; it does not yet run the full pressure-calibrated
four-case failure comparison. Phase 5 remains open until that comparison and
the eligible panel record are complete; see
[`docs/reproduction.md`](docs/reproduction.md) for the current scope.

## Phase 6 — Public release

Publish the code, configurations, plotting scripts, permitted generated data,
LaTeX source, and compiled report to the `mhemmett/axial-modeling` GitHub
repository. The repository is public; this phase remains open until the final
versioned project release includes its environment report, validation outcome,
panel statuses, and known limitations. Do not publish restricted inputs,
credentials, or data prohibited by the provenance rules.
