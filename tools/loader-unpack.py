#!/usr/bin/env python3
"""Recover the boot loader's compressed second stage out of a flash dump.

Why this exists
---------------
Every string the operator has ever seen from the `<RealTek>` prompt -- the `?`
help, `FLR`, `IPCONFIG`, `Flash Read Successed!` -- is **absent from the raw
4 MiB dump**. Grepping the image for `FLR` finds nothing, and that silence was
read here for three weeks as "the loader is small and terse".

It is not. `0x000000`-`0x0012F0` is stage 1 (DRAM training: `Booting...`,
`DTR Done.`, `DCR Done.`, `DDCR Done.`) and at `0x0012F0` there is an
LZMA-alone stream, 17,334 bytes in, 56,592 bytes out. The command interpreter,
the TFTP client, the SPI chip table and the whole help text live inside it.

Three questions this answers, none of which needs the device:

  P9-1  Can the boot loader pass a kernel command line?  Its command table and
        its entire string space are searchable once the stage is unpacked. A
        loader that can set `init=` has to have somewhere to put it.
  P9-3  What is the rescue path, exactly?  `AUTOBURN`, `IPCONFIG`, `LOADADDR`
        and the TFTP message set describe the whole flow, including which knob
        decides whether an upload is written to flash.
  §8.9  Which code path prints `Flash Write Successed!`.  The string exists;
        the interactive `FLW` does not print it. Both clusters are reported
        with addresses so the difference is pointable rather than asserted.

Failing
-------
A recovery script that cannot fail proves nothing, so this one refuses to
produce a report unless:

  * exactly one LZMA signature is found in the loader region (not "the first");
  * the stream's own declared output size matches what came out;
  * the unpacked stage contains `COMMAND MODE HELP` -- the positive control. A
    wrong offset that happens to decompress still fails this;
  * every command name the `?` help prints is found in the unpacked stage. This
    is what makes an *absence* mean something: the same scan that reports "no
    kernel command line anywhere" is demonstrated, in the same run, to find the
    seventeen strings already known to be there.

Usage
-----
    python3 tools/loader-unpack.py <flash-dump> [-o reports/bootloader-....json]
    python3 tools/loader-unpack.py <flash-dump> --extract /tmp/stage2.bin
    python3 tools/loader-unpack.py <flash-dump> --strings          # human read
"""

from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import re
import struct
import sys
from pathlib import Path
from typing import Any

PRODUCER = "loader-unpack"
SCHEMA = "1"

# H601, the hardware MIB block, begins at 0x006000. Everything before it is the
# loader. Searching further would find the compressed configuration regions and
# the kernel, and "exactly one match" would stop being a meaningful check.
LOADER_REGION_END = 0x006000

# LZMA-alone: props(1) dict_size(4, LE) uncompressed_size(8, LE). 0x5D is
# lc=3,lp=0,pb=2 -- what every LZMA SDK encoder of that era emitted by default.
LZMA_PROPS = 0x5D

# The seventeen names the `?` help prints on this unit, captured verbatim at the
# console on 2026-08-17 (RUNBOOK 8.7.7). They are the positive control: this
# tool's absence claims are only worth reading if the same scan finds these.
DOCUMENTED_COMMANDS = [
    "HELP", "DB", "DW", "EB", "EW", "CMP", "IPCONFIG", "AUTOBURN",
    "LOADADDR", "J", "FLR", "FLW", "MDIOR", "MDIOW", "PHYR", "PHYW", "PORT1",
]

# A loader able to hand Linux an `init=` has to hold the text somewhere.
CMDLINE_NEEDLES = [
    "cmdline", "bootargs", "bootcmd", "console=", "root=", "init=", "mem=",
    "rootfstype", "setenv", "printenv", "env ", "ethaddr", "bootdelay",
]

RESCUE_NEEDLES = ["TFTP", "tftp", "Upload", "Download", "AutoBurn", "AUTOBURN",
                  "burn", "Burn", "Load Addr", "LOADADDR", "IPCONFIG",
                  "Target IP", "Target Address"]

# open #17: does FLW erase the containing sector, and does it preserve the rest?
ERASE_NEEDLES = ["erase", "Erase", "ERASE", "sector", "Sector", "block",
                 "Block", "chip", "Chip"]

# --- the loader's own SPI flash table --------------------------------------
#
# `chipName: UNKNOWN` has been in this project's boot log since 2026-08-15 and
# nothing explained it. It is explainable with no device at all: the loader
# carries a table of fixed-size flash descriptors, each holding a three-byte
# JEDEC id and a pointer to the part's name, and the part fitted to this board
# has no row in it.
#
# What is measured and what is inferred, kept apart on purpose:
#   measured  the record stride, the offset of the name pointer, the id bytes,
#             the load base (recovered, and it has to explain EVERY pointer)
#   inferred  what four of the eight fields mean. That reading comes from their
#             values, not from any code, so it is reported as `inferred_*` and
#             the raw words are reported beside it.
CHIP_RECORD = 0x20          # measured: consecutive ids sit exactly 0x20 apart
CHIP_NAME_PTR = 0x18        # measured: the one field that resolves into strings
CHIP_MIN_ROWS = 16          # below this the walk has found something else
KSEG0 = (0x80000000, 0x90000000)


class LoaderError(Exception):
    """Raised for every refusal, so the guard suite can assert on the reason."""


