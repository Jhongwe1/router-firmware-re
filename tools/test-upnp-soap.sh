#!/usr/bin/env bash
# Guard suite for tools/upnp-soap.py.
#
# This tool sends one request to a daemon that dies when it does not like the
# request, so every run costs a power cycle if it is wrong. Three of its refusals
# exist because each of them has already cost one:
#
#   * **a payload must not pass through a shell.** The first P6-1 attempt on
#     2026-08-19 typed a 25-byte backtick payload on a command line; the LOCAL
#     shell expanded it and 431 bytes of a local ping's stdout went to the device,
#     killed miniigd and destroyed the test. `--arg-file` is the fix and it is
#     only meaningful if it really reads bytes verbatim, newlines included.
#
#   * **the control URL is not typed.** `/upnp/control/WANIPConn1` is
#     miniupnpd's; this binary answers on `/upnp/control/WANIPConnection`, and
#     the wrong one returns a clean 404 that reads as "no UPnP control surface"
#     with the port open the whole time. So it is read from the device's own
#     description document, and a document without a WANIPConnection service is
#     a refusal rather than a guess.
#
#   * **a SOAP fault is an answer, not an error.** "this version validates the
#     field" arrives as HTTP 500 with a UPnPError code, and a tool that treats
#     500 as a transport failure throws away the result.
#
# Everything below runs against a local HTTP server this script starts, so it
# needs no device and no network beyond loopback.
#
#   bash tools/test-upnp-soap.sh
set -uo pipefail

cd "$(dirname "$0")/.." || { echo "  FAIL  cannot cd to the repository root"; exit 1; }
TOOL=tools/upnp-soap.py
PY="${PYTHON:-python3}"

pass=0; fail=0
ok()  { echo "  ok    $1"; pass=$((pass + 1)); }
bad() { echo "  FAIL  $1"; fail=$((fail + 1)); }

