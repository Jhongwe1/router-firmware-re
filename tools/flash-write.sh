#!/usr/bin/env bash
#
# flash-write.sh — write the SPI NOR on my own unit through a CH341A, and make
# the thing you are about to change visible before it changes.
#
# Why this is a second file rather than a flag on flash-read.sh
# ------------------------------------------------------------
# `tools/flash-read.sh` says, in its own header, that there is no code path in
# it that passes -w, -E or -v to flashrom, on purpose. A `--write` flag would
# have made that sentence false, and the sentence is worth more than the
# convenience: a reader who wants to know whether the reading tool can damage
# the part gets to answer it by grepping one file.
#
# The same split exists one layer down, and it is deliberate:
#   tools/console-write.py   writes through the boot loader (FLW), refuses the
#                            loader region and H601, needs the board powered
#   this file                writes through a clip, refuses the same two ranges,
#                            needs the board UNPOWERED
# Two paths, same two protected regions. If only one of them refused, the
# protection would be a property of a tool rather than a property of the project.
#
# What it will not do
# -------------------
#   * it never passes -E. There is no chip-erase path here.
#   * it never writes without reading the chip first and showing you the diff.
#   * `commit` refuses if any byte that would change falls outside an allow-list.
#   * `restore` refuses an image whose sha256 does not appear in
#     dumps/MANIFEST.json. You can put back something this repository has
#     recorded reading. You cannot put back something nobody wrote down.
#
# Why a whole-image diff instead of "write these bytes at this offset"
# --------------------------------------------------------------------
# An offset check only proves the offset you TYPED is allowed. A diff proves the
# bytes that will actually move are the bytes you meant -- including the ones
# you did not know were different, which is the case that damages a part. It
# also costs nothing extra: flashrom already reads before it writes, and only
# erases the blocks that differ.
#
# Usage:
#   ./tools/flash-write.sh plan    --image F [--allow LO-HI]...
#   ./tools/flash-write.sh commit  --image F --expect-id 1c7016 --yes
#   ./tools/flash-write.sh restore --image F --sha256 HASH --expect-id 1c7016 --yes
#
# Options:
#   --image F        the FULL 4 MiB image you want the chip to hold afterwards
#   --allow LO-HI    repeatable; a range commit may change, e.g. 0x3FF000-0x400000
#   --expect-id HEX  predicted JEDEC id. Required for anything that writes
#   --sha256 HASH    restore only; must match the file AND be in dumps/MANIFEST.json
#   --yes            skip the "is the router unplugged" prompt
#   --keep-preimage  keep the pre-write read even when nothing is written
#
# Environment:
#   FWRE_WORK  artefact root. Defaults to ~/fwre-work. Images and pre-write reads
#              never go in the repository - see dumps/README.md.
#
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${FWRE_WORK:-$HOME/fwre-work}"
DEST="$WORK/dumps"
MANIFEST="$REPO/dumps/MANIFEST.json"
PROGRAMMER="ch341a_spi"
FLASH_BYTES=4194304

# The two ranges no path in this project writes, on either instrument.
#   0x000000-0x006000  the boot loader. Damage it and the console that would
#                      have recovered the part is the thing that is gone.
#   0x006000-0x008000  H601: this unit's MAC addresses and radio calibration.
#                      Measured at manufacture, in no vendor image, and NOT
#                      restored by the reset button - PROGRESS.md W07 close.
FORBIDDEN=("0x000000-0x006000" "0x006000-0x008000")

c_ok()   { printf '\033[32m  ok  \033[0m %s\n' "$*"; }
c_run()  { printf '\033[36m ==>  \033[0m %s\n' "$*"; }
c_warn() { printf '\033[33m warn \033[0m %s\n' "$*"; }
c_err()  { printf '\033[31m FAIL \033[0m %s\n' "$*" >&2; }
die()    { c_err "$*"; exit 1; }

# The same one owner for flashrom's output format that flash-read.sh uses. This
# file had its own copy until 2026-08-21, with the same defect: it asked for -V
# and looked for a line printed only at -VVV, so `identify` found no id and
# refused EVERY write with "not writing a chip that is silent" -- on a chip that
# was answering. It fails safe, which is right, and it names the wrong cause,
# which is what makes it expensive: the operator unclips a working part.
# shellcheck source=tools/lib/flashrom-parse.sh
. "$REPO/tools/lib/flashrom-parse.sh"

