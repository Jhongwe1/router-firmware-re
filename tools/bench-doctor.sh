#!/usr/bin/env bash
# Is this machine ready to do the thing you are about to do?
#
# Why this exists
# ---------------
# A copy-pasteable runsheet does not fail a newcomer at the commands. It fails
# them at the first moment the output differs from the document, because a
# markdown file can ask them to check something but it cannot tell them what
# went wrong. This can.
#
# Every check prints one of three things, and the third is the point:
#
#     ok    <what holds>
#     --    <what is missing, and which tier needs it>
#     FAIL  <what is wrong>  ->  the exact command that fixes it
#
# Three tiers, because most of this repository is reproducible and the part that
# is not should say so rather than being discovered by a reader at step 40:
#
#   1  clone        a clone and an internet connection. Everything the two
#                   published firmware images support, plus every guard suite.
#   2  dump         tier 1 plus a flash dump read off an N150RT. Reports about
#                   the build this unit runs, and the emulator.
#   3  bench        tier 2 plus the physical device on a wire: serial adapter
#                   attached, USB Ethernet attached, an isolated segment.
#
# A tier's checks are skipped, not failed, when its inputs are absent -- a
# reader at tier 1 is not doing anything wrong.
#
#   bash tools/bench-doctor.sh              # every tier this machine can reach
#   bash tools/bench-doctor.sh 1            # only tier 1
#   bash tools/bench-doctor.sh bench        # only tier 3
#
set -uo pipefail

cd "$(dirname "$0")/.." || { echo "cannot cd to the repository root"; exit 1; }

WANT="${1:-all}"
FWRE_WORK="${FWRE_WORK:-$HOME/fwre-work}"
DUMPS="$FWRE_WORK/dumps"
VENV="$FWRE_WORK/venv"
EX="$FWRE_WORK/extracted"

# The two reads of this unit's flash, from 2026-08-14 and 2026-08-16. Identical,
# which is what makes them a backup rather than one file twice.
DUMP_SHA=a800059a9b8c414df026a22b8423a5939d0f9bb793109d0f7ce086f6810f37ea

pass=0; miss=0; fail=0
ok()   { printf '  \033[32mok\033[0m    %s\n' "$1"; pass=$((pass + 1)); }
skip() { printf '  \033[90m--\033[0m    %s\n' "$1"; miss=$((miss + 1)); }
bad()  { printf '  \033[31mFAIL\033[0m  %s\n        \033[36m->\033[0m %s\n' "$1" "$2"; fail=$((fail + 1)); }
head_() { printf '\n\033[1m%s\033[0m\n' "$1"; }

want() {
  case "$WANT" in
    all) return 0 ;;
    1|clone)  [ "$1" = 1 ] ;;
    2|dump)   [ "$1" = 2 ] ;;
    3|bench)  [ "$1" = 3 ] ;;
    *) echo "unknown tier: $WANT  (use 1|clone, 2|dump, 3|bench, or nothing)"; exit 2 ;;
  esac
}

# have <binary> <what it is for> <how to get it>
have() {
  if command -v "$1" >/dev/null 2>&1; then
    ok "$1 — $2"
  else
    bad "$1 is not on PATH — $2" "$3"
  fi
}

# ---------------------------------------------------------------- tier 1
if want 1; then
head_ "tier 1 — a clone and an internet connection"

if command -v python3 >/dev/null 2>&1; then
  if python3 -c 'import tomllib' 2>/dev/null; then
    ok "python3 $(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])') has tomllib (3.11+)"
  else
    bad "python3 is older than 3.11 — rtcase needs tomllib" \
        "install python3.11+, or run with FWRE_PY=$VENV/bin/python"
  fi
else
  bad "python3 is not on PATH" "sudo apt install python3"
fi

have make      "the task runner every command in runsheet.md goes through" "sudo apt install make"
have git       "provenance: the register's freeze is only meaningful in a diff" "sudo apt install git"
have sha256sum "hash verification of the firmware images and the dump"       "sudo apt install coreutils"
have xxd       "reading bytes back out of a dump by hand"                    "sudo apt install xxd"
have cmp       "the snapshot comparisons"                                     "sudo apt install diffutils"
have shellcheck "linting the shell tools, exactly as CI does"                "sudo apt install shellcheck"

