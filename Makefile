SHELL := /bin/bash
ROOT := $(CURDIR)
ENV_PREFIX := $(ROOT)/envs/axial-modeling
PYLITH_DIST := $(ROOT)/pylith/pylith-5.0.2-linux-x86_64
OOI_START_DATE ?= 2014-01-01
OOI_END_DATE ?= $(shell date -u +%F)

.PHONY: env install-pylith build shell tmux pylith-version mesh smoke maxwell-restart thermal-material-smoke thermal-cross-mesh-smoke thermal-model thermal-property-slices model-setup-schematic thermal-maxwell-smoke maxwell-ellipsoid-smoke ellipsoid-failure-progression-smoke thermal-maxwell-ellipsoid-smoke hydrothermal-maxwell-ellipsoid-smoke eq16-maxwell-ellipsoid-smoke eq16-hydrothermal-maxwell-ellipsoid-smoke generalized-maxwell-check rheology-case-matrix historical-generalized-maxwell-check historical-generalized-maxwell-1998-continuous-check historical-generalized-maxwell-2011-continuous-check historical-post-2011-bpr-check historical-post-2017-bpr-check historical-early-bpr-spatial-check mogi-benchmark mogi-domain-sensitivity failure-connectivity-smoke failure-progression-smoke bpr-observation-plot bpr-mogi-check bpr-historical-check historical-bpr-daily historical-bpr-maxwell-pressure-inversion bpr-archive-crosscheck ellipsoid-unit-response ellipsoid-base-depth-sensitivity ellipsoid-bpr-check ooi-maxwell-ellipsoid-check ooi-eq16-hydrothermal-maxwell-check ooi-maxwell-history-plot ooi-maxwell-pressure-inversion ellipsoid-mesh-sensitivity report report-clean reproduce test lint clean

env:
	mkdir -p "$(ROOT)/.conda/pkgs"
	CONDA_PKGS_DIRS="$(ROOT)/.conda/pkgs" conda env create --prefix "$(ENV_PREFIX)" --file environment.yml

install-pylith:
	@test -f pylith/pylith-5.0.2-linux-x86_64.tar.gz || { echo "Missing PyLith 5.0.2 tarball under pylith/"; exit 1; }
	cd pylith && sha256sum -c SHA256SUMS
	@if [ ! -f "$(PYLITH_DIST)/setup.sh" ]; then tar -xzf pylith/pylith-5.0.2-linux-x86_64.tar.gz -C pylith; fi

build: install-pylith

shell:
	bash -lc 'source "$$(conda info --base)/etc/profile.d/conda.sh" && conda activate "$(ENV_PREFIX)" && source scripts/activate.sh && exec bash -i'

tmux:
	conda run --name tmux tmux new-session -A -s axial-modeling "bash --rcfile $(ROOT)/scripts/activate.sh -i"

pylith-version: install-pylith
	bash -lc 'source "$$(conda info --base)/etc/profile.d/conda.sh" && conda activate "$(ENV_PREFIX)" && source scripts/activate.sh && pylith --version'

mesh:
	conda run --prefix "$(ENV_PREFIX)" python meshing/axial_box_ellipsoid.py --output pylith/step00_elastic_cavity/mesh/axial_box.msh

smoke:
	conda run --prefix "$(ENV_PREFIX)" bash scripts/smoke_test.sh

maxwell-restart:
	conda run --prefix "$(ENV_PREFIX)" bash scripts/maxwell_restart_smoke.sh

thermal-material-smoke:
	conda run --prefix "$(ENV_PREFIX)" bash scripts/thermal_material_smoke.sh

thermal-cross-mesh-smoke:
	conda run --prefix "$(ENV_PREFIX)" bash scripts/thermal_cross_mesh_smoke.sh

maxwell-ellipsoid-smoke:
	conda run --prefix "$(ENV_PREFIX)" bash scripts/maxwell_ellipsoid_smoke.sh

generalized-maxwell-check:
	conda run --prefix "$(ENV_PREFIX)" bash scripts/generalized_maxwell_ellipsoid_smoke.sh

