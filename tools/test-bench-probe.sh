#!/usr/bin/env bash
# Guard suite for tools/bench-probe.py.
#
# The refusals in that tool are the reason it exists rather than a page of curl,
# and they run once, on a bench, against the only unit there is. So they are
# driven here against a local HTTP server instead: no router, no network
# segment, nothing that can be broken by getting it wrong.
#
# Each case asserts on ITS OWN message. The positive control -- a probe run
# against a server that really answers -- is not padding: a suite of refusals
# passes just as well when the tool cannot make a request at all.
#
#   bash tools/test-bench-probe.sh
#
set -uo pipefail

cd "$(dirname "$0")/.." || { echo "  FAIL  cannot cd to the repository root"; exit 1; }
PY="${FWRE_PY:-python3}"

TMP="$(mktemp -d)"
SRV_PID=""
cleanup() { [ -n "$SRV_PID" ] && kill "$SRV_PID" 2>/dev/null; rm -rf "$TMP"; }
trap cleanup EXIT

pass=0; fail=0
ok()  { echo "  ok    $1"; pass=$((pass + 1)); }
bad() { echo "  FAIL  $1"; fail=$((fail + 1)); }

# must_refuse <label> <needle> <python snippet>
# bench-probe.py is not an importable module name (the hyphen), so it is loaded
# by path rather than imported.
must_refuse() {
  local label="$1" needle="$2" snippet="$3" out rc
  out="$("$PY" - "$snippet" <<'PYEOF' 2>&1
import importlib.util, pathlib, sys
spec = importlib.util.spec_from_file_location("bp", pathlib.Path("tools/bench-probe.py"))
bp = importlib.util.module_from_spec(spec); spec.loader.exec_module(bp)
try:
    exec(sys.argv[1], {"bp": bp})
except bp.ProbeError as e:
    print("REFUSED:", e); raise SystemExit(1)
print("ACCEPTED")
PYEOF
)"; rc=$?
  if [ "$rc" -eq 0 ]; then
    bad "$label -- accepted, and it must not be"
  elif [[ "$out" == *"$needle"* ]]; then
    ok "$label"
  else
    bad "$label -- refused for the WRONG reason:"; echo "$out" | sed 's/^/          /'
  fi
}

echo "=== refusals ==="

must_refuse "POST to /boafrm/* without submit-url" "without submit-url" \
  'bp.check_post("/boafrm/formWsc", {"wlanMode": "0"})'

must_refuse "a shell metacharacter in a parameter" "reconnaissance" \
  'bp.check_params({"sysCmd": "1;ls"})'

must_refuse "a backtick in a parameter" "reconnaissance" \
  'bp.check_params({"localPin": "1`id`"})'

# The refusal list added on 2026-08-17. `--allow-post` reads as "yes, I accept
# that this changes the configuration"; it must not also read as "yes, take the
# LAN address away from me half way through the sweep".
must_refuse "POST to the handler that owns the LAN address" "LAN addressing" \
  'bp.check_post("/boafrm/formTcpipSetup", {"submit-url": "/status.htm"})'

must_refuse "POST to the handler that owns the admin password" "CVE-2019-19823" \
  'bp.check_post("/boafrm/formPasswordSetup", {"submit-url": "/status.htm"})'

must_refuse "POST to the firmware upload handler" "This is the one" \
  'bp.check_post("/boafrm/formUpload", {"submit-url": "/status.htm"})'

# And the flag that overrides them has to actually override them, or the
# refusals above are a wall with no door and a future week edits the tool.
"$PY" - <<'PYEOF'
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location("bp", pathlib.Path("tools/bench-probe.py"))
bp = importlib.util.module_from_spec(spec); spec.loader.exec_module(bp)
bp.check_post("/boafrm/formTcpipSetup", {"submit-url": "/x"}, allow_destructive=True)
assert len(bp.HAZARDOUS) >= 13, len(bp.HAZARDOUS)
assert all(v.strip() for v in bp.HAZARDOUS.values()), "an entry with no reason"
PYEOF
if [ $? -eq 0 ]; then
  ok "--allow-destructive opens the door, and every entry carries a reason"
else
  bad "--allow-destructive did not override, or an entry has no reason"
fi

echo
echo "=== the write/read split is made from evidence, and it splits ==="
"$PY" - <<'PYEOF'
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location("bp", pathlib.Path("tools/bench-probe.py"))
bp = importlib.util.module_from_spec(spec); spec.loader.exec_module(bp)
prof = bp.handler_sink_profile()
# The classifier is only meaningful if the report it reads really does name
# handlers. An empty profile would silently call every endpoint read-only, and
# P3-13's comparison would then be between a set and itself.
assert len(prof) > 20, f"only {len(prof)} handlers have a sink profile"
assert "form_formSysCmd" in prof, "the G4 target has no sink profile"
assert "system" in prof["form_formSysCmd"], prof["form_formSysCmd"]
spawn = {k for k, v in prof.items() if "system" in v or "execl" in v}
assert 10 < len(spawn) < len(prof), f"{len(spawn)} of {len(prof)} spawn"
print(f"  ok    {len(prof)} handlers profiled, {len(spawn)} reach a "
      f"process-spawning sink")
PYEOF
if [ $? -eq 0 ]; then pass=$((pass + 1)); else bad "handler sink profile"; fi

