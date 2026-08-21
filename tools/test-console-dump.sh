#!/usr/bin/env bash
# Self-test for the DB transcript parser in tools/console-dump.py.
#
# The parser is the only thing standing between "70 minutes of hex text over a
# 38400 line with no flow control" and "a 4 MiB image with a hole in it that
# still looks like a 4 MiB image". Every case below is a way the wire actually
# fails, and each one asserts on its OWN failure message: a parser that rejects
# a short line for the wrong reason is a parser whose next revision will accept
# it silently.
#
# The control case at the end is not padding. A reject-only suite in this
# repository once reported 5/5 while every invocation was failing to start.
#
#   bash tools/test-console-dump.sh
#
set -uo pipefail

cd "$(dirname "$0")/.." || { echo "  FAIL  cannot cd to the repository root"; exit 1; }

PY="${FWRE_PY:-python3}"
T=tools/console-dump.py
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
ERR="$TMP/err"

pass=0
fail=0
ok()  { echo "  ok    $1"; pass=$((pass + 1)); }
bad() { echo "  FAIL  $1"; fail=$((fail + 1)); }

echo "=== interpreter ==="
# Named and printed, never assumed. On 2026-08-14 a bare `python3` in a login
# shell here resolved to an unrelated project's venv, and a guard suite went
# 5/5 green while every invocation was dying on an import (PROGRESS.md, W02
# "G2 checkbox 4"). console-dump.py is stdlib-only so any 3.10+ is genuinely
# fine - but which one ran has to be on the record, not inferred.
"$PY" -c 'import sys; print("  " + sys.executable + "  " + sys.version.split()[0]); \
sys.exit(0 if sys.version_info >= (3, 10) else 1)' || {
  echo "  FAIL  need python 3.10+"; exit 1; }
case "$("$PY" -c 'import sys; print(sys.executable)')" in
  "$HOME/fwre-work/venv/"*) ;;
  *) echo "  note  that is not this project's venv. Harmless here (the parser"
     echo "        imports nothing outside the standard library) and it would"
     echo "        NOT be harmless the day it does. FWRE_PY overrides it." ;;
esac
echo

# A clean transcript in the shape the device ACTUALLY produces, captured from
# the unit on 2026-08-16: a column header line, and an ASCII column after the
# bytes.
#
# The first version of these fixtures had no ASCII column, because they were
# written from the transcript quoted in notes/flash-layout.md - the same summary
# the parser's regex was written from. The suite passed 10/10 against a format
# the device does not emit, and the parser then rejected every real line on the
# first run. A guard suite that shares an assumption with the code it guards is
# not a second source; it is the same source twice.
cat > "$TMP/good.txt" <<'EOF'
DB 81000000 48
 [Addr]   .0 .1 .2 .3 .4 .5 .6 .7 .8 .9 .A .B .C .D .E .F
