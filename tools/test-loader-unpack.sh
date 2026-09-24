#!/usr/bin/env bash
# Guard suite for tools/loader-unpack.py.
#
# That tool's headline result is an *absence*: the boot loader contains no
# kernel command line, no environment, and no way to set one -- which is what
# refutes P9-1 without a single power cycle. An absence is only worth reading if
# the instrument that reports it is shown, in the same run, to find things that
# are there. So the cases below are in two halves:
#
#   * refusals -- every way the unpacker can be pointed at the wrong bytes and
#     produce a plausible-looking report, driven with synthetic images so no
#     flash dump is needed and CI can run them;
#   * the positive control -- a synthetic loader carrying the same seventeen
#     command names and the same help banner, which must unpack cleanly. Without
#     it a suite of refusals passes just as well when the tool is broken and
#     refuses everything.
#
#   bash tools/test-loader-unpack.sh
#
set -uo pipefail

cd "$(dirname "$0")/.." || { echo "  FAIL  cannot cd to the repository root"; exit 1; }
PY="${FWRE_PY:-python3}"
TOOL="tools/loader-unpack.py"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
ok()  { echo "  ok    $1"; pass=$((pass + 1)); }
bad() { echo "  FAIL  $1"; fail=$((fail + 1)); }

# Build a synthetic 4 MiB image whose loader region holds one LZMA-alone stream.
# `payload` is the text that goes inside it, `count` how many streams to plant.
make_image() {
  local out="$1" payload="$2" count="${3:-1}"
  "$PY" - "$out" "$payload" "$count" <<'PYEOF'
import lzma, sys, struct
out, payload, count = sys.argv[1], sys.argv[2], int(sys.argv[3])
# Padded past the tool's 1 KiB floor with filler that carries no command names
# and no help banner, so what each fixture proves stays exactly what it says.
body = (payload + "\n" + ("." * 79 + "\n") * 40).encode()
# LZMA-alone with an explicit size, which is what the RealTek packer emits and
# what the tool insists on so it can size-check the result.
c = lzma.compress(body, format=lzma.FORMAT_ALONE,
                  filters=[{"id": lzma.FILTER_LZMA1, "preset": 6,
                            "dict_size": 1 << 23}])
c = c[:5] + struct.pack("<Q", len(body)) + c[13:]
buf = bytearray(b"\x00" * (4 << 20))
buf[0x400:0x400 + 10] = b"Booting..."
for i in range(count):
    at = 0x1000 + i * 0x1800
    buf[at:at + len(c)] = c
open(out, "wb").write(bytes(buf))
PYEOF
}

# The real loader's help block, near enough that the seventeen-command control
# and the banner check both pass.
GOOD_PAYLOAD='----------------- COMMAND MODE HELP ------------------
HELP (?)   : Print this help message
DB <Address> <Len>
DW <Address> <Len>
EB <Address> <Value1> <Value2>...
EW <Address> <Value1> <Value2>...
CMP <dst><src><length>
IPCONFIG:<TargetAddress>
AUTOBURN: 0/1
LOADADDR: <Load Address>
J: Jump to <TargetAddress>
FLR: FLR <dst><src><length>
FLW <dst_ROM_offset><src_RAM_addr><length_Byte> <SPI cnt#>
MDIOR MDIOW PHYR PHYW PORT1
Flash Read Successed!'

expect_refusal() {
  local label="$1" needle="$2" img="$3" out rc
  out="$("$PY" "$TOOL" "$img" 2>&1)"; rc=$?
  if [ "$rc" -eq 0 ]; then
    bad "$label — accepted when it should have refused"
  elif printf '%s' "$out" | grep -qF "$needle"; then
    ok "$label"
  else
    bad "$label — refused, but for the wrong reason: $(printf '%s' "$out" | head -2)"
  fi
}

echo "loader-unpack guard suite"

# 1. No stream at all.
"$PY" - "$TMP/empty.bin" <<'PYEOF'
import sys
open(sys.argv[1], "wb").write(b"\x00" * (4 << 20))
PYEOF
expect_refusal "an image with no LZMA stream is refused" "no LZMA-alone stream" "$TMP/empty.bin"

