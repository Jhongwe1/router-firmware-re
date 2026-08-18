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
REPO="$(cd "$(dirname "$0")/.." && pwd)"

# This unit's own dump. Used ONLY as a second source for layout checks, never as
# an input to a built image -- see cmd_mkflash. Absent on anybody else's desk,
# and everything that touches it has to cope with that.
DUMPREF="$WORK/dumps/flash-n150rt-console-1.bin"

# ------------------------------------------------------------- profiles ----
# Two environments, and the difference between them is the whole of G4's third
# clause.
#
#   unit-2018   the build this unit actually runs, standing on this unit's own
#               flash dump. Everything W05 and W06 measured under emulation was
#               measured here. A stranger cannot reproduce it: neither the
#               rootfs nor the flash is downloadable.
#
#   v2.1.2      a published image, and nothing else. The rootfs comes out of
#               the .web container; the flash is rebuilt from the same container
#               by tools/mkflash.py, which places each section at the burnAddr
#               the container declares and leaves everything else 0xFF. That
#               "everything else" is the first 64 KiB -- boot loader, H601,
#               COMPDS, COMPCS -- and it is in no image anybody can download.
#
# Adding a profile means declaring FLASH_ORIGIN and a CONTROL set that can fail.
# A profile whose control cannot fail is not a second environment, it is a
# second way to believe the first one.
PROFILE="${QEMU_PROFILE:-unit-2018}"
if [ "${1:-}" = "--profile" ]; then
  [ -n "${2:-}" ] || { echo "${0##*/}: --profile needs a name" >&2; exit 2; }
  PROFILE="$2"; shift 2
fi

# The names this script accepts, in one place. The `have:` list in the refusal
# below is built from it, so the advertised set and the checked set cannot
# drift apart; that the case arms below match it is what test-qemu-env.sh
# checks, and that is the direction that can actually go wrong.
ALL_PROFILES="unit-2018 v2.1.2"

case "$PROFILE" in
  unit-2018)
    ROOTFS="$WORK/extracted/unit-2018/squashfs-root"
    ENVDIR="$WORK/qemu-env-2018"
    DUMP="$WORK/dumps/flash-n150rt-console-1.bin"
    # The only backup of this unit's H601 block. If this hash does not match,
    # the input is not the image every finding in this repository was measured
    # on.
    DUMP_SHA256="a800059a9b8c414df026a22b8423a5939d0f9bb793109d0f7ce086f6810f37ea"
    DUMP_ORIGIN="this unit's own flash, read out through the boot loader on 2026-08-16"
    # Positive control: values this unit's configuration is known to hold, read
    # in W04-2 by a decoder that shares no code with the vendor's binary. If the
    # environment is wired up wrongly -- wrong image, empty device file, stale
    # shared memory -- these stop matching, and the run stops.
    declare -a CONTROL=(
      "TELNET_ENABLED=0"
      "IP_ADDR=10.1.1.1"
      'USER_NAME="admin"'
    )
    MIB_MIN=2000
    DOCROOT_EXPECT=143
    ;;
  v2.1.2)
    ROOTFS="$WORK/extracted/v2.1.2/squashfs-root"
    ENVDIR="$WORK/qemu-env-v2.1.2"
    DUMP="$WORK/qemu-env-v2.1.2-flash.bin"
    DUMP_SHA256="0d10c63fb86082a0cbf552f305d1134491513b001b49a026dbdce435f5578af5"
    DUMP_ORIGIN="rebuilt by \`$0 --profile v2.1.2 mkflash\` from the published V2.1.2-B20150825 container, plus three synthesised regions -- H601 at 0x6000 and COMPDS/COMPCS at 0x8000/0xC000, all with zeroed payloads. reports/mkflash-2.1.2.json names every byte range and where it came from"
    # Left empty on purpose until measured. The values this environment holds
    # are whatever the *published* image defaults to, and this project has never
    # read them; borrowing unit-2018's would be asserting that a build we have
    # not started agrees with one we have. `check` refuses an empty CONTROL
    # rather than passing over it, which is instrument bug 12's shape and the
    # reason that refusal is written down.
    declare -a CONTROL=()
    MIB_MIN=0
    DOCROOT_EXPECT=144
    ;;
  *)
    echo "${0##*/}: unknown profile '$PROFILE' (have: ${ALL_PROFILES// /, })" >&2
    exit 2 ;;
