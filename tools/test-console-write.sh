#!/usr/bin/env bash
# Guard suite for tools/console-write.py -- the only tool in this repository
# that can destroy the unit.
#
# Everything else here can be re-run.  A wrong FLW cannot: the boot loader at
# 0x000000 is what the recovery path itself runs on, and H601 at 0x006000 holds
# this unit's MAC addresses and radio calibration, which exist nowhere else and
# which a factory reset does not restore.  So the refusals below are not a
# quality exercise; each one is a specific way this unit could have been lost.
#
# Two halves, and the second is what makes the first mean anything:
#
#   * refusals -- every route to writing the wrong bytes, the wrong length, or
#     the wrong place, driven through --dry-run so no device is needed;
#   * positive controls -- a legitimate write and a legitimate drill must be
#     ACCEPTED, and the command lines they emit must be exactly right.  A suite
#     of refusals passes just as well against a tool that refuses everything,
#     and that tool would be useless at the moment it is needed.
#
#   bash tools/test-console-write.sh
#
set -uo pipefail

cd "$(dirname "$0")/.." || { echo "  FAIL  cannot cd to the repository root"; exit 1; }
PY="${FWRE_PY:-python3}"
TOOL="tools/console-write.py"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
ok()  { echo "  ok    $1"; pass=$((pass + 1)); }
bad() { echo "  FAIL  $1"; fail=$((fail + 1)); }

# 16 KiB of recognisable, non-blank content standing in for a COMPDS restore.
"$PY" - "$TMP/payload.bin" <<'PYEOF'
import sys
open(sys.argv[1], "wb").write(bytes((i * 7 + 1) & 0xFF for i in range(0x4000)))
PYEOF
SHA="$("$PY" -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$TMP/payload.bin")"

printf '\xde\xad\xbe\xef\xde\xad\xbe\xef' > "$TMP/eight.bin"
"$PY" -c 'import sys;open(sys.argv[1],"wb").write(b"\xff"*0x1000)' "$TMP/blank.bin"
"$PY" -c 'import sys;open(sys.argv[1],"wb").write(bytes(0x1000))' "$TMP/sector.bin"
SHA_SECTOR="$("$PY" -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$TMP/sector.bin")"

# All refusal cases go through --dry-run: the point is that the tool stops
# before it opens the port, not that it stops after talking to the device.
refuse() {
  local label="$1" needle="$2"; shift 2
  local out rc
  out="$("$PY" "$TOOL" "$@" --dry-run 2>&1)"; rc=$?
  if [ "$rc" -eq 0 ]; then
    bad "$label — ACCEPTED when it should have refused"
  # `--` matters: several of these needles begin with `--`, and without it grep
  # reads the needle as its own option and reports every case as a wrong-reason
  # failure. Three cases failed that way on the first run of this suite.
  elif printf '%s' "$out" | grep -qF -- "$needle"; then
    ok "$label"
  else
    bad "$label — refused for the wrong reason: $(printf '%s' "$out" | head -2 | tr '\n' ' ')"
  fi
}

echo "console-write guard suite"
echo
echo "=== the ranges that must be unreachable ==="

refuse "the boot loader at 0x000000 is refused" "boot loader" \
  write --flash 0x0 --length 0x1000 --input "$TMP/sector.bin" \
        --confirm 0x0 --expect-sha256 "$SHA_SECTOR"

refuse "H601 at 0x006000 is refused — the MACs and radio calibration" "H601" \
  write --flash 0x6000 --length 0x1000 --input "$TMP/sector.bin" \
        --confirm 0x6000 --expect-sha256 "$SHA_SECTOR"

refuse "the kernel/rootfs region is refused" "kernel, rootfs" \
  write --flash 0x100000 --length 0x1000 --input "$TMP/sector.bin" \
        --confirm 0x100000 --expect-sha256 "$SHA_SECTOR"

