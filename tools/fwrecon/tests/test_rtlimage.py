"""Tests for the Realtek IMG_HEADER_T container parser."""

from __future__ import annotations

from fwrecon import rtlimage

from .fixtures import build_realtek_image, build_squashfs_superblock

LZMA_STUB = b"\x5d\x00\x00\x80\x00" + b"\x00" * 64
BZIP2_STUB = b"BZh91AY&SY" + b"\x00" * 64


def _two_section_image(trailer: bytes = b"TOTOLINK-N150RT-V2.1.0\n") -> bytes:
    return build_realtek_image(
        [
            (b"cr6c", 0x80C00000, 0x00010000, LZMA_STUB),
            (b"r6cr", 0x002D0000, 0x00180000, build_squashfs_superblock()),
        ],
        trailer=trailer,
    )


def test_walks_all_sections(tmp_path):
    p = tmp_path / "fw.web"
    p.write_bytes(_two_section_image())
    rep = rtlimage.parse(p)
    assert [s.tag for s in rep.sections] == ["cr6c", "r6cr"]


def test_header_fields_decoded_big_endian(tmp_path):
    p = tmp_path / "fw.web"
    p.write_bytes(_two_section_image())
    rep = rtlimage.parse(p)
    kernel, rootfs = rep.sections
    assert kernel.start_addr == 0x80C00000   # KSEG0 load address
    assert kernel.burn_addr == 0x00010000    # 64 KiB into flash
    assert rootfs.burn_addr == 0x00180000    # 1.5 MiB into flash


def test_sections_are_contiguous(tmp_path):
    """Each section's payload must end exactly where the next header begins.

    This is the self-consistency check that validates the assumed 16-byte header
    layout; if the field order were wrong the offsets would not chain.
    """
    p = tmp_path / "fw.web"
    p.write_bytes(_two_section_image())
    rep = rtlimage.parse(p)
    for a, b in zip(rep.sections, rep.sections[1:], strict=False):
        assert a.payload_offset + a.length == b.offset


def test_payload_types_identified(tmp_path):
    p = tmp_path / "fw.web"
    p.write_bytes(_two_section_image())
    rep = rtlimage.parse(p)
    assert rep.sections[0].payload_type.startswith("lzma")
    assert "squashfs" in rep.sections[1].payload_type


def test_trailer_captured(tmp_path):
    p = tmp_path / "fw.web"
    p.write_bytes(_two_section_image())
    rep = rtlimage.parse(p)
    assert rep.trailer == "TOTOLINK-N150RT-V2.1.0"
    assert rep.trailer_offset is not None


def test_no_trailer_is_fine(tmp_path):
    p = tmp_path / "fw.web"
    p.write_bytes(_two_section_image(trailer=b""))
    rep = rtlimage.parse(p)
    assert rep.trailer is None
    assert not rep.anomalies


def test_flash_map_and_minimum_size(tmp_path):
    p = tmp_path / "fw.web"
    p.write_bytes(_two_section_image())
    rep = rtlimage.parse(p)
    rootfs = rep.sections[1]
    assert rep.min_flash_size == rootfs.burn_addr + rootfs.length
    assert rep.min_flash_size > 1.5 * 1024 * 1024


def test_squashfs_superblock_parsed(tmp_path):
    p = tmp_path / "fw.web"
    p.write_bytes(_two_section_image())
    q = rtlimage.parse(p).sections[1].squashfs
    assert q is not None
    assert q.version == "4.0"
    assert q.compression == "lzma"
    assert q.inodes == 582
    assert q.block_size == 131072


def test_implausible_mkfs_time_flagged(tmp_path):
    """The vendor images carry a mkfs_time in 2038. That must be reported, not
    silently rendered as a date, because it means the image cannot be dated
    from its own metadata."""
    p = tmp_path / "fw.web"
    p.write_bytes(_two_section_image())
    q = rtlimage.parse(p).sections[1].squashfs
    assert q.anomalies
    assert "implausible" in q.anomalies[0]


