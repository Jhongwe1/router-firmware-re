#!/usr/bin/env bash
# Guard suite for tools/qemu-env.sh.
#
# The environment that script builds is the only place a result can be produced
# by *running* this unit's firmware rather than by reading it, so a silent
# defect in it would contaminate everything downstream. Two failure modes are
# specific to it and neither is visible in the output of a successful run:
#
#   1. a wrong or truncated flash image still lets the guest start, and every
#      MIB value then comes from somewhere that is not this device;
#   2. `flash`, `boa` and `sysconf` cache the MIB table in System V shared
#      memory, which belongs to the host kernel and outlives the guest. A test
#      that restores /dev/mtdblock0 and nothing else reads the previous test's
#      values. This is not hypothetical: the first measurement session produced
#      a diff containing a field it had never written.
#
# So this suite drives the refusals directly. Each case asserts on ITS OWN
# failure message rather than on the exit status -- on this script's first run,
# three cases "failed" and all three were one unrelated bug ($HOME is /root
# under sudo), which an exit-status check would have counted as three passes.
#
#   bash tools/test-qemu-env.sh
#
# Cases needing neither root nor the flash dump run everywhere, including CI.
# The rest report themselves as skipped rather than quietly not running.
set -uo pipefail

cd "$(dirname "$0")/.." || { echo "  FAIL  cannot cd to the repository root"; exit 1; }
TOOL=tools/qemu-env.sh

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0; skip=0
ok()   { echo "  ok    $1"; pass=$((pass + 1)); }
bad()  { echo "  FAIL  $1"; fail=$((fail + 1)); }
skipped() { echo "  skip  $1"; skip=$((skip + 1)); }

# must_refuse <label> <substring the message must contain> <cmd...>
must_refuse() {
  local label="$1" want="$2"; shift 2
  local out rc
  out="$("$@" 2>&1)"; rc=$?
  if [ "$rc" -eq 0 ]; then
    bad "$label -- it succeeded and must not have"
  elif [[ "$out" == *"$want"* ]]; then
    ok "$label"
  else
    bad "$label -- refused for the WRONG reason:"
    echo "$out" | sed 's/^/          /'
  fi
}

must_accept() {
  local label="$1"; shift
  local out rc
  out="$("$@" 2>&1)"; rc=$?
  if [ "$rc" -eq 0 ]; then
    ok "$label"
  else
    bad "$label -- the control failed, so every case above proves nothing:"
    echo "$out" | sed 's/^/          /'
  fi
}

echo "tools/qemu-env.sh -- refusals that need no hardware"

# 1. no subcommand at all
must_refuse "no subcommand prints usage and exits 2" "usage:" bash "$TOOL"

# 2. an unknown subcommand is not silently treated as `run`
must_refuse "unknown subcommand refused" "usage:" bash "$TOOL" definitely-not-a-command

# 3. a dump that is not this unit's image. The hash is the only thing standing
#    between "measured on this device" and "measured on something else", so it
#    has to be checked before anything is copied.
mkdir -p "$TMP/fake/dumps" "$TMP/fake/extracted/unit-2018/squashfs-root"
head -c 4194304 /dev/zero > "$TMP/fake/dumps/flash-n150rt-console-1.bin"
must_refuse "wrong flash image refused by hash" "hash mismatch" \
  env FWRE_WORK="$TMP/fake" bash "$TOOL" build

# 4. a missing dump is named as such rather than crashing later
rm -f "$TMP/fake/dumps/flash-n150rt-console-1.bin"
must_refuse "absent flash image named, not crashed on" "no flash dump at" \
  env FWRE_WORK="$TMP/fake" bash "$TOOL" build

# 5. reset before build must not silently do nothing
must_refuse "reset before build refused" "run build first" \
  env FWRE_WORK="$TMP/fake" bash "$TOOL" reset

echo
echo "tools/qemu-env.sh -- the positive control, which needs the dump and root"

