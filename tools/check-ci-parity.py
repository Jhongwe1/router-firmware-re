#!/usr/bin/env python3
"""`make ci` and .github/workflows/ci.yml are two hand-kept lists. Diff them.

Why this exists
---------------
Five times now, a guard suite has been added to one of these files and not the
other. The workflow's own comment above the `config-diff` step says "it is the
fourth time these two lists have diverged"; the fifth was
`tools/test-device-liveness.sh` and `tools/test-rogue-dhcp.sh`, added to `make
ci` on 2026-08-18 and 2026-08-19 and absent here, found by diffing the files
rather than by noticing.

Both directions hurt, and they hurt differently:

  * **in `make ci`, not in CI** -- a push goes out green on a check nobody
    remote ever runs, so a broken suite reaches `main`;
  * **in CI, not in `make ci`** -- the local command stops predicting the remote
    one, and the habit of running it before pushing quietly becomes useless.

RUNBOOK 10.21 records the first of those as a rule. A rule that has been broken
five times is not a rule, it is a reminder, and the repository's own answer to
that -- `tools/check-benchlog.py` -- was to replace the reminder with a checker.
This is the same move applied to the thing the reminder was about.

What it compares, and what it deliberately does not
---------------------------------------------------
It compares the set of `tools/*.sh` and `tools/*.py` invocations, not the set of
target names. The two files organise the work differently on purpose -- `make`
has targets, the workflow has jobs that parallelise -- so comparing names would
force a shape neither file wants. What has to match is *which scripts run*.

Everything outside `tools/` is out of scope: `ruff`, `pytest`, `shellcheck` and
the container build are invoked differently in the two files by design, and
RUNBOOK 10.21 already covers the one of those that drifted.

    python3 tools/check-ci-parity.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MAKEFILE = REPO / "Makefile"
WORKFLOW = REPO / ".github/workflows/ci.yml"

SCRIPT = re.compile(r"tools/[A-Za-z0-9_/.-]+\.(?:sh|py)")

# Deliberate one-sided entries, each with the reason it is one-sided. An entry
# here is a decision; an entry missing from here is a divergence. Adding a name
# to this dict is how you say "on purpose", and it leaves a diff that says so.
DELIBERATE: dict[str, str] = {
    # Regeneration targets, not checks: they need the extracted rootfs or the
    # flash dump, neither of which a runner can have. `check-reports.py` is what
    # holds their committed output to account, and that does run in CI.
    "tools/mipsref.py": "regenerates a report; needs the extracted rootfs",
    "tools/libbase.py": "regenerates a report; needs the extracted rootfs",
    "tools/loader-unpack.py": "regenerates a report; needs the flash dump",
    "tools/device-liveness.py": "talks to the router; there is no router in CI",
    "tools/count-checks.sh": "counts the other suites; not itself a check",
    "tools/unpack-firmware.sh": "needs vendor firmware, which is not redistributed",
    "tools/fetch-firmware.sh": "downloads vendor firmware",
    "tools/flash-read.sh": "drives the boot loader over a serial cable",
    "tools/qemu-env.sh": "needs root and a chroot",
    "tools/config-diff.py": "end-to-end run needs the chroot; its suite runs in both",
    "tools/bench-doctor.sh": "checks a bench workstation's prerequisites",
    "tools/ioc-precheck.sh": "runs against the device before a session",
    "tools/config-attrib.sh": "runs against the device",
    "tools/session-window.sh": "runs against the device",
    "tools/coldboot-timing.sh": "runs against the device",
    "tools/rogue-dhcp.py": "binds a raw socket on a real interface",
    "tools/annotate-photo.py": "operates on bench photographs",
    "tools/redact-photo.py": "operates on bench photographs",
    "tools/bench-probe.py": "sends requests to the device",
    "tools/console-dump.py": "drives the serial console",
    "tools/console-write.py": "drives the serial console",
    "tools/crash-triage.py": "needs the chroot",
    "tools/paramfuzz.py": "needs the chroot",
    "tools/formtable-scan.py": "needs the extracted rootfs",
    "tools/handler-sweep.py": "needs the chroot",
    "tools/cve-endpoints.py": "needs the extracted rootfs",
    "tools/failopen-probe.sh": "needs the chroot",
    "tools/mkflash.py": "needs the flash dump",
    "tools/mkcompds.py": "needs the flash dump",
    "tools/mkhwsetting.py": "needs the flash dump",
    "tools/zipprefix.py": "helper, driven by the fwrecon suite",
    "tools/alignfix": "a library, loaded by the thing under test",
    "tools/bughunt.py": "renders a note from committed reports",
    "tools/mipsref.py ": "regenerates a report",
}


def make_ci_scripts(text: str) -> tuple[set[str], list[str]]:
    """Every tools/ script reachable from the `ci:` target, transitively."""
    recipes: dict[str, list[str]] = {}
    prereqs: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("\t") and current:
            recipes[current].append(line)
            continue
        m = re.match(r"^([A-Za-z0-9_.-]+):\s*([^=]*)$", line)
        if m and not line.startswith("\t"):
            current = m.group(1)
            recipes.setdefault(current, [])
            deps = m.group(2).split("##")[0].split()
            prereqs[current] = deps
            continue
        if not line.startswith("\t"):
            current = None
    if "ci" not in prereqs:
        raise SystemExit("Makefile has no `ci:` target -- this checker is looking "
                         "at the wrong file, and a green run would mean nothing")
    seen: set[str] = set()
    order: list[str] = []
    stack = list(prereqs["ci"])
    while stack:
        t = stack.pop(0)
        if t in seen:
            continue
        seen.add(t)
        order.append(t)
        stack.extend(prereqs.get(t, []))
    found: set[str] = set()
    for t in order:
        for line in recipes.get(t, []):
            found.update(SCRIPT.findall(line))
    return found, order


def workflow_scripts(text: str) -> set[str]:
    """Every tools/ script inside a `run:` block. Comments are not steps."""
    found: set[str] = set()
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^(\s*)-?\s*run:\s*(\|-?|>-?)?\s*(.*)$", line)
        if m:
            indent, block, inline = m.group(1), m.group(2), m.group(3)
            if block:
                i += 1
                while i < len(lines):
                    nxt = lines[i]
                    if nxt.strip() and not nxt.startswith(indent + " "):
                        break
                    found.update(SCRIPT.findall(nxt.split("#")[0]))
                    i += 1
                continue
            found.update(SCRIPT.findall(inline.split("#")[0]))
        i += 1
    return found


def compare(make_set: set[str], wf_set: set[str],
            deliberate: dict[str, str] | None = None) -> list[str]:
    deliberate = DELIBERATE if deliberate is None else deliberate
    problems = []
    for s in sorted(make_set - wf_set):
        if s in deliberate:
            continue
        problems.append(
            f"{s} runs in `make ci` and not in .github/workflows/ci.yml -- a push "
            "can go out green on a check the remote never runs")
    for s in sorted(wf_set - make_set):
        if s in deliberate:
            continue
        problems.append(
            f"{s} runs in CI and not in `make ci` -- running the local command "
            "before pushing has stopped predicting the remote one")
    return problems


def workflow_parses(path: Path | None = None) -> tuple[bool | None, str]:
    """Does the workflow parse as YAML at all?

    Added 2026-08-19, immediately after this file shipped green on a workflow
    GitHub could not read. A step named with an unquoted backtick -- `` `make
    ci` and this file run the same suites`` -- is a YAML syntax error, because a
    backtick cannot start a plain scalar. The whole run failed in 0 s while this
    checker reported the two lists in agreement, **because it reads the file
    with a regex and a regex does not care whether the document is valid**.

    A checker that reads a config file with a pattern will pass on a file the
    real consumer rejects, every time. So the file gets shown to a parser.
    Returns (None, reason) when no parser is available, which is reported as a
    skip rather than as a pass -- a check that could not run has not run.
    """
    try:
        # Imported here, not at the top: it is optional and its absence is a
        # reportable state rather than a crash.
        import yaml
    except ImportError:
        return None, "PyYAML is not installed here, so the workflow was NOT parsed"
    try:
        yaml.safe_load((path or WORKFLOW).read_text(encoding="utf-8"))
    except Exception as exc:  # any parse error at all, and the message is the point
        return False, " ".join(str(exc).split())
    return True, "the workflow parses as YAML"


def main() -> int:
    if not MAKEFILE.exists() or not WORKFLOW.exists():
        print("check-ci-parity: Makefile or .github/workflows/ci.yml is missing",
              file=sys.stderr)
        return 2
    parsed, why = workflow_parses()
    if parsed is False:
        print("check-ci-parity: .github/workflows/ci.yml is not valid YAML, so "
              "GitHub will fail the whole run before any step starts:\n")
        print(f"  {why}\n")
        print("Nothing below this line means anything until that is fixed.")
        return 1
    make_set, targets = make_ci_scripts(MAKEFILE.read_text(encoding="utf-8"))
    wf_set = workflow_scripts(WORKFLOW.read_text(encoding="utf-8"))
    problems = compare(make_set, wf_set)
    shared = len(make_set & wf_set)
    if problems:
        print(f"check-ci-parity: {len(problems)} divergence(s) between "
              "`make ci` and .github/workflows/ci.yml\n")
        for p in problems:
            print(f"  {p}")
        print("\nEither add the step to the other file, or record the reason in "
              "DELIBERATE in this script -- which leaves a diff saying it was a "
              "decision.")
        return 1
    print(f"  ok   `make ci` ({len(targets)} targets) and the workflow run the "
          f"same {shared} tools/ scripts")
    print(f"  {'ok  ' if parsed else 'skip'} {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
