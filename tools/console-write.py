#!/usr/bin/env python3
"""Write the SPI flash through the RealTek boot loader, and refuse every write
this project could not undo.

Why this exists, and why it is a separate file
----------------------------------------------
``tools/console-dump.py`` ends its docstring with a guarantee: *nothing here
writes to the device* - it names the four writing commands and says none of them
is ever sent.  That sentence is checkable by grepping one file, and
``tools/test-console-dump.sh`` greps it.  Adding a write path there would destroy
the one property that makes the read tool safe to hand to somebody in a hurry.
So the write path lives here, where the guarantee is the opposite one and every
guard is about the consequence.

This file carries the same kind of grep-checkable property, one step narrower:
**the token for the boot loader's burn switch does not appear anywhere in it**,
so no arrangement of arguments can make this tool change whether an upload
reaches flash.  That switch belongs to ``console-dump.py``'s ``rescue``
subcommand, which can emit it with the value ``0`` and no other.
``tools/test-console-write.sh`` greps for the token, which is why the paragraph
you are reading spells it out longhand.

The consequence is specific.  On 2026-08-17 an unauthenticated POST round
overwrote this unit's ``COMPDS`` factory-default region with the contents of
``COMPCS`` (PROGRESS.md, W05 close-out).  The bytes exist twice off the device,
so nothing is lost - but putting them back needs 16 KiB written through a
console whose only staging primitive is ``EB``, one line of hex at a time.
``runsheet.md`` A2.5 records that this tool did not exist and that it must be
proven at the drill address ``0x3F0000`` before it is ever pointed at
``0x8000``.  This file is that tool.

What the boot loader gives us, measured on this unit
----------------------------------------------------
* ``EB <ram> <hex> [<hex> ...]`` - stage bytes into RAM.  The multi-byte form
  works (2026-08-17); how many bytes one line accepts is a device fact nobody
  had measured, so ``probe-eb`` measures it in RAM and writes nothing to flash.
* ``FLW <flash> <ram> <len>`` - program.  **The argument order is the reverse of
  ``FLR``'s** (``FLR <ram> <flash> <len>``), the confirmation prompt punctuates
  differently (``(Y)es, (N)o->`` against ``(Y)es , (N)o ?``), and success prints
  a single ``.`` rather than any sentence.
* ``FLW`` is read-modify-erase-program of the containing 4 KiB sector and it
  preserves the rest of that sector (PROGRESS.md open #17, settled 2026-08-17
  with a control).  So a write of eight bytes still rewrites 4,096: power lost
  mid-cycle costs the whole sector, not the eight bytes.
* The loader's command set contains **no erase command at all**, which is how we
  know ``FLW`` must be doing the erase itself.

Refusals
--------
An allow-list, not a deny-list.  A deny-list's failure mode is forgetting to
deny something; here the only two writable ranges are named and everything else
- the boot loader at ``0x000000``, and ``H601`` at ``0x006000`` holding this
unit's MAC addresses and radio calibration, which exist nowhere else in the
world and which a factory reset does not restore - is unreachable by
construction.  There is no flag that widens the list.

Then, for a write outside the drill sector:

* offset and length must be whole 4 KiB sectors, because that is the unit
  ``FLW`` actually operates on;
* ``--expect-sha256`` is required and must match the bytes about to be written,
  so a truncated or wrong source file cannot be programmed silently;
* ``--confirm`` must repeat the target offset, so a mistyped address needs two
  coincident mistakes rather than one;
* an all-``FF`` source is refused unless ``--allow-blank``, because a zeroed or
  short file is what a restore-gone-wrong looks like from inside.

And on every run, whatever the target:

* a **positive control** - flash ``0x000000`` is read into the verify address
  first and must come back ``0b f0 00 04``.  It proves ``FLR``/``DB`` work, and
  it proves the verify address did not already contain the answer;
* **staged RAM is read back before ``FLW`` is sent.**  If ``EB`` only took the
  first byte of each line, this is where the run stops - before flash is
  touched, not after;
* **the written range is read back into a third address and compared byte for
  byte** against the source, and the first differing offset is reported;
* the JSON report is written on every exit path including failure.  Instrument
  bug 20 was a tool that detected the most interesting event of a session and
  discarded the evidence of it in the same action.

Bytes inside ``0x006000``-``0x010000`` are this unit's secrets (MACs, radio
calibration, admin credentials, PSK, WPS PIN).  They are never printed, not even
in an error message; offsets and digests are.  That range is also the one this
tool exists to restore, so the rule and the purpose meet here rather than
anywhere else.

Usage
-----
  # how many bytes does EB take on one line?  RAM only, no flash write at all
  tools/console-write.py probe-eb --port /dev/ttyUSB0 --at-prompt

  # the A2.5 rehearsal, automated, in the erased tail
  tools/console-write.py drill --port /dev/ttyUSB0 --at-prompt -o drill.json

  # the real thing
  tools/console-write.py write --port /dev/ttyUSB0 --at-prompt \\
      --flash 0x8000 --confirm 0x8000 --length 0x4000 \\
      --input compds.bin --expect-sha256 <64 hex> -o restore.json

``--dry-run`` runs every check above and prints the exact command lines without
opening the port.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load_reader():
    """Import console-dump.py for its console, parser and read path.

    The hyphen in the filename means this cannot be a plain import.  Sharing the
    module is the point: every byte this project has read off the flash came
    through ``parse_db``, and the verification half of a write must not use a
    second, subtly different parser written for the occasion.
    """
    path = os.path.join(_HERE, "console-dump.py")
    spec = importlib.util.spec_from_file_location("console_dump", path)
    if spec is None or spec.loader is None:  # pragma: no cover - packaging error
        raise SystemExit(f"  FAIL  cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CD = _load_reader()

SECTOR = 0x1000
PROMPT = CD.PROMPT

# The two ranges this tool may write, and nothing else.  A range is (lo, hi,
# why, drill).  `drill` relaxes the sector-alignment and sha256 requirements,
# because the rehearsal deliberately writes eight bytes.
DRILL_LO, DRILL_HI = 0x3F0000, 0x400000
WRITABLE = (
    (DRILL_LO, DRILL_HI, "the erased tail - no live data, this is the rehearsal area", True),
    (0x008000, 0x010000, "COMPDS factory defaults + COMPCS live configuration", False),
)

# Stated so a reader does not have to derive it from the allow-list.  Never
# reachable: 0x000000-0x006000 boot loader, 0x006000-0x008000 H601 (this unit's
# MACs and radio calibration), 0x010000-0x3F0000 kernel, rootfs and web bundle.
NEVER = (
    (0x000000, 0x006000, "boot loader - bricks the unit, and the recovery path runs on it"),
    (0x006000, 0x008000, "H601 - this unit's MACs and radio calibration, unique in the world"),
    (0x010000, DRILL_LO, "kernel, rootfs and web bundle"),
)

CONTROL_FLASH_OFFSET = CD.CONTROL_FLASH_OFFSET
CONTROL_EXPECT = CD.CONTROL_EXPECT

# The confirmation prompt FLW asks.  It is NOT the one FLR asks, and the two
# differ by a space and a question mark:
#     FLR   (Y)es , (N)o ?
#     FLW   (Y)es, (N)o->
# Matching on the common prefix rather than either full string means this works
# for both and cannot be broken by the punctuation drifting between builds.
CONFIRM = b"(Y)es"


class WriteError(Exception):
    """Anything that would leave flash in a state nobody chose."""


def fail(msg: str) -> None:
    print(f"  FAIL  {msg}", file=sys.stderr)
    raise SystemExit(1)


def is_secret(offset: int, length: int = 1) -> bool:
    return CD.is_secret(offset, length)


def redacted(data: bytes, offset: int) -> str:
    """Render bytes for a log, or a digest if they belong to this unit alone."""
    if is_secret(offset, len(data)):
        return (f"<{len(data)} bytes withheld: inside the per-unit secret region "
                f"0x006000-0x010000, sha256 {hashlib.sha256(data).hexdigest()[:16]}...>")
    return " ".join(f"{b:02x}" for b in data[:16]) + ("..." if len(data) > 16 else "")


# ---------------------------------------------------------------------------
# the checks - pure, no I/O, driven by tools/test-console-write.sh
# ---------------------------------------------------------------------------
def classify(flash: int, length: int) -> tuple[bool, str]:
    """Is this range writable at all?  Returns (is_drill, why) or raises."""
    if length <= 0:
        raise WriteError("length must be positive")
    end = flash + length
    for lo, hi, why, drill in WRITABLE:
        if flash >= lo and end <= hi:
            return drill, why
    for lo, hi, why in NEVER:
        if flash < hi and end > lo:
            raise WriteError(
                f"{flash:#08x}+{length:#x} touches {lo:#08x}-{hi:#08x}: {why}.\n"
                "        This tool has an allow-list, not a deny-list, and no flag "
                "widens it.\n"
                "        If this region genuinely has to be written, that is a "
                "decision to take\n"
                "        with the unit's only copy of it in hand, not a flag to pass."
            )
    ranges = ", ".join(f"{lo:#08x}-{hi:#08x}" for lo, hi, _, _ in WRITABLE)
    raise WriteError(
        f"{flash:#08x}+{length:#x} is outside every writable range ({ranges})"
    )


def check_payload(
    data: bytes, flash: int, length: int, is_drill: bool,
    expect_sha256: str | None, confirm: int | None, allow_blank: bool,
) -> str:
    """Every refusal that can be decided before the port is opened.

    Returns the sha256 of the payload.  Order matters only in that the cheapest
    and most likely mistake - a short file - is reported first.
    """
    if len(data) != length:
        raise WriteError(
            f"the source holds {len(data)} bytes and --length says {length} "
            f"({length:#x}).\n"
            "        A short file is exactly what a restore-gone-wrong looks like "
            "from inside."
        )

    digest = hashlib.sha256(data).hexdigest()

    if not is_drill:
        if flash % SECTOR or length % SECTOR:
            raise WriteError(
                f"{flash:#08x}+{length:#x} is not whole 4 KiB sectors.\n"
                "        FLW is read-modify-erase-program of the containing sector, "
                "so a partial\n"
                "        write still rewrites 4,096 bytes.  Expressing it in sectors "
                "makes what\n"
                "        is actually at risk visible in the command line."
            )
        if confirm is None or confirm != flash:
            raise WriteError(
                f"--confirm must repeat the target offset exactly (got "
                f"{'nothing' if confirm is None else hex(confirm)}, "
                f"expected {flash:#x}).\n"
                "        Outside the drill sector a mistyped address should need two "
                "coincident\n        mistakes, not one."
            )
        if not expect_sha256:
            raise WriteError(
                "--expect-sha256 is required outside the drill sector.\n"
                f"        These bytes are sha256 {digest}\n"
                "        Pass it only after checking it against the source the bytes "
                "came from."
            )
        if expect_sha256.lower() != digest:
            raise WriteError(
                "the payload does not match --expect-sha256.\n"
                f"        expected  {expect_sha256.lower()}\n"
                f"        payload   {digest}\n"
                "        The file on disk is not the file you think it is.  Stop here."
            )

    if not allow_blank and data and all(b == 0xFF for b in data):
        raise WriteError(
            "the payload is entirely 0xFF.\n"
            "        Programming blank over a live region is what a truncated source "
            "file does.\n"
            "        Pass --allow-blank if erasing really is the intent (the drill's "
            "step 6 is)."
        )
    return digest


def sector_plan(flash: int, length: int) -> list[tuple[int, int, int]]:
    """Split a write so no single FLW crosses a 4 KiB sector boundary.

    Returns (payload_offset, flash_offset, count).  One FLW per sector is not a
    performance choice: the sector is the unit whose semantics were measured, and
    a multi-sector FLW is a behaviour nobody on this project has observed.
    """
    out = []
    done = 0
    while done < length:
        here = flash + done
        room = SECTOR - (here % SECTOR)
        n = min(room, length - done)
        out.append((done, here, n))
        done += n
    return out


def eb_lines(ram: int, data: bytes, per_line: int) -> list[str]:
    """The exact EB command lines that stage *data* at *ram*."""
    if per_line <= 0:
        raise WriteError("--eb-bytes must be positive")
    out = []
    for i in range(0, len(data), per_line):
        chunk = data[i:i + per_line]
        hexed = " ".join(f"{b:02X}" for b in chunk)
        out.append(f"EB {ram + i:X} {hexed}")
    return out


# ---------------------------------------------------------------------------
# device operations
# ---------------------------------------------------------------------------
def eb(con, ram: int, data: bytes, per_line: int, timeout: float, dry: list | None = None) -> None:
    for line in eb_lines(ram, data, per_line):
        if dry is not None:
            dry.append(line)
            continue
        try:
            con.command(line.encode(), timeout)
        except CD.DumpError as e:
            raise WriteError(
                f"EB did not come back to the prompt: {e}\n"
                "        If the loader dropped into an interactive edit mode, the "
                "NEXT command\n"
                "        would be eaten as an edit value.  Stopping rather than "
                "guessing.\n"
                "        Nothing has been written to flash at this point."
            ) from e


def flw(con, flash: int, ram: int, length: int, timeout: float, dry: list | None = None) -> str:
    """RAM -> flash.  Argument order is the reverse of FLR's.  Read it twice."""
    line = f"FLW {flash:X} {ram:X} {length:X}"
    if dry is not None:
        dry.append(line)
        dry.append("Y")
        return ""
    con.termios.tcflush(con.fd, con.termios.TCIFLUSH)
    con.write((line + "\r").encode())
    try:
        con.read_until(CONFIRM, 10.0)
    except CD.DumpError as e:
        raise WriteError(
            f"FLW did not ask for confirmation: {e}\n"
            "        It asks `(Y)es, (N)o->` - note that this is NOT FLR's "
            "`(Y)es , (N)o ?`.\n"
            "        If no prompt appeared, the command was not understood and "
            "nothing was written."
        ) from e
    # It eats the whole next line as the answer.  Sending anything but Y here
    # gets `Abort!` followed by a spurious `Unknown command !`.
    con.write(b"Y\r")
    out = con.read_until(PROMPT, timeout).decode(errors="replace")
    if "Abort" in out:
        raise WriteError("FLW aborted - the confirmation was not accepted")
    # Success prints a single `.`; the sentence `Flash Write Successed!` exists in
    # the loader but belongs to the TFTP auto-burn path, 2.7 KiB away in stage 2.
    # So the check is on the echo of the request, which names the chip and the
    # mapped address, rather than on any success string.
    if "SPI flash" not in out and "." not in out:
        raise WriteError(
            "FLW printed neither its `Write 0x... Bytes to SPI flash#1 ...` echo "
            "nor a `.`.\n"
            f"        What came back: {out.strip()[:200]!r}"
        )
    return out


