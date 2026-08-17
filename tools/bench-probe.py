#!/usr/bin/env python3
"""Drive the W05 network probes against the unit, and record what came back.

Why a tool rather than a page of curl
-------------------------------------
The register schedules ~20 HTTP tests against one device, and three of them are
sweeps over the 57 entries of `root_form[]`. Typed by hand that is an hour of
copy-paste in which the interesting answer -- a 404 where a 200 was predicted --
is a line that scrolls past. Worse, two of the failure modes are silent:

  * `submit-url` omitted from a POST reaches `strcpy(p, "/status.htm")` into a
    read-only segment (notes/submit-url-overflow.md). As the code reads, that
    kills the web server. Every subsequent endpoint then answers "connection
    refused", which looks exactly like "the endpoint does not exist" -- so one
    mistyped request silently turns a 57-endpoint census into a 57-endpoint
    false negative. This tool will not send such a POST.

  * a device that stopped answering half way through produces a run whose second
    half is all failures and whose transcript gives no way to tell when it
    stopped. So the control is re-run *between* groups, not only at the start.

What it will not do
-------------------
  * POST to a form handler unless asked with --allow-post. A POST runs the
    handler, and a handler whose parameters are all absent still writes whatever
    its accessors defaulted to. Existence can be probed with GET; changing the
    device's configuration to find out whether a route exists is not a trade
    this tool makes for you.
  * send shell metacharacters in any parameter. Injection is W06's job and it
    happens after the recovery drill, not inside a reconnaissance sweep.
  * write anything unless every response it recorded is in the transcript.

Everything is stdlib: this runs on the bench machine, not in CI.

  python3 tools/bench-probe.py control    --host 10.1.1.1
  python3 tools/bench-probe.py fingerprint --host 10.1.1.1 -o dumps/w05-fp.json
  python3 tools/bench-probe.py endpoints  --host 10.1.1.1 -o dumps/w05-ep.json
  python3 tools/bench-probe.py gate       --host 10.1.1.1 -o dumps/w05-gate.json
  python3 tools/bench-probe.py ssdp       --host 10.1.1.1 -o dumps/w05-ssdp.json
"""

from __future__ import annotations

import argparse
import json
import re
import socket
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
FORMTABLE = REPO / "reports/ghidra-formtable-unit-2018.json"

# Anything that would turn a parameter into a second command. A reconnaissance
# sweep has no business carrying one, and the check is here rather than in the
# operator's memory.
SHELL_METACHARACTERS = set(";|&`$><\n\r\\'\"")

BODY_KEEP = 512          # bytes of body kept per response
CONNECT_TIMEOUT = 6.0


class ProbeError(Exception):
    pass


# --------------------------------------------------------------------------
# HTTP, by hand.
#
# urllib normalises the request line -- it collapses `//`, resolves `/../`, and
# refuses some of the shapes this file exists to send. Several of the gate tests
# are *about* those shapes (P2-2, P2-3), so the request has to go out exactly as
# written. That means a socket and a hand-built request.
# --------------------------------------------------------------------------
def raw_request(
    host: str,
    port: int,
    method: str,
    target: str,
    headers: dict[str, str] | None = None,
    body: bytes = b"",
    timeout: float = CONNECT_TIMEOUT,
) -> dict[str, Any]:
    hdr = {"Host": f"{host}:{port}" if port != 80 else host,
           "User-Agent": "fwre-bench-probe/1",
           "Connection": "close"}
    if headers:
        hdr.update(headers)
    if body:
        hdr["Content-Length"] = str(len(body))
        hdr.setdefault("Content-Type", "application/x-www-form-urlencoded")

    req = f"{method} {target} HTTP/1.1\r\n".encode("latin-1")
    for k, v in hdr.items():
        req += f"{k}: {v}\r\n".encode("latin-1")
    req += b"\r\n" + body

    out: dict[str, Any] = {
        "method": method, "target": target, "headers": hdr,
        "body": body.decode("latin-1") if body else "",
        "request_wire": req.decode("latin-1"),
    }
    t0 = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout) as s:
            s.settimeout(timeout)
            s.sendall(req)
            chunks, total = [], 0
            while total < 65536:
                try:
                    b = s.recv(4096)
                except TimeoutError:
                    out["note"] = "read timed out; partial response recorded"
                    break
                if not b:
                    break
                chunks.append(b)
                total += len(b)
        data = b"".join(chunks)
    except OSError as e:
        out["error"] = f"{type(e).__name__}: {e}"
        out["elapsed_ms"] = round((time.monotonic() - t0) * 1000)
        return out

    out["elapsed_ms"] = round((time.monotonic() - t0) * 1000)
    head, _, rest = data.partition(b"\r\n\r\n")
    lines = head.decode("latin-1", "replace").split("\r\n")
    out["status_line"] = lines[0] if lines else ""
    m = re.match(r"HTTP/\d\.\d\s+(\d{3})", out["status_line"])
    out["status"] = int(m.group(1)) if m else None
    out["response_headers"] = {}
    for ln in lines[1:]:
        if ":" in ln:
            k, v = ln.split(":", 1)
            out["response_headers"][k.strip()] = v.strip()
    out["body_bytes"] = len(rest)
    out["body_head"] = rest[:BODY_KEEP].decode("latin-1", "replace")
    return out