# 2. Two streams: "the first one" would be a silent wrong answer.
make_image "$TMP/two.bin" "$GOOD_PAYLOAD" 2
expect_refusal "two streams in the loader region are refused, not picked between" \
               "more than one LZMA-alone stream" "$TMP/two.bin"

# 3. Something that decompresses but is not the command interpreter. This is the
#    case a bare "did it decompress?" check would wave through.
make_image "$TMP/wrong.bin" "this decompresses fine and is not a boot loader at all"
expect_refusal "a stream that unpacks to the wrong thing is refused" \
               "COMMAND MODE HELP" "$TMP/wrong.bin"

# 4. The banner present but commands missing — a partial or differently packed
#    loader, where the absence claims would be meaningless.
make_image "$TMP/partial.bin" "----------------- COMMAND MODE HELP ------------------
DB <Address> <Len>
FLR: FLR <dst><src><length>"
expect_refusal "a stage missing documented commands is refused" \
               "the string scan did not find these commands" "$TMP/partial.bin"

# 5. Truncated stream: declared output size will not match.
make_image "$TMP/trunc.bin" "$GOOD_PAYLOAD"
"$PY" - "$TMP/trunc.bin" <<'PYEOF'
import sys
p = sys.argv[1]
b = bytearray(open(p, "rb").read())
# Cut the compressed stream in half, leaving the 13-byte header intact.
for i in range(0x1000 + 13 + 40, 0x1000 + 0x1700):
    b[i] = 0
open(p, "wb").write(bytes(b))
PYEOF
out="$("$PY" "$TOOL" "$TMP/trunc.bin" 2>&1)"; rc=$?
if [ "$rc" -eq 0 ]; then
  bad "a truncated stream is refused — accepted instead"
elif printf '%s' "$out" | grep -qE "did not decompress|is not evidence"; then
  ok "a truncated stream is refused"
else
  bad "a truncated stream is refused — wrong reason: $(printf '%s' "$out" | head -2)"
fi

# 6. THE POSITIVE CONTROL. Everything above passes just as well when the tool
#    refuses unconditionally.
make_image "$TMP/good.bin" "$GOOD_PAYLOAD"
if out="$("$PY" "$TOOL" "$TMP/good.bin" 2>/dev/null)"; then
  if printf '%s' "$out" | grep -q '"self_check": "OK"' &&
     printf '%s' "$out" | grep -q '"help_banner_present": true'; then
    ok "positive control: a well-formed loader unpacks and self-checks"
  else
    bad "positive control: unpacked but the report is not shaped right"
  fi
else
  bad "positive control: a well-formed loader was refused"
fi

# 7. And the control that the *absence* reporting works: the synthetic loader
#    has no kernel command line either, so the count must be zero — but the
#    command control above proves the scanner is not simply blind.
if printf '%s' "$out" | "$PY" -c '
import json, sys
d = json.load(sys.stdin)
q = d["questions"]["P9-1_kernel_cmdline"]
assert q["hits"] == [], q["hits"]
assert len(d["controls"]["documented_commands_found"]) == 17
'; then
  ok "the cmdline scan reports zero hits while the same scan finds all 17 commands"
else
  bad "the cmdline/command scan pair did not behave"
fi

# ---------------------------------------------------------------------------
# The chip table. Added 2026-08-20, because `chipName: UNKNOWN` in this unit's
# own boot log turned out to be answerable from the loader alone -- and the
# answer is an ABSENCE ("this part has no row"), which is exactly the class of
# claim that needs the instrument shown finding things that are there.
#
# The load base is RECOVERED rather than assumed, so the two ways a recovery
# lies -- finding nothing, and finding more than one and picking -- both get a
# case, and so does the query that the W08 prediction actually rests on.
# ---------------------------------------------------------------------------

