#!/usr/bin/env python3
"""Read a ZIP's local file header, and recover the payload from a truncated one.

Written because W04-2 obtained the published V2.1.6 as a 40%-complete browser
download and drew conclusions from it. Two things had to be true for that to be
legitimate, and neither was checked by a tool:

  1. the archive really is truncated rather than corrupt — an important
     distinction, because deflate is a stream and a *prefix* still decompresses
     while a corrupt file does not; and
  2. nobody later mistakes the prefix for the whole image.

So this refuses to write a recovered payload from an incomplete archive unless
told `--allow-partial`, and names the output accordingly. `PROGRESS.md` open #0
asks for the zip's own CRC-32 to be verified before anything is concluded from
a re-download; that check is the point of this script and it is wired to the
exit code, because a check that cannot fail proves nothing.

Reads the header field by field rather than trusting the inner filename. The
filename is text a mirror can type; the DOS timestamp is a separate field the
packer writes, so the two agreeing is worth more than either alone. It is still
only corroboration: TOTOLINK publishes no signature, so nothing here can show
the bytes came from the vendor (`firmware/SOURCES.json`).

Usage:
    python tools/zipprefix.py ARCHIVE.zip [-o RECOVERED.bin] [--allow-partial]

Exit codes:
    0  archive complete and CRC-32 verified
    1  archive incomplete (or CRC mismatch) — expected for a partial download,
       and still a failure unless --allow-partial says that was the intent
    2  not a ZIP local file header at all
"""

from __future__ import annotations

import argparse
import binascii
import struct
import sys
import zlib
from pathlib import Path

LOCAL_HEADER = b"PK\x03\x04"
EOCD = b"PK\x05\x06"
FIXED = "<HHHHHIIIHH"          # after the 4-byte signature, ZIP APPNOTE 4.3.7
FIXED_LEN = struct.calcsize(FIXED)


def dos_datetime(mdate: int, mtime: int) -> str:
    return (
        f"{((mdate >> 9) & 0x7F) + 1980:04d}-{(mdate >> 5) & 0x0F:02d}-{mdate & 0x1F:02d} "
        f"{(mtime >> 11) & 0x1F:02d}:{(mtime >> 5) & 0x3F:02d}:{(mtime & 0x1F) * 2:02d}"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("archive")
    ap.add_argument("-o", "--output", help="write the recovered payload here")
    ap.add_argument("--allow-partial", action="store_true",
                    help="permit writing output from a known-incomplete archive")
    args = ap.parse_args(argv)

    blob = Path(args.archive).read_bytes()
    print(f"archive              {args.archive}")
    print(f"bytes on disk        {len(blob):,}")

    if blob[:4] != LOCAL_HEADER:
        print(f"FATAL: no local file header signature (got {blob[:4]!r})", file=sys.stderr)
        return 2

    (_ver, _flags, method, mtime, mdate, crc,
     csize, usize, nlen, elen) = struct.unpack(FIXED, blob[4:4 + FIXED_LEN])
    name = blob[30:30 + nlen].decode("ascii", "replace")
    data_off = 30 + nlen + elen

    print(f"inner filename       {name}")
    print(f"method               {method} ({'deflate' if method == 8 else 'other'})")
    print(f"DOS mtime            {dos_datetime(mdate, mtime)}")
    print(f"stored CRC-32        0x{crc:08x}")
    print(f"compressed size      {csize:,}")
    print(f"uncompressed size    {usize:,}")

    # The filename may embed a build date (TOTOLINK ships "...-B20160516.1233").
    # It is text; the DOS field is not. Report whether they agree.
    stamp = f"{((mdate >> 9) & 0x7F) + 1980:04d}{(mdate >> 5) & 0x0F:02d}{mdate & 0x1F:02d}"
    if f"B{stamp}" in name:
        print(f"filename build date  B{stamp} — agrees with the DOS timestamp field")
    elif "-B" in name:
        print(f"filename build date  differs from the DOS timestamp field ({stamp})")

    present = len(blob) - data_off
    complete = present >= csize and blob.rfind(EOCD) >= 0
    print(f"compressed present   {present:,} of {csize:,} ({100.0 * present / csize:.1f}%)")
    print(f"central directory    {'present' if blob.rfind(EOCD) >= 0 else 'ABSENT — truncated'}")

    if method != 8:
        print("FATAL: only deflate is handled", file=sys.stderr)
        return 2

    d = zlib.decompressobj(-15)
    out = bytearray()
    try:
        out += d.decompress(blob[data_off:])
        out += d.flush()
    except zlib.error as e:
        print(f"deflate stopped      {e}")
    print(f"recovered            {len(out):,} of {usize:,} ({100.0 * len(out) / usize:.1f}%)")

    actual = binascii.crc32(bytes(out)) & 0xFFFFFFFF
    ok = actual == crc and len(out) == usize
    print(f"CRC-32 recovered     0x{actual:08x}  vs stored 0x{crc:08x}  "
          f"-> {'VERIFIED' if ok else 'MISMATCH'}")

    if ok and not complete:
        # Would mean the whole payload decompressed out of a file missing its
        # central directory. Possible, but it is the shape a bug makes, so say so.
        print("NOTE: CRC verified on an archive with no central directory")

    if args.output:
        if not ok and not args.allow_partial:
            print("refusing to write a payload that failed CRC verification; "
                  "pass --allow-partial if an incomplete recovery is the intent",
                  file=sys.stderr)
            return 1
        Path(args.output).write_bytes(bytes(out))
        state = "complete, CRC-verified" if ok else "INCOMPLETE — not the whole image"
        print(f"wrote                {args.output}  ({len(out):,} bytes, {state})")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
