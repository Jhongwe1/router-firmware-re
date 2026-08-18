#!/usr/bin/env python3
"""Emit a structurally valid, content-free Realtek `H601` hardware-setting block.

Why this exists
---------------
`apmib_init()` refuses to start when the hardware setting is absent, and the
hardware setting is written at manufacture -- it is in no downloadable image.
Measured on 2026-08-18: a flash rebuilt from the published V2.1.2 container and
nothing else produces

    Invalid hw setting signature [sig=  ]!
    Initialize AP MIB failed!

so the emulation route that G4 clause 3 asks for cannot start from a download
alone.  This tool is the smallest thing that closes that gap without borrowing
a byte from any physical unit.

What it emits, and what it deliberately does not
------------------------------------------------
A real `H601` block holds MAC addresses and per-die radio calibration.  Those
are a measurement of one piece of silicon; `docs/disclosure.md` treats them as
per-unit and this tool never reproduces them.  The payload here is zeroed, with
one checksum byte chosen so the block validates.  What comes out is therefore
*structurally* a hardware setting and *semantically* empty -- which is the
honest thing for a reproduction environment to stand on, because anyone can
regenerate it and it describes nobody's hardware.

The format, and where each field came from
------------------------------------------
Derived on 2026-08-18 from this unit's dump, then cross-checked against a fact
W06 had already established by a different route:

    +0  char  sig[2]   "H6"
    +2  char  ver[2]   "01"          ASCII, the same convention COMPCS uses
    +4  u16   len      1166, big-endian, payload bytes excluding this header
    +6  u8    payload[len]           sum(payload) & 0xff == 0

`0x6000 + 6 + 1166 = 0x6494`, so the block's last byte is `0x6493` -- which is
the byte W06 identified as "the H601 region's 8-bit checksum" by watching it
change under an injected `flash set`.  Reading it out of the header arithmetic
and watching it move under a write are independent, and they agree.

`--verify-format-against` re-derives the header from a real dump and refuses if
this tool's constants disagree with it.  It compares *structure only*: sig, ver,
declared length and whether the checksum rule holds. No payload byte is read,
compared or printed.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

SIG = b"H6"
VER = b"01"
HEADER_LEN = 6
PAYLOAD_LEN = 1166
DEFAULT_BASE = 0x6000


class HwError(Exception):
    pass


def build(payload_len: int = PAYLOAD_LEN) -> bytes:
    if payload_len < 1:
        raise HwError("payload length must be at least 1 (the checksum byte)")
    payload = bytearray(payload_len)
    # Everything is zero, so the running sum is zero and the checksum byte is
    # zero too. Computing it anyway rather than writing 0: the moment anyone
    # gives this tool a non-empty payload the constant would be silently wrong,
    # and a checksum that happens to be right is not a checksum.
    payload[-1] = (-sum(payload[:-1])) & 0xFF
    blk = SIG + VER + payload_len.to_bytes(2, "big") + bytes(payload)

    # Self-check on the artefact, not on the intent.
    if len(blk) != HEADER_LEN + payload_len:
        raise HwError(f"self-check: built {len(blk)} bytes, wanted {HEADER_LEN + payload_len}")
    if sum(blk[HEADER_LEN:]) & 0xFF != 0:
        raise HwError("self-check: payload checksum does not sum to zero")
    if blk[:2] != SIG or blk[2:4] != VER:
        raise HwError("self-check: signature or version did not land where declared")
    return blk


def verify_format_against(dump: Path, base: int, payload_len: int) -> list[str]:
    """Structure only. Reads the six header bytes and computes one sum; no
    payload byte is printed, returned or compared against anything."""
    data = dump.read_bytes()
    if len(data) < base + HEADER_LEN:
        return [f"{dump.name}: too short to hold a header at {base:#x}"]
    problems = []
    sig, ver = data[base:base + 2], data[base + 2:base + 4]
    ln = int.from_bytes(data[base + 4:base + 6], "big")
    if sig != SIG:
        problems.append(f"{dump.name}: signature at {base:#x} is {sig!r}, this tool emits {SIG!r}")
    if ver != VER:
        problems.append(f"{dump.name}: version at {base:#x} is {ver!r}, this tool emits {VER!r}")
    if ln != payload_len:
        problems.append(
            f"{dump.name}: declares payload length {ln}, this tool emits {payload_len}"
        )
    if not problems:
        end = base + HEADER_LEN + ln
        if len(data) < end:
            problems.append(f"{dump.name}: declares {ln} payload bytes but the dump ends first")
        elif sum(data[base + HEADER_LEN:end]) & 0xFF != 0:
            problems.append(
                f"{dump.name}: the payload at {base:#x} does not sum to zero mod 256, so "
                f"the checksum rule this tool implements is not the rule this image uses"
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Emit a structurally valid, content-free H601 hardware-setting block.",
        epilog="The output contains no data from any physical unit: the payload is "
        "zeroed and the checksum is computed over those zeros. Splice it in with "
        "tools/mkflash.py --overlay FILE@0x6000.",
    )
    ap.add_argument("--out", required=True, type=Path, help="where to write the block")
    ap.add_argument(
        "--payload-len", type=lambda s: int(s, 0), default=PAYLOAD_LEN,
        help=f"payload bytes excluding the 6-byte header (default {PAYLOAD_LEN})",
    )
    ap.add_argument(
        "--verify-format-against", type=Path, metavar="DUMP",
        help="a real flash dump to check the header constants against (structure only)",
    )
    ap.add_argument(
        "--base", type=lambda s: int(s, 0), default=DEFAULT_BASE,
        help=f"where the block sits in that dump (default {DEFAULT_BASE:#x})",
    )
    args = ap.parse_args(argv)

    try:
        if args.verify_format_against:
            problems = verify_format_against(
                args.verify_format_against, args.base, args.payload_len
            )
            if problems:
                raise HwError("\n       ".join(problems))
            print(f"format check ok against {args.verify_format_against.name} "
                  f"(sig, version, declared length, checksum rule)")
        blk = build(args.payload_len)
    except HwError as exc:
        print(f"mkhwsetting: {exc}", file=sys.stderr)
        return 1

    args.out.write_bytes(blk)
    print(f"wrote {args.out}  {len(blk)} bytes  sha256 {hashlib.sha256(blk).hexdigest()}")
    print(f"  sig {SIG.decode()} ver {VER.decode()} payload {args.payload_len} "
          f"-> occupies {args.base:#08x}..{args.base + len(blk):#08x}")
    print("  payload is zeroed: this block describes no physical unit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