make_chip_image() {
  local out="$1" mode="${2:-good}"
  "$PY" - "$out" "$mode" <<'PYEOF'
import lzma, struct, sys
out, mode = sys.argv[1], sys.argv[2]

HELP = ("----------------- COMMAND MODE HELP ------------------\n"
        "HELP (?) DB DW EB EW CMP IPCONFIG AUTOBURN LOADADDR J FLR FLW "
        "MDIOR MDIOW PHYR PHYW PORT1\n"
        + ("." * 79 + "\n") * 40)

def plant(blob, base, names, stride, damage_at=None):
    off = {}
    for n in names:
        while len(blob) % 4:
            blob += b"\x00"
        off[n] = len(blob)
        blob += n.encode() + b"\x00"
    while len(blob) % 4:
        blob += b"\x00"
    for i, n in enumerate(names):
        words = [0x1c3000 + i, 0, 0x15, 0x10000, 0x1000, 0x100,
                 base + off[n], 0x50]
        if damage_at == i:
            words[0] = 0x11223344          # a non-zero top byte: not a JEDEC id
        blob += struct.pack(">8I", *words)
        blob += b"\x00" * (stride - 0x20)  # 0 for the real stride
    return blob

body = bytearray(HELP.encode())
A = ["AA25X%03d" % i for i in range(20)]
B = ["BB25X%03d" % i for i in range(20)]
if mode != "none":
    stride = 0x24 if mode == "stride" else 0x20
    damage = 5 if mode == "badid" else None
    body = plant(body, 0x80400000, A, stride, damage)
if mode == "two":
    body = plant(body, 0x80500000, B, 0x20)
if mode == "orphan":
    # One more pointer at a name this table uses, parked off the stride: a row
    # the walk cannot reach, which is what makes a reported absence untrue.
    while len(body) % 4:
        body += b"\x00"
    body += struct.pack(">I", 0x80400000 + body.find(b"AA25X003"))

c = lzma.compress(bytes(body), format=lzma.FORMAT_ALONE,
                  filters=[{"id": lzma.FILTER_LZMA1, "preset": 6,
                            "dict_size": 1 << 23}])
c = c[:5] + struct.pack("<Q", len(body)) + c[13:]
buf = bytearray(b"\x00" * (4 << 20))
buf[0x400:0x400 + 10] = b"Booting..."
buf[0x1000:0x1000 + len(c)] = c
open(out, "wb").write(bytes(buf))
PYEOF
}

expect_table_refusal() {
  local label="$1" needle="$2" img="$3" out rc
  out="$("$PY" "$TOOL" --chip-table "$img" 2>&1)"; rc=$?
  if [ "$rc" -eq 0 ]; then
    bad "$label — the table was accepted when it should have been refused"
  elif printf '%s' "$out" | grep -qF "$needle"; then
    ok "$label"
  else
    bad "$label — refused for the wrong reason: $(printf '%s' "$out" | head -2)"
  fi
}

# 8. THE POSITIVE CONTROL for the table, first: everything below passes just as
#    well against a decoder that refuses everything.
make_chip_image "$TMP/chip-good.bin" good
if out="$("$PY" "$TOOL" --chip-table "$TMP/chip-good.bin" 2>&1)"; then
  if printf '%s' "$out" | grep -q "load base   0x80400000" &&
     printf '%s' "$out" | grep -q "20 records"; then
    ok "positive control: a planted table decodes and the load base is recovered"
  else
    bad "positive control: decoded, but not to the planted base/count: $(printf '%s' "$out" | head -2)"
  fi
else
  bad "positive control: a well-formed chip table was refused"
fi

# 9. The query the W08 prediction rests on, in BOTH directions. A lookup that
#    only ever says "absent" would answer P9-7 the same way whatever the chip
#    turns out to be.
if "$PY" "$TOOL" --has-id 1c3000 "$TMP/chip-good.bin" >/dev/null 2>&1; then
  ok "--has-id exits 0 for an id the table does hold"
else
  bad "--has-id refused an id that is in the planted table"
fi
if "$PY" "$TOOL" --has-id 1c7016 "$TMP/chip-good.bin" >/dev/null 2>&1; then
  bad "--has-id exited 0 for an id nothing planted — it is not reading the table"
else
  ok "--has-id exits 1 for an id the table does not hold"
fi

# 10. Nothing to find. The refusal has to name what it looked for.
make_chip_image "$TMP/chip-none.bin" none
expect_table_refusal "a stage with no chip table is refused, not reported empty" \
                     "no page-aligned load base" "$TMP/chip-none.bin"

# 11. Two bases each explaining a table. Picking one is how a recovery script
#     produces a confident wrong answer, so it must refuse instead.
make_chip_image "$TMP/chip-two.bin" two
expect_table_refusal "two load bases are refused, not chosen between" \
                     "load bases each explain a table" "$TMP/chip-two.bin"

