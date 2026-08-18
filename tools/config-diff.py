#!/usr/bin/env python3
"""Change one MIB value, then say which bytes moved -- in both coordinate systems.

What this exists for
--------------------
`P8-23` asks whether the field table `fwrecon compcs` decodes out of a
configuration region agrees with what actually changes when one known value is
written.  Its refutation condition is that the two disagree.

Answering it by hand, the way `runsheet.md` A1.9 originally spelled it out, gets
two things wrong and both of them look like a result:

  * **The write hangs without `tools/alignfix/`.**  `flash set` on a COMPCS
    field runs libapmib's TLV serialiser, whose halfword stores land on odd
    addresses by construction.  Under qemu-user that is a SIGBUS; the guest
    prints `qemu: uncaught target signal 10 (Bus error) - core dumped` and then
    does not exit.  A step with no ceiling on it simply never returns, which
    reads as "slow" rather than as "wrong".

  * **The two answers are not in the same space.**  `qemu-env.sh diff` reports
    offsets into the *flash image*; the region is compressed (7,478 bytes on
    flash for 45,226 decompressed on this unit), so those offsets are into the
    compressed payload.  `fwrecon compcs` reports offsets into the *decompressed*
    payload.  Comparing them directly compares two different things, and on the
    first run they looked two bytes apart and nearly right, which is the worst
    possible outcome.

So this drives both halves and compares the decoded ones, and refuses in every
way the comparison can be vacuous.

The refusals, and why each one is here
--------------------------------------
  * the value does not read back  -> the write did not happen, and every diff
    below would be measuring something else;
  * nothing changed in the flash image -> ditto, and it is the shape a silently
    failing `flash set` takes;
  * nothing changed in the decoded table -> the decoder cannot see a write it
    should see, which is P8-23 refuted in the decoder's direction;
  * more than one field changed -> P8-23 refuted in the other direction: the
    write is not localised to the field the table names.  Reported with the
    extra fields named, because "which extras" is the whole diagnosis.

A run that cannot come back with any of those is not a measurement.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# Long enough that a healthy write (about a second, with a dozen alignfix
# fix-ups) never trips it, short enough that the hang above is reported as a
# hang rather than waited out.
WRITE_TIMEOUT = 90
ENVDIR_SUFFIX = {"unit-2018": "2018", "v2.1.2": "v2.1.2"}


def work_dir() -> Path:
    """$FWRE_WORK, else the invoking user's home -- never root's.

    Same rule as qemu-env.sh: under sudo, $HOME is /root and the environment
    would be looked for in a directory that does not exist.
    """
    env = os.environ.get("FWRE_WORK")
    if env:
        return Path(env)
    user = os.environ.get("SUDO_USER")
    if user:
        import pwd
        return Path(pwd.getpwnam(user).pw_dir) / "fwre-work"
    return Path.home() / "fwre-work"


def qemu_env(profile: str, *args: str, timeout: int | None = None):
    return subprocess.run(
        ["tools/qemu-env.sh", "--profile", profile, *args],
        cwd=REPO, capture_output=True, timeout=timeout, check=False)


def read_mib(profile: str, name: str) -> str | None:
    """`flash get NAME` prints `NAME=value`. Anything else is not a value."""
    r = qemu_env(profile, "run", "/bin/flash", "get", name, timeout=60)
    for line in r.stdout.decode(errors="replace").splitlines():
        line = line.strip()
        if line.startswith(name + "="):
            return line[len(name) + 1:]
    return None


def flash_bytes_diff(before: Path, after: Path) -> list[dict]:
    a, b = before.read_bytes(), after.read_bytes()
    if len(a) != len(b):
        raise SystemExit(f"image sizes differ: {len(a)} vs {len(b)}")
    return [{"offset": f"0x{i:06x}", "before": f"0x{x:02x}", "after": f"0x{y:02x}"}
            for i, (x, y) in enumerate(zip(a, b, strict=True)) if x != y]


def decode_region(py: str, image: Path, region: str, mib_so: Path | None,
                  out: Path) -> dict:
    cmd = [py, "-m", "fwrecon", "compcs", str(image), "--offset", region,
           "-f", "json", "-o", str(out)]
    if mib_so:
        cmd += ["--mib", str(mib_so)]
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, check=False)
    if r.returncode != 0 or not out.is_file():
        raise SystemExit("fwrecon compcs failed on " + str(image) + "\n  " +
                         r.stderr.decode(errors="replace")[:400])
    return json.loads(out.read_text(encoding="utf-8"))


def entries(doc: dict) -> list[dict]:
    for value in doc.values():
        if isinstance(value, list) and value and isinstance(value[0], dict) \
                and "offset" in value[0] and "name" in value[0]:
            return value
    return []


def compare(before: list[dict], after: list[dict], name: str) -> dict:
    """The whole of P8-23, as one function so a test can drive it without root."""
    ba = {e["name"]: e for e in before}
    aa = {e["name"]: e for e in after}
    changed = sorted(n for n in ba if n in aa and ba[n].get("raw") != aa[n].get("raw"))
    appeared = sorted(set(aa) - set(ba))
    vanished = sorted(set(ba) - set(aa))
    problems = []
    if not changed:
        problems.append(
            "the decoder sees no field change at all, though the image changed. "
            "Either the region offset is wrong or the decoder is not reading "
            "the region this write landed in -- P8-23 refuted, decoder side")
    elif changed != [name]:
        problems.append(
            f"the write is not localised: expected only {name!r} to change, "
            f"got {changed}. P8-23 refuted -- one of the two paths is wrong "
            "and the extras name which")
    if appeared or vanished:
        problems.append(
            f"the field set itself moved: appeared={appeared[:8]} "
            f"vanished={vanished[:8]}; a differential across two different "
            "field sets is not a differential")
    return {
        "changed": [{"name": n, "offset": ba[n]["offset"], "length": ba[n]["length"],
                     "raw_before": ba[n].get("raw"), "raw_after": aa[n].get("raw")}
                    for n in changed],
        "appeared": appeared, "vanished": vanished, "problems": problems,
    }


def classify_flash_offsets(diff: list[dict], region_offset: int,
                           comp_len: int | None) -> list[dict]:
    """Say, for each changed byte, which part of the region it is in.

    This is the half that makes the two coordinate systems visible instead of
    inviting the reader to compare them. A byte inside the compressed payload
    has no simple relation to a decompressed field offset, and saying so is the
    point.
    """
    out = []
    for d in diff:
        off = int(d["offset"], 16)
        rel = off - region_offset
        if rel < 0:
            where = "before the region"
        elif comp_len is None:
            where = "inside the region, compressed length unknown"
        elif rel < comp_len:
            where = ("inside the compressed payload -- NOT comparable to a "
                     "decoded field offset")
        else:
            where = f"after the compressed payload (+{rel - comp_len} past its end)"
        out.append({**d, "region_relative": f"0x{rel:x}" if rel >= 0 else str(rel),
                    "where": where})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--profile", default="unit-2018",
                    choices=sorted(ENVDIR_SUFFIX), help="which environment")
    ap.add_argument("--mib", required=True, metavar="NAME",
                    help="the MIB name to change, e.g. DHCP_LEASE_TIME")
    ap.add_argument("--to", required=True, metavar="VALUE",
                    help="the value to write")
    ap.add_argument("--region", default="0x00C000",
                    help="config region offset in the flash image (default the "
                         "live COMPCS region)")
    ap.add_argument("--mib-so", help="libapmib.so, to name the ids "
                                     "(default: this profile's own)")
    ap.add_argument("--python", default=None,
                    help="the interpreter fwrecon is installed into "
                         "(default $FWRE_WORK/venv/bin/python)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if os.geteuid() != 0:
        raise SystemExit("needs root: the environment is a chroot. Run under sudo.")

    work = work_dir()
    env = work / ("qemu-env-" + ENVDIR_SUFFIX[args.profile])
    pristine = env / ".mtd-pristine.bin"
    live = env / "dev/mtdblock0"
    if not pristine.is_file():
        raise SystemExit(f"no environment at {env} (run: sudo tools/qemu-env.sh "
                         f"--profile {args.profile} build)")
    py = args.python or str(work / "venv/bin/python")
    if not Path(py).exists():
        raise SystemExit(f"no interpreter at {py}; pass --python")
    mib_so = Path(args.mib_so) if args.mib_so else None
    if mib_so is None:
        guess = work / "extracted" / args.profile / "squashfs-root/lib/libapmib.so"
        mib_so = guess if guess.is_file() else None

    qemu_env(args.profile, "reap")
    r = qemu_env(args.profile, "reset")
    if r.returncode != 0:
        raise SystemExit("reset failed: " + r.stderr.decode(errors="replace")[:400])

    before_value = read_mib(args.profile, args.mib)
    if before_value is None:
        raise SystemExit(
            f"{args.mib} did not read back at all before the write. Either the "
            "name is not in this build's MIB table or the environment is not "
            "serving one; nothing below would mean anything.")

    # The write. --alignfix is not optional here and the ceiling is the point:
    # without the preload this call never returns.
    try:
        w = subprocess.run(
            ["tools/qemu-env.sh", "--profile", args.profile, "run",
             "-E", "LD_PRELOAD=/lib/alignfix.so",
             "/bin/flash", "set", args.mib, args.to],
            cwd=REPO, capture_output=True, timeout=WRITE_TIMEOUT, check=False)
        write_out = (w.stdout + w.stderr).decode(errors="replace")
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(
            f"`flash set {args.mib}` did not return in {WRITE_TIMEOUT} s.\n"
            "  That is the unaligned-store hang: libapmib's TLV serialiser takes\n"
            "  a SIGBUS per halfword store and qemu-user does not fix them up.\n"
            "  This tool already passes LD_PRELOAD=/lib/alignfix.so, so if you\n"
            "  see this, check that the preload exists in the environment:\n"
            f"    ls -l {env}/lib/alignfix.so") from exc
    fixups = write_out.count("alignfix: fixed")

    after_value = read_mib(args.profile, args.mib)
    if after_value != args.to:
        raise SystemExit(
            f"{args.mib} reads back as {after_value!r}, not {args.to!r}. The "
            "write did not take, so the diff below would be of something else.")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        before_img, after_img = tmp / "before.bin", tmp / "after.bin"
        shutil.copy(pristine, before_img)
        shutil.copy(live, after_img)

        raw = flash_bytes_diff(before_img, after_img)
        if not raw:
            raise SystemExit(
                "not one byte of the flash image changed, yet the value reads "
                "back changed. The value is coming from the shared-memory MIB "
                "cache and has not reached the image; `reset` clears that cache "
                "and this run did reset, so this is a real disagreement.")

        b_doc = decode_region(py, before_img, args.region, mib_so, tmp / "b.json")
        a_doc = decode_region(py, after_img, args.region, mib_so, tmp / "a.json")

    cmp_result = compare(entries(b_doc), entries(a_doc), args.mib)
    comp_len = b_doc.get("comp_len")
    report = {
        "producer": "config-diff",
        "schema_version": "1",
        "profile": args.profile,
        "image": str(live),
        "pristine": str(pristine),
        "region_offset": args.region,
        "mib": args.mib,
        "mib_table": str(mib_so) if mib_so else None,
        "value_before": before_value,
        "value_after": after_value,
        "alignfix_fixups": fixups,
        "region": {k: b_doc.get(k) for k in
                   ("magic", "role", "comp_rate", "comp_len",
                    "decompressed_len", "declared_len")},
        "flash_diff": classify_flash_offsets(raw, int(args.region, 16),
                                             comp_len if isinstance(comp_len, int) else None),
        "decoded_diff": cmp_result["changed"],
        "decoded_appeared": cmp_result["appeared"],
        "decoded_vanished": cmp_result["vanished"],
        "problems": cmp_result["problems"],
    }
    Path(args.out).write_text(json.dumps(report, indent=2) + "\n",
                              encoding="utf-8", newline="\n")
    print(f"  wrote {args.out}")
    print(f"  {args.mib}: {before_value} -> {after_value}   "
          f"({fixups} unaligned stores fixed up)")
    print(f"  flash image: {len(raw)} byte(s) changed")
    for d in report["flash_diff"]:
        print(f"    {d['offset']}  {d['before']} -> {d['after']}   {d['where']}")
    print(f"  decoded table: {len(report['decoded_diff'])} field(s) changed")
    for d in report["decoded_diff"]:
        print(f"    offset {d['offset']:<6} len {d['length']:<3} {d['name']:<24}"
              f" {d['raw_before']} -> {d['raw_after']}")
    if cmp_result["problems"]:
        for p in cmp_result["problems"]:
            sys.stderr.write("  DISAGREEMENT: " + p + "\n")
        return 2
    print("  the two paths name the same field, and only that field.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
