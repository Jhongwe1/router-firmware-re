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

echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