# 12. Records at the wrong stride: the run filter is what makes this a table
#     rather than 20 coincidences, so breaking the stride must break the walk.
make_chip_image "$TMP/chip-stride.bin" stride
expect_table_refusal "records that do not sit on the measured stride are refused" \
                     "no page-aligned load base" "$TMP/chip-stride.bin"

# 13. A row whose id word is not a three-byte id. The stride still holds and the
#     name still resolves, so only the id check can catch this one.
make_chip_image "$TMP/chip-badid.bin" badid
expect_table_refusal "a record whose id word has a non-zero top byte is refused" \
                     "non-zero top byte" "$TMP/chip-badid.bin"

# 14. A row the walk cannot reach. This is the one that matters, because every
#     claim built on this table is an ABSENCE, and a walk that stops early
#     reports absence for a part that is present.
make_chip_image "$TMP/chip-orphan.bin" orphan
expect_table_refusal "a pointer into the name block off the walked stride is refused" \
                     "would not be an absence" "$TMP/chip-orphan.bin"

# 15. And the softness is deliberate, so it is pinned: a fixture with no table
#     still produces a self-checking report, with the refusal recorded in it
#     rather than the field silently missing.
if out="$("$PY" "$TOOL" "$TMP/chip-none.bin" 2>/dev/null)"; then
  if printf '%s' "$out" | "$PY" -c '
import json, sys
d = json.load(sys.stdin)
assert d["self_check"] == "OK"
assert "refused" in d["chip_table"], d["chip_table"]
'; then
    ok "an absent table is reported as a refusal inside a report that still self-checks"
  else
    bad "an absent table did not surface as a refusal in the JSON report"
  fi
else
  bad "a fixture with no chip table was refused outright — the softness is gone"
fi

# ---------------------------------------------------------------------------
# The command table, and what each handler actually reads. Added 2026-08-21 for
# open #98 -- `FLW` declares four arguments and the runsheet sends three.
#
# The headline result here is again an ABSENCE, and a sharper one than the chip
# table's: *no instruction in the image reads the table's argument-count field*.
# A tool that reports that is one hard-coded `False` away from being a liar, so
# the suite below carries the reverse control -- a fixture whose reader DOES
# load that field, which must come back `true`. Same for the handler analysis:
# four planted handlers with four different shapes, and the decoder has to tell
# them apart rather than reporting "unchecked" for everything.
# ---------------------------------------------------------------------------

