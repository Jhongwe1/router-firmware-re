#!/bin/bash
#
# failopen-probe.sh -- what does this unit's boot script do when the settings
# regions are damaged?
#
# The question comes from four lines of /bin/startup.sh, which rcS runs before
# anything else:
#
#     flash test-dsconf         -> non-zero?
#       flash test-csconf       -> also non-zero?
#         flash default-sw
#         ...
#         flash set TELNET_ENABLED 1
#
# Both settings regions invalid means the device boots on factory defaults and
# turns telnet on, and /etc/passwd.org has carried root:123456 and
# onlime_r:12345 (uid 0) unchanged since 2015.  That is register case P8-24.
#
# Why this is a script and not four commands typed at a prompt
# ------------------------------------------------------------
# Three of the failure modes here are silent, and this project has been caught
# by all three before:
#
#   * `startup.sh` ends by running `flash reset1` if test-csconf is STILL
#     failing, which would overwrite the TELNET_ENABLED it just set.  Reading
#     the flag afterwards cannot tell "never enabled" from "enabled and then
#     overwritten" -- so this dumps the two regions either side and reports
#     which one changed, not just the flag.
#   * A corruption that does not actually land looks exactly like a device that
#     tolerates corruption.  Every write is read back before the boot script
#     runs, and the probe refuses if the bytes are not what it wrote.
#   * `flash` answers an unknown subcommand with rc=255 and a usage dump, so a
#     subcommand that does not exist in this build would make every branch look
#     "failed".  The control run establishes that test-dsconf and test-csconf
#     return 0 on a healthy image, which is the only thing that makes a
#     non-zero result mean anything.
#
# It measures four states, and the two middles are what separate the readings:
#
#   healthy          control -- both tests must pass and telnet must stay off
#   ds-only          only the factory-default region damaged
#   cs-only          only the live-configuration region damaged
#   both             the state P8-24 predicts enables telnet
#
# and each damaged state is run twice, once with the region's magic destroyed
# and once with the magic intact and a single payload byte flipped, because
# "what counts as invalid" decides whether an attacker who can write bytes can
# reach this at all.
#
# Nothing here touches hardware.  It runs entirely inside the qemu-user profile
# built by tools/qemu-env.sh, whose /dev/mtdblock0 is a copy of this unit's
# flash dump and is restored from .mtd-pristine.bin between measurements.
#
# Usage:
#   sudo tools/failopen-probe.sh [--profile unit-2018] [-o reports/failopen-unit-2018.json]

set -uo pipefail

PROFILE="unit-2018"
OUT=""
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${FWRE_WORK:=/home/key/fwre-work}"

# The two settings regions, located in W02 and confirmed by fwrecon compcs.
DS_OFF=$((0x008000))     # COMPDS -- factory defaults
CS_OFF=$((0x00C000))     # COMPCS -- live configuration

die() { echo "failopen-probe: $*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    -o|--out)  OUT="$2"; shift 2 ;;
    -h|--help) sed -n '2,50p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

[ "$(id -u)" -eq 0 ] || die "must run as root -- qemu-env.sh chroots"

QENV="$REPO/tools/qemu-env.sh"
[ -x "$QENV" ] || [ -f "$QENV" ] || die "no tools/qemu-env.sh"

case "$PROFILE" in
  unit-2018) ENVDIR="$FWRE_WORK/qemu-env-2018" ;;
  v2.1.2)    ENVDIR="$FWRE_WORK/qemu-env-v2.1.2" ;;
  *) die "unknown profile: $PROFILE" ;;
esac
MTD="$ENVDIR/dev/mtdblock0"
[ -f "$MTD" ] || die "no $MTD; run: sudo tools/qemu-env.sh --profile $PROFILE build"

TRANSCRIPTS="$FWRE_WORK/dumps/failopen-$PROFILE"
mkdir -p "$TRANSCRIPTS" || die "cannot create $TRANSCRIPTS"

q() { FWRE_WORK="$FWRE_WORK" bash "$QENV" --profile "$PROFILE" "$@"; }