rheology-case-matrix:
	PYTHONPATH="$(ROOT)/src" conda run --prefix "$(ENV_PREFIX)" python scripts/rheology_case_matrix.py

historical-generalized-maxwell-check: ellipsoid-unit-response
	conda run --prefix "$(ENV_PREFIX)" bash scripts/historical_generalized_maxwell_bpr_check.sh

historical-generalized-maxwell-1998-continuous-check: ellipsoid-unit-response
	conda run --prefix "$(ENV_PREFIX)" bash scripts/historical_generalized_maxwell_bpr_check.sh --only-1998-continuous-followup

historical-generalized-maxwell-2011-continuous-check: ellipsoid-unit-response
	conda run --prefix "$(ENV_PREFIX)" bash scripts/historical_generalized_maxwell_bpr_check.sh --only-2011-continuous-followup

historical-post-2011-bpr-check: ellipsoid-unit-response
	conda run --prefix "$(ENV_PREFIX)" bash scripts/historical_generalized_maxwell_bpr_check.sh --only-post-2011-deployment-checks

historical-post-2017-bpr-check: ellipsoid-unit-response historical-bpr-daily
	conda run --prefix "$(ENV_PREFIX)" bash scripts/historical_generalized_maxwell_bpr_check.sh --only-post-2017-deployment-checks

historical-early-bpr-spatial-check:
	conda run --prefix "$(ENV_PREFIX)" python scripts/historical_early_bpr_spatial_check.py

ellipsoid-failure-progression-smoke: maxwell-ellipsoid-smoke
	conda run --prefix "$(ENV_PREFIX)" bash scripts/ellipsoid_failure_progression_smoke.sh

thermal-maxwell-ellipsoid-smoke:
	conda run --prefix "$(ENV_PREFIX)" python scripts/thermal_maxwell_ellipsoid.py

hydrothermal-maxwell-ellipsoid-smoke:
	conda run --prefix "$(ENV_PREFIX)" python scripts/thermal_maxwell_ellipsoid.py --hydrothermal

eq16-maxwell-ellipsoid-smoke:
	conda run --prefix "$(ENV_PREFIX)" python scripts/thermal_maxwell_ellipsoid.py --eq16-modulus

eq16-hydrothermal-maxwell-ellipsoid-smoke:
	conda run --prefix "$(ENV_PREFIX)" python scripts/thermal_maxwell_ellipsoid.py --hydrothermal --eq16-modulus

thermal-model:
	conda run --prefix "$(ENV_PREFIX)" bash scripts/steady_thermal_model.sh

thermal-property-slices: thermal-model
	conda run --prefix "$(ENV_PREFIX)" python scripts/plot_thermal_property_slices.py

model-setup-schematic:
	conda run --prefix "$(ENV_PREFIX)" python scripts/plot_model_setup_schematic.py

thermal-maxwell-smoke: thermal-model
	conda run --prefix "$(ENV_PREFIX)" bash scripts/thermal_maxwell_smoke.sh

mogi-benchmark:
	conda run --prefix "$(ENV_PREFIX)" bash scripts/mogi_benchmark_smoke.sh

mogi-domain-sensitivity:
	conda run --prefix "$(ENV_PREFIX)" bash scripts/mogi_domain_sensitivity.sh

bpr-observation-plot:
	conda run --prefix "$(ENV_PREFIX)" python scripts/plot_ooi_bpr.py

bpr-mogi-check:
	conda run --prefix "$(ENV_PREFIX)" python scripts/bpr_mogi_check.py

bpr-historical-check: ellipsoid-unit-response historical-bpr-daily
	conda run --prefix "$(ENV_PREFIX)" python scripts/historical_bpr_ellipsoid_check.py
	conda run --prefix "$(ENV_PREFIX)" python scripts/historical_bpr_mogi_check.py
	conda run --prefix "$(ENV_PREFIX)" python scripts/historical_bpr_mogi_timeseries.py
	conda run --prefix "$(ENV_PREFIX)" python scripts/historical_bpr_mogi_deployments.py
	conda run --prefix "$(ENV_PREFIX)" python scripts/historical_bpr_ellipsoid_deployments.py
	conda run --prefix "$(ENV_PREFIX)" python scripts/plot_historical_bpr.py

