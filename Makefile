SHELL := /bin/bash
ROOT := $(CURDIR)
override SHELL := $(ROOT)/scripts/bounded-shell
ENV_PREFIX := $(ROOT)/envs/axial-modeling
PYLITH_DIST := $(ROOT)/pylith/pylith-5.0.2-linux-x86_64
override export PYLITH_NODES := 8
override export OMP_NUM_THREADS := 1
override export OPENBLAS_NUM_THREADS := 1
override export MKL_NUM_THREADS := 1
override export NUMEXPR_NUM_THREADS := 1

.NOTPARALLEL:

.PHONY: env install-pylith build shell tmux pylith-version mesh smoke maxwell-restart thermal-material-smoke thermal-cross-mesh-smoke thermal-model thermal-property-slices figure3-rheology-properties model-setup-schematic figure1-sources figure1-map winkler-scale winkler-foundation-check tectonic-boundary-sensitivity thermal-maxwell-smoke maxwell-ellipsoid-smoke ellipsoid-failure-progression-smoke thermal-maxwell-ellipsoid-smoke hydrothermal-maxwell-ellipsoid-smoke eq16-maxwell-ellipsoid-smoke eq16-hydrothermal-maxwell-ellipsoid-smoke generalized-maxwell-check rheology-case-matrix historical-failure-time-refinement historical-four-case-bpr-calibration historical-four-case-corrected-bpr-calibration historical-bpr-corrected-daily mogi-benchmark mogi-domain-sensitivity failure-connectivity-smoke failure-progression-smoke historical-bpr-daily ellipsoid-unit-response ellipsoid-base-depth-sensitivity ellipsoid-mesh-sensitivity report progress-assessment report-clean reproduce test lint clean

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

figure3-rheology-properties: rheology-case-matrix
	PYTHONPATH="$(ROOT)/src" conda run --prefix "$(ENV_PREFIX)" python scripts/plot_rheology_property_matrix.py

historical-failure-time-refinement: ellipsoid-unit-response historical-bpr-daily
	conda run --prefix "$(ENV_PREFIX)" bash scripts/historical_failure_time_refinement.sh $(FAILURE_REFINEMENT_ARGS)

historical-four-case-bpr-calibration: ellipsoid-unit-response historical-bpr-daily
	conda run --prefix "$(ENV_PREFIX)" python scripts/historical_four_case_bpr_calibration.py --event 1998 --overwrite
	conda run --prefix "$(ENV_PREFIX)" python scripts/historical_four_case_bpr_calibration.py --event 2011 --overwrite

historical-bpr-corrected-daily: historical-bpr-daily
	conda run --prefix "$(ENV_PREFIX)" python data/process_corrected_historical_bpr.py

historical-four-case-corrected-bpr-calibration: ellipsoid-unit-response historical-bpr-corrected-daily
	conda run --prefix "$(ENV_PREFIX)" python scripts/historical_four_case_bpr_calibration.py --event 1998 --corrected-observations --overwrite
	conda run --prefix "$(ENV_PREFIX)" python scripts/historical_four_case_bpr_calibration.py --event 2011 --corrected-observations --overwrite

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

.PHONY: thermal-mesh-sensitivity
thermal-mesh-sensitivity:
	conda run --prefix "$(ENV_PREFIX)" python scripts/thermal_mesh_sensitivity.py

thermal-property-slices: thermal-model
	conda run --prefix "$(ENV_PREFIX)" python scripts/plot_thermal_property_slices.py

model-setup-schematic:
	conda run --prefix "$(ENV_PREFIX)" python scripts/plot_model_setup_schematic.py

figure1-sources:
	python data/fetch_figure1_sources.py

figure1-map:
	conda run --prefix "$(ENV_PREFIX)" python scripts/plot_figure1_map.py

winkler-scale:
	PYTHONPATH="$(ROOT)/src" conda run --prefix "$(ENV_PREFIX)" python scripts/winkler_foundation_scale.py

WINKLER_STIFFNESS_PA_PER_M ?= 3.2373e4
winkler-foundation-check: ellipsoid-unit-response
	PYTHONPATH="$(ROOT)/src" conda run --prefix "$(ENV_PREFIX)" python scripts/winkler_foundation_check.py --stiffness-pa-per-m "$(WINKLER_STIFFNESS_PA_PER_M)"

tectonic-boundary-sensitivity:
	PYTHONPATH="$(ROOT)/src:$(ROOT)/scripts" conda run --prefix "$(ENV_PREFIX)" python scripts/tectonic_boundary_sensitivity.py

thermal-maxwell-smoke: thermal-model
	conda run --prefix "$(ENV_PREFIX)" bash scripts/thermal_maxwell_smoke.sh

mogi-benchmark:
	conda run --prefix "$(ENV_PREFIX)" bash scripts/mogi_benchmark_smoke.sh

mogi-domain-sensitivity:
	conda run --prefix "$(ENV_PREFIX)" bash scripts/mogi_domain_sensitivity.sh

