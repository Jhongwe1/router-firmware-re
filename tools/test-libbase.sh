#!/usr/bin/env bash
# Guard suite for tools/libbase.py.
#
# The tool turns one line of console output into an address a ret2libc chain
# would jump to. Everything it says rests on two filters, and both of them are
# the kind that look like they worked when they did not:
#
#   * **page alignment.** An implied base with low bits set means the assumed
#     symbol is wrong. If solve_base ever returned a candidate it should have
#     rejected, every base below it would still look plausible -- 0x2aae3000 and
#     0x2aae3018 read the same to a human.
#
#   * **one answer, or none.** A symbol at least a page long admits more than
#     one page-aligned base. Silently taking the first is how a tool reports a
#     number for an address it cannot actually place, so the refusal is driven
#     here directly rather than assumed.
#
# Everything below runs against ELF files this script builds, so it needs no
# firmware, no rootfs and no device. The one case that does need the extracted
# rootfs -- agreeing with tools/mipsref.py on where `strcpy` and `system` are --
# is skipped with a line saying so rather than silently passing, because a
# cross-check that can vanish is not a cross-check.
#
#   bash tools/test-libbase.sh
set -uo pipefail

cd "$(dirname "$0")/.." || { echo "  FAIL  cannot cd to the repository root"; exit 1; }
TOOL=tools/libbase.py
PY="${PYTHON:-python3}"

pass=0; fail=0; skip=0
ok()   { echo "  ok    $1"; pass=$((pass + 1)); }
bad()  { echo "  FAIL  $1"; fail=$((fail + 1)); }
skipd(){ echo "  skip  $1"; skip=$((skip + 1)); }

# check <label> <python body printing PASS or a reason>
check() {
  local label="$1" script="$2" out
  out="$("$PY" - <<PYEOF 2>&1
import importlib.util, struct, sys, tempfile, os
spec = importlib.util.spec_from_file_location("libbase", "$TOOL")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def build_elf(path, *, machine=8, endian=2, loads=None, dynamic=True,
              symbols=(), code=None):
    """A minimal big-endian MIPS32 ET_DYN ELF, laid out vaddr == offset.

    Identity-mapping the first PT_LOAD keeps the fixture readable: an address in
    a test case is also a file offset, so a wrong answer is traceable by eye.
    """
    if loads is None:
        loads = [(0, 0x8000, 5), (0x10800, 0x100, 6)]
    strtab_off, symtab_off, dyn_off, code_off = 0x200, 0x300, 0x100, 0x400

    names, strtab = {}, b"\\0"
    for s in symbols:
        names[s[0]] = len(strtab)
        strtab += s[0].encode() + b"\\0"

    symtab = b"\\0" * 16                       # index 0 is always undefined
    for name, value, size, typ in symbols:
        symtab += struct.pack(">IIIBBH", names[name], value, size, typ, 0, 1)

    dyn = []
    if dynamic:
        dyn = [(5, strtab_off), (6, symtab_off), (10, len(strtab)),
               (11, 16), (0x70000011, len(symbols) + 1), (0, 0)]
    dynb = b"".join(struct.pack(">II", t, v) for t, v in dyn)

    size = 0x8000
    buf = bytearray(b"\\0" * size)
    buf[strtab_off:strtab_off + len(strtab)] = strtab
    buf[symtab_off:symtab_off + len(symtab)] = symtab
    buf[dyn_off:dyn_off + len(dynb)] = dynb
    for off, word in (code or {}).items():
        buf[off:off + 4] = struct.pack(">I", word)

    ph = []
    for vaddr, memsz, flags in loads:
        filesz = min(memsz, size - vaddr) if vaddr < size else 0
        ph.append((1, vaddr, vaddr, vaddr, filesz, memsz, flags, 0x10000))
    if dynamic:
        ph.append((2, dyn_off, dyn_off, dyn_off, len(dynb), len(dynb), 6, 4))

    eh = bytearray(52)
    eh[0:4] = b"\\x7fELF"
    eh[4], eh[5], eh[6] = 1, endian, 1
    struct.pack_into(">HHIIIIIHHHHHH", eh, 16,
                     3, machine, 1, 0, 52, 0, 0, 52, 32, len(ph), 0, 0, 0)
    out = bytes(eh) + b"".join(struct.pack(">8I", *p) for p in ph)
    buf[0:len(out)] = out
    with open(path, "wb") as fh:
        fh.write(bytes(buf))
    return path


TMP = tempfile.mkdtemp()
def tmp(n):
    return os.path.join(TMP, n)

$script
PYEOF
)"
  if [ "$out" = "PASS" ]; then ok "$label"; else bad "$label -- $out"; fi
}

