#!/usr/bin/env python3
"""Lift the acceptance criteria out of the private week plans into docs/gates.md.

Why this exists
---------------
`README.md` said, of the gate board:

    The gates below are the acceptance criteria from the week plans in
    [`plan/`](plan/) -- copied, not invented after the fact.

`plan/` is gitignored. The sentence sent a reader to a 404, which is worse than
not making the claim: the whole weight of the gate board is that a stranger can
go and check that the standard was written before the work, and the link that
was supposed to let them do it did not exist.

Publishing `plan/` wholesale is not the fix. Those files are working documents
addressed to the author -- `W04`'s section 四 is a set of interview answers, in
the first person, of exactly the shape `CLAUDE.md`'s house style forbids in a
committed file. Publishing them would trade one problem for a worse one.

So this extracts the part that is a *standard* and leaves the part that is a
*schedule* or a *rehearsal*. What comes out:

    the week's stated goal, its precondition, its gate, and its acceptance
    checklist, verbatim

What stays behind:

    the day-by-day schedule, the time budgets, the stop-losses, and every
    section written to the author rather than to a reader

What this proves, and what it does not
--------------------------------------
It proves the extract matches the plan files **as they are now**. It does not
date them: `plan/` has no git history, because it is not tracked, so nothing
here can show a plan was not edited afterwards. Saying otherwise would be the
same error the 404 was.

What does date them is in this repository, and a reader can check it without
trusting the author: the **first commit of `PROGRESS.md`** -- `b085444`,
2026-08-07, the day W01 closed and nine days before the hardware arrived --
already carries the full W01--W10 table with G0--G5 assigned to their weeks.
Every later gate was met against a standard that commit had already fixed. That
is the sentence `README.md` should have been making, and `docs/gates.md` makes
it with the commit named.

The criteria are reproduced in the language they were written in. A translation
would be a rewrite, and the claim this page exists to support is that nothing
was rewritten. A one-line English gloss is added per week, marked as a gloss.

    python3 tools/extract-gates.py            # write docs/gates.md
    python3 tools/extract-gates.py --check    # fail if the committed file drifted
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLANS = REPO / "plan"
OUT = REPO / "docs" / "gates.md"

PLAN_NAME = re.compile(r"^(W\d{2}(?:-\d)?)_")
# The header fields that state a standard. `專案`, `日期` and `週預算` are
# scheduling and are deliberately not lifted.
KEEP_FIELDS = ("週次", "前置條件", "本週目標", "Gate")
# The acceptance section, however each week numbered it: 三/四/五, 驗收門檻 or DoD.
ACCEPT = re.compile(r"^##\s*[一二三四五六七八九十]+、.*(?:驗收門檻|DoD).*$", re.MULTILINE)

GLOSS = {
    "W01": "Toolchain green, and the seven structural facts answered from measurement "
           "rather than from a spec sheet.",
    "W02": "A boot log and a flash dump off the unit itself, cross-checked against the "
           "vendor image.",
    "W03": "No formal gate. The dispatch table found, and at least one authentication "
           "candidate.",
    "W04": "Point at the instruction a CVE lives on, and say why it is wrong.",
    "W04-2": "Three builds read across, the configuration region decoded, and the next "
             "target chosen from evidence.",
    "W05": "No formal gate. A prediction scorecard completed, and one repeatable dynamic "
           "path standing up.",
    "W06": "One chain reproduced end to end, with the evidence layer named at each link.",
    "W07": "No formal gate. Twelve sinks under verdict, each verdict pointing back at a "
           "report.",
    "W08": "No formal gate. Every chapter carries content, and every claim points at a "
           "regenerable artefact.",
    "W09": "Published, legible to a stranger in ten minutes, one full chain, and every "
           "claim naming the binary it was measured on.",
    "W10": "No gate. Buffer week.",
}

PREAMBLE = """# Gates — the acceptance criteria, copied from the week plans

Every ✅ on the board in [`README.md`](../README.md) is scored against one of the
checklists below. They are **not** written here; they are lifted verbatim out of
the ten week plans by [`tools/extract-gates.py`](../tools/extract-gates.py), and
`make check-gates` fails if this file and those plans have drifted apart.

## Why the plans themselves are not in this repository

They are working documents addressed to the author: day-by-day schedules, time
budgets, stop-losses, and — in `W04` and `W09` — sections that rehearse how to
answer an interview question. `CLAUDE.md`'s house style forbids that register in
a committed file, and publishing the plans to fix a broken link would have
traded a small problem for a larger one. What is a *standard* is here; what is a
*schedule* or a *rehearsal* is not.

## What this page proves, and what it does not

It proves that the text below matches the plan files **as they are now**. It
does **not** date them. `plan/` is untracked, so nothing in it has a history,
and no hash printed here can show that a criterion was not softened after the
fact.