historical-bpr-daily:
	@if [[ ! -f data/processed/axial_historical_bpr/summary.json || data/process_historical_bpr.py -nt data/processed/axial_historical_bpr/summary.json || src/axialstress/historical_bpr.py -nt data/processed/axial_historical_bpr/summary.json || ( -f data/raw/axial_bpr/manifest.json && data/raw/axial_bpr/manifest.json -nt data/processed/axial_historical_bpr/summary.json ) ]]; then \
		conda run --prefix "$(ENV_PREFIX)" python data/process_historical_bpr.py; \
	else \
		echo "Raw historical BPR daily means are up to date."; \
	fi

ellipsoid-unit-response:
	conda run --prefix "$(ENV_PREFIX)" bash scripts/ellipsoid_unit_response.sh

report: progress-assessment
	latexmk -cd -pdf -interaction=nonstopmode -halt-on-error report/axial_model_report.tex

progress-assessment:
	latexmk -pdf -interaction=nonstopmode -halt-on-error progress_assessment.tex

report-clean:
	latexmk -cd -C report/axial_model_report.tex

reproduce:
	bash scripts/reproduce.sh

.PHONY: reproduction-status paper-bpr paper-bpr-fetch method-reconstruction method-failure-screen method-150m-reconstruction
.PHONY: method-source-maxwell method-source-bpr-failure method-source-threshold method-source-time-steps method-source-volume method-source-figure4 method-source-figure3 report-figure1b report-figure2 report-figure5 report-paper-figures

METHOD_SOURCE_MAXWELL_ARGS ?=
method-source-maxwell:
	PYTHONPATH="$(ROOT)/src:$(ROOT)/scripts" conda run --prefix "$(ENV_PREFIX)" python scripts/source_value_maxwell_cases.py --overwrite $(METHOD_SOURCE_MAXWELL_ARGS)

method-source-bpr-failure: paper-bpr
	PYTHONPATH="$(ROOT)/src:$(ROOT)/scripts" conda run --prefix "$(ENV_PREFIX)" python scripts/source_value_bpr_failure.py --overwrite

method-source-threshold:
	PYTHONPATH="$(ROOT)/src:$(ROOT)/scripts" conda run --prefix "$(ENV_PREFIX)" python scripts/source_value_final_threshold.py

method-source-time-steps:
	PYTHONPATH="$(ROOT)/src:$(ROOT)/scripts" conda run --prefix "$(ENV_PREFIX)" python scripts/source_value_time_step_sweep.py --overwrite

method-source-volume:
	PYTHONPATH="$(ROOT)/src:$(ROOT)/scripts" conda run --prefix "$(ENV_PREFIX)" python scripts/source_value_volume_history.py

method-source-figure4: method-source-volume
	PYTHONPATH="$(ROOT)/src:$(ROOT)/scripts" conda run --prefix "$(ENV_PREFIX)" python scripts/plot_source_value_figure4.py

method-source-figure3:
	PYTHONPATH="$(ROOT)/src:$(ROOT)/scripts" conda run --prefix "$(ENV_PREFIX)" python scripts/plot_source_value_figure3.py

report-figure1b:
	PYTHONPATH="$(ROOT)/src:$(ROOT)/scripts" conda run --prefix "$(ENV_PREFIX)" python scripts/plot_report_figure1b_pylith_context.py

report-figure2: paper-bpr
	PYTHONPATH="$(ROOT)/src:$(ROOT)/scripts" conda run --prefix "$(ENV_PREFIX)" python scripts/plot_report_figure2_bpr_history.py

report-figure5:
	PYTHONPATH="$(ROOT)/src:$(ROOT)/scripts" conda run --prefix "$(ENV_PREFIX)" python scripts/plot_report_figure5_cycles.py

report-figure5-150m:
	PYTHONPATH="$(ROOT)/src:$(ROOT)/scripts" conda run --prefix "$(ENV_PREFIX)" python scripts/plot_report_figure5_cycles.py --mesh-m 150 --fine-root "$(FIVE_CASE_SCRATCH_DIR)"

report-figure3-150m:
	PYTHONPATH="$(ROOT)/src:$(ROOT)/scripts" conda run --prefix "$(ENV_PREFIX)" python scripts/plot_source_value_figure3.py --mesh-m 150 --input-dir "$(FIVE_CASE_SCRATCH_DIR)/source_value_bpr_failure_2011_2015_150m"

method-source-volume-150m:
	PYTHONPATH="$(ROOT)/src:$(ROOT)/scripts" conda run --prefix "$(ENV_PREFIX)" python scripts/source_value_volume_history.py --input-dir "$(FIVE_CASE_SCRATCH_DIR)/source_value_bpr_failure_2011_2015_150m" --mesh data/processed/refined_elastic_basis_150m/axial_ellipsoid.msh

report-figure4-150m: method-source-volume-150m
	PYTHONPATH="$(ROOT)/src:$(ROOT)/scripts" conda run --prefix "$(ENV_PREFIX)" python scripts/plot_source_value_figure4.py --input-dir "$(FIVE_CASE_SCRATCH_DIR)/source_value_bpr_failure_2011_2015_150m"