# The dangerous one: the *start* is allowed, so a range check that only looked
# at the offset would let this through and take H601 with it.
refuse "a range starting in H601 and ending in COMPDS is refused whole" "H601" \
  write --flash 0x7000 --length 0x2000 --input "$TMP/payload.bin" \
        --confirm 0x7000 --expect-sha256 "$SHA"

# And the mirror: starting inside the allow-list, running out of it. It names
# the kernel rather than the allow-list, which is the more useful message —
# the answer to "why not" is what it would have hit, not what it missed.
refuse "a range that starts in COMPCS and runs past 0x010000 is refused" \
  "kernel, rootfs" \
  write --flash 0xF000 --length 0x2000 --input "$TMP/payload.bin" \
        --confirm 0xF000 --expect-sha256 "$SHA"

echo
echo "=== the interlocks on a legitimate range ==="

refuse "no --confirm is refused" "--confirm must repeat" \
  write --flash 0x8000 --length 0x4000 --input "$TMP/payload.bin" \
        --expect-sha256 "$SHA"

refuse "a --confirm that does not match --flash is refused" "--confirm must repeat" \
  write --flash 0x8000 --length 0x4000 --input "$TMP/payload.bin" \
        --confirm 0x9000 --expect-sha256 "$SHA"

refuse "no --expect-sha256 is refused outside the drill sector" "--expect-sha256 is required" \
  write --flash 0x8000 --length 0x4000 --input "$TMP/payload.bin" --confirm 0x8000

refuse "a payload that does not match --expect-sha256 is refused" \
  "does not match --expect-sha256" \
  write --flash 0x8000 --length 0x4000 --input "$TMP/payload.bin" \
        --confirm 0x8000 --expect-sha256 "$(printf '%064d' 0)"

refuse "a source file shorter than --length is refused" "A short file is exactly" \
  write --flash 0x8000 --length 0x4000 --input "$TMP/eight.bin" \
        --confirm 0x8000 --expect-sha256 "$SHA"

refuse "an offset that is not sector-aligned is refused" "not whole 4 KiB sectors" \
  write --flash 0x8800 --length 0x1000 --input "$TMP/sector.bin" \
        --confirm 0x8800 --expect-sha256 "$SHA_SECTOR"

refuse "a length that is not a whole number of sectors is refused" "not whole 4 KiB sectors" \
  write --flash 0x8000 --length 8 --input "$TMP/eight.bin" --confirm 0x8000 \
        --expect-sha256 "$("$PY" -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$TMP/eight.bin")"

BLANK_SHA="$("$PY" -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$TMP/blank.bin")"
refuse "an all-0xFF payload is refused by default" "entirely 0xFF" \
  write --flash 0x8000 --length 0x1000 --input "$TMP/blank.bin" \
        --confirm 0x8000 --expect-sha256 "$BLANK_SHA"

refuse "--eb-bytes 0 is refused rather than looping forever" "must be positive" \
  write --flash 0x3F0000 --input "$TMP/eight.bin" --eb-bytes 0

echo
echo "=== positive controls — a tool that refuses everything is useless ==="

if out="$("$PY" "$TOOL" write --flash 0x8000 --length 0x4000 --input "$TMP/payload.bin" \
          --confirm 0x8000 --expect-sha256 "$SHA" --dry-run -o "$TMP/report.json" 2>&1)"; then
  if printf '%s' "$out" | grep -q '4 sector(s)'; then
    ok "positive control: a well-formed 16 KiB COMPDS restore is accepted, as 4 sectors"
  else
    bad "positive control: accepted but did not plan 4 sectors"
  fi
else
  bad "positive control: a legitimate restore was refused — $(printf '%s' "$out" | head -2)"
fi

if [ -f "$TMP/report.json" ]; then
  ok "a transcript is written even on a dry run"
else
  bad "no transcript was written"
fi

# The drill sector is deliberately looser: eight bytes, no sha256, no --confirm.
if "$PY" "$TOOL" write --flash 0x3F0000 --input "$TMP/eight.bin" --dry-run >/dev/null 2>&1; then
  ok "positive control: the drill sector takes an 8-byte write with no sha256"
