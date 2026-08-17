#!/usr/bin/env python3
"""Turn the CI gate's output into a work list, across every build at once.

W07's premise is that the hunting has already been done by instruments built in
earlier weeks, and what is missing is the arithmetic. Three things come out of
that arithmetic and none of them is a hunch:

1. **The residue.** `BoaGate` reports 134 findings on this unit's build. Subtract
   the sites a published CVE already explains and what remains is the week's
   work list -- computed, not chosen.

2. **Divergence between builds.** The same instrument runs on three binaries
   five years apart. A site present in 2015 and gone in 2018 is a fix; a site
   absent in 2018 and back in 2020 is a regression, and regressions across a
   vendor's own release line are close to invisible to the CVE system because
   nobody looks at three versions at once.

3. **Islands.** A handler in `root_form[]` that no page in the shipped UI ever
   names. That is not a vulnerability by itself and this tool does not pretend
   otherwise -- it prints the candidates and the boring explanations that have
   to be excluded first.

Why the UI side is trustworthy here
-----------------------------------
`/web` in the extracted rootfs is a symlink to `/var/web`, which is empty: the
pages live in the `w6cg` flash partition and `rcS` unpacks them at boot with
`flash extr /web`. So the UI half of an island comparison cannot be read out of
the rootfs at all -- a grep over the extracted tree finds nothing and would make
*every* handler look like an island. The docroots used here are the ones the
**vendor's own extractor** produced inside the emulated environments, which is
why `tools/qemu-env.sh build` is a prerequisite rather than a convenience.

The known-CVE list is not a filter of convenience
-------------------------------------------------
Every entry carries the identifier that explains it. Subtracting a site because
"we already know about that one" without saying which advisory says so is how a
finding gets lost, so an unexplained subtraction is impossible by construction:
the value *is* the citation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# label -> (gate report, dispatch table report, docroot inside the built env)
BUILDS = {
    "2.1.2": ("ghidra-gate-2.1.2.json", "ghidra-formtable-2.1.2.json", "qemu-env-v2.1.2/var/web"),
    "unit-2018": ("ghidra-gate-unit-2018.json", "ghidra-formtable-unit-2018.json",
                  "qemu-env-2018/var/web"),
    "3.4.0": ("ghidra-gate-3.4.0.json", "ghidra-formtable-3.4.0.json", None),
}

# `function:parameter` -> the advisory that explains it. notes/cve-status.md and
# notes/prior-art.md carry the full table; these are the ones that would
# otherwise show up as fresh findings.
KNOWN_CVE = {
    "form_formWsc:localPin": "CVE-2025-3987 / CVE-2025-4462 (same source line)",
    "form_formWsc:peerPin": "CVE-2025-3987 family -- and REFUTED on this unit, W06 P3-1",
    "form_formWsc:targetAPSsid": "CVE-2025-6299 -- and not an injection here, W06 P3-4",
    "form_formSysCmd:sysCmd": "CVE-2024-51228 -- the CVE that names this build",
    "form_formRoute:subnet": "no CVE; project-original D-1, WITHDRAWN W06 -- "
                             "Talos TALOS-2023-1894 explains it as an sprintf misread",
}

# R2 is the rule that says "reaches system()/popen()". W06 measured six of its
# sites on this unit and two did not execute, so its output is not evidence on
# its own -- it is a list of things to go and check. Stated here because this
# tool's output is the input to the rest of the week.
R2_CAVEAT = ("BoaGate R2 has known false positives: 2 of 6 sites on unit-2018 produced no "
             "execution when fired at the device (W06, instrument bug 25). A site listed "
             "here is a candidate, not a finding.")


def _default_work() -> Path:
    """$FWRE_WORK, or the *invoking* user's home -- not root's.

    This tool needs sudo to read the docroots, and under sudo `Path.home()` is
    `/root`, where none of the artefacts are. The failure is loud rather than
    subtle (`no docroot at /root/fwre-work/...`), but it sends the reader to
    rebuild an environment that already exists, which is the same wrong-fix
    problem as instrument bug 24.
    """
    import os
    import pwd

    env = os.environ.get("FWRE_WORK")
    if env:
        return Path(env)
    user = os.environ.get("SUDO_USER")
    if user:
        try:
            return Path(pwd.getpwnam(user).pw_dir) / "fwre-work"
        except KeyError:
            pass
    return Path.home() / "fwre-work"


def load(name: str) -> dict:
    return json.loads((REPO / "reports" / name).read_text("utf-8"))


def handler_names(formtable: dict) -> dict[str, str]:
    """address -> handler name, from the recovered root_form[] table."""
    out = {}
    for t in formtable.get("tables", []):
        if t.get("role") != "root_form":
            continue
        for e in t.get("entries", []):
            if e.get("name") and e.get("handler"):
                out[str(e["handler"]).lower().lstrip("0").zfill(8)] = e["name"]
    return out


def ui_referenced(docroot: Path) -> tuple[set[str], int, list[str]]:
    """Handler names any shipped page mentions, the number of files read, and
    anything that could not be read.

    Reads the docroot the vendor's own `flash extr` produced, not the extracted
    rootfs -- see the module note.

    The unreadable list is returned rather than swallowed, and the caller treats
    a non-empty one as fatal. First version of this function skipped unreadable
    entries silently: `flash extr` creates subdirectories owned by root, the
    tool ran as an ordinary user, and it read 91 of 146 files while reporting an
    island count with no hint that a third of the UI had not been looked at.
    **Every handler whose only mention lived in an unreadable directory would
    have been named as an island** -- a fabricated finding produced by a
    permission error. Instrument bug 32.
    """
    import os

    seen: set[str] = set()
    unreadable: list[str] = []
    read = 0
    pat = re.compile(rb"boafrm/([A-Za-z0-9_]+)")

    def onerror(exc: OSError) -> None:
        unreadable.append(f"{getattr(exc, 'filename', '?')}: {exc.strerror}")

    for root, _dirs, files in os.walk(docroot, onerror=onerror):
        for fn in files:
            p = Path(root) / fn
            try:
                blob = p.read_bytes()
            except OSError as exc:
                unreadable.append(f"{p}: {exc.strerror}")
                continue
            read += 1
            seen |= {m.decode("ascii") for m in pat.findall(blob)}
    return seen, read, unreadable


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    # The docroots are root-owned, so this runs under sudo -- and under sudo
    # Path.home() is /root, which is not where the artefacts are. qemu-env.sh
    # carries the same fix and the same comment; this is the second tool to
    # need it, which is why it is a named function rather than an inline expression.
    ap.add_argument("--work", type=Path, default=_default_work(),
                    help="where the built emulation environments live")
    ap.add_argument("--out", type=Path, default=REPO / "reports/bughunt.json")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    report: dict = {
        "producer": "bughunt",
        "schema_version": "1",
        "rules": None,
        "r2_caveat": R2_CAVEAT,
        "known_cve": KNOWN_CVE,
        "builds": {},
        "residue": [],
        "divergence": [],
        "islands": {},
        "self_check": {},
    }

    # key -> {label: finding}, where key is (rule, function, parameter). The
    # sink *address* is deliberately not in the key: it moves between builds and
    # would make every site look unique, which is the opposite of the point.
    across: dict[tuple[str, str, str], dict[str, dict]] = defaultdict(dict)
    joined = unjoined = 0

    for label, (gate_f, ft_f, docroot) in BUILDS.items():
        gate, ft = load(gate_f), load(ft_f)
        names = handler_names(ft)
        report["rules"] = gate.get("rules")
        report["builds"][label] = {
            "source_sha256": gate.get("source_sha256"),
            "findings": gate.get("finding_count"),
            "by_rule": gate.get("findings_by_rule"),
            "dispatch_entries": len(names),
        }
        for f in gate.get("findings", []):
            entry = str(f.get("entry", "")).lower().lstrip("0").zfill(8)
            if entry in names:
                joined += 1
            else:
                unjoined += 1
            across[(f["rule"], f["function"], f.get("parameter") or "?")][label] = f

        if docroot:
            d = args.work / docroot
            if not d.is_dir():
                print(f"bughunt: no docroot at {d}\n"
                      f"         island analysis needs it. Build the environment first:\n"
                      f"           sudo tools/qemu-env.sh --profile "
                      f"{'v2.1.2' if label == '2.1.2' else 'unit-2018'} build",
                      file=sys.stderr)
                return 1
            refd, read, unreadable = ui_referenced(d)
            if unreadable:
                print(f"bughunt: {len(unreadable)} path(s) under {d} could not be read.\n"
                      f"         An island list computed from a partial docroot invents "
                      f"islands, so this is fatal rather than a warning.\n"
                      f"         `flash extr` creates root-owned subdirectories; re-run "
                      f"with sudo.\n         first: {unreadable[0]}", file=sys.stderr)
                return 1
            table = set(names.values())
            # root_form[] names are bare (`formWsc`); pages spell them the same
            # way after the /boafrm/ prefix, so the two sets are comparable.
            islands = sorted(table - refd)

            # `plan/W07` Day 1 asks three questions of every island and refuses
            # to call one a debug interface until the boring answers are
            # excluded. Two of the three are answerable from reports already
            # committed, so they are answered here rather than by hand:
            # what parameters it takes, and which sink each one reaches. The
            # third -- is it reachable unauthenticated -- follows from the gate
            # model (P2-1 / P3-13: the gate matches on .htm/.asp, so nothing
            # under /boafrm/ is gated at all) and is worth firing at the
            # emulated server rather than reasoning about.
            addr_of = {n: a for a, n in names.items()}
            detail = {}
            for name in islands:
                sites = [
                    {"rule": f["rule"], "parameter": f.get("parameter"),
                     "sink": f.get("sink"), "site": f.get("site")}
                    for f in gate.get("findings", [])
                    if str(f.get("entry", "")).lower().lstrip("0").zfill(8) == addr_of[name]
                ]
                detail[name] = {
                    "handler_addr": addr_of[name],
                    "gate_sites": sites,
                    "params": sorted({s["parameter"] for s in sites if s["parameter"]}),
                }

            report["islands"][label] = {
                "docroot": str(d),
                "files_read": read,
                "handlers_in_table": len(table),
                "handlers_named_by_ui": len(refd & table),
                "islands": islands,
                "island_detail": detail,
                # The inverse, and it is not a footnote: a page that posts to a
                # handler the dispatch table does not have is a form that submits
                # to a 404. W04-2 found one of these by hand (`syscmd.htm` ->
                # `formSysCmd`, notes/w6cg-web-ui.md). Enumerating both directions
                # shows it is a pattern rather than an oddity.
                "ui_names_no_handler": sorted(refd - table),
            }

    # The join is a control: if the gate's `entry` addresses stopped lining up
    # with the dispatch table's handler addresses, every cross-reference below
    # would be silently meaningless.
    report["self_check"] = {
        "gate_findings_joined_to_a_dispatch_entry": joined,
        "not_joined": unjoined,
        "note": "A finding that does not join is in a function the dispatch table does "
                "not point at -- a helper, or a handler reached another way. Some are "
                "expected; all of them being unjoined means the two reports disagree "
                "about addresses and nothing here is trustworthy.",
    }

    for (rule, func, param), per in sorted(across.items()):
        key = f"{func}:{param}"
        row = {
            "rule": rule,
            "function": func,
            "parameter": param,
            "builds": sorted(per),
            "sink": {lbl: f.get("sink") for lbl, f in per.items()},
            "site": {lbl: f.get("site") for lbl, f in per.items()},
        }
        explained = KNOWN_CVE.get(key)
        if explained:
            row["explained_by"] = explained
        elif "unit-2018" in per:
            report["residue"].append(row)
        # Present in some builds and not others, and only worth printing where
        # every build was actually scanned for it.
        if len(per) != len(BUILDS):
            row2 = dict(row)
            row2["absent_from"] = sorted(set(BUILDS) - set(per))
            report["divergence"].append(row2)

    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if not args.quiet:
        print(f"wrote {args.out}")
        for lbl, b in report["builds"].items():
            print(f"  {lbl:10} {b['findings']:>4} findings  {b['by_rule']}  "
                  f"{b['dispatch_entries']} dispatch entries")
        print(f"  join control: {joined} findings joined to a dispatch entry, {unjoined} not")
        r2 = [r for r in report["residue"] if r["rule"] == "R2"]
        print(f"  residue on unit-2018: {len(report['residue'])} sites no known CVE explains"
              f"  ({len(r2)} of them R2 -- command execution candidates)")
        print(f"  divergence: {len(report['divergence'])} sites not present in all "
              f"{len(BUILDS)} builds")
        for lbl, isl in report["islands"].items():
            print(f"  islands {lbl}: {len(isl['islands'])} of {isl['handlers_in_table']} "
                  f"handlers named by no page in {isl['files_read']} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
