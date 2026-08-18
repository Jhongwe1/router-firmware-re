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
RB="$TMP/rb-selftest.md"
trap 'rm -rf "$TMP"; rm -f "$RS"' EXIT

write_good_runbook() { cp RUNBOOK.md "$RB"; }

# A minimally valid runsheet: a front-page index, one station, one step under the
# matching station carrying the four promised fields, one real make target, one
# real tool with a real subcommand and a real flag, one resolvable
# cross-reference, one tagged output block, and a Part B.
write_good() {
  cat > "$RS" <<'MD'
# fixture

## 目錄

| 節 | 這一節做什麼 | 關掉的項目 |
|---|---|---|
| `A1.1` | a step | `P0-2` |

# Part A — 程序

## 第 1 站 · 桌面

### A1.1 a step（關 `P0-2`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T1 | 純讀 | §8.12.3 | 2026-08-17 |

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

# expect_fail_runbook <label> <needle> -- the §8.12 half. It is only checked for
# the REAL runsheet, so these pass the real one with a doctored RUNBOOK copy.
expect_fail_runbook() {
  local label="$1" needle="$2" out rc
  out="$("$PY" tools/check-runsheet.py runsheet.md --runbook "$RB" 2>&1)"; rc=$?
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

# The same failure one layer down, and it got past the case above for two weeks.
# `--disclosure reveal` sat in three of runsheet.md's commands with CI green:
# the flag is real, the VALUE is not, and argparse kills the command before it
# does anything. A checker that reads `--disclosure` and stops has read the flag
# rather than the command.
write_good
sed -i 's|python3 tools/rtcase.py todo --week W05|python3 tools/rtcase.py record --evidence telepathy|' "$RS"
expect_fail "a value outside the flag's own choices" "rejects \`--evidence telepathy\`"

# ...and the positive control, because a check that rejects every value would
# pass the case above while making the runsheet unwritable.
write_good
sed -i 's|python3 tools/rtcase.py todo --week W05|python3 tools/rtcase.py record --evidence dynamic|' "$RS"
if "$PY" tools/check-runsheet.py "$RS" >/dev/null 2>&1; then
  ok "a value that IS in the flag's choices"
else
  bad "a value that IS in the flag's choices — rejected, so the check is not usable"
  "$PY" tools/check-runsheet.py "$RS" 2>&1 | sed 's/^/          /'
fi

# A shell variable is not a value this checker can resolve, and pretending
# otherwise would turn a real check into a plausible one.
write_good
sed -i 's|python3 tools/rtcase.py todo --week W05|python3 tools/rtcase.py record --evidence "$KIND"|' "$RS"
if "$PY" tools/check-runsheet.py "$RS" >/dev/null 2>&1; then
  ok "a shell variable as the value is left alone"
else
  bad "a shell variable as the value is rejected — the checker is guessing"
  "$PY" tools/check-runsheet.py "$RS" 2>&1 | sed 's/^/          /'
fi

write_good
sed -i 's|§8.12.3|§8.99.9|' "$RS"
expect_fail "a cross-reference that resolves to no RUNBOOK heading" "does not resolve"

write_good
sed -i 's|(`RUNBOOK.md`)|(NOT-A-FILE.md)|; s|\[`RUNBOOK.md`\](RUNBOOK.md)|[x](NOT-A-FILE.md)|' "$RS"
expect_fail "a link target that does not exist" "link target NOT-A-FILE.md does not exist"

write_good
sed -i '/^| 層 | 動到裝置/d' "$RS"
expect_fail "a step with no four-field table" "declares no"

write_good
sed -i 's|2026-08-17|sometime last week|' "$RS"
expect_fail "a 最後驗證 with no date in it" "names no date"

write_good
sed -i 's#| T1 | 純讀 | §8.12.3 |#| T1 | 純讀 | see the runbook |#' "$RS"
expect_fail "a 為什麼 column naming no RUNBOOK section" "names no RUNBOOK section"

write_good
sed -i '/^# Part B/d' "$RS"
expect_fail "no Part B section" "no \`# Part B\` section"

echo
echo "=== stations: the number IS the device state a step needs ==="

# A step filed under the wrong station is a step a reader runs with the board in
# the wrong state, and nothing else in the file would say so.
write_good
sed -i 's|^## 第 1 站 · 桌面|## 第 3 站 · 服務中|' "$RS"
expect_fail "a step filed under a station that is not its own" "sits under"

write_good
sed -i '/^## 第 1 站/d' "$RS"
expect_fail "a Part A with no station headings" "no \`## 第 N 站\` station headings"

echo
echo "=== the heading owns which tests a step closes ==="

# Silence is indistinguishable from a forgotten field, so it is not allowed.
write_good
sed -i 's|^### A1.1 a step（關 `P0-2`）|### A1.1 a step|' "$RS"
expect_fail "a step heading claiming neither （關 …） nor （不關登記簿項目）" \
            "ends with neither"

echo
echo "=== the front-page index is a pointer, and a machine keeps it one ==="

write_good
sed -i '/^| `A1.1` | a step |/d' "$RS"
expect_fail "an index that does not list a step that exists" "does not list A1.1"

write_good
"$PY" - "$RS" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
p.write_text(p.read_text("utf-8").replace(
    "| `A1.1` | a step | `P0-2` |", "| `A1.1` | a step | `P0-5` |"), "utf-8")
PYEOF
expect_fail "an index disagreeing with a heading about what it closes" \
            "the 目錄 says A1.1 closes"

write_good
"$PY" - "$RS" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
p.write_text(p.read_text("utf-8").replace(
    "| `A1.1` | a step | `P0-2` |",
    "| `A1.1` | a step | `P0-2` |\n| `A9.9` | invented | — |"), "utf-8")
PYEOF
expect_fail "an index row for a step that does not exist" "which is not a step"

echo
echo "=== the other half of the split: RUNBOOK.md §8.12 ==="

# The rule that matters most here. §8.12 declared its commands had moved out and
# then carried twelve blocks, four of them already refuted at the bench -- and
# the checker could not see them because it only read runsheet.md.
write_good_runbook
"$PY" - "$RB" <<'PYEOF'
import pathlib, re, sys
p = pathlib.Path(sys.argv[1]); t = p.read_text("utf-8")
i = t.index("### 8.12.2")
p.write_text(t[:i] + "```bash\nAUTOBURN: 0\n```\n\n" + t[i:], "utf-8")
PYEOF
expect_fail_runbook "a command fence inside §8.12" "must contain no command fences"

write_good_runbook
"$PY" - "$RB" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
p.write_text(p.read_text("utf-8").replace(
    "### 8.12.2 抓 bootloader　→ `runsheet.md` `A2.2`",
    "### 8.12.2 抓 bootloader"), "utf-8")
PYEOF
expect_fail_runbook "a §8.12 subsection naming no runsheet step" \
                    "names 0 runsheet steps"

write_good_runbook
"$PY" - "$RB" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
p.write_text(p.read_text("utf-8").replace(
    "### 8.12.2 抓 bootloader　→ `runsheet.md` `A2.2`",
    "### 8.12.2 抓 bootloader　→ `runsheet.md` `A2.3`"), "utf-8")
PYEOF
expect_fail_runbook "two §8.12 subsections claiming the same step" \
                    "both claim to explain"

write_good_runbook
"$PY" - "$RB" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
p.write_text(p.read_text("utf-8").replace(
    "### 8.12.2 抓 bootloader　→ `runsheet.md` `A2.2`",
    "### 8.12.2 抓 bootloader　→ `runsheet.md` `A9.9`"), "utf-8")
PYEOF
expect_fail_runbook "a §8.12 subsection naming a step that does not exist" \
                    "which runsheet.md does not have"

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
# Both the heading and the index row, or the index/heading disagreement fires
# first and this case would pass for a reason it is not testing.
write_good
sed -i 's|`P0-2`|`P99-99`|g' "$RS"
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

# The direction that fires BEFORE a session rather than after it.
#
# Everything above keys on `executed`, so a week that has not started reads as
# fully covered. That is not hypothetical: on 2026-08-18 W07 had 58 live rows,
# 2 claimed, 11 exempted and 47 with neither, 32 of them scheduled for a bench
# visit the same evening. W08 is the fixture for it because it has sixteen live
# rows and zero results, so only the new rule can fire and a pass here cannot be
# the old rule passing by accident.
write_good
sed -i 's|## B-W99|## B-W08|' "$RS"
out="$("$PY" tools/check-runsheet.py "$RS" 2>&1)"; rc=$?
if [ "$rc" -eq 0 ]; then
  bad "a runsheet covering a week whose rows have no procedure was accepted"
elif printf '%s' "$out" | grep -qF "scheduled test(s) with no procedure"; then
  ok "a scheduled test with no step is reported before it has ever run"
else
  bad "the pre-session gap was reported for the wrong reason:"
  printf '%s\n' "$out" | sed 's/^/          /'
fi

# And the same escape hatch has to work for it, or a week that genuinely has no
# bench procedure -- because its rows are desk work -- could never be declared.
write_good
"$PY" - "$RS" <<'PYEOF'
import pathlib, sys, tomllib
p = pathlib.Path(sys.argv[1])
reg = tomllib.loads(pathlib.Path("test-cases.toml").read_text("utf-8"))
ids = sorted(c["id"] for c in reg["case"]
             if str(c.get("week")) == "W08"
             and not str(c.get("cut_reason", "")).strip())
s = p.read_text("utf-8").replace("## B-W99", "## B-W08")
s += "\n<!-- no-procedure: " + " ".join(ids) + " -- fixture -->\n"
p.write_text(s, "utf-8")
PYEOF
if "$PY" tools/check-runsheet.py "$RS" >/dev/null 2>&1; then
  ok "an outstanding row may be exempted, so an honest gap is still declarable"
else
  bad "a scheduled-but-unrun row could not be exempted"
  "$PY" tools/check-runsheet.py "$RS" 2>&1 | sed 's/^/          /'
fi

# Instrument bug 31, 2026-08-18. The checker used re.search, which takes the
# FIRST match -- and the appendix paragraph that *documents* this escape hatch
# quotes the marker inline, so it parsed as an empty exemption block sitting
# above the real one. Two exempted cases were reported as unexempted and the
# block naming them was never read. The prose describing a mechanism is not the
# mechanism, and only one of them was being looked at.
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
              and c != "P0-2"})
