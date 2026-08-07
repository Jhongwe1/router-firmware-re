"""Attack-surface inventory for an unpacked embedded root filesystem.

The questions this answers are the ones you would otherwise re-type as a dozen
ad-hoc ``find | grep`` pipelines every time you look at a new image — and,
more importantly, the ones it is easy to forget to ask on the fourth image when
you remembered on the first:

  * which binaries reach a command-execution or unbounded-copy sink;
  * which HTTP handlers the web server exposes;
  * which paths in the read-only filesystem are symlinks pointing at writable
    storage (this is how a router leaks its own config file out of the docroot);
  * what the init scripts start, and what was *commented out* rather than removed.

That last one is not pedantry. In the 2015 N150RT image, ``/etc/init.d/rcS``
contains ``#skt&`` — the backdoor service disabled by commenting out one line,
with ``/bin/skt`` still shipped in the filesystem. A tool that only reports what
runs would have called that image clean.
"""

from __future__ import annotations

import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path

from . import elf

# Boa-based Realtek firmware dispatches POST bodies to handlers named formXxx /
# fromXxx (the latter is a vendor typo that shipped, and is itself a CVE'd
# endpoint - see /boafrm/fromStaticDHCP), reachable under /boafrm/<name>.
HANDLER_RE = re.compile(rb"\b((?:form|from)[A-Za-z][A-Za-z0-9_]{2,40})\b")

# Words that are not handlers but match the pattern.
HANDLER_STOPWORDS = {
    "format", "formatted", "formatting", "formats", "former", "formerly",
    "formal", "formula", "fromPort", "formfeed",
}

CREDENTIAL_FILENAMES = re.compile(
    r"^(passwd|shadow|group|gshadow|.*\.pem|.*\.key|.*\.crt|.*\.cer|"
    r".*\.p12|.*_rsa|.*_dsa|authorized_keys|.*\.dat)$", re.I)

INIT_SCRIPT_GLOBS = ("etc/init.d/*", "etc/rc.d/*", "etc/inittab", "init",
                     "etc/rc.local", "etc/profile", "bin/init.sh")

# Services whose presence or absence changes the exposure story.
SERVICE_MARKERS = re.compile(
    r"\b(telnetd?|utelnetd|dropbear|sshd|ftpd|tftpd?|skt|boa|httpd|lighttpd|"
    r"upnpd?|miniigd|cwmpClient|tr069|snmpd)\b")


def iter_strings(data: bytes, min_len: int = 4):
    """A ``strings(1)`` equivalent, kept in-process so results are stable and
    the tool has no runtime dependency on binutils."""
    run = bytearray()
    for byte in data:
        if 0x20 <= byte < 0x7F:
            run.append(byte)
            continue
        if len(run) >= min_len:
            yield run.decode("ascii")
        run.clear()
    if len(run) >= min_len:
        yield run.decode("ascii")


@dataclass
class BinaryEntry:
    path: str
    size: int
    mode: str
    endian: str
    machine: str
    load_base: str
    entry: str
    stripped_sections: bool
    needed: list[str]
    sinks: dict[str, list[str]]
    hardening: dict


@dataclass
class SuspectSymlink:
    path: str
    target: str
    reason: str
    # True only when the link sits inside the web document root. That subset is
    # the one that turns runtime state into a downloadable URL; the rest
    # (/etc -> /var, udhcpc hooks) are ordinary read-only-rootfs plumbing and
    # would drown the signal if ranked the same.
    in_docroot: bool = False


@dataclass
class InitFinding:
    file: str
    line_no: int
    line: str
    commented: bool


@dataclass
class RootfsReport:
    root: str
    label: str = ""
    file_count: int = 0
    dir_count: int = 0
    symlink_count: int = 0
    total_bytes: int = 0

    web_server: str | None = None
    web_server_banner: str | None = None
    document_root: str | None = None

    handlers: list[str] = field(default_factory=list)
    handler_source: str | None = None

    binaries: list[BinaryEntry] = field(default_factory=list)
    command_exec_binaries: list[str] = field(default_factory=list)

    suspect_symlinks: list[SuspectSymlink] = field(default_factory=list)
    setuid_files: list[str] = field(default_factory=list)
    world_writable: list[str] = field(default_factory=list)
    credential_files: list[str] = field(default_factory=list)

    init_findings: list[InitFinding] = field(default_factory=list)
    disabled_services: list[str] = field(default_factory=list)

    notes: list[str] = field(default_factory=list)


def _mode_str(mode: int) -> str:
    return stat.filemode(mode)


def _find_web_server(root: Path) -> tuple[Path | None, str | None]:
    for candidate in ("bin/boa", "usr/sbin/boa", "sbin/boa", "usr/bin/boa",
                      "bin/httpd", "usr/sbin/httpd", "bin/goahead", "bin/lighttpd"):
        p = root / candidate
        if p.is_file():
            banner = None
            try:
                for s in iter_strings(p.read_bytes(), 6):
                    if re.match(r"^(Boa|GoAhead|lighttpd|thttpd|mini_httpd)/[\d.]", s):
                        banner = s
                        break
            except OSError:
                pass
            return p, banner
    return None, None


def _document_root(root: Path) -> str | None:
    for conf in root.glob("etc/**/boa.conf*"):
        try:
            for line in conf.read_text("utf-8", "replace").splitlines():
                line = line.strip()
                if line.lower().startswith("documentroot"):
                    return line.split(None, 1)[1].strip()
        except OSError:
            continue
    return None


def _extract_handlers(binary: Path) -> list[str]:
    try:
        data = binary.read_bytes()
    except OSError:
        return []
    found = {m.decode("ascii") for m in HANDLER_RE.findall(data)}
    return sorted(found - HANDLER_STOPWORDS)