if [ -x "$VENV/bin/python" ]; then
  if "$VENV/bin/python" -c 'import fwrecon' 2>/dev/null; then
    ok "the analysis venv exists and fwrecon imports"
  else
    bad "the venv exists but fwrecon does not import" "make venv"
  fi
else
  bad "no analysis venv at $VENV" "make venv"
fi

if [ -x "$VENV/bin/ruff" ]; then ok "ruff (make lint)"; else
  bad "ruff is not in the venv" "make venv"; fi

# binwalk is installed by `make setup` into ~/.cargo/bin, which a non-login
# shell does not have on PATH. "not installed" and "installed where this shell
# cannot see it" need different fixes, and conflating them sends a reader to
# re-run a 20-minute install they have already done.
if command -v binwalk >/dev/null 2>&1; then
  ok "binwalk — carving the images, and finding the loader's LZMA stage 2"
elif [ -x "$HOME/.cargo/bin/binwalk" ]; then
  bad "binwalk is installed at ~/.cargo/bin but not on this shell's PATH" \
      "use a login shell: wsl -d Ubuntu-24.04 -- bash -lc '<command>'   (or: export PATH=\"\$HOME/.cargo/bin:\$PATH\")"
else
  bad "binwalk is not installed" "make setup   (installs to ~/.cargo/bin; afterwards use a login shell)"
fi
have unsquashfs "extracting the LZMA SquashFS root filesystems" "sudo apt install squashfs-tools"

# The register is a gate, and a red register makes every later result
# inadmissible rather than merely unrecorded.
if python3 tools/rtcase.py check >/dev/null 2>&1; then
  ok "the test register is green ($(python3 tools/rtcase.py stats 2>/dev/null))"
else
  bad "the test register does not pass its own check" "python3 tools/rtcase.py check   # read the reason"
fi

if [ -z "$(git status --porcelain 2>/dev/null)" ]; then
  ok "the working tree is clean — a bench session's diff will be only the session"
else
  skip "the working tree has uncommitted changes; commit before a session so the plan's timestamp means something"
fi
fi

# ---------------------------------------------------------------- tier 2
if want 2; then
head_ "tier 2 — a flash dump read off an N150RT"

dumps_ok=0
if [ -d "$DUMPS" ]; then
  for n in 1 2; do
    f="$DUMPS/flash-n150rt-console-$n.bin"
    if [ ! -f "$f" ]; then
      skip "$(basename "$f") absent — tier 2 and 3 need it (RUNBOOK 8.7.9 reads it off the device)"
      continue
    fi
    got="$(sha256sum "$f" | cut -d' ' -f1)"
    if [ "$got" = "$DUMP_SHA" ]; then
      ok "$(basename "$f") — sha256 matches the 2026-08-16 read"
      dumps_ok=$((dumps_ok + 1))
    else
      bad "$(basename "$f") sha256 is $got, not $DUMP_SHA" \
          "STOP. This is the only restore image there is. Do not overwrite it; work out which copy is wrong first"
    fi
  done
else
  skip "no $DUMPS — tier 1 does not need it"
fi
[ "$dumps_ok" = 2 ] && ok "two independent reads agree — there is a safety net" \
  || skip "fewer than two agreeing dumps: a bench session that writes flash has no second copy"

if [ -d "$EX/unit-2018/squashfs-root" ]; then
  ok "this unit's rootfs is extracted"
  if [ -f "$EX/unit-2018/squashfs-root/lib/libapmib.so" ]; then
    ok "libapmib.so present — the config decode and the MIB cross-check need it"
  else
    bad "libapmib.so missing from the extracted rootfs" "bash tools/unpack-firmware.sh --flash $DUMPS/flash-n150rt-console-1.bin"
  fi
else
  skip "no extracted unit-2018 rootfs — needed by recon-unit, loader-report and qemu-env"
fi

if [ -x "$VENV/bin/python" ] && [ -f "$DUMPS/flash-n150rt-console-1.bin" ]; then
  if python3 tools/loader-unpack.py "$DUMPS/flash-n150rt-console-1.bin" >/dev/null 2>&1; then
    ok "the boot loader's stage 2 unpacks and passes its own positive control"
  else
    bad "loader-unpack refuses this dump" "python3 tools/loader-unpack.py $DUMPS/flash-n150rt-console-1.bin   # read the refusal"
  fi
fi
fi

# ---------------------------------------------------------------- tier 3
if want 3; then
head_ "tier 3 — the device on a wire"

