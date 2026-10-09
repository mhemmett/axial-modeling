# Cabaniss et al. (2020): written methods and parameters

## Study question

Cabaniss et al. test whether eruptions at Axial Seamount occur when increasing
reservoir pressure drives tensile failure at the magma reservoir and a
through-going Mohr–Coulomb failure path to the seafloor. Their three-dimensional
COMSOL Multiphysics 5.4 models use 22 years of bottom-pressure-recorder (BPR)
deformation to constrain pressure histories, then compare stress evolution
across four host-rock rheologies. This repository independently recreates the
workflow with PyLith and any documented coupling component needed for the full
model. Written rheology constraints and independently archived BPR tide/drift
correction channels are authorized inputs. Cabaniss model outputs, pressure or
stress histories, eruption predictions, and published figure values are
excluded. Independent OOI BPR records support checks from 2014 onward; their
provenance and limits are recorded in [`../data/README.md`](../data/README.md).

## Model geometry and loading

The primary modeled magma reservoir is an ellipsoidal void measuring 6 km in
length, 3 km in width, and 1 km in thickness, with its center 1.6 km below the
seafloor. It approximates a high-melt-fraction region in the main magma
reservoir identified by Arnulf et al. (2014, 2018). A pressure boundary on the
void interior is calibrated against central-caldera deformation. The supplement
also tests a 14 km × 3 km × 1 km full-reservoir geometry and a 6 km × 3 km ×
1 km partial reservoir at greater depth. Table S3 lists a 2.8 km depth for that
deep case, while nearby prose says 2.6 km; the reference point for the table's
depth values is not defined.

The paper uses a Winkler elastic-foundation condition at the base and roller
conditions on lateral faces. It applies a 60 mm/year full spreading rate
orthogonal to the Juan de Fuca Ridge in a separate tectonic-loading experiment.
The supplement's Table S1 instead lists prescribed velocities from -20 to
20 mm/year, and its model-setup caption does not give the numerical split
between opposite faces. The Phase 0 mesh retains its 40 km × 40 km × 20 km
fallback because the written source does not specify the model-box dimensions.
The supplement defines spring stiffness as `s = rho V g / Zdisp` and uses
`Zdisp = 1e-10 m` for its benchmark. Without the model-box volume and block
density, that expression does not determine an absolute stiffness value.

## Rheology configurations

1. **Non-temperature-dependent elastic:** linear elastic properties are uniform
   in space.
2. **Non-temperature-dependent viscoelastic:** viscoelastic properties are
   uniform and do not vary with temperature.
3. **Temperature-dependent viscoelastic:** Young's modulus and viscosity vary
   with the model temperature field.
4. **Temperature-dependent viscoelastic with hydrothermal circulation:** the
   fourth model adds greater thermal conductivity in the brittle crust to
   represent hydrothermal cooling.

The supplement specifies a steady-state conduction model,
`div(k grad(T)) = -Q`, with zero heat production, a 30 °C/km background
geotherm, a 0 °C surface, and a 1200 °C reservoir boundary. It gives the
temperature-dependent viscosity as `eta = AD exp(EA/(Rg T))` and Young's
modulus as Eq. 16, with `ED = 25 GPa` described as ductile and `EB = 50 GPa`
described as brittle. As printed, that equation makes modulus rise toward
75 GPa as temperature increases, which conflicts with those descriptions; do
not implement the law until a final-version source resolves the inconsistency.
The hydrothermal case raises conductivity with a Nusselt number
of 8 in crust shallower than 6 km and cooler than 600 °C. Those changes cool
the shallow reservoir region and shift brittle behavior closer to the reservoir.
Table S1 labels heat-production units as °C even though Eq. 14 requires a
volumetric heat-production quantity; the recorded zero is usable, but the unit
label is not.

## Failure definitions

The study labels a model **eruptible** at the first tensile failure along the
reservoir boundary. It labels an **eruption** when tensile failure at that
boundary coincides with through-going Mohr–Coulomb failure from the reservoir
to the surface. Supplementary Eq. 25 gives `tau = C + f sigma_n`, and Table S1
lists `C = 1 MPa` and `f = 25 degrees`. The table calls `f` an angle, but the
equation uses it as a coefficient; the supplement does not state the
conversion. It also gives no tensile-strength value. Andersonian stress
orientations classify faulting style where failure occurs. These are
postprocessed criteria, not a plastic constitutive law.

## Data and limitations

The main article cites Integrated Earth Data Applications records
[10.1594/IEDA/322282](https://doi.org/10.1594/IEDA/322282) and
[10.1594/IEDA/322344](https://doi.org/10.1594/IEDA/322344) for its BPR inputs.
This project uses original raw `Depth` and `RawDep` channels and documented
MGDS tide/drift-correction fields from selected archived deployments. These
are observation records, not Cabaniss model products. The project excludes
the paper's modeled pressure/stress histories, eruption predictions, plotted
model values, and COMSOL files. The independently sourced eruption dates are
January 1998, 6 April 2011, and 24 April 2015.
The publisher-served supplementary PDF provides Tables S1–S3, Eqs. 1–25, and
captions for Figs. S1–S6. Its pages carry a “Confidential manuscript
submitted” footer, so extracted supplement values are identified as coming
from that publisher-served copy and may reflect a pre-publication version.
Table S1 also leaves several implementation details unresolved, including
Poisson ratio, tensile strength, host-rock density, and the conversion from its
tabulated friction angle to the coefficient in Eq. 25. Record missing
observations when authorized archives do not supply them.

## Sources

- Cabaniss, H. E., Gregg, P. M., Nooner, S. L., and Chadwick, W. W. (2020),
  *Triggering of eruptions at Axial Seamount, Juan de Fuca Ridge*, Scientific
  Reports, 10, 10219. [Article](https://doi.org/10.1038/s41598-020-67043-0).
- [Supplementary information](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41598-020-67043-0/MediaObjects/41598_2020_67043_MOESM1_ESM.pdf).
- Arnulf, A. F. et al. (2014), *Anatomy of an active submarine volcano*,
  Geology, 42, 655–658. [doi:10.1130/G35629.1](https://doi.org/10.1130/G35629.1).
- Arnulf, A. F. et al. (2018), *Structure, seismicity, and accretionary
  processes at the hot spot-influenced Axial Seamount on the Juan de Fuca Ridge*,
  Journal of Geophysical Research: Solid Earth, 123, 4618–4646.
  [doi:10.1029/2017JB015131](https://doi.org/10.1029/2017JB015131).
