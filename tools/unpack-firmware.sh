#!/usr/bin/env bash
#
# unpack-firmware.sh — carve the root filesystem out of each firmware image and
# extract it, using offsets computed by fwrecon rather than hard-coded constants.
#
# The offsets are not magic numbers: `fwrecon image` parses the Realtek
# IMG_HEADER_T chain and reports where the r6cr (rootfs) payload begins. Feeding
# that back into the extraction step means the two can never drift apart, and it
# exercises the parser against every image we handle.
#
# Extraction target
# -----------------
# Everything lands under $FWRE_WORK (default ~/fwre-work), which MUST be a real
# Linux filesystem. Extracting a SquashFS onto a DrvFs mount (/mnt/c) silently
# loses symlinks, permission bits and setuid flags — and this analysis turns on
# exactly those details: /web/config.dat is a *symlink*, and "no setuid binaries"
# is a claim you can only make if setuid bits survived extraction.
#
set -euo pipefail

WORK="${FWRE_WORK:-$HOME/fwre-work}"
FW="$WORK/firmware"
EX="$WORK/extracted"
PY="${FWRE_PY:-$WORK/venv/bin/python}"

c_ok()   { printf '\033[32m  ok  \033[0m %s\n' "$*"; }
c_run()  { printf '\033[36m ==>  \033[0m %s\n' "$*"; }
c_warn() { printf '\033[33m warn \033[0m %s\n' "$*"; }
c_err()  { printf '\033[31m FAIL \033[0m %s\n' "$*" >&2; }

. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/require-linux-workspace.sh"

[ -x "$PY" ] || { c_err "no python at $PY — run 'make venv' first"; exit 2; }

# version-label  image-filename
IMAGES=(
  "v2.1.2 TOTOLINK-N150RT-V2.1.2-B20150825.1601.web"
  "v3.4.0 TOTOLINK-N150RT-V3.4.0-B20201030.1142.web"
)

unpack_one() {
  local label="$1" filename="$2"
  local img="$FW/$filename"
  local out="$EX/$label"

  echo
  echo "--- $label ($filename) --------------------------------------------"
  [ -f "$img" ] || { c_err "missing $img — run 'make fetch'"; return 1; }
  mkdir -p "$out"

  # Ask the parser where the root filesystem starts and how long it is.
  local meta offset length compression
  meta="$("$PY" -m fwrecon image "$img" --json)"
  offset="$(jq -r '[.sections[] | select(.tag=="r6cr")][0].payload_offset' <<<"$meta")"
  length="$(jq -r '[.sections[] | select(.tag=="r6cr")][0].payload_actual' <<<"$meta")"
  compression="$(jq -r '[.sections[] | select(.tag=="r6cr")][0].squashfs.compression' <<<"$meta")"

  if [ "$offset" = "null" ]; then
    c_err "no r6cr section found in $filename"
    return 1
  fi
  c_ok "rootfs at file offset $offset ($length bytes, $compression-compressed)"

  carve_and_extract "$img" "$out" "$offset" "$length"
}

