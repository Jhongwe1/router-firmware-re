#!/usr/bin/env python3
"""Read the SPI flash through the RealTek boot loader console, and refuse to
produce a file that cannot be shown to be complete.

Why this exists
---------------
The boot loader on this unit exposes ``FLR`` (flash -> RAM) and ``DB`` (show
RAM).  Together they are a complete flash read path that needs no SOIC-8 clip,
no programmer and no risk to the board.  What they are not is a *reliable
transport*: the console is 38400 8N1 with no flow control, and moving 4 MiB
across it means roughly 16 MB of hex text and about 70 minutes of wire time.
Over that distance dropped characters are not a possibility, they are a
schedule.

A dropped character does not announce itself.  It produces a slightly shorter
dump that still looks like a hex dump, and if you paste the log into a naive
converter you get a well-formed image with a hole in it and every offset after
the hole shifted.  Every downstream conclusion - the flash map, the SquashFS
superblock, the address of `boa` - would then be confidently wrong.  This
project's recurring failure mode is a plausible artefact rather than a crash
(PROGRESS.md, W03/W04 instrument notes), so the parser here is built to fail:

  * every line must match the exact ``AAAAAAAA: xx xx ...`` shape
  * addresses must start where they were asked to and rise by exactly 16
  * a chunk with one byte missing is rejected whole and re-read
  * if any chunk cannot be read cleanly, **no output file is written** - only
    a ``.partial`` and a report naming the ranges that failed

What this tool cannot prove
---------------------------
A parser cannot see a corrupted byte that happens to still be two hex digits in
a well-formed line.  Three independent things cover that, and none of them is
this parser:

  1. ``--control``: flash ``0x000000`` is read first and its first four bytes
     must be ``0b f0 00 04`` - the value an earlier, unrelated console session
     recorded (notes/flash-layout.md).  A positive control with a known answer.
  2. ``--verify-sample``: after the dump completes, a random sample of chunks is
     read a second time over the wire and compared.  A transport that corrupts
     bytes silently will not corrupt the same byte twice.
  3. The structure inside the image: the SquashFS at ``0x180000`` must
     decompress.  1.8 MiB of LZMA is an integrity check no serial line survives
     by accident.

The two radix traps in this command set are handled here so nobody has to
remember them: ``FLR`` takes hex for all three arguments and then eats the next
line as the answer to ``(Y)es , (N)o ?``; ``DB`` takes a hex address and a
**decimal** length.

Usage
-----
  # convert a hex dump captured by hand (this is also what the guard suite drives)
  tools/console-dump.py parse capture.txt --base 0x81000000 --length 4096 -o out.bin

  # sit on the port streaming ESC until the boot loader prompt appears
  tools/console-dump.py catch --port /dev/ttyUSB0

  # the whole thing
  tools/console-dump.py dump --port /dev/ttyUSB0 \
      --flash 0x0 --length 0x400000 --ram 0x81000000 -o $FWRE_WORK/dumps/flash.bin

Nothing here writes to the device.  ``FLW``, ``EB``, ``EW`` and ``AUTOBURN``
are never sent; the only commands this file can emit are ``DB`` and ``FLR``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import select
import sys
import textwrap
import time

PROMPT = b"<RealTek>"
CONFIRM = b"(Y)es"

# The real shape of a DB line, captured from the device on 2026-08-16:
#
#      [Addr]   .0 .1 .2 .3 .4 .5 .6 .7 .8 .9 .A .B .C .D .E .F
#     80500000: 00 00 00 00 00 00 80 21 40 90 60 00 00 00 00 00     .......!@.`.....
#
# The first version of this regex had no ASCII column, because it was written
# from the transcript quoted in notes/flash-layout.md - and that note, quite
# properly, had trimmed the column to fit the page. A note is a summary; it is
# not a specification. Every DB line was rejected and the first run died on the
# positive control with "no data lines at all".
#
# Bytes are separated by exactly one space, and the ASCII column by at least
# two, so the boundary is unambiguous. The {1,16} cap and the per-line length
# check in parse_db are the second and third layers: if this regex ever swallows
# part of the ASCII column, the byte count is wrong and the chunk is rejected.
LINE_RE = re.compile(
    rb"^\s*([0-9A-Fa-f]{8})\s*:((?:[ \t][0-9A-Fa-f]{2}){1,16})(?:[ \t]{2,}.*)?[ \t]*$"
)

# Regions of this unit's flash that must never be printed, logged or pasted:
# per-unit MAC addresses and radio calibration, then the live configuration
# (admin credentials, PSK, WPS PIN).  See dumps/README.md and
# notes/flash-layout.md section 6.  Progress output prints offsets only, but an
# error message quoting a bad line would leak bytes, so errors get redacted too.
SECRET_RANGES = ((0x006000, 0x010000),)

# From notes/flash-layout.md - read on 2026-08-15 through a console session that
# has nothing to do with this script.  Used as a positive control: if FLR really
# copied flash 0x000000 into RAM, these are the bytes that must come back.
CONTROL_FLASH_OFFSET = 0x000000
CONTROL_EXPECT = bytes((0x0B, 0xF0, 0x00, 0x04))


class DumpError(Exception):
    """Raised for anything that would otherwise produce a plausible artefact.

    ``sample`` carries what the console actually said.  Without it the first
    real failure of this tool reported "no data lines at all" and nothing else,
    which named the symptom and hid the cause - the cause was one missing
    column in a regex, visible instantly in three lines of raw output.
    """

    def __init__(self, msg: str, sample: bytes = b""):
        super().__init__(msg)
        self.sample = sample


def fail(msg: str) -> None:
    print(f"  FAIL  {msg}", file=sys.stderr)
    raise SystemExit(1)


def is_secret(offset: int, length: int = 1) -> bool:
    return any(offset < hi and offset + length > lo for lo, hi in SECRET_RANGES)


def show_sample(e: DumpError, offset: int, length: int = 1) -> None:
    """Print what the console actually said - unless that would leak the unit.

    An instrument that reports only its own verdict makes you debug the
    instrument.  An instrument that pastes raw flash into a terminal log leaks
    this unit's MAC and admin credentials.  The offset decides which it is.
    """
    if not e.sample:
        return
    if is_secret(offset, length):
        print("        (raw response withheld: this offset is inside the "
              "per-unit secret region 0x006000-0x010000)")
        return
    print("        what the console actually said:")
    for ln in e.sample.decode(errors="replace").splitlines()[:6]:
        print(f"        | {ln.rstrip()}")


# ---------------------------------------------------------------------------
# the parser - pure, no I/O, driven by tools/test-console-dump.sh
# ---------------------------------------------------------------------------
def parse_db(text: bytes, base: int, length: int) -> bytes:
    """Turn one ``DB`` transcript into bytes, or raise.

    Deliberately strict.  Anything unexpected is an error, because the
    alternative - skipping a line that did not parse - is exactly how a hole
    gets into an image that still looks fine.
    """
    if length <= 0:
        raise DumpError("length must be positive")

    out = bytearray()
    expect = base
    seen = 0

    for raw in text.splitlines():
        m = LINE_RE.match(raw)
        if not m:
            continue  # echoed command, banner, prompt - not a data line
        seen += 1
        addr = int(m.group(1), 16)
        data = bytes.fromhex(m.group(2).decode("ascii").replace("\t", " ").replace(" ", ""))

        if addr != expect:
            raise DumpError(
                f"address discontinuity: expected {expect:08X}, got {addr:08X} "
                f"(gap of {addr - expect} bytes at data line {seen}) - "
                "a line was dropped on the wire"
            )
        remaining = length - len(out)
        if len(data) != min(16, remaining):
            raise DumpError(
                f"line at {addr:08X} carries {len(data)} bytes, expected "
                f"{min(16, remaining)} - a byte was dropped inside the line"
            )
        out += data
        expect += len(data)
        if len(out) >= length:
            break

    if seen == 0:
        raise DumpError(
            "no data lines at all - the console returned nothing parseable",
            sample=text[:400],
        )
    if len(out) != length:
        raise DumpError(
            f"short read: {len(out)} of {length} bytes across {seen} lines - "
            "the transcript ends early",
            sample=text[-400:],
        )
    return bytes(out)


# ---------------------------------------------------------------------------
# serial, on stdlib only.  pyserial is not a dependency of this project and a
# capture tool that needs `pip install` before it can be used in a hurry is a
# capture tool that will not be used.
# ---------------------------------------------------------------------------
class Console:
    def __init__(self, path: str, baud: int = 38400, verbose: bool = False):
        import termios

        self.termios = termios
        self.verbose = verbose
        try:
            self.fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        except OSError as e:
            fail(f"cannot open {path}: {e}\n"
                 "        On WSL the adapter must be attached from Windows first:\n"
                 "            usbipd attach --wsl --busid <id>")
        speed = getattr(termios, f"B{baud}", None)
        if speed is None:
            fail(f"{baud} is not a baud rate this platform names (B{baud} missing)")

        attrs = termios.tcgetattr(self.fd)
        cc = list(attrs[6])
        cc[termios.VMIN] = 0
        cc[termios.VTIME] = 0
        # raw: no translation anywhere.  ICRNL in particular would rewrite the
        # boot loader's line endings and the address regex would stop matching.
        termios.tcsetattr(
            self.fd, termios.TCSANOW,
            [0, 0, termios.CS8 | termios.CREAD | termios.CLOCAL, 0, speed, speed, cc],
        )
        termios.tcflush(self.fd, termios.TCIOFLUSH)

    def write(self, data: bytes) -> None:
        os.write(self.fd, data)

    def read_until(self, needle: bytes, timeout: float, keep: bool = True) -> bytes:
        """Read until *needle* appears.  Returns everything read, needle included."""
        buf = bytearray()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            r, _, _ = select.select([self.fd], [], [], 0.2)
            if r:
                chunk = os.read(self.fd, 4096)
                if chunk:
                    buf += chunk
                    if needle in buf:
                        return bytes(buf) if keep else bytes(buf).replace(needle, b"")
        raise DumpError(
            f"timed out after {timeout:.0f}s waiting for {needle!r} "
            f"({len(buf)} bytes read)"
        )

    def command(self, cmd: bytes, timeout: float) -> bytes:
        self.termios.tcflush(self.fd, self.termios.TCIFLUSH)
        if self.verbose:
            print(f"  >>>   {cmd.decode(errors='replace')}")
        self.write(cmd + b"\r")
        return self.read_until(PROMPT, timeout)

    def close(self) -> None:
        os.close(self.fd)


def catch_prompt(con: Console, seconds: float) -> None:
    """Stream ESC across power-on until the boot loader answers.

    The interrupt window is about a second wide and opens the moment the board
    comes up, so ESC has to already be in flight.  Pressing it after output
    appears is too late - see notes/uart-pinout.md section 4.
    """
    print()
    print("  streaming ESC.  >>> POWER THE ROUTER ON NOW <<<")
    print(f"  ({seconds:.0f}s window; Ctrl-C to give up)")
    deadline = time.monotonic() + seconds
    buf = bytearray()
    while time.monotonic() < deadline:
        con.write(b"\x1b")
        r, _, _ = select.select([con.fd], [], [], 0.02)
        if r:
            buf += os.read(con.fd, 4096)
            if PROMPT in buf:
                print("  ok    <RealTek> - the boot loader is ours")
                if b"RTL8196" in buf:
                    banner = next(
                        (ln for ln in buf.splitlines() if b"RealTek(RTL" in ln), b""
                    )
                    print(f"        {banner.decode(errors='replace').strip()}")
                time.sleep(0.3)
                con.termios.tcflush(con.fd, con.termios.TCIFLUSH)
                return
    if not buf:
        raise DumpError(
            "nothing came back at all.  TX/RX swapped, wrong port, or the board "
            "never powered on"
        )
    raise DumpError(
        "the board booted past the interrupt window.  Power off, run this "
        "again, and only then power on"
    )


def settle(con: Console, tries: int = 4) -> bool:
    """Clear what the interrupt technique leaves in the boot loader's line buffer.

    ``catch_prompt`` streams ESC continuously because the interrupt window is
    about a second wide.  The boot loader consumes one ESC to break out of the
    boot - and the rest stay queued in its input buffer.  So the FIRST command
    sent after a successful catch arrives with a pile of ESCs in front of it and
    comes back ``Unknown command !``.

    Found on 2026-08-16: immediately after a clean catch, ``?`` returned
    ``Unknown command !``, while a session on 2026-08-15 had used ``?`` to print
    the whole command set.  Two sessions disagreeing about the same device is
    the instrument talking, not the device - and here the instrument was the ESC
    stream this file writes.

    This matters beyond cosmetics: without it the first command of a dump run is
    the ``FLR`` positive control, and it would have been eaten.
    """
    for _ in range(tries):
        con.termios.tcflush(con.fd, con.termios.TCIOFLUSH)
        con.write(b"\r")
        try:
            out = con.read_until(PROMPT, 5.0)
        except DumpError:
            continue
        if b"Unknown command" not in out:
            return True
    return False


# ---------------------------------------------------------------------------
# device operations
# ---------------------------------------------------------------------------
def flr(con: Console, ram: int, flash: int, length: int, timeout: float = 60.0) -> None:
    """flash -> RAM.  All three arguments hex; then the confirmation line."""
    con.termios.tcflush(con.fd, con.termios.TCIFLUSH)
    con.write(f"FLR {ram:X} {flash:X} {length:X}\r".encode())
    try:
        con.read_until(CONFIRM, 10.0)
    except DumpError as e:
        raise DumpError(f"FLR did not ask for confirmation: {e}") from e
    # It eats the whole next line as the answer.  Sending the next command here
    # instead of Y gets 'Abort!' and then a spurious 'Unknown command !', and a
    # later DB then returns stale RAM that looks entirely reasonable.
    con.write(b"Y\r")
    out = con.read_until(PROMPT, timeout)
    if b"Abort" in out:
        raise DumpError("FLR aborted - the confirmation was not accepted")


def db(con: Console, ram: int, length: int, timeout: float) -> bytes:
    """RAM -> hex text -> bytes.  Address hex, length DECIMAL."""
    out = con.command(f"DB {ram:X} {length}".encode(), timeout)
    return parse_db(out, ram, length)


def read_range(
    con: Console, ram: int, flash: int, length: int, chunk: int, retries: int,
    label: str = "", progress: bool = True,
) -> tuple[bytes, list[dict]]:
    """DB the already-FLR'd RAM window out in chunks, validating each one."""
    data = bytearray()
    stats: list[dict] = []
    started = time.monotonic()
    done = 0
    # 16 bytes of data cost about 60 bytes of hex text; at 38400 that is ~64
    # bytes/s of payload.  Allow 4x that before calling a chunk hung.
    per_chunk_timeout = max(20.0, (chunk / 16.0) * 60.0 / 3840.0 * 4.0)

    while done < length:
        n = min(chunk, length - done)
        off = flash + done
        last_err = ""
        for attempt in range(1, retries + 2):
            try:
                block = db(con, ram + done, n, per_chunk_timeout)
                stats.append({"flash_offset": off, "bytes": n, "attempts": attempt})
                data += block
                break
            except DumpError as e:
                last_err = str(e)
                if attempt <= retries:
                    print(f"\n  warn  {off:#08x}: {e}")
                    show_sample(e, off, n)
                    print(f"        re-reading (attempt {attempt + 1} of "
                          f"{retries + 1})")
                    time.sleep(0.5)
                    con.termios.tcflush(con.fd, con.termios.TCIOFLUSH)
        else:
            raise DumpError(
                f"chunk at flash {off:#08x} failed {retries + 1} times: {last_err}"
            )
        done += n
        if progress:
            elapsed = time.monotonic() - started
            rate = done / elapsed if elapsed > 0 else 0
            eta = (length - done) / rate if rate > 0 else 0
            pct = 100.0 * done / length
            print(f"\r  {label}{done:>8}/{length} bytes  {pct:5.1f}%  "
                  f"{rate:6.0f} B/s  eta {eta / 60:5.1f} min", end="", flush=True)
    if progress:
        print()
    return bytes(data), stats


