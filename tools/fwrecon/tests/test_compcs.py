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

from fwrecon import compcs, mibtable

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


# The real dataclasses, not stand-ins. A test double for the MIB table would
# have to reimplement `count` from total_size/element_size, and a reimplemented
# invariant is one that can quietly stop matching the code it is checking.

def _Mib(entries, sub_tables=None):
    return mibtable.MibTable(entries=list(entries),
                             sub_tables=list(sub_tables or []))


def _E(i, n, *, total=0, element=0, kind=0):
    return mibtable.MibEntry(id=i, name=n, offset=0, type=kind,
                             total_size=total, declared_size=total,
                             element_size=element)


def _Sub(entries, offset=0x1000):
    ents = list(entries)
    return mibtable.MibSubTable(offset=offset, record_count=len(ents), entries=ents)


def _body_tlvs(entries: list[tuple[int, bytes]]) -> bytes:
    return b"".join(struct.pack(">HH", i, len(v)) + v for i, v in entries)


def _table_value(rows: list[list[tuple[int, bytes]]]) -> bytes:
    """The on-flash form of a table-valued entry: each element's TLV stream,
    concatenated. No count and no terminator - the geometry is in libapmib."""
    return b"".join(_body_tlvs(r) for r in rows)


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


# ------------------------------------------------------- table-valued entries
#
# `WLAN_ROOT` was 22,044 of the 45,226 decompressed bytes and was reported as a
# hex string until 2026-08-21, so `notes/compcs-decode.md` described a region as
# decoded while half of it had never been walked. These tests are the shape of
# that decode, and every one of them except the first two makes it refuse.

_TWO_FIELDS = _Sub([_E(0x4BB, "WLAN_ACL_ADDR_MACADDR", total=6, element=1),
                    _E(0x4BC, "WLAN_ACL_ADDR_COMMENT", total=4, element=1)])
#: two elements of (6 + 4) struct bytes = 20, plus 4 x 4 header bytes = 36
_TWO_ROWS = [[(0x4BB, b"\x00\x11\x22\x33\x44\x55"), (0x4BC, b"abc\x00")],
             [(0x4BB, b"\x66\x77\x88\x99\xaa\xbb"), (0x4BC, b"xyz\x00")]]
#: the same two elements with every field two bytes longer than libapmib
#: declares. Geometry that agrees on the element size and disagrees on the byte
#: total is the only way to reach the header arithmetic on its own.
_FAT_ROWS = [[(0x4BB, b"\x00\x11\x22\x33\x44\x55\x66\x77"), (0x4BC, b"abcde\x00")],
             [(0x4BB, b"\x66\x77\x88\x99\xaa\xbb\xcc\xdd"), (0x4BC, b"vwxyz\x00")]]


def _tbl_mib(*, total=20, element=10, sub=None):
    return _Mib([_E(0x8036, "MACAC_ADDR", total=total, element=element, kind=0x11)],
                [sub if sub is not None else _TWO_FIELDS])


def test_table_valued_entry_decodes_into_named_rows():
    cfg = compcs.decode_region(
        _region(_body([(0x8036, _table_value(_TWO_ROWS))])), 0, mib=_tbl_mib())
    e = cfg.entries[0]
    assert cfg.verdict == "consistent", cfg.anomalies
    assert cfg.table_entries == 1 and cfg.table_entries_decoded == 1
    assert len(e.rows) == 2
    assert [c.name for c in e.rows[0]] == ["WLAN_ACL_ADDR_MACADDR",
                                           "WLAN_ACL_ADDR_COMMENT"]
    assert e.rows[0][0].value == "00:11:22:33:44:55"
    assert e.rows[1][1].value == "xyz"
    assert "run at 0x1000" in e.table_source
    assert cfg.nested_entries == 4


def test_no_mib_leaves_a_table_undescended_without_calling_it_an_anomaly():
    """Without --mib nothing says how many elements there are. That is the
    caller choosing not to supply a source, not a defect, and it must not read
    as one."""
    cfg = compcs.decode_region(
        _region(_body([(0x8036, _table_value(_TWO_ROWS))])), 0)
    assert cfg.entries[0].rows == []
    assert "no --mib" in cfg.entries[0].table_note
    assert not any("did not decode" in a for a in cfg.anomalies)


