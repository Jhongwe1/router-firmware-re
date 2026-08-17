#!/usr/bin/env bash
# Self-test for tools/rtcase.py.
#
# rtcase is a gate. A gate that cannot fail is not a gate, it is a decoration
# that reports success - which is exactly how instrument bug 12 shipped in this
# project: a self-check that only fired when an override was passed, reporting
# `consistent` when none was. So every check rtcase claims to make gets a case
# here that MUST make it fail.
#
# The first case is the control and it must SUCCEED. Without it, a broken
# interpreter or a missing file would make every "this must be rejected" case
# pass for the wrong reason - the failure mode tools/test-photo-tools.sh caught
# on 2026-08-14, where 5/5 guards passed while every invocation was dying on an
# import.
#
#   bash tools/test-rtcase.sh

set -uo pipefail

cd "$(dirname "$0")/.." || { echo "  FAIL  cannot cd to the repository root"; exit 1; }

PY="${FWRE_PY:-python3}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0
fail=0
ok()  { echo "  ok    $1"; pass=$((pass + 1)); }
bad() { echo "  FAIL  $1"; fail=$((fail + 1)); }

echo "=== interpreter ==="
if ! "$PY" -c 'import tomllib' 2>/dev/null; then
  echo "  FAIL  $PY has no tomllib - rtcase needs 3.11+"
  echo "        try: FWRE_PY=\$HOME/fwre-work/venv/bin/python bash tools/test-rtcase.sh"
  exit 1
fi
ok "$($PY -V) has tomllib"

# --- helpers ---------------------------------------------------------------

# Writes a minimal but valid register to $1, then applies the sed edits in $2..
mkreg() {
  cat > "$1" <<'TOML'
schema_version = "1"
[freeze]
sha256 = "REPLACED"
[schedule]
sha256 = "REPLACED"
[ledger]
output = ".rtcase-selftest.md"
[ledger.phase_titles]
"0" = "Phase 0"
[[case]]
id = "T-1"
phase = "0"
section = "1.1"
title = "case with a refutation"
feasibility = 5
exit_evidence = "static"
week = "W05"
predict = "something"
refute = "something else"
[[case]]
id = "T-2"
phase = "0"
section = "1.2"
title = "case without a refutation"
feasibility = 3
exit_evidence = "unverified"
week = "W06"
TOML
}

# Rewrites [freeze].sha256 AND [schedule].sha256 in $1 to their current values,
# each into its own section. A single global re.sub would put the freeze hash in
# both, and then every schedule case below would fail for the wrong reason.
refreeze() {
  local hf hs
  hf="$($PY tools/rtcase.py freeze "$1")"
  hs="$($PY tools/rtcase.py schedule "$1")"
  "$PY" - "$1" "$hf" "$hs" <<'PYEOF'
import pathlib, re, sys
p = pathlib.Path(sys.argv[1])
text, section = [], None
for line in p.read_text("utf-8").splitlines(keepends=True):
    m = re.match(r"\[(\w+)\]", line)
    if m:
        section = m.group(1)
    if section in ("freeze", "schedule") and line.startswith("sha256 = "):
        line = f'sha256 = "{sys.argv[2 if section == "freeze" else 3]}"\n'
    text.append(line)
p.write_text("".join(text), "utf-8")
PYEOF
}

results() { printf '%s\n' "$1" > "$TMP/results.json"; }

# The per-case freeze stamp for $1, as rtcase computes it. Fixtures use this so
# that a case meant to test one check does not also trip the stamp check and
# pass for the wrong reason.
stamp() {
  "$PY" - "$TMP/reg.toml" "$1" <<'PYEOF'
import sys
sys.path.insert(0, "tools")
import rtcase
cases = {c["id"]: c for c in rtcase.load_register(__import__("pathlib").Path(sys.argv[1]))["case"]}
print(rtcase.case_freeze(cases[sys.argv[2]]))
PYEOF
}

run() { "$PY" tools/rtcase.py check "$TMP/reg.toml" --results "$TMP/results.json" 2>"$TMP/err"; }

# A case must be rejected, and the reason must appear in the message. Checking
# only the exit code would let a case pass for an unrelated failure.
reject() {
  local what="$1" needle="$2"
  if run; then
    bad "$what - accepted, and it must not be"
  elif ! grep -q "$needle" "$TMP/err"; then
    bad "$what - rejected, but for the wrong reason:"
    sed 's/^/          /' "$TMP/err"
  else
    ok "$what"
  fi
}