echo
echo "=== the endpoint list comes from the committed report, not from memory ==="
"$PY" - <<'PYEOF'
import importlib.util, pathlib, sys
spec = importlib.util.spec_from_file_location("bp", pathlib.Path("tools/bench-probe.py"))
bp = importlib.util.module_from_spec(spec); spec.loader.exec_module(bp)
names, meta = bp.load_endpoints()
assert len(names) == meta["entry_count"], (len(names), meta["entry_count"])
assert meta["entry_count"] == 57, meta["entry_count"]
assert "formSysCmd" in names, "the G4 target is not in the recovered table"
assert meta["table_address"] == "00483758", meta["table_address"]
print(f"  ok    {len(names)} endpoints from {meta['source']} @ {meta['table_address']}")
PYEOF
if [ $? -eq 0 ]; then pass=$((pass + 1)); else bad "endpoint list"; fi

echo
echo "=== the control knows the difference between reachable and on the segment ==="
"$PY" - <<'PYEOF'
import importlib.util, pathlib, sys
spec = importlib.util.spec_from_file_location("bp", pathlib.Path("tools/bench-probe.py"))
bp = importlib.util.module_from_spec(spec); spec.loader.exec_module(bp)

lo = bp.route_to("127.0.0.1")
assert lo["direct"] is True, f"loopback should be directly attached: {lo}"

# A public address must never be claimed as directly attached. On a host with a
# default route this resolves through a gateway; on one without, it resolves to
# nothing. Either is acceptable; "direct" is not.
pub = bp.route_to("8.8.8.8")
assert pub["direct"] is not True, f"a routed address claimed as direct: {pub}"

bad = bp.route_to("not-an-address")
assert bad["direct"] is None, f"a non-address should not resolve: {bad}"
print(f"  ok    directly attached vs routed is decided from /proc/net/route "
      f"(lo={lo['iface']}, 8.8.8.8 via {pub.get('via')})")
PYEOF
if [ $? -eq 0 ]; then pass=$((pass + 1)); else bad "route classification"; fi

echo
echo "=== the control: a probe run against a server that really answers ==="
PORT=18080
"$PY" - "$PORT" "$TMP" <<'PYEOF' &
import http.server, socketserver, sys, os
port, root = int(sys.argv[1]), sys.argv[2]
os.chdir(root)
open("status.htm", "w").write("<html>ok</html>")
class H(http.server.SimpleHTTPRequestHandler):
    server_version = "Boa/0.94.14rc21"
    sys_version = ""
    def log_message(self, *a): pass
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("127.0.0.1", port), H) as httpd:
    httpd.serve_forever()
PYEOF
SRV_PID=$!
for _ in $(seq 1 40); do
  "$PY" -c "import socket,sys; s=socket.create_connection(('127.0.0.1',$PORT),0.2); s.close()" 2>/dev/null && break
  sleep 0.1
done

out="$("$PY" tools/bench-probe.py control --host 127.0.0.1 --port "$PORT" 2>&1)"
if [[ "$out" == *"Boa/0.94.14rc21"* ]]; then
  ok "control reaches a live server and reads its Server header"
else
  bad "control against a live server -- the refusals above prove nothing:"
  echo "$out" | sed 's/^/          /'
fi

out="$("$PY" tools/bench-probe.py fingerprint --host 127.0.0.1 --port "$PORT" \
        -o "$TMP/fp.json" 2>&1)"
if [ -s "$TMP/fp.json" ] && [[ "$out" == *"200"* ]] && [[ "$out" == *"404"* ]]; then
  ok "fingerprint records both a 200 and a 404, and writes a transcript"
else
  bad "fingerprint against a live server:"; echo "$out" | sed 's/^/          /'
fi

if "$PY" - "$TMP/fp.json" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
recs = d["records"]
assert any(r.get("probe") == "control-after" for r in recs), "no control after the run"
assert all("request_wire" in r for r in recs if r.get("probe") != "control-after" or True), "a record without its verbatim request"
sys.exit(0)
PYEOF
then ok "every record carries its verbatim request, and the run re-checks the control"
else bad "transcript shape"; fi

echo
echo "=== a dead control must stop the run, not produce 'findings' ==="
out="$("$PY" tools/bench-probe.py endpoints --host 127.0.0.1 --port 19999 2>&1)"; rc=$?
if [ "$rc" -eq 0 ]; then
  bad "an unreachable device -- the run continued"
elif [[ "$out" == *"control failed"* ]]; then
  ok "an unreachable device stops the run before any endpoint is probed"
else
  bad "an unreachable device -- stopped for the wrong reason:"; echo "$out" | sed 's/^/          /'
fi

echo
echo "=== a run that stops must still write what it saw ==="
# On 2026-08-17 a sweep stopped at endpoint 60 of 64 because the web server
# stopped accepting, and wrote nothing at all -- so the fifty-nine responses
# before it, and the elapsed_ms that would have named the slow one, were gone.
# Detecting the interesting event and destroying the evidence of it are not
# supposed to be the same action.
rm -f "$TMP/stopped.json"
out="$("$PY" tools/bench-probe.py endpoints --host 127.0.0.1 --port 19999 \
        -o "$TMP/stopped.json" 2>&1)"; rc=$?
if [ "$rc" -eq 0 ]; then
  bad "a stopped run reported success"
elif [ ! -s "$TMP/stopped.json" ]; then
  bad "a stopped run wrote no transcript"
elif "$PY" -c '
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
assert d.get("stopped"), "no stopped block"
assert "control failed" in d["stopped"]["reason"], d["stopped"]["reason"]
assert isinstance(d.get("journal"), list), "no journal"
assert len(d["journal"]) >= 1, "journal is empty"
# And the *records* -- the group annotations, not just the raw requests. On the
# 2026-08-17 run these were still lost, because the group built its list locally
# and the exception unwound past the return, so the per-endpoint stall
# measurement written to describe the stall did not survive the stall.
assert isinstance(d.get("records"), list), "no records"
' "$TMP/stopped.json"; then
  ok "a stopped run writes a transcript naming why it stopped, with its journal"
else
  bad "the stopped transcript is not shaped right"
fi

echo
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ]
