# Router Firmware Reverse Engineering — TOTOLINK N150RT

[![CI](https://github.com/Jhongwe1/router-firmware-re/actions/workflows/ci.yml/badge.svg)](https://github.com/Jhongwe1/router-firmware-re/actions/workflows/ci.yml)

A firmware reverse-engineering study of a consumer router I own, done for
learning and as a portfolio piece. The goal is to take a real, end-of-life
embedded device, rebuild an understanding of its firmware from nothing, and
trace **already-publicly-disclosed** vulnerabilities down to the responsible
function in the binary.

> 🚧 **In progress since 2026-07-30. G0 ✅ · G1 ✅ · G2 ✅ passed 2026-08-16 ·
> G3 ✅ passed 2026-08-11 · G3.5 ✅ · G3.75 ✅ both passed 2026-08-17 ·
> G4 ✅ passed 2026-08-18, clause 3 split into 3a met / 3b impossible.**
>
> **Latest (W08 Day 1, 2026-08-21): half of this device's configuration had
> never been decoded, and the tool that had found the name table for it printed
> the table's length and threw the table away.** Thirteen of the 344 entries in
> the configuration region are *table-valued*; one of them, `WLAN_ROOT`, is
> **22,044 of the 45,226 decompressed bytes**. All thirteen decode now — six
> blocks of 3,674 bytes with no remainder, checked against a geometry read out
> of `libapmib.so`'s own records (`count = total_size / element_size`) rather
> than inferred from the data it validates.
>
> The name table was already in the committed report, as a number:
> `"runner_up": 133`, printed since W04, and each `WLAN_ROOT` block is 133 TLVs.
> **Nothing was wrong, nothing disagreed, no figure was absurd** — the recovery
> had asked "which run is the table" instead of "what are the runs", and a check
> cannot catch a question nobody posed.
>
> What it settles: this build's factory wireless configuration is an **open
> network** — `ENCRYPT = 0`, `WPA_PSK` and `WSC_PSK` all zero, a fixed SSID,
> WPS enabled — corroborated by one line the device's own `/bin/flash` printed
> in W07. And reading across six builds, the two 2020 ones add
> `WSC_AUTO_LOCK_DOWN` and `IEEE80211W`; the 2018 build on this unit has neither.
> [`notes/wlan-root.md`](notes/wlan-root.md).
>
> **The same day, this project broke its own first rule and caught it four hours
> later.** Two format strings in the boot loader — `**TFTP Client Upload...` —
> were read as saying the loader is a TFTP *client*, a design conclusion was
> written on top of that single source, and it was pushed. "Client" names the
> peer. The measurement that settles it had been in `BENCH-LOG.md` since
> 2026-08-17: a read request sent to the loader came back with **516 bytes of
> DATA from port 2098**. A wrong claim about protocol direction does not look
> wrong — it becomes a tool that is written, tested and taken to the bench,
> where it listens on port 69 while the loader waits to be asked, and the
> failure arrives as "the rescue path does not work", pointing at the device.
> The correction, and the client that replaced the server:
> [`tools/loader-tftp.py`](tools/loader-tftp.py).
>
> **Latest (W08 Day 0, 2026-08-20): the boot loader has been printing
> `chipName: UNKNOWN` since the first boot log this project captured, and the
> answer was inside the loader.** It carries a table of 32 SPI flash
> descriptors keyed on JEDEC id — recovered at a fixed `0x20` stride, with the
> stage-2 load base *derived* from the name pointers rather than assumed, by a
> funnel that refuses at zero survivors and at two. **This unit's part has no row
> in it.** The same table turns out to carry a vendor defect: `ef3016` appears
> twice, naming both `W25X32` and `W25X64`, and `W25X64`'s real id is `ef3017`.
> [`notes/loader-chip-table.md`](notes/loader-chip-table.md).
>
> A second desk result, on a copy of the dump and with nothing clipped: the
> string `admin` appears **once**, literally, inside the *compressed*
> configuration region, and `USER_PASSWORD` is a back-reference to it. The proof
> is arithmetic — perturbing those five bytes moves the payload checksum by
> exactly **twice** the byte-sum delta. Replacing them with a permutation of the
> same characters leaves the checksum valid and changes **two** fields. Whether
> the running device reads it is the one thing left for the clip.
>
> **Latest (W06, 2026-08-17): an unauthenticated HTTP POST changed nine specific
> bytes on this router's SPI flash, and all nine are named.** Eight are the ASCII
> digits of a value chosen by the client; the ninth is the region's checksum,
> recomputed by the device. They are read before and after through the boot
> loader over a serial console — a path sharing no code with the web server, the
> kernel, or Ethernet.
>
> **They are also in the wrong region.** The plan said that write lands in the
> configuration block. It lands in `H601`, which holds this unit's MAC addresses
> and radio calibration — measured at manufacture, in no vendor image, and **not
> restored by a factory reset.**
>
> All nine were put back, and the final read is byte-identical to a dump taken
> before this project had ever written to the device.
>
> Two instruments written for this project are now confirmed by the vendor's own
> binaries running over the same bytes: `flash extr /web` writes **143 files
> whose SHA-256s all match** what `fwrecon web` declared from a format with no
> checksum in it, and `flash all` agrees with `fwrecon compcs` on **249 of 316
> shared names**, with 66 more explained by four rendering rules and exactly one
> left over. **`boa` creates `/web/config.dat` during start-up**, before it
> listens — so the exposure half of CVE-2019-19822 on this hardware needs no
> request at all, which is one step shorter than this repository had assumed.
>
> **`G3.5` closed on the bench**: the flash recovery path was executed —
> write, read back to a *different* RAM address, erase, verify — and the drill
> turned up something its own criterion did not ask about. The boot loader has
> **no erase command at all**, so `FLW` must erase for itself, which points at a
> whole-4-KiB read-modify-erase-program cycle. `H601` — this unit's MACs and
> radio calibration, which exist nowhere else — is inside one such sector, and
> so is the `HW_WLAN0_WSC_PIN` that W06's proof-of-concept writes.
>
> **W05 closed at 27 of 27 with the definition of done complete.** Four cases
> scheduled for the week were ones the week's own plan forbids running — three
> command injections it defers to W06, and the reset button, which is
> destructive — so its closure command could never have reached zero. They were
> moved with a reason, a date and a hash re-declared in the same commit;
> `[schedule].sha256` now makes a week that moves show up in a diff, the same way
> `[freeze].sha256` already did for a prediction.
>
> **The boot loader's own strings are not in the flash dump.** `grep FLR` over
> 4 MiB finds nothing, and that had been read as *the loader is terse*. At
> `0x0012F0` there is an LZMA stream, 17,334 bytes in and 56,592 out, holding the
> command interpreter, the TFTP client and the SPI chip table. Unpacking it
> settles `P9-1` from the desk: thirteen command-line-shaped needles, **zero
> hits**, from a scan demonstrated in the same run to find all seventeen commands
> the console prints. The kernel, decompressed from the same dump, carries
> `console=ttyS0,38400 root=/dev/mtdblock1` compiled in and **no `init=`** — so
> the boot loader has nowhere to put one, and the prediction that it could was
> refuted without spending a power cycle.
>
> **The authorisation gate predicted three pages nobody had looked at.** W04-2
> read eleven exemption strings out of `process_header_end` at instruction level.
> Five name pages the firmware does not ship; an unanchored substring test over
> the rest predicts exactly seven exempt pages — including `wan_status.htm` and
> `Connect_status.htm`, which are unauthenticated only because `status.htm` is a
> substring of them. Seven predicted, seven observed, sixty-nine blocked, **no
> error either way across all 76 shipped pages** — and then `/boafrm/formLogin.htm`
> answered `404` where the other fifty-six answered `302`, because `formLogin` is
> on that list too. It is still not a bypass, and the reason is sharper than "it
> did not work": the exemption and the file lookup read the same normalised path,
> so any path decorated enough to become exempt is one the server then fails to
> open.
>
> **And an unauthenticated POST with no parameters at all holds the device's
> single web server for four to ten seconds; about forty-five in sequence remove
> it until someone cuts the power.** `ping` keeps answering, the console prints
> nothing, and nothing respawns `boa`. Separately, that POST round overwrote the
> **factory-default** configuration region with the current one — so on this
> build, "restore factory defaults" would restore whatever was last written.
>
> **And then it was put on an isolated segment and asked 22 of the 31 questions
> that were frozen before the first packet.** An unauthenticated
> `GET /config.dat` returns 7,490 bytes whose SHA-256 is **identical to flash
> offset `0xC000` in W02's dump** — so CVE-2019-19822 is demonstrated end to end,
> the credentials it contains authenticate, and, incidentally, **this flash has
> now been read by a second instrument**: the kernel's MTD driver over Ethernet,
> against the boot loader's SPI routine over UART. That column has been empty
> since W02.
>
> **Four predictions were refuted, which is the return on writing them down
> first.** The substring bypass the disassembly implied does not work — twelve
> shapes, none bypassed. The session model is not the global the disassembly
> pointed at: there is no session at all, only stateless HTTP Basic, with no
> lockout after fifty wrong passwords. And two open TCP ports — **52869 and
> 52881, both UPnP** — appear in no prediction at all, on a device whose UPnP
> daemon answers `Server: miniupnpd/1.4` while being `/bin/miniigd`, which is a
> different project with a different CVE history.
>
> **The identifier the device publishes is not the one its CVE is indexed
> under.** `/etc/version` says `TOTOLINK-CX-N150RT-…`; `boa` says
> `TOTOLINK-N150RT-…` and that is what an unauthenticated `status.htm` returns.
> `CX` appears in exactly one file in the rootfs. This project lost two weeks to
> that string; **this is the mechanism.**
>

> **Latest (W04-2, 2026-08-16): the build this device actually runs has been
> read, and it has a command-execution handler that neither downloadable image
> has.** `formSysCmd` is entry `0x004838a8` of this unit's dispatch table —
> `grep` on the three raw binaries gives **0 / 1 / 0** for 2015 / 2018 / 2020.
> Its `sysCmd` parameter reaches `system()` unfiltered, and this build's
> authorisation gate only runs on URIs containing `.htm` or `.asp`, which
> `/boafrm/formSysCmd` does not. W04 had recorded the handler's absence from the
> published images as the vendor's fix; a fix does not reappear two and a half
> years later, and that reading is withdrawn.
>
> **That endpoint turns out to have its own CVE, which this project did not know
> while reading it.** CVE-2024-51228 names `/boafrm/formSysCmd` and lists
> `TOTOLINK-CX-N150RT V2.1.6-B20171121.1002` — byte-for-byte this unit's
> `/etc/version`. So the reachability result is an **independent derivation from
> the binary of a claim disclosed in 2024**, and
> [`prior-art.md`](notes/prior-art.md#2024--cve-2024-51228-and-the-gap-that-let-it-be-missed)
> records why a survey organised around known disclosure events missed it.
> **What is this project's own is narrower and checkable:** NVD scores it `PR:H`
> (privileges required, high) for 6.8 MEDIUM, while the original researcher
> writes "without credentials" and the instruction-level read agrees with the
> researcher. If they are right the vector is `PR:N` and the score 8.8 HIGH.
>
> Nothing has been sent to the device over the network. That is G4's job.
> **G3.5 closed on 2026-08-17**, when the flash recovery path was finally
> executed on the bench.
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
> had:** `TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002`, read from `/etc/version` in
> its own flash. A serial console at 38400 — pin-out measured, baud measured from
> pulse width rather than guessed — got the image off it. Not V2.1.2, not V3.4.0,
> a third build, and that includes `/bin/boa`, **the binary this project has been
> reverse engineering since W03**, so W03/W04's findings describe two images this
> device has never run. **Its *version* is published; this *build* is not** — the
> downloadable V2.1.6 is `B20160516`, eighteen months earlier and without the `CX`.
> The binaries are stamped 2018-01-10, seven weeks after the version label, and
> why is unresolved — but the label is the searchable identifier and the timestamp
> is not, which is how CVE-2024-51228 sat unfound for two weeks.
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
  >   The second-source column is empty on purpose, and it is the Day 2–4 work list.
  >
  >   > **Corrected 2026-08-21.** This bullet used to add that `flashrom` agreeing
  >   > on 4096 KiB is not independent *"because its database is keyed on the same
  >   > part name"*. **That is false** — flashrom matches on `manufacture_id` and
  >   > `model_id`, and the name is the lookup's output rather than its index. Told
  >   > to emulate `W25Q128FV` it answers `W25Q128.V`: a different string comes out
  >   > than went in, which a name-keyed lookup cannot do. So flashrom's answer
  >   > **is** a second source for *which part an id denotes* — though not for
  >   > *what the id bytes are*, which is the same clip on the same bus. The same
  >   > wrong sentence stood in `RUNBOOK` §8.12.41 and in `P9-7`'s registered
  >   > prediction; the RUNBOOK is corrected, the prediction is deliberately not.
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
  > - **And five more on 2026-08-18, one of which reached outside the tooling
  >   entirely**: guests ran in a `chroot` as root with no namespace, so a
  >   firmware handler that calls `system("reboot -f")` powered off the host —
  >   three times, each time looking like the harness hanging. Two of the other
  >   four were a closed loop: a refusal that printed a fix command its own
  >   parser rejects, and the correctly-spelled version exiting 1 in silence
  >   without killing anything.
  >
  > ⚠️ **No second instrument has read this chip, and no JEDEC ID** — true as of
  > **2026-08-20**. Both full reads and the 2026-08-15 windows all go through the
  > boot loader's `FLR`, so a systematically wrong `FLR` would be invisible to
  > every one of them. That column stays empty on purpose.
  >
  > 🛑 **The instrument was used on 2026-08-21 and could not reach the part.**
  > Seating the SOIC-8 clip on `U19` takes the **CH341A itself** off the USB bus,
  > and the chip measures **1.70 V** under three different supplies — including an
  > external regulator that held a healthy 3.3 V on its own side. **In-circuit
  > reading does not work on this board.** Whether that is the board clamping the
  > `VCC` net or resistance in the clip path is **open item 97**, and the committed
  > claim is only the first half. **Nothing was read and nothing was written**; the
  > router was never powered. `BENCH-LOG.md` 2026-08-21 實錄 carries every number.
  > The column above therefore stays empty, now for a measured reason rather than
  > for want of an instrument.
  >
  > 📌 **The instrument exists and is verified** (2026-08-20). The CH341A that W02
  > measured as an un-modded 5 V board has been
  > re-worked — 5 V feed cut on the back, 3.3 V jumpered into that pin — and the
  > mod is confirmed **at two points in the circuit**: all eight socket pins read
  > 3.3 V (the effect, and `DO` was the 5 V board's worst pin, held 1.7 V above
  > its own supply), and **pin 28**, the CH341A's own I/O supply, reads 3.3 V
  > (the cause — and the measurement W02 recorded as missing). `BENCH-LOG.md`
  > `T-84`.
  >
  > **Having a verified instrument is still not having the measurement**, and
  > that distinction is what this line has been holding open since 2026-08-16.
  > `A5.1`–`A5.5` are written, every prediction is in `BENCH-LOG.md` 2026-08-20
  > §2, and nothing has been clipped.
  >
  > 🔎 What the desk *did* settle, with no clip: the boot loader carries a table of
  > 32 flash descriptors keyed on JEDEC id, and **this unit's part has no row in
  > it** — which is why `chipName: UNKNOWN` has been on line 3 of every boot log
  > since 2026-08-15. [`notes/loader-chip-table.md`](notes/loader-chip-table.md).

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

- [x] **G3.5 — every `boa` claim names the binary it was measured on** (W04-2) ✅ **passed 2026-08-17** ← [PROGRESS.md](PROGRESS.md#w04-2--2026-08-16)
  - [x] `root_form[]` + sink census for all three builds, each carrying its input's SHA-256
  - [x] [`notes/auth-flow-2018.md`](notes/auth-flow-2018.md) — the gate on the resident build, key branch read at **instruction level** because the decompiler raised three warnings on it
  - [x] [`notes/compcs-decode.md`](notes/compcs-decode.md) — the config region decoded; `TELNET_ENABLED = 0` with a second source
  - [x] G4's target chosen from evidence: `POST /boafrm/formSysCmd`
  - [x] **the `FLW` recovery path rehearsed** — executed 2026-08-17: write, read
        back **to a different RAM address**, erase, verify. Verbatim transcript in
        [`RUNBOOK.md` §8.9.1](RUNBOOK.md), and the drill overturned four things
        the runbook asserted about it

  > ### ★ What W04-2 turned up
  >
  > - **`formSysCmd` is in this unit's dispatch table and in neither published
  >   image.** `grep -aoc` on the three raw binaries: **0 / 1 / 0**. Absent →
  >   present → absent is a build-time option, not a vendor fix, and **W04's
  >   G3 box 1 is overturned.** CVE-2019-19824 lists "N150RT through 3.4.0" as
  >   affected; both images anyone can download happen to be ones without it, so
  >   reproducing that CVE from published firmware gives the wrong answer about
  >   this hardware.
  > - **The gate is a third answer.** 2015 checks `strstr(uri,"htm")`; 2020 adds
  >   POST; **2018 checks `.htm` or `.asp` and nothing else** — 2015's outcome by
  >   2020's mechanism, decided by 13 unanchored `strstr` calls on one string.
  > - **The config region is decoded.** LZSS over a TLV table, confirmed twice —
  >   inferred from the data, then read out of `libapmib.so`'s `Decode`, which
  >   also supplied a checksum invisible in the data that both regions pass.
  >   `USER_PASSWORD` is `admin` in plaintext, which is CVE-2019-19823 located
  >   rather than cited, and `SSH_PASSWORD` is a factory-default `xa.zioncom` —
  >   a **third** credential system where W04 found two.
  > - **`TELNET_ENABLED = 0`, confirmed by the code that reads it.** So
  >   `root:123456` is *not* an entry point on this unit — it is the second stage
  >   of a chain, and calling it an entry point overstates it by a step.
  > - **A build gate with a positive control** — [`BoaGate.java`](ghidra/scripts/BoaGate.java).
  >   None of the three builds would pass it, and while R1 and R3 nearly halve by
  >   2020, **R2 — a request parameter reaching a shell — goes 5 → 6 → 8.**
  >   The control earned its keep immediately: the gate returned **0 findings on
  >   a build known to be defective**, twice, for two unrelated reasons. Both
  >   would have shipped as "clean".
  >
  > ⚠️ **Still entirely static.** Nothing has been sent to the device, no port
  > has been touched, and the phrase used throughout is *the code reads as*.

- [x] **G3.75 — nothing is sent to the device until the pre-engagement is done** (W05 Day 0) ✅ **passed 2026-08-17** ← [PROGRESS.md](PROGRESS.md#w05--2026-08-17)
  - [x] **the `FLW` recovery path rehearsed** — this is G3.5 #5, cited and not restated. Closed 2026-08-17
  - [x] **isolation verified** — exactly two MAC addresses on the segment, eight packets each, no DNS and nothing outbound. The control is that the capture recorded 16 packets at all: an earlier one recorded **zero**, and zero proves nothing until the link is known to deliver
  - [x] **IoC pre-check** — both halves, against criteria written before the check: **the live config differs from this unit's own factory baseline in 4 of 343 entries**, no fifth, and every port the register named is closed
  - [x] **the prediction ledger is frozen** ← [`test-ledger.md`](test-ledger.md) — **134** registered tests, **117** carrying a written refutation condition, hashed and committed **before any request is served**; W05 closed **27 of 27**
  - [x] **the disclosure register is written** ← [`docs/disclosure.md`](docs/disclosure.md) — seventeen rows, what each is worth, and the rule that decides what gets published

  > ### ★ Why this gate exists
  >
  > W05–W07 execute on the order of 130 tests against one device, and two things
  > go wrong with that if the list is a document. **State duplicated across two
  > files drifts** — PROGRESS.md records that happening on 2026-08-16, one commit
  > after the rule against it was rewritten. And **a test with no pre-written
  > failure condition gets read as a success afterwards**, because by the time
  > the response arrives the reader knows what they wanted to see.
  >
  > So the register owns per-test state and nothing else does; the gate board
  > links to it and never restates a row. Predictions and refutation conditions
  > are hashed into the register, so editing one after the fact means editing the
  > hash in the same commit, where `git diff` shows it. `tools/rtcase.py check`
  > runs in CI and **refuses a result whose case has no refutation condition, a
  > confirming verdict with no artefact, an artefact path that does not exist,
  > and a prediction edited after a result was recorded against it.**
  >
  > [`tools/test-rtcase.sh`](tools/test-rtcase.sh) drives 22 cases proving each
  > of those refusals actually fires, and CI runs it beside the gate — because a
  > gate that has never been seen to fail is the shape of instrument bug 12.
  >
  > **Nine items were cut rather than run**, each with its reason in the ledger:
  > post-exploitation persistence, anti-forensics, lateral movement, credential
  > harvesting on a live host, downgrading the unit to reinstall a factory
  > backdoor, and the wireless attacks whose radiation reaches third parties.
  > None of them produce a checkable fact about this device.

- [x] **G4 — a PoC a stranger can follow** (W05–W06) ✅ **passed 2026-08-18**, clause 3 split ← [PROGRESS.md](PROGRESS.md#w07-day-0--g4-closed--2026-08-18)
  - [x] a chain on the physical unit, each link separately pointable — [`poc/`](poc/)
  - [x] **at least one link evidenced out of band**, not from the HTTP response — **two**: ICMP echo requests sourced from the router, and nine named bytes on the SPI NOR
  - [x] **3a — an L2 path for the command-injection primitive**: anyone, a downloadable image, emulation — [`poc/05`](poc/05-l2-published-image.md), `P0-11` + `P3-14`
  - [x] **3b — an L2 path for the L1 chain** — ❌ **impossible by construction, and recorded as the finding.** See below
  - [x] every PoC document opens with a scope table saying which builds were tested and which were not
  - [x] [`poc/run.sh`](poc/run.sh) fails and names the failing step — 11 checks against the device, 8 under emulation, and it caught two defects **in itself** on its first run

  > ❌ **Clause 3 was split rather than met, and the half that cannot be met is
  > the finding.** The plan assumed the L2 reproduction would run the `localPin`
  > line, which *is* byte-identical in the 2015 and 2020 images. W04-2 then moved
  > G4's target to `formSysCmd` for a good reason — it is the CVE that names the
  > build this unit runs — and nobody noticed that **the new target is in neither
  > downloadable image's dispatch table** (`0x0044ee2c` here, absent in both), so
  > that chain cannot exist there at all. Two individually correct decisions whose
  > combination was not. **A CVE naming a build nobody can download is not
  > reproducible by anyone who does not already own one**, and no amount of work
  > changes that — so 3b is closed as impossible instead of carried as a debt.
  >
  > ✅ **3a is met and it is not a consolation prize.** An unauthenticated
  > `POST /boafrm/formWsc` executed a command inside an environment built from the
  > published V2.1.2 container and nothing else. `qemu`'s own syscall trace shows
  > `execve("/bin/sh",{"sh","-c","flash set HW_WLAN0_WSC_PIN 1;cat /etc/version > …"})`,
  > and the file it wrote contains `TOTOLINK-N150RT-V2.1.2` — the published build
  > naming itself through a command it was made to run. Two controls on the same
  > handler in the same session, `peerPin` and `targetAPSsid`, did nothing — the
  > **same three-way discrimination W06 measured on silicon**, five years of
  > firmware apart.
  >
  > 🔵 **What the download does not contain, measured rather than assumed.** The
  > container has exactly three sections and the **first 64 KiB of flash is in
  > none of them** — boot loader, `H601`, `COMPDS`, `COMPCS` are written at
  > manufacture. A flash holding only what the container declares gets as far as
  > `Invalid hw setting signature` and stops. 82.9 % of the image is reconstructed
  > from the download; the remaining three regions are synthesised with zeroed
  > payloads and **no byte is copied from any physical unit** —
  > [`reports/mkflash-2.1.2.json`](reports/mkflash-2.1.2.json) names every range.
  > The vendor's own `flash default` would generate the real thing "from hard
  > code" and **cannot run under `qemu-user`**: it dies on an unaligned store the
  > device's MIPS kernel fixes in its trap handler. That one difference is why
  > Realtek-SDK userland resists emulation from a download.

  > ✅ **`boa` serves under `qemu-user` after all, and W05 said it could not.**
  > The alignment trap is real, but `-strace` puts it in one place: `boa` takes
  > `SIGBUS` at an odd address immediately after
  > `open("/web/config.dat", O_RDWR|O_CREAT|O_TRUNC)` — it dies **generating**
  > that file at start-up, not serving. Make that one `open()` fail and the server
  > binds and answers, with the authorisation gate behaving exactly as W04-2 read
  > it at instruction level: an exempt page 200, a gated page 302. The
  > unauthenticated command injection reproduces there too, **with no device
  > attached**.
  >
  > The irony is exact: the line that produces this project's best evidence chain
  > — an unauthenticated `GET /config.dat` — is the same line that makes it the
  > one link emulation cannot reproduce.

  > 🔴 **What the flash evidence turned out to be.** `plan/W06` drew the last link
  > as *"`flash set` writes the `COMPCS` block"*. It writes **`H601`** — the
  > hardware MIB at `0x6000`, which holds this unit's MAC addresses and its radio
  > calibration constants. They were measured at manufacture, appear in no vendor
  > image, and **a factory reset does not restore them**. So one unauthenticated
  > HTTP POST reaches the one region of this device that cannot be recovered from
  > any source outside the device itself.
  >
  > This project spent that morning building a flash writer whose allow-list makes
  > `H601` unreachable by construction, with no flag to widen it — and then the
  > device's own `flash set`, driven by one request, wrote it anyway. **The guard
  > protected the instrument, not the device.**
  >
  > Nine bytes changed, all nine came back, and the final read is byte-identical
  > both to the pre-injection snapshot and to a dump taken before this project had
  > ever written to the device. **Changed, pointed at, and reversed — all three on
  > silicon.**

- [ ] **G5 — published write-up** (W08–W09) — a stranger understands the whole chain in 10 minutes
- [x] **W07 — systematic bug hunt** (no gate) ✅ **closed 2026-08-19** — 8 categories, not driven by known CVEs. **58 of 58 register rows closed.** The last one, `P5-2`, had been written off as needing an observation channel this device does not offer, and it needed none: two kernel fault messages already sitting in [`BENCH-LOG.md`](BENCH-LOG.md) put `libuClibc` at `0x2aae3000` in `boa` and `system` at `0x2ab08460`, with the four-byte disagreement against qemu-user *predicted* by the MIPS branch-delay-slot rule rather than tolerated ([`notes/mips-ret2libc.md`](notes/mips-ret2libc.md), [`tools/libbase.py`](tools/libbase.py)). It was recorded **`partial`**, not confirmed, because both messages came from one boot and the register's refutation asks for two — scoring a condition that could not have fired is the mistake this same week caught itself making elsewhere. **The device settled it that night**: `/proc/<pid>/maps`, read over a telnet shell four boots later, prints `libuClibc` at `0x2aae3000` in `boa` and `0x2aabe000` in `wscd` — the second of those a value that had been *predicted* from one library's program headers and never observed. `/proc/sys/kernel/randomize_va_space` reads **2**, full randomisation, on a kernel that does not act on it; believing the flag would have closed the row as refuted without one address being read. Three bench visits, 2026-08-18 and the close-out overnight into 2026-08-19: 21 rows closed on the silicon plus 4 upgraded off emulated evidence, then the reset button, the WAN behavioural half, and a route injection the first visit could not deliver. The heaviest result was not on the list: an unauthenticated POST from W05 had written `DHCP_MTU_SIZE=0` to flash, and this unit was unable to obtain a WAN address for two days — through every reboot, and through four bench sessions that had no reason to look. It also overwrote the **factory-default** block, 25 of 343 fields, so the vendor's own recovery path had to be tested rather than assumed; the reset button restores from a hard-coded table instead and brought the device back byte-for-byte to its 2026-08-16 state. Nothing now starts a session without asking the device whether it can still route ([`tools/device-liveness.py`](tools/device-liveness.py), wired into `make doctor`). The deliverable is [`notes/bughunt.md`](notes/bughunt.md), **twenty-four** verdicts each pointing at a file under `reports/`, and a *relatively safe* section the same size as the verdict table. The last two arrived on the closing night: `miniigd` **terminates** on any `NewInternalClient` that `inet_addr()` rejects — one unauthenticated request, recoverable only by power cycle, and *not* an injection, which took a twenty-two-character control with no shell metacharacter in it to establish; and the CVE-2014-8361 command execution the same handler's code shape promises **does not happen on this build**, because the daemon dies first. Three of them are this project's own findings **withdrawn**, and one more turned out to have a CVE against it. The last thing W07 found was not a defect in the firmware: **six committed files, one of them the disclosure register, asserted `52869/tcp open` in the present tense** — sourced to a sweep from 2026-08-16, while the same repository recorded the port **closed** on 2026-08-18 because this project's own unauthenticated POST round had disabled the daemon. Both readings were right when taken and neither sentence carried a date. They all do now — the most recent retraction came from building an instrument that could tell the emulator's behaviour from the firmware's ([`tools/alignfix/`](tools/alignfix/)), not from arguing about a caveat
- [ ] **W10 — close-out, disclosure admin, buffer**

## What is here

| Path | |
|---|---|
| [`REPRODUCE.md`](REPRODUCE.md) | **Start here.** Which claims you can verify with a clone alone, which need an N150RT of your own, and **which are not reproducible by anyone but the author — and why.** Also: the one five-minute check worth running first |
| [`runsheet.md`](runsheet.md) | **The commands.** Four stations, and a step's number *is* the state the board has to be in (`A2.3` = stopped at `<RealTek>`), so front to back is a correct order to run it in. Per step: what to paste, the **verbatim** output to compare against, a stop condition, and the gotcha that bites there. Physical actions marked. `make ci` verifies every command still resolves (Traditional Chinese) |
| [`RUNBOOK.md`](RUNBOOK.md) | **Why each step exists**, and how it went wrong the first time. The reference behind the runsheet — it holds the reasoning, the runsheet holds the commands, and neither repeats the other (Traditional Chinese) |
| [`PROGRESS.md`](PROGRESS.md) | Gate status — the evidence behind every box above |
| [`notes/anatomy-n150rt.md`](notes/anatomy-n150rt.md) | How the firmware is built: container format, flash map, binaries, mitigations |
| [`notes/hardware-inspection.md`](notes/hardware-inspection.md) | **What the board actually is** — five ICs, the 4 MiB flash that W01 predicted, and a column of second sources that is still empty |
| [`notes/img/`](notes/img/) | Board photographs, the annotation spec they are rendered from, and what had to be painted out before they could be published |
| [`notes/uart-pinout.md`](notes/uart-pinout.md) | **The serial console** — pin-out with two sources per pin, baud measured from pulse width, why the console gives no shell, and the boot loader's command set |
| [`notes/uart-findings.md`](notes/uart-findings.md) | **The build nobody had** — a 2018 firmware that is neither analysed image, and what that costs the W03/W04 findings |
| [`notes/flash-layout.md`](notes/flash-layout.md) | **The flash map, read off the device** — W01's three predicted burn addresses, all three hit, plus where the config actually lives |
| [`notes/dump-vs-official.md`](notes/dump-vs-official.md) | **The 4 MiB dump against the two published images** — a five-year vendor remediation caught mid-step, and what four layers of verification do and do not prove |
| [`notes/prior-art.md`](notes/prior-art.md) | Who disclosed what, when — and which claims survive contact with these images |
| [`notes/cve-status.md`](notes/cve-status.md) | **Per-CVE, against the build this unit runs** — five located in its own binary, two refuted by it, and two published endpoint names that exist in no dispatch table |
| [`poc/`](poc/) | **The reproductions** — two public CVE chains with the requests, the flash-byte evidence, and one file that deliberately carries **no request at all** because what it describes has not been reported to anyone. `run.sh` runs against a device or against an emulated copy, and says which step failed |
| [`docs/report-draft.md`](docs/report-draft.md) | **The report that has not been sent** — what would go to TWCERT/CC, what is attached and what is not, and the one step that is blocking it |
| [`docs/disclosure.md`](docs/disclosure.md) | **The disclosure register** — what might be new, what state it is in, and the rule separating a finding from a reproduction from tradecraft. Two entries were **withdrawn** on 2026-08-17, one of them by prior art that a by-handler search found in a single query |
| [`test-ledger.md`](test-ledger.md) | **The test register, generated** — 135 tests with their predictions frozen before the first request, what would refute each, and what nine items were cut and why (Traditional Chinese) |
| [`notes/attack-surface.md`](notes/attack-surface.md) | Where to look, ranked |
| [`notes/ghidra-triage.md`](notes/ghidra-triage.md) | Which functions to open first, and why — with the three W01 calls W03 overturned |
| [`notes/dispatch-table.md`](notes/dispatch-table.md) | `root_form[]` recovered: every `/boafrm/` route in both builds, and what changed between them |
| [`notes/auth-flow.md`](notes/auth-flow.md) | **How Boa decides you are allowed in** — the substring gate, the IP-as-session model, the uninitialised credential compare |
| [`notes/sink-inventory.md`](notes/sink-inventory.md) | Every `system`/`strcpy`/`sprintf` call site, ranked — and how the first version of the census was wrong |
| [`notes/auth-flow-2020.md`](notes/auth-flow-2020.md) | **The 2020 rewrite** — what it fixed, what it kept, and the 401 that is never sent |
| [`notes/auth-flow-2018.md`](notes/auth-flow-2018.md) | **The gate on the build this unit runs** — a third answer, and the command handler that is only in this build |
| [`notes/three-way-read.md`](notes/three-way-read.md) | **2015, 2018, 2020 read across** — with the predictions committed before the tools ran, and the three that failed |
| [`notes/compcs-decode.md`](notes/compcs-decode.md) | **The configuration region decoded** — the format, `TELNET_ENABLED`, and a per-field disclosure table |
| [`notes/submit-url-overflow.md`](notes/submit-url-overflow.md) | **Four CVEs, one idiom, 34 handlers** — `lastUrl[100]` and the parameter you must not omit |
| [`notes/credentials.md`](notes/credentials.md) | **Where the credentials actually are** — the backdoor account W01 concluded could not exist, and two shipped private keys |
| [`notes/mib-and-config-dat.md`](notes/mib-and-config-dat.md) | The APMIB table recovered, and what `config.dat` is made of |
| [`notes/formSysCmd-analysis.md`](notes/formSysCmd-analysis.md) | The CVE endpoint that is not there, and why three pieces of evidence pointed the wrong way |
| [`notes/emulation-2018.md`](notes/emulation-2018.md) | **This unit's firmware running on an x86 host** — what was faked, whether each substitution distorts the result, and exactly where `boa` stops |
| [`notes/oracle-design.md`](notes/oracle-design.md) | **Five observation channels for a blind injection**, four of them rehearsed under emulation — including one that points at the bytes that changed in SPI flash |
| [`BENCH-LOG.md`](BENCH-LOG.md) | **What was actually run at the bench, session by session** — the plan written before touching anything, then verbatim record cards. Append-only (Traditional Chinese) |
| [`notes/w6cg-web-ui.md`](notes/w6cg-web-ui.md) | **The web UI the vendor actually shipped** — the page and the route are anti-correlated across three builds, and the 2015 fix was half a fix |
| [`notes/skt-analysis.md`](notes/skt-analysis.md) | The 2015 backdoor decoded: port, magic words, and the one `iptables` line it exists to run |
| [`reports/`](reports/) | Generated analysis: per-version reports, version diff, Ghidra string xrefs |
| [`tools/fwrecon/`](tools/fwrecon/) | The analysis tool written for this project |
| [`plan/`](plan/) | The ten week plans the gates above come from (Traditional Chinese) |
| [`LOG.md`](LOG.md) | Running log, including every wrong turn (Traditional Chinese) |
| [`study/QA.md`](study/QA.md) | Self-examination bank — for every claim in this repository, the question a reviewer trying to break it would ask, with collapsible answers (Traditional Chinese) |
| [`study/weekly-results.md`](study/weekly-results.md) | What each week actually produced, in the form it would be said out loud — every claim with its evidence, **and what that week did not prove** (Traditional Chinese) |

## Reproducing

**[`REPRODUCE.md`](REPRODUCE.md) first** — it says which of the claims above you
can verify with a clone alone, which need an N150RT of your own, and which are
not reproducible by anyone but the author. The commands themselves, one section
per step with its expected output and its stop conditions, are in
[`runsheet.md`](runsheet.md); the reasoning behind each is in
[`RUNBOOK.md`](RUNBOOK.md).

```bash
make doctor    # is this machine ready? every failure names the command that fixes it
make setup     # install the toolchain (Linux side)
make verify    # G0: every tool answers when called
make fetch     # download + hash-verify the firmware (not redistributed here)
make unpack    # carve and extract the root filesystems
make recon     # regenerate everything under reports/
make ci        # 199 checks — and 89 of them exist to prove the tools can refuse
make rtcase    # G3.75: the test register is frozen, every result carries evidence
make ledger    # regenerate test-ledger.md from the register
```

**If you have five minutes and no hardware**, run this one:

```bash
bash tools/test-loader-unpack.sh
```

Seven cases, no device and no downloads. It builds five deliberately broken
synthetic boot-loader images and checks the unpacker refuses each **for the right
reason**, then unpacks a good one as the positive control — because a tool that
always refuses and a tool that refuses correctly are indistinguishable in a suite
made only of refusals.

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