esac

# The reverse of the block above: environment directory -> profile name.
#
# These are NOT the same string -- profile `unit-2018` lives in `qemu-env-2018`
# -- and that is the whole of the bug. cmd_reset derived the name it printed
# with `${dir##*qemu-env-}`, which yields `2018`, and the parser above rejects
# `--profile 2018` with exit 2. So the refusal that blocks a reset printed a fix
# that is itself refused, for exactly one of the two profiles: the default one,
# which is the one an orphan is always in. A reset blocked this way stayed
# blocked, and that is what stopped the V2.1.2 measurement on 2026-08-18.
#
# Two hand-kept lists are acceptable only with something proving they agree:
# test-qemu-env.sh walks $ALL_PROFILES through the parser and back through this
# function, both directions, and needs neither root nor the flash dump.
profile_of_envdir() {
  case "${1##*/}" in
    qemu-env-2018)   printf '%s' 'unit-2018' ;;
    qemu-env-v2.1.2) printf '%s' 'v2.1.2' ;;
    *) return 1 ;;
  esac
}


PRISTINE="$ENVDIR/.mtd-pristine.bin"

die() { printf '%s: %s\n' "${0##*/}" "$*" >&2; exit 1; }
note() { printf '  %s\n' "$*"; }

need_root() { [ "$(id -u)" -eq 0 ] || die "needs root (chroot); re-run with sudo"; }

# ---------------------------------------------------------------- guest ----
# Every guest starts through this, and the reason is one measurement.
#
# `chroot` is not isolation. On 2026-08-18 a single POST to /boafrm/formWsc on
# the v2.1.2 profile reached, in the guest's own syscall trace,
#
#     execve("/bin/sh", {"sh", "-c", "reboot -f"})
#
# and busybox's `reboot -f` is a bare reboot(2). qemu-user hands it to the host
# kernel, this whole tool runs as root, and there was no namespace between the
# two -- so the HOST powered off. It did that three times before the cause was
# named, and each time it looked like the harness hanging: partial output, a
# report never written, /tmp empty afterwards. Nothing in the environment said
# what had happened, because the thing that would have said it had just been
# shut down.
#
# A PID namespace makes reboot(2) mean what it means on the device: the init of
# that namespace is signalled and the namespace ends. The unit-2018 build takes
# a different path for the same request -- `flash write-current` and `sysconf
# wlaninit wlaninterface` -- so this cost nothing for four weeks, and would have
# cost the next session too.
#
# --mount-proc is deliberately NOT passed: $ENVDIR/proc is already mounted from
# the host mount namespace, and a fresh mount namespace would hide it from the
# guest. That is a behaviour change, not a containment.
#
# It is also the orphan fix: killing the namespace's init takes its children
# with it, and children exec'd through binfmt are exactly what `reap` exists for.
guest() { unshare --pid --fork chroot "$ENVDIR" ./qemu-mips-static "$@"; }

verify_dump() {
  [ -f "$DUMP" ] || die "no flash dump at $DUMP"
  local got
  got="$(sha256sum "$DUMP" | cut -d' ' -f1)"
  [ "$got" = "$DUMP_SHA256" ] || die \
    "flash image hash mismatch for profile '$PROFILE'
       expected $DUMP_SHA256
       got      $got
     This image is: $DUMP_ORIGIN
     Not proceeding."
}