echo "tools/libbase.py -- the two filters, and every way it refuses"

# --------------------------------------------------------------------------
# 1. The parser, on a file whose answers are known by construction
# --------------------------------------------------------------------------

check "the span is page-rounded across every PT_LOAD, .bss included" '
p = build_elf(tmp("a.so"), loads=[(0, 0x8000, 5), (0x10800, 0x100, 6)])
e = m.Elf(p)
# highest is 0x10800 + 0x100 = 0x10900, rounded up to 0x11000
print("PASS" if m.mapped_span(e) == 0x11000 else "span=0x%x" % m.mapped_span(e))
'

check "memsz is what counts, not filesz -- a .bss-heavy object is not short" '
p = build_elf(tmp("b.so"), loads=[(0, 0x1000, 5), (0x2000, 0x9000, 6)])
e = m.Elf(p)
print("PASS" if m.mapped_span(e) == 0xb000 else "span=0x%x" % m.mapped_span(e))
'

check "symbols come out of PT_DYNAMIC, with no section headers present" '
p = build_elf(tmp("c.so"), symbols=[("strcpy", 0x1b200, 40, 2),
                                    ("system", 0x25460, 100, 2)])
e = m.Elf(p)
got = {s["name"]: s["value"] for s in e.symbols}
print("PASS" if got == {"strcpy": 0x1b200, "system": 0x25460} else repr(got))
'

# --------------------------------------------------------------------------
# 2. The page-alignment filter -- the one that carries the whole answer
# --------------------------------------------------------------------------

check "one page-aligned base is found where exactly one exists" '
sym = {"name": "strcpy", "value": 0x1b200, "size": 40}
print("PASS" if m.solve_base(0x2aafe218, sym) == [0x2aae3000]
      else repr(m.solve_base(0x2aafe218, sym)))
'

check "an address that no page-aligned base can put inside the symbol is refused" '
# A symbol of n bytes covers n consecutive bases, so the alignment filter rejects
# only about 1 - n/4096 of addresses for a 40-byte function. 0x2aafe250 is one it
# does reject; 0x2aafe219 is NOT, which is why that near-miss is not the case
# here and why the report has to publish how many symbols survived the filter.
sym = {"name": "strcpy", "value": 0x1b200, "size": 40}
print("PASS" if m.solve_base(0x2aafe250, sym) == [] else repr(m.solve_base(0x2aafe250, sym)))
'

check "a symbol a page long or more admits several bases, and all of them are returned" '
sym = {"name": "big", "value": 0x1000, "size": 0x2000}
r = m.solve_base(0x2aafe218, sym)
print("PASS" if len(r) == 2 and all(b % 0x1000 == 0 for b in r) else repr(r))
'

check "the alignment filter is quantified, not asserted" '
p = build_elf(tmp("d.so"), symbols=[("strcpy", 0x1b200, 40, 2),
                                    ("other", 0x1000, 8, 2)])
e = m.Elf(p)
# only strcpy can hold this address with a page-aligned base
print("PASS" if m.discrimination(e, 0x2aafe218) == 1
      else "discrimination=%d" % m.discrimination(e, 0x2aafe218))
'

# --------------------------------------------------------------------------
# 3. The delay slot -- the four bytes that make the device and qemu agree
# --------------------------------------------------------------------------

check "the words at strcpy+0x18 and +0x1c decode as bnez then sb" '
print("PASS" if m.decode_kind(0x1460fffc) == "bnez" and m.decode_kind(0xa0c30000) == "sb"
      else "%s / %s" % (m.decode_kind(0x1460fffc), m.decode_kind(0xa0c30000)))
'

check "the branch and the store name the same source register" '
print("PASS" if m.rs_rt(0x1460fffc)[0] == m.rs_rt(0xa0c30000)[1]
      else "%r %r" % (m.rs_rt(0x1460fffc), m.rs_rt(0xa0c30000)))
'

check "a jr and a plain sw are not mistaken for a branch" '
print("PASS" if m.decode_kind(0x03e00008) == "jump-register"
      and m.decode_kind(0xac620000) == "sw" else "wrong kinds")
'