if [ -f "$REPO/tools/lib/require-linux-workspace.sh" ]; then
  # shellcheck source=tools/lib/require-linux-workspace.sh
  . "$REPO/tools/lib/require-linux-workspace.sh"
fi

SUDO=()
[ "$(id -u)" -eq 0 ] || SUDO=(sudo)

flashrom_rw() { "${SUDO[@]}" flashrom -p "$PROGRAMMER" "$@"; }

need() { command -v "$1" >/dev/null || die "$1 is required ($2)"; }

# One definition, five call sites. Also the reason none of them inline a
# `local x="$(...)"`: that form masks the command's exit status, which on a tool
# whose every artefact is named after a timestamp is a filename nobody notices.
stamp() { date -u +%Y%m%dT%H%M%SZ; }

# ---------------------------------------------------------------------------
# diff_ranges A B -- the byte ranges in which two same-sized files differ.
# Sourceable and hardware-free, so tools/test-flash-tools.sh can drive it.
# ---------------------------------------------------------------------------
diff_ranges() {
  python3 - "$1" "$2" <<'PYEOF'
import sys
a = open(sys.argv[1], "rb").read()
b = open(sys.argv[2], "rb").read()
if len(a) != len(b):
    print(f"SIZE {len(a)} {len(b)}")
    raise SystemExit(3)
runs, start = [], None
for i in range(len(a)):
    if a[i] != b[i]:
        if start is None:
            start = i
    elif start is not None:
        runs.append((start, i))
        start = None
if start is not None:
    runs.append((start, len(a)))
# Coalesce runs closer together than one 4 KiB sector: flashrom erases whole
# sectors, so two changes 12 bytes apart are one write, not two.
merged = []
for lo, hi in runs:
    if merged and lo - merged[-1][1] < 0x1000:
        merged[-1] = (merged[-1][0], hi)
    else:
        merged.append((lo, hi))
for lo, hi in merged:
    print(f"0x{lo:06x}-0x{hi:06x} {hi - lo}")
PYEOF
}

# range_within LO HI LIST... -- is [LO,HI) inside any range in LIST?
range_within() {
  local lo="$1" hi="$2"; shift 2
  local r rlo rhi
  for r in "$@"; do
    rlo="${r%%-*}"; rhi="${r##*-}"
    if [ "$((lo))" -ge "$((rlo))" ] && [ "$((hi))" -le "$((rhi))" ]; then
      return 0
    fi
  done
  return 1
}

# range_overlaps LO HI LIST... -- does [LO,HI) touch any range in LIST?
range_overlaps() {
  local lo="$1" hi="$2"; shift 2
  local r rlo rhi
  for r in "$@"; do
    rlo="${r%%-*}"; rhi="${r##*-}"
    if [ "$((lo))" -lt "$((rhi))" ] && [ "$((hi))" -gt "$((rlo))" ]; then
      return 0
    fi
  done
  return 1
}

preflight() {
  need flashrom "apt install flashrom"
  need sha256sum "coreutils"
  need python3 "python3"
  mkdir -p "$DEST"
  if command -v lsusb >/dev/null; then
    if lsusb | grep -qi '1a86:5512'; then
      c_ok "CH341A present on the USB bus (1a86:5512)"
    else
      die "no 1a86:5512 on the USB bus - usbipd attach it from Windows first"
    fi
  else
    die "lsusb is not installed, so the programmer cannot be confirmed present.
        apt install usbutils. A check that degrades to a warning has not run,
        and this is the tool where that matters most."
  fi
}

confirm_unplugged() {
  [ "${ASSUME_YES:-0}" -eq 1 ] && return 0
  echo
  echo "  About to WRITE. Before that:"
  echo "    - router power adapter UNPLUGGED, not just switched off"
  echo "    - the USB-TTL serial adapter unplugged too"
  echo "    - the programmer measured at 3.3 V on the socket, not 5 V"
  echo "    - you have a verified read of this chip you could put back"
  echo
  read -r -p "  All four true? [y/N] " ans
  case "$ans" in [yY]*) ;; *) die "stopped at the operator's own check" ;; esac
}