def control(con, ram: int, timeout: float) -> None:
    """Prove FLR/DB work, and that *ram* does not already hold the answer.

    Reading a known place in flash into the address a later step will check is
    strictly stronger than 'use an address you have not used', which was the
    2026-08-17 morning's mistake: you do not know what an unused address holds.
    After this, that RAM holds a third thing - neither the payload nor blank.
    """
    CD.flr(con, ram, CONTROL_FLASH_OFFSET, len(CONTROL_EXPECT), timeout)
    got = CD.db(con, ram, len(CONTROL_EXPECT), timeout)
    if got != CONTROL_EXPECT:
        raise WriteError(
            f"positive control failed: flash {CONTROL_FLASH_OFFSET:#08x} came back "
            f"{got.hex(' ')}, expected {CONTROL_EXPECT.hex(' ')}.\n"
            "        Either FLR/DB are not doing what they say or this is not the "
            "same flash.\n"
            "        Nothing further is sent."
        )


def read_back(con, ram: int, flash: int, length: int, timeout: float) -> bytes:
    CD.flr(con, ram, flash, length, timeout)
    out = bytearray()
    step = 256
    for off in range(0, length, step):
        n = min(step, length - off)
        out += CD.db(con, ram + off, n, timeout)
    return bytes(out)


def first_difference(a: bytes, b: bytes) -> int | None:
    # strict=False is deliberate: a short read-back is one of the failures this
    # function exists to name, and it is named by the length check below rather
    # than by an exception raised mid-comparison.
    for i, (x, y) in enumerate(zip(a, b, strict=False)):
        if x != y:
            return i
    return None if len(a) == len(b) else min(len(a), len(b))