have picocom "typing boot loader commands by hand when a tool will not do it" "sudo apt install picocom"
have nmap    "the port round"                                                 "sudo apt install nmap"
have tshark  "the isolation capture, and counting MAC addresses in it"        "sudo apt install tshark"

# --- station 5: the clip, added 2026-08-20 --------------------------------
# lsusb is a hard fail rather than a skip, and that is the whole point of the
# entry. flash-read.sh degrades to a warning without it and flash-write.sh
# refuses outright, because the check it performs -- "is the programmer really
# on the bus" -- is the one standing between a clip and a 4 MiB part that holds
# a build published nowhere. Instrument bug 45: a check that degrades to a skip
# has not run, and it degrades in the environments with the fewest tools.
have lsusb "confirming the CH341A is really on the bus before anything is clipped" \
           "sudo apt install usbutils"
if command -v lsusb >/dev/null 2>&1; then
  if lsusb 2>/dev/null | grep -qi '1a86:5512'; then
    ok "CH341A (1a86:5512) is attached to this WSL instance"
  else
    skip "no CH341A on the bus — only station 5 needs it"
  fi
fi

# shellcheck disable=SC2012  # a count is all that is wanted, not the names
if ls /dev/ttyUSB* >/dev/null 2>&1; then
  for d in /dev/ttyUSB*; do ok "$d present"; done
  if [ -r /dev/ttyUSB0 ] && [ -w /dev/ttyUSB0 ]; then
    ok "/dev/ttyUSB0 is readable and writable by this user"
  else
    bad "/dev/ttyUSB0 exists but this user cannot use it" \
        "sudo usermod -aG dialout \$USER && exec newgrp dialout    # or prefix commands with sudo"
  fi
else
  bad "no /dev/ttyUSB* — the serial adapter is not attached to this WSL instance" \
      "PowerShell:  usbipd list  then  usbipd attach --wsl --busid <the 10c4:ea60 one>"
fi

IFACE="$(ip -br link 2>/dev/null | awk '/^enx/{print $1; exit}')"
if [ -n "$IFACE" ]; then
  ok "USB Ethernet is inside WSL as $IFACE"
  state="$(ip -br link show "$IFACE" | awk '{print $2}')"
  # NOT "the other end is powered and negotiated", which this said until
  # 2026-08-21. This rtl8153 asserts carrier with nothing at the far end: on
  # 2026-08-18 it reported LOWER_UP with the board demonstrably unplugged, and it
  # did so again on 2026-08-21 while the router sat unpowered on the desk.
  # runsheet.md A3.1 carries the same warning and the doctor was contradicting
  # it. A check that states a conclusion its input cannot support is worse than
  # no check, because the operator believes it.
  if ip -br link show "$IFACE" | grep -q LOWER_UP; then
    ok "$IFACE reports carrier — which this adapter also does with nothing attached, so it is not evidence the device is powered (ip neigh + rx_packets are)"
  else
    skip "$IFACE is $state with no carrier — normal while the device is unplugged or sitting in the boot loader before Ethernet init"
  fi
  addr="$(ip -br addr show "$IFACE" | awk '{print $3}')"
  if [ -n "$addr" ]; then ok "$IFACE has $addr"; else
    skip "$IFACE has no address yet — runsheet.md A3.1 assigns 10.1.1.100/24"; fi
else
  bad "no enx* interface — the USB Ethernet adapter is not attached to this WSL instance" \
      "PowerShell:  usbipd attach --wsl --busid <the 0bda:8153 one>"
fi

# Instrument bug 21 in PROGRESS.md: `ping 10.1.1.1` succeeded while the adapter
# was on the Windows side and every packet was being routed. The only tell was
# ttl=63. This reads the routing table instead of trusting a reply.
# Only worth asking once the interface is here: with the adapter on the Windows
# side this always says "routed", which is the same fact reported twice and sends
# the reader chasing a second cause that does not exist.
if [ -r /proc/net/route ] && [ -n "$IFACE" ]; then
  # The default route matches every destination, so "is there a route to
  # 10.1.1.1" is always yes and the `none` branch below was unreachable — dead
  # code that had the only correct message in it. The state it was written for
  # is the state every session starts in (adapter attached to WSL, segment not
  # configured yet), and in that state this check FAILED and told the operator
  # to attach the adapter they had just attached.
  #
  # A check whose failure names the wrong fix is worse than no check: it sends
  # you to re-do something that is already right, and the real cause goes on
  # looking like the one you just ruled out. Instrument bug 24.
  #
  # So the mask width is now part of the answer, not just the tiebreak: a
  # default route (mask 0) matching is "no route to this segment", and only a
  # more specific route can be direct or genuinely gatewayed.
  direct="$(python3 - <<'PY' 2>/dev/null
