#!/usr/bin/env python3
"""POST to every handler in the dispatch table and record which ones the server
does not survive.

Why this can be done at all
---------------------------
`P4-7` was moved out of W06 with a reason that was about cost, not doubt: the
W05 POST round took the web server down twice, nothing on the device respawns
`boa`, and recovery is a power cycle. Fifty-seven endpoints at roughly forty-five
requests per cycle is a bench session spent almost entirely on power cycles.

Under emulation the server is a process and the state is a file, so a restart
costs a second and the sweep is bounded by nothing. That is the whole argument
for having built the environment, and this is the tool that spends it.

What it does NOT establish
--------------------------
`qemu-user` raises SIGBUS on unaligned accesses that the device's MIPS kernel
fixes in its trap handler. A handler that kills `boa` here has **not** been shown
to kill it on silicon, and this tool refuses to phrase it that way: the JSON
field is `died_under_emulation`. Turning that into a statement about the device
takes the device, and the candidate list is the point -- W06 measured a
one-request outage on the hardware (`docs/disclosure.md` D-11) without being able
to say which handler class it belonged to.

The controls, which are not optional
------------------------------------
Three, and the sweep refuses to report anything if they do not hold:

  * a handler the UI uses must answer and survive -- otherwise "it died" means
    "the harness is broken";
  * a handler that does not exist must 404 -- otherwise every result is the
    same result;
  * at least one handler must survive -- a sweep where everything dies is
    measuring the emulator, not the firmware.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _work() -> Path:
    """$FWRE_WORK, or the invoking user's home -- never root's. See _run()."""
    import pwd

    if os.environ.get("FWRE_WORK"):
        return Path(os.environ["FWRE_WORK"])
    user = os.environ.get("SUDO_USER")
    if user and user != "root":
        try:
            return Path(pwd.getpwnam(user).pw_dir) / "fwre-work"
        except KeyError:
            pass
    return Path.home() / "fwre-work"


WORK = _work()
PROFILE_TABLE = {"unit-2018": "ghidra-formtable-unit-2018.json",
                 "v2.1.2": "ghidra-formtable-2.1.2.json"}
# A handler the shipped UI posts to, and one that cannot exist.
LIVE_CONTROL = "formLogin"
DEAD_CONTROL = "formNotARealHandler"


def http(url: str, data: bytes | None = None, timeout: float = 8.0) -> tuple[int, int]:
    """(status, body length). 0 means the connection produced no response."""
    req = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET")
    if data is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, len(r.read())
    except urllib.error.HTTPError as e:
        return e.code, len(e.read() or b"")
    except Exception:
        return 0, 0


def handlers(profile: str) -> list[str]:
    doc = json.loads((REPO / "reports" / PROFILE_TABLE[profile]).read_text("utf-8"))
    out: list[str] = []
    for t in doc.get("tables", []):
        if t.get("role") == "root_form":
            out += [e["name"] for e in t.get("entries", []) if e.get("name")]
    return sorted(set(out))


class Server:
    def __init__(self, profile: str, port: int, quiet: bool, alignfix: bool = False):
        self.profile, self.port, self.quiet = profile, port, quiet
        self.alignfix = alignfix
        self.restarts = 0
        self.failed_restarts = 0

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        # Two things here, and both were bugs first.
        #
        # No nested sudo. This tool needs root, so it is usually already root --
        # and `sudo` from root sets SUDO_USER=root, so qemu-env.sh resolves the
        # work directory to /root/fwre-work and reports "no /var/boa.conf ...;
        # run build" about a directory that never held one. Every restart in the
        # first sweep failed that way, 55 of them, and the message pointed at
        # rebuilding an environment that was fine. Same shape as instrument bug
        # 24: a failure that names the wrong fix.
        #
        # And FWRE_WORK is passed explicitly, so the child does not have to
        # guess from an identity that sudo has already rewritten.
        cmd = [str(REPO / "tools/qemu-env.sh"), "--profile", self.profile, *args]
        if os.geteuid() != 0:
            cmd = ["sudo", "-n", *cmd]
        env = dict(os.environ, FWRE_WORK=str(WORK))
        return subprocess.run(cmd, capture_output=True, text=True, timeout=180, env=env)

    def alive(self) -> bool:
        return http(f"http://127.0.0.1:{self.port}/login.htm")[0] == 200

    def start(self) -> bool:
        # `reap`, not `stop`. stop kills the pid in the pidfile, and a boa that
        # crashed left that pidfile pointing at a corpse -- so stop reported
        # success while the process actually holding the port was still there.
        # Across one 58-handler sweep that produced 32 orphans, the port was held
        # by an arbitrary old one, and every probe after the first crash was
        # answered by a server carrying state from earlier in the run. The
        # results were nonsense that looked exactly like data.
        self._run("reap")
        # `reset`, not just `reap`. A boa killed by SIGBUS leaves the SysV
        # semaphore the MIB cache uses in a state the next one cannot take:
        # it spins on `APMIB Semaphore Lock semop() failed !! [Invalid argument]`
        # and never binds, so `serve` times out and the sweep stalls with a
        # confident-looking "restart failed". Only `reset` drops the segments.
        #
        # It also restores the flash, which is the point rather than a side
        # effect: every probe then starts from the same bytes, and a handler
        # that wrote something cannot change the meaning of the next result.
        self._run("reset")
        serve_args = ["serve", str(self.port)]
        if self.alignfix:
            serve_args.append("--alignfix")
        p = self._run(*serve_args)
        return "is serving" in p.stdout

    def ensure(self) -> bool:
        if self.alive():
            return True
        self.restarts += 1
        for _ in range(3):
            if self.start() and self.alive():
                return True
            time.sleep(1)
        self.failed_restarts += 1
        return False

    def ensure_pristine(self) -> bool:
        """Restart unconditionally, so this probe starts from the pristine flash.

        Only needed once the server stops dying. Without alignfix every probe
        that reached the config serialiser crashed the server, and the crash
        forced a `reset` -- so each handler was measured against untouched flash
        *by accident*, as a side effect of the bug. Fix the alignment and the
        crashes stop, the resets stop with them, and handler N is measured
        against whatever handlers 1..N-1 wrote. The environment's own control
        set caught this within one sweep: USER_NAME came back "" instead of
        "admin", because a POST carrying only `submit-url` makes the handler
        save its empty form fields.
        """
        self.restarts += 1
        for _ in range(3):
            if self.start() and self.alive():
                return True
            time.sleep(1)
        self.failed_restarts += 1
        return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--profile", choices=sorted(PROFILE_TABLE), default="unit-2018")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--param", default="submit-url=/wireless.htm",
                    help="the body to POST (default: a well-formed submit-url and nothing else)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--alignfix", action="store_true",
                    help="emulate unaligned accesses the way the device's kernel does "
                         "(tools/alignfix). Off by default; the first sweep ran without "
                         "it and 39 of 57 handlers 'died' inside libapmib's TLV "
                         "serialiser, which is the emulator and not the firmware")
    ap.add_argument("--reset-each", dest="reset_each", action="store_true", default=None,
                    help="restart and restore the flash before every probe. Defaults to "
                         "on when --alignfix is on, because handlers that no longer crash "
                         "do save, and probe N would otherwise read what probes 1..N-1 wrote")
    ap.add_argument("--no-reset-each", dest="reset_each", action="store_false",
                    help="do not restore between probes. Only sound when nothing writes")
    args = ap.parse_args(argv)

    if os.geteuid() != 0 and subprocess.run(["sudo", "-n", "true"],
                                            capture_output=True).returncode != 0:
        print("handler-sweep: needs passwordless sudo to restart the server", file=sys.stderr)
        return 1

    # With alignfix on, handlers write. Without it they crashed before they
    # could, and the crash reset the flash. So the guarantee "every probe sees
    # the same bytes" was a by-product of the defect, and removing the defect
    # removes the guarantee unless it is asked for explicitly.
    reset_each = args.reset_each if args.reset_each is not None else args.alignfix

    srv = Server(args.profile, args.port, args.quiet, alignfix=args.alignfix)
    if not srv.ensure():
        print(f"handler-sweep: could not stand the server up on port {args.port}.\n"
              f"  sudo tools/qemu-env.sh --profile {args.profile} build", file=sys.stderr)
        return 1

    names = handlers(args.profile)
    body = args.param.encode()
    base = f"http://127.0.0.1:{args.port}/boafrm/"
    rows = []

    for name in [LIVE_CONTROL, DEAD_CONTROL] + [n for n in names
                                                if n not in (LIVE_CONTROL, DEAD_CONTROL)]:
        ok = srv.ensure_pristine() if reset_each else srv.ensure()
        if not ok:
            rows.append({"handler": name, "status": None, "died_under_emulation": None,
                         "note": "server could not be restarted before this probe"})
            continue
        status, length = http(base + name, body)
        survived = srv.alive()
        rows.append({"handler": name, "status": status, "body_len": length,
                     "died_under_emulation": not survived})
        if not args.quiet:
            mark = "DIED" if not survived else "    "
            print(f"  {name:26} {status:>4}  {length:>6}B  {mark}")

    live = next(r for r in rows if r["handler"] == LIVE_CONTROL)
    dead = next(r for r in rows if r["handler"] == DEAD_CONTROL)
    died = [r["handler"] for r in rows if r.get("died_under_emulation")]
    survivors = [r["handler"] for r in rows if r.get("died_under_emulation") is False]

    problems = []
    if live["status"] not in (200, 302) or live["died_under_emulation"]:
        problems.append(f"live control {LIVE_CONTROL} returned {live['status']} and "
                        f"{'died' if live['died_under_emulation'] else 'survived'} -- "
                        f"the harness cannot tell a dead handler from a dead harness")
    if dead["status"] != 404:
        problems.append(f"dead control {DEAD_CONTROL} returned {dead['status']}, not 404 -- "
                        f"this server answers everything the same way, so no result "
                        f"below discriminates")
    if not survivors:
        problems.append("every handler died, which measures the emulator rather than "
                        "the firmware")

    # The control that only exists because the flash can now be written: after
    # the last probe the environment must still hold the values it started with.
    # If it does not, some probe wrote and something after it read the write, and
    # the run is a sequence rather than 58 independent measurements.
    final = srv._run("reset")
    check = srv._run("check")
    env_intact = check.returncode == 0
    if not env_intact:
        problems.append("the environment's own control set does not pass after the "
                        "sweep, so at least one probe left state behind: "
                        + (check.stdout or check.stderr or "").strip().replace("\n", " | "))
    del final

    report = {
        "producer": "handler-sweep",
        "schema_version": "1",
        "profile": args.profile,
        "alignfix": bool(args.alignfix),
        "reset_each": bool(reset_each),
        "body": args.param,
        "handlers_probed": len(rows),
        "died_under_emulation": sorted(died),
        "survived": sorted(survivors),
        "restarts": srv.restarts,
        "failed_restarts": srv.failed_restarts,
        "controls": {"live": live, "dead": dead, "env_intact_after_sweep": env_intact},
        "control_problems": problems,
        "caveat": "died_under_emulation is NOT a claim about the device. qemu-user raises "
                  "SIGBUS where the MIPS kernel fixes unaligned accesses up. This is a "
                  "candidate list for the bench, not a result from it."
                  + ("" if args.alignfix else
                     " With alignfix off -- as here -- that caveat is not hypothetical: "
                     "the first sweep's 39 deaths were traced to one halfword store in "
                     "libapmib's mib_write_to_raw, so this column is measuring which "
                     "handlers reach the config serialiser, not which ones are fragile. "
                     "Re-run with --alignfix for the list that means what it says."),
    }
    if args.out:
        args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"\n  {len(died)} of {len(rows)} died under emulation, {len(survivors)} survived, "
          f"{srv.restarts} restarts ({srv.failed_restarts} failed)")
    if problems:
        print("\n".join("  CONTROL FAILED: " + p for p in problems), file=sys.stderr)
        return 1
    print("  controls held: a real handler answered and survived, a fake one 404'd")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
