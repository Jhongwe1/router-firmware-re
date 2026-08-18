#!/usr/bin/env python3
"""Send the parameters the gate itself named, at lengths that matter, and record
what stops answering.

Why this is not a fuzzer in the usual sense
-------------------------------------------
The W07 plan is explicit: *a two-hundred-line loop is enough, and writing a
framework is out of scope*. What makes a campaign worth running here is not
mutation cleverness, it is that **the input set is computed rather than
imagined**:

  * the endpoints are the 57 entries of the recovered `root_form[]`, not the
    output of `strings | grep form`;
  * the parameter names are the ones `BoaGate` attributes to each handler in
    `reports/ghidra-gate-*.json`, so every request exercises a path some rule
    already claims reaches a sink;
  * the *absence* dimension exists because of what 2026-08-18 measured: five
    handlers die on a POST that omits one parameter, and the reason is a
    `strcpy` into the pooled empty-string literal, which lives in a segment
    mapped `R-X`. A length ladder alone never finds that -- the value has to be
    missing, not long.

Four dimensions, and each one is a different question
----------------------------------------------------
  ladder   the same parameter at 8 / 100 / 260 / 800 / 4096 bytes.  100 and 260
           are not round numbers: `lastUrl[100]` is the buffer W04 measured on
           V2.1.2, and 258 is the stack destination `BoaGate` reports for
           `form_formFilter`'s `ip6addr`.
  cyclic   a de Bruijn-style pattern at the largest length, so that if anything
           *does* land on a return address the offset is readable from the
           register dump instead of requiring a bisection.  This tool does not
           read registers -- `tools/crash-triage.py` does -- so what it produces
           is a case to hand over, not a verdict.
  absent   every declared parameter of the handler except one.  The one left
           out is the variable.
  protocol P4-8: oversized request line, oversized single header, many headers,
           many parameters, and a Range header.  These are properties of the
           server rather than of a handler, so they are sent once, to a page
           the gate exempts.

The controls, and why the negative one is the load-bearing half
---------------------------------------------------------------
`P4-9`'s refutation condition, re-frozen on 2026-08-18 before this file existed,
reads: *a full round with zero deaths, in which the positive control was also
not flagged, means the survival detection is broken -- fix the harness before
reading the results.*  The original wording named "P4-3's known crash", and P4-3
had been refuted on this build, so the control it named did not exist and the
condition could never be constructed.  The control now is `formSchedule` with no
`webpage` parameter: measured, reproducible, and the only handler-and-body pair
on this build known to remove the server with a well-formed request.

So a round reports nothing unless **both** hold: a handler known to survive
survived, and the handler known to die was detected as dead.
"""

from __future__ import annotations

import argparse
import json
import os
import string
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LADDER = (8, 100, 260, 800, 4096)


def cyclic(n: int) -> str:
    """Three-character de Bruijn cycle: 26*26*26 = 17,576 unique offsets, which
    is four times the longest value this tool sends."""
    out = []
    for a in string.ascii_lowercase:
        for b in string.ascii_lowercase:
            for c in string.ascii_lowercase:
                out.append(a + b + c)
                if len("".join(out)) >= n:
                    return "".join(out)[:n]
    return "".join(out)[:n]


def qemu(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["tools/qemu-env.sh", *args], cwd=REPO,
                          capture_output=True, check=False)


def restart(port: int, alignfix: bool) -> bool:
    qemu("stop")
    qemu("reap")
    if qemu("reset").returncode != 0:
        return False
    cmd = ["serve", str(port)] + (["--alignfix"] if alignfix else [])
    return qemu(*cmd).returncode == 0


def alive(port: int, timeout: float = 4.0) -> bool:
    try:
        with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/login.htm", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not follow 302, and the reason is a measurement this tool got wrong.

    The first path-dictionary run reported GET 200 with a 2,895-byte body for
    every path it tried -- including `/zzqq-not-real.htm`, a name chosen
    precisely because nothing could implement it. urllib follows redirects by
    default, and this build answers any non-exempt path with `302 -> home.htm`,
    so every probe was measuring the gate's redirect and reporting the size of
    the home page. An existence probe that follows redirects cannot distinguish
    "this path exists" from "this path was redirected somewhere that does".

    It was the control that caught it, not the result: sixteen dictionary
    entries agreeing with each other says nothing, and one impossible name
    agreeing with them says everything.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(NoRedirect)


