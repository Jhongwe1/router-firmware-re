"""Minimal, dependency-free ELF32 reader aimed at embedded firmware binaries.

Why not just shell out to ``readelf``?
-------------------------------------
Because ``readelf`` answers questions using the *section header table*, and
embedded vendors routinely strip it. The TOTOLINK N150RT V3.4.0 build ships a
``/bin/boa`` processed with ``sstrip``: ``e_shnum == 0``. Against that binary::

    $ readelf --dyn-syms bin/boa      # prints nothing at all, exit status 0
    $ nm -D bin/boa | grep system     # U system

A tool that silently returns an empty list when it cannot answer is worse than
one that errors, because the caller records "no dangerous imports" and moves on.
That actually happened during this project's first analysis pass, and it is the
reason this module exists.

So this reader deliberately works the way the *dynamic loader* does: everything
comes from the program headers and ``PT_DYNAMIC``, which cannot be stripped
without breaking the binary. Section headers are used only when present, and
only as a bonus.

MIPS note: MIPS has no ``DT_HASH``-independent way to size ``.dynsym``, so the
o32 ABI defines ``DT_MIPS_SYMTABNO`` (0x70000011) to carry the symbol count
directly. That tag is what makes symbol enumeration possible here.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------- constants

ELFCLASS32, ELFCLASS64 = 1, 2
ELFDATA2LSB, ELFDATA2MSB = 1, 2

ET_NAMES = {0: "NONE", 1: "REL", 2: "EXEC", 3: "DYN", 4: "CORE"}

# Only the machines plausibly met in consumer-router firmware are named; the
# rest are reported numerically rather than guessed at.
EM_NAMES = {
    2: "SPARC", 3: "x86", 8: "MIPS", 20: "PowerPC", 40: "ARM",
    62: "x86-64", 183: "AArch64", 243: "RISC-V",
}
EM_MIPS = 8

PT_LOAD, PT_DYNAMIC, PT_INTERP = 1, 2, 3
PT_GNU_EH_FRAME, PT_GNU_STACK, PT_GNU_RELRO = 0x6474E550, 0x6474E551, 0x6474E552

DT_NULL, DT_NEEDED, DT_STRTAB, DT_SYMTAB = 0, 1, 5, 6
DT_STRSZ, DT_SYMENT, DT_SONAME, DT_RPATH = 10, 11, 14, 15
DT_TEXTREL, DT_BIND_NOW, DT_RUNPATH, DT_FLAGS = 22, 24, 29, 30
DT_MIPS_SYMTABNO = 0x70000011

DF_BIND_NOW = 0x08

PF_X, PF_W, PF_R = 0x1, 0x2, 0x4

# MIPS e_flags bits worth surfacing: they pin down the ABI and ISA level, which
# is exactly what you need to pick the right Ghidra language spec and the right
# qemu-user binary.
EF_MIPS_NOREORDER = 0x00000001
EF_MIPS_PIC = 0x00000002
EF_MIPS_CPIC = 0x00000004
EF_MIPS_ABI_O32 = 0x00001000
EF_MIPS_ARCH_MASK = 0xF0000000
EF_MIPS_ARCH_NAMES = {
    0x00000000: "mips1", 0x10000000: "mips2", 0x20000000: "mips3",
    0x30000000: "mips4", 0x40000000: "mips5", 0x50000000: "mips32",
    0x60000000: "mips64", 0x70000000: "mips32r2", 0x80000000: "mips64r2",
}

# Imports that make a binary worth a closer look. Split by the kind of bug they
# tend to produce so the report can group them meaningfully rather than dumping
# one flat list.
SINKS: dict[str, tuple[str, ...]] = {
    "command_exec": ("system", "popen", "execl", "execlp", "execle", "execv",
                     "execvp", "execve", "doSystem", "twsystem"),
    "unbounded_copy": ("strcpy", "strcat", "sprintf", "vsprintf", "gets",
                       "wcscpy", "wcscat"),
    "bounded_but_error_prone": ("strncpy", "strncat", "snprintf", "vsnprintf",
                                "memcpy", "memmove", "alloca"),
    "format_string": ("printf", "fprintf", "syslog", "vprintf", "vfprintf"),
    "input_parse": ("scanf", "sscanf", "fscanf", "atoi", "strtol"),
}

# Presence of these imports is evidence a hardening feature is compiled in.
CANARY_MARKERS = ("__stack_chk_fail", "__stack_chk_guard", "__stack_smash_handler")


# ---------------------------------------------------------------- data model

@dataclass(frozen=True)
class Segment:
    type: int
    offset: int
    vaddr: int
    filesz: int
    memsz: int
    flags: int

    @property
    def perms(self) -> str:
        return ("R" if self.flags & PF_R else "-") + \
               ("W" if self.flags & PF_W else "-") + \
               ("X" if self.flags & PF_X else "-")


@dataclass
class Hardening:
    nx: bool | None            # None = no PT_GNU_STACK, i.e. toolchain predates it
    pie: bool
    relro: str                 # "none" | "partial" | "full"
    canary: bool
    fortify: bool
    rwx_segments: list[str] = field(default_factory=list)
    text_relocations: bool = False


@dataclass
class ElfReport:
    path: str
    is_elf: bool
    error: str | None = None

    bits: int = 0
    endian: str = ""           # "big" | "little"
    machine: str = ""
    machine_id: int = 0
    type: str = ""
    entry: int = 0
    load_base: int = 0
    interpreter: str | None = None
    soname: str | None = None
    section_headers: bool = True   # False => sstrip'd
    build_id: str | None = None

    mips_isa: str | None = None
    mips_abi: str | None = None
    mips_flags: list[str] = field(default_factory=list)

    needed: list[str] = field(default_factory=list)
    rpath: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    sinks: dict[str, list[str]] = field(default_factory=dict)
    segments: list[Segment] = field(default_factory=list)
    hardening: Hardening | None = None

    def sink_count(self) -> int:
        return sum(len(v) for v in self.sinks.values())


# ---------------------------------------------------------------- reader

class Elf32Reader:
    """Parses an ELF32 file using program headers only.

    Raises ``ValueError`` for anything that is not a 32-bit ELF; callers that
    sweep a whole filesystem should use :func:`analyse` instead, which converts
    that into a report carrying an ``error``.
    """

    def __init__(self, data: bytes, path: str = "<memory>"):
        self.data = data
        self.path = path

        if len(data) < 52 or data[:4] != b"\x7fELF":
            raise ValueError("not an ELF file")
        if data[4] != ELFCLASS32:
            raise ValueError(f"not ELF32 (ei_class={data[4]})")

        self.endian = "big" if data[5] == ELFDATA2MSB else "little"
        self._e = ">" if self.endian == "big" else "<"

        (self.e_type, self.e_machine, _ver, self.e_entry, self.e_phoff,
         self.e_shoff, self.e_flags, _ehsize, self.e_phentsize, self.e_phnum,
         _shentsize, self.e_shnum, _shstrndx) = struct.unpack_from(
            self._e + "HHIIIIIHHHHHH", data, 16)

        self.segments = self._read_segments()

    # -- low level -----------------------------------------------------------

    def _read_segments(self) -> list[Segment]:
        out: list[Segment] = []
        for i in range(self.e_phnum):
            off = self.e_phoff + i * self.e_phentsize
            if off + 32 > len(self.data):
                break
            p_type, p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz, p_flags, _al = \
                struct.unpack_from(self._e + "8I", self.data, off)
            out.append(Segment(p_type, p_offset, p_vaddr, p_filesz, p_memsz, p_flags))
        return out

    def vaddr_to_offset(self, vaddr: int) -> int | None:
        """Translate a virtual address to a file offset via the LOAD segments.

        This is the piece that makes section headers unnecessary: DT_* entries
        hold virtual addresses, and the LOAD segments are the authoritative
        vaddr->offset map that the kernel itself uses.
        """
        for s in self.segments:
            if s.type == PT_LOAD and s.vaddr <= vaddr < s.vaddr + s.filesz:
                return s.offset + (vaddr - s.vaddr)
        return None

    def _cstr(self, offset: int, limit: int = 4096) -> str:
        end = self.data.find(b"\x00", offset, offset + limit)
        if end < 0:
            end = min(offset + limit, len(self.data))
        return self.data[offset:end].decode("utf-8", "replace")

    # -- dynamic section -----------------------------------------------------

    def dynamic_entries(self) -> list[tuple[int, int]]:
        dyn = next((s for s in self.segments if s.type == PT_DYNAMIC), None)
        if dyn is None:
            return []
        out: list[tuple[int, int]] = []
        off = dyn.offset
        end = min(off + dyn.filesz, len(self.data))
        while off + 8 <= end:
            tag, val = struct.unpack_from(self._e + "iI", self.data, off)
            out.append((tag, val))
            if tag == DT_NULL:
                break
            off += 8
        return out

    def interpreter(self) -> str | None:
        seg = next((s for s in self.segments if s.type == PT_INTERP), None)
        return self._cstr(seg.offset) if seg else None

    def dynamic_symbols(self) -> tuple[list[str], list[str]]:
        """Return ``(imports, exports)`` read straight out of ``.dynsym``.

        Works on sstrip'd binaries because the symbol table is located through
        ``DT_SYMTAB``/``DT_STRTAB`` and sized through ``DT_MIPS_SYMTABNO``.
        On non-MIPS targets without that tag we stop at the first entry that
        falls outside the string table, which is a conservative bound.
        """
        d = dict(self.dynamic_entries())
        symtab_va, strtab_va = d.get(DT_SYMTAB), d.get(DT_STRTAB)
        if not symtab_va or not strtab_va:
            return [], []

        syment = d.get(DT_SYMENT, 16) or 16
        strsz = d.get(DT_STRSZ, 0)
        symtab_off = self.vaddr_to_offset(symtab_va)
        strtab_off = self.vaddr_to_offset(strtab_va)
        if symtab_off is None or strtab_off is None:
            return [], []

        count = d.get(DT_MIPS_SYMTABNO)
        if not count:
            # Without an explicit count, bound the walk by where the string
            # table starts (dynsym conventionally precedes it) and cap it so a
            # malformed file cannot spin.
            span = max(0, (strtab_off - symtab_off))
            count = min(span // syment, 65536) if span > 0 else 0

        imports: list[str] = []
        exports: list[str] = []
        for i in range(count):
            off = symtab_off + i * syment
            if off + 16 > len(self.data):
                break
            # _st_value is intentionally unused: see the classification comment
            # below — reading it into the decision is the bug this avoids.
            st_name, _st_value, _st_size, _st_info, _st_other, st_shndx = \
                struct.unpack_from(self._e + "IIIBBH", self.data, off)
            if st_name == 0 or (strsz and st_name >= strsz):
                continue
            name = self._cstr(strtab_off + st_name, 256)
            if not name:
                continue
            # An import is a symbol the loader must resolve, and the ABI says
            # that is exactly st_shndx == SHN_UNDEF (0). st_value must NOT be
            # part of the test: on MIPS, undefined functions carry the address
            # of their lazy-binding stub in .MIPS.stubs, so st_value is usually
            # non-zero. Requiring st_value == 0 here silently reclassified 165
            # of /bin/boa's 181 imports as exports - including system() and
            # strcpy(), i.e. precisely the symbols this tool exists to find.
            if st_shndx == 0:
                imports.append(name)
            else:
                exports.append(name)
        return sorted(set(imports)), sorted(set(exports))

    # -- interpretation ------------------------------------------------------

    def mips_flags(self) -> tuple[str | None, str | None, list[str]]:
        if self.e_machine != EM_MIPS:
            return None, None, []
        isa = EF_MIPS_ARCH_NAMES.get(self.e_flags & EF_MIPS_ARCH_MASK)
        abi = "o32" if self.e_flags & EF_MIPS_ABI_O32 else None
        notes = []
        if self.e_flags & EF_MIPS_NOREORDER:
            notes.append("noreorder")
        if self.e_flags & EF_MIPS_PIC:
            notes.append("pic")
        if self.e_flags & EF_MIPS_CPIC:
            notes.append("cpic")
        return isa, abi, notes

    def hardening(self, imports: list[str]) -> Hardening:
        d = dict(self.dynamic_entries())
        gnu_stack = next((s for s in self.segments if s.type == PT_GNU_STACK), None)
        relro_seg = next((s for s in self.segments if s.type == PT_GNU_RELRO), None)
        bind_now = DT_BIND_NOW in d or bool(d.get(DT_FLAGS, 0) & DF_BIND_NOW)

        if relro_seg is None:
            relro = "none"
        elif bind_now:
            relro = "full"
        else:
            relro = "partial"

        imp = set(imports)
        return Hardening(
            # No PT_GNU_STACK at all means the toolchain never emitted the marker,
            # so the kernel falls back to an executable stack. Reported as None
            # rather than False to keep "absent" distinguishable from "off".
            nx=None if gnu_stack is None else not bool(gnu_stack.flags & PF_X),
            pie=self.e_type == 3,
            relro=relro,
            canary=any(m in imp for m in CANARY_MARKERS),
            fortify=any(n.endswith("_chk") for n in imp),
            rwx_segments=[f"{s.perms}@0x{s.vaddr:08x}" for s in self.segments
                          if s.type == PT_LOAD and (s.flags & PF_W) and (s.flags & PF_X)],
            text_relocations=DT_TEXTREL in d,
        )


# ---------------------------------------------------------------- entry point

def analyse(path: str | Path) -> ElfReport:
    """Analyse one file. Never raises: non-ELF and unreadable files come back
    as a report with ``is_elf=False`` so a filesystem sweep cannot be derailed
    by one odd file."""
    p = Path(path)
    try:
        data = p.read_bytes()
    except OSError as exc:
        return ElfReport(path=str(p), is_elf=False, error=f"read failed: {exc}")

    try:
        r = Elf32Reader(data, str(p))
    except ValueError as exc:
        return ElfReport(path=str(p), is_elf=False, error=str(exc))

    imports, exports = r.dynamic_symbols()
    dyn = dict(r.dynamic_entries())
    strtab_off = r.vaddr_to_offset(dyn.get(DT_STRTAB, 0)) if DT_STRTAB in dyn else None

    def dynstr(tag: int) -> list[str]:
        if strtab_off is None:
            return []
        return [r._cstr(strtab_off + v) for t, v in r.dynamic_entries() if t == tag]

    isa, abi, mips_notes = r.mips_flags()
    loads = [s for s in r.segments if s.type == PT_LOAD]

    sinks = {
        kind: sorted(n for n in names if n in set(imports))
        for kind, names in SINKS.items()
    }

    return ElfReport(
        path=str(p),
        is_elf=True,
        bits=32,
        endian=r.endian,
        machine=EM_NAMES.get(r.e_machine, f"unknown({r.e_machine})"),
        machine_id=r.e_machine,
        type=ET_NAMES.get(r.e_type, str(r.e_type)),
        entry=r.e_entry,
        load_base=min((s.vaddr for s in loads), default=0),
        interpreter=r.interpreter(),
        soname=(dynstr(DT_SONAME) or [None])[0],
        # e_shnum == 0 is the signature of sstrip; recording it explains why
        # section-based tools go quiet on this binary.
        section_headers=r.e_shnum != 0,
        mips_isa=isa,
        mips_abi=abi,
        mips_flags=mips_notes,
        needed=dynstr(DT_NEEDED),
        rpath=dynstr(DT_RPATH) + dynstr(DT_RUNPATH),
        imports=imports,
        exports=exports,
        sinks={k: v for k, v in sinks.items() if v},
        segments=loads,
        hardening=r.hardening(imports),
    )
