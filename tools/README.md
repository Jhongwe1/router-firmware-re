# `tools/` — what each one answers, and which finding it produced

Forty-seven scripts and four packages. They are flat on purpose: every one is
invoked by name from [`../journal/runsheet.md`](../journal/runsheet.md) or from
the `Makefile`, and a directory move would break a document that gets typed at a
bench with a device powered on. **This index is the structure**; the filesystem
is an invocation surface.

Two rules run through all of them:

1. **A tool that cannot fail proves nothing.** Every instrument here that makes
   a judgement has a `test-*.sh` beside it whose cases exist to feed it bad
   input and require it to refuse. That is 496 of the 626 checks `make ci` runs.
2. **A tool reporting `0` is making a claim.** Several of the sixty instrument
   bugs in [`../writeup/12-instruments.md`](../writeup/12-instruments.md) were
   tools reporting nothing found, correctly formatted, for weeks.

## Analysis — the things that produced findings

| tool | the question it answers | where the answer went |
|---|---|---|
| [`fwrecon/`](fwrecon/) | a zero-dependency firmware CLI: containers, SquashFS, ELF, imports, mitigations. 130 parser tests | [`../notes/anatomy-n150rt.md`](../notes/anatomy-n150rt.md) |
| [`formtable-scan.py`](formtable-scan.py) | where is `root_form[]`, and what is in it, across six builds | [`../notes/dispatch-table.md`](../notes/dispatch-table.md) · [`../writeup/07-across.md`](../writeup/07-across.md) |
| [`cve-endpoints.py`](cve-endpoints.py) | does the endpoint a published advisory names exist in this build's table | [`../notes/cve-status.md`](../notes/cve-status.md) |
| [`handler-sweep.py`](handler-sweep.py) | which handlers die, and on what input | [`../notes/absent-parameter-strcpy.md`](../notes/absent-parameter-strcpy.md) |
| [`paramfuzz.py`](paramfuzz.py) | the parameter-level sweep behind that | same |
| [`crash-triage.py`](crash-triage.py) | is a crash a controlled `$pc` or a store to a read-only literal | [`../notes/mips-ret2libc.md`](../notes/mips-ret2libc.md) |
| [`libbase.py`](libbase.py) | where is uClibc mapped, derived from two kernel fault lines | same |
| [`mipsref.py`](mipsref.py) | MIPS-I instruction reference used to confirm decompiler output at instruction level | throughout |
| [`bughunt.py`](bughunt.py) | the verdict register behind the systematic hunt | [`../notes/bughunt.md`](../notes/bughunt.md) |
| [`config-diff.py`](config-diff.py) | which named configuration fields changed between two flash reads | [`../poc/03-flash-evidence.md`](../poc/03-flash-evidence.md) |
| [`mkcompds.py`](mkcompds.py) | build and decode the vendor's compressed MIB format | [`../notes/compcs-decode.md`](../notes/compcs-decode.md) |
| [`alignfix/`](alignfix/) | an `LD_PRELOAD` shim that removes qemu-user's missing MIPS unaligned-access fixup — 39 of 57 handlers "dying" was the emulator | [`../notes/emulation-2018.md`](../notes/emulation-2018.md) |
| [`upnp-soap.py`](upnp-soap.py) | the `miniigd` request that terminates the daemon, with its control | [`../notes/three-unread-binaries.md`](../notes/three-unread-binaries.md) |

## The bench — anything that touches the device

Every one of these is invoked from a numbered station in
[`../journal/runsheet.md`](../journal/runsheet.md), where the station number
**is** the state the device has to be in.

