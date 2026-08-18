#!/usr/bin/env python3
"""Build a flash image out of a published firmware container, and say exactly
which bytes came from where.

Why this exists
---------------
G4 clause 3 asks for a reproduction path that needs nothing but a downloadable
image.  W06 proved `boa` serves under `qemu-user`, but it proved it with *this
unit's* rootfs standing on *this unit's* flash dump -- a per-unit artefact no
stranger can obtain.  Swapping the rootfs is easy; the flash is the hard half,
because `/dev/mtdblock0` is not a thing the vendor ships.  A `.web` container
carries three regions and each one declares the flash offset it is burned to,
so most of a flash image can be reconstructed from the download alone.

*Most* is the operative word, and the point of this tool is to make the
remainder impossible to overlook.  Everything the container does not cover is
left `0xFF`, and the JSON report names every range and where it came from.  An
overlay -- a byte range supplied from a file rather than from the image -- is
recorded with its sha256 and a mandatory `--overlay-origin` string, so a reader
can tell "reconstructed from the published image" from "I pasted this in" at a
glance rather than by reading the build script.

The header question, which is not cosmetic
------------------------------------------
`notes/flash-layout.md` measured it on silicon: the 16-byte `IMG_HEADER_T` is
present in flash for `w6cg` and `cr6c`, and *absent* for the root filesystem,
which begins with its SquashFS superblock exactly at the partition boundary.
Get this wrong by 16 bytes and the boot loader still finds the kernel while the
rootfs fails to mount -- a failure that looks like a corrupt image rather than
an off-by-header.  `HEADERLESS_TAGS` encodes the measurement, and
`--verify-structure-against` re-checks it against a real dump instead of
trusting the constant.

This tool can fail, and the failures are the interesting part: overlapping
sections, a section that runs off the end of the flash, a container that claims
a byte below `FIRMWARE_FLOOR`, an overlay that collides with the image, a magic
that is not where the section table said it would be.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools" / "fwrecon" / "src"))

try:
    from fwrecon.rtlimage import HEADER_SIZE, parse
except ImportError as exc:  # pragma: no cover - environment problem, not logic
    sys.exit(f"mkflash: cannot import fwrecon ({exc}); try `make setup`")

DEFAULT_SIZE = 4 * 1024 * 1024
BLANK = 0xFF

# Measured, not assumed -- notes/flash-layout.md section 2. The rootfs is
# written to its partition without the container header; the other two keep it.
HEADERLESS_TAGS = frozenset({"r6cr"})

# Nothing a vendor container declares should land below this. On this family the
# first 64 KiB is boot loader, H601 (hardware setting: MACs and radio
# calibration) and the two configuration blocks -- all written at manufacture.
# A container that claims any of it is either a different product or a parse
# error, and both are worth stopping for.
FIRMWARE_FLOOR = 0x010000

EXPECTED_MAGIC = {
    "w6cg": b"w6cg",
    "cr6c": b"cr6c",
    "r6cr": b"hsqs",  # headerless: what lands is the SquashFS superblock
}


class BuildError(Exception):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _overlap(a_start: int, a_len: int, b_start: int, b_len: int) -> bool:
    return a_start < b_start + b_len and b_start < a_start + a_len


def _parse_overlay(spec: str) -> tuple[Path, int]:
    """`PATH@OFFSET`, offset in C-style hex or decimal. Split on the LAST '@'
    so a path containing '@' still works."""
    if "@" not in spec:
        raise BuildError(f"overlay {spec!r} has no @OFFSET")
    path_s, _, off_s = spec.rpartition("@")
    if not path_s:
        raise BuildError(f"overlay {spec!r} has an empty path")
    try:
        off = int(off_s, 0)
    except ValueError:
        raise BuildError(f"overlay {spec!r}: {off_s!r} is not a number") from None
    if off < 0:
        raise BuildError(f"overlay {spec!r}: negative offset")
    return Path(path_s), off


def build(
    image: Path,
    size: int,
    overlays: list[tuple[Path, int]],
    overlay_origin: str,
) -> tuple[bytearray, dict]:
    rep = parse(image)
    if not rep.sections:
        raise BuildError(f"{image}: no container sections recognised")

    flash = bytearray([BLANK]) * size
    raw = image.read_bytes()
    placed: list[dict] = []

    for sec in rep.sections:
        headerless = sec.tag in HEADERLESS_TAGS
        src_start = sec.payload_offset if headerless else sec.offset
        span = sec.payload_actual + (0 if headerless else HEADER_SIZE)
        blob = raw[src_start : src_start + span]
        if len(blob) != span:
            raise BuildError(
                f"section {sec.index} ({sec.tag}): container is short -- wanted "
                f"{span} bytes at file offset {src_start}, got {len(blob)}"
            )
        dst = sec.burn_addr
        if dst < FIRMWARE_FLOOR:
            raise BuildError(
                f"section {sec.index} ({sec.tag}) burns to {dst:#08x}, below the "
                f"{FIRMWARE_FLOOR:#08x} floor. That region is written at "
                f"manufacture (boot loader / H601 / config), so either this is "
                f"not an N150RT-family container or the header parse is wrong"
            )
        if dst + span > size:
            raise BuildError(
                f"section {sec.index} ({sec.tag}) needs {dst:#08x}..{dst + span:#08x} "
                f"but the flash is {size:#08x} bytes"
            )
        for prev in placed:
            if _overlap(dst, span, prev["flash_offset"], prev["length"]):
                raise BuildError(
                    f"section {sec.tag} at {dst:#08x}+{span} overlaps "
                    f"{prev['tag']} at {prev['flash_offset']:#08x}+{prev['length']}"
                )
        flash[dst : dst + span] = blob
        placed.append(
            {
                "tag": sec.tag,
                "flash_offset": dst,
                "flash_offset_hex": f"{dst:#08x}",
                "length": span,
                "header_in_flash": not headerless,
                "provenance": "published-image",
                "sha256": _sha256(blob),
            }
        )

    for path, off in overlays:
        blob = path.read_bytes()
        if not blob:
            raise BuildError(f"overlay {path} is empty")
        if off + len(blob) > size:
            raise BuildError(
                f"overlay {path} at {off:#08x} runs past the end of a "
                f"{size:#08x}-byte flash"
            )
        for prev in placed:
            if _overlap(off, len(blob), prev["flash_offset"], prev["length"]):
                raise BuildError(
                    f"overlay {path} at {off:#08x}+{len(blob)} collides with "
                    f"{prev['tag']} at {prev['flash_offset']:#08x}. An overlay may "
                    f"fill what the image does not cover, never overwrite it"
                )
        flash[off : off + len(blob)] = blob
        placed.append(
            {
                "tag": path.name,
                "flash_offset": off,
                "flash_offset_hex": f"{off:#08x}",
                "length": len(blob),
                "header_in_flash": None,
                "provenance": "overlay",
                "origin": overlay_origin,
                "sha256": _sha256(blob),
            }
        )

    placed.sort(key=lambda p: p["flash_offset"])

    # Self-check, and it must be able to fail: read the magic back out of the
    # buffer that was actually produced, not out of the section table that
    # produced it. Those are two different things and only one of them is the
    # artefact.
    for p in placed:
        want = EXPECTED_MAGIC.get(p["tag"])
        if want is None:
            continue
        got = bytes(flash[p["flash_offset"] : p["flash_offset"] + len(want)])
        if got != want:
            raise BuildError(
                f"self-check: expected {want!r} at {p['flash_offset']:#08x} for "
                f"{p['tag']}, found {got!r}"
            )

    covered = sum(p["length"] for p in placed)
    gaps = []
    cursor = 0
    for p in placed:
        if p["flash_offset"] > cursor:
            gaps.append(
                {
                    "start": cursor,
                    "start_hex": f"{cursor:#08x}",
                    "length": p["flash_offset"] - cursor,
                    "provenance": "blank (0xFF) -- in no published image",
                }
            )
        cursor = max(cursor, p["flash_offset"] + p["length"])
    if cursor < size:
        gaps.append(
            {
                "start": cursor,
                "start_hex": f"{cursor:#08x}",
                "length": size - cursor,
                "provenance": "blank (0xFF) -- in no published image",
            }
        )

    report = {
        "producer": "mkflash",
        "schema_version": "1",
        "container": str(image),
        "container_sha256": _sha256(raw),
        "flash_size": size,
        "covered_bytes": covered,
        "blank_bytes": size - covered,
        "ranges": placed,
        "gaps": gaps,
        "note": (
            "Every range marked published-image is reconstructed from the "
            "container named above and from nothing else. Ranges marked overlay "
            "are not in that container; their origin field says where they came "
            "from. Gaps are 0xFF and are in no published image."
        ),
    }
    return flash, report


def verify_structure(dump: Path, placed: list[dict]) -> list[str]:
    """Second source for the header model: check a real flash dump carries the
    same magic at the same burn addresses. Returns human-readable findings; an
    empty list means every image-derived range agreed."""
    data = dump.read_bytes()
    problems = []
    for p in placed:
        if p["provenance"] != "published-image":
            continue
        want = EXPECTED_MAGIC.get(p["tag"])
        if want is None:
            continue
        off = p["flash_offset"]
        got = data[off : off + len(want)]
        if got != want:
            problems.append(
                f"{dump.name}: expected {want!r} at {off:#08x} ({p['tag']}), "
                f"found {got!r} -- the header model in HEADERLESS_TAGS does not "
                f"describe this dump"
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Build a flash image from a published firmware container.",
        epilog="Ranges the container does not cover are left 0xFF and named in "
        "the JSON report. Use --overlay to fill them, and --overlay-origin to "
        "say where the filling came from.",
    )
    ap.add_argument("--image", required=True, type=Path, help="the .web container")
    ap.add_argument("--out", required=True, type=Path, help="flash image to write")
    ap.add_argument(
        "--size", type=lambda s: int(s, 0), default=DEFAULT_SIZE,
        help=f"flash size in bytes (default {DEFAULT_SIZE:#x})",
    )
    ap.add_argument(
        "--overlay", action="append", default=[], metavar="PATH@OFFSET",
        help="repeatable; splice a file in at a flash offset the image does not cover",
    )
    ap.add_argument(
        "--overlay-origin", default="",
        help="required with --overlay: one line saying where the overlay bytes "
        "came from, recorded in the report",
    )
    ap.add_argument("--json", type=Path, help="write the provenance report here")
    ap.add_argument(
        "--verify-structure-against", type=Path, metavar="DUMP",
        help="a real flash dump to check the header model against",
    )
    args = ap.parse_args(argv)

    if args.overlay and not args.overlay_origin.strip():
        ap.error(
            "--overlay requires --overlay-origin. An overlay is the one part of "
            "the image a stranger cannot reproduce from the download, so it does "
            "not go in unnamed"
        )

    try:
        overlays = [_parse_overlay(s) for s in args.overlay]
        for path, _ in overlays:
            if not path.is_file():
                raise BuildError(f"overlay {path} does not exist")
        flash, report = build(args.image, args.size, overlays, args.overlay_origin)
        if args.verify_structure_against:
            problems = verify_structure(args.verify_structure_against, report["ranges"])
            report["structure_verified_against"] = str(args.verify_structure_against)
            report["structure_problems"] = problems
            if problems:
                raise BuildError("\n       ".join(problems))
    except BuildError as exc:
        print(f"mkflash: {exc}", file=sys.stderr)
        return 1

    args.out.write_bytes(bytes(flash))
    report["out"] = str(args.out)
    report["out_sha256"] = _sha256(bytes(flash))
    if args.json:
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    pct = 100.0 * report["covered_bytes"] / report["flash_size"]
    print(f"wrote {args.out}  ({report['flash_size']} bytes)")
    for p in report["ranges"]:
        kind = p["provenance"]
        extra = f"  <- {p.get('origin')}" if kind == "overlay" else ""
        print(f"  {p['flash_offset_hex']}  {p['length']:>9}  {p['tag']:<12} {kind}{extra}")
    for g in report["gaps"]:
        print(f"  {g['start_hex']}  {g['length']:>9}  {'-':<12} blank 0xFF")
    print(f"  covered {report['covered_bytes']} of {report['flash_size']} ({pct:.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
