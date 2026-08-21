#!/usr/bin/env bash
# Self-test for tools/mkramboot.py.
#
# The thing this builds gets uploaded into the RAM of the only unit there is and
# then jumped to.  If it is wrong the observable result is a console that says
# nothing -- which is also what "the jump never happened" looks like, and that
# ambiguity is the entire reason P9-12 needs this payload rather than any file.
# So the interesting cases here are not the refusals: they are the ones that
# prove the *simulator* goes red when the payload is broken.  A build check that
# cannot fail would certify a program that prints nothing.
#
# Every guard is verified in reverse: the bug is put back into a copy of the
# tool, and the copy must fail.
#
#   bash tools/test-mkramboot.sh
#
set -uo pipefail

cd "$(dirname "$0")/.." || { echo "  FAIL  cannot cd to the repository root"; exit 1; }

PY="${FWRE_PY:-python3}"
TOOL=tools/mkramboot.py
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0
fail=0
ok()  { echo "  ok    $1"; pass=$((pass + 1)); }
bad() { echo "  FAIL  $1"; fail=$((fail + 1)); }

# A fixed nonce, so that the golden hash below is a hash of something.
NONCE=3f7c91a2
GOLDEN=9223fc15a466c7ae4be7f8ebbbd8eb024a52cf1874189dab0aa792fe7a5b0a28

echo "=== interpreter ==="
"$PY" -c 'import sys; print("  " + sys.executable + "  " + sys.version.split()[0]); \
sys.exit(0 if sys.version_info >= (3, 10) else 1)' || {
  echo "  FAIL  need python 3.10+"; exit 1; }
echo

# refuses:  the tool must exit non-zero AND its output must mention the reason.
refuses() {
  local why="$1"; shift
  local want="$1"; shift
  local out
  out="$("$PY" "$TOOL" "$@" 2>&1)"
  if [ $? -eq 0 ]; then
    bad "$why -- it succeeded"
  elif ! printf '%s' "$out" | grep -qi -- "$want"; then
    bad "$why -- it failed, but for a reason that does not mention '$want':"
    printf '%s\n' "$out" | sed 's/^/        /'
  else
    ok "$why"
  fi
}

accepts() {
  local why="$1"; shift
  local out
  out="$("$PY" "$TOOL" "$@" 2>&1)"
  if [ $? -ne 0 ]; then
    bad "$why -- it refused:"
    printf '%s\n' "$out" | sed 's/^/        /'
  else
    ok "$why"
  fi
}

echo "=== controls: the cases that must SUCCEED ==="
accepts "a plain build with a fixed nonce" --nonce "$NONCE"

"$PY" "$TOOL" --nonce "$NONCE" -o "$TMP/a.bin" > "$TMP/a.log" 2>&1
if [ -s "$TMP/a.bin" ]; then
  ok "it writes an image ($(wc -c < "$TMP/a.bin" | tr -d ' ') bytes)"
else
  bad "it wrote no image"
fi

GOT="$("$PY" -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$TMP/a.bin")"
if [ "$GOT" = "$GOLDEN" ]; then
  ok "the bytes are the golden ones ($GOLDEN)"
else
  bad "the bytes changed: $GOT, expected $GOLDEN.  If that is deliberate, the
        disassembly in notes/loader-tftp-and-commands.md changes with it"
fi

"$PY" "$TOOL" --nonce "$NONCE" -o "$TMP/b.bin" > /dev/null 2>&1
if cmp -s "$TMP/a.bin" "$TMP/b.bin"; then
  ok "two builds of the same nonce are byte identical"
else
  bad "the build is not reproducible"
fi

# The banner has to be in the image, or the marker the operator greps the
# console for is not the marker that was uploaded.
if grep -qa "RAMBOOT P9-12 $NONCE" "$TMP/a.bin"; then
  ok "the banner is in the image, and it contains the nonce"
else
  bad "the image does not contain the banner"
fi

if "$PY" "$TOOL" --nonce "$NONCE" --print-disassembly 2>&1 | grep -q "3c08b800"; then
  ok "the disassembly names the UART (lui t0,0xb800)"
else
  bad "the disassembly does not show the UART load"
fi

REPORT="$TMP/r.json"
"$PY" "$TOOL" --nonce "$NONCE" --report "$REPORT" > /dev/null 2>&1
if "$PY" -c "
import json,sys
r=json.load(open(sys.argv[1]))
assert r['uart_thr']=='0xb8002000', r['uart_thr']
assert r['uart_lsr']=='0xb8002014', r['uart_lsr']
assert r['nonce']==sys.argv[2]
assert r['simulated_output'].strip().endswith('***')
assert len(r['disassembly'])>20
" "$REPORT" "$NONCE" 2>/dev/null; then
  ok "the JSON transcript carries the UART addresses, the nonce and the listing"
else
  bad "the JSON transcript is missing fields"