# ---------------------------------------------------------------------------
# subcommands
# ---------------------------------------------------------------------------
def cmd_parse(args) -> int:
    with open(args.input, "rb") as fh:
        text = fh.read()
    try:
        data = parse_db(text, args.base, args.length)
    except DumpError as e:
        fail(str(e))
    if args.output:
        with open(args.output, "wb") as fh:
            fh.write(data)
        print(f"  ok    {len(data)} bytes -> {args.output}")
        print(f"  ok    sha256  {hashlib.sha256(data).hexdigest()}")
    else:
        print(f"  ok    {len(data)} bytes parsed, sha256 "
              f"{hashlib.sha256(data).hexdigest()}")
    return 0


def cmd_catch(args) -> int:
    con = Console(args.port, args.baud, args.verbose)
    try:
        catch_prompt(con, args.window)
        if settle(con):
            print("  ok    input buffer drained (the ESC stream leaves ESCs queued)")
        else:
            print("  warn  could not get a clean prompt after draining")
        out = con.command(b"?", 10.0)
        print("  ok    command set:")
        for ln in out.decode(errors="replace").splitlines():
            if ln.strip() and not ln.startswith("?"):
                print(f"        {ln.rstrip()}")
    except DumpError as e:
        fail(str(e))
    finally:
        con.close()
    return 0