81000000: 0b f0 00 04 00 00 00 00 3c 08 a0 00 25 08 00 01     ........<...%...
81000010: 40 88 60 00 00 00 00 00 3c 1a 80 00 27 5a 10 00     @.`.....<...'Z..
81000020: 03 40 00 08 00 00 00 00 ff ff ff ff ff ff ff ff     .@..............
<RealTek>
EOF

# Adversarial: an ASCII column that reads like more hex bytes. If the byte
# matcher ever runs past the column boundary this is what catches it, and the
# per-line length check is the layer underneath.
cat > "$TMP/ascii-trap.txt" <<'EOF'
DB 81000000 16
 [Addr]   .0 .1 .2 .3 .4 .5 .6 .7 .8 .9 .A .B .C .D .E .F
81000000: 61 62 20 63 64 20 65 66 20 30 31 20 32 33 20 34     ab cd ef 01 23 4
<RealTek>
EOF

# One line gone: what a dropped burst looks like. The bytes on either side are
# perfectly valid, which is the whole problem.
grep -v '^81000010' "$TMP/good.txt" > "$TMP/dropped-line.txt"

# One byte gone from inside a line. 15 bytes, still well-formed hex.
sed 's/^81000010: 40 88/81000010: 88/' "$TMP/good.txt" > "$TMP/short-line.txt"

# The transcript ends early - the console stopped talking mid-dump.
head -3 "$TMP/good.txt" > "$TMP/truncated.txt"

# Nothing parseable at all: wrong command, or the port is dead.
printf 'DB 81000000 48\nUnknown command !\n<RealTek>\n' > "$TMP/nothing.txt"

# A duplicated address - a retry whose output got concatenated with the first
# attempt. Address stride catches it.
sed '4i\
81000010: 40 88 60 00 00 00 00 00 3c 1a 80 00 27 5a 10 00' "$TMP/good.txt" > "$TMP/dup.txt"

must_reject() {
  local label="$1" want="$2"; shift 2
  if "$PY" "$T" parse "$@" >/dev/null 2>"$ERR"; then
    bad "$label -- it PASSED and must not have"
    return
  fi
  local msg
  msg="$(head -1 "$ERR" | sed 's/^ *FAIL *//')"
  if [[ "$msg" == *"$want"* ]]; then
    ok "$label"
  else
    bad "$label -- rejected for the WRONG reason: $msg"
  fi
}

must_accept() {
  local label="$1"; shift
  if "$PY" "$T" parse "$@" >/dev/null 2>"$ERR"; then
    ok "$label"
  else
    bad "$label -- the control failed, so every case above proves nothing: $(head -1 "$ERR")"
  fi
}

B=(--base 0x81000000 --length 48)

echo "=== must be rejected ==="
must_reject "a dropped line"            "address discontinuity" "$TMP/dropped-line.txt" "${B[@]}"
must_reject "a byte dropped in a line"  "expected 16"           "$TMP/short-line.txt"   "${B[@]}"
must_reject "a truncated transcript"    "short read"            "$TMP/truncated.txt"    "${B[@]}"
must_reject "no data lines at all"      "nothing parseable"     "$TMP/nothing.txt"      "${B[@]}"
must_reject "a duplicated address"      "address discontinuity" "$TMP/dup.txt"          "${B[@]}"
must_reject "asked for the wrong base"  "address discontinuity" "$TMP/good.txt" --base 0x80000000 --length 48
must_reject "asked for more than is there" "short read"         "$TMP/good.txt" --base 0x81000000 --length 64
echo

echo "=== must be accepted (the controls) ==="
must_accept "a real transcript: header line and ASCII column ignored" \
            "$TMP/good.txt" "${B[@]}" -o "$TMP/out.bin"
must_accept "an ASCII column that reads like more hex bytes" \
            "$TMP/ascii-trap.txt" --base 0x81000000 --length 16 -o "$TMP/trap.bin"

if [ -f "$TMP/trap.bin" ]; then
  got="$("$PY" -c 'import sys;print(open(sys.argv[1],"rb").read().hex(" "))' "$TMP/trap.bin")"
  want="61 62 20 63 64 20 65 66 20 30 31 20 32 33 20 34"
  [ "$got" = "$want" ] && ok "the trap line decoded to the bytes, not to its own ASCII column" \
                       || bad "trap line decoded to '$got'"
fi

# And the bytes have to be RIGHT, not merely accepted. A parser that returns 48
# bytes of anything would pass every case above.
if [ -f "$TMP/out.bin" ]; then
  got="$("$PY" -c 'import sys;print(open(sys.argv[1],"rb").read()[:4].hex(" "))' "$TMP/out.bin")"
  if [ "$got" = "0b f0 00 04" ]; then
    ok "the first four bytes are the boot loader's, not just 48 bytes of something"
  else
    bad "content wrong: first four bytes are '$got', expected '0b f0 00 04'"
  fi
  sz="$(stat -c %s "$TMP/out.bin")"
  [ "$sz" = "48" ] && ok "output is exactly 48 bytes" || bad "output is $sz bytes, expected 48"
else
  bad "no output file was written"
fi
echo
echo "=== rescue: the one write this tool is allowed to make ==="

# `rescue` sends AUTOBURN: 0, which FORBIDDEN blocks for `cmd`. The exception is
# argued in cmd_rescue's docstring, and it is only defensible while the value it
# can emit is fixed. These cases are about that, and they need no device.

# NOT `cmd 2>&1 | grep -q ...`. This file runs under `set -o pipefail`, and
# `grep -q` exits the instant it matches, so the writer takes SIGPIPE and the
# pipeline reports 141 for a SUCCESSFUL match. That is instrument bug 15,
# already recorded in PROGRESS.md -- and it was reintroduced here on
# 2026-08-17, in the guard suite, which is the one place it is least visible.
# Capture first, test second.
out="$("$PY" tools/console-dump.py rescue --ip 999.1.1.1 2>&1)"
case "$out" in
  *"not a dotted quad"*) ok "rescue refuses an address that is not a dotted quad" ;;
  *) bad "rescue accepted 999.1.1.1: $out" ;;
esac

out="$("$PY" tools/console-dump.py rescue --ip 10.1.1.1 --autoburn 1 2>&1)"
case "$out" in
  *"unrecognized arguments"*|*"invalid choice"*)
    ok "there is no flag that turns autoburn ON" ;;
  *) bad "rescue took an --autoburn flag; the exception to FORBIDDEN is no longer narrow" ;;
esac

# The source itself must contain no way to emit the dangerous value. A flag is
# not the only way one could appear.
if grep -q 'AUTOBURN: 1' tools/console-dump.py; then
  bad "the literal 'AUTOBURN: 1' appears in the source"
else
  ok "the string 'AUTOBURN: 1' does not exist anywhere in the tool"
fi

# LOADADDR joined FORBIDDEN on 2026-08-21 and got a narrow home here, for the
# same reason AUTOBURN did: refusing outright pushes the operator to type it
# into picocom, and 0x8040D3A8 decides where the next upload lands, where a read
# is served from, and what the auto-execute path jumps to.
out="$("$PY" tools/console-dump.py cmd LOADADDR 81000000 2>&1)"
case "$out" in
  *"refusing to send"*) ok "cmd refuses LOADADDR: it is loader state, and cmd only reads" ;;
  *) bad "cmd was willing to send LOADADDR: $out" ;;
esac

out="$("$PY" tools/console-dump.py rescue --ip 10.1.1.1 --load-addr 0x80410000 2>&1)"
case "$out" in
  *"loader's own image"*) ok "rescue refuses a load address inside the loader's own image" ;;
  *) bad "an upload address inside the loader was accepted: $out" ;;
esac

out="$("$PY" tools/console-dump.py rescue --ip 10.1.1.1 --load-addr 0x00300000 2>&1)"
case "$out" in
  *"outside KSEG"*) ok "rescue refuses a load address outside KSEG0/KSEG1" ;;
  *) bad "an unmapped load address was accepted: $out" ;;
esac

out="$("$PY" tools/console-dump.py rescue --ip 10.1.1.1 --load-addr 0x80500002 2>&1)"
case "$out" in
  *"word aligned"*) ok "rescue refuses a load address that is not word aligned" ;;
  *) bad "a misaligned load address was accepted: $out" ;;
esac

# And, as with AUTOBURN, the source must contain no way to send the value that
# hands the jump to the loader instead of to a person.
if grep -qE '"(nfjrom|boot\.img)"' tools/console-dump.py; then
  bad "this tool can name one of the loader's auto-execute filenames"
else
  ok "no auto-execute filename appears in this tool at all"
fi

# And the reply assertions, which are what make a silent no-op impossible.
for needle in 'AutoBurning=1' 'AutoBurning=0' 'Sending nothing further'; do
  if grep -q "$needle" tools/console-dump.py; then
    ok "rescue checks the loader's reply for '$needle'"
  else
    bad "rescue does not mention '$needle'"
  fi
done

echo

echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