# ---------------------------------------------------------------- byte surgery
# Two kinds of damage, because they answer different questions.
#   magic  -- the first 8 bytes of the region, which carry the COMPDS/COMPCS
#             signature.  The crudest possible damage.
#   csum   -- one byte deep inside the payload, magic left intact.  This is what
#             an attacker who can write a few bytes actually produces, and if
#             only `magic` counts as invalid then this path is much narrower
#             than it looks.
damage() {  # damage <offset> <magic|csum>
  python3 - "$MTD" "$1" "$2" <<'PY'
import sys
path, off, kind = sys.argv[1], int(sys.argv[2]), sys.argv[3]
with open(path, 'r+b') as f:
    if kind == 'magic':
        at, new = off, b'\x00' * 8
    elif kind == 'csum':
        at, new = off + 0x40, None
    else:
        sys.exit("bad damage kind")
    f.seek(at)
    old = f.read(8 if new else 1)
    if new is None:
        new = bytes([old[0] ^ 0xFF])
    f.seek(at)
    f.write(new)
    f.flush()
    # read back: a write that did not land looks exactly like a device that
    # tolerates the damage
    f.seek(at)
    got = f.read(len(new))
if got != new:
    sys.exit(f"write did not land at 0x{at:x}: wrote {new.hex()} read {got.hex()}")
print(f"0x{at:08x} {old.hex()} -> {new.hex()}")
PY
}

region_digest() {  # region_digest <offset> <len>
  python3 - "$MTD" "$1" "$2" <<'PY'
import sys, hashlib
path, off, ln = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
with open(path, 'rb') as f:
    f.seek(off)
    print(hashlib.sha256(f.read(ln)).hexdigest()[:16])
PY
}

rc_of() {  # rc_of <flash subcommand words...>
  local out
  out=$(q run /bin/flash "$@" 2>&1)
  local rc=$?
  # An unknown subcommand is rc=255 plus a usage dump.  Distinguish it, because
  # "this build has no such subcommand" and "this build says invalid" are
  # different facts and both are non-zero.
  if printf '%s' "$out" | head -1 | grep -q '^Usage: flash cmd'; then
    echo "255-usage"
  else
    echo "$rc"
  fi
}

telnet_flag() {
  local v
  v=$(q run /bin/flash get TELNET_ENABLED 2>&1 | tr -d '\r\0' | sed -n 's/^TELNET_ENABLED=//p' | head -1)
  # With a damaged region `flash get` cannot answer at all, and that is a
  # distinct state from "the flag is 0". Never collapse them.
  echo "${v:-unreadable}"
}

# The control that would have caught the first run of this probe. `run` executes
# its argument under qemu-mips-static, which wants an ELF; a #!/bin/sh script
# handed to it produces no output and no effect, which is indistinguishable from
# a boot script that decided to do nothing. Prove the shell runs before
# believing anything the boot script did or did not say.
# Every damaged state below ends with `flash default-sw` or `flash reset1` dying
# on SIGBUS, and there are two readings of that: "this environment cannot write
# flash at all" and "the RECOVERY write specifically dies". They lead to
# opposite conclusions about the device, so separate them here, on a healthy
# image, where a plain `flash set` must succeed and be readable back.
write_control() {
  local before after
  before=$(q run /bin/flash get WAN_DHCP 2>&1 | tr -d '\r\0' | sed -n 's/^WAN_DHCP=//p' | head -1)
  q run /bin/flash set WAN_DHCP 7 >/dev/null 2>&1
  after=$(q run /bin/flash get WAN_DHCP 2>&1 | tr -d '\r\0' | sed -n 's/^WAN_DHCP=//p' | head -1)
  [ "$after" = "7" ] || die "CONTROL FAILED: a plain 'flash set' does not take in this environment (WAN_DHCP $before -> ${after:-?}), so a SIGBUS on the recovery path would say nothing about the recovery path"
  echo "  control ok: a plain 'flash set' writes and reads back here (WAN_DHCP $before -> $after), so writes are not broken in general"
  q reset >/dev/null 2>&1 || die "reset after write control failed"
}