make_cmd_image() {
  local out="$1" mode="${2:-good}"
  "$PY" - "$out" "$mode" <<'PYEOF'
import lzma, struct, sys
out, mode = sys.argv[1], sys.argv[2]

BASE, ALT = 0x80400000, 0x80500000
NAMES = ["?", "DB", "DW", "EB", "EW", "CMP", "IPCONFIG", "AUTOBURN",
         "LOADADDR", "J", "FLR", "FLW", "MDIOR", "MDIOW", "PHYR", "PHYW",
         "PORT1"]

BANNER = ("----------------- COMMAND MODE HELP ------------------\n"
          "HELP (?)   : Print this help message\n"
          "DB <Address> <Len>\nDW <Address> <Len>\n"
          "EB <Address> <Value1> <Value2>...\n"
          "EW <Address> <Value1> <Value2>...\n"
          "CMP <dst><src><length>\nIPCONFIG:<TargetAddress>\n"
          "AUTOBURN: 0/1\nLOADADDR: <Load Address>\n"
          "J: Jump to <TargetAddress>\nFLR: FLR <dst><src><length>\n"
          "FLW <dst_ROM_offset><src_RAM_addr><length_Byte> <SPI cnt#>\n"
          "MDIOR MDIOW PHYR PHYW PORT1\nFlash Read Successed!\n"
          + ("." * 79 + "\n") * 20)

body = bytearray(BANNER.encode())


def align():
    while len(body) % 4:
        body.append(0)


def put_str(text):
    align()
    at = len(body)
    body.extend(text.encode() + b"\x00")
    return at


def put_code(words):
    align()
    at = len(body)
    for w in words:
        body.extend(struct.pack(">I", w))
    return at


name_off = {n: put_str(n) for n in NAMES}
# One help string carries tabs on purpose: the printable-run string scanner
# cannot see it, so a decoder that resolves pointers with that scanner refuses
# the whole table. That is how the first version of this decoder failed.
help_off = {n: put_str("HELP (?)\t\t\t\t    : Print this help message"
                       if n == "?" else "%s <arg1> <arg2>" % n)
            for n in NAMES}

PROLOGUE, JR_RA, NOP = 0x27BDFFE0, 0x03E00008, 0x00000000
H = {
    # returns without touching argv or argc
    "plain": put_code([PROLOGUE, JR_RA, NOP]),
    # blez a0, +2 ; nop ; lw a0,0(a1) ; jr ra  -- argc consumed before argv
    "checked": put_code([PROLOGUE, 0x18800002, NOP, 0x8CA40000, JR_RA, NOP]),
    # lw a0,0(a1) ; lw a0,4(a1) ; lw a0,8(a1) ; jr ra  -- three slots, no check
    "unchecked3": put_code([PROLOGUE, 0x8CA40000, 0x8CA40004, 0x8CA40008,
                            JR_RA, NOP]),
    # sll v0,a2,2 ; addu v0,v0,a1 ; lw a0,4(v0) ; jr ra  -- argv[1+n]
    "variadic": put_code([PROLOGUE, 0x00061080, 0x00451021, 0x8C440004,
                          JR_RA, NOP]),
    # blez a0,+2 ; lw a0,0(a1) ; lw a0,8(a1) ; jr ra -- the first load sits in
    # the DELAY SLOT, so it runs whichever way the branch goes. A walk that
    # steps over delay slots sees only slot 2 and calls that the answer.
    "delayslot": put_code([PROLOGUE, 0x18800002, 0x8CA40000, 0x8CA40008,
                           JR_RA, NOP]),
    # bnez a0,+2 ; nop ; lui a1,0x1234 ; lw a0,0(a1) ; jr ra -- $a1 is
    # overwritten only on the path the load is NOT on. This is `IPCONFIG`'s
    # shape, and a linear scan reads it as touching no argv at all.
    "twopath": put_code([PROLOGUE, 0x14800002, NOP, 0x3C051234, 0x8CA40000,
                         JR_RA, NOP]),
}
# move s0,a1 ; jal plain ; nop ; lw a0,0(a1) ; lw a0,4(s0) ; jr ra -- the call
# clobbers $a1 and does not clobber $s0, so exactly one of the two loads is a
# read of argv. A walk with no o32 clobber rule records both.
H["aftercall"] = put_code([
    PROLOGUE, 0x00A08025, 0x0C000000 | (((BASE + H["plain"]) >> 2) & 0x03FFFFFF),
    NOP, 0x8CA40000, 0x8E040004, JR_RA, NOP])

SHAPE = {"?": "plain", "PORT1": "plain", "EB": "variadic", "EW": "variadic",
         "J": "checked", "DB": "checked", "DW": "checked", "CMP": "checked",
         "IPCONFIG": "checked", "MDIOR": "checked", "MDIOW": "checked",
         "FLR": "aftercall", "PHYW": "delayslot", "PHYR": "twopath"}
ARGC = {"?": 0, "DB": 2, "DW": 2, "EB": 2, "EW": 2, "CMP": 3, "IPCONFIG": 2,
        "AUTOBURN": 1, "LOADADDR": 1, "J": 1, "FLR": 3, "FLW": 4, "MDIOR": 0,
        "MDIOW": 0, "PHYR": 2, "PHYW": 3, "PORT1": 3}

rows = [n for n in NAMES if not (mode == "missing" and n == "FLW")]
stride = 0x14 if mode == "stride" else 0x10
align()
table_at = len(body)
if mode != "none":
    for n in rows:
        handler = BASE + H[SHAPE.get(n, "unchecked3")]
        if mode == "nohandler":
            # Into the middle of a routine: not a string, and not a prologue.
            # Pointing it at a *name* would be caught by the name column check
            # instead, and the prologue test would never be exercised.
            handler = BASE + H["plain"] + 4
        body.extend(struct.pack(">4I", BASE + name_off[n], ARGC[n], handler,
                                BASE + help_off[n]))
        body.extend(b"\x00" * (stride - 0x10))
if mode == "two":
    align()
    for n in rows:
        body.extend(struct.pack(">4I", ALT + name_off[n], ARGC[n],
                                ALT + H[SHAPE.get(n, "unchecked3")],
                                ALT + help_off[n]))
if mode == "basemix":
    # A chip table whose name pointers imply a DIFFERENT load base. Two tables
    # in one image cannot have two bases; the decoders must notice.
    chip_names = ["ZZ25X%03d" % i for i in range(20)]
    offs = [put_str(c) for c in chip_names]
    align()
    for i, o in enumerate(offs):
        body.extend(struct.pack(">8I", 0x1C3000 + i, 0, 0x15, 0x10000,
                                0x1000, 0x100, ALT + o, 0x50))

# The two instructions that build the table's address, and a walk that reads
# the fields a dispatcher would. `enforced` adds the one load that would make
# the declared count load-bearing.
if mode not in ("none", "unreachable"):
    addr = BASE + table_at
    hi, lo = (addr >> 16) & 0xFFFF, addr & 0xFFFF
    if lo & 0x8000:
        hi = (hi + 1) & 0xFFFF
    reader = [0x3C020000 | hi, 0x24500000 | lo, 0x8E030000, 0x8E03000C]
    if mode == "enforced":
        reader.append(0x8E030004)                 # lw v1,4(s0) -- the count
    reader += [0x8E030008, JR_RA, NOP]
    put_code(reader)

c = lzma.compress(bytes(body), format=lzma.FORMAT_ALONE,
                  filters=[{"id": lzma.FILTER_LZMA1, "preset": 6,
                            "dict_size": 1 << 23}])
c = c[:5] + struct.pack("<Q", len(body)) + c[13:]
buf = bytearray(b"\x00" * (4 << 20))
buf[0x400:0x400 + 10] = b"Booting..."
buf[0x1000:0x1000 + len(c)] = c
open(out, "wb").write(bytes(buf))
PYEOF
}