def find_lzma(buf: bytes, region_end: int) -> int:
    """Offset of the single LZMA-alone stream in the loader region.

    "The first match" would be wrong for the same reason `head -1` is wrong on a
    grep whose result decides something: it turns "I found one" and "I found
    four and picked one" into the same output.
    """
    hits = []
    end = min(region_end, len(buf))
    for off in range(0, end - 13):
        if buf[off] != LZMA_PROPS:
            continue
        dict_size = struct.unpack_from("<I", buf, off + 1)[0]
        # Dictionary sizes are powers of two in this range; anything else is a
        # 0x5D byte in ordinary code.
        if dict_size < (1 << 12) or dict_size > (1 << 26) or (dict_size & (dict_size - 1)):
            continue
        out_size = struct.unpack_from("<Q", buf, off + 5)[0]
        if out_size == 0xFFFFFFFFFFFFFFFF:
            # Streams with an unknown size cannot be size-checked, so accepting
            # one would quietly remove this tool's main control.
            continue
        if not (1 << 10) <= out_size <= (1 << 22):
            continue
        hits.append(off)
    if not hits:
        raise LoaderError(
            f"no LZMA-alone stream found in 0x0-0x{end:06x}. Either this dump's "
            "loader is not packed the way this unit's is, or the region bound is "
            "wrong -- check that H601 still starts at 0x006000")
    if len(hits) > 1:
        raise LoaderError(
            "more than one LZMA-alone stream in the loader region "
            f"({', '.join(f'0x{h:06x}' for h in hits)}); refusing to guess which "
            "one is the second stage")
    return hits[0]


def unpack(buf: bytes, off: int) -> tuple[bytes, dict[str, Any]]:
    dict_size = struct.unpack_from("<I", buf, off + 1)[0]
    out_size = struct.unpack_from("<Q", buf, off + 5)[0]
    d = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    try:
        out = d.decompress(buf[off:])
    except lzma.LZMAError as exc:
        raise LoaderError(f"LZMA stream at 0x{off:06x} did not decompress: {exc}") from exc
    if len(out) != out_size:
        raise LoaderError(
            f"stream at 0x{off:06x} declares {out_size} bytes of output and "
            f"produced {len(out)}. A partial decompression is not evidence")
    # `unused_data` is what is left of the input after the stream ends, which is
    # how the compressed length is measured rather than assumed.
    comp_len = len(buf) - off - len(d.unused_data)
    return out, {
        "offset": f"0x{off:06x}",
        "lzma_props": f"0x{LZMA_PROPS:02x}",
        "dict_size": dict_size,
        "compressed_bytes": comp_len,
        "uncompressed_bytes": len(out),
        "declared_uncompressed_bytes": out_size,
        "ends_at": f"0x{off + comp_len:06x}",
    }


def strings(blob: bytes, minlen: int = 4) -> list[tuple[int, str]]:
    pat = rb"[\x20-\x7e]{%d,}" % minlen
    return [(m.start(), m.group().decode("ascii")) for m in re.finditer(pat, blob)]


def hits_for(table: list[tuple[int, str]], needles: list[str]) -> list[dict[str, str]]:
    out = []
    for off, s in table:
        for n in needles:
            if n in s:
                out.append({"offset": f"0x{off:05x}", "string": s})
                break
    return out


def cstrings(blob: bytes, minlen: int = 4) -> dict[int, str]:
    """offset -> the NUL-terminated string that *starts* there.

    Deliberately not `strings()` above. A pointer has to land on the start of a
    string, and a run scanner that reports the whole run cannot tell the start
    of one from the middle of one -- which is the difference between a table of
    26 part names and 26 coincidences.
    """
    out: dict[int, str] = {}
    for m in re.finditer(rb"[\x20-\x7e]{%d,}\x00" % minlen, blob):
        out[m.start()] = m.group()[:-1].decode("ascii")
    return out


def _run_at_stride(offsets: list[int], step: int) -> list[int]:
    """The longest arithmetic progression of `step` inside `offsets`."""
    seen, best = set(offsets), []
    for o in offsets:
        if o - step in seen:
            continue                      # not the start of a run
        run = [o]
        while run[-1] + step in seen:
            run.append(run[-1] + step)
        if len(run) > len(best):
            best = run
    return best


def _walk_cstring(blob: bytes, off: int, limit: int = 64) -> str:
    """Read a C string by walking bytes, so the regex scanner is not the only
    reader of the one field this whole table hangs on."""
    end = blob.find(b"\x00", off, off + limit)
    if end < 0:
        raise LoaderError(f"no NUL within {limit} bytes of 0x{off:05x}")
    return blob[off:end].decode("ascii", "replace")