.PHONY: ooi-center-fetch ooi-center-process method-historical-cycle-failure method-post2015-failure method-source-event-states method-source-tectonic-failure report-post2015
ooi-center-fetch:
	conda run --prefix "$(ENV_PREFIX)" python data/fetch_ooi_center_daily.py $(OOI_FETCH_ARGS)

ooi-center-process:
	conda run --prefix "$(ENV_PREFIX)" python data/process_ooi_center_daily.py

method-historical-cycle-failure: report-figure2
	PYTHONPATH="$(ROOT)/src:$(ROOT)/scripts" conda run --prefix "$(ENV_PREFIX)" python scripts/elastic_historical_cycle_failure.py
	PYTHONPATH="$(ROOT)/src:$(ROOT)/scripts" conda run --prefix "$(ENV_PREFIX)" python scripts/source_value_historical_cycle_failure.py

method-post2015-failure:
	PYTHONPATH="$(ROOT)/src:$(ROOT)/scripts" conda run --prefix "$(ENV_PREFIX)" python scripts/source_value_ooi_failure.py

method-source-event-states:
	@for cycle in 1998-2011 2011-2015; do \
		for case in constant_maxwell thermal_maxwell hydrothermal_maxwell; do \
			PYTHONPATH="$(ROOT)/src:$(ROOT)/scripts" conda run --prefix "$(ENV_PREFIX)" python scripts/source_value_event_states.py --cycle "$$cycle" --case "$$case" || exit; \
		done; \
	done

method-source-tectonic-failure:
	@for cycle in 1998-2011 2011-2015 post-2015; do \
		PYTHONPATH="$(ROOT)/src:$(ROOT)/scripts" conda run --prefix "$(ENV_PREFIX)" python scripts/source_value_tectonic_failure.py --cycle "$$cycle" || exit; \
	done

report-post2015:
	PYTHONPATH="$(ROOT)/src:$(ROOT)/scripts" conda run --prefix "$(ENV_PREFIX)" python scripts/plot_report_post2015_failure.py

report-post2015-150m:
	PYTHONPATH="$(ROOT)/src:$(ROOT)/scripts" conda run --prefix "$(ENV_PREFIX)" python scripts/plot_report_post2015_failure.py --mesh-m 150 --fine-root "$(FIVE_CASE_SCRATCH_DIR)"

report-paper-figures: figure1-map report-figure1b report-figure2 report-figure3-150m report-figure4-150m report-figure5-150m report-post2015-150m

reproduction-status:
	conda run --prefix "$(ENV_PREFIX)" python scripts/reproduction_status.py

paper-bpr-fetch:
	conda run --prefix "$(ENV_PREFIX)" python data/fetch_paper_bpr.py $(PAPER_BPR_FETCH_ARGS)

paper-bpr:
	PYTHONPATH="$(ROOT)/src" conda run --prefix "$(ENV_PREFIX)" python data/process_paper_bpr.py

method-reconstruction:
	PYTHONPATH="$(ROOT)/src" conda run --prefix "$(ENV_PREFIX)" python scripts/reconstruct_center_pressure.py

method-failure-screen: paper-bpr winkler-foundation-check
	PYTHONPATH="$(ROOT)/src" conda run --prefix "$(ENV_PREFIX)" python scripts/reconstruct_center_pressure.py --surface pylith/step16_winkler_foundation/output/fixed-base-surface.h5 --output-dir data/processed/method_reconstruction_2011_2015_gravity_fixed --overwrite
	PYTHONPATH="$(ROOT)/src" conda run --prefix "$(ENV_PREFIX)" python scripts/screen_bpr_failure.py --overwrite

method-mesh-refinement: paper-bpr
	bash scripts/method_mesh_refinement.sh

.PHONY: method-five-case-150m-reconstruction report-figure5-150m report-figure3-150m method-source-volume-150m report-figure4-150m report-post2015-150m
FIVE_CASE_SCRATCH_DIR ?= /tmp/axial-150m-runs
method-five-case-150m-reconstruction: report-figure2
	env -u PYTHONHOME bash scripts/bounded-shell scripts/run_five_case_mesh_refinement.sh "$(FIVE_CASE_SCRATCH_DIR)"

ellipsoid-mesh-sensitivity:
	conda run --prefix "$(ENV_PREFIX)" python scripts/ellipsoid_mesh_sensitivity.py

ellipsoid-base-depth-sensitivity:
	conda run --prefix "$(ENV_PREFIX)" python scripts/ellipsoid_base_depth_sensitivity.py

failure-connectivity-smoke: mogi-benchmark
	conda run --prefix "$(ENV_PREFIX)" bash scripts/failure_connectivity_smoke.sh

failure-progression-smoke: failure-connectivity-smoke
	conda run --prefix "$(ENV_PREFIX)" bash scripts/failure_progression_smoke.sh

test:
	PYTHONPATH="$(ROOT)/src:$(ROOT)/scripts" conda run --prefix "$(ENV_PREFIX)" python -m pytest tests/

lint:
	conda run --prefix "$(ENV_PREFIX)" ruff check src tests meshing data scripts

clean:
	find pylith/step00_elastic_cavity -type f \( -name '*.msh' -o -name '*.h5' -o -name '*.xmf' -o -name '*.log' \) -delete
