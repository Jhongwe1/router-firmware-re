"""Recover the Realtek APMIB configuration table from ``libapmib.so``.

Why this exists
---------------
Every interesting decision in ``/bin/boa`` is expressed as a number::

    apmib_get(0xb6, username);
    apmib_get(0xb7, password);
    apmib_set(0x1ec, client_ip);

Reading the authorisation path in W03 meant carrying those numbers around as
unknowns and describing them by what the surrounding code did with them. That
is a guess dressed as a fact: ``0xb6`` was called "the configured admin
username" because it was compared against one, not because anything said so.

``libapmib.so`` says so. It carries the table the whole SDK is built around, and
each record holds the numeric id next to a human name — ``AUTHG_IP_ADDR``,
``AUTHG_USER_NAME``, ``AUTHG_PASS_WORD``. Recovering it turns every
``apmib_get`` in the firmware from a number into a name, and it is also the
index of what ``/web/config.dat`` contains, which is the substance of
CVE-2019-19823.

The record layout, and how it was established
---------------------------------------------
Not from a leaked SDK header — this project has already been burned once by
assuming a published ``rtl819x`` struct described the binary in front of it
(``notes/dispatch-table.md``). It was measured, by finding the three names Boa's
authorisation code uses and dumping the bytes around them::

    00c818  00 00 01 ec                        id
    00c81c  41 55 54 48 47 5f 49 50 5f 41 ...  "AUTHG_IP_ADDR"
    ...
    00c854  00 00 01 ed                        id      <- exactly 0x3c later
    00c858  41 55 54 48 47 5f 55 53 45 52 ...  "AUTHG_USER_NAME"

So: a 60-byte record, a big-endian ``uint32`` id, then a 32-byte inline name.
The names being *inline* rather than pointed-to is why ``strings`` shows them
run together with a stray leading byte from the previous record's tail.

How this is allowed to fail
---------------------------
A recovery script that cannot fail proves nothing. This one refuses in three
ways:

* the stride is fixed at 60 and never inferred per-run;
* the three anchor ids Boa uses must land on the three names Boa's behaviour
  implies, or ``verdict`` is ``SUSPECT`` and the caller is told which anchor
  disagreed;
* at least one anchor id must be present, and every anchor that is present must
  carry the name the firmware's own behaviour implies.

The check that did *not* survive contact with the binary
--------------------------------------------------------
The first version required ids to increase monotonically across the whole run,
reasoning that a C array is written in declaration order. That fired
immediately - ``0x1ef AUTHG_PHONE`` followed by ``0x13e DFS_ENABLED`` - and the
check was wrong, not the walk. ``libapmib`` chains sub-tables: its own
diagnostic string is ``mibtbl->id (%08x) unitsize (%d) totoal size (%d)
mibtbl->nextbl %p``. A falling id is a segment boundary, so segments are now
counted and reported as structure. Bit 15 of an id marks a *table-valued* entry
(``IPFILTER_ENABLED`` 0x74 beside ``IPFILTER_TBL`` 0x8076), which is why
segment ordering is judged on the masked id.
"""

from __future__ import annotations

import hashlib
import re
import struct
from dataclasses import dataclass, field

RECORD_SIZE = 60
NAME_OFFSET = 4
NAME_SIZE = 32
ID_STRUCT = ">I"

# Anchors: id -> name. Not chosen for convenience. Every one of these is an id
# that process_header_end passes to apmib_get/apmib_set, so if the recovered
# table disagrees the recovery is wrong in exactly the place the rest of the
# analysis depends on.
#
# They are checked, not searched for. V3.4.0 dropped the whole AUTHG_* family -
# which is independently visible in its string table (notes/auth-flow.md) - so
# an anchor the build genuinely does not have must read as absent rather than as
# a failed recovery. What is required is that *some* anchor is present and that
# every present anchor matches.
ANCHORS = {
    0xB6: "USER_NAME",
    0xB7: "USER_PASSWORD",
    0x1EC: "AUTHG_IP_ADDR",
    0x1ED: "AUTHG_USER_NAME",
    0x1EE: "AUTHG_PASS_WORD",
}

