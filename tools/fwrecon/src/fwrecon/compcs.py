"""Decode a Realtek APMIB configuration region (COMPCS / COMPDS / COMPHS).

What this is
------------
Three regions of this device's flash hold the same MIB table in three roles:

    0x006000  H601     hardware setting  (per-unit MACs, radio calibration)
    0x008000  COMPDS   default setting   (factory)
    0x00C000  COMPCS   current setting   (live)  <- this is /web/config.dat

W04 deferred decoding these because it had no real blob; W02 read the flash and
put one on disk. This module turns the blob into named MIB entries, which is the
second half of CVE-2019-19823 ("plaintext password storage") -- the first half
being that `USER_PASSWORD` is an ordinary MIB entry with an ordinary record.

Where the format came from, and in which order
----------------------------------------------
Both, deliberately, and the order is recorded because it was not the intended
one. The layout below was first inferred from the bytes (an LZSS hypothesis
tested against the two blobs), and only then read out of `libapmib.so`'s own
`Decode` at `0x00012e98` and `_apmib_dsconf` at `0x0001781c`. The plan for the
week said to read the binary first, precisely so that a decoder that "looks
right" cannot be built on a guess -- and doing it the other way round was a
mistake that happened to be caught by the binary agreeing.

What the binary added that the data could not have told us:

  * the ring buffer is filled with 0x20, not 0x00 (both decode identically here,
    which is itself a check -- see `ring_fill_agrees` below);
  * `compLen` is bounded by the vendor at 1..0x4000 -- `if (0x3fff < len - 1U) return 0`;
  * the decompression buffer is `malloc(compRate * compLen)`, so the u16 is an
    allocation hint, not a format field;
  * the signature is *two* characters plus a *two-ASCII-digit* version parsed
    with `sscanf("%02d")`, not a four-character magic;
  * an 8-bit checksum over the payload must sum to zero. Nothing in the data
    suggests it. It is the single strongest correctness check available here and
    it was found by reading the code.

Layout
------
Flash region::

    +0   char     magic[6]     "COMPCS" / "COMPDS" / "COMPHS"
    +6   uint16   compRate     big-endian; decompression buffer = compRate * compLen
    +8   uint32   compLen      big-endian; compressed payload length, 1..0x4000
    +12  uint8    payload[compLen]

Payload is LZSS (Okumura): 4096-byte ring pre-filled with 0x20, write pointer
starting at 4078, a flag byte whose bits are consumed LSB-first, 1 = literal
byte, 0 = a two-byte reference ``pos = b0 | ((b1 & 0xf0) << 4)``,
``len = (b1 & 0x0f) + 3``.

Decompressed::

    +0   char     sig[2]       "6G" default setting / "6g" current setting
    +2   char     ver[2]       ASCII, "03"
    +4   uint32   len          payload length; total = len + 8
    +8   TLV stream, repeated { uint16 id; uint16 len; uint8 value[len] }

and ``sum(payload) & 0xff == 0``.

Bit 15 of an id marks a table-valued entry, the same convention `mibtable.py`
records for the id/name table itself.

Table-valued entries, and the half of the region that was never read
--------------------------------------------------------------------
Until 2026-08-21 a table-valued entry was reported as its length and its hex.
One of them, ``WLAN_ROOT``, is **22,044 of the 45,226 decompressed bytes** — so
``notes/compcs-decode.md`` described a region as decoded while half of it had
never been looked at. It is decoded down to the TLV layer, and one TLV was half
the payload.

A table-valued value is the same ``{u16 id; u16 len; u8 value[len]}`` stream,
repeated once per element, and it nests: ``WLAN_ROOT`` holds six wlan blocks and
each block holds four tables of its own. What makes this a decode rather than a
plausible walk is that ``libapmib`` states the geometry and the arithmetic has
to close::

    WLAN_ROOT      total_size 15156 / element_size 2526 = 6 elements
    one element    2526 struct bytes + 133x4 own headers + 616 nested headers
                 = 3674 TLV bytes                          6 x 3674 = 22044, remainder 0

    MACAC_ADDR     540 struct + 40x4 = 700   SCHEDULE_TBL  280 + 50x4 = 480
    WDS            248 struct + 24x4 = 344   MESH_ACL_ADDR 540 + 40x4 = 700

so a value's length must equal ``total_size`` plus four bytes for **every TLV at
every depth inside it**. Every one of those numbers comes from the binary; none
is inferred from the data it is checking. The first version of that sum charged
only the top level and had ``WLAN_ROOT`` come out 3,696 bytes short — which is
6 blocks x 154 nested TLVs x 4, so the miss named its own cause.

Which sub-table names the elements is decided the same way — by test, not by
convention. The ids observed inside the value must equal the id set of one of
the runs :func:`fwrecon.mibtable.analyse` recovered, and that run's member sizes
must sum to ``element_size``. **No match is a refusal.** Several matches is a
refusal *only if they disagree*: ``libapmib`` carries the twelve-record
``PROFILE_SSID..PROFILE_PSK_FORMAT`` run twice, at 0xb130 and 0xb43c, with the
same ids, names and sizes, and refusing that would be refusing to choose between
two spellings of one word. What stays refused is candidates that would give
different answers, because there the decoder would be picking — and picking is
what this check exists to prevent.
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field

MAGICS = {
    b"COMPCS": "current setting",
    b"COMPDS": "default setting",
    b"COMPHS": "hardware setting",
}

HEADER_SIZE = 12
#: `_apmib_dsconf` rejects anything outside this before allocating. Copied from
#: the binary rather than chosen: a bound you invented is a bound you can widen
#: when it becomes inconvenient.
MAX_COMP_LEN = 0x4000
#: Sanity ceiling on compRate * compLen, so a corrupt u16 cannot ask for GiB.
MAX_DECOMPRESSED = 1 << 20

RING_SIZE = 4096
RING_FILL = 0x20
RING_START = 4078
MATCH_MIN = 3


class CompcsError(ValueError):
    """The blob is not what it claims to be. Always raised, never guessed past."""


@dataclass
class Entry:
    id: int
    name: str
    length: int
    offset: int
    raw: str                       # hex
    value: str                     # rendered
    kind: str                      # str | ipv4 | mac | u8 | u16 | u32 | bytes
    table_valued: bool = False
    unknown_id: bool = False
    disclosure: str = "open"
    disclosure_reason: str = ""
    #: Table-valued only. One list per element, each a decode of that element's
    #: own TLV stream. Empty when the entry is not table-valued *or* when the
    #: nested decode refused - `table_note` says which, and the two must never
    #: be confusable.
    rows: list[list[Entry]] = field(default_factory=list)
    table_source: str = ""      # e.g. "wlan table @0x12754 (133 records)"
    table_note: str = ""        # why rows is empty, or what the arithmetic showed
    #: Set when `rows` holds this entry's bytes, so `raw` and `value` are left
    #: empty instead of repeating them. A decoded `WLAN_ROOT` is 22,044 bytes
    #: whose hex would otherwise appear three times in one report - once here,
    #: once across the six blocks, once inside their nested tables. After this,
    #: every byte is present exactly once, in the leaf that owns it.
    #:
    #: It is not a size fix and should not be defended as one: it took the
    #: report from 2.06 MB to 2.00 MB. The report grew from 288 KB because it
    #: now carries 3,335 entries instead of 344, which is the content arriving,
    #: not overhead. What this flag buys is that the same bytes are not asserted
    #: in three places, and that the elision is stated rather than noticed.
    raw_elided_into_rows: bool = False

    @property
    def id_hex(self) -> str:
        return f"0x{self.id:x}"


@dataclass
class Config:
    producer: str = "fwrecon:compcs"
    path: str = ""
    source_sha256: str = ""
    region_offset: int = 0
    magic: str = ""
    role: str = ""
    comp_rate: int = 0
    comp_len: int = 0
    decompressed_len: int = 0
    signature: str = ""
    version: str = ""
    declared_len: int = 0
    checksum_ok: bool = False
    ring_fill_agrees: bool = False
    entry_count: int = 0
    unknown_ids: int = 0
    #: Table-valued entries met, and how many of them produced rows. Reported
    #: rather than assumed equal: `check-reports.py` refuses a committed report
    #: where they differ, so "half the region is still opaque" cannot be a state
    #: this repository ships without saying so.
    table_entries: int = 0
    table_entries_decoded: int = 0
    nested_entries: int = 0
    trailing_bytes: int = 0
    mib_records: int = 0
    mib_distinct_ids: int = 0
    mib_duplicate_ids: list[str] = field(default_factory=list)
    disclosure_mode: str = "open"
    entries: list[Entry] = field(default_factory=list)
    anomalies: list[str] = field(default_factory=list)
    verdict: str = "consistent"


# --------------------------------------------------------------------- LZSS

def lzss_decode(payload: bytes, limit: int, fill: int = RING_FILL) -> bytes:
    """Okumura LZSS, transcribed from `Decode` @ 0x00012e98 in libapmib.so.

    `limit` is the caller's allocation (compRate * compLen). The vendor's own
    Decode() writes into a buffer of exactly that size and does not check, so a
    blob claiming a small compRate and expanding further is a heap overflow in
    the device's own library. Here it is an error, and the error is the finding.
    """
    ring = bytearray([fill]) * RING_SIZE
    r = RING_START
    out = bytearray()
    i, n = 0, len(payload)
    flags = 0
    while i < n:
        flags >>= 1
        if not flags & 0x100:
            flags = payload[i] | 0xFF00
            i += 1
            if i > n:
                break
        if i >= n:
            break
        if flags & 1:
            out.append(payload[i])
            ring[r] = payload[i]
            r = (r + 1) & (RING_SIZE - 1)
            i += 1
        else:
            if i + 1 >= n:
                break
            b0, b1 = payload[i], payload[i + 1]
            i += 2
            pos = b0 | ((b1 & 0xF0) << 4)
            for k in range((b1 & 0x0F) + MATCH_MIN):
                c = ring[(pos + k) & (RING_SIZE - 1)]
                out.append(c)
                ring[r] = c
                r = (r + 1) & (RING_SIZE - 1)
        if len(out) > limit:
            raise CompcsError(
                f"decompressed past the vendor's own buffer: {len(out)} bytes written "
                f"into a malloc(compRate * compLen) = {limit}. Either the header is "
                f"wrong or this blob overflows libapmib's heap on the device.")
    return bytes(out)


def lzss_encode(data: bytes, fill: int = RING_FILL, *, max_candidates: int = 64) -> bytes:
    """The inverse of :func:`lzss_decode`, and the thing this module lacked.

    Written 2026-08-18 because two separate pieces of work stalled on the same
    absence. `P8-12` -- upload a configuration that turns telnet on -- has been
    parked as "blocked, fwrecon has no encoder" since the register was written.
    And G4's L2 environment needs a *default* settings block for a published
    image, because that block is written at manufacture and ships in no
    download: `apmib_init()` prints

        Invalid default setting signature or version number [sig=.., ver=-1, len=-1]!
        Expect [sig=6G, ver=3, len=32858]!

    and refuses to start. The vendor's own `flash default` would generate one,
    but it dies under qemu-user on an unaligned store the real MIPS kernel fixes
    up, so the generator is unavailable exactly where it is needed.

    Correctness here is not argued, it is checked: :func:`encode_region` runs
    the result back through :func:`lzss_decode` -- the decoder transcribed from
    the vendor's own `Decode` -- and refuses to return anything that does not
    round-trip. An encoder verified against its own idea of the format would be
    worth nothing.

    Greedy, with a 3-gram index over the ring rather than an exhaustive scan; a
    full search is O(n * 4096 * 18) and this is called on 32 KiB blobs. The
    ratio is not the point -- fitting inside the 16 KiB the flash layout gives
    each region is, and `max_candidates` is the knob if that ever gets tight.
    """
    match_max = 0x0F + MATCH_MIN
    mask = RING_SIZE - 1
    ring = bytearray([fill]) * RING_SIZE
    r = RING_START
    out = bytearray()
    index: dict[bytes, list[int]] = {}
    i, n = 0, len(data)
    flag_pos, flag_bit, flags = 0, 0, 0

    while i < n:
        if flag_bit == 0:
            flag_pos = len(out)
            out.append(0)
            flags = 0

        best_len, best_pos = 0, 0
        if i + MATCH_MIN <= n:
            for pos in index.get(bytes(data[i : i + MATCH_MIN]), ()):
                ln = 0
                while ln < match_max and i + ln < n and ring[(pos + ln) & mask] == data[i + ln]:
                    ln += 1
                if ln > best_len:
                    best_len, best_pos = ln, pos
                    if ln == match_max:
                        break

        if best_len >= MATCH_MIN:
            out.append(best_pos & 0xFF)
            out.append((((best_pos >> 8) & 0x0F) << 4) | (best_len - MATCH_MIN))
            take = best_len
        else:
            flags |= 1 << flag_bit
            out.append(data[i])
            take = 1
        out[flag_pos] = flags
        flag_bit = (flag_bit + 1) & 7

        for k in range(take):
            ring[r] = data[i + k]
            # Index the 3-gram that *ends* at the byte just written, so every
            # candidate position names a window whose bytes are all present.
            start = (r - MATCH_MIN + 1) & mask
            key = bytes(ring[(start + j) & mask] for j in range(MATCH_MIN))
            slots = index.setdefault(key, [])
            slots.insert(0, start)
            if len(slots) > max_candidates:
                del slots[max_candidates:]
            r = (r + 1) & mask
        i += take

    return bytes(out)


def encode_region(
    body: bytes, magic: bytes, *, comp_rate: int | None = None, max_bytes: int | None = None
) -> bytes:
    """Wrap `body` as an on-flash COMPCS/COMPDS region, and prove it decodes.

    `body` is the *decompressed* form in full, sig and version included -- the
    thing :func:`decode_region` hands back before it starts walking TLVs.

    `comp_rate` defaults to the ratio actually achieved, rounded up. It is not a
    format field -- the vendor uses it as `malloc(comp_rate * comp_len)` -- so a
    fixed constant is wrong in a way that only shows up on the device: the
    vendor's 7 suits their 6.05x on a real configuration, and an all-zero blob
    compresses 8.4x, which would have the library allocate less than it decodes
    into. Copying the vendor's constant looked like fidelity and was a heap
    overflow. Pass it explicitly only to reproduce a specific image.
    """
    if len(magic) != 6:
        raise CompcsError(f"magic must be 6 bytes, got {len(magic)}: {magic!r}")
    payload = lzss_encode(body)
    if comp_rate is None:
        comp_rate = -(-len(body) // len(payload)) if payload else 1
    if not 1 <= comp_rate <= 0xFFFF:
        raise CompcsError(f"comp_rate {comp_rate} does not fit the u16 the header has")

    # The vendor decodes into malloc(comp_rate * comp_len) and does not check
    # (see lzss_decode). An encoder that emits a header the vendor's own
    # allocator cannot honour is writing a heap overflow into a config file.
    budget = comp_rate * len(payload)
    if budget < len(body):
        raise CompcsError(
            f"comp_rate {comp_rate} x compLen {len(payload)} = {budget} is smaller "
            f"than the {len(body)} bytes this decodes to, which would overflow "
            f"libapmib's own buffer on the device. Raise comp_rate."
        )

    round_tripped = lzss_decode(payload, budget)
    if round_tripped != body:
        raise CompcsError(
            f"round-trip failed: encoded {len(body)} bytes, the vendor's own "
            f"decoder gives back {len(round_tripped)}. Not emitting this."
        )

    region = magic + struct.pack(">HI", comp_rate, len(payload)) + payload
    if max_bytes is not None and len(region) > max_bytes:
        raise CompcsError(
            f"region is {len(region)} bytes and the slot is {max_bytes}. "
            f"The flash layout puts COMPDS at 0x8000 and COMPCS at 0xC000, so "
            f"each has 16 KiB and neither may run into the next."
        )
    return region


# ------------------------------------------------------------------ rendering

_PRINTABLE = set(range(0x20, 0x7F))


def _render(value: bytes) -> tuple[str, str]:
    """(kind, rendered). Deliberately conservative: anything unrecognised stays hex."""
    if not value:
        return "bytes", ""
    stripped = value.split(b"\x00", 1)[0]
    if len(stripped) >= 2 and all(b in _PRINTABLE for b in stripped):
        return "str", stripped.decode("ascii")
    if len(value) == 4:
        return "ipv4", ".".join(str(b) for b in value)
    if len(value) == 6:
        return "mac", ":".join(f"{b:02x}" for b in value)
    if len(value) == 1:
        return "u8", str(value[0])
    if len(value) == 2:
        return "u16", str(struct.unpack(">H", value)[0])
    return "bytes", value.hex()


#: Fields whose value is a per-unit identifier rather than a setting. Under
#: `--disclosure protect` these are replaced by a digest. The list is by *name*
#: and errs wide, because a field wrongly protected costs a reader one lookup
#: and a field wrongly published cannot be taken back.
_PER_UNIT = ("MAC", "SERIAL", "SN_", "_SN", "UUID", "DEVICE_ID")


#: Nesting seen in this firmware is two deep (region -> WLAN_ROOT -> MACAC_ADDR).
#: The limit is 4 so a third real level would still decode, and a self-referential
#: stream cannot spin: a walk that cannot terminate is not a decoder.
MAX_TABLE_DEPTH = 4


def _classify(name: str, mode: str) -> tuple[str, str]:
    if mode == "open":
        return "open", "disclosure=open: self-purchased EOL unit, not in service"
    if any(k in name.upper() for k in _PER_UNIT):
        return "protect", "per-unit identifier; value replaced by sha256 under protect mode"
    return "open", "not a per-unit identifier"


# -------------------------------------------------------------------- decode

def _scope_names(scope) -> dict[int, str]:
    if scope is None:
        return {}
    out: dict[int, str] = {}
    for e in getattr(scope, "entries", []) or []:
        ident = e.id if isinstance(e.id, int) else int(str(e.id), 0)
        out.setdefault(ident, e.name)
    return out


def _scope_entry(scope, ident: int):
    """The declaring record for `ident`, looked up **in this scope only**.

    Scoping is the whole point. ``MACAC_ADDR`` (0x8036) is a record of the wlan
    sub-table, not of the main table, and ``SSID`` is 0x0001 in the wlan table
    and something else elsewhere. A global search across all twenty-one runs
    would resolve some ids to a record from the wrong table and be right often
    enough to look correct.
    """
    if scope is None:
        return None
    for e in getattr(scope, "entries", []) or []:
        if e.id == ident:
            return e
    return None


def _walk_stream(body: bytes, scope, cfg: Config, mib,
                 disclosure: str, where: str, depth: int) -> tuple[list[Entry], int]:
    """Walk one ``{u16 id; u16 len; u8 value[len]}`` stream and build entries.

    `scope` is the MIB table these ids are drawn from — the main table at the
    top level, the matched sub-table inside an element.

    Structural failure raises: a length that runs past the end means the stream
    is not what it claims, and truncating gives a plausible partial table, which
    is the one thing worse than an error. Failure to *name* a nested table does
    not raise - the bytes are still a valid stream - it is recorded on the entry
    and counted, so the verdict goes SUSPECT and the report cannot be committed.
    """
    names = _scope_names(scope)
    entries: list[Entry] = []
    off = 0
    while off + 4 <= len(body):
        ident, ln = struct.unpack_from(">HH", body, off)
        if ident == 0 and ln == 0:
            break
        if off + 4 + ln > len(body):
            raise CompcsError(
                f"TLV at {where} offset {off} declares {ln} bytes, which runs "
                f"{off + 4 + ln - len(body)} bytes past the end of the {where}. "
                f"Refusing to truncate and return a partial table.")
        raw = body[off + 4: off + 4 + ln]
        base = ident & 0x7FFF
        name = names.get(ident) or names.get(base) or ""
        kind, rendered = _render(raw)
        mode, reason = _classify(name or f"id_{ident:#x}", disclosure)
        if mode == "protect":
            rendered = "sha256:" + hashlib.sha256(raw).hexdigest()[:16]
            shown = rendered
        else:
            shown = raw.hex()
        entry = Entry(
            id=ident, name=name or f"<unknown id {ident:#x}>", length=ln, offset=off,
            raw=shown, value=rendered, kind=kind,
            table_valued=bool(ident & 0x8000),
            # Kept, never dropped. mib-and-config-dat.md records a duplicate id
            # that was first written off as the walk going too far and turned out
            # to be a defect in the vendor's own table. Discarding what the tool
            # does not recognise protects the tool's reputation at the result's
            # expense.
            unknown_id=not name,
            disclosure=mode, disclosure_reason=reason)
        if entry.table_valued:
            cfg.table_entries += 1
            _decode_table(entry, raw, cfg, scope, mib, disclosure, depth)
        entries.append(entry)
        off += 4 + ln
    if depth:
        cfg.nested_entries += len(entries)
    return entries, off


def _decode_table(entry: Entry, raw: bytes, cfg: Config, scope, mib,
                  disclosure: str, depth: int) -> None:
    """Fill `entry.rows`, or say on the entry why it could not be filled."""
    if depth >= MAX_TABLE_DEPTH:
        entry.table_note = f"not descended: nesting deeper than {MAX_TABLE_DEPTH}"
        cfg.anomalies.append(
            f"{entry.name}: table nesting exceeded {MAX_TABLE_DEPTH} levels")
        return
    if mib is None:
        entry.table_note = ("not descended: no --mib, so nothing says which table "
                            "names these elements or how many there are")
        return

    declared = _scope_entry(scope, entry.id)
    if declared is None or declared.count == 0:
        entry.table_note = (
            f"the MIB table has no usable geometry for id {entry.id_hex}"
            if declared is None else
            f"{declared.name} declares total_size {declared.total_size} and "
            f"element_size {declared.element_size}, which is not a whole number "
            f"of elements")
        cfg.anomalies.append(f"{entry.name}: {entry.table_note}")
        return

    # Walk once, flat, only to learn which ids are present. The grouping comes
    # from the binary's element count, never from guessing where a row ends.
    flat, consumed = _walk_stream(raw, None, _Sink(), None, disclosure,
                                  f"{entry.name} value", depth + 1)
    if consumed != len(raw):
        entry.table_note = (f"walk consumed {consumed} of {len(raw)} bytes")
        cfg.anomalies.append(f"{entry.name}: {entry.table_note}")
        return

    observed = {e.id for e in flat}
    matches = [t for t in getattr(mib, "sub_tables", []) if t.ids == observed]
    if not matches:
        entry.table_note = (
            f"no sub-table in libapmib has exactly the {len(observed)} ids this "
            f"value contains, so nothing names these fields")
        cfg.anomalies.append(f"{entry.name}: {entry.table_note}")
        return
    # More than one run can match, and whether that is an ambiguity depends on
    # whether they would give different answers. `libapmib` carries the
    # PROFILE_SSID..PROFILE_PSK_FORMAT run *twice*, at 0xb130 and 0xb43c, with
    # the same twelve ids, the same names and the same sizes - one per profile
    # slot. Refusing that would be refusing to choose between two spellings of
    # the same word. What must still be refused is two candidates that disagree,
    # because there the decoder would be picking, and picking is the thing this
    # check exists to prevent.
    signatures = {(tuple(sorted((e.id, e.name) for e in t.entries)), t.element_bytes)
                  for t in matches}
    if len(signatures) != 1:
        entry.table_note = (
            f"{len(matches)} sub-tables have these {len(observed)} ids and "
            f"{len(signatures)} of them disagree about the names or the sizes; "
            f"a decode needs one answer, not the nearest one")
        cfg.anomalies.append(f"{entry.name}: {entry.table_note}")
        return
    sub = matches[0]
    duplicate_note = ("" if len(matches) == 1 else
                      f", one of {len(matches)} identical runs")

    if sub.element_bytes != declared.element_size:
        entry.table_note = (
            f"the matched sub-table's members total {sub.element_bytes} bytes but "
            f"{declared.name} declares element_size {declared.element_size}")
        cfg.anomalies.append(f"{entry.name}: {entry.table_note}")
        return

    fields = len(sub.entries)
    if len(flat) != fields * declared.count:
        entry.table_note = (
            f"{len(flat)} TLVs against {fields} fields x {declared.count} elements "
            f"= {fields * declared.count}")
        cfg.anomalies.append(f"{entry.name}: {entry.table_note}")
        return

    # The arithmetic that ties the on-flash encoding to the in-memory struct:
    # struct bytes plus four header bytes for every TLV at every depth inside.
    deep = _count_tlvs_deep(raw)
    if deep is None:
        entry.table_note = "a nested value does not close on a TLV boundary"
        cfg.anomalies.append(f"{entry.name}: {entry.table_note}")
        return
    expected = declared.total_size + 4 * deep
    if expected != len(raw):
        entry.table_note = (
            f"{declared.total_size} struct bytes + {deep} x 4 header bytes "
            f"= {expected}, but the value is {len(raw)}")
        cfg.anomalies.append(f"{entry.name}: {entry.table_note}")
        return

    element_len = len(raw) // declared.count
    rows: list[list[Entry]] = []
    for k in range(declared.count):
        chunk = raw[k * element_len:(k + 1) * element_len]
        row, used = _walk_stream(chunk, sub, cfg, mib, disclosure,
                                 f"{entry.name}[{k}]", depth + 1)
        if used != len(chunk):
            entry.table_note = (
                f"element {k} consumed {used} of {element_len} bytes, so the "
                f"elements are not the fixed stride {declared.name} declares")
            cfg.anomalies.append(f"{entry.name}: {entry.table_note}")
            return
        rows.append(row)

    entry.rows = rows
    entry.table_source = (f"{sub.entries[0].name}.. run at 0x{sub.offset:x} "
                          f"({sub.record_count} records){duplicate_note}")
    entry.table_note = (f"{declared.count} elements x {element_len} bytes "
                        f"= {declared.total_size} struct + {4 * deep} headers")
    entry.raw = ""
    entry.value = f"{declared.count} elements, decoded into rows"
    entry.raw_elided_into_rows = True
    cfg.table_entries_decoded += 1


def _count_tlvs_deep(raw: bytes) -> int | None:
    """TLVs in this value at every depth, or None if some level does not close.

    The four header bytes a field costs are charged once per TLV *anywhere*
    inside, so a table holding tables costs more than its own field count. The
    first version of the arithmetic below charged only the top level and made
    ``WLAN_ROOT`` come out 3,696 bytes short — which is exactly 6 blocks x 154
    nested TLVs x 4. That miss is the reason this function exists rather than a
    ``len(flat)``: the check has to charge what the encoding charges.
    """
    total = 0
    off = 0
    while off + 4 <= len(raw):
        ident, ln = struct.unpack_from(">HH", raw, off)
        if ident == 0 and ln == 0:
            break
        if off + 4 + ln > len(raw):
            return None
        total += 1
        if ident & 0x8000:
            inner = _count_tlvs_deep(raw[off + 4: off + 4 + ln])
            if inner is None:
                return None
            total += inner
        off += 4 + ln
    return total if off == len(raw) else None


class _Sink:
    """A throwaway Config-shaped object for the probe walk.

    The probe exists only to learn the id set; its anomalies and counters
    describe a walk that is about to be redone properly, and letting them reach
    the real report would double-count every nested entry.
    """
    def __init__(self) -> None:
        self.anomalies: list[str] = []
        self.table_entries = 0
        self.table_entries_decoded = 0
        self.nested_entries = 0


def decode_region(data: bytes, offset: int, *, mib=None, disclosure: str = "open",
                  path: str = "", source_sha256: str = "") -> Config:
    """Decode one config region out of `data` at `offset`. Raises on anything
    it cannot justify; never returns a partial answer dressed as a whole one."""
    if disclosure not in ("open", "protect"):
        raise CompcsError(f"unknown disclosure mode {disclosure!r}")
    if offset < 0 or offset + HEADER_SIZE > len(data):
        raise CompcsError(f"offset {offset:#x} is outside a {len(data)}-byte image")

    magic = data[offset:offset + 6]
    if magic not in MAGICS:
        raise CompcsError(
            f"no APMIB config magic at {offset:#x}: found {magic!r}, "
            f"expected one of {sorted(m.decode() for m in MAGICS)}")

    comp_rate, comp_len = struct.unpack_from(">HI", data, offset + 6)
    if not 1 <= comp_len <= MAX_COMP_LEN:
        raise CompcsError(
            f"compLen {comp_len} is outside the vendor's own bound 1..{MAX_COMP_LEN} "
            f"(_apmib_dsconf: `if (0x3fff < len - 1U) return 0`)")
    if comp_rate == 0:
        raise CompcsError("compRate is 0, so the vendor would malloc(0) and Decode into it")
    budget = comp_rate * comp_len
    if budget > MAX_DECOMPRESSED:
        raise CompcsError(
            f"compRate * compLen = {budget} exceeds the {MAX_DECOMPRESSED}-byte ceiling")
    if offset + HEADER_SIZE + comp_len > len(data):
        raise CompcsError(
            f"payload of {comp_len} bytes at {offset + HEADER_SIZE:#x} runs past "
            f"the end of a {len(data)}-byte image")

    payload = data[offset + HEADER_SIZE: offset + HEADER_SIZE + comp_len]
    out = lzss_decode(payload, budget, fill=RING_FILL)

    cfg = Config(path=path, source_sha256=source_sha256, region_offset=offset,
                 magic=magic.decode(), role=MAGICS[magic], comp_rate=comp_rate,
                 comp_len=comp_len, decompressed_len=len(out),
                 disclosure_mode=disclosure)

    # A back-reference into never-written ring space would decode differently
    # under a different fill. The vendor uses 0x20; if 0x00 gives another answer,
    # this stream depends on uninitialised window content and the result is not
    # trustworthy however plausible it looks. Free, and it cannot be tuned.
    cfg.ring_fill_agrees = (out == lzss_decode(payload, budget, fill=0x00))
    if not cfg.ring_fill_agrees:
        cfg.anomalies.append(
            "decoding with ring fill 0x00 and 0x20 disagrees: the stream references "
            "window bytes no literal ever wrote")

    if len(out) < 8:
        raise CompcsError(f"decompressed to {len(out)} bytes, too short for the 8-byte header")
    cfg.signature = out[:2].decode("latin1")
    cfg.version = out[2:4].decode("latin1")
    (cfg.declared_len,) = struct.unpack_from(">I", out, 4)

    if cfg.signature not in ("6G", "6g"):
        raise CompcsError(
            f"decompressed signature {cfg.signature!r} is not '6G' or '6g'; "
            f"libapmib compares exactly 2 bytes and rejects anything else")
    if not cfg.version.isdigit():
        raise CompcsError(
            f"version field {cfg.version!r} is not two ASCII digits "
            f"(libapmib parses it with sscanf(\"%02d\"))")
    if cfg.declared_len + 8 != len(out):
        raise CompcsError(
            f"header declares {cfg.declared_len} payload bytes, so the whole blob should "
            f"be {cfg.declared_len + 8}; decompression produced {len(out)}")

    body = out[8:8 + cfg.declared_len]
    cfg.checksum_ok = (sum(body) & 0xFF) == 0
    if not cfg.checksum_ok:
        raise CompcsError(
            f"libapmib's 8-bit payload checksum is {sum(body) & 0xFF}, not 0. "
            f"The device itself would reject this blob.")

    # --------------------------------------------------------- TLV walk
    if mib is not None:
        mib_entries = getattr(mib, "entries", []) or []
        # Records, not distinct ids. The vendor's table binds 0x182 to two names
        # in both the 2015 and the 2018 build, so distinct-id count is one short
        # of the record count and comparing against it makes a correct decode
        # look like an off-by-one. mib-and-config-dat.md has the history.
        cfg.mib_records = len(mib_entries)
        cfg.mib_distinct_ids = len(_scope_names(mib))
        cfg.mib_duplicate_ids = list(getattr(mib, "duplicate_ids", []) or [])

    cfg.entries, off = _walk_stream(body, mib, cfg, mib, disclosure, "payload", 0)

    cfg.entry_count = len(cfg.entries)
    cfg.unknown_ids = sum(1 for e in cfg.entries if e.unknown_id)
    # Exactly one byte is expected: the pad libapmib adds so its 8-bit sum over
    # the payload comes to zero. Two or more means the TLV walk stopped early.
    tail = len(body) - off
    cfg.trailing_bytes = tail
    if tail > 1:
        cfg.anomalies.append(
            f"{tail} bytes left over after the TLV walk; exactly one is expected "
            f"(libapmib's checksum pad), so the stream is not fully understood")
    if mib is not None and cfg.entry_count != cfg.mib_records:
        cfg.anomalies.append(
            f"{cfg.entry_count} TLVs against {cfg.mib_records} records in the MIB table; "
            f"these are the same table in two files and should match")
    if cfg.unknown_ids:
        cfg.anomalies.append(f"{cfg.unknown_ids} id(s) not present in the MIB table")
    # Only when a MIB was supplied. Without one there is nothing to decode a
    # table *against*, and reporting that as an anomaly would make `--mib`
    # look optional-but-broken rather than required for this claim.
    if mib is not None and cfg.table_entries != cfg.table_entries_decoded:
        opaque = cfg.table_entries - cfg.table_entries_decoded
        cfg.anomalies.append(
            f"{opaque} of {cfg.table_entries} table-valued entries did not decode; "
            f"one of them was 22,044 of 45,226 bytes when this was written, so an "
            f"undecoded table is not a rounding error in the coverage claim")
    cfg.verdict = "consistent" if not cfg.anomalies else "SUSPECT"
    return cfg


def decode_file(path: str, offset: int, **kw) -> Config:
    with open(path, "rb") as fh:
        data = fh.read()
    return decode_region(data, offset, path=path,
                         source_sha256=hashlib.sha256(data).hexdigest(), **kw)


def to_markdown(cfg: Config) -> str:
    lines = [
        f"# {cfg.magic} @ {cfg.region_offset:#08x} — {cfg.role}",
        "",
        f"- source: `{cfg.path}`",
        f"- sha256: `{cfg.source_sha256}`",
        f"- compRate/compLen: {cfg.comp_rate} / {cfg.comp_len} "
        f"(buffer {cfg.comp_rate * cfg.comp_len})",
        f"- decompressed: {cfg.decompressed_len} bytes, "
        f"signature `{cfg.signature}` version `{cfg.version}`",
        f"- vendor checksum: {'PASS' if cfg.checksum_ok else 'FAIL'}"
        f" · ring-fill cross-check: {'agrees' if cfg.ring_fill_agrees else 'DISAGREES'}",
        f"- entries: {cfg.entry_count} (MIB table has {cfg.mib_records})"
        f" · unknown ids: {cfg.unknown_ids}",
        f"- table-valued entries: {cfg.table_entries_decoded}/{cfg.table_entries} "
        f"decoded, {cfg.nested_entries} nested entries below them",
        f"- disclosure mode: `{cfg.disclosure_mode}`",
        f"- verdict: **{cfg.verdict}**",
        "",
        "| id | name | len | kind | value |",
        "|---|---|---|---|---|",
    ]
    for e in cfg.entries:
        lines.append(f"| `{e.id_hex}` | {e.name} | {e.length} | {e.kind} | `{e.value}` |")
    for e in cfg.entries:
        if not e.table_valued:
            continue
        lines += ["", f"## {e.name} (`{e.id_hex}`) — {e.length} bytes", ""]
        lines.append(f"- {e.table_note or 'not decoded'}")
        if e.table_source:
            lines.append(f"- named by: {e.table_source}")
        for k, row in enumerate(e.rows):
            lines += ["", f"### {e.name}[{k}]", "",
                      "| id | name | len | kind | value |", "|---|---|---|---|---|"]
            for c in row:
                lines.append(f"| `{c.id_hex}` | {c.name} | {c.length} | "
                             f"{c.kind} | `{c.value}` |")
    if cfg.anomalies:
        lines += ["", "## Anomalies", ""]
        lines += [f"- {a}" for a in cfg.anomalies]
    return "\n".join(lines) + "\n"