What does date them is in this repository, and it needs no trust:

> **The first commit of `PROGRESS.md` — [`b085444`](../journal/PROGRESS.md),
> 2026-08-07 — already carries the full W01–W10 table with G0–G5 assigned to
> their weeks**, on the day W01 closed and nine days before the hardware
> arrived. Every gate met after that date was met against a standard that commit
> had already fixed. `git log --diff-filter=A -- PROGRESS.md` is the whole check.

Where a plan turned out to be wrong, the correction is in
[`PROGRESS.md § Corrections`](../journal/PROGRESS.md) rather than in a quiet edit
here — `W04-2` and `G3.5` exist only because W02 found the unit runs a build
neither W03 nor W04 had read.

## A note on language

The criteria are reproduced in the language they were written in. A translation
would be a rewrite, and the claim this page exists to support is that nothing was
rewritten. The one-line English gloss under each heading is a **gloss added
here**, not part of the extract.

---
"""  # noqa: RUF001 - the en dashes above are ranges in generated Markdown
# prose, not code, and the rest of this repository writes ranges the same way.


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def section(text: str) -> str:
    """The acceptance section, from its heading to the next `## ` or rule."""
    m = ACCEPT.search(text)
    if not m:
        return ""
    rest = text[m.end():]
    stop = re.search(r"^(##\s|---\s*$)", rest, re.MULTILINE)
    body = rest[: stop.start()] if stop else rest
    return (m.group(0) + "\n" + body).rstrip()


def header(text: str) -> list[str]:
    out = []
    for line in text.splitlines()[:20]:
        if not line.startswith(">"):
            continue
        field = line.lstrip("> ").lstrip("*")
        for k in KEEP_FIELDS:
            if field.startswith(f"**{k}**"):
                out.append(line.rstrip())
                break
    return out


def build() -> str:
    if not PLANS.is_dir():
        return ""
    plans = []
    for p in sorted(PLANS.glob("W*.md")):
        m = PLAN_NAME.match(p.name)
        if m:
            plans.append((m.group(1), p))
    plans.sort(key=lambda t: (t[0][:3], t[0]))

    parts = [PREAMBLE]
    prov = ["| week | source file | SHA-256 of the source |", "|---|---|---|"]

    for week, p in plans:
        text = p.read_text(encoding="utf-8")
        head = header(text)
        body = section(text)
        parts.append(f"\n## {week}\n")
        gloss = GLOSS.get(week)
        if gloss:
            parts.append(f"*Gloss (added here, not part of the extract):* {gloss}\n")
        if head:
            parts.append("\n".join(head) + "\n")
        if body:
            parts.append("\n" + body + "\n")
        else:
            parts.append(
                "\n*This plan states its DoD in the header block above and carries no "
                "separate acceptance section.*\n"
            )
        prov.append(f"| `{week}` | `plan/{p.name}` | `{sha256(p)}` |")

    parts.append("\n---\n\n## Provenance\n\n")
    parts.append(
        "The SHA-256 of each source, so that a regeneration can be shown to have read the\n"
        "same bytes. As above: this pins the extract to the source, not the source to a\n"
        "date.\n\n"
    )
    parts.append("\n".join(prov) + "\n")
    parts.append(
        "\n<!-- Generated by tools/extract-gates.py. "
        "Do not edit; edit the plan and regenerate. -->\n"
    )
    return "".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="fail if docs/gates.md differs from a fresh extract")
    args = ap.parse_args()

    fresh = build()
    if not fresh:
        # plan/ is gitignored, so a GitHub runner does not have it. Saying so is
        # the point: a check that silently passes where its input is absent is
        # instrument bug 24 -- a self-check that passes because it never fires.
        print("  skip  extract-gates: plan/ is not present (gitignored); "
              "this check runs on the author's machine only")
        return 0

    if args.check:
        if not OUT.exists():
            print(f"check-gates: {OUT.relative_to(REPO)} does not exist; run make gates")
            return 1
        if OUT.read_text(encoding="utf-8") != fresh:
            print(f"check-gates: {OUT.relative_to(REPO)} differs from a fresh extract "
                  f"of plan/ -- run `make gates` and commit the result")
            return 1
        # Count the week headings this file writes, not every line that starts
        # "## W" -- the extracted sections carry their own headings and the first
        # version of this line counted those too, reporting 13 plans where there
        # are 11. A checker that miscounts in its own success message is the
        # thing this repository is least entitled to ship.
        n = len(re.findall(r"^## (W\d{2}(?:-\d)?)$", fresh, re.MULTILINE))
        print(f"  ok   check-gates: docs/gates.md matches all {n} week plans")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(fresh, encoding="utf-8", newline="\n")
    print(f"  ok   wrote {OUT.relative_to(REPO)} ({fresh.count(chr(10))} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