def chip_table(stage2: bytes) -> dict[str, Any]:
    """Decode the loader's SPI flash descriptor table out of the unpacked stage.

    The load base is *recovered*, not assumed, and the recovery is a funnel that
    can end at zero or at more than one -- both of which are refusals. This is
    the same shape as `tools/libbase.py`: page alignment, then a structural
    filter, then exactly one survivor or nothing.
    """
    names = cstrings(stage2, 4)
    words = {off: struct.unpack_from(">I", stage2, off)[0]
             for off in range(0, len(stage2) - 3, 4)}
    ptr_words = {o: v for o, v in words.items() if KSEG0[0] <= v < KSEG0[1]}

    # Every (pointer, string) pair implies one load base. Keep the page-aligned
    # ones: a load base is a mapping and a mapping is page-granular.
    tally: dict[int, set[int]] = {}
    for o, v in ptr_words.items():
        for s in names:
            b = v - s
            if b <= 0 or b & 0xFFF:
                continue
            tally.setdefault(b, set()).add(o)

    survivors = []
    for b, offs in sorted(tally.items()):
        run = _run_at_stride(sorted(offs), CHIP_RECORD)
        if len(run) >= CHIP_MIN_ROWS:
            survivors.append((b, run))

    funnel = {
        "kseg0_words": len(ptr_words),
        "page_aligned_bases_proposed": len(tally),
        f"...whose pointers run at a 0x{CHIP_RECORD:x} stride, "
        f"{CHIP_MIN_ROWS}+ deep": len(survivors),
    }
    if not survivors:
        raise LoaderError(
            "no page-aligned load base puts a run of at least "
            f"{CHIP_MIN_ROWS} pointers on a 0x{CHIP_RECORD:x} stride. Either "
            "this loader has no chip table or its shape is not the one this "
            "tool measured on unit-2018")
    if len(survivors) > 1:
        raise LoaderError(
            f"{len(survivors)} load bases each explain a table: "
            + ", ".join(f"0x{b:08x}" for b, _ in survivors)
            + ". A recovery that cannot narrow to one has not recovered anything")

    base, run = survivors[0]
    rows, ids = [], []
    for ptr_off in run:
        rec = ptr_off - CHIP_NAME_PTR
        if rec < 0 or rec + CHIP_RECORD > len(stage2):
            raise LoaderError(f"record at 0x{rec:05x} falls outside the stage")
        f = struct.unpack_from(">8I", stage2, rec)
        name_at = f[6] - base
        # Two readers of the same bytes: the regex scan above, and a byte walk.
        walked = _walk_cstring(stage2, name_at)
        if names.get(name_at) != walked:
            raise LoaderError(
                f"record 0x{rec:05x}: the string scanner says "
                f"{names.get(name_at)!r} at 0x{name_at:05x} and a byte walk says "
                f"{walked!r}. One of the two readers is wrong")
        if f[0] >> 24:
            raise LoaderError(
                f"record 0x{rec:05x}: id word 0x{f[0]:08x} has a non-zero top "
                "byte, so it is not a three-byte JEDEC id and the stride is "
                "finding something else")
        ids.append(f[0])
        rows.append({
            "at": f"0x{rec:05x}",
            "jedec_id": f"{f[0]:06x}",
            "name": walked,
            "name_ptr": f"0x{f[6]:08x}",
            "words": [f"0x{w:08x}" for w in f],
            "inferred_capacity_code": f"0x{f[2]:02x}",
            "inferred_block_bytes": f[3],
            "inferred_smallest_erase_bytes": f[4],
            "inferred_page_bytes": f[5],
        })

    # The headline result here is an ABSENCE -- "this part has no row" -- and a
    # walk that stopped early would produce exactly that answer for a part that
    # does have one. So: every word anywhere in the stage that points into the
    # span of names this table uses must be one of the pointers already walked.
    # One that is not is a row the walk missed, and it is a refusal rather than
    # a footnote, because the query built on top of this reports absence.
    name_lo = min(f[6] for f in [struct.unpack_from(">8I", stage2, p - CHIP_NAME_PTR)
                                 for p in run])
    name_hi = max(f[6] for f in [struct.unpack_from(">8I", stage2, p - CHIP_NAME_PTR)
                                 for p in run])
    name_hi += len(_walk_cstring(stage2, name_hi - base)) + 1
    orphans = sorted(o for o, v in ptr_words.items()
                     if name_lo <= v < name_hi and o not in set(run))
    if orphans:
        raise LoaderError(
            f"{len(orphans)} word(s) point into this table's own name block but "
            "are not on the walked stride: "
            + ", ".join(f"0x{o:05x}" for o in orphans[:8])
            + ". Each is a row the walk did not reach, so an absence reported "
              "from this table would not be an absence")

    dupes: dict[str, list[str]] = {}
    for row in rows:
        dupes.setdefault(row["jedec_id"], []).append(row["name"])
    duplicate_ids = {k: v for k, v in dupes.items() if len(v) > 1}

    return {
        "load_base": f"0x{base:08x}",
        "how_the_base_was_found": funnel,
        "record_stride": f"0x{CHIP_RECORD:02x}",
        "name_pointer_offset": f"0x{CHIP_NAME_PTR:02x}",
        "record_count": len(rows),
        "distinct_ids": len(set(ids)),
        "name_block": f"0x{name_lo - base:05x}-0x{name_hi - base:05x}",
        "pointers_into_the_name_block_outside_the_walk": 0,
        "duplicate_ids": duplicate_ids,
        "ids": sorted({f"{i:06x}" for i in ids}),
        "smallest_erase_values_seen": sorted({r["inferred_smallest_erase_bytes"]
                                              for r in rows}),
        "reading": (
            "The stride, the offsets and the ids are measured. The four "
            "`inferred_*` fields are read off values that repeat across rows -- "
            "no code was disassembled to get them, and the raw words are in "
            "`words` so a later reader can disagree."),
        "rows": rows,
    }


# --- the loader's own command table, and what its handlers actually read ----
#
# open #98: `FLW`'s table entry declares four arguments and `runsheet.md` A2.5
# sends three. That question was asked because the table had been *transcribed*
# into a note by hand, and a hand-transcribed table is a claim with no
# instrument behind it. This decodes it instead, and then answers the question
# the table cannot: how many arguments each handler *dereferences*, and whether
# it looks at the count it was passed before doing so.
#
# What is measured and what is inferred, kept apart on purpose:
#   measured  the record stride, which column holds the argument count (derived
#             from the shape of the four words, not assumed), the load base, and
#             for each handler the constant argv displacements it loads and the
#             address of the first instruction that consumes argc
#   inferred  nothing. Where the walk cannot see -- a handler that hands argv to
#             a callee, or one whose index is computed at run time -- it says so
#             rather than reporting a number
COMMAND_RECORD = 0x10       # measured: four words per entry
COMMAND_MIN_ROWS = 8        # below this a "run" is coincidence
COMMAND_MAX_ARGC = 15       # the count column is a small int; 15 is generous
COMMAND_NAME_RE = re.compile(r"^[A-Z0-9?]{1,10}$")