# --- 1. the control: the real register must pass ---------------------------

echo "=== control ==="
if "$PY" tools/rtcase.py check >/dev/null 2>"$TMP/err"; then
  ok "the committed register passes"
else
  bad "the committed register does not pass - every case below would then pass for free"
  sed 's/^/          /' "$TMP/err"
fi

# --- 2. freeze ------------------------------------------------------------

echo "=== the freeze ==="
mkreg "$TMP/reg.toml"; refreeze "$TMP/reg.toml"; results '{"producer":"rtcase","schema_version":"1","results":[]}'
if run; then ok "a correctly frozen register passes"; else bad "a correctly frozen register was rejected"; fi

sed -i 's/refute = "something else"/refute = "something QUIETLY EDITED"/' "$TMP/reg.toml"
reject "editing a refutation without updating the hash" "freeze mismatch"

# --- 2b. the schedule -------------------------------------------------------
#
# Added 2026-08-17. Four cases sat in W05 that W05's own plan forbids running,
# so its closure command could never reach zero. Moving them is right; moving
# them quietly is the same act as editing a prediction after the result, which
# this file already refuses. So a week may move and it must show.

echo "=== the schedule ==="
mkreg "$TMP/reg.toml"; refreeze "$TMP/reg.toml"
sed -i '0,/^week = "W05"$/s//week = "W06"/' "$TMP/reg.toml"
reject "moving a case to another week without updating the hash" "schedule mismatch"

# The hash alone is not enough: it can be re-declared as easily as it can be
# broken. What makes the move auditable is that the case has to say what it
# moved from and why.
mkreg "$TMP/reg.toml"
sed -i '0,/^week = "W05"$/s//week = "W06"\nrescheduled_from = "W05"\nreschedule_date = "2026-08-17"/' "$TMP/reg.toml"
refreeze "$TMP/reg.toml"
reject "rescheduling with no reason on the record" "no reschedule_reason"

mkreg "$TMP/reg.toml"
sed -i '0,/^week = "W05"$/s//week = "W06"\nrescheduled_from = "W05"\nreschedule_reason = "because"/' "$TMP/reg.toml"
refreeze "$TMP/reg.toml"
reject "rescheduling with no date" "no reschedule_date"

mkreg "$TMP/reg.toml"
sed -i '0,/^week = "W05"$/s//week = "W05"\nrescheduled_from = "W05"\nreschedule_reason = "x"\nreschedule_date = "2026-08-17"/' "$TMP/reg.toml"
refreeze "$TMP/reg.toml"
reject "a reschedule record whose from and to are the same week" "the same"

mkreg "$TMP/reg.toml"
sed -i '0,/^week = "W05"$/s//week = "W05"\nreschedule_reason = "moved, honest"/' "$TMP/reg.toml"
refreeze "$TMP/reg.toml"
reject "a reason with no rescheduled_from" "does not say what it moved from"

# And the positive control for this block: a complete, honest reschedule passes.
mkreg "$TMP/reg.toml"
sed -i '0,/^week = "W05"$/s//week = "W06"\nrescheduled_from = "W05"\nreschedule_reason = "the week plan forbids it"\nreschedule_date = "2026-08-17"/' "$TMP/reg.toml"
refreeze "$TMP/reg.toml"
if run; then
  ok "a reschedule with from, reason, date and a re-declared hash passes"
else
  bad "a complete reschedule was rejected"; sed 's/^/          /' "$TMP/err"
fi

# --- 3. an empty freeze set must not pass vacuously ------------------------

echo "=== the control inside the tool ==="
mkreg "$TMP/reg.toml"
sed -i '/^predict = /d;/^refute = /d' "$TMP/reg.toml"
refreeze "$TMP/reg.toml"
reject "a register where nothing is frozen" "prove nothing"

# --- 4. refutation-before-result ------------------------------------------

echo "=== refute first ==="
mkreg "$TMP/reg.toml"; refreeze "$TMP/reg.toml"
S1="$(stamp T-1)"; S2="$(stamp T-2)"
res() { results "{\"producer\":\"rtcase\",\"schema_version\":\"1\",\"results\":[{$1}]}"; }
GOOD="\"id\":\"T-1\",\"date\":\"2026-08-20\",\"verdict\":\"confirmed\",\"evidence_kind\":\"dynamic\",\"artefacts\":[\"README.md\"],\"case_freeze_sha256\":\"$S1\""

