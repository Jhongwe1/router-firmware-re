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

Two producers write into reports/, on purpose:

  fwrecon        `fwrecon report`      -> carries "schema_version"
  Ghidra script  BoaStringXrefs.java   -> carries "program" and "matches"

An unrecognised file is an error rather than something to skip. A stray or
half-written report in a directory that is presented as the project's results
is exactly the thing worth failing on.

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
    counts = {"fwrecon": 0, "ghidra": 0}

    for path in files:
        try:
            doc = json.loads(path.read_text("utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path.name}: invalid JSON ({exc})")
            continue

        if "schema_version" in doc:
            counts["fwrecon"] += 1
            got = doc["schema_version"]
            if got != expected:
                errors.append(
                    f"{path.name}: fwrecon schema {got!r}, current source emits "
                    f"{expected!r} — regenerate with `make recon`")
            for field in ("label", "generated_at_utc"):
                if field not in doc:
                    errors.append(f"{path.name}: missing required field {field!r}")

        elif "program" in doc and "matches" in doc:
            counts["ghidra"] += 1
            for field in ("language", "image_base", "function_count"):
                if field not in doc:
                    errors.append(f"{path.name}: missing required field {field!r}")
            # A run that recovered no functions means the language spec was wrong
            # or analysis did not complete; the file would look fine otherwise.
            if doc.get("function_count", 0) < 1:
                errors.append(f"{path.name}: function_count is 0 — analysis did not run")

        else:
            errors.append(
                f"{path.name}: unrecognised report shape (no 'schema_version', "
                "and not a Ghidra string-xref report)")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    print(f"reports OK — {counts['fwrecon']} fwrecon (schema {expected}), "
          f"{counts['ghidra']} Ghidra")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
