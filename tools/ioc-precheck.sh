#!/usr/bin/env bash
# The pre-engagement check: has anything about this unit's configuration changed
# since the last session, and does the vendor's own checksum still pass?
#
# G3.75's third box. It exists because this model is named in public botnet
# tooling, and "the device looks fine" is not a check -- a number that was
# written down before the session and compared afterwards is.
#
# What it compares
# ----------------
# `COMPCS` at 0xC000 is the live configuration; `COMPDS` at 0x8000 is the
# factory default, written at manufacture. Both are LZSS-compressed and both
# carry an 8-bit payload checksum that `libapmib` itself verifies, so this
# reports three things the decoder cannot fake:
#
#   checksum_ok        libapmib's own checksum over the payload
#   ring_fill_agrees   decoding twice with different LZSS window fills agrees,
#                      so the result never depended on window bytes no literal
#                      wrote
#   verdict            the decoder's own opinion of its work
#
# and then the number that matters: how many of the shared entries differ.
#
# The expected value is NOT a constant
# ------------------------------------
# It was 4 of 343 up to 2026-08-17. That afternoon's POST round rewrote COMPDS
# from COMPCS, so it is 0 of 343 now. The check is "the same number the last
# session recorded", not "4" -- and a difference this script cannot explain is
# the thing to stop on. BENCH-LOG.md carries the number for each session.
#
#   bash tools/ioc-precheck.sh <64KiB-or-4MiB-image>
#
set -uo pipefail

cd "$(dirname "$0")/.." || exit 1

SNAP="${1:-}"
if [ -z "$SNAP" ] || [ ! -f "$SNAP" ]; then
  echo "usage: bash tools/ioc-precheck.sh <image>" >&2
  echo "  a 64 KiB config-region snapshot (RUNBOOK 8.12.3) or a full 4 MiB dump" >&2
  exit 2
fi

FWRE_WORK="${FWRE_WORK:-$HOME/fwre-work}"
PY="${FWRE_PY:-$FWRE_WORK/venv/bin/python}"
LIB="${FWRE_MIB:-$FWRE_WORK/extracted/unit-2018/squashfs-root/lib/libapmib.so}"

[ -x "$PY" ] || { echo "no analysis venv at $PY — run: make venv" >&2; exit 2; }
[ -f "$LIB" ] || { echo "no libapmib.so at $LIB — the MIB names come from it" >&2; exit 2; }

sz=$(stat -c %s "$SNAP")
if [ "$sz" -lt 65536 ]; then
  echo "$SNAP is $sz bytes; the configuration regions end at 0x10000" >&2
  exit 2
fi

OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT

for off in 0xC000 0x8000; do
  if ! "$PY" -m fwrecon compcs "$SNAP" --offset "$off" --mib "$LIB" \
        --disclosure protect -f json -o "$OUT/cs-$off.json" >/dev/null; then
    echo "  FAIL  fwrecon refused to decode $off — read its message above" >&2
    exit 1
  fi
done

"$PY" - "$OUT" <<'PYEOF'
import json
import sys

out = sys.argv[1]
cs = json.load(open(f"{out}/cs-0xC000.json", encoding="utf-8"))
ds = json.load(open(f"{out}/cs-0x8000.json", encoding="utf-8"))

bad = 0
for tag, d in (("COMPCS", cs), ("COMPDS", ds)):
    print(f"{tag}: checksum_ok={d.get('checksum_ok')} "
          f"verdict={d.get('verdict')} "
          f"ring_fill_agrees={d.get('ring_fill_agrees')} "
          f"entries={len(d.get('entries', []))}")
    # Each of these is the vendor's code or the decoder's own control saying the
    # decode is not trustworthy. A count computed from an untrustworthy decode
    # would look exactly like a count computed from a good one.
    if not d.get("checksum_ok"):
        print(f"  FAIL  {tag}: libapmib's own payload checksum does not pass. "
              "The device would reject this blob and so should this script",
              file=sys.stderr)
        bad += 1
    if not d.get("ring_fill_agrees"):
        print(f"  FAIL  {tag}: decoding with two different LZSS window fills "
              "disagrees, so the result depended on bytes no literal wrote",
              file=sys.stderr)
        bad += 1
    if d.get("verdict") != "consistent":
        print(f"  FAIL  {tag}: verdict is {d.get('verdict')!r}", file=sys.stderr)
        bad += 1

a = {e["name"]: e.get("value") for e in cs["entries"]}
b = {e["name"]: e.get("value") for e in ds["entries"]}
common = sorted(set(a) & set(b))
diff = [n for n in common if a[n] != b[n]]

print()
print(f"common entries: {len(common)}")
print(f"differing     : {len(diff)}"
      + (f"  -> {' · '.join(diff)}" if diff else ""))
only_cs, only_ds = sorted(set(a) - set(b)), sorted(set(b) - set(a))
if only_cs or only_ds:
    print(f"only in COMPCS: {only_cs}")
    print(f"only in COMPDS: {only_ds}")

print()
print("Compare this against the number the LAST session recorded in BENCH-LOG.md.")
print("It is not a constant: it was 4 of 343 until 2026-08-17, and 0 of 343 after")
print("that afternoon's POST round rewrote COMPDS. A difference you cannot")
print("account for is where you stop.")
sys.exit(1 if bad else 0)
PYEOF
