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
        rtcase rtcase-test todo ledger check-ledger shellcheck ci clean-work qemu-env qemu-test probe-test \
        loader-test loader-report doctor check-runsheet runsheet-test \
        dump-test flash-tools-test photo-test write-test failopen-test alignfix-test check-benchlog benchlog-test config-diff-test count-checks liveness liveness-test dhcp-test mipsref-reports

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

runsheet-test: ## Prove the runsheet checker can fail (29 cases)
	bash tools/test-check-runsheet.sh

# The record-card template lived only in plan/, which is gitignored and which
# committed files may not quote - so the format BENCH-LOG.md must follow lived
# where BENCH-LOG.md could not cite it, and drifted out within a week.
#
# It checks a second thing since 2026-08-18, and that one is about the file
# existing rather than its cards being well formed: **every session PROGRESS.md
# records must have an entry here on the same date.** A desk-only day feels
# exempt - nothing was typed at the device - and it is precisely the day the
# next visit's plan changes, which is the half of this file that gets forgotten.
# W07 Day 3 forgot it; the author noticed, no tool could have.
check-benchlog: ## Every bench record card carries a refutation condition, and every session has an entry
	python3 tools/check-benchlog.py

benchlog-test: ## Prove the bench-log checker can fail (17 cases)
	bash tools/test-check-benchlog.sh

rtcase: ## G3.75: the test register is frozen and every result carries evidence
	python3 tools/rtcase.py check

todo: ## What this week still owes: `make todo WEEK=W05`
	python3 tools/rtcase.py todo $(if $(WEEK),--week $(WEEK),)

rtcase-test: ## Prove the register gate can actually fail (34 cases)
	bash tools/test-rtcase.sh

ledger: ## Regenerate test-ledger.md from the register + results
	python3 tools/rtcase.py render
	python3 tools/rtcase.py check

# The same check .github/workflows/ci.yml runs, and it was the ONE step `make ci`
# did not have. test-ledger.md is generated from the register; a session that
# records a result and does not re-render leaves the two disagreeing, and the
# only thing that noticed was GitHub. That is the failure mode this target
# exists to remove: `make ci` said "everything CI checks" while being a strict
# subset of it, so local green and remote red were possible and nothing local
# could tell you which. Found 2026-08-18, on a staleness the previous session
# had already committed.
check-ledger: ## The generated ledger matches the register it comes from
	@python3 tools/rtcase.py render
	@git diff --exit-code -- test-ledger.md \
	  || { echo "test-ledger.md was out of date and has just been regenerated."; \
	       echo "Commit it in the same commit as the result that changed it."; \
	       exit 1; }

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

# The three suites below were written before `ci` existed as a single list and
# were never added to it -- 35 cases, none needing hardware, recorded as
# PROGRESS open #33 when the totals were recounted on 2026-08-17. The largest of
# them guards the flash parser, which is the code path every byte of this unit's
# dump came through. Found by counting, not by anything checking.
dump-test: ## Prove the flash reader's refusals fire (needs no device)
	bash tools/test-console-dump.sh

flash-tools-test: ## Prove the CH341A path's refusals fire (needs no programmer)
	bash tools/test-flash-tools.sh

photo-test: ## Prove the redaction and annotation guards fire (needs no photograph)
	bash tools/test-photo-tools.sh

# The write path is the only tool here that can destroy the unit, so its guard
# suite is the one that most needs to be in CI rather than in a habit.
write-test: ## Prove the flash writer refuses every range it must not touch
	bash tools/test-console-write.sh

# The probe damages a flash image and asks the vendor's boot script what it does
# about it, so every reading it produces is a difference from a control. Its
# first working run reported seven states in which nothing happened, because the
# boot script was being handed to qemu-user as if it were an ELF -- a complete,
# plausible table of nothing. This suite covers the refusals that need no
# emulation environment; the three in-run controls need root and a built profile
# and are enforced a second time by check-reports.py on the committed artefact.
failopen-test: ## Prove the fail-open probe's refusals fire (needs no device)
	bash tools/test-failopen-probe.sh

# The shim that removes qemu-user's one divergence from the device's kernel.
# It has more leverage than anything else in tools/: with it on, code paths that
# could not run at all do run, so a result taken with it and a result taken
# without it are answers to different questions. Its suite therefore checks two
# things a normal test would not -- that the build's architecture checks reject
# a wrong architecture, and that the flag is still off by default.
alignfix-test: ## Prove the alignment shim and its build checks can fail (needs no device)
	bash tools/test-alignfix.sh

