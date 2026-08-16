"""Tests for the APMIB configuration-region decoder.

Every test that matters here makes the decoder *fail*. A config decoder that
returns a plausible table when it is wrong is the worst tool this project could
own: unlike a sink census, nothing downstream would ever contradict it, because
the decoded table *is* the evidence. So the specification was written as a list
of things that must produce an error rather than an answer, and each one has a
test below.

Two of these encode facts that came out of ``libapmib.so`` rather than out of
the data, and neither could have been guessed:

* :func:`test_bad_checksum_is_rejected` - the vendor sums the payload as signed
  bytes and requires zero. Nothing in the blob hints at it; it is in
  ``_apmib_dsconf`` at ``0x0001781c``. It is also the strongest correctness
  check available, because a single wrong byte anywhere in 45,218 fails it.
* :func:`test_decompressing_past_the_vendor_buffer_is_an_error` - ``Decode``
  writes into ``malloc(compRate * compLen)`` and does not bound-check. On the
  device that is a heap overflow driven by two header fields; here it is an
  error, and the error is the finding.

And one encodes a mistake this decoder actually made on first run against the
real firmware: :func:`test_one_trailing_byte_is_the_checksum_pad_not_an_anomaly`.
"""

from __future__ import annotations

import struct

import pytest

from fwrecon import compcs


# --------------------------------------------------------------- builders

def _compress_literal(payload: bytes) -> bytes:
    """Encode `payload` as all-literal LZSS: a flag byte of 0xff per 8 bytes.

    Deliberately not a real compressor. The decoder must accept a stream that
    uses only the literal path, and building one by hand keeps the test
    independent of any matching logic.
    """
    out = bytearray()
    for i in range(0, len(payload), 8):
        chunk = payload[i:i + 8]
        out.append((1 << len(chunk)) - 1)
        out += chunk
    return bytes(out)


def _body(entries: list[tuple[int, bytes]], sig: bytes = b"6g", ver: bytes = b"03") -> bytes:
    """A decompressed region: sig, ver, u32 len, TLVs, checksum pad."""
    tlv = b"".join(struct.pack(">HH", i, len(v)) + v for i, v in entries)
    payload = tlv + b"\x00"                      # placeholder for the pad byte
    fixed = payload[:-1] + bytes([(-sum(payload[:-1])) & 0xFF])
    return sig + ver + struct.pack(">I", len(fixed)) + fixed


def _region(body: bytes, magic: bytes = b"COMPCS", rate: int | None = None) -> bytes:
    comp = _compress_literal(body)
    if rate is None:
        # ceil(len(body) / len(comp)), the way the vendor sizes its buffer
        rate = (len(body) + len(comp) - 1) // len(comp) + 1
    return magic + struct.pack(">HI", rate, len(comp)) + comp


class _Mib:
    def __init__(self, entries):
        self.entries = entries
        self.duplicate_ids = []


class _E:
    def __init__(self, i, n):
        self.id, self.name = i, n


# ---------------------------------------------------------------- happy path

def test_round_trip_decodes_named_entries():
    mib = _Mib([_E(0xAA, "IP_ADDR"), _E(0xAB, "SUBNET_MASK")])
    blob = _region(_body([(0xAA, bytes([10, 1, 1, 1])), (0xAB, bytes([255, 255, 255, 0]))]))
    cfg = compcs.decode_region(blob, 0, mib=mib)
    assert cfg.magic == "COMPCS"
    assert cfg.signature == "6g" and cfg.version == "03"
    assert cfg.checksum_ok
    assert cfg.entry_count == 2
    assert cfg.unknown_ids == 0
    assert [e.name for e in cfg.entries] == ["IP_ADDR", "SUBNET_MASK"]
    assert cfg.entries[0].value == "10.1.1.1"
    assert cfg.entries[1].value == "255.255.255.0"
    assert cfg.verdict == "consistent"


