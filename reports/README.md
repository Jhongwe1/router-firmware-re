# `reports/` — the regenerable evidence

Seventy-odd files, all generated, none hand-edited. **Every claim anywhere in
this repository is supposed to point at one of these**, and the naming is what
makes that usable:

```
<producer>-<build>[-<subject>].json
```

`<build>` is the one rule that matters. **`unit-2018` is this device's own
firmware, read off its flash; `2.1.2` and `3.4.0` are published images anyone
can download.** A finding named `-unit-2018` is a statement about this
hardware's software. A finding named `-2.1.2` is not, and was treated as one for
two weeks in W03 and W04 — which is what `writeup/05` is about.

## Every report names its own input, and CI enforces it

Each file carries the **SHA-256 of the binary it describes**.
[`../tools/check-reports.py`](../tools/check-reports.py) fails the build if one
does not, because W03 produced two reports that both said `program: boa` with
nothing to tell them apart. **A report that cannot name its own input is not
evidence.** Regenerate with `make recon`; the Ghidra ones need
`ghidra/analyze.ps1 -Binary`, and omitting `-Binary` is the failure that rule
exists for.

## By producer

| prefix | producer | what it holds |
|---|---|---|
| `n150rt-*` | [`fwrecon`](../tools/fwrecon/) | the structural read of a whole image: container, filesystem, ELF inventory, imports, mitigations. `.md` beside `.json` is the rendered version |
| `webbundle-*` | `fwrecon` | the `w6cg` web bundle, including from the image that downloaded incomplete |
| `ghidra-formtable-*` | `BoaFormTable.java` | `root_form[]` and `asp_page_variables` recovered by address, with every entry |
| `formtable-scan-six-builds` | [`formtable-scan.py`](../tools/formtable-scan.py) | **the six-build comparison** — the one that shows `formSysCmd` was removed per product, not on a date |
| `ghidra-sinks-*` | `BoaSinks.java` | the sink census. The 2015 run once returned **1** where it should have returned 589 |
| `ghidra-gate-*` | `BoaGate.java` | the static gate: request-parameter data reaching an unbounded sink, by rule. `findings_by_rule.R2` is the cell chapter 7 quotes |
| `ghidra-xref-*` | `BoaXref.java` | cross-references for one named symbol — the `-<subject>` suffix is the symbol |
| `ghidra-argtrace-*` | `BoaArgTrace.java` | argument provenance into a sink |
| `ghidra-mnemonics-*` | `BoaMnemonics.java` | instruction-level counts, including the `LWL`/`LWR`/`SWL`/`SWR` test that turned a spec-sheet guess into a measurement |
| `ghidra-strings-*` | `BoaStrings.java` | the string space, used as one of the continuity checks on the mirrored images |
| `mib-table-*` | [`mkcompds.py`](../tools/mkcompds.py) | the MIB field table per build |
| `compcs-*`, `compds-*` | `mkcompds.py` | the decoded configuration regions |
| `crash-triage-*` | [`crash-triage.py`](../tools/crash-triage.py) | what a fault actually was. `-cyclic` is the de Bruijn run that reads the frame off directly |
| `handler-sweep-*` | [`handler-sweep.py`](../tools/handler-sweep.py) | which handlers die. **`-alignfix` is the control**: the same sweep with qemu-user's missing unaligned-access fixup restored, which took "39 of 57 handlers are fragile" down to one |
| `paramfuzz-*` | [`paramfuzz.py`](../tools/paramfuzz.py) | the parameter-level version |
| `libbase-*` | [`libbase.py`](../tools/libbase.py) | where uClibc is mapped on this unit |
| `mipsref-*` | [`mipsref.py`](../tools/mipsref.py) | an instruction-level confirmation of a decompiler reading — **a warning from the decompiler costs it the last word** |
| `cve-endpoints-*` | [`cve-endpoints.py`](../tools/cve-endpoints.py) | does the endpoint an advisory names exist in this build's table |
| `flashdump-*`, `bootloader-*` | [`console-dump.py`](../tools/console-dump.py) | what was read off the chip, and from where |
| `config-diff-*` | [`config-diff.py`](../tools/config-diff.py) | which named fields changed between two flash reads — the nine bytes in [`../poc/03-flash-evidence.md`](../poc/03-flash-evidence.md) |
| `failopen-*` | [`failopen-probe.sh`](../tools/failopen-probe.sh) | the config-invalid → telnet-on path |
| `mkflash-*` | [`mkflash.py`](../tools/mkflash.py) | a built image, kept so the build is checkable |
| `diff-2.1.2-to-3.4.0.md` | `fwrecon` | the published-image diff |
| `bughunt.json` | [`bughunt.py`](../tools/bughunt.py) | the verdict register behind [`../notes/bughunt.md`](../notes/bughunt.md) |
| `test-results.json` | [`rtcase.py`](../tools/rtcase.py) | **every recorded test result with its artefacts.** The register itself is [`../test-cases.toml`](../test-cases.toml); this is what was measured against it |

## What is not here

The firmware images and this unit's flash dump. The vendor's images are not
redistributed; the dump contains this unit's MAC addresses, radio calibration
and administrator password. `make fetch` obtains the published ones and verifies
their hashes, and [`../REPRODUCE.md`](../REPRODUCE.md) says on its first page
which claims that leaves unverifiable by anyone but the author — rather than
letting a reader find out at step 40.