config-diff-test: ## Drive config-diff's comparison and its refusals (needs no root)
	bash tools/test-config-diff.sh

# Open item 73: every check `make doctor` ran asked whether the HOST was ready.
# The device had a persistent, self-inflicted WAN outage for two days and four
# bench sessions did not notice, because nothing asked the device anything. This
# does, in one unauthenticated GET.
liveness: ## Can the router still route? `make liveness` or `make liveness HOST=10.1.1.1`
	python3 tools/device-liveness.py $(if $(HOST),--host $(HOST),) 	  --mib "$(EX)/unit-2018/squashfs-root/lib/libapmib.so"

liveness-test: ## Prove the liveness check can say no (19 cases, needs no device)
	bash tools/test-device-liveness.sh

# The tool hands out addresses to anything that asks, so its first refusal --
# one named interface, and not the one carrying the default route -- is the
# load-bearing part, and it has to be provable without a wire.
dhcp-test: ## Prove the rogue DHCP server's encoders and refusals (needs no device)
	bash tools/test-rogue-dhcp.sh

# `P5-2` asks for an address a ret2libc chain would jump to, and the only inputs
# are two console lines that name no library. Everything the answer rests on is a
# filter that looks like it worked when it did not, so the refusals are the tool:
# a base with low bits set, and a symbol long enough that more than one base fits.
libbase-test: ## Prove the library-base solver can refuse (27 cases, needs no device)
	bash tools/test-libbase.sh

# Five times a suite has been added to one of `make ci` / the CI workflow and
# not the other, and every one of them was found by diffing the files rather
# than by noticing. RUNBOOK 10.21 made it a rule; a rule broken five times is a
# reminder, so this is the reminder replaced by a checker.
check-ci-parity: ## `make ci` and the GitHub workflow run the same tools/ scripts
	python3 tools/check-ci-parity.py

ci-parity-test: ## Prove the parity checker can fail (needs no device)
	bash tools/test-check-ci-parity.sh

libbase-report: ## Solve uClibc's load base from the two recorded faults (needs the rootfs)
	@test -f "$(EX)/unit-2018/squashfs-root/lib/libuClibc-0.9.30.3.so" || \
	  { echo "no extracted rootfs - run tools/unpack-firmware.sh"; exit 2; }
	python3 tools/libbase.py \
	  --in "$(EX)/unit-2018/squashfs-root/lib/libuClibc-0.9.30.3.so" \
	  --report --differing-object "$(EX)/unit-2018/squashfs-root/lib/libapmib.so" \
	  --json $(REPORTS)/libbase-unit-2018.json

# Regenerating these by hand is how the first one came to name a GOT slot as
# though it were the variable. The command is the evidence for what the report
# measured, so it lives where it can be re-run rather than in a shell history.
mipsref-reports: ## Re-scan the auth-session globals (needs the extracted rootfs)
	@test -f "$(EX)/unit-2018/squashfs-root/bin/boa" || 	  { echo "no $(EX)/unit-2018/squashfs-root/bin/boa - run tools/unpack-firmware.sh"; exit 2; }
	python3 tools/mipsref.py "$(EX)/unit-2018/squashfs-root/bin/boa" 	  --sym beforeuptime --sym authipaddr --sym nowuptime --addr 004899e8 	  --control 004899e0 --control-indirect 004899e0 	  --json $(REPORTS)/mipsref-unit-2018-authsession.json
	python3 tools/mipsref.py "$(EX)/unit-2018/squashfs-root/bin/boa" 	  --addr 004899d8 --control 004899e0 --control-indirect 004899e0 	  --json $(REPORTS)/mipsref-unit-2018-checkauthflag.json

count-checks: ## How many guard checks make ci runs, per suite (REPRODUCE.md quotes the total)
	bash tools/count-checks.sh

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
ci: lint test shellcheck check-reports check-runsheet check-benchlog benchlog-test rtcase rtcase-test check-ledger check-ci-parity ci-parity-test qemu-test probe-test loader-test runsheet-test dump-test flash-tools-test photo-test write-test failopen-test alignfix-test config-diff-test liveness-test dhcp-test libbase-test ## Everything CI checks, except the container build
	@echo "  ok   local CI equivalents passed (container build not included)"

diff: venv ## Diff the two builds
	$(PY) -m fwrecon diff $(REPORTS)/n150rt-2.1.2.json $(REPORTS)/n150rt-3.4.0.json \
		-f md -o $(REPORTS)/diff-2.1.2-to-3.4.0.md

clean-work: ## Delete unpacked filesystems (images and reports are kept)
	rm -rf $(EX)