res "$GOOD"
if run; then ok "a well-formed result passes"; else bad "a well-formed result was rejected"; sed 's/^/          /' "$TMP/err"; fi

res "\"id\":\"T-2\",\"date\":\"2026-08-20\",\"verdict\":\"confirmed\",\"evidence_kind\":\"dynamic\",\"artefacts\":[\"README.md\"],\"case_freeze_sha256\":\"$S2\""
reject "a result for a case with no refutation condition" "no refutation condition"

res "\"id\":\"T-9\",\"date\":\"2026-08-20\",\"verdict\":\"confirmed\",\"evidence_kind\":\"dynamic\",\"artefacts\":[\"README.md\"],\"case_freeze_sha256\":\"$S1\""
reject "a result for a case that does not exist" "unknown case"

# --- 5. the stamp: a prediction edited after its result ---------------------

echo "=== the stamp ==="
res "${GOOD/\"case_freeze_sha256\":\"$S1\"/\"note\":\"\"}"
reject "a result with no case_freeze_sha256" "carries no case_freeze_sha256"

res "$GOOD"
sed -i 's/refute = "something else"/refute = "something WEAKER, written after the fact"/' "$TMP/reg.toml"
refreeze "$TMP/reg.toml"
reject "editing a refutation that already has a result against it" "has been edited since the"

# --- 6. evidence ----------------------------------------------------------

echo "=== evidence ==="
mkreg "$TMP/reg.toml"; refreeze "$TMP/reg.toml"
res "\"id\":\"T-1\",\"date\":\"2026-08-20\",\"verdict\":\"confirmed\",\"evidence_kind\":\"dynamic\",\"artefacts\":[],\"case_freeze_sha256\":\"$S1\""
reject "a confirmed verdict naming no artefact" "not evidence"

res "\"id\":\"T-1\",\"date\":\"2026-08-20\",\"verdict\":\"confirmed\",\"evidence_kind\":\"dynamic\",\"artefacts\":[\"notes/does-not-exist.md\"],\"case_freeze_sha256\":\"$S1\""
reject "an artefact path that does not exist" "does not exist"

res "\"id\":\"T-1\",\"date\":\"2026-08-20\",\"verdict\":\"confirmed\",\"evidence_kind\":\"guess\",\"artefacts\":[\"README.md\"],\"case_freeze_sha256\":\"$S1\""
reject "an evidence_kind that is neither static nor dynamic" "evidence_kind"

res "\"id\":\"T-1\",\"verdict\":\"confirmed\",\"evidence_kind\":\"dynamic\",\"artefacts\":[\"README.md\"],\"case_freeze_sha256\":\"$S1\""
reject "a result with no date" "no date"

# --- 6b. the marks: executed is not the same as executed on the device -----
#
# W05 added a third evidence grade, `emulated`, for results produced by running
# this unit's own binaries under qemu against its own flash image. The whole
# reason it is a separate grade is that it must not be readable as the dynamic
# tick, and "must not" is worth nothing until something checks it. This also
# fails if a fourth grade is ever added without deciding what it renders as.

echo "=== marks ==="

mark_for() {
  "$PY" - "$1" <<'PYEOF'
import sys
sys.path.insert(0, "tools")
import rtcase
print(rtcase.verdict_cell({}, {"verdict": "confirmed", "evidence_kind": sys.argv[1]}, 1))
PYEOF
}

TICK="$(mark_for dynamic)"
if [ -n "$TICK" ]; then
  ok "a confirmed/dynamic result renders as the tick ($TICK)"
else
  bad "a confirmed/dynamic result renders as nothing - the control below is meaningless"
fi

for kind in $("$PY" -c 'import sys; sys.path.insert(0,"tools"); import rtcase; print(" ".join(k for k in rtcase.EVIDENCE_KINDS if k != "dynamic"))'); do
  m="$(mark_for "$kind")"
  if [ "$m" = "$TICK" ]; then
    bad "a confirmed/$kind result renders as the dynamic tick"
  elif [ -z "$m" ]; then
    bad "a confirmed/$kind result renders as nothing at all"
  else
    ok "a confirmed/$kind result renders as $m, not the tick"
  fi
