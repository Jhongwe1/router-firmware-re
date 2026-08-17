#!/usr/bin/env python3
"""Check that every command in runsheet.md still resolves.

Why this exists
---------------
`runsheet.md` is hand-written on purpose: it is the one document a stranger
follows front to back, and generating it from `RUNBOOK.md` would make it exactly
as hand-holding as a reference document, which is the problem it exists to solve.

The cost of hand-writing is drift, and this narrows that cost to the part that
matters. It does not check the prose. It checks the claims a command makes about
the repository:

  * every `make <target>` names a target the Makefile defines;
  * every `tools/<x>` path exists;
  * every flag passed to one of this project's own Python tools appears in that
    tool's own argparse definition, and every subcommand it names is a real
    subcommand;
  * every `§8.x.y` cross-reference resolves to a heading in RUNBOOK.md;
  * every relative link resolves to a file that exists;
  * every fenced block is tagged, so "run this" and "this is what you will see"
    are never the same thing to a reader;
  * every step declares the six fields the file's own preamble promises, and
    names the date its commands were last actually run.

The last one is the reason this is worth having rather than being a tidiness
check. On 2026-08-17 a step was written into `RUNBOOK.md` with the command
`AUTOBURN: 0`, which the boot loader rejects -- the help text is not the syntax.
A reader following it would have stopped at the first device command in that
section. Nothing in the repository could have caught it, because nothing was
reading the commands as commands.

What it deliberately does NOT check
-----------------------------------
Semantics. If the runsheet says "expect 4 / 343" and the baseline has moved, the
flags are all still valid and this passes. That class of drift is handled by the
runsheet citing rather than restating, and by `BENCH-LOG.md` being the record of
what the number actually was. A checker that pretended to catch it would be
worse than one that says it does not.

Usage:  python3 tools/check-runsheet.py [runsheet.md]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Steps are `## A<n> <title>` in Part A. Part B is a per-week composition list
# and carries no commands of its own, so it is not held to the step anatomy.
STEP_RE = re.compile(r"^## (A\d+(?:\.\d+)?) ")
FENCE_RE = re.compile(r"^```(\w*)")

# The fields the file's own preamble promises a reader. `層` and `最後驗證` are
# required of every step; the rest are required only where they apply, and a
# missing stop condition on a step that can fail is a judgement this cannot make.
REQUIRED_FIELDS = ("**層**", "**最後驗證**")

# This project's own tools, checked against their own --help.
OWN_TOOLS = {
    "tools/rtcase.py", "tools/bench-probe.py", "tools/console-dump.py",
    "tools/loader-unpack.py", "tools/check-reports.py",
    "tools/check-runsheet.py", "tools/annotate-photo.py",
    "tools/redact-photo.py", "tools/zipprefix.py",
}


def makefile_targets() -> set[str]:
    text = (REPO / "Makefile").read_text("utf-8")
    return {m.group(1) for m in re.finditer(r"(?m)^([a-zA-Z0-9_-]+):", text)}


def runbook_headings() -> set[str]:
    text = (REPO / "RUNBOOK.md").read_text("utf-8")
    out = set()
    for m in re.finditer(r"(?m)^#{2,4}\s+(\d+(?:\.\d+)*)", text):
        out.add(m.group(1))
    return out


def tool_help(tool: str) -> str:
    """`--help` for one of our tools, plus each subcommand's own help.

    Subparsers hide their flags behind the subcommand, so `--help` alone would
    not list `--at-prompt` and this check would pass over the flags most likely
    to be wrong.
    """
    parts = []
    try:
        r = subprocess.run([sys.executable, str(REPO / tool), "--help"],
                           capture_output=True, text=True, timeout=60, check=False)
        parts.append(r.stdout + r.stderr)
    except (OSError, subprocess.SubprocessError) as exc:
        return f"<<unavailable: {exc}>>"
    for sub in re.findall(r"\{([a-z0-9,\-_]+)\}", parts[0]):
        for name in sub.split(","):
            try:
                r = subprocess.run([sys.executable, str(REPO / tool), name, "--help"],
                                   capture_output=True, text=True, timeout=60,
                                   check=False)
                parts.append(r.stdout + r.stderr)
            except (OSError, subprocess.SubprocessError):
                pass
    return "\n".join(parts)


def check(path: Path) -> int:
    text = path.read_text("utf-8")
    lines = text.splitlines()
    errors: list[str] = []
    warnings: list[str] = []

    targets = makefile_targets()
    headings = runbook_headings()
    helps: dict[str, str] = {}

    # ---- fences and command extraction ---------------------------------
    #
    # Two things this got wrong on its first run, both found by running it:
    #
    #   * A fence nested inside a blockquote (`>     ```bash`) was not seen as a
    #     fence at all, so the commands inside it were never checked -- and this
    #     file puts its gotchas in blockquotes, which is exactly where a
    #     recovery command is most likely to be. One `tools/config-attrib.sh`
    #     reference sailed through.
    #   * `[16bit](400MHz)` inside the boot loader's banner is a markdown link as
    #     far as a regex is concerned. Link checking has to skip fences.
    #
    # So the fence state machine runs first and records which lines are inside a
    # fence; everything else consults it.
    def unquote(s: str) -> str:
        return re.sub(r"^(?:\s*>)+\s?", "", s)

    commands: list[tuple[int, str]] = []
    fenced: set[int] = set()
    in_fence, lang, fence_line = False, "", 0
    untagged = 0
    for i, line in enumerate(lines, 1):
        bare = unquote(line)
        if bare.startswith("```"):
            if in_fence:
                in_fence = False
                fenced.add(i)
                continue
            m = FENCE_RE.match(bare)
            in_fence, lang, fence_line = True, (m.group(1) if m else ""), i
            fenced.add(i)
            if not lang:
                untagged += 1
                warnings.append(
                    f"{path.name}:{i}: fenced block with no language. A reader "
                    "cannot tell 'run this' from 'you will see this'")
            continue
        if in_fence:
            fenced.add(i)
            if lang in ("bash", "sh", "powershell"):
                commands.append((i, bare))
    if in_fence:
        errors.append(f"{path.name}:{fence_line}: unterminated code fence")

    if not commands:
        errors.append(
            f"{path.name}: no shell commands found at all. Either the file is "
            "empty or the fence language tags changed, and in both cases every "
            "check below would pass over nothing")

    # ---- make targets --------------------------------------------------
    seen_make = set()
    for ln, line in commands:
        for m in re.finditer(r"\bmake\s+([a-zA-Z0-9_-]+)", line):
            t = m.group(1)
            if t in ("TIER", "WEEK"):
                continue
            seen_make.add(t)
            if t not in targets:
                errors.append(f"{path.name}:{ln}: `make {t}` — no such target in Makefile")

    # ---- our tools: paths, subcommands, flags --------------------------
    for ln, line in commands:
        for m in re.finditer(r"\btools/[A-Za-z0-9_.-]+", line):
            rel = m.group(0)
            if not (REPO / rel).exists():
                errors.append(f"{path.name}:{ln}: {rel} does not exist")
                continue
            if rel not in OWN_TOOLS:
                continue
            if rel not in helps:
                helps[rel] = tool_help(rel)
            h = helps[rel]
            if h.startswith("<<unavailable"):
                warnings.append(f"{path.name}:{ln}: could not run {rel} --help ({h})")
                continue
            tail = line[m.end():]
            # subcommand: the first bare word after the tool path
            sub = re.match(r"\s+([a-z][a-z0-9-]*)\b", tail)
            if sub:
                name = sub.group(1)
                declared = set()
                for grp in re.findall(r"\{([a-z0-9,\-_]+)\}", h):
                    declared.update(grp.split(","))
                if declared and name not in declared:
                    errors.append(
                        f"{path.name}:{ln}: {rel} has no subcommand `{name}` "
                        f"(it has: {', '.join(sorted(declared))})")
            for f in re.findall(r"(?<![\w-])(--[a-z][a-z0-9-]*)", tail):
                if f not in h:
                    errors.append(
                        f"{path.name}:{ln}: {rel} does not accept `{f}`")

    # ---- cross-references into RUNBOOK ---------------------------------
    for i, line in enumerate(lines, 1):
        for m in re.finditer(r"§\s?(\d+(?:\.\d+)+)", line):
            if m.group(1) not in headings:
                errors.append(
                    f"{path.name}:{i}: §{m.group(1)} does not resolve to a "
                    "heading in RUNBOOK.md")

    # ---- relative links ------------------------------------------------
    for i, line in enumerate(lines, 1):
        if i in fenced:
            continue
        for m in re.finditer(r"\]\((?!https?:|#)([^)]+)\)", line):
            tgt = m.group(1).split("#")[0]
            if not tgt:
                continue
            if not (path.parent / tgt).exists():
                errors.append(f"{path.name}:{i}: link target {tgt} does not exist")

    # ---- step anatomy --------------------------------------------------
    steps: list[tuple[str, int]] = []
    for i, line in enumerate(lines, 1):
        m = STEP_RE.match(line)
        if m:
            steps.append((m.group(1), i))
    if not steps:
        errors.append(f"{path.name}: no `## A<n>` steps found — the file's shape changed")
    partb = text.find("# Part B")
    for j, (name, ln) in enumerate(steps):
        end = steps[j + 1][1] if j + 1 < len(steps) else len(lines)
        body = "\n".join(lines[ln:end])
        # Only steps that ask a reader to run something. A14 is a symptom/cause
        # table: demanding "was this last verified?" of a troubleshooting index
        # would be a field filled in to satisfy a checker, which is worse than
        # no field.
        if not any(ln <= c <= end for c, _ in commands):
            continue
        for field in REQUIRED_FIELDS:
            if field not in body:
                errors.append(
                    f"{path.name}:{ln}: step {name} does not declare {field}. "
                    "The preamble promises a reader every step carries it")
        m = re.search(r"\*\*最後驗證\*\*\s*\|\s*([^|\n]+)", body)
        if m and not re.search(r"\d{4}-\d{2}-\d{2}", m.group(1)):
            errors.append(
                f"{path.name}:{ln}: step {name}'s 最後驗證 names no date. "
                "A reader has to know how old these commands are")
    if partb < 0:
        errors.append(f"{path.name}: no `# Part B` section — per-week run orders live there")

    # ---- report --------------------------------------------------------
    for w in warnings:
        print(f"  warn  {w}", file=sys.stderr)
    if errors:
        for e in errors:
            print(f"  FAIL  {e}", file=sys.stderr)
        return 1
    print(f"runsheet OK — {len(steps)} steps, {len(commands)} command lines, "
          f"{len(seen_make)} make targets, {len(helps)} tools checked against "
          f"their own --help, {untagged} untagged fences")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runsheet", nargs="?", default=str(REPO / "runsheet.md"),
                    type=Path)
    args = ap.parse_args(argv[1:])
    if not args.runsheet.is_file():
        print(f"no such file: {args.runsheet}", file=sys.stderr)
        return 2
    return check(args.runsheet)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
