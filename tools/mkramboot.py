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


def sw(rt: int, base: int, off: int) -> int:
    return _i(0x2B, base, rt, off)


def xori(rt: int, rs: int, imm: int) -> int:
    return _i(0x0E, rs, rt, imm)


def mfc0(rt: int, rd: int) -> int:
    return 0x40000000 | (0 << 21) | (rt << 16) | (rd << 11)


def mtc0(rt: int, rd: int) -> int:
    return 0x40000000 | (4 << 21) | (rt << 16) | (rd << 11)


def jr(rs: int) -> int:
    return (rs << 21) | 0x08


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
    that the branch arithmetic is checked against them rather than counted.

    The two ``nop``s at 0x20 and 0x34 are **load delay slots**, not padding, and
    version 1 of this file did not have them.  See ``simulate`` below.
    """
    body_len = 0x70
    msg = message + b"\x00"
    while len(msg) % 4:
        msg += b"\x00"

    L_OUTER, L_NEXT, L_WAIT, L_EMIT, L_DELAY, L_DLOOP, L_MSG = (
        0x18, 0x1C, 0x30, 0x4C, 0x58, 0x5C, body_len)

    prog: list[tuple[int, int, str]] = [
        (0x00, bal(branch_off(0x00, 0x08)), "bal     0x08"),
        (0x04, NOP, "nop"),
        (0x08, addiu(S0, RA, L_MSG - 0x08), f"addiu   s0,ra,{L_MSG - 0x08:#x}"),
        (0x0C, lui(T0, UART_BASE >> 16), f"lui     t0,{UART_BASE >> 16:#x}"),
        (0x10, ori(T1, T0, UART_LSR), f"ori     t1,t0,{UART_LSR:#x}"),
        (0x14, ori(T0, T0, UART_THR), f"ori     t0,t0,{UART_THR:#x}"),
        (L_OUTER, addu(S1, S0, ZERO), "addu    s1,s0,zero"),
        (L_NEXT, lbu(A0, S1, 0), "lbu     a0,0(s1)"),
        (0x20, NOP, "nop                     # load delay slot"),
        (0x24, beq(A0, ZERO, branch_off(0x24, L_DELAY)), "beq     a0,zero,delay"),
        (0x28, addiu(S1, S1, 1), "addiu   s1,s1,1"),
        (0x2C, addiu(T3, ZERO, TX_SPIN), f"addiu   t3,zero,{TX_SPIN}"),
        (L_WAIT, lbu(T2, T1, 0), "lbu     t2,0(t1)"),
        (0x34, NOP, "nop                     # load delay slot"),
        (0x38, andi(T2, T2, LSR_TX_EMPTY), f"andi    t2,t2,{LSR_TX_EMPTY:#x}"),
        (0x3C, bne(T2, ZERO, branch_off(0x3C, L_EMIT)), "bne     t2,zero,emit"),
        (0x40, addiu(T3, T3, -1), "addiu   t3,t3,-1"),
        (0x44, bne(T3, ZERO, branch_off(0x44, L_WAIT)), "bne     t3,zero,wait"),
        (0x48, NOP, "nop"),
        (L_EMIT, sb(A0, T0, 0), "sb      a0,0(t0)"),
        (0x50, beq(ZERO, ZERO, branch_off(0x50, L_NEXT)), "b       next"),
        (0x54, NOP, "nop"),
        (L_DELAY, lui(T4, delay_hi), f"lui     t4,{delay_hi:#x}"),
        (L_DLOOP, addiu(T4, T4, -1), "addiu   t4,t4,-1"),
        (0x60, bne(T4, ZERO, branch_off(0x60, L_DLOOP)), "bne     t4,zero,dloop"),
        (0x64, NOP, "nop"),
        (0x68, beq(ZERO, ZERO, branch_off(0x68, L_OUTER)), "b       outer"),
        (0x6C, NOP, "nop"),
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
# the second payload: put the interrupt state back, then return to the prompt
#
# `J` does four things before it jumps (0x8040925C): it writes 0 to GIMR0, it
# clears IE in CP0 Status, it clears bit 0 of PCRP0-PCRP4, and it replaces the
# running program.  On 2026-08-22 the bench restored the five PCRP bits after a
# `J` and TFTP did not come back, which leaves three candidates and excludes
# none.  The loader has no command that writes CP0 Status -- `MTC0SR` is
# commented out of the vendor's table and absent from the seventeen this build
# prints -- so separating them needs a payload, and `P9-16` had just shown that
# a payload ending in `jr ra` returns to the prompt.
#
# Two variants, differing in exactly five words at the same five offsets, so the
# operator retypes one `EW` line and nothing else:
#
#   --irq-restore <GIMR0>              GIMR0 := <value>, then set IE, then jr ra
#   --irq-restore <GIMR0> --no-set-ie  GIMR0 := <value>, then jr ra
#
# The IE half is copied instruction for instruction out of the loader's own
# `sti` at 0x80408484-0x80408494 -- the one it executes at boot, one instruction
# after printing `---Ethernet init Okay!`, before it enters the command loop.
# Reusing its bytes rather than writing an equivalent sequence means the payload
# cannot restore a *different* interrupt state from the one the prompt normally
# runs in, and the `DW` read-back of the image is a diff against a known five
# words.
GIMR0 = 0xB8003000
STATUS = 12
IRQ_BODY = 0x50
# The loader's own line discipline, both measured: GetLine takes at most 128
# characters (0x8040919C `li a1,128`) and the tokeniser has twenty argv slots
# (0x8040728C `li a1,20`), so an `EW` line carries at most eighteen values.
CONSOLE_LINE_MAX = 128
CONSOLE_MAX_TOKENS = 20


def build_irq_restore(gimr0: int, set_ie: bool) -> tuple[bytes, list[tuple[int, str]]]:
    """Return (image, listing).  Eighteen words, no loads, no branches.

    No `bal`, and that is deliberate.  The banner payload needs its own address
    to find its message; this one has no data, so the constant goes in a
    `lui`/`ori` pair and the image is position independent without touching
    `ra` -- which it must not, because `ra` is how it gets back into the `J`
    handler at 0x80409368.
    """
    hi, lo = (gimr0 >> 16) & 0xFFFF, gimr0 & 0xFFFF
    # The five CP0 words sit at 0x28-0x38 on purpose: with ten words to an `EW`
    # line that puts the whole `sti` on the SECOND line, so the two variants
    # differ in one typed line and in nothing else. An experiment whose variable
    # is spread across two commands is two experiments.
    cp0 = [
        (0x28, mfc0(AT, STATUS), "mfc0    $1,$12          # 0x80408484, verbatim"),
        (0x2C, NOP, "nop                     # 0x80408488"),
        (0x30, ori(AT, AT, 0x1F), "ori     $1,$1,0x1f      # 0x8040848C"),
        (0x34, xori(AT, AT, 0x1E), "xori    $1,$1,0x1e      # 0x80408490 -> IE=1"),
        (0x38, mtc0(AT, STATUS), "mtc0    $1,$12          # 0x80408494"),
    ] if set_ie else [
        (off, NOP, "nop                     # --no-set-ie: IE is left cleared")
        for off in (0x28, 0x2C, 0x30, 0x34, 0x38)
    ]

    prog: list[tuple[int, int, str]] = [
        (0x00, lui(T1, hi), f"lui     t1,{hi:#06x}"),
        (0x04, ori(T1, T1, lo), f"ori     t1,t1,{lo:#06x}     # GIMR0 value: {gimr0:#010x}"),
        (0x08, lui(T2, GIMR0 >> 16), f"lui     t2,{GIMR0 >> 16:#06x}"),
        (0x0C, sw(T1, T2, GIMR0 & 0xFFFF), f"sw      t1,{GIMR0 & 0xFFFF:#x}(t2)      # 0xB8003000"),
        (0x10, NOP, "nop"),
        (0x14, NOP, "nop"),
        (0x18, NOP, "nop"),
        (0x1C, NOP, "nop"),
        (0x20, NOP, "nop"),
        (0x24, NOP, "nop"),
        *cp0,
        (0x3C, NOP, "nop                     # the loader pads its own mtc0 with three"),
        (0x40, NOP, "nop"),
        (0x44, NOP, "nop"),
        (0x48, jr(RA), "jr      ra              # back into the J handler at 0x80409368"),
        (0x4C, NOP, "nop"),
    ]

    words = bytearray()
    listing: list[tuple[int, str]] = []
    for want_off, word, text in prog:
        if want_off != len(words):
            raise AssertionError(
                f"layout drift: {text} is at {len(words):#x}, the label says {want_off:#x}")
        words += struct.pack(">I", word)
        listing.append((want_off, f"{word:08x}  {text}"))
    if len(words) != IRQ_BODY:
        raise AssertionError(f"body is {len(words):#x}, the labels assume {IRQ_BODY:#x}")
    return bytes(words), listing


def ew_lines(load: int, image: bytes, per_line: int = 10) -> list[str]:
    """The `EW` lines that put this image in RAM, split to fit the line buffer.

    `EW` is on `console-dump.py`'s FORBIDDEN list, so these are typed by hand,
    and the split is not cosmetic: a line longer than 128 characters is
    truncated by `GetLine` with no error, and a line with more than twenty
    tokens loses the tail to the tokeniser's slot count.  Both bounds are the
    loader's, both are measured, and a payload silently half-written is a `J`
    into whatever was there before.
    """
    out = []
    words = [struct.unpack_from(">I", image, o)[0] for o in range(0, len(image), 4)]
    for i in range(0, len(words), per_line):
        chunk = words[i:i + per_line]
        line = f"EW {load + i * 4:08X} " + " ".join(f"{w:08X}" for w in chunk)
        if len(line) > CONSOLE_LINE_MAX:
            raise ValueError(
                f"`{line[:24]}...` is {len(line)} characters and GetLine takes "
                f"{CONSOLE_LINE_MAX}; the tail would be silently dropped")
        if len(line.split()) > CONSOLE_MAX_TOKENS:
            raise ValueError(
                f"that line has {len(line.split())} tokens and the tokeniser has "
                f"{CONSOLE_MAX_TOKENS} slots; the tail would be silently dropped")
        out.append(line)
    return out


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

    def __init__(self, out: bytes, lsr_reads: int, steps: int,
                 mmio: dict[int, int] | None = None,
                 status: int | None = None, returned: bool = False) -> None:
        self.out, self.lsr_reads, self.steps = out, lsr_reads, steps
        # For the interrupt-restoring payload the observable is not the UART:
        # it is which register got which word, what CP0 Status ended up as, and
        # whether `ra` was still intact when the payload returned through it.
        self.mmio = mmio or {}
        self.status = status
        self.returned = returned


def sources(w: int) -> set[int]:
    """Which registers this instruction reads.  Only the forms the encoder emits;
    anything else is a crash in the simulator rather than a guess."""
    op = w >> 26
    rs, rt = (w >> 21) & 31, (w >> 16) & 31
    if w == 0:
        return set()
    if op == 0x00 and (w & 0x3F) == 0x21:          # addu
        return {rs, rt}
    if op == 0x0F:                                  # lui
        return set()
    if op in (0x09, 0x0C, 0x0D):                    # addiu, andi, ori
        return {rs}
    if op == 0x24:                                  # lbu
        return {rs}
    if op == 0x28:                                  # sb
        return {rs, rt}
    if op in (0x04, 0x05):                          # beq, bne
        return {rs, rt}
    if op == 0x01:                                  # bgezal
        return {rs}
    if op == 0x0E:                                  # xori
        return {rs}
    if op == 0x2B:                                  # sw
        return {rs, rt}
    if op == 0x10:                                  # mfc0 / mtc0
        return {rt} if rs == 4 else set()
    if op == 0x00 and (w & 0x3F) == 0x08:           # jr
        return {rs}
    raise SimError(f"sources(): unimplemented instruction {w:#010x}")


def simulate(image: bytes, load: int, *, lsr_value: int = SIM_LSR_IDLE,
             max_steps: int = 4_000_000, want_bytes: int = 0,
             status_in: int | None = None, ra: int | None = None,
             word_stores_allowed: frozenset[int] = frozenset()) -> SimResult:
    reg = [0] * 32
    out = bytearray()
    pc = load
    steps = 0
    lsr_reads = 0
    mmio: dict[int, int] = {}
    status = status_in
    if ra is not None:
        reg[RA] = ra
    pending: tuple[int, int] | None = None   # (target, executes_after_delay_slot)
    # The MIPS-I load delay slot, which this core exposes architecturally.  A
    # load's result is not readable by the instruction that follows it.
    load_pending: tuple[int, int] | None = None

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

        # The hazard, refused rather than modelled.  A stale read here is not a
        # technique anyone would choose, so the useful behaviour is to stop and
        # name it -- see the note on this in `simulate`'s section header.
        to_apply, load_pending = load_pending, None
        if to_apply is not None and to_apply[0] in sources(w):
            raise SimError(
                f"the instruction at {pc:#010x} ({w:#010x}) reads r{to_apply[0]} in the "
                f"load delay slot. On this core it sees the PREVIOUS value: 1,474 loads "
                f"in the loader's own second stage and not one of them is followed by an "
                f"instruction reading what it loaded. Put a nop there")
        new_load: tuple[int, int] | None = None

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
            new_load = (rt, load_byte((reg[rs] + simm) & 0xFFFFFFFF))
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
        elif op == 0x0E:                                             # xori
            reg[rt] = reg[rs] ^ imm
        elif op == 0x2B:                                             # sw
            addr = (reg[rs] + simm) & 0xFFFFFFFF
            if addr not in word_stores_allowed:
                raise SimError(
                    f"word store to {addr:#010x}, which this payload is not "
                    f"allowed to touch (allowed: "
                    f"{', '.join(f'{a:#010x}' for a in sorted(word_stores_allowed)) or 'nothing'})")
            mmio[addr] = reg[rt]
        elif op == 0x10 and rs == 0:                                 # mfc0
            if ((w >> 11) & 31) != STATUS or status is None:
                raise SimError(f"mfc0 from an unmodelled CP0 register at {pc:#010x}")
            new_load = (rt, status)          # CP0 reads take the load slot too
        elif op == 0x10 and rs == 4:                                 # mtc0
            if ((w >> 11) & 31) != STATUS:
                raise SimError(f"mtc0 to an unmodelled CP0 register at {pc:#010x}")
            status = reg[rt]
        elif op == 0x00 and (w & 0x3F) == 0x08:                      # jr
            if pending is not None:
                raise SimError(f"jr in a delay slot at {pc:#010x}")
            pending = (reg[rs], 0)
            if reg[rs] == (ra if ra is not None else 0):
                # The payload is returning through `ra` -- run the delay slot
                # and stop.  Anything after that belongs to the loader.
                w2 = word_at(pc + 4)
                if w2 != 0:
                    raise SimError(
                        f"the delay slot of `jr ra` holds {w2:#010x}, not a nop. "
                        "It executes before the return and nothing here has "
                        "modelled what it would do")
                return SimResult(bytes(out), lsr_reads, steps, mmio, status, True)
            raise SimError(
                f"`jr` at {pc:#010x} jumps to {reg[rs]:#010x}, which is not the "
                "return address the J handler set")
        else:
            raise SimError(f"unimplemented instruction {w:#010x} at {pc:#010x}")

        # The previous instruction's load lands now, after this one's own write.
        if to_apply is not None:
            reg[to_apply[0]] = to_apply[1]
        load_pending = new_load
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
# `ra` when the payload starts, read off the loader: `J` reaches its target
# through `jalr s0` at 0x80409360, so the return address is the next
# instruction, where the handler restores ra and s0 and returns to the
# dispatcher.  Confirmed on the device 2026-08-21 (`P9-16`).
J_RETURN_ADDRESS = 0x80409368
# A stand-in Status with IE clear and bits 1..4 set, so the simulation shows
# both halves of the loader's `sti`: bit 0 raised, bits 1..4 cleared, the rest
# untouched.  Not a measurement -- no loader command reads CP0 Status, which is
# the whole reason this payload exists.
SIM_STATUS_AFTER_J = 0x1000FF1E
ETH_IRQ_BIT = 15


def _main_irq_restore(args, p) -> int:
    try:
        gimr0 = int(args.irq_restore, 16)
    except ValueError:
        fail(f"--irq-restore {args.irq_restore!r} is not hex")
        return 1
    if not 0 <= gimr0 <= 0xFFFFFFFF:
        fail("--irq-restore takes a 32-bit value")
    if gimr0 == 0:
        fail("--irq-restore 0 would write the value `J` already wrote. Read "
             "GIMR0 with `DW B8003000 1` at the prompt BEFORE the jump; if it "
             "really is zero then interrupts were already masked and the "
             "experiment this payload is for does not apply")
    if not (gimr0 >> ETH_IRQ_BIT) & 1 and not args.allow_no_eth_bit:
        fail(f"--irq-restore {gimr0:#010x} has bit {ETH_IRQ_BIT} clear. That is "
             f"the eth0 interrupt this loader installs (request_IRQ at "
             f"0x80402A44, name string `eth0`), so restoring this value leaves "
             f"the receive path masked and the measurement cannot come out "
             f"positive for any reason worth reading. Pass --allow-no-eth-bit "
             f"only if the device really did read this back")
    if args.load % 4:
        fail(f"--load {args.load:#x} is not word aligned")
    if not KSEG[0] <= args.load < KSEG[1]:
        fail(f"--load {args.load:#x} is outside KSEG0/KSEG1")

    set_ie = not args.no_set_ie
    try:
        image, listing = build_irq_restore(gimr0, set_ie)
    except (AssertionError, ValueError) as e:
        fail(str(e))
        return 1
    if len(image) > args.max_bytes:
        fail(f"the payload is {len(image)} bytes and --max-bytes is {args.max_bytes}")

    def run(at: int) -> SimResult:
        try:
            return simulate(image, at, status_in=SIM_STATUS_AFTER_J,
                            ra=J_RETURN_ADDRESS,
                            word_stores_allowed=frozenset({GIMR0}),
                            max_steps=1000)
        except SimError as e:
            fail(f"the payload does not run at {at:#010x}: {e}")
            raise SystemExit(1) from e

    first = run(args.load)
    second = run(args.load + 0x10000)
    if (first.mmio, first.status, first.returned) != \
       (second.mmio, second.status, second.returned):
        fail("the payload behaves differently at two load addresses, so it is "
             "not position independent and `J` to anything but --load is a "
             "different program")
    if first.mmio.get(GIMR0) != gimr0:
        fail(f"the payload writes {first.mmio.get(GIMR0)} to GIMR0, not {gimr0:#010x}")
    if not first.returned:
        fail("the payload does not return through `ra`, so `J` to it costs a "
             "power cycle and P9-16's result is being thrown away")
    want = ((SIM_STATUS_AFTER_J & ~0x1F) | 1) if set_ie else SIM_STATUS_AFTER_J
    if first.status != want:
        fail(f"CP0 Status ends as {first.status:#010x}, not {want:#010x}. "
             + ('The sti was copied wrong' if set_ie
                else 'Something touched Status and --no-set-ie says nothing should'))

    try:
        lines = ew_lines(args.load, image)
    except ValueError as e:
        fail(str(e))
        return 1

    digest = hashlib.sha256(image).hexdigest()
    if args.output:
        if os.path.exists(args.output) and not args.force:
            fail(f"{args.output} exists; --force to overwrite")
        with open(args.output, "wb") as fh:
            fh.write(image)

    print(f"  ok    irq-restore payload, {len(image)} bytes, "
          f"IE {'set' if set_ie else 'left cleared'}, GIMR0 := {gimr0:#010x}")
    print(f"        simulated at {args.load:#010x} and {args.load + 0x10000:#010x}: "
          f"identical, returns to {J_RETURN_ADDRESS:#010x}")
    print(f"        sha256 {digest}")
    print()
    for off, text in listing:
        print(f"  {args.load + off:08X}  {text}")
    print()
    print("  type these at <RealTek>, then verify before jumping:")
    for line in lines:
        print(f"    {line}          ({len(line)} chars, "
              f"{len(line.split())} tokens)")
    print(f"    DW {args.load:08X} {len(image) // 4}")
    print(f"    J {args.load:08X}")
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "producer": "mkramboot", "mode": "irq-restore", "schema": "1",
                "load": f"0x{args.load:08X}",
                "gimr0": f"0x{gimr0:08X}",
                "set_ie": set_ie,
                "bytes": len(image),
                "sha256": digest,
                "returns_to": f"0x{J_RETURN_ADDRESS:08X}",
                "simulated_status_in": f"0x{SIM_STATUS_AFTER_J:08X}",
                "simulated_status_out": f"0x{first.status:08X}",
                "simulated_gimr0_write": f"0x{first.mmio[GIMR0]:08X}",
                "ew_lines": lines,
                "listing": [f"{args.load + o:08X}  {t}" for o, t in listing],
            }, indent=2) + "\n")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Build the UART-speaking RAM payload P9-12 needs")
    p.add_argument("--nonce",
                   help="hex, 4-16 characters. It must not occur in any --check-absent "
                        "file, or seeing it on the console proves nothing. Required "
                        "for the banner payload; ignored by --irq-restore")
    p.add_argument("--irq-restore", metavar="GIMR0HEX",
                   help="build the OTHER payload instead: write this value to "
                        "GIMR0 (0xB8003000), set IE, and `jr ra` back to the "
                        "loader's prompt. The value is what `DW B8003000 1` "
                        "read at the prompt BEFORE the J, in hex")
    p.add_argument("--no-set-ie", action="store_true",
                   help="--irq-restore only: leave IE cleared, so the two "
                        "variants differ in exactly five words and the "
                        "experiment has one variable")
    p.add_argument("--allow-no-eth-bit", action="store_true",
                   help="--irq-restore only: accept a GIMR0 value with bit 15 "
                        "clear. Bit 15 is the eth0 line this loader installs at "
                        "0x80402A44, so a value without it restores an interrupt "
                        "state in which TFTP cannot answer -- which is not the "
                        "experiment, and is almost always a transcription error")
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

    if args.irq_restore is not None:
        return _main_irq_restore(args, p)
    if args.nonce is None:
        fail("--nonce is required for the banner payload (or use --irq-restore)")
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
    if diff != [0x58]:
        fail(f"the short-delay build differs from the shipped one at {diff}, not only at "
             "the delay constant (0x58). The repeat check would be testing another program")
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