# Commands that modify the device.  This tool exists to read; it refuses to be
# the thing that bricked the only unit that gates G2 and G4.
FORBIDDEN = ("FLW", "EB", "EW", "AUTOBURN", "J ")


def cmd_cmd(args) -> int:
    text = " ".join(args.words).strip()
    upper = text.upper()
    for bad in FORBIDDEN:
        if upper.startswith(bad.strip()):
            fail(f"refusing to send {text!r}: {bad.strip()} writes to the device.\n"
                 "        This tool only reads.  If you genuinely need to write, "
                 "type it into picocom yourself, having decided to.")
    con = Console(args.port, args.baud, args.verbose)
    try:
        if not args.at_prompt:
            catch_prompt(con, args.window)
        settle(con)
        out = con.command(text.encode(), args.timeout)
        print(out.decode(errors="replace"))
    except DumpError as e:
        fail(str(e))
    finally:
        con.close()
    return 0


def cmd_rescue(args) -> int:
    """P9-3: bring up the boot loader's network side, and nothing else.

    `AUTOBURN` is on FORBIDDEN above and that is right for `cmd`, which exists to
    read. It is wrong for this one operation, and the reason is worth writing
    down because it inverts the usual argument for a guard:

        `AUTOBURN: 0` is the command that makes every later command safe. It is
        the switch deciding whether a file arriving over TFTP gets written to
        flash. Refusing to send it does not prevent a dangerous action -- it
        pushes the dangerous action onto a human typing `AUTOBURN: 0` into
        picocom, one keystroke away from the opposite value, on the only unit
        there is.

    So this subcommand exists and it is deliberately narrow:

      * the only autoburn value it can emit is `0`. There is no flag for 1, and
        adding one would be a change to this file that shows up in a diff.
      * it asserts the loader echoed `AutoBurning=0`. If the reply says 1, the
        run stops -- the command did the opposite of what was asked and nothing
        else should be sent.
      * it never sends LOADADDR, never sends J, and uploads nothing. Entering
        rescue and confirming its network answers is the whole of what P9-3's
        frozen refutation asks ("if rescue mode cannot be entered..."), and an
        upload is not part of that question.

    The expected replies are not folklore: they are the format strings recovered
    from the loader's own LZMA second stage by tools/loader-unpack.py --
        0x0b430  AutoBurning=%d
        0x0b374   Target Address=%d.%d.%d.%d
        0x0b394  Now your Target IP is %d.%d.%d.%d
    """
    try:
        octets = [int(p) for p in args.ip.split(".")]
        if len(octets) != 4 or not all(0 <= o <= 255 for o in octets):
            raise ValueError
    except ValueError:
        fail(f"--ip {args.ip!r} is not a dotted quad")

    con = Console(args.port, args.baud, args.verbose)
    report: dict = {"ip": args.ip, "steps": []}
    try:
        if not args.at_prompt:
            catch_prompt(con, args.window)
        if not settle(con):
            raise DumpError("could not get a clean prompt")

        # The help prints `AUTOBURN: 0/1`, and that is not the syntax. The
        # loader's own string table holds `AUTOBURN` and `AUTOBURN: 0/1` as two
        # separate strings -- a command token and a help line -- and the same is
        # true of IPCONFIG and LOADADDR. This is the third time this loader's
        # documentation disagrees with its parser: `HELP` is rejected while `?`
        # works, and FLR and FLW punctuate their confirmation prompts
        # differently.
        #
        # So the forms are tried in order, and EVERY one of them carries 0.
        # There is no arrangement of these candidates that turns autoburn on.
        print("  ==>   autoburn off   (the switch that decides whether an upload "
              "reaches flash)")
        out = ""
        for form in ("AUTOBURN: 0", "AUTOBURN 0", "AUTOBURN=0", "AUTOBURN:0"):
            out = con.command(form.encode(), args.timeout).decode(errors="replace")
            report["steps"].append({"sent": form, "reply": out})
            if "Unknown command" not in out:
                print(f"  ok    the form this loader accepts is {form!r}")
                break
            print(f"        {form!r} -> Unknown command !")
        print(textwrap.indent(out.strip(), "        "))
        if "AutoBurning=1" in out:
            raise DumpError(
                "the loader replied AutoBurning=1. It did the opposite of what "
                "was asked, and with autoburn on, anything arriving over TFTP "
                "is written to flash. Sending nothing further.")
        if "AutoBurning=0" not in out:
            raise DumpError(
                "the loader did not echo AutoBurning=0, so the state of the "
                "switch is unknown. That is not a state to bring a network up in."
            )
        print("  ok    autoburn is off")

        print(f"  ==>   IPCONFIG {args.ip}")
        out = ""
        for form in (f"IPCONFIG:{args.ip}", f"IPCONFIG {args.ip}",
                     f"IPCONFIG={args.ip}"):
            out = con.command(form.encode(), args.timeout).decode(errors="replace")
            report["steps"].append({"sent": form, "reply": out})
            if "Unknown command" not in out:
                print(f"  ok    the form this loader accepts is {form!r}")
                break
            print(f"        {form!r} -> Unknown command !")
        print(textwrap.indent(out.strip(), "        "))
        if args.ip not in out:
            raise DumpError(
                f"the loader did not echo {args.ip}. Its network is not "
                "configured, so a ping failing afterwards would prove nothing")
        print(f"  ok    the loader reports {args.ip}")
        print()
        # This block used to say: ping it, and a reply is the whole of what P9-3
        # asks. Both halves of that were wrong and the bench refuted them on
        # 2026-08-17 -- a TFTP-only stack owes nobody an ICMP implementation, and
        # the loader synthesises its MAC from the address it was handed
        # (0a:01:01:01 for 10.1.1.1), so it is not this unit's MAC either.
        #
        # The advice survived the refutation because tools/check-runsheet.py
        # reads runsheet.md and RUNBOOK.md, and nothing reads what the tools
        # themselves print. Same shape as instrument bug 22, one file further out.
        print("  ==>   ping will NOT answer, and that is not a failure.")
        print("        This loader implements TFTP and no ICMP at all, measured "
              "2026-08-17.")
        print("        What does show the link is live, none of it needing an "
              "upload:")
        print("          * arp -n " + args.ip + "  resolves")
        print("          * the host interface's rx_packets counter moves")
        print("          * a TFTP read request comes back with DATA")
        print("        Entering rescue mode is the whole of what P9-3 asks. "
              "Nothing is uploaded.")
    except DumpError as e:
        fail(str(e))
    finally:
        con.close()
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"  ok    transcript -> {args.output}")
    return 0


