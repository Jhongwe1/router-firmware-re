"""Synthetic binaries built in-memory for the test suite.

Vendor firmware is not redistributable, so the tests cannot ship a real image.
Building the structures by hand is better anyway: each fixture encodes exactly
the property under test, including the awkward ones (a section-header-stripped
ELF, a truncated container) that a real sample would only give you by luck.
"""

from __future__ import annotations

import struct

ELF_BASE = 0x00400000


def build_mips_be_elf(*, strip_sections: bool = True,
                      imports: tuple[str, ...] = ("system", "strcpy"),
                      exports: tuple[str, ...] = ("main",),
                      needed: tuple[str, ...] = ("libc.so.0",),
                      exec_stack: bool = True) -> bytes:
    """Build a big-endian MIPS-I ELF32 shaped like a Realtek SDK binary.

    Layout is deliberately simple and self-describing: one RX LOAD covering the
    whole file mapped at ``ELF_BASE``, so file offset and virtual address differ
    by a constant and the vaddr->offset translation under test is exercised for
    real rather than trivially.
    """
    e = ">"
    off_phdr = 52
    n_phdr = 2 + (0 if exec_stack else 1)
    off_dyn = 0x80
    off_str = 0x180
    off_sym = 0x280

    # --- string table -----------------------------------------------------
    strtab = bytearray(b"\x00")
    str_off: dict[str, int] = {}
    for name in (*needed, *imports, *exports):
        if name in str_off:
            continue
        str_off[name] = len(strtab)
        strtab += name.encode() + b"\x00"

    # --- symbol table -----------------------------------------------------
    symtab = bytearray(struct.pack(e + "IIIBBH", 0, 0, 0, 0, 0, 0))  # index 0 is reserved
    for i, name in enumerate(imports):
        # SHN_UNDEF (st_shndx == 0) is what makes a symbol an import.
        #
        # st_value is deliberately NON-zero here, because that is what real MIPS
        # binaries look like: an undefined function carries the address of its
        # lazy-binding stub in .MIPS.stubs. Any classifier that also demands
        # st_value == 0 will mistake every imported function for an export, so
        # the fixture must reproduce the trap rather than the textbook case.
        stub_addr = ELF_BASE + 0x800 + i * 8
        symtab += struct.pack(e + "IIIBBH", str_off[name], stub_addr, 0, 0x12, 0, 0)
    for name in exports:
        symtab += struct.pack(e + "IIIBBH", str_off[name], ELF_BASE + 0x400, 4, 0x12, 0, 1)
    n_syms = 1 + len(imports) + len(exports)

    # --- dynamic section --------------------------------------------------
    DT_NEEDED, DT_STRTAB, DT_SYMTAB, DT_STRSZ, DT_SYMENT = 1, 5, 6, 10, 11
    DT_MIPS_SYMTABNO, DT_NULL = 0x70000011, 0
    dyn = bytearray()
    for name in needed:
        dyn += struct.pack(e + "iI", DT_NEEDED, str_off[name])
    dyn += struct.pack(e + "iI", DT_STRTAB, ELF_BASE + off_str)
    dyn += struct.pack(e + "iI", DT_SYMTAB, ELF_BASE + off_sym)
    dyn += struct.pack(e + "iI", DT_STRSZ, len(strtab))
    dyn += struct.pack(e + "iI", DT_SYMENT, 16)
    # MIPS has no DT_HASH-independent symbol count; this tag is the ABI's answer
    # and is what lets the parser enumerate symbols with no section headers.
    dyn += struct.pack(e + "iI", DT_MIPS_SYMTABNO, n_syms)
    dyn += struct.pack(e + "iI", DT_NULL, 0)

    total = off_sym + len(symtab)

    # --- program headers --------------------------------------------------
    PT_LOAD, PT_DYNAMIC, PT_GNU_STACK = 1, 2, 0x6474E551
    PF_X, PF_W, PF_R = 1, 2, 4
    phdrs = b""
    phdrs += struct.pack(e + "8I", PT_LOAD, 0, ELF_BASE, ELF_BASE,
                         total, total, PF_R | PF_X, 0x10000)
    phdrs += struct.pack(e + "8I", PT_DYNAMIC, off_dyn, ELF_BASE + off_dyn,
                         ELF_BASE + off_dyn, len(dyn), len(dyn), PF_R | PF_W, 4)
    if not exec_stack:
        phdrs += struct.pack(e + "8I", PT_GNU_STACK, 0, 0, 0, 0, 0, PF_R | PF_W, 4)

    # --- ELF header -------------------------------------------------------
    EM_MIPS, ET_EXEC, ELFCLASS32, ELFDATA2MSB = 8, 2, 1, 2
    # mips1 | o32 | noreorder | cpic — the flag combination seen on these images.
    e_flags = 0x00001005
    ident = bytes([0x7F]) + b"ELF" + bytes([ELFCLASS32, ELFDATA2MSB, 1, 0]) + b"\x00" * 8
    ehdr = ident + struct.pack(
        e + "HHIIIIIHHHHHH",
        ET_EXEC, EM_MIPS, 1,
        ELF_BASE + 0x400,        # e_entry
        off_phdr,                # e_phoff
        0 if strip_sections else total,   # e_shoff
        e_flags,
        52, 32, n_phdr,
        0 if strip_sections else 40,
        0 if strip_sections else 3,
        0 if strip_sections else 2,
    )

    buf = bytearray(total)
    buf[0:52] = ehdr
    buf[off_phdr:off_phdr + len(phdrs)] = phdrs
    buf[off_dyn:off_dyn + len(dyn)] = dyn
    buf[off_str:off_str + len(strtab)] = strtab
    buf[off_sym:off_sym + len(symtab)] = symtab
    return bytes(buf)


def build_squashfs_superblock(*, compression: int = 2, inodes: int = 582,
                              block_size: int = 131072,
                              mkfs_time: int = 0x802D2100,
                              bytes_used: int = 2_173_799) -> bytes:
    """A SquashFS 4.0 superblock — little-endian on disk by specification, even
    on big-endian hosts, which is why one appears inside a big-endian MIPS image."""
    block_log = block_size.bit_length() - 1
    sb = struct.pack(
        "<4sIIII" + "HHHH" + "HH" + "QQQQQQQQ",
        b"hsqs", inodes, mkfs_time, block_size, 28,
        compression, block_log, 0xC0, 3,
        4, 0,
        0x1234, bytes_used, 0, 0, 0, 0, 0, 0,
    )
    return sb + b"\x00" * (256 - len(sb))


def build_realtek_image(sections: list[tuple[bytes, int, int, bytes]],
                        trailer: bytes = b"") -> bytes:
    """Assemble sections as ``(tag, start_addr, burn_addr, payload)``."""
    out = bytearray()
    for tag, start, burn, payload in sections:
        out += tag + struct.pack(">3I", start, burn, len(payload))
        out += payload
    out += trailer
    return bytes(out)
