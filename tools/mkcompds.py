#!/usr/bin/env python3
"""Emit a minimal, valid COMPDS / COMPCS settings region for an emulated flash.

Why this exists
---------------
A flash rebuilt from a published container cannot start `apmib`, because the
settings regions are written at manufacture and ship in no download. With a
hardware-setting block in place (tools/mkhwsetting.py) the vendor's library gets
one step further and then says exactly what it wants:

    Invalid default setting signature or version number [sig=.., ver=-1, len=-1]!
    Expect [sig=6G, ver=3, len=32858]!

That message is the specification, and this tool writes to it. The vendor's own
`flash default` would generate the real thing "from hard code", but it dies
under qemu-user on an unaligned store that the device's MIPS kernel fixes up in
its trap handler -- so on the desktop the generator is unavailable at precisely
the point it is needed. This produces the smallest blob the library will accept
instead: a well-formed, all-zero MIB.

What that costs, said here rather than discovered later
-------------------------------------------------------
Every setting comes out zero. `IP_ADDR` is 0.0.0.0, there is no admin password,
no SSID. This is emphatically *not* a stand-in for a real configuration, and
nothing about default credentials or shipped settings may be concluded from an
environment standing on it. What it is good for is the code paths that do not
read configuration -- which includes the request handlers, and therefore the
command-injection site G4 clause 3a is about.

It is also, deliberately, nobody's configuration. A real COMPDS lifted off a
physical unit would work better and would make the environment unreproducible
by anyone who does not own that unit, which is the whole objection L2 exists to
answer.

Format: `notes/compcs-decode.md`. The 8-bit payload checksum is the vendor's,
recovered from `_apmib_dsconf` at 0x0001781c, and an all-zero payload satisfies
it trivially -- which is worth stating, because a checksum that is satisfied by
construction has not been tested by this tool. `tools/test-mkcompds.sh` uses a
non-zero body for exactly that reason.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools" / "fwrecon" / "src"))

try:
    from fwrecon.compcs import CompcsError, encode_region
except ImportError as exc:  # pragma: no cover
    sys.exit(f"mkcompds: cannot import fwrecon ({exc}); try `make setup`")

# "6G" is the default block, "6g" the current one -- one bit of case, and it is
# the only thing distinguishing the two decompressed streams.
SIG = {"compds": b"6G", "compcs": b"6g"}
MAGIC = {"compds": b"COMPDS", "compcs": b"COMPCS"}
# COMPDS sits at 0x8000 and COMPCS at 0xC000, so each has 16 KiB and neither may
# grow into the next.
SLOT_BYTES = 0x4000


def build_body(sig: bytes, version: int, length: int) -> bytes:
    """sig[2] + ver[2] ASCII + u32 len + `length` payload bytes summing to zero."""
    if not 0 <= version <= 99:
        raise CompcsError(f"version {version} does not fit the two ASCII digits the format has")
    payload = bytearray(length)
    payload[-1] = (-sum(payload[:-1])) & 0xFF
    body = sig + f"{version:02d}".encode("ascii") + struct.pack(">I", length) + bytes(payload)
    if len(body) != 8 + length:
        raise CompcsError(f"self-check: body is {len(body)}, declared {length} + 8")
    if sum(body[8:]) & 0xFF != 0:
        raise CompcsError("self-check: payload does not sum to zero mod 256")
    return body


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Emit a minimal valid COMPDS/COMPCS region for an emulated flash.",
        epilog="Take --length from what libapmib says it expects: run "
        "`flash all` in the environment and read the 'Expect [sig=..., len=N]' line.",
    )
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--kind", choices=sorted(SIG), default="compds")
    ap.add_argument(
        "--length", required=True, type=lambda s: int(s, 0),
        help="payload length the target build expects (32858 for V2.1.2)",
    )
    ap.add_argument("--version", type=int, default=3, help="MIB version (default 3)")
    ap.add_argument(
        "--comp-rate", type=int, default=None,
        help="allocation hint; default is the ratio actually achieved, rounded up",
    )
    ap.add_argument(
        "--slot-bytes", type=lambda s: int(s, 0), default=SLOT_BYTES,
        help=f"refuse to emit a region larger than this (default {SLOT_BYTES:#x})",
    )
    args = ap.parse_args(argv)

    try:
        body = build_body(SIG[args.kind], args.version, args.length)
        region = encode_region(
            body, MAGIC[args.kind], comp_rate=args.comp_rate, max_bytes=args.slot_bytes
        )
    except CompcsError as exc:
        print(f"mkcompds: {exc}", file=sys.stderr)
        return 1

    args.out.write_bytes(region)
    ratio = len(body) / len(region)
    print(f"wrote {args.out}  {len(region)} bytes  sha256 {hashlib.sha256(region).hexdigest()}")
    print(f"  {args.kind.upper()}  sig {SIG[args.kind].decode()} ver {args.version:02d} "
          f"payload {args.length}  ->  {len(body)} decompressed, {ratio:.1f}x")
    print("  round-tripped through the vendor's own decoder before writing")
    print("  every setting in it is zero: this is not a configuration")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
