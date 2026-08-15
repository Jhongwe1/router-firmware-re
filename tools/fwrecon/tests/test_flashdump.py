"""Tests for the raw flash dump checker.

Every case here is a way a dump can be wrong while still being a well-formed
4 MiB file, because that is the only failure mode worth defending against: a
truncated or unreadable file announces itself, and a dump with a hole in it
does not.

The control case comes first and is not decoration. A suite of rejections can
pass with the checker broken - which is exactly what happened to a guard suite
in this repository on 2026-08-14.
"""

from __future__ import annotations

import json

from fwrecon import flashdump

from .fixtures import build_flash_dump


def test_a_clean_image_passes_every_hard_check():
    rep = flashdump.check_image(bytes(build_flash_dump()))
    assert rep.self_check == "OK", [c.name for c in rep.failed_hard]
    assert rep.failed_hard == []
    # tools/check-reports.py routes on this and refuses a committed report whose
    # self_check is not OK; a report that cannot say what produced it, or that
    # failed its own checks, is not evidence.
    assert rep.producer == "fwrecon:flashdump"
    assert rep.sha256
    assert rep.size == 4 * 1024 * 1024
    assert rep.image_end == 0x180000 + 0x1CA041
    assert rep.squashfs is not None
    assert rep.squashfs.compression == "lzma"
    assert rep.squashfs.inodes == 567


def test_a_2mb_part_aliasing_into_4mb_is_caught():
    # The published specification for this device says 2 MB. If the part really
    # were 2 MB, reading 4 MiB would return the lower half twice. This is the
    # one check that tests the part rather than its contents.
    img = build_flash_dump()
    img[len(img) // 2:] = img[:len(img) // 2]
    rep = flashdump.check_image(bytes(img))
    assert rep.self_check == "SUSPECT"
    assert any("alias" in c.name for c in rep.failed_hard)


def test_wrong_boot_bytes_are_caught():
    img = build_flash_dump()
    img[0:4] = b"\x00\x00\x00\x00"
    rep = flashdump.check_image(bytes(img))
    assert any(c.name.startswith("boot code") for c in rep.failed_hard)


def test_a_shifted_read_is_caught_at_every_anchor():
    # What a dropped chunk actually does: everything after the hole slides down.
    # A single anchor could miss it; the point of checking four independent
    # offsets is that a shift cannot satisfy them all.
    img = build_flash_dump()
    shifted = bytearray(img[:0x060000]) + bytearray(img[0x060000 + 0x1000:]) \
        + bytearray(b"\xff" * 0x1000)
    rep = flashdump.check_image(bytes(shifted))
    names = {c.name for c in rep.failed_hard}
    assert "cr6c signature" in names
    assert "SquashFS magic" in names


def test_container_length_mismatch_is_caught():
    img = build_flash_dump(cr6c_len=0x0F1000)
    rep = flashdump.check_image(bytes(img))
    assert any(c.name == "cr6c length" for c in rep.failed_hard)


def test_squashfs_inode_count_mismatch_is_caught():
    # 567 inodes is what the 2018 build has; 582 is the 2015 image and 827 the
    # 2020 one. Reading the wrong build back would show up here.
    img = build_flash_dump(inodes=582)
    rep = flashdump.check_image(bytes(img))
    assert any(c.name == "SquashFS inodes" for c in rep.failed_hard)


def test_a_written_tail_is_caught():
    img = build_flash_dump()
    img[0x3F0000] = 0x00
    rep = flashdump.check_image(bytes(img))
    assert any("erased" in c.name for c in rep.failed_hard)


def test_a_short_image_is_suspect_and_stops_early():
    rep = flashdump.check_image(bytes(build_flash_dump())[:0x100000])
    assert rep.self_check == "SUSPECT"
    assert rep.anomalies


def test_config_block_differences_are_soft_not_corruption():
    # COMPCS is the live configuration and the device rewrites it whenever
    # anything is saved. A difference there is information; it must not condemn
    # the dump the way a broken container header does.
    img = build_flash_dump()
    img[0x00C000:0x00C006] = b"XXXXXX"
    rep = flashdump.check_image(bytes(img))
    assert rep.self_check == "OK"
    assert any("COMPCS" in c.name for c in rep.failed_soft)


def test_per_unit_secrets_never_reach_the_output():
    # The rule that reaches photographs, boot logs and dumps alike: anything
    # true of *this unit* is withheld; only what is true of the model is
    # published. A checker that pastes the MAC into a report defeats the
    # redaction applied everywhere else.
    marker = b"MACMACMACMAC-PSK-WPSPIN"
    img = build_flash_dump(secret_marker=marker)
    rep = flashdump.check_image(bytes(img))

    text = flashdump.render_text(rep)
    blob = json.dumps(rep, default=lambda o: o.__dict__)

    assert marker.decode() not in text
    assert marker.decode() not in blob
    assert "withheld" in text
    # The digest is reported, so two reads can be compared without either being
    # exposed.
    assert rep.secret_regions[0]["sha256"] in blob
    assert rep.secret_regions[0]["printed"] is False


def test_the_gaps_w02_assumed_were_padding_are_measured_not_assumed():
    rep = flashdump.check_image(bytes(build_flash_dump()))
    assert len(rep.gaps) == 2
    for g in rep.gaps:
        assert g["bytes"] > 0
        assert "sha256" in g
        # The fixture pads with 0xFF, so the assumption holds there. On the real
        # dump this field is the answer to a question notes/flash-layout.md
        # explicitly left open.
        assert g["all_one_value"] is True