# ---------------------------------------------------------------------------
# subcommands
# ---------------------------------------------------------------------------
def open_console(args):
    con = CD.Console(args.port, args.baud, args.verbose)
    if not args.at_prompt:
        CD.catch_prompt(con, args.window)
    if not CD.settle(con):
        con.close()
        fail("could not get a clean prompt.  The ESC stream leaves ESCs queued in "
             "the loader's input buffer; `settle` clears them and it did not.")
    return con


def write_report(path: str | None, report: dict) -> None:
    """Always, including on failure.  See instrument bug 20."""
    if not path:
        return
    report["written_at_unix"] = int(time.time())
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(f"  ok    transcript -> {path}")


def cmd_probe_eb(args) -> int:
    """How many bytes does one EB line actually take?  RAM only.

    runsheet.md A2.5 records the multi-byte form working on 2026-08-17 and does
    not say where it stops.  Staging 16 KiB with the wrong answer means either
    four times the wire time it needed, or - much worse - a RAM image with one
    byte per line landed and the rest dropped.  The stage-verify would catch
    that, but measuring costs one minute and removes the question.

    Nothing here goes near flash.  The pattern is written to RAM, read back, and
    the largest line whose bytes all landed is reported.
    """
    report: dict = {"probe": "eb-line-capacity", "ram": args.ram, "results": []}
    if args.dry_run:
        for n in args.sizes:
            print(f"  ==>   {eb_lines(args.ram, bytes(range(n)), n)[0]}")
        return 0
    con = open_console(args)
    best = 0
    try:
        for n in args.sizes:
            # A distinct pattern per size, so a stale RAM value cannot be mistaken
            # for a success: byte i is (size ^ i) & 0xff.
            payload = bytes(((n ^ i) & 0xFF) for i in range(n))
            addr = args.ram + (n * 0x100)
            eb(con, addr, payload, n, args.timeout)
            got = CD.db(con, addr, n, args.timeout)
            landed = sum(1 for i in range(n) if got[i] == payload[i])
            ok = got == payload
            report["results"].append(
                {"bytes_per_line": n, "landed": landed, "ok": ok}
            )
            print(f"  {'ok   ' if ok else 'fail '} {n:3d} bytes on one line: "
                  f"{landed}/{n} landed")
            if ok:
                best = max(best, n)
            else:
                break
    except (WriteError, CD.DumpError) as e:
        report["error"] = str(e)
        write_report(args.output, report)
        con.close()
        fail(str(e))
    con.close()
    report["max_bytes_per_line"] = best
    write_report(args.output, report)
    if best == 0:
        fail("not even one byte landed through EB.  The staging path does not work "
             "and no write should be attempted.")
    print()
    print(f"  ok    EB takes {best} bytes on one line on this unit")
    print(f"        16 KiB would need {16384 // best} EB commands")
    return 0


