#!/usr/bin/env bash
# Guard suite for tools/check-numbers.py.
#
# This checker was the only one in tools/ without a suite, and it is the one that
# has been wrong twice:
#
#   * bug 59 -- its first version read prose grammar, and 13 of its first 18
#     findings were its own, because English gives `141 registered tests` and
#     `Three registered tests are frozen against it` the same shape;
#   * bug 61 -- it asserted an environment-dependent recount. On a GitHub runner
#     with no pytest, `count-checks.sh` returned 468 against this workstation's
#     626 and the checker called fourteen correct numbers stale. **Local green,
#     remote red, with the repository unchanged between them.**
#
# So the cases below are about the three things it has to keep straight: a number
# that disagrees, a claim site that has gone, and a generator this environment
# cannot run. The third must SKIP and say so -- failing there would make the
# build depend on which machine it ran on, and passing silently would be
# instrument bug 12.
#
#   bash tools/test-check-numbers.sh
set -uo pipefail

cd "$(dirname "$0")/.." || { echo "  FAIL  cannot cd to the repository root"; exit 1; }
TOOL=tools/check-numbers.py
PY="${PYTHON:-python3}"

pass=0; fail=0
ok()  { echo "  ok    $1"; pass=$((pass + 1)); }
bad() { echo "  FAIL  $1"; fail=$((fail + 1)); }

# Each case loads the module and drives it directly. The alternative -- a scratch
# repository with a synthetic register, a fake rtcase and a fake count-checks --
# would be testing the fixture.
check() {
  local label="$1" script="$2" out
  out="$("$PY" - <<PYEOF 2>&1
import importlib.util, io, contextlib, sys
spec = importlib.util.spec_from_file_location("cn", "$TOOL")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
$script
PYEOF
)"
  if [ "$out" = "PASS" ]; then ok "$label"; else bad "$label -- $out"; fi
}

echo "tools/check-numbers.py -- the disagreements it must catch, and the one it must not judge"

# ---------------------------------------------------------------------------
# Number words. "Twenty-three items were cut" is the same claim as "23".
# ---------------------------------------------------------------------------
check "digits, number words and hyphenated tens all read as the same claim" '
cases = {"141": 141, "23": 23, "Twenty-three": 23, "fifty-six": 56, "sixty": 60,
         "seven": 7, "Fifteen": 15, "1,024": 1024}
bad = {k: m.to_int(k) for k, v in cases.items() if m.to_int(k) != v}
print("PASS" if not bad else f"misread {bad}")
'

check "a word that is not a number reads as None, not as zero" '
junk = ["boafrm", "", "  ", "twenty-twenty", "hundred-three", "-", "0x40"]
bad = [j for j in junk if m.to_int(j) is not None]
print("PASS" if not bad else f"accepted junk: {bad}")
'

# `0x40` above matters: a hex address must not be read as a decimal count.
check "zero is a number, and is not confused with unreadable" '
print("PASS" if m.to_int("0") == 0 and m.to_int("zero") == 0 else "zero mishandled")
'

# ---------------------------------------------------------------------------
# The claim-site table: coverage must be visible and must not shrink silently.
# ---------------------------------------------------------------------------
check "every claim site names a file that exists" '
import pathlib
gone = sorted({rel for _, rel, _, _ in m.SITES if not (m.REPO / rel).exists()})
print("PASS" if not gone else f"claim sites point at missing files: {gone}")
'

check "every claim site still matches its file — a rewritten sentence is a failure" '
import re, pathlib
dead = []
for key, rel, pat, what in m.SITES:
    text = (m.REPO / rel).read_text(encoding="utf-8")
    if not re.search(pat, text, re.MULTILINE):
        dead.append(f"{rel}:{key}:{what}")
print("PASS" if not dead else f"claim sites no longer matching: {dead}")
'

check "every claim site has a generator that produces its key" '
keys = {k for k, _, _, _ in m.SITES}
truth = m.owners(626, 130)
missing = sorted(keys - set(truth) - set(m.UNMEASURED))
print("PASS" if not missing else f"no generator for: {missing}")
'

