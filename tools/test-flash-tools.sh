#!/usr/bin/env bash
# Self-test for the screening checks in tools/flash-read.sh.
#
# The screening checks exist to catch a dump that is obviously wrong while the
# clip is still on the chip. They run once, on a day when the hardware is
# attached and the operator is tired — which is the worst possible time to find
# out that a check has a typo in it and silently passes everything.
#
# So they are driven here against synthetic images instead, with no programmer,
# no clip and no router. Four cases: three that MUST be rejected, each asserting
# on its own failure message rather than on the exit status, and one control
# that MUST pass. The control is not padding: on 2026-08-14 a reject-only suite
# in this repository reported 5/5 while every invocation was failing to start,
# and the control is what caught it (PROGRESS.md § G2 checkbox 4).
#
#   bash tools/test-flash-tools.sh
#
set -uo pipefail

cd "$(dirname "$0")/.." || { echo "  FAIL  cannot cd to the repository root"; exit 1; }

# Sourcing brings in `screen` and turns on `set -e`; the suite needs to survive
# its own failing cases, so switch it back off immediately.
# shellcheck source=tools/flash-read.sh
. tools/flash-read.sh
set +e

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

FULL=4194304
pass=0
fail=0
ok()  { echo "  ok    $1"; pass=$((pass + 1)); }
bad() { echo "  FAIL  $1"; fail=$((fail + 1)); }

must_reject() {
  local label="$1" want="$2" file="$3" size="$4" out
  out="$(screen_image "$file" "$size" 2>&1)"
  if [ $? -eq 0 ]; then
    bad "$label -- it PASSED and must not have"
    return
  fi
  if [[ "$out" == *"$want"* ]]; then
    ok "$label"
  else
    bad "$label -- rejected for the WRONG reason:"
    echo "$out" | sed 's/^/          /'
  fi
}

must_accept() {
  local label="$1" file="$2" size="$3" out
  out="$(screen_image "$file" "$size" 2>&1)"
  if [ $? -eq 0 ]; then
    ok "$label"
  else
    bad "$label -- the control failed, so every case above proves nothing:"
    echo "$out" | sed 's/^/          /'
  fi
}

echo "=== building synthetic images ==="
head -c "$FULL" /dev/zero | LC_ALL=C tr '\000' '\377' > "$TMP/all-ff.bin"
head -c $((FULL / 2)) /dev/urandom > "$TMP/half.bin"
cat "$TMP/half.bin" "$TMP/half.bin" > "$TMP/aliased.bin"
head -c "$FULL" /dev/urandom > "$TMP/good.bin"
head -c 100 /dev/urandom > "$TMP/short.bin"
ls -l "$TMP" | sed 's/^/  /'
echo

echo "=== must be rejected ==="
must_reject "a clip making no contact (all 0xFF)" \
            "nothing but 0x00 and 0xFF" "$TMP/all-ff.bin" "$FULL"
must_reject "a 2 MiB part aliasing into 4 MiB"    \
            "halves are identical"      "$TMP/aliased.bin" "$FULL"
must_reject "a short read"                        \
            "expected $FULL"            "$TMP/short.bin"   "$FULL"
echo

echo "=== must be accepted (the control) ==="
must_accept "a full-size image whose halves differ" "$TMP/good.bin" "$FULL"
echo

# ---------------------------------------------------------------------------
# tools/flash-write.sh — the allow-list, driven with no programmer attached.
#
# Added 2026-08-20 with the write path. The safety argument of that file is one
# sentence — "no byte moves unless you named the range it is in, and two ranges
# cannot be named at all" — and a safety argument that has never been made to
# fire is a comment. Every case below is a way the check could be wrong while
# still looking right on the day.
# ---------------------------------------------------------------------------
# shellcheck source=tools/flash-write.sh
. tools/flash-write.sh
set +e

patch_at() {           # patch_at FILE OFFSET NBYTES
  python3 - "$1" "$2" "$3" <<'PYEOF'
import sys
p, off, n = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3], 0)
with open(p, "r+b") as f:
    f.seek(off)
    f.write(bytes([0x5a]) * n)
PYEOF
}

echo "=== tools/flash-write.sh: what the diff sees ==="
truncate -s "$FULL" "$TMP/base.bin"
cp "$TMP/base.bin" "$TMP/same.bin"

out="$(diff_ranges "$TMP/base.bin" "$TMP/same.bin")"
[ -z "$out" ] && ok "two identical images produce no ranges" \
              || bad "identical images produced ranges: $out"

