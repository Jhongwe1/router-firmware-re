"""Cross-version diff of two fwrecon reports.

The interesting question about a firmware line is rarely "what is in this
build" — it is "what changed, and does the change match what the vendor said
changed". A CVE record states that versions "through 3.4.0" are affected; it
does not tell you whether the fix in the next build removed the vulnerable
code, removed only the UI that reached it, or removed nothing at all.

Diffing two structured inventories answers that mechanically.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Change:
    category: str
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    note: str = ""

    @property
    def empty(self) -> bool:
        return not self.added and not self.removed


def _load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text("utf-8"))


def _set_diff(category: str, a: list, b: list, note: str = "") -> Change:
    sa, sb = set(a or []), set(b or [])
    return Change(category, sorted(sb - sa), sorted(sa - sb), note)


def compare(left_path: str | Path, right_path: str | Path) -> dict:
    """Compare two report JSON files. ``left`` is the older build."""
    a, b = _load(left_path), _load(right_path)
    ra = a.get("rootfs") or {}
    rb = b.get("rootfs") or {}

    changes: list[Change] = []

    changes.append(_set_diff(
        "web handlers",
        ra.get("handlers", []), rb.get("handlers", []),
        "handlers reachable as /boafrm/<name>"))

    changes.append(_set_diff(
        "binaries",
        [x["path"] for x in ra.get("binaries", [])],
        [x["path"] for x in rb.get("binaries", [])]))

    changes.append(_set_diff(
        "binaries reaching a command-execution sink",
        ra.get("command_exec_binaries", []), rb.get("command_exec_binaries", [])))

    changes.append(_set_diff(
        "symlinks exposing runtime state inside the web document root",
        _docroot_links(ra), _docroot_links(rb),
        "a link surviving across versions means the exposure path was not closed"))

    changes.append(_set_diff(
        "other symlinks into runtime-writable storage",
        _other_links(ra), _other_links(rb),
        "ordinary read-only-rootfs plumbing; listed for completeness"))

    changes.append(_set_diff(
        "shared libraries needed by the web server",
        _webserver_needed(ra), _webserver_needed(rb)))

    changes.append(_set_diff(
        "services referenced by init scripts",
        [f"{f['file']}:{f['line']}" for f in ra.get("init_findings", [])],
        [f"{f['file']}:{f['line']}" for f in rb.get("init_findings", [])]))

    return {
        "left": {"label": a.get("label"), "sha256": a.get("image_sha256")},
        "right": {"label": b.get("label"), "sha256": b.get("image_sha256")},
        "changes": [
            {"category": c.category, "added": c.added, "removed": c.removed,
             "note": c.note}
            for c in changes if not c.empty
        ],
        "unchanged_categories": [c.category for c in changes if c.empty],
    }


def _docroot_links(rootfs: dict) -> list[str]:
    return [f"{s['path']} -> {s['target']}"
            for s in rootfs.get("suspect_symlinks", []) if s.get("in_docroot")]


def _other_links(rootfs: dict) -> list[str]:
    return [f"{s['path']} -> {s['target']}"
            for s in rootfs.get("suspect_symlinks", []) if not s.get("in_docroot")]


def _webserver_needed(rootfs: dict) -> list[str]:
    ws = rootfs.get("web_server")
    for b in rootfs.get("binaries", []):
        if b["path"] == ws:
            return b.get("needed", [])
    return []


def to_markdown(d: dict) -> str:
    L: list[str] = []
    a = L.append
    a(f"# Version diff: {d['left']['label']} -> {d['right']['label']}\n")
    a(f"- older: `{d['left']['sha256']}`")
    a(f"- newer: `{d['right']['sha256']}`\n")

    if not d["changes"]:
        a("_No structural differences in the compared categories._\n")
    for c in d["changes"]:
        a(f"## {c['category']}\n")
        if c["note"]:
            a(f"_{c['note']}_\n")
        if c["added"]:
            a(f"**Added ({len(c['added'])})**\n")
            a("```")
            for x in c["added"]:
                a(f"+ {x}")
            a("```\n")
        if c["removed"]:
            a(f"**Removed ({len(c['removed'])})**\n")
            a("```")
            for x in c["removed"]:
                a(f"- {x}")
            a("```\n")

    if d["unchanged_categories"]:
        a("## Unchanged\n")
        for c in d["unchanged_categories"]:
            a(f"- {c}")
        a("")
    return "\n".join(L) + "\n"
