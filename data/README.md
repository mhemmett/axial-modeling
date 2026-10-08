# Data provenance

The article and supplement provide the model specification. This project does
not use datasets, numerical series, model output, code, plotting scripts, or
figure files supplied with the publication. It does not digitize published
plots. The user authorized independent BPR observations from the Ocean
Observatories Initiative (OOI) for model checking.

## OOI bottom-pressure records

The fetcher requests OOI's `BOTSFLU-DAYDEPTH` product for two Bottom Pressure
and Tilt instruments: Central Caldera (`RS03CCAL-MJ03F-05-BOTPTA301`) and
Eastern Caldera (`RS03ECAL-MJ03E-06-BOTPTA302`). OOI describes this daily series
as a 24-hour mean depth derived from detided 15-second pressure averages and
corrected for pressure-sensor drift using remotely operated vehicle (ROV)
measurements. The product is delivered as signed depth in meters, with uplift
positive. See the [OOI product description](https://oceanobservatories.org/data-product/botsflu/)
and [instrument locations](https://oceanobservatories.org/instrument-series/botpta/).

Run `python data/fetch_bpr.py` to print the public OOI ERDDAP requests. Add
`--download` to retrieve daily records and a manifest containing query URLs,
row counts, retrieval time, and checksums. The default date range begins in
2014 and ends today; actual deployment coverage starts in August 2014 at
Central Caldera and September 2014 at Eastern Caldera. The compressed
responses remain under ignored `data/raw/ooi_bpr/` and must not be committed.

Run `python data/process_bpr.py PATH_TO_FILE.csv.gz` to convert signed depth to
relative uplift from the first available daily sample while preserving the
OOI aggregate quality flag. OOI reports this flag as `NOT_EVALUATED` for the
downloaded daily series; the workflow retains that status and does not treat
it as a pass. Processed observations remain under ignored `data/processed/`.

After processing both sites, run `make bpr-observation-plot` to write
`figures/ooi_bpr_relative_uplift.png` and `.pdf`. The two records use separate
first-sample baselines; the plot retains and labels their OOI aggregate quality
codes. This observation-only plot covers available data from 2014 onward and
does not include eruption markers or earthquake counts.

OOI coverage does not extend to the 1998 and 2011 eruptions. It can check the
2014–present part of the modeled surface-deformation history, subject to the
unresolved validation of the underlying model physics. Earthquake catalogs,
bathymetry, and lava-flow source records remain outside the authorized inputs.
