#!/usr/bin/env bash
# Guard suite for tools/rogue-dhcp.py.
#
# This tool hands out addresses, a default route and a DNS server to anything
# that asks. Started on the wrong interface it is not a failed test, it is
# somebody else's outage — so the refusal that names one interface and checks it
# is the load-bearing part, and it has to be provable without a wire.
#
# The option encoders are the other half. Option 33 and option 121 carry the
# same routes in different shapes, and getting either wrong produces a lease the
# device accepts and a route it never installs — a clean, quiet, wrong negative.
# So they are checked against hand-computed bytes.
#
# Nothing below needs root, a device, or a network: the pure functions are
# driven directly, and the one CLI case is the geteuid refusal, which CI can
# exercise precisely because CI is not root.
#
#   bash tools/test-rogue-dhcp.sh
set -uo pipefail

cd "$(dirname "$0")/.." || { echo "  FAIL  cannot cd to the repository root"; exit 1; }
TOOL=tools/rogue-dhcp.py
PY="${PYTHON:-python3}"

pass=0; fail=0
ok()  { echo "  ok    $1"; pass=$((pass + 1)); }
bad() { echo "  FAIL  $1"; fail=$((fail + 1)); }

check() {
  local label="$1" script="$2" out
  out="$("$PY" - <<PYEOF 2>&1
import importlib.util
spec = importlib.util.spec_from_file_location("rogue", "$TOOL")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
$script
PYEOF
)"
  if [ "$out" = "PASS" ]; then ok "$label"; else bad "$label -- $out"; fi
}

echo "tools/rogue-dhcp.py -- the encoders and the refusals, driven directly"

check "option 121 encodes a /16 as width + significant octets + gateway" '
got = m.encode_routes([("10.99.0.0/16", "192.168.77.66")], True).hex()
print("PASS" if got == "100a63c0a84d42" else got)
'

check "option 121 encodes a /24 with three octets, not four" '
got = m.encode_routes([("10.99.7.0/24", "192.168.77.66")], True).hex()
print("PASS" if got == "180a6307c0a84d42" else got)
'

check "option 121 encodes a default route as one byte of width" '
got = m.encode_routes([("0.0.0.0/0", "192.168.77.66")], True).hex()
print("PASS" if got == "00c0a84d42" else got)
'

check "option 33 encodes fixed 8-byte pairs and carries no mask" '
got = m.encode_routes([("10.99.0.0/16", "192.168.77.66")], False).hex()
print("PASS" if got == "0a630000c0a84d42" else got)
'

check "two routes encode back to back, not merged" '
r = [("10.99.0.0/16", "192.168.77.66"), ("172.16.0.0/12", "192.168.77.67")]
a = m.encode_routes(r, True).hex()
print("PASS" if a == "100a63c0a84d420cac10c0a84d43" else a)
'

check "same_subnet says yes inside the mask and no outside it" '
y = m.same_subnet("192.168.77.1", "192.168.77.100", "255.255.255.0")
n = m.same_subnet("192.168.77.1", "10.1.1.100", "255.255.255.0")
print("PASS" if (y and not n) else "y=%r n=%r" % (y, n))
'

check "the reply is a BOOTREPLY carrying the magic cookie and the right type" '
class A:
    offer="192.168.77.100"; server="192.168.77.1"; netmask="255.255.255.0"
    router=None; dns=None; domain=None; lease=600
raw = m.build_reply(m.ACK, 0x11223344, bytes.fromhex("aabbccddeeff"), A, [])
opts = m.parse_options(raw[240:])
print("PASS" if (raw[0] == 2 and raw[236:240] == m.MAGIC and opts[53] == b"\x05"
                 and opts[54] == m.ip2b("192.168.77.1")) else repr(raw[:8]))
'

check "the offered address lands in yiaddr where a client looks for it" '
class A:
    offer="192.168.77.100"; server="192.168.77.1"; netmask="255.255.255.0"
    router=None; dns=None; domain=None; lease=600
raw = m.build_reply(m.OFFER, 1, b"\x00"*6, A, [])
print("PASS" if m.b2ip(raw[16:20]) == "192.168.77.100" else m.b2ip(raw[16:20]))
'

check "route options only appear when routes were asked for" '
class A:
    offer="192.168.77.100"; server="192.168.77.1"; netmask="255.255.255.0"
    router=None; dns=None; domain=None; lease=600
bare = m.parse_options(m.build_reply(m.ACK, 1, b"\x00"*6, A, [])[240:])
with_ = m.parse_options(m.build_reply(m.ACK, 1, b"\x00"*6, A,
                                      [("10.99.0.0/16", "192.168.77.66")])[240:])
print("PASS" if (33 not in bare and 121 not in bare and 249 not in bare
                 and 33 in with_ and 121 in with_ and 249 in with_)
      else "bare=%r with=%r" % (sorted(bare), sorted(with_)))
'

check "parse_options stops at the end marker and skips padding" '
data = bytes([0, 0, 53, 1, 5, 54, 4, 192, 168, 77, 1, 255, 66, 66, 66])
o = m.parse_options(data)
print("PASS" if (o[53] == b"\x05" and o[54] == m.ip2b("192.168.77.1")
                 and 66 not in o) else repr(o))
'

# The CLI half. CI is not root, which is exactly what makes this case runnable:
# the tool must refuse before it opens a socket, not after.
out="$("$PY" "$TOOL" --iface lo --server 10.0.0.1 --offer 10.0.0.2 --seconds 1 2>&1)"; rc=$?
if [ "$rc" = 2 ] && printf '%s' "$out" | grep -q "needs root"; then
  ok "it refuses before binding when it cannot bind (exit $rc)"
else
  bad "the non-root refusal did not fire: rc=$rc out=$(printf '%s' "$out" | head -1)"
fi

out="$("$PY" "$TOOL" --server 10.0.0.1 --offer 10.0.0.2 2>&1)"; rc=$?
if [ "$rc" != 0 ] && printf '%s' "$out" | grep -q -- "--iface"; then
  ok "it refuses to run without being told which interface"
else
  bad "a missing --iface was accepted: rc=$rc"
fi

echo
echo "  $pass passed, $fail failed"
[ "$fail" = 0 ] || exit 1
