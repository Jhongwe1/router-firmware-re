#!/usr/bin/env bash
# Guard suite for tools/check-runsheet.py.
#
# That checker is the only thing standing between a hand-written runsheet and a
# reader who follows a command that no longer works. A checker that cannot fail
# would be worse than none, because it would make "runsheet OK" mean nothing --
# and this project has shipped exactly that once already (PROGRESS.md,
# instrument bug 12).
#
# So every claim it makes gets a synthetic runsheet that MUST make it fail, and
# the assertion is on the MESSAGE, not on the exit code: a case that fails for an
# unrelated reason would otherwise pass.
#
#   bash tools/test-check-runsheet.sh
#
set -uo pipefail

cd "$(dirname "$0")/.." || { echo "  FAIL  cannot cd to the repository root"; exit 1; }
PY="${FWRE_PY:-python3}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
ok()  { echo "  ok    $1"; pass=$((pass + 1)); }
bad() { echo "  FAIL  $1"; fail=$((fail + 1)); }

# The checker resolves relative links against the runsheet's own directory, so
# fixtures live at the repository root and are removed on exit.
RS="rs-selftest-$$.md"
trap 'rm -rf "$TMP"; rm -f "$RS"' EXIT

# A minimally valid runsheet: one step with the promised fields, one real make
# target, one real tool with a real subcommand and a real flag, one resolvable
# cross-reference, one tagged output block, and a Part B.
write_good() {
  cat > "$RS" <<'MD'
# fixture

## A1 a step

| | |
|---|---|
| **層** | T1 |
| **關掉的項目** | `P0-2` |
| **最後驗證** | 2026-08-17 |

```bash
make ledger
python3 tools/rtcase.py todo --week W05
```

```text
W05: 27/27 done, 0 outstanding
```

See §8.12.3 and [`RUNBOOK.md`](RUNBOOK.md).

# Part B — per week

## B-W99
A week with no executed tests, so the fixture carries no coverage obligation of
its own. The coverage cases below switch this to a real week on purpose.
MD
}

# expect_fail <label> <needle>
expect_fail() {
  local label="$1" needle="$2" out rc
  out="$("$PY" tools/check-runsheet.py "$RS" 2>&1)"; rc=$?
  if [ "$rc" -eq 0 ]; then
    bad "$label — accepted, and it must not be"
  elif printf '%s' "$out" | grep -qF "$needle"; then
    ok "$label"
  else
    bad "$label — rejected for the WRONG reason:"; printf '%s\n' "$out" | sed 's/^/          /'
  fi
}

echo "=== the control: the committed runsheet must pass ==="
if out="$("$PY" tools/check-runsheet.py 2>&1)"; then
  ok "runsheet.md passes ($(printf '%s' "$out" | tail -1))"
else
  bad "runsheet.md does not pass — every case below would then pass for free"
  printf '%s\n' "$out" | sed 's/^/          /'
fi

echo
echo "=== the control inside the fixture ==="
write_good
if "$PY" tools/check-runsheet.py "$RS" >/dev/null 2>&1; then
  ok "a minimal well-formed runsheet passes"
else
  bad "the fixture itself is rejected, so nothing below proves anything"
  "$PY" tools/check-runsheet.py "$RS" 2>&1 | sed 's/^/          /'
fi

echo
echo "=== every claim the checker makes ==="

write_good
sed -i 's|make ledger|make no-such-target|' "$RS"
expect_fail "a make target that does not exist" "no such target in Makefile"

write_good
sed -i 's|tools/rtcase.py|tools/no-such-tool.py|' "$RS"
expect_fail "a tools/ path that does not exist" "does not exist"

write_good
sed -i 's|rtcase.py todo|rtcase.py nosuchsub|' "$RS"
expect_fail "a subcommand the tool does not have" "has no subcommand"

# The one that matters most: on 2026-08-17 a step shipped with `AUTOBURN: 0`,
# which the boot loader rejects. Nothing could catch it because nothing read the
# commands as commands.
write_good
sed -i 's|--week W05|--nosuchflag W05|' "$RS"
expect_fail "a flag the tool does not accept" "does not accept"

write_good
sed -i 's|§8.12.3|§8.99.9|' "$RS"
expect_fail "a cross-reference that resolves to no RUNBOOK heading" "does not resolve"

write_good
sed -i 's|(`RUNBOOK.md`)|(NOT-A-FILE.md)|; s|\[`RUNBOOK.md`\](RUNBOOK.md)|[x](NOT-A-FILE.md)|' "$RS"
expect_fail "a link target that does not exist" "link target NOT-A-FILE.md does not exist"

