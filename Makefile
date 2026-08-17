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
.PHONY: help setup verify fetch unpack venv test lint recon recon-unit diff check-reports \
        rtcase rtcase-test todo ledger shellcheck ci clean-work qemu-env qemu-test probe-test \
        loader-test loader-report doctor check-runsheet runsheet-test

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
	# The standalone scripts are not inside the fwrecon package, so ruff's
	# upward config search never reaches tools/fwrecon/pyproject.toml and they
	# were silently linted under default rules until 2026-08-16. Point them at
	# the same config rather than adding a second one that can drift.
	$(VENV)/bin/ruff check --config tools/fwrecon/pyproject.toml tools/*.py

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
	# Only 2015-family images carry a w6cg bundle; V3.4.0 has none, which is
	# why there is no 3.4.0 line here rather than a failing one.
	$(PY) -m fwrecon web "$(V1_IMG)" --json -o $(REPORTS)/webbundle-2.1.2.json
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
	$(PY) -m fwrecon web "$(UNIT_DUMP)" --at 0x010000 --json \
		-o $(REPORTS)/webbundle-unit-2018.json

# Also deliberately NOT part of `recon`, for the mirror-image reason to
# recon-unit: this one needs an image `make fetch` cannot download. Softpedia
# serves V2.1.6 to a browser and 403s every script, and the copy obtained that
# way is 40% complete. Its w6cg section is nonetheless byte-complete, which is
# the only reason a report is possible at all - see RUNBOOK 8.8.4. Errors
# rather than skipping, because a silently absent report reads as "not
# interesting" instead of "not obtainable".
recon-partial: venv ## Report for the partially-downloaded published V2.1.6 (see PROGRESS open #0)
	@test -f "$(FW)/v2.1.6-partial.web" || \
	  { echo "no $(FW)/v2.1.6-partial.web - recover it with tools/zipprefix.py --allow-partial"; exit 2; }
	$(PY) -m fwrecon web "$(FW)/v2.1.6-partial.web" --json \
		-o $(REPORTS)/webbundle-2.1.6-b20160516.json

check-reports: ## Verify the committed reports still match the tooling
	python3 tools/check-reports.py

# The first command of any session, and the only one that is allowed to be run
# without having read anything. Every failure names the command that fixes it.
# TIER=1 clone only · TIER=2 adds a flash dump · TIER=3 adds the device.
doctor: ## Is this machine ready? `make doctor` or `make doctor TIER=1`
	@bash tools/bench-doctor.sh $(if $(TIER),$(TIER),all)

# runsheet.md is hand-written on purpose - it is the one document a stranger
# follows front to back, and generating it from RUNBOOK.md would make it exactly
# as terse as a reference. The cost of hand-writing is drift, and this narrows
# that cost to the part that matters: a command that no longer resolves.
check-runsheet: ## Verify every command in runsheet.md still resolves
	python3 tools/check-runsheet.py

runsheet-test: ## Prove the runsheet checker can fail (18 cases)
	bash tools/test-check-runsheet.sh

rtcase: ## G3.75: the test register is frozen and every result carries evidence
	python3 tools/rtcase.py check

todo: ## What this week still owes: `make todo WEEK=W05`
	python3 tools/rtcase.py todo $(if $(WEEK),--week $(WEEK),)

rtcase-test: ## Prove the register gate can actually fail (22 cases)
	bash tools/test-rtcase.sh

ledger: ## Regenerate test-ledger.md from the register + results
	python3 tools/rtcase.py render
	python3 tools/rtcase.py check

shellcheck: ## Lint the shell scripts, exactly as CI does
	shellcheck --severity=warning tools/*.sh tools/setup/*.sh

# Like recon-unit, this needs the flash dump read off my own unit, so it is not
# something a reader can reproduce. It is here because the alternative is a
# sequence of chroot invocations typed from memory, and one of them - `reset` -
# has to do two things that look like one.
qemu-env: ## Build the qemu-user environment for the build this unit runs (needs the flash dump + root)
	sudo bash tools/qemu-env.sh build

qemu-test: ## Prove the emulation environment's positive control can fail
	bash tools/test-qemu-env.sh

probe-test: ## Prove the bench prober's refusals fire (needs no device)
	bash tools/test-bench-probe.sh

loader-test: ## Prove the boot-loader unpacker's refusals fire (needs no dump)
	bash tools/test-loader-unpack.sh

# Like recon-unit and qemu-env: needs the flash dump read off my own unit, so it
# is not in `recon`. The report it writes is mostly a claim about what the boot
# loader does *not* contain, which is why its committed form carries a positive
# control and `check-reports.py` fails without one.
loader-report: ## Unpack the boot loader's LZMA stage 2 (needs the flash dump)
	python3 tools/loader-unpack.py "$(UNIT_DUMP)" -o $(REPORTS)/bootloader-unit-2018.json

# Exists because on 2026-08-15 a push went out green on `make lint test
# check-reports` and CI failed anyway: there are four jobs and that covers two of
# them. Knowing which subset to run by heart is not a check, it is a habit that
# eventually forgets. `make ci` is the whole set minus the container build, which
# is left out only because it costs minutes rather than seconds - run
# `docker build -f docker/Dockerfile .` before touching anything under docker/.
# `rtcase-test` is in here and not optional. It is the only thing proving the
# register gate can fail; without it `make rtcase` going green means nothing,
# which is the exact shape of instrument bug 12.
ci: lint test shellcheck check-reports check-runsheet rtcase rtcase-test qemu-test probe-test loader-test runsheet-test ## Everything CI checks, except the container build
	@echo "  ok   local CI equivalents passed (container build not included)"

diff: venv ## Diff the two builds
	$(PY) -m fwrecon diff $(REPORTS)/n150rt-2.1.2.json $(REPORTS)/n150rt-3.4.0.json \
		-f md -o $(REPORTS)/diff-2.1.2-to-3.4.0.md

clean-work: ## Delete unpacked filesystems (images and reports are kept)
	rm -rf $(EX)