expect_cmd_refusal() {
  local label="$1" needle="$2" img="$3" out rc
  out="$("$PY" "$TOOL" --commands "$img" 2>&1)"; rc=$?
  if [ "$rc" -eq 0 ]; then
    bad "$label — the command table was accepted when it should have been refused"
  elif printf '%s' "$out" | grep -qF "$needle"; then
    ok "$label"
  else
    bad "$label — refused for the wrong reason: $(printf '%s' "$out" | head -2)"
  fi
}

# 16. THE POSITIVE CONTROL, and it is four controls in one: the field order is
#     derived (not told), and the four planted handler shapes have to come back
#     as four different readings.
make_cmd_image "$TMP/cmd-good.bin" good
if out="$("$PY" "$TOOL" "$TMP/cmd-good.bin" 2>/dev/null)"; then
  if printf '%s' "$out" | "$PY" -c '
import json, sys
t = json.load(sys.stdin)["command_table"]
assert "refused" not in t, t
assert t["field_offsets"] == {"name": 0, "argc": 4, "handler": 8, "help": 12}, \
    t["field_offsets"]
assert t["record_count"] == 17, t["record_count"]
by = {r["name"]: r for r in t["rows"]}
# declared four, dereferences three, and never looks at the count it was given
assert by["FLW"]["declared_argc"] == 4
assert by["FLW"]["argv_slots_read"] == [0, 1, 2], by["FLW"]
assert by["FLW"]["argc_first_consumed_at"] is None, by["FLW"]
# the same walk has to see a handler that DOES check, or it is measuring nothing
assert by["J"]["argc_first_consumed_at"] is not None, by["J"]
assert by["J"]["argv_slots_read"] == [0], by["J"]
# a computed index is reported as computed, not as a slot number
assert by["EB"]["argv_slots_read_at_a_computed_index"] == [1], by["EB"]
assert by["EB"]["argv_slots_read"] == [], by["EB"]
# and a handler that touches neither is not reported as unchecked-and-reading
assert by["PORT1"]["argv_slots_read"] == [], by["PORT1"]
# a load in a branch delay slot happens whichever way the branch goes
assert by["PHYW"]["argv_slots_read"] == [0, 2], by["PHYW"]
# $a1 dies across a call and $s0 does not, so one of two loads is a real read
assert by["FLR"]["argv_slots_read"] == [1], by["FLR"]
assert by["FLR"]["argv_or_argc_live_at_calls"], by["FLR"]
# and the join is an intersection, so a clobber on the other path is not one
assert by["PHYR"]["argv_slots_read"] == [0], by["PHYR"]
assert not any(r["walk_truncated"] for r in t["rows"]), "a walk ran out of steps"
'; then
    ok "positive control: the field order is derived and seven handler shapes read as seven"
  else
    bad "positive control: the planted command table did not decode as planted"
  fi
