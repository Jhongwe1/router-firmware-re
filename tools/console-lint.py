#!/usr/bin/env python3
"""Read a `<RealTek>` console log the way the loader's own dispatcher reads it.

Why this exists
---------------
On 2026-08-21 a `picocom` log recorded two commands that the boot loader
answered `Unknown command !`.  One was diagnosed the next morning by re-reading
the same file with `cat -A`: the line carried `^[[A^[[B`, two arrow keys, and
this loader has no line editing, so those four bytes went into `argv[0]`.  The
other was written up as **cause unknown** -- and its cause was in the same file,
in plain ASCII, needing no `cat -A` at all.

The lesson recorded that morning was "read the verbatim log correctly".  That is
a discipline, and disciplines are what this repository has already watched fail
three times.  This is the same instruction as a script:

  * `\\n` from `printf` reaches the wire as `\\n\\r`, because the loader's
    `putchar` appends the carriage return (`0x80406BA4`).  Every line in a
    picocom capture therefore begins with the previous line's `\\r`.
  * The command prompt is `printf("%s", "<RealTek>")` at `0x80409178`, with no
    newline, and the newline that closes an echoed command line is a separate
    `printf("\\n")` at `0x804091A8` -- *after* `GetLine` returns.  So the bytes
    between a prompt and the next `\\n` are exactly what the operator typed and
    the loader echoed.
  * **A `<RealTek>` on the wire is not always a prompt.** The TFTP completion
    path prints `"\\n.Success!\\n%s"` (`0x8040A948`, printed at `0x80401CD0`)
    and the upload path prints `"\\nSuccess!\\n%s"` (`0x8040A8E4` at
    `0x80401AEC`), and in both the `%s` is a **second copy** of the string
    `<RealTek>` at `0x8040A894`.  Those run in the ethernet interrupt handler
    while `GetLine` is still collecting a line, and they do not touch the line
    buffer.  A search for cross-references to the dispatcher's copy at
    `0x8040B314` finds exactly one and says the prompt has one owner, which is
    how this was missed for a day.
  * The tokeniser at `0x80407248` stores `argv[i] = p` **before** it tests
    whether `*p` is a space (`0x80407290`, then `0x804072D4` writes the NUL).
    So a command line that begins with whitespace has `argv[0] == ""`, which
    matches none of the seventeen names, and the loader answers
    `Unknown command !` to a line that looks perfectly clean.
  * `GetLine` expands a TAB into **eight spaces** (`0x8040713C`-`0x80407168`),
    into the buffer and onto the console.  One keypress, eight characters, and
    nothing on the screen says which it was.

What it reports
---------------
Findings, each naming the loader address that owns the behaviour, and -- the
part that makes it an instrument rather than a highlighter -- **every
`Unknown command !` in the file is accounted for or reported as unexplained**,
and an unexplained one is a non-zero exit.  A linter that only points at things
it recognises cannot tell you it has missed something.

Usage
-----
    python3 tools/console-lint.py dumps/w08-a28.log
    python3 tools/console-lint.py --json report.json LOG [LOG...]
    python3 tools/console-lint.py --quiet LOG      # exit code only
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

PRODUCER = "console-lint"
SCHEMA = "1"

PROMPT = b"<RealTek>"
UNKNOWN = b"Unknown command !"

# The seventeen names this loader's `?` prints, captured at the console on
# 2026-08-17 and re-confirmed 2026-08-21.  The dispatcher upper-cases `argv[0]`
# first (`strupr` at 0x80407040), so the comparison here is upper-case too.
COMMANDS = {"?", "DB", "DW", "EB", "EW", "CMP", "IPCONFIG", "AUTOBURN",
            "LOADADDR", "J", "FLR", "FLW", "MDIOR", "MDIOW", "PHYR", "PHYW",
            "PORT1"}

# Every message the loader prints *from the ethernet interrupt* ends with `%s`
# and passes the second copy of the prompt string, so it repaints the prompt.
# `Flash Read Successed!` (0x8040B4A4, printed by the FLR handler at
# 0x80409A5C) deliberately does NOT appear here: it carries no `%s`, it runs in
# the command context, and treating it as a repaint would make the linter
# silently carry a buffer across a boundary that really was cleared.
REPAINT_TAIL = re.compile(
    rb"(?:\.?Success!|Flash Write Successed!|Flash Write Failed!)\s*$")
REPAINT_OWNERS = (
    "TFTP download complete 0x80401CD0 (format 0x8040A948), TFTP upload "
    "complete 0x80401AEC (0x8040A8E4), auto-burn 0x804018D0 / 0x804018B8 "
    "(0x8040A860 / 0x8040A878); every one passes the second copy of the "
    "prompt string at 0x8040A894 as its %s")

# `GetLine`'s destructive backspace echo: BS, space, BS (0x8040711C-0x80407130).
ERASE = b"\x08\x20\x08"

WHITESPACE = b" \t"


class Finding(dict):
    pass


def _segments(buf: bytes) -> list[dict[str, Any]]:
    """Every `<RealTek>` in the stream, with the bytes echoed after it.

    A segment ends at the next `\\n`, which is the dispatcher's own
    `printf("\\n")` after `GetLine` returns -- or, when the line was never
    submitted, the leading `\\n` of whatever printed next.  Telling those two
    apart is not possible from the byte stream alone and this function does not
    try; that is what `_walk` uses the repaint classification for.
    """
    out = []
    at = 0
    while True:
        i = buf.find(PROMPT, at)
        if i < 0:
            return out
        start = i + len(PROMPT)
        nl = buf.find(b"\n", start)
        end = len(buf) if nl < 0 else nl
        before = buf[max(0, i - 40):i].replace(b"\r", b"").replace(b"\n", b"")
        out.append({
            "offset": i,
            "echo": buf[start:end],
            "repaint": bool(REPAINT_TAIL.search(before)),
        })
        at = end if end > at else at + 1


def _strip_erases(echo: bytes) -> bytes:
    """Apply the destructive backspaces the device echoed, as `GetLine` did."""
    out = bytearray()
    i = 0
    while i < len(echo):
        if echo[i:i + 3] == ERASE:
            if out:
                out.pop()
            i += 3
            continue
        out.append(echo[i])
        i += 1
    return bytes(out)


def _controls(line: bytes) -> list[str]:
    bad = []
    for b in line:
        if b == 0x09:                       # TAB reaches GetLine as a TAB
            bad.append("0x09 TAB")
        elif b < 0x20 or b == 0x7F:
            bad.append(f"0x{b:02x}")
    return bad


def _first_token(line: bytes) -> str:
    t = line.split(b" ")[0] if line else b""
    return t.decode("latin-1").upper()


def lint(buf: bytes, name: str) -> dict[str, Any]:
    segs = _segments(buf)
    findings: list[Finding] = []
    # `pending` is the loader's line buffer as this reading reconstructs it: a
    # real prompt means `GetLine` returned and the dispatcher memset it
    # (0x80409190); a repaint means nothing of the sort.
    pending = b""
    accounted: list[int] = []

    for seg in segs:
        echo = _strip_erases(seg["echo"])
        if seg["repaint"]:
            findings.append(Finding(
                kind="tftp-repaint",
                offset=seg["offset"],
                detail=("this `<RealTek>` was printed by the TFTP completion "
                        "path, not by the command loop, and it does not clear "
                        "the line buffer"),
                owner=REPAINT_OWNERS,
                carried=pending.decode("latin-1"),
            ))
        else:
            pending = b""
        pending += echo

        ctrl = _controls(echo)
        if ctrl:
            findings.append(Finding(
                kind="control-bytes",
                offset=seg["offset"],
                detail=(f"the echoed line carries {', '.join(sorted(set(ctrl)))}. "
                        "This loader has no line editing and no history, so an "
                        "arrow key puts its three bytes straight into argv[0]; "
                        "a TAB is expanded by GetLine into eight spaces"),
                owner="GetLine 0x8040708C; the TAB expansion is 0x8040713C-0x80407168",
                line=echo.decode("latin-1"),
            ))

        # What the device said next decides whether this line was submitted.
        nxt = buf.find(PROMPT, seg["offset"] + len(PROMPT))
        tail = buf[seg["offset"]:nxt if nxt > 0 else len(buf)]
        rejected = UNKNOWN in tail
        if rejected:
            accounted.append(seg["offset"])
            head = pending.lstrip(WHITESPACE)
            if pending[:1] in (b" ", b"\t"):
                findings.append(Finding(
                    kind="leading-whitespace",
                    offset=seg["offset"],
                    detail=("the submitted line begins with whitespace, so the "
                            "tokeniser sets argv[0] to the empty string and no "
                            "name matches. The visible text is irrelevant"),
                    owner="tokeniser 0x80407248: argv[i] is stored at 0x80407290 "
                          "before 0x804072D4 tests for a space",
                    line=pending.decode("latin-1"),
                    would_have_run=_first_token(head),
                ))
            elif ctrl:
                pass                        # already reported above
            elif _first_token(pending) not in COMMANDS:
                findings.append(Finding(
                    kind="not-a-command",
                    offset=seg["offset"],
                    detail=(f"argv[0] is {_first_token(pending)!r}, which is not "
                            "one of the seventeen names the table carries"),
                    owner="command table 0x8040DBC0; argv[0] is upper-cased by "
                          "strupr at 0x80407040 before the comparison",
                    line=pending.decode("latin-1"),
                ))
            else:
                findings.append(Finding(
                    kind="unexplained-rejection",
                    offset=seg["offset"],
                    detail=("the loader answered `Unknown command !` to a line "
                            "whose argv[0] is a valid command name, with no "
                            "leading whitespace and no control bytes. This "
                            "reading does not explain it"),
                    owner=None,
                    line=pending.decode("latin-1"),
                ))
            pending = b""

    unexplained = [f for f in findings if f["kind"] == "unexplained-rejection"]
    return {
        "producer": PRODUCER,
        "schema": SCHEMA,
        "log": name,
        "bytes": len(buf),
        "prompts": len(segs),
        "repaints": sum(1 for s in segs if s["repaint"]),
        "rejections": buf.count(UNKNOWN),
        "rejections_accounted_for": len(accounted),
        "findings": findings,
        "unexplained": len(unexplained),
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logs", nargs="+", type=Path)
    ap.add_argument("--json", type=Path, help="write the report here")
    ap.add_argument("--quiet", action="store_true",
                    help="print nothing; the exit code is the result")
    ap.add_argument("--expect-clean", action="store_true",
                    help="exit non-zero if there is any finding at all, not "
                         "just an unexplained rejection")
    args = ap.parse_args(argv[1:])

    reports = []
    bad = 0
    for path in args.logs:
        if not path.is_file():
            print(f"no such log: {path}", file=sys.stderr)
            return 2
        rep = lint(path.read_bytes(), path.name)
        reports.append(rep)
        if rep["unexplained"]:
            bad += rep["unexplained"]
        if args.expect_clean and rep["findings"]:
            bad += len(rep["findings"])
        if args.quiet:
            continue
        print(f"{path}: {rep['prompts']} prompts "
              f"({rep['repaints']} printed by the TFTP path), "
              f"{rep['rejections']} rejection(s), "
              f"{len(rep['findings'])} finding(s)")
        for f in rep["findings"]:
            print(f"  0x{f['offset']:06x}  {f['kind']}")
            print(f"            {f['detail']}")
            if f.get("owner"):
                print(f"            owner: {f['owner']}")
            if f.get("line") is not None:
                print(f"            line:  {f['line']!r}")
            if f.get("carried"):
                print(f"            already in the buffer: {f['carried']!r}")
            if f.get("would_have_run"):
                print(f"            without the whitespace this would have run "
                      f"{f['would_have_run']}")
        if rep["rejections"] != rep["rejections_accounted_for"]:
            print(f"  NOTE  {rep['rejections']} rejections in the file, "
                  f"{rep['rejections_accounted_for']} tied to a prompt")

    if args.json:
        args.json.write_text(
            json.dumps(reports if len(reports) > 1 else reports[0],
                       indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
