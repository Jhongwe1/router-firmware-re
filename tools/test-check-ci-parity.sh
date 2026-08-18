#!/usr/bin/env bash
# Guard suite for tools/check-ci-parity.py.
#
# The checker's whole job is to fail, and a checker whose failure path has never
# run is the shape of instrument bug 12 -- it went green for a year on a corpus
# that never contained the thing it was looking for. So every case below feeds
# it a divergence it must catch, and one it must not.
#
# The two parsers are where it can go quietly wrong, and in opposite directions:
#
#   * the Makefile side walks `ci:` transitively. If it stopped at the first
#     level it would silently compare a subset, and a subset that happens to
#     agree looks exactly like parity;
#   * the workflow side must read `run:` blocks and NOT comments. This file's own
#     workflow names four suites in prose, and counting those as steps would make
#     a missing step invisible -- which is how the fifth divergence survived.
#
#   bash tools/test-check-ci-parity.sh
set -uo pipefail

cd "$(dirname "$0")/.." || { echo "  FAIL  cannot cd to the repository root"; exit 1; }
TOOL=tools/check-ci-parity.py
PY="${PYTHON:-python3}"

pass=0; fail=0; skip=0
ok()   { echo "  ok    $1"; pass=$((pass + 1)); }
bad()  { echo "  FAIL  $1"; fail=$((fail + 1)); }
skipd(){ echo "  skip  $1"; skip=$((skip + 1)); }

# The two parser cases below need PyYAML, and a GitHub runner's setup-python does
# not ship it. They are SKIPPED rather than silently dropped, because the checker
# they exercise degrades to a skip in the same environment -- and a suite that
# hides that would be claiming coverage the CI run does not have. The workflow
# installs pyyaml so that both stop being skips there; this stays for anyone
# running the suite on a bare interpreter.
if "$PY" -c "import yaml" >/dev/null 2>&1; then HAVE_YAML=1; else HAVE_YAML=0; fi

check() {
  local label="$1" script="$2" out
  out="$("$PY" - <<PYEOF 2>&1
import importlib.util
spec = importlib.util.spec_from_file_location("parity", "$TOOL")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
$script
PYEOF
)"
  if [ "$out" = "PASS" ]; then ok "$label"; else bad "$label -- $out"; fi
}

echo "tools/check-ci-parity.py -- the divergences it must catch, and the one it must not"

# --------------------------------------------------------------------------
# The Makefile side
# --------------------------------------------------------------------------

check "the ci target is walked transitively, not one level deep" '
mk = "ci: a b\n\techo done\n\na: c\n\tbash tools/test-a.sh\n\nb:\n\tbash tools/test-b.sh\n\nc:\n\tbash tools/test-c.sh\n"
got, targets = m.make_ci_scripts(mk)
print("PASS" if got == {"tools/test-a.sh", "tools/test-b.sh", "tools/test-c.sh"}
      else repr(got))
'

check "a Makefile with no ci target is an error, not an empty comparison" '
try:
    m.make_ci_scripts("all:\n\techo hi\n")
    print("accepted a Makefile with no ci target")
except SystemExit as exc:
    print("PASS" if "no `ci:` target" in str(exc) else str(exc))
'

check "a help comment after the prerequisites is not read as a prerequisite" '
mk = "ci: a ## Everything CI checks\n\techo done\n\na:\n\tbash tools/test-a.sh\n"
got, _ = m.make_ci_scripts(mk)
print("PASS" if got == {"tools/test-a.sh"} else repr(got))
'

# --------------------------------------------------------------------------
# The workflow side -- the half that let the fifth divergence through
# --------------------------------------------------------------------------

check "a script named only in a comment is not counted as a step" '
wf = "jobs:\n  a:\n    steps:\n      # tools/test-ghost.sh was added on some date\n      - name: real\n        run: bash tools/test-real.sh\n"
print("PASS" if m.workflow_scripts(wf) == {"tools/test-real.sh"}
      else repr(m.workflow_scripts(wf)))
'

check "a trailing comment on a run line is not counted" '
wf = "jobs:\n  a:\n    steps:\n      - run: bash tools/test-real.sh  # not tools/test-ghost.sh\n"
print("PASS" if m.workflow_scripts(wf) == {"tools/test-real.sh"}
      else repr(m.workflow_scripts(wf)))
'

check "a block run: | is read to its end and no further" '
wf = ("jobs:\n  a:\n    steps:\n      - name: many\n        run: |\n"
      "          bash tools/test-one.sh\n          bash tools/test-two.sh\n"
      "      - name: after\n        run: bash tools/test-three.sh\n")