def cmd_drill(args) -> int:
    """runsheet.md A2.5, automated, with the control the hand-typed version needed.

    Six steps, in the erased tail at 0x3F0000, and the fifth is the one that
    matters: write a second pattern elsewhere in the same 4 KiB sector, then read
    the first one back.  It survives -> FLW preserves the sector.  It is 0xFF ->
    FLW erases the whole sector, and every restore has to be sector-sized.
    Both answers are correct results and the tool records which it saw.
    """
    a, b = 0x3F0000, 0x3F0100
    pat_a = bytes((0xDE, 0xAD, 0xBE, 0xEF, 0xDE, 0xAD, 0xBE, 0xEF))
    pat_b = bytes((0xCA, 0xFE, 0xBA, 0xBE, 0xCA, 0xFE, 0xBA, 0xBE))
    blank = b"\xff" * 8
    report: dict = {"drill": "A2.5", "flash": {"pattern_at": a, "neighbour_at": b},
                    "steps": []}

    if args.dry_run:
        dry: list[str] = []
        eb(None, args.ram, pat_a, 8, 0, dry)
        flw(None, a, args.ram, 8, 0, dry)
        for line in dry:
            print(f"  ==>   {line}")
        return 0

    con = open_console(args)

    def step(name: str, **kw) -> None:
        report["steps"].append({"step": name, **kw})

    try:
        print("  ==>   step 1: the target is blank")
        control(con, args.verify_ram, args.timeout)
        before = read_back(con, args.verify_ram, a, 8, args.timeout)
        step("target-blank", got=before.hex(" "), blank=(before == blank))
        if before != blank:
            raise WriteError(
                f"{a:#08x} holds {before.hex(' ')}, not ff.  Something is there and "
                "what it is\n        has to be known before it is overwritten."
            )
        print("  ok    ff ff ff ff ff ff ff ff")

        print("  ==>   step 2: stage the pattern and prove it is in RAM")
        eb(con, args.ram, pat_a, args.eb_bytes, args.timeout)
        staged = CD.db(con, args.ram, 8, args.timeout)
        step("stage", want=pat_a.hex(" "), got=staged.hex(" "))
        if staged != pat_a:
            raise WriteError(
                f"RAM holds {staged.hex(' ')}, wanted {pat_a.hex(' ')}.  EB did not "
                "take the\n        whole line - re-run `probe-eb`.  Flash is untouched."
            )
        print(f"  ok    {staged.hex(' ')}")

        print("  ==>   step 3: FLW  (the first irreversible action)")
        out = flw(con, a, args.ram, 8, args.timeout)
        step("flw", reply=out.strip()[:200])
        print("  ok    programmed")

        print("  ==>   step 4: read back into a different address")
        control(con, args.verify_ram, args.timeout)
        got = read_back(con, args.verify_ram, a, 8, args.timeout)
        step("verify", got=got.hex(" "), match=(got == pat_a))
        if got != pat_a:
            raise WriteError(f"read back {got.hex(' ')}, wrote {pat_a.hex(' ')}")
        print(f"  ok    {got.hex(' ')}")

        print("  ==>   step 5: sector semantics - write a neighbour, re-read the first")
        eb(con, args.ram, pat_b, args.eb_bytes, args.timeout)
        staged = CD.db(con, args.ram, 8, args.timeout)
        if staged != pat_b:
            raise WriteError(f"RAM holds {staged.hex(' ')}, wanted {pat_b.hex(' ')}")
        flw(con, b, args.ram, 8, args.timeout)
        control(con, args.verify_ram, args.timeout)
        neighbour = read_back(con, args.verify_ram, a, 8, args.timeout)
        preserved = neighbour == pat_a
        step("sector-semantics", got=neighbour.hex(" "),
             semantics="read-modify-erase-program" if preserved else "erase-whole-sector")
        if preserved:
            print("  ok    the first pattern survived -> FLW preserves the sector")
        elif neighbour == blank:
            print("  ok    the first pattern is gone -> FLW erases the whole sector")
            print("        A restore must then be sector-sized.  This is a result, "
                  "not a failure.")
        else:
            raise WriteError(f"neither pattern nor blank: {neighbour.hex(' ')}")

        print("  ==>   step 6: put it back")
        eb(con, args.ram, blank, args.eb_bytes, args.timeout)
        flw(con, a, args.ram, 8, args.timeout)
        control(con, args.verify_ram, args.timeout)
        final = read_back(con, args.verify_ram, a, 8, args.timeout)
        step("restore", got=final.hex(" "), erased=(final == blank))
        if final == blank:
            print("  ok    ff ff ff ff ff ff ff ff - FLW can return a byte to ff")
        else:
            print(f"  warn  {final.hex(' ')} - FLW is pure programming here, 1 cannot "
                  "become 0.")
            print("        P0-3's frozen refutation covers this case.  Record it; do "
                  "not retry.")
    except (WriteError, CD.DumpError) as e:
        report["error"] = str(e)
        write_report(args.output, report)
        con.close()
        fail(str(e))
    con.close()
    report["ok"] = True
    write_report(args.output, report)
    return 0