# ---------------------------------------------------------------------------
# Instrument bug 61: an environment that cannot run the recount.
# ---------------------------------------------------------------------------
check "an INCOMPLETE recount leaves checks/guards/pytest unmeasured, not wrong" '
import subprocess, types
real = subprocess.run
def fake(args, **kw):
    if args[:2] == ["bash", "tools/count-checks.sh"]:
        return types.SimpleNamespace(
            stdout="  test-a.sh   12\n  fwrecon pytest  --\n"
                   "INCOMPLETE: fwrecon-pytest test-flash-tools.sh\n"
                   "  total   468\n")
    return real(args, **kw)
m.subprocess.run = fake
truth = m.owners(None, None)
m.subprocess.run = real
leaked = [k for k in ("checks", "guards", "pytest") if k in truth]
named = all(k in m.UNMEASURED for k in ("checks", "guards", "pytest"))
why = m.UNMEASURED.get("checks", "")
ok = not leaked and named and "fwrecon-pytest" in why
print("PASS" if ok else f"leaked={leaked} named={named} why={why!r}")
'

check "a COMPLETE recount is used, and guards is the total minus the parser tests" '
import subprocess, types
real = subprocess.run
def fake(args, **kw):
    if args[:2] == ["bash", "tools/count-checks.sh"]:
        return types.SimpleNamespace(
            stdout="  test-a.sh   12\n  fwrecon pytest  130\n  total   626\n")
    return real(args, **kw)
m.subprocess.run = fake
truth = m.owners(None, None)
m.subprocess.run = real
ok = truth.get("checks") == 626 and truth.get("pytest") == 130 and truth.get("guards") == 496
print("PASS" if ok else f"got {[truth.get(k) for k in (chr(99)+chr(104)+chr(101)+chr(99)+chr(107)+chr(115), chr(112)+chr(121)+chr(116)+chr(101)+chr(115)+chr(116), chr(103)+chr(117)+chr(97)+chr(114)+chr(100)+chr(115))]}")
'

# The positive control for the two above: without it, "always returns nothing"
# and "returns nothing when the recount is incomplete" are the same behaviour.
check "the INCOMPLETE marker is required — a plain table is not treated as incomplete" '
import subprocess, types
real = subprocess.run
def fake(args, **kw):
    if args[:2] == ["bash", "tools/count-checks.sh"]:
        return types.SimpleNamespace(stdout="  fwrecon pytest  130\n  total   626\n")
    return real(args, **kw)
m.subprocess.run = fake
truth = m.owners(None, None)
m.subprocess.run = real
print("PASS" if "checks" in truth and not m.UNMEASURED else f"truth={sorted(truth)} unmeasured={sorted(m.UNMEASURED)}")
'

# ---------------------------------------------------------------------------
# The generators themselves
# ---------------------------------------------------------------------------
check "the register generators read the register, not a constant" '
truth = m.owners(626, 130)
reg = (m.REPO / "test-cases.toml").read_text(encoding="utf-8")
import re
cases = len(re.findall(r"^\[\[case\]\]", reg, re.MULTILINE))
cuts  = len(re.findall(r"^cut_reason\s*=", reg, re.MULTILINE))
ok = truth["registered"] == cases and truth["cut"] == cuts
print("PASS" if ok else f"registered={truth[chr(114)+chr(101)+chr(103)+chr(105)+chr(115)+chr(116)+chr(101)+chr(114)+chr(101)+chr(100)]} vs {cases}, cut={truth[chr(99)+chr(117)+chr(116)]} vs {cuts}")
'

check "the instrument-bug count is the highest row in chapter 12, not a constant" '
truth = m.owners(626, 130)
import re
body = (m.REPO / "writeup" / "12-instruments.md").read_text(encoding="utf-8")
rows = [int(n) for n in re.findall(r"^\|\s*(\d+)", body, re.MULTILINE)]
print("PASS" if truth["bugs"] == max(rows) else f"bugs={truth[chr(98)+chr(117)+chr(103)+chr(115)]} max row={max(rows)}")
'

check "suites and checkers are counted from the filesystem" '
truth = m.owners(626, 130)
suites = len(list((m.REPO / "tools").glob("test-*.sh")))
checkers = len(list((m.REPO / "tools").glob("check-*.py")))
ok = truth["suites"] == suites and truth["checkers"] == checkers
print("PASS" if ok else f"suites={truth[chr(115)+chr(117)+chr(105)+chr(116)+chr(101)+chr(115)]}/{suites} checkers={truth[chr(99)+chr(104)+chr(101)+chr(99)+chr(107)+chr(101)+chr(114)+chr(115)]}/{checkers}")
'

echo
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