shell_control() {
  local got
  got=$(q run /bin/sh -c 'echo SHELL_RUNS' 2>&1 | tr -d '\r\0' | grep -c SHELL_RUNS)
  [ "$got" -ge 1 ] || die "CONTROL FAILED: /bin/sh does not execute in this environment, so \"startup.sh said nothing\" would mean nothing"
}

RESULTS=()
record() { RESULTS+=("$1"); }

measure() {  # measure <label> <ds-damage|-> <cs-damage|->
  local label="$1" dsk="$2" csk="$3"
  echo
  echo "=== $label ==="
  q reap  >/dev/null 2>&1
  q reset >/dev/null 2>&1 || die "reset failed for $label"

  local dsnote="-" csnote="-"
  if [ "$dsk" != "-" ]; then dsnote=$(damage "$DS_OFF" "$dsk") || die "damage ds failed"; echo "  damaged COMPDS ($dsk): $dsnote"; fi
  if [ "$csk" != "-" ]; then csnote=$(damage "$CS_OFF" "$csk") || die "damage cs failed"; echo "  damaged COMPCS ($csk): $csnote"; fi

  local ds_before cs_before
  ds_before=$(region_digest "$DS_OFF" 7481)
  cs_before=$(region_digest "$CS_OFF" 7478)

  local rc_ds rc_cs tel_before
  rc_ds=$(rc_of test-dsconf)
  rc_cs=$(rc_of test-csconf)
  tel_before=$(telnet_flag)
  echo "  before: test-dsconf=$rc_ds test-csconf=$rc_cs TELNET_ENABLED=${tel_before:-<unreadable>}"

  # Run the vendor's own boot script, not a reimplementation of it.
  #
  # Through /bin/sh, not directly. `qemu-env.sh run` executes its argument under
  # qemu-mips-static, which needs an ELF -- handed a `#!/bin/sh` script it fails
  # and prints nothing useful. The first run of this probe did exactly that and
  # produced a clean, complete-looking table in which startup.sh "said nothing"
  # and changed nothing in all seven states, including the one it was written to
  # detect. The numbers were plausible; the script had never executed.
  #
  # The full transcript goes to a file and only a summary to the screen. The
  # first working run of this probe put 240 characters on screen and every one
  # of them was `flash`'s own stderr complaining about the signature -- the line
  # that decides the whole question, startup.sh's own `echo`, was past the cut.
  local sout tpath
  tpath="$TRANSCRIPTS/$(printf '%s' "$label" | tr -c 'a-zA-Z0-9' '-').log"
  q run /bin/sh /bin/startup.sh > "$tpath" 2>&1
  sout=$(tr -d '\r\0' < "$tpath" | grep -E 'configuration invalid|reset default' | tr '\n' ';')
  local nsig nbus
  # `grep -c` prints 0 AND exits 1 when there is no match, so the obvious
  # `|| echo 0` appends a second zero and the field becomes "0\n0".
  nsig=$(grep -c 'Invalid default setting signature' "$tpath" 2>/dev/null); nsig=${nsig:-0}
  nbus=$(grep -c 'Bus error' "$tpath" 2>/dev/null); nbus=${nbus:-0}
  echo "  startup.sh branch: ${sout:-<no branch message - suspect>}"
  echo "  transcript: $(wc -l < "$tpath") lines, $nsig signature complaints, $nbus SIGBUS  -> $tpath"

  local rc_ds2 rc_cs2 tel_after ds_after cs_after
  rc_ds2=$(rc_of test-dsconf)
  rc_cs2=$(rc_of test-csconf)
  tel_after=$(telnet_flag)
  ds_after=$(region_digest "$DS_OFF" 7481)
  cs_after=$(region_digest "$CS_OFF" 7478)
  echo "  after : test-dsconf=$rc_ds2 test-csconf=$rc_cs2 TELNET_ENABLED=${tel_after:-<unreadable>}"
  echo "  COMPDS $ds_before -> $ds_after $([ "$ds_before" = "$ds_after" ] && echo '(unchanged)' || echo '(REWRITTEN)')"
  echo "  COMPCS $cs_before -> $cs_after $([ "$cs_before" = "$cs_after" ] && echo '(unchanged)' || echo '(REWRITTEN)')"

  record "$(printf '{"label":"%s","ds_damage":"%s","cs_damage":"%s","rc_ds_before":"%s","rc_cs_before":"%s","telnet_before":"%s","rc_ds_after":"%s","rc_cs_after":"%s","telnet_after":"%s","compds":"%s->%s","compcs":"%s->%s","branch_message":"%s","sigbus_lines":%s,"transcript":"%s"}' \
    "$label" "$dsk" "$csk" "$rc_ds" "$rc_cs" "${tel_before:-?}" "$rc_ds2" "$rc_cs2" "${tel_after:-?}" \
    "$ds_before" "$ds_after" "$cs_before" "$cs_after" \
    "$(printf '%s' "$sout" | sed 's/"/\\"/g')" "${nbus:-0}" "$tpath")"
}

