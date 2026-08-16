"""Command-line entry point for fwrecon."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import compcs as compcsmod
from . import diff as diffmod
from . import elf, flashdump, mibtable, report, rootfs, rtlimage

__version__ = "0.1.0"


def _write(text: str, out: str | None) -> None:
    if out:
        p = Path(out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, "utf-8")
        print(f"wrote {p}", file=sys.stderr)
    else:
        sys.stdout.write(text)


def cmd_image(args) -> int:
    rep = rtlimage.parse(args.image)
    if args.json:
        _write(json.dumps(rep, default=lambda o: o.__dict__, indent=2), args.output)
        return 0
    print(f"{rep.path}  ({rep.size:,} bytes)")
    print(f"{'#':>2}  {'tag':<6} {'file off':>10} {'flash off':>10} "
          f"{'ram addr':>10} {'length':>12}  payload")
    for s in rep.sections:
        print(f"{s.index:>2}  {s.tag:<6} 0x{s.offset:08x} 0x{s.burn_addr:08x} "
              f"0x{s.start_addr:08x} {s.length:>12,}  {s.payload_type}")
        for f in s.inner_findings:
            print(f"      inner: {f}")
        if s.squashfs:
            q = s.squashfs
            print(f"      squashfs v{q.version} {q.compression} "
                  f"inodes={q.inodes} block={q.block_size} used={q.bytes_used:,}")
            for x in q.anomalies:
                print(f"      ! {x}")
        for x in s.anomalies:
            print(f"      ! {x}")
    if rep.trailer:
        print(f"trailer @0x{rep.trailer_offset:x}: {rep.trailer!r}")
    if rep.min_flash_size:
        print(f"minimum flash size implied: {rep.min_flash_size:,} bytes "
              f"({rep.min_flash_size / 1048576:.2f} MiB)")
    for x in rep.anomalies:
        print(f"! {x}")
    return 0


def cmd_elf(args) -> int:
    r = elf.analyse(args.path)
    if not r.is_elf:
        print(f"{args.path}: not an ELF32 ({r.error})", file=sys.stderr)
        return 1
    if args.json:
        _write(json.dumps(r, default=lambda o: o.__dict__, indent=2), args.output)
        return 0
    print(f"{r.path}")
    print(f"  type          {r.type}  {r.machine} {r.mips_isa or ''} "
          f"{r.mips_abi or ''} ({r.endian}-endian)")
    print(f"  entry         0x{r.entry:08x}   load base 0x{r.load_base:08x}")
    print(f"  interpreter   {r.interpreter}")
    print(f"  sections      {'present' if r.section_headers else 'STRIPPED (sstrip)'}")
    print(f"  needed        {', '.join(r.needed) or '-'}")
    h = r.hardening
    if h:
        nx = {None: "absent (exec stack)", True: "yes", False: "no"}[h.nx]
        print(f"  hardening     NX={nx}  PIE={h.pie}  RELRO={h.relro}  "
              f"canary={h.canary}  fortify={h.fortify}")
        if h.rwx_segments:
            print(f"                RWX segments: {', '.join(h.rwx_segments)}")
    for kind, names in r.sinks.items():
        print(f"  {kind:<24} {', '.join(names)}")
    print(f"  imports       {len(r.imports)}   exports {len(r.exports)}")
    return 0


def cmd_rootfs(args) -> int:
    rr = rootfs.analyse(args.root, label=args.label or "")
    rep = report.build(args.label or Path(args.root).name, rootfs=rr)
    _emit(rep, args)
    return 0


def cmd_report(args) -> int:
    img = rtlimage.parse(args.image) if args.image else None
    rr = rootfs.analyse(args.rootfs, label=args.label or "") if args.rootfs else None
    if img is None and rr is None:
        print("need at least --image or --rootfs", file=sys.stderr)
        return 2
    rep = report.build(args.label or "unnamed", image=img, rootfs=rr)
    _emit(rep, args)
    return 0


def cmd_mib(args) -> int:
    t = mibtable.analyse(args.path)
    if args.format == "json":
        _write(json.dumps(t, default=lambda o: o.__dict__, indent=2), args.output)
    else:
        _write(mibtable.to_markdown(t), args.output)
    # A SUSPECT recovery exits non-zero on purpose: this table is used to name
    # ids in the notes, and a table that failed its own anchor check must not be
    # quoted from just because it printed something.
    return 0 if t.verdict == "consistent" else 1


def cmd_flashdump(args) -> int:
    rep = flashdump.check_file(args.image)
    if args.format == "json":
        _write(json.dumps(rep, default=lambda o: o.__dict__, indent=2), args.output)
    else:
        _write(flashdump.render_text(rep) + "\n", args.output)
    # A dump whose hard checks failed exits non-zero, for the same reason `mib`
    # does: this image is about to be the source for every W05/W06 claim about
    # this unit, and one that disagrees with what the device said yesterday must
    # not be quoted from just because it produced a file.
    return 0 if rep.self_check == "OK" else 1


def cmd_compcs(args) -> int:
    mib = mibtable.analyse(args.mib) if args.mib else None
    try:
        cfg = compcsmod.decode_file(
            args.image, int(args.offset, 0), mib=mib, disclosure=args.disclosure)
    except compcsmod.CompcsError as exc:
        # Printed, not raised as a traceback, and non-zero. A config decoder that
        # returns something plausible when it is wrong is the single worst tool
        # this project could own: every downstream claim would be about a table
        # that does not exist.
        print(f"fwrecon compcs: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        _write(json.dumps(cfg, default=lambda o: o.__dict__, indent=2), args.output)
    else:
        _write(compcsmod.to_markdown(cfg), args.output)
    return 0 if cfg.verdict == "consistent" else 1


def _emit(rep, args) -> None:
    if args.format == "json":
        _write(report.to_json(rep), args.output)
    else:
        _write(report.to_markdown(rep), args.output)


def cmd_diff(args) -> int:
    d = diffmod.compare(args.old, args.new)
    if args.format == "json":
        _write(json.dumps(d, indent=2), args.output)
    else:
        _write(diffmod.to_markdown(d), args.output)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fwrecon",
        description="Structured reconnaissance for Realtek-SDK router firmware.")
    p.add_argument("--version", action="version", version=f"fwrecon {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("image", help="parse a Realtek .web container")
    pi.add_argument("image")
    pi.add_argument("--json", action="store_true")
    pi.add_argument("-o", "--output")
    pi.set_defaults(func=cmd_image)

    pe = sub.add_parser("elf", help="inspect one ELF32 binary")
    pe.add_argument("path")
    pe.add_argument("--json", action="store_true")
    pe.add_argument("-o", "--output")
    pe.set_defaults(func=cmd_elf)

    pr = sub.add_parser("rootfs", help="inventory an unpacked root filesystem")
    pr.add_argument("root")
    pr.add_argument("--label")
    pr.add_argument("-f", "--format", choices=("json", "md"), default="md")
    pr.add_argument("-o", "--output")
    pr.set_defaults(func=cmd_rootfs)

    pf = sub.add_parser("report", help="full report: container + rootfs")
    pf.add_argument("--image")
    pf.add_argument("--rootfs")
    pf.add_argument("--label")
    pf.add_argument("-f", "--format", choices=("json", "md"), default="json")
    pf.add_argument("-o", "--output")
    pf.set_defaults(func=cmd_report)

    pm = sub.add_parser("mib", help="recover the APMIB id/name table from libapmib.so")
    pm.add_argument("path")
    pm.add_argument("-f", "--format", choices=("json", "md"), default="md")
    pm.add_argument("-o", "--output")
    pm.set_defaults(func=cmd_mib)

    px = sub.add_parser(
        "flashdump",
        help="check a raw SPI flash image against what was known before it existed")
    px.add_argument("image")
    px.add_argument("-f", "--format", choices=("json", "text"), default="text")
    px.add_argument("-o", "--output")
    px.set_defaults(func=cmd_flashdump)

    pc = sub.add_parser(
        "compcs",
        help="decode an APMIB config region (COMPCS/COMPDS/COMPHS) out of a flash image")
    pc.add_argument("image")
    pc.add_argument("--offset", required=True,
                    help="region offset, e.g. 0x00C000 for the live configuration")
    pc.add_argument("--mib", help="mib-table JSON or libapmib.so, to name the ids")
    pc.add_argument("--disclosure", choices=("open", "protect"), default="open",
                    help="protect replaces per-unit identifiers with a digest")
    pc.add_argument("-f", "--format", choices=("json", "md"), default="md")
    pc.add_argument("-o", "--output")
    pc.set_defaults(func=cmd_compcs)

    pd = sub.add_parser("diff", help="diff two report JSON files")
    pd.add_argument("old")
    pd.add_argument("new")
    pd.add_argument("-f", "--format", choices=("json", "md"), default="md")
    pd.add_argument("-o", "--output")
    pd.set_defaults(func=cmd_diff)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
