"""Validate a raw SPI flash image read off the device against what is already known.

Why this is not just ``binwalk`` on the dump
--------------------------------------------
``binwalk`` answers "what signatures are in this file". That is the wrong
question for a dump. The dump's job is to be *the same bytes as the chip*, and
signature scanning cannot fail in the way that matters: a read with a hole in
it, or a read from the wrong part, still contains a SquashFS somewhere and
still looks like a firmware image.

So this module checks the dump against expectations that were written down
**before** it existed, each carrying its own source:

  * W01 parsed the two vendor ``.web`` containers and derived where each section
    would be burned, three weeks before any hardware arrived
    (``notes/anatomy-n150rt.md``);
  * a console session on 2026-08-15 read 64-byte windows at chosen offsets
    through ``FLR``/``DB`` and recorded what was there
    (``notes/flash-layout.md``).

A check that agrees is corroboration. A check that disagrees is a finding - it
means the dump, the earlier reading, or the device changed, and which of those
it is has to be decided rather than assumed. Nothing here silently repairs
anything.

Two classes of check
--------------------
``hard``  structure that cannot legitimately differ between two reads of the
          same unit: boot code, container headers, the filesystem superblock.
          A mismatch means the dump is not trustworthy.
``soft``  the configuration blocks. ``COMPCS`` is the *live* configuration and
          the device rewrites it whenever anything is saved, so a difference
          there is information, not corruption.

What this module does not print
-------------------------------
``0x006000``-``0x010000`` holds this unit's MAC addresses, radio calibration and
live configuration. This module reports that those blocks are present, their
length, and their SHA-256 - never a byte of their content. A digest is enough to
answer "did the configuration change between two reads" without putting the
answer in a terminal log.

That behaviour is deliberately **unchanged** by the 2026-08-16 disclosure
decision, which publishes this particular unit's values. The decision was about
one device; this is a structural check that will be pointed at others. Reading
the configuration is what ``fwrecon compcs`` is for, and it takes an explicit
``--disclosure`` mode so that publishing is always something the caller asked
for rather than a default. See ``dumps/README.md`` and ``notes/compcs-decode.md``.
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field
from pathlib import Path

from .rtlimage import HEADER_SIZE, SquashfsInfo, _parse_squashfs

FLASH_SIZE = 4 * 1024 * 1024

# Per-unit secrets. Present in the image, never in the output.
SECRET_RANGES: tuple[tuple[int, int], ...] = ((0x006000, 0x010000),)

SRC_W01 = "W01: burnAddr parsed from the vendor .web containers (notes/anatomy-n150rt.md)"
SRC_CONSOLE = "2026-08-15 console session, FLR+DB windows (notes/flash-layout.md)"


@dataclass
class Check:
    name: str
    offset: int
    expected: str
    observed: str
    ok: bool
    kind: str  # "hard" or "soft"
    source: str


@dataclass
class FlashReport:
    path: str
    size: int
    sha256: str
    # Named so tools/check-reports.py can tell this apart from the other
    # producers writing into reports/, and so the file says what made it.
    producer: str = "fwrecon:flashdump"
    checks: list[Check] = field(default_factory=list)
    squashfs: SquashfsInfo | None = None
    image_end: int | None = None
    secret_regions: list[dict] = field(default_factory=list)
    gaps: list[dict] = field(default_factory=list)
    anomalies: list[str] = field(default_factory=list)
    self_check: str = "unknown"

    @property
    def failed_hard(self) -> list[Check]:
        return [c for c in self.checks if c.kind == "hard" and not c.ok]

    @property
    def failed_soft(self) -> list[Check]:
        return [c for c in self.checks if c.kind == "soft" and not c.ok]


def _hex(b: bytes) -> str:
    return " ".join(f"{x:02x}" for x in b)


def _add(rep: FlashReport, name: str, offset: int, expected, observed,
         kind: str, source: str) -> bool:
    ok = expected == observed
    rep.checks.append(Check(
        name=name, offset=offset,
        expected=_hex(expected) if isinstance(expected, bytes) else str(expected),
        observed=_hex(observed) if isinstance(observed, bytes) else str(observed),
        ok=ok, kind=kind, source=source,
    ))
    return ok


def _img_header(data: bytes, offset: int) -> tuple[bytes, int, int, int]:
    tag = data[offset:offset + 4]
    start, burn, length = struct.unpack_from(">3I", data, offset + 4)
    return tag, start, burn, length


def check_image(data: bytes, path: str = "-") -> FlashReport:
    rep = FlashReport(path=path, size=len(data),
                      sha256=hashlib.sha256(data).hexdigest())

    # ---- size -------------------------------------------------------------
    _add(rep, "flash size", 0, FLASH_SIZE, len(data), "hard",
         "EN25QH32B is 32 Mbit; W01 derived >= 4 MB from the container map "
         "against a published 2 MB specification")
    if len(data) < 0x200000:
        rep.anomalies.append("image is too short for any further check")
        rep.self_check = "SUSPECT"
        return rep

    # ---- the part is not a 2 MB part aliasing -----------------------------
    # The published specification says 2 MB. If it were, the upper half would be
    # an image of the lower one. This is the one check that tests the *part*
    # rather than the contents, and it needs no signature table to do it.
    half = len(data) // 2
    aliased = data[:half] == data[half:]
    _add(rep, "upper half is not an alias of the lower", half,
         "differ", "identical" if aliased else "differ", "hard",
         "the published 2 MB specification, tested rather than cited")

    # ---- boot code --------------------------------------------------------
    _add(rep, "boot code at 0x000000", 0x000000,
         bytes((0x0B, 0xF0, 0x00, 0x04)), data[0:4], "hard", SRC_CONSOLE)

    # ---- container headers ------------------------------------------------
    for off, tag, burn, length, start, extra in (
        (0x010000, b"w6cg", 0x010000, 0x043A14, None, b"BZh9"),
        (0x060000, b"cr6c", 0x060000, 0x0F1002, 0x80500000, None),
    ):
        got_tag, got_start, got_burn, got_len = _img_header(data, off)
        _add(rep, f"{tag.decode()} signature", off, tag, got_tag, "hard", SRC_W01)
        _add(rep, f"{tag.decode()} burnAddr", off, hex(burn), hex(got_burn), "hard", SRC_W01)
        _add(rep, f"{tag.decode()} length", off, length, got_len, "hard", SRC_CONSOLE)
        if start is not None:
            _add(rep, f"{tag.decode()} startAddr", off, hex(start), hex(got_start),
                 "hard", "the boot log's 'Jump to image start=0x80500000'")
        if extra is not None:
            _add(rep, f"{tag.decode()} payload magic", off + HEADER_SIZE,
                 extra, data[off + HEADER_SIZE:off + HEADER_SIZE + len(extra)],
                 "hard", SRC_CONSOLE)

    # ---- the root filesystem ---------------------------------------------
    sq_off = 0x180000
    _add(rep, "SquashFS magic", sq_off, b"hsqs", data[sq_off:sq_off + 4], "hard", SRC_W01)
    sq = _parse_squashfs(data, sq_off)
    rep.squashfs = sq
    if sq is not None:
        _add(rep, "SquashFS version", sq_off, "4.0", sq.version, "hard", SRC_CONSOLE)
        _add(rep, "SquashFS compression", sq_off, "lzma", sq.compression, "hard",
             SRC_CONSOLE + " - LZMA like the 2015 family, not XZ like 2020")
        _add(rep, "SquashFS inodes", sq_off, 567, sq.inodes, "hard", SRC_CONSOLE)
        _add(rep, "SquashFS bytes_used", sq_off, 0x1CA041, sq.bytes_used, "hard",
             SRC_CONSOLE)
        _add(rep, "SquashFS mkfs_time raw", sq_off, hex(0x80AD1C00),
             hex(sq.mkfs_time_raw), "hard",
             SRC_CONSOLE + " - a byte-swapped size, not a timestamp; three "
             "builds now carry it")
        rep.image_end = sq_off + sq.bytes_used
    else:
        rep.anomalies.append("no parseable SquashFS superblock at 0x180000")

    # ---- the tail is erased ----------------------------------------------
    # W02 read 0x350000 and 0x3F0000 as all-FF through the console. With the
    # whole part in hand the claim can be made about the whole tail instead of
    # two windows.
    if rep.image_end:
        tail_start = (rep.image_end + 0xFFFF) & ~0xFFFF
        tail = data[tail_start:]
        first_set = next((i for i, b in enumerate(tail) if b != 0xFF), None)
        _add(rep, f"tail from {tail_start:#08x} is erased", tail_start,
             "all 0xFF",
             "all 0xFF" if first_set is None
             else f"first non-FF byte at {tail_start + first_set:#08x}",
             "hard", "W02 read 0x350000 and 0x3F0000 as FF; this tests the whole tail")

    # ---- the gaps W02 assumed were padding -------------------------------
    # notes/flash-layout.md section 7: "The gaps at 0x053A24-0x05FFFF and
    # 0x151012-0x17FFFF are assumed to be padding to the next 64 KB boundary.
    # Not read." They are readable now, so the assumption gets tested.
    for lo, hi, what in (
        (0x010000 + HEADER_SIZE + 0x043A14, 0x060000, "after w6cg"),
        (0x060000 + HEADER_SIZE + 0x0F1002, 0x180000, "after cr6c"),
    ):
        if hi <= len(data) and lo < hi:
            blob = data[lo:hi]
            counts = {b: blob.count(bytes([b])) for b in (0x00, 0xFF)}
            rep.gaps.append({
                "from": lo, "to": hi, "bytes": hi - lo, "what": what,
                "ff_bytes": counts[0xFF], "zero_bytes": counts[0x00],
                "all_one_value": counts[0xFF] == len(blob) or counts[0x00] == len(blob),
                "sha256": hashlib.sha256(blob).hexdigest(),
            })

    # ---- per-unit secrets: presence and digest, never content -------------
    for lo, hi in SECRET_RANGES:
        blob = data[lo:hi]
        rep.secret_regions.append({
            "from": lo, "to": hi, "bytes": len(blob),
            "sha256": hashlib.sha256(blob).hexdigest(),
            "contains": "MAC addresses, radio calibration, COMPDS factory "
                        "defaults, COMPCS live configuration",
            "printed": False,
        })
    for off, magic, kind in (
        (0x006000, b"H601", "soft"),
        (0x008000, b"COMPDS", "soft"),
        (0x00C000, b"COMPCS", "soft"),
    ):
        _add(rep, f"{magic.decode()} present at {off:#08x}", off, magic,
             data[off:off + len(magic)], kind, SRC_CONSOLE)

    hard_failed = len(rep.failed_hard)
    rep.self_check = "OK" if hard_failed == 0 else "SUSPECT"
    return rep


def check_file(path: str | Path) -> FlashReport:
    p = Path(path)
    return check_image(p.read_bytes(), str(p))


def render_text(rep: FlashReport) -> str:
    out: list[str] = []
    out.append(f"flash dump : {rep.path}")
    out.append(f"size       : {rep.size} bytes ({rep.size / 1024 / 1024:.2f} MiB)")
    out.append(f"sha256     : {rep.sha256}")
    out.append("")
    width = max((len(c.name) for c in rep.checks), default=10)
    for c in rep.checks:
        mark = " ok " if c.ok else "FAIL"
        out.append(f"  [{mark}] {c.name:<{width}}  {c.observed}"
                   + ("" if c.ok else f"   (expected {c.expected})"))
    out.append("")
    if rep.squashfs:
        s = rep.squashfs
        out.append(f"rootfs     : SquashFS {s.version}, {s.compression}, "
                   f"{s.inodes} inodes, {s.bytes_used} bytes used")
    if rep.image_end:
        out.append(f"image ends : {rep.image_end:#08x} "
                   f"({rep.image_end / 1024 / 1024:.2f} MiB)")
    for g in rep.gaps:
        state = "one repeated value" if g["all_one_value"] else "MIXED CONTENT"
        out.append(f"gap {g['what']:<12} {g['from']:#08x}-{g['to']:#08x} "
                   f"{g['bytes']:>7} bytes  {state}")
    for r in rep.secret_regions:
        out.append(f"withheld   : {r['from']:#08x}-{r['to']:#08x} "
                   f"({r['bytes']} bytes) sha256 {r['sha256'][:16]}... "
                   "- content never printed")
    for a in rep.anomalies:
        out.append(f"anomaly    : {a}")
    out.append("")
    out.append(f"self_check : {rep.self_check}"
               + (f"  ({len(rep.failed_hard)} hard checks failed)"
                  if rep.failed_hard else ""))
    if rep.failed_soft:
        out.append("             soft mismatches are configuration, not corruption: "
                   + ", ".join(c.name for c in rep.failed_soft))
    return "\n".join(out)
