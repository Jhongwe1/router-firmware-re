#!/usr/bin/env bash
# Guard suite for tools/device-liveness.py.
#
# The tool exists because four bench sessions ran on a router whose WAN had been
# dead since 2026-08-17 and nothing said so. A health check that cannot fail
# would repeat that exactly: it would print a reassuring line every session and
# mean nothing. So every refusal below is driven directly --
#
#   * an empty decode is what a decoder pointed at the wrong offset looks like,
#     and it must not read as a healthy device;
#   * a field the tool asserts on but cannot find is a tooling failure, not a
#     pass;
#   * a baseline that loaded nothing must not turn the drift half into a silent
#     "nothing drifted";
#   * something that answers on port 80 without answering with a configuration
#     is not evidence the device is fine.
#
# `assess()` is a pure function over decoded entries, so nothing below needs the
# device, the network, fwrecon, the flash dump or root -- which is the point:
# CI has none of them and this suite still proves the tool can say no.
#
#   bash tools/test-device-liveness.sh
set -uo pipefail

cd "$(dirname "$0")/.." || { echo "  FAIL  cannot cd to the repository root"; exit 1; }
TOOL=tools/device-liveness.py
PY="${PYTHON:-python3}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
ok()  { echo "  ok    $1"; pass=$((pass + 1)); }
bad() { echo "  FAIL  $1"; fail=$((fail + 1)); }

# check <label> <python body printing PASS or a reason>
check() {
  local label="$1" script="$2" out
  out="$("$PY" - <<PYEOF 2>&1
import importlib.util
spec = importlib.util.spec_from_file_location("liveness", "$TOOL")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def entries(**kw):
    base = {"DHCP_MTU_SIZE": "1500", "WAN_DHCP": "1", "OP_MODE": "0",
            "IP_ADDR": "10.1.1.1", "USER_PASSWORD": "admin"}
    base.update(kw)
    return [{"name": k, "value": v} for k, v in base.items()]

$script
PYEOF
)"
  if [ "$out" = "PASS" ]; then ok "$label"; else bad "$label -- $out"; fi
}

# cli <label> <expected-exit> <args...>
cli() {
  local label="$1" want="$2"; shift 2
  local out rc
  out="$("$PY" "$TOOL" "$@" 2>&1)"; rc=$?
  if [ "$rc" = "$want" ]; then ok "$label (exit $rc)"; else
    bad "$label -- expected exit $want, got $rc: $(echo "$out" | head -2 | tr '\n' ' ')"
  fi
}

echo "tools/device-liveness.py -- the judgement, driven directly"

check "a healthy configuration passes" '
r = m.assess(entries(), baseline=None)
print("PASS" if r["verdict"] == "OK" and not r["problems"] else repr(r["verdict"]) + repr(r["problems"]))
'

check "DHCP_MTU_SIZE=0 is BROKEN, and the check names the field" '
r = m.assess(entries(DHCP_MTU_SIZE="0"), baseline=None)
bad = [c for c in r["checks"] if not c["ok"]]
print("PASS" if r["verdict"] == "BROKEN" and [c["field"] for c in bad] == ["DHCP_MTU_SIZE"]
      else "verdict=%s bad=%r" % (r["verdict"], bad))
'

check "the failing check carries the sentence that says what breaks" '
r = m.assess(entries(DHCP_MTU_SIZE="0"), baseline=None)
c = [c for c in r["checks"] if not c["ok"]][0]
print("PASS" if "MTU" in c["breaks"] and len(c["breaks"]) > 40 else repr(c["breaks"]))
'

check "WAN_DHCP=0 is BROKEN" '
r = m.assess(entries(WAN_DHCP="0"), baseline=None)
print("PASS" if r["verdict"] == "BROKEN" else r["verdict"])
'

check "OP_MODE moved off gateway is BROKEN" '
r = m.assess(entries(OP_MODE="1"), baseline=None)
print("PASS" if r["verdict"] == "BROKEN" else r["verdict"])
'

check "the LAN address moving is BROKEN, not a timeout to debug" '
r = m.assess(entries(IP_ADDR="192.168.1.1"), baseline=None)
print("PASS" if r["verdict"] == "BROKEN" else r["verdict"])
'