fi

echo
echo "=== refusals ==="
refuses "a nonce that is not hex" "hex characters" --nonce zzzz
refuses "a nonce that is too short" "hex characters" --nonce ab
refuses "a load address that is not word aligned" "word aligned" \
        --nonce "$NONCE" --load 80500002
refuses "a load address outside KSEG0/KSEG1" "KSEG" --nonce "$NONCE" --load 00300000
refuses "a payload larger than --max-bytes" "max-bytes" --nonce "$NONCE" --max-bytes 32
refuses "an output file that already exists" "exists" \
        --nonce "$NONCE" -o "$TMP/a.bin"
accepts "the same output file with --force" --nonce "$NONCE" -o "$TMP/a.bin" --force
refuses "a --check-absent file that does not exist" "check-absent" \
        --nonce "$NONCE" --check-absent "$TMP/nope.bin"

# The one that matters most: a marker already present in flash.  Seeing the
# banner on the console would then be evidence of nothing.
printf 'padding N150RT RAMBOOT P9-12 deadbeef padding' > "$TMP/haystack.bin"
refuses "a nonce that already occurs in the file it is checked against" \
        "already occurs" --nonce deadbeef --check-absent "$TMP/haystack.bin"
refuses "a marker that already occurs, even with a fresh nonce" \
        "already occurs" --nonce 1234abcd --check-absent "$TMP/haystack.bin"
printf 'nothing to see here' > "$TMP/clean.bin"
accepts "a nonce absent from the file it is checked against" \
        --nonce "$NONCE" --check-absent "$TMP/clean.bin"

echo
echo "=== the simulator, verified in reverse ==="
# Each case puts a real bug back into a copy of the tool.  The copy must refuse.
broken() {
  local why="$1"; local sedexpr="$2"; local want="$3"
  local copy="$TMP/broken.py"
  sed "$sedexpr" "$TOOL" > "$copy"
  if cmp -s "$copy" "$TOOL"; then
    bad "$why -- the patch changed nothing, so this case proves nothing"
    return
  fi
  local out
  out="$("$PY" "$copy" --nonce "$NONCE" 2>&1)"
  if [ $? -eq 0 ]; then
    bad "$why -- the broken build SUCCEEDED"
  elif ! printf '%s' "$out" | grep -qi -- "$want"; then
    bad "$why -- it failed but not with '$want':"
    printf '%s\n' "$out" | sed 's/^/        /'
  else
    ok "$why"
  fi
}

# 1. The bug this tool actually had: branch offsets relative to PC+8.
broken "an off-by-one-word branch offset is caught" \
       's/delta = target - (here + 4)/delta = target - (here + 8)/' \
       "parted company"

# 2. The wrong LSR bit.  This one produces IDENTICAL output -- the payload spins
#    the full 6540 iterations per character and then writes anyway -- so no
#    check on the bytes can see it.  What sees it is the count of line-status
#    reads: one per character from a UART that was ready every time.
broken "polling the wrong LSR bits is caught, though the output is identical" \
       's/^LSR_TX_EMPTY = 0x60.*/LSR_TX_EMPTY = 0x01/' \
       "wrong bits"

# 3. The wrong transmit register: a store to something that is not the UART.
#    This is the case that failed while the simulator shared the encoder's
#    constants -- patching one moved both, and the model accepted the store.
broken "a transmit register that is not the UART's is caught" \
       's/^UART_THR = 0x2000.*/UART_THR = 0x2400/' \
       "not the UART"
broken "a line-status register that is not the UART's is caught" \
       's/^UART_LSR = 0x2014.*/UART_LSR = 0x2018/' \
       "outside the image and the UART"

# 4. Position independence: materialise the message address absolutely instead
#    of deriving it from $ra.  The first simulation catches it, because an
#    absolute 0x68 is not inside an image loaded at 0x80500000.
broken "a payload that materialises the message address absolutely is caught" \
       's/addiu(S0, RA, L_MSG - 0x08)/addiu(S0, ZERO, L_MSG)/' \
       "does not run"

# 5. The outer loop: make the banner print once and fall off the end.
broken "a payload that does not repeat is caught, and as a refusal not a traceback" \
       's/(0x60, beq(ZERO, ZERO, branch_off(0x60, L_OUTER)), "b       outer")/(0x60, NOP, "nop")/' \
       "does not run"

# 6. The cursor: drop the increment and the banner becomes one byte forever.
broken "a cursor that does not advance is caught" \
       's/(0x24, addiu(S1, S1, 1), "addiu   s1,s1,1")/(0x24, NOP, "nop")/' \
       "parted company"

# 7. The layout assertion: move a label without moving the instruction.
broken "a label that disagrees with the layout is caught" \
       's/L_EMIT, sb(A0, T0, 0)/0x40, sb(A0, T0, 0)/' \
       "layout drift"

echo
echo "=== summary ==="
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
