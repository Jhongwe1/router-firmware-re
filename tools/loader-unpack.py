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
                "hits": hits_for(table, ERASE_NEEDLES + ["Flash Write", "Flash Read",
                                                        "Write 0x", "SPI"]),
            },
        },
        "help_text": [{"offset": f"0x{o:05x}", "string": s} for o, s in table
                      if 12 <= len(s) and re.search(
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
