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
GOLDEN=977a84b439f77dc0641e7e993702de0132818e6908af56b3f26b6550f4e22dfd

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
       's/(0x68, beq(ZERO, ZERO, branch_off(0x68, L_OUTER)), "b       outer")/(0x68, NOP, "nop")/' \
       "does not run"

# 6. The cursor: drop the increment and the banner becomes one byte forever.
broken "a cursor that does not advance is caught" \
       's/(0x28, addiu(S1, S1, 1), "addiu   s1,s1,1")/(0x28, NOP, "nop")/' \
       "parted company"

# 8. The bug that reached the device on 2026-08-21 -- the only one in this file
#    that a build certified and the silicon refuted.
#
#    `andi t2,t2,0x60` sat in the load delay slot of `lbu t2,0(t1)`, so it masked
#    the PREVIOUS line-status reading, which after the first character is
#    permanently non-zero. The wait loop therefore never waited: all 41 bytes went
#    out back to back, the 16550's 16-byte FIFO took the first 16 and dropped the
#    rest, and the console printed `*** N150RT RAM` forever -- with the nonce in
#    the part that was thrown away.
#
#    Version 1 of the simulator applied a load's result immediately, which models
#    a core WITH interlocks. This one has none, and the evidence is in its own
#    loader: 1,474 loads in the second stage, not one followed by an instruction
#    that reads what it loaded, 43.8% followed by an explicit nop.
broken "an instruction in the load delay slot is caught" \
       's|(0x34, NOP, "nop                     # load delay slot"),|(0x34, addiu(T2, T2, 0), "addiu   t2,t2,0"),|' \
       "load delay slot"
broken "the same hazard on the character fetch is caught" \
       's|(0x20, NOP, "nop                     # load delay slot"),|(0x20, addu(A0, A0, ZERO), "move    a0,a0"),|' \
       "load delay slot"

# 7. The layout assertion: move a label without moving the instruction.
broken "a label that disagrees with the layout is caught" \
       's/L_EMIT, sb(A0, T0, 0)/0x40, sb(A0, T0, 0)/' \
       "layout drift"

# ---------------------------------------------------------------------------
# --irq-restore: the second payload, and the reasons it is allowed to refuse
# ---------------------------------------------------------------------------
echo
echo "=== --irq-restore ==="

GIMR=00008000
accepts "an irq-restore build with the predicted GIMR0" --irq-restore "$GIMR"
accepts "the same build with --no-set-ie" --irq-restore "$GIMR" --no-set-ie

refuses "a GIMR0 of zero" "already wrote" --irq-restore 0
refuses "a GIMR0 with the eth0 bit clear" "bit 15 clear" --irq-restore 100
accepts "...unless the override says the device really read it back" \
        --irq-restore 100 --allow-no-eth-bit
refuses "an unaligned load address" "word aligned" --irq-restore "$GIMR" --load 80540002
refuses "a load address outside KSEG" "KSEG" --irq-restore "$GIMR" --load 00300000
refuses "a payload larger than --max-bytes" "max-bytes" \
        --irq-restore "$GIMR" --max-bytes 32
refuses "a GIMR0 that is not hex" "not hex" --irq-restore zzzz

# The single-variable claim, checked rather than asserted: the two variants must
# differ in exactly five words, and all five must land on the SECOND `EW` line.
# If they ever straddle both lines the operator retypes two commands to change
# one thing, and that is two experiments.
"$PY" "$TOOL" --irq-restore "$GIMR" -o "$TMP/ie.bin" >/dev/null 2>&1
"$PY" "$TOOL" --irq-restore "$GIMR" --no-set-ie -o "$TMP/noie.bin" >/dev/null 2>&1
if "$PY" - "$TMP/ie.bin" "$TMP/noie.bin" <<'PYEOF'
import struct, sys
a = open(sys.argv[1], "rb").read()
b = open(sys.argv[2], "rb").read()
assert len(a) == len(b) == 0x50, (len(a), len(b))
wa = [struct.unpack_from(">I", a, o)[0] for o in range(0, len(a), 4)]
wb = [struct.unpack_from(">I", b, o)[0] for o in range(0, len(b), 4)]
diff = [i for i, (x, y) in enumerate(zip(wa, wb)) if x != y]
assert diff == [10, 12, 13, 14], diff        # 0x28, 0x30, 0x34, 0x38
assert all(i >= 10 for i in diff), diff      # all on the second ten-word line
# and the five CP0 words are the loader's own sti, copied verbatim
assert wa[10:15] == [0x40016000, 0x00000000, 0x3421001F, 0x3821001E, 0x40816000], \
    [hex(w) for w in wa[10:15]]
