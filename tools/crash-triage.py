#!/usr/bin/env python3
"""Why did that handler kill the server?  Answered with registers, not a shrug.

What this exists for
--------------------
`handler-sweep.py` reports `died_under_emulation` and nothing else.  That was
enough while the answer was "the emulator" -- 39 of 57 handlers were dying on a
qemu SIGBUS inside libapmib's TLV serialiser, and the fix for that was
`tools/alignfix/`, not a triage tool.  With that divergence removed the deaths
are down to a handful, and "died" stops being a category and becomes a
question: *which* instruction, writing *where*, called from *what*.

A death with no address is not a finding.  It is a candidate list of one.

How it gets an answer
---------------------
`boa` installs its own SIGSEGV handler -- the log line is `caught SIGSEGV,
dumping core in /tmp` -- and then aborts, so the signal never reaches qemu's
default handler and no address is ever printed.  So this drives qemu-user's
gdbstub instead: gdb sees the signal first, `nopass` keeps it away from boa's
handler, and the registers are still the ones the faulting instruction ran
with.

Two details are load-bearing and both cost a session to find:

  * `boa` daemonises.  Under the gdbstub gdb follows the parent, which exits
    immediately, and the run ends with "[Inferior 1 exited normally]" and an
    empty register dump.  `-d` keeps it in the foreground; the flag is real,
    the usage string in this binary being
    `[-c serverroot] [-d] [-f configfile] [-r chroot]`.
  * SIGBUS must be passed through, not stopped on.  With `--alignfix` loaded
    the firmware takes dozens of SIGBUS per configuration write *by design*,
    and a gdb that stops on each one never reaches the fault being triaged.

What it does with the answer
----------------------------
The faulting instruction is decoded far enough to name the register holding
the store address, that register's value is read, and the value is classified
against the binary's own program headers: which PT_LOAD contains it, with what
flags.  "SIGSEGV" and "SIGSEGV storing into a segment mapped R-X" are
different findings, and only the second one explains anything.

The control, which is not optional
----------------------------------
At least one case must be a handler and body known NOT to fault, and it must
come back clean.  Without it, a harness that reports "signal" for everything --
because the environment is broken, because the port was held by a corpse,
because $ENVDIR resolved to /root -- is indistinguishable from a run in which
everything really crashed.  This repository has produced that table twice, and
the second time was the afternoon this file was written.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GDB_PORT = 1234
HTTP_PORT = 8080
# How long to wait in `continue` before calling it "did not fault". The POST is
# fired at +3 s and a fault stops the inferior essentially at once, so this is
# generous by an order of magnitude and still cheap enough that controls are
# worth running.
NO_FAULT_SECONDS = 25


def work_dir() -> Path:
    """$FWRE_WORK, else the invoking user's home -- never root's.

    Same rule as qemu-env.sh and for the same reason: a nested `sudo` sets
    SUDO_USER=root, which silently moves the environment to /root/fwre-work.
    """
    if os.environ.get("FWRE_WORK"):
        return Path(os.environ["FWRE_WORK"])
    user = os.environ.get("SUDO_USER")
    if user and user != "root":
        import pwd

        return Path(pwd.getpwnam(user).pw_dir) / "fwre-work"
    return Path.home() / "fwre-work"


def program_headers(path: Path) -> list:
    """PT_LOAD entries, from the program header table alone.

    These binaries are `sstrip`'d: `readelf -S` returns nothing at all, so
    anything needing a section header is unavailable here.  Segments survive
    because the loader needs them.
    """
    data = path.read_bytes()
    if data[:4] != b"\x7fELF":
        raise SystemExit(str(path) + ": not an ELF")
    if data[5] != 2:
        raise SystemExit(str(path) + ": not big-endian; this corpus is MIPS-BE")
    e_phoff = struct.unpack_from(">I", data, 0x1C)[0]
    e_phentsize, e_phnum = struct.unpack_from(">HH", data, 0x2A)
    out = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        fields = struct.unpack_from(">8I", data, off)
        p_type, _, p_vaddr, _, _, p_memsz, p_flags, _ = fields
        if p_type != 1:
            continue
        flags = ""
        for ch, bit in (("R", 4), ("W", 2), ("X", 1)):
            flags += ch if p_flags & bit else "-"
        out.append({"vaddr": p_vaddr, "memsz": p_memsz, "flags": flags,
                    "writable": bool(p_flags & 2)})
    return out


def classify(addr: int, phdrs: list) -> dict:
    for ph in phdrs:
        if ph["vaddr"] <= addr < ph["vaddr"] + ph["memsz"]:
            if ph["writable"]:
                verdict = "inside a writable PT_LOAD"
            else:
                verdict = ("inside a NON-writable PT_LOAD -- a store here faults "
                           "by protection, and the MIPS kernel does not fix that up")
            return {"segment_vaddr": "0x{:08x}".format(ph["vaddr"]),
                    "segment_flags": ph["flags"],
                    "writable": ph["writable"], "verdict": verdict}
    return {"segment_vaddr": None, "segment_flags": None, "writable": None,
            "verdict": "outside every PT_LOAD of this binary "
                       "(a shared library, the stack, or unmapped)"}


STORE_MNEMONICS = ("sb", "sh", "sw", "swl", "swr")
# `pc` is in this list and it is not one of the 32 general registers. It was
# left out of the first version, so every case in the first run reported
# `"pc": "0x00000000"` -- a wrong number rather than a missing field, which is
# worse: `ra` was right, the disassembly was right, and the one value a reader
# would quote first was zero. Nothing failed. The lesson is the register's own:
# a tool that reports 0 is making a claim.
REG_NAMES = ["zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
             "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
             "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
             "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra", "pc"]
DISASM = re.compile(r"^=>\s+0x([0-9a-f]+)\s*(?:<[^>]*>)?:\s+(\S+)\s*(.*)$", re.M)
REGVAL = re.compile(r"^(\w+):\s+0x([0-9a-f]+)\s*$", re.M)
SIGLINE = re.compile(r"Program received signal (\w+)", re.M)


def gdb_script(handler: str, body: str, tmp: Path) -> Path:
    curl = (f'curl -s -m 6 -o /dev/null -X POST '
            f'http://127.0.0.1:{HTTP_PORT}/boafrm/{handler} '
            f'--data "{body}"')
    regs = "\n".join(f'printf "{r}: 0x%x\\n", ${r}' for r in REG_NAMES)
    text = "\n".join([
        "set confirm off",
        "set pagination off",
        "set architecture mips",
        f"target remote 127.0.0.1:{GDB_PORT}",
        "handle SIGSEGV stop print nopass",
        "handle SIGBUS nostop noprint pass",
        f"shell (sleep 3; {curl}) &",
        "continue",
        "echo \\n=====REGS=====\\n",
        regs,
        "echo \\n=====DISASM=====\\n",
        "x/6i $pc-8",
        "echo \\n=====END=====\\n",
        "",
    ])
    f = tmp / "triage.gdb"
    f.write_text(text, encoding="utf-8", newline="\n")
    return f


def run_case(env: Path, handler: str, body: str, phdrs: list, tmp: Path,
             profile: str = "unit-2018") -> dict:
    # `--profile` on every call. The first version left it off, so a run asked
    # for `v2.1.2` reset and reaped the *default* environment while triaging the
    # v2.1.2 one -- two profiles, one of them restored between probes and the
    # other not. Nothing would have failed; the second and later cases would
    # simply have been measured on state the first one left behind.
    pfx = ["tools/qemu-env.sh", "--profile", profile]
    for sub in ("stop", "reap"):
        subprocess.run([*pfx, sub], cwd=REPO, capture_output=True, check=False)
    r = subprocess.run([*pfx, "reset"], cwd=REPO,
                       capture_output=True, check=False)
    if r.returncode != 0:
        raise SystemExit("reset failed: " + r.stderr.decode(errors="replace")[:400])

    conf = re.sub(r"(?m)^Port .*", f"Port {HTTP_PORT}",
                  (env / "var/boa.conf").read_text())
    (env / "var/boa-dbg.conf").write_text(conf, encoding="utf-8", newline="\n")

    # boa generates /web/config.dat at start-up down a path that faults; the
    # environment makes that one open() fail by making the path a directory.
    cd = env / "var/web/config.dat"
    if cd.is_file():
        cd.unlink()
    cd.mkdir(parents=True, exist_ok=True)

    with open(env / "tmp/boa-triage.log", "wb") as log:
        # `unshare --pid --fork`, and it is not optional. chroot is not
        # isolation: on the v2.1.2 profile a POST to /boafrm/formWsc reaches
        # system("reboot -f"), qemu-user passes reboot(2) to the host kernel,
        # and this runs as root -- so the host powered off, three times, each
        # time looking like this tool hanging. In a PID namespace that syscall
        # signals the namespace's own init, which is what it means on the
        # device. See tools/qemu-env.sh guest().
        qemu = subprocess.Popen(
            ["unshare", "--pid", "--fork",
             "chroot", str(env), "./qemu-mips-static", "-g", str(GDB_PORT),
             "-E", "LD_PRELOAD=/lib/alignfix.so",
             "/bin/boa", "-d", "-f", "/var/boa-dbg.conf"],
            stdout=log, stderr=subprocess.STDOUT)
    time.sleep(1)
    # The timeout IS the negative oracle, and that is why it is short.
    #
    # `continue` returns when the inferior stops. A handler that faults stops it
    # within a second of the POST; a handler that does not fault never stops it
    # at all, so gdb sits in `continue` until something kills it. The first
    # version of this file used 180 s and let TimeoutExpired propagate, which
    # meant the first control -- a handler chosen precisely because it survives
    # -- burned three minutes and then took the whole run down with it,
    # discarding five cases that had already completed. A run whose controls
    # cannot pass cheaply is a run whose controls get dropped.
    timed_out = False
    try:
        g = subprocess.run(
            ["gdb-multiarch", "-q", "-batch", "-x",
             str(gdb_script(handler, body, tmp)), str(env / "bin/boa")],
            capture_output=True, timeout=NO_FAULT_SECONDS)
        out = g.stdout.decode(errors="replace") + g.stderr.decode(errors="replace")
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        out = ((exc.stdout or b"") + (exc.stderr or b"")).decode(errors="replace")
    finally:
        qemu.kill()
        subprocess.run(["pkill", "-9", "-f",
                        f"qemu-mips-static -g {GDB_PORT}"],
                       capture_output=True, check=False)
        # And a reap, because the pattern above cannot match what the guest
        # forks: children go through binfmt as `mips-binfmt-P /bin/ntp_inet`,
        # a different command line entirely. One of those survived a whole
        # session on 2026-08-18 and blocked the next reset. reap finds them by
        # /proc/PID/root instead of by argv.
        subprocess.run(["tools/qemu-env.sh", "--profile", profile, "reap"],
                       cwd=REPO, capture_output=True, check=False)

    case = {"handler": handler, "body": body}
    sig = SIGLINE.search(out)
    if not sig:
        case["signal"] = None
        case["seconds_waited"] = NO_FAULT_SECONDS if timed_out else None
        case["verdict"] = (
            f"no signal in {NO_FAULT_SECONDS} s -- the handler did not fault"
            if timed_out else
            "no signal, and gdb returned early: read the log, this is not the "
            "same answer as 'it survived'")
        return case
    case["signal"] = sig.group(1)

    regs = {}
    for m in REGVAL.finditer(out):
        regs[m.group(1)] = int(m.group(2), 16)
    if "pc" not in regs or "ra" not in regs:
        # Refuse rather than report a zero. See the note beside REG_NAMES.
        case["verdict"] = ("the register dump did not contain pc and ra; "
                           "the gdb output shape changed and nothing below "
                           "this line can be trusted")
        case["raw_tail"] = out[-1500:]
        return case
    case["pc"] = "0x{:08x}".format(regs["pc"])
    case["ra"] = "0x{:08x}".format(regs.get("ra", 0))
    case["ra_in_boa"] = classify(regs.get("ra", 0), phdrs)

    d = DISASM.search(out)
    if d:
        case["faulting_instruction"] = (d.group(2) + " " + d.group(3)).strip()
        mnem, ops = d.group(2), d.group(3)
        m = re.match(r"\S+,\s*(-?\d+)\((\w+)\)", ops)
        if mnem in STORE_MNEMONICS and m:
            base = m.group(2)
            addr = (regs.get(base, 0) + int(m.group(1))) & 0xFFFFFFFF
            case["store_target"] = f"0x{addr:08x}"
            case["store_base_register"] = base
            case["store_target_in_boa"] = classify(addr, phdrs)
        else:
            case["store_target"] = None
            case["store_target_in_boa"] = {
                "verdict": "the faulting instruction is not a decoded store form; "
                           "read pc and the disassembly instead"}
        tail = out.split("=====DISASM=====")[-1].splitlines()
        case["disassembly"] = [ln.strip() for ln in tail
                               if ln.strip() and "=====" not in ln][:6]
    case["registers"] = {k: f"0x{v:08x}" for k, v in sorted(regs.items())}
    return case


def parse_spec(spec: str):
    handler, _, body = spec.partition(":")
    return handler, body


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--profile", default="unit-2018",
                    choices=["unit-2018", "v2.1.2"])
    ap.add_argument("--case", action="append", default=[],
                    metavar="HANDLER[:BODY]",
                    help="repeatable; a handler to fault, with an optional POST body")
    ap.add_argument("--control", action="append", default=[],
                    metavar="HANDLER[:BODY]",
                    help="repeatable; MUST NOT fault. At least one is required")
    ap.add_argument("--binary", help="the boa this profile runs (segment lookup)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if os.geteuid() != 0:
        raise SystemExit("needs root: the environment is a chroot. Run under sudo.")
    if not args.control:
        raise SystemExit(
            "refusing to run with no control.\n"
            "  A harness that reports a signal for every case looks exactly like a\n"
            "  run in which everything crashed. Name a handler+body known to\n"
            "  survive, e.g.  --control formNtp:")
    for tool in ("gdb-multiarch", "chroot", "pkill"):
        if not shutil.which(tool):
            raise SystemExit("missing " + tool)

    suffix = "2018" if args.profile == "unit-2018" else args.profile
    env = work_dir() / ("qemu-env-" + suffix)
    if not (env / "var/boa.conf").is_file():
        raise SystemExit(
            f"no environment at {env}\n"
            f"  work dir {work_dir()} (FWRE_WORK, else the invoking user's home)\n"
            "  If that looks wrong this is the sudo-inside-sudo trap: SUDO_USER\n"
            "  becomes root and the work dir moves to /root. Pass FWRE_WORK.")

    binary = Path(args.binary) if args.binary else env / "bin/boa"
    phdrs = program_headers(binary)

    report = {
        "producer": "crash-triage",
        "schema_version": "1",
        "profile": args.profile,
        "binary": str(binary),
        "alignfix": True,
        "program_headers": [
            {"vaddr": "0x{:08x}".format(p["vaddr"]), "memsz": "0x{:x}".format(p["memsz"]),
             "flags": p["flags"]} for p in phdrs],
        "cases": [], "controls": [], "control_problems": [],
    }
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for spec in args.case:
            h, b = parse_spec(spec)
            print(f"  case    {h:<22} body={b!r}", flush=True)
            report["cases"].append(run_case(env, h, b, phdrs, tmp, args.profile))
        for spec in args.control:
            h, b = parse_spec(spec)
            print(f"  control {h:<22} body={b!r}", flush=True)
            c = run_case(env, h, b, phdrs, tmp, args.profile)
            report["controls"].append(c)
            if c.get("signal"):
                report["control_problems"].append(
                    "control {} faulted with {}; every case in this run is "
                    "suspect and none of them is reported as a finding".format(h, c["signal"]))

    subprocess.run(["tools/qemu-env.sh", "--profile", args.profile, "stop"],
                   cwd=REPO, capture_output=True, check=False)

    Path(args.out).write_text(json.dumps(report, indent=2) + "\n",
                              encoding="utf-8", newline="\n")
    print("\n  wrote " + args.out)
    for c in report["cases"]:
        sig = c.get("signal") or "no signal"
        ins = c.get("faulting_instruction", "")
        tgt = c.get("store_target") or ""
        seg = c.get("store_target_in_boa", {}).get("verdict", "")
        print(f"  {c['handler']:<22} {sig:<10} {ins:<20} {tgt:<12} {seg}")
    if report["control_problems"]:
        for p in report["control_problems"]:
            sys.stderr.write("  CONTROL FAILED: " + p + "\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
