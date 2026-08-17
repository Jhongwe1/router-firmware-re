#!/usr/bin/env bash
# Build and drive a qemu-user chroot of the build this unit actually runs, with
# this unit's own flash dump standing in for /dev/mtdblock0.
#
# Why this exists
# ---------------
# W01 showed the 2015 MIPS binaries start under qemu-mips-static.  What it could
# not do was serve anything, because libapmib.so reads flash partitions that do
# not exist in a chroot.  W02 took a byte-for-byte copy of this unit's flash, so
# the missing partition is now a file on disk -- and `apmib` reaches it with
# lseek()+read(), not ioctl(), which is the thing that decides whether a plain
# file is good enough.  It is.
#
# The state that is NOT in the flash file
# ---------------------------------------
# `flash`, `boa` and `sysconf` cache the MIB table in a System V shared-memory
# segment.  That segment belongs to the host kernel, it outlives every guest
# process, and restoring /dev/mtdblock0 does not touch it.  A test run after
# another test therefore reads the previous test's values.  This was found the
# hard way: a run that changed one field produced a diff containing a second
# field's bytes.  `reset` removes the segments; every measurement must go
# through it.  See notes/emulation-2018.md.
#
# Nothing here writes to the dump.  The dump is verified against a recorded
# hash and copied; the copy is what the guest sees.

set -euo pipefail

# $HOME is /root under sudo, and this whole tool needs sudo. Resolve the
# invoking user's home instead, or the environment is built somewhere the
# artefacts are not. (Found by the guard suite on its first run, which reported
# three unrelated "failures" that were all this one line.)
_home_of() { getent passwd "$1" 2>/dev/null | cut -d: -f6; }
WORK="${FWRE_WORK:-$(_home_of "${SUDO_USER:-$(id -un)}")/fwre-work}"
ROOTFS="$WORK/extracted/unit-2018/squashfs-root"
ENVDIR="$WORK/qemu-env-2018"
DUMP="$WORK/dumps/flash-n150rt-console-1.bin"
PRISTINE="$ENVDIR/.mtd-pristine.bin"

# The only backup of this unit's H601 block. If this hash does not match, the
# input is not the image every finding in this repository was measured on.
DUMP_SHA256="a800059a9b8c414df026a22b8423a5939d0f9bb793109d0f7ce086f6810f37ea"

# Positive control: values this unit's configuration is known to hold, read in
# W04-2 by a decoder that shares no code with the vendor's binary. If the
# environment is wired up wrongly -- wrong image, empty device file, stale
# shared memory -- these stop matching, and the run stops.
declare -a CONTROL=(
  "TELNET_ENABLED=0"
  "IP_ADDR=10.1.1.1"
  'USER_NAME="admin"'
)

die() { printf '%s: %s\n' "${0##*/}" "$*" >&2; exit 1; }
note() { printf '  %s\n' "$*"; }

need_root() { [ "$(id -u)" -eq 0 ] || die "needs root (chroot); re-run with sudo"; }

verify_dump() {
  [ -f "$DUMP" ] || die "no flash dump at $DUMP"
  local got
  got="$(sha256sum "$DUMP" | cut -d' ' -f1)"
  [ "$got" = "$DUMP_SHA256" ] || die \
    "flash dump hash mismatch
       expected $DUMP_SHA256
       got      $got
     This file is the only copy of this unit's H601 block. Not proceeding."
}

