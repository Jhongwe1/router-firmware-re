# Router Firmware Reverse Engineering — TOTOLINK N150RT

[![CI](https://github.com/Jhongwe1/router-firmware-re/actions/workflows/ci.yml/badge.svg)](https://github.com/Jhongwe1/router-firmware-re/actions/workflows/ci.yml)

A firmware reverse-engineering study of a consumer router I own, done for
learning and as a portfolio piece. The goal is to take a real, end-of-life
embedded device, rebuild an understanding of its firmware from nothing, and
trace **already-publicly-disclosed** vulnerabilities down to the responsible
function in the binary.

> 🚧 **In progress since 2026-07-30. G0 ✅ · G1 ✅ · G2 ✅ passed 2026-08-16 ·
> G3 ✅ passed 2026-08-11.**
> Two firmware images are unpacked and measured — **V2.1.2 (2015-08-25)** and
> **V3.4.0 (2020-10-30)** — and they bracket both public disclosure events
> affecting this device, which turns a teardown into a before/after comparison.
> Board below; the evidence behind every ticked box is in
> [`PROGRESS.md`](PROGRESS.md).
>
> **Latest (W02, 2026-08-16): the whole flash is off the device, and the build on it
> catches the vendor mid-fix.** 4 MiB read through the boot loader's own `FLR`+`DB` —
> no clip, no programmer, zero chunk retries — because the CH341A measured as an
> un-modded 5 V board and this unit is the only one there is. Reading the resident
> **2018-01-10** build against the two published images shows the response to Pierre
> Kim's 2015 disclosure happening in **three steps across five years**: comment out
> the line (2015) → **delete the backdoor binary and keep the uid 0 account** (2018)
> → remove the account (2020). **The middle step is on no download page.**
>
> **The device has been powered on since 2026-08-15, and it runs a firmware nobody
> had.** A serial console at 38400 — pin-out measured, baud measured from pulse width
> rather than guessed — puts the resident build at **2018-01-10**: not V2.1.2, not
> V3.4.0, a third one. That includes `/bin/boa`, **the binary this project has been
> reverse engineering since W03**, so W03/W04's findings describe two images this
> device has never run.
>
> The boot loader console also yields `FLR` + `DB` — **a full flash read path with
> no chip clip** — and with it, W01's container work is confirmed against silicon:
> the three burn addresses it derived from the vendor `.web` files are exactly where
> a third, unseen build sits. The config blob W04 needed is at flash `0x00C000`, and
> the barcode on the PCB is confirmed to be the unit's MAC.
>
> **W04:** the fourteen 2025 CVEs against this model reduce to **three**
> defects — two of them a single line and a single copy-pasted idiom, both
> **already present in the 2015 image**. The 2020 build repaired W03's
> authorisation hole but kept the technique that caused it, so `GET /config.dat`
> is still ungated nine months after full disclosure. And W01's
> "there is no `/etc/passwd`" was a false negative: both images ship one, and the
> 2015 template still contains Pierre Kim's `onlime_r` backdoor account at uid 0.
> **Those W04 results are static, read out of firmware images. The device itself
> was first powered on in W02 on 2026-08-15, and it turns out to run neither of
> them.**

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

- [x] **G2 — hardware access: UART + SPI dump** (W02) ✅ **passed 2026-08-16** ← [PROGRESS.md](PROGRESS.md#w02--2026-08-14--16)
  - [x] **a live bootlog** ← [`notes/uart-findings.md`](notes/uart-findings.md) —
        captured at 38400 over a measured pin-out, and independently decoded a
        second time off the same wire by a logic analyser; the two transcripts are
        byte-identical
  - [x] **SPI dump + hash verification** — **two** full 4 MiB reads, 105 minutes each,
        zero chunk retries, staged through **different RAM addresses** so a bad RAM
        region could not produce two identical wrong answers. `sha256 a800059a…` both
        times, recomputed independently of the tool that wrote them, and `cmp` finds
        zero differing bytes. 21 structural checks against expectations recorded
        before the image existed
  - [x] **dump vs vendor image compared** ← [`notes/dump-vs-official.md`](notes/dump-vs-official.md) —
        and the unit's build turns out to sit in the middle of a **five-year, three-step
        vendor remediation** that neither published image shows
  - [x] **annotated PCB photograph** ← [`notes/img/`](notes/img/) — rendered from a
        committed JSON spec, not drawn in an image editor, and the unit's MAC and
        serial are painted out with the coordinates recorded
  - [x] **settles two open questions, both carried since W01** — the real flash part
        and size (**Eon EN25QH32B, 4 MiB**, against a published 2 MB), and which build
        this unit runs (**2018-01-10 — neither analysed image**, which the Day 1
        date-code prediction called before anything was powered on)

  > ![TOTOLINK N150RT PCB, annotated](notes/img/05-pcb-top-annotated.jpg)
  >
  > ### ★ What W02 Day 1 turned up
  >
  > - **The flash is 4 MiB, and W01 said so first.** Eon EN25QH32B, 32 Mbit, at
  >   `U19`. W01 derived `≥ 4 MB` from the vendor container's own burn addresses
  >   three weeks before the hardware arrived, against a published specification of
  >   2 MB. This is the first falsifiable claim the project made about the physical
  >   world, and the physical world agreed.
  > - **The SoC is an RTL8196E**, not the RTL8196C the plan asserted — a different
  >   CPU core, which bears directly on W01's reading of the ELF header as MIPS-I
  >   and turns it into a testable hypothesis about the SDK's toolchain.
  > - **The RAM is 32 MiB fitted**, not 16 MB. *Fitted* is not *usable*; the kernel
  >   banner decides the second number and both are recorded.
  > - **The UART header is already populated** — W02 requires no soldering at all,
  >   which takes the week's largest irreversible-damage risk off the table.
  > - **Every one of those readings has exactly one source: the ink on the package.**
  >   `flashrom` agreeing that an `EN25QH32` is 4096 KiB is **not** independent — its
  >   database is keyed on the same part name. The second-source column is empty on
  >   purpose, and it is the Day 2–4 work list.
  >
  > ### ★ What W02 Day 2–3 turned up
  >
  > - **The unit runs a third firmware — built 2018-01-10 — including its own
  >   `/bin/boa`.** So the binary this project has read since W03 is not the one
  >   this device runs. W03/W04's findings still stand for the images they name;
  >   they simply do not cover this hardware, and W05/W06 against it will be testing
  >   a third binary.
  > - **W01's flash map, confirmed on silicon.** The three burn addresses it derived
  >   from the vendor containers — `w6cg` at `0x010000`, `cr6c` at `0x060000`, rootfs
  >   at `0x180000` — are exactly where this unseen build sits. Three for three, and
  >   the image needs 3.29 MiB against a published 2 MB.
  > - **`FLR` + `DB` in the boot loader is a full flash read path with no chip clip.**
  >   The plan listed that only as a bonus for the case where everything else already
  >   worked.
  > - **A W01 hedge comes off.** Its "*possibly* a build-script bug writing a size
  >   into `mkfs_time`" now holds on a third independent build.
  > - **The config blob W04 was blocked on is at `0x00C000`**, with its factory-default
  >   twin at `0x008000` — a differential pair into an undocumented format.
  > - **RTL8196E is now three sources deep**, including the boot code comparing a
  >   chip-ID register against `0x8196E000`. The Linux driver's dissenting
  >   `chip name: 8196C` loses because two lines earlier it announces it is probing an
  >   RTL8186.
  >
  > ### ★ What W02 Day 4 turned up
  >
  > - **The vendor's fix for the 2015 backdoor took three steps across five years,
  >   and the middle one exists on no download page.** 2015: comment out `#skt&`.
  >   **2018 (this unit): delete `/bin/skt` — and leave the `onlime_r` uid 0 account
  >   untouched, byte for byte, next to the dead `#skt&` line.** 2020: finally remove
  >   the account. CVE-2015-9550 and 9551 were disclosed together; two and a half
  >   years later the vendor had fixed one of them. `root:zhxPr1e7Npazg` is identical
  >   in all three.
  > - **The full 4 MiB was read through the boot loader, not a programmer.** The
  >   CH341A on the desk measured as an un-modded 5 V board — every pin it drives at
  >   5 V into a 3.3 V part — so the risk was left on a $3 board instead of on the
  >   only unit that gates G2 and G4. `FLR`+`DB`, 105 minutes, **zero chunk retries**.
  > - **The dump is checked against expectations written before it existed:** W01's
  >   burn addresses, derived from the vendor containers three weeks before the
  >   hardware arrived, and every offset the 2026-08-15 console session read. 21 hard
  >   checks, all passed — and the strongest check is not on that list, because
  >   **1.8 MiB of LZMA does not decompress by accident.**
  > - **Four more instrument bugs, none caught by a tool's own self-check** — including
  >   a parser written from a *summary* of the device's output when the verbatim
  >   transcript was in the runbook all along, and its guard suite passing 10/10
  >   against a format the device does not emit.
  >
  > ⚠️ **No second instrument has read this chip, and no JEDEC ID.** Both full reads
  > and the 2026-08-15 windows all go through the boot loader's `FLR`, so a
  > systematically wrong `FLR` would be invisible to every one of them. That column
  > stays empty on purpose.

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
  > ⚠️ **All of it is static**, read out of the two vendor images. W02 has since
  > powered the device on and found it runs **neither of them**, so none of this is
  > yet known to describe the hardware on the bench. The 2020 substring bypass in
  > particular is a reading of three
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
| [`notes/hardware-inspection.md`](notes/hardware-inspection.md) | **What the board actually is** — five ICs, the 4 MiB flash that W01 predicted, and a column of second sources that is still empty |
| [`notes/img/`](notes/img/) | Board photographs, the annotation spec they are rendered from, and what had to be painted out before they could be published |
| [`notes/uart-pinout.md`](notes/uart-pinout.md) | **The serial console** — pin-out with two sources per pin, baud measured from pulse width, why the console gives no shell, and the boot loader's command set |
| [`notes/uart-findings.md`](notes/uart-findings.md) | **The build nobody had** — a 2018 firmware that is neither analysed image, and what that costs the W03/W04 findings |
| [`notes/flash-layout.md`](notes/flash-layout.md) | **The flash map, read off the device** — W01's three predicted burn addresses, all three hit, plus where the config actually lives |
| [`notes/dump-vs-official.md`](notes/dump-vs-official.md) | **The 4 MiB dump against the two published images** — a five-year vendor remediation caught mid-step, and what four layers of verification do and do not prove |
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
| [`study/weekly-results.md`](study/weekly-results.md) | What each week actually produced, in the form it would be said out loud — every claim with its evidence, **and what that week did not prove** (Traditional Chinese) |

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
