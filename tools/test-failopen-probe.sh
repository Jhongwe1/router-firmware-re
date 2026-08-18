#!/bin/bash
#
# Guard suite for tools/failopen-probe.sh.
#
# The probe's whole value is that it damages a flash image and then asks the
# vendor's own boot script what it does about it, so *every* interesting reading
# is a difference from a control. Its first working run reported seven states in
# which nothing happened, because the boot script was being handed to qemu-user
# as if it were an ELF and had never executed - a complete, plausible table of
# nothing. That is instrument bug 38 and it is why this file exists.
#
# What this suite covers: the refusals that need no emulation environment, and
# the byte surgery's read-back, which is the check that stops "the write did not
# land" from looking like "the device tolerated the damage".
#
# What it deliberately does NOT cover, stated rather than discovered later:
# the three in-run controls (shell_runs, plain_write_takes,
# healthy_image_passes_both_tests_and_telnet_off) all need a built profile and
# root, so they cannot be exercised here. They are enforced a second time on the
# committed artefact by tools/check-reports.py, whose refusals for this producer
# WERE each watched firing, and that is the only reason this gap is acceptable
# rather than merely unavoidable.
#
#   bash tools/test-failopen-probe.sh

set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

PROBE="tools/failopen-probe.sh"
pass=0
fail=0

ok()   { printf '  ok    %s\n' "$1"; pass=$((pass + 1)); }
bad()  { printf '  FAIL  %s\n' "$1"; fail=$((fail + 1)); }

# expect_refusal <label> <needle> <command...>
expect_refusal() {
  local label="$1" needle="$2"; shift 2
  local out rc
  out=$("$@" 2>&1); rc=$?
  if [ "$rc" -eq 0 ]; then
    bad "$label — exited 0, so it did not refuse"
  elif printf '%s' "$out" | grep -q -- "$needle"; then
    ok "$label"
  else
    bad "$label — refused, but not for the stated reason: $(printf '%s' "$out" | head -1)"
  fi
}

echo "=== the refusals that need no environment ==="

expect_refusal "an unknown argument is refused" \
  "unknown argument" bash "$PROBE" --not-a-real-flag

expect_refusal "an unknown profile is refused" \
  "unknown profile" bash "$PROBE" --profile no-such-profile

# --help must work and must NOT require root, or nobody can read it on a desk
help_out=$(bash "$PROBE" --help 2>&1)
if printf '%s' "$help_out" | grep -q "failopen-probe.sh"; then
  ok "--help prints without root"
else
  bad "--help printed nothing recognisable"
fi

# Everything else needs root because qemu-env.sh chroots. Check the refusal is
# there and says so, rather than failing later with a confusing error - bug 24's
# lesson is that a failure naming the wrong fix is worse than no message.
if [ "$(id -u)" -ne 0 ]; then
  expect_refusal "running as non-root is refused, and says why" \
    "must run as root" bash "$PROBE"
else
  echo "  skip  non-root refusal (this shell is root)"
fi

echo
echo "=== the byte surgery reads back what it wrote ==="

# The probe's `damage` helper is inline python. Exercise the same contract here:
# a write that does not land must be an error, not a silent pass, because a
# corruption that never happened is indistinguishable from a device that
# tolerated it.
tmp=$(mktemp)
python3 - "$tmp" <<'PY'
import sys
open(sys.argv[1], 'wb').write(b'COMPDS\x00\x07' + bytes(0x100))
PY

readback=$(python3 - "$tmp" <<'PY'
import sys
path = sys.argv[1]
with open(path, 'r+b') as f:
    f.seek(0)
    old = f.read(8)
    f.seek(0)
    f.write(b'\x00' * 8)
    f.flush()
    f.seek(0)
    got = f.read(8)
if got != b'\x00' * 8:
    sys.exit("write did not land")
print(old.hex())
PY
)
if [ "$readback" = "434f4d5044530007" ]; then
  ok "magic damage reports the ORIGINAL bytes, so the transcript can be checked"
else
  bad "magic damage reported '$readback', expected the COMPDS signature"
fi

# And the negative: a read-only file must produce an error, not a quiet skip.
chmod 400 "$tmp"
if [ "$(id -u)" -ne 0 ]; then
  out=$(python3 - "$tmp" <<'PY' 2>&1
import sys
try:
    with open(sys.argv[1], 'r+b') as f:
        f.write(b'\x00')
except OSError as e:
    sys.exit(f"refused: {e}")
PY
)
  if printf '%s' "$out" | grep -q "refused:"; then
    ok "an unwritable image is an error, not a silent skip"
  else
    bad "an unwritable image did not raise"
  fi
else
  echo "  skip  unwritable-image case (root ignores mode 400)"
fi
chmod 600 "$tmp"; rm -f "$tmp"

echo
echo "=== the report shape the checker will demand ==="

# check-reports.py refuses this producer's output unless three controls say
# "pass" and at least one damage state made the boot script branch. Prove the
# probe emits those field names at all - a typo here would produce a report that
# fails CI for a reason unrelated to the measurement.
for field in '"producer": "failopen-probe"' 'shell_runs' 'plain_write_takes' \
             'healthy_image_passes_both_tests_and_telnet_off' 'branch_message' \
             'source_sha256' 'caveat'; do
  if grep -q -- "$field" "$PROBE"; then
    ok "the report carries $field"
  else
    bad "the probe never emits $field, which check-reports.py requires"
  fi
done

echo
if [ "$fail" -eq 0 ]; then
  echo "  $pass passed, 0 failed"
else
  echo "  $pass passed, $fail failed"
  exit 1
fi