def test_table_with_no_matching_sub_table_is_refused():
    mib = _tbl_mib(sub=_Sub([_E(0x999, "SOMETHING_ELSE", total=10, element=1)]))
    cfg = compcs.decode_region(
        _region(_body([(0x8036, _table_value(_TWO_ROWS))])), 0, mib=mib)
    assert cfg.entries[0].rows == []
    assert "no sub-table" in cfg.entries[0].table_note
    assert cfg.verdict == "SUSPECT"


def test_two_disagreeing_sub_tables_are_refused():
    """Same ids, different names. The decoder must not pick the nearest."""
    other = _Sub([_E(0x4BB, "MECH_ACL_MACADDR", total=6, element=1),
                  _E(0x4BC, "MECH_ACL_COMMENT", total=4, element=1)], offset=0x2000)
    mib = _Mib([_E(0x8036, "MACAC_ADDR", total=20, element=10, kind=0x11)],
               [_TWO_FIELDS, other])
    cfg = compcs.decode_region(
        _region(_body([(0x8036, _table_value(_TWO_ROWS))])), 0, mib=mib)
    assert cfg.entries[0].rows == []
    assert "disagree about the names" in cfg.entries[0].table_note
    assert cfg.verdict == "SUSPECT"


def test_two_identical_sub_tables_are_not_an_ambiguity():
    """libapmib carries PROFILE_SSID..PROFILE_PSK_FORMAT twice, at 0xb130 and
    0xb43c, byte-identical. Refusing that would be refusing to choose between
    two spellings of one word - and it did refuse, on the real firmware, before
    this case existed."""
    twin = _Sub([_E(0x4BB, "WLAN_ACL_ADDR_MACADDR", total=6, element=1),
                 _E(0x4BC, "WLAN_ACL_ADDR_COMMENT", total=4, element=1)],
                offset=0x2000)
    mib = _Mib([_E(0x8036, "MACAC_ADDR", total=20, element=10, kind=0x11)],
               [_TWO_FIELDS, twin])
    cfg = compcs.decode_region(
        _region(_body([(0x8036, _table_value(_TWO_ROWS))])), 0, mib=mib)
    assert cfg.verdict == "consistent", cfg.anomalies
    assert len(cfg.entries[0].rows) == 2
    assert "one of 2 identical runs" in cfg.entries[0].table_source


def test_element_size_disagreeing_with_the_sub_table_is_refused():
    """The binary says one element is 10 bytes and the sub-table members sum to
    10. Change the declaration and the two sources no longer corroborate."""
    cfg = compcs.decode_region(
        _region(_body([(0x8036, _table_value(_TWO_ROWS))])), 0,
        mib=_tbl_mib(total=22, element=11))
    assert cfg.entries[0].rows == []
    assert "declares element_size 11" in cfg.entries[0].table_note
    assert cfg.verdict == "SUSPECT"


def test_element_count_disagreeing_with_the_tlv_count_is_refused():
    cfg = compcs.decode_region(
        _region(_body([(0x8036, _table_value(_TWO_ROWS))])), 0,
        mib=_tbl_mib(total=30, element=10))          # says 3 elements, data has 2
    assert cfg.entries[0].rows == []
    assert "4 TLVs against 2 fields x 3 elements" in cfg.entries[0].table_note
    assert cfg.verdict == "SUSPECT"


def test_header_arithmetic_that_does_not_close_is_refused():
    """Element size agrees, element count agrees, and the bytes still do not.

    Each field here carries two bytes more than libapmib declares, so the walk
    produces exactly the four TLVs the geometry predicts while the value is 44
    bytes where 20 struct + 4x4 headers = 36. Without this check the decode
    would have looked right and been silently long.
    """
    cfg = compcs.decode_region(
        _region(_body([(0x8036, _table_value(_FAT_ROWS))])), 0, mib=_tbl_mib())
    assert cfg.entries[0].rows == []
    assert "= 36, but the value is 44" in cfg.entries[0].table_note
    assert cfg.verdict == "SUSPECT"


