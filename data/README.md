# Data provenance

The model specification comes from the article, its supplementary materials,
and other written descriptions. This project does not use the authors'
original source datasets, code, simulation outputs, plotting scripts, or figure
files. It does not digitize published plots.

The paper cites processed bottom-pressure-recorder (BPR) records hosted by the
Integrated Earth Data Applications (IEDA):

- [Chadwick and Nooner, DOI 10.1594/IEDA/322282](https://doi.org/10.1594/IEDA/322282)
- [Fox, DOI 10.1594/IEDA/322344](https://doi.org/10.1594/IEDA/322344)

These citations document the publication's observational context only. Do not
download or use those records in this project. `python data/fetch_bpr.py`
prints the references and confirms that retrieval is disabled. A data-dependent
panel may be reproduced only when its numerical input is specified in an
allowed written source. Otherwise, record the missing input and classify the
panel as partial or not reproduced.

The eruption dates reported in the paper are January 1998, 6 April 2011, and
24 April 2015. They may be used as written event markers, but not to infer or
reconstruct unreported observational time series.