done

# --- 7. cuts --------------------------------------------------------------

echo "=== cuts ==="
mkreg "$TMP/reg.toml"
sed -i '/^refute = "something else"$/a cut_reason = "not in scope"' "$TMP/reg.toml"
refreeze "$TMP/reg.toml"
res "\"id\":\"T-1\",\"date\":\"2026-08-20\",\"verdict\":\"na\",\"evidence_kind\":\"static\",\"artefacts\":[],\"case_freeze_sha256\":\"$S1\""
reject "a result recorded against a case that was cut" "was cut"

mkreg "$TMP/reg.toml"
printf 'cut_reason = "   "\n' >> "$TMP/reg.toml"
refreeze "$TMP/reg.toml"
results '{"producer":"rtcase","schema_version":"1","results":[]}'
reject "a cut with an empty reason" "cut_reason is present but empty"

# --- 8. register shape ----------------------------------------------------

echo "=== register shape ==="
mkreg "$TMP/reg.toml"
sed -i '0,/id = "T-2"/s//id = "T-1"/' "$TMP/reg.toml"
refreeze "$TMP/reg.toml"
reject "two cases sharing an id" "duplicate id"

mkreg "$TMP/reg.toml"
sed -i 's/feasibility = 5/feasibility = 9/' "$TMP/reg.toml"
refreeze "$TMP/reg.toml"
reject "a feasibility outside 1-5" "feasibility"

mkreg "$TMP/reg.toml"
sed -i 's/exit_evidence = "static"/exit_evidence = "probably"/' "$TMP/reg.toml"
refreeze "$TMP/reg.toml"
reject "an exit_evidence outside the enum" "exit_evidence"

mkreg "$TMP/reg.toml"
sed -i 's/phase = "0"/phase = "7"/' "$TMP/reg.toml"
refreeze "$TMP/reg.toml"
reject "a phase with no title" "no title"

# --- 9. record refuses before it writes -----------------------------------

echo "=== record ==="
mkreg "$TMP/reg.toml"; refreeze "$TMP/reg.toml"; results '{"producer":"rtcase","schema_version":"1","results":[]}'
if "$PY" tools/rtcase.py record --register "$TMP/reg.toml" --results "$TMP/results.json" \
     --id T-2 --date 2026-08-20 --verdict confirmed --evidence dynamic --artefact README.md \
     >/dev/null 2>"$TMP/err"; then
  bad "record wrote a result for a case with no refutation condition"
elif ! grep -q "no refutation condition" "$TMP/err"; then
  bad "record refused, but for the wrong reason:"
  sed 's/^/          /' "$TMP/err"
else
  ok "record refuses a case with no refutation condition, before writing anything"
fi

if "$PY" tools/rtcase.py record --register "$TMP/reg.toml" --results "$TMP/results.json" \
     --id T-1 --date 2026-08-20 --verdict confirmed --evidence dynamic --artefact README.md \
     >/dev/null 2>"$TMP/err"; then
  if grep -q '"register_freeze_sha256"' "$TMP/results.json"; then
    ok "record writes, and stamps the freeze the result was taken under"
  else
    bad "record wrote without stamping register_freeze_sha256"
  fi
else
  bad "record refused a well-formed result:"
  sed 's/^/          /' "$TMP/err"
fi

# --- 10. todo: the week schedule has to reflect what is actually recorded ---

echo "=== todo ==="
mkreg "$TMP/reg.toml"; refreeze "$TMP/reg.toml"
results '{"producer":"rtcase","schema_version":"1","results":[]}'
if "$PY" tools/rtcase.py todo "$TMP/reg.toml" --results "$TMP/results.json" --week W05 \
     2>"$TMP/err" | grep -q "T-1"; then
  ok "todo lists an outstanding item for its week"
else
  bad "todo did not list the outstanding item"
  sed 's/^/          /' "$TMP/err"
fi

# The one that matters: once a result exists, the item must drop off the list.
# A schedule that keeps showing done work is a schedule nobody reads.
res "$GOOD"
if "$PY" tools/rtcase.py todo "$TMP/reg.toml" --results "$TMP/results.json" --week W05 \
     2>"$TMP/err" | grep -q "T-1"; then
  bad "todo still lists T-1 after a result was recorded for it"
else
  ok "todo drops an item once it has a result"
fi

echo
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