def _classify_symlink(link: Path, root: Path) -> SuspectSymlink | None:
    """Flag symlinks that escape the read-only image into runtime-writable storage.

    On these devices the SquashFS root is read-only, so anything mutable lives on
    a tmpfs under /var or /tmp. A symlink from inside the web document root to
    /var is therefore not a mistake — it is the mechanism by which generated
    runtime state becomes web-reachable. ``/web/config.dat -> /var/config.dat``
    is exactly that, and it is the exposure path behind CVE-2019-19822.
    """
    try:
        target = os.readlink(link)
    except OSError:
        return None

    rel = link.relative_to(root).as_posix()
    in_docroot = rel.startswith(("web/", "www/", "htdocs/", "var/web/"))
    writable_target = target.startswith(("/var", "/tmp", "/dev/shm", "/proc"))

    if in_docroot and writable_target:
        return SuspectSymlink(
            path="/" + rel, target=target, in_docroot=True,
            reason="web-reachable path resolves into runtime-writable storage; "
                   "whatever the firmware writes there becomes downloadable")
    if writable_target:
        return SuspectSymlink(
            path="/" + rel, target=target,
            reason="read-only image path redirected to writable storage")
    if target.startswith("/") and not (root / target.lstrip("/")).exists():
        return SuspectSymlink(
            path="/" + rel, target=target,
            reason="dangling absolute symlink (target created at runtime)")
    return None


def _scan_init(root: Path) -> tuple[list[InitFinding], list[str]]:
    findings: list[InitFinding] = []
    disabled: set[str] = set()

    scripts: list[Path] = []
    for pattern in INIT_SCRIPT_GLOBS:
        scripts.extend(p for p in root.glob(pattern) if p.is_file())

    for script in sorted(set(scripts)):
        try:
            raw = script.read_bytes()
        except OSError:
            continue
        # /init is a busybox ELF on these images, not a shell script. Reading it
        # as text and grepping for service names produced lines of decompiled
        # garbage in the report, so screen on content rather than on filename.
        if b"\x00" in raw[:4096] or raw[:4] == b"\x7fELF":
            continue
        text = raw.decode("utf-8", "replace")
        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if not stripped:
                continue
            if not SERVICE_MARKERS.search(stripped):
                continue
            commented = stripped.startswith("#")
            findings.append(InitFinding(
                file="/" + script.relative_to(root).as_posix(),
                line_no=i, line=stripped[:200], commented=commented))
            if commented:
                for m in SERVICE_MARKERS.findall(stripped):
                    disabled.add(m)
    return findings, sorted(disabled)


def analyse(root: str | Path, label: str = "") -> RootfsReport:
    root = Path(root)
    rep = RootfsReport(root=str(root), label=label)

    web_bin, banner = _find_web_server(root)
    if web_bin:
        rep.web_server = "/" + web_bin.relative_to(root).as_posix()
        rep.web_server_banner = banner
        rep.handlers = _extract_handlers(web_bin)
        rep.handler_source = rep.web_server
    rep.document_root = _document_root(root)

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        d = Path(dirpath)
        rep.dir_count += len(dirnames)
        for name in filenames:
            p = d / name
            try:
                st = p.lstat()
            except OSError:
                continue

            if stat.S_ISLNK(st.st_mode):
                rep.symlink_count += 1
                sus = _classify_symlink(p, root)
                if sus:
                    rep.suspect_symlinks.append(sus)
                continue

            rep.file_count += 1
            rep.total_bytes += st.st_size
            rel = "/" + p.relative_to(root).as_posix()

            if st.st_mode & (stat.S_ISUID | stat.S_ISGID):
                rep.setuid_files.append(f"{rel} ({_mode_str(st.st_mode)})")
            if st.st_mode & stat.S_IWOTH:
                rep.world_writable.append(rel)
            if CREDENTIAL_FILENAMES.match(name):
                rep.credential_files.append(f"{rel} ({st.st_size} bytes)")

            # Only regular executables are worth an ELF parse attempt.
            if not (st.st_mode & 0o111) or st.st_size < 52:
                continue
            er = elf.analyse(p)
            if not er.is_elf:
                continue

            h = er.hardening
            rep.binaries.append(BinaryEntry(
                path=rel,
                size=st.st_size,
                mode=_mode_str(st.st_mode),
                endian=er.endian,
                machine=f"{er.machine} {er.mips_isa or ''}".strip(),
                load_base=f"0x{er.load_base:08x}",
                entry=f"0x{er.entry:08x}",
                stripped_sections=not er.section_headers,
                needed=er.needed,
                sinks=er.sinks,
                hardening={
                    "nx": h.nx, "pie": h.pie, "relro": h.relro,
                    "canary": h.canary, "fortify": h.fortify,
                    "rwx_segments": h.rwx_segments,
                    "text_relocations": h.text_relocations,
                } if h else {},
            ))
            if er.sinks.get("command_exec"):
                rep.command_exec_binaries.append(rel)

    rep.binaries.sort(key=lambda b: b.path)
    rep.command_exec_binaries.sort()
    rep.suspect_symlinks.sort(key=lambda s: s.path)
    rep.credential_files.sort()

    rep.init_findings, rep.disabled_services = _scan_init(root)

    if rep.disabled_services:
        rep.notes.append(
            "Services present in the image but disabled only by commenting out "
            f"their init line: {', '.join(rep.disabled_services)}. The binaries "
            "are still on the device and remain reachable to anything that can "
            "execute a command.")
    if not (root / "etc/passwd").exists():
        rep.notes.append(
            "No /etc/passwd in the image: local accounts, if any, are created at "
            "runtime or authentication is handled entirely inside the "
            "application, not by the C library. Any credential check therefore "
            "lives in a binary and must be found by reversing, not by reading "
            "a config file.")
    return rep