cp "$TMP/base.bin" "$TMP/one.bin"; patch_at "$TMP/one.bin" 0x3FF010 1
out="$(diff_ranges "$TMP/base.bin" "$TMP/one.bin")"
[ "$out" = "0x3ff010-0x3ff011 1" ] && ok "one changed byte is reported as one 1-byte range" \
                                   || bad "one changed byte came back as: $out"

# Two changes 12 bytes apart are ONE erase, not two. A tool that reported them
# separately would let an operator allow one and not notice the other rides along.
cp "$TMP/base.bin" "$TMP/near.bin"
patch_at "$TMP/near.bin" 0x3FF000 4; patch_at "$TMP/near.bin" 0x3FF010 4
out="$(diff_ranges "$TMP/base.bin" "$TMP/near.bin" | wc -l)"
[ "$out" = "1" ] && ok "two changes inside one 4 KiB sector coalesce into one range" \
                 || bad "changes 12 bytes apart came back as $out ranges"

cp "$TMP/base.bin" "$TMP/far.bin"
patch_at "$TMP/far.bin" 0x100000 4; patch_at "$TMP/far.bin" 0x300000 4
out="$(diff_ranges "$TMP/base.bin" "$TMP/far.bin" | wc -l)"
[ "$out" = "2" ] && ok "changes a megabyte apart stay two ranges" \
                 || bad "distant changes came back as $out ranges"

truncate -s 1024 "$TMP/small.bin"
out="$(diff_ranges "$TMP/base.bin" "$TMP/small.bin" 2>&1)"
[ $? -ne 0 ] && ok "images of different sizes are refused, not compared" \
             || bad "a size mismatch was compared anyway: $out"

echo
echo "=== tools/flash-write.sh: the allow-list ==="
range_within 0x3FF010 0x3FF011 "0x3FF000-0x400000" \
  && ok "a change inside an allowed range is inside it" \
  || bad "range_within rejected a range that is plainly inside"

range_within 0x3FEFF0 0x3FF010 "0x3FF000-0x400000" \
  && bad "range_within accepted a range that straddles the lower edge" \
  || ok "a change straddling the edge of an allowed range is NOT inside it"

range_overlaps 0x007FFF 0x008000 "${FORBIDDEN[@]}" \
  && ok "a single byte at the top of H601 counts as touching H601" \
  || bad "range_overlaps missed a one-byte change inside H601"

range_overlaps 0x008000 0x008004 "${FORBIDDEN[@]}" \
  && bad "range_overlaps flagged the byte immediately after H601" \
  || ok "the byte immediately after H601 is not H601"

echo
echo "=== tools/flash-write.sh: the refusal that has to outrank the operator ==="
# The case that matters. An operator who allows the whole part must STILL be
# refused for the boot loader and H601, or the allow-list is advice.
cp "$TMP/base.bin" "$TMP/loader.bin"; patch_at "$TMP/loader.bin" 0x001000 4
out="$(show_plan "$TMP/base.bin" "$TMP/loader.bin" "0x000000-0x400000" 2>&1)"
if [ $? -eq 0 ]; then
  bad "a write into the boot loader was ALLOWED by allowing the whole part"
elif [[ "$out" == *"REFUSED"* ]]; then
  ok "allowing the whole part does not permit the boot loader"
else
  bad "the boot loader write was refused for the wrong reason: $out"
fi

cp "$TMP/base.bin" "$TMP/h601.bin"; patch_at "$TMP/h601.bin" 0x006100 4
out="$(show_plan "$TMP/base.bin" "$TMP/h601.bin" "0x000000-0x400000" 2>&1)"
[ $? -ne 0 ] && [[ "$out" == *"REFUSED"* ]] \
  && ok "allowing the whole part does not permit H601 either" \
  || bad "an H601 write survived the whole-part allow: $out"

out="$(show_plan "$TMP/base.bin" "$TMP/one.bin" "0x3FF000-0x400000" 2>&1)"
[ $? -eq 0 ] && ok "control: a change inside the named range is allowed through" \
             || bad "control: an allowed change was refused, so every case above proves nothing: $out"

out="$(show_plan "$TMP/base.bin" "$TMP/one.bin" "0x00C000-0x00E000" 2>&1)"
[ $? -eq 1 ] && ok "the same change is refused when a different range is named" \
             || bad "naming the wrong range still let the change through"

show_plan "$TMP/base.bin" "$TMP/same.bin" "0x3FF000-0x400000" >/dev/null 2>&1
[ $? -eq 2 ] && ok "an image the chip already holds reports nothing to do, not success" \
             || bad "a no-op write did not report itself as one"
echo

echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
