#!/usr/bin/env bash
# Guard suite for tools/console-lint.py.
#
# That tool's headline result is a *diagnosis*: it says why the loader answered
# `Unknown command !` to a line that reads perfectly. Two halves have to hold or
# the diagnosis is worthless:
#
#   * it must FIRE on each mechanism, on a fixture built to carry exactly one of
#     them, so a finding names a cause rather than a coincidence;
#   * it must STAY SILENT on a clean session, and it must say `unexplained` when
#     a rejection has none of the known causes. A linter that recognises three
#     patterns and reports nothing else looks identical to one that understands
#     the device -- right up to the moment it matters.
#
#   bash tools/test-console-lint.sh
#
set -uo pipefail

cd "$(dirname "$0")/.." || { echo "  FAIL  cannot cd to the repository root"; exit 1; }
PY="${FWRE_PY:-python3}"
TOOL="tools/console-lint.py"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
ok()  { echo "  ok    $1"; pass=$((pass + 1)); }
bad() { echo "  FAIL  $1"; fail=$((fail + 1)); }

# The device's own framing, so the fixtures are the byte stream the wire
# carries: putchar('\n') emits \n\r (0x80406BA4), the prompt has no newline of
# its own, and the dispatcher prints "\n" after GetLine returns (0x804091A8).
P='\r<RealTek>'
N='\n\r'

mk() { printf "$1" > "$TMP/$2"; }

run() { "$PY" "$TOOL" "$TMP/$1" 2>&1; }
code() { "$PY" "$TOOL" "$TMP/$1" >/dev/null 2>&1; echo $?; }

# --------------------------------------------------------------------------
# the positive control -- a clean session must produce nothing at all
# --------------------------------------------------------------------------
mk "${P}DW 80540000 2${N}80540000:\t03E00008\t00000000${N}${P}J 80540000${N}---Jump to address=80540000${N}${P}" clean.log
out="$(run clean.log)"
if grep -q "0 finding(s)" <<<"$out" && [ "$(code clean.log)" = 0 ]; then
  ok "a clean session produces no findings and exit 0"
else
  bad "a clean session was not clean: $out"
fi

# --------------------------------------------------------------------------
# each mechanism, one per fixture
# --------------------------------------------------------------------------
mk "${P}\x1b[A\x1b[BFLR 80520000 0 100${N}Unknown command !\r${N}${P}" arrows.log
out="$(run arrows.log)"
if grep -q "control-bytes" <<<"$out" && grep -q "0x1b" <<<"$out"; then
  ok "arrow keys in the line are reported as control bytes"
else
  bad "arrow keys were not caught: $out"
fi

mk "${P}\tDW 80540000 2${N}Unknown command !\r${N}${P}" tab.log
out="$(run tab.log)"
if grep -q "control-bytes" <<<"$out" && grep -q "0x09 TAB" <<<"$out"; then
  ok "a TAB in the line is reported, and named as the eight-space expansion"
else
  bad "a TAB was not caught: $out"
fi

mk "${P} DW 80540000 2${N}Unknown command !\r${N}${P}" lead.log
out="$(run lead.log)"
if grep -q "leading-whitespace" <<<"$out" && grep -q "would have run DW" <<<"$out"; then
  ok "a leading space is reported, with the command it would have run"
else
  bad "a leading space was not caught: $out"
fi

mk "${P}zzz 1${N}Unknown command !\r${N}${P}" notcmd.log
out="$(run notcmd.log)"
if grep -q "not-a-command" <<<"$out" && grep -q "'ZZZ'" <<<"$out"; then
  ok "a name outside the seventeen is reported, upper-cased as strupr leaves it"
else
  bad "an unknown name was not reported: $out"
fi

mk "${P}help${N}Unknown command !\r${N}${P}" help.log
out="$(run help.log)"
if grep -q "not-a-command" <<<"$out" && grep -q "'HELP'" <<<"$out"; then
  ok "lower case is folded before the comparison, as strupr at 0x80407040 does"
else
  bad "case folding was not applied: $out"
