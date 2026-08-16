"""Tests for the w6cg web-resource bundle parser.

The layout was recovered by inspection, so most of these are about the walk
being *able to fail*: the archive carries no entry count and no terminator, and
"the strides added up to exactly the file length" is the only thing standing
between a correct parse and a plausible-looking wrong one.
"""

from __future__ import annotations

import bz2
import struct

import pytest

from fwrecon import webbundle

from .fixtures import build_realtek_image


def build_entry(name: bytes, content: bytes, *, declared: int | None = None) -> bytes:
    """One 64-byte header plus content. ``declared`` lies about the length."""
    header = bytearray(64)
    header[0:len(name)] = name
    struct.pack_into(">I", header, 0x3C,
                     len(content) if declared is None else declared)
    return bytes(header) + content


def build_bundle(entries: list[tuple[bytes, bytes]], trailing: bytes = b"") -> bytes:
    body = b"".join(build_entry(n, c) for n, c in entries) + trailing
    return bz2.compress(body)


def wrap(payload: bytes, *, tag: bytes = b"w6cg") -> bytes:
    return build_realtek_image([(tag, 0x00010000, 0x00010000, payload)])


DEFAULT = [
    (b"password.htm", b"<html>password</html>"),
    (b"syscmd.htm", b'<form action=/boafrm/formSysCmd method=POST name="formSysCmd">'),
    (b"icons/logo.gif", b"GIF89a" + b"\x00" * 40),
]


def _write(tmp_path, data: bytes, name: str = "fw.web"):
    p = tmp_path / name
    p.write_bytes(data)
    return p


def test_walks_every_entry_and_consumes_the_archive_exactly(tmp_path):
    p = _write(tmp_path, wrap(build_bundle(DEFAULT)))
    rep = webbundle.parse(p)
    assert [e.name for e in rep.entries] == ["password.htm", "syscmd.htm", "icons/logo.gif"]
    assert rep.bytes_unconsumed == 0
    assert rep.self_check == "exact"
    assert rep.anomalies == []


def test_length_field_is_big_endian(tmp_path):
    # 0x0100 bytes: little-endian misreading gives 1, which would derail. The
    # point of the test is that only one interpretation walks to the end.
    content = b"x" * 0x0100
    p = _write(tmp_path, wrap(build_bundle([(b"a.htm", content), (b"b.htm", b"y")])))
    rep = webbundle.parse(p)
    assert rep.self_check == "exact"
    assert rep.entries[0].length == 0x0100


def test_trailing_slack_is_reported_not_ignored(tmp_path):
    p = _write(tmp_path, wrap(build_bundle(DEFAULT, trailing=b"\x00" * 9)))
    rep = webbundle.parse(p)
    assert rep.self_check == "derailed"
    assert rep.bytes_unconsumed > 0
    assert rep.anomalies


def test_overlong_declared_length_derails_and_says_so(tmp_path):
    body = (build_entry(b"a.htm", b"short", declared=99999)
            + build_entry(b"b.htm", b"tail"))
    p = _write(tmp_path, wrap(bz2.compress(body)))
    rep = webbundle.parse(p)
    assert rep.self_check == "derailed"
    assert "derailed" in " ".join(rep.anomalies)
    # It stops at the bad entry rather than emitting a half-read one.
    assert [e.name for e in rep.entries] == []


def test_a_wrong_length_offset_cannot_walk_to_the_end(tmp_path, monkeypatch):
    """The self-check earns its keep only if a plausible wrong guess fails it."""
    p = _write(tmp_path, wrap(build_bundle(DEFAULT)))
    assert webbundle.parse(p).self_check == "exact"
    monkeypatch.setattr(webbundle, "LENGTH_OFFSET", 0x38)
    assert webbundle.parse(p).self_check == "derailed"


def test_grep_searches_content_and_not_names(tmp_path):
    body = (build_entry(b"syscmd.htm", b"<form action=/boafrm/formSysCmd>")
            + build_entry(b"language_en.js", b"/**** syscmd.htm ****/ var syscmd_x"))
    p = _write(tmp_path, wrap(bz2.compress(body)))

    hits = webbundle.grep(p, b"formSysCmd")
    assert [(e.name, n) for e, n in hits] == [("syscmd.htm", 1)]

    # A comment banner naming the page is not the page: it matches its own file
    # and must not be attributed to syscmd.htm.
    banner = webbundle.grep(p, b"syscmd.htm")
    assert [e.name for e, _ in banner] == ["language_en.js"]


def test_reads_the_section_out_of_a_raw_flash_dump(tmp_path):
    payload = build_bundle(DEFAULT)
    dump = bytearray(b"\xff" * 0x30000)
    dump[0x010000:0x010010] = b"w6cg" + struct.pack(">3I", 0x010000, 0x010000, len(payload))
    dump[0x010010:0x010010 + len(payload)] = payload
    p = _write(tmp_path, bytes(dump), "flash.bin")

    rep = webbundle.parse(p, at=0x010000)
    assert rep.self_check == "exact"
    assert rep.section_offset == 0x010000
    assert rep.find("syscmd.htm") is not None


def test_wrong_at_offset_is_an_error_not_a_guess(tmp_path):
    p = _write(tmp_path, wrap(build_bundle(DEFAULT)))
    with pytest.raises(ValueError, match="no w6cg signature"):
        webbundle.parse(p, at=0x1234)


def test_2020_family_image_without_a_bundle_says_so(tmp_path):
    kernel_only = build_realtek_image(
        [(b"cr6c", 0x80C00000, 0x010000, b"\x5d\x00\x00" * 8)])
    p = _write(tmp_path, kernel_only)
    with pytest.raises(ValueError, match="no w6cg section"):
        webbundle.parse(p)


def test_undecompressible_payload_is_reported_not_raised(tmp_path):
    p = _write(tmp_path, wrap(b"BZh9" + b"\x00" * 64))
    rep = webbundle.parse(p)
    assert rep.self_check == "undecompressible"
    assert rep.entries == []


def test_extracting_one_entry_returns_its_exact_bytes(tmp_path):
    p = _write(tmp_path, wrap(build_bundle(DEFAULT)))
    rep = webbundle.parse(p)
    e = rep.find("syscmd.htm")
    assert webbundle.contents(p, e) == DEFAULT[1][1]
