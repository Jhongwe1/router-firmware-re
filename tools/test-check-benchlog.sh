#!/usr/bin/env bash
# Guard suite for tools/check-benchlog.py.
#
# The checker exists because a record-card template that lived only in the
# gitignored plan/ drifted out of the bench log within one week. This suite
# exists because that checker, on its own first run, reported "19 record cards,
# every one with a refutation check" about a file holding thirty - it took one
# fenced block to be one card, and W05 had written five cards in one block.
#
# So the control that matters here is not "does it reject a bad card". It is
# **does it see every card there is**. A checker that silently covers a subset
# passes a suite of refusals just as happily as one that works.
#
#   bash tools/test-check-benchlog.sh
#
set -uo pipefail

cd "$(dirname "$0")/.." || { echo "  FAIL  cannot cd to the repository root"; exit 1; }
PY="${FWRE_PY:-python3}"
TOOL="tools/check-benchlog.py"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
ok()  { echo "  ok    $1"; pass=$((pass + 1)); }
bad() { echo "  FAIL  $1"; fail=$((fail + 1)); }

good_card() {
  cat <<'EOF'
T-01  P0-1  a thing                                    07:31
      判定: ✅ 成立
      反證檢查: 測前寫下「看到 X 就是不成立」，實際看到 Y
EOF
}

expect_refusal() {
  local label="$1" needle="$2" file="$3" out rc
  out="$("$PY" "$TOOL" "$file" 2>&1)"; rc=$?
  if [ "$rc" -eq 0 ]; then
    bad "$label — accepted when it should have refused"
  elif printf '%s' "$out" | grep -qF -- "$needle"; then
    ok "$label"
  else
    bad "$label — refused for the wrong reason: $(printf '%s' "$out" | head -1)"
  fi
}

echo "check-benchlog guard suite"
echo
echo "=== the refusals ==="

{ echo '```text'; good_card | sed '/反證檢查/d'; echo '```'; } > "$TMP/no-refute.md"
expect_refusal "a card with no 反證檢查 is refused" "no 反證檢查 field" "$TMP/no-refute.md"

{ echo '```text'; good_card | sed 's/^      判定.*//'; echo '```'; } > "$TMP/no-verdict.md"
expect_refusal "a card with no 判定 is refused" "no 判定 line" "$TMP/no-verdict.md"

{ echo '```text'; good_card | sed 's/判定: ✅ 成立/判定: it went fine/'; echo '```'; } > "$TMP/no-marker.md"
expect_refusal "a 判定 with none of the four markers is refused" "none of the four markers" "$TMP/no-marker.md"

{ echo '```text'; good_card | sed 's/                                    07:31//'; echo '```'; } > "$TMP/no-time.md"
expect_refusal "a card with no time is refused" "no time on its header line" "$TMP/no-time.md"

# Half a refutation is the failure this whole file is about: the condition
# written beforehand, and then no statement of what was actually seen.
{ echo '```text'; good_card | sed 's/，實際看到 Y//'; echo '```'; } > "$TMP/half.md"
expect_refusal "a 反證檢查 that stops after the pre-written condition is refused" \
               "records what was written beforehand and stops" "$TMP/half.md"

{ echo '```text'; good_card | sed 's/測前寫下「看到 X 就是不成立」，//'; echo '```'; } > "$TMP/unquoted.md"
expect_refusal "a 反證檢查 with no quoted pre-written condition is refused" \
               "does not quote the condition" "$TMP/unquoted.md"

{ echo '```text'; good_card; good_card; echo '```'; } > "$TMP/dup.md"
expect_refusal "two cards with the same id are refused" "is already used at line" "$TMP/dup.md"

printf '# nothing here\n\nno cards at all.\n' > "$TMP/empty.md"
expect_refusal "a file with no cards is refused, not passed vacuously" \
               "no record cards found at all" "$TMP/empty.md"

{ echo '<!-- benchlog-exempt: T-01 short -->'; echo '```text'; good_card | sed '/反證檢查/d'; echo '```'; } > "$TMP/thin.md"
expect_refusal "an exemption with no real reason is refused" "has no real reason" "$TMP/thin.md"

echo
echo "=== the controls ==="

{ echo '```text'; good_card; echo '```'; } > "$TMP/good.md"
if "$PY" "$TOOL" "$TMP/good.md" >/dev/null 2>&1; then
  ok "positive control: a well-formed card passes"
else
  bad "positive control: a well-formed card was refused"
fi