# -------------------------------------------------------------- mkflash ----
# Construct the profile's flash image from artefacts a stranger can obtain.
#
# This exists as a subcommand rather than as a paragraph in the runsheet because
# G4 clause 3a's entire claim is "anyone can do this". A claim like that is
# worth what its command line is worth: the steps are deterministic, so the
# image has a fixed sha256, and the profile above pins it. If someone runs this
# and gets a different hash, one of the two of us has a different container.
cmd_mkflash() {
  [ "$PROFILE" = "v2.1.2" ] || die \
    "profile '$PROFILE' does not build its flash -- it stands on a real dump
     read off the hardware ($DUMP). There is nothing here to construct."

  local img="$WORK/firmware/TOTOLINK-N150RT-V2.1.2-B20150825.1601.web"
  local parts="$WORK/l2-parts"
  [ -f "$img" ] || die "no published container at $img (make fetch)"
  mkdir -p "$parts"

  # The structure checks read this unit's dump, and requiring one would defeat
  # the point of the profile: a stranger has no dump, so a build that insists on
  # one is not the reproduction path clause 3a asks for. They are therefore
  # optional -- and their absence is *said*, because a check that quietly does
  # not run is indistinguishable from a check that passed.
  local -a vstruct=() vfmt=()
  if [ -f "$DUMPREF" ]; then
    vstruct=(--verify-structure-against "$DUMPREF")
    vfmt=(--verify-format-against "$DUMPREF")
    note "cross-checking layout against $DUMPREF"
  else
    note "no reference dump at $DUMPREF -- building WITHOUT the structure checks."
    note "That is the normal case for anyone who does not own one of these units."
  fi

  # 1. The hardware setting. Bootstrap only: structurally valid, semantically
  #    empty, and enough for apmib_init() to get past its first check.
  python3 "$REPO/tools/mkhwsetting.py" --out "$parts/h601.bin" \
    "${vfmt[@]}" || die "mkhwsetting failed"

  # 2 and 3. The two settings blocks. The length is not a guess: libapmib prints
  #    `Expect [sig=6G, ver=3, len=32858]!` when it rejects a bad one, so the
  #    number below is the library's own statement of what it wants.
  python3 "$REPO/tools/mkcompds.py" --out "$parts/compds.bin" --kind compds --length 32858 \
    || die "mkcompds (COMPDS) failed"
  python3 "$REPO/tools/mkcompds.py" --out "$parts/compcs.bin" --kind compcs --length 32858 \
    || die "mkcompds (COMPCS) failed"

  python3 "$REPO/tools/mkflash.py" \
    --image "$img" --out "$DUMP" --json "$REPO/reports/mkflash-2.1.2.json" \
    "${vstruct[@]}" \
    --overlay "$parts/h601.bin@0x6000" \
    --overlay "$parts/compds.bin@0x8000" \
    --overlay "$parts/compcs.bin@0xC000" \
    --overlay-origin "synthesised from public artefacts by tools/mkhwsetting.py (H601) and tools/mkcompds.py (COMPDS/COMPCS); all-zero payloads, no data from any physical unit" \
    || die "mkflash failed"

  local got; got="$(sha256sum "$DUMP" | cut -d' ' -f1)"
  if [ "$got" = "$DUMP_SHA256" ]; then
    note "sha256 matches the pinned value -- this build is bit-reproducible"
  else
    echo "  NOTE: sha256 is $got, the profile pins $DUMP_SHA256." >&2
    echo "        If a generator changed on purpose, update DUMP_SHA256 in the" >&2
    echo "        same commit so the change appears in the diff." >&2
  fi
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

  # A previous build leaves /proc mounted inside the environment, and `rm -rf`
  # then walks into a live procfs: it fails on every entry it cannot remove,
  # returns non-zero, and leaves a half-deleted tree. The copy that follows then
  # merges into the wreckage and the *next* command reports
  # `./qemu-mips-static: No such file or directory` -- a message that points
  # nowhere near the cause. Found on the first v2.1.2 rebuild, 2026-08-18.
  #
  # Unmount first, and refuse to delete if the unmount did not take. `rm -rf`
  # through a live mountpoint is the mechanism by which a tool deletes things
  # outside the directory it was aimed at, so this is a refusal and not a retry.
  if [ -d "$ENVDIR" ]; then
    if mountpoint -q "$ENVDIR/proc"; then
      umount "$ENVDIR/proc" 2>/dev/null || true
    fi
    if mountpoint -q "$ENVDIR/proc"; then
      die "$ENVDIR/proc is still a mountpoint after umount.
     Not running rm -rf through it. Unmount it by hand and re-run:
       sudo umount $ENVDIR/proc"
    fi
    rm -rf "$ENVDIR"
  fi
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
  guest /bin/flash extr /web >/dev/null 2>&1 || true

  echo "built $ENVDIR  (profile $PROFILE)"
  # The count comes from the web bundle report for this build, not from a
  # constant: 143 for unit-2018 and 144 for V2.1.2, and hard-coding either one
  # makes the other look broken.
  note "docroot files: $(find "$ENVDIR/var/web" -type f | wc -l)   (bundle declares $DOCROOT_EXPECT)"
  cmd_check
}