else
  bad "the drill sector refused the rehearsal it exists for"
fi

if "$PY" "$TOOL" write --flash 0x3F0000 --input "$TMP/blank.bin" --allow-blank \
     --dry-run >/dev/null 2>&1; then
  ok "positive control: --allow-blank permits the drill's step 6"
else
  bad "--allow-blank did not permit an all-0xFF drill write"
fi

echo
echo "=== the command lines themselves ==="

# The reversed-argument trap.  FLR is <ram> <flash> <len> and FLW is
# <flash> <ram> <len>; getting it backwards here writes RAM contents to the
# address that should have been the source.  Assert the order, not the shape.
out="$("$PY" "$TOOL" write --flash 0x3F0000 --input "$TMP/eight.bin" \
       --ram 0x80600000 --dry-run 2>&1)"
if printf '%s' "$out" | grep -q 'FLW 3F0000 80600000 8'; then
  ok "FLW is emitted as <flash> <ram> <len> — the reverse of FLR's order"
else
  bad "FLW argument order is wrong: $(printf '%s' "$out" | grep FLW | head -1)"
fi

if printf '%s' "$out" | grep -q 'EB 80600000 DE AD BE EF DE AD BE EF'; then
  ok "EB stages to RAM as uppercase hex bytes on one line"
else
  bad "EB line is not the measured form: $(printf '%s' "$out" | grep EB | head -1)"
fi

# One FLW per sector, and never one that crosses a boundary.  A write of 16
# bytes straddling 0x3F0FF8 must come out as two FLWs, 8 bytes each.
"$PY" -c 'import sys;open(sys.argv[1],"wb").write(bytes(range(16)))' "$TMP/sixteen.bin"
out="$("$PY" "$TOOL" write --flash 0x3F0FF8 --input "$TMP/sixteen.bin" --dry-run 2>&1)"
# Anchored on the `==>` marker: a loose `grep -c 'FLW '` also matches the header
# line's "one FLW each" and reports three commands where two were emitted.
n="$(printf '%s' "$out" | grep -cE '==> +FLW ')"
if [ "$n" -eq 2 ] && printf '%s' "$out" | grep -q 'FLW 3F0FF8 .* 8' &&
   printf '%s' "$out" | grep -q 'FLW 3F1000 .* 8'; then
  ok "a write straddling a sector boundary is split into two FLWs"
else
  bad "sector splitting is wrong: $n FLW line(s)"
fi

if "$PY" "$TOOL" probe-eb --dry-run 2>&1 | grep -q '^ *==> *EB '; then
  ok "probe-eb emits EB lines"
else
  bad "probe-eb emitted no EB line"
fi

if "$PY" "$TOOL" probe-eb --dry-run 2>&1 | grep -q 'FLW'; then
  bad "probe-eb emitted an FLW — it must never touch flash"
else
  ok "probe-eb emits no FLW at all — it is a RAM-only measurement"
fi

echo
echo "=== structural: the allow-list cannot be widened by accident ==="

# Reading the constant rather than the behaviour, so that a future edit adding a
# third range fails here and has to be argued for in a diff.
if "$PY" - <<'PYEOF'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("cw", "tools/console-write.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
ranges = [(lo, hi) for lo, hi, _, _ in m.WRITABLE]
assert ranges == [(0x3F0000, 0x400000), (0x008000, 0x010000)], ranges
# H601 and the loader must be covered by NEVER, not merely absent from WRITABLE.
covered = lambda a: any(lo <= a < hi for lo, hi, _ in m.NEVER)
assert covered(0x006000) and covered(0x007FFF) and covered(0x000000), "H601/loader not in NEVER"
sys.exit(0)
PYEOF
then
  ok "the allow-list is exactly the drill sector and the config region"
else
  bad "the allow-list has changed shape — that is a decision, not a refactor"
fi

if grep -q 'AUTOBURN' "$TOOL"; then
  bad "AUTOBURN appears in the source — this tool must never touch the burn switch"
else
  ok "AUTOBURN appears nowhere in the source"
fi

echo
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
