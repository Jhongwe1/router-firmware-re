#!/usr/bin/env python3
"""Build the RAM payload P9-12 needs: something that speaks the moment it runs.

Why this exists
---------------
`P9-12`'s refutation condition was frozen on 2026-08-18 and it names its own
blind spot.  Clause (b), whose owner is that row in ``test-cases.toml`` and which
is not restated here: **if the console says nothing after `J`, "it jumped and the
target was silent" cannot be told from "it never jumped", the row can only be
recorded `partial`, and the next measurement has to be named -- the cheapest
being an uploaded image whose first act is to write a character to the UART.**

So an upload of *anything* -- a firmware image, a text file, random bytes --
cannot close that row.  Only an image whose first act is visible can, and until
2026-08-21 nothing in this repository produced one: `runsheet.md` `A2.7` named
``$HOME/fwre-work/w08-ramboot.bin`` and no tool, target or script anywhere
created that file.

What it emits
-------------
About forty instructions of big-endian MIPS-I that print a marker string to the
UART, wait, and print it again, forever.  It is **position independent** -- the
address is recovered with ``bal`` rather than assumed -- so the same bytes work
whatever the loader's ``LOADADDR`` happens to be, and that claim is *tested*
rather than asserted (see ``--load`` below).

Where the UART address comes from, and why it is not from memory
----------------------------------------------------------------
``0xB8002000`` (THR) and ``0xB8002014`` (LSR, bits ``0x60`` = THRE|TEMT) are read
out of **this loader's own putchar**, at ``0x80406B6C`` in the decompressed second
stage::

    80406b6c  lui   v0,0xb800
    80406b70  ori   a1,v0,0x2014      <- LSR
    80406b78  slti  v0,v1,6540        <- bounded spin, then write anyway
    80406b84  lbu   v0,0(a1)
    80406b8c  andi  v0,v0,0x60        <- THRE|TEMT
    80406b9c  ori   v1,v0,0x2000      <- THR
    80406ba0  sb    a0,0(v1)

The bounded spin is copied deliberately.  An unbounded one would turn "the UART
never asserts THRE" into silence on the console, and silence is exactly the
observation `P9-12` cannot interpret.  Bounded, "no output" means "did not
execute" much more strongly than it otherwise would.

How this is allowed to fail
---------------------------
* a marker that already exists in flash proves nothing when it appears on the
  console, so ``--check-absent`` searches the files it is given and refuses;
* the payload is **simulated** before it is written -- every build runs the
  encoded words through the interpreter at the bottom of this file against a
  stand-in UART, and refuses unless the bytes that come out are exactly the
  marker.  A payload nobody has executed is a hypothesis;
* it is simulated at **two different load addresses** and refuses unless both
  produce identical output, which is what "position independent" means;
* a message with a NUL or a byte above 0x7F is refused: the payload's loop ends
  at NUL, and a high byte is not something a 38400 8N1 console renders back;
* an existing output file is not overwritten without ``--force``;
* a load address that is not word-aligned, or outside KSEG0/KSEG1, is refused --
  ``J`` on this loader jumps to whatever it parsed and prints nothing first
  (``0x8040925C``; and with no argument at all it jumps to uninitialised stack).

Usage
-----
  tools/mkramboot.py --nonce 3f7c91a2 -o "$HOME/fwre-work/w08-ramboot.bin" \
      --check-absent "$HOME/fwre-work/dumps/flash-n150rt-console-2.bin" \
      --report "$HOME/fwre-work/dumps/w08-ramboot.json"
  tools/mkramboot.py --nonce 3f7c91a2 --print-disassembly
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
import sys

# The loader's own putchar, read at 0x80406B6C.  Named rather than inlined so
# that the disassembly listing and the simulator cannot drift apart from the
# encoder.
UART_BASE = 0xB8002000
UART_THR = 0x2000          # transmit holding register, byte wide
UART_LSR = 0x2014          # line status register
LSR_TX_EMPTY = 0x60        # THRE | TEMT, the pair the loader tests
TX_SPIN = 6540             # the loader's own bound at 0x80406B78

# ~1 second between banners at 400 MHz, three instructions to the iteration.
# This is a chosen constant, NOT a measurement: nothing here has clocked this
# CPU, and the interval on the console is whatever it is.
DEFAULT_DELAY_HI = 0x0800

DEFAULT_MAX_BYTES = 1024
KSEG = (0x80000000, 0xC0000000)

ZERO, AT, V0, V1, A0, A1, A2, A3 = 0, 1, 2, 3, 4, 5, 6, 7
T0, T1, T2, T3, T4 = 8, 9, 10, 11, 12
S0, S1 = 16, 17
RA = 31

REGNAME = {0: "zero", 4: "a0", 8: "t0", 9: "t1", 10: "t2", 11: "t3", 12: "t4",
           16: "s0", 17: "s1", 31: "ra"}


def fail(msg: str) -> None:
    print(f"  FAIL  {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# encoder -- only the forms this payload uses, so that an unsupported one is a
# crash here rather than a wrong word in an image nobody can single-step.
# ---------------------------------------------------------------------------
def _i(op: int, rs: int, rt: int, imm: int) -> int:
    return (op << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def lui(rt: int, imm: int) -> int:
    return _i(0x0F, 0, rt, imm)


def ori(rt: int, rs: int, imm: int) -> int:
    return _i(0x0D, rs, rt, imm)


def andi(rt: int, rs: int, imm: int) -> int:
    return _i(0x0C, rs, rt, imm)


def addiu(rt: int, rs: int, imm: int) -> int:
    return _i(0x09, rs, rt, imm)


def lbu(rt: int, base: int, off: int) -> int:
    return _i(0x24, base, rt, off)


def sb(rt: int, base: int, off: int) -> int:
    return _i(0x28, base, rt, off)


def addu(rd: int, rs: int, rt: int) -> int:
    return (rs << 21) | (rt << 16) | (rd << 11) | 0x21


def beq(rs: int, rt: int, off: int) -> int:
    return _i(0x04, rs, rt, off)


def bne(rs: int, rt: int, off: int) -> int:
    return _i(0x05, rs, rt, off)


def bal(off: int) -> int:
    # bgezal $zero, off -- always taken, and $ra becomes the address after the
    # delay slot.  That is the whole of this payload's position independence.
    return _i(0x01, ZERO, 0x11, off)


NOP = 0


def branch_off(here: int, target: int) -> int:
    """Words, relative to the delay slot -- ``target = PC + 4 + (offset << 2)``.

    Version 1 of this used ``PC + 8``, which is how the offset is often described
    ("relative to the instruction after the delay slot"), and every branch in the
    payload landed one word early.  The arithmetic is settled by two instructions
    out of this loader's own putchar rather than by a reference::

        80406b7c  10400007  beqz v0,0x80406b9c    0x6b7c + 4 + 7*4  = 0x6b9c
        80406b90  1040fff9  beqz v0,0x80406b78    0x6b90 + 4 + -7*4 = 0x6b78

    The simulator below is what caught it: the payload assembled, looked
    plausible, and printed the first byte of the banner forty-one times.
    """
    delta = target - (here + 4)
    if delta % 4:
        raise ValueError("branch target is not word aligned")
    words = delta // 4
    if not -0x8000 <= words < 0x8000:
        raise ValueError(f"branch out of range: {words} words")
    return words


def build(message: bytes, delay_hi: int = DEFAULT_DELAY_HI) -> tuple[bytes, list[tuple[int, str]]]:
    """Return (image, listing).  Offsets below are the labels, kept explicit so
    that the branch arithmetic is checked against them rather than counted."""
    body_len = 0x68
    msg = message + b"\x00"
    while len(msg) % 4:
        msg += b"\x00"

    L_OUTER, L_NEXT, L_WAIT, L_EMIT, L_DELAY, L_DLOOP, L_MSG = (
        0x18, 0x1C, 0x2C, 0x44, 0x50, 0x54, body_len)

    prog: list[tuple[int, int, str]] = [
        (0x00, bal(branch_off(0x00, 0x08)), "bal     0x08"),
        (0x04, NOP, "nop"),
        (0x08, addiu(S0, RA, L_MSG - 0x08), f"addiu   s0,ra,{L_MSG - 0x08:#x}"),
        (0x0C, lui(T0, UART_BASE >> 16), f"lui     t0,{UART_BASE >> 16:#x}"),
        (0x10, ori(T1, T0, UART_LSR), f"ori     t1,t0,{UART_LSR:#x}"),
        (0x14, ori(T0, T0, UART_THR), f"ori     t0,t0,{UART_THR:#x}"),
        (L_OUTER, addu(S1, S0, ZERO), "addu    s1,s0,zero"),
        (L_NEXT, lbu(A0, S1, 0), "lbu     a0,0(s1)"),
        (0x20, beq(A0, ZERO, branch_off(0x20, L_DELAY)), "beq     a0,zero,delay"),
        (0x24, addiu(S1, S1, 1), "addiu   s1,s1,1"),
        (0x28, addiu(T3, ZERO, TX_SPIN), f"addiu   t3,zero,{TX_SPIN}"),
        (L_WAIT, lbu(T2, T1, 0), "lbu     t2,0(t1)"),
        (0x30, andi(T2, T2, LSR_TX_EMPTY), f"andi    t2,t2,{LSR_TX_EMPTY:#x}"),
        (0x34, bne(T2, ZERO, branch_off(0x34, L_EMIT)), "bne     t2,zero,emit"),
        (0x38, addiu(T3, T3, -1), "addiu   t3,t3,-1"),
        (0x3C, bne(T3, ZERO, branch_off(0x3C, L_WAIT)), "bne     t3,zero,wait"),
        (0x40, NOP, "nop"),
        (L_EMIT, sb(A0, T0, 0), "sb      a0,0(t0)"),
        (0x48, beq(ZERO, ZERO, branch_off(0x48, L_NEXT)), "b       next"),
        (0x4C, NOP, "nop"),
        (L_DELAY, lui(T4, delay_hi), f"lui     t4,{delay_hi:#x}"),
        (L_DLOOP, addiu(T4, T4, -1), "addiu   t4,t4,-1"),
        (0x58, bne(T4, ZERO, branch_off(0x58, L_DLOOP)), "bne     t4,zero,dloop"),
        (0x5C, NOP, "nop"),
        (0x60, beq(ZERO, ZERO, branch_off(0x60, L_OUTER)), "b       outer"),
        (0x64, NOP, "nop"),
    ]

    words = bytearray()
    listing: list[tuple[int, str]] = []
    for want_off, word, text in prog:
        if want_off != len(words):
            raise AssertionError(
                f"layout drift: {text} is at {len(words):#x}, the label says {want_off:#x}")
        words += struct.pack(">I", word)
        listing.append((want_off, f"{word:08x}  {text}"))
    if len(words) != body_len:
        raise AssertionError(f"body is {len(words):#x}, the labels assume {body_len:#x}")
    listing.append((body_len, f"{'':8}  .ascii {message!r}"))
    return bytes(words) + msg, listing


# ---------------------------------------------------------------------------
# simulator -- the reason a build here is evidence rather than an intention.
#
# It implements exactly the forms the encoder emits, including the branch delay
# slot, and it models the UART as a register file: reads of LSR return a status,
# writes to THR append to a buffer.  If the payload does anything else -- an
# opcode this does not know, a load or store outside the image and the UART, or
# more instructions than a bound -- it stops and says which.
#
# It carries the DEVICE's addresses, deliberately not the encoder's constants.
# Version 1 shared them, and the guard suite showed what that costs: patching
# UART_THR moved the payload and the model together, so a store to the wrong
# address was a store the model happily accepted.  A model that follows the
# thing it is checking is not a model.
# ---------------------------------------------------------------------------
SIM_THR = 0xB8002000      # from the loader's putchar, 0x80406B9C: ori v1,v0,0x2000
SIM_LSR = 0xB8002014      # from 0x80406B70: ori a1,v0,0x2014
SIM_LSR_IDLE = 0x60       # what a 16550 with an empty transmitter reports


class SimError(Exception):
    pass


class SimResult:
    """What came out of the UART, and how hard the payload had to work for it."""

    def __init__(self, out: bytes, lsr_reads: int, steps: int) -> None:
        self.out, self.lsr_reads, self.steps = out, lsr_reads, steps


def simulate(image: bytes, load: int, *, lsr_value: int = SIM_LSR_IDLE,
             max_steps: int = 4_000_000, want_bytes: int = 0) -> SimResult:
    reg = [0] * 32
    out = bytearray()
    pc = load
    steps = 0
    lsr_reads = 0
    pending: tuple[int, int] | None = None   # (target, executes_after_delay_slot)

    def word_at(a: int) -> int:
        o = a - load
        if not (0 <= o + 3 < len(image)):
            raise SimError(f"instruction fetch outside the image at {a:#010x}")
        return struct.unpack_from(">I", image, o)[0]

    def load_byte(a: int) -> int:
        nonlocal lsr_reads
        if a == SIM_LSR:
            lsr_reads += 1
            return lsr_value
        o = a - load
        if not (0 <= o < len(image)):
            raise SimError(f"byte load outside the image and the UART at {a:#010x}")
        return image[o]

    def store_byte(a: int, v: int) -> None:
        if a == SIM_THR:
            out.append(v & 0xFF)
            return
        raise SimError(f"byte store to {a:#010x}, which is not the UART")

    while steps < max_steps:
        steps += 1
        w = word_at(pc)
        op = w >> 26
        rs, rt = (w >> 21) & 31, (w >> 16) & 31
        imm = w & 0xFFFF
        simm = imm - 0x10000 if imm & 0x8000 else imm
        taken: int | None = None

        if w == 0:
            pass
        elif op == 0x00 and (w & 0x3F) == 0x21:                      # addu
            rd = (w >> 11) & 31
            reg[rd] = (reg[rs] + reg[rt]) & 0xFFFFFFFF
        elif op == 0x0F:                                             # lui
            reg[rt] = (imm << 16) & 0xFFFFFFFF
        elif op == 0x0D:                                             # ori
            reg[rt] = reg[rs] | imm
        elif op == 0x0C:                                             # andi
            reg[rt] = reg[rs] & imm
        elif op == 0x09:                                             # addiu
            reg[rt] = (reg[rs] + simm) & 0xFFFFFFFF
        elif op == 0x24:                                             # lbu
            reg[rt] = load_byte((reg[rs] + simm) & 0xFFFFFFFF)
        elif op == 0x28:                                             # sb
            store_byte((reg[rs] + simm) & 0xFFFFFFFF, reg[rt])
        elif op == 0x04:                                             # beq
            if reg[rs] == reg[rt]:
                taken = pc + 4 + simm * 4
        elif op == 0x05:                                             # bne
            if reg[rs] != reg[rt]:
                taken = pc + 4 + simm * 4
        elif op == 0x01 and rt == 0x11:                              # bgezal (bal)
            reg[RA] = pc + 8
            if reg[rs] >= 0:
                taken = pc + 4 + simm * 4
        else:
            raise SimError(f"unimplemented instruction {w:#010x} at {pc:#010x}")

        reg[ZERO] = 0
        if pending is not None:
            target = pending[0]
            pending = None
            pc = target
        elif taken is not None:
            pending = (taken, 0)
            pc += 4
        else:
            pc += 4

        if want_bytes and len(out) >= want_bytes:
            return SimResult(bytes(out), lsr_reads, steps)
    raise SimError(f"ran {max_steps} instructions without producing {want_bytes} bytes")


# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Build the UART-speaking RAM payload P9-12 needs")
    p.add_argument("--nonce", required=True,
                   help="hex, 4-16 characters. It must not occur in any --check-absent "
                        "file, or seeing it on the console proves nothing")
    p.add_argument("--marker", default="N150RT RAMBOOT P9-12",
                   help="the fixed part of the banner (default: %(default)s)")
    p.add_argument("--load", type=lambda s: int(s, 16), default=0x80500000,
                   help="the address J will be given, hex. Recorded, and the payload is "
                        "simulated at it -- but the bytes do not depend on it, and this "
                        "tool proves that rather than claiming it (default: 80500000)")
    p.add_argument("--delay-hi", type=lambda s: int(s, 0), default=DEFAULT_DELAY_HI,
                   help="upper half of the inter-banner spin count (default: 0x800)")
    p.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES,
                   help=f"refuse a payload larger than this (default {DEFAULT_MAX_BYTES})")
    p.add_argument("--check-absent", action="append", default=[], metavar="FILE",
                   help="refuse if the marker or the nonce occurs in FILE. Repeatable")
    p.add_argument("-o", "--output", help="write the image here")
    p.add_argument("--force", action="store_true", help="overwrite an existing output")
    p.add_argument("--report", help="write a JSON transcript here")
    p.add_argument("--print-disassembly", action="store_true")
    args = p.parse_args(argv)

    if not re.fullmatch(r"[0-9a-fA-F]{4,16}", args.nonce):
        fail(f"--nonce {args.nonce!r}: 4 to 16 hex characters, so that it is short enough "
             "to read off a console and long enough not to occur by accident")
    if args.load % 4:
        fail(f"--load {args.load:#x} is not word aligned; J would jump into the middle of "
             "an instruction")
    if not KSEG[0] <= args.load < KSEG[1]:
        fail(f"--load {args.load:#x} is outside KSEG0/KSEG1. A bare physical address is "
             "unmapped in kernel mode and the loader's J prints nothing before jumping")

    banner = f"\r\n*** {args.marker} {args.nonce} ***\r\n"
    message = banner.encode("ascii", errors="strict")
    if b"\x00" in message:
        fail("the banner contains a NUL, which is where the payload's loop stops")
    if any(b > 0x7F for b in message):
        fail("the banner contains a byte above 0x7F")

    try:
        image, listing = build(message, args.delay_hi)
    except (AssertionError, ValueError) as e:
        fail(str(e))
        return 1
    if len(image) > args.max_bytes:
        fail(f"the payload is {len(image)} bytes and --max-bytes is {args.max_bytes}")

    # -- the checks that make this evidence ---------------------------------
    def run(img: bytes, at: int, why: str, **kw) -> SimResult:
        try:
            return simulate(img, at, **kw)
        except SimError as e:
            fail(f"the payload does not run ({why}): {e}")
            raise SystemExit(1) from e

    first = run(image, args.load, f"at {args.load:#010x}", want_bytes=len(message))
    if first.out != message:
        fail(f"the payload emits {first.out!r}, not the banner {message!r}. "
             "The encoder and the intent have parted company")
    # With a UART that reports itself empty, the payload should look at the line
    # status once per character.  Anything more means it is polling for a bit
    # that is not the one the loader polls, which on hardware costs the whole
    # bounded spin per byte and shows up nowhere in the output.
    if first.lsr_reads != len(message):
        fail(f"the payload read the line status {first.lsr_reads} times to emit "
             f"{len(message)} bytes from a UART that was ready every time. It is testing "
             f"the wrong bits: the loader's own putchar tests {LSR_TX_EMPTY:#04x}")

    elsewhere = run(image, 0x81000000, "at 0x81000000", want_bytes=len(message))
    if elsewhere.out != first.out:
        fail("the payload emits different bytes at a different load address, so it is not "
             "position independent and --load is load bearing after all")

    # A second banner, to show the outer loop closes rather than falling off the
    # end.  Simulating the shipped image through its own inter-banner spin would
    # be ~400 million interpreted instructions, so the repeat is shown on an
    # image built with the smallest possible delay -- and the claim "identical
    # except for that one immediate" is checked here rather than asserted.
    short, _ = build(message, 1)
    diff = [i for i in range(0, len(image), 4) if image[i:i + 4] != short[i:i + 4]]
    if diff != [0x50]:
        fail(f"the short-delay build differs from the shipped one at {diff}, not only at "
             "the delay constant (0x50). The repeat check would be testing another program")
    twice = run(short, args.load, "the second banner", want_bytes=len(message) * 2)
    if twice.out != message * 2:
        fail(f"the payload does not repeat: the second banner came out as "
             f"{twice.out[len(message):]!r}")

    # The console is the thing being asked a question, so the case where it never
    # says it is ready has to be exercised too -- that is what the bounded spin
    # copied from the loader is for.
    stuck = run(image, args.load, "with a UART that is never empty",
                lsr_value=0x00, want_bytes=len(message))
    if stuck.out != message:
        fail("with the UART never reporting itself empty the payload emits "
             f"{stuck.out!r}. The bounded spin is not doing what the loader's own does")

    print(f"  ok    {len(image)} bytes, {len(image) // 4} words of code plus the banner")
    print(f"  ok    simulated at {args.load:#010x} and at 0x81000000: identical output")
    print(f"  ok    it emits {message!r} and repeats")
    print(f"  ok    one line-status read per character on a ready UART "
          f"({first.lsr_reads} for {len(message)} bytes)")
    print("  ok    it still emits with the UART never reporting itself empty "
          f"(bounded at {TX_SPIN}, as the loader's own putchar is)")

    for path in args.check_absent:
        try:
            with open(path, "rb") as fh:
                blob = fh.read()
        except OSError as e:
            fail(f"--check-absent {path}: {e}")
        for needle, what in ((args.nonce.encode(), "nonce"),
                             (args.marker.encode(), "marker")):
            if needle in blob:
                fail(f"the {what} {needle!r} already occurs in {os.path.basename(path)}. "
                     "Seeing it on the console would then prove nothing about what ran")
        print(f"  ok    neither the marker nor the nonce occurs in {os.path.basename(path)} "
              f"({len(blob)} bytes)")
    if not args.check_absent:
        print("  note  no --check-absent given, so nothing has established that this "
              "banner is absent from flash. A banner that is already on the part is not "
              "evidence that anything executed")

    dis = [f"{args.load + off:#010x}  {text}" for off, text in listing]
    if args.print_disassembly:
        print()
        for line in dis:
            print("        " + line)
        print()

    digest = hashlib.sha256(image).hexdigest()
    print(f"  ok    sha256 {digest}")

    if args.output:
        if os.path.exists(args.output) and not args.force:
            fail(f"{args.output} exists. Refusing to overwrite; --force if that is what "
                 "you mean")
        with open(args.output, "wb") as fh:
            fh.write(image)
        print(f"  ok    -> {args.output}")
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump({"producer": "mkramboot", "nonce": args.nonce,
                       "marker": args.marker, "banner": banner,
                       "load": f"{args.load:#010x}", "bytes": len(image),
                       "sha256": digest, "delay_hi": args.delay_hi,
                       "uart_thr": f"{UART_BASE | UART_THR:#010x}",
                       "uart_lsr": f"{UART_BASE | UART_LSR:#010x}",
                       "checked_absent_from": args.check_absent,
                       "disassembly": dis,
                       "simulated_output": message.decode("ascii")}, fh, indent=2)
        print(f"  ok    transcript -> {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