# o32: a call may leave anything in these, so an alias held in one does not
# survive a `jal`. s0-s8/gp/sp do survive, which is why every handler that uses
# argv after a call has first moved it into an s register.
CALLER_SAVED = frozenset({1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
                          24, 25, 31})
REG_A0, REG_A1, REG_RA = 4, 5, 31
MIPS_LOADS = {0x20, 0x21, 0x23, 0x24, 0x25}
MIPS_STORES = {0x28, 0x29, 0x2B}


def _mips(word: int) -> tuple[int, int, int, int, int, int]:
    """op, rs, rt, rd, funct, immediate."""
    return (word >> 26, (word >> 21) & 31, (word >> 16) & 31,
            (word >> 11) & 31, word & 63, word & 0xFFFF)


def _simm(imm: int) -> int:
    return imm - 0x10000 if imm & 0x8000 else imm


def _defines(word: int) -> int | None:
    op, _rs, rt, rd, fn, _ = _mips(word)
    if op == 0x00:
        if fn in (0x08, 0x18, 0x19, 0x1A, 0x1B):     # jr, mult, div
            return None
        return rd or None
    if op == 0x03:                                    # jal
        return REG_RA
    if op in (0x01, 0x02, 0x04, 0x05, 0x06, 0x07) or op in MIPS_STORES:
        return None
    return rt or None


def _uses(word: int) -> set[int]:
    op, rs, rt, _rd, fn, _ = _mips(word)
    if op == 0x00:
        if fn in (0x00, 0x02, 0x03):                  # sll/srl/sra: rt only
            return {rt}
        if fn in (0x08, 0x09):                        # jr/jalr
            return {rs}
        if fn in (0x10, 0x12):                        # mfhi/mflo
            return set()
        return {rs, rt}
    if op in (0x02, 0x03, 0x0F):                      # j/jal/lui
        return set()
    if op in (0x04, 0x05):
        return {rs, rt}
    if op in (0x01, 0x06, 0x07):
        return {rs}
    if op in MIPS_STORES:
        return {rs, rt}
    return {rs}


def _rename(word: int) -> tuple[int, int] | None:
    """`move rd, rs` in either of the two encodings gcc emits -> (rd, rs)."""
    op, rs, rt, rd, fn, _ = _mips(word)
    if op == 0x00 and fn in (0x21, 0x25):             # addu/or with zero
        if rt == 0:
            return rd, rs
        if rs == 0:
            return rd, rt
    return None


class PointerWalk:
    """Follow one tagged pointer through a routine's control flow graph.

    Two properties make this usable as evidence rather than as a hint:

    * **Merging at a join is an intersection.** A register counts as the
      pointer only if it holds it on *every* path that reaches the instruction.
      The other choice, union, calls a register the pointer on the strength of
      one path and then invents dereferences that never happen -- and version 1
      of this walk was a straight linear scan, which is a union of every path
      whether or not it is reachable. It read `IPCONFIG` as touching no argv at
      all, because the argc==0 branch overwrites `$a1` on a path the argc!=0
      branch never takes.
    * **A computed index is reported as computed**, never as a slot number.
      `EB` reaches `argv[1+n]` through `addu`, and a walk that only understands
      constant displacements has to either miss it or guess it.
    """

    def __init__(self, code_at, limit: int = 800) -> None:
        self.code_at = code_at
        self.limit = limit
        self.reads: list[tuple[int, int, bool]] = []   # pc, byte offset, computed
        self.secondary: list[int] = []                 # pc consuming the 2nd tag
        self.calls_holding: list[tuple[int, int | None]] = []
        self.returns: list[int] = []
        self.truncated = False

    def run(self, entry: int, pointer: dict[int, tuple[int, bool]],
            secondary: frozenset[int] = frozenset()) -> None:
        work = [(entry, dict(pointer), frozenset(secondary))]
        seen: set[tuple] = set()
        steps = 0
        while work:
            pc, ptr, sec = work.pop()
            while True:
                steps += 1
                if steps > self.limit:
                    self.truncated = True
                    break
                key = (pc, tuple(sorted(ptr.items())), sec)
                if key in seen:
                    break
                seen.add(key)

                word = self.code_at(pc)
                op, rs, rt, _rd, fn, _imm = _mips(word)
                self._observe(pc, word, ptr, sec)

                is_call = op == 0x03 or (op == 0x00 and fn == 0x09)
                is_ret = op == 0x00 and fn == 0x08 and rs == REG_RA
                target = self._branch(pc, word)
                jump = self._jump(pc, word) if op == 0x02 else None

                if is_call or is_ret or target is not None or jump is not None:
                    # the delay slot executes before control transfers
                    delay = self.code_at(pc + 4)
                    self._observe(pc + 4, delay, ptr, sec)
                    ptr, sec = self._apply(delay, ptr, sec)

                if is_call:
                    held = [r for r in (4, 5, 6, 7) if r in ptr or r in sec]
                    if held:
                        self.calls_holding.append(
                            (pc, self._jump(pc, word) if op == 0x03 else None))
                    ptr = {r: v for r, v in ptr.items() if r not in CALLER_SAVED}
                    sec = frozenset(sec - CALLER_SAVED)
                    pc += 8
                    continue
                if is_ret:
                    self.returns.append(pc)
                    break
                if jump is not None:
                    pc = jump
                    continue
                if target is not None:
                    work.append((target, dict(ptr), sec))
                    if op == 0x04 and rs == rt:        # beq r,r: never falls through
                        break
                    pc += 8
                    continue

                ptr, sec = self._apply(word, ptr, sec)
                pc += 4

    def _observe(self, pc, word, ptr, sec) -> None:
        op, rs, _, _, _, imm = _mips(word)
        if (op in MIPS_LOADS or op in MIPS_STORES) and rs in ptr:
            offset, computed = ptr[rs]
            self.reads.append((pc, offset + _simm(imm), computed))
        if sec and (_uses(word) & sec):
            move = _rename(word)
            if not (move and move[1] in sec):
                self.secondary.append(pc)

    @staticmethod
    def _branch(pc: int, word: int) -> int | None:
        op, _, rt, _, _, imm = _mips(word)
        if op in (0x04, 0x05, 0x06, 0x07) or (op == 0x01 and rt in (0, 1, 16, 17)):
            return pc + 4 + (_simm(imm) << 2)
        return None

    @staticmethod
    def _jump(pc: int, word: int) -> int:
        return ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)

    @staticmethod
    def _apply(word, ptr, sec):
        op, rs, rt, _rd, fn, imm = _mips(word)
        ptr, sec = dict(ptr), set(sec)
        move = _rename(word)
        derived = None
        if move and move[1] in ptr:
            derived = ptr[move[1]]
        elif op == 0x09 and rs in ptr:                 # addiu rt, base, imm
            derived = (ptr[rs][0] + _simm(imm), ptr[rs][1])
        elif op == 0x00 and fn in (0x20, 0x21, 0x25):  # add/addu/or rd, rs, rt
            if rs in ptr and rt not in ptr:
                derived = (ptr[rs][0], True)
            elif rt in ptr and rs not in ptr:
                derived = (ptr[rt][0], True)
        carries_secondary = bool(move and move[1] in sec)
        dest = _defines(word)
        if dest is not None:
            ptr.pop(dest, None)
            sec.discard(dest)
            if derived is not None:
                ptr[dest] = derived
            if carries_secondary:
                sec.add(dest)
        return ptr, frozenset(sec)


