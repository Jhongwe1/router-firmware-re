#!/usr/bin/env python3
"""Paint solid rectangles over regions of a photograph, irreversibly.

Used to remove unit-identifying labels — MAC address, serial number, QR code —
from photographs of my own hardware before they are committed. The rule this
enforces is in ``notes/img/README.md``: anything read off *this specific unit*
is redacted before it is committed; only what is true of *the model* is
published.

Deliberately opinionated:

* **Solid fill, never blur or pixelate.** A blur is a reversible transform on a
  known font; a filled rectangle destroys the information.
* **Re-encodes the whole image**, so no original JPEG coefficients survive for
  the painted region.
* **Drops EXIF**, which on a phone photograph carries GPS and a device id — a
  second identifier that survives every visual redaction.
* **Refuses to write over its input.** The unredacted original belongs in
  ``$FWRE_WORK``, outside the repository, not under an ``.orig`` suffix next to
  the file you are about to push.

Every guard below is an error, never a warning, and the result is verified by
reading the output back. **A redaction tool that can silently do nothing is
worse than no tool**, because it produces the belief that the job was done.

Usage:

    redact-photo.py IN OUT --box X,Y,W,H [--box ...] [--expect-size WxH]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover - environment problem, not logic
    sys.exit("error: Pillow is not installed (python3 -m pip install Pillow)")

FILL = (0, 0, 0)

# A box smaller than this is either a typo in the coordinates or an attempt to
# hide something that was never legible in the first place. Fixing it at 48 also
# means the read-back check below never needs a "box too small, skipping" branch
# — and a check with a skip path is a check that can quietly not run.
MIN_EDGE = 48

# JPEG minimum coded unit. Saved with subsampling=0 so it is 8x8 rather than
# 16x16; inset by twice that when verifying, so the sampled core is made only of
# blocks that lie wholly inside the painted region.
JPEG_MCU = 8
INSET = 2 * JPEG_MCU

# Ceiling for the whole box on read-back. A hard black rectangle re-encodes with
# ringing against its own edges, so "every pixel is exactly 0" is a condition a
# lossy format can never satisfy — this bound exists only to catch a box that
# landed somewhere completely wrong. The real guarantee is the core check.
EDGE_TOLERANCE = 96


class RedactionError(Exception):
    """Any condition under which the redaction must not be claimed to have run."""


def parse_box(text: str) -> tuple[int, int, int, int]:
    parts = text.split(",")
    if len(parts) != 4:
        raise RedactionError(f"--box wants X,Y,W,H — got {text!r}")
    try:
        x, y, w, h = (int(p) for p in parts)
    except ValueError as exc:
        raise RedactionError(f"--box {text!r}: {exc}") from exc
    if w < MIN_EDGE or h < MIN_EDGE:
        raise RedactionError(
            f"--box {text!r} is {w}x{h}; anything under {MIN_EDGE}px on an edge "
            "reads as a coordinate typo, not a redaction"
        )
    return x, y, w, h


def parse_size(text: str) -> tuple[int, int]:
    try:
        w, h = (int(p) for p in text.lower().split("x"))
    except ValueError as exc:
        raise RedactionError(f"--expect-size wants WxH — got {text!r}") from exc
    return w, h


def redact(
    src: Path,
    dst: Path,
    boxes: list[tuple[int, int, int, int]],
    expect_size: tuple[int, int] | None = None,
    quality: int = 92,
) -> tuple[int, int]:
    if not src.is_file():
        raise RedactionError(f"input does not exist: {src}")
    if dst.resolve() == src.resolve():
        raise RedactionError(
            "refusing to write over the input — keep the unredacted original "
            "outside the repository, in $FWRE_WORK"
        )
    if not boxes:
        raise RedactionError("no --box given; nothing would be redacted")

    with Image.open(src) as img:
        img = img.convert("RGB")
        width, height = img.size

        if expect_size is not None and (width, height) != expect_size:
            raise RedactionError(
                f"{src.name} is {width}x{height}, expected "
                f"{expect_size[0]}x{expect_size[1]} — the coordinates below were "
                "measured against a different image"
            )

        for x, y, w, h in boxes:
            if x < 0 or y < 0 or x + w > width or y + h > height:
                raise RedactionError(
                    f"box {x},{y},{w},{h} falls outside the {width}x{height} image"
                )

        draw = ImageDraw.Draw(img)
        for x, y, w, h in boxes:
            draw.rectangle([x, y, x + w - 1, y + h - 1], fill=FILL)

        # No exif= keyword: Pillow only writes EXIF that is passed in explicitly,
        # so the phone's GPS tag and device id do not reach the output.
        # subsampling=0 keeps the MCU at 8x8, which the read-back check relies on.
        img.save(dst, "JPEG", quality=quality, subsampling=0, optimize=True)

    # Post-condition, read back off disk rather than from the object still in
    # memory. This is what makes a silent no-op impossible — and it is written in
    # two parts, because a single "every pixel is exactly the fill colour" test
    # cannot pass on a lossy format and would therefore have to be deleted.
    with Image.open(dst) as out:
        out = out.convert("RGB")
        if out.size != (width, height):
            raise RedactionError("output geometry does not match the input")
        for x, y, w, h in boxes:
            worst = max(hi for _, hi in out.crop((x, y, x + w, y + h)).getextrema())
            if worst > EDGE_TOLERANCE:
                raise RedactionError(
                    f"box {x},{y},{w},{h} peaks at {worst}/255 in the written "
                    f"file, over the {EDGE_TOLERANCE} tolerance — that box did "
                    "not land where it was meant to"
                )
            core = out.crop((x + INSET, y + INSET, x + w - INSET, y + h - INSET))
            if core.getextrema() != ((0, 0), (0, 0), (0, 0)):
                raise RedactionError(
                    f"box {x},{y},{w},{h} is not solid at its core — "
                    "the redaction did not take"
                )
        if out.getexif():
            raise RedactionError("EXIF survived into the output")

    return width, height


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument(
        "--box",
        action="append",
        default=[],
        metavar="X,Y,W,H",
        help="region to paint out, in pixels; repeatable",
    )
    ap.add_argument(
        "--expect-size",
        metavar="WxH",
        help="fail unless the input has exactly these dimensions",
    )
    ap.add_argument("--quality", type=int, default=92)
    args = ap.parse_args(argv)

    try:
        boxes = [parse_box(b) for b in args.box]
        size = parse_size(args.expect_size) if args.expect_size else None
        w, h = redact(args.src, args.dst, boxes, size, args.quality)
    except RedactionError as exc:
        print(f"  FAIL  {exc}", file=sys.stderr)
        return 1

    covered = sum(bw * bh for _, _, bw, bh in boxes)
    print(
        f"  ok    {args.dst.name}: {len(boxes)} region(s), "
        f"{covered:,} px ({covered / (w * h):.2%} of frame) painted out, "
        f"EXIF dropped, verified on read-back"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