else
  bad "positive control: a well-formed command table was refused"
fi

# 17. The absence, in both directions. `declared_argc_is_read_by_the_dispatcher`
#     is the whole answer to open #98, and a field that is always false answers
#     it the same way whatever the loader does.
if "$PY" "$TOOL" "$TMP/cmd-good.bin" 2>/dev/null | "$PY" -c '
import json, sys
t = json.load(sys.stdin)["command_table"]
assert t["declared_argc_is_read_by_the_dispatcher"] is False, t
assert t["field_offsets_any_instruction_reads"] == [0, 8, 12], t
'; then
  ok "a table whose count field nothing loads reports that field as unread"
else
  bad "the unread-count reading did not come back from a fixture that plants it"
fi
make_cmd_image "$TMP/cmd-enforced.bin" enforced
if "$PY" "$TOOL" "$TMP/cmd-enforced.bin" 2>/dev/null | "$PY" -c '
import json, sys
t = json.load(sys.stdin)["command_table"]
assert t["declared_argc_is_read_by_the_dispatcher"] is True, t
assert 4 in t["field_offsets_any_instruction_reads"], t
'; then
  ok "REVERSE control: add one load of +4 and the same field comes back true"
else
  bad "a fixture whose reader loads the count field still reported it unread"
fi

# 18. Nothing to find.
make_cmd_image "$TMP/cmd-none.bin" none
expect_cmd_refusal "a stage with no command table is refused, not reported empty" \
                   "command-name pointers on a" "$TMP/cmd-none.bin"

# 19. Two bases each explaining a table.
make_cmd_image "$TMP/cmd-two.bin" two
expect_cmd_refusal "two load bases are refused, not chosen between" \
                   "each explain a command table" "$TMP/cmd-two.bin"

# 20. Records off the measured stride.
make_cmd_image "$TMP/cmd-stride.bin" stride
expect_cmd_refusal "records that do not sit on the 0x10 stride are refused" \
                   "command-name pointers on a" "$TMP/cmd-stride.bin"

# 21. The handler column pointed at a string. Both columns hold in-range
#     pointers, so only the prologue check can tell them apart -- and getting
#     this wrong is exactly the transcription error open #98 was chasing.
make_cmd_image "$TMP/cmd-nohandler.bin" nohandler
expect_cmd_refusal "a handler column that points at data, not a prologue, is refused" \
                   "function prologue" "$TMP/cmd-nohandler.bin"

# 22. A table that decodes but is missing a command the device's own `?` prints.
make_cmd_image "$TMP/cmd-missing.bin" missing
expect_cmd_refusal "a decoded table missing a command the console prints is refused" \
                   "missing commands the console" "$TMP/cmd-missing.bin"

# 23. A table nothing in the image can reach. The claim that rests on this walk
#     is "no instruction reads +4"; if no instruction reaches the table at all,
#     that sentence is true and worthless.
make_cmd_image "$TMP/cmd-unreachable.bin" unreachable
expect_cmd_refusal "a table no instruction builds the address of is refused" \
                   "no instruction can reach" "$TMP/cmd-unreachable.bin"

# 24. Two tables, two load bases. The chip table and the command table are
#     recovered independently and must land on the same base; a disagreement is
#     one of the two recoveries being wrong, and picking either is a guess.
make_cmd_image "$TMP/cmd-basemix.bin" basemix
expect_cmd_refusal "the chip table and the command table disagreeing on the base is refused" \
                   "cannot have two" "$TMP/cmd-basemix.bin"

