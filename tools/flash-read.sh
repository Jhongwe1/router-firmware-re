#!/usr/bin/env bash
#
# flash-read.sh — read the SPI NOR off my own unit through a CH341A, and refuse
# to call the result evidence until it has survived more than one check.
#
# Why this exists rather than "just run flashrom -r"
# -------------------------------------------------
# The week plan's acceptance criterion is "read twice, the two hashes must
# match". That is weaker than it sounds. Two reads through the *same* seating of
# the same clip share every failure mode they have: a lifted leg, a line the SoC
# is holding, a programmer driving 5 V into a 3.3 V part. All of those produce a
# stable, repeatable, well-formed, wrong answer — which is the failure mode this
# project keeps catching (PROGRESS.md § Two tooling bugs, § Instrument work).
#
# So this script separates the two questions the plan conflates:
#
#   is the read REPEATABLE?  -> N reads in one seating, hashes compared here
#   is the read CORRECT?     -> not answerable by the reader. Four other things
#                               answer it, and none of them is flashrom:
#                                 1. the JEDEC ID the silicon reports (the part
#                                    name on the package is NOT a second source
#                                    for it - notes/hardware-inspection.md §1)
#                                 2. a second seating of the clip (run again
#                                    with --label seat-b, then `compare`)
#                                 3. the boot loader's own FLR path, which
#                                    reaches the same die through the SoC
#                                    instead of through the clip
#                                 4. the structure inside the image
#                                    (tools/check-flash-dump.py)
#
# This script does 1 and 2 and stops. It never writes to the chip: there is no
# code path here that passes -w, -E or -v to flashrom, on purpose.
#
# Usage:
#   ./tools/flash-read.sh probe                       # identify only, no read
#   ./tools/flash-read.sh read --label seat-a --expect-id 1c7016
#   ./tools/flash-read.sh read --label seat-b --expect-id 1c7016
#   ./tools/flash-read.sh compare <file> <file> ...   # across seatings
#
# Options for `read`:
#   --label L       names this seating of the clip     (default: seat-a)
#   --reads N       reads to take in this seating      (default: 2)
#   --expect-id HEX predicted JEDEC id, e.g. 1c7016    (default: unpinned)
#   --expect-size N predicted size in bytes            (default: 4194304)
#   --chip NAME     force flashrom's chip selection    (default: probe)
#   --yes           skip the "is the router unplugged" prompt
#   --no-record     do not touch dumps/MANIFEST.json
#
# Write the prediction down BEFORE the measurement. --expect-id turns this from
# "look what it said" into a test that can fail, which is the only kind worth
# running - same reason W02 Day 1's date-code prediction was committed before
# the console came up.
#
# Environment:
#   FWRE_WORK  artefact root. Defaults to ~/fwre-work. Raw dumps NEVER go in the
#              repository: they are vendor firmware, and they carry this unit's
#              MACs, PSK and admin credentials. See dumps/README.md.
#
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${FWRE_WORK:-$HOME/fwre-work}"
DEST="$WORK/dumps"
MANIFEST="$REPO/dumps/MANIFEST.json"
PROGRAMMER="ch341a_spi"

c_ok()   { printf '\033[32m  ok  \033[0m %s\n' "$*"; }
c_run()  { printf '\033[36m ==>  \033[0m %s\n' "$*"; }
c_warn() { printf '\033[33m warn \033[0m %s\n' "$*"; }
c_err()  { printf '\033[31m FAIL \033[0m %s\n' "$*" >&2; }
die()    { c_err "$*"; exit 1; }

# shellcheck source=tools/lib/require-linux-workspace.sh
. "$REPO/tools/lib/require-linux-workspace.sh"

# ---------------------------------------------------------------------------
# flashrom needs USB access. Running the whole script as root would leave
# root-owned artefacts in $FWRE_WORK, so only the programmer call is elevated.
# ---------------------------------------------------------------------------
SUDO=()
[ "$(id -u)" -eq 0 ] || SUDO=(sudo)

flashrom_ro() {
  # Every invocation of flashrom in this file goes through here. Nothing that
  # modifies the chip can be reached from this function.
  "${SUDO[@]}" flashrom -p "$PROGRAMMER" "$@"
}

need() { command -v "$1" >/dev/null || die "$1 is required ($2)"; }

