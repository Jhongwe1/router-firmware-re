#!/usr/bin/env bash
# What did this session change, and can you prove it was this session?
#
# The two 64 KiB snapshots taken either side of a round that writes are only
# useful if the difference between them can be attributed. This does that in
# two passes, and the first one matters more than it looks:
#
#   1. a raw byte comparison, which does not go through any decoder. Region
#      boundaries in the result are the check on the second pass: a decoder
#      misreading would not produce a difference that stops cleanly at 0x8000.
#   2. a field comparison through `fwrecon compcs`, naming what moved.
#
# It also prints the new COMPCS-vs-COMPDS number, because that is the frozen
# input to the next session's pre-check and it moves.
#
# On 2026-08-17 this reported something nobody had predicted: the POST round
# moved 19 fields in COMPCS and 23 in COMPDS -- the same 19 plus the four that
# had distinguished the two regions, each to COMPCS's value. An unauthenticated
# configuration write also rewrites the factory defaults.
#
#   bash tools/config-attrib.sh <before.bin> <after.bin>
#
set -uo pipefail

cd "$(dirname "$0")/.." || exit 1

PRE="${1:-}"; POST="${2:-}"
if [ -z "$PRE" ] || [ -z "$POST" ] || [ ! -f "$PRE" ] || [ ! -f "$POST" ]; then
  echo "usage: bash tools/config-attrib.sh <before.bin> <after.bin>" >&2
  exit 2
fi

FWRE_WORK="${FWRE_WORK:-$HOME/fwre-work}"
PY="${FWRE_PY:-$FWRE_WORK/venv/bin/python}"
LIB="${FWRE_MIB:-$FWRE_WORK/extracted/unit-2018/squashfs-root/lib/libapmib.so}"
[ -x "$PY" ] || { echo "no analysis venv at $PY — run: make venv" >&2; exit 2; }
[ -f "$LIB" ] || { echo "no libapmib.so at $LIB" >&2; exit 2; }

changed=$(cmp -l "$PRE" "$POST" 2>/dev/null | wc -l)
echo "raw: $changed of $(stat -c %s "$PRE") bytes differ"
echo
echo "=== where, without going through any decoder ==="
"$PY" - "$PRE" "$POST" <<'PYEOF'
import sys
a = open(sys.argv[1], "rb").read()
b = open(sys.argv[2], "rb").read()
REGIONS = [(0x0000, 0x6000, "boot loader"),
           (0x6000, 0x8000, "H601   hardware MIB (MAC + radio calibration)"),
           (0x8000, 0xC000, "COMPDS factory defaults"),
           (0xC000, 0x10000, "COMPCS live configuration")]
for lo, hi, name in REGIONS:
    d = [i for i in range(lo, min(hi, len(a), len(b))) if a[i] != b[i]]
    if d:
        print(f"  0x{lo:05x}-0x{hi:05x}  {name:<44} {len(d)} bytes "
              f"(0x{d[0]:05x}..0x{d[-1]:05x})")
    else:
        print(f"  0x{lo:05x}-0x{hi:05x}  {name:<44} UNCHANGED")
print()
print("  H601 changing is the one to stop on: this unit's MAC addresses and")
print("  radio calibration exist in no vendor image and no factory reset")
print("  restores them.")
PYEOF

OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT
for tag in pre post; do
  src="$PRE"; [ "$tag" = post ] && src="$POST"
  for off in 0xC000 0x8000; do
    "$PY" -m fwrecon compcs "$src" --offset "$off" --mib "$LIB" \
          --disclosure protect -f json -o "$OUT/$tag-$off.json" >/dev/null || exit 1
  done
done

echo
echo "=== which fields, and in which region ==="
"$PY" - "$OUT" <<'PYEOF'
import json
import sys

out = sys.argv[1]


def load(p):
    d = json.load(open(p, encoding="utf-8"))
    return {e["name"]: e.get("value") for e in d["entries"]}


csp, csq = load(f"{out}/pre-0xC000.json"), load(f"{out}/post-0xC000.json")
dsp, dsq = load(f"{out}/pre-0x8000.json"), load(f"{out}/post-0x8000.json")

cs_ch = sorted(n for n in csp if n in csq and csp[n] != csq[n])
ds_ch = sorted(n for n in dsp if n in dsq and dsp[n] != dsq[n])
print(f"  COMPCS (live)    : {len(cs_ch)} fields")
print(f"  COMPDS (defaults): {len(ds_ch)} fields")
extra = sorted(set(ds_ch) - set(cs_ch))
if extra:
    print(f"  only in COMPDS   : {extra}")
    print()
    print("  ** COMPDS moving is not a side effect. It is the factory-default")
    print("     region, and a write that reaches it means 'restore factory")
    print("     defaults' would restore whatever was last written. **")

# Values are printed only for fields whose names say they are flags or sizes.
# Anything else could be a per-unit identifier, and those do not go into a
# transcript that might be committed -- same rule as masking the PCB barcode.
SAFE = ("ENABLED", "DISABLED", "MODE", "SIZE", "ROUTE", "LOGIN", "PARAM")
print()
for n in sorted(set(cs_ch) | set(ds_ch)):
    if any(k in n for k in SAFE):
        print(f"  {n:<30} CS {str(csp.get(n))[:16]:<18} -> {str(csq.get(n))[:16]:<18}"
              f" | DS {str(dsp.get(n))[:12]:<14} -> {str(dsq.get(n))[:12]}")
    else:
        print(f"  {n:<30} (value withheld: may be a per-unit identifier)")

common = sorted(set(csq) & set(dsq))
now = [n for n in common if csq[n] != dsq[n]]
print()
print(f"  NEW BASELINE for the next pre-check: COMPCS vs COMPDS differ in "
      f"{len(now)} of {len(common)}")
if now:
    print(f"    {' · '.join(now)}")
print("  Record that number in BENCH-LOG.md. The next session compares against")
print("  it, not against a constant.")
PYEOF
