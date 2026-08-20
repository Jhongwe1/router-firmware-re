#!/usr/bin/env python3
"""Check that every command in runsheet.md still resolves, and that the split
between runsheet.md and RUNBOOK.md §8.12 is real rather than claimed.

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
    tool's own argparse definition, and every subcommand it names is real;
  * every `§8.x.y` cross-reference resolves to a heading in RUNBOOK.md;
  * every relative link resolves to a file that exists;
  * every fenced block is tagged, so "run this" and "this is what you will see"
    are never the same thing to a reader;
  * every step sits under a station whose number matches its own, declares the
    four fields the file's own preamble promises, and names the date its commands
    were last actually run;
  * the front-page index names exactly the steps that exist, closing exactly the
    tests their headings claim;
  * **§8.12 of RUNBOOK.md contains no command fences at all**, and every one of
    its subsections is paired one-to-one with a step.

The last two are the reason this is worth having rather than being a tidiness
check. On 2026-08-17 a step was written into `RUNBOOK.md` with the command
`AUTOBURN: 0`, which the boot loader rejects -- the help text is not the syntax.
A reader following it would have stopped at the first device command in that
section. Nothing in the repository could have caught it, because nothing was
reading the commands as commands.

And when §8.12 was finally measured, it opened by declaring that the commands
had moved out to `runsheet.md` -- and then carried twelve command blocks, four of
which the bench had already refuted. The fix is not to check the commands there.
It is to forbid them: a section that may not hold a command cannot hold a stale
one. That is the `no command fences` rule below.

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
import contextlib
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# A newline, as a name. Every error message in this file is an f-string and
# a literal backslash-n inside one is the single easiest thing to get wrong
# when this file is edited by a script rather than by hand.
NL = chr(10)

# Part A is four stations; a step is `### A<station>.<n>`. The first digit is the
# device state the step needs, which is why it is worth checking that a step sits
# under the matching station heading: a step filed under the wrong station is a
# step a reader will run with the board in the wrong state.
STEP_RE = re.compile(r"^### (A(\d+)\.\d+) ")
STATION_RE = re.compile(r"^## 第 (\d+) 站")
SUBSTEP_RE = re.compile(r"^#### (A\d+(?:\.\d+)+)")
FENCE_RE = re.compile(r"^```(\w*)")

# Every step heading ends with the tests it closes, or says it closes none. That
# is the single place those ids live: the metadata table below does not repeat
# them, so there is nothing to drift against.
#
# This checker reads a Traditional Chinese document, so fullwidth parentheses are
# the thing being matched rather than a mistyped ASCII one. Ruff cannot tell those
# apart, so they are declared here once and every message below is built from
# these names instead of repeating the literal.
CLOSES = "（關"                    # noqa: RUF001
CLOSES_RE = re.compile(CLOSES + r"\s*(.+?)）\s*$")   # noqa: RUF001
NOCLOSE = "（不關登記簿項目）"      # noqa: RUF001
CLOSES_SHOWN = CLOSES + " …）"     # noqa: RUF001  — how it reads in a message

META_HEADER = "| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |"

# (marker, the only station whose device state can run it, what it means).
# A command is evidence of the state it needs, and that evidence is checkable.
STATE_MARKERS = [
    ("--at-prompt", 2, "the flag means the board is already halted at <RealTek>"),
    ("console-dump.py dump", 2, "FLR + DB are boot-loader commands"),
    ("console-dump.py catch", 2, "it streams ESC across power-on to halt the board"),
    ("http://10.1.1.1", 3, "nothing is served until the board has booted"),
]

RUNBOOK_812_SUB = re.compile(r"^### (8\.12\.(\d+))\b(.*)$")
COMMAND_LANGS = {"bash", "sh", "powershell", "shell", "ps1", ""}

# This project's own tools, checked against their own --help.
OWN_TOOLS = {
    "tools/rtcase.py", "tools/bench-probe.py", "tools/console-dump.py",
    "tools/loader-unpack.py", "tools/check-reports.py",
    "tools/check-runsheet.py", "tools/annotate-photo.py",
    "tools/redact-photo.py", "tools/zipprefix.py",
    # The write path. It is in this set for the same reason it has the largest
    # guard suite: a flag that has been renamed or removed is, on this one tool,
    # the difference between programming 0x008000 and programming whatever the
    # argument parser fell back to.
    "tools/console-write.py",
    # Added 2026-08-18 with the steps that cite them. All three are new enough
    # that their flags are still moving, which is exactly when a runsheet goes
    # stale without anything saying so.
    "tools/paramfuzz.py", "tools/crash-triage.py", "tools/formtable-scan.py",
    "tools/handler-sweep.py",
    # Added 2026-08-19 with A1.10, A3.1.4, A3.18 and A3.24. All four are new
    # enough that their flags are still moving, and three of them are cited by a
    # step a stranger is expected to follow front to back.
    "tools/device-liveness.py", "tools/cve-endpoints.py", "tools/rogue-dhcp.py",
    "tools/mipsref.py",
    # Added 2026-08-19 with A3.15. Its `--arg-file` flag exists because the
    # alternative -- a payload on the command line -- was expanded by the local
    # shell and destroyed a test, so a runsheet that still shows the old form
    # would cost another power cycle rather than a puzzled minute.
    "tools/upnp-soap.py",
    # The two shell tools, added 2026-08-20. They are here for the same reason
    # console-write.py is: on these two, a flag that has been renamed is the
    # difference between writing 0x3FF000 and writing whatever the argument
    # parser fell back to -- except that a shell script has no argument parser
    # to fall back in, which makes it worse rather than better.
    "tools/flash-read.sh", "tools/flash-write.sh",
}


def makefile_targets() -> set[str]:
    text = (REPO / "Makefile").read_text("utf-8")
    return {m.group(1) for m in re.finditer(r"(?m)^([a-zA-Z0-9_-]+):", text)}


def runbook_headings(runbook: Path) -> set[str]:
    text = runbook.read_text("utf-8")
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
    # A shell tool has no argparse, so its `--help` is the Usage block it prints
    # when called with no arguments. Both of the shell tools in OWN_TOOLS are
    # written to do exactly that and to exit 2 without touching hardware -- which
    # is checked here by asking for it, not assumed. Added 2026-08-20 with
    # flash-write.sh: the two tools that can destroy the part were the two whose
    # flags nothing validated, because the check was written for Python.
    argv = ([sys.executable, str(REPO / tool), "--help"] if tool.endswith(".py")
            else ["bash", str(REPO / tool)])
    parts = []
    try:
        r = subprocess.run(argv, capture_output=True, text=True,
                           timeout=60, check=False)
        parts.append(r.stdout + r.stderr)
    except (OSError, subprocess.SubprocessError) as exc:
        return f"<<unavailable: {exc}>>"
    if not tool.endswith(".py"):
        if "Usage:" not in parts[0]:
            return (f"<<unavailable: {tool} printed no Usage block when called "
                    "with no arguments, so its flags cannot be checked>>")
        return parts[0]
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


def declared_choices(help_text: str) -> dict[str, set[str]]:
    """Flags whose VALUE argparse restricts, and the values it will take.

    argparse renders a `choices=` flag as `--disclosure {open,protect}`, in both
    the usage line and the options block, so the set is recoverable from the
    help text without importing the tool.

    This exists because the flag check above is not enough. On 2026-08-18 three
    commands in `runsheet.md` passed `--disclosure reveal` to `fwrecon compcs`,
    which accepts `open` and `protect`; every one of them died on argparse before
    doing any work, and CI was green throughout, because `--disclosure` is a real
    flag and `reveal` is not a flag at all. That is the same shape as the
    `AUTOBURN: 0` failure this whole checker was written for -- **the help text
    is not the syntax** -- arriving a second time through the one gap the first
    fix left open.
    """
    out: dict[str, set[str]] = {}
    for m in re.finditer(r"(--[a-z][a-z0-9-]*)[= ]\{([^}]+)\}", help_text):
        out.setdefault(m.group(1), set()).update(
            c.strip() for c in m.group(2).split(",") if c.strip())
    return out


def check_runbook_812(path: Path, errors: list[str], step_ids: list[str],
                      why: dict[str, str]) -> None:
    """§8.12 holds no commands, and pairs one-to-one with the steps.

    Both halves of that sentence were false on 2026-08-17 and neither was
    visible: the section said the commands had moved, twelve blocks said
    otherwise, and no step named the subsection that explained it.
    """
    lines = path.read_text("utf-8").split("\n")
    try:
        start = next(i for i, s in enumerate(lines) if s.startswith("## 8.12 "))
    except StopIteration:
        errors.append(f"{path.name}: no `## 8.12` section — the runsheet's 為什麼 "
                      "column points into it")
        return
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].startswith("## ") and not lines[i].startswith("## 8.12")),
               len(lines))

    in_fence = False
    for i in range(start, end):
        bare = re.sub(r"^(?:\s*>)+\s?", "", lines[i])
        if not bare.startswith("```"):
            continue
        if not in_fence:
            lang = (FENCE_RE.match(bare).group(1) if FENCE_RE.match(bare) else "")
            if lang.lower() in COMMAND_LANGS:
                errors.append(
                    f"{path.name}:{i + 1}: §8.12 must contain no command fences "
                    f"(found ```{lang or '<untagged>'}). Commands belong in "
                    "runsheet.md; this section owns why they exist. A section "
                    "that may not hold a command cannot hold a stale one")
        in_fence = not in_fence

    # one-to-one with the steps
    named: dict[str, str] = {}
    for i in range(start, end):
        m = RUNBOOK_812_SUB.match(lines[i])
        if not m:
            continue
        sub, num, tail = m.group(1), m.group(2), m.group(3)
        if num == "0":                      # 8.12.0 is a pointer, not a step's why
            continue
        ids = re.findall(r"`(A\d+\.\d+)`", tail)
        if len(ids) != 1:
            errors.append(
                f"{path.name}:{i + 1}: §{sub} names {len(ids)} runsheet steps in "
                "its heading, and it must name exactly one. Without it, a reader "
                "in one file cannot find the other half in the other")
            continue
        if ids[0] not in step_ids:
            errors.append(f"{path.name}:{i + 1}: §{sub} names step {ids[0]}, "
                          "which runsheet.md does not have")
            continue
        if ids[0] in named:
            errors.append(f"{path.name}:{i + 1}: §{sub} and §{named[ids[0]]} both "
                          f"claim to explain {ids[0]}")
            continue
        named[ids[0]] = sub
        want = f"§{sub}"
        if want not in why.get(ids[0], ""):
            errors.append(
                f"{path.name}:{i + 1}: §{sub} says it explains {ids[0]}, but that "
                f"step's 為什麼 column names {why.get(ids[0], '(nothing)')!r}. "
                "The pairing has to hold from both ends or one of them is wrong")

    # And the other direction: a step may point at §8.12.N only if §8.12.N points
    # back. Without this, a step could name a subsection that explains a
    # different step and nothing would say so from the runsheet's side.
    back = {v: k for k, v in named.items()}
    for step, cell in sorted(why.items()):
        for sub in re.findall(r"§\s?(8\.12\.\d+)", cell):
            if named.get(step) != sub:
                errors.append(
                    f"runsheet.md: step {step} names §{sub} as its 為什麼, but "
                    f"§{sub} names {back.get(sub, 'nothing')}. "
                    "One of the two is pointing at the wrong half")


def check(path: Path, runbook: Path) -> int:
    text = path.read_text("utf-8")
    lines = text.splitlines()
    errors: list[str] = []
    warnings: list[str] = []

    targets = makefile_targets()
    headings = runbook_headings(runbook)
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
            # ...and for the flags whose value argparse restricts, the value.
            choices = declared_choices(h)
            for fm in re.finditer(
                    r"(?<![\w-])(--[a-z][a-z0-9-]*)[= ]+([^\s\|;)&]+)", tail):
                flag, raw = fm.group(1), fm.group(2)
                if flag not in choices:
                    continue
                val = raw.strip("'\"")
                # A shell variable, a substitution, or the next flag: this check
                # reads commands, not the shell, and guessing what `$PROFILE`
                # expands to would turn a real check into a plausible one.
                if not val or val[0] in "-$`" or "$" in val:
                    continue
                if val not in choices[flag]:
                    errors.append(
                        f"{path.name}:{ln}: {rel} rejects `{flag} {val}` "
                        f"(it accepts: {', '.join(sorted(choices[flag]))})")

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

    # ---- stations and step anatomy -------------------------------------
    steps: list[tuple[str, int, str]] = []      # id, line, heading
    station_at: dict[int, int] = {}             # line -> station number
    for i, line in enumerate(lines, 1):
        m = STATION_RE.match(line)
        if m:
            station_at[i] = int(m.group(1))
        m = STEP_RE.match(line)
        if m:
            steps.append((m.group(1), i, line))
    if not steps:
        errors.append(f"{path.name}: no `### A<station>.<n>` steps found — "
                      "the file's shape changed")
    if not station_at:
        errors.append(f"{path.name}: no `## 第 N 站` station headings found. "
                      "The station number IS the device state a step needs, so "
                      "without them a reader has no way to know it")

    closes: dict[str, list[str]] = {}
    why: dict[str, str] = {}
    partb = text.find("# Part B")
    for j, (name, ln, heading) in enumerate(steps):
        end = steps[j + 1][1] if j + 1 < len(steps) else (
            len(lines) if partb < 0 else next(
                (i for i, s in enumerate(lines, 1) if s.startswith("# Part B")),
                len(lines)))
        body = "\n".join(lines[ln:end])

        # the station the step is filed under must match its own first digit
        want = int(name[1:].split(".")[0])
        current = None
        for line_no in sorted(station_at):
            if line_no < ln:
                current = station_at[line_no]
        if current is not None and current != want:
            errors.append(
                f"{path.name}:{ln}: step {name} sits under 第 {current} 站. "
                f"Its number says 第 {want} 站, and the number is what tells a "
                "reader what state the board has to be in")

        # The heading being under the right station is not the same as the
        # *commands* being runnable in that station's device state, and the
        # check above only ever saw the heading. A3.24 carried a
        # `console-dump.py dump --at-prompt` for a year of revisions: that flag
        # means "the board is already sitting at <RealTek>", which is 第 2 站,
        # inside a step filed under 第 3 站 where the board is booted and
        # serving. Reading A1.1 -> A4.2 front to back is supposed to BE a
        # correct order to run it in; a step that cannot execute where it sits
        # breaks that promise silently. Found 2026-08-19, alongside the same
        # command naming the wrong flash offset. PROGRESS open item 71.
        # Only command fences, and only where the prose has not already sent the
        # reader to the other station. A3.8's recovery path legitimately says
        # "回 A2.2 搶 bootloader" and then gives a boot-loader
        # command; that is a correct instruction, not a misfiled step. So the
        # escape hatch is naming the station you are sending the reader to --
        # which is the thing that makes it correct in the first place.
        for cmd_line, cmd_text in commands:
            if not (ln < cmd_line < end):
                continue
            for marker, only_in, what in STATE_MARKERS:
                if marker not in cmd_text or want == only_in:
                    continue
                lead = NL.join(lines[max(0, cmd_line - 14):cmd_line])
                if re.search(rf"A{only_in}\.\d|第 {only_in} 站", lead):
                    continue
                errors.append(
                    f"{path.name}:{cmd_line}: step {name} is filed under 第 "
                    f"{want} 站 and runs `{marker}`, which needs 第 {only_in} 站 "
                    f"({what}). The station number IS the device state, so this "
                    "command cannot be run where the document puts it. If it is "
                    f"a deliberate detour, say so: name A{only_in}.x or 第 "
                    f"{only_in} 站 in the lines above it")

        # what it closes: from the heading, and nowhere else
        m = CLOSES_RE.search(heading)
        if m:
            ids = re.findall(r"P\d+-\d+", m.group(1))
            if not ids:
                errors.append(f"{path.name}:{ln}: step {name}'s {CLOSES_SHOWN} "
                              "names no test id")
            closes[name] = ids
        elif NOCLOSE in heading:
            closes[name] = []
        else:
            errors.append(
                f"{path.name}:{ln}: step {name}'s heading ends with neither "
                f"{CLOSES_SHOWN} nor {NOCLOSE}. Silence there is indistinguishable "
                "from a forgotten field, and the coverage check below is only "
                "as good as that distinction")

        # the four-field table
        if META_HEADER not in body:
            errors.append(
                f"{path.name}:{ln}: step {name} declares no "
                "層/動到裝置/為什麼這一節存在/最後驗證 table. The preamble "
                "promises a reader every step carries those four")
            continue
        rows = [r for r in body.split("\n")
                if r.startswith("|") and "---" not in r and r != META_HEADER]
        if not rows:
            errors.append(f"{path.name}:{ln}: step {name}'s table has a header "
                          "and no row")
            continue
        cells = [c.strip() for c in rows[0].strip("|").split("|")]
        if len(cells) != 4:
            errors.append(f"{path.name}:{ln}: step {name}'s table row has "
                          f"{len(cells)} cells, expected 4")
            continue
        why[name] = cells[2]
        if not re.search(r"§\s?\d+(\.\d+)*", cells[2]):
            errors.append(
                f"{path.name}:{ln}: step {name}'s 為什麼這一節存在 names no "
                "RUNBOOK section. Two files only divide the work if each points "
                "at the other")
        if not re.search(r"\d{4}-\d{2}-\d{2}", cells[3]):
            errors.append(
                f"{path.name}:{ln}: step {name}'s 最後驗證 names no date. "
                "A reader has to know how old these commands are")
    if partb < 0:
        errors.append(f"{path.name}: no `# Part B` section — per-week run orders live there")

    # ---- the front-page index ------------------------------------------
    #
    # The index repeats the ids in the headings, and repetition is exactly what
    # this repository forbids -- unless a machine keeps the two the same. This is
    # that machine, so the index is a pointer rather than a second owner.
    idx: dict[str, list[str]] = {}
    part_a_line = next((k for k, s in enumerate(lines, 1)
                        if s.startswith("# Part A")), len(lines))
    for line in lines[:part_a_line]:
        m = re.match(r"^\|\s*`(A\d+\.\d+)`\s*\|(.*)\|(.*)\|\s*$", line)
        if m:
            idx[m.group(1)] = re.findall(r"P\d+-\d+", m.group(3))
    if steps:
        if not idx:
            errors.append(f"{path.name}: no front-page index rows found. The 目錄 "
                          "is how a reader sees the whole procedure at once")
        missing = [s for s, _, _ in steps if s not in idx]
        surplus = [s for s in idx if s not in {x for x, _, _ in steps}]
        if missing:
            errors.append(f"{path.name}: the 目錄 does not list {', '.join(missing)}")
        if surplus:
            errors.append(f"{path.name}: the 目錄 lists {', '.join(surplus)}, "
                          "which is not a step")
        for s, _, _ in steps:
            if s in idx and set(idx[s]) != set(closes.get(s, [])):
                errors.append(
                    f"{path.name}: the 目錄 says {s} closes "
                    f"{sorted(idx[s]) or '—'} but its heading says "
                    f"{sorted(closes.get(s, [])) or '—'}")

    # ---- coverage: 27 results should mean 27 reproducible paths ---------
    #
    # Asked by the author on 2026-08-17: "we closed 27 tests this week -- should
    # there not be 27 things somebody can re-run?" Yes. And when that was
    # measured, runsheet.md named exactly ONE of the 27.
    #
    # A registered test whose result nobody can reach a procedure for is a
    # finding a reader has to take on trust, which is the thing this whole
    # repository is arranged against. So each step declares which tests it
    # closes, and this checks it in BOTH directions:
    #
    #   * a test id a step claims must exist in the register (no typos, no
    #     invented ids -- a mapping that names P9-99 looks like coverage);
    #   * every executed test must be claimed by at least one step, or listed
    #     in the "no procedure" block below with a reason.
    #
    # The second direction is the one that matters. The first would pass on an
    # empty mapping.
    reg = REPO / "test-cases.toml"
    results = REPO / "reports/test-results.json"
    if reg.is_file() and results.is_file():
        import json as _json
        import tomllib
        doc = tomllib.loads(reg.read_text("utf-8"))
        cases = {c["id"]: c for c in doc.get("case", [])}
        executed = {r["id"] for r in
                    _json.loads(results.read_text("utf-8")).get("results", [])}

        claimed: dict[str, list[str]] = {}
        for name, ids in closes.items():
            for cid in ids:
                claimed.setdefault(cid, []).append(name)
        if not claimed:
            errors.append(
                f"{path.name}: no step claims to close any registered test. "
                f"Either the {CLOSES_SHOWN} annotation was removed or its shape "
                "changed, and the coverage check below would then pass over "
                "nothing")

        for cid, where in sorted(claimed.items()):
            if cid not in cases:
                errors.append(
                    f"{path.name}: step {'/'.join(where)} claims to close {cid}, "
                    "which is not in the register")

        # Steps close tests for the weeks the runsheet actually covers. A test
        # from a week whose sections are not written yet is not a gap.
        covered_weeks = set(re.findall(r"(?m)^## B-(W\d+)", text))
        owed = {cid for cid in executed
                if cid in cases
                and str(cases[cid].get("week")) in covered_weeks
                and not str(cases[cid].get("cut_reason", "")).strip()}
        # An explicit escape hatch, because some results genuinely have no
        # procedure -- and saying which, with a reason, is honest where silence
        # is not.
        # findall, not search. `search` takes the FIRST match, and on 2026-08-18
        # the first match was the appendix paragraph *explaining* this mechanism,
        # which quotes `<!-- no-procedure: ... -->` inline and therefore parses as
        # an empty exemption block sitting above the real one. Two genuinely
        # exempted cases were reported as unexempted and the block naming them was
        # never read. A checker defeated by its own documentation is the same
        # shape as bugs 22, 23 and 28: the text and the thing it describes are
        # different objects, and only one of them was being looked at.
        exempt = set()
        for block in re.findall(r"(?s)<!--\s*no-procedure:(.*?)-->", text):
            exempt |= set(re.findall(r"\b(P\d+-\d+)\b", block))
        gap = sorted(owed - set(claimed) - exempt)
        if gap:
            errors.append(
                f"{path.name}: {len(gap)} executed test(s) that no step claims "
                f"and no exemption names: {', '.join(gap)}.\n"
                "        A result nobody can reach a procedure for is a claim a "
                f"reader has to take on trust. Add it to a step's {CLOSES_SHOWN}, or "
                "name it in the `<!-- no-procedure: ... -->` block with a reason.")
        covered = len(owed & set(claimed))

        # ---- the direction that fires BEFORE the session, not after -----
        #
        # Everything above keys on `executed`, and that is the defect it took
        # until 2026-08-18 to notice. A row acquires a result, and only then
        # does anything demand a procedure for it -- so the runsheet has never
        # once been written before a session. W05 and W06 read as fully covered
        # because they are finished. W07 read as fully covered because it had
        # not started: 58 live rows, 2 claimed, 11 exempted, 47 with neither,
        # and 32 of those scheduled for a bench visit the same evening.
        #
        # The half of this that hurt: P2-11, the 601-second window, went into
        # the bench plan with the words "this has no procedure and it cannot be
        # improvised on the night", and no tool could say so. Back-filling a
        # runsheet is not the same document as following one, and only the
        # second kind can be wrong in a way you find out about in time.
        #
        # So: the same rule, one step earlier. Every LIVE row scheduled for a
        # week this runsheet claims to cover needs a step or a reason, whether
        # or not it has run. Part B is append-only, so adding a `## B-W0N`
        # block is the act that turns this on for that week, and it cannot be
        # quietly turned off again.
        scheduled = {cid for cid, c in cases.items()
                     if str(c.get("week")) in covered_weeks
                     and not str(c.get("cut_reason", "")).strip()}
        unplanned = sorted(scheduled - executed - set(claimed) - exempt)
        if unplanned:
            errors.append(NL.join([
                f"{path.name}: {len(unplanned)} scheduled test(s) with no "
                f"procedure and no exemption: {', '.join(unplanned)}.",
                "        These are rows a session is expected to close, and "
                "nothing here says how.",
                "        Write the step, or name it in the "
                "`<!-- no-procedure: ... -->` block with a reason.",
                "        A row that reaches the bench with no written step gets "
                "improvised, and an",
                "        improvised step is one whose ordering constraints are "
                "discovered afterwards.",
            ]))
    else:
        covered = 0
        warnings.append(f"{path.name}: no register or results file; coverage unchecked")

    # ---- the other half of the split -----------------------------------
    #
    # Only for the real runsheet: a synthetic fixture has one step, and holding
    # the whole of §8.12 to a one-to-one pairing with it would make every
    # fixture-based case fail for the same unrelated reason. The guard suite
    # exercises this half by passing the real runsheet with a doctored
    # `--runbook`.
    if path.resolve() == (REPO / "runsheet.md").resolve():
        check_runbook_812(runbook, errors, [s for s, _, _ in steps], why)

    # ---- report --------------------------------------------------------
    for w in warnings:
        print(f"  warn  {w}", file=sys.stderr)
    if errors:
        for e in errors:
            print(f"  FAIL  {e}", file=sys.stderr)
        return 1
    print(f"runsheet OK — {len(steps)} steps in {len(station_at)} stations, "
          f"{len(commands)} command lines, {len(seen_make)} make targets, "
          f"{len(helps)} tools checked against their own --help, "
          f"{untagged} untagged fences, {covered} executed tests reachable")
    return 0


def main(argv: list[str]) -> int:
    for s in (sys.stdout, sys.stderr):
        with contextlib.suppress(AttributeError, ValueError):
            s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runsheet", nargs="?", default=str(REPO / "runsheet.md"),
                    type=Path)
    ap.add_argument("--runbook", default=str(REPO / "RUNBOOK.md"), type=Path,
                    help="the other half of the split; override it to let the "
                         "guard suite prove the §8.12 rules can fail")
    args = ap.parse_args(argv[1:])
    for f in (args.runsheet, args.runbook):
        if not f.is_file():
            print(f"no such file: {f}", file=sys.stderr)
            return 2
    return check(args.runsheet, args.runbook)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
