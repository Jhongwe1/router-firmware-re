#!/usr/bin/env python3
"""Can this router still do its job? -- asked of the device, in one unauthenticated GET.

Why this exists
---------------
On 2026-08-17 an unauthenticated POST round wrote `DHCP_MTU_SIZE = 0` into this
unit's flash.  The WAN interface has come up with `MTU:0` on every boot since:
no DISCOVER, no ARP, not one packet out of `eth1`, and no WAN address.  Four
bench sessions ran between then and 2026-08-19 and **not one of them noticed**,
because every instrument this project owns asks whether the *host* is ready --
toolchain, hashes, serial port, USB Ethernet, isolated segment -- and not one
asks whether the *device* still works.

The finding it produced is closed.  What was open is this file: PROGRESS.md
open item 73.  A session that starts on a router which cannot route is a session
whose every negative result has a second explanation nobody wrote down.

How it asks, and why that path
------------------------------
`GET /config.dat`.  The path carries no `.htm` and no `.asp`, so the
authorisation gate does not run for it (CVE-2019-19822, `P10-1`), and `boa`
creates the file at startup by reading the COMPCS region straight out of flash.
So one unauthenticated request returns the device's entire live configuration,
and this repository already has the decoder for it.

Using a disclosure defect as a health check is deliberate.  The alternative
paths all cost more and prove less: the serial console has no shell, the web UI
needs credentials and renders only some of these fields on any page, and a
telnet shell has to be *opened* by command injection first -- which changes the
device before measuring it.  This changes nothing and needs no credentials.

What it can and cannot tell you
-------------------------------
`config.dat` is written when `boa` starts, from flash.  So this reads the
**persistent** configuration -- exactly the class of breakage that survives a
reboot and therefore the class nobody catches.  It does **not** see runtime
state: an interface manually reconfigured with `ifconfig` this session, a
process that has died, a cable in the wrong socket.  Those need the wire.

Two halves, and the second one is the general fix
-------------------------------------------------
1. **Named assertions**, each with the sentence that says what breaks.  These
   are the fields whose value decides whether the box is a router.
2. **Drift against the frozen baseline** -- every field that differs from the
   pristine 2026-08-16 read, counted and listed.  Half 1 only catches breakage
   somebody has already thought of; `DHCP_MTU_SIZE` was not on anybody's list
   until it had been 0 for two days.  Half 2 catches the next one.

    python3 tools/device-liveness.py                       # ask the device
    python3 tools/device-liveness.py --from-file cfg.bin   # ask a saved copy
    python3 tools/device-liveness.py --json out.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
COMPCS_MAGIC = b"COMPCS"

# The fields that decide whether this box is still a router, each with the
# sentence a reader needs to act on it. Anything without such a sentence does
# not belong here -- a check whose failure does not say what broke sends the
# reader to guess, and guessing is what four sessions did.
PRIMARY = [
    ("DHCP_MTU_SIZE", "1500",
     "the WAN interface's MTU. At 0 the interface comes up unable to transmit: "
     "no DISCOVER, no ARP, zero packets on the wire, no WAN address, on every "
     "boot. This field WAS 0 from 2026-08-17 to 2026-08-19 and nothing noticed"),
    ("WAN_DHCP", "1",
     "the WAN acquires its address by DHCP. If this is 0 the device is not "
     "asking for a lease at all, and 'no lease' means something different"),
    ("OP_MODE", "0",
     "gateway mode. In bridge or WISP mode the routing behaviour under test is "
     "not the behaviour the box is in, and nothing on the wire says so"),
    ("IP_ADDR", "10.1.1.1",
     "the LAN address every command in runsheet.md is addressed to. If this "
     "moved, a whole session of 000s and timeouts has a boring explanation"),
]

# Not a value assertion -- a shape one, because the value is a credential and
# docs/disclosure.md owns whether it is printed. P2-11's own caution field says
# the row must run on a machine whose password is not empty, because A3.11.2
# sets it empty and then a 200 measures D-4 instead. Nothing enforced that.
NONEMPTY = [
    ("USER_PASSWORD",
     "the admin password is empty, so an authorisation result measured now is "
     "measuring the empty-password bypass (D-4), not whatever it claims. "
     "A3.11.2 sets this; restore it before measuring anything about auth"),
]


def is_redacted(value) -> bool:
    """`--disclosure protect` replaces a per-unit identifier with its digest."""
    return isinstance(value, str) and value.startswith("sha256:")


def fetch(host: str, timeout: float, path: str = "/config.dat") -> bytes:
    url = f"http://{host}{path}"
    request = urllib.request.Request(url, headers={"User-Agent": "fwre-liveness/1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def decode(blob_path: Path, mib: Path | None, python: str, offset: str = "0x000000"):
    """Hand the bytes to this repository's own COMPCS decoder."""
    cmd = [python, "-m", "fwrecon", "compcs", str(blob_path),
           "--offset", offset, "--disclosure", "protect", "-f", "json"]
    if mib:
        cmd += ["--mib", str(mib)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise SystemExit(
            "device-liveness: fwrecon could not decode the served config.\n"
            f"  {' '.join(cmd)}\n{proc.stderr.strip()}")
    return json.loads(proc.stdout)


def assess(entries, baseline=None, expect=None, nonempty=None):
    """The judgement, as a pure function -- no device, no network, no fwrecon.

    Every refusal below exists because its absence looks exactly like a pass:

      * an empty decode is not a clean bill of health, it is a decoder pointed
        at the wrong offset;
      * a field this tool asserts on but cannot find is not "fine", it is a
        build whose MIB table does not match the one being read;
      * a baseline that could not be loaded must not silently turn the drift
        half into "nothing drifted".
    """
    checks, problems, drifted = [], [], []
    expect = list(PRIMARY if expect is None else expect)
    nonempty = list(NONEMPTY if nonempty is None else nonempty)
    by_name = {e["name"]: e for e in entries if e.get("name")}

    if not by_name:
        problems.append(
            "the decode produced no named entries at all. That is a decoder "
            "pointed at the wrong offset or a MIB table that does not match "
            "this build -- it is not a healthy device")
        return {"verdict": "UNUSABLE", "checks": checks, "problems": problems,
                "drifted": drifted, "incomparable": [], "fields_seen": 0}

    for name, want, why in expect:
        entry = by_name.get(name)
        if entry is None:
            problems.append(
                f"{name} is not in the decoded configuration. This tool asserts "
                f"on it, so its absence is a tooling failure, not a pass -- {why}")
            continue
        got = str(entry.get("value"))
        checks.append({"field": name, "expected": want, "actual": got,
                       "ok": got == want, "breaks": why})

    for name, why in nonempty:
        entry = by_name.get(name)
        if entry is None:
            problems.append(
                f"{name} is not in the decoded configuration, and this tool "
                f"asserts it is non-empty -- {why}")
            continue
        got = str(entry.get("value") or "")
        checks.append({"field": name, "expected": "<non-empty>",
                       "actual": "<empty>" if not got else "<set>",
                       "ok": bool(got), "breaks": why})

    incomparable = []
    if baseline is not None:
        base = {e["name"]: str(e.get("value")) for e in baseline if e.get("name")}
        if not base:
            problems.append(
                "the baseline decoded to no named entries, so the drift half "
                "reports nothing and that is not the same as nothing drifting")
        else:
            for name in sorted(set(base) | set(by_name)):
                was = base.get(name)
                now = str(by_name[name].get("value")) if name in by_name else None
                # This runs the live decode under --disclosure protect, so a
                # per-unit identifier comes back as a digest while the committed
                # baseline holds the value in the clear. Comparing those two
                # manufactures drift for every redacted field -- five of them on
                # the first real run, which is exactly the sort of noise that
                # trains a reader to stop reading the list. A digest against a
                # cleartext value is not a comparison; say so and count it.
                if is_redacted(was) != is_redacted(now):
                    incomparable.append(name)
                    continue
                if was != now:
                    drifted.append({"field": name, "baseline": was, "now": now})

    failed = [c for c in checks if not c["ok"]]
    if problems:
        verdict = "UNUSABLE"
    elif failed:
        verdict = "BROKEN"
    else:
        verdict = "OK"
    return {"verdict": verdict, "checks": checks, "problems": problems,
            "drifted": drifted, "incomparable": sorted(incomparable),
            "fields_seen": len(by_name)}


def trim(value, width: int = 28):
    text = "<absent>" if value is None else str(value)
    return text if len(text) <= width else text[:width - 3] + "..."


def load_baseline(path: Path):
    if not path.exists():
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    return doc.get("entries") or []


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="10.1.1.1",
                        help="the device's LAN address (default 10.1.1.1)")
    parser.add_argument("--timeout", type=float, default=8.0,
                        help="seconds to wait for the GET. Keep it above the "
                             "10.3 s formWlanSetup taught us about: a short "
                             "timeout is indistinguishable from a dead server")
    parser.add_argument("--from-file", default=None,
                        help="a saved config.dat instead of asking the device")
    parser.add_argument("--offset", default="0x000000",
                        help="region offset inside --from-file (a served "
                             "config.dat starts at 0)")
    parser.add_argument("--baseline",
                        default=str(REPO / "reports" / "compcs-unit-2018.json"),
                        help="the frozen decode to measure drift against")
    parser.add_argument("--no-baseline", action="store_true",
                        help="skip the drift half (the assertions still run)")
    parser.add_argument("--mib", default=None,
                        help="libapmib.so, to name the ids")
    parser.add_argument("--python",
                        default=os.environ.get("FWRE_PY",
                                               str(Path.home() / "fwre-work" /
                                                   "venv" / "bin" / "python")),
                        help="the interpreter fwrecon is installed into")
    parser.add_argument("--json", default=None, help="write the result here")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    source = args.from_file or f"http://{args.host}/config.dat"
    tmp = None
    try:
        if args.from_file:
            blob = Path(args.from_file).read_bytes()
            blob_path = Path(args.from_file)
        else:
            try:
                blob = fetch(args.host, args.timeout)
            except (urllib.error.URLError, OSError) as exc:
                print(f"device-liveness: {args.host} did not serve /config.dat "
                      f"({exc}). That is not a pass and not a failure -- the "
                      "device is off, unplugged, or the segment is not up. "
                      "Nothing here has been measured.", file=sys.stderr)
                return 3
            with tempfile.NamedTemporaryFile(suffix=".dat", delete=False) as handle:
                handle.write(blob)
                tmp = Path(handle.name)
            blob_path = tmp

        offset = int(args.offset, 0)
        if len(blob) < offset + len(COMPCS_MAGIC):
            print(f"device-liveness: {source} returned {len(blob)} bytes, too "
                  "short to be a configuration region. A truncated answer is "
                  "not a healthy device.", file=sys.stderr)
            return 2
        if blob[offset:offset + len(COMPCS_MAGIC)] != COMPCS_MAGIC:
            print(f"device-liveness: {source} does not start with COMPCS at "
                  f"{args.offset} (saw {blob[offset:offset + 8]!r}). Something "
                  "answered, and it did not answer with a configuration -- do "
                  "not read that as the device being fine.", file=sys.stderr)
            return 2

        mib = Path(args.mib) if args.mib else None
        doc = decode(blob_path, mib, args.python, args.offset)
        baseline = None if args.no_baseline else load_baseline(Path(args.baseline))
        if baseline is None and not args.no_baseline:
            print(f"device-liveness: no baseline at {args.baseline}; the drift "
                  "half is not running. Pass --no-baseline to say that was "
                  "intended.", file=sys.stderr)
        result = assess(doc.get("entries") or [], baseline)
        result["source"] = source
        result["bytes"] = len(blob)
        result["baseline"] = None if baseline is None else args.baseline
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)

    if not args.quiet:
        print(f"device-liveness: {source} -> {result['bytes']} bytes, "
              f"{result['fields_seen']} named fields")
        for check in result["checks"]:
            mark = "ok  " if check["ok"] else "FAIL"
            print(f"  {mark}  {check['field']:<16} "
                  f"expected {check['expected']:<12} got {check['actual']}")
            if not check["ok"]:
                print(f"        -> {check['breaks']}")
        for problem in result["problems"]:
            print(f"  STOP  {problem}")
        if result["drifted"]:
            print(f"\n  {len(result['drifted'])} field(s) differ from the frozen "
                  "baseline:")
            for d in result["drifted"]:
                print(f"        {d['field']:<26} {trim(d['baseline'])} -> "
                      f"{trim(d['now'])}")
        if result["incomparable"]:
            print(f"\n  {len(result['incomparable'])} field(s) not compared "
                  "(redacted here, in the clear in the baseline): "
                  + ", ".join(result["incomparable"]))
        print(f"\n  verdict: {result['verdict']}")

    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=2) + "\n",
                                   encoding="utf-8")
    return 0 if result["verdict"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
