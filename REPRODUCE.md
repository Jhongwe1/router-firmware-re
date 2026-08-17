# Reproducing this

**Start here if you cloned this repository and want to check something rather
than read about it.**

This page says which claims you can verify, with what, and — the part most
repositories leave out — **which ones you cannot verify at all, and why.**
The commands themselves are in [`runsheet.md`](runsheet.md), one section per
step, each with its expected output and its stop conditions.

---

## The honest version, in one table

| tier | what you need | what you can check | roughly |
|---|---|---|---|
| **T1** | this clone and an internet connection | the two **published** firmware images, every report derived from them, and **276 checks that prove this project's own instruments can fail** | 30 min, most of it downloads |
| **T2** | T1 **+ your own N150RT + a CP2102 serial adapter** (about US$3) | your unit's flash, its own boot loader, its own `boa`, the emulator — the same *procedures*, on *your* bytes | an afternoon |
| **T3** | T2 **+ a USB Ethernet adapter + a segment you are willing to isolate** | the network behaviour: the authorisation gate, the endpoint census, the timing | a second afternoon |
| **T-none** | — | **the specific byte-level results this repository reports** | not reproducible by anyone but the author, and the reason is below |

### Why T-none exists, and why saying so is the point

This unit runs `TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002`. **That build is on no
vendor download page** — its *version* is published, the *build* is not, and the
published V2.1.6 is a different build eighteen months earlier. So:

- **You cannot download the firmware this repository's headline findings are
  about.** They were read out of this unit's flash.
- **The flash image is not redistributable and would not help you if it were.**
  The region at `0x006000` (`H601`) holds this unit's MAC addresses and its radio
  calibration constants. They exist nowhere else, no factory reset restores them,
  and publishing them identifies one physical device.
- So a byte-for-byte match against, say, `sha256 e09cbf84…` for
  `GET /config.dat` is **not** something you can obtain. What you can obtain is
  the same result *on your unit*, with the same tools, and compare the shapes.

Two other builds — **V2.1.2 (2015)** and **V3.4.0 (2020)** — *are* downloadable,
and every claim about those is T1. The repository always names which binary a
claim was measured on, which is what makes this split possible at all.

---

## T1 — a clone and an internet connection

### What it verifies

- Every report under [`reports/`](reports/) that comes from a downloadable image:
  the string tables, the `/boafrm/` dispatch tables, the sink inventories and the
  argument traces for **V2.1.2 and V3.4.0**.
- The container format this project reverse-engineered from two files, including
  the `w6cg` web bundle walk that has **no checksum and no entry count** — so
  "the strides consumed the archive exactly" is the only evidence the layout was
  read correctly.
- The test register: 130 tests, their predictions, their refutation conditions,
  and the two hashes that make an edit to either show up in a diff.
- **And the thing actually worth your time:** that this project's instruments
  refuse what they claim to refuse.

### The commands

[`runsheet.md` `A1.2`](runsheet.md). In short:

```bash
make doctor TIER=1     # every prerequisite, each failure naming its own fix
make setup             # the Linux-side toolchain
make fetch             # the two published images, hash-verified
make unpack            # carve and extract
make recon             # every report a downloadable image supports
make ci                # ← the 276 checks
```

### Running the firmware, with no device — G4 clause 3a

Added 2026-08-18. This is the part of the attack chain a stranger can execute,
and it needs nothing but the download:

```bash
sudo tools/qemu-env.sh --profile v2.1.2 mkflash   # rebuild the flash from the container
sudo tools/qemu-env.sh --profile v2.1.2 build     # unpack the rootfs, populate /var
sudo tools/qemu-env.sh --profile v2.1.2 serve 8081
```

`serve` refuses to report the server up unless an exempt page returns 200 **and**
a gated page returns 302, so "it started" is never confused with "it is behaving
like the firmware". Then the published CVE-2025-3987 injection, unauthenticated,
against your own local process — the full write-up with its controls is
[`poc/05-l2-published-image.md`](poc/05-l2-published-image.md).

Two things to expect, because neither is obvious:

- **The flash image has a pinned sha256.** `mkflash` compares against it. A
  different hash means you have a different container, not a different mood.
- **The first 64 KiB of that image is not in the download** and never can be.
  Boot loader, `H601`, `COMPDS` and `COMPCS` are written at manufacture. Three
  regions are synthesised with zeroed payloads;
  [`reports/mkflash-2.1.2.json`](reports/mkflash-2.1.2.json) names every byte
  range and its origin. **So every setting in this environment is zero** — no
  address, no SSID, no password — and nothing about shipped defaults can be
  concluded from it.

### Why `make ci` is the interesting one

Most of a reverse-engineering repository is assertions. This part is not:

