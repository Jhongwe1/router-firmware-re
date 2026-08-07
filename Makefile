# TOTOLINK N150RT firmware reverse-engineering — task runner.
#
# Artefact policy: the repository holds text (notes, tooling, generated reports).
# Firmware images and unpacked filesystems live under $(FWRE_WORK), which must be
# a real Linux filesystem — see docs/workspace-layout.md for why /mnt/c is not one.

FWRE_WORK ?= $(HOME)/fwre-work
FW        := $(FWRE_WORK)/firmware
EX        := $(FWRE_WORK)/extracted
VENV      := $(FWRE_WORK)/venv
PY        := $(VENV)/bin/python
REPORTS   := reports

V1_LABEL  := N150RT V2.1.2-B20150825
V2_LABEL  := N150RT V3.4.0-B20201030
V1_IMG    := $(FW)/TOTOLINK-N150RT-V2.1.2-B20150825.1601.web
V2_IMG    := $(FW)/TOTOLINK-N150RT-V3.4.0-B20201030.1142.web

.DEFAULT_GOAL := help
.PHONY: help setup verify fetch unpack venv test lint recon diff check-reports clean-work

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
	 | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup: ## Install the Linux-side toolchain (G0)
	bash tools/setup/setup-wsl.sh all

verify: ## Re-check that every tool answers when called (G0 gate)
	bash tools/setup/setup-wsl.sh verify

fetch: ## Download + hash-verify the firmware declared in firmware/SOURCES.json
	FWRE_WORK=$(FWRE_WORK) bash tools/fetch-firmware.sh

unpack: ## Carve and extract the SquashFS root filesystems
	FWRE_WORK=$(FWRE_WORK) bash tools/unpack-firmware.sh

venv: $(PY) ## Create the analysis virtualenv
$(PY):
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -q --upgrade pip
	$(VENV)/bin/pip install -q -e 'tools/fwrecon[dev]'

test: venv ## Run the fwrecon test suite
	cd tools/fwrecon && $(PY) -m pytest

lint: venv ## Lint the tooling
	$(VENV)/bin/ruff check tools/fwrecon/src tools/fwrecon/tests

recon: venv ## Regenerate every report under reports/
	@mkdir -p $(REPORTS)
	$(PY) -m fwrecon report --image "$(V1_IMG)" --rootfs "$(EX)/v2.1.2/squashfs-root" \
		--label "$(V1_LABEL)" -f json -o $(REPORTS)/n150rt-2.1.2.json
	$(PY) -m fwrecon report --image "$(V1_IMG)" --rootfs "$(EX)/v2.1.2/squashfs-root" \
		--label "$(V1_LABEL)" -f md   -o $(REPORTS)/n150rt-2.1.2.md
	$(PY) -m fwrecon report --image "$(V2_IMG)" --rootfs "$(EX)/v3.4.0/squashfs-root" \
		--label "$(V2_LABEL)" -f json -o $(REPORTS)/n150rt-3.4.0.json
	$(PY) -m fwrecon report --image "$(V2_IMG)" --rootfs "$(EX)/v3.4.0/squashfs-root" \
		--label "$(V2_LABEL)" -f md   -o $(REPORTS)/n150rt-3.4.0.md
	$(MAKE) diff

check-reports: ## Verify the committed reports still match the tooling (what CI runs)
	python3 tools/check-reports.py

diff: venv ## Diff the two builds
	$(PY) -m fwrecon diff $(REPORTS)/n150rt-2.1.2.json $(REPORTS)/n150rt-3.4.0.json \
		-f md -o $(REPORTS)/diff-2.1.2-to-3.4.0.md

clean-work: ## Delete unpacked filesystems (images and reports are kept)
	rm -rf $(EX)
