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
  * POST to thirteen named handlers even then. Configuration change is
    recoverable and attributable with a snapshot either side; losing the LAN
    address mid-sweep, losing the admin password, or entering the firmware
    upload path is not. See HAZARDOUS below -- each entry carries its reason,
    the skipped names go into the transcript's first record, and overriding
    them takes a second flag.
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
SINKS = REPO / "reports/ghidra-sinks-unit-2018.json"

# --------------------------------------------------------------------------
# Handlers a parameter-less POST must not reach.
#
# `--allow-post` was written for P1-4, whose whole shape is "POST all 57 names
# and see which answer". What that sentence hides is that on this build 23 of
# the 57 call system() and 13 call execl() (reports/ghidra-sinks-unit-2018.json),
# and a handler whose parameters are all absent still writes whatever its
# accessors defaulted to. A blind sweep therefore runs 36 process-spawning
# handlers on the only unit there is.
#
# Four of the outcomes are not "the configuration changed", which a snapshot
# pair can attribute and undo. They destroy the run or the evidence:
#
#   * losing the address the sweep is being driven over turns every remaining
#     endpoint into "connection refused" -- the exact false-negative shape this
#     file was written to prevent, wearing different clothes;
#   * losing the admin password destroys the CVE-2019-19823 chain, which is the
#     hardest evidence this project has;
#   * the firmware and configuration upload paths are the ones that brick;
#   * an operating-mode change reboots into a different network.
#
# So they are refused by name, each with its reason, and the refusal is
# recorded in the transcript rather than being a quiet gap. A future week that
# genuinely wants one has to pass --allow-destructive and say so on the record.
# --------------------------------------------------------------------------
HAZARDOUS: dict[str, str] = {
    "formTcpipSetup": "LAN addressing. Losing it mid-sweep makes every "
                      "remaining endpoint read as absent",
    "formWanTcpipSetup": "WAN addressing; same class, and it can restart the "
                         "network stack",
    "formVlan": "VLAN membership. Can remove the bench port from the segment",
    "formPasswordSetup": "the admin credential. Changing it destroys the "
                         "end-to-end CVE-2019-19823 demonstration, which "
                         "depends on admin/admin being the value decoded from "
                         "this unit's own flash",
    "formUpload": "firmware upload; boa carries DownloadRFW. This is the one "
                  "that bricks",
    "formUploadConfig": "configuration restore; sscanf over an uploaded file",
    "formSaveConfig": "commits the configuration, so anything the sweep "
                      "changed earlier would be made durable by it",
    "formOpMode": "operating mode (router/AP/bridge) and a reboot with it",
    "formOpMode1": "operating mode; same",
    "formOpMode2": "operating mode; same",
    "formWizard": "the setup wizard writes many fields at once and calls "
                  "system()",
    "formRebootCheck": "reboot",
    "formRebootSchedule": "reboot scheduling",
    # Added 2026-08-18 from the guest's own syscall trace, not from its name.
    # A POST carrying localPin, on THIS unit's build, does:
    #     open("/dev/mtdblock0", O_RDWR); write(fd, ..., 7495)
    #     fork -> sh -c "flash write-current"
    #     fork -> sh -c "sysconf wlaninit wlaninterface"
    # so it commits 7 KB of configuration to flash and restarts the wireless
    # interface. On the 2015 build the same request ends in
    #     fork -> sh -c "reboot -f"
    # instead. Either outcome turns every endpoint after it in the sweep into
    # "connection refused", which is the false-negative this whole file exists
    # to prevent -- and the flash write is durable whether or not formSaveConfig
    # is ever reached.
    "formWsc": "WPS. Measured under emulation to write 7,495 bytes to "
               "/dev/mtdblock0, run `flash write-current`, and re-init wlan0; "
               "the 2015 build reboots instead. Durable, and it can drop the "
               "operator's own link mid-sweep",
}

# The three endpoints P3-13's own prediction names as "write" ones. Probing the
# set the test names, rather than a set this file invented, is the difference
# between answering the registered question and answering a nearby one.
NAMED_WRITE_ENDPOINTS = {"formUpload", "formPasswordSetup", "formSaveConfig"}