| tool | what it does |
|---|---|
| [`bench-doctor.sh`](bench-doctor.sh) | first command of any session: are the prerequisites met, and which command fixes each failure |
| [`device-liveness.py`](device-liveness.py) | can the device still route — asked before a session, because one of this project's own POSTs once left it unable to for two days |
| [`bench-probe.py`](bench-probe.py) | the HTTP probe, with the refusals that stop a crash being reported as an injection |
| [`console-dump.py`](console-dump.py) | read flash through the boot loader's own `FLR`/`DB`, with the redaction rule |
| [`console-write.py`](console-write.py) | write flash, with an allow-list that refuses every range it must refuse |
| [`console-lint.py`](console-lint.py) | read a console log the way the dispatcher reads it, and **account for every `Unknown command !` or report it unexplained** |
| [`flash-read.sh`](flash-read.sh) · [`flash-write.sh`](flash-write.sh) | the SPI-clip path, which measured 1.70 V on a 3.3 V part and read nothing |
| [`loader-tftp.py`](loader-tftp.py) | the loader's TFTP client, and the upload it must refuse |
| [`mkramboot.py`](mkramboot.py) | **hand-assembled position-independent MIPS-I payload**, UART address disassembled out of the loader's own `putchar`, every word verified by a built-in simulator before it is written, built for two load addresses to prove it is really PIC |
| [`mkflash.py`](mkflash.py) · [`mkhwsetting.py`](mkhwsetting.py) | build the flash images those paths consume |
| [`failopen-probe.sh`](failopen-probe.sh) | the config-invalid → telnet-on path |
| [`rogue-dhcp.py`](rogue-dhcp.py) · [`session-window.sh`](session-window.sh) · [`coldboot-timing.sh`](coldboot-timing.sh) | the three behavioural measurements that need a second host |
| [`ioc-precheck.sh`](ioc-precheck.sh) | what must be true before the device is touched at all |

## The register and the documents

These are the instruments pointed at **this repository** rather than at the
router. They exist because a claim that two documents agree is a claim, and this
project has been wrong about it.

| tool | what it refuses |
|---|---|
| [`rtcase.py`](rtcase.py) | a result with no pre-written refutation condition; an edited prediction after a result; a dynamic tick for a static reading; a rescheduled week with no reason |
| [`check-reports.py`](check-reports.py) | a Ghidra or `fwrecon` report that does not name the SHA-256 of the binary it describes |
| [`check-runsheet.py`](check-runsheet.py) | a command that no longer resolves, a flag absent from the tool's own `--help`, a `§8.x.y` that does not exist, an untagged fence, **and a `§8.12` section carrying a command block** |
| [`check-benchlog.py`](check-benchlog.py) | a record card with no verdict or no refutation check, and a `PROGRESS.md` session with no bench-log entry on the same date |
| [`check-ci-parity.py`](check-ci-parity.py) | `make ci` and the workflow running different sets of scripts |
| [`check-links.py`](check-links.py) | a relative link to a file **git does not track** — the `plan/` 404 was a directory that exists on disk |
| [`check-numbers.py`](check-numbers.py) | a front-door number that disagrees with the generator that owns it, **and a claim site that has stopped matching** |
| [`check-expired.py`](check-expired.py) | a published sentence that was true until a dated event and is asserted in the present tense after it |
| [`extract-gates.py`](extract-gates.py) | `docs/gates.md` drifting from the private week plans it was lifted from |
| [`count-checks.sh`](count-checks.sh) | nothing — it re-derives the total and states its counting rule, so that the number on the front door is one anybody can recompute |

## Fetching, unpacking, environment

[`fetch-firmware.sh`](fetch-firmware.sh) (declared hashes, never redistributed) ·
[`unpack-firmware.sh`](unpack-firmware.sh) ·
[`loader-unpack.py`](loader-unpack.py) ·
[`zipprefix.py`](zipprefix.py) (the partially-downloaded image whose web bundle is
still byte-complete) ·
[`qemu-env.sh`](qemu-env.sh) ·
[`config-attrib.sh`](config-attrib.sh) ·
[`setup/`](setup/) ·
[`lib/`](lib/) ·
[`redact-photo.py`](redact-photo.py) and [`annotate-photo.py`](annotate-photo.py)
(EXIF and GPS stripped before a board photograph is published; the annotations
are a committed spec, not a drawing).

## The guard suites

Twenty-three `test-*.sh`, one per instrument that makes a judgement. They are
the reason the check total is worth quoting: **they are not tests that the tool
works, they are tests that it refuses.** `make count-checks` prints the
per-suite table and states what it counts and what it does not.

Run one with no device and no downloads:

```bash
bash tools/test-loader-unpack.sh
```
