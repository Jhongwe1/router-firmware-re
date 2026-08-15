#!/usr/bin/env python3
"""Render an annotated copy of a photograph from a committed JSON spec.

G2 asks for an *annotated* PCB photograph. Doing that in an image editor
produces a file nobody can check, diff, or regenerate after the source photo is
retaken — the same objection this project raised against Ghidra screenshots in
W03, and the same answer: put the annotation in a text file and generate the
picture from it.

So the callouts live in ``notes/img/*-annotations.json`` and this script renders
them. The spec is reviewable, a moved box shows up in ``git diff`` as a changed
number, and anyone can re-render against the original photograph to confirm the
labels point where the note claims they point.

The rendered legend sits in a strip appended *below* the frame rather than over
it, so no annotation can ever hide part of the evidence it is describing.

Spec format::

    {
      "source": "03-pcb-top-redacted.jpg",
      "expect_size": "2048x1536",
      "title": "...",
      "subtitle": "...",
      "boxes": [ {"x": 970, "y": 620, "w": 275, "h": 285, "label": "..."} ]
    }

Usage:

    annotate-photo.py SPEC.json OUT.jpg
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - environment problem, not logic
    sys.exit("error: Pillow is not installed (python3 -m pip install Pillow)")

ACCENT = (255, 212, 0)
ACCENT_INK = (0, 0, 0)
LEGEND_BG = (17, 17, 17)
LEGEND_INK = (238, 238, 238)

STROKE = 5
MIN_EDGE = 24
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")


class AnnotationError(Exception):
    """Any condition under which the render must not be claimed to have run."""


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONT_DIR / name
    if not path.is_file():
        raise AnnotationError(
            f"font not found: {path} (apt install fonts-dejavu-core). Refusing "
            "to fall back to Pillow's bitmap font, which is illegible at this scale"
        )
    return ImageFont.truetype(str(path), size)


def load_spec(path: Path) -> dict:
    if not path.is_file():
        raise AnnotationError(f"spec does not exist: {path}")
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AnnotationError(f"{path.name}: {exc}") from exc

    for key in ("source", "expect_size", "title", "boxes"):
        if key not in spec:
            raise AnnotationError(f"{path.name}: missing required key {key!r}")
    if not spec["boxes"]:
        raise AnnotationError(f"{path.name}: 'boxes' is empty; nothing to annotate")

    labels = [b.get("label", "") for b in spec["boxes"]]
    if not all(labels):
        raise AnnotationError(f"{path.name}: every box needs a non-empty 'label'")
    if len(set(labels)) != len(labels):
        raise AnnotationError(f"{path.name}: two boxes carry the same label")
    return spec


def render(spec_path: Path, dst: Path) -> tuple[int, int, int]:
    spec = load_spec(spec_path)
    src = spec_path.parent / spec["source"]
    if not src.is_file():
        raise AnnotationError(f"source image does not exist: {src}")
    if dst.resolve() == src.resolve():
        raise AnnotationError("refusing to write over the source photograph")

    want_w, want_h = (int(v) for v in spec["expect_size"].lower().split("x"))

    with Image.open(src) as base:
        base = base.convert("RGB")
        width, height = base.size
        if (width, height) != (want_w, want_h):
            raise AnnotationError(
                f"{src.name} is {width}x{height}, spec declares {want_w}x{want_h} "
                "— the box coordinates were measured against a different image"
            )

        boxes = spec["boxes"]
        for i, b in enumerate(boxes, 1):
            x, y, w, h = (int(b[k]) for k in ("x", "y", "w", "h"))
            if w < MIN_EDGE or h < MIN_EDGE:
                raise AnnotationError(f"box {i} is {w}x{h}; under the {MIN_EDGE}px minimum")
            if x < 0 or y < 0 or x + w > width or y + h > height:
                raise AnnotationError(
                    f"box {i} ({x},{y},{w},{h}) falls outside the {width}x{height} frame"
                )

        f_badge = font("DejaVuSans-Bold.ttf", 44)
        f_title = font("DejaVuSans-Bold.ttf", 46)

        pad = 32
        num_gap = 52
        probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))

        # Lay the legend out so that it demonstrably fits: try two columns, fall
        # back to one, and shrink the type until the longest label clears the
        # frame. This ends in an error rather than a best effort, because a
        # legend that overprints itself still *looks* like a finished figure —
        # which is the worst thing a tool can hand you.
        layout = None
        for cols in (2, 1):
            gutter = pad if cols > 1 else 0
            avail = (width - 2 * pad) // cols - num_gap - gutter
            for size in range(38, 17, -2):
                f_item = font("DejaVuSans.ttf", size)
                widest = max(probe.textlength(b["label"], font=f_item) for b in boxes)
                if widest <= avail:
                    layout = (cols, (len(boxes) + cols - 1) // cols, f_item, size)
                    break
            if layout:
                break
        if layout is None:
            raise AnnotationError(
                f"{len(boxes)} labels will not fit in {width}px even at the "
                "smallest size tried — shorten them, or split the figure"
            )
        cols, rows, f_item, item_size = layout
        line = item_size + 16

        sub_size = 0
        f_sub = None
        if spec.get("subtitle"):
            for sub_size in range(30, 15, -2):
                f_sub = font("DejaVuSans.ttf", sub_size)
                if probe.textlength(spec["subtitle"], font=f_sub) <= width - 2 * pad:
                    break
            else:
                raise AnnotationError("subtitle will not fit on one line")

        legend_h = pad + 60 + (sub_size + 18 if f_sub else 0) + rows * line + pad

        canvas = Image.new("RGB", (width, height + legend_h), LEGEND_BG)
        canvas.paste(base, (0, 0))
        draw = ImageDraw.Draw(canvas)

        for i, b in enumerate(boxes, 1):
            x, y, w, h = (int(b[k]) for k in ("x", "y", "w", "h"))
            draw.rectangle([x, y, x + w, y + h], outline=ACCENT, width=STROKE)
            tag = str(i)
            tw = draw.textlength(tag, font=f_badge)
            bw, bh = int(tw) + 26, 56
            # Keep the badge inside the frame even for a box at the top edge.
            by = y - bh if y - bh >= 0 else y
            bx = min(x, width - bw)
            draw.rectangle([bx, by, bx + bw, by + bh], fill=ACCENT)
            draw.text((bx + 13, by + 4), tag, font=f_badge, fill=ACCENT_INK)

        ty = height + pad
        draw.text((pad, ty), spec["title"], font=f_title, fill=LEGEND_INK)
        ty += 60
        if f_sub:
            draw.text((pad, ty), spec["subtitle"], font=f_sub, fill=(150, 150, 150))
            ty += sub_size + 18

        col_w = (width - 2 * pad) // cols
        placed = []
        for i, b in enumerate(boxes):
            cx = pad + (i // rows) * col_w
            cy = ty + (i % rows) * line
            placed.append((i, cx, cy, b["label"]))

        # Post-condition on the layout, checked before a single pixel is drawn.
        for i, cx, _, label in placed:
            right = cx + num_gap + probe.textlength(label, font=f_item)
            if right > width - pad:
                raise AnnotationError(
                    f"legend entry {i + 1} would run {int(right - (width - pad))}px "
                    f"off the frame: {label!r}"
                )
        if ty + rows * line > height + legend_h - pad + 1:
            raise AnnotationError("legend is taller than the strip reserved for it")

        for i, cx, cy, label in placed:
            draw.text((cx, cy), f"{i + 1}", font=f_item, fill=ACCENT)
            draw.text((cx + num_gap, cy), label, font=f_item, fill=LEGEND_INK)

        canvas.save(dst, "JPEG", quality=88, subsampling=0, optimize=True)

    with Image.open(dst) as out:
        if out.size != (width, height + legend_h):
            raise AnnotationError("rendered geometry does not match what was computed")

    return width, height + legend_h, len(boxes)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    try:
        w, h, n = render(Path(argv[0]), Path(argv[1]))
    except AnnotationError as exc:
        print(f"  FAIL  {exc}", file=sys.stderr)
        return 1
    print(f"  ok    {Path(argv[1]).name}: {n} callouts, {w}x{h}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
