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

# ---------------------------------------------------------------------------
# 6-12. The two defects of 2026-08-18, both invisible in the output of a
# successful run -- which is the property this whole suite exists for.
#
# A reset refused because another profile still had a live guest, and the fix it
# printed was `--profile 2018 reap`: rejected by its own parser with exit 2,
# because the profile is named `unit-2018` and only its DIRECTORY is
# `qemu-env-2018`. Retyping it correctly then exited 1 having printed nothing
# and killed nothing, because env_pids ended in a `&&` list that is false on the
# final /proc entry and set -e took the script down at the assignment. Together
# they are a closed loop: the reset stays blocked and neither half says why.
#
# Nothing below needs root, a chroot or the flash dump. That is deliberate --
# CI was green while both defects were live.

# 6-8. env_pids under the caller's own shell options, with /proc simulated.
#
# Two things had to be got right here and the first version got both wrong.
#
# (1) These run in a SEPARATE bash process and the status is read afterwards.
#     They must NOT be written as `if ( set -e; ... ); then`, because POSIX
#     disables set -e for everything in the condition of an if -- the same rule
#     as the `|| true` in cmd_reset that hid the defect in the first place. A
#     test written that way passes against the broken function.
#
# (2) `readlink` is stubbed rather than left to read the real /proc. As an
#     ordinary user almost every /proc/PID/root is unreadable, so readlink fails
#     and the iteration ends on `continue`, whose status is 0 -- and the loop's
#     final status is 0, and the defect does not appear. It appears only when
#     readlink SUCCEEDS on the last entry, i.e. only under root, which is the
#     only way reap is ever run. So the defect was invisible to any test that
#     did not simulate the privilege the tool requires, and CI is not root.
#
# exit 1 = set -e ended it at the assignment;  exit 3 = it ran and said the
# wrong thing. Keeping those apart is the point.
env_pids_probe() {   # $1 readlink stub body   $2 ENVDIR   $3 -z or -n
  { echo 'set -euo pipefail'
    sed -n '/^env_pids()/,/^}/p' "$TOOL"
    echo "readlink() { $1 }"
    echo "ENVDIR=$2"
    echo 'pids="$(env_pids)"'
    echo "[ $3 " '"$pids" ] || exit 3'
  } > "$TMP/env_pids_probe.sh"
  bash "$TMP/env_pids_probe.sh" >/dev/null 2>&1
}

# 6. Nothing in this environment: reap must be able to say so, not die saying
#    nothing. Every entry readable, none of them ours -- i.e. root.
env_pids_probe 'echo /elsewhere;' /the/env/dir -z; rc=$?
case "$rc" in
  0) ok "env_pids exits 0 when every entry is readable and none match" ;;
  1) bad "env_pids returned non-zero having found nothing. Under set -e that
        ends cmd_reap at its first assignment: exit 1, no output, nothing
        killed, and the reset that sent you here stays blocked" ;;
  *) bad "env_pids probe (empty case) exited $rc" ;;
esac

# 7. The case that actually happened: there IS something to reap, and it is not
#    the last entry scanned. Under the defect reap exits 1 before the first kill.
one_match='case "$1" in */1/root) echo "$ENVDIR" ;; *) echo /elsewhere ;; esac;'
env_pids_probe "$one_match" /the/env/dir -n; rc=$?
case "$rc" in
  0) ok "env_pids exits 0 with a match that is not the last entry" ;;
  1) bad "env_pids returned non-zero WITH processes to report -- this is the
        live case: reap exits 1 before killing anything and prints nothing" ;;
  3) bad "env_pids reported nothing although one entry matched" ;;
  *) bad "env_pids probe (one match) exited $rc" ;;
esac

# 8. And when the last entry does match -- the accident under which the broken
#    version returned 0. It must still pass, so the fix is not an inversion.
env_pids_probe 'echo "$ENVDIR";' /the/env/dir -n; rc=$?
case "$rc" in
  0) ok "env_pids exits 0 when every entry matches" ;;
  3) bad "env_pids reported nothing although every entry matched" ;;
  *) bad "env_pids probe (all match) exited $rc" ;;
esac

