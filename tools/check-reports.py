#!/usr/bin/env python3
"""Validate the committed reports against the current tooling.

The reports are committed so a reader without the (non-redistributable)
firmware can still see the findings. That only works if they stay in step with
the code that produced them, and the usual way to break that is to change a
report's shape and forget to regenerate.

CI cannot regenerate them — no firmware on a runner — so it checks what it can:

  * every JSON under reports/ parses;
  * every file is recognisably the output of one of the two producers;
  * fwrecon reports carry the schema version the current source emits.

Several producers write into reports/, on purpose:

  fwrecon        `fwrecon report`      -> carries "schema_version"
  fwrecon        `fwrecon mib`         -> carries "producer": "fwrecon:mib"
  Ghidra scripts BoaFormTable, BoaSinks, BoaDecompile, BoaXref, BoaArgTrace
                                       -> carry "producer": "ghidra:<Script>"
  Ghidra script  BoaStringXrefs.java   -> carries "program" and "matches"
                                          (W01, predates the "producer" field)
  tools/loader-unpack.py               -> carries "producer": "loader-unpack"
                                          (the boot loader's LZMA second stage,
                                           unpacked from a flash dump. Its
                                           checks are all about the positive
                                           control, because the report is mostly
                                           a claim about what is *absent*)
  tools/failopen-probe.sh              -> carries "producer": "failopen-probe"
                                          (what /bin/startup.sh does when the
                                           settings regions are damaged. Every
                                           check here is about a control: the
                                           probe's first working run reported
                                           seven states in which nothing
                                           happened, because the boot script was
                                           being handed to qemu-user as if it
                                           were an ELF and had never executed)
  tools/rtcase.py `rtcase record`      -> carries "producer": "rtcase"
                                          (shape only here; admissibility is
                                           `rtcase check`, which needs the
                                           register)
  tools/mkflash.py                     -> carries "producer": "mkflash"
  tools/crash-triage.py                -> carries "producer": "crash-triage"
  tools/paramfuzz.py                   -> carries "producer": "paramfuzz"
  tools/formtable-scan.py              -> carries "producer": "formtable-scan"
  tools/config-diff.py                 -> carries "producer": "config-diff"
                                          (a provenance map for a rebuilt flash
                                           image. The check that matters is that
                                           every *overlay* names an origin: an
                                           overlay is by definition a range the
                                           published image does not supply, and
                                           an unnamed one is indistinguishable
                                           from a byte lifted off a physical
                                           unit — which would silently void the
                                           whole "anyone can rebuild this" claim
                                           G4 clause 3a rests on)

An unrecognised file is an error rather than something to skip. A stray or
half-written report in a directory that is presented as the project's results
is exactly the thing worth failing on.

Every Ghidra report is additionally required to carry a non-empty
"source_sha256". W01 shipped two reports both saying `"program": "boa"` with
nothing to say which firmware image each came from — they were correct, but
only their filenames claimed so. A report that cannot name its own input is not
evidence, so that is now a hard failure.

Usage:  python tools/check-reports.py [reports-dir]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REPORT_SRC = REPO / "tools/fwrecon/src/fwrecon/report.py"


def current_schema_version() -> str:
    m = re.search(r'SCHEMA_VERSION = "([^"]+)"', REPORT_SRC.read_text("utf-8"))
    if not m:
        raise SystemExit(f"could not find SCHEMA_VERSION in {REPORT_SRC}")
    return m.group(1)


def main(argv: list[str]) -> int:
    reports_dir = Path(argv[1]) if len(argv) > 1 else REPO / "reports"
    expected = current_schema_version()

    files = sorted(reports_dir.glob("*.json"))
    if not files:
        print(f"no JSON reports found under {reports_dir}", file=sys.stderr)
        return 1

    errors: list[str] = []
    counts = {"fwrecon": 0, "ghidra": 0, "rtcase": 0, "mkflash": 0, "emulation": 0}

    for path in files:
        try:
            doc = json.loads(path.read_text("utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path.name}: invalid JSON ({exc})")
            continue

        # Must come before the schema_version branch: the rtcase results file
        # carries one of its own, and would otherwise be checked against
        # fwrecon's.
        if str(doc.get("producer", "")) == "rtcase":
            counts["rtcase"] += 1
            # Shape only. Whether the results are *admissible* — a refutation
            # written before the result, an artefact that exists, a prediction
            # that has not been edited since — is `tools/rtcase.py check`, which
            # needs the register and runs as its own CI step.
            if not doc.get("register"):
                errors.append(
                    f"{path.name}: no register - the results cannot name the test "
                    "register they were recorded against")
            if not isinstance(doc.get("results"), list):
                errors.append(f"{path.name}: results is not a list")
            for i, res in enumerate(doc.get("results", [])):
                for field in ("id", "date", "verdict", "evidence_kind", "case_freeze_sha256"):
                    if not res.get(field):
                        errors.append(f"{path.name}: results[{i}] missing {field!r}")

        # Provenance reports from tools/mkflash.py. Checked here rather than
        # exempted, because the single load-bearing claim of the L2 environment
        # is "every byte in this image came from a download, or is named". An
        # overlay is a byte range that did *not* come from the download, so an
        # overlay without an origin is exactly the failure this file must catch:
        # the image would still build, still boot, and quietly depend on
        # something a stranger cannot obtain.
        elif str(doc.get("producer", "")) == "mkflash":
            counts["mkflash"] += 1
            for field in ("container", "container_sha256", "flash_size", "ranges", "gaps"):
                if doc.get(field) in (None, "", []):
                    errors.append(f"{path.name}: missing required field {field!r}")
            ranges = doc.get("ranges") or []
            for i, rng in enumerate(ranges):
                prov = rng.get("provenance")
                if prov not in ("published-image", "overlay"):
                    errors.append(
                        f"{path.name}: ranges[{i}] provenance is {prov!r}, must be "
                        f"'published-image' or 'overlay'")
                if not rng.get("sha256"):
                    errors.append(f"{path.name}: ranges[{i}] has no sha256")
                if prov == "overlay" and not str(rng.get("origin", "")).strip():
                    errors.append(
                        f"{path.name}: ranges[{i}] at {rng.get('flash_offset_hex')} is an "
                        f"overlay with no origin. An overlay is the part of the image "
                        f"that is NOT in the download; unnamed, it is indistinguishable "
                        f"from something lifted off a physical unit")
            covered, blank = doc.get("covered_bytes"), doc.get("blank_bytes")
            size = doc.get("flash_size")
            if None not in (covered, blank, size) and covered + blank != size:
                errors.append(
                    f"{path.name}: covered {covered} + blank {blank} != flash_size "
                    f"{size}, so the provenance map does not account for every byte")

        # Dynamic sweeps from tools/handler-sweep.py and the static work list
        # from tools/bughunt.py. Both are emulation-side, and the thing worth
        # failing on is the same for both: a result set with no working controls
        # is indistinguishable from a result set where everything behaved the
        # same way. handler-sweep in particular spent three runs producing
        # confident nonsense because its controls could not tell "my server" from
        # "somebody's server".
        elif str(doc.get("producer", "")) in ("handler-sweep", "bughunt"):
            counts["emulation"] += 1
            if doc["producer"] == "handler-sweep":
                for field in ("profile", "died_under_emulation", "survived",
                              "controls", "caveat"):
                    if doc.get(field) in (None, ""):
                        errors.append(f"{path.name}: missing required field {field!r}")
                # `body` is checked for PRESENCE, not for truthiness. An empty
                # body is not a missing field here -- it is the measurement:
                # the 2026-08-18 sweep that found the five handlers dying on an
                # absent parameter sent exactly that, and an emptiness test
                # rejected its own report.
                if "body" not in doc:
                    errors.append(f"{path.name}: missing required field 'body'")
                if doc.get("control_problems"):
                    errors.append(
                        f"{path.name}: recorded with {len(doc['control_problems'])} failed "
                        f"control(s) — {doc['control_problems'][0]}")
                if not doc.get("survived"):
                    errors.append(
                        f"{path.name}: nothing survived, so the sweep measured the "
                        f"emulator rather than the firmware")
            else:
                for field in ("known_cve", "builds", "islands", "self_check"):
                    if doc.get(field) in (None, "", {}):
                        errors.append(f"{path.name}: missing required field {field!r}")
                sc = doc.get("self_check", {})
                if not sc.get("gate_findings_joined_to_a_dispatch_entry"):
                    errors.append(
                        f"{path.name}: no gate finding joined to a dispatch entry, so the "
                        f"two reports disagree about addresses and every cross-reference "
                        f"in this file is meaningless")

        # tools/failopen-probe.sh. Same failure mode as handler-sweep and worse:
        # this probe damages the flash image and then asks the vendor's own boot
        # script what it does about it, so *every* interesting reading is a
        # difference from the control. If the controls did not run, a table
        # showing "nothing happened in any state" is exactly what a probe that
        # never executed the boot script produces - and that is not a
        # hypothetical, it is what the first working run of this tool committed
        # to the screen.
        elif str(doc.get("producer", "")) == "failopen-probe":
            counts["emulation"] += 1
            for field in ("profile", "source_sha256", "case", "caveat", "measurements"):
                if doc.get(field) in (None, "", [], {}):
                    errors.append(f"{path.name}: missing required field {field!r}")
            ctl = doc.get("controls") or {}
            for name in ("shell_runs", "plain_write_takes",
                         "healthy_image_passes_both_tests_and_telnet_off"):
                if ctl.get(name) != "pass":
                    errors.append(
                        f"{path.name}: control {name!r} is {ctl.get(name)!r}, not 'pass' - "
                        f"without it every row in this table could equally be a probe that "
                        f"never ran")
            # The whole point is a state that differs from the control. A run in
            # which the boot script took no branch anywhere measured nothing.
            branched = [m for m in doc.get("measurements", [])
                        if m.get("branch_message", "").strip()
                        and "no branch message" not in m.get("branch_message", "")]
            if not branched:
                errors.append(
                    f"{path.name}: no damage state made the boot script take any branch, "
                    f"so this run measured the harness rather than the firmware")

        # tools/crash-triage.py, tools/paramfuzz.py, tools/formtable-scan.py --
        # all three added 2026-08-18, and all three fail the same way if they
        # fail at all: they produce a confident table with no controls behind
        # it. That is not hypothetical for any of them. `paramfuzz` reported a
        # clean path dictionary whose GETs were all following the gate's own
        # redirect; `crash-triage` reported five faults with `pc` = 0 because
        # `pc` was not in its register list; `formtable-scan` would return an
        # empty answer for a wrong stride, which looks exactly like a binary
        # with no dispatch table. So the control is what is checked here, not
        # the finding.
        elif str(doc.get("producer", "")) == "crash-triage":
            counts["emulation"] += 1
            if not doc.get("controls"):
                errors.append(
                    f"{path.name}: no control case. A harness that reports a "
                    "signal for every case looks exactly like a run in which "
                    "everything crashed")
            if doc.get("control_problems"):
                errors.append(
                    f"{path.name}: recorded with {len(doc['control_problems'])} "
                    f"failed control(s) - {doc['control_problems'][0]}")
            for c in doc.get("controls", []):
                if c.get("signal"):
                    errors.append(
                        f"{path.name}: control {c.get('handler')!r} faulted with "
                        f"{c['signal']} and the file was committed anyway")
            for c in doc.get("cases", []):
                if c.get("signal") and c.get("pc") in (None, "0x00000000"):
                    errors.append(
                        f"{path.name}: case {c.get('handler')!r} carries a signal "
                        "with pc = 0, which is a wrong number rather than a "
                        "missing one - the register dump did not contain pc")
            if not doc.get("program_headers"):
                errors.append(
                    f"{path.name}: no program headers, so no store target can be "
                    "classified and 'SIGSEGV' is all this file says")

        # config-diff answers P8-23 by comparing two paths that are easy to
        # make agree by accident. A committed file that still carries a
        # disagreement is the failure this check exists for -- and so is one
        # whose flash diff was never classified against the region, because
        # the compressed-payload offsets and the decoded field offsets are two
        # coordinate systems and the first version of that comparison put them
        # side by side as though they were one.
        elif str(doc.get("producer", "")) == "config-diff":
            counts["emulation"] += 1
            if doc.get("problems"):
                errors.append(
                    f"{path.name}: recorded with {len(doc['problems'])} "
                    f"disagreement(s) - {doc['problems'][0]}")
            if not doc.get("decoded_diff"):
                errors.append(
                    f"{path.name}: no decoded field changed, so this file says "
                    "nothing about whether the two paths agree")
            if not doc.get("flash_diff"):
                errors.append(
                    f"{path.name}: no flash bytes changed, so there was no "
                    "write to compare a decode against")
            for d in doc.get("flash_diff", []):
                if not d.get("where"):
                    errors.append(
                        f"{path.name}: a changed byte at {d.get('offset')} is "
                        "not placed relative to the region, so nothing stops a "
                        "reader comparing it to a decoded field offset")
                    break
            for field in ("mib", "value_before", "value_after", "region_offset"):
                if doc.get(field) in (None, ""):
                    errors.append(
                        f"{path.name}: missing required field {field!r}")

        elif str(doc.get("producer", "")) == "paramfuzz":
            counts["emulation"] += 1
            if doc.get("control_problems"):
                errors.append(
                    f"{path.name}: recorded with {len(doc['control_problems'])} "
                    f"failed control(s) - {doc['control_problems'][0]}")
            ctl = doc.get("controls") or {}
            if ctl.get("negative", {}).get("survived") is not False:
                errors.append(
                    f"{path.name}: the negative control survived. If the one "
                    "handler+body measured to remove the server is not detected "
                    "here, nothing this round reports as 'survived' means "
                    "anything")
            if ctl.get("positive", {}).get("survived") is not True:
                errors.append(
                    f"{path.name}: the positive control died, so the environment "
                    "is what was measured and not the handlers")
            for entry in doc.get("path_dictionary", []):
                if entry.get("row") == "CONTROL":
                    break
            else:
                if "path_dictionary" in doc:
                    errors.append(
                        f"{path.name}: the path dictionary has no CONTROL row. "
                        "Sixteen entries agreeing with each other says nothing "
                        "without one name nobody could have implemented")

        elif str(doc.get("producer", "")) == "formtable-scan":
            counts["ghidra"] += 1
            for b in doc.get("binaries", []):
                if b.get("control_missing"):
                    errors.append(
                        f"{path.name}: {b.get('binary')} never yielded "
                        f"{b['control_missing']} - a scan that returns a clean "
                        "empty answer for a wrong stride is indistinguishable "
                        "from a binary with no dispatch table")
                if not b.get("runs"):
                    errors.append(
                        f"{path.name}: {b.get('binary')} produced no runs at all")

        elif "schema_version" in doc:
            counts["fwrecon"] += 1
            got = doc["schema_version"]
            if got != expected:
                errors.append(
                    f"{path.name}: fwrecon schema {got!r}, current source emits "
                    f"{expected!r} — regenerate with `make recon`")
            for field in ("label", "generated_at_utc"):
                if field not in doc:
                    errors.append(f"{path.name}: missing required field {field!r}")

        elif str(doc.get("producer", "")) == "fwrecon:mib":
            counts["fwrecon"] += 1
            if not doc.get("source_sha256"):
                errors.append(
                    f"{path.name}: no source_sha256 - the report cannot name the "
                    "library it describes")
            if doc.get("verdict") != "consistent":
                errors.append(
                    f"{path.name}: verdict is {doc.get('verdict')!r} - a MIB table "
                    "that failed its own anchor check must not be committed as "
                    "evidence")
            if not doc.get("entries"):
                errors.append(f"{path.name}: no MIB entries recovered")

        elif str(doc.get("producer", "")) == "fwrecon:webbundle":
            counts["fwrecon"] += 1
            if not doc.get("source_sha256"):
                errors.append(
                    f"{path.name}: no source_sha256 - the report cannot name the "
                    "image it describes")
            # The w6cg format carries no checksum, no entry count and no
            # terminator, so "the strides consumed the archive exactly" is the
            # only evidence the layout was read correctly. A derailed walk still
            # produces a plausible-looking entry list, which is precisely why it
            # must never be committed as evidence.
            if doc.get("self_check") != "exact":
                errors.append(
                    f"{path.name}: self_check is {doc.get('self_check')!r} - the "
                    "entry walk did not consume the archive exactly, so the "
                    "recovered layout does not hold")
            if doc.get("bytes_unconsumed"):
                errors.append(
                    f"{path.name}: {doc['bytes_unconsumed']} bytes unconsumed")
            if not doc.get("entries"):
                errors.append(f"{path.name}: no bundle entries recovered")

        elif str(doc.get("producer", "")) == "fwrecon:compcs":
            counts["fwrecon"] += 1
            if not doc.get("source_sha256"):
                errors.append(
                    f"{path.name}: no source_sha256 - the report cannot name the "
                    "flash image it describes")
            # The two checks that come from libapmib itself rather than from this
            # decoder's own opinion of its work. A committed config table that
            # fails the vendor's own checksum is not evidence of anything, and a
            # ring-fill disagreement means the decode depended on window bytes no
            # literal ever wrote.
            if not doc.get("checksum_ok"):
                errors.append(
                    f"{path.name}: checksum_ok is false - libapmib's own 8-bit "
                    "payload checksum does not pass, so the device would reject "
                    "this blob and so should the repository")
            if not doc.get("ring_fill_agrees"):
                errors.append(
                    f"{path.name}: ring_fill_agrees is false - decoding with two "
                    "different LZSS window fills disagrees")
            if doc.get("verdict") != "consistent":
                errors.append(
                    f"{path.name}: verdict is {doc.get('verdict')!r} - a config "
                    "decode that flagged its own anomalies must not be committed "
                    "as evidence")
            if not doc.get("entries"):
                errors.append(f"{path.name}: no config entries recovered")

        elif str(doc.get("producer", "")) == "fwrecon:flashdump":
            counts["fwrecon"] += 1
            if not doc.get("sha256"):
                errors.append(
                    f"{path.name}: no sha256 - the report cannot name the image "
                    "it describes")
            # Same rule as the MIB table above, for the same reason: this report
            # is the evidence that a flash dump read off the device agrees with
            # what was known before it existed. One that failed its own hard
            # checks must not sit in reports/ looking like a result.
            if doc.get("self_check") != "OK":
                errors.append(
                    f"{path.name}: self_check is {doc.get('self_check')!r} - a "
                    "dump that failed its own structural checks must not be "
                    "committed as evidence")
            if not doc.get("checks"):
                errors.append(f"{path.name}: no checks were run")

        elif str(doc.get("producer", "")) == "loader-unpack":
            counts["fwrecon"] += 1
            if not doc.get("source_sha256"):
                errors.append(
                    f"{path.name}: no source_sha256 - the report cannot name the "
                    "flash image it describes")
            # This report's value is its *absences*: it says the boot loader has
            # no kernel command line anywhere in it. An absence is only evidence
            # if the same scan is shown to find things that are there, so the
            # positive control is not optional and a report that shipped without
            # it must not sit in reports/ looking like a result.
            ctl = doc.get("controls", {})
            if not ctl.get("help_banner_present"):
                errors.append(
                    f"{path.name}: the unpacked stage does not contain the "
                    "console help banner, so it is not the command interpreter")
            if ctl.get("documented_commands_missing"):
                errors.append(
                    f"{path.name}: the string scan missed "
                    f"{ctl['documented_commands_missing']} - commands the console's "
                    "own `?` prints. Its absence claims are worthless until it "
                    "finds all of them")
            if len(ctl.get("documented_commands_found") or []) < 17:
                errors.append(
                    f"{path.name}: only "
                    f"{len(ctl.get('documented_commands_found') or [])} of the 17 "
                    "documented commands were found")
            if doc.get("self_check") != "OK":
                errors.append(
                    f"{path.name}: self_check is {doc.get('self_check')!r}")

        elif str(doc.get("producer", "")) == "cve-endpoints":
            counts["ghidra"] += 1
            # The failure mode is a clean, short, wrong report: a parser that
            # read three rows out of notes/cve-status.md instead of thirty-three
            # produces exactly the same shape as one that read them all, and a
            # matcher that says "absent" to everything produces a table full of
            # interesting-looking negatives. Both are caught by the controls and
            # by nothing else, so a report that did not run them is not evidence.
            if doc.get("control_ok") is not True:
                errors.append(
                    f"{path.name}: control_ok is {doc.get('control_ok')!r} - the "
                    "positive control (formSysCmd/sysCmd), the negative control "
                    "or the parse floor did not hold, so every 'not present on "
                    "this build' below is unusable")
            if not doc.get("source_sha256"):
                errors.append(
                    f"{path.name}: no source_sha256 - the report cannot name the "
                    "binary whose dispatch table it read")
            if int(doc.get("root_form_entries") or 0) < 1:
                errors.append(
                    f"{path.name}: root_form_entries is "
                    f"{doc.get('root_form_entries')!r}; an empty dispatch table "
                    "makes every endpoint look absent")

        elif str(doc.get("producer", "")) == "mipsref":
            counts["ghidra"] += 1
            # tools/mipsref.py answers "who references this address" from
            # instruction encodings, with no symbol table and no Ghidra. Its
            # whole value is being a second source, and its characteristic output
            # is a *zero*: "nothing reads this global". A zero produced by a
            # broken decode and a zero produced by a binary that really holds
            # nothing are the same file, so all three of these are required.
            if not doc.get("source_sha256"):
                errors.append(
                    f"{path.name}: no source_sha256 - the report cannot name the "
                    "binary it describes")
            if doc.get("gp") is None:
                errors.append(
                    f"{path.name}: gp is null, so the gp-relative addressing form "
                    "was never checked and a reference through it would have been "
                    "missed silently")
            if doc.get("control_ok") is not True:
                errors.append(
                    f"{path.name}: control_ok is {doc.get('control_ok')!r} - a scan "
                    "whose control address did not come back with both a read and "
                    "a write proves nothing about the addresses that came back "
                    "empty, and must not be committed as evidence")
            # Schema 2 added the dereference pass, and with it a second control.
            # The first one was green throughout the run whose `beforeuptime`
            # answer the device refuted: 0x004899e0 has a direct read and a
            # direct store, so it exercised only the addressing form the scanner
            # could already see. A control proves the path it travels. This one
            # requires a store found *through a register*, so a build that lost
            # the pass fails here instead of quietly reproducing version 1's
            # numbers -- which is the shape of the failure, not a hypothetical.
            if doc.get("schema", 1) >= 2:
                if doc.get("control_indirect_ok") is not True:
                    errors.append(
                        f"{path.name}: control_indirect_ok is "
                        f"{doc.get('control_indirect_ok')!r} - the dereference "
                        "pass was not proved to run, so every 'no writes' answer "
                        "in this file is the version 1 answer")
                if not doc.get("dynsym_count"):
                    errors.append(
                        f"{path.name}: dynsym_count is "
                        f"{doc.get('dynsym_count')!r} - without .dynsym a GOT "
                        "slot cannot be told from a variable, and reporting a "
                        "slot as a datum is exactly what schema 2 exists to stop")

        elif str(doc.get("producer", "")).startswith("ghidra:") or (
            "program" in doc and "matches" in doc
        ):
            counts["ghidra"] += 1
            for field in ("language", "image_base", "function_count"):
                if field not in doc:
                    errors.append(f"{path.name}: missing required field {field!r}")
            # A run that recovered no functions means the language spec was wrong
            # or analysis did not complete; the file would look fine otherwise.
            if doc.get("function_count", 0) < 1:
                errors.append(f"{path.name}: function_count is 0 — analysis did not run")
            if "producer" in doc and not doc.get("source_sha256"):
                errors.append(
                    f"{path.name}: no source_sha256 — the report cannot name the "
                    "binary it describes; re-run analyze.ps1 with -Binary")

        else:
            errors.append(
                f"{path.name}: unrecognised report shape (no 'schema_version', "
                "and not a Ghidra string-xref report)")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    print(f"reports OK — {counts['fwrecon']} fwrecon (schema {expected}), "
          f"{counts['ghidra']} Ghidra, {counts['rtcase']} rtcase, "
          f"{counts['mkflash']} mkflash, {counts['emulation']} emulation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