preflight() {
  need flashrom "apt install flashrom"
  need jq       "apt install jq"
  need sha256sum "coreutils"
  mkdir -p "$DEST"

  if command -v lsusb >/dev/null; then
    if lsusb | grep -qi '1a86:5512'; then
      c_ok "CH341A present on the USB bus (1a86:5512)"
    else
      c_err "no 1a86:5512 on the USB bus."
      c_err "On WSL the device has to be attached from Windows first:"
      c_err "    usbipd list"
      c_err "    usbipd bind   --busid <id>     (administrator, once per device)"
      c_err "    usbipd attach --wsl --busid <id>   (every replug)"
      exit 2
    fi
  else
    c_warn "lsusb not installed - cannot confirm the programmer is attached"
  fi
}

# ---------------------------------------------------------------------------
# probe: identify the part from what the silicon reports, not from its package
# ---------------------------------------------------------------------------
PROBE_LOG=""
JEDEC_ID=""
CHIP_NAME=""
FLASHROM_VER=""

probe() {
  local expect_id="${1:-}"
  local stamp
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  PROBE_LOG="$DEST/flash-probe-$stamp.log"

  c_run "probing (no read, no write)"
  # A failed probe is informative, so capture the log either way.
  flashrom_ro -V >"$PROBE_LOG" 2>&1 || true

  FLASHROM_VER="$(grep -m1 -oE 'flashrom [0-9][^ ,]*' "$PROBE_LOG" || true)"
  CHIP_NAME="$(grep -m1 -oE 'Found [^\n]*flash chip "[^"]+"' "$PROBE_LOG" \
               | sed -E 's/.*"([^"]+)".*/\1/' || true)"

  # RDID is re-issued for every candidate in flashrom's table, so a healthy
  # probe prints the same three bytes dozens of times. More than one distinct
  # value means the bus is unstable - that is a contact problem, not a finding.
  local ids
  ids="$(grep -oE 'RDID returned 0x[0-9a-f]{2} 0x[0-9a-f]{2} 0x[0-9a-f]{2}' "$PROBE_LOG" \
         | sed -E 's/RDID returned 0x([0-9a-f]{2}) 0x([0-9a-f]{2}) 0x([0-9a-f]{2})/\1\2\3/' \
         | sort -u || true)"

  if [ -z "$ids" ]; then
    c_err "no JEDEC id came back. The chip is not answering."
    c_err "  - router unplugged? the clip cannot power the whole board reliably"
    c_err "  - pin 1 of the clip on pin 1 of U19? (the dot on the package)"
    c_err "  - SOP-8 comes in 150 mil and 208 mil; the kit clip is often narrow"
    c_err "log: $PROBE_LOG"
    return 1
  fi

  if [ "$(printf '%s\n' "$ids" | wc -l)" -gt 1 ]; then
    c_err "the chip returned MORE THAN ONE id across probes:"
    printf '%s\n' "$ids" | sed 's/^/         0x/' >&2
    c_err "that is an unstable contact. Re-seat the clip; do not read yet."
    return 1
  fi

  JEDEC_ID="$ids"
  c_ok "JEDEC id  0x$JEDEC_ID   (manufacturer 0x${JEDEC_ID:0:2}, device 0x${JEDEC_ID:2:4})"
  [ -n "$CHIP_NAME" ]    && c_ok "flashrom calls it: $CHIP_NAME"
  [ -n "$FLASHROM_VER" ] && c_ok "$FLASHROM_VER"

  # The third RDID byte is log2(bytes) by convention for this class of part.
  # Convention, not standard - which is why it is reported, not asserted.
  local cap="${JEDEC_ID:4:2}" declared
  declared="$(( 1 << 0x$cap ))"
  c_ok "third id byte 0x$cap -> 2^$((0x$cap)) = $declared bytes, if the log2 convention holds"

  if [ -n "$expect_id" ]; then
    if [ "$(printf '%s' "$expect_id" | tr 'A-Z' 'a-z')" = "$JEDEC_ID" ]; then
      c_ok "matches the prediction (0x$expect_id)"
    else
      c_err "PREDICTION MISSED: expected 0x$expect_id, silicon says 0x$JEDEC_ID"
      c_err "Do not overwrite the prediction. A missed prediction is a result."
      return 1
    fi
  else
    c_warn "no --expect-id given; this run observes, it does not test"
  fi

  if grep -qi 'sfdp' "$PROBE_LOG"; then
    c_ok "SFDP tables were parsed - see $PROBE_LOG (a density source that owes"
    c_ok "     nothing to the part name or to flashrom's table)"
  else
    c_warn "no SFDP in the log: this part predates it, or does not implement it."
    c_warn "     Negative result - record it, do not go looking for it twice."
  fi
  return 0
}