# ---------------------------------------------------------------- reset ----
# Restore BOTH pieces of state. Restoring only the file is the bug this
# subcommand exists to prevent.
cmd_reset() {
  [ -f "$PRISTINE" ] || die "no pristine image; run build first"
  need_root

  # The IPC removal below is HOST-GLOBAL: SysV segments have no namespace here,
  # so `reset` on one profile destroys the segments the other profile's running
  # boa is holding. That process then spins on
  #   APMIB Semaphore Lock semop() failed !! [Invalid argument]
  # forever, never binds, and the next `serve` times out with no output -- which
  # is what happened on 2026-08-18 once a second profile existed, and it looked
  # like a broken restart rather than a broken reset.
  #
  # So: stop everything in THIS environment first, and refuse if another
  # profile's environment still has processes, rather than pulling the floor out
  # from under it.
  local other n hint
  # `|| true` because reap having nothing to do is not an error. It is NOT here
  # to swallow a broken reap -- which is exactly what it used to do, see
  # env_pids above.
  cmd_reap >/dev/null 2>&1 || true
  for other in "$WORK"/qemu-env-*; do
    [ -d "$other" ] || continue
    [ "$other" = "$ENVDIR" ] && continue
    n=0
    for p in /proc/[0-9]*; do
      [ "$(readlink "$p/root" 2>/dev/null)" = "$other" ] && n=$((n + 1))
    done
    if hint="$(profile_of_envdir "$other")"; then
      hint="sudo $0 --profile $hint reap"
    else
      hint="no profile in this script owns $other -- kill them by hand"
    fi
    [ "$n" -eq 0 ] || die \
      "$n process(es) are still running in $other, and this reset would delete
     the SysV segments they are using -- they have no namespace on this host.
     Stop them first:
       $hint"
  done

  cp "$PRISTINE" "$ENVDIR/dev/mtdblock0"
  cp "$PRISTINE" "$ENVDIR/dev/mtd0"
  local id
  for id in $(ipcs -m | awk 'NR>3 && $2 ~ /^[0-9]+$/ {print $2}'); do
    ipcrm -m "$id" 2>/dev/null || true
  done
  for id in $(ipcs -s | awk 'NR>3 && $2 ~ /^[0-9]+$/ {print $2}'); do
    ipcrm -s "$id" 2>/dev/null || true
  done
  # -rf, not -f. `serve` deliberately makes this path a DIRECTORY so that boa's
  # start-up open(O_RDWR|O_CREAT|O_TRUNC) returns EISDIR instead of taking the
  # unaligned path that kills it under qemu-user -- see the comment above
  # cmd_serve. `rm -f` cannot remove a directory, so after any `serve` this line
  # failed, and because it is the last command in the function it made `reset`
  # return non-zero while every restore above it had in fact succeeded. A caller
  # that trusted the exit status saw "reset failed" and stopped; a caller that
  # did not would have carried the previous run's docroot into the next
  # measurement. Found 2026-08-18 by failopen-probe.sh, which is the first
  # caller to check reset's exit status at all.
  rm -rf "$ENVDIR/var/web/config.dat"
  [ -e "$ENVDIR/var/web/config.dat" ] && die "could not clear $ENVDIR/var/web/config.dat"

  # And restore the web server's own runtime config, which `build` composes the
  # way `sysconf` does on the device: the template plus an appended Port line.
  #
  # This line exists because of what --alignfix made possible. Once handlers
  # stopped dying inside libapmib they began running their side effects, and one
  # of them re-ran the `cp -a /etc/boa/boa.conf.bak /var/boa.conf` half of
  # sysconf's job without the append. The file went back to the upstream sample,
  # in which `Port` is commented out -- so `serve`'s `sed s/^Port .*/` matched
  # nothing, boa bound port 0, and every probe afterwards timed out with the
  # environment otherwise healthy: `check` passed all three controls, because the
  # flash was fine. It was not the flash.
  #
  # Same shape as instrument bugs 37 and 41: a restore trusted to restore
  # everything, restoring less than everything. `reset` had always covered the
  # flash and the SysV segments and never /var, and until handlers could write
  # nothing in /var ever changed.
  cp -a "$ENVDIR/etc/boa/boa.conf.bak" "$ENVDIR/var/boa.conf"
  echo 'Port 80' >> "$ENVDIR/var/boa.conf"
  grep -q '^Port ' "$ENVDIR/var/boa.conf" || die \
    "restored $ENVDIR/var/boa.conf has no uncommented Port line, so serve's
     rewrite would match nothing and boa would bind an arbitrary port"
  return 0
}