# --------------------------------------------------------------------------
# refusals
# --------------------------------------------------------------------------
def check_params(params: dict[str, str]) -> None:
    for k, v in params.items():
        bad = SHELL_METACHARACTERS & set(v)
        if bad:
            raise ProbeError(
                f"parameter {k!r} contains {sorted(bad)!r}. This tool does "
                "reconnaissance; command injection is W06's, and it runs after "
                "the recovery drill rather than inside a sweep"
            )


def check_post(target: str, params: dict[str, str]) -> None:
    if "/boafrm/" in target and "submit-url" not in params:
        raise ProbeError(
            f"refusing POST {target} without submit-url. When the parameter is "
            "absent the handler strcpy()s \"/status.htm\" into a read-only "
            "segment (notes/submit-url-overflow.md); as the code reads that is "
            "a one-request crash of the web server, and every endpoint probed "
            "afterwards would answer as if it did not exist"
        )


def urlencode(params: dict[str, str]) -> bytes:
    from urllib.parse import quote
    return "&".join(f"{quote(k, safe='')}={quote(v, safe='')}"
                    for k, v in params.items()).encode("latin-1")


# --------------------------------------------------------------------------
# the control
# --------------------------------------------------------------------------
def route_to(host: str) -> dict[str, Any]:
    """Is `host` on a directly-connected subnet, and on which interface?

    This is here because "the device answers" is not the same as "I am on its
    segment", and the difference is invisible in an HTTP response. On
    2026-08-17 the USB Ethernet adapter came up on the *Windows* side while the
    tests were being driven from WSL: `ping 10.1.1.1` succeeded and everything
    looked fine, and the only tell was `ttl=63` where a directly attached Linux
    host answers 64. Through that path SSDP cannot work at all (multicast does
    not cross the NAT), two source addresses collapse into one, and a raw-socket
    scan measures the NAT rather than the device -- while the transcript would
    have recorded none of it.
    """
    out: dict[str, Any] = {"target": host, "direct": None, "iface": None,
                           "via": None}
    try:
        packed = socket.inet_aton(host)
    except OSError:
        return out
    target = int.from_bytes(packed, "big")
    # /proc/net/route carries the *main* table only; the loopback route lives in
    # the local table and is absent from it, so 127/8 would otherwise fall
    # through to the default route and be reported as reached via a gateway.
    # Found by the guard suite on this function's first run.
    if packed[0] == 127:
        out.update(direct=True, iface="lo")
        return out
    best = -1
    try:
        with open("/proc/net/route", encoding="ascii") as fh:
            next(fh)
            for line in fh:
                f = line.split()
                if len(f) < 8:
                    continue
                iface, dest, gw, mask = f[0], f[1], f[2], f[7]
                # /proc/net/route is little-endian hex
                d = int.from_bytes(bytes.fromhex(dest), "little")
                g = int.from_bytes(bytes.fromhex(gw), "little")
                m = int.from_bytes(bytes.fromhex(mask), "little")
                if (target & m) != d:
                    continue
                bits = bin(m).count("1")
                if bits > best:
                    best = bits
                    out["iface"] = iface
                    out["direct"] = (g == 0)
                    out["via"] = None if g == 0 else str(
                        socket.inet_ntoa(g.to_bytes(4, "big")))
    except OSError as e:
        out["error"] = f"{type(e).__name__}: {e}"
    return out