_NAME_RE = re.compile(rb"^[A-Z][A-Z0-9_]{2,31}\x00*$")


@dataclass
class MibEntry:
    id: int
    name: str
    offset: int          # file offset of the record

    @property
    def id_hex(self) -> str:
        return f"0x{self.id:x}"


@dataclass
class MibTable:
    producer: str = "fwrecon:mib"
    path: str = ""
    source_sha256: str = ""
    entries: list[MibEntry] = field(default_factory=list)
    table_offset: int = -1
    record_size: int = RECORD_SIZE
    segments: int = 1
    runner_up: int = 0
    anchors_matched: int = 0
    anchors_checked: dict[str, str] = field(default_factory=dict)
    duplicate_ids: list[str] = field(default_factory=list)
    anomalies: list[str] = field(default_factory=list)
    verdict: str = "consistent"

    def by_id(self, mib_id: int) -> str | None:
        for e in self.entries:
            if e.id == mib_id:
                return e.name
        return None


def _name_at(data: bytes, off: int) -> str | None:
    raw = data[off + NAME_OFFSET: off + NAME_OFFSET + NAME_SIZE]
    if len(raw) < NAME_SIZE or not _NAME_RE.match(raw):
        return None
    return raw.split(b"\x00", 1)[0].decode("ascii")


def _record_at(data: bytes, off: int) -> MibEntry | None:
    if off < 0 or off + RECORD_SIZE > len(data):
        return None
    name = _name_at(data, off)
    if name is None:
        return None
    (mib_id,) = struct.unpack_from(ID_STRUCT, data, off)
    if mib_id == 0 or mib_id > 0xFFFF:
        return None
    return MibEntry(id=mib_id, name=name, offset=off)