# Anything that would turn a parameter into a second command. A reconnaissance
# sweep has no business carrying one, and the check is here rather than in the
# operator's memory.
SHELL_METACHARACTERS = set(";|&`$><\n\r\\'\"")

BODY_KEEP = 512          # bytes of body kept per response
CONNECT_TIMEOUT = 6.0


class ProbeError(Exception):
    pass


# Every request and response, appended as it happens, independently of whichever
# group is running.
#
# Added 2026-08-17 after a run that stopped mid-sweep wrote NOTHING. The web
# server stopped accepting at endpoint 60 of 64, the control caught it and the
# run halted -- correctly -- and then `main` returned on the exception before
# reaching the line that writes the transcript. So the tool detected the
# interesting event and destroyed the evidence of it in the same breath: fifty-
# nine responses, each with its elapsed_ms, and the one that had taken seconds
# was in there.
#
# A run that stops is exactly the run whose transcript matters most.
JOURNAL: list[dict[str, Any]] = []

# And the same argument one level up. JOURNAL holds raw requests; the *records*
# are the raw request plus what the group knew about it -- which endpoint name,
# where it came from, and how long the server then took to answer again. Those
# annotations were still being thrown away on a stopped run, because the group
# built its list locally and the exception unwound past the return.
#
# So the list lives here and the groups append into it as they go. The
# measurement that exists to describe a stall must survive the stall.
RECORDS: list[dict[str, Any]] = []


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
    record: bool = True,
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
        if record:
            JOURNAL.append(out)
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
    if record:
        JOURNAL.append(out)
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


# The redirect parameter is NOT `submit-url` for every handler, and a guard that
# assumes it is has exactly one hole -- which is the handler that most needs the
# guard.
#
# Measured 2026-08-18 under emulation, with controls: five of this build's 57
# handlers remove the web server when their redirect parameter is absent, and
# all five die at the same instruction storing to the same address, the pooled
# empty-string literal at 0x004725d0, which lives in a PT_LOAD mapped R-X. Four
# of them take `submit-url` and were already covered. `formSchedule` takes
# `webpage`, so this guard let it through -- and `formSchedule` is also the one
# handler that dies *with* a well-formed `submit-url` present, because
# `submit-url` is not the parameter it reads.
#
# The names come from the recovered dispatch table's own string lists rather
# than from a habit: `reports/ghidra-formtable-unit-2018.json`, cross-read
# against `tools/formtable-scan.py`. One entry today; the shape is a map so that
# the next one found is a line rather than an argument.
# → notes/submit-url-overflow.md, reports/crash-triage-unit-2018.json
REDIRECT_PARAM = {"formSchedule": "webpage"}
DEFAULT_REDIRECT_PARAM = "submit-url"


def redirect_param(target: str) -> str:
    return REDIRECT_PARAM.get(target.rsplit("/", 1)[-1], DEFAULT_REDIRECT_PARAM)