# ---------------------------------------------------------------- build ----
cmd_build() {
  # Input validation first, root second. The other order makes every bad-input
  # case refuse with "needs root", which is a refusal for the wrong reason --
  # and the guard suite counted three of those as three distinct passes until
  # it started asserting on the message instead of the exit status.
  verify_dump
  [ -d "$ROOTFS" ] || die "no rootfs at $ROOTFS (make unpack)"
  command -v qemu-mips-static >/dev/null || die "qemu-mips-static not installed"
  need_root

  rm -rf "$ENVDIR"
  cp -a "$ROOTFS" "$ENVDIR"
  cp "$(command -v qemu-mips-static)" "$ENVDIR/qemu-mips-static"

  # Everything below is the device's own boot doing its own work, copied out of
  # /etc/init.d/rcS and out of /bin/sysconf's string table. Nothing is invented.
  #   rcS:      mount -t ramfs ramfs /var  (here: an ordinary directory)
  local d
  for d in tmp web log run lock system dnrd lib lib/misc samba cwmp_default \
           cwmp_config linuxigd ppp ppp/peers config private tmp/usb net-snmp \
           udhcpc udhcpd myca 1x; do
    mkdir -p "$ENVDIR/var/$d"
  done
  #   rcS:      cp /etc/shadow.sample /var/shadow
  cp "$ENVDIR/etc/shadow.sample" "$ENVDIR/var/shadow" 2>/dev/null || true
  #   sysconf:  cp /etc/passwd.org /var/passwd
  cp "$ENVDIR/etc/passwd.org" "$ENVDIR/var/passwd" 2>/dev/null || true
  #   sysconf:  cp -a /etc/boa/boa.conf.bak /var/boa.conf ; echo "Port 80" >>
  cp -a "$ENVDIR/etc/boa/boa.conf.bak" "$ENVDIR/var/boa.conf"
  echo 'Port 80' >> "$ENVDIR/var/boa.conf"

  # The one substitution that is not the device's own: the flash partition.
  cp "$DUMP" "$PRISTINE"
  cp "$PRISTINE" "$ENVDIR/dev/mtdblock0"
  cp "$PRISTINE" "$ENVDIR/dev/mtd0"

  mknod "$ENVDIR/dev/null"    c 1 3 2>/dev/null || true
  mknod "$ENVDIR/dev/zero"    c 1 5 2>/dev/null || true
  mknod "$ENVDIR/dev/console" c 5 1 2>/dev/null || true
  mknod "$ENVDIR/dev/tty"     c 5 0 2>/dev/null || true
  chmod 666 "$ENVDIR/dev/null" "$ENVDIR/dev/zero" 2>/dev/null || true

  mkdir -p "$ENVDIR/proc"
  mountpoint -q "$ENVDIR/proc" || mount -t proc none "$ENVDIR/proc" || true

  # The document root, populated the way rcS populates it: `flash extr /web`,
  # which reads the w6cg bundle straight out of the device file above.
  chroot "$ENVDIR" ./qemu-mips-static /bin/flash extr /web >/dev/null 2>&1 || true

  echo "built $ENVDIR"
  note "docroot files: $(find "$ENVDIR/var/web" -type f | wc -l)   (expect 143)"
  cmd_check
}

# ---------------------------------------------------------------- reset ----
# Restore BOTH pieces of state. Restoring only the file is the bug this
# subcommand exists to prevent.
cmd_reset() {
  [ -f "$PRISTINE" ] || die "no pristine image; run build first"
  need_root
  cp "$PRISTINE" "$ENVDIR/dev/mtdblock0"
  cp "$PRISTINE" "$ENVDIR/dev/mtd0"
  local id
  for id in $(ipcs -m | awk 'NR>3 && $2 ~ /^[0-9]+$/ {print $2}'); do
    ipcrm -m "$id" 2>/dev/null || true
  done
  for id in $(ipcs -s | awk 'NR>3 && $2 ~ /^[0-9]+$/ {print $2}'); do
    ipcrm -s "$id" 2>/dev/null || true
  done
  rm -f "$ENVDIR/var/web/config.dat"
}