def cmd_write(args) -> int:
    try:
        with open(args.input, "rb") as fh:
            data = fh.read()
    except OSError as e:
        fail(f"cannot read {args.input}: {e}")

    length = args.length if args.length is not None else len(data)
    try:
        is_drill, why = classify(args.flash, length)
        digest = check_payload(
            data, args.flash, length, is_drill,
            args.expect_sha256, args.confirm, args.allow_blank,
        )
    except WriteError as e:
        fail(str(e))

    plan = sector_plan(args.flash, length)
    report: dict = {
        "write": {"flash": args.flash, "length": length, "sha256": digest,
                  "source": os.path.basename(args.input), "range": why,
                  "sectors": len(plan)},
        "steps": [],
    }

    print(f"  ==>   {args.flash:#08x} + {length:#x} ({length} bytes) into: {why}")
    print(f"        payload sha256 {digest}")
    print(f"        {len(plan)} sector(s), one FLW each, staged {args.eb_bytes} "
          f"bytes per EB line")
    if is_secret(args.flash, length):
        print("        this range is per-unit secret: offsets and digests are "
              "logged, bytes are not")

    if args.dry_run:
        dry: list[str] = []
        for payload_off, flash_off, n in plan:
            eb(None, args.ram, data[payload_off:payload_off + n], args.eb_bytes, 0, dry)
            flw(None, flash_off, args.ram, n, 0, dry)
        for line in dry[:args.dry_lines]:
            print(f"  ==>   {line}")
        if len(dry) > args.dry_lines:
            print(f"  ...   {len(dry) - args.dry_lines} more lines "
                  f"({len(dry)} total)")
        write_report(args.output, report)
        return 0

    con = open_console(args)
    try:
        print("  ==>   positive control")
        control(con, args.verify_ram, args.timeout)
        print(f"  ok    flash {CONTROL_FLASH_OFFSET:#08x} -> "
              f"{CONTROL_EXPECT.hex(' ')}")

        for i, (payload_off, flash_off, n) in enumerate(plan, 1):
            chunk = data[payload_off:payload_off + n]
            print(f"  ==>   sector {i}/{len(plan)}: {flash_off:#08x} + {n:#x}")

            eb(con, args.ram, chunk, args.eb_bytes, args.timeout)
            staged = read_ram(con, args.ram, n, args.timeout)
            if staged != chunk:
                bad = first_difference(staged, chunk)
                raise WriteError(
                    f"staged RAM does not match the payload at byte {bad} "
                    f"(flash {flash_off + (bad or 0):#08x}).\n"
                    "        EB did not take what it was given.  **Flash has not "
                    "been written for this\n        sector.**  Re-run `probe-eb` "
                    "with a smaller --eb-bytes."
                )
            print(f"        staged and verified in RAM ({n} bytes)")

            out = flw(con, flash_off, args.ram, n, args.timeout)
            report["steps"].append({
                "sector": i, "flash": flash_off, "bytes": n,
                "sha256": hashlib.sha256(chunk).hexdigest(),
                "flw_reply": out.strip()[:200],
            })
            print("        FLW ok")

        print("  ==>   verify: read the whole range back into a third address")
        control(con, args.verify_ram, args.timeout)
        got = read_back(con, args.verify_ram, args.flash, length, args.timeout)
        bad = first_difference(got, data)
        report["verify"] = {
            "sha256": hashlib.sha256(got).hexdigest(),
            "match": bad is None,
            "first_difference": bad,
        }
        if bad is not None:
            raise WriteError(
                f"read-back differs from the source at byte {bad} "
                f"(flash {args.flash + bad:#08x}).\n"
                f"        source   {redacted(data[bad:bad + 8], args.flash + bad)}\n"
                f"        flash    {redacted(got[bad:bad + 8], args.flash + bad)}\n"
                "        The write did not take.  Do not re-run blindly: read the "
                "range first."
            )
        print(f"  ok    {length} bytes match, sha256 "
              f"{hashlib.sha256(got).hexdigest()}")
    except (WriteError, CD.DumpError) as e:
        report["error"] = str(e)
        write_report(args.output, report)
        con.close()
        fail(str(e))
    con.close()
    report["ok"] = True
    write_report(args.output, report)
    return 0


