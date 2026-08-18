#!/usr/bin/env bash
# Guard suite for tools/config-diff.py.
#
# The tool answers P8-23 by comparing two paths that are easy to make agree by
# accident: a byte diff of the flash image and a decode of the same region. Both
# of its refusals exist because a run that cannot produce them is not a
# measurement --
#
#   * "no field changed" is what a decoder pointed at the wrong region looks
#     like, and it is indistinguishable from a clean run unless something says
#     so;
#   * "more than one field changed" is P8-23's own refutation condition, and it
#     has to name the extras, because which extras moved IS the diagnosis.
#
# So the comparison is a function, and this suite drives it directly. Nothing
# below needs root, a chroot, the flash dump or fwrecon: the cases that need
# those are the tool's own end-to-end run, and CI is not root.
#
#   bash tools/test-config-diff.sh
set -uo pipefail

cd "$(dirname "$0")/.." || { echo "  FAIL  cannot cd to the repository root"; exit 1; }
TOOL=tools/config-diff.py
PY="${PYTHON:-python3}"

pass=0; fail=0
ok()  { echo "  ok    $1"; pass=$((pass + 1)); }
bad() { echo "  FAIL  $1"; fail=$((fail + 1)); }

# run_case <label> <python expression printing PASS or a reason> ...
check() {
  local label="$1" script="$2" out
  out="$("$PY" - <<PYEOF 2>&1
import importlib.util, sys
spec = importlib.util.spec_from_file_location("cfgdiff", "$TOOL")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
$script
PYEOF
)"
  if [ "$out" = "PASS" ]; then ok "$label"; else bad "$label -- $out"; fi
}

echo "tools/config-diff.py -- the comparison, driven directly"

# 1. the clean case: exactly the field asked for, and nothing else
check "one field changed and it is the right one" '
b = [{"name": "A", "offset": 91, "length": 4, "raw": "000001e0"},
     {"name": "B", "offset": 99, "length": 4, "raw": "00000001"}]
a = [{"name": "A", "offset": 91, "length": 4, "raw": "000010e1"},
     {"name": "B", "offset": 99, "length": 4, "raw": "00000001"}]
r = m.compare(b, a, "A")
print("PASS" if not r["problems"] and [c["name"] for c in r["changed"]] == ["A"]
      else "problems=%r changed=%r" % (r["problems"], r["changed"]))
'

# 2. nothing changed -- the shape of a decoder pointed at the wrong region
check "no field changed is refused" '
b = [{"name": "A", "offset": 91, "length": 4, "raw": "000001e0"}]
r = m.compare(b, list(b), "A")
print("PASS" if any("no field change" in p for p in r["problems"])
      else "problems=%r" % (r["problems"],))
'

# 3. the write spilled -- P8-23 refuted, and the extras must be named
check "a second changed field is refused, and named" '
b = [{"name": "A", "offset": 91, "length": 4, "raw": "000001e0"},
     {"name": "B", "offset": 99, "length": 4, "raw": "00000001"}]
a = [{"name": "A", "offset": 91, "length": 4, "raw": "000010e1"},
     {"name": "B", "offset": 99, "length": 4, "raw": "000000ff"}]
r = m.compare(b, a, "A")
joined = " ".join(r["problems"])
print("PASS" if "not localised" in joined and "B" in joined
      else "problems=%r" % (r["problems"],))
'

# 4. the wrong field changed and the named one did not
check "the wrong field changing is refused" '
b = [{"name": "A", "offset": 91, "length": 4, "raw": "000001e0"},
     {"name": "B", "offset": 99, "length": 4, "raw": "00000001"}]
a = [{"name": "A", "offset": 91, "length": 4, "raw": "000001e0"},
     {"name": "B", "offset": 99, "length": 4, "raw": "000000ff"}]
r = m.compare(b, a, "A")
print("PASS" if any("not localised" in p for p in r["problems"])
      else "problems=%r" % (r["problems"],))
'

# 5. a differential across two different field sets is not a differential
check "a moving field set is refused" '
b = [{"name": "A", "offset": 91, "length": 4, "raw": "000001e0"}]
a = [{"name": "A", "offset": 91, "length": 4, "raw": "000010e1"},
     {"name": "C", "offset": 107, "length": 1, "raw": "00"}]
r = m.compare(b, a, "A")
print("PASS" if any("field set itself moved" in p for p in r["problems"])
      else "problems=%r" % (r["problems"],))
'

echo
echo "tools/config-diff.py -- the two coordinate systems are labelled, not compared"

# 6. a byte inside the compressed payload must be marked as not comparable.
#    This is the one that would have caught reading 0xC060 as "field offset 96".
check "a byte in the compressed payload is marked incomparable" '
d = m.classify_flash_offsets(
      [{"offset": "0x00c060", "before": "0x01", "after": "0x10"}],
      0xC000, 7478)
print("PASS" if "NOT comparable" in d[0]["where"] else "where=%r" % d[0]["where"])
'

# 7. and a byte past the compressed data is placed relative to its end
check "a byte past the payload is placed relative to its end" '
d = m.classify_flash_offsets(
      [{"offset": "0x00dd41", "before": "0xa8", "after": "0x98"}],
      0xC000, 7478)
print("PASS" if "past its end" in d[0]["where"] else "where=%r" % d[0]["where"])
'

# 8. with no compressed length known it must say so rather than guess
check "an unknown compressed length is stated, not assumed" '
d = m.classify_flash_offsets(
      [{"offset": "0x00c060", "before": "0x01", "after": "0x10"}], 0xC000, None)
print("PASS" if "unknown" in d[0]["where"] else "where=%r" % d[0]["where"])
'

echo
echo "tools/config-diff.py -- refusals at the command line"

out="$("$PY" "$TOOL" --mib DHCP_LEASE_TIME --to 4321 2>&1)"
if [[ "$out" == *"--out"* ]]; then ok "refuses without --out"; else
  bad "missing --out was not named: $out"; fi

out="$("$PY" "$TOOL" --profile not-a-profile --mib X --to 1 --out /dev/null 2>&1)"
if [[ "$out" == *"invalid choice"* ]]; then ok "refuses an unknown profile"; else
  bad "unknown profile was not refused: $out"; fi

if [ "$(id -u)" -ne 0 ]; then
  out="$("$PY" "$TOOL" --mib X --to 1 --out /dev/null 2>&1)"
  if [[ "$out" == *"needs root"* ]]; then ok "refuses to run unprivileged"; else
    bad "running as a normal user was not refused: $out"; fi
fi

echo
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ]