fi

# --------------------------------------------------------------------------
# the one this tool exists for: a repaint carrying a buffer across
# --------------------------------------------------------------------------
mk "${P}        ${N}**TFTP GET File probe,Size 00000000 Byte${N}.Success!${N}<RealTek>EB 80540000 03 E0${N}Unknown command !\r${N}${P}" repaint.log
out="$(run repaint.log)"
if grep -q "tftp-repaint" <<<"$out" \
   && grep -q "leading-whitespace" <<<"$out" \
   && grep -q "would have run EB" <<<"$out"; then
  ok "a prompt printed by the TFTP path carries the buffer across, and the next line's argv[0] is empty"
else
  bad "the repaint carry-over was not reconstructed: $out"
fi

# ...and the negative control for that rule. `Flash Read Successed!` is printed
# by the FLR handler in the command context and carries no %s, so the prompt
# after it IS a prompt and the buffer IS clear.
mk "${P}FLR 80570000 3F0000 200${N}Flash Read Successed!${N}${P}DB 80570000 272${N}" flr.log
out="$(run flr.log)"
if grep -q "(0 printed by the TFTP path)" <<<"$out" && grep -q "0 finding(s)" <<<"$out"; then
  ok "\`Flash Read Successed!\` is not treated as a repaint -- it has no %s"
else
  bad "FLR's message was misread as a repaint: $out"
fi

# --------------------------------------------------------------------------
# the refusal that keeps the other seven honest
# --------------------------------------------------------------------------
mk "${P}DW 80540000 2${N}Unknown command !\r${N}${P}" mystery.log
out="$(run mystery.log)"
if grep -q "unexplained-rejection" <<<"$out" && [ "$(code mystery.log)" = 1 ]; then
  ok "a rejection with none of the known causes is reported unexplained, exit 1"
else
  bad "an unexplained rejection was swallowed: $out (exit $(code mystery.log))"
fi

# --------------------------------------------------------------------------
# the erase echo is the device's, not the operator's
# --------------------------------------------------------------------------
mk "${P}DX\x08 \x08W 80540000 2${N}80540000:\t03E00008${N}${P}" erase.log
out="$(run erase.log)"
if grep -q "0 finding(s)" <<<"$out"; then
  ok "the BS-space-BS erase echo is applied, not reported as a control byte"
else
  bad "the erase echo was reported as damage: $out"
fi

# --------------------------------------------------------------------------
# --expect-clean turns any finding into a failure
# --------------------------------------------------------------------------
if [ "$("$PY" "$TOOL" --expect-clean "$TMP/lead.log" >/dev/null 2>&1; echo $?)" = 1 ] \
   && [ "$("$PY" "$TOOL" --expect-clean "$TMP/clean.log" >/dev/null 2>&1; echo $?)" = 0 ]; then
  ok "--expect-clean fails on a finding and passes on a clean log"
else
  bad "--expect-clean does not discriminate"
fi

# --------------------------------------------------------------------------
# a missing file is an error, not an empty report
# --------------------------------------------------------------------------
if [ "$("$PY" "$TOOL" "$TMP/nope.log" >/dev/null 2>&1; echo $?)" = 2 ]; then
  ok "a missing log exits 2 rather than reporting a clean session"
else
  bad "a missing log did not error"
fi

# --------------------------------------------------------------------------
# the JSON carries the same verdict as the text
# --------------------------------------------------------------------------
"$PY" "$TOOL" --quiet --json "$TMP/rep.json" "$TMP/repaint.log" >/dev/null 2>&1
if "$PY" - "$TMP/rep.json" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1]))
kinds = {f["kind"] for f in d["findings"]}
assert "tftp-repaint" in kinds and "leading-whitespace" in kinds, kinds
assert d["repaints"] == 1, d["repaints"]
assert d["rejections"] == d["rejections_accounted_for"] == 1, d
PYEOF
then
  ok "the JSON report carries the findings and the accounting"
else
  bad "the JSON report disagrees with the text output"
fi

echo
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ]
