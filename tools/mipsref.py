#!/usr/bin/env python3
"""Who references this address? -- answered from instruction encodings alone.

Why this exists
---------------
BoaXref's "refs:<addr>" selector answers the same question from Ghidra's
reference model, and for check_auth_flag it answered "one write, no reads".  A
global that is written and never read is a strong claim -- it is the difference
between a latent SDK defect and a live one -- and this repository's rule is that
no claim rests on one tool.  Ghidra and this script are independent: this one
has no symbol table, no analysis database and no reference model.  It decodes
MIPS instructions out of the file and matches immediates.

The three addressing forms, because missing one looks exactly like a clean
result
--------------------------------------------------------------------------
  1. lui r,%hi(a) paired with a load/store/addiu carrying %lo(a).  The pair can
     be split across basic blocks, so this matches on the low half alone and
     prints the instruction; a false positive is visible in the output and a
     miss is not.
  2. gp-relative, "lw r,disp(gp)".  gp is NOT taken from Ghidra -- it is
     computed as DT_PLTGOT + 0x7ff0 out of the ELF's own PT_DYNAMIC, which
     survives sstrip because it is a segment and not a section.  On this
     corpus readelf -S returns nothing at all, so anything that needs a section
     header is not available as a second source here.
  3. A 16-bit-representable absolute off $zero, which the toolchain emits for
     low addresses.  Included so the answer does not depend on linker choices.

The control
-----------
--control <addr> names an address that MUST come back with at least one read
AND at least one write.  A scanner that cannot fail proves nothing: if the
decode is wrong, or the gp value is wrong, or the file-offset to virtual-address
mapping is wrong, the control returns zero and this exits 2 rather than printing
a confident empty answer.  Same rule BoaGate learned the hard way, twice -- it
reported 0 findings on the build W03 had hand-read 34 defects out of.
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
REG_ZERO = 0
REG_GP = 28

PT_LOAD = 1
PT_DYNAMIC = 2
PF_X = 0x1
DT_NULL = 0
DT_PLTGOT = 3


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


def executable_ranges(segments):
    out = []
    for seg in segments:
        if seg["type"] == PT_LOAD and (seg["flags"] & PF_X):
            out.append((seg["offset"], seg["offset"] + seg["filesz"]))
    return out


def scan(data, segments, gp, target):
    low_half = target & 0xFFFF
    hits = []
    for start, end in executable_ranges(segments):
        end = min(end, len(data))
        for off in range(start - (start % 4), end - 3, 4):
            (word,) = struct.unpack_from(">I", data, off)
            opcode = (word >> 26) & 0x3F
            entry = OPCODES.get(opcode)
            if entry is None:
                continue
            mnemonic, reads, writes = entry
            base = (word >> 21) & 31
            imm = word & 0xFFFF
            signed = imm - 0x10000 if imm & 0x8000 else imm
            if base == REG_GP and gp is not None and ((gp + signed) & 0xFFFFFFFF) == target:
                form = "gp-relative"
            elif base == REG_ZERO and (signed & 0xFFFFFFFF) == target:
                form = "absolute"
            elif imm == low_half and base not in (REG_GP, REG_ZERO):
                form = "lo-half"
            else:
                continue
            hits.append({
                "file_offset": off,
                "vaddr": off_to_vaddr(segments, off),
                "word": word,
                "mnemonic": mnemonic,
                "form": form,
                "base_reg": base,
                "reads": reads,
                "writes": writes,
            })
    return hits


def wanted_any(args) -> bool:
    return bool(args.addr) or bool(args.control)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("binary")
    parser.add_argument("--addr", action="append", default=[],
                        help="target virtual address in hex; repeatable")
    parser.add_argument("--segments", action="store_true",
                        help="print the program headers with their flags and say which "
                             "one holds DT_PLTGOT. This is the second source for the "
                             "'RELRO: none' column the fwrecon reports carry -- on MIPS "
                             "the GOT is where every call goes, so whether that segment "
                             "is writable is the whole of P5-3's question")
    parser.add_argument("--control", default=None,
                        help="address that must show at least one read and one "
                             "write, else exit 2")
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

    result = {
        "producer": "mipsref",
        "binary": args.binary,
        # G3.5's rule: a report that cannot name the binary it describes is not
        # evidence about any binary. The path is not enough -- two builds live at
        # the same path in two extracted trees.
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "dt_pltgot": pltgot,
        "gp": gp,
        "control": args.control,
        # Written last, and it is what makes a committed "0 references" answer
        # readable. Without it a scan that decoded nothing and a binary that
        # really holds nothing produce the same file.
        "control_ok": None,
        "targets": {},
    }
    got_text = hex(pltgot) if pltgot else "absent"
    gp_text = hex(gp) if gp else "unknown"
    print(f"file: {args.binary} ({len(data)} bytes)")
    print(f"DT_PLTGOT={got_text} so gp={gp_text} -- read from the ELF, not from Ghidra")

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

    wanted = list(args.addr)
    if args.control and args.control not in wanted:
        wanted.append(args.control)

    for text in wanted:
        addr = int(text, 16)
        hits = scan(data, segments, gp, addr)
        result["targets"][f"0x{addr:08x}"] = hits
        reads = sum(1 for h in hits if h["reads"])
        writes = sum(1 for h in hits if h["writes"])
        marker = "   <-- CONTROL" if args.control and text == args.control else ""
        print(f"\n0x{addr:08x}: {len(hits)} reference(s), "
              f"{reads} read, {writes} write{marker}")
        for hit in hits:
            print(f"   file=0x{hit['file_offset']:06x} "
                  f"va=0x{hit['vaddr'] or 0:08x}  "
                  f"{hit['mnemonic']:<5} {hit['form']:<12} "
                  f"base=${hit['base_reg']:<2} word=0x{hit['word']:08x}")

    # The control is evaluated BEFORE the file is written, so that a report which
    # fails it is never committed as though it had passed. A failed run still
    # writes -- with control_ok false -- because a reader who has one should be
    # able to see what it saw, and check-reports.py refuses it.
    failed = False
    if args.control:
        hits = result["targets"][f"0x{int(args.control, 16):08x}"]
        ok = any(h["reads"] for h in hits) and any(h["writes"] for h in hits)
        result["control_ok"] = ok
        failed = not ok

    if args.json:
        with open(args.json, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(result, handle, indent=2)
            handle.write("\n")

    if args.control:
        if failed:
            print(f"\nmipsref: CONTROL FAILED -- {args.control} shows no read "
                  "and/or no write. The decode, the gp value or the "
                  "offset-to-vaddr mapping is wrong, so every other answer "
                  "above is unusable.", file=sys.stderr)
            return 2
        print(f"\ncontrol ok: {args.control} carries both a read and a write")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
