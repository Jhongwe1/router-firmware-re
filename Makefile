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

# The build that is actually on my unit, read out of its flash on 2026-08-16.
# It is on no vendor download page, so unlike the two above it cannot be fetched.
UNIT_LABEL := N150RT unit, 2018-01-10 build (read from flash)
UNIT_DUMP  := $(FWRE_WORK)/dumps/flash-n150rt-console-1.bin

.DEFAULT_GOAL := help
.PHONY: help setup verify fetch unpack venv test lint recon recon-unit diff check-reports shellcheck ci clean-work

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

# Deliberately NOT part of `recon`. Every other report regenerates from an image
# `make fetch` can download; this one needs a flash dump read off my own unit,
# which nobody else can obtain. Committing it is still right - it is the
# evidence - but a reader has to know that "re-run make recon" does not
# reproduce it. Provenance is in dumps/MANIFEST.json.
recon-unit: venv ## Reports for the build read off my own unit (needs the flash dump)
	@test -d "$(EX)/unit-2018/squashfs-root" || \
	  { echo "no $(EX)/unit-2018/squashfs-root - run tools/unpack-firmware.sh --flash <dump>"; exit 2; }
	$(PY) -m fwrecon report --rootfs "$(EX)/unit-2018/squashfs-root" \
		--label "$(UNIT_LABEL)" -f json -o $(REPORTS)/n150rt-unit-2018.json
	$(PY) -m fwrecon report --rootfs "$(EX)/unit-2018/squashfs-root" \
		--label "$(UNIT_LABEL)" -f md   -o $(REPORTS)/n150rt-unit-2018.md
	$(PY) -m fwrecon flashdump "$(UNIT_DUMP)" -f json -o $(REPORTS)/flashdump-unit-2018.json

check-reports: ## Verify the committed reports still match the tooling
	python3 tools/check-reports.py

shellcheck: ## Lint the shell scripts, exactly as CI does
	shellcheck --severity=warning tools/*.sh tools/setup/*.sh

# Exists because on 2026-08-15 a push went out green on `make lint test
# check-reports` and CI failed anyway: there are four jobs and that covers two of
# them. Knowing which subset to run by heart is not a check, it is a habit that
# eventually forgets. `make ci` is the whole set minus the container build, which
# is left out only because it costs minutes rather than seconds - run
# `docker build -f docker/Dockerfile .` before touching anything under docker/.
ci: lint test shellcheck check-reports ## Everything CI checks, except the container build
	@echo "  ok   local CI equivalents passed (container build not included)"

diff: venv ## Diff the two builds
	$(PY) -m fwrecon diff $(REPORTS)/n150rt-2.1.2.json $(REPORTS)/n150rt-3.4.0.json \
		-f md -o $(REPORTS)/diff-2.1.2-to-3.4.0.md

clean-work: ## Delete unpacked filesystems (images and reports are kept)
	rm -rf $(EX)
