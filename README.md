# Router Firmware Reverse Engineering — TOTOLINK N150RT

[![CI](https://github.com/Jhongwe1/router-firmware-re/actions/workflows/ci.yml/badge.svg)](https://github.com/Jhongwe1/router-firmware-re/actions/workflows/ci.yml)

A firmware reverse-engineering study of a consumer router I own, done for
learning and as a portfolio piece. The goal is to take a real, end-of-life
embedded device, rebuild an understanding of its firmware from nothing, and
trace **already-publicly-disclosed** vulnerabilities down to the responsible
function in the binary.

> 🚧 **In progress since 2026-07-30. G0 ✅ · G1 ✅ · G2 ⏸ blocked on hardware
> delivery · G3 ✅ passed 2026-08-11.**
> Two firmware images are unpacked and measured — **V2.1.2 (2015-08-25)** and
> **V3.4.0 (2020-10-30)** — and they bracket both public disclosure events
> affecting this device, which turns a teardown into a before/after comparison.
> Board below; the evidence behind every ticked box is in
> [`PROGRESS.md`](PROGRESS.md).
>
> **Latest (W04):** the fourteen 2025 CVEs against this model reduce to **three**
> defects — two of them a single line and a single copy-pasted idiom, both
> **already present in the 2015 image**. The 2020 build repaired W03's
> authorisation hole but kept the technique that caused it, so `GET /config.dat`
> is still ungated nine months after full disclosure. And W01's
> "there is no `/etc/passwd`" was a false negative: both images ship one, and the
> 2015 template still contains Pierre Kim's `onlime_r` backdoor account at uid 0.
> **Static results; no device has been powered on yet.**

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
> request-authorisation code — **answered in W03/W04: no authorisation runs for
> it, in either build**. The symlink proved the file is in the docroot and
> nothing more; the gate is what settled it. Which build is actually on my unit is decided
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

- [x] **G3 — point at the line in the binary** (W03–W04) ✅ **passed 2026-08-11** ← [PROGRESS.md](PROGRESS.md#w04--2026-08-11)
  - [x] the `/boafrm/` dispatch table found, with ≥ 10 handlers listed — **59 in 2015, 49 in 2020**, both `root_form[]` arrays recovered with the function that reads each
  - [x] ≥ 1 authentication candidate function identified — `process_header_end`, in **both** builds: `0x0040be0c` (2015) and `0x00409fd8` (2020)
  - [x] **where `formSysCmd` is really registered** — **nowhere.** It is in neither dispatch table; and V2.1.2 ships *after* the last build Pierre Kim reports as vulnerable to CVE-2015-9551, so this reads as the vendor's fix
  - [x] **whether Boa authenticates `.dat` requests** — **no, in both builds**, and not because `.dat` is special: 2015 checks only URIs containing `htm`, 2020 checks only `.htm`, `.asp` or POST
  - [x] `FUN_00440eec` holds `cp /var/web/config.dat %s` — traced: `formSaveConfig`, a `localtime()` filename. **Not injectable**, and the buffer W03 worried about has 100 bytes for a 47-character format
  - [x] [`notes/sink-inventory.md`](notes/sink-inventory.md), and ≥ 5 functions renamed in Ghidra — **185 named** from table evidence, in the project database
  - [x] [`notes/auth-flow.md`](notes/auth-flow.md) complete for 2015 **and** [`notes/auth-flow-2020.md`](notes/auth-flow-2020.md) for 2020
  - [x] ≥ 1 of the CVE-2025 series root-caused — **twelve of the fourteen**, and they reduce to **three** defects. The series names *this* model (`N150RT 3.4.0-B20190525`), which W01 and W03 both had wrong
  - [x] **beyond the gate:** the backdoor account located — `onlime_r` / `12345`, uid 0, in the build the vendor shipped *after* the 2015 disclosure · every MIB id named from `libapmib.so` · two shipped private keys

  > ### ★ What W04 turned up
  >
  > - **Fourteen 2025 CVEs, three defects.** `sprintf(buf[100], "flash set
  >   HW_WLAN0_WSC_PIN %s", localPin); system(buf)` is a single line that is both
  >   CVE-2025-3987 (no filtering) and CVE-2025-4462 (no bound) — and it is
  >   **identical in the 2015 image**, ten years before either id existed. Four
  >   more are one `submit-url` idiom that appears in **34 handlers**; the four
  >   with ids are a sample, not a set.
  > - **`lastUrl[100]`, then `needReboot`.** The `submit-url` copy lands in a
  >   `.bss` buffer whose size comes from the symbol table, not from a guess, and
  >   the next two objects after it are control flags. Separately, omitting the
  >   parameter makes the handler `strcpy` into the `""` literal in a read-only
  >   segment — as the code reads, a one-request unauthenticated crash.
  > - **The 2020 build fixed the 2015 hole and kept the technique.** Every POST
  >   is now gated — that is a real repair. But authorisation is still decided by
  >   `strstr` over the URI, and the exemption list is unanchored.
  >   `GET /config.dat` remains outside the gate in a build dated nine months
  >   after full disclosure.
  > - **W01's "there is no `/etc/passwd`" was a false negative** — a dangling
  >   symlink read as an absent file. Both images ship the template; the 2015 one
  >   contains Pierre Kim's `onlime_r` account at uid 0, with his published hash,
  >   and `root` is `123456` in **both** builds.
  > - **Three bugs in the new tracer, none caught by its own self-check.** All
  >   three were caught by the project's own rule — read the two builds across,
  >   not down — because one codebase five years apart cannot go 86 → 0.
  >
  > ⚠️ **All of it is static.** No device has been powered on — W02 is still
  > blocked. The 2020 substring bypass in particular is a reading of three
  > `strstr` calls that has never been executed; it goes to TWCERT/CC if and only
  > if W05/W06 demonstrates it.

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
| [`notes/ghidra-triage.md`](notes/ghidra-triage.md) | Which functions to open first, and why — with the three W01 calls W03 overturned |
| [`notes/dispatch-table.md`](notes/dispatch-table.md) | `root_form[]` recovered: every `/boafrm/` route in both builds, and what changed between them |
| [`notes/auth-flow.md`](notes/auth-flow.md) | **How Boa decides you are allowed in** — the substring gate, the IP-as-session model, the uninitialised credential compare |
| [`notes/sink-inventory.md`](notes/sink-inventory.md) | Every `system`/`strcpy`/`sprintf` call site, ranked — and how the first version of the census was wrong |
| [`notes/auth-flow-2020.md`](notes/auth-flow-2020.md) | **The 2020 rewrite** — what it fixed, what it kept, and the 401 that is never sent |
| [`notes/submit-url-overflow.md`](notes/submit-url-overflow.md) | **Four CVEs, one idiom, 34 handlers** — `lastUrl[100]` and the parameter you must not omit |
| [`notes/credentials.md`](notes/credentials.md) | **Where the credentials actually are** — the backdoor account W01 concluded could not exist, and two shipped private keys |
| [`notes/mib-and-config-dat.md`](notes/mib-and-config-dat.md) | The APMIB table recovered, and what `config.dat` is made of |
| [`notes/formSysCmd-analysis.md`](notes/formSysCmd-analysis.md) | The CVE endpoint that is not there, and why three pieces of evidence pointed the wrong way |
| [`notes/skt-analysis.md`](notes/skt-analysis.md) | The 2015 backdoor decoded: port, magic words, and the one `iptables` line it exists to run |
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

$boa = '\\wsl$\Ubuntu-24.04\home\<user>\fwre-work\extracted\v2.1.2\squashfs-root\bin\boa'
.\ghidra\import.ps1  -Label 2.1.2 -Binary $boa                    # analyse once (minutes)
.\ghidra\analyze.ps1 -Label 2.1.2 -Script BoaFormTable -Binary $boa   # recover root_form[]
.\ghidra\analyze.ps1 -Label 2.1.2 -Script BoaSinks     -Binary $boa   # sink census
```

Import and analysis are separated on purpose: auto-analysis is expensive and
cached in the project, a script is cheap and gets rewritten a dozen times a day.
Every Ghidra report records the SHA-256 of the binary it describes, and CI fails
if one does not — a report that cannot name its own input is not evidence.

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
