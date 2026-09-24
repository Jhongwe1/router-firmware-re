#!/usr/bin/env python3
"""Wire test-check-numbers.sh in; instrument bug 61."""
from __future__ import annotations

import pathlib
import sys

changed = []


def sub(rel: str, old: str, new: str) -> None:
    p = pathlib.Path(rel)
    s = p.read_text(encoding="utf-8")
    if old not in s and new in s:
        return
    if s.count(old) != 1:
        print(f"  !! {rel}: expected 1 of {old[:60]!r}, found {s.count(old)}")
        sys.exit(1)
    p.write_text(s.replace(old, new), encoding="utf-8", newline="\n")
    changed.append(rel)


sub("Makefile",
    "gates: ## Regenerate docs/gates.md from the (private) week plans",
    "numbers-test: ## Prove the number checker can fail, and that it skips what it cannot measure (12 cases)\n"
    "\tbash tools/test-check-numbers.sh\n\n"
    "gates: ## Regenerate docs/gates.md from the (private) week plans")

sub("Makefile",
    "check-links links-test check-numbers check-expired expired-test check-gates",
    "check-links links-test check-numbers numbers-test check-expired expired-test check-gates")

sub(".github/workflows/ci.yml",
    "      - name: numbers — the front door agrees with what generates it\n"
    "        run: python3 tools/check-numbers.py",
    "      - name: numbers — the front door agrees with what generates it\n"
    "        run: python3 tools/check-numbers.py\n"
    "      # This step exists because the one above went green here and red on a\n"
    "      # runner with the repository unchanged: no pytest in this job meant\n"
    "      # count-checks.sh returned 468 against 626, and the checker called\n"
    "      # fourteen correct numbers stale. It now refuses to judge a recount it\n"
    "      # could not complete, and these cases are what hold it to that.\n"
    "      - name: number checker — prove it can fail, and that it skips what it cannot measure\n"
    "        run: bash tools/test-check-numbers.sh")

# --- instrument bug 61 --------------------------------------------------------
C12 = "writeup/12-instruments.md"
sub(C12, "# 12. Sixty instruments, sixty bugs — none caught by a self-check",
     "# 12. Sixty-one instruments, sixty-one bugs — none caught by a self-check")
sub(C12, "Sixty times, an instrument this project built or relied on was wrong.",
     "Sixty-one times, an instrument this project built or relied on was wrong.")
sub(C12, "> **Sixty instrument bugs. Not one was caught by the instrument's own",
     "> **Sixty-one instrument bugs. Not one was caught by the instrument's own")
sub(C12, "> **Where this chapter stops:** sixty is the count of bugs *found*.",
     "> **Where this chapter stops:** sixty-one is the count of bugs *found*.")

sub(C12,
    "| 60 | a **guard suite** whose `must_catch` helper piped the checker into `grep` ",
    "| 61 | the numbers checker asserting an **environment-dependent** recount. "
    "`count-checks.sh` turned a suite it could not run into `0` checks, so a GitHub "
    "runner with no pytest totalled **468** against this workstation's **626**, and "
    "fourteen correct numbers were reported stale — **local green, remote red, "
    "repository unchanged** | the remote run, on the push that opened the pull "
    "request. Nothing local could have: the bug *is* the difference between the two "
    "machines |\n"
    "| 60 | a **guard suite** whose `must_catch` helper piped the checker into `grep` ")

sub(C12,
    "2026-09-25, the publication week, and nothing was being measured — three checkers",
    "2026-09-25, the publication week, and nothing was being measured — three checkers")

sub(C12,
    "All four **invented work**.",
    "All five **invented work**.")

sub(C12,
    "reported **6 failures out of 13** against a checker that was working correctly.",
    "reported **6 failures out of 13** against a checker that was working correctly. And\n"
    "the numbers checker, once fixed and green here, went red on the GitHub runner and\n"
    "called **fourteen correct numbers stale** — because it was asserting a recount the\n"
    "runner could not complete, and `count-checks.sh` scored a suite it could not run as\n"
    "**zero checks** rather than as *unmeasured*.")

sub(C12,
    "structure is a statement about the suite. (`set -o pipefail` and a command whose\n"
    "job is to exit non-zero: the pipeline returns the checker's status, not grep's.)",
    "structure is a statement about the suite. (`set -o pipefail` and a command whose\n"
    "job is to exit non-zero: the pipeline returns the checker's status, not grep's.)\n\n"
    "The fifth is the one with teeth, because **nothing local could have caught it.**\n"
    "The repository was byte-identical on both machines; the disagreement was between\n"
    "the machines. It is this chapter's own rule arriving from a direction it had not\n"
    "been stated in: *a tool reporting `0` is making a claim* — and `count-checks.sh`\n"
    "had been making that claim, in a shell default (`${n:-0}`) written months earlier,\n"
    "every time a dependency was missing. It only became visible when something finally\n"
    "**compared two environments**, which is the same move as comparing two builds.")

# --- everywhere else -----------------------------------------------------------
sub("writeup/README.md",
    "*Reading a vendor's five-year fix off the chip — and what sixty broken",
    "*Reading a vendor's five-year fix off the chip — and what sixty-one broken")
sub("writeup/README.md",
    "sixty of my own instruments were wrong, and **not one was caught by its own",
    "sixty-one of my own instruments were wrong, and **not one was caught by its own")
sub("writeup/README.md",
    "| **12** | [Sixty instruments, sixty bugs](12-instruments.md) |",
    "| **12** | [Sixty-one instruments, sixty-one bugs](12-instruments.md) |")
sub("README.md",
    "| **Instruments of mine that were wrong** | **sixty**, all listed.",
    "| **Instruments of mine that were wrong** | **sixty-one**, all listed.")
sub("README.md",
    "- **Sixty of my own instruments were wrong, and all of them are published**",
    "- **Sixty-one of my own instruments were wrong, and all of them are published**")
sub("docs/how-this-was-built.md",
    "- **Noticing when a tool was lying.** Sixty times",
    "- **Noticing when a tool was lying.** Sixty-one times")
sub("docs/how-this-was-built.md",
    "hour on 2026-09-25 by comparing a brand-new checker's output against the file\n"
    "  it is judging, which is the whole method in one sentence.",
    "hour on 2026-09-25 by comparing a brand-new checker's output against the file\n"
    "  it is judging; a fifth by two machines disagreeing about the same commit.")
sub("journal/README.md",
    "sixty of my own broken instruments.",
    "sixty-one of my own broken instruments.")

print("  patched:", ", ".join(sorted(set(changed))))