# ---------------------------------------------------------------------------
# screening checks. These cannot prove a dump is right; they catch the three
# ways it is obviously wrong, while the clip is still on and re-reading is cheap.
# ---------------------------------------------------------------------------
screen_image() {
  local f="$1" expect_size="$2" rc=0 size content half

  size="$(stat -c %s "$f")"
  if [ "$size" = "$expect_size" ]; then
    c_ok "size      $size bytes"
  else
    c_err "size      $size bytes, expected $expect_size"
    rc=1
  fi

  # An entirely 0x00/0xFF image is what a clip that is not making contact
  # produces, and it is a perfectly well-formed file.
  content="$( { LC_ALL=C tr -d '\000\377' <"$f" || true; } | wc -c)"
  if [ "$content" -eq 0 ]; then
    c_err "the image is nothing but 0x00 and 0xFF - the clip is not reading"
    rc=1
  else
    c_ok "content   $content bytes are neither 0x00 nor 0xFF"
  fi

  # The published specification for this device says 2 MB. If the part really
  # were 2 MB, addresses above it would alias and the halves would be equal.
  half=$((size / 2))
  if cmp -s <(head -c "$half" "$f") <(tail -c "$half" "$f"); then
    c_err "the two halves are identical - this reads like a $((half / 1024 / 1024)) MiB part aliasing,"
    c_err "which would overturn the 4 MiB finding. Check the programmer first."
    rc=1
  else
    c_ok "halves    differ - the upper half is not an alias of the lower"
  fi

  return "$rc"
}

record() {
  local file="$1" size="$2" sha="$3" second="$4" reads="$5" label="$6"
  local entry tmp
  entry="$(jq -n \
    --arg file "$(basename "$file")" \
    --arg taken "$(date -u +%Y-%m-%d)" \
    --argjson bytes "$size" \
    --arg sha256 "$sha" \
    --arg sha256_second_read "$second" \
    --argjson reads_in_this_seating "$reads" \
    --arg seating "$label" \
    --arg interface "CH341A ($PROGRAMMER) + SOIC-8 clip, in circuit, router unplugged" \
    --arg jedec_id "${JEDEC_ID:-unknown}" \
    --arg chip_name "${CHIP_NAME:-unknown}" \
    --arg flashrom "${FLASHROM_VER:-unknown}" \
    '{file:$file, kind:"spi-flash-full", taken:$taken, bytes:$bytes,
      sha256:$sha256, sha256_second_read:$sha256_second_read,
      reads_in_this_seating:$reads_in_this_seating, seating:$seating,
      interface:$interface, jedec_id:$jedec_id, chip_name:$chip_name,
      flashrom:$flashrom,
      contains_unit_identifiers:true,
      not_committed_because:[
        "vendor firmware, which this project does not redistribute"
      ],
      disclosure_policy:"per field, not per region - see dumps/MANIFEST.json and notes/compcs-decode.md",
      recorded_by:"tools/flash-read.sh"}')"

  tmp="$(mktemp)"
  jq --argjson e "$entry" \
     '.reads |= ((map(select(.file != $e.file))) + [$e])
      | .not_yet_taken |= map(select(.file != $e.file))' \
     "$MANIFEST" >"$tmp"
  mv "$tmp" "$MANIFEST"
  c_ok "recorded in dumps/MANIFEST.json (git diff it before committing)"
}