def cmd_dump(args) -> int:
    if os.path.exists(args.output) and not args.force:
        fail(f"{args.output} exists.  Refusing to overwrite a dump - pass --force "
             "only if you are certain the existing one is worthless")

    con = Console(args.port, args.baud, args.verbose)
    report: dict = {
        "port": args.port, "baud": args.baud,
        "flash_offset": args.flash, "length": args.length,
        "ram": args.ram, "chunk": args.chunk,
        "control": None, "verify_sample": None,
    }
    t0 = time.monotonic()
    try:
        if not args.at_prompt:
            catch_prompt(con, args.window)
        if not settle(con):
            raise DumpError(
                "could not get a clean prompt.  Every command would arrive with "
                "queued input in front of it"
            )

        # -- positive control -------------------------------------------------
        # Read a region whose first bytes an unrelated session already recorded.
        # This is what separates "FLR copied the flash" from "that is whatever
        # happened to be in RAM already" - the distinction that cost an evening
        # on 2026-08-15 and was settled there by the same trick.
        if not args.no_control:
            print("  ==>   control: FLR flash 0x000000 -> RAM, expecting "
                  f"{CONTROL_EXPECT.hex(' ')}")
            flr(con, args.ram, CONTROL_FLASH_OFFSET, 64)
            try:
                head = db(con, args.ram, 64, 30.0)[:4]
            except DumpError as e:
                show_sample(e, CONTROL_FLASH_OFFSET, 64)
                raise
            report["control"] = {"expected": CONTROL_EXPECT.hex(" "),
                                 "observed": head.hex(" ")}
            if head != CONTROL_EXPECT:
                raise DumpError(
                    f"control failed: flash 0x000000 begins {head.hex(' ')}, "
                    f"but a console session on 2026-08-15 read "
                    f"{CONTROL_EXPECT.hex(' ')}.  Either the read path is wrong "
                    "or the flash changed - both are findings, neither is a dump"
                )
            print(f"  ok    control matched: {head.hex(' ')}")

        # -- the read ---------------------------------------------------------
        print(f"  ==>   FLR flash {args.flash:#08x} +{args.length:#x} "
              f"-> RAM {args.ram:#010x}")
        flr(con, args.ram, args.flash, args.length, timeout=args.flr_timeout)
        print("  ==>   DB, chunked and validated per chunk")
        data, stats = read_range(con, args.ram, args.flash, args.length,
                                 args.chunk, args.retries)

        # The bytes are in hand and they cost 95 minutes.  Write them out
        # BEFORE verification: a transport hiccup during the second pass must
        # never be able to discard a complete read.  Verification then decides
        # what the file is *called*, not whether it exists.
        with open(args.output, "wb") as fh:
            fh.write(data)

        # -- second pass over a sample ---------------------------------------
        # The parser cannot see a corrupted byte inside a well-formed line.  A
        # re-read can: a transport that flips a bit will not flip the same bit
        # twice.  Cheap, because it is a sample.
        #
        # Two failures live here and they are not the same failure:
        #   a chunk that will not parse  -> the wire hiccuped.  Retry; if it
        #                                   still will not parse, that chunk is
        #                                   simply unverified.  Not fatal.
        #   a chunk that parses and DIFFERS -> the transport is corrupting bytes
        #                                   inside well-formed lines.  Fatal.
        # Conflating them means one dropped character at minute 94 throws away
        # a good dump, which is how an over-strict instrument teaches its
        # operator to stop running it.
        if args.verify_sample > 0 and len(stats) > 1:
            rng = random.Random(args.seed)
            k = max(1, int(len(stats) * args.verify_sample))
            picks = rng.sample(range(len(stats)), k)
            print(f"  ==>   verifying {k} of {len(stats)} chunks by re-reading them")
            bad: list[int] = []
            unverified: list[int] = []
            for i in picks:
                off = stats[i]["flash_offset"] - args.flash
                n = stats[i]["bytes"]
                for _attempt in range(args.retries + 1):
                    try:
                        again = db(con, args.ram + off, n, 90.0)
                        if again != data[off:off + n]:
                            bad.append(stats[i]["flash_offset"])
                        break
                    except DumpError:
                        con.termios.tcflush(con.fd, con.termios.TCIOFLUSH)
                        time.sleep(0.5)
                else:
                    unverified.append(stats[i]["flash_offset"])
            report["verify_sample"] = {
                "chunks": k, "mismatched": bad, "unreadable": unverified,
            }
            if bad:
                raise DumpError(
                    "re-reading disagreed with the first pass at "
                    + ", ".join(f"{b:#08x}" for b in bad)
                    + " - the transport is corrupting bytes inside well-formed "
                    "lines, which no parser can see.  The dump is not evidence."
                )
            if unverified:
                print(f"  warn  {len(unverified)} sampled chunks could not be "
                      "re-read at all; they are unverified, not wrong")
            print(f"  ok    {k - len(unverified)} of {k} re-read chunks identical")

    except DumpError as e:
        # Two different situations, and they must not share a filename:
        #   read never completed        -> .partial  (a fragment)
        #   read completed, trust did not -> .suspect (whole, but not evidence)
        # Neither is allowed to keep the name a good dump would have had.
        blob = locals().get("data", b"")
        if os.path.exists(args.output):
            os.replace(args.output, args.output + ".suspect")
            where, what = args.output + ".suspect", "a complete read that FAILED VERIFICATION"
        else:
            where = args.output + ".partial"
            with open(where, "wb") as fh:
                fh.write(blob)
            what = "a partial dump, NOT an image"
        fail(f"{e}\n"
             f"        wrote {where} - {what}.\n"
             "        It does not carry the output name on purpose: an image "
             "that looks complete and is not\n"
             "        is worse than no image.")
    except KeyboardInterrupt:
        fail("interrupted by the operator - no output file written")
    finally:
        con.close()

    digest = hashlib.sha256(data).hexdigest()
    report.update({
        "bytes": len(data), "sha256": digest,
        "seconds": round(time.monotonic() - t0, 1),
        "chunks": len(stats),
        "chunks_needing_retry": sum(1 for s in stats if s["attempts"] > 1),
        "tool": "tools/console-dump.py",
    })
    with open(args.output + ".json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    print()
    print(f"  ok    {len(data)} bytes -> {args.output}")
    print(f"  ok    sha256  {digest}")
    print(f"  ok    {report['chunks']} chunks, "
          f"{report['chunks_needing_retry']} needed a re-read, "
          f"{report['seconds'] / 60:.1f} min")
    print()
    print("  This dump is REPEATABLE and CONTROLLED.  It is not yet CORROBORATED:")
    print("    - the structural check against the 2026-08-15 console windows")
    print("    - the SquashFS at 0x180000 must decompress")
    print("    - a second read by a different instrument (a 3.3 V programmer)")
    return 0


def auto_int(s: str) -> int:
    return int(s, 0)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("parse", help="convert a captured DB transcript to binary")
    pp.add_argument("input")
    pp.add_argument("--base", type=auto_int, required=True,
                    help="address the DB command was given")
    pp.add_argument("--length", type=auto_int, required=True,
                    help="bytes the DB command was asked for")
    pp.add_argument("-o", "--output")
    pp.set_defaults(func=cmd_parse)

    pc = sub.add_parser("catch", help="stream ESC across power-on, then show '?'")
    pc.add_argument("--port", default="/dev/ttyUSB0")
    pc.add_argument("--baud", type=int, default=38400)
    pc.add_argument("--window", type=float, default=60.0)
    pc.add_argument("-v", "--verbose", action="store_true")
    pc.set_defaults(func=cmd_catch)

    px = sub.add_parser("cmd", help="send one read-only command and print the reply")
    px.add_argument("words", nargs="+")
    px.add_argument("--port", default="/dev/ttyUSB0")
    px.add_argument("--baud", type=int, default=38400)
    px.add_argument("--window", type=float, default=120.0)
    px.add_argument("--timeout", type=float, default=15.0)
    px.add_argument("--at-prompt", action="store_true")
    px.add_argument("-v", "--verbose", action="store_true")
    px.set_defaults(func=cmd_cmd)

    pr = sub.add_parser("rescue",
                        help="P9-3: autoburn OFF, then bring up the loader's IP. "
                             "Uploads nothing, writes no flash")
    pr.add_argument("--ip", required=True, help="the address the loader answers on")
    pr.add_argument("--port", default="/dev/ttyUSB0")
    pr.add_argument("--baud", type=int, default=38400)
    pr.add_argument("--window", type=float, default=120.0)
    pr.add_argument("--timeout", type=float, default=15.0)
    pr.add_argument("--at-prompt", action="store_true")
    pr.add_argument("-o", "--output", help="JSON transcript")
    pr.add_argument("-v", "--verbose", action="store_true")
    pr.set_defaults(func=cmd_rescue)

    pd = sub.add_parser("dump", help="FLR + DB a flash range into a file")
    pd.add_argument("--port", default="/dev/ttyUSB0")
    pd.add_argument("--baud", type=int, default=38400)
    pd.add_argument("--flash", type=auto_int, default=0)
    pd.add_argument("--length", type=auto_int, default=0x400000)
    pd.add_argument("--ram", type=auto_int, default=0x81000000,
                    help="RAM staging address; well clear of the kernel's 0x80500000")
    pd.add_argument("--chunk", type=auto_int, default=4096)
    pd.add_argument("--retries", type=int, default=3)
    pd.add_argument("--verify-sample", type=float, default=0.05)
    pd.add_argument("--seed", type=int, default=1)
    pd.add_argument("--window", type=float, default=60.0)
    pd.add_argument("--flr-timeout", type=float, default=120.0)
    pd.add_argument("--at-prompt", action="store_true",
                    help="the board is already sitting at <RealTek>")
    pd.add_argument("--no-control", action="store_true",
                    help="skip the positive control (do not)")
    pd.add_argument("--force", action="store_true")
    pd.add_argument("-v", "--verbose", action="store_true")
    pd.add_argument("-o", "--output", required=True)
    pd.set_defaults(func=cmd_dump)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