assert wa[-2] == 0x03E00008 and wa[-1] == 0, [hex(w) for w in wa[-2:]]
PYEOF
then
  ok "the two variants differ in the CP0 block only, all of it on the second EW line"
else
  bad "the two variants do not differ the way the experiment assumes"
fi

# The line-length bound is the loader's, and it is the one that silently
# truncates rather than erroring, so the tool has to be the thing that notices.
if "$PY" - <<'PYEOF'
import sys
sys.path.insert(0, "tools")
import importlib.util
spec = importlib.util.spec_from_file_location("mk", "tools/mkramboot.py")
mk = importlib.util.module_from_spec(spec); spec.loader.exec_module(mk)
img, _ = mk.build_irq_restore(0x8000, True)
mk.ew_lines(0x80540000, img)                       # the default split fits
try:
    mk.ew_lines(0x80540000, img, per_line=20)      # one line, 20 values
except ValueError as e:
    assert "GetLine takes 128" in str(e) or "slots" in str(e), str(e)
else:
    raise SystemExit("a 20-value EW line was accepted; GetLine would truncate it")
PYEOF
then
  ok "an EW line past the loader's 128-character buffer is refused, not truncated"
else
  bad "the EW line bound is not enforced"
fi

# The report has to carry what a reader would otherwise take on trust.
"$PY" "$TOOL" --irq-restore "$GIMR" --load 80540000 --report "$TMP/irq.json" >/dev/null 2>&1
if "$PY" - "$TMP/irq.json" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1]))
assert d["mode"] == "irq-restore" and d["set_ie"] is True
assert d["gimr0"] == "0x00008000" and d["returns_to"] == "0x80409368"
assert d["simulated_status_out"] == "0x1000FF01", d["simulated_status_out"]
assert len(d["ew_lines"]) == 2 and all(len(l) <= 128 for l in d["ew_lines"])
PYEOF
then
  ok "the JSON transcript carries the simulated CP0 result and the EW lines"
else
  bad "the JSON transcript is missing what the bench would have to take on trust"
fi

# Two mutants, each removing one property the experiment depends on.
irq_broken() {
  local why="$1"; local sedexpr="$2"; local want="$3"
  local copy="$TMP/irqbroken.py"
  sed "$sedexpr" "$TOOL" > "$copy"
  if cmp -s "$copy" "$TOOL"; then
    bad "$why -- the patch changed nothing, so this case proves nothing"
    return
  fi
  local out
  out="$("$PY" "$copy" --irq-restore "$GIMR" 2>&1)"
  if [ $? -eq 0 ]; then
    bad "$why -- the broken build SUCCEEDED"
  elif ! printf '%s' "$out" | grep -qi -- "$want"; then
    bad "$why -- it failed but not with '$want':"
    printf '%s\n' "$out" | sed 's/^/        /'
  else
    ok "$why"
  fi
}

# If the payload does not end in `jr ra` it is a one-way trip, and P9-16's
# result -- that a payload can come back -- is being thrown away silently.
irq_broken "a payload that never returns is caught" \
           's|(0x48, jr(RA), "jr      ra|(0x48, NOP, "nop  ; was jr ra|' \
           "instruction fetch outside the image"

# If the store goes anywhere but GIMR0 the simulator must stop, because a
# payload that writes a register nobody chose is how a zero-write section stops
# being a zero-write section.
irq_broken "a word store to an address the payload may not touch is caught" \
           's|sw(T1, T2, GIMR0 \& 0xFFFF)|sw(T1, T2, 0x3004)|' \
           "not allowed to touch"

echo
echo "=== summary ==="
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