# ---------------------------------------------------------------------------
# 25-31. The interrupt wiring (open #101).
#
# These drive the analysis functions directly rather than through a synthetic
# 4 MiB image, because what has to be proved is arithmetic on instruction words
# and a fixture large enough to carry an interrupt controller would hide it.
# The case that matters is 27: two `cli`/`sti` idioms whose only difference is
# one bit of one immediate. Version 1 of this analysis matched the *shape*
# `ori $1,1 / mtc0` and reported that nothing in the image ever sets IE -- while
# `0x80408494` was setting it with `ori 0x1f / xori 0x1e`, four instructions
# after the loader printed `---Ethernet init Okay!` on this unit's own boot log.
# ---------------------------------------------------------------------------
irq_case() {
  local why="$1"; shift
  if "$PY" - "$@" <<'PYEOF'
import importlib.util, struct, sys
spec = importlib.util.spec_from_file_location("lu", "tools/loader-unpack.py")
lu = importlib.util.module_from_spec(spec); spec.loader.exec_module(lu)


def W(*ws):
    return b"".join(struct.pack(">I", w) for w in ws)


def ie(*ws):
    rows = lu._status_census(lu._words_of(W(*ws)), 0x80400000)
    assert len(rows) == 1, rows
    return rows[0]["ie_bit_after"]


which = sys.argv[1]
MFC0, MTC0, MTC0Z = 0x40016000, 0x40816000, 0x40806000

if which == "sti":
    assert ie(MFC0, 0, 0x3421001F, 0x3821001E, MTC0) == "1"
elif which == "cli-1f":
    # one bit of one immediate away from the case above
    assert ie(MFC0, 0, 0x3421001F, 0x3821001F, MTC0) == "0"
elif which == "cli-01":
    assert ie(MFC0, 0, 0x34210001, 0x38210001, MTC0) == "0"
elif which == "zero":
    assert ie(MTC0Z) == "0"
elif which == "restore":
    # `mtc0` of what `mfc0` read, untouched: IE is whatever it was
    assert ie(MFC0, 0, MTC0) == "S"
elif which == "control":
    # the whole analysis refuses when the census cannot see the writes that
    # clear IE, because then its report that nothing SETS it is worthless
    try:
        lu.interrupt_wiring(W(MFC0, 0, 0x3421001F, 0x3821001E, MTC0), 0x80400000)
    except lu.LoaderError as e:
        assert "clear IE" in str(e), str(e)
    else:
        raise SystemExit("the analysis did not refuse on a one-write image")
elif which == "funcstart":
    # A function entry is an address something CALLS. The word after the
    # previous `jr ra` is not the same thing: the routine before `enable_irq`
    # in this loader ends in `rfe`.
    words = [0x03E00008, 0x00000000, 0x00000000, 0x00000000]
    assert lu._func_start(words, 3, {2}) == 2
    assert lu._func_start(words, 3, set()) is None
    assert lu._func_start(words, 3, {2}, back=0) is None
else:
    raise SystemExit(f"unknown case {which}")
PYEOF
  then ok "$why"; else bad "$why"; fi
}

irq_case "an sti built as ori 0x1f / xori 0x1e is read as setting IE" sti
irq_case "the same shape with xori 0x1f is read as clearing it" cli-1f
irq_case "the ori 1 / xori 1 cli is read as clearing it" cli-01
irq_case "mtc0 zero is read as clearing it" zero
irq_case "mtc0 of an untouched mfc0 is read as leaving IE alone" restore
irq_case "an image the census cannot find cli sites in is refused" control
irq_case "a function entry is derived from what calls it, not from the previous jr ra" funcstart

# 32. The committed report is what the note cites, so it is what CI checks. The
#     dump itself lives outside the repository and CI cannot regenerate this.
if "$PY" - <<'PYEOF'
import json
d = json.load(open("reports/bootloader-unit-2018.json"))
w = d["interrupt_wiring"]
assert "refused" not in w, w["refused"]
eth = [r for r in w["installs"] if r["name"] == "eth0"]
assert len(eth) == 1 and eth[0]["irq"] == 15, w["installs"]
assert w["console_input"]["polls_only_the_uart"] is True
assert w["console_input"]["unresolved_memory_references"] == 0
assert w["boot_path_to_the_prompt"]["found"] is True
assert "Ethernet init Okay" in \
    w["boot_path_to_the_prompt"]["console_line_printed_immediately_before_sti"]
assert len(w["writes_that_set_ie"]) >= 1 and len(w["writes_that_clear_ie"]) >= 4
PYEOF
then
  ok "the committed report carries the eth0 install, the boot path and the console reading"
else
  bad "the committed report does not carry the interrupt wiring the note cites"
fi

echo
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