def control(host: str, port: int) -> dict[str, Any]:
    """The device answers, answers as the thing we think it is, and is on our
    segment.

    Re-run between groups. A run whose second half is all failures because the
    web server died in the first half must not read as a finding about the
    second half.
    """
    r = raw_request(host, port, "GET", "/")
    ok = r.get("status") is not None
    server = r.get("response_headers", {}).get("Server", "")
    return {"probe": "control", "reachable": ok, "server": server,
            "route": route_to(host), **r}


def require_control(host: str, port: int, where: str,
                    need_direct: bool = False) -> dict[str, Any]:
    c = control(host, port)
    if not c["reachable"]:
        raise ProbeError(
            f"control failed {where}: {c.get('error') or 'no HTTP status line'}.\n"
            "  Stopping. Results recorded after an unreachable control describe "
            "the state of the web server, not the state of the endpoint."
        )
    rt = c.get("route", {})
    if rt.get("direct") is False and need_direct:
        raise ProbeError(
            f"control failed {where}: {host} is reached via {rt.get('via')} on "
            f"{rt.get('iface')}, not on a directly connected subnet.\n"
            "  This group needs to be on the device's segment. Broadcast and "
            "multicast do not cross a router, and a negative result would look "
            "exactly like the service being absent.\n"
            "  If the adapter is attached to the host rather than here: "
            "`usbipd attach --wsl --busid <id>`."
        )
    return c


# --------------------------------------------------------------------------
# groups
# --------------------------------------------------------------------------
def load_endpoints() -> tuple[list[str], dict[str, Any]]:
    doc = json.loads(FORMTABLE.read_text("utf-8"))
    for t in doc["tables"]:
        if t.get("role") == "root_form":
            names = [e["name"] for e in t["entries"]]
            meta = {"source": str(FORMTABLE.relative_to(REPO)),
                    "table_address": t["address"],
                    "entry_count": t["entry_count"],
                    "program_sha256": doc.get("source_sha256")}
            return names, meta
    raise ProbeError(f"no root_form table in {FORMTABLE}")


def group_fingerprint(host: str, port: int) -> list[dict[str, Any]]:
    """P1-3 (Boa fingerprint, 404 shape) and P1-8 (/boafrm/ vs /goform/)."""
    out = []
    for label, method, target in [
        ("root", "GET", "/"),
        ("login page", "GET", "/login.htm"),
        ("status page", "GET", "/status.htm"),
        ("config.dat, ungated in all three builds", "GET", "/config.dat"),
        ("ca.cer", "GET", "/ca.cer"),
        ("404 shape", "GET", "/this-does-not-exist-9d3f.htm"),
        ("404 shape, no extension", "GET", "/this-does-not-exist-9d3f"),
        ("boafrm prefix, GET", "GET", "/boafrm/formSysCmd"),
        ("goform prefix (P1-8: expected absent)", "GET", "/goform/formSysCmd"),
        ("cgi-bin", "GET", "/cgi-bin/"),
        ("syscmd.htm (not in the 143-file bundle)", "GET", "/syscmd.htm"),
        ("HEAD /", "HEAD", "/"),
        ("OPTIONS *", "OPTIONS", "*"),
    ]:
        r = raw_request(host, port, method, target)
        out.append({"probe": "fingerprint", "label": label, **r})
    return out


def group_endpoints(host: str, port: int, allow_post: bool) -> list[dict[str, Any]]:
    """P1-4 / P1-5 / P1-6.

    P1-5 is the interesting one and it is a test of the tools, not the device:
    Ghidra's root_form[] has 57 entries, fwrecon's string extraction found 60.
    The three extra names are probed here alongside the 57.
    P1-6 probes the two spellings the published CVEs use, which do not match the
    dispatch table.
    """
    names, meta = load_endpoints()
    extra = ["formOpdRedirect", "formWanRedirect", "formWlanRedirect2"]
    cve_spellings = ["formWlwds", "fromStaticDHCP"]
    real_spellings = ["formWlWds", "formStaticDHCP"]

    out: list[dict[str, Any]] = [{"probe": "endpoints-meta", **meta,
                                  "extra_from_string_extraction": extra,
                                  "cve_spellings": cve_spellings}]
    plan = ([(n, "root_form") for n in names]
            + [(n, "string-extraction-only") for n in extra]
            + [(n, "CVE text spelling") for n in cve_spellings]
            + [(n, "dispatch-table spelling") for n in real_spellings])

    for i, (name, origin) in enumerate(plan):
        if i and i % 20 == 0:
            require_control(host, port, f"before endpoint {i} of {len(plan)}")
        target = f"/boafrm/{name}"
        if allow_post:
            params = {"submit-url": "/status.htm"}
            check_params(params)
            check_post(target, params)
            r = raw_request(host, port, "POST", target, body=urlencode(params))
            r["method_note"] = "POST with submit-url only; the handler ran"
        else:
            r = raw_request(host, port, "GET", target)
            r["method_note"] = "GET; the handler's parameter processing may not run"
        out.append({"probe": "endpoint", "name": name, "origin": origin, **r})
    return out


