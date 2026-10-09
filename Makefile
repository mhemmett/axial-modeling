SHELL := /bin/bash
ROOT := $(CURDIR)
ENV_PREFIX := $(ROOT)/envs/axial-modeling
PYLITH_DIST := $(ROOT)/pylith/pylith-5.0.2-linux-x86_64
OOI_START_DATE ?= 2014-01-01
OOI_END_DATE ?= $(shell date -u +%F)

.PHONY: env install-pylith build shell tmux pylith-version mesh smoke maxwell-restart thermal-material-smoke thermal-model thermal-maxwell-smoke maxwell-ellipsoid-smoke ellipsoid-failure-progression-smoke thermal-maxwell-ellipsoid-smoke hydrothermal-maxwell-ellipsoid-smoke eq16-maxwell-ellipsoid-smoke eq16-hydrothermal-maxwell-ellipsoid-smoke mogi-benchmark failure-connectivity-smoke failure-progression-smoke bpr-observation-plot bpr-mogi-check bpr-historical-check ellipsoid-unit-response ellipsoid-bpr-check ooi-maxwell-ellipsoid-check ooi-eq16-hydrothermal-maxwell-check ooi-maxwell-history-plot ellipsoid-mesh-sensitivity report report-clean reproduce test lint clean

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

maxwell-ellipsoid-smoke:
	conda run --prefix "$(ENV_PREFIX)" bash scripts/maxwell_ellipsoid_smoke.sh

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

thermal-maxwell-smoke: thermal-model
	conda run --prefix "$(ENV_PREFIX)" bash scripts/thermal_maxwell_smoke.sh

mogi-benchmark:
	conda run --prefix "$(ENV_PREFIX)" bash scripts/mogi_benchmark_smoke.sh

bpr-observation-plot:
	conda run --prefix "$(ENV_PREFIX)" python scripts/plot_ooi_bpr.py

bpr-mogi-check:
	conda run --prefix "$(ENV_PREFIX)" python scripts/bpr_mogi_check.py

bpr-historical-check: ellipsoid-unit-response
	conda run --prefix "$(ENV_PREFIX)" python data/process_historical_bpr.py
	conda run --prefix "$(ENV_PREFIX)" python scripts/historical_bpr_ellipsoid_check.py
	conda run --prefix "$(ENV_PREFIX)" python scripts/historical_bpr_mogi_check.py
	conda run --prefix "$(ENV_PREFIX)" python scripts/historical_bpr_mogi_timeseries.py
	conda run --prefix "$(ENV_PREFIX)" python scripts/historical_bpr_mogi_deployments.py
	conda run --prefix "$(ENV_PREFIX)" python scripts/plot_historical_bpr.py

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

report:
	latexmk -cd -pdf -interaction=nonstopmode -halt-on-error report/axial_model_report.tex

report-clean:
	latexmk -cd -C report/axial_model_report.tex

reproduce:
	OOI_START_DATE="$(OOI_START_DATE)" OOI_END_DATE="$(OOI_END_DATE)" bash scripts/reproduce.sh

ellipsoid-mesh-sensitivity:
	conda run --prefix "$(ENV_PREFIX)" python scripts/ellipsoid_mesh_sensitivity.py

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