def _materialisations(stage2: bytes, base: int, addr: int,
                      window: int = 16) -> list[int]:
    """Every `lui`/`addiu` or `lui`/`ori` pair in the stage that builds `addr`.

    A code reference to a table is not a data word pointing at it -- MIPS builds
    the address out of two immediates -- so searching the image for the pointer
    value finds nothing and proves nothing. This is what makes "no instruction
    reads offset 4" a claim rather than a hope.
    """
    hi, lo = (addr >> 16) & 0xFFFF, addr & 0xFFFF
    if lo & 0x8000:
        hi = (hi + 1) & 0xFFFF
    words = [struct.unpack_from(">I", stage2, o)[0]
             for o in range(0, len(stage2) - 3, 4)]
    sites = []
    for i, word in enumerate(words):
        op, rs, _rt, _, _, imm = _mips(word)
        if op not in (0x09, 0x0D) or imm != lo or rs == 0:
            continue                                   # addiu / ori
        for back in range(1, window + 1):
            if i - back < 0:
                break
            prev = words[i - back]
            pop, _, prt, _, _, pimm = _mips(prev)
            if pop == 0x0F and prt == rs and pimm == hi:
                sites.append(base + i * 4)
                break
    return sites


def _walk_cstring_soft(stage2: bytes, off: int, limit: int = 200) -> str | None:
    """A C string is bytes-up-to-NUL, not a maximal run of printable bytes.

    `cstrings()` above cannot see this loader's first help line at all: it holds
    four tab characters, so the printable-run scanner breaks it in two and
    neither half ends at a NUL. Following a *pointer* needs a reader that walks
    from where the pointer lands, and the first version of this decoder refused
    the real table for exactly that reason.
    """
    if off < 0 or off >= len(stage2):
        return None
    end = stage2.find(b"\x00", off, off + limit)
    if end < 0 or end == off:
        return None
    body = stage2[off:end]
    if any(b not in b"\t\n\r" and not 0x20 <= b <= 0x7E for b in body):
        return None
    return body.decode("ascii")


def _is_prologue(word: int) -> bool:
    """`addiu sp, sp, -N` -- how every routine in this stage starts.

    This is what tells the handler column from the help column: both hold
    in-range pointers into the stage, and only one of them points at something
    that decodes as the first instruction of a function. Without it the two are
    interchangeable and the decoder would be free to name them either way round
    -- which is the mistake the hand transcription made.
    """
    op, rs, rt, _, _, imm = _mips(word)
    return op == 0x09 and rs == 29 and rt == 29 and _simm(imm) < 0