def group_gate(host: str, port: int) -> list[dict[str, Any]]:
    """P2-1 / P2-2 / P2-3 / P2-5.

    This build's process_header_end (0x0040bb1c) runs the authorisation check
    only when the URI contains ".htm" or ".asp" -- 13 unanchored strstr calls on
    one string. Static analysis says what the mechanism is. Only a request says
    how wide the door it opens actually is, because URI normalisation and
    translate_uri sit in between.
    """
    cases = [
        ("plain .htm page (gate should run)", "GET", "/status.htm"),
        ("plain page, no extension (gate should not run)", "GET", "/status"),
        ("config.dat (P2-1: outside the gate)", "GET", "/config.dat"),
        ("uppercase .HTM (strstr is case sensitive)", "GET", "/status.HTM"),
        ("mixed case .Htm", "GET", "/status.Htm"),
        (".htm in the query string only", "GET", "/config.dat?x=.htm"),
        (".htm in a path segment, not the extension", "GET", "/x.htmfoo/config.dat"),
        ("P2-2: exemption string injected into the path", "GET", "/login.htm/../config.dat"),
        ("P2-2: 'login' as a substring elsewhere", "GET", "/config.dat?login=1"),
        ("P2-3: double slash", "GET", "//config.dat"),
        ("P2-3: dot segment", "GET", "/./config.dat"),
        ("P2-3: parent segment", "GET", "/a/../config.dat"),
        ("P2-3: percent-encoded slash", "GET", "/%2fconfig.dat"),
        ("P2-3: percent-encoded dot", "GET", "/%2e/config.dat"),
        ("P2-3: trailing dot on a gated page", "GET", "/status.htm."),
        ("P2-3: trailing space (encoded)", "GET", "/status.htm%20"),
        ("P2-3: null byte (encoded)", "GET", "/status.htm%00.dat"),
        ("P2-3: backslash", "GET", "/\\config.dat"),
        ("P2-5: GET a form handler with a query string", "GET",
         "/boafrm/formSysCmd?submit-url=/status.htm"),
        ("P2-5: GET a form handler, no parameters", "GET", "/boafrm/formWsc"),
    ]
    out = []
    for i, (label, method, target) in enumerate(cases):
        if i and i % 10 == 0:
            require_control(host, port, f"before gate case {i}")
        r = raw_request(host, port, method, target)
        out.append({"probe": "gate", "label": label, **r})

    # P2-4: does anything in the request head change the answer?
    for label, hdrs in [
        ("Host: an unrelated name", {"Host": "example.invalid"}),
        ("Host: empty", {"Host": ""}),
        ("X-Forwarded-For: 127.0.0.1", {"X-Forwarded-For": "127.0.0.1"}),
        ("Referer: the device itself", {"Referer": f"http://{host}/status.htm"}),
        ("Authorization: Basic admin:admin",
         {"Authorization": "Basic YWRtaW46YWRtaW4="}),
    ]:
        r = raw_request(host, port, "GET", "/status.htm", headers=hdrs)
        out.append({"probe": "gate-headers", "label": label, **r})
    return out


