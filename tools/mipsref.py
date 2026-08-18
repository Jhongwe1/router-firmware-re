#!/usr/bin/env python3
"""Who references this address? -- answered from instruction encodings alone.

Why this exists
---------------
BoaXref's "refs:<addr>" selector answers the same question from Ghidra's
reference model, and for check_auth_flag it answered "one write, no reads".  A
global that is written and never read is a strong claim -- it is the difference
between a latent SDK defect and a live one -- and this repository's rule is that
no claim rests on one tool.  Ghidra and this script are independent: this one
has no analysis database and no reference model.  It decodes MIPS instructions
out of the file and matches immediates.

What version 1 got wrong, and how the device caught it
------------------------------------------------------
Version 1 reported two numbers per address, "reads" and "writes", derived from
the opcode of whichever instruction carried the address as an immediate.  On
2026-08-18 the bench refuted a firmware claim that rested on one of those
numbers: `beforeuptime` (0x004899dc) came back **one read, zero writes**, so the
session window was read as expiring at uptime 601 -- and the device instead
showed it expiring 601 s after *each login*, twice, 706 s apart.

The store was at 0x0044f140 the whole time.  Three separate blindnesses, each of
which alone is enough to turn a written global into `writes: 0`:

  1. **The address never appears in the storing instruction.**  o32 PIC loads a
     global's address out of the GOT -- `lw $v1,%got(beforeuptime)($gp)` -- and
     then stores through it with `sw $v0,0($v1)`.  The immediate in the `sw` is
     `0`.  Nothing in that instruction names 0x004899dc.
  2. **An address in a register is not an access, and not a non-access either.**
     `addiu $a0,$v0,%lo(authipaddr)` materialises an address so that a callee
     can write through it.  Version 1 scored it `reads: False, writes: False`,
     which is indistinguishable in the totals from "not referenced".
  3. **A GOT slot was reported as if it were the variable.**  The committed
     report named 0x00486270 `authipaddr` and gave it "6 reads, 0 writes".
     0x00486270 is `authipaddr`'s *GOT slot*; the variable is at 0x0048fbd8.
     All six were `lw ...($gp)` -- six *address materialisations*, no reads at
     all.

So the answer this tool gives is now four numbers, not two, and it separates
**the address being taken** from **the address being written**:

    direct load        lb/lh/lw/lbu/lhu whose immediate names the address
    direct store       sb/sh/sw whose immediate names the address
    address taken      addiu/addi/ori, or lw ...($gp) of the GOT slot, putting
                       the address into a register
    indirect load /    a load or store through a register that was just shown to
    indirect store     hold the address, at address+displacement
    argument to call   the address is live in $a0..$a3 at a jal/jalr, so a
                       callee may do anything to it (this is the strcpy shape)

and the control that decides whether any of it is trustworthy is now two
controls, because a control can only prove the forms it exercises -- see below.

The addressing forms, because missing one looks exactly like a clean result
------------------------------------------------------------------------
  1. lui r,%hi(a) paired with a load/store/addiu carrying %lo(a).  The pair can
     be split across basic blocks, so this matches on the low half alone and
     prints the instruction; a false positive is visible in the output and a
     miss is not.  Where a matching lui *is* found in a short backward window
     the hit is marked `hi_confirmed`, which separates the 815 coincidental
     `imm == 0x25d0` matches from the handful that really name 0x004725d0.
  2. gp-relative, "lw r,disp(gp)".  gp is NOT taken from Ghidra -- it is
     computed as DT_PLTGOT + 0x7ff0 out of the ELF's own PT_DYNAMIC, which
     survives sstrip because it is a segment and not a section.  On this
     corpus readelf -S returns nothing at all, so anything that needs a section
     header is not available as a second source here.
  3. A 16-bit-representable absolute off $zero, which the toolchain emits for
     low addresses.  Included so the answer does not depend on linker choices.
  4. **Through the GOT.**  The one version 1 did not have.  `lw r,%got(sym)($gp)`
     names the slot, not the symbol, and every subsequent access is at `0(r)`.
     This form is invisible to any scanner that matches immediates against the
     variable's own address, and on this binary it is how `boa` reaches most of
     its globals.

The symbol table nobody had read
--------------------------------
`sstrip` removed the section headers, so `readelf -s` prints nothing and the
project treated this corpus as symbol-less for four weeks.  But `.dynsym` is
reachable without section headers: DT_SYMTAB, DT_STRTAB and DT_SYMENT are in
PT_DYNAMIC because the runtime loader needs them.  424 symbols on this build,
`beforeuptime` and `authipaddr` among them, with their real addresses.  That is
what makes `--sym` possible, what lets a GOT slot be resolved to the symbol it
holds, and what makes "0x00486270 is not authipaddr" a statement the tool can
make by itself rather than a mistake a reader has to catch.

The controls
------------
`--control <addr>` names an address that MUST come back with at least one
direct read AND at least one direct store.  A scanner that cannot fail proves
nothing: if the decode is wrong, or the gp value is wrong, or the file-offset to
virtual-address mapping is wrong, the control returns zero and this exits 2
rather than printing a confident empty answer.  Same rule BoaGate learned the
hard way, twice -- it reported 0 findings on the build W03 had hand-read 34
defects out of.

`--control-indirect <addr>` is the second control, and it exists because the
first one passed all along.  0x004899e0 (`nowuptime`) carries a direct read and
a direct store, so `--control 004899e0` was green in the very run whose
`beforeuptime` answer was wrong.  **A control exercises the code path it
travels and no other.**  The indirect control requires at least one store found
through the dereference pass, so a version of this tool that lost that pass
fails loudly instead of quietly reporting the same numbers as version 1.
`nowuptime` is written both ways in this binary, at 0x0040be54 directly and at
0x0044f14c through its GOT slot, which makes it the one address that can hold
both controls at once.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys

# opcode -> (mnemonic, reads_memory, writes_memory).  Only the forms that can
# carry a %lo() displacement; anything else cannot name an address this way.
OPCODES = {
    0x08: ("addi", False, False),
    0x09: ("addiu", False, False),
    0x0D: ("ori", False, False),
    0x20: ("lb", True, False),
    0x21: ("lh", True, False),
    0x23: ("lw", True, False),
    0x24: ("lbu", True, False),
    0x25: ("lhu", True, False),
    0x28: ("sb", False, True),
    0x29: ("sh", False, True),
    0x2B: ("sw", False, True),
}
LOADS = {0x20: "lb", 0x21: "lh", 0x23: "lw", 0x24: "lbu", 0x25: "lhu"}
STORES = {0x28: "sb", 0x29: "sh", 0x2B: "sw"}
OP_LUI = 0x0F
OP_SPECIAL = 0x00
OP_JAL = 0x03
OP_J = 0x02
FUNCT_JR = 0x08
FUNCT_JALR = 0x09
REG_ZERO = 0
REG_GP = 28
ARG_REGS = (4, 5, 6, 7)                       # $a0..$a3
# o32: everything except $s0..$s7, $gp, $sp, $s8 and $ra is caller-saved, so a
# call destroys it.  Tracking a pointer across a call in $a0 and then crediting
# a later store to it is exactly the kind of confident wrong answer this file
# exists to stop producing.
CALLEE_SAVED = frozenset({16, 17, 18, 19, 20, 21, 22, 23, 28, 29, 30, 31})

PT_LOAD = 1
PT_DYNAMIC = 2
PF_X = 0x1
DT_NULL = 0
DT_STRTAB = 5
DT_SYMTAB = 6
DT_SYMENT = 11
DT_PLTGOT = 3
DT_MIPS_LOCAL_GOTNO = 0x7000000A
DT_MIPS_SYMTABNO = 0x70000011
DT_MIPS_GOTSYM = 0x70000013

# How far the dereference pass follows a register.  A basic block in this corpus
# is short; the walk also stops at the first redefinition, at a call that
# clobbers the register, and at the end of the block, so this is only a backstop
# against a straight-line run of nothing relevant.
DEREF_WINDOW = 24
# How far back a matching lui is looked for when confirming a %hi/%lo pair.
HI_WINDOW = 12


def parse_elf(data: bytes) -> dict:
    """Program headers and PT_DYNAMIC only.  Section headers are gone: sstrip."""
    if data[:4] != b"\x7fELF":
        raise SystemExit("mipsref: not an ELF")
    if data[4] != 1:
        raise SystemExit("mipsref: ELFCLASS32 only")
    if data[5] != 2:
        raise SystemExit(f"mipsref: big-endian only; EI_DATA={data[5]}")
    (e_phoff,) = struct.unpack_from(">I", data, 0x1C)
    e_phentsize, e_phnum = struct.unpack_from(">HH", data, 0x2A)
    segments = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        fields = struct.unpack_from(">8I", data, off)
        segments.append({
            "type": fields[0], "offset": fields[1], "vaddr": fields[2],
            "filesz": fields[4], "memsz": fields[5], "flags": fields[6],
        })
    dynamic = {}
    for seg in segments:
        if seg["type"] != PT_DYNAMIC:
            continue
        pos = seg["offset"]
        while pos + 8 <= len(data):
            tag, val = struct.unpack_from(">II", data, pos)
            if tag == DT_NULL:
                break
            dynamic.setdefault(tag, val)
            pos += 8
    return {"segments": segments, "dynamic": dynamic}


def off_to_vaddr(segments, off):
    for seg in segments:
        if seg["type"] != PT_LOAD:
            continue
        if seg["offset"] <= off < seg["offset"] + seg["filesz"]:
            return seg["vaddr"] + (off - seg["offset"])
    return None


def vaddr_to_off(segments, vaddr):
    for seg in segments:
        if seg["type"] != PT_LOAD:
            continue
        if seg["vaddr"] <= vaddr < seg["vaddr"] + seg["filesz"]:
            return seg["offset"] + (vaddr - seg["vaddr"])
    return None


def executable_ranges(segments):
    out = []
    for seg in segments:
        if seg["type"] == PT_LOAD and (seg["flags"] & PF_X):
            out.append((seg["offset"], seg["offset"] + seg["filesz"]))
    return out


class Symbols:
    """`.dynsym`, reached through PT_DYNAMIC because the section headers are gone.

    This is not a convenience.  Without it the tool cannot tell a GOT slot from
    a variable, which is the mistake that put "authipaddr: 6 reads, 0 writes"
    into a committed report.
    """

    def __init__(self, data, segments, dynamic):
        self.by_name = {}
        self.by_addr = {}
        self.count = 0
        self.got_slots = {}
        self.got_base = dynamic.get(DT_PLTGOT)
        self.local_gotno = dynamic.get(DT_MIPS_LOCAL_GOTNO)
        self.gotsym = dynamic.get(DT_MIPS_GOTSYM)
        self.symtabno = dynamic.get(DT_MIPS_SYMTABNO)
        symtab = dynamic.get(DT_SYMTAB)
        strtab = dynamic.get(DT_STRTAB)
        syment = dynamic.get(DT_SYMENT) or 16
        if symtab is None or strtab is None or self.symtabno is None:
            return
        str_off = vaddr_to_off(segments, strtab)
        sym_off = vaddr_to_off(segments, symtab)
        if str_off is None or sym_off is None:
            return
        for i in range(self.symtabno):
            pos = sym_off + i * syment
            if pos + 16 > len(data):
                break
            st_name, st_value, st_size, _info, _other, st_shndx = \
                struct.unpack_from(">IIIBBH", data, pos)
            end = data.find(b"\0", str_off + st_name)
            name = data[str_off + st_name:end].decode("ascii", "replace")
            if not name:
                continue
            self.count += 1
            self.by_name.setdefault(name, (st_value, st_size, st_shndx))
            if st_value:
                self.by_addr.setdefault(st_value, name)
        if self.got_base is not None and self.local_gotno is not None \
                and self.gotsym is not None:
            n_global = self.symtabno - self.gotsym
            for i in range(n_global):
                slot = self.got_base + 4 * (self.local_gotno + i)
                idx = self.gotsym + i
                pos = sym_off + idx * syment
                if pos + 16 > len(data):
                    break
                st_name, st_value, _sz, _info, _other, _shndx = \
                    struct.unpack_from(">IIIBBH", data, pos)
                end = data.find(b"\0", str_off + st_name)
                name = data[str_off + st_name:end].decode("ascii", "replace")
                self.got_slots[slot] = {"symbol": name, "value": st_value,
                                        "index": idx}

    def got_end(self):
        if self.got_base is None or self.local_gotno is None \
                or self.gotsym is None or self.symtabno is None:
            return None
        return self.got_base + 4 * (self.local_gotno + self.symtabno - self.gotsym)

    def is_got_slot(self, addr):
        end = self.got_end()
        return end is not None and self.got_base <= addr < end

    def describe(self, addr):
        """A name for an address, exact or as symbol+offset."""
        if addr in self.by_addr:
            return self.by_addr[addr]
        best = None
        for value, name in self.by_addr.items():
            if value <= addr and (best is None or value > best[0]):
                size = self.by_name.get(name, (0, 0, 0))[1]
                if size and addr < value + size:
                    best = (value, name)
        if best:
            return f"{best[1]}+{addr - best[0]}"
        return None


def hi_of(addr):
    return ((addr + 0x8000) >> 16) & 0xFFFF


class Code:
    """The executable words, indexed by file offset, decoded once."""

    def __init__(self, data, segments):
        self.data = data
        self.segments = segments
        self.words = {}
        for start, end in executable_ranges(segments):
            end = min(end, len(data))
            for off in range(start - (start % 4), end - 3, 4):
                (word,) = struct.unpack_from(">I", data, off)
                self.words[off] = word

    def va(self, off):
        return off_to_vaddr(self.segments, off)


def dest_register(word):
    """Which register this instruction writes, or None.

    Only the forms that matter for invalidating a tracked pointer.  Anything
    unrecognised returns None, which is the permissive answer -- and permissive
    here means the walk keeps going and may attribute one store too many, which
    is visible in the output, rather than stopping early and reporting a miss,
    which is not.
    """
    op = word >> 26
    if op == OP_SPECIAL:
        funct = word & 0x3F
        if funct in (FUNCT_JR,):
            return None
        return (word >> 11) & 31                       # rd
    if op in (OP_LUI, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E) or op in LOADS:
        return (word >> 16) & 31                       # rt
    return None


def is_call(word):
    op = word >> 26
    if op == OP_JAL:
        return True
    return op == OP_SPECIAL and (word & 0x3F) == FUNCT_JALR


def is_block_end(word):
    op = word >> 26
    if op == OP_J:
        return True
    return op == OP_SPECIAL and (word & 0x3F) == FUNCT_JR


def follow(code, off, reg, target, symbols, name):
    """Walk forward from `off` while `reg` still holds `target`.

    Returns the indirect accesses and the calls the pointer was live across.
    The walk ends at the first of: the register being redefined, a call that
    clobbers it, the end of the basic block, or DEREF_WINDOW instructions.
    Branch delay slots are not special-cased for termination -- the instruction
    after a jump executes, so the walk continues one past a block end and then
    stops.
    """
    out = []
    ended = None

    def access(pos, word, delay_slot=False):
        """Record a load/store through `reg`, or return False if it is neither."""
        op = word >> 26
        base = (word >> 21) & 31
        if base != reg or (op not in STORES and op not in LOADS):
            return False
        disp = word & 0xFFFF
        disp = disp - 0x10000 if disp & 0x8000 else disp
        table = STORES if op in STORES else LOADS
        out.append({
            "kind": "indirect-store" if op in STORES else "indirect-load",
            "mnemonic": table[op], "vaddr": code.va(pos), "file_offset": pos,
            "displacement": disp, "effective": (target + disp) & 0xFFFFFFFF,
            "value_reg": (word >> 16) & 31, "base_reg": reg, "word": word,
            "delay_slot": delay_slot,
        })
        return True

    k = 1
    while k <= DEREF_WINDOW:
        pos = off + 4 * k
        word = code.words.get(pos)
        if word is None:
            ended = "end-of-segment"
            break
        rt = (word >> 16) & 31
        if access(pos, word):
            if (word >> 26) in LOADS and rt == reg:
                ended = "pointer-reloaded"
                break
            k += 1
            continue
        if is_call(word) or is_block_end(word):
            # The delay slot executes BEFORE control transfers, so the pointer
            # is still live in it. Reading the call as the end of the register's
            # life and stopping here is how the indirect control first failed:
            # `nowuptime` is stored at 0x0044f14c, which is the delay slot of
            # the jalr at 0x0044f148. One instruction, and the answer inverts.
            if is_call(word) and reg in ARG_REGS:
                out.append({"kind": "arg-to-call", "mnemonic": "jal/jalr",
                            "vaddr": code.va(pos), "file_offset": pos,
                            "arg_reg": reg, "word": word, "delay_slot": False,
                            "note": f"${reg} still holds &{name}, so the callee "
                                    "may read or write through it"})
            slot = code.words.get(pos + 4)
            if slot is not None:
                access(pos + 4, slot, delay_slot=True)
            if is_block_end(word):
                ended = "end-of-block"
                break
            if reg not in CALLEE_SAVED:
                ended = "clobbered-by-call"
                break
            k += 2                      # past the call and its delay slot
            continue
        if dest_register(word) == reg:
            ended = "redefined"
            break
        k += 1
    return out, ended or "window-exhausted"


def confirm_hi(code, off, target, base_reg):
    """Was a matching `lui base_reg,%hi(target)` emitted just before this?

    A %lo() match alone is ambiguous: 815 instructions in this boa carry
    `imm == 0x25d0` and one of them is the reference to 0x004725d0.  A confirmed
    pair is not required -- the halves can be split across basic blocks, which
    is why the permissive match stays -- but where the pair is visible, saying
    so turns an unusable list into a short one.
    """
    want = hi_of(target)
    for k in range(1, HI_WINDOW + 1):
        word = code.words.get(off - 4 * k)
        if word is None:
            return False
        if (word >> 26) == OP_LUI and ((word >> 16) & 31) == base_reg \
                and (word & 0xFFFF) == want:
            return True
        if dest_register(word) == base_reg:
            return False
    return False


def scan(code, symbols, gp, target, name):
    """Every instruction that names `target`, classified, plus what follows."""
    low_half = target & 0xFFFF
    direct = []
    indirect = []
    got_slot = None
    if symbols.got_base is not None:
        for slot, info in symbols.got_slots.items():
            if info["value"] == target and info["symbol"] == name:
                got_slot = slot
                break
        if got_slot is None and name:
            for slot, info in symbols.got_slots.items():
                if info["symbol"] == name:
                    got_slot = slot
                    break
    got_disp = None
    if got_slot is not None and gp is not None:
        delta = got_slot - gp
        if -0x8000 <= delta < 0x8000:
            got_disp = delta & 0xFFFF

    for off in sorted(code.words):
        word = code.words[off]
        opcode = (word >> 26) & 0x3F
        base = (word >> 21) & 31
        rt = (word >> 16) & 31
        imm = word & 0xFFFF
        signed = imm - 0x10000 if imm & 0x8000 else imm

        # form 4: the GOT.  `lw rt,%got(sym)($gp)` puts &sym into rt.
        if got_disp is not None and opcode == 0x23 and base == REG_GP \
                and imm == got_disp:
            hit = {"file_offset": off, "vaddr": code.va(off), "word": word,
                   "mnemonic": "lw", "form": "got", "kind": "address-taken",
                   "base_reg": base, "into_reg": rt, "hi_confirmed": None,
                   "reads": False, "writes": False,
                   "note": f"loads &{name or hex(target)} out of GOT slot "
                           f"0x{got_slot:08x}"}
            direct.append(hit)
            found, why = follow(code, off, rt, target, symbols, name or hex(target))
            for f in found:
                f["from_vaddr"] = hit["vaddr"]
                f["via"] = "got"
            if found:
                indirect.extend(found)
            hit["follow_ended"] = why
            continue

        entry = OPCODES.get(opcode)
        if entry is None:
            continue
        mnemonic, reads, writes = entry
        if base == REG_GP and gp is not None and ((gp + signed) & 0xFFFFFFFF) == target:
            form = "gp-relative"
        elif base == REG_ZERO and (signed & 0xFFFFFFFF) == target:
            form = "absolute"
        elif imm == low_half and base not in (REG_GP, REG_ZERO):
            form = "lo-half"
        else:
            continue
        if reads:
            kind = "load"
        elif writes:
            kind = "store"
        else:
            kind = "address-taken"
        hit = {"file_offset": off, "vaddr": code.va(off), "word": word,
               "mnemonic": mnemonic, "form": form, "kind": kind,
               "base_reg": base, "into_reg": rt if kind != "store" else None,
               "hi_confirmed": confirm_hi(code, off, target, base)
                               if form == "lo-half" else None,
               "reads": reads, "writes": writes}
        direct.append(hit)
        if kind == "address-taken":
            found, why = follow(code, off, rt, target, symbols, name or hex(target))
            for f in found:
                f["from_vaddr"] = hit["vaddr"]
                f["via"] = form
            indirect.extend(found)
            hit["follow_ended"] = why
    return direct, indirect, got_slot


def summarise(direct, indirect):
    return {
        "direct_loads": sum(1 for h in direct if h["kind"] == "load"),
        "direct_stores": sum(1 for h in direct if h["kind"] == "store"),
        "address_taken": sum(1 for h in direct if h["kind"] == "address-taken"),
        "indirect_loads": sum(1 for h in indirect if h["kind"] == "indirect-load"),
        "indirect_stores": sum(1 for h in indirect if h["kind"] == "indirect-store"),
        "args_to_calls": sum(1 for h in indirect if h["kind"] == "arg-to-call"),
        "hi_confirmed": sum(1 for h in direct if h.get("hi_confirmed") is True),
    }


def resolve(spec, symbols):
    """`--addr`/`--sym`/control values: hex, or a symbol name."""
    text = spec.strip()
    try:
        return int(text, 16), symbols.by_addr.get(int(text, 16))
    except ValueError:
        pass
    if text in symbols.by_name:
        return symbols.by_name[text][0], text
    raise SystemExit(
        f"mipsref: {spec!r} is neither a hex address nor a symbol in .dynsym "
        f"({symbols.count} symbols read). Run with --symbols to list them.")


def wanted_any(args) -> bool:
    return bool(args.addr) or bool(args.sym) or bool(args.control) \
        or bool(args.control_indirect)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("binary")
    parser.add_argument("--addr", action="append", default=[],
                        help="target virtual address in hex; repeatable. A "
                             "symbol name is accepted here too")
    parser.add_argument("--sym", action="append", default=[],
                        help="target by symbol name out of .dynsym; repeatable")
    parser.add_argument("--segments", action="store_true",
                        help="print the program headers with their flags and say which "
                             "one holds DT_PLTGOT. This is the second source for the "
                             "'RELRO: none' column the fwrecon reports carry -- on MIPS "
                             "the GOT is where every call goes, so whether that segment "
                             "is writable is the whole of P5-3's question")
    parser.add_argument("--symbols", action="store_true",
                        help="list .dynsym, recovered through PT_DYNAMIC because "
                             "sstrip removed the section headers")
    parser.add_argument("--control", default=None,
                        help="address that must show at least one direct read "
                             "and one direct store, else exit 2")
    parser.add_argument("--control-indirect", default=None,
                        help="address that must show at least one store found "
                             "through the dereference pass, else exit 2. Without "
                             "it a build that lost that pass reports the same "
                             "numbers version 1 did, silently")
    parser.add_argument("--json", default=None,
                        help="write the full result to this path")
    args = parser.parse_args()

    with open(args.binary, "rb") as handle:
        data = handle.read()
    elf = parse_elf(data)
    segments = elf["segments"]
    if not executable_ranges(segments):
        raise SystemExit("mipsref: no executable PT_LOAD segment")
    pltgot = elf["dynamic"].get(DT_PLTGOT)
    gp = (pltgot + 0x7FF0) if pltgot else None
    symbols = Symbols(data, segments, elf["dynamic"])
    code = Code(data, segments)

    result = {
        "producer": "mipsref",
        "schema": 2,
        "binary": args.binary,
        # G3.5's rule: a report that cannot name the binary it describes is not
        # evidence about any binary. The path is not enough -- two builds live at
        # the same path in two extracted trees.
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "dt_pltgot": pltgot,
        "gp": gp,
        "dynsym_count": symbols.count,
        "got": {
            "base": symbols.got_base,
            "local_gotno": symbols.local_gotno,
            "gotsym": symbols.gotsym,
            "symtabno": symbols.symtabno,
            "end": symbols.got_end(),
        },
        "control": args.control,
        "control_indirect": args.control_indirect,
        # Written last, and it is what makes a committed "0 references" answer
        # readable. Without it a scan that decoded nothing and a binary that
        # really holds nothing produce the same file.
        "control_ok": None,
        "control_indirect_ok": None,
        "targets": {},
    }
    got_text = hex(pltgot) if pltgot else "absent"
    gp_text = hex(gp) if gp else "unknown"
    print(f"file: {args.binary} ({len(data)} bytes)")
    print(f"DT_PLTGOT={got_text} so gp={gp_text} -- read from the ELF, not from Ghidra")
    if symbols.count:
        print(f".dynsym: {symbols.count} symbols via PT_DYNAMIC "
              f"(sstrip removed the section headers, not these)")
        if symbols.got_end() is not None:
            print(f"GOT: 0x{symbols.got_base:08x}..0x{symbols.got_end():08x}, "
                  f"{symbols.local_gotno} local + "
                  f"{symbols.symtabno - symbols.gotsym} global slots")
    else:
        print(".dynsym: not recoverable from PT_DYNAMIC on this binary -- "
              "GOT slots cannot be told from variables, so treat every "
              "address-taken count below as a lower bound")

    if args.symbols:
        print("\ndynamic symbols with an address")
        for addr in sorted(symbols.by_addr):
            print(f"  0x{addr:08x}  {symbols.by_addr[addr]}")

    if args.segments:
        names = {1: "LOAD", 2: "DYNAMIC", 3: "INTERP", 4: "NOTE", 6: "PHDR",
                 0x6474E550: "GNU_EH_FRAME", 0x6474E551: "GNU_STACK",
                 0x6474E552: "GNU_RELRO", 0x70000000: "MIPS_REGINFO"}
        print("\nprogram headers")
        relro = None
        for seg in segments:
            flags = "".join(c if seg["flags"] & bit else "-"
                            for bit, c in ((4, "R"), (2, "W"), (1, "X")))
            holds = ""
            if pltgot and seg["type"] == PT_LOAD and \
               seg["vaddr"] <= pltgot < seg["vaddr"] + seg["memsz"]:
                holds = "   <-- holds DT_PLTGOT (the GOT)"
            if seg["type"] == 0x6474E552:
                relro = seg
            kind = names.get(seg["type"], hex(seg["type"]))
            print(f"  {kind:<14} vaddr=0x{seg['vaddr']:08x} "
                  f"memsz=0x{seg['memsz']:06x}  {flags}{holds}")
        if relro is None:
            print("  no PT_GNU_RELRO segment: nothing is re-protected read-only after "
                  "relocation, so the GOT keeps whatever flags its PT_LOAD has")
        else:
            end = relro["vaddr"] + relro["memsz"]
            print(f"  PT_GNU_RELRO covers 0x{relro['vaddr']:08x}..0x{end:08x}")
        if not wanted_any(args):
            return 0
    if args.symbols and not wanted_any(args):
        return 0

    wanted = list(args.addr) + list(args.sym)
    for extra in (args.control, args.control_indirect):
        if extra and extra not in wanted:
            wanted.append(extra)

    resolved = {}
    for text in wanted:
        addr, name = resolve(text, symbols)

        # The mistake that produced "authipaddr: 6 reads, 0 writes". A GOT slot
        # is not the variable; every reference to it is an address being taken.
        # Redirect rather than answer, because answering is what went wrong.
        if symbols.is_got_slot(addr):
            info = symbols.got_slots.get(addr)
            if info:
                print(f"\n0x{addr:08x} is GOT slot #{(addr - symbols.got_base)//4}, "
                      f"holding &{info['symbol']} = 0x{info['value']:08x}.")
                print("   It is not a datum. Every instruction that names it is "
                      "taking an address, and nothing ever stores to a GOT slot in "
                      "normal code, so a 'writes: 0' answer here means nothing.")
                print(f"   Scanning {info['symbol']} at 0x{info['value']:08x} instead.")
                addr, name = info["value"], info["symbol"]
            else:
                print(f"\n0x{addr:08x} is inside the GOT but names no global slot "
                      "(it is one of the local entries). Not a datum.")

        if name is None:
            name = symbols.describe(addr)
        direct, indirect, got_slot = scan(code, symbols, gp, addr, name)
        summary = summarise(direct, indirect)
        resolved[text] = f"0x{addr:08x}"
        result["targets"][f"0x{addr:08x}"] = {
            "symbol": name,
            "got_slot": got_slot,
            "summary": summary,
            "direct": direct,
            "indirect": indirect,
        }
        marker = ""
        if args.control and text == args.control:
            marker += "   <-- CONTROL"
        if args.control_indirect and text == args.control_indirect:
            marker += "   <-- INDIRECT CONTROL"
        title = f"0x{addr:08x}"
        if name:
            title += f"  {name}"
        if got_slot is not None:
            title += f"  (GOT slot 0x{got_slot:08x})"
        print(f"\n{title}{marker}")
        print(f"   direct: {summary['direct_loads']} load, "
              f"{summary['direct_stores']} store, "
              f"{summary['address_taken']} address-taken"
              + (f" ({summary['hi_confirmed']} with a confirmed %hi pair)"
                 if any(h.get("hi_confirmed") is not None for h in direct) else ""))
        print(f"   through a register: {summary['indirect_loads']} load, "
              f"{summary['indirect_stores']} store, "
              f"{summary['args_to_calls']} live at a call")
        for hit in direct:
            extra = ""
            if hit["form"] == "lo-half":
                extra = "  hi:yes" if hit.get("hi_confirmed") else "  hi:no"
            if hit.get("note"):
                extra += "  " + hit["note"]
            print(f"   file=0x{hit['file_offset']:06x} "
                  f"va=0x{hit['vaddr'] or 0:08x}  "
                  f"{hit['mnemonic']:<5} {hit['form']:<12} "
                  f"{hit['kind']:<14} base=${hit['base_reg']:<2} "
                  f"word=0x{hit['word']:08x}{extra}")
        for hit in indirect:
            where = f"{name or 'target'}+{hit.get('displacement', 0)}"
            print(f"      -> va=0x{hit['vaddr'] or 0:08x}  "
                  f"{hit['mnemonic']:<6} {hit['kind']:<15} {where:<22} "
                  f"(from 0x{hit['from_vaddr'] or 0:08x} via {hit['via']})")

    # The controls are evaluated BEFORE the file is written, so that a report
    # which fails one is never committed as though it had passed. A failed run
    # still writes -- with control_ok false -- because a reader who has one
    # should be able to see what it saw, and check-reports.py refuses it.
    failed = False
    if args.control:
        entry = result["targets"][resolved[args.control]]
        ok = entry["summary"]["direct_loads"] > 0 and entry["summary"]["direct_stores"] > 0
        result["control_ok"] = ok
        failed = failed or not ok
    if args.control_indirect:
        entry = result["targets"][resolved[args.control_indirect]]
        ok = entry["summary"]["indirect_stores"] > 0
        result["control_indirect_ok"] = ok
        failed = failed or not ok

    if args.json:
        with open(args.json, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(result, handle, indent=2)
            handle.write("\n")

    if failed:
        if args.control and result["control_ok"] is False:
            print(f"\nmipsref: CONTROL FAILED -- {args.control} shows no direct "
                  "read and/or no direct store. The decode, the gp value or the "
                  "offset-to-vaddr mapping is wrong, so every other answer "
                  "above is unusable.", file=sys.stderr)
        if args.control_indirect and result["control_indirect_ok"] is False:
            print(f"\nmipsref: INDIRECT CONTROL FAILED -- {args.control_indirect} "
                  "shows no store reached through a register. The dereference "
                  "pass is not running, so every 'no writes' answer above is the "
                  "version 1 answer, which was wrong about beforeuptime.",
                  file=sys.stderr)
        return 2
    if args.control:
        print(f"\ncontrol ok: {args.control} carries both a direct read and a "
              "direct store")
    if args.control_indirect:
        print(f"indirect control ok: {args.control_indirect} carries a store "
              "reached through a register, so the dereference pass ran")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