def read_ram(con, ram: int, length: int, timeout: float) -> bytes:
    out = bytearray()
    step = 256
    for off in range(0, length, step):
        n = min(step, length - off)
        out += CD.db(con, ram + off, n, timeout)
    return bytes(out)


# ---------------------------------------------------------------------------
def auto_int(s: str) -> int:
    return int(s, 0)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="console-write.py",
        description="Write the SPI flash through the RealTek boot loader, with an "
                    "allow-list of two ranges and a read-back on every write.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="The boot loader at 0x000000 and H601 at 0x006000 cannot be written "
               "by this tool at all,\nand no flag changes that.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, need_port=True):
        sp.add_argument("--port", default="/dev/ttyUSB0",
                        help="serial device (default: %(default)s)")
        sp.add_argument("--baud", type=int, default=38400,
                        help="measured on this unit, not guessed (default: %(default)s)")
        sp.add_argument("--at-prompt", action="store_true",
                        help="the board is already sitting at <RealTek>; do not stream ESC")
        sp.add_argument("--window", type=float, default=25.0,
                        help="seconds to stream ESC waiting for power-on (default: %(default)s)")
        sp.add_argument("--timeout", type=float, default=30.0,
                        help="per-command timeout in seconds (default: %(default)s)")
        sp.add_argument("--ram", type=auto_int, default=0x80600000,
                        help="staging address (default: 0x80600000)")
        sp.add_argument("--verify-ram", type=auto_int, default=0x80700000,
                        help="read-back address, deliberately not the staging one "
                             "(default: 0x80700000)")
        sp.add_argument("--eb-bytes", type=int, default=8,
                        help="bytes per EB line; measure it with probe-eb "
                             "(default: %(default)s)")
        sp.add_argument("--dry-run", action="store_true",
                        help="run every check and print the commands; open no port")
        sp.add_argument("--verbose", action="store_true", help="echo every command sent")
        sp.add_argument("-o", "--output", help="write a JSON transcript here")

    sp = sub.add_parser("probe-eb", help="measure how many bytes one EB line takes "
                                         "(RAM only, writes no flash)")
    common(sp)
    sp.add_argument("--sizes", type=int, nargs="+", default=[8, 16, 32, 64],
                    help="line sizes to try, ascending (default: 8 16 32 64)")
    sp.set_defaults(func=cmd_probe_eb)

    sp = sub.add_parser("drill", help="the A2.5 rehearsal at 0x3F0000, with its control")
    common(sp)
    sp.set_defaults(func=cmd_drill)

    sp = sub.add_parser("write", help="write a file to an allow-listed flash range")
    common(sp)
    sp.add_argument("--flash", type=auto_int, required=True, help="target flash offset")
    sp.add_argument("--length", type=auto_int,
                    help="bytes to write (default: the whole input file)")
    sp.add_argument("--input", required=True, help="the bytes to program")
    sp.add_argument("--confirm", type=auto_int,
                    help="repeat --flash exactly; required outside the drill sector")
    sp.add_argument("--expect-sha256",
                    help="sha256 of the payload; required outside the drill sector")
    sp.add_argument("--allow-blank", action="store_true",
                    help="permit an all-0xFF payload (the drill's step 6 is one)")
    sp.add_argument("--dry-lines", type=int, default=12,
                    help="how many command lines --dry-run prints (default: %(default)s)")
    sp.set_defaults(func=cmd_write)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