check "an empty admin password is BROKEN (P2-11 cannot be measured on it)" '
r = m.assess(entries(USER_PASSWORD=""), baseline=None)
bad = [c for c in r["checks"] if not c["ok"]]
print("PASS" if r["verdict"] == "BROKEN" and [c["field"] for c in bad] == ["USER_PASSWORD"]
      else "verdict=%s bad=%r" % (r["verdict"], bad))
'

check "the password check never puts the password in its output" '
r = m.assess(entries(USER_PASSWORD="hunter2"), baseline=None)
print("PASS" if "hunter2" not in repr(r) else "the password leaked into the result")
'

check "no entries at all is UNUSABLE, not OK" '
r = m.assess([], baseline=None)
print("PASS" if r["verdict"] == "UNUSABLE" and r["problems"] else repr(r))
'

check "an asserted field that is absent is UNUSABLE, not a pass" '
e = [x for x in entries() if x["name"] != "DHCP_MTU_SIZE"]
r = m.assess(e, baseline=None)
print("PASS" if r["verdict"] == "UNUSABLE" and any("DHCP_MTU_SIZE" in p for p in r["problems"])
      else "verdict=%s problems=%r" % (r["verdict"], r["problems"]))
'

check "an absent password field is UNUSABLE, not assumed set" '
e = [x for x in entries() if x["name"] != "USER_PASSWORD"]
r = m.assess(e, baseline=None)
print("PASS" if r["verdict"] == "UNUSABLE" else "verdict=%s" % r["verdict"])
'

check "drift against the baseline is listed field by field" '
r = m.assess(entries(), baseline=[{"name": "DHCP_MTU_SIZE", "value": "1500"},
                                  {"name": "UPNP_ENABLED", "value": "1"}])
names = sorted(d["field"] for d in r["drifted"])
print("PASS" if "UPNP_ENABLED" in names else repr(r["drifted"]))
'

check "drift alone does not fail the device -- it is the other half" '
r = m.assess(entries(), baseline=[{"name": "UPNP_ENABLED", "value": "1"}])
print("PASS" if r["verdict"] == "OK" and r["drifted"] else "verdict=%s" % r["verdict"])
'

check "a baseline that decoded to nothing is reported, not silently empty" '
r = m.assess(entries(), baseline=[])
print("PASS" if any("baseline" in p for p in r["problems"]) else repr(r["problems"]))
'

check "a field present now and absent from the baseline counts as drift" '
r = m.assess(entries(), baseline=[{"name": "DHCP_MTU_SIZE", "value": "1500"}])
d = {x["field"]: (x["baseline"], x["now"]) for x in r["drifted"]}
print("PASS" if d.get("IP_ADDR") == (None, "10.1.1.1") else repr(d))
'

check "the 2026-08-17 damage, replayed: every field that moved is named" '
pristine = entries(UPNP_ENABLED="1", ALG_SIP_ENABLED="1")
now      = entries(DHCP_MTU_SIZE="0", UPNP_ENABLED="0", ALG_SIP_ENABLED="0")
r = m.assess(now, baseline=pristine)
names = sorted(d["field"] for d in r["drifted"])
print("PASS" if r["verdict"] == "BROKEN" and
      names == ["ALG_SIP_ENABLED", "DHCP_MTU_SIZE", "UPNP_ENABLED"]
      else "verdict=%s names=%r" % (r["verdict"], names))
'

# ---- the file-shaped refusals, at the command line ---------------------
printf 'COMPCS' > "$TMP/too-short.bin"
printf 'NOTCOMPCS and then some more bytes to be long enough' > "$TMP/wrong-magic.bin"

cli "a file that is not a configuration is refused" 2 \
    --from-file "$TMP/wrong-magic.bin" --no-baseline --quiet
cli "a truncated answer is refused, not read as healthy" 2 \
    --from-file "$TMP/too-short.bin" --offset 0x10 --no-baseline --quiet
cli "an unreachable device is 3 -- neither pass nor fail" 3 \
    --host 203.0.113.199 --timeout 1 --no-baseline --quiet

echo
echo "  $pass passed, $fail failed"
[ "$fail" = 0 ] || exit 1