# 9. Every profile the script advertises in its own refusal must be one the
#    parser accepts. Read out of that message rather than restated here.
advertised="$(bash "$TOOL" --profile ..nope.. reap 2>&1 |
              awk -F'have: ' 'NF > 1 { print $2 }' | tr -d ' )' | tr ',' ' ')"
if [ -z "$advertised" ]; then
  bad "could not read the profile list out of the unknown-profile refusal"
else
  n_ok=0
  for prof in $advertised; do
    if bash "$TOOL" --profile "$prof" ..nope.. 2>&1 | grep -q "unknown profile"; then
      bad "the script advertises profile '$prof' and its own parser rejects it"
    else
      n_ok=$((n_ok + 1))
    fi
  done
  [ "$n_ok" -eq 0 ] || ok "all $n_ok advertised profile name(s) accepted by the parser"
fi

# 10. ALL_PROFILES and the profile block are the same set.
#
#    The refusal's `have:` list is now BUILT from $ALL_PROFILES, so comparing
#    those two would be a test that cannot fail. The direction that can go wrong
#    is the other one: a name advertised with no case arm behind it, or a case
#    arm nobody advertises. Both are read out of the file rather than restated.
eval "$(grep -m1 '^ALL_PROFILES=' "$TOOL")"
sorted_words() { local w; for w in $1; do echo "$w"; done | sort | tr -d ' '; }
arms="$(awk '
  /^case .*PROFILE.* in/          { inb = 1; next }
  inb && /^esac$/                 { inb = 0 }
  inb && /^  [A-Za-z0-9._-]+[)]$/ { p = $1; sub(/[)]$/, "", p); print p }
' "$TOOL")"
if [ -z "$arms" ]; then
  bad "could not read a single profile arm out of the case block"
elif [ "$(sorted_words "$ALL_PROFILES")" = "$(sorted_words "$arms")" ]; then
  ok "ALL_PROFILES and the profile block name the same set"
else
  bad "ALL_PROFILES='$ALL_PROFILES' but the case block has '$(echo $arms)'"
fi

# 11. The round trip the bug broke: every ENVDIR the profile block can select
#     maps back, through profile_of_envdir, to the profile that selected it --
#     and to a name the parser accepts. The old `${dir##*qemu-env-}` fails this
#     for unit-2018 and passes for v2.1.2, which is why one profile worked.
eval "$(sed -n '/^profile_of_envdir()/,/^}/p' "$TOOL")"
pairs="$(awk '
  /^case .*PROFILE.* in/            { inb = 1; next }
  inb && /^esac$/                   { inb = 0 }
  inb && /^  [A-Za-z0-9._-]+[)]$/   { p = $1; sub(/[)]$/, "", p); next }
  inb && /^    ENVDIR=/ && p != ""  {
      d = $0; sub(/^ *ENVDIR="/, "", d); sub(/"$/, "", d)
      print p, d; p = "" }
' "$TOOL")"
n_pairs="$(printf '%s' "$pairs" | grep -c . || true)"
if [ "$n_pairs" -eq 0 ]; then
  bad "could not read a single profile -> ENVDIR pair out of the case block"
else
  rt=0
  while read -r prof dir; do
    [ -n "$prof" ] || continue
    got="$(profile_of_envdir "$dir" 2>/dev/null)" || got="<no mapping>"
    if [ "$got" != "$prof" ]; then
      bad "round trip: profile '$prof' uses $dir, which maps back to '$got'"
    elif ! sorted_words "$ALL_PROFILES" | grep -qx "$got"; then
      bad "round trip: '$dir' maps to '$got', which is not in ALL_PROFILES"
    else
      rt=$((rt + 1))
    fi
  done <<EOF_PAIRS
$pairs
EOF_PAIRS
  [ "$rt" -ne "$n_pairs" ] || ok "all $rt ENVDIR(s) map back to the profile that selected them"
fi

# 12. And the shape itself is banned. A refusal may name $PROFILE or a literal;
#     it may not build a profile name out of a path, which is what produced a
#     fix command its own parser rejects.
if grep -n -- '--profile [$]{' "$TOOL" > "$TMP/derived"; then
  bad "a refusal derives its --profile argument from a path expansion:"
  sed 's/^/          /' "$TMP/derived"
else
  ok "no refusal builds a --profile argument out of a directory name"
fi

echo

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
