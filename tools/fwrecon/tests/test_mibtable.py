"""Tests for the APMIB table recovery.

The load-bearing tests here are the ones that make the recovery *fail*. A tool
that walks a fixed stride through a binary and prints 413 plausible-looking rows
is easy to write and impossible to trust; the value is entirely in whether it
notices when it is wrong. Two of these encode mistakes the first version
actually made against the real firmware:

* :func:`test_missing_authg_family_is_not_a_failure` - V3.4.0 removed the whole
  ``AUTHG_*`` family, and anchoring recovery on ``AUTHG_IP_ADDR`` made the tool
  report "cannot locate the table" for a build whose table was intact.
* :func:`test_duplicate_id_is_reported_without_failing_recovery` - V2.1.2 binds
  id ``0x182`` to two names. That is a property of the vendor's table
  (``libapmib`` ships its own "detect duplicate id" check), and calling it a
  recovery failure would have discarded a real finding.
"""

from __future__ import annotations

import struct

import pytest

from fwrecon import mibtable


def _record(mib_id: int, name: str) -> bytes:
    rec = bytearray(mibtable.RECORD_SIZE)
    struct.pack_into(">I", rec, 0, mib_id)
    encoded = name.encode("ascii")
    assert len(encoded) < mibtable.NAME_SIZE
    rec[mibtable.NAME_OFFSET:mibtable.NAME_OFFSET + len(encoded)] = encoded
    return bytes(rec)


def _library(records: list[tuple[int, str]], *, pad: int = 256) -> bytes:
    """A stand-in for libapmib.so: filler, the table, filler."""
    body = b"".join(_record(i, n) for i, n in records)
    return (b"\x11" * pad) + body + (b"\x22" * pad)


def _write(tmp_path, data: bytes):
    p = tmp_path / "libapmib.so"
    p.write_bytes(data)
    return p


FULL = [
    (0xB6, "USER_NAME"),
    (0xB7, "USER_PASSWORD"),
    (0x1EC, "AUTHG_IP_ADDR"),
    (0x1ED, "AUTHG_USER_NAME"),
    (0x1EE, "AUTHG_PASS_WORD"),
]


def test_recovers_ids_and_names(tmp_path):
    t = mibtable.analyse(_write(tmp_path, _library(FULL)))
    assert t.verdict == "consistent"
    assert len(t.entries) == len(FULL)
    assert t.by_id(0xB6) == "USER_NAME"
    assert t.by_id(0x1EE) == "AUTHG_PASS_WORD"
    assert t.anchors_matched == 5


def test_report_names_its_own_input(tmp_path):
    # Same rule the Ghidra reports live under: a report that cannot say which
    # binary produced it is not evidence.
    t = mibtable.analyse(_write(tmp_path, _library(FULL)))
    assert len(t.source_sha256) == 64
    assert t.producer == "fwrecon:mib"


def test_missing_authg_family_is_not_a_failure(tmp_path):
    """V3.4.0 dropped AUTHG_*; its table is still perfectly recoverable."""
    without = [r for r in FULL if not r[1].startswith("AUTHG")]
    without += [(0xAA, "IP_ADDR"), (0xAB, "SUBNET_MASK"), (0xC5, "HOST_NAME")]
    t = mibtable.analyse(_write(tmp_path, _library(without)))
    assert t.verdict == "consistent"
    assert t.by_id(0x1EC) is None
    assert t.anchors_checked["0x1ec"] == "<absent from this build>"
    assert t.anchors_matched == 2


def test_wrong_name_on_a_known_id_fails(tmp_path):
    """The anchor check is the one thing tying the table to the firmware."""
    wrong = [(0xB6, "USER_NAME"), (0xB7, "SOMETHING_ELSE"), (0xAA, "IP_ADDR")]
    t = mibtable.analyse(_write(tmp_path, _library(wrong)))
    assert t.verdict == "SUSPECT"
    assert any("0xb7" in a for a in t.anomalies)


def test_no_anchor_present_is_unverified_not_clean(tmp_path):
    anonymous = [(0x10, "SOME_SETTING"), (0x11, "OTHER_SETTING"),
                 (0x12, "THIRD_SETTING")]
    t = mibtable.analyse(_write(tmp_path, _library(anonymous)))
    assert t.verdict == "SUSPECT"
    assert any("no anchor id was present" in a for a in t.anomalies)


def test_duplicate_id_is_reported_without_failing_recovery(tmp_path):
    dup = [*FULL, (0x182, "CUSTOM_PASSTHRU_ENABLED"), (0x182, "MLD_PROXY_DISABLED")]
    t = mibtable.analyse(_write(tmp_path, _library(dup)))
    assert t.verdict == "consistent"
    assert len(t.duplicate_ids) == 1
    assert "0x182" in t.duplicate_ids[0]


def test_two_comparable_runs_are_refused(tmp_path):
    """An ambiguous answer must not be resolved by picking the longer one."""
    a = _library(FULL, pad=64)
    b = b"".join(_record(0x300 + i, f"OTHER_{i}") for i in range(len(FULL)))
    t = mibtable.analyse(_write(tmp_path, a + b"\x33" * 64 + b))
    assert t.verdict == "SUSPECT"
    assert any("unambiguously" in x for x in t.anomalies)


def test_segments_count_chained_subtables(tmp_path):
    # A falling id is a sub-table boundary in libapmib, not damage. Only the
    # drops count: 0x10,0x11 | 0x08,0x09,0xb6 is two segments, because 0x09 ->
    # 0xb6 still ascends and so continues the same sub-table.
    chained = [(0x10, "A_ONE"), (0x11, "A_TWO"),
               (0x08, "B_ONE"), (0x09, "B_TWO"),
               (0xB6, "USER_NAME")]
    t = mibtable.analyse(_write(tmp_path, _library(chained)))
    assert t.segments == 2

    three = [*chained, (0x02, "C_ONE"), (0x03, "C_TWO")]
    assert mibtable.analyse(_write(tmp_path, _library(three))).segments == 3


def test_table_valued_ids_do_not_look_like_a_boundary(tmp_path):
    # IPFILTER_ENABLED 0x74 sits beside IPFILTER_TBL 0x8076: bit 15 marks a
    # table-valued entry, so ordering is judged on the masked id.
    flagged = [(0xB6, "USER_NAME"), (0x74, "IPFILTER_ENABLED"),
               (0x8076, "IPFILTER_TBL")]
    t = mibtable.analyse(_write(tmp_path, _library(flagged)))
    assert t.segments == 2      # only the 0xb6 -> 0x74 drop


@pytest.mark.parametrize("junk", [b"", b"\x00" * 4096, b"not an elf at all"])
def test_nothing_recoverable_says_so(tmp_path, junk):
    t = mibtable.analyse(_write(tmp_path, junk))
    assert t.verdict == "SUSPECT"
    assert t.entries == []