# THE control this suite exists for. Five cards in ONE fence: the first version
# of the checker saw one and reported success for the file.
{
  echo '```text'
  for n in 01 02 03 04 05; do
    printf 'T-%s  P0-1  card %s                                   07:3%s\n' "$n" "$n" "${n#0}"
    printf '      判定: ✅ 成立\n'
    printf '      反證檢查: 測前寫下「看到 X 就是不成立」，實際看到 Y\n\n'
  done
  echo '```'
} > "$TMP/multi.md"
out="$("$PY" "$TOOL" "$TMP/multi.md" 2>&1)"
if printf '%s' "$out" | grep -q '5 record cards'; then
  ok "five cards in ONE fenced block are all counted, not just the first"
else
  bad "multi-card fence miscounted: $(printf '%s' "$out" | tail -1)"
fi

# And prove the count is load-bearing: break the LAST card in a shared fence and
# it must still be caught. If only the first card is parsed, this passes wrongly.
{
  echo '```text'
  printf 'T-01  P0-1  fine                                       07:31\n'
  printf '      判定: ✅ 成立\n'
  printf '      反證檢查: 測前寫下「看到 X 就是不成立」，實際看到 Y\n\n'
  printf 'T-02  P0-2  broken                                     07:32\n'
  printf '      判定: ✅ 成立\n'
  echo '```'
} > "$TMP/last-broken.md"
expect_refusal "a broken card LAST in a shared fence is still caught" \
               "T-02 has **no 反證檢查 field**" "$TMP/last-broken.md"

{
  echo '<!-- benchlog-exempt: T-01 this card predates the checker and the file is'
  echo 'append-only, so it stays as it is and the gap is recorded rather than fixed -->'
  echo '```text'; good_card | sed '/反證檢查/d'; echo '```'
} > "$TMP/exempt.md"
if "$PY" "$TOOL" "$TMP/exempt.md" 2>&1 | grep -q '1 exempted with a reason'; then
  ok "an exemption with a real reason is honoured, and reported rather than hidden"
else
  bad "the exemption was not honoured or not reported"
fi

echo
echo "=== every session PROGRESS.md records has an entry here ==="
#
# Added 2026-08-18, the day the rule it enforces was broken. A desk-only session
# rewrote three of the next bench visit's predictions and wrote nothing in the
# bench log, because nothing had been typed at the device and the file felt
# inapplicable. The author caught it; no tool could have. These four cases are
# the ones that separate "the check works" from "the check is present".
#
S="$TMP/sessions"; mkdir -p "$S"
{ echo '```text'; good_card; echo '```'; } > "$S/cards.md"

mk_pair() {  # mk_pair <bench-heading-line...> ; PROGRESS body on stdin
  cat "$S/cards.md" > "$S/BENCH-LOG.md"
  printf '%s\n' "$@" >> "$S/BENCH-LOG.md"
  cat > "$S/PROGRESS.md"
}

mk_pair '# 2026-08-17 — a session that happened' <<'EOF'
## W06 — 2026-08-17 (night)
## W07 Day 3 — a desk-only day — 2026-08-18
EOF
expect_refusal "a PROGRESS session with no bench-log entry for that date is refused" \
               "PROGRESS.md records a session on 2026-08-18" "$S/BENCH-LOG.md"

mk_pair '# 2026-08-17 — a session that happened' \
        '# 2026-08-18 — the plan for the next visit, written before touching anything' <<'EOF'
## W06 — 2026-08-17 (night)
## W07 Day 3 — a desk-only day — 2026-08-18
EOF
if "$PY" "$TOOL" "$S/BENCH-LOG.md" >/dev/null 2>&1; then
  ok "a session WITH an entry on the same date is accepted"
else
  bad "a session with a matching entry was refused"
fi

# The floor. W01-W04 predate the bench log because they predate the device.
mk_pair '# 2026-08-17 — the first bench day' <<'EOF'
## W03 — 2026-08-10
## W04 — 2026-08-11
EOF
if "$PY" "$TOOL" "$S/BENCH-LOG.md" >/dev/null 2>&1; then
  ok "sessions predating the bench log's first entry are exempt"
else
  bad "a pre-bench-log session was wrongly refused"
fi

# And the one that makes the heading rule load-bearing: a date mentioned only in
# prose is a reference, not an entry. Taking any date anywhere would accept this.
mk_pair '# 2026-08-17 — a session that happened' \
        'On 2026-08-18 the desk work changed three predictions.' <<'EOF'
## W06 — 2026-08-17 (night)
## W07 Day 3 — a desk-only day — 2026-08-18
EOF
expect_refusal "a date mentioned only in prose does not count as an entry" \
               "PROGRESS.md records a session on 2026-08-18" "$S/BENCH-LOG.md"

echo
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