s = p.read_text("utf-8").replace("## B-W99", "## B-W05")
# The decoy: a documentation mention, EARLIER in the file than the real block.
s = s.replace("# fixture",
              "# fixture\n\nAnything with no procedure goes in a "
              "`<!-- no-procedure: ... -->` block with a reason.\n")
s += "\n<!-- no-procedure: " + " ".join(ids) + " — fixture -->\n"
p.write_text(s, "utf-8")
PYEOF
if "$PY" tools/check-runsheet.py "$RS" >/dev/null 2>&1; then
  ok "a prose mention of the marker does not shadow the real block"
else
  bad "the documentation of the escape hatch defeated the escape hatch"
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
echo "=== the station number IS the device state, and commands prove it ==="

# A3.24 carried `console-dump.py dump --at-prompt` for every revision up to
# 2026-08-19 while sitting under 第 3 站. --at-prompt means the board is halted
# at <RealTek>, which is 第 2 站. Reading A1.1 -> A4.2 front to back is supposed
# to BE a correct order to run it in; a step whose commands need another
# station's device state breaks that quietly, and the station-heading check
# above could not see it because the heading was fine.
write_good
"$PY" - "$RS" <<'PYEOF'
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
s = s.replace("""```bash
make ledger""", """```bash
python3 tools/console-dump.py dump --at-prompt --flash 0x0 --length 0x10000 -o /tmp/x.bin
make ledger""")
open(p, "w", encoding="utf-8").write(s)
PYEOF
expect_fail "a 第 3 站 command inside a 第 1 站 step" "cannot be run where the document puts it"