import socket
t = int.from_bytes(socket.inet_aton("10.1.1.1"), "big")
best, gw = -1, None
with open("/proc/net/route", encoding="ascii") as fh:
    next(fh)
    for line in fh:
        f = line.split()
        if len(f) < 8:
            continue
        d = int.from_bytes(bytes.fromhex(f[1]), "little")
        g = int.from_bytes(bytes.fromhex(f[2]), "little")
        m = int.from_bytes(bytes.fromhex(f[7]), "little")
        if (t & m) == d and bin(m).count("1") > best:
            best, gw = bin(m).count("1"), g
if best <= 0:                     # nothing, or only the default route
    print("unconfigured")
else:
    print("direct" if gw == 0 else "routed")
PY
)"
  case "$direct" in
    direct) ok "10.1.1.1 resolves to a directly attached subnet — not through a gateway" ;;
    routed) bad "10.1.1.1 is reachable only through a gateway" \
                "A specific route sends it via a gateway, so a reply would come back ttl=63 and prove nothing. Check which interface owns it: ip route get 10.1.1.1" ;;
    *)      skip "no route to the 10.1.1.0/24 segment yet (only the default route matches) — runsheet.md A3.1 adds one" ;;
  esac
fi

# Everything above this line asks whether the HOST is ready. None of it asks
# whether the DEVICE still works, and on 2026-08-17 an unauthenticated POST
# round of this project's own wrote DHCP_MTU_SIZE=0 into the unit's flash. The
# WAN has been dead on every boot since; four bench sessions ran and not one
# noticed, because nothing was looking. PROGRESS.md open item 73.
#
# One unauthenticated GET /config.dat returns the whole live configuration --
# the gate does not run for a path with no .htm -- so this costs one request,
# no credentials and no shell, and it reads the persistent state, which is the
# class of breakage that survives a reboot and therefore the class that goes
# unnoticed. A device that is off is skipped, not failed: exit 3 means nothing
# was measured, and that is a third answer on purpose.
head_ "tier 3 — the device can still do its job"
if [ ! -x "$VENV/bin/python" ]; then
  skip "no analysis venv, so the served configuration cannot be decoded — make venv"
else
  mib="$EX/unit-2018/squashfs-root/lib/libapmib.so"
  live_args=(--host 10.1.1.1 --timeout 8)
  [ -f "$mib" ] && live_args+=(--mib "$mib")
  live_out="$(python3 tools/device-liveness.py "${live_args[@]}" 2>&1)"
  case "$?" in
    0) ok "10.1.1.1 serves its configuration and every primary-function field holds"
       drift="$(printf '%s\n' "$live_out" | sed -n 's/^  \([0-9]*\) field(s) differ.*/\1/p')"
       [ -n "$drift" ] && [ "$drift" != 0 ] && \
         skip "$drift field(s) differ from the frozen 2026-08-16 baseline — expected after W05/W06/W07, but read the list before blaming a measurement on the device" ;;
    3) skip "10.1.1.1 did not answer /config.dat — normal before the device is powered on. Nothing about the device has been measured" ;;
    1) bad "the device answered and it is NOT doing its job: $(printf '%s\n' "$live_out" | sed -n 's/^  FAIL  //p' | tr '\n' ';')" \
           "python3 tools/device-liveness.py   # the failing field names what breaks. Do not start a session on this: every negative result gets a second explanation" ;;
    *) bad "device-liveness could not decide: $(printf '%s\n' "$live_out" | tail -1)" \
           "python3 tools/device-liveness.py   # read the refusal" ;;
  esac
fi
fi

# ----------------------------------------------------------------- summary
printf '\n  %d ok, %d not applicable, %d to fix\n' "$pass" "$miss" "$fail"
if [ "$fail" -gt 0 ]; then
  printf '  \033[31mDo not start a session with a FAIL above.\033[0m Each one names its fix.\n'
  exit 1
fi
printf '  ready for: '
if want 3 && [ "$WANT" = all ]; then printf 'whatever the tiers above allow.\n'; else printf 'tier %s.\n' "$WANT"; fi