print("PASS" if m.workflow_scripts(wf) ==
      {"tools/test-one.sh", "tools/test-two.sh", "tools/test-three.sh"}
      else repr(m.workflow_scripts(wf)))
'

# --------------------------------------------------------------------------
# The comparison itself, in both directions
# --------------------------------------------------------------------------

check "a suite in make ci and not in the workflow is reported, and named" '
p = m.compare({"tools/test-a.sh", "tools/test-b.sh"}, {"tools/test-a.sh"}, {})
print("PASS" if len(p) == 1 and "tools/test-b.sh" in p[0]
      and "not in .github" in p[0] else repr(p))
'

check "a suite in the workflow and not in make ci is reported too" '
p = m.compare({"tools/test-a.sh"}, {"tools/test-a.sh", "tools/test-b.sh"}, {})
print("PASS" if len(p) == 1 and "tools/test-b.sh" in p[0]
      and "not in `make ci`" in p[0] else repr(p))
'

check "both directions at once are both reported, not just the first" '
p = m.compare({"tools/test-a.sh"}, {"tools/test-b.sh"}, {})
print("PASS" if len(p) == 2 else repr(p))
'

# --------------------------------------------------------------------------
# The parser check, added after this suite went green on a workflow GitHub
# could not read at all. A regex does not care whether the document is valid.
# --------------------------------------------------------------------------

if [ "$HAVE_YAML" = "0" ]; then
  skipd "a workflow that is not valid YAML is reported as broken -- no PyYAML here"
  skipd "a valid workflow parses, and says so -- no PyYAML here"
fi

[ "$HAVE_YAML" = "1" ] &&
check "a workflow that is not valid YAML is reported as broken, not as parity" '
import pathlib, tempfile
d = tempfile.mkdtemp()
p = pathlib.Path(d) / "ci.yml"
# A backtick cannot start a YAML plain scalar. This exact line shipped.
p.write_text("jobs:\n  a:\n    steps:\n      - name: `make ci` and this file agree\n        run: bash tools/test-a.sh\n")
ok, why = m.workflow_parses(p)
print("PASS" if ok is False and "`" in why else "%r %r" % (ok, why))
'

[ "$HAVE_YAML" = "1" ] &&
check "a valid workflow parses, and says so" '
import pathlib, tempfile
d = tempfile.mkdtemp()
p = pathlib.Path(d) / "ci.yml"
p.write_text("jobs:\n  a:\n    steps:\n      - name: \"`make ci` and this file agree\"\n        run: bash tools/test-a.sh\n")
ok, why = m.workflow_parses(p)
print("PASS" if ok is True else "%r %r" % (ok, why))
'

check "with no YAML parser available the answer is None, which is a skip not a pass" '
import builtins, pathlib, tempfile
real = builtins.__import__
def fake(name, *a, **k):
    if name == "yaml":
        raise ImportError("no yaml here")
    return real(name, *a, **k)
builtins.__import__ = fake
try:
    ok, why = m.workflow_parses(pathlib.Path(tempfile.mkstemp()[1]))
finally:
    builtins.__import__ = real
print("PASS" if ok is None and "NOT parsed" in why else "%r %r" % (ok, why))
'

check "identical sets are silent" '
p = m.compare({"tools/test-a.sh"}, {"tools/test-a.sh"}, {})
print("PASS" if p == [] else repr(p))
'

check "a one-sided entry recorded as deliberate is allowed through" '
p = m.compare({"tools/test-a.sh", "tools/flash-read.sh"}, {"tools/test-a.sh"},
              {"tools/flash-read.sh": "drives a serial cable"})
print("PASS" if p == [] else repr(p))
'

check "the deliberate list does not silence a name it does not contain" '
p = m.compare({"tools/test-a.sh", "tools/test-b.sh"}, {"tools/test-a.sh"},
              {"tools/flash-read.sh": "drives a serial cable"})
print("PASS" if len(p) == 1 and "tools/test-b.sh" in p[0] else repr(p))
'

# --------------------------------------------------------------------------
# And against the real files, which is the case that has to stay green
# --------------------------------------------------------------------------

if "$PY" "$TOOL" >/dev/null 2>&1; then
  ok "the repository's own two files agree right now"
else
  bad "the repository's own two files have diverged -- run $TOOL to see how"
fi

echo
echo "  $pass passed, $fail failed, $skip skipped"
[ "$fail" -eq 0 ] || exit 1