write_good
sed -i '/^| \*\*最後驗證\*\*/d' "$RS"
expect_fail "a step with no 最後驗證 field" "does not declare"

write_good
sed -i 's|2026-08-17|sometime last week|' "$RS"
expect_fail "a 最後驗證 with no date in it" "names no date"

write_good
sed -i '/^# Part B/d' "$RS"
expect_fail "no Part B section" "no \`# Part B\` section"

# A file with no commands at all: every check above would pass over nothing,
# which is the shape of instrument bug 12.
write_good
"$PY" - "$RS" <<'PYEOF'
import re, sys, pathlib
p = pathlib.Path(sys.argv[1])
p.write_text(re.sub(r"```bash.*?```", "", p.read_text("utf-8"), flags=re.S), "utf-8")
PYEOF
expect_fail "a runsheet with no commands at all" "no shell commands found at all"

echo
echo "=== coverage: an executed test with no procedure is a claim taken on trust ==="

# A step claiming an id that is not in the register. A mapping naming P9-99 looks
# exactly like coverage from a distance.
write_good
"$PY" - "$RS" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
s = p.read_text("utf-8").replace("| **最後驗證** |",
    "| **關掉的項目** | `P99-99` |\n| **最後驗證** |", 1)
p.write_text(s, "utf-8")
PYEOF
expect_fail "a step claiming a test id the register does not have" \
            "which is not in the register"

# The direction that matters. The fixture already claims P0-2; switching Part B to
# a week that really has results makes every OTHER result unreachable.
write_good
sed -i 's|## B-W99|## B-W05|' "$RS"
out="$("$PY" tools/check-runsheet.py "$RS" 2>&1)"; rc=$?
if [ "$rc" -eq 0 ]; then
  bad "a runsheet covering W05 but claiming one test was accepted"
elif printf '%s' "$out" | grep -qF "no step claims and no exemption names"; then
  ok "every executed test of a covered week must be claimed by some step"
else
  bad "coverage gap reported for the wrong reason:"; printf '%s\n' "$out" | sed 's/^/          /'
fi

# The escape hatch has to work, or the only way to pass is to claim coverage you
# do not have -- which is worse than an honest gap.
write_good
"$PY" - "$RS" <<'PYEOF'
import json, pathlib, sys, tomllib
p = pathlib.Path(sys.argv[1])
reg = tomllib.loads(pathlib.Path("test-cases.toml").read_text("utf-8"))
cases = {c["id"]: c for c in reg["case"]}
done = [r["id"] for r in
        json.loads(pathlib.Path("reports/test-results.json").read_text("utf-8"))["results"]]
ids = sorted({c for c in done if c in cases
              and str(cases[c].get("week")) == "W05"
              and not str(cases[c].get("cut_reason", "")).strip()
              and c != "P0-2"})          # P0-2 is the fixture's own claim
s = p.read_text("utf-8").replace("## B-W99", "## B-W05")
s += "\n<!-- no-procedure: " + " ".join(ids) + " — fixture -->\n"
p.write_text(s, "utf-8")
PYEOF
if "$PY" tools/check-runsheet.py "$RS" >/dev/null 2>&1; then
  ok "the no-procedure escape hatch is honoured when it names the gap"
else
  bad "the escape hatch did not work, so the only way to pass is to overclaim"
  "$PY" tools/check-runsheet.py "$RS" 2>&1 | sed 's/^/          /'
fi

echo
echo "=== fences: a reader must never confuse 'run this' with 'you will see this' ==="
write_good
sed -i '0,/^```text$/s//```/' "$RS"
out="$("$PY" tools/check-runsheet.py "$RS" 2>&1)"
if printf '%s' "$out" | grep -qF "fenced block with no language"; then
  ok "an untagged fence is reported"
else
  bad "an untagged fence passed unreported"
fi

write_good
printf '\n```bash\nunterminated\n' >> "$RS"
expect_fail "an unterminated fence" "unterminated code fence"

# Fences nested in a blockquote were invisible on this checker's first run, and a
# real tools/ reference inside one sailed through unchecked.
write_good
"$PY" - "$RS" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
p.write_text(p.read_text("utf-8") + "\n> ```bash\n> make no-such-target-in-a-quote\n> ```\n", "utf-8")
PYEOF
expect_fail "a command hidden inside a blockquoted fence" "no-such-target-in-a-quote"

echo
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