def send(port: int, path: str, body: str | None, headers: dict | None = None,
         timeout: float = 8.0) -> dict:
    url = f"http://127.0.0.1:{port}{path}"
    data = body.encode() if body is not None else None
    req = urllib.request.Request(url, data=data,
                                 method="POST" if data is not None else "GET")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    t0 = time.time()
    try:
        with _OPENER.open(req, timeout=timeout) as r:
            return {"status": r.status, "len": len(r.read()),
                    "location": r.headers.get("Location"),
                    "ms": int((time.time() - t0) * 1000)}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "len": len(e.read() or b""),
                "location": e.headers.get("Location") if e.headers else None,
                "ms": int((time.time() - t0) * 1000)}
    except Exception as e:
        return {"status": None, "len": 0, "ms": int((time.time() - t0) * 1000),
                "error": type(e).__name__}


def gate_params(gate: Path, stack_only: bool = False) -> dict:
    """{handler: sorted[parameter]} from BoaGate's own findings.

    `stack_only` keeps the findings whose destination BoaGate reports as a
    stack slot (`sp-NNN` in its `detail`). That is the population the length
    ladder is aimed at -- a return address lives in the same frame -- and it is
    22 of this build's 134 findings, across 11 functions and 17 parameters.
    Running the ladder over all 134 costs an hour of restarts to ask the wrong
    question of 112 of them.
    """
    d = json.loads(gate.read_text("utf-8"))
    out: dict[str, set] = {}
    for f in d["findings"]:
        if stack_only and "sp-" not in (f.get("detail") or ""):
            continue
        fn = f["function"]
        name = fn[len("form_"):] if fn.startswith("form_") else fn
        out.setdefault(name, set()).add(f["parameter"])
    return {k: sorted(v) for k, v in sorted(out.items())}


