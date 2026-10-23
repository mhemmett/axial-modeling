# Figure reproduction record

This inventory tracks the paper's numerical and conceptual figures. Project
plots must be generated from the independent PyLith model and authorized BPR
observations. Published panels and reported values are comparison targets;
they are not inputs to the model calibration. The project uses the Center BPR
history and the reported eruption dates. The pressure history is calibrated
from Center BPR observations alone.

## Comparison rules

Use paper text, tables, captions, and plotted results to establish the target
quantity, range, timing, and presentation. Record whether each comparison uses
a textual value or a value estimated from a published plot. Do not use author
code, COMSOL files, or author-generated model fields. Recreate figure panels
from project outputs and identify any implementation difference from the
paper.

## Main figures

| Figure | Target | Current implementation and next work |
| --- | --- | --- |
| Fig. 1 | Axial map, reservoir setting, and Center BPR location. | The project map uses independent bathymetry, lava-flow, earthquake, and seismic-velocity records. Compare its extent, labels, reservoir location, and BPR position with the published figure. |
| Fig. 2 | Center BPR inflation and deflation history with earthquake counts and eruption markers. | Build the paper's historical Center series and add the corresponding earthquake record and event markers. |
| Fig. 3 | Spatial material properties for four rheologies. | A project property matrix exists. Reconcile the modulus law, Maxwell parameters, domain, and panel values before treating it as reproduced. |
| Fig. 4a | Reservoir overpressure required to reproduce the Center BPR deformation history. | Existing fits are retrospective diagnostics on separate event windows and use provisional compliance. Rebuild one pressure history over the paper's full interval and compare pressure magnitude and timing with the published curves. |
| Fig. 4b | Reservoir volume change required to reproduce the Center BPR history. | A cavity-volume integrator reads PyLith displacements on the Gmsh boundary. A geometry-only sweep reduces the nominal-volume deficit from 34.90% at 2,499 tetrahedra to 1.72% at 15,423 tetrahedra. Mechanical convergence and the four-case history remain open. |
| Fig. 5 | Tensile and Mohr–Coulomb failure fields at predicted and observed eruption times. | Current postprocessed paths use assumed properties and are time-step sensitive. Reproduce the reported failure fields and eruption timing after the threshold and stress solution converge. |
| Fig. 6 | Conceptual eruption mechanism. | Recreate only after the numerical panels are established; label the diagram as conceptual. |

## Supplementary figures

| Figure | Target | Current implementation and next work |
| --- | --- | --- |
| S1 | Temperature, Young's modulus, viscosity, and thermal conductivity for all four rheologies. | One hydrothermal property slice exists. Reproduce all fields with the resolved modulus law and reported thermal boundaries. |
| S2 | Hydrothermal effect on brittle–ductile transition location. | Not reproduced. Calculate transition location for the paper's baseline and hydrothermal cases. |
| S3 | Mogi, Del Negro, two-dimensional FEM, and three-dimensional FEM compatibility, including base conditions. | PyLith benchmarks remain incomplete. Rebuild the specified responses and compare against the reported curves and ranges. |
| S4 | Surface displacement across the Winkler spring-weakening sweep. | Not reproduced. Implement the spring sweep and compare the transition from equivalent to observably different response. |
| S5 | Model geometry, thermal and mechanical boundaries, and tectonic loading. | A project schematic exists. Update it to the model configuration used for the final reproduced runs. |
| S6 | Center BPR pressure for reservoir geometries and rheologies. | Not reproduced. Run the reported geometries and compare Center-fit pressures with the published panels. |

## Required comparison record

For every numerical panel, record the project command, output file, case
configuration, units, time or spatial domain, corresponding published target,
comparison method, validation checks, and remaining discrepancy. Keep
numerical reproduction results separate from parameter calibration so that a
reported value cannot be forced by tuning an undocumented input.