echo "failopen-probe: profile=$PROFILE env=$ENVDIR"
echo "measuring what /bin/startup.sh does to TELNET_ENABLED under four damage states"

# The control has to come first and it has to be able to fail: if telnet is
# already 1 on a healthy image, nothing below means anything.
measure "healthy (control)"       -     -
shell_control
echo "  control ok: /bin/sh executes in this environment"
CTRL_SHELL="pass"
write_control
CTRL_WRITE="pass"
CTRL="${RESULTS[0]}"
case "$CTRL" in
  *'"rc_ds_before":"0"'*'"rc_cs_before":"0"'*'"telnet_before":"0"'*) : ;;
  *) die "CONTROL FAILED: on a healthy image test-dsconf/test-csconf must both return 0 and TELNET_ENABLED must be 0. Got: $CTRL" ;;
esac
CTRL_HEALTHY="pass"
echo "  control ok: healthy image passes both tests and telnet is off"

measure "ds-only  magic"          magic -
measure "cs-only  magic"          -     magic
measure "both     magic"          magic magic
measure "both     csum-only"      csum  csum
measure "ds-only  csum-only"      csum  -
measure "cs-only  csum-only"      -     csum

echo
echo "=== restoring the environment ==="
q reap  >/dev/null 2>&1
q reset >/dev/null 2>&1 || die "final reset failed -- the environment is left damaged"
FINAL=$(telnet_flag)
[ "$FINAL" = "0" ] || die "environment not clean after restore: TELNET_ENABLED=$FINAL"
echo "  restored, TELNET_ENABLED=0"

if [ -n "$OUT" ]; then
  {
    printf '{\n  "producer": "failopen-probe",\n  "profile": "%s",\n' "$PROFILE"
    printf '  "flash_image": "%s",\n' "$MTD"
    printf '  "source_sha256": "%s",\n' "$(sha256sum "$MTD" | cut -d' ' -f1)"
    printf '  "question": "which damage states make /bin/startup.sh set TELNET_ENABLED=1",\n'
    printf '  "case": "P8-24",\n'
    printf '  "controls": {"shell_runs": "%s", "plain_write_takes": "%s", "healthy_image_passes_both_tests_and_telnet_off": "%s"},\n' \
      "${CTRL_SHELL:-NOT RUN}" "${CTRL_WRITE:-NOT RUN}" "${CTRL_HEALTHY:-NOT RUN}"
    printf '  "caveat": "qemu-user raises SIGBUS on the unaligned access flash default-sw and flash reset1 take, so no damaged state observed a completed recovery write. The branch being ENTERED is measured; what it writes is not. The plain_write_takes control is what makes that a statement about the recovery path rather than about this environment.",\n'
    printf '  "measurements": [\n'
    local_first=1
    for r in "${RESULTS[@]}"; do
      [ $local_first -eq 1 ] && local_first=0 || printf ',\n'
      printf '    %s' "$r"
    done
    printf '\n  ]\n}\n'
  } > "$OUT"
  echo "wrote $OUT"
fi