def test_one_trailing_byte_is_the_checksum_pad_not_an_anomaly():
    """The first version flagged this and exited non-zero on a correct decode.

    libapmib's checksum pad sits inside the declared length, so a complete TLV
    walk always leaves exactly one byte over. Calling that "the stream is not
    fully understood" made a byte-perfect decode of the real firmware report
    SUSPECT -- a false alarm, which is how real alarms get ignored.
    """
    mib = _Mib([_E(0xAA, "IP_ADDR")])
    cfg = compcs.decode_region(_region(_body([(0xAA, b"\x01\x02\x03\x04")])), 0, mib=mib)
    assert cfg.trailing_bytes == 1
    assert cfg.verdict == "consistent"
    assert not cfg.anomalies


# ------------------------------------------------------- the failure contract

def test_wrong_magic_is_an_error_not_a_guess():
    blob = _region(_body([(1, b"\x00")]))
    with pytest.raises(compcs.CompcsError, match="no APMIB config magic"):
        compcs.decode_region(b"H601" + blob[4:], 0)


def test_comp_len_outside_the_vendor_bound_is_rejected():
    body = _body([(1, b"\x00")])
    comp = _compress_literal(body)
    bad = b"COMPCS" + struct.pack(">HI", 7, compcs.MAX_COMP_LEN + 1) + comp
    with pytest.raises(compcs.CompcsError, match="vendor's own bound"):
        compcs.decode_region(bad, 0)


def test_zero_comp_rate_is_rejected():
    body = _body([(1, b"\x00")])
    comp = _compress_literal(body)
    with pytest.raises(compcs.CompcsError, match="compRate is 0"):
        compcs.decode_region(b"COMPCS" + struct.pack(">HI", 0, len(comp)) + comp, 0)


def test_payload_running_past_the_image_is_rejected():
    body = _body([(1, b"\x00")])
    comp = _compress_literal(body)
    truncated = b"COMPCS" + struct.pack(">HI", 7, len(comp)) + comp[:-4]
    with pytest.raises(compcs.CompcsError, match="runs past the end"):
        compcs.decode_region(truncated, 0)


def test_decompressing_past_the_vendor_buffer_is_an_error():
    """compRate is an allocation hint; understating it overflows libapmib's heap.

    This needs a stream that actually *expands*, so an all-literal fixture will
    not do -- it can only ever shrink the ratio. A flag byte of 0x00 is eight
    back-references, each emitting up to 18 bytes from 2 input bytes, i.e. 17
    bytes in and 144 out. With compRate 1 the vendor would malloc 17 bytes and
    Decode would write 144 into it.
    """
    stream = bytes([0x00]) + bytes([0x00, 0x0F] * 8)     # 8 matches, max length
    assert len(stream) == 17
    blob = b"COMPCS" + struct.pack(">HI", 1, len(stream)) + stream
    with pytest.raises(compcs.CompcsError, match="past the vendor's own buffer"):
        compcs.decode_region(blob, 0)


def test_bad_signature_is_rejected():
    with pytest.raises(compcs.CompcsError, match="is not '6G' or '6g'"):
        compcs.decode_region(_region(_body([(1, b"\x00")], sig=b"XX")), 0)


def test_non_numeric_version_is_rejected():
    with pytest.raises(compcs.CompcsError, match="two ASCII digits"):
        compcs.decode_region(_region(_body([(1, b"\x00")], ver=b"ab")), 0)


def test_declared_length_disagreeing_with_the_decode_is_rejected():
    body = bytearray(_body([(1, b"\x00\x01\x02\x03")]))
    struct.pack_into(">I", body, 4, struct.unpack_from(">I", body, 4)[0] + 3)
    with pytest.raises(compcs.CompcsError, match="header declares"):
        compcs.decode_region(_region(bytes(body)), 0)


def test_bad_checksum_is_rejected():
    body = bytearray(_body([(0xAA, b"\x01\x02\x03\x04")]))
    body[-1] = (body[-1] + 1) & 0xFF          # one byte wrong, anywhere, is enough
    with pytest.raises(compcs.CompcsError, match="checksum"):
        compcs.decode_region(_region(bytes(body)), 0)