| suite | cases | what it proves |
|---|---|---|
| `tools/test-rtcase.sh` | 34 | the register gate can fail: a prediction edited after a result, a week moved without a reason, **a reschedule reason rewritten after its hash was declared**, a result with no refutation condition, an artefact that does not exist, a static reading rendered as a dynamic tick |
| `tools/test-check-benchlog.sh` | 13 | the bench-log checker can fail, **and that it sees every card there is** — its first version took one fenced block to be one card and reported "19 record cards, every one with a refutation check" about a file holding thirty |
| `tools/test-console-write.sh` | 28 | the flash **writer** refuses every range it must never touch — the boot loader the recovery path runs on, and the block holding this unit's MACs and radio calibration — plus a wrong hash, a short file, a misaligned sector, a blank payload, and a dry run that would print the bytes it promised to withhold |
| `tools/test-bench-probe.sh` | 15 | the network prober refuses a POST that would crash the web server, refuses shell metacharacters, refuses thirteen handlers by name, and **writes its transcript even when the run stops** |
| `tools/test-console-dump.sh` | 18 | the flash reader parses a real console transcript, ignores the ASCII column that looks like more hex, and cannot emit the one boot-loader command that would be dangerous |
| `tools/test-loader-unpack.sh` | 7 | the boot-loader unpacker refuses an image with no stream, with two streams, with a truncated stream, and one that decompresses to the wrong thing — plus a positive control |
| `tools/test-qemu-env.sh` | 5 | the emulator's positive control can fail |
| `tools/test-check-runsheet.sh` | 29 | the runsheet checker can fail: a flag no tool accepts, a step under the wrong station, an index disagreeing with a heading, **and a command fence in the section that is not allowed to hold one** |
| `tools/test-flash-tools.sh`, `tools/test-photo-tools.sh` | 4 + 13 | the hardware-side helpers, and photo redaction |
| `tools/fwrecon` pytest | 110 | the parsers |

**166 guard cases across ten suites, plus 110 parser tests, and `make ci` now
runs all of them** — 276 checks from a clone, with no device.

Until 2026-08-17 it ran 89 of 124: `test-console-dump.sh` (18),
`test-photo-tools.sh` (13) and `test-flash-tools.sh` (4) were in no CI list at
all. None of them needs hardware, so that was a gap rather than a constraint —
and the largest of the three guards the flash parser, which is the code path
every byte of this unit's dump came through. **It was found by recounting the
totals, not by anything checking.** Each suite still runs on its own:

```bash
bash tools/test-console-write.sh
bash tools/test-console-dump.sh
```

Every one of those cases exists because **a check that cannot fail is a
decoration that reports success**, and this project shipped one of those once
(`PROGRESS.md`, instrument bug 12). Run any suite on its own and read its
header: each says which real failure it was written after.

### What T1 cannot tell you

Nothing in T1 touches the 2018 build. Every `boa` claim it can verify is about
V2.1.2 or V3.4.0 — **two binaries this device has never run.** That distinction
is the whole reason gate G3.5 exists.

That now cuts sharper than it used to. The emulated environment above runs a
real command injection, and it is **not** the chain this project's headline
result is about: `formSysCmd` (CVE-2024-51228) is in the 2018 build's dispatch
table and in *neither* downloadable image, so that chain cannot be reproduced by
anyone who does not own one of these units. T1 gets you the *class* of defect on
firmware you can obtain. It cannot get you this device.

`flash default`, the vendor's own configuration generator, also **will not run**
here — it dies on an unaligned store the device's MIPS kernel fixes in its trap
handler and `qemu-user` does not. If you are wondering why emulating Realtek SDK
firmware from a download so often "almost" works, that is the reason, and it is
measured rather than folklore.

---

## T2 — your own N150RT and a serial adapter

### What you need

| | |
|---|---|
| a TOTOLINK N150RT | any hardware revision; yours will run a different build, and that is fine — the *procedures* transfer, the *bytes* will not |
| a CP2102 (or CH340) USB-serial adapter, 3.3 V | about US$3. **Do not connect its VCC** |
| access to the four-pin UART header | pin 1 is the silkscreen triangle; you need pins 2, 3 and 4 |
| `usbipd-win`, if you are on Windows with WSL | so the adapter reaches the Linux side |

**No soldering.** The flash is read through the boot loader's own `FLR` command
over the serial console — no SOIC-8 clip, no desoldering, and nothing written.

### What it verifies

- Your unit's flash, read twice, and the two reads compared. **Two agreeing
  reads is what makes it a backup rather than one file twice** — and that is the
  precondition for everything in T3 that writes.
- Your unit's flash map, checked against what the container format predicted.
- Your boot loader's second stage: `0x0012F0` is an LZMA stream, and **none of
  the strings the `<RealTek>` prompt prints exist as plaintext in the raw
  4 MiB**. `tools/loader-unpack.py` recovers them and refuses to produce a report
  unless it also finds all seventeen commands the console itself prints.