def command_table(stage2: bytes, base_hint: int | None = None) -> dict[str, Any]:
    """Decode the `<RealTek>` command table, and read each handler for argc use.

    The field order is *derived*: of the four words in a record, one column is a
    small integer in every row, two resolve to string starts and one into the
    code. A note in this repository asserted the order `{name, help, argc,
    handler}` from a hand transcription and it is `{name, argc, handler, help}`
    -- which is why this decoder refuses to be told the layout.
    """
    names = cstrings(stage2, 1)
    end = len(stage2)
    words = {off: struct.unpack_from(">I", stage2, off)[0]
             for off in range(0, end - 3, 4)}

    # Propose bases from any word that could be a name pointer at a plausible
    # record start, then keep the ones that explain a run.
    tally: dict[int, set[int]] = {}
    for off, value in words.items():
        if not KSEG0[0] <= value < KSEG0[1]:
            continue
        for s, text in names.items():
            b = value - s
            if b <= 0 or b & 0xFFF or not COMMAND_NAME_RE.match(text):
                continue
            tally.setdefault(b, set()).add(off)

    survivors = []
    for b, offs in sorted(tally.items()):
        run = _run_at_stride(sorted(offs), COMMAND_RECORD)
        if len(run) >= COMMAND_MIN_ROWS:
            survivors.append((b, run))
    funnel = {
        "page_aligned_bases_proposed": len(tally),
        f"...whose name pointers run at a 0x{COMMAND_RECORD:x} stride, "
        f"{COMMAND_MIN_ROWS}+ deep": len(survivors),
    }
    if not survivors:
        raise LoaderError(
            "no page-aligned load base puts a run of at least "
            f"{COMMAND_MIN_ROWS} command-name pointers on a "
            f"0x{COMMAND_RECORD:x} stride")
    if len(survivors) > 1:
        raise LoaderError(
            f"{len(survivors)} load bases each explain a command table: "
            + ", ".join(f"0x{b:08x}" for b, _ in survivors)
            + ". A recovery that cannot narrow to one has not recovered anything")
    base, run = survivors[0]
    if base_hint is not None and base != base_hint:
        raise LoaderError(
            f"the command table wants load base 0x{base:08x} and the chip table "
            f"wants 0x{base_hint:08x}. Two tables in one image cannot have two "
            "load bases; one of the two recoveries is wrong")

    # Where the record starts and which column is which, both derived. The run
    # was built from name pointers, so the name column may be any of the four
    # and the record may start up to three words before the first hit. Each of
    # the four alignments is tried and exactly one must split cleanly.
    def word_at(va: int) -> int | None:
        off = va - base
        if off < 0 or off + 4 > end or off % 4:
            return None
        return struct.unpack_from(">I", stage2, off)[0]

    def classify(start: int) -> tuple[dict[int, str], list[tuple]] | None:
        if start < 0 or start + len(run) * COMMAND_RECORD > end:
            return None
        raw = [struct.unpack_from(">4I", stage2, start + i * COMMAND_RECORD)
               for i in range(len(run))]
        roles: dict[int, str] = {}
        for col in range(4):
            column = [r[col] for r in raw]
            if all(v <= COMMAND_MAX_ARGC for v in column):
                roles[col] = "argc"
            elif all(COMMAND_NAME_RE.match(_walk_cstring_soft(stage2, v - base)
                                           or "") for v in column):
                roles[col] = "name"
            elif all(_walk_cstring_soft(stage2, v - base) for v in column):
                roles[col] = "help"
            elif all((w := word_at(v)) is not None and _is_prologue(w)
                     for v in column):
                roles[col] = "handler"
        if sorted(roles.values()) != ["argc", "handler", "help", "name"]:
            return None
        return roles, raw

    aligned = [(start, got) for k in range(4)
               if (start := run[0] - 4 * k) is not None
               and (got := classify(start)) is not None]
    if not aligned:
        raise LoaderError(
            "no alignment of the 0x10 record splits into one small integer, "
            "one command name, one help string and one pointer at a function "
            "prologue. The record shape is not the one this tool measured")
    if len(aligned) > 1:
        raise LoaderError(
            f"{len(aligned)} record alignments each split cleanly "
            + ", ".join(f"0x{base + s:08x}" for s, _ in aligned)
            + ". A field order that cannot be narrowed to one has not been "
              "measured")
    start, (roles, rows_raw) = aligned[0]
    name_col = next(c for c in roles if roles[c] == "name")
    help_col = next(c for c in roles if roles[c] == "help")
    argc_col = next(c for c in roles if roles[c] == "argc")
    func_col = next(c for c in roles if roles[c] == "handler")

    def resolves(value: int, b: int) -> str | None:
        return _walk_cstring_soft(stage2, value - b)

    def code_at(va: int) -> int:
        off = va - base
        if off < 0 or off + 4 > end:
            raise LoaderError(f"handler walk left the stage at 0x{va:08x}")
        return struct.unpack_from(">I", stage2, off)[0]

    rows = []
    for i, raw in enumerate(rows_raw):
        name = resolves(raw[name_col], base)
        walk = PointerWalk(code_at)
        walk.run(raw[func_col], {REG_A1: (0, False)}, frozenset({REG_A0}))
        exact = sorted({off // 4 for _, off, comp in walk.reads
                        if not comp and off >= 0 and off % 4 == 0})
        computed = sorted({off // 4 for _, off, comp in walk.reads
                           if comp and off >= 0 and off % 4 == 0})
        first_use = min((pc for pc, _, _ in walk.reads), default=None)
        first_test = min(walk.secondary, default=None)
        rows.append({
            "at": f"0x{base + start + i * COMMAND_RECORD:08x}",
            "name": name,
            "declared_argc": raw[argc_col],
            "handler": f"0x{raw[func_col]:08x}",
            "help": resolves(raw[help_col], base),
            "argv_slots_read": exact,
            "argv_slots_read_at_a_computed_index": computed,
            "argc_first_consumed_at":
                None if first_test is None else f"0x{first_test:08x}",
            "first_argv_dereference_at":
                None if first_use is None else f"0x{first_use:08x}",
            "argv_or_argc_live_at_calls": [f"0x{pc:08x}"
                                           for pc, _ in walk.calls_holding],
            "walk_truncated": walk.truncated,
        })

    missing = [c for c in DOCUMENTED_COMMANDS if c != "HELP"
               and c not in {r["name"] for r in rows}]
    if missing:
        raise LoaderError(
            "the decoded command table is missing commands the console's own "
            f"`?` prints: {', '.join(missing)}. A table that does not contain "
            "what the device already showed is not this loader's table")

    table_va = base + start
    sites = _materialisations(stage2, base, table_va)
    if not sites:
        raise LoaderError(
            f"nothing in the image builds the address 0x{table_va:08x}. A table "
            "no instruction can reach is not a table")
    readers = []
    for site in sites:
        _op, _rs, rt, _, _, _ = _mips(code_at(site))
        walk = PointerWalk(code_at)
        walk.run(site + 4, {rt: (0, False)})
        readers.append({
            "site": f"0x{site:08x}",
            "field_offsets_read": sorted({off % COMMAND_RECORD
                                          for _, off, _ in walk.reads}),
            "walk_truncated": walk.truncated,
        })
    read_offsets = sorted({o for r in readers for o in r["field_offsets_read"]})

    return {
        "load_base": f"0x{base:08x}",
        "how_the_base_was_found": funnel,
        "at": f"0x{table_va:08x}",
        "record_stride": f"0x{COMMAND_RECORD:x}",
        "record_count": len(rows),
        "field_offsets": {
            "name": name_col * 4, "argc": argc_col * 4,
            "handler": func_col * 4, "help": help_col * 4,
        },
        "readers_of_the_table": readers,
        "field_offsets_any_instruction_reads": read_offsets,
        "declared_argc_is_read_by_the_dispatcher": argc_col * 4 in read_offsets,
        "reading": (
            "`declared_argc` is what the table says; `argv_slots_read` is what "
            "the handler loads. Where the two differ the handler wins -- the "
            "count column is only enforced if some instruction reads it, and "
            "`field_offsets_any_instruction_reads` says whether any does."),
        "rows": rows,
    }


