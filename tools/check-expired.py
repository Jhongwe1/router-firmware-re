#!/usr/bin/env python3
"""Sentences that were true until a dated event, and false in the present tense after it.

Why this exists
---------------
W07 found **six committed files, one of them the disclosure register, asserting
`52869/tcp open` in the present tense** — sourced to a sweep from 2026-08-16,
while the same repository recorded the port **closed** on 2026-08-18 because this
project's own unauthenticated POST had killed the daemon. Both readings were
right when taken. Neither sentence carried a date.

The six were fixed. **The corpus was not swept**, and on 2026-09-25 the same
shape was still alive in eight files, in the most damaging form available:

    "No device has been powered on."

in `notes/auth-flow.md`, `notes/sink-inventory.md`,
`notes/submit-url-overflow.md`, `notes/credentials.md` and four more — six weeks
after this unit was first powered, in the same repository whose own `README`
said the device had been serving since 2026-08-15. A reader who opened
`sink-inventory.md` first was told, flatly, that nothing had been measured.

The failure is not that the sentences were written. They were **true when
written** and writing them was correct. The failure is that *"true on the day"*
and *"true"* look identical in a file with no date on it, and nothing in this
repository could tell them apart.

What it checks
--------------
A table of **expired assertions**: a phrase, the date it stopped being true, and
what replaced it. Any tracked file outside `journal/` that still contains the
phrase fails — **unless the same line carries a date on or before the expiry**,
which is what turns a present-tense claim back into a dated observation and is
exactly the fix.

    notes/img/pcb-top-annotations.json:
      "W02 Day 1, 2026-08-14. ... No device has been powered on."   <- passes

`journal/` is exempt by design. `PROGRESS.md`, `LOG.md` and `BENCH-LOG.md`
record what was believed on a day; rewriting them would destroy the only
evidence that the belief changed.

**Code formatting is a quotation mark.** The first run flagged five lines and
four of them were *this repository discussing the bug* — `writeup/11-bughunt.md`
saying *"asserted `52869/tcp open` in the present tense"*, and the correction
section of `writeup/02-corpus.md` naming the phantom image it had just removed.
So a match inside a fenced block or an inline code span is a **quoted artefact,
not a claim in the author's voice**, and it is skipped. That rule works here
because this repository backticks everything it quotes; it would not work in
prose that does not.

The eight files that actually failed had the sentence in plain prose, in the
author's voice, which is exactly the distinction that matters.

What it deliberately does NOT do
--------------------------------
It does not find *new* expired assertions — it cannot, because "this sentence
has an unstated time dependency" is not a property of the text. Every row below
was found by a person and is here so that it stays found. **The register is the
deliverable, not the scanner**, and a row costs three lines to add on the day
someone notices.

    python3 tools/check-expired.py
    python3 tools/check-expired.py --list    # the register, with dates
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
FENCE = re.compile(r"^(```|~~~).*?^\1", re.MULTILINE | re.DOTALL)
CODE = re.compile(r"`[^`\n]*`")


def blank(m: re.Match[str]) -> str:
    """Replace with spaces, keeping every newline so line numbers survive."""
    return re.sub(r"[^\n]", " ", m.group(0))

# (expiry date, phrase regex, what is true now, where the evidence is)
EXPIRED: list[tuple[str, str, str, str]] = [
    (
        "2026-08-15",
        r"[Nn]o device has been powered on",
        "this unit has been powered and serving since 2026-08-15",
        "journal/PROGRESS.md W02, journal/BENCH-LOG.md 2026-08-15",
    ),
    (
        "2026-08-15",
        r"the hardware has not arrived",
        "the hardware arrived 2026-08-14 and was powered 2026-08-15",
        "journal/PROGRESS.md W02",
    ),
    (
        "2026-08-16",
        r"W02 is blocked on hardware",
        "W02 closed 2026-08-16; G2 passed",
        "README.md gate board, journal/PROGRESS.md W02",
    ),
    (
        "2026-08-16",
        r"(?:is|as) a W02 task",
        "W02 closed 2026-08-16 — say what it answered, or that it did not",
        "journal/PROGRESS.md W02",
    ),
    (
        "2026-08-18",
        r"52869/tcp\s+open",
        "closed since 2026-08-18: this project's own POST round killed the daemon",
        "notes/three-unread-binaries.md, journal/PROGRESS.md W07",
    ),
    (
        "2026-08-23",
        r"(?:will be|to be) reported to TWCERT",
        "nothing is reported to anyone; everything is published",
        "docs/disclosure.md, the decision of 2026-08-23",
    ),
    (
        "2026-09-25",
        r"\bV4\.1\.5cu\b",
        "no such image exists in this project; the corpus is in firmware/SOURCES.json",
        "writeup/02-corpus.md, the correction section",
    ),
]


# The register necessarily contains every phrase it registers, and the guard
# suite necessarily feeds them to it. Scanning either is a tautology, not a
# check. Named explicitly rather than pattern-matched, so that adding a file
# here is a visible decision -- and found by the guard suite rather than by a
# person, because the real repository had not yet staged this file when the
# first run came back clean.
SELF = {"tools/check-expired.py", "tools/test-check-expired.sh"}


def tracked() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout
    return [
        p for p in out.split("\0")
        if p and not p.startswith("journal/") and p not in SELF
    ]


def dated_before(line: str, expiry: str) -> bool:
    """True if the line carries a date on or before the expiry.

    A dated observation is not an expired assertion. This is the whole fix for
    the class, and the checker has to accept the fix or it teaches people to
    delete evidence instead of dating it.
    """
    return any(m.group(0) <= expiry for m in DATE.finditer(line))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--list", action="store_true", help="print the register and stop")
    args = ap.parse_args()

    if args.list:
        print(f"  {len(EXPIRED)} expired assertions on the register:")
        for expiry, pattern, now, where in EXPIRED:
            print(f"    {expiry}  /{pattern}/")
            print(f"              now: {now}")
            print(f"              see: {where}")
        return 0

    compiled = [(e, re.compile(p), n, w) for e, p, n, w in EXPIRED]
    found: list[str] = []
    dated: list[str] = []
    scanned = 0

    for rel in tracked():
        path = REPO / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # binary, or not ours to read
        scanned += 1
        # A match inside a fence or a code span is a quotation of the assertion,
        # not the assertion. Blanked rather than removed so that the line
        # numbers and the `>>>` echo below still point at the real source line.
        raw = text.splitlines()
        text = CODE.sub(blank, FENCE.sub(blank, text))
        for lineno, line in enumerate(text.splitlines(), 1):
            for expiry, pattern, now, where in compiled:
                if not pattern.search(line):
                    continue
                if dated_before(line, expiry):
                    dated.append(f"{rel}:{lineno}: dated on or before {expiry}")
                    continue
                found.append(
                    f"{rel}:{lineno}: stopped being true on {expiry}\n"
                    f"      now: {now}\n"
                    f"      see: {where}\n"
                    f"      fix: state the date it was measured, or say what is true now\n"
                    f"      >>>  {raw[lineno - 1].strip()[:100]}"
                )

    if found:
        print(f"check-expired: {len(found)} assertion(s) outlived the fact they describe")
        for f in found:
            print(f"  {f}")
        return 1

    print(
        f"  ok   check-expired: {len(EXPIRED)} expired assertions, none present in "
        f"{scanned} tracked files outside journal/ "
        f"({len(dated)} carried a date on or before their expiry and are fine)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