WORK="${FWRE_WORK:-$(getent passwd "${SUDO_USER:-$(id -un)}" | cut -d: -f6)/fwre-work}"
DUMP="$WORK/dumps/flash-n150rt-console-1.bin"
ENVDIR="$WORK/qemu-env-2018"

if [ ! -f "$DUMP" ]; then
  skipped "no flash dump at $DUMP (it is not in the repository, by policy)"
elif [ "$(id -u)" -ne 0 ]; then
  skipped "not root; chroot cases need 'sudo bash $0'"
elif ! command -v qemu-mips-static >/dev/null; then
  skipped "qemu-mips-static not installed"
elif [ ! -d "$ENVDIR" ]; then
  skipped "no environment at $ENVDIR (run: sudo bash $TOOL build)"
else
  drop_shm() {
    local id
    for id in $(ipcs -m | awk 'NR>3 && $2 ~ /^[0-9]+$/ {print $2}'); do ipcrm -m "$id" 2>/dev/null || true; done
    for id in $(ipcs -s | awk 'NR>3 && $2 ~ /^[0-9]+$/ {print $2}'); do ipcrm -s "$id" 2>/dev/null || true; done
  }

  bash "$TOOL" reset >/dev/null 2>&1
  must_accept "control passes on a correct environment" bash "$TOOL" check

  cp "$ENVDIR/dev/mtdblock0" "$TMP/keep.bin"

  # The configuration region zeroed: the guest still starts, and without a
  # control the run would report values that are not this device's.
  dd if=/dev/zero of="$ENVDIR/dev/mtdblock0" bs=4096 count=1 seek=12 conv=notrunc 2>/dev/null
  drop_shm
  must_refuse "zeroed config region caught by the control" "control FAILED" \
    bash "$TOOL" check

  cp "$TMP/keep.bin" "$ENVDIR/dev/mtdblock0"
  : > "$ENVDIR/dev/mtdblock0"
  drop_shm
  must_refuse "empty device file caught by the control" "control FAILED" \
    bash "$TOOL" check

  cp "$TMP/keep.bin" "$ENVDIR/dev/mtdblock0"
  drop_shm
  must_accept "reset restores the environment" bash "$TOOL" reset
  must_accept "control passes again after reset" bash "$TOOL" check
  must_accept "diff is empty on a clean environment" bash "$TOOL" diff

  # The measurement this environment exists for, end to end: one shell command
  # of the shape boa's sprintf() produces, and both observation channels.
  bash "$TOOL" run /bin/sh -c \
    'flash set HW_WLAN0_WSC_PIN 1;ls -l / > /var/web/probe.txt 2>&1;#' >/dev/null 2>&1
  out="$(bash "$TOOL" diff 2>&1)"; rc=$?
  if [ "$rc" -eq 0 ] && [[ "$out" == *"balances"* ]] && [[ "$out" == *"0x006493"* ]]; then
    ok "injected command changes 3 bytes and the H601 checksum balances"
  else
    bad "injected command: expected a balancing 3-byte diff, got:"
    echo "$out" | sed 's/^/          /'
  fi
  if [ -s "$ENVDIR/var/web/probe.txt" ]; then
    ok "command output reached the document root (oracle 0)"
  else
    bad "oracle 0: nothing landed in the document root"
  fi
  rm -f "$ENVDIR/var/web/probe.txt"

  # And that reset really does undo the shared-memory half.
  bash "$TOOL" reset >/dev/null 2>&1
  if bash "$TOOL" run /bin/flash get HW_WLAN0_WSC_PIN 2>/dev/null | grep -q '99956042'; then
    ok "reset clears the shared-memory MIB cache, not just the image"
  else
    bad "reset left a previous test's value in shared memory"
  fi
fi

echo
echo "  $pass passed, $fail failed, $skip skipped"
[ "$fail" -eq 0 ]
