# Router Firmware Reverse Engineering — TOTOLINK N150RT

[![CI](https://github.com/Jhongwe1/router-firmware-re/actions/workflows/ci.yml/badge.svg)](https://github.com/Jhongwe1/router-firmware-re/actions/workflows/ci.yml)

A firmware reverse-engineering study of a consumer router I own, done for
learning and as a portfolio piece. The goal is to take a real, end-of-life
embedded device, rebuild an understanding of its firmware from nothing, and
trace **already-publicly-disclosed** vulnerabilities down to the responsible
function in the binary.

> 🚧 **In progress since 2026-07-30. G0 ✅ · G1 ✅ · G2 ⏸ blocked on hardware
> delivery · G3 ▶ next.**
> Two firmware images are unpacked and measured — **V2.1.2 (2015-08-25)** and
> **V3.4.0 (2020-10-30)** — and they bracket both public disclosure events
> affecting this device, which turns a teardown into a before/after comparison.
> Board below; the evidence behind every ticked box is in
> [`PROGRESS.md`](PROGRESS.md).

The point is not the device. It is being able to take an undocumented binary
system on an unfamiliar architecture, build understanding from zero, and reason
about its security — with results another person can reproduce.

## Target

- **Device:** TOTOLINK N150RT, hardware V2.0 — a 2018-era 150 Mbps consumer router
- **Support status:** end-of-life, no longer vendor-supported
- **Ownership:** personally owned; all work is on my own hardware
- **Platform (measured, not assumed):** big-endian MIPS-I / o32 · Realtek SDK ·
  Boa 0.94.14rc21 running as root · SquashFS 4.0 root filesystem ·
  handlers dispatched under `/boafrm/form*`

## Status

The gates below are the acceptance criteria from the week plans in
[`plan/`](plan/) — copied, not invented after the fact. Nothing is ticked here
that is not backed by a command someone else can re-run.

- [x] **G0 — toolchain green** (W01) ← [PROGRESS.md](PROGRESS.md#g0--toolchain-green)
  - [x] binwalk + sasquatch produce a SquashFS from the vendor image
  - [x] `qemu-mips-static`, `flashrom`, `picocom` all answer when run
  - [x] Ghidra 12.1.2 on pinned Temurin JDK 21 — SHA-256 verified, no admin rights needed
  - [x] every tool checked by **running** it, not by testing for a file — `make verify`

  > 📌 The plan's G0 listed PuTTY. Dropped rather than forgotten: `picocom` does
  > the same job from inside WSL, where the rest of the toolchain already lives.
  > `usbipd-win` and FirmAE were **deferred with a written reason each**, so a
  > later session finds a decision instead of an oversight —
  > [Deliberately not done in W01](PROGRESS.md#deliberately-not-done-in-w01).

- [x] **G1 — firmware anatomy, seven elements answered from measurement** (W01) ← [PROGRESS.md](PROGRESS.md#g1--seven-elements-answered-from-measurement)
  - [x] firmware unpacked — SquashFS 4.0, LZMA (2015) and XZ (2020)
  - [x] all seven elements answered from the images, not from a datasheet:
        SoC · architecture · endianness · load base · filesystem · web binary · config storage
  - [x] [`notes/anatomy-n150rt.md`](notes/anatomy-n150rt.md) — how the firmware is built
  - [x] [`notes/prior-art.md`](notes/prior-art.md) — planned as `pierre-kim-map.md`,
        renamed once the attribution turned out to be wrong
  - [x] [`notes/attack-surface.md`](notes/attack-surface.md) v1 — where to look, ranked
  - [x] **beyond the plan:** two firmware versions instead of one ·
        [`fwrecon`](tools/fwrecon/), a zero-runtime-dependency analysis tool with 58 tests ·
        headless Ghidra triage emitting diffable JSON instead of a one-machine GUI session ·
        pinned [`docker/Dockerfile`](docker/Dockerfile) + CI

  > ⚠️ **Four things the plan asserted that the images contradict** — full table in
  > [Corrections to the original plan](PROGRESS.md#corrections-to-the-original-plan):
  > CVE-2019-1982x are **Błażej Adamczyk's**, not Pierre Kim's ·
  > there is **no `/etc/passwd`** in either image, so the credential check lives inside a binary ·
  > `formSysCmd` **is not a string in either `boa`** ·
  > the flash map needs **≥ 3.57 MiB**, not the 2 MB the published specs claim.

### ★ What G1 actually turned up

- **The 2015 build is the vendor's response to Pierre Kim's July 2015
  disclosure — and the response was to comment out one line.** `/etc/init.d/rcS`
  contains `#skt&`; `/bin/skt`, a socket-driven `system()` wrapper, is still
  shipped and still executable. Not starting a backdoor and not having one are
  different properties.
- **In the 2020 build — nine months after the Realtek SDK full disclosure —
  `/web/config.dat` is a symlink to `/var/config.dat`,** and `rcS` copies `/web/*`
  into the live document root. The exposure path behind CVE-2019-19822 is
  structurally intact.
- **`formSysCmd` does not appear in either binary** — but `sysCmdselect`,
  `sysCmdLog` and `/tmp/syscmd.log` do. The CVE-2019-19824 feature is compiled
  in; only its dispatch name is missing from the string table.
- **No exploit mitigations anywhere:** no canary, RELRO, PIE or FORTIFY, and no
  `PT_GNU_STACK` on most binaries — an executable stack. Boa runs as root.

> ⚠️ **Scope of these claims.** All four are **static** results, read out of
> firmware images — no running device has been touched yet. In particular,
> whether `/config.dat` is reachable *unauthenticated* depends on Boa's
> request-authorisation code, which is G3's job; the symlink proves the file is
> in the docroot and nothing more. Which build is actually on my unit is decided
> by a flash dump, which is G2's job.

- [ ] **G2 — hardware access: UART + SPI dump** (W02) ⏸ **blocked on hardware delivery**
  - [ ] a live bootlog, **or** a recorded fallback
  - [ ] SPI dump + hash verification, **or** the vendor-firmware main path
  - [ ] dump vs vendor image compared, **or** the reason recorded
  - [ ] annotated PCB photograph
  - [ ] settles two open questions: the real flash part and size, and which build my unit runs

  > 📌 **Blocked on delivery, not on knowledge** — so G3 is being worked first.
  > The plan's own gate text allows "vendor-firmware main path + honest record"
  > as a pass, which means G2 cannot become an indefinite blocker. First action
  > when the USB-TTL adapter arrives: install `usbipd-win` (needs elevation, so
  > it belongs in the same sitting as the rest of the hardware setup).

- [ ] **G3 — point at the line in the binary** (W03–W04) ▶ **next**
  - [ ] the `/boafrm/` dispatch table found, with ≥ 10 handlers listed
  - [ ] ≥ 1 authentication candidate function identified
  - [ ] **where `formSysCmd` is really registered** — read `handleForm`
  - [ ] **whether Boa authenticates `.dat` requests** — read `translate_uri`
  - [ ] `FUN_00440eec` in the 2020 build holds `cp /var/web/config.dat %s` — trace the `%s`
  - [ ] `notes/sink-inventory.md`, and ≥ 5 functions renamed in Ghidra
  - [ ] `notes/auth-flow.md` complete
  - [ ] ≥ 1 of the CVE-2025 series root-caused

  > 📌 The first three boxes are literally the [open questions carried out of
  > W01](PROGRESS.md#open-carried-forward). Starting points are already picked and
  > justified in [`notes/ghidra-triage.md`](notes/ghidra-triage.md) — this gate
  > opens with a reading list, not a blank Ghidra window.

- [ ] **G4 — a PoC a stranger can follow** (W05–W06)
  - [ ] ≥ 1 CVE reproduced on the physical unit or under emulation
  - [ ] `poc/` with preconditions, copy-pasteable `curl`, expected result, evidence
  - [ ] a stranger clones the repo and reproduces it inside 5 minutes

  > ✅ **The emulation risk is already partly retired.** The plan flagged this as
  > a W05 risk; a ten-minute check at W01 close-out showed the cheap path works —
  > the 2015 MIPS binaries run on an x86 host under `qemu-mips-static` in a
  > chroot, and `/bin/boa` prints its real usage text including `-c serverroot`
  > and `-f configfile`. **Scope: this shows the binaries load and start.**
  > Serving an actual request goes through `libapmib.so`, which reads `/dev/mtd*`
  > partitions that do not exist in a chroot. Bridging that is still G4's problem.

- [ ] **G5 — published write-up** (W08–W09) — a stranger understands the whole chain in 10 minutes
- [ ] **W07 — systematic bug hunt** (no gate) — 8 categories, not driven by known CVEs
- [ ] **W10 — close-out, disclosure admin, buffer**

## What is here

| Path | |
|---|---|
| [`RUNBOOK.md`](RUNBOOK.md) | **Start here to reproduce this.** Step-by-step from a bare Windows machine, written for someone with no reverse-engineering background. Every command carries its real expected output. (Traditional Chinese) |
| [`PROGRESS.md`](PROGRESS.md) | Gate status — the evidence behind every box above |
| [`notes/anatomy-n150rt.md`](notes/anatomy-n150rt.md) | How the firmware is built: container format, flash map, binaries, mitigations |
| [`notes/prior-art.md`](notes/prior-art.md) | Who disclosed what, when — and which claims survive contact with these images |
| [`notes/attack-surface.md`](notes/attack-surface.md) | Where to look, ranked |
| [`notes/ghidra-triage.md`](notes/ghidra-triage.md) | Which functions to open first, and why |
| [`reports/`](reports/) | Generated analysis: per-version reports, version diff, Ghidra string xrefs |
| [`tools/fwrecon/`](tools/fwrecon/) | The analysis tool written for this project |
| [`plan/`](plan/) | The ten week plans the gates above come from (Traditional Chinese) |
| [`LOG.md`](LOG.md) | Running log, including every wrong turn (Traditional Chinese) |
| [`study/QA.md`](study/QA.md) | Self-examination bank — the questions a hostile interviewer would ask about this work, with collapsible answers (Traditional Chinese) |

## Reproducing

[`RUNBOOK.md`](RUNBOOK.md) walks through this from a bare Windows machine,
assuming no prior reverse-engineering knowledge. The short version:

```bash
make setup     # install the toolchain (Linux side)
make verify    # G0: every tool answers when called
make fetch     # download + hash-verify the firmware (not redistributed here)
make unpack    # carve and extract the root filesystems
make recon     # regenerate everything under reports/
make test      # fwrecon test suite
```

```powershell
# Windows side: pinned JDK 21 + Ghidra 12.1.2, no admin rights needed
powershell -ExecutionPolicy Bypass -File tools\setup\setup-windows.ps1 all
.\ghidra\import.ps1 -Label 2.1.2 -Binary \\wsl$\Ubuntu-24.04\home\<user>\fwre-work\extracted\v2.1.2\squashfs-root\bin\boa
```

A pinned container image is in [`docker/Dockerfile`](docker/Dockerfile); CI
builds it on every push, so the toolchain pins are checked continuously.

Artefacts live outside the repository, on a Linux filesystem — see
[`docs/workspace-layout.md`](docs/workspace-layout.md) for why that is a
correctness requirement here and not a preference.

## Scope & ethics

- Work is limited to **hardware I own**, in an **isolated lab environment** —
  nothing is connected to production networks during testing.
- The focus is **understanding publicly disclosed issues**, not producing
  weaponised exploits.
- I do **not** test third-party, production, or ISP-owned devices.
- **Coordinated disclosure:** anything genuinely new goes to **TWCERT/CC** before
  any public discussion.
- Vendor firmware is **not redistributed** here — only the provenance and hashes
  needed to obtain and verify identical copies.