# ---------------------------------------------------------------- check ----
# A control that can fail. Three values this unit is known to hold, read back
# through the vendor's own binary. Wrong image, empty device node or stale
# shared memory each break at least one of them.
cmd_check() {
  need_root
  local rc=0 want got n tmp
  tmp="$(mktemp)"; trap 'rm -f "$tmp"' RETURN

  # Deliberately a file, not `printf ... | grep`. Under `set -o pipefail`,
  # `grep -q` exits the moment it matches, the writer takes SIGPIPE, and the
  # pipeline reports 141 even though the match succeeded -- so a control line
  # in the middle of a 2,317-line stream failed at random while one near the
  # end passed. A control that fails nondeterministically is worse than none.
  chroot "$ENVDIR" ./qemu-mips-static /bin/flash all >"$tmp" 2>/dev/null \
    || die "positive control: /bin/flash all did not run at all"
  [ -s "$tmp" ] || die "positive control: /bin/flash all produced nothing"

  for want in "${CONTROL[@]}"; do
    if grep -qxF "$want" "$tmp"; then
      note "control ok: $want"
    else
      got="$(grep -m1 "^${want%%=*}=" "$tmp" || true)"
      printf '  control FAILED: expected %s, got %s\n' \
        "$want" "${got:-<absent>}" >&2
      rc=1
    fi
  done

  n="$(grep -c '=' "$tmp" || true)"
  note "MIB lines from the vendor binary: $n"
  [ "$n" -gt 2000 ] || { echo "  control FAILED: too few MIB lines ($n)" >&2; rc=1; }
  [ "$rc" -eq 0 ] || die "positive control failed - every result from this environment is suspect"
  echo "positive control passed"
}

# ------------------------------------------------------------------ run ----
cmd_run() { need_root; exec chroot "$ENVDIR" ./qemu-mips-static "$@"; }

# ----------------------------------------------------------------- serve ---
# Stand `boa` up under qemu-user and prove it is answering before saying so.
#
# W05 recorded that this was impossible: "boa cannot serve under qemu-user,
# blocked on an alignment trap the host kernel would fix" (PROGRESS open #16).
# The trap is real and it is an unaligned halfword store, but it is not where
# that sentence puts it. Measured 2026-08-17 with `-strace`:
#
#   open("/dev/mtdblock0") lseek(49152) read(7490)      <- COMPCS
#   open("/web/config.dat", O_RDWR|O_CREAT|O_TRUNC) = 3
#   --- SIGBUS si_addr=0x00492b41 ---                   <- odd address
#
# It dies *generating /web/config.dat at start-up*, not serving. Make that one
# open() fail - config.dat is a directory here, so it returns EISDIR - and boa
# prints `Create config file error!`, carries on, binds, and answers.
#
# The irony is worth keeping: the line that produces this project's best
# evidence chain (an unauthenticated GET of config.dat, CVE-2019-19822) is the
# exact line that makes the emulation route look impossible.
#
# What this costs, stated rather than discovered later: /config.dat cannot be
# fetched from the emulated server, because the file it would serve is the
# directory standing in the way. Links 1 and 2 of the chain stay device-only;
# links 3, 4 and the gate reproduce here.
cmd_serve() {
  need_root
  local port="${1:-8080}" conf="$ENVDIR/var/boa-emu.conf"
  [ -f "$ENVDIR/var/boa.conf" ] || die "no /var/boa.conf in the environment; run build"
  sed "s/^Port .*/Port $port/" "$ENVDIR/var/boa.conf" > "$conf"

  rm -rf "$ENVDIR/var/web/config.dat"
  mkdir -p "$ENVDIR/var/web/config.dat"

  chroot "$ENVDIR" ./qemu-mips-static /bin/boa -f /var/boa-emu.conf \
      >"$ENVDIR/tmp/boa-emu.log" 2>&1 &
  local pid=$!
  local i=0
  while [ "$i" -lt 20 ]; do
    sleep 1; i=$((i + 1))
    curl -sf -m 2 -o /dev/null "http://127.0.0.1:$port/login.htm" && break
  done

  # Two controls, and the second is the one that matters. "It answered" is not
  # "it is this firmware answering the way this firmware answers": an exempt
  # page must come back 200 and a gated one must be redirected, which is the
  # gate model read at instruction level in W04-2 and measured on the device in
  # W05. If only the first held, something else is on the port.
  local ok=0 code
  code="$(curl -s -m 5 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$port/login.htm")"
  if [ "$code" = "200" ]; then note "control ok: login.htm 200 (exempt page served)"; else
    echo "  control FAILED: login.htm returned $code, expected 200" >&2; ok=1; fi
  code="$(curl -s -m 5 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$port/blank.htm")"
  if [ "$code" = "302" ]; then note "control ok: blank.htm 302 (gated page redirected)"; else
    echo "  control FAILED: blank.htm returned $code, expected 302 - the gate is" \
         "not behaving as it does on the device, so nothing measured here transfers" >&2; ok=1; fi

  if [ "$ok" -ne 0 ]; then
    kill "$pid" 2>/dev/null
    die "emulated server did not reproduce the gate; refusing to report it as up"
  fi
  echo "$pid" > "$ENVDIR/tmp/boa-emu.pid"
  echo "boa is serving on 127.0.0.1:$port (pid $pid).  Stop it with:"
  echo "  sudo $0 stop"
}