def test_xz_compression_id(tmp_path):
    p = tmp_path / "fw.web"
    p.write_bytes(build_realtek_image(
        [(b"r6cr", 0, 0x180000, build_squashfs_superblock(compression=4))]))
    assert rtlimage.parse(p).sections[0].squashfs.compression == "xz"


def test_inner_scan_finds_lzma_behind_boot_stub(tmp_path):
    """The kernel section opens with raw MIPS code; the compressed payload only
    starts further in, so a leading-magic check alone would call it unknown."""
    stub = b"\x3c\x10\x80\xd3" * 64          # plausible-looking MIPS lui sled
    p = tmp_path / "fw.web"
    p.write_bytes(build_realtek_image(
        [(b"cr6c", 0x80C00000, 0x10000, stub + LZMA_STUB)]))
    sec = rtlimage.parse(p).sections[0]
    assert sec.payload_type == "raw/unrecognised"
    assert any("lzma" in f for f in sec.inner_findings)


def test_truncated_image_reports_anomaly_not_crash(tmp_path):
    """Observed on the archive.org copy of V2.1.2: the rootfs section's declared
    length runs 9 bytes past end of file."""
    data = bytearray(_two_section_image(trailer=b""))
    del data[-9:]
    p = tmp_path / "trunc.web"
    p.write_bytes(bytes(data))
    rep = rtlimage.parse(p)
    sec = rep.sections[-1]
    assert sec.anomalies
    assert "truncated" in sec.anomalies[0] or "exceeds" in sec.anomalies[0]
    assert sec.payload_actual == sec.length - 9


def test_bzip2_web_bundle_section(tmp_path):
    """The 2015 image carries an extra bzip2 'w6cg' region holding the web UI."""
    p = tmp_path / "fw.web"
    p.write_bytes(build_realtek_image(
        [(b"w6cg", 0x00010000, 0x00010000, BZIP2_STUB)]))
    sec = rtlimage.parse(p).sections[0]
    assert sec.tag == "w6cg"
    assert sec.payload_type == "bzip2"
    assert "web resource" in sec.description


def test_two_byte_gzip_magic_is_not_enough(tmp_path):
    """Regression: a bare \\x1f\\x8b fires constantly inside compressed data and
    reported a phantom gzip stream inside the 2015 LZMA kernel."""
    payload = b"\x3c\x10\x80\xd3" * 8 + b"\x1f\x8b\x00\x00" + b"\x00" * 32
    p = tmp_path / "fw.web"
    p.write_bytes(build_realtek_image([(b"cr6c", 0, 0x10000, payload)]))
    sec = rtlimage.parse(p).sections[0]
    assert not any("gzip" in f for f in sec.inner_findings)


def test_real_gzip_stream_is_still_found(tmp_path):
    payload = b"\x3c\x10\x80\xd3" * 8 + b"\x1f\x8b\x08\x00" + b"\x00" * 32
    p = tmp_path / "fw.web"
    p.write_bytes(build_realtek_image([(b"cr6c", 0, 0x10000, payload)]))
    sec = rtlimage.parse(p).sections[0]
    assert any("gzip" in f for f in sec.inner_findings)


def test_garbage_file_yields_no_sections(tmp_path):
    p = tmp_path / "garbage.bin"
    p.write_bytes(b"\x00\xff" * 512)
    rep = rtlimage.parse(p)
    assert rep.sections == []
    assert any("no Realtek" in a for a in rep.anomalies)


def test_unknown_tag_still_parsed_but_labelled(tmp_path):
    p = tmp_path / "fw.web"
    p.write_bytes(build_realtek_image([(b"zzzz", 0, 0, LZMA_STUB)]))
    sec = rtlimage.parse(p).sections[0]
    assert sec.tag == "zzzz"
    assert sec.description == "unknown section type"