def check_post(target: str, params: dict[str, str],
               allow_destructive: bool = False) -> None:
    want = redirect_param(target)
    if "/boafrm/" in target and want not in params:
        raise ProbeError(
            f"refusing POST {target} without {want}. When that parameter is "
            "absent the handler strcpy()s \"/status.htm\" into the pointer the "
            "accessor returned, and for an absent parameter that pointer is a "
            "read-only string literal (notes/submit-url-overflow.md). Measured "
            "under emulation on 2026-08-18: SIGSEGV, one request, no payload, "
            "and every endpoint probed afterwards answers as if it did not "
            f"exist. This handler's redirect parameter is {want!r}, not "
            f"necessarily {DEFAULT_REDIRECT_PARAM!r}."
        )
    name = target.rsplit("/", 1)[-1]
    if name in HAZARDOUS and not allow_destructive:
        raise ProbeError(
            f"refusing POST {target}: {HAZARDOUS[name]}.\n"
            "  A POST runs the handler, and absent parameters do not mean the "
            "handler does nothing -- the accessors return their defaults and it "
            "writes those.\n"
            "  This is not the configuration-changes-and-a-snapshot-attributes-it "
            "case. Pass --allow-destructive if that is genuinely the decision, "
            "and take a 64 KiB snapshot either side first (RUNBOOK 8.12.3)."
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


def wait_ready(host: str, port: int, budget: float = 45.0) -> dict[str, Any]:
    """Poll until the web server answers again, and report how long that took.

    `boa` here is one process. A handler that calls system() or execl() does not
    return to the accept loop until the child does, so for that whole interval
    the server answers nobody -- and with the backlog full, new connections are
    refused outright. A sweep that fires the next POST immediately therefore
    measures its own impatience.

    Sleeping a fixed two seconds between POSTs would work around that. Waiting
    for readiness instead *measures* it: the number this returns is how long
    that endpoint occupied the only web server the device has, from an
    unauthenticated request carrying no parameters. That is the finding, not the
    obstacle.
    """
    t0 = time.monotonic()
    tries = 0
    while time.monotonic() - t0 < budget:
        tries += 1
        r = raw_request(host, port, "GET", "/", timeout=2.0, record=False)
        if r.get("status") is not None:
            return {"ready": True, "stall_s": round(time.monotonic() - t0, 2),
                    "polls": tries}
        time.sleep(0.5)
    return {"ready": False, "stall_s": round(time.monotonic() - t0, 2),
            "polls": tries, "budget_s": budget}


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
                    need_direct: bool = False, tries: int = 3,
                    gap: float = 6.0) -> dict[str, Any]:
    # Retried, and every attempt kept. `boa` on this unit is ONE process
    # (`boa: starting server pid=350, port 80`), so a handler that calls
    # system() blocks the accept loop for as long as the command runs; the
    # listen backlog fills and new connections are refused. To a single-shot
    # control that is indistinguishable from a web server that has died.
    #
    # Seen on 2026-08-17: the sweep stopped at endpoint 60 of 64 with
    # ConnectionRefusedError, and the device was answering 200 again a minute
    # later. Both readings are worth recording and they are not the same
    # finding, so the retry is not a loosening of the check -- it is the check
    # learning to tell them apart. If every attempt fails it still stops.
    attempts: list[dict[str, Any]] = []
    c: dict[str, Any] = {}
    for i in range(max(1, tries)):
        if i:
            time.sleep(gap)
        c = control(host, port)
        attempts.append({"attempt": i + 1, "reachable": c["reachable"],
                         "error": c.get("error", ""),
                         "elapsed_ms": c.get("elapsed_ms")})
        if c["reachable"]:
            break
    c["attempts"] = attempts
    if len(attempts) > 1 and c["reachable"]:
        c["recovered_after"] = len(attempts)
        print(f"  note  control {where}: refused, then answered on attempt "
              f"{len(attempts)}. The server was BUSY, not dead - and a "
              f"single-shot control would have called it dead", file=sys.stderr)
    if not c["reachable"]:
        raise ProbeError(
            f"control failed {where} on all {len(attempts)} attempts "
            f"{gap:.0f}s apart: {c.get('error') or 'no HTTP status line'}.\n"
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
    out = RECORDS
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


def group_endpoints(host: str, port: int, allow_post: bool,
                    allow_destructive: bool = False) -> list[dict[str, Any]]:
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

    out = RECORDS
    out.append({"probe": "endpoints-meta", **meta,
                "extra_from_string_extraction": extra,
                "cve_spellings": cve_spellings})
    plan = ([(n, "root_form") for n in names]
            + [(n, "string-extraction-only") for n in extra]
            + [(n, "CVE text spelling") for n in cve_spellings]
            + [(n, "dispatch-table spelling") for n in real_spellings])

    skipped = [n for n, _ in plan if n in HAZARDOUS] if allow_post else []
    out[0]["hazardous_skipped"] = skipped
    out[0]["hazardous_reasons"] = {n: HAZARDOUS[n] for n in skipped}
    # A sweep that silently covers 44 of 57 reads as a complete census. The
    # count and the names go in the transcript's first record, before any
    # result, so a reader meets the gap before they meet the findings.
    if skipped:
        print(f"  note  {len(skipped)} of {len(plan)} endpoints will not be "
              f"POSTed: {', '.join(skipped)}", file=sys.stderr)

    # Every 5 when POSTing, every 20 when not. A POST runs the handler, so the
    # window in which the device can stop answering is a window this sweep
    # opened; 20 requests of it is 20 results that have to be re-run.
    step = 5 if allow_post else 20
    for i, (name, origin) in enumerate(plan):
        if i and i % step == 0:
            require_control(host, port, f"before endpoint {i} of {len(plan)}")
        target = f"/boafrm/{name}"
        if allow_post and name in HAZARDOUS and not allow_destructive:
            out.append({"probe": "endpoint", "name": name, "origin": origin,
                        "skipped": "hazardous", "reason": HAZARDOUS[name],
                        "method_note": "not sent; see RUNBOOK 8.12.12"})
            continue
        if allow_post:
            # Not a fixed `submit-url`: the parameter a handler defaults by
            # writing into the returned pointer is per-handler, and sending the
            # wrong name is indistinguishable from sending nothing. See
            # REDIRECT_PARAM.
            params = {redirect_param(target): "/status.htm"}
            check_params(params)
            check_post(target, params, allow_destructive)
            r = raw_request(host, port, "POST", target, body=urlencode(params))
            r["method_note"] = (
                f"POST with {redirect_param(target)} only; the handler ran")
            # How long this one endpoint kept the device's only web server to
            # itself. Recorded per endpoint, in the same run, unauthenticated
            # and with no parameters beyond submit-url.
            r["server"] = wait_ready(host, port)
            if not r["server"]["ready"]:
                raise ProbeError(
                    f"after POST {target} the web server did not answer within "
                    f"{r['server']['budget_s']:.0f}s. Stopping: that is either a "
                    "handler that does not return or a server that has gone, and "
                    "either way nothing measured after it is about the next "
                    "endpoint")
        else:
            r = raw_request(host, port, "GET", target)
            r["method_note"] = "GET; the handler's parameter processing may not run"
        out.append({"probe": "endpoint", "name": name, "origin": origin, **r})
    return out


def handler_sink_profile() -> dict[str, list[str]]:
    """Which sinks each `/boafrm/` handler reaches, from the committed report.

    Used to split the endpoint list into "reconfigures the device" and "does
    not" on evidence rather than on whether the name contains the word `Setup`.
    A handler that calls system() or execl() is running ifconfig / route /
    iptables / flash; one that calls neither is not.
    """
    doc = json.loads(SINKS.read_text("utf-8"))
    sinks = doc.get("sinks")
    if not isinstance(sinks, dict):
        raise ProbeError(f"{SINKS} has no 'sinks' object; its shape changed")
    prof: dict[str, list[str]] = {}
    for sink_name, d in sinks.items():
        for cs in d.get("call_sites") or []:
            if cs.get("is_handler") and cs.get("caller"):
                prof.setdefault(cs["caller"], []).append(sink_name)
    if not prof:
        raise ProbeError(
            f"{SINKS} lists no handler call sites at all. Either the report was "
            "generated before BoaFormTable named the handlers, or the "
            "'is_handler' field moved -- and a classification built on an empty "
            "profile would call every endpoint read-only")
    return {k: sorted(set(v)) for k, v in prof.items()}


def group_writes(host: str, port: int) -> list[dict[str, Any]]:
    """P3-13 -- are the *write* endpoints outside the gate, like the read ones?

    The prediction is that the gate only looks for `.htm` / `.asp` in the URI,
    so write-class handlers sit outside it exactly as read-class ones do. Its
    refutation is "write endpoints blocked while read ones are not -> the gate
    is not a plain URI string test".

    The obvious way to test that is to POST the write handlers, and it is the
    wrong way: it runs them. But the claim is about the *gate*, and the gate
    decides in process_header_end from the URI alone, before handleForm is ever
    reached. So each name is probed in two URI shapes with GET:

        /boafrm/formX        -- no `.htm` anywhere -> the gate should not run
        /boafrm/formX.htm    -- contains `.htm`    -> the gate should run

    If the second flips to `302 -> login.htm` while the first does not, the gate
    is a URI string test and the endpoint's write-ness had no bearing on it --
    which is exactly the demonstration `/config.dat` versus `/config.dat.htm`
    already gave for a non-form path.

    GET never reaches handleForm on this build (every `/boafrm/` GET redirects
    in translate_uri), so **not one handler runs in this group**.
    """
    names, meta = load_endpoints()
    prof = handler_sink_profile()

    def classify(n: str) -> str:
        sinks = prof.get(f"form_{n}") or prof.get(n) or []
        spawns = [s for s in sinks if s in ("system", "popen", "execl", "execlp",
                                            "execle", "execv", "execvp", "execve")]
        return "spawns" if spawns else "quiet"

    groups = {n: classify(n) for n in names}
    n_spawn = sum(1 for v in groups.values() if v == "spawns")
    out = RECORDS
    out.append({
        "probe": "writes-meta", **meta,
        # Two groupings, and the difference between them matters more than
        # either. The first is what the register's own text names; the second is
        # what a committed report can actually measure.
        "named_by_P3_13": sorted(NAMED_WRITE_ENDPOINTS & set(names)),
        "classifier": "handler reaches a process-spawning sink in "
                      + str(SINKS.relative_to(REPO)),
        "classifier_measures": "spawning a process, NOT writing configuration",
        "classifier_limit":
            "A handler can persist configuration through apmib_set without "
            "spawning anything, and formPasswordSetup is exactly that case: its "
            "only tracked sink is strcpy, so this classifier calls it 'quiet' "
            "while it plainly writes the admin credential. The split is a proxy "
            "and it is reported as one. Naming which handlers write MIB needs an "
            "apmib_set caller census, which no committed report carries -- "
            "PROGRESS carried-forward.",
        "spawns": sorted(n for n, v in groups.items() if v == "spawns"),
        "quiet": sorted(n for n, v in groups.items() if v == "quiet"),
        "counts": {"spawns": n_spawn, "quiet": len(names) - n_spawn,
                   "no_sink_profile": sum(
                       1 for n in names
                       if not (prof.get(f"form_{n}") or prof.get(n)))},
        "method_note": "GET only. GET never reaches handleForm on this build, "
                       "so no handler runs in this group",
    })
    missing = NAMED_WRITE_ENDPOINTS - set(names)
    if missing:
        raise ProbeError(
            f"P3-13's prediction names {sorted(missing)}, which the recovered "
            "root_form[] does not contain. Either the register means a different "
            "build or the table is short -- and comparing 'write endpoints' "
            "against a set missing the ones the test names proves nothing")
    if n_spawn == 0 or n_spawn == len(names):
        raise ProbeError(
            f"the classifier put all {len(names)} endpoints in one class, so it "
            "separates nothing and the comparison it exists to make cannot be "
            "made")

    for i, name in enumerate(names):
        if i and i % 20 == 0:
            require_control(host, port, f"before write-probe {i} of {len(names)}")
        for suffix in ("", ".htm"):
            r = raw_request(host, port, "GET", f"/boafrm/{name}{suffix}")
            out.append({"probe": "write-endpoint", "name": name,
                        "klass": groups[name],
                        "named_by_test": name in NAMED_WRITE_ENDPOINTS,
                        "uri_shape": "bare" if not suffix else "with .htm", **r})
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
    # --------------------------------------------------------------------
    # The unanchored-exemption test, added 2026-08-17 after the morning round.
    #
    # The morning tried twelve shapes that smuggle an exemption string into the
    # path of a *protected* page. All twelve failed, and the conclusion drawn
    # was "the comparison must be anchored or length-limited somewhere". That
    # conclusion is wrong, and the reason the shapes failed is different: the
    # path is normalised before the gate sees it, so `/login.htm/../password.htm`
    # is already `/password.htm` by then and the substring is gone.
    #
    # BoaXref on process_header_end lists ten .htm names. Five of the ten
    # (notice, notice_frame, iLogin, iReboot, iLink) are not shipped in the
    # 143-file bundle at all. If the remaining five are matched UNANCHORED, then
    # `status.htm` also exempts `wan_status.htm` and `Connect_status.htm` --
    # which is exactly the seven pages the morning found served without
    # credentials, and exactly the sixty-nine it found blocked. Seventy-six
    # shipped pages, no error in either direction.
    #
    # That is a fit to existing data. These two requests are the part it did not
    # see, and either one can refute it:
    #
    #   an absent .htm with no exemption substring -> the gate runs -> login.htm
    #   an absent .htm CONTAINING one              -> exempt -> home.htm
    #
    # If the second answers login.htm, the model is dead and the morning's
    # reading stands.
    cases += [
        ("UNANCHORED: absent .htm, no exemption substring (expect login.htm)",
         "GET", "/zzqq.htm"),
        ("UNANCHORED: absent .htm containing 'status.htm' (expect home.htm)",
         "GET", "/zzqq_status.htm"),
        ("UNANCHORED: absent .htm containing 'login.htm'",
         "GET", "/zzqq_login.htm"),
        ("UNANCHORED: absent .htm containing 'index.htm'",
         "GET", "/zzqq_index.htm"),
        ("control for the pair: a shipped page that IS exempt",
         "GET", "/wan_status.htm"),
        ("control for the pair: a shipped page that is NOT",
         "GET", "/password.htm"),
        # Five names the gate references that the bundle does not ship. If one
        # of them answers unlike an ordinary absent page, the bundle is not the
        # whole document root.
        ("gate names it, bundle does not ship it", "GET", "/notice.htm"),
        ("gate names it, bundle does not ship it", "GET", "/iLogin.htm"),
        ("gate names it, bundle does not ship it", "GET", "/iReboot.htm"),
        # process_header_end also references five /boafrm/ names -- formUpload,
        # formUploadConfig and the three *Redirect ones. Whatever it does with
        # them happens before handleForm, so a GET is enough to see whether the
        # gate treats them unlike the other 52.
        ("gate names this handler: formUpload", "GET", "/boafrm/formUpload"),
        ("gate names this handler: formUploadConfig", "GET",
         "/boafrm/formUploadConfig"),
        ("gate names this handler: formOpdRedirect", "GET",
         "/boafrm/formOpdRedirect"),
        ("a handler the gate does NOT name, for comparison", "GET",
         "/boafrm/formWsc"),
    ]

    # --------------------------------------------------------------------
    # The question the unanchored result raises, and the one the morning round
    # could not ask because it used the wrong strings.
    #
    # On 2026-08-17 morning, P2-2 tried `/password.htm?login=1`. The exemption
    # tokens carry the extension -- `login.htm`, not `login` -- so that request
    # contained no exemption string and its 302 proved nothing about the query.
    #
    # If the gate tests the URI *before* the query is split off, then appending
    # `?x=status.htm` to a protected page is an authorisation bypass, and it
    # needs no traversal, no encoding and no normalisation trick. If it tests
    # the path only, every one of these stays 302 -> login.htm.
    #
    # These are GETs against pages the morning confirmed are gated
    # (/password.htm, /tcpiplan.htm, /upload.htm all answered 302 -> login.htm).
    # Nothing is written and no handler runs.
    for page in ("/password.htm", "/tcpiplan.htm", "/upload.htm"):
        cases += [
            (f"BYPASS?: {page} with an exemption string in the query",
             "GET", f"{page}?x=status.htm"),
            (f"BYPASS?: {page} with a bare exemption string in the query",
             "GET", f"{page}?status.htm"),
            (f"BYPASS?: {page} with an exemption string in a fragment",
             "GET", f"{page}#status.htm"),
            (f"BYPASS?: {page} with an exemption string after a semicolon",
             "GET", f"{page};status.htm"),
            (f"BYPASS?: {page} with an exemption string as a path suffix",
             "GET", f"{page}/status.htm"),
        ]
    cases += [
        ("BYPASS control: the gated page, untouched", "GET", "/password.htm"),
        ("BYPASS control: an exempt page, untouched", "GET", "/status.htm"),
    ]

    out = RECORDS
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
    out = RECORDS
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
    "control": lambda h, p, a: [control(h, p)],
    "fingerprint": lambda h, p, a: group_fingerprint(h, p),
    "endpoints": lambda h, p, a: group_endpoints(h, p, a.allow_post,
                                                 a.allow_destructive),
    "gate": lambda h, p, a: group_gate(h, p),
    "writes": lambda h, p, a: group_writes(h, p),
    "ssdp": lambda h, p, a: group_ssdp(h, p),
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
    ap.add_argument("--allow-destructive", action="store_true",
                    help="also POST the handlers on the refusal list -- LAN "
                         "addressing, the admin password, firmware and config "
                         "upload, operating mode, reboot. Each is refused by "
                         "name with its reason; this overrides all of them at "
                         "once, which is why it is a separate flag from "
                         "--allow-post and why the transcript records it")
    ap.add_argument("-o", "--output", help="JSON transcript (recommended)")
    args = ap.parse_args(argv)
    if args.allow_destructive and not args.allow_post:
        print("bench-probe: --allow-destructive without --allow-post does "
              "nothing; the refusal list only applies to POSTs", file=sys.stderr)
        return 2

    records: list[dict[str, Any]] = RECORDS
    stopped: dict[str, Any] | None = None
    try:
        if args.group != "control":
            # SSDP is the group that cannot survive a router in the path at all,
            # so it refuses; the rest warn, because a warning that stops work is
            # worse than one that is read.
            require_control(args.host, args.port, "before the run",
                            need_direct=(args.group == "ssdp"))
        records = GROUPS[args.group](args.host, args.port, args)
        if args.group not in ("control", "ssdp"):
            # The spread goes first: `control()` sets "probe" itself, so putting
            # the literal first lets it be overwritten and the after-run control
            # is indistinguishable from the before-run one in the transcript.
            # Caught by the guard suite, which asserts the record is there.
            records.append({**require_control(args.host, args.port, "after the run"),
                            "probe": "control-after"})
    except ProbeError as e:
        # Falls through to write the transcript. The run that stopped is the run
        # whose transcript matters most, and until 2026-08-17 this branch
        # returned before reaching the writer, discarding fifty-nine responses
        # and the elapsed_ms that would have named the slow one.
        stopped = {"reason": str(e), "requests_before_stopping": len(JOURNAL)}
        print(f"bench-probe: {e}", file=sys.stderr)

    doc = {
        "producer": "bench-probe/1",
        "group": args.group,
        "host": args.host,
        "port": args.port,
        "allow_post": args.allow_post,
        "allow_destructive": args.allow_destructive,
        "stopped": stopped,
        "records": records,
        # Every request this process made, in order, whether or not the group
        # that made it finished. Duplicates `records` on a clean run, on purpose.
        "journal": JOURNAL,
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
        print(f"wrote {args.output}"
              + (f"  ({len(JOURNAL)} requests, run STOPPED)" if stopped else ""))
    else:
        print("  (no --output: nothing was recorded. A probe whose response is "
              "not kept is not evidence)", file=sys.stderr)

    if stopped:
        # The slowest requests before the stop, because on a single-process
        # server the thing that stopped it is usually the thing that took the
        # longest just before.
        slow = sorted((r for r in JOURNAL if r.get("elapsed_ms") is not None),
                      key=lambda r: -r["elapsed_ms"])[:5]
        print("\n  slowest requests before the stop:", file=sys.stderr)
        for r in slow:
            print(f"    {r['elapsed_ms']:>7} ms  {r['method']} {r['target']}",
                  file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