def probe_one(port: int, alignfix: bool, path: str, body: str | None,
              headers: dict | None = None) -> dict:
    """One request against a freshly restored environment.

    Restarting for every probe is what makes a result mean anything here: a
    handler that saves configuration changes what the next probe reads, and
    with `--alignfix` on they *do* save. The previous sweep learned that the
    hard way -- the per-probe pristine flash had been an accident of the crash,
    and removing the crash removed it.
    """
    if not restart(port, alignfix):
        return {"harness_error": "serve failed"}
    if not alive(port):
        return {"harness_error": "server did not answer before the probe"}
    r = send(port, path, body, headers)
    time.sleep(0.5)
    r["survived"] = alive(port)
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--gate", default="reports/ghidra-gate-unit-2018.json")
    ap.add_argument("--no-alignfix", action="store_true",
                    help="run without the alignment shim. Off by default here, "
                         "unlike qemu-env.sh: without it every configuration "
                         "write looks like a crash and the whole round is noise")
    ap.add_argument("--dimension", action="append", default=[],
                    choices=["ladder", "cyclic", "absent", "protocol", "paths"],
                    help="repeatable; default is all five")
    ap.add_argument("--limit-handlers", type=int, default=0,
                    help="stop after N handlers (a smoke run, not a result)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if os.geteuid() != 0:
        raise SystemExit("needs root: the environment is a chroot. Run under sudo.")
    alignfix = not args.no_alignfix
    dims = args.dimension or ["ladder", "cyclic", "absent", "protocol", "paths"]
    port = args.port

    params = gate_params(REPO / args.gate)
    stack = gate_params(REPO / args.gate, stack_only=True)
    report = {
        "producer": "paramfuzz",
        "schema_version": "1",
        "profile": "unit-2018",
        "alignfix": alignfix,
        "gate_report": args.gate,
        "dimensions": dims,
        "ladder": list(LADDER),
        "ladder_population": "BoaGate findings whose destination is a stack slot",
        "handlers_from_gate": len(params),
        "parameters_from_gate": sum(len(v) for v in params.values()),
        "handlers_with_stack_destination": len(stack),
        "parameters_with_stack_destination": sum(len(v) for v in stack.values()),
        "controls": {},
        "control_problems": [],
        "deaths": [],
        "anomalies": [],
        "requests": 0,
    }

    # ---- controls first. A round that cannot detect the known death is not a
    # round, and finding that out afterwards costs the whole round.
    print("  control  negative: formSchedule with no webpage (must be DETECTED "
          "as dead)", flush=True)
    neg = probe_one(port, alignfix, "/boafrm/formSchedule", "")
    print("  control  positive: formNtp with no body (must SURVIVE)", flush=True)
    pos = probe_one(port, alignfix, "/boafrm/formNtp", "")
    report["controls"] = {"negative": neg, "positive": pos}
    report["requests"] += 2
    if neg.get("survived", True):
        report["control_problems"].append(
            "the negative control survived: formSchedule with no `webpage` is "
            "the one handler+body on this build measured to remove the server "
            "(reports/crash-triage-unit-2018.json). If it is not detected here, "
            "nothing this round reports as 'survived' means anything")
    if not pos.get("survived", False):
        report["control_problems"].append(
            "the positive control died: formNtp with an empty body survives on "
            "this build. Something is wrong with the environment, not with the "
            "handlers")
    if report["control_problems"]:
        Path(args.out).write_text(json.dumps(report, indent=2) + "\n",
                                  encoding="utf-8", newline="\n")
        for p in report["control_problems"]:
            sys.stderr.write("  CONTROL FAILED: " + p + "\n")
        return 2

    def record(kind: str, handler: str, param: str, detail: str, r: dict) -> None:
        report["requests"] += 1
        row = {"dimension": kind, "handler": handler, "parameter": param,
               "detail": detail, **r}
        if r.get("harness_error"):
            report["anomalies"].append(row)
            return
        if not r.get("survived", True):
            report["deaths"].append(row)
            print(f"    DEAD  {kind:<10} {handler:<22} {param:<14} {detail}",
                  flush=True)

    handlers = list(params.items())
    stack_handlers = list(stack.items())
    if args.limit_handlers:
        handlers = handlers[:args.limit_handlers]
        stack_handlers = stack_handlers[:args.limit_handlers]

    if "ladder" in dims:
        nparam = sum(len(v) for _, v in stack_handlers)
        print(f"  ladder   {len(stack_handlers)} handlers x {nparam} "
              f"parameters x {len(LADDER)} lengths (stack destinations "
              "only)", flush=True)
        for h, ps in stack_handlers:
            for p in ps:
                for n in LADDER:
                    body = urllib.parse.urlencode({p: "A" * n, "submit-url": "/status.htm"})
                    record("ladder", h, p, f"{n} bytes",
                           probe_one(port, alignfix, "/boafrm/" + h, body))

    if "cyclic" in dims:
        pat = cyclic(max(LADDER))
        print(f"  cyclic   {len(stack_handlers)} handlers, {len(pat)}-byte "
              "de Bruijn pattern (stack destinations only)", flush=True)
        for h, ps in stack_handlers:
            for p in ps:
                body = urllib.parse.urlencode({p: pat, "submit-url": "/status.htm"})
                record("cyclic", h, p, f"de Bruijn {len}"(pat),
                       probe_one(port, alignfix, "/boafrm/" + h, body))

    if "absent" in dims:
        print("  absent   every declared parameter present except one", flush=True)
        for h, ps in handlers:
            for p in ps:
                body = urllib.parse.urlencode(
                    {q: "/status.htm" if q.endswith("url") else "1"
                     for q in ps if q != p})
                record("absent", h, p, "omitted",
                       probe_one(port, alignfix, "/boafrm/" + h, body))

    if "protocol" in dims:
        print("  protocol P4-8: header and parameter-count bombs", flush=True)
        cases = [
            ("long-uri", "/login.htm?" + "a" * 8192, None, None),
            ("long-header", "/login.htm", None, {"X-Pad": "A" * 8192}),
            ("many-headers", "/login.htm", None,
             {f"X-P{i}": "v" for i in range(200)}),
            ("param-bomb-1k", "/boafrm/formNtp",
             "&".join(f"p{i}=v" for i in range(1000)), None),
            ("param-bomb-100k", "/boafrm/formNtp",
             "&".join(f"p{i}=v" for i in range(100000)), None),
            ("range", "/login.htm", None, {"Range": "bytes=0-" + "9" * 400}),
        ]
        for name, path, body, hdrs in cases:
            record("protocol", "-", name, name,
                   probe_one(port, alignfix, path, body, hdrs))

    if "paths" in dims:
        # P3-8 .. P3-12: the dictionaries other TOTOLINK families answer on.
        # Every one of these predicts 404 on this build; a response is the
        # refutation, and it is the same refutation for all five rows -- that
        # root_form[] is not the only dispatch source.
        print("  paths    other-family dictionaries (P3-8..P3-12, P1-7)",
              flush=True)
        dictionary = [
            ("P3-8", "/boafrm/formPing"), ("P3-8", "/boafrm/formTracert"),
            ("P3-8", "/boafrm/formDiagnosis"), ("P3-8", "/boafrm/formNslookup"),
            ("P3-9", "/formLoginAuth.htm"), ("P3-9", "/cgi-bin/cstecgi.cgi"),
            ("P3-10", "/cstecgi.cgi"), ("P3-11", "/cgi-bin/download.cgi"),
            ("P3-12", "/cgi-bin/luci"), ("P3-12", "/cgi-bin/adm.cgi"),
            ("P1-7", "/goform/formLogin"), ("P1-7", "/goform/setSysAdm"),
            ("P1-7", "/boafrm/formDebug"), ("P1-7", "/boafrm/formFactoryTest"),
            ("P1-7", "/boafrm/formTest"), ("P1-7", "/boafrm/formEngineer"),
            # Three controls, one per response class this dictionary can
            # produce. The first smoke run had only the /boafrm/ one, and it
            # was not enough: every /cgi-bin/ and /goform/ path came back 400,
            # which reads as "something answered" until a path that certainly
            # does not exist comes back 400 as well. A response class shared
            # with a name nobody could have implemented is not evidence of an
            # endpoint.
            ("CONTROL", "/boafrm/formNotARealHandlerZZ"),
            ("CONTROL", "/cgi-bin/zzqq-not-real.cgi"),
            ("CONTROL", "/zzqq-not-real.htm"),
        ]
        # One restart for the whole dictionary: none of these reaches a handler
        # if the prediction holds, and if one does the round stops being cheap
        # anyway. Liveness is re-checked after every request.
        if not restart(port, alignfix):
            report["anomalies"].append({"dimension": "paths",
                                        "harness_error": "serve failed"})
        else:
            hits = []
            for row, path in dictionary:
                # Both verbs. A POST to a path Boa does not treat as a form
                # handler is answered by the request parser, not by the
                # dispatcher, so POST alone cannot distinguish "absent" from
                # "present but not POST-able". GET can.
                g = send(port, path, None)
                p = send(port, path, "submit-url=/status.htm")
                survived = alive(port)
                report["requests"] += 2
                hits.append({"row": row, "path": path,
                             "get": g, "post": p, "survived": survived})
                if not survived:
                    report["deaths"].append({"dimension": "paths", "handler": path,
                                             "parameter": "-", "detail": row,
                                             "get": g, "post": p,
                                             "survived": False})
                    restart(port, alignfix)
            report["path_dictionary"] = hits

    qemu("stop")
    report["deaths_total"] = len(report["deaths"])
    Path(args.out).write_text(json.dumps(report, indent=2) + "\n",
                              encoding="utf-8", newline="\n")
    ndead, nanom = len(report["deaths"]), len(report["anomalies"])
    print(f"\n  {report['requests']} requests, {ndead} deaths, "
          f"{nanom} harness anomalies -> {args.out}")
    for d in report["deaths"]:
        print(f"    {d['dimension']:<9} {d['handler']:<22} {d['parameter']:<14} {d['detail']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