check "an epc is carried as two readings, because the console prints no BD bit" '
r = m.epc_candidates(0x2aafe218)
print("PASS" if [c["addr"] for c in r] == [0x2aafe218, 0x2aafe21c] else repr(r))
'

# One fixture drives both filters. Three functions a page apart in link-time
# value all admit a page-aligned base for the SAME runtime address -- which is
# the real situation on this library, where 22 of them did.
FIXTURE='
p = build_elf(tmp("e.so"),
              symbols=[("strcpy", 0x400, 40, 2), ("putclike", 0x1400, 40, 2),
                       ("quiet", 0x2400, 40, 2)],
              code={0x418: 0x1460fffc, 0x41c: 0xa0c30000,
                    0x1418: 0x10600002, 0x141c: 0xac620000,
                    0x2418: 0x00000000, 0x241c: 0x00000000})
e = m.Elf(p)
c = m.candidate_sites(e, 0x4418, "store")
'

check "three functions admit the same address, and only a store survives the fault kind" "$FIXTURE"'
r = {x["symbol"]: x["survives"] for x in c}
print("PASS" if r == {"strcpy": True, "putclike": True, "quiet": False} else repr(r))
'

check "the qemu instruction pair separates strcpy from another delay-slot store" "$FIXTURE"'
r = {x["symbol"]: x["matches_qemu_instruction_pair"] for x in c}
print("PASS" if r == {"strcpy": True, "putclike": False, "quiet": False} else repr(r))
'

check "each surviving candidate carries the base it would imply, and they differ" "$FIXTURE"'
r = {x["symbol"]: x["implied_base"] for x in c}
print("PASS" if r == {"strcpy": "0x00004000", "putclike": "0x00003000",
                      "quiet": "0x00002000"} else repr(r))
'

# --------------------------------------------------------------------------
# 4. The refusals
# --------------------------------------------------------------------------

check "a symbol the file does not export is refused, not guessed at" '
p = build_elf(tmp("g.so"), symbols=[("strcpy", 0x1b200, 40, 2)])
e = m.Elf(p)
try:
    e.symbol("system")
    print("returned an address for a name that is not there")
except m.Refused as exc:
    print("PASS" if "no dynamic symbol" in str(exc) else str(exc))
'

check "an offset inside no symbol comes back as None, not as the nearest one" '
p = build_elf(tmp("h.so"), symbols=[("strcpy", 0x1b200, 40, 2)])
e = m.Elf(p)
print("PASS" if m.containing_symbol(e, 0x1b300) is None
      else repr(m.containing_symbol(e, 0x1b300)))
'

check "a file that is not an ELF is refused" '
open(tmp("i.so"), "wb").write(b"not an elf at all, just bytes")
try:
    m.Elf(tmp("i.so")); print("read a non-ELF")
except m.ElfError as exc:
    print("PASS" if "not an ELF" in str(exc) else str(exc))
'

check "a little-endian ELF is refused rather than byte-swapped by accident" '
build_elf(tmp("j.so"), endian=1)
try:
    m.Elf(tmp("j.so")); print("accepted little-endian")
except m.ElfError as exc:
    print("PASS" if "big-endian" in str(exc) else str(exc))
'

check "an ELF for another machine is refused" '
build_elf(tmp("k.so"), machine=40)
try:
    m.Elf(tmp("k.so")); print("accepted a non-MIPS ELF")
except m.ElfError as exc:
    print("PASS" if "MIPS" in str(exc) else str(exc))
'

check "an object with no PT_LOAD is refused -- it is never mapped, so it has no base" '
build_elf(tmp("l.so"), loads=[])
try:
    m.Elf(tmp("l.so")); print("accepted an object with no PT_LOAD")
except m.ElfError as exc:
    print("PASS" if "PT_LOAD" in str(exc) else str(exc))
'

check "an object with no PT_DYNAMIC cannot be asked for symbols" '
p = build_elf(tmp("n.so"), dynamic=False)
e = m.Elf(p)
try:
    e.symbols; print("produced symbols with no dynamic segment")
except m.ElfError as exc:
    print("PASS" if "PT_DYNAMIC" in str(exc) else str(exc))
'

# --------------------------------------------------------------------------
# 5. The command line refuses in the same places, with exit 2
# --------------------------------------------------------------------------

cli() {
  local label="$1" want="$2"; shift 2
  local out rc
  out="$("$PY" "$TOOL" "$@" 2>&1)"; rc=$?
  if [ "$rc" = "2" ] && printf %s "$out" | grep -q "$want"; then
    ok "$label"
  else
    bad "$label -- rc=$rc out=${out:0:120}"
  fi
}

