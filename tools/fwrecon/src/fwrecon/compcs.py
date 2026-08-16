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


def _classify(name: str, mode: str) -> tuple[str, str]:
    if mode == "open":
        return "open", "disclosure=open: self-purchased EOL unit, not in service"
    if any(k in name.upper() for k in _PER_UNIT):
        return "protect", "per-unit identifier; value replaced by sha256 under protect mode"
    return "open", "not a per-unit identifier"


# -------------------------------------------------------------------- decode

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
    names = {}
    if mib is not None:
        mib_entries = getattr(mib, "entries", []) or []
        for e in mib_entries:
            ident = e.id if isinstance(e.id, int) else int(str(e.id), 0)
            names.setdefault(ident, e.name)
        # Records, not distinct ids. The vendor's table binds 0x182 to two names
        # in both the 2015 and the 2018 build, so distinct-id count is one short
        # of the record count and comparing against it makes a correct decode
        # look like an off-by-one. mib-and-config-dat.md has the history.
        cfg.mib_records = len(mib_entries)
        cfg.mib_distinct_ids = len(names)
        cfg.mib_duplicate_ids = list(getattr(mib, "duplicate_ids", []) or [])

    off = 0
    while off + 4 <= len(body):
        ident, ln = struct.unpack_from(">HH", body, off)
        if ident == 0 and ln == 0:
            break
        if off + 4 + ln > len(body):
            raise CompcsError(
                f"TLV at payload offset {off} declares {ln} bytes, which runs "
                f"{off + 4 + ln - len(body)} bytes past the end of the payload. "
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
        cfg.entries.append(Entry(
            id=ident, name=name or f"<unknown id {ident:#x}>", length=ln, offset=off,
            raw=shown, value=rendered, kind=kind,
            table_valued=bool(ident & 0x8000),
            # Kept, never dropped. mib-and-config-dat.md records a duplicate id
            # that was first written off as the walk going too far and turned out
            # to be a defect in the vendor's own table. Discarding what the tool
            # does not recognise protects the tool's reputation at the result's
            # expense.
            unknown_id=not name,
            disclosure=mode, disclosure_reason=reason))
        off += 4 + ln

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
    cfg.verdict = "consistent" if not cfg.anomalies else "SUSPECT"
    return cfg


def decode_file(path: str, offset: int, **kw) -> Config:
    data = open(path, "rb").read()
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
        f"- disclosure mode: `{cfg.disclosure_mode}`",
        f"- verdict: **{cfg.verdict}**",
        "",
        "| id | name | len | kind | value |",
        "|---|---|---|---|---|",
    ]
    for e in cfg.entries:
        lines.append(f"| `{e.id_hex}` | {e.name} | {e.length} | {e.kind} | `{e.value}` |")
    if cfg.anomalies:
        lines += ["", "## Anomalies", ""]
        lines += [f"- {a}" for a in cfg.anomalies]
    return "\n".join(lines) + "\n"
