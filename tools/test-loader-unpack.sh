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

echo
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