def group_ssdp(host: str, port: int) -> list[dict[str, Any]]:
    """P1-10. UPNP_ENABLED is 1 in both the live config and the factory
    default, and /bin/sysconf holds the miniigd and mini_upnpd strings -- but
    nobody has read the branch that starts them, which is why this is a test and
    not a statement. Which daemon answers also decides which CVEs apply:
    miniigd is Realtek's (CVE-2014-8361), mini_upnpd is a different codebase.
    """
    msg = ("M-SEARCH * HTTP/1.1\r\n"
           "HOST: 239.255.255.250:1900\r\n"
           'MAN: "ssdp:discover"\r\n'
           "MX: 2\r\n"
           "ST: upnp:rootdevice\r\n\r\n").encode("latin-1")
    out = []
    for label, dest in [("unicast to the device", host),
                        ("multicast", "239.255.255.250")]:
        rec: dict[str, Any] = {"probe": "ssdp", "label": label,
                               "dest": dest, "request_wire": msg.decode()}
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(4.0)
            s.sendto(msg, (dest, 1900))
            replies = []
            t0 = time.monotonic()
            while time.monotonic() - t0 < 4.0:
                try:
                    data, addr = s.recvfrom(4096)
                except TimeoutError:
                    break
                replies.append({"from": f"{addr[0]}:{addr[1]}",
                                "text": data.decode("latin-1", "replace")})
            s.close()
            rec["replies"] = replies
            rec["reply_count"] = len(replies)
        except OSError as e:
            rec["error"] = f"{type(e).__name__}: {e}"
        out.append(rec)
    return out


GROUPS = {
    "control": lambda h, p, _: [control(h, p)],
    "fingerprint": lambda h, p, _: group_fingerprint(h, p),
    "endpoints": group_endpoints,
    "gate": lambda h, p, _: group_gate(h, p),
    "ssdp": lambda h, p, _: group_ssdp(h, p),
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("group", choices=sorted(GROUPS))
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, default=80)
    ap.add_argument("--allow-post", action="store_true",
                    help="POST to form handlers. A POST RUNS THE HANDLER and can "
                         "change this unit's configuration. Take a 64 KiB config "
                         "snapshot before and after; tools/qemu-env.sh diff shows "
                         "what a write looks like")
    ap.add_argument("-o", "--output", help="JSON transcript (recommended)")
    args = ap.parse_args(argv)

    try:
        if args.group != "control":
            # SSDP is the group that cannot survive a router in the path at all,
            # so it refuses; the rest warn, because a warning that stops work is
            # worse than one that is read.
            require_control(args.host, args.port, "before the run",
                            need_direct=(args.group == "ssdp"))
        records = GROUPS[args.group](args.host, args.port, args.allow_post)
        if args.group not in ("control", "ssdp"):
            # The spread goes first: `control()` sets "probe" itself, so putting
            # the literal first lets it be overwritten and the after-run control
            # is indistinguishable from the before-run one in the transcript.
            # Caught by the guard suite, which asserts the record is there.
            records.append({**require_control(args.host, args.port, "after the run"),
                            "probe": "control-after"})
    except ProbeError as e:
        print(f"bench-probe: {e}", file=sys.stderr)
        return 1

    doc = {
        "producer": "bench-probe/1",
        "group": args.group,
        "host": args.host,
        "port": args.port,
        "allow_post": args.allow_post,
        "records": records,
    }
    for r in records:
        st = r.get("status")
        lab = r.get("label") or r.get("name") or r.get("probe")
        srv = r.get("response_headers", {}).get("Server", "")
        err = r.get("error", "")
        extra = f"  {srv}" if srv else ""
        if r.get("probe") == "ssdp":
            print(f"  {'':>4}  {lab:<46} replies={r.get('reply_count', '-')} {err}")
        else:
            code = st if st is not None else "---"
            print(f"  {code:>4}  {lab:<46} {r.get('body_bytes', 0):>6}B{extra} {err}")

    rt = next((r.get("route") for r in records if r.get("route")), None)
    if rt:
        if rt.get("direct"):
            print(f"  route: {args.host} is directly attached on {rt['iface']}")
        elif rt.get("direct") is False:
            print(f"\n  ⚠ {args.host} is reached via {rt.get('via')} on "
                  f"{rt.get('iface')} — NOT directly attached.\n"
                  "    Every result above is a measurement of that path as much "
                  "as of the device.\n"
                  "    Source-address behaviour, broadcast, multicast and raw "
                  "scans are all unreliable through it.", file=sys.stderr)

    if args.output:
        Path(args.output).write_text(json.dumps(doc, indent=1, ensure_ascii=False), "utf-8")
        print(f"wrote {args.output}")
    else:
        print("  (no --output: nothing was recorded. A probe whose response is "
              "not kept is not evidence)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
