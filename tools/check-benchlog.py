#!/usr/bin/env python3
"""Every record card in BENCH-LOG.md carries a refutation check.

Why this exists
---------------
`plan/Redteam_Testing_playbook.md` section 1.4 defines the record-card template
and ends with one rule in bold: **the refutation field may not be blank**, because
a test with no pre-written definition of failure will be read as a success after
the fact.

That template lived only in `plan/`, which is gitignored and which CLAUDE.md
forbids quoting into committed files. So **the format BENCH-LOG.md is supposed
to follow lived in a file BENCH-LOG.md is not allowed to cite**, and nothing in
the repository carried it. W05's cards followed it because the playbook had just
been reorganised and was still to hand. W06's first draft did not: nine prose
sections, six of them with no refutation field at all — written by the same
session that spent the evening insisting on exactly that rule.

A rule with no owner and no checker lasts until the person who wrote it forgets.
The owner is now BENCH-LOG.md's own header; this is the checker.

What it checks
--------------
For every card - a fenced block whose first line starts with ``T-`` followed by
digits:

  * a ``判定:`` line, with one of the four verdict markers;
  * a ``反證檢查:`` line that is **not** empty and that carries both halves:
    what was written down beforehand, and what was actually seen;
  * a date/time on the header line, because a card that cannot be placed in the
    session's order cannot be cross-checked against the console log.

What it deliberately does NOT check
-----------------------------------
The verbatim-request field, because ``docs/disclosure.md`` overrides the template
for anything not yet reported: those cards say the request is withheld and point
at the register row instead. Requiring a verbatim request here would force a
choice between failing CI and publishing a recipe for an unreported defect on a
device that is end-of-life and still deployed. The disclosure rule wins, and a
checker that did not know that would quietly push the other way.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT = REPO / "BENCH-LOG.md"

CARD_START = re.compile(r"^T-\d+[A-Za-z]?\s")
VERDICTS = ("✅", "❌", "🔶", "⚠️")
# A time of day (07:31, 22:4x) or a date. The second minute digit may be `x`
# because the log records approximate minutes when the transcript timestamp was
# not captured, and an honest "about ten past" beats a precise invention. The
# first version of this pattern required two digits and rejected every card the
# W06 session had written that way - a checker whose first run fails on correct
# input teaches its operator to distrust it, which is the opposite of the point.
# Ruff flags the fullwidth colon and the en dash below as "ambiguous". They are
# deliberate: this matches text in a Traditional Chinese file whose house style
# IS fullwidth punctuation, so the lookalike character is the one that appears.
# Replacing them with ASCII would make the checker silently stop matching the
# file it exists to check - the quietest way for a check to become decoration.
#
# (Do not start that explanation with the word noqa. Ruff read an earlier version
#  of this comment as a blanket directive and then reported it as unused.)
_WHEN_RE = r"\d{1,2}[:：]\d[\dx](?:[-–]\d{1,2}[:：]\d[\dx])?|\d{4}-\d{2}-\d{2}"  # noqa: RUF001
WHEN = re.compile(_WHEN_RE)

# Cards that predate this checker and cannot be fixed, because BENCH-LOG.md is
# append-only and a past session's record is evidence rather than a document.
# Each exemption is declared IN the file, with a reason, and this reads them from
# there rather than carrying a list of its own - a checker holding its own
# exemptions is a second owner of the same state.
EXEMPT = re.compile(r"<!--\s*benchlog-exempt:\s*(T-\d+)\s+(.+?)\s*-->", re.S)


def cards(text: str) -> list[tuple[int, list[str]]]:
    """Return (line number of the card's first line, its lines) for each card.

    A fence may hold SEVERAL cards. The first version of this took one fence to
    be one card, and reported "19 record cards, every one with a refutation
    check" on a file holding about thirty - because W05 wrote T-01 through T-05
    inside a single block, and everything after the first line of that block was
    invisible. A checker that silently covers less than it claims is the exact
    defect this file records twenty-seven instances of, and it managed to be one
    on its first run.
    """
    out: list[tuple[int, list[str]]] = []
    lines = text.split("\n")
    in_fence = False
    cur: list[str] | None = None
    start = 0

    def flush() -> None:
        nonlocal cur
        if cur:
            out.append((start, cur))
        cur = None

    for i, ln in enumerate(lines, 1):
        if ln.startswith("```"):
            if in_fence:
                flush()
            in_fence = not in_fence
            continue
        if not in_fence:
            continue
        if CARD_START.match(ln):
            flush()
            cur, start = [ln], i
        elif cur is not None:
            cur.append(ln)
    flush()
    return out


def check(path: Path) -> int:
    text = path.read_text("utf-8")
    found = cards(text)
    errors: list[str] = []

    exempt = {m.group(1): " ".join(m.group(2).split()) for m in EXEMPT.finditer(text)}
    for ident, why in sorted(exempt.items()):
        if len(why) < 30:
            errors.append(f"{path.name}: exemption for {ident} has no real reason "
                          f"({why!r}). An exemption without one is a silent skip")

    seen: dict[str, int] = {}

    if not found:
        # The failure mode this guards against is not a missing field but a
        # changed shape: if the cards stop being fenced, or stop starting with
        # T-, every check below passes over nothing and reports success.
        errors.append(
            f"{path.name}: no record cards found at all. Either the file has "
            "none, or the card shape changed and every check below just passed "
            "over an empty list")

    for ln, card in found:
        head = card[0].strip()
        ident = head.split()[0]
        body = "\n".join(card)

        # Ids must be unique: this is one continuous append-only record, and a
        # collision means two sessions' evidence is filed under one name. The
        # W06 draft restarted at T-06 and collided with nine of W05's.
        if ident in seen:
            errors.append(f"{path.name}:{ln}: card id {ident} is already used at "
                          f"line {seen[ident]}. Ids are unique across the whole "
                          "file, not per session")
        else:
            seen[ident] = ln

        if ident in exempt:
            continue

        if not WHEN.search(head):
            errors.append(f"{path.name}:{ln}: card {ident} has no time on its "
                          "header line, so it cannot be placed in the session's "
                          "order")

        if "判定" not in body:
            errors.append(f"{path.name}:{ln}: card {ident} has no 判定 line")
        elif not any(v in body for v in VERDICTS):
            errors.append(f"{path.name}:{ln}: card {ident} has a 判定 line with "
                          f"none of the four markers {' '.join(VERDICTS)}")

        # Same reason as WHEN above: the fullwidth colon is what the file uses.
        m = re.search(r"反證檢查\s*[:：](.*?)(?=\n\S|\Z)", body, re.S)  # noqa: RUF001
        if not m:
            errors.append(
                f"{path.name}:{ln}: card {ident} has **no 反證檢查 field**. "
                "A test with no pre-written definition of failure is read as a "
                "success afterwards, because by the time the result is in you "
                "already know what you wanted to see")
            continue
        said = " ".join(m.group(1).split())
        # Both halves, and the test is structural rather than lexical: the
        # pre-written condition is quoted with 「」, and something has to follow
        # the closing bracket saying what was actually seen. Keying on the word
        # 實際 was the first attempt and it rejected a W05 card that ends
        # "…」。前者成立" - which IS the second half, phrased differently. A
        # checker that only accepts one wording trains people to write for the
        # checker.
        close = said.rfind("」")
        if not said:
            errors.append(f"{path.name}:{ln}: card {ident}'s 反證檢查 is empty")
        elif close < 0:
            errors.append(
                f"{path.name}:{ln}: card {ident}'s 反證檢查 does not quote the "
                "condition that was written beforehand. Put it in 「」 so a "
                "reader can see it was written first rather than fitted after")
        elif len(said) - close < 4:
            errors.append(
                f"{path.name}:{ln}: card {ident}'s 反證檢查 records what was "
                "written beforehand and stops. Say what was actually seen, or it "
                "is a prediction rather than a check")

    errors += check_sessions_are_paired(path)

    for e in errors:
        print(f"  FAIL  {e}", file=sys.stderr)
    if errors:
        print(f"\n  {len(errors)} problem(s) in {len(found)} card(s)", file=sys.stderr)
        return 1
    note = f", {len(exempt)} exempted with a reason" if exempt else ""
    print(f"bench log OK — {len(found)} record cards{note}, every other one with "
          "a verdict and a refutation check that names both halves; every session "
          "PROGRESS.md records has an entry here on the same date")
    return 0


DATE = re.compile(r"(20\d\d-\d\d-\d\d)")
# A session heading in PROGRESS.md: "## W07 Day 3 — … — 2026-08-18",
# "## W06 — 2026-08-17 (night)", "## W05 close-out, second pass — 2026-08-17".
SESSION_HEADING = re.compile(r"^##\s+(W\d\d\b.*)$")


def check_sessions_are_paired(bench_path: Path) -> list[str]:
    """Every session PROGRESS.md records must appear in BENCH-LOG.md by date.

    Why this exists
    ---------------
    BENCH-LOG.md owns two things: what was typed and seen on a bench day, **and
    the plan written before touching anything**. The second half is the one that
    gets forgotten, because on a desk-only day nothing was typed and the file
    feels inapplicable — and yet a desk-only day is exactly when the next visit's
    plan changes, which is exactly what has to be on the record *before* the
    device is plugged in rather than after.

    It was forgotten on 2026-08-18 (W07 Day 3), on a day that rewrote three of
    the next visit's predictions. The author noticed, not a tool. Everything else
    in this file checks the shape of a card that exists; nothing checked that a
    session had an entry at all, which is the same blind spot instrument bug 22
    had: the checker read only the file it was pointed at.

    The rule is deliberately weak — it matches on **date**, not on content, so it
    cannot judge whether the entry says anything useful. A checker that tried
    would be guessing. This one only refuses the case that actually happens:
    a session written up in PROGRESS.md with no line in BENCH-LOG.md at all.

    Sessions predating BENCH-LOG.md's first entry are exempt, because W01-W04
    had no device to be at.
    """
    progress = bench_path.parent / "PROGRESS.md"
    if not progress.exists() or not bench_path.exists():
        return []
    # Headings only. Taking every date in the file makes the floor below far too
    # early -- the prose refers back to W01-era dates -- and it also lets a
    # passing mention of a date count as an entry for that day, which is the one
    # thing this check must not accept.
    bench_dates = {
        d
        for line in bench_path.read_text(encoding="utf-8").splitlines()
        if line.startswith("#")
        for d in DATE.findall(line)
    }
    if not bench_dates:
        return []
    first_bench_day = min(bench_dates)

    problems: list[str] = []
    for line in progress.read_text(encoding="utf-8").splitlines():
        m = SESSION_HEADING.match(line)
        if not m:
            continue
        heading = m.group(1).strip()
        dates = DATE.findall(heading)
        if not dates:
            continue
        day = dates[-1]
        if day < first_bench_day:
            continue
        if day not in bench_dates:
            problems.append(
                f"PROGRESS.md records a session on {day} ({heading[:60]}) and "
                f"{bench_path.name} has no entry for that date. If the device was "
                "not touched, that is not an exemption: this file also owns the "
                "plan written BEFORE the next visit, and a desk-only day is when "
                "that plan changes")
    return problems


def main(argv: list[str]) -> int:
    return check(Path(argv[1]) if len(argv) > 1 else DEFAULT)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