def test_tlv_running_past_the_payload_is_an_error_not_a_truncation():
    """The tempting failure is to return the entries walked so far. It is wrong:
    a short table that looks complete is exactly the artefact nobody can catch."""
    tlv = struct.pack(">HH", 0xAA, 64) + b"\x01\x02"     # claims 64, supplies 2
    payload = tlv + b"\x00"
    payload = payload[:-1] + bytes([(-sum(payload[:-1])) & 0xFF])
    body = b"6g03" + struct.pack(">I", len(payload)) + payload
    with pytest.raises(compcs.CompcsError, match="past the end of the payload"):
        compcs.decode_region(_region(body), 0)


def test_unknown_id_is_kept_and_flagged_never_dropped():
    """Discarding what the tool does not recognise protects the tool and loses
    the finding. mib-and-config-dat.md records a real duplicate id that was
    first written off as the walk overrunning."""
    mib = _Mib([_E(0xAA, "IP_ADDR")])
    cfg = compcs.decode_region(
        _region(_body([(0xAA, b"\x01\x02\x03\x04"), (0x7777, b"\xde\xad\xbe")])), 0, mib=mib)
    assert cfg.entry_count == 2
    assert cfg.unknown_ids == 1
    assert cfg.entries[1].unknown_id
    assert "0x7777" in cfg.entries[1].name
    assert cfg.entries[1].value == "deadbe"
    assert cfg.verdict == "SUSPECT"


def test_table_valued_ids_are_marked():
    cfg = compcs.decode_region(_region(_body([(0x8076, b"\x00")])), 0)
    assert cfg.entries[0].table_valued


def test_offset_outside_the_image_is_rejected():
    with pytest.raises(compcs.CompcsError, match="outside a"):
        compcs.decode_region(b"COMPCS" + b"\x00" * 6, 4096)


def test_unknown_disclosure_mode_is_rejected():
    with pytest.raises(compcs.CompcsError, match="unknown disclosure mode"):
        compcs.decode_region(_region(_body([(1, b"\x00")])), 0, disclosure="maybe")


# ----------------------------------------------------------------- disclosure

def test_protect_mode_never_emits_mac_derived_fields():
    """Today's decision is that this unit's values are published. That changed a
    *policy*, and the mechanism must survive it: the next device may not be mine.
    So `protect` keeps working and keeps its own test -- the one that fails if
    the capability is quietly deleted along with the policy."""
    known_mac = bytes.fromhex("001122334455")
    mib = _Mib([_E(0x10, "ELAN_MAC_ADDR"), _E(0xAA, "IP_ADDR")])
    blob = _region(_body([(0x10, known_mac), (0xAA, bytes([10, 1, 1, 1]))]))

    cfg = compcs.decode_region(blob, 0, mib=mib, disclosure="protect")
    rendered = " ".join(f"{e.raw} {e.value}" for e in cfg.entries)
    assert known_mac.hex() not in rendered
    assert "00:11:22:33:44:55" not in rendered
    assert cfg.entries[0].disclosure == "protect"
    assert cfg.entries[0].value.startswith("sha256:")
    # and a field that is not a per-unit identifier is untouched
    assert cfg.entries[1].value == "10.1.1.1"
    assert known_mac.hex() not in compcs.to_markdown(cfg)

    opened = compcs.decode_region(blob, 0, mib=mib, disclosure="open")
    assert opened.entries[0].value == "00:11:22:33:44:55"


def test_ring_fill_cross_check_is_reported():
    """Both fills agree on real firmware, which is what makes the check cheap.
    It is recorded rather than assumed so that a stream depending on
    uninitialised window bytes is visible instead of merely plausible."""
    cfg = compcs.decode_region(_region(_body([(0xAA, b"\x01\x02\x03\x04")])), 0)
    assert cfg.ring_fill_agrees is True
