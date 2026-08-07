"""Report assembly: one machine-readable object, two renderings.

JSON is the product. Markdown is a view of it. Keeping that order matters —
if the Markdown were the product, every downstream question ("which handlers
appeared between these two builds?") would mean re-parsing prose.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .rootfs import RootfsReport
from .rtlimage import ImageReport

SCHEMA_VERSION = "1.0"


@dataclass
class FirmwareReport:
    schema_version: str = SCHEMA_VERSION
    generated_at_utc: str = ""
    label: str = ""
    image_file: str | None = None
    image_sha256: str | None = None
    image: ImageReport | None = None
    rootfs: RootfsReport | None = None
    findings: list[dict] = field(default_factory=list)


def sha256_file(path: str | Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def build(label: str,
          image: ImageReport | None = None,
          rootfs: RootfsReport | None = None) -> FirmwareReport:
    rep = FirmwareReport(
        generated_at_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        label=label,
        image=image,
        rootfs=rootfs,
    )
    if image:
        rep.image_file = image.path
        rep.image_sha256 = sha256_file(image.path)
    rep.findings = derive_findings(rep)
    return rep


def derive_findings(rep: FirmwareReport) -> list[dict]:
    """Turn raw inventory into ranked, human-meaningful observations.

    These are *observations about the image*, not vulnerability claims. Every
    one of them is a structural fact that can be checked from the JSON; whether
    a given fact is exploitable is decided later, by reversing the binary, not
    here. Keeping that boundary sharp is what stops an inventory tool from
    turning into a false-positive generator.
    """
    out: list[dict] = []
    rf, img = rep.rootfs, rep.image

    if rf:
        for link in rf.suspect_symlinks:
            if link.in_docroot:
                out.append({
                    "severity": "high",
                    "kind": "web-exposed-runtime-file",
                    "detail": f"{link.path} -> {link.target}",
                    "why": link.reason,
                })

        if rf.disabled_services:
            out.append({
                "severity": "medium",
                "kind": "service-disabled-not-removed",
                "detail": ", ".join(rf.disabled_services),
                "why": "init line commented out, binary still present in the image",
            })

        n_exec = len(rf.command_exec_binaries)
        if n_exec:
            out.append({
                "severity": "info",
                "kind": "command-exec-surface",
                "detail": f"{n_exec} binaries import system()/popen()/exec*()",
                "why": "each is a place where attacker-influenced data could reach a shell",
            })

        no_nx = [b.path for b in rf.binaries if (b.hardening or {}).get("nx") is None]
        if no_nx:
            out.append({
                "severity": "info",
                "kind": "no-nx-marker",
                "detail": f"{len(no_nx)} binaries have no PT_GNU_STACK segment",
                "why": "toolchain predates the marker, so the kernel maps the stack "
                       "executable; memory-corruption bugs need no ROP chain",
            })
        rwx = [b.path for b in rf.binaries if (b.hardening or {}).get("rwx_segments")]
        if rwx:
            out.append({
                "severity": "low",
                "kind": "rwx-segment",
                "detail": ", ".join(rwx[:8]),
                "why": "a writable and executable LOAD segment",
            })

        if rf.web_server and rf.handlers:
            out.append({
                "severity": "info",
                "kind": "web-handler-surface",
                "detail": f"{len(rf.handlers)} form handlers in {rf.web_server}",
                "why": "each handler parses request parameters and is a candidate "
                       "entry point",
            })

    if img:
        for sec in img.sections:
            for a in sec.anomalies:
                out.append({"severity": "low", "kind": "image-anomaly",
                            "detail": f"section {sec.tag}: {a}", "why": "structural"})
            if sec.squashfs:
                for a in sec.squashfs.anomalies:
                    out.append({"severity": "info", "kind": "squashfs-anomaly",
                                "detail": a, "why": "filesystem metadata"})
        if img.min_flash_size:
            out.append({
                "severity": "info",
                "kind": "flash-size-lower-bound",
                "detail": f"image requires at least {img.min_flash_size} bytes "
                          f"({img.min_flash_size / 1024 / 1024:.2f} MiB) of flash",
                "why": "highest burnAddr + length across sections; use this to "
                       "sanity-check the part marking before dumping",
            })

    order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    out.sort(key=lambda f: order.get(f["severity"], 9))
    return out


def to_dict(rep: FirmwareReport) -> dict:
    return dataclasses.asdict(rep)


def to_json(rep: FirmwareReport, indent: int = 2) -> str:
    return json.dumps(to_dict(rep), indent=indent, sort_keys=False, default=str)


# ---------------------------------------------------------------- markdown

def _table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_none_\n"
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out) + "\n"


def to_markdown(rep: FirmwareReport) -> str:
    L: list[str] = []
    a = L.append

    a(f"# Firmware recon — {rep.label}\n")
    a(f"_Generated {rep.generated_at_utc} by fwrecon schema {rep.schema_version}._\n")
    if rep.image_file:
        a(f"- **Image:** `{Path(rep.image_file).name}`")
        a(f"- **SHA-256:** `{rep.image_sha256}`\n")

    if rep.findings:
        a("## Observations\n")
        a(_table(["Severity", "Kind", "Detail", "Why it matters"],
                 [[f["severity"], f["kind"], f["detail"], f["why"]]
                  for f in rep.findings]))

    img = rep.image
    if img:
        a("## Container layout\n")
        a(f"`{Path(img.path).name}` — {img.size:,} bytes, "
          f"{len(img.sections)} section(s).\n")
        a(_table(
            ["#", "Tag", "Description", "File off", "Flash off", "RAM addr",
             "Length", "Payload"],
            [[s.index, f"`{s.tag}`", s.description, f"0x{s.offset:x}",
              f"0x{s.burn_addr:06x}", f"0x{s.start_addr:08x}",
              f"{s.length:,}", s.payload_type] for s in img.sections]))
        if img.trailer:
            a(f"\n**Trailer** at `0x{img.trailer_offset:x}`: `{img.trailer}`\n")
        for s in img.sections:
            if s.inner_findings:
                a(f"\nInside `{s.tag}`: {', '.join(s.inner_findings)}\n")
            if s.squashfs:
                q = s.squashfs
                a(f"\n**SquashFS** in `{s.tag}`: v{q.version}, {q.compression}, "
                  f"{q.inodes:,} inodes, {q.block_size:,} B blocks, "
                  f"{q.bytes_used:,} bytes used.\n")
        if img.min_flash_size:
            a(f"\n**Minimum flash size implied by the flash map:** "
              f"{img.min_flash_size:,} bytes "
              f"({img.min_flash_size / 1024 / 1024:.2f} MiB)\n")
        if img.anomalies:
            a("\n**Image anomalies**\n")
            for x in img.anomalies:
                a(f"- {x}")
            a("")

    rf = rep.rootfs
    if rf:
        a("## Root filesystem\n")
        a(f"- Path: `{rf.root}`")
        a(f"- {rf.file_count:,} files, {rf.dir_count:,} dirs, "
          f"{rf.symlink_count:,} symlinks, {rf.total_bytes:,} bytes")
        a(f"- Web server: `{rf.web_server}` ({rf.web_server_banner or 'no banner'})")
        a(f"- DocumentRoot: `{rf.document_root}`")
        a(f"- ELF binaries: {len(rf.binaries)}\n")

        if rf.suspect_symlinks:
            a("### Symlinks that escape the read-only image\n")
            a(_table(["Path", "Target", "Why flagged"],
                     [[f"`{s.path}`", f"`{s.target}`", s.reason]
                      for s in rf.suspect_symlinks]))

        if rf.handlers:
            a(f"### Web handlers ({len(rf.handlers)})\n")
            a("Extracted from `" + str(rf.handler_source) + "`. Reachable as "
              "`/boafrm/<name>`.\n")
            a("```")
            line = ""
            for h in rf.handlers:
                if len(line) + len(h) > 92:
                    a(line.rstrip())
                    line = ""
                line += h + "  "
            if line:
                a(line.rstrip())
            a("```\n")

        if rf.command_exec_binaries:
            a(f"### Binaries reaching a command-execution sink "
              f"({len(rf.command_exec_binaries)})\n")
            a("```")
            for p in rf.command_exec_binaries:
                a(p)
            a("```\n")

        if rf.init_findings:
            a("### Init-script service references\n")
            a(_table(["File", "Line", "Enabled", "Statement"],
                     [[f"`{f.file}`", f.line_no,
                       "no (commented)" if f.commented else "yes", f"`{f.line}`"]
                      for f in rf.init_findings]))

        if rf.credential_files:
            a("### Credential-shaped files\n```")
            for c in rf.credential_files:
                a(c)
            a("```\n")

        if rf.setuid_files:
            a("### setuid/setgid\n```")
            for s in rf.setuid_files:
                a(s)
            a("```\n")

        if rf.notes:
            a("### Notes\n")
            for n in rf.notes:
                a(f"- {n}")
            a("")

        a("### Binary hardening\n")
        a(_table(
            ["Binary", "Endian", "Machine", "Load base", "Sections", "NX",
             "Canary", "RELRO", "Sinks"],
            [[f"`{b.path}`", b.endian, b.machine, b.load_base,
              "stripped" if b.stripped_sections else "present",
              {None: "absent", True: "yes", False: "no"}[b.hardening.get("nx")],
              "yes" if b.hardening.get("canary") else "no",
              b.hardening.get("relro", "?"),
              ", ".join(f"{k}:{len(v)}" for k, v in b.sinks.items()) or "-"]
             for b in rf.binaries]))

    return "\n".join(L) + "\n"