def analyse(path: str) -> MibTable:
    """Recover the MIB table from one ``libapmib.so``."""
    with open(path, "rb") as fh:
        data = fh.read()
    # Same rule as the Ghidra reports: a report that cannot name the binary it
    # describes is not evidence (tools/check-reports.py enforces it).
    table = MibTable(path=path, source_sha256=hashlib.sha256(data).hexdigest())

    # Find the table structurally rather than from a known name.
    #
    # The first version anchored on the literal "AUTHG_IP_ADDR" and required it
    # to appear exactly once. That works on V2.1.2 and fails flat on V3.4.0,
    # which removed the AUTHG_* entries - the tool reported "cannot locate the
    # table" for a build whose table is perfectly intact. Anchoring recovery on
    # a name that a later build is free to delete makes the instrument version
    # specific for no reason.
    #
    # So: parse every offset that can be read as a record, chain them into runs
    # of the fixed stride, and take the longest run. Names are still required to
    # be identifier-shaped and ids to be in range, so a run of the length seen
    # here cannot be coincidence - but the runner-up is reported, and a
    # runner-up of comparable size means the answer is ambiguous and is refused.
    candidates = sorted(
        off for off in range(0, len(data) - RECORD_SIZE + 1, 4)
        if _record_at(data, off) is not None)
    cand_set = set(candidates)

    runs: list[tuple[int, int]] = []          # (start offset, record count)
    for off in candidates:
        if off - RECORD_SIZE in cand_set:
            continue                          # not the head of a run
        n = 0
        cur = off
        while cur in cand_set:
            n += 1
            cur += RECORD_SIZE
        runs.append((off, n))
    runs.sort(key=lambda r: r[1], reverse=True)

    if not runs:
        table.verdict = "SUSPECT"
        table.anomalies.append("no record-shaped bytes found at all")
        return table

    table.table_offset, count = runs[0]
    table.runner_up = runs[1][1] if len(runs) > 1 else 0
    if table.runner_up * 2 >= count:
        table.anomalies.append(
            f"longest run is {count} records but a second run of "
            f"{table.runner_up} exists - the table is not identifiable "
            "unambiguously")

    off = table.table_offset
    for _ in range(count):
        rec = _record_at(data, off)
        assert rec is not None                # guaranteed by the run construction
        table.entries.append(rec)
        off += RECORD_SIZE

    # A falling id is a sub-table boundary, not damage - see the module note.
    for prev, cur in zip(table.entries, table.entries[1:], strict=False):
        if (cur.id & 0x7FFF) <= (prev.id & 0x7FFF):
            table.segments += 1

    # One id under two names is reported, but not as a recovery failure.
    #
    # It was, at first. Then V2.1.2 turned up 0x182 bound to both
    # CUSTOM_PASSTHRU_ENABLED and MLD_PROXY_DISABLED and the walk was blamed.
    # libapmib carries its own runtime string "MIB Error: %s detect duplicate id
    # in %s" and exports mibtbl_check, so the vendor knows this can happen and
    # checks for it at load time. A duplicate is a property of the firmware -
    # apmib_get(0x182) resolves to whichever record the lookup reaches first -
    # and V3.4.0 has none. Reporting it as "the tool is broken" would have
    # thrown away a real finding.
    seen: dict[int, str] = {}
    for e in table.entries:
        if e.id in seen and seen[e.id] != e.name:
            table.duplicate_ids.append(
                f"{e.id_hex}: {seen[e.id]} and {e.name} (record at 0x{e.offset:x})")
        seen.setdefault(e.id, e.name)

    matched = 0
    for mib_id, expected in sorted(ANCHORS.items()):
        got = table.by_id(mib_id)
        table.anchors_checked[f"0x{mib_id:x}"] = got or "<absent from this build>"
        if got is None:
            continue
        if got == expected:
            matched += 1
        else:
            table.anomalies.append(
                f"anchor 0x{mib_id:x} recovered as {got!r}, expected {expected!r}")
    table.anchors_matched = matched
    if matched == 0:
        table.anomalies.append(
            "no anchor id was present - nothing ties this table to the ids the "
            "firmware actually uses, so it is unverified")

    if table.anomalies:
        table.verdict = "SUSPECT"
    elif len(table.entries) < len(ANCHORS):
        table.verdict = "SUSPECT"
        table.anomalies.append(
            f"only {len(table.entries)} records recovered - the walk did not run")
    return table


def to_markdown(t: MibTable) -> str:
    lines = [
        "# APMIB table",
        "",
        f"- source: `{t.path}`",
        f"- sha256: `{t.source_sha256}`",
        f"- table at file offset `0x{t.table_offset:x}`, "
        f"{len(t.entries)} records of {t.record_size} bytes "
        f"across {t.segments} chained sub-tables",
        f"- next-longest competing run: {t.runner_up} records",
        f"- anchors matched: {t.anchors_matched}/{len(t.anchors_checked)}",
        f"- self-check: **{t.verdict}**",
        "",
        "Anchors (the ids Boa's authorisation path uses):",
        "",
        "| id | recovered name |",
        "|---|---|",
    ]
    for k, v in t.anchors_checked.items():
        lines.append(f"| `{k}` | `{v}` |")
    if t.duplicate_ids:
        lines += ["", "Duplicate ids (a property of the vendor table, not of the "
                  "recovery - `libapmib` checks for these itself):", ""]
        lines += [f"- {d}" for d in t.duplicate_ids]
    if t.anomalies:
        lines += ["", "Anomalies:", ""] + [f"- {a}" for a in t.anomalies]
    lines += ["", "| id | name |", "|---|---|"]
    for e in t.entries:
        lines.append(f"| `{e.id_hex}` | `{e.name}` |")
    return "\n".join(lines) + "\n"