check() {
  local label="$1" script="$2" out
  out="$("$PY" - <<PYEOF 2>&1
import importlib.util, sys, threading, http.server, socketserver, tempfile, os
spec = importlib.util.spec_from_file_location("upnpsoap", "$TOOL")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

DESC = b'''<?xml version="1.0"?><root>
<service><serviceType>urn:schemas-upnp-org:service:WANCommonInterfaceConfig:1</serviceType>
<controlURL>/upnp/control/WANCommonInterfaceConfig</controlURL></service>
<service><serviceType>urn:schemas-upnp-org:service:WANIPConnection:1</serviceType>
<controlURL>/upnp/control/WANIPConnection</controlURL></service>
</root>'''

BODY = {}

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass
    def version_string(self):
        # send_response() emits its own Server header first, and the first one
        # is the one a client reads -- so the banner has to be set here rather
        # than added afterwards. The banner matters: on the real unit it names
        # miniupnpd while the binary is Realtek's miniigd.
        return "miniupnpd/1.4 UPnP/1.4"
    def do_GET(self):
        if self.path == "/picsdesc.xml":
            self.send_response(200)
            self.send_header("Content-Length", str(len(DESC)))
            self.end_headers(); self.wfile.write(DESC)
        else:
            self.send_error(404)
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        BODY["sent"] = self.rfile.read(n).decode()
        BODY["soapaction"] = self.headers.get("SOAPAction")
        BODY["path"] = self.path
        if b"FAULT" in BODY["sent"].encode():
            payload = (b"<s:Envelope><s:Body><s:Fault><detail><UPnPError>"
                       b"<errorCode>718</errorCode>"
                       b"<errorDescription>ConflictInMappingEntry</errorDescription>"
                       b"</UPnPError></detail></s:Fault></s:Body></s:Envelope>")
            self.send_response(500)
        else:
            payload = (b"<s:Envelope><s:Body><u:X><NewInternalClient>10.1.1.1"
                       b"</NewInternalClient><NewEnabled>1</NewEnabled>"
                       b"</u:X></s:Body></s:Envelope>")
            self.send_response(200)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers(); self.wfile.write(payload)

srv = socketserver.TCPServer(("127.0.0.1", 0), H)
PORT = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
TMP = tempfile.mkdtemp()

import contextlib, io
def run(argv):
    """main() prints its transcript; the case below is asserting on the exit
    code and on what reached the server, so its own output is noise here."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return m.main(argv)
$script
srv.shutdown()
PYEOF
)"
  if [ "$out" = "PASS" ]; then ok "$label"; else bad "$label -- $out"; fi
}

echo "tools/upnp-soap.py -- the control URL it will not guess, and the shell it will not use"

check "the control URL is read from the device, not typed" '
d = m.describe("127.0.0.1", PORT, 5)
print("PASS" if d["wan_control_url"] == "/upnp/control/WANIPConnection"
      and d["wan_service"].endswith("WANIPConnection:1") else repr(d))
'

check "the Server banner is captured, because it names a codebase this is not" '
d = m.describe("127.0.0.1", PORT, 5)
print("PASS" if "miniupnpd" in d["server_header"] else repr(d["server_header"]))
'

check "a description with no WANIPConnection service is refused, not guessed past" '
import http.server, socketserver, threading
class B(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        p = b"<root><service><serviceType>urn:x:Other:1</serviceType><controlURL>/x</controlURL></service></root>"
        self.send_response(200); self.send_header("Content-Length", str(len(p)))
        self.end_headers(); self.wfile.write(p)
s2 = socketserver.TCPServer(("127.0.0.1", 0), B)
threading.Thread(target=s2.serve_forever, daemon=True).start()
try:
    m.describe("127.0.0.1", s2.server_address[1], 5)
    print("guessed a control URL that is not there")
except m.Refused as exc:
    print("PASS" if "no WANIPConnection" in str(exc) else str(exc))
s2.shutdown()
'

check "a shell metacharacter without --inject is refused" '
rc = run(["--host", "127.0.0.1", "--port", str(PORT), "--action",
             "AddPortMapping", "--arg", "NewInternalClient=`id`"])
print("PASS" if rc == 2 and "sent" not in BODY else "rc=%r sent=%r" % (rc, BODY))
'

check "the same value WITH --inject is sent, and sent verbatim" '
rc = run(["--host", "127.0.0.1", "--port", str(PORT), "--action",
             "AddPortMapping", "--arg", "NewInternalClient=`id`", "--inject"])
print("PASS" if rc == 0 and "<NewInternalClient>`id`</NewInternalClient>" in BODY["sent"]
      else "rc=%r %r" % (rc, BODY.get("sent")))
'

check "--arg-file reads the bytes verbatim, newlines and all" '
p = os.path.join(TMP, "payload.txt")
open(p, "w").write("`ping -c 4 10.1.1.100`\n")
rc = run(["--host", "127.0.0.1", "--port", str(PORT), "--action",
             "AddPortMapping", "--arg", "NewInternalClient=PLACEHOLDER",
             "--arg-file", "NewInternalClient=" + p, "--inject"])
sent = BODY["sent"]
print("PASS" if rc == 0
      and "<NewInternalClient>`ping -c 4 10.1.1.100`</NewInternalClient>" in sent
      and "PLACEHOLDER" not in sent else "rc=%r %r" % (rc, sent))
'

check "--arg-file keeps the position the caller gave it, so argument order is theirs" '
p = os.path.join(TMP, "p2.txt"); open(p, "w").write("X")
run(["--host", "127.0.0.1", "--port", str(PORT), "--action", "AddPortMapping",
        "--arg", "NewRemoteHost=", "--arg", "NewInternalClient=PLACEHOLDER",
        "--arg", "NewEnabled=1", "--arg-file", "NewInternalClient=" + p, "--inject"])
s = BODY["sent"]
print("PASS" if s.index("NewRemoteHost") < s.index("NewInternalClient")
      < s.index("NewEnabled") else s)
'

check "--arg-file without --inject is refused, because that is what it is for" '
p = os.path.join(TMP, "p3.txt"); open(p, "w").write("X")
BODY.clear()
rc = run(["--host", "127.0.0.1", "--port", str(PORT), "--action",
             "AddPortMapping", "--arg-file", "NewInternalClient=" + p])
print("PASS" if rc == 2 and "sent" not in BODY else "rc=%r %r" % (rc, BODY))
'

check "an action this tool does not send is refused before anything leaves" '
BODY.clear()
rc = run(["--host", "127.0.0.1", "--port", str(PORT), "--action", "AddPortMappng"])
print("PASS" if rc == 2 and "sent" not in BODY else "rc=%r %r" % (rc, BODY))
'

check "the SOAPAction header carries the service and the action" '
run(["--host", "127.0.0.1", "--port", str(PORT), "--action", "GetExternalIPAddress"])
print("PASS" if BODY["soapaction"] ==
      chr(34) + "urn:schemas-upnp-org:service:WANIPConnection:1#GetExternalIPAddress" + chr(34)
      else repr(BODY["soapaction"]))
'

check "a SOAP fault is read as an answer, with its error code, not as a failure" '
rc = run(["--host", "127.0.0.1", "--port", str(PORT), "--action",
             "AddPortMapping", "--arg", "NewPortMappingDescription=FAULT"])
print("PASS" if rc == 0 else "rc=%r" % rc)
'

check "the fault code and description are extracted, because they ARE the result" '
d = m.describe("127.0.0.1", PORT, 5)
r = m.call("127.0.0.1", PORT, d["wan_control_url"], d["wan_service"],
           "AddPortMapping", [("NewPortMappingDescription", "FAULT")], 5)
print("PASS" if r["status"] == 500 and r["upnp_error"] == 718
      and r["upnp_error_description"] == "ConflictInMappingEntry"
      else repr(r))
'

check "New* fields are parsed out of a successful body" '
d = m.describe("127.0.0.1", PORT, 5)
r = m.call("127.0.0.1", PORT, d["wan_control_url"], d["wan_service"],
           "GetGenericPortMappingEntry", [], 5)
print("PASS" if r["fields"].get("NewInternalClient") == "10.1.1.1" else repr(r["fields"]))
'

check "a closed connection is reported as one, not as an empty answer" '
import socket
s3 = socket.socket(); s3.bind(("127.0.0.1", 0)); s3.listen(1)
port = s3.getsockname()[1]; s3.close()
d = {"wan_control_url": "/upnp/control/WANIPConnection",
     "wan_service": "urn:schemas-upnp-org:service:WANIPConnection:1"}
r = m.call("127.0.0.1", port, d["wan_control_url"], d["wan_service"],
           "GetExternalIPAddress", [], 3)
print("PASS" if r["status"] is None and "error" in r else repr(r))
'

echo
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
