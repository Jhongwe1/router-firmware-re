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
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ]