# Identify, and refuse to touch a chip that will not say what it is.
JEDEC_ID=""
identify() {
  local expect="$1" log ids
  log="$DEST/write-probe-$(date -u +%Y%m%dT%H%M%SZ).log"
  c_run "probing before anything is written"
  flashrom_rw "$FLASHROM_PROBE_V" >"$log" 2>&1 || true
  ids="$(parse_rdids "$log")"
  if [ -z "$ids" ]; then
    case "$(rdid_failure_kind "$log")" in
      not-printed)
        die "flashrom identified a part but this log has no RDID line in it. NOTHING WAS WRITTEN, and DO NOT RE-SEAT THE CLIP: the bus carried a transaction, so what is missing is the line, not the answer. flashrom 1.3.0 prints it only at -VVV. Check: grep -i rdid $log" ;;
      *)
        die "no JEDEC id came back and flashrom identified nothing either, so the bus itself is the suspect. Not writing a chip that is silent. log: $log" ;;
    esac
  fi
  [ "$(printf '%s\n' "$ids" | wc -l)" -eq 1 ] \
    || die "the chip returned more than one id across probes - unstable contact. log: $log"
  JEDEC_ID="$ids"
  c_ok "JEDEC id 0x$JEDEC_ID"
  [ -n "$expect" ] || die "--expect-id is required for anything that writes"
  [ "$(printf '%s' "$expect" | tr '[:upper:]' '[:lower:]')" = "$JEDEC_ID" ] \
    || die "PREDICTION MISSED: expected 0x$expect, silicon says 0x$JEDEC_ID. Nothing was written."
}

read_chip() {
  local out="$1"
  c_run "reading the chip as it is now -> $out"
  flashrom_rw -r "$out" >/dev/null 2>&1 || die "the pre-write read failed. Nothing was written."
  [ "$(id -u)" -eq 0 ] || "${SUDO[@]}" chown "$(id -u):$(id -g)" "$out"
  [ "$(stat -c %s "$out")" = "$FLASH_BYTES" ] \
    || die "the pre-write read is $(stat -c %s "$out") bytes, expected $FLASH_BYTES"
  c_ok "pre-write image  $(sha256sum "$out" | cut -d' ' -f1)"
}

show_plan() {
  local pre="$1" want="$2"; shift 2
  local allow=("$@") lo hi n rc=0 total=0 count=0
  echo
  c_run "what would change"
  while read -r range n; do
    [ -n "$range" ] || continue
    lo="${range%%-*}"; hi="${range##*-}"
    count=$((count + 1)); total=$((total + n))
    if range_overlaps "$lo" "$hi" "${FORBIDDEN[@]}"; then
      c_err "$range  $n bytes  <- REFUSED: the boot loader or H601"
      rc=1
    elif [ "${#allow[@]}" -gt 0 ] && range_within "$lo" "$hi" "${allow[@]}"; then
      c_ok  "$range  $n bytes  (allowed)"
    else
      c_err "$range  $n bytes  <- outside every --allow range"
      rc=1
    fi
  done < <(diff_ranges "$pre" "$want")
  if [ "$count" -eq 0 ]; then
    c_warn "the chip already holds exactly these bytes. Nothing to write."
    return 2
  fi
  echo
  c_run "$count range(s), $total bytes, in a $FLASH_BYTES byte part"
  return "$rc"
}

cmd_plan() {
  local image="" allow=() keep=0
  while [ $# -gt 0 ]; do
    case "$1" in
      --image) image="$2"; shift 2 ;;
      --allow) allow+=("$2"); shift 2 ;;
      --keep-preimage) keep=1; shift ;;
      *) die "unknown option: $1" ;;
    esac
  done
  [ -f "$image" ] || die "no such image: $image"
  preflight
  local pre rc=0
  pre="$DEST/preimage-$(stamp).bin"
  read_chip "$pre"
  show_plan "$pre" "$image" "${allow[@]+"${allow[@]}"}" || rc=$?
  [ "$keep" -eq 1 ] || { rm -f "$pre"; c_warn "pre-write read discarded (--keep-preimage to keep it)"; }
  case "$rc" in
    # Not backticks. In a double-quoted bash string a backtick is command
    # substitution, and this repository has lost a test, a heredoc, a sed
    # expression and a remote build to exactly that in one session.
    0) c_ok "every changed range is inside an --allow range. commit would proceed." ;;
    2) ;;
    *) c_err "commit would REFUSE this image." ;;
  esac
  return "$rc"
}