# ---------------------------------------------------------------- check ----
# A control that can fail. Three values this unit is known to hold, read back
# through the vendor's own binary. Wrong image, empty device node or stale
# shared memory each break at least one of them.
cmd_check() {
  need_root
  local rc=0 want got n tmp
  # An empty control set would let every loop below iterate zero times and the
  # function return success -- instrument bug 12 exactly, a check that reports
  # a pass when it has nothing to check. A profile with no controls is an
  # uncalibrated profile and it says so.
  if [ "${#CONTROL[@]}" -eq 0 ]; then
    die "profile '$PROFILE' declares no positive control, so this check would
     pass over an empty set and prove nothing. Measure the values this image
     actually holds -- \`$0 --profile $PROFILE run /bin/flash all\` -- confirm
     them against a second source, then pin them in CONTROL."
  fi
  tmp="$(mktemp)"; trap 'rm -f "$tmp"' RETURN

  # Deliberately a file, not `printf ... | grep`. Under `set -o pipefail`,
  # `grep -q` exits the moment it matches, the writer takes SIGPIPE, and the
  # pipeline reports 141 even though the match succeeded -- so a control line
  # in the middle of a 2,317-line stream failed at random while one near the
  # end passed. A control that fails nondeterministically is worse than none.
  guest /bin/flash all >"$tmp" 2>/dev/null \
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
  [ "$n" -gt "$MIB_MIN" ] || { echo "  control FAILED: too few MIB lines ($n, want > $MIB_MIN)" >&2; rc=1; }
  [ "$rc" -eq 0 ] || die "positive control failed - every result from this environment is suspect"
  echo "positive control passed"
}

# ------------------------------------------------------------------ run ----

cmd_run() { need_root; guest "$@"; }

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
# Who is listening on a TCP port, as a pid, or empty.
#
# The trailing `|| true` is load-bearing. `grep` exits 1 when the port is FREE,
# which is the ordinary case, and under `set -euo pipefail` that made the whole
# pipeline fail, which made the assignment fail, which made `serve` exit 1 --
# printing nothing at all. A guard written to stop a stale server silently
# stopped the server it was guarding, and the symptom was an empty line.
port_holder() {
  ss -ltnp 2>/dev/null | awk -v p=":$1\$" '$4 ~ p {print $0}' \
    | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2 || true
}

# Every guest process still running inside THIS environment, found by the one
# thing that cannot match the wrong process: /proc/<pid>/root resolves to the
# chroot it is in. `pkill -f` was rejected once already for matching the calling
# shell's own command line (see cmd_stop); matching on a command-line pattern
# would also match the *other* profile's boa, which is a different environment
# with a different flash and would be silently killed by a tool aimed here.
env_pids() {
  local p target
  for p in /proc/[0-9]*; do
    target="$(readlink "$p/root" 2>/dev/null)" || continue
    if [ "$target" = "$ENVDIR" ]; then printf '%s\n' "${p#/proc/}"; fi
  done
  # `return 0`, and it is load-bearing under `set -euo pipefail`.
  #
  # The last statement used to be `[ ... ] && printf`. On the FINAL /proc entry
  # -- which is essentially never a guest -- the test is false, so the && list
  # returns 1, so the *function* returns 1, so `pids="$(env_pids)"` in cmd_reap
  # returns 1, and `set -e` ended the script right there: exit 1, nothing
  # killed, and not one byte on stdout or stderr.
  #
  # It looked like it worked because cmd_reset calls it as `cmd_reap ... ||
  # true`, and a `||` list disables `set -e` for the whole dynamic extent of the
  # call. So reap worked in the one place its result was thrown away, and failed
  # every time it was asked for by name -- and whether it failed at all depended
  # on which /proc entry the glob happened to sort last.
  return 0
}

