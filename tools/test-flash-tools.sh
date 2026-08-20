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

echo "=== tools/flash-read.sh: parsing what flashrom actually says ==="
# Captured from flashrom 1.3.0-2.1ubuntu2, the build on this workstation. These
# are here because two of the patterns they exercise were wrong for four days
# and printed nothing rather than failing -- so nothing in the suite, and
# nothing at the bench, would have said so. Instrument bug 50.
cat > "$TMP/probe-good.log" <<'LOG'
flashrom unknown on Linux 6.6.87.2-microsoft-standard-WSL2 (x86_64)
flashrom is free software, get the source code at https://flashrom.org
Probing for Eon EN25QH32, 4096 kB: RDID returned 0x1c 0x70 0x16. probe_spi_rdid_generic: id1 0x1c, id2 0x7016
Probing for Eon EN25Q32(A/B), 4096 kB: RDID returned 0x1c 0x70 0x16. Chip status register is 0x00.
Found Eon flash chip "EN25QH32" (4096 kB, SPI) on ch341a_spi.
LOG

cat > "$TMP/probe-forced.log" <<'LOG'
flashrom unknown on Linux 6.6.87.2-microsoft-standard-WSL2 (x86_64)
Assuming Eon flash chip "EN25QH32" (4096 kB, SPI) on ch341a_spi.
LOG

cat > "$TMP/probe-unstable.log" <<'LOG'
Probing for Eon EN25QH32, 4096 kB: RDID returned 0x1c 0x70 0x16. Ok.
Probing for Eon EN25Q32(A/B), 4096 kB: RDID returned 0x1c 0x70 0x14. Ok.
LOG

eq() {  # label want got
  if [ "$2" = "$3" ]; then ok "$1"; else
    bad "$1 -- wanted [$2], got [$3]"; fi
}

eq "the chip name survives a vendor string containing the letter n" \
   "EN25QH32" "$(parse_chip_name "$TMP/probe-good.log")"
eq "a matched identification reports the verb Found" \
   "Found" "$(parse_chip_verb "$TMP/probe-good.log")"
eq "a name supplied with -c is reported as Assuming, not as a source" \
   "Assuming" "$(parse_chip_verb "$TMP/probe-forced.log")"
eq "a version banner that says 'unknown' is still recorded, not dropped" \
   "flashrom unknown on Linux 6.6.87.2-microsoft-standard-WSL2 (x86_64)" \
   "$(parse_flashrom_version "$TMP/probe-good.log")"
eq "dozens of identical RDID lines collapse to one id" \
   "1c7016" "$(parse_rdids "$TMP/probe-good.log")"
eq "two distinct RDID values are BOTH returned, so the caller can refuse" \
   "1c7014
1c7016" "$(parse_rdids "$TMP/probe-unstable.log")"
eq "a log with no identification line yields an empty name, not a guess" \
   "" "$(parse_chip_name "$TMP/probe-unstable.log")"
echo

# Instrument bug 51: these two logs are the difference between "re-seat the
# clip" and "do not touch the clip", and until 2026-08-21 the tool printed the
# first message for both. The fixture below is the real shape of a flashrom
# 1.3.0 -VVV log, including the four-byte RDID4 line, which must NOT be counted
# as a second, disagreeing id.
cat > "$TMP/probe-noprint.log" <<'LOG'
flashrom unknown on Linux 6.6.87.2-microsoft-standard-WSL2 (x86_64)
Found Eon flash chip "EN25QH32" (4096 kB, SPI) on ch341a_spi.
LOG

cat > "$TMP/probe-dead.log" <<'LOG'
flashrom unknown on Linux 6.6.87.2-microsoft-standard-WSL2 (x86_64)
No EEPROM/flash device found.
LOG

cat > "$TMP/probe-rdid4.log" <<'LOG'
RDID returned 0xef 0x40 0x18. Ignoring RES in favour of RDID.
RDID returned 0xef 0x40 0x18 0xff. compare_id: id1 0xef, id2 0x4018
RDID returned 0xef 0x40 0x18. compare_id: id1 0xef, id2 0x4018
LOG

eq "a log with an identification line but no RDID is NOT a contact problem" \
   "not-printed" "$(rdid_failure_kind "$TMP/probe-noprint.log")"