cmd_commit() {
  local image="" allow=() expect=""
  ASSUME_YES=0
  while [ $# -gt 0 ]; do
    case "$1" in
      --image) image="$2"; shift 2 ;;
      --allow) allow+=("$2"); shift 2 ;;
      --expect-id) expect="$2"; shift 2 ;;
      --yes) ASSUME_YES=1; shift ;;
      *) die "unknown option: $1" ;;
    esac
  done
  [ -f "$image" ] || die "no such image: $image"
  [ "${#allow[@]}" -gt 0 ] || die "commit with no --allow range would permit any change. Name the range you mean."
  preflight
  confirm_unplugged
  identify "$expect"
  local pre after
  pre="$DEST/preimage-$(stamp).bin"
  read_chip "$pre"
  show_plan "$pre" "$image" "${allow[@]}" \
    || die "refused. The pre-write read is kept at $pre and nothing was written."
  c_run "writing"
  flashrom_rw -w "$image" || die "the write FAILED. The chip may be part-written.
        Do not unclip. Put back the pre-write image:
          ./tools/flash-write.sh restore --image $pre --sha256 $(sha256sum "$pre" | cut -d' ' -f1) --expect-id $JEDEC_ID --yes"
  c_ok "flashrom verified the write (it verifies by default; -n is never passed here)"
  after="$DEST/postimage-$(stamp).bin"
  read_chip "$after"
  if cmp -s "$after" "$image"; then
    c_ok "independent read-back is byte-identical to the image you asked for"
  else
    c_err "the read-back DIFFERS from the image. flashrom said it verified; a second read disagrees."
    diff_ranges "$after" "$image"
    return 1
  fi
  echo
  c_ok "pre-write image kept at $pre - that is the thing that undoes this"
}

cmd_restore() {
  local image="" want="" expect=""
  ASSUME_YES=0
  while [ $# -gt 0 ]; do
    case "$1" in
      --image) image="$2"; shift 2 ;;
      --sha256) want="$2"; shift 2 ;;
      --expect-id) expect="$2"; shift 2 ;;
      --yes) ASSUME_YES=1; shift ;;
      *) die "unknown option: $1" ;;
    esac
  done
  [ -f "$image" ] || die "no such image: $image"
  [ -n "$want" ] || die "--sha256 is required: restore writes every region, including the two commit refuses"
  local got
  got="$(sha256sum "$image" | cut -d' ' -f1)"
  [ "$got" = "$want" ] || die "the image hashes $got, you named $want"
  if ! grep -qF "$want" "$MANIFEST"; then
    die "$want does not appear in dumps/MANIFEST.json.
        restore puts back an image this repository has recorded reading. An image
        nobody wrote down is not a restore, it is a write with a friendly name."
  fi
  c_ok "$want is recorded in dumps/MANIFEST.json"
  preflight
  confirm_unplugged
  identify "$expect"
  local pre after
  pre="$DEST/preimage-$(stamp).bin"
  read_chip "$pre"
  echo
  c_warn "restore writes EVERY differing region, including the boot loader and H601."
  diff_ranges "$pre" "$image" || true
  c_run "writing the recorded image back"
  flashrom_rw -w "$image" || die "the restore FAILED and the part may be inconsistent. Do not unclip."
  after="$DEST/postimage-$(stamp).bin"
  read_chip "$after"
  if cmp -s "$after" "$image"; then
    c_ok "read-back is byte-identical to the recorded image"
  else
    die "read-back differs from the recorded image after a restore"
  fi
}

main() {
  local sub="${1:-}"
  [ $# -gt 0 ] && shift
  case "$sub" in
    plan)    cmd_plan "$@" ;;
    commit)  cmd_commit "$@" ;;
    restore) cmd_restore "$@" ;;
    # To the first line that is not a comment, then drop it. The old form
    # stopped at the first bare `#`, which is the line between Usage and
    # Options -- so half the flags never printed, and check-runsheet.py
    # reads this block as the tool's own --help. Found 2026-08-20.
    *) sed -n '/^# Usage:/,/^[^#]/p' "${BASH_SOURCE[0]}" | sed '$d' | sed 's/^#\s\?//'
       exit 2 ;;
  esac
}

# Sourceable, so the guard suite can drive diff_ranges, range_within and
# range_overlaps against synthetic images with no programmer attached. The
# allow-list is the whole safety argument of this file; a safety argument nobody
# can run without the hardware is one that gets written once and never tested.
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  main "$@"
fi