# ...and the escape hatch, because A3.8 does this legitimately: its recovery
# path says "回 A2.2 搶 bootloader（要斷電重開）" and then gives a boot-loader
# command. Naming the station you are sending the reader to is what makes that
# correct, so naming it is what the checker accepts.
write_good
"$PY" - "$RS" <<'PYEOF'
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
s = s.replace("""```bash
make ledger""", """先回 A2.2 搶 bootloader（要斷電重開），然後：

```bash
python3 tools/console-dump.py dump --at-prompt --flash 0x0 --length 0x10000 -o /tmp/x.bin
make ledger""")
open(p, "w", encoding="utf-8").write(s)
PYEOF
if "$PY" tools/check-runsheet.py "$RS" >/dev/null 2>&1; then
  ok "a deliberate detour that names the station it sends you to is accepted"
else
  bad "the detour escape hatch does not work, so A3.8 cannot be written correctly"
  "$PY" tools/check-runsheet.py "$RS" 2>&1 | sed 's/^/          /'
fi

# The other direction: a boot-loader step cannot curl the web server, because
# nothing is served until the board has booted.
write_good
"$PY" - "$RS" <<'PYEOF'
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
s = s.replace("## 第 1 站 · 桌面", "## 第 2 站 · 停在 <RealTek>")
s = s.replace("### A1.1 a step", "### A2.1 a step")
s = s.replace("| `A1.1` |", "| `A2.1` |")
s = s.replace("""```bash
make ledger""", """```bash
curl -s http://10.1.1.1/config.dat -o /tmp/c.dat
make ledger""")
open(p, "w", encoding="utf-8").write(s)
PYEOF
expect_fail "a curl at the device inside a boot-loader step" "nothing is served until the board has booted"

echo
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