cmd_read() {
  local label="seat-a" reads=2 expect_id="" expect_size=4194304 chip="" assume_yes=0 do_record=1
  while [ $# -gt 0 ]; do
    case "$1" in
      --label)       label="$2";       shift 2 ;;
      --reads)       reads="$2";       shift 2 ;;
      --expect-id)   expect_id="$2";   shift 2 ;;
      --expect-size) expect_size="$2"; shift 2 ;;
      --chip)        chip="$2";        shift 2 ;;
      --yes)         assume_yes=1;     shift ;;
      --no-record)   do_record=0;      shift ;;
      *) die "unknown option: $1" ;;
    esac
  done

  preflight

  if [ "$assume_yes" -eq 0 ]; then
    echo
    echo "  Before the clip goes on:"
    echo "    - router power adapter UNPLUGGED, not just switched off"
    echo "    - the USB-TTL serial adapter unplugged too (it is a second ground"
    echo "      and a second supply into the same board)"
    echo "    - the programmer measured: 3.3 V on the socket, not 5 V"
    echo
    read -r -p "  All three true? [y/N] " ans
    case "$ans" in [yY]*) ;; *) die "stopped at the operator's own check" ;; esac
  fi

  probe "$expect_id" || die "identification failed - not reading a chip that will not say what it is"

  local args=(-r) f files=() hashes=() sha i
  [ -n "$chip" ] && args=(-c "$chip" -r)

  for i in $(seq 1 "$reads"); do
    f="$DEST/flash-n150rt-$label-$i.bin"
    c_run "read $i/$reads -> $f"
    flashrom_ro "${args[@]}" "$f" >>"$PROBE_LOG" 2>&1 \
      || die "flashrom read failed - see $PROBE_LOG"
    [ "$(id -u)" -eq 0 ] || "${SUDO[@]}" chown "$(id -u):$(id -g)" "$f"
    sha="$(sha256sum "$f" | cut -d' ' -f1)"
    c_ok "sha256    $sha"
    files+=("$f")
    hashes+=("$sha")
  done

  echo
  c_run "screening ${files[0]}"
  screen_image "${files[0]}" "$expect_size" || die "the image failed screening - do not unclip yet, re-seat and read again"

  echo
  local distinct
  distinct="$(printf '%s\n' "${hashes[@]}" | sort -u | wc -l)"
  if [ "$distinct" -eq 1 ]; then
    c_ok "all $reads reads in seating '$label' agree"
  else
    c_err "the $reads reads DISAGREE - $distinct distinct hashes."
    c_err "that is a contact problem. Clean the legs, re-seat, read again."
    exit 1
  fi

  [ "$do_record" -eq 1 ] && record "${files[0]}" "$(stat -c %s "${files[0]}")" \
      "${hashes[0]}" "${hashes[1]:-none}" "$reads" "$label"

  echo
  c_warn "REPEATABLE is not CORRECT. This seating agrees with itself and nothing else."
  echo   "        next:  unclip, re-seat, and run again with --label seat-b"
  echo   "        then:  ./tools/flash-read.sh compare $DEST/flash-n150rt-*-1.bin"
  echo   "        then:  python -m fwrecon flashdump ${files[0]}   (structural check"
  echo   "               against the offsets the boot loader's FLR path read"
  echo   "               independently on 2026-08-15 - notes/flash-layout.md)"
}

cmd_compare() {
  [ $# -ge 2 ] || die "compare needs at least two files"
  local f sha first="" rc=0
  for f in "$@"; do
    [ -f "$f" ] || die "no such file: $f"
    sha="$(sha256sum "$f" | cut -d' ' -f1)"
    printf '  %s  %s\n' "$sha" "$(basename "$f")"
    [ -z "$first" ] && first="$sha"
    [ "$sha" = "$first" ] || rc=1
  done
  echo
  if [ "$rc" -eq 0 ]; then
    c_ok "identical across every file listed"
    c_ok "if those came from different seatings of the clip, the read is now"
    c_ok "independent of how the clip sat - which two reads in one seating never showed"
  else
    c_err "the files DIFFER."
    c_err "Do not average them and do not pick one. Find out which is wrong:"
    c_err "  cmp -l <a> <b> | wc -l     how many bytes, and are they clustered?"
    c_err "A handful of scattered bytes is a marginal contact; a whole region is"
    c_err "an address-line problem. Either way the dump is not evidence yet."
  fi
  return "$rc"
}

main() {
  local sub="${1:-}"
  [ $# -gt 0 ] && shift
  case "$sub" in
    probe)   preflight; probe "${1:-}" ;;
    read)    cmd_read "$@" ;;
    compare) cmd_compare "$@" ;;
    *) sed -n '/^# Usage:/,/^#$/p' "${BASH_SOURCE[0]}" | sed 's/^#\s\?//'
       exit 2 ;;
  esac
}

# Sourceable, so that tools/test-flash-tools.sh can drive `screen` against
# synthetic images without a programmer attached. A screening check nobody can
# run without the hardware is a check that gets written once and never tested.
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  main "$@"
fi
