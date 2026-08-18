#!/usr/bin/env python3
"""Call one IGD SOAP action and record exactly what came back.

Why a tool rather than a curl line
----------------------------------
`P6-1` and `P8-7` both send `AddPortMapping` to `/bin/miniigd` on this unit, and
between them they need the same request to be sent twice with one field changed.
Three things about that make a hand-typed `curl` the wrong instrument, and all
three have already cost this project a session:

  * **The control URL in the working notes was wrong for a year.**
    `/upnp/control/WANIPConn1` is `miniupnpd`'s path; this binary answers on
    `/upnp/control/WANIPConnection`, and the wrong one returns a clean 404 that
    reads as "this device has no UPnP control surface" with the port open the
    whole time. So the path is not typed here, it is read out of the device's own
    description document and the tool refuses to guess.

  * **A field this project puts shell metacharacters into must not be sent by
    accident.** `--inject` is a separate flag from the value: a run without it
    refuses any argument containing a backtick, `$(`, `;`, `|` or a newline. A
    benign baseline and a deliberate injection are then different commands in the
    log rather than one command with a different string in it.

  * **A mapping that is created has to be deleted in the same run.** `--cleanup`
    pairs `AddPortMapping` with `DeletePortMapping` on the same three keys and
    reports whether the delete was accepted, because "I meant to remove it" is
    not a record.

What it does not do
-------------------
It sends one action. It does not sweep, it does not retry, and it has no payload
of its own: every argument comes from the command line, so the transcript in
`BENCH-LOG.md` is the whole of what was sent.

    tools/upnp-soap.py --host 10.1.1.1 --describe
    tools/upnp-soap.py --host 10.1.1.1 --action GetGenericPortMappingEntry \
        --arg NewPortMappingIndex=0
    tools/upnp-soap.py --host 10.1.1.1 --action AddPortMapping \
        --arg NewExternalPort=8080 --arg NewInternalClient=10.1.1.1 ...
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request

# Actions this tool will send. Anything else is a typo or a different service,
# and a typo that reaches the device as a SOAPAction header produces a 401/500
# that reads like a finding.
ACTIONS = {
    "GetGenericPortMappingEntry",
    "GetSpecificPortMappingEntry",
    "AddPortMapping",
    "DeletePortMapping",
    "GetExternalIPAddress",
    "GetStatusInfo",
    "GetNATRSIPStatus",
}

# The shapes that turn a value into a command. Refused unless --inject is given.
META = re.compile(r"[`;|&\n\r]|\$\(")

ENVELOPE = (
    '<?xml version="1.0"?>\n'
    '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"'
    ' s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">\n'
    " <s:Body>\n"
    '  <u:{action} xmlns:u="{service}">\n'
    "{args}"
    "  </u:{action}>\n"
    " </s:Body>\n"
    "</s:Envelope>\n"
)


class Refused(Exception):
    """A request this tool will not send, with the reason attached."""


def describe(host: str, port: int, timeout: float) -> dict:
    """Read the control URL and service type off the device, never assume them."""
    url = f"http://{host}:{port}/picsdesc.xml"
    with urllib.request.urlopen(url, timeout=timeout) as r:
        body = r.read().decode("utf-8", "replace")
        server = r.headers.get("Server", "")
    services = re.findall(
        r"<serviceType>([^<]+)</serviceType>.*?<controlURL>([^<]+)</controlURL>",
        body, re.S)
    wan = [(s, c) for s, c in services if "WANIPConnection" in s]
    if not wan:
        raise Refused(
            f"{url} carries no WANIPConnection service, so there is no control "
            "URL to call. Either this is not an IGD or miniigd is not the thing "
            "answering")
    return {
        "description_url": url,
        "server_header": server,
        "services": [{"serviceType": s, "controlURL": c} for s, c in services],
        "wan_service": wan[0][0],
        "wan_control_url": wan[0][1],
        "description_bytes": len(body),
    }


def call(host: str, port: int, control_url: str, service: str, action: str,
         args: list[tuple[str, str]], timeout: float) -> dict:
    body = ENVELOPE.format(
        action=action, service=service,
        args="".join(f"   <{k}>{v}</{k}>\n" for k, v in args))
    url = f"http://{host}:{port}{control_url}"
    req = urllib.request.Request(
        url, data=body.encode("utf-8"), method="POST",
        headers={
            "Content-Type": 'text/xml; charset="utf-8"',
            "SOAPAction": f'"{service}#{action}"',
        })
    out: dict = {"url": url, "action": action, "sent": body}
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out["status"] = r.status
            out["body"] = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        out["status"] = exc.code
        out["body"] = exc.read().decode("utf-8", "replace")
    except OSError as exc:
        out["status"] = None
        out["error"] = str(exc)
        return out
    # A SOAP fault is a 500 with a UPnPError code, and it is an answer, not a
    # failure: "the version validates this field" arrives in exactly that shape.
    m = re.search(r"<errorCode>(\d+)</errorCode>", out["body"])
    if m:
        out["upnp_error"] = int(m.group(1))
        d = re.search(r"<errorDescription>([^<]*)</errorDescription>", out["body"])
        out["upnp_error_description"] = d.group(1) if d else None
    out["fields"] = dict(re.findall(r"<(New[A-Za-z]+)>([^<]*)</New[A-Za-z]+>",
                                    out["body"]))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Call one IGD SOAP action.")
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, default=52869)
    ap.add_argument("--timeout", type=float, default=8.0)
    ap.add_argument("--describe", action="store_true",
                    help="read and print the description document, send nothing")
    ap.add_argument("--action", help=f"one of: {', '.join(sorted(ACTIONS))}")
    ap.add_argument("--arg", action="append", default=[], metavar="NAME=VALUE")
    # Added 2026-08-19, immediately after it was needed. A backtick payload typed
    # on a command line is expanded by the LOCAL shell before this process sees
    # it, and the failure is silent and total: on the first attempt at P6-1 the
    # 25-byte payload arrived here as 431 bytes of the local ping's stdout, which
    # took miniigd down and destroyed the test. Reading the value from a file is
    # the only form that has no shell between the bytes and the socket.
    ap.add_argument("--arg-file", action="append", default=[], metavar="NAME=PATH",
                    help="take an argument's value from a file, verbatim, with no "
                         "shell in the path")
    ap.add_argument("--inject", action="store_true",
                    help="permit shell metacharacters in an argument value")
    ap.add_argument("--json", help="write the whole exchange here")
    args = ap.parse_args(argv)

    try:
        desc = describe(args.host, args.port, args.timeout)
        if args.describe:
            print(json.dumps(desc, indent=2))
            return 0
        if not args.action:
            ap.error("--action is required unless --describe")
        if args.action not in ACTIONS:
            raise Refused(
                f"{args.action!r} is not an action this tool sends. Known: "
                + ", ".join(sorted(ACTIONS)))
        pairs = []
        for a in args.arg:
            if "=" not in a:
                raise Refused(f"--arg {a!r} is not NAME=VALUE")
            k, v = a.split("=", 1)
            if META.search(v) and not args.inject:
                raise Refused(
                    f"argument {k} carries a shell metacharacter and --inject "
                    "was not given. A baseline run and an injection run are "
                    "different commands on purpose")
            pairs.append((k, v))
        # A file-sourced value REPLACES the same name given by --arg, so the
        # caller keeps control of argument order by listing a placeholder there.
        # (This device parses by name -- GetValueFromNameValueList, read at
        # instruction level in notes/three-unread-binaries.md -- so order should
        # not matter; keeping it under the caller's control means the tool does
        # not depend on that being true.)
        for a in args.arg_file:
            if "=" not in a:
                raise Refused(f"--arg-file {a!r} is not NAME=PATH")
            if not args.inject:
                raise Refused(
                    "--arg-file exists so a payload never passes through a "
                    "shell, which is only worth doing for an injection; pass "
                    "--inject to say so")
            k, path = a.split("=", 1)
            with open(path, "rb") as fh:
                v = fh.read().decode("utf-8").rstrip("\n")
            print(f"  (payload for {k}: {len(v)} bytes from {path}, "
                  f"{v.count(chr(10))} newlines)")
            for i, (name, _) in enumerate(pairs):
                if name == k:
                    pairs[i] = (k, v)
                    break
            else:
                pairs.append((k, v))

        res = call(args.host, args.port, desc["wan_control_url"],
                   desc["wan_service"], args.action, pairs, args.timeout)
        doc = {"producer": "upnp-soap", "schema": 1,
               "describe": desc, "injected": bool(args.inject), "result": res}
        text = json.dumps(doc, indent=2)
        if args.json:
            with open(args.json, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text + "\n")
            print(f"wrote {args.json}")
        print(f"POST {res['url']}")
        print(f"  SOAPAction {desc['wan_service']}#{args.action}")
        for k, v in pairs:
            print(f"  {k} = {v}")
        print(f"  -> HTTP {res.get('status')}")
        if "error" in res:
            print(f"  -> {res['error']}")
        if "upnp_error" in res:
            print(f"  -> UPnPError {res['upnp_error']} "
                  f"{res.get('upnp_error_description')}")
        for k, v in (res.get("fields") or {}).items():
            print(f"  <- {k} = {v}")
        return 0
    except Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