# ------------------------------------------------------------------ reap ----
# Kill every guest process belonging to this environment.
#
# `boa` under qemu-user does not survive several of its own handlers, and a
# crashed process leaves the pidfile pointing at a corpse -- so `stop` reports
# success and the process that was actually listening is still there. Over a
# 58-handler sweep on 2026-08-18 that produced **32 orphans**, and the port was
# held by an arbitrary old one. Every probe after the first crash was answered
# by a server carrying state from an earlier point in the run, and the results
# were nonsense in a way that looked like data.
cmd_reap() {
  need_root
  local pids n
  pids="$(env_pids)"
  n="$(printf '%s' "$pids" | grep -c . || true)"
  if [ "$n" -eq 0 ]; then echo "no processes running in $ENVDIR"; return 0; fi
  echo "$pids" | xargs -r kill  2>/dev/null || true
  sleep 1
  echo "$pids" | xargs -r kill -9 2>/dev/null || true
  rm -f "$ENVDIR/tmp/boa-emu.pid"
  echo "reaped $n process(es) in $ENVDIR"
}

cmd_serve() {
  need_root
  local port="8080" alignfix=0 preload=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --alignfix) alignfix=1; shift ;;
      -*) die "serve: unknown option '$1' (have: --alignfix)" ;;
      *) port="$1"; shift ;;
    esac
  done
  local conf="$ENVDIR/var/boa-emu.conf"

  # Does this environment exist at all?  FIRST, and that ordering is the fix
  # for instrument bug 44.
  #
  # This check used to sit below the alignfix block.  When $ENVDIR is wrong --
  # the documented sudo-inside-sudo trap, where SUDO_USER becomes root and
  # $WORK moves to /root/fwre-work -- the alignfix branch was reached first,
  # found no alignfix.so under a directory that does not exist, tried to build
  # one there, and died with "alignfix: build failed. Run it directly to see
  # why".  Running it directly writes to /tmp and SUCCEEDS, which confirms the
  # wrong diagnosis and sends the operator round the loop again.  Measured
  # 2026-08-18: a probe matrix wrapped in its own `sudo` produced seven rows of
  # "the server did not answer" for that reason and nothing else, and the first
  # hypothesis it suggested -- ETXTBSY on a mapped alignfix.so -- was tested and
  # refuted before the real cause was found.
  #
  # The rule: when two refusals can fire for the same cause, the one that names
  # the cause has to be the one that fires.
  # Name the directory. This message used to say only "run build", and when the
  # work directory was resolved wrongly -- nested sudo makes SUDO_USER=root and
  # sends everything to /root/fwre-work -- it sent the operator to rebuild an
  # environment that was already correct, 55 times. A refusal that does not say
  # where it looked cannot be distinguished from the thing it accuses you of.
  [ -f "$ENVDIR/var/boa.conf" ] || die \
    "no boa.conf at $ENVDIR/var/boa.conf
     profile   $PROFILE
     work dir  $WORK   (FWRE_WORK, else the invoking user's home)
     If that work dir looks wrong, this is the sudo-inside-sudo trap: SUDO_USER
     becomes root and \$WORK moves to /root. Pass FWRE_WORK explicitly.
     If it looks right, the environment really is missing: run build."

  # --------------------------------------------------------------- alignfix
  # OFF BY DEFAULT, and that is the decision rather than the omission.
  #
  # qemu-user delivers SIGBUS for unaligned user-space accesses; the MIPS kernel
  # on the device fixes them up and the program never notices. libapmib's
  # `mib_write_to_raw` packs variable-length TLV records, so its halfword stores
  # land on odd addresses as a matter of course -- which is why 39 of 57
  # handlers "died" in the W07 sweep, why P8-24's recovery write could not be
  # observed, and why nothing that saves configuration could be measured here.
  # tools/alignfix/ removes that one divergence.
  #
  # It stays opt-in because turning it on changes what the environment IS.
  # Every measurement this repository has recorded under emulation was taken
  # without it, the CONTROL set above was established without it, and a flag
  # that silently changed all of that would make two incomparable things look
  # like one. So: the mode is chosen explicitly, printed here, and the fix-up
  # count is written to the log where a report can pick it up. A run that fixes
  # up 24 unaligned stores is not the same claim as one that fixes up none, and
  # the difference has to be visible.
  if [ "$alignfix" -eq 1 ]; then
    local so="$ENVDIR/lib/alignfix.so"
    if [ ! -f "$so" ]; then
      note "alignfix: building tools/alignfix/alignfix.so"
      bash "$REPO/tools/alignfix/build.sh" "$so" >/dev/null || die \
        "alignfix: build failed. Run it directly to see why:
       bash $REPO/tools/alignfix/build.sh /tmp/alignfix.so"
    fi
    preload="-E LD_PRELOAD=/lib/alignfix.so"
    note "alignfix: ON -- unaligned accesses will be emulated, as the device's"
    note "          kernel does. This environment is NOT byte-identical to the"
    note "          one every earlier measurement was taken in."
  else
    note "alignfix: off (default). Handlers that write configuration will die"
    note "          on a qemu SIGBUS inside libapmib; that is the emulator, not"
    note "          the firmware. Pass --alignfix to remove that divergence."
  fi

  # Refuse to start on a port somebody else holds. Without this the checks below
  # pass by talking to the incumbent: they verify a property of the *port*, not
  # of the process this function started, and those are different claims.
  local holder; holder="$(port_holder "$port")"
  if [ -n "$holder" ]; then
    die "port $port is already held by pid $holder ($(tr '\0' ' ' < "/proc/$holder/cmdline" 2>/dev/null))
     Starting now would bind nothing and every check below would be answered by
     that process instead. If it is a leftover of this environment:
       sudo $0 --profile $PROFILE reap"
  fi
  sed "s/^Port .*/Port $port/" "$ENVDIR/var/boa.conf" > "$conf"

  rm -rf "$ENVDIR/var/web/config.dat"
  mkdir -p "$ENVDIR/var/web/config.dat"

  # shellcheck disable=SC2086  # $preload is either empty or exactly two words
  guest $preload /bin/boa -d -f /var/boa-emu.conf \
      >"$ENVDIR/tmp/boa-emu.log" 2>&1 &
  # `-d`, and the namespace above forces it. boa daemonises by default: it
  # forks and the parent exits -- and that parent is pid 1 of the new PID
  # namespace, so the kernel kills everything else in it. The log read
  # `boa: starting server pid=3` and then nothing was listening, on both
  # profiles, which looks exactly like a server that failed to bind.
  #
  # -d changes the process structure and nothing about how a request is
  # handled; crash-triage.py has driven this binary that way since it was
  # written. Besides working at all, it buys this: the process holding the
  # socket IS the namespace's init, so killing it takes every child with it --
  # which is the orphan problem the comment further down was written about.
  local i=0
  while [ "$i" -lt 20 ]; do
    sleep 1; i=$((i + 1))
    curl -sf -m 2 -o /dev/null "http://127.0.0.1:$port/login.htm" && break
  done

  # Before either control below: is ANYTHING listening? The controls read a
  # status code out of curl, and `code="$(curl ...)"` under set -e takes the
  # whole script down with curl's exit 7 when there is no server -- so the
  # message written for exactly this case, the one that names the log file,
  # could never print. `serve` exited a bare 7 and said nothing at all. Same
  # shape as instrument bug 44: of two refusals that can fire for one cause,
  # the one that names the cause has to be the one that fires.
  # And the check that the two above cannot make: is the process answering the
  # one this function started? A control that cannot tell "my server is up" from
  # "somebody's server is up" is the failure this whole subcommand exists to
  # prevent, and it went undetected for a full sweep.
  # `boa` daemonises. The pid bash hands back is the launcher's; the process
  # that ends up holding the socket is its child, and after the launcher exits
  # that child is re-parented to init. So "is the listener the pid I started"
  # is the wrong question -- it is never true -- and the right one is whether
  # the listener is running inside THIS environment, which /proc/<pid>/root
  # answers exactly and which also tells the two profiles apart.
  #
  # This is also why orphans accumulated: the pidfile held the launcher's pid,
  # so `stop` killed a process that had already exited, reported success, and
  # left the server running. Thirty-two of them by the end of one sweep. The
  # pidfile now holds the pid that owns the socket.
  local holder_now holder_root
  holder_now="$(port_holder "$port")"
  if [ -z "$holder_now" ]; then
    die "nothing is listening on $port after $i seconds.
     The log is $ENVDIR/tmp/boa-emu.log"
  fi
  holder_root="$(readlink "/proc/$holder_now/root" 2>/dev/null || true)"
  if [ "$holder_root" != "$ENVDIR" ]; then
    die "port $port is held by pid $holder_now, whose root is
       ${holder_root:-<unreadable>}
     and this profile's environment is
       $ENVDIR
     Everything measured against it would belong to another environment.
       sudo $0 --profile $PROFILE reap"
  fi

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
    kill "$holder_now" 2>/dev/null
    die "emulated server did not reproduce the gate; refusing to report it as up"
  fi
  echo "$holder_now" > "$ENVDIR/tmp/boa-emu.pid"
  echo "boa is serving on 127.0.0.1:$port (pid $holder_now).  Stop it with:"
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
  mkflash) shift; cmd_mkflash "$@" ;;
  build) shift; cmd_build "$@" ;;
  reset) shift; cmd_reset "$@" ;;
  check) shift; cmd_check "$@" ;;
  diff)  shift; cmd_diff  "$@" ;;
  run)   shift; cmd_run   "$@" ;;
  serve) shift; cmd_serve "$@" ;;
  stop)  shift; cmd_stop  "$@" ;;
  reap)  shift; cmd_reap  "$@" ;;
  *) cat >&2 <<EOF
