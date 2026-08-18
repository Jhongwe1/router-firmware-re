#!/usr/bin/env python3
"""Recover `root_form[]` from instruction-free data alone -- a second source for
the dispatch table.

Why a second source
-------------------
Every statement this project makes about which endpoints exist rests on
`reports/ghidra-formtable-*.json`, and that file has exactly one producer.
`readelf` cannot check it: these binaries are `sstrip`'d and have no section
headers at all, so there is nothing to cross-read. The repository's own rule --
*no claim from a single tool* -- has therefore never been satisfied for the one
table that decides what "the attack surface" means.

This is the second source. It has no decompiler, no analysis database, no
reference model and no symbol table. It reads the program headers, then walks
the writable segment looking for the shape of the table itself:

    struct { const char *name; int (*handler)(request *); } root_form[];

An entry is accepted when the first word points at a NUL-terminated identifier
inside a non-writable segment and the second points, word-aligned, into an
executable one. Runs of consecutive accepted entries are reported; a run is the
table.

What it can be wrong about, said before it is run
-------------------------------------------------
  * It finds *shape*, not meaning. Any array of (string pointer, code pointer)
    matches, which is why runs are reported with their addresses and names
    rather than as "the dispatch table" -- `asp_page_variables` has the same
    shape and this scanner finds it too. That is a feature: two tables of the
    same shape is a fact about the binary.
  * A table whose entries are interleaved with a third word would not match at
    stride 8. The stride is therefore a flag, and a run found at one stride and
    not another is reported rather than hidden.
  * A name is accepted on its bytes, so a run of unrelated adjacent strings
    could in principle pass. The control below is what makes that visible.

The control
-----------
`--expect` names identifiers that MUST appear in some run, and the scan exits 2
if any is missing. Every boa in this corpus dispatches `formLogin`; a scanner
that returns a clean empty answer because the stride is wrong, or because the
segment maths is off by an image base, looks exactly like a binary with no
dispatch table. This repository has shipped that mistake twice -- `BoaGate`
reporting 0 findings on a build with 34 hand-read defects, and a tracer going
from 86 to 0 across a version bump.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from pathlib import Path

IDENT = re.compile(rb"^[A-Za-z_][A-Za-z0-9_.\-]{2,63}$")


def load_segments(data: bytes) -> list:
    if data[:4] != b"\x7fELF":
        raise SystemExit("not an ELF")
    if data[5] != 2:
        raise SystemExit("not big-endian; this corpus is MIPS-BE")
    e_phoff = struct.unpack_from(">I", data, 0x1C)[0]
    e_phentsize, e_phnum = struct.unpack_from(">HH", data, 0x2A)
    segs = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, p_offset, p_vaddr, _, p_filesz, p_memsz, p_flags, _ = \
            struct.unpack_from(">8I", data, off)
        if p_type != 1:
            continue
        segs.append({"offset": p_offset, "vaddr": p_vaddr, "filesz": p_filesz,
                     "memsz": p_memsz, "flags": p_flags})
    return segs


def reader(data: bytes, segs: list):
    def to_file(vaddr: int, want_exec=None, want_write=None):
        for s in segs:
            if not (s["vaddr"] <= vaddr < s["vaddr"] + s["filesz"]):
                continue
            if want_exec is not None and bool(s["flags"] & 1) != want_exec:
                return None
            if want_write is not None and bool(s["flags"] & 2) != want_write:
                return None
            return s["offset"] + (vaddr - s["vaddr"])
        return None

    def cstring(vaddr: int, limit: int = 64):
        off = to_file(vaddr, want_write=False)
        if off is None:
            return None
        end = data.find(b"\x00", off, off + limit + 1)
        if end < 0:
            return None
        return data[off:end]

    return to_file, cstring


def scan(path: Path, stride: int) -> dict:
    data = path.read_bytes()
    segs = load_segments(data)
    to_file, cstring = reader(data, segs)

    entries = {}
    for s in segs:
        if not (s["flags"] & 2):        # writable segments only
            continue
        base = s["vaddr"]
        for pos in range(0, (s["filesz"] // 4) * 4 - 4, 4):
            w0, w1 = struct.unpack_from(">II", data, s["offset"] + pos)
            if not w0 or not w1:
                continue
            name = cstring(w0)
            if not name or not IDENT.match(name):
                continue
            if to_file(w1, want_exec=True) is None or w1 % 4:
                continue
            entries[base + pos] = name.decode("ascii")

    runs = []
    addrs = sorted(entries)
    i = 0
    while i < len(addrs):
        j = i
        while j + 1 < len(addrs) and addrs[j + 1] - addrs[j] == stride:
            j += 1
        if j - i + 1 >= 8:
            names = [entries[a] for a in addrs[i:j + 1]]
            form = sum(1 for n in names if n.startswith("form"))
            runs.append({
                "address": f"0x{addrs[i]:08x}",
                "entry_count": j - i + 1,
                "names_starting_with_form": form,
                "role": ("root_form (a dispatch table)" if form > (j - i + 1) / 2
                         else "some other array of (string, function) pairs"),
                "names": names,
            })
        i = j + 1

    return {
        "producer": "formtable-scan",
        "schema_version": "1",
        "binary": str(path),
        "bytes": len(data),
        "stride_bytes": stride,
        "segments": [{"vaddr": f"0x{s['vaddr']:08x}",
                      "filesz": f"0x{s['filesz']:x}",
                      "flags": "".join(c if s["flags"] & b else "-"
                                       for c, b in (("R", 4), ("W", 2), ("X", 1)))}
                     for s in segs],
        "candidate_entries": len(entries),
        "runs": runs,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("binary", nargs="+")
    ap.add_argument("--stride", type=int, default=8,
                    help="bytes per entry (default 8: two 32-bit words)")
    ap.add_argument("--expect", action="append", default=["formLogin"],
                    metavar="NAME",
                    help="repeatable; a name that MUST be found, else exit 2")
    ap.add_argument("--compare", metavar="GHIDRA_JSON",
                    help="a ghidra-formtable-*.json to diff the recovered "
                         "root_form against")
    ap.add_argument("--json", metavar="OUT")
    args = ap.parse_args()

    out = {"producer": "formtable-scan", "schema_version": "1",
           "expect": args.expect, "binaries": []}
    rc = 0
    for b in args.binary:
        r = scan(Path(b), args.stride)
        names = {n for run in r["runs"] for n in run["names"]}
        missing = [e for e in args.expect if e not in names]
        r["control_missing"] = missing
        out["binaries"].append(r)
        tag = Path(b).parent.parent.name
        print(f"{tag:<14} {r['candidate_entries']} candidate pairs, {len(r['runs'])} run(s)")
        for run in r["runs"]:
            print(f"    {run['address']}  {run['entry_count']:>3} entries  {run['role']}")
        if missing:
            print("    CONTROL FAILED: never found {}".format(", ".join(missing)),
                  file=sys.stderr)
            rc = 2

    if args.compare:
        g = json.loads(Path(args.compare).read_text("utf-8"))
        ghidra = {e["name"] for t in g["tables"] if t["role"] == "root_form"
                  for e in t["entries"]}
        mine = set()
        for r in out["binaries"]:
            for run in r["runs"]:
                if run["names_starting_with_form"] > run["entry_count"] / 2:
                    mine |= set(run["names"])
        out["compare"] = {
            "ghidra_report": args.compare,
            "ghidra_only": sorted(ghidra - mine),
            "scan_only": sorted(mine - ghidra),
            "agree": len(ghidra & mine),
        }
        agree, gonly, sonly = (len(ghidra & mine), len(ghidra - mine),
                               len(mine - ghidra))
        print(f"\n  vs {args.compare}: {agree} agree, "
              f"{gonly} ghidra-only, {sonly} scan-only")
        for n in sorted(ghidra - mine):
            print(f"    ghidra only: {n}")
        for n in sorted(mine - ghidra):
            print(f"    scan   only: {n}")

    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=2) + "\n",
                                   encoding="utf-8", newline="\n")
        print(f"\n  wrote {args.json}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