- Your unit's configuration, decoded, with `libapmib`'s **own** checksum passing.
- The emulator: your unit's `boa`, running on an x86 host, with a copy of your
  own flash standing in for `/dev/mtdblock0`.

### The commands

[`runsheet.md`](runsheet.md) `A1.1` → `A1.3` → `A1.4` → then 第 2 站 in order
(`A2.1` → `A2.3`), plus:

```bash
make doctor TIER=2
make recon-unit        # reports for the build YOUR unit runs
make loader-report     # the boot loader's LZMA stage 2
make qemu-env          # the emulator (needs root)
make qemu-test
```

> **`A2.5` is the only irreversible section in the whole document**, and it will
> not let you start without two agreeing dumps. Read it in full before running
> any of it.

---

## T3 — the device on an isolated segment

### Read this before you plug anything in

Everything in T3 sends packets to a router. Three rules, and the second is the
one people skip:

1. **Nothing on the WAN port.** Not a cable, not an uplink.
2. **The USB Ethernet adapter must be handed to the Linux side, not left on the
   host.** If it stays on the host, the host takes a DHCP lease from the device
   and may route through it; `ping` will still succeed and the only tell is
   `ttl=63`. In that state isolation cannot be verified, multicast does not
   work at all, and two source addresses collapse into one. `runsheet.md` `A3.1`
   proves the route is direct from the routing table instead of trusting a reply.
3. **It is your own device, on a segment with nothing else on it.** `A3.3` verifies
   that by counting MAC addresses in a capture — and it manufactures known
   traffic first, because *zero packets captured is not evidence of a quiet
   segment* until the link is known to deliver.

### What it verifies

- The authorisation gate's actual reach: which pages are served without
  credentials, and why. On this unit that is **seven of the seventy-six shipped
  `.htm` pages**, and two of the seven are exempt only because another page's
  name is a substring of theirs.
- The `/boafrm/` endpoint census, and what it costs: **an unauthenticated POST
  with no parameters at all occupies the single-process web server for seconds.**
- Boot-to-serviceable timing, and the gap between the web server announcing
  itself and answering.
- The boot loader's rescue path, without uploading anything.

### The commands

**[`runsheet.md`](runsheet.md) 第 3 站, front to back** — `A3.1` → `A3.8`. The
station numbering is the point: the leading digit is the state the board has to
be in, so reading the station in order *is* a correct order to run it in.

```bash
make doctor TIER=3
```

> 🔴 **`A3.8` changes your device's configuration, and on this build it also
> rewrites the factory-default region.** That is a finding, not a warning about
> clumsiness: a write that reaches `COMPDS` means "restore factory defaults"
> would restore whatever was last written. Take the `A2.3` snapshot first, both
> before and after, and attribute the difference with
> `bash tools/config-attrib.sh <before> <after>`.

---

## If you only have five minutes

```bash
bash tools/test-loader-unpack.sh
```

Seven cases, no device, no firmware, no downloads. It builds five deliberately
broken synthetic boot-loader images and checks that the unpacker refuses each
one **for the right reason**, then unpacks a well-formed one as the positive
control.

That last case is the point. **A tool that always refuses and a tool that
refuses correctly are indistinguishable in a suite made only of refusals** — and
the headline result that unpacker produces is an *absence* (the boot loader
contains no way to pass a kernel command line), which is worth nothing unless
the same scan is shown, in the same run, to find seventeen things that are there.

---

## Where each kind of thing lives

| you want | read |
|---|---|
| the exact commands, with expected output | [`runsheet.md`](runsheet.md) |
| why a step exists, and what went wrong the first time | [`RUNBOOK.md`](RUNBOOK.md) |
| what this project claims, and what would refute each claim | [`test-ledger.md`](test-ledger.md) |
| what actually happened on a given day, verbatim | [`BENCH-LOG.md`](BENCH-LOG.md) |
| the gates, the weeks, and the open questions | [`PROGRESS.md`](PROGRESS.md) |
| what is published and what is held back | [`docs/disclosure.md`](docs/disclosure.md) |
| hostile questions and the answers | [`study/QA.md`](study/QA.md) |
| what each week did **not** prove | [`study/weekly-results.md`](study/weekly-results.md) |

## Scope

This studies a device the author owns, on an isolated segment, to trace
**already-publicly-disclosed** vulnerabilities to the responsible function.
Findings and their addresses are published; reproductions follow the state in
[`docs/disclosure.md`](docs/disclosure.md); post-exploitation tradecraft is not
published at all, and the nine items cut for that reason are listed with their
reasons in [`test-ledger.md`](test-ledger.md).

**Do not point any of this at hardware that is not yours.**
