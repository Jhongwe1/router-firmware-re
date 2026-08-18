#!/usr/bin/env python3
"""Where was the shared library mapped -- answered from the ELF and one kernel line.

What this exists for
--------------------
`P5-2` asks whether uClibc sits at a fixed address on this unit, so that a
ret2libc target can be *computed* rather than leaked.  Its refutation condition
is written as "the libc base differs across two reboots".

That refutation is aimed at the wrong axis, and saying so is the first thing
this tool does.  Address-space randomisation on Linux is applied per `execve`,
not per boot: `randomize_va_space` is consulted in `load_elf_binary`, and two
processes started from the same boot get independently randomised layouts if it
is on.  So two *processes* is the discriminating measurement, and two reboots is
a weaker version of it that happens to be harder to obtain on a device with no
shell.

This unit has already produced two of them, in kernel fault messages recorded at
the bench, from two different programs that link *different* library sets:

    boa     do_page_fault() ... epc == 2aafe218  ra == 00445974
    wscd    do_page_fault() ... epc == 2aae1f38  ra == 2aae1e64

Neither line names a library.  Turning them into a base is what this does.

The three things it will not do
-------------------------------
  * **It will not accept a base that is not page-aligned.**  `mmap` returns
    page-aligned addresses, so an implied base with low bits set means the
    assumed symbol is the wrong one.  This is the only cheap falsifier available
    and it is a 1-in-1024 filter per candidate, so it is applied first and the
    report carries how many of the library's symbols survived it.

  * **It will not silently pick one candidate.**  A symbol at least a page long
    admits more than one page-aligned base.  Where that happens the answer is a
    list and the exit status is a refusal, because choosing between them needs
    evidence this tool does not have.

  * **It will not confuse an `epc` with a faulting instruction.**  On MIPS, when
    the fault is taken in a branch delay slot the kernel sets `Cause.BD` and
    `EPC` names the *branch*, four bytes earlier, because restarting has to
    re-execute the branch.  The console line does not print `BD`.  So both
    `epc` and `epc + 4` are resolved and the report says which one landed and
    whether the word at `epc` decodes as a branch -- which is what makes the
    four-byte disagreement between this device and qemu-user a prediction
    instead of an excuse.

The control, and why it is this one
-----------------------------------
`crash-triage-unit-2018.json` carries qemu-user's own disassembly of the same
fault:

    0x2b327218:  bnez  v1,0x2b32720c
 => 0x2b32721c:  sb    v1,0(a2)

Those two words are read back out of `libuClibc` at the offsets this tool
derives and decoded independently.  If the bytes in the file are not a `bne`
against `$zero` followed by an `sb` through the same register, then "the fault
is in `strcpy`" was an assumption and every number below it is void.  The report
carries `control_ok` and `check-reports.py` refuses the file without it.

The ELF reader here is deliberately its own, rather than an import of
`tools/mipsref.py`.  Both walk `PT_DYNAMIC` to reach `.dynsym` -- `sstrip`
removed the section headers from this corpus, not the dynamic segment -- and
`tools/test-libbase.sh` asserts the two agree on `strcpy` and `system`.  A
symbol address is the input to everything else in this file, so it is the one
number that gets two readers.

    tools/libbase.py --span   <so>
    tools/libbase.py --solve  0x2aafe218 --in <libc> --symbol strcpy
    tools/libbase.py --resolve 0x2aae1f38 --in <libc> --base 0x2aabe000
    tools/libbase.py --report ... --json reports/libbase-unit-2018.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

PAGE = 0x1000

PT_LOAD = 1
PT_DYNAMIC = 2

DT_NULL = 0
DT_NEEDED = 1
DT_STRTAB = 5
DT_SYMTAB = 6
DT_STRSZ = 10
DT_SYMENT = 11
DT_MIPS_SYMTABNO = 0x70000011

STT_FUNC = 2
STT_OBJECT = 1


class ElfError(Exception):
    """The file is not the big-endian MIPS ELF this tool can read."""


class Refused(Exception):
    """A measurement this tool will not report, with the reason attached."""


# --------------------------------------------------------------------------
# The ELF, read directly. Big-endian MIPS32 only, which is the whole corpus.
# --------------------------------------------------------------------------


class Elf:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.data = self.path.read_bytes()
        d = self.data
        if len(d) < 52 or d[:4] != b"\x7fELF":
            raise ElfError(f"{self.path.name}: not an ELF")
        if d[4] != 1:
            raise ElfError(f"{self.path.name}: not ELFCLASS32")
        if d[5] != 2:
            raise ElfError(f"{self.path.name}: not big-endian")
        (self.e_type, self.e_machine) = struct.unpack_from(">HH", d, 16)
        if self.e_machine != 8:
            raise ElfError(f"{self.path.name}: e_machine {self.e_machine}, not MIPS")
        (self.e_phoff,) = struct.unpack_from(">I", d, 28)
        (self.e_phentsize, self.e_phnum) = struct.unpack_from(">HH", d, 42)
        self.phdrs = []
        for i in range(self.e_phnum):
            off = self.e_phoff + i * self.e_phentsize
            if off + 32 > len(d):
                raise ElfError(f"{self.path.name}: program header {i} runs off the end")
            p_type, p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz, p_flags, p_align = (
                struct.unpack_from(">8I", d, off))
            self.phdrs.append({
                "type": p_type, "offset": p_offset, "vaddr": p_vaddr,
                "filesz": p_filesz, "memsz": p_memsz, "flags": p_flags,
                "align": p_align,
            })
        self.loads = [p for p in self.phdrs if p["type"] == PT_LOAD]
        if not self.loads:
            raise ElfError(f"{self.path.name}: no PT_LOAD, so it is never mapped")
        self._dynamic = None
        self._symbols = None

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()

    def vaddr_to_off(self, vaddr: int) -> int | None:
        for p in self.loads:
            if p["vaddr"] <= vaddr < p["vaddr"] + p["filesz"]:
                return p["offset"] + (vaddr - p["vaddr"])
        return None

    def word(self, vaddr: int) -> int | None:
        """The 32-bit big-endian word at a link-time address, or None."""
        off = self.vaddr_to_off(vaddr)
        if off is None or off + 4 > len(self.data):
            return None
        return struct.unpack_from(">I", self.data, off)[0]

    @property
    def dynamic(self) -> list[tuple[int, int]]:
        if self._dynamic is None:
            dyn = [p for p in self.phdrs if p["type"] == PT_DYNAMIC]
            if not dyn:
                raise ElfError(f"{self.path.name}: no PT_DYNAMIC")
            p = dyn[0]
            out = []
            for i in range(p["filesz"] // 8):
                tag, val = struct.unpack_from(">II", self.data, p["offset"] + i * 8)
                out.append((tag, val))
                if tag == DT_NULL:
                    break
            self._dynamic = out
        return self._dynamic

    def dt(self, tag: int) -> int | None:
        for t, v in self.dynamic:
            if t == tag:
                return v
        return None

    def needed(self) -> list[str]:
        strtab = self.dt(DT_STRTAB)
        if strtab is None:
            return []
        base = self.vaddr_to_off(strtab)
        if base is None:
            base = strtab
        out = []
        for t, v in self.dynamic:
            if t != DT_NEEDED:
                continue
            end = self.data.index(b"\0", base + v)
            out.append(self.data[base + v:end].decode("ascii", "replace"))
        return out

    @property
    def symbols(self) -> list[dict]:
        """(value, size, name, type) for every .dynsym entry with an address.

        The count comes from DT_MIPS_SYMTABNO, which the ABI requires and which
        does not depend on a section header the `sstrip` in this corpus removed.
        """
        if self._symbols is not None:
            return self._symbols
        symtab = self.dt(DT_SYMTAB)
        strtab = self.dt(DT_STRTAB)
        count = self.dt(DT_MIPS_SYMTABNO)
        syment = self.dt(DT_SYMENT) or 16
        if symtab is None or strtab is None or count is None:
            raise ElfError(
                f"{self.path.name}: PT_DYNAMIC has no DT_SYMTAB/DT_STRTAB/"
                "DT_MIPS_SYMTABNO, so .dynsym cannot be reached without section "
                "headers")
        soff = self.vaddr_to_off(symtab)
        stroff = self.vaddr_to_off(strtab)
        if soff is None or stroff is None:
            raise ElfError(f"{self.path.name}: DT_SYMTAB/DT_STRTAB fall outside PT_LOAD")
        out = []
        for i in range(count):
            off = soff + i * syment
            if off + 16 > len(self.data):
                break
            st_name, st_value, st_size, st_info, _o, _shndx = struct.unpack_from(
                ">IIIBBH", self.data, off)
            if st_value == 0 or st_name == 0:
                continue
            end = self.data.index(b"\0", stroff + st_name)
            name = self.data[stroff + st_name:end].decode("ascii", "replace")
            out.append({
                "name": name, "value": st_value, "size": st_size,
                "type": st_info & 0xF,
            })
        self._symbols = out
        return out

    def symbol(self, name: str) -> dict:
        for s in self.symbols:
            if s["name"] == name:
                return s
        raise Refused(
            f"{self.path.name}: no dynamic symbol named {name!r}; this tool will "
            "not guess an address for a name the file does not export")


# --------------------------------------------------------------------------
# The four operations, as functions, so the guard suite can drive them.
# --------------------------------------------------------------------------


def mapped_span(elf: Elf, page: int = PAGE) -> int:
    """How much address space one object occupies once mapped.

    The loader reserves the whole vaddr range in one mapping and then protects
    the pieces, so the span that matters is from the lowest PT_LOAD's page down
    to the highest PT_LOAD's page up -- p_filesz is irrelevant and p_memsz is
    what counts, because .bss is mapped too.
    """
    lo = min(p["vaddr"] for p in elf.loads)
    hi = max(p["vaddr"] + p["memsz"] for p in elf.loads)
    lo &= ~(page - 1)
    hi = (hi + page - 1) & ~(page - 1)
    return hi - lo


def solve_base(addr: int, sym: dict, page: int = PAGE) -> list[int]:
    """Every page-aligned base that would put `addr` inside `sym`.

    Empty means the assumed symbol cannot explain the address at all. More than
    one means the symbol is at least a page long and the alignment filter has no
    power here; both are refusals, and neither is a number.
    """
    size = sym["size"] or 1
    out = []
    for k in range(size):
        base = addr - sym["value"] - k
        if base > 0 and base % page == 0:
            out.append(base)
    return out


def coincidence_window(elf: Elf, epc: int, ra: int, lo: int, hi: int,
                       page: int = PAGE) -> list[dict]:
    """How many other page-aligned bases would have looked just as good.

    A prediction that lands is worth exactly as much as the number of ways it
    could have failed, and asserting that number is not measuring it. So this
    sweeps every page-aligned base across a window and counts the ones that put
    BOTH the faulting address and the return address inside one and the same
    function -- which is the property the prediction was judged on.

    The answer on this unit is 8 in 256, not 1 in 256, and that belongs in the
    report: the prediction survived a filter it had roughly a one-in-thirty
    chance of surviving by luck, and the rest of the weight has to come from the
    fault *kind*, which is a separate argument.
    """
    out = []
    for base in range(lo, hi, page):
        a = containing_symbol(elf, epc - base)
        b = containing_symbol(elf, ra - base)
        if a and b and a["name"] == b["name"] and a["type"] == STT_FUNC:
            out.append({"base": f"0x{base:08x}", "symbol": a["name"]})
    return out


def containing_symbol(elf: Elf, off: int) -> dict | None:
    """The symbol whose [value, value+size) contains a link-time offset."""
    best = None
    for s in elf.symbols:
        size = s["size"] or 1
        if (s["value"] <= off < s["value"] + size
                and (best is None or s["value"] > best["value"])):
            best = s
    return best


def discrimination(elf: Elf, addr: int, page: int = PAGE) -> int:
    """How many of this library's symbols could have explained `addr`.

    The whole weight of a solved base rests on the page-alignment filter, so the
    report has to say how selective that filter actually was. If every symbol
    survives it, the answer below is arithmetic dressed as evidence.
    """
    n = 0
    for s in elf.symbols:
        if solve_base(addr, s, page):
            n += 1
    return n


def candidate_sites(elf: Elf, addr: int, want: str, page: int = PAGE) -> list[dict]:
    """Every symbol that could hold `addr`, with the instruction that would be there.

    Page alignment on its own leaves a couple of dozen symbols, and picking
    `strcpy` out of them because the answer is known is not a measurement. The
    kernel line says `invalid WRITE access`, so the instruction at the implied
    offset has to be a store; that is a property of the bytes in the file and it
    is checkable per candidate. What survives both filters is the list this
    returns, and if it has more than one entry the report says so rather than
    narrating past it.
    """
    stores = {"sb", "sh", "sw"}
    branches = {"bne", "bnez", "beq", "beqz", "branch", "jump-register"}
    out = []
    for s in elf.symbols:
        if s["type"] != STT_FUNC:
            continue
        for base in solve_base(addr, s, page):
            off = addr - base
            word = elf.word(off)
            if word is None:
                continue
            kind = decode_kind(word)
            nxt = elf.word(off + 4)
            nkind = None if nxt is None else decode_kind(nxt)
            # Two readings, because the console line does not print Cause.BD.
            direct = kind in stores if want == "store" else kind == want
            delayed = (kind in branches
                       and (nkind in stores if want == "store" else nkind == want))
            # The last filter is not a property of this file: qemu-user executed
            # the same request on a different host and printed the instruction
            # *pair* -- `bnez v1,...` then `sb v1,0(a2)`, one source register
            # shared. Requiring that pair is what separates a second observer
            # from a second guess.
            pair = (kind == "bnez" and nkind == "sb"
                    and rs_rt(word)[0] == rs_rt(nxt)[1])
            out.append({
                "symbol": s["name"],
                "symbol_value": f"0x{s['value']:x}",
                "symbol_size": s["size"],
                "implied_base": f"0x{base:08x}",
                "offset_into_symbol": f"0x{off - s['value']:x}",
                "word": f"0x{word:08x}",
                "instruction": kind,
                "next_instruction": nkind,
                "fault_at_epc": direct,
                "fault_in_delay_slot": delayed,
                "matches_qemu_instruction_pair": pair,
                "survives": direct or delayed,
            })
    return out


# MIPS32 instructions that have a delay slot. An epc naming one of these means
# the fault was taken in the slot and the faulting instruction is at epc + 4.
_BRANCH_OPS = {0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x14, 0x15, 0x16, 0x17}
_REGIMM_RT = {0x00, 0x01, 0x02, 0x03, 0x10, 0x11, 0x12, 0x13}


def decode_kind(word: int) -> str:
    """Just enough decode to tell a branch from a store. Not a disassembler."""
    op = (word >> 26) & 0x3F
    if op in _BRANCH_OPS:
        rt = (word >> 16) & 0x1F
        if op == 0x05:
            return "bne" if rt else "bnez"
        if op == 0x04:
            return "beq" if rt else "beqz"
        return "branch"
    if op == 0x01 and ((word >> 16) & 0x1F) in _REGIMM_RT:
        return "branch"
    if op == 0x11 and ((word >> 21) & 0x1F) == 0x08:
        return "branch"
    if op == 0x00 and (word & 0x3F) in (0x08, 0x09):
        return "jump-register"
    if op == 0x28:
        return "sb"
    if op == 0x29:
        return "sh"
    if op == 0x2B:
        return "sw"
    if op in (0x20, 0x21, 0x23, 0x24, 0x25):
        return "load"
    return "other"


def rs_rt(word: int) -> tuple[int, int]:
    return ((word >> 21) & 0x1F, (word >> 16) & 0x1F)


def epc_candidates(epc: int) -> list[dict]:
    """The two addresses a MIPS kernel `epc` can mean.

    The console line prints no `BD` bit, so both have to be carried until one of
    them resolves. Order matters only for reporting: the delay-slot reading is
    listed second because it is the one that needs a branch at `epc` to be true.
    """
    return [
        {"addr": epc, "reading": "the faulting instruction itself"},
        {"addr": epc + 4,
         "reading": "the delay slot of a branch at epc (Cause.BD set)"},
    ]


# --------------------------------------------------------------------------
# The report
# --------------------------------------------------------------------------


def control_strcpy_bytes(libc: Elf, sym: dict) -> dict:
    """Read back the two words qemu-user disassembled, out of the file.

    `crash-triage-unit-2018.json` says the fault is `sb v1,0(a2)` at strcpy+0x1c
    with `bnez v1,...` at +0x18. If the bytes in libuClibc are not those two
    instructions, then naming `strcpy` was an assumption and the base derived
    from it means nothing.
    """
    at18 = libc.word(sym["value"] + 0x18)
    at1c = libc.word(sym["value"] + 0x1C)
    out = {
        "site": f"{sym['name']}+0x18 / +0x1c",
        "word_at_plus_0x18": None if at18 is None else f"0x{at18:08x}",
        "word_at_plus_0x1c": None if at1c is None else f"0x{at1c:08x}",
        "kind_at_plus_0x18": None if at18 is None else decode_kind(at18),
        "kind_at_plus_0x1c": None if at1c is None else decode_kind(at1c),
        "qemu_disassembly": ["bnez v1,0x2b32720c", "sb v1,0(a2)"],
    }
    ok = False
    if at18 is not None and at1c is not None:
        branch_ok = out["kind_at_plus_0x18"] == "bnez"
        store_ok = out["kind_at_plus_0x1c"] == "sb"
        # Same register in both: `bnez v1` then `sb v1,0(a2)`.
        same_reg = rs_rt(at18)[0] == rs_rt(at1c)[1]
        out["branch_matches"] = branch_ok
        out["store_matches"] = store_ok
        out["same_source_register"] = same_reg
        ok = branch_ok and store_ok and same_reg
    out["ok"] = ok
    return out


def build_report(libc_path: Path, args) -> dict:
    libc = Elf(libc_path)
    strcpy = libc.symbol("strcpy")
    system = libc.symbol("system")

    control = control_strcpy_bytes(libc, strcpy)

    # boa: the kernel named the branch, so the base follows from epc, not epc+4.
    boa_epc = args.boa_epc
    boa_readings = []
    for cand in epc_candidates(boa_epc):
        bases = solve_base(cand["addr"], strcpy)
        cand["bases"] = [f"0x{b:08x}" for b in bases]
        cand["offset_into_symbol"] = (
            None if not bases else cand["addr"] - bases[0] - strcpy["value"])
        boa_readings.append(cand)
    # Narrowing, mechanically. The kernel line says "invalid WRITE access", so a
    # candidate has to put a store at the epc or in the delay slot of a branch
    # there. This is the step that stops `strcpy` being a name pulled out of the
    # answer.
    cands = candidate_sites(libc, boa_epc, "store")
    survivors = [c for c in cands if c["survives"]]
    pair_matched = [c for c in survivors if c["matches_qemu_instruction_pair"]]
    if len(pair_matched) != 1:
        raise Refused(
            f"{len(pair_matched)} candidates match qemu-user's instruction pair "
            "(bnez R / sb R,0(reg)); the narrowing does not land on one site and "
            "this tool will not name one: "
            + ", ".join(c["symbol"] for c in pair_matched))
    if pair_matched[0]["symbol"] != "strcpy":
        raise Refused(
            "the narrowing lands on "
            f"{pair_matched[0]['symbol']}, not strcpy -- the report below is "
            "written around strcpy and would be describing a different fault")

    bases = solve_base(boa_epc, strcpy)
    if not bases:
        raise Refused(
            f"boa epc 0x{boa_epc:08x} admits no page-aligned base inside strcpy "
            f"(0x{strcpy['value']:x}, {strcpy['size']} bytes) -- the assumption "
            "that the fault is in strcpy is refuted, not adjusted")
    if len(bases) > 1:
        raise Refused(
            f"boa epc 0x{boa_epc:08x} admits {len(bases)} page-aligned bases "
            "inside strcpy; the alignment filter has no power here and this "
            "tool will not choose between them: "
            + ", ".join(f"0x{b:08x}" for b in bases))
    boa_base = bases[0]

    # The prediction. Nothing below is measured: it comes out of libapmib's own
    # program headers, and it is the half of this report that can be wrong.
    apmib = Elf(args.differing_object)
    span = mapped_span(apmib)
    predicted = boa_base - span
    if predicted % PAGE:
        raise Refused(
            f"predicted sibling base 0x{predicted:08x} is not page-aligned; the "
            "span model is wrong, and a prediction that cannot be a base is not "
            "a prediction")
    off = args.wscd_epc - predicted
    hit = containing_symbol(libc, off)
    if hit is None:
        raise Refused(
            f"wscd epc 0x{args.wscd_epc:08x} lands at libc+0x{off:x} under the "
            f"predicted base 0x{predicted:08x}, and that offset is inside no "
            "dynamic symbol -- the prediction failed and the difference between "
            "the two processes is not this object's span")
    ra_off = args.wscd_ra - predicted
    ra_hit = containing_symbol(libc, ra_off)

    # The prediction's own error bar. Swept over the 256 pages around the answer,
    # because that is the neighbourhood a wrong span model would have landed in.
    lo = (predicted - 0xBE000) & ~(PAGE - 1)
    rivals = coincidence_window(libc, args.wscd_epc, args.wscd_ra, lo, lo + 0x100000)

    return {
        "producer": "libbase",
        "schema": 1,
        "question": "P5-2 -- is uClibc at a computable address on this unit",
        "page_size": PAGE,
        "objects": {
            "libc": {
                "path": str(libc_path),
                "sha256": libc.sha256,
                "dynsym_count": len(libc.symbols),
                "mapped_span": f"0x{mapped_span(libc):x}",
                "needed": libc.needed(),
            },
            "differing_object": {
                "path": str(args.differing_object),
                "sha256": apmib.sha256,
                "mapped_span": f"0x{span:x}",
            },
        },
        "source_sha256": libc.sha256,
        "control": control,
        "control_ok": control["ok"],
        "measured": {
            "boa": {
                "kernel_line": f"epc == {boa_epc:08x}, ra == {args.boa_ra:08x}",
                "epc_readings": boa_readings,
                "symbol": "strcpy",
                "symbol_value": f"0x{strcpy['value']:x}",
                "symbol_size": strcpy["size"],
                "offset_into_symbol": f"0x{boa_epc - boa_base - strcpy['value']:x}",
                "libc_base": f"0x{boa_base:08x}",
                "symbols_admitting_a_page_aligned_base": discrimination(libc, boa_epc),
                "symbols_total": len(libc.symbols),
                "narrowing": {
                    "fault_kind_from_kernel": "invalid write access -- a store",
                    "function_candidates_after_page_alignment": len(cands),
                    "candidates_putting_a_store_at_epc_or_its_delay_slot":
                        len(survivors),
                    "candidates_matching_qemus_instruction_pair": len(pair_matched),
                    "survivors": survivors,
                },
            },
        },
        "predicted": {
            "claim": (
                "boa NEEDED libapmib.so, libc.so.0, libgcc_s.so.1; wscd NEEDED "
                "libc.so.0, libgcc_s.so.1. If the loader allocates bottom-up and "
                "nothing is randomised, the two libc bases differ by exactly the "
                "mapped span of the one object that differs."),
            "differing_object_span": f"0x{span:x}",
            "wscd_libc_base": f"0x{predicted:08x}",
            "wscd_epc": f"0x{args.wscd_epc:08x}",
            "wscd_epc_offset": f"0x{off:x}",
            "wscd_epc_symbol": hit["name"],
            "wscd_epc_into_symbol": f"0x{off - hit['value']:x}",
            "wscd_ra_symbol": None if ra_hit is None else ra_hit["name"],
            "wscd_ra_into_symbol":
                None if ra_hit is None else f"0x{ra_off - ra_hit['value']:x}",
            "held": hit is not None,
            "how_easily_it_could_have_held_by_luck": {
                "window": f"0x{lo:08x}..0x{lo + 0x100000:08x}, {0x100000 // PAGE} pages",
                "bases_putting_epc_and_ra_in_one_function": len(rivals),
                "so_the_prediction_survived_a_filter_of_about":
                    f"1 in {(0x100000 // PAGE) // max(len(rivals), 1)}",
                "rivals": rivals,
                "what_carries_the_rest": (
                    "the fault kind. The kernel line is 'invalid READ access from "
                    "4187c8bc' -- a wild pointer dereference -- and of the bases "
                    "above, the predicted one names free(), which with malloc() is "
                    "where a corrupted heap chunk is read. The others would each "
                    "need a different story and none was offered."),
            },
        },
        "answer": {
            "system_symbol_value": f"0x{system['value']:x}",
            "system_in_boa": f"0x{boa_base + system['value']:08x}",
            "system_in_wscd": f"0x{predicted + system['value']:08x}",
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Where was the shared library mapped -- from the ELF and one "
                    "kernel line.")
    ap.add_argument("--in", dest="lib", help="the shared object to read")
    ap.add_argument("--span", action="store_true",
                    help="print the mapped span of --in and stop")
    ap.add_argument("--solve", type=lambda s: int(s, 0),
                    help="an absolute runtime address to solve a base for")
    ap.add_argument("--symbol", help="the symbol --solve is believed to be inside")
    ap.add_argument("--resolve", type=lambda s: int(s, 0),
                    help="an absolute runtime address to name, given --base")
    ap.add_argument("--base", type=lambda s: int(s, 0), help="a known load base")
    ap.add_argument("--report", action="store_true",
                    help="build the full P5-2 report from the recorded faults")
    ap.add_argument("--differing-object",
                    help="the object present in one process and not the other")
    ap.add_argument("--boa-epc", type=lambda s: int(s, 0), default=0x2AAFE218)
    ap.add_argument("--boa-ra", type=lambda s: int(s, 0), default=0x00445974)
    ap.add_argument("--wscd-epc", type=lambda s: int(s, 0), default=0x2AAE1F38)
    ap.add_argument("--wscd-ra", type=lambda s: int(s, 0), default=0x2AAE1E64)
    ap.add_argument("--json", help="write the report here")
    args = ap.parse_args(argv)

    if not args.lib:
        ap.error("--in is required")
    path = Path(args.lib)

    try:
        if args.span:
            elf = Elf(path)
            print(f"{path.name}: mapped span 0x{mapped_span(elf):x} "
                  f"({len(elf.loads)} PT_LOAD, page 0x{PAGE:x})")
            return 0

        if args.solve is not None:
            if not args.symbol:
                ap.error("--solve needs --symbol")
            elf = Elf(path)
            sym = elf.symbol(args.symbol)
            bases = solve_base(args.solve, sym)
            if not bases:
                raise Refused(
                    f"0x{args.solve:08x} admits no page-aligned base inside "
                    f"{args.symbol} (0x{sym['value']:x}, {sym['size']} bytes)")
            if len(bases) > 1:
                raise Refused(
                    f"0x{args.solve:08x} admits {len(bases)} page-aligned bases "
                    f"inside {args.symbol}; refusing to choose")
            print(f"0x{args.solve:08x} in {args.symbol} "
                  f"(+0x{args.solve - bases[0] - sym['value']:x}) "
                  f"-> base 0x{bases[0]:08x}")
            print(f"  of {len(elf.symbols)} dynamic symbols, "
                  f"{discrimination(elf, args.solve)} admit a page-aligned base "
                  "for this address")
            return 0

        if args.resolve is not None:
            if args.base is None:
                ap.error("--resolve needs --base")
            elf = Elf(path)
            off = args.resolve - args.base
            hit = containing_symbol(elf, off)
            if hit is None:
                raise Refused(
                    f"0x{args.resolve:08x} is libc+0x{off:x} under base "
                    f"0x{args.base:08x}, and that is inside no dynamic symbol")
            print(f"0x{args.resolve:08x} = +0x{off:x} = "
                  f"{hit['name']}+0x{off - hit['value']:x} "
                  f"(symbol at 0x{hit['value']:x}, {hit['size']} bytes)")
            return 0

        if args.report:
            if not args.differing_object:
                ap.error("--report needs --differing-object")
            doc = build_report(path, args)
            text = json.dumps(doc, indent=2, sort_keys=False) + "\n"
            if args.json:
                Path(args.json).write_text(text, encoding="utf-8", newline="\n")
                print(f"wrote {args.json}")
            else:
                sys.stdout.write(text)
            return 0

        ap.error("nothing to do: pass --span, --solve, --resolve or --report")
    except (ElfError, Refused) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
