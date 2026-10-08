SHELL := /bin/bash
ROOT := $(CURDIR)
ENV_PREFIX := $(ROOT)/envs/axial-modeling
PYLITH_DIST := $(ROOT)/pylith/pylith-5.0.2-linux-x86_64

.PHONY: env install-pylith build shell tmux pylith-version mesh smoke maxwell-restart thermal-material-smoke mogi-benchmark failure-connectivity-smoke failure-progression-smoke test lint clean

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

mogi-benchmark:
	conda run --prefix "$(ENV_PREFIX)" bash scripts/mogi_benchmark_smoke.sh

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