# `pkill -f 'qemu-mips-static /bin/boa'` is the obvious way to stop it and it is
# a trap: pkill -f matches whole command lines, so a shell invoked as
# `bash -lc '... pkill -f "qemu-mips-static /bin/boa" ...'` has the pattern in
# its own cmdline and kills itself. That happened the first time this
# subcommand was tested, and the exit status was 15 with no other explanation.
# A pidfile costs one line and cannot match the wrong thing.
cmd_stop() {
  need_root
  local pf="$ENVDIR/tmp/boa-emu.pid"
  [ -f "$pf" ] || { echo "no pidfile - nothing recorded as running"; return 0; }
  local pid; pid="$(cat "$pf")"
  if kill "$pid" 2>/dev/null; then echo "stopped pid $pid"; else
    echo "pid $pid was not running"; fi
  rm -f "$pf"
}

# ----------------------------------------------------------------- diff ----
# What did a guest command change in the flash image, and does the H601
# checksum at 0x6493 still balance?
cmd_diff() {
  [ -f "$PRISTINE" ] || die "no pristine image; run build first"
  need_root
  python3 - "$PRISTINE" "$ENVDIR/dev/mtdblock0" <<'PY'
import sys
a = open(sys.argv[1], 'rb').read()
b = open(sys.argv[2], 'rb').read()
d = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
if not d:
    print("no bytes changed")
    raise SystemExit(0)
CK = 0x6493                      # the H601 region's 8-bit checksum (measured)
print(f"{len(d)} bytes changed")
for i in d:
    print(f"  0x{i:06x}  {a[i]:#04x} -> {b[i]:#04x}"
          + ("   <- H601 checksum" if i == CK else ""))
if CK in d:
    tot = sum(b[i] - a[i] for i in d if i != CK)
    got, want = (b[CK] - a[CK]) % 256, (-tot) % 256
    print(f"checksum: delta {got}, expected {want} -> "
          f"{'balances' if got == want else 'DOES NOT BALANCE'}")
    sys.exit(0 if got == want else 1)
PY
}

case "${1:-}" in
  build) shift; cmd_build "$@" ;;
  reset) shift; cmd_reset "$@" ;;
  check) shift; cmd_check "$@" ;;
  diff)  shift; cmd_diff  "$@" ;;
  run)   shift; cmd_run   "$@" ;;
  serve) shift; cmd_serve "$@" ;;
  stop)  shift; cmd_stop  "$@" ;;
  *) cat >&2 <<EOF
usage: sudo $0 {build|reset|check|diff|run|serve|stop ...}

  build   create $ENVDIR from the unit-2018 rootfs + this unit's flash dump
  reset   restore the flash image AND drop the SysV shm/sem the MIB cache uses
  check   positive control: three known values, read back through /bin/flash
  diff    what changed in the flash image, and whether 0x6493 still balances
  run     run a command inside the environment, e.g.
            sudo $0 run /bin/flash get TELNET_ENABLED
            sudo $0 run /bin/sh -c 'flash set HW_WLAN0_WSC_PIN 1;ls -l / > /var/web/x.txt'
  serve   stand boa up on 127.0.0.1 and prove the gate behaves as it does on
          the device before saying it is up, e.g.
            sudo $0 serve 8080
  stop    stop it, by pidfile. Not \`pkill -f\`, which matches the calling
          shell's own command line and kills it

Always: reset before a measurement. Restoring the file alone is not a reset.
EOF
    exit 2 ;;
esac