historical-bpr-daily:
	@if [[ ! -f data/processed/axial_historical_bpr/summary.json || data/process_historical_bpr.py -nt data/processed/axial_historical_bpr/summary.json || src/axialstress/historical_bpr.py -nt data/processed/axial_historical_bpr/summary.json || ( -f data/raw/axial_bpr/manifest.json && data/raw/axial_bpr/manifest.json -nt data/processed/axial_historical_bpr/summary.json ) ]]; then \
		conda run --prefix "$(ENV_PREFIX)" python data/process_historical_bpr.py; \
	else \
		echo "Raw historical BPR daily means are up to date."; \
	fi

historical-bpr-maxwell-pressure-inversion: historical-bpr-daily
	conda run --prefix "$(ENV_PREFIX)" python scripts/ooi_maxwell_ellipsoid_check.py --historical-viscoelastic-pressure-inversion
	conda run --prefix "$(ENV_PREFIX)" python scripts/plot_historical_maxwell_pressure_inversion.py

bpr-archive-crosscheck:
	conda run --prefix "$(ENV_PREFIX)" python scripts/historical_bpr_archive_crosscheck.py

ellipsoid-unit-response:
	conda run --prefix "$(ENV_PREFIX)" bash scripts/ellipsoid_unit_response.sh

ellipsoid-bpr-check: ellipsoid-unit-response
	conda run --prefix "$(ENV_PREFIX)" python scripts/ellipsoid_bpr_check.py

ooi-maxwell-ellipsoid-check:
	conda run --prefix "$(ENV_PREFIX)" python scripts/ooi_maxwell_ellipsoid_check.py

ooi-eq16-hydrothermal-maxwell-check:
	conda run --prefix "$(ENV_PREFIX)" python scripts/ooi_maxwell_ellipsoid_check.py --eq16-hydrothermal

ooi-maxwell-history-plot:
	conda run --prefix "$(ENV_PREFIX)" python scripts/plot_ooi_maxwell_history.py

ooi-maxwell-pressure-inversion: ellipsoid-bpr-check
	conda run --prefix "$(ENV_PREFIX)" python scripts/ooi_maxwell_ellipsoid_check.py --viscoelastic-pressure-inversion
	conda run --prefix "$(ENV_PREFIX)" python scripts/plot_ooi_maxwell_history.py \
		--summary data/processed/ooi_maxwell_viscoelastic_inversion_summary.json \
		--timeseries data/processed/ooi_maxwell_viscoelastic_inversion_timeseries.csv \
		--output-stem figures/ooi_maxwell_viscoelastic_inversion

report:
	latexmk -cd -pdf -interaction=nonstopmode -halt-on-error report/axial_model_report.tex

report-clean:
	latexmk -cd -C report/axial_model_report.tex

reproduce:
	OOI_START_DATE="$(OOI_START_DATE)" OOI_END_DATE="$(OOI_END_DATE)" bash scripts/reproduce.sh

ellipsoid-mesh-sensitivity:
	conda run --prefix "$(ENV_PREFIX)" python scripts/ellipsoid_mesh_sensitivity.py

ellipsoid-base-depth-sensitivity:
	conda run --prefix "$(ENV_PREFIX)" python scripts/ellipsoid_base_depth_sensitivity.py

failure-connectivity-smoke: mogi-benchmark
	conda run --prefix "$(ENV_PREFIX)" bash scripts/failure_connectivity_smoke.sh

failure-progression-smoke: failure-connectivity-smoke
	conda run --prefix "$(ENV_PREFIX)" bash scripts/failure_progression_smoke.sh

test:
	conda run --prefix "$(ENV_PREFIX)" python -m pytest tests/

lint:
	conda run --prefix "$(ENV_PREFIX)" ruff check src tests meshing data scripts

clean:
	find pylith/step00_elastic_cavity -type f \( -name '*.msh' -o -name '*.h5' -o -name '*.xmf' -o -name '*.log' \) -delete