FIX="$(mktemp -d)"
# Two fixtures for the command line: one symbol short enough that the alignment
# filter lands on a single base, one a page or longer so that it cannot.
"$PY" - <<PYEOF
import importlib.util, struct
spec = importlib.util.spec_from_file_location("libbase", "$TOOL")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def build(path, symbols):
    strtab_off, symtab_off, dyn_off = 0x200, 0x300, 0x100
    names, strtab = {}, b"\0"
    for s in symbols:
        names[s[0]] = len(strtab); strtab += s[0].encode() + b"\0"
    symtab = b"\0" * 16
    for name, value, size, typ in symbols:
        symtab += struct.pack(">IIIBBH", names[name], value, size, typ, 0, 1)
    dyn = [(5, strtab_off), (6, symtab_off), (10, len(strtab)), (11, 16),
           (0x70000011, len(symbols) + 1), (0, 0)]
    dynb = b"".join(struct.pack(">II", t, v) for t, v in dyn)
    buf = bytearray(b"\0" * 0x8000)
    buf[strtab_off:strtab_off + len(strtab)] = strtab
    buf[symtab_off:symtab_off + len(symtab)] = symtab
    buf[dyn_off:dyn_off + len(dynb)] = dynb
    ph = [(1, 0, 0, 0, 0x8000, 0x8000, 5, 0x10000),
          (2, dyn_off, dyn_off, dyn_off, len(dynb), len(dynb), 6, 4)]
    eh = bytearray(52); eh[0:4] = b"\x7fELF"; eh[4], eh[5], eh[6] = 1, 2, 1
    struct.pack_into(">HHIIIIIHHHHHH", eh, 16, 3, 8, 1, 0, 52, 0, 0, 52, 32,
                     len(ph), 0, 0, 0)
    out = bytes(eh) + b"".join(struct.pack(">8I", *p) for p in ph)
    buf[0:len(out)] = out
    open(path, "wb").write(bytes(buf))

build("$FIX/small.so", [("strcpy", 0x1b200, 40, 2)])
build("$FIX/big.so", [("big", 0x1000, 0x2000, 2)])
PYEOF

cli "--solve refuses an address no page-aligned base explains" "no page-aligned base" \
    --in "$FIX/small.so" --solve 0x2aafe250 --symbol strcpy
cli "--solve refuses to choose when the symbol is a page or longer" "refusing to choose" \
    --in "$FIX/big.so" --solve 0x2aafe218 --symbol big
cli "--solve refuses a symbol name the file does not export" "no dynamic symbol" \
    --in "$FIX/small.so" --solve 0x2aafe218 --symbol nosuchthing
cli "--resolve refuses an address that lands inside no symbol" "inside no dynamic symbol" \
    --in "$FIX/small.so" --resolve 0x2aafe900 --base 0x2aae3000

"$PY" "$TOOL" --in "$FIX/small.so" --solve 0x2aafe218 --symbol strcpy >/dev/null 2>&1 \
  && ok "--solve returns 0 on the case that does resolve" \
  || bad "--solve failed on the good case"

rm -rf "$FIX"

# --------------------------------------------------------------------------
# 6. The one cross-check that needs the firmware, and says so when it cannot run
# --------------------------------------------------------------------------

LIBC="${FWRE_WORK:-$HOME/fwre-work}/extracted/unit-2018/squashfs-root/lib/libuClibc-0.9.30.3.so"
if [ -f "$LIBC" ]; then
  a="$("$PY" "$TOOL" --in "$LIBC" --solve 0x2aafe218 --symbol strcpy 2>&1 \
       | head -1 | grep -oE 'base 0x[0-9a-f]+')"
  b="$("$PY" tools/mipsref.py --symbols "$LIBC" 2>&1 | grep -wE 'strcpy' \
       | awk '{print $1}')"
  if [ "$a" = "base 0x2aae3000" ] && [ "$b" = "0x0001b200" ]; then
    ok "libbase and mipsref agree on where strcpy is (two readers, one PT_DYNAMIC)"
  else
    bad "cross-check: libbase said '$a', mipsref said '$b'"
  fi
else
  skipd "libbase vs mipsref on the real uClibc -- no extracted rootfs here"
fi

echo
echo "  $pass passed, $fail failed, $skip skipped"
[ "$fail" -eq 0 ] || exit 1