usage: sudo $0 [--profile NAME] {build|reset|check|diff|run|serve|stop|reap ...}

  --profile NAME   which firmware to stand up. Default unit-2018.
        unit-2018  the build this unit runs, on this unit's own flash dump.
                   Not reproducible by anyone else: neither half is downloadable.
        v2.1.2     a published image and nothing else -- rootfs from the .web
                   container, flash rebuilt from the same container by
                   tools/mkflash.py. This is the profile G4 clause 3a is about.
        Currently: $PROFILE -> $ENVDIR

  mkflash construct the profile's flash image from a published container plus
          synthesised settings regions. v2.1.2 only; unit-2018 stands on a
          real dump and refuses
  build   create $ENVDIR from the $PROFILE rootfs + its flash image
  reset   restore the flash image AND drop the SysV shm/sem the MIB cache uses
  check   positive control: three known values, read back through /bin/flash
  diff    what changed in the flash image, and whether 0x6493 still balances
  run     run a command inside the environment, e.g.
            sudo $0 run /bin/flash get TELNET_ENABLED
            sudo $0 run /bin/sh -c 'flash set HW_WLAN0_WSC_PIN 1;ls -l / > /var/web/x.txt'
  serve   stand boa up on 127.0.0.1 and prove the gate behaves as it does on
          the device before saying it is up, e.g.
            sudo $0 serve 8080
          --alignfix  emulate unaligned accesses the way the device's MIPS
                      kernel does, via tools/alignfix/. OFF by default: it
                      changes what the environment is, and every measurement
                      recorded before 2026-08-18 was taken without it. Turn it
                      on to reach any path that writes configuration -- without
                      it libapmib's TLV serialiser takes a qemu SIGBUS and the
                      handler looks like it crashed the server, e.g.
                        sudo $0 serve 8080 --alignfix
  stop    stop it, by pidfile. Not \`pkill -f\`, which matches the calling
          shell's own command line and kills it
  reap    kill EVERY guest process still running in this environment, found by
          /proc/<pid>/root rather than by a command-line pattern. boa does not
          survive several of its own handlers, and a crashed one leaves the
          pidfile pointing at a corpse -- so orphans accumulate and an old one
          keeps the port. Run this between sweeps

Always: reset before a measurement. Restoring the file alone is not a reset.
EOF
    exit 2 ;;
esac