def command_table_or_reason(stage2: bytes,
                            base_hint: int | None = None) -> dict[str, Any]:
    try:
        return command_table(stage2, base_hint)
    except LoaderError as exc:
        return {"refused": str(exc)}


def chip_table_or_reason(stage2: bytes) -> dict[str, Any]:
    try:
        return chip_table(stage2)
    except LoaderError as exc:
        return {"refused": str(exc)}


def build(dump: Path, region_end: int) -> tuple[dict[str, Any], bytes]:
    buf = dump.read_bytes()
    off = find_lzma(buf, region_end)
    stage2, meta = unpack(buf, off)
    table = strings(stage2)
    joined = "\n".join(s for _, s in table)

    # --- the positive controls -------------------------------------------
    if "COMMAND MODE HELP" not in joined:
        raise LoaderError(
            "the unpacked stage does not contain 'COMMAND MODE HELP'. Something "
            "decompressed, but it is not the command interpreter this tool "
            "claims to be reading")
    found_cmds, missing_cmds = [], []
    for cmd in DOCUMENTED_COMMANDS:
        # Word-ish boundary: `J` and `DB` are short enough to match inside other
        # words, and a control that passes by accident is not a control.
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(cmd)}(?![A-Za-z0-9_])", joined):
            found_cmds.append(cmd)
        else:
            missing_cmds.append(cmd)
    if missing_cmds:
        raise LoaderError(
            "the string scan did not find these commands the console's own `?` "
            f"prints: {', '.join(missing_cmds)}. Until it finds all seventeen, "
            "this tool reporting that something is *absent* means nothing")

    chip_tbl = chip_table_or_reason(stage2)
    chip_base = (int(chip_tbl["load_base"], 16)
                 if "load_base" in chip_tbl else None)

    doc: dict[str, Any] = {
        "producer": PRODUCER,
        "schema": SCHEMA,
        "source": dump.name,
        "source_sha256": hashlib.sha256(buf).hexdigest(),
        "source_bytes": len(buf),
        "loader_region_end": f"0x{region_end:06x}",
        "stage1": {
            "range": f"0x000000-{meta['offset']}",
            "bytes": off,
            "strings": [{"offset": f"0x{o:05x}", "string": s}
                        for o, s in strings(buf[:off], 5)],
        },
        "stage2": {
            **meta,
            "sha256": hashlib.sha256(stage2).hexdigest(),
            "string_count": len(table),
        },
        "self_check": "OK",
        # Soft on purpose. A synthetic fixture carrying the seventeen command
        # names has no chip table, and a real loader from another vendor may
        # not either; neither is a reason to refuse the whole report. The
        # refusal text is kept so an absent table reads as an absent table
        # rather than as a field nobody filled in.
        "chip_table": chip_tbl,
        # Soft for the same reason, and it takes the chip table's load base as a
        # hint: two tables in one image cannot have two bases, so a disagreement
        # is a refusal rather than a field nobody compared.
        "command_table": command_table_or_reason(stage2, chip_base),
        "controls": {
            "help_banner_present": True,
            "documented_commands_found": found_cmds,
            "documented_commands_missing": missing_cmds,
        },
        "questions": {
            "P9-1_kernel_cmdline": {
                "asks": "can the boot loader hand Linux a command line",
                "needles": CMDLINE_NEEDLES,
                "hits": hits_for(table, CMDLINE_NEEDLES),
            },
            "P9-3_rescue_path": {
                "asks": "what the TFTP rescue flow is and which knob writes flash",
                "hits": hits_for(table, RESCUE_NEEDLES),
            },
            "open17_flash_write": {
                "asks": "which path prints 'Flash Write Successed!', and does the "
                        "loader name an erase unit",
                "hits": hits_for(table, [*ERASE_NEEDLES, "Flash Write",
                                         "Flash Read", "Write 0x", "SPI"]),
            },
        },
        "help_text": [{"offset": f"0x{o:05x}", "string": s} for o, s in table
                      if len(s) >= 12 and re.search(
                          r"(COMMAND MODE|Print this help|<Address>|<Len>|"
                          r"<Value1>|<TargetAddress>|<Load Address>|"
                          r"<dst_ROM_offset>|Jump to)", s)],
    }
    return doc, stage2


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dump", type=Path)
    ap.add_argument("-o", "--out", type=Path, help="write the JSON report here")
    ap.add_argument("--extract", type=Path, help="also write the unpacked stage 2")
    ap.add_argument("--strings", action="store_true",
                    help="print the unpacked stage's strings instead of JSON")
    ap.add_argument("--chip-table", action="store_true",
                    help="print the loader's SPI flash descriptor table instead "
                         "of JSON, and exit non-zero if it cannot be recovered")
    ap.add_argument("--commands", action="store_true",
                    help="print the loader's command table beside what each "
                         "handler actually dereferences, and exit non-zero if "
                         "it cannot be recovered")
    ap.add_argument("--has-id", metavar="HEX",
                    help="ask whether a three-byte JEDEC id, e.g. 1c7016, has a "
                         "row in that table. Exit 0 if it does, 1 if it does not")
    ap.add_argument("--region-end", type=lambda s: int(s, 0), default=LOADER_REGION_END)
    args = ap.parse_args(argv[1:])

    if not args.dump.is_file():
        print(f"no such dump: {args.dump}", file=sys.stderr)
        return 2
    try:
        doc, stage2 = build(args.dump, args.region_end)
    except LoaderError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1

    if args.extract:
        args.extract.write_bytes(stage2)
        print(f"stage 2 -> {args.extract} ({len(stage2):,} bytes)", file=sys.stderr)

    if args.strings:
        for off, s in strings(stage2):
            print(f"0x{off:05x}  {s}")
        return 0

    if args.commands:
        tbl = doc["command_table"]
        if "refused" in tbl:
            print(f"refused: {tbl['refused']}", file=sys.stderr)
            return 1
        off = tbl["field_offsets"]
        print(f"table at {tbl['at']}, {tbl['record_count']} records, "
              f"stride {tbl['record_stride']}, load base {tbl['load_base']}")
        print(f"fields (derived): name +{off['name']}  argc +{off['argc']}  "
              f"handler +{off['handler']}  help +{off['help']}")
        for r in tbl["readers_of_the_table"]:
            print(f"  read at {r['site']}: field offsets "
                  f"{r['field_offsets_read']}")
        print(f"  declared_argc (+{off['argc']}) is read by an instruction: "
              f"{tbl['declared_argc_is_read_by_the_dispatcher']}")
        print()
        print(f"  {'name':<9} {'says':>4} {'reads':<14} {'checks argc':<12} "
              f"handler")
        for r in tbl["rows"]:
            reads = ",".join(str(s) for s in r["argv_slots_read"]) or "-"
            if r["argv_slots_read_at_a_computed_index"]:
                reads += "+" + ",".join(
                    f"{s}+n" for s in r["argv_slots_read_at_a_computed_index"])
            checks = ("no" if r["argc_first_consumed_at"] is None
                      else r["argc_first_consumed_at"])
            flag = ""
            if r["argc_first_consumed_at"] is None and r["argv_slots_read"]:
                flag = "  <- dereferences argv unchecked"
            if not r["argv_slots_read"] and not \
                    r["argv_slots_read_at_a_computed_index"] and \
                    r["argv_or_argc_live_at_calls"]:
                flag = "  <- hands argv to a callee; not followed"
            print(f"  {r['name']:<9} {r['declared_argc']:>4} {reads:<14} "
                  f"{checks:<12} {r['handler']}{flag}")
        return 0

    if args.chip_table or args.has_id:
        tbl = doc["chip_table"]
        if "refused" in tbl:
            print(f"refused: {tbl['refused']}", file=sys.stderr)
            return 1
        if args.has_id:
            want = args.has_id.lower().removeprefix("0x")
            hit = [r for r in tbl["rows"] if r["jedec_id"] == want]
            if hit:
                print(f"{want}: {', '.join(sorted({r['name'] for r in hit}))} "
                      f"({len(hit)} row(s))")
                return 0
            print(f"{want}: no row. The loader cannot name this part, which is "
                  f"what `chipName: UNKNOWN` looks like from the inside.")
            return 1
        print(f"load base   {tbl['load_base']}   "
              f"(recovered: {tbl['how_the_base_was_found']})")
        print(f"{tbl['record_count']} records, {tbl['distinct_ids']} distinct ids, "
              f"stride {tbl['record_stride']}")
        for r in tbl["rows"]:
            print(f"  {r['at']}  {r['jedec_id']}  {r['name']:<12}"
                  f"  erase {r['inferred_smallest_erase_bytes']:>6}"
                  f"  page {r['inferred_page_bytes']}")
        for jid, who in sorted(tbl["duplicate_ids"].items()):
            print(f"  DUPLICATE id {jid}: {', '.join(who)}")
        return 0

    text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"{args.out}: stage 2 {doc['stage2']['uncompressed_bytes']:,} bytes, "
              f"{doc['stage2']['string_count']} strings, "
              f"{len(doc['questions']['P9-1_kernel_cmdline']['hits'])} cmdline hits",
              file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
