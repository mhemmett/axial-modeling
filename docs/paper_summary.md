# Cabaniss et al. (2020): methods and results

## Study question

Cabaniss et al. test whether eruptions at Axial Seamount occur when increasing
reservoir pressure drives tensile failure at the magma reservoir and a
through-going Mohr–Coulomb failure path to the seafloor. Their three-dimensional
COMSOL Multiphysics 5.4 models use 22 years of bottom-pressure-recorder (BPR)
deformation to constrain pressure histories, then compare stress evolution
across four host-rock rheologies. This repository will independently recreate
the workflow with PyLith and any documented coupling component needed for the
full model. The observations are described here as part of the paper's method;
their source records are excluded from project inputs by the provenance rules.

## Model geometry and loading

The modeled magma reservoir is an ellipsoidal void measuring 6 km in length,
3 km in width, and 1 km in thickness. Its center is 1.6 km below the seafloor.
The geometry approximates a high-melt-fraction region in the main magma
reservoir identified by Arnulf et al. (2014, 2018). A pressure boundary on the
void interior is calibrated to reproduce the observed central-caldera surface
deformation.

The paper uses a Winkler elastic-foundation condition at the base and roller
conditions on the lateral faces. Additional experiments apply tectonic stress
associated with Juan de Fuca Ridge spreading. The complete domain dimensions,
material-property tables, and exact boundary/load values are cited in the
supplement; those values remain unverified because the supplement could not be
downloaded in this session. The model-domain size in the Phase 0 mesh is
therefore a documented project fallback, not a recovered paper parameter.

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

The temperature-dependent cases weaken the host rock around the hot reservoir
and delay widespread failure relative to the non-temperature-dependent models.
The hydrothermal case cools crust within 6 km of the surface, including the
shallow reservoir region, and shifts brittle behavior closer to the reservoir.

## Failure definitions

The study labels a model **eruptible** at the first tensile failure along the
reservoir boundary. It labels an **eruption** when tensile failure at that
boundary coincides with through-going Mohr–Coulomb failure from the reservoir
to the surface. Andersonian stress orientations are used to classify expected
faulting style where failure occurs. These are postprocessed criteria in the
paper, not a plastic constitutive law.

## Results to reproduce

The temperature-dependent models predict a reservoir overpressure threshold of
12–14 MPa. Their predicted 2011 eruption is 128 days early and their predicted
2015 eruption is 173 days early. In comparison, the non-temperature-dependent
elastic model predicts the 2011 event 4,240 days early and the 2015 event 1,464
days early. These timings show that rheology changes the forecast even when the
critical overpressure remains similar.

## Data and limitations

The paper cites Integrated Earth Data Applications records
[10.1594/IEDA/322282](https://doi.org/10.1594/IEDA/322282) and
[10.1594/IEDA/322344](https://doi.org/10.1594/IEDA/322344) for its BPR inputs.
These source datasets and the
COMSOL model files mentioned in the paper are not used by this project. The
published eruption sequence is January 1998, 6 April 2011, and 24 April 2015.
Use only numerical observations stated in allowed written sources; record a
missing series when those sources do not specify it.

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