eq "a log with nothing identified at all IS a contact problem" \
   "no-answer" "$(rdid_failure_kind "$TMP/probe-dead.log")"
eq "a four-byte RDID4 line does not become a second, disagreeing id" \
   "ef4018" "$(parse_rdids "$TMP/probe-rdid4.log")"
echo
echo "=== tools/flash-read.sh: probe(), end to end, against a real flashrom ==="
# No clip, no router, no CH341A: flashrom's own dummy programmer answers RDID
# out of its table, which is enough to drive every line of probe(). This case
# exists because the four parsers above are only half the claim -- the other
# half is that probe() asks flashrom for a verbosity at which the line it
# parses is actually printed, and on 2026-08-21 it did not. Instrument bug 51.
if command -v flashrom >/dev/null 2>&1; then
  ( export FLASH_READ_PROGRAMMER="dummy:emulate=W25Q128FV"
    PROGRAMMER="$FLASH_READ_PROGRAMMER"
    DEST="$TMP/e2e"; mkdir -p "$DEST"

    out="$(probe ef4018 2>&1)"; rc=$?
    [ $rc -eq 0 ] \
      && [[ "$out" == *"matches the prediction"* ]] \
      && [[ "$out" == *"JEDEC id  0xef4018"* ]] \
      && echo "  ok    probe reads an id out of a real flashrom log and matches it" \
      || { echo "  FAIL  probe could not identify the dummy part (rc=$rc)"; echo "$out" | sed 's/^/          /'; exit 1; }

    [[ "$out" == *"flashrom calls it: W25Q128.V"* ]] \
      && echo "  ok    probe reports the name flashrom's own id-keyed table gives" \
      || { echo "  FAIL  the chip name is missing from a real probe"; exit 1; }

    out="$(probe 1c7016 2>&1)"; rc=$?
    [ $rc -ne 0 ] && [[ "$out" == *"PREDICTION MISSED"* ]] \
      && echo "  ok    a wrong prediction fails the probe, so the test can fail" \
      || { echo "  FAIL  a wrong prediction did not fail the probe (rc=$rc)"; exit 1; }

    out="$(cmd_read --label nope --expect-id ef4018 --yes 2>&1)"; rc=$?
    [ $rc -ne 0 ] && [[ "$out" == *"probing only"* ]] \
      && echo "  ok    a READ through the dummy is refused, not recorded" \
      || { echo "  FAIL  a dummy read was not refused (rc=$rc)"; exit 1; }
  )
  if [ $? -eq 0 ]; then pass=$((pass + 4)); else fail=$((fail + 1)); fi
else
  echo "  --    flashrom absent, probe() end-to-end not exercised"
fi
echo

echo "=== the two clip tools do not get their own opinion of flashrom ==="
# Instrument bugs 50 and 51 were one wrong belief with two homes. Fixing both
# copies fixes today; this case is about tomorrow. It fails if either tool grows
# its own probe verbosity or its own copy of the parse.
for f in tools/flash-read.sh tools/flash-write.sh; do
  if grep -q 'lib/flashrom-parse.sh' "$f"; then
    ok "$f sources the one owner of flashrom's output format"
  else
    bad "$f no longer sources tools/lib/flashrom-parse.sh"
  fi
  if grep -qE 'flashrom_(ro|rw) +-V+ ' "$f"; then
    bad "$f hardcodes a probe verbosity again instead of \$FLASHROM_PROBE_V"
  else
    ok "$f asks the shared constant for the probe verbosity"
  fi
  if grep -qE "grep .*'RDID returned" "$f"; then
    bad "$f grew its own copy of the RDID parse"
  else
    ok "$f has no private copy of the RDID parse"
  fi
done
# And the constant has to be the value that was actually measured, not a value
# that merely exists: -V and -VV both produce zero RDID lines on flashrom 1.3.0.
if [ "$FLASHROM_PROBE_V" = "-VVV" ]; then
  ok "the shared probe verbosity is the measured one (-VVV)"
else
  bad "FLASHROM_PROBE_V is $FLASHROM_PROBE_V; -V and -VV print no RDID line at all"
fi
echo

echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