# Shared by the vendor-container path and the raw-flash path. They differ only
# in how the offset is discovered; everything after the carve is identical, and
# keeping it identical is the point - a rootfs read off the device must be
# extracted by exactly the same steps as one carved from a vendor image, or the
# two cannot be compared.
carve_and_extract() {
  local img="$1" out="$2" offset="$3" length="$4"

  local sqfs="$out/rootfs.squashfs"
  # bs/skip in blocks would be faster but the offset is not block-aligned;
  # iflag=skip_bytes keeps it exact without a byte-at-a-time copy.
  dd if="$img" of="$sqfs" bs=1M iflag=skip_bytes,count_bytes \
     skip="$offset" count="$length" status=none
  c_ok "carved $(stat -c %s "$sqfs") bytes -> $sqfs"

  rm -rf "$out/squashfs-root"

  # unsquashfs exits 2 when it cannot create device nodes or set ownership,
  # which is expected as a normal user and does not mean extraction failed.
  # Treat "the tree exists and has files" as the success condition instead.
  local log="$out/extract.log"
  if unsquashfs -d "$out/squashfs-root" "$sqfs" >"$log" 2>&1; then
    c_ok "unsquashfs: clean"
  elif [ -d "$out/squashfs-root" ] && [ -n "$(ls -A "$out/squashfs-root")" ]; then
    c_warn "unsquashfs returned non-zero but produced a tree (device nodes and"
    c_warn "ownership need root; file contents and modes are intact)"
  else
    # Realtek sometimes ships LZMA SquashFS that stock unsquashfs rejects.
    c_warn "unsquashfs failed; retrying with sasquatch"
    if ! sasquatch -d "$out/squashfs-root" "$sqfs" >>"$log" 2>&1 \
       && [ ! -d "$out/squashfs-root" ]; then
      c_err "both unsquashfs and sasquatch failed — see $log"
      return 1
    fi
  fi

  local files dirs links
  files=$(find "$out/squashfs-root" -type f | wc -l)
  dirs=$(find "$out/squashfs-root" -type d | wc -l)
  links=$(find "$out/squashfs-root" -type l | wc -l)
  c_ok "extracted: $files files, $dirs dirs, $links symlinks"

  # Symlinks are load-bearing for this analysis; if none survived, the target
  # filesystem cannot represent them and every later conclusion is suspect.
  if [ "$links" -eq 0 ]; then
    c_err "no symlinks in the extracted tree — is \$FWRE_WORK on a filesystem"
    c_err "that cannot represent them? Findings would be wrong; stopping."
    return 1
  fi
}

# ---------------------------------------------------------------------------
# Raw flash dump read off the device (W02 Day 4).
#
# A flash image is not a vendor container: there is no r6cr header in front of
# the root filesystem, because the boot loader mounts it as an MTD partition and
# a squashfs has to begin exactly on the partition boundary. So the offset comes
# from `fwrecon flashdump` instead, which knows it from the console session that
# read the device on 2026-08-15.
#
# The refusal below is the point of routing this through the checker at all: a
# dump whose hard checks failed must not become a filesystem that later analysis
# quotes as if it were the device.
# ---------------------------------------------------------------------------
unpack_flash() {
  local img="$1" label="${2:-unit-2018}"
  local out="$EX/$label"

  echo
  echo "--- $label (raw flash: $(basename "$img")) ------------------------"
  [ -f "$img" ] || { c_err "missing $img"; return 1; }
  mkdir -p "$out"

  local meta verdict offset length compression
  if ! meta="$("$PY" -m fwrecon flashdump "$img" --format json)"; then
    c_err "fwrecon flashdump reported hard-check failures for $img"
    c_err "refusing to extract: see the checker's output above"
    return 1
  fi
  verdict="$(jq -r '.self_check' <<<"$meta")"
  [ "$verdict" = "OK" ] || { c_err "self_check=$verdict — not extracting"; return 1; }

  offset="$(jq -r '.squashfs.offset' <<<"$meta")"
  length="$(jq -r '.squashfs.bytes_used' <<<"$meta")"
  compression="$(jq -r '.squashfs.compression' <<<"$meta")"
  [ "$offset" != "null" ] || { c_err "no SquashFS located in $img"; return 1; }
  c_ok "rootfs at flash offset $offset ($length bytes, $compression-compressed)"

  carve_and_extract "$img" "$out" "$offset" "$length"
}

usage() {
  cat <<'EOF'
usage:
  unpack-firmware.sh                       # both vendor images
  unpack-firmware.sh --flash <image.bin> [--label NAME]
                                           # a raw SPI flash dump off the device
EOF
}

main() {
  local flash="" label="unit-2018"
  while [ $# -gt 0 ]; do
    case "$1" in
      --flash) flash="$2"; shift 2 ;;
      --label) label="$2"; shift 2 ;;
      -h|--help) usage; exit 0 ;;
      *) c_err "unknown option: $1"; usage; exit 2 ;;
    esac
  done

  local rc=0
  if [ -n "$flash" ]; then
    unpack_flash "$flash" "$label" || rc=1
  else
    for entry in "${IMAGES[@]}"; do
      unpack_one ${entry} || rc=1
    done
  fi

  echo
  [ "$rc" -eq 0 ] && c_ok "unpacked into $EX" || c_err "some images failed"
  return "$rc"
}

main "$@"
