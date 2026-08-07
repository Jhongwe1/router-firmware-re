"""Tests for the ELF reader.

The load-bearing test here is :func:`test_sstripped_binary_still_yields_imports`.
It encodes the bug that motivated writing this module at all: ``readelf`` reports
nothing for a section-header-stripped binary and exits 0, so a wrapper around it
silently concludes "no dangerous imports".
"""

from __future__ import annotations

import struct

import pytest

from fwrecon import elf

from .fixtures import ELF_BASE, build_mips_be_elf


@pytest.fixture
def stripped(tmp_path):
    p = tmp_path / "boa"
    p.write_bytes(build_mips_be_elf(strip_sections=True))
    return p


def test_identifies_big_endian_mips_o32(stripped):
    r = elf.analyse(stripped)
    assert r.is_elf
    assert r.endian == "big"
    assert r.machine == "MIPS"
    assert r.mips_isa == "mips1"
    assert r.mips_abi == "o32"
    assert "cpic" in r.mips_flags


def test_load_base_and_entry(stripped):
    r = elf.analyse(stripped)
    assert r.load_base == ELF_BASE
    assert r.entry == ELF_BASE + 0x400


def test_sstripped_binary_still_yields_imports(stripped):
    """A binary with e_shnum == 0 must still give up its dynamic symbols.

    This is the whole point of parsing PT_DYNAMIC rather than .dynsym.
    """
    r = elf.analyse(stripped)
    assert r.section_headers is False, "fixture should have no section headers"
    assert "system" in r.imports
    assert "strcpy" in r.imports
    assert r.sinks["command_exec"] == ["system"]
    assert r.sinks["unbounded_copy"] == ["strcpy"]


def test_exports_separated_from_imports(stripped):
    r = elf.analyse(stripped)
    assert "main" in r.exports
    assert "main" not in r.imports


def test_mips_stub_address_does_not_hide_an_import(stripped):
    """Regression: undefined MIPS symbols carry a .MIPS.stubs address in
    st_value, so classification must key on st_shndx alone.

    Keying on st_value == 0 as well reclassified 165 of /bin/boa's 181 imports
    as exports on the real 2015 image — system() and strcpy() among them.
    """
    r = elf.analyse(stripped)
    assert "system" in r.imports
    assert "system" not in r.exports
    assert len(r.imports) == 2
    assert len(r.exports) == 1


def test_needed_libraries(stripped):
    r = elf.analyse(stripped)
    assert r.needed == ["libc.so.0"]


def test_section_headers_detected_when_present(tmp_path):
    p = tmp_path / "with_sections"
    p.write_bytes(build_mips_be_elf(strip_sections=False))
    assert elf.analyse(p).section_headers is True


def test_missing_gnu_stack_reported_as_absent_not_false(stripped):
    """`None` and `False` mean different things and must not be conflated:
    absent marker => kernel maps an executable stack; present-and-non-exec => NX on."""
    r = elf.analyse(stripped)
    assert r.hardening.nx is None


def test_gnu_stack_present_gives_nx_true(tmp_path):
    p = tmp_path / "nx"
    p.write_bytes(build_mips_be_elf(exec_stack=False))
    assert elf.analyse(p).hardening.nx is True


def test_no_canary_or_fortify_in_plain_build(stripped):
    h = elf.analyse(stripped).hardening
    assert h.canary is False
    assert h.fortify is False
    assert h.relro == "none"


def test_canary_detected_from_import(tmp_path):
    p = tmp_path / "canary"
    p.write_bytes(build_mips_be_elf(imports=("system", "__stack_chk_fail")))
    assert elf.analyse(p).hardening.canary is True


def test_fortify_detected_from_chk_import(tmp_path):
    p = tmp_path / "fortified"
    p.write_bytes(build_mips_be_elf(imports=("__sprintf_chk",)))
    assert elf.analyse(p).hardening.fortify is True


def test_non_elf_file_reports_error_rather_than_raising(tmp_path):
    p = tmp_path / "notelf"
    p.write_bytes(b"#!/bin/sh\necho hi\n")
    r = elf.analyse(p)
    assert r.is_elf is False
    assert "not an ELF" in r.error


def test_truncated_elf_does_not_raise(tmp_path):
    p = tmp_path / "trunc"
    p.write_bytes(build_mips_be_elf()[:40])
    r = elf.analyse(p)
    assert r.is_elf is False


def test_missing_file_reports_error(tmp_path):
    r = elf.analyse(tmp_path / "nope")
    assert r.is_elf is False
    assert "read failed" in r.error


def test_vaddr_translation_round_trip():
    data = build_mips_be_elf()
    r = elf.Elf32Reader(data)
    assert r.vaddr_to_offset(ELF_BASE) == 0
    assert r.vaddr_to_offset(ELF_BASE + 0x100) == 0x100
    # Outside every LOAD segment there is no mapping, and the reader must say so
    # rather than returning a plausible-looking wrong offset.
    assert r.vaddr_to_offset(0x10000000) is None


def test_little_endian_binary_parses_too(tmp_path):
    """Endianness is read from e_ident, not assumed, so flip one byte and the
    header fields must still decode — here by checking it does NOT decode as BE."""
    data = bytearray(build_mips_be_elf())
    data[5] = 1  # ELFDATA2LSB
    p = tmp_path / "le"
    p.write_bytes(bytes(data))
    r = elf.analyse(p)
    assert r.endian == "little"
    # The rest of the file is still big-endian, so the byte-swapped read must
    # produce different values than the BE parse - proving endianness is applied.
    assert r.entry != ELF_BASE + 0x400


def test_elf64_is_rejected_explicitly(tmp_path):
    data = bytearray(build_mips_be_elf())
    data[4] = 2  # ELFCLASS64
    p = tmp_path / "elf64"
    p.write_bytes(bytes(data))
    r = elf.analyse(p)
    assert r.is_elf is False
    assert "ELF32" in r.error


def test_rwx_segment_flagged(tmp_path):
    """A LOAD segment that is both writable and executable should surface."""
    data = bytearray(build_mips_be_elf())
    # PT_LOAD is the first program header at offset 52; p_flags is its 7th u32.
    flags_off = 52 + 6 * 4
    struct.pack_into(">I", data, flags_off, 0x7)  # RWX
    p = tmp_path / "rwx"
    p.write_bytes(bytes(data))
    r = elf.analyse(p)
    assert r.hardening.rwx_segments
    assert "RWX" in r.hardening.rwx_segments[0]