def test_nested_headers_are_charged_to_the_arithmetic():
    """The bug this check was written with, reproduced small.

    The first version charged four header bytes per *top-level* TLV, so a table
    holding a table came out short - on the real firmware, `WLAN_ROOT` by 3,696
    bytes, which is exactly 6 blocks x 154 nested TLVs x 4. Here: an outer table
    of one element whose one field is itself a two-element table.
    """
    inner = _table_value(_TWO_ROWS)                      # 36 bytes, 4 TLVs
    outer_value = _body_tlvs([(0x8036, inner)])          # 4 + 36 = 40 bytes
    inner_sub = _Sub([_E(0x8036, "MACAC_ADDR", total=20, element=10, kind=0x11)],
                     offset=0x3000)
    mib = _Mib([_E(0x8065, "WLAN_ROOT", total=20, element=20, kind=0x10)],
               [inner_sub, _TWO_FIELDS])
    cfg = compcs.decode_region(_region(_body([(0x8065, outer_value)])), 0, mib=mib)
    # 20 struct bytes + 5 TLVs (1 outer + 4 inner) x 4 = 40 == len(outer_value)
    assert cfg.verdict == "consistent", cfg.anomalies
    assert "20 struct + 20 headers" in cfg.entries[0].table_note
    assert len(cfg.entries[0].rows) == 1
    assert len(cfg.entries[0].rows[0][0].rows) == 2       # and it descended again


def test_nesting_deeper_than_the_limit_is_refused_not_recursed():
    """A backstop, exercised directly.

    Reaching it through the public path would need five nested levels whose
    geometry all closes, because every check above fires first - so the guard
    exists for a stream that lies *consistently*, and calling the private
    function is the only way to present one without also having to assert that
    such a stream is constructible.
    """
    entry = compcs.Entry(id=0x8036, name="MACAC_ADDR", length=0, offset=0,
                         raw="", value="", kind="bytes", table_valued=True)
    cfg = compcs.Config()
    compcs._decode_table(entry, b"", cfg, None, _tbl_mib(), "open",
                         compcs.MAX_TABLE_DEPTH)
    assert entry.rows == []
    assert "nesting deeper" in entry.table_note
    assert any("nesting exceeded" in a for a in cfg.anomalies)


def test_an_undecoded_table_is_counted_and_named_in_the_verdict():
    """The coverage claim is the point. A region reported as decoded while one
    of its entries is half the payload is the exact failure this replaces."""
    mib = _tbl_mib(sub=_Sub([_E(0x999, "SOMETHING_ELSE", total=10, element=1)]))
    cfg = compcs.decode_region(
        _region(_body([(0x8036, _table_value(_TWO_ROWS))])), 0, mib=mib)
    assert cfg.table_entries == 1
    assert cfg.table_entries_decoded == 0
    assert any("table-valued entries did not decode" in a for a in cfg.anomalies)


def test_a_decoded_table_does_not_repeat_its_bytes():
    """The parent value is exactly the concatenation of its rows, so carrying
    both asserts the same bytes twice. Every byte stays present once, in the
    leaf that owns it, and the elision is a flag rather than a surprise."""
    value = _table_value(_TWO_ROWS)
    cfg = compcs.decode_region(
        _region(_body([(0x8036, value)])), 0, mib=_tbl_mib())
    e = cfg.entries[0]
    assert e.raw == "" and e.raw_elided_into_rows
    assert e.value == "2 elements, decoded into rows"
    assert e.length == len(value)          # the length is still stated
    # and the bytes are all still there, once
    rebuilt = b"".join(
        struct.pack(">HH", c.id, c.length) + bytes.fromhex(c.raw)
        for row in e.rows for c in row)
    assert rebuilt == value


def test_a_refused_table_keeps_its_bytes():
    """A table that did not decode must keep its hex: that is the only form the
    evidence has left, and eliding it would hide the undecoded half instead of
    reporting it."""
    mib = _tbl_mib(sub=_Sub([_E(0x999, "SOMETHING_ELSE", total=10, element=1)]))
    cfg = compcs.decode_region(
        _region(_body([(0x8036, _table_value(_TWO_ROWS))])), 0, mib=mib)
    e = cfg.entries[0]
    assert not e.raw_elided_into_rows
    assert e.raw == _table_value(_TWO_ROWS).hex()
