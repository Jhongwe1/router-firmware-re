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
  tools/rtcase.py `rtcase record`      -> carries "producer": "rtcase"
                                          (shape only here; admissibility is
                                           `rtcase check`, which needs the
                                           register)

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
    counts = {"fwrecon": 0, "ghidra": 0, "rtcase": 0}

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
          f"{counts['ghidra']} Ghidra, {counts['rtcase']} rtcase")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
