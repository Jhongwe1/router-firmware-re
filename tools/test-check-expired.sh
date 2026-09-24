#!/usr/bin/env bash
# Guard suite for tools/check-expired.py.
#
# The checker has exactly three judgements to get right, and each one can fail
# in both directions:
#
#   * the phrase is present in the author's voice           -> must fail
#   * the phrase is present but the line carries a date on
#     or before the expiry                                  -> must pass
#   * the phrase is present inside a fence or a code span,
#     i.e. the repository is discussing the bug rather than
#     committing it                                         -> must pass
#
# The third rule was added after the first run flagged five lines, four of them
# this repository's own account of the W07 failure. A checker that cannot tell a
# claim from a quotation of a claim makes the write-up unable to describe its
# own corrections, which would be a worse outcome than the bug.
#
#   bash tools/test-check-expired.sh
set -uo pipefail

cd "$(dirname "$0")/.." || { echo "  FAIL  cannot cd to the repository root"; exit 1; }
TOOL="$(pwd)/tools/check-expired.py"
PY="${PYTHON:-python3}"

pass=0; fail=0
ok()  { echo "  ok    $1"; pass=$((pass + 1)); }
bad() { echo "  FAIL  $1"; fail=$((fail + 1)); }

SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

build() {
  local d="$SCRATCH/$1"
  mkdir -p "$d/tools" "$d/notes" "$d/journal"
  cp "$TOOL" "$d/tools/check-expired.py"
  git -C "$d" init -q
  git -C "$d" config user.email t@t
  git -C "$d" config user.name t
  echo "$d"
}
# The output is captured into a variable and grepped separately, NOT piped.
# `set -o pipefail` makes a pipeline inherit the checker's exit status, and this
# checker's whole job is to exit 1 -- so `checker | grep -q` returned 1 even when
# grep matched, and every must_catch case reported a false failure. Instrument
# bug 60: the third this week to be wrong in the direction of finding something.
run() {
  OUT="$( cd "$1" && "$PY" tools/check-expired.py 2>&1 )"
  RC=$?
}

must_catch() {
  local d="$1" label="$2" want="$3"
  run "$d"
  if [ "$RC" = "0" ]; then bad "$label -- exited 0"
  elif ! printf '%s' "$OUT" | grep -qF "$want"; then
    bad "$label -- failed, but not about '$want': $(printf '%s' "$OUT" | head -2 | tr '\n' ' ')"
  else ok "$label"; fi
}
must_pass() {
  local d="$1" label="$2"
  run "$d"
  if [ "$RC" = "0" ]; then ok "$label"
  else bad "$label -- flagged correct input: $(printf '%s' "$OUT" | head -2 | tr '\n' ' ')"; fi
}

echo "tools/check-expired.py -- claims it must catch, and quotations it must not"

# --- the assertion, in the author's voice ------------------------------------
d="$(build plain)"
printf '# n\n\nStatic only. No device has been powered on.\n' > "$d/notes/a.md"
git -C "$d" add -A && git -C "$d" commit -qm x
must_catch "$d" "the bare assertion, six weeks after it stopped being true" "stopped being true on 2026-08-15"

# --- the fix the checker must accept -----------------------------------------
# Dating the sentence is THE fix. If the checker rejected this it would be
# teaching its operator to delete the observation instead of dating it, which
# destroys evidence to satisfy a tool.
d="$(build dated)"
printf '# n\n\nW02 Day 1, 2026-08-14: no device has been powered on.\n' > "$d/notes/a.md"
git -C "$d" add -A && git -C "$d" commit -qm x
must_pass "$d" "a date on or before the expiry turns a claim into an observation"

d="$(build dated-after)"
printf '# n\n\nOn 2026-09-01: no device has been powered on.\n' > "$d/notes/a.md"
git -C "$d" add -A && git -C "$d" commit -qm x
must_catch "$d" "a date AFTER the expiry does not excuse it" "stopped being true"

# --- quotation, not assertion -------------------------------------------------
d="$(build backticks)"
printf '# n\n\nSix files asserted `52869/tcp open` in the present tense, and W07 fixed them.\n' \
  > "$d/notes/a.md"
git -C "$d" add -A && git -C "$d" commit -qm x
must_pass "$d" "inside a code span: the repository discussing its own bug"

d="$(build fenced)"
printf '# n\n\n```\n52869/tcp open   unknown syn-ack ttl 64\n```\n' > "$d/notes/a.md"
git -C "$d" add -A && git -C "$d" commit -qm x
must_pass "$d" "inside a fence: captured scanner output, quoted verbatim"

# Positive control for the two above -- without it, "skips everything" and
# "skips quotations" are the same suite.
d="$(build fenced-control)"
printf '# n\n\n```\n52869/tcp open\n```\n\nThe port 52869/tcp open right now.\n' > "$d/notes/a.md"
git -C "$d" add -A && git -C "$d" commit -qm x
must_catch "$d" "positive control: the same phrase outside the fence is caught" "stopped being true"

# --- scope ---------------------------------------------------------------------
d="$(build journal)"
printf '# j\n\nNo device has been powered on.\n' > "$d/journal/PROGRESS.md"
git -C "$d" add -A && git -C "$d" commit -qm x
must_pass "$d" "journal/ is exempt -- it records what was believed on a day"

d="$(build untracked)"
printf '# n\n\nNo device has been powered on.\n' > "$d/notes/a.md"
printf 'notes/\n' > "$d/.gitignore"
git -C "$d" add .gitignore && git -C "$d" commit -qm x
must_pass "$d" "an untracked file is not published, so it is not judged"

# --- the other rows on the register ---------------------------------------------
d="$(build twcert)"
printf '# n\n\nThis will be reported to TWCERT/CC before publication.\n' > "$d/notes/a.md"
git -C "$d" add -A && git -C "$d" commit -qm x
must_catch "$d" "the disclosure promise retired on 2026-08-23" "stopped being true on 2026-08-23"

d="$(build phantom)"
printf '# n\n\nAlso compared against V4.1.5cu from a mirror.\n' > "$d/notes/a.md"
git -C "$d" add -A && git -C "$d" commit -qm x
must_catch "$d" "the image that exists in no manifest" "stopped being true on 2026-09-25"

d="$(build w02task)"
printf '# n\n\nConfirming the chip marking is a W02 task.\n' > "$d/notes/a.md"
git -C "$d" add -A && git -C "$d" commit -qm x
must_catch "$d" "\"is a W02 task\" after W02 closed" "stopped being true on 2026-08-16"

# --- the register itself ---------------------------------------------------------
d="$(build clean)"
printf '# n\n\nEverything here is measured and dated.\n' > "$d/notes/a.md"
git -C "$d" add -A && git -C "$d" commit -qm x
must_pass "$d" "a corpus with none of them present"

if "$PY" "$TOOL" --list 2>&1 | grep -q "expired assertions on the register"; then
  ok "--list prints the register rather than only the failures"
else
  bad "--list does not print the register"
fi

echo
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
