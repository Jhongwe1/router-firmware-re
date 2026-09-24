#!/usr/bin/env python3
"""A number on the front door agrees with the thing that generates it.

Why this exists
---------------
`tools/count-checks.sh` opens with the diagnosis:

    REPRODUCE.md's front page tells a stranger the number. It said 276 ... until
    2026-08-18, when a recount made it 322 -- and the same recount put the
    pre-session figure at 304, so it had been wrong before this session touched
    anything. **Nothing was checking it, and a number on the front door that
    nobody can re-derive is worth less than no number.**

The medicine was written and never taken. `count-checks.sh` was not wired into
`make ci`, and by 2026-09-25 the front page said **592** where a recount said
**593**, and **130 tests** where the register held **141** -- on the same page
that said 141 a hundred and forty lines further down.

Why the medicine was not taken, and what changes here
-----------------------------------------------------
`count-checks.sh`'s footer gives a real reason not to wire it in:

    It is not checked in CI on purpose: a suite that grows should not turn the
    build red.

That is correct about **asserting a constant** and it is the wrong conclusion.
Pinning the total to 593 goes red the next time anyone adds a test. Asserting
that **the prose equals the recount** goes red only when the prose is stale,
which is the defect. The distinction is between checking a value and checking an
agreement, and only the second is maintainable.

How this checker is built, and why not the obvious way
------------------------------------------------------
The first version scanned prose for `N tests`, `N checks`, `N items cut`. It
reported 18 disagreements on its first run and **13 of them were the checker**:

    `2015 checks strstr(uri,"htm")`    -- "checks" is a verb
    `Fifteen registered tests cannot be run at this desk`   -- a subset, correctly 15
    `Three registered tests are frozen against it`          -- a subset
    `the nine items cut for`                                -- a subset

English gives a total and a subset the same grammar, so no amount of pattern
work separates them. That was the third instrument this week to fail in the
direction of *finding something*, after the two in `check-links.py`.

So the design is inverted. This file carries a **table of claim sites**: the
specific sentences on the front door that state a total, each with the generator
that owns it. Two consequences, and the second is the load-bearing one:

  * a number that drifts is caught, because the site is checked;
  * **a site that stops matching is also a failure.** If a sentence is rewritten
    or deleted, the checker says so rather than quietly covering less. A guard
    that silently narrows is instrument bug 12, which went green for a year on a
    corpus that never contained what it was looking for.

The cost is that a *new* total in a *new* sentence is invisible until someone
adds it here. That is a real hole and it is the honest trade: this checker
knows what it covers and says how much, rather than appearing to cover prose it
cannot actually read.

    python3 tools/check-numbers.py
    python3 tools/check-numbers.py --checks 613 --pytest 130   # skip the recount
    python3 tools/check-numbers.py --show
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
        "seventy": 70, "eighty": 80, "ninety": 90}


def to_int(word: str) -> int | None:
    """`141`, `Twenty-three` and `fifty-six` are the same kind of claim."""
    w = word.strip().lower().replace(",", "")
    if w.isdigit():
        return int(w)
    if w in UNITS:
        return UNITS[w]
    if w in TENS:
        return TENS[w]
    if "-" in w:
        a, _, b = w.partition("-")
        if a in TENS and b in UNITS and UNITS[b] < 10:
            return TENS[a] + UNITS[b]
    return None


# A number written either way. Kept as one fragment so every site spells it the
# same: a site that accepted only digits would go quiet the day someone wrote
# the number out, which is the failure this checker is built to not have.
N = r"([0-9]{1,4}|[A-Za-z]+(?:-[a-z]+)?)"

# -----------------------------------------------------------------------------
# The claim sites.
#
#   (owner key, file, regex, what the sentence is)
#
# Every one of these must match at least once. Rewriting the sentence is fine --
# update the pattern in the same commit, which is the point at which someone
# looks at the number.
# -----------------------------------------------------------------------------
SITES: list[tuple[str, str, str, str]] = [
    # ---- checks `make ci` runs -------------------------------------------
    ("checks", "README.md", r"make ci\s+#\s*" + N + r" checks", "the make ci comment"),
    ("checks", "README.md", r"\*\*" + N + r" checks\*\*, of which", "the 60-second table"),
    ("checks", "README.md", r"of the " + N + r" checks exist only to feed", "the method section"),
    ("guards", "README.md",
     r"\*\*" + N + r" exist to prove a tool can refuse\*\*", "the 60-second table"),
    ("guards", "README.md",
     r"refusing\.\*\* " + N + r" of the [0-9]+ checks", "the method section"),
    ("registered", "README.md",
     r"before the packet\.\*\* " + N + r" registered tests", "the method section"),
    ("frozen", "README.md",
     r"registered tests, " + N + r"\n  carrying a written statement", "the method section"),
    ("bugs", "README.md", r"wrong\*\* \| \*\*" + N + r"\*\*, all listed", "the 60-second table"),
    ("bugs", "README.md",
     r"- \*\*" + N + r" of my own instruments were wrong", "the method section"),
    ("bugs", "docs/how-this-was-built.md",
     r"a tool was lying\.\*\* " + N + r" times", "the AI-collaboration note"),
    ("checks", "REPRODUCE.md",
     N + r" checks that prove this project's own instruments can fail", "the T1 tier row"),
    ("checks", "REPRODUCE.md", r"make ci\s+#\s*←\s*the " + N + r" checks", "the make ci comment"),
    ("checks", "REPRODUCE.md",
     r"\*\*" + N + r" checks\*\* from a clone", "the 'runs all of them' paragraph"),
    ("checks", "writeup/14-limits.md",
     N + r" checks that prove this project's own", "the quoted T1 tier row"),
    ("checks", "writeup/15-disclosure.md",
     r"make ci\s+#\s*" + N + r" checks", "the make ci comment"),
    # ---- the split of that total ------------------------------------------
    ("guards", "REPRODUCE.md", r"\*\*" + N + r" guard cases across", "the guard/parser split"),
    ("guards", "writeup/12-instruments.md",
     N + r" guard\s*\n?cases across", "the guard/parser split"),
    ("checkers", "README.md",
     r"and \*\*" + N + r"\*\* consistency checkers", "the 60-second table"),
    ("suites", "REPRODUCE.md", r"guard cases across " + N + r" suites", "the suite count"),
    ("suites", "writeup/12-instruments.md", r"cases across " + N + r" suites", "the suite count"),
    ("pytest", "REPRODUCE.md", r"plus " + N + r" parser tests", "the parser-test count"),
    ("pytest", "writeup/12-instruments.md",
     r"plus " + N + r" parser tests", "the parser-test count"),
    # ---- the register -----------------------------------------------------
    ("registered", "README.md", r"\*\*" + N + r"\*\* registered tests", "the G3.75 evidence line"),
    ("registered", "README.md",
     r"generated\*\*\s*—\s*" + N + r" tests with their predictions", "the What-is-here row"),
    ("registered", "README.md",
     r"on the order of " + N + r" tests against one device", "the W05-W07 scope note"),
    ("registered", "REPRODUCE.md", r"The test register: " + N + r" tests", "the T1 contents list"),
    ("registered", "writeup/01-rules.md",
     N + r" registered tests, [0-9]+ with a written refutation", "the rules chapter"),
    ("frozen", "README.md",
     r"\*\*" + N + r"\*\* carrying a written refutation", "the G3.75 evidence line"),
    ("frozen", "writeup/01-rules.md",
     r"[0-9]+ registered tests, " + N + r" with a written refutation", "the rules chapter"),
    ("cut", "README.md",
     r"\*\*" + N + r" items were cut rather than run\*\*", "the cut-items note"),
    ("cut", "README.md", r"what \*\*" + N + r"\*\* items were cut", "the What-is-here row"),
    ("cut", "writeup/14-limits.md",
     N + r" of this register's rows were never executed", "the limits chapter"),
    # ---- instrument bugs --------------------------------------------------
    ("bugs", "writeup/12-instruments.md", r"^# 12\. " + N + r" instruments", "the chapter title"),
    ("bugs", "writeup/12-instruments.md",
     r"\*\*" + N + r" instrument bugs\.", "the closing sentence"),
    ("bugs", "writeup/README.md", r"what " + N + r" broken", "the subtitle"),
    ("bugs", "writeup/README.md", N + r" of my own instruments were wrong", "the TL;DR"),
    ("bugs", "writeup/README.md", r"\[" + N + r" instruments, [a-z-]+ bugs\]", "the chapter table"),
]


UNMEASURED: dict[str, str] = {}


def owners(checks: int | None, pytest_n: int | None) -> dict[str, int]:
    """Re-derive each number from the thing that owns it.

    Keys this environment cannot measure are left out and recorded in
    UNMEASURED instead. That distinction is the whole of instrument bug 61:
    the first version asserted `checks` everywhere, and on a GitHub runner --
    which has no pytest and no flashrom in the job that runs this -- the
    recount came back **468** against this workstation's **626**, so the
    checker reported fourteen correct numbers as stale. Same direction as 57
    through 60: inventing work.

    A missing key must NOT read as "the generator is broken", because the two
    need opposite responses -- one is a repository defect, the other is a fact
    about where the check is running, and only the first should fail a build.
    """
    out: dict[str, int] = {}
    UNMEASURED.clear()

    stats = subprocess.run(
        [sys.executable, "tools/rtcase.py", "stats"],
        cwd=REPO, capture_output=True, text=True,
    ).stdout
    for key in ("registered", "frozen", "executed"):
        m = re.search(r"(\d+)\s+" + key, stats)
        if m:
            out[key] = int(m.group(1))

    toml = (REPO / "test-cases.toml").read_text(encoding="utf-8")
    out["cut"] = len(re.findall(r"^cut_reason\s*=", toml, re.MULTILINE))

    out["suites"] = len(list((REPO / "tools").glob("test-*.sh")))
    out["checkers"] = len(list((REPO / "tools").glob("check-*.py")))

    # The instrument-bug count has no register of its own: chapter 12's table
    # *is* the list, and its highest row number is the count. That makes the
    # chapter the owner -- one piece of state, one owner -- so adding a row is
    # what moves the number everywhere else, which is the right direction of
    # causation. A separate register would be a second owner.
    ch12 = REPO / "writeup" / "12-instruments.md"
    if ch12.exists():
        body = ch12.read_text(encoding="utf-8")
        single = r"^\|\s*(\d+)(?:[-–]\d+)?\s*\|"  # noqa: RUF001
        ranged = r"^\|\s*\d+[-–](\d+)\s*\|"  # noqa: RUF001
        nums = [int(n) for n in re.findall(single, body, re.MULTILINE)]
        nums += [int(n) for n in re.findall(ranged, body, re.MULTILINE)]
        if nums:
            out["bugs"] = max(nums)

    if checks is not None and pytest_n is not None:
        out["checks"], out["pytest"] = checks, pytest_n
    else:
        table = subprocess.run(
            ["bash", "tools/count-checks.sh"], cwd=REPO,
            capture_output=True, text=True,
        ).stdout
        incomplete = re.search(r"^INCOMPLETE:(.*)$", table, re.MULTILINE)
        if incomplete:
            # count-checks.sh could not run every suite here, so its total is
            # a floor rather than the number. Refuse to judge the prose
            # against it rather than judging it against a floor.
            why = incomplete.group(1).strip()
            for k in ("checks", "guards", "pytest"):
                UNMEASURED[k] = (
                    f"count-checks.sh could not run: {why}. Its total is a "
                    f"floor here, not the count"
                )
            return out
        m = re.search(r"^\s*total\s+(\d+)\s*$", table, re.MULTILINE)
        p = re.search(r"fwrecon pytest\s+(\d+)", table)
        if m:
            out["checks"] = int(m.group(1))
        if p:
            out["pytest"] = int(p.group(1))
    if "checks" in out and "pytest" in out:
        out["guards"] = out["checks"] - out["pytest"]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--checks", type=int, default=None,
                    help="the count-checks.sh total, if already computed")
    ap.add_argument("--pytest", type=int, default=None,
                    help="the fwrecon pytest count, if already computed")
    ap.add_argument("--show", action="store_true", help="print each owner's value and stop")
    args = ap.parse_args()

    truth = owners(args.checks, args.pytest)
    if args.show:
        for k, v in sorted(truth.items()):
            print(f"  {k:12} {v}")
        return 0

    wrong: list[str] = []
    missing: list[str] = []
    skipped: set[str] = set()
    agreed = 0
    cache: dict[str, str] = {}

    for key, rel, pattern, what in SITES:
        if key in UNMEASURED:
            skipped.add(key)
            continue
        if key not in truth:
            missing.append(f"{key}: no generator produced a value -- "
                           f"the owner is broken, not the prose")
            continue
        path = REPO / rel
        if not path.exists():
            missing.append(f"{rel}: the file this claim site lives in is gone ({what})")
            continue
        if rel not in cache:
            cache[rel] = path.read_text(encoding="utf-8")
        text = cache[rel]
        hits = list(re.finditer(pattern, text, re.MULTILINE))
        if not hits:
            missing.append(
                f"{rel}: the claim site for '{key}' no longer matches ({what}).\n"
                f"      Either the sentence was rewritten -- update the pattern in "
                f"tools/check-numbers.py -- or the number was dropped."
            )
            continue
        for m in hits:
            claimed = to_int(m.group(1))
            line = text.count("\n", 0, m.start()) + 1
            if claimed is None:
                wrong.append(f"{rel}:{line}: '{m.group(1)}' is not a number "
                             f"this checker can read ({what})")
            elif claimed != truth[key]:
                wrong.append(
                    f"{rel}:{line}: {what} says {claimed}, the generator re-derives "
                    f"{truth[key]} ({key})"
                )
            else:
                agreed += 1

    for key in sorted(skipped):
        print(f"  note  {key}: not judged here -- {UNMEASURED[key]}")

    if missing or wrong:
        print(f"check-numbers: {len(wrong)} stale number(s), "
              f"{len(missing)} claim site(s) not found")
        for m in missing:
            print(f"  {m}")
        for w in wrong:
            print(f"  {w}")
        return 1

    judged = len(SITES) - sum(1 for k, _, _, _ in SITES if k in skipped)
    print(f"  ok   check-numbers: {agreed} claim(s) at {judged} of {len(SITES)} sites agree "
          f"with their generators "
          f"({', '.join(f'{k}={v}' for k, v in sorted(truth.items()))})"
          + (f"; {len(skipped)} owner(s) not measurable here" if skipped else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
