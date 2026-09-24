#!/usr/bin/env bash
# Guard suite for tools/check-links.py.
#
# The checker's first run on this repository reported 21 broken links. Eighteen
# of them were the checker. Its slug function collapsed runs of whitespace, so
# every anchor spanning an em dash came out one hyphen short; and it blanked
# inline code before slugging, so every heading naming a symbol lost the symbol.
# Both failed in the same direction -- **finding something** -- which is the
# expensive direction, because a checker that invents work is obeyed twice
# before it is doubted.
#
# So this suite is built around the two things a link checker can be wrong
# about, in both directions:
#
#   * whether a target resolves -- and the case that matters here is a file that
#     is **on disk but not in the repository**, because that is the one the
#     file system agrees with and the reader does not. It is the bug the checker
#     was written for and it gets its own case;
#   * whether an anchor exists -- where every false positive is a heading the
#     slugger rendered differently from GitHub. The four regression cases below
#     are the four shapes this repository's headings actually take.
#
# Each case builds a throw-away git repository, because `git ls-files` is the
# checker's only source of truth and a suite that stubbed it would be testing
# something else.
#
#   bash tools/test-check-links.sh
set -uo pipefail

cd "$(dirname "$0")/.." || { echo "  FAIL  cannot cd to the repository root"; exit 1; }
TOOL="$(pwd)/tools/check-links.py"
PY="${PYTHON:-python3}"

pass=0; fail=0
ok()  { echo "  ok    $1"; pass=$((pass + 1)); }
bad() { echo "  FAIL  $1"; fail=$((fail + 1)); }

SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

# build <name> -- a fresh git repo at $SCRATCH/<name> with the checker in place.
# Nothing is committed by the helper; each case stages exactly what it means the
# repository to contain, which is the distinction under test.
build() {
  local d="$SCRATCH/$1"
  mkdir -p "$d/tools"
  cp "$TOOL" "$d/tools/check-links.py"
  git -C "$d" init -q
  git -C "$d" config user.email t@t
  git -C "$d" config user.name t
  echo "$d"
}

# run <dir> -- the checker's exit code and output, from inside that repo.
run() {
  ( cd "$1" && "$PY" tools/check-links.py 2>&1 )
}
rc() {
  ( cd "$1" && "$PY" tools/check-links.py >/dev/null 2>&1; echo $? )
}

# must_catch <name> <expected substring>
must_catch() {
  local d="$1" label="$2" want="$3" out code
  out="$(run "$d")"; code="$(rc "$d")"
  if [ "$code" = "0" ]; then
    bad "$label -- exited 0; it should have failed"
  elif ! printf '%s' "$out" | grep -qF "$want"; then
    bad "$label -- failed, but not about '$want': $(printf '%s' "$out" | head -2 | tr '\n' ' ')"
  else
    ok "$label"
  fi
}

# must_pass <name>
must_pass() {
  local d="$1" label="$2" out code
  out="$(run "$d")"; code="$(rc "$d")"
  if [ "$code" = "0" ]; then ok "$label"
  else bad "$label -- flagged correct input: $(printf '%s' "$out" | head -3 | tr '\n' ' ')"; fi
}

echo "tools/check-links.py -- the breaks it must catch, and the correct links it must not"

# ---------------------------------------------------------------------------
# Resolution: what a reader gets
# ---------------------------------------------------------------------------

d="$(build missing)"
printf '# t\n\n[gone](notes/nope.md)\n' > "$d/README.md"
git -C "$d" add README.md && git -C "$d" commit -qm x
must_catch "$d" "a target that does not exist anywhere" "does not exist"

# THE case. `plan/` is in .gitignore, it is on the author's disk, and the link
# to it in README.md was a 404 for eleven weeks while every filesystem-based
# check passed. A checker that uses os.path.exists reports this repo clean.
d="$(build untracked)"
mkdir -p "$d/plan"
printf 'week one\n' > "$d/plan/W01.md"
printf 'plan/\n' > "$d/.gitignore"
printf '# t\n\n[the week plans](plan/)\n' > "$d/README.md"
git -C "$d" add README.md .gitignore && git -C "$d" commit -qm x
must_catch "$d" "on disk, gitignored -- the bug this was written for" "does not track it"

d="$(build tracked-dir)"
mkdir -p "$d/notes"
printf '# n\n' > "$d/notes/a.md"
printf '# t\n\n[notes](notes/)\n' > "$d/README.md"
git -C "$d" add README.md notes/a.md && git -C "$d" commit -qm x
must_pass "$d" "a directory with tracked files under it resolves"

d="$(build relative)"
mkdir -p "$d/notes" "$d/writeup"
printf '# n\n' > "$d/notes/a.md"
printf '# w\n\n[back](../notes/a.md)\n' > "$d/writeup/ch.md"
printf '# t\n' > "$d/README.md"
git -C "$d" add . && git -C "$d" commit -qm x
must_pass "$d" "../ resolves against the linking file, not the repo root"

d="$(build escape)"
mkdir -p "$d/writeup"
printf '# w\n\n[out](../../etc/passwd)\n' > "$d/writeup/ch.md"
printf '# t\n' > "$d/README.md"
git -C "$d" add . && git -C "$d" commit -qm x
must_catch "$d" "a path climbing above the repository root" "does not exist"

d="$(build external)"
printf '# t\n\n[nvd](https://nvd.nist.gov/x)\n[m](mailto:a@b.c)\n[p](//cdn/x.js)\n' > "$d/README.md"
git -C "$d" add . && git -C "$d" commit -qm x
must_pass "$d" "http / mailto / protocol-relative are out of scope"

# ---------------------------------------------------------------------------
# Where a link is not a link
# ---------------------------------------------------------------------------

d="$(build fenced)"
printf '# t\n\n```\n[example](nowhere/at/all.md)\n```\n' > "$d/README.md"
git -C "$d" add . && git -C "$d" commit -qm x
must_pass "$d" "a link inside a fenced block is an example, not a link"

d="$(build inline-code)"
printf '# t\n\nwrite it as `[x](nowhere.md)` and it renders literally\n' > "$d/README.md"
git -C "$d" add . && git -C "$d" commit -qm x
must_pass "$d" "a link inside inline code is not a link"

# The inverse, so the two cases above cannot pass by the checker ignoring
# everything: an identical target outside a fence must still be caught.
d="$(build fenced-control)"
printf '# t\n\n```\n[example](nowhere/at/all.md)\n```\n\n[real](nowhere/at/all.md)\n' > "$d/README.md"
git -C "$d" add . && git -C "$d" commit -qm x
must_catch "$d" "positive control: the same target outside the fence is caught" "does not exist"

d="$(build refdef)"
printf '# t\n\nsee [the note][n]\n\n[n]: notes/gone.md\n' > "$d/README.md"
git -C "$d" add . && git -C "$d" commit -qm x
must_catch "$d" "a reference definition is a link too" "does not exist"

# ---------------------------------------------------------------------------
# Anchors -- the four heading shapes this repository actually uses
# ---------------------------------------------------------------------------

d="$(build anchor-missing)"
printf '# t\n\n## A real heading\n\n[jump](#a-heading-that-is-not-there)\n' > "$d/README.md"
git -C "$d" add . && git -C "$d" commit -qm x
must_catch "$d" "an anchor with no heading behind it" "no heading"

# Regression, instrument bug 1: punctuation leaves its gap behind. `codes — a`
# renders as `codes--a`, two hyphens, because GitHub replaces each space and
# does not collapse the run.
d="$(build anchor-emdash)"
printf '# t\n\n## 6. Date codes — a prediction written *before* the dump\n\n[j](#6-date-codes--a-prediction-written-before-the-dump)\n' > "$d/README.md"
git -C "$d" add . && git -C "$d" commit -qm x
must_pass "$d" "regression: em dash leaves a double hyphen, emphasis is stripped"

# Regression, instrument bug 2: GitHub slugs the rendered heading, so inline
# code contributes its contents. Blanking it first deleted the symbol.
d="$(build anchor-code)"
printf '# t\n\n### 7.4 `J2` and the power switch\n\n[j](#74-j2-and-the-power-switch)\n' > "$d/README.md"
git -C "$d" add . && git -C "$d" commit -qm x
must_pass "$d" "regression: a symbol in backticks stays in the anchor"

d="$(build anchor-slash)"
printf '# t\n\n## W02 — 2026-08-14 / 16\n\n[j](#w02--2026-08-14--16)\n' > "$d/README.md"
git -C "$d" add . && git -C "$d" commit -qm x
must_pass "$d" "regression: a slash between spaces leaves two hyphens"

d="$(build anchor-dupe)"
printf '# t\n\n## Corrections\n\n## Corrections\n\n[a](#corrections)\n[b](#corrections-1)\n' > "$d/README.md"
git -C "$d" add . && git -C "$d" commit -qm x
must_pass "$d" "a repeated heading gets the -1 suffix GitHub gives it"

d="$(build anchor-cross)"
mkdir -p "$d/notes"
printf '# n\n\n## The five ICs\n' > "$d/notes/a.md"
printf '# t\n\n[j](notes/a.md#the-five-ics)\n' > "$d/README.md"
git -C "$d" add . && git -C "$d" commit -qm x
must_pass "$d" "an anchor in another file is resolved in that file"

d="$(build anchor-cross-bad)"
mkdir -p "$d/notes"
printf '# n\n\n## The five ICs\n' > "$d/notes/a.md"
printf '# t\n\n[j](notes/a.md#the-six-ics)\n' > "$d/README.md"
git -C "$d" add . && git -C "$d" commit -qm x
must_catch "$d" "a wrong anchor in another file is caught" "has no heading"

# A heading inside a fenced block is not a heading, so an anchor to it is not
# an anchor. Without this the checker would certify links into example output.
d="$(build anchor-fenced-heading)"
printf '# t\n\n```\n## Not a heading\n```\n\n[j](#not-a-heading)\n' > "$d/README.md"
git -C "$d" add . && git -C "$d" commit -qm x
must_catch "$d" "a heading inside a fence does not create an anchor" "no heading"

# ---------------------------------------------------------------------------
# The boundary this checker declares
# ---------------------------------------------------------------------------

# Non-ASCII fragments are not judged, because GitHub's CJK slug rule is not the
# documented ASCII one. The file half must still be checked -- skipping the
# fragment must not skip the link.
d="$(build cjk-skip)"
printf '# t\n\n## 四、下一場從哪裡開始\n\n[j](#四下一場從哪裡開始)\n' > "$d/README.md"
git -C "$d" add . && git -C "$d" commit -qm x
must_pass "$d" "a CJK fragment is skipped rather than guessed at"

d="$(build cjk-file-half)"
printf '# t\n\n[j](journal/gone.md#四、下一場)\n' > "$d/README.md"
git -C "$d" add . && git -C "$d" commit -qm x
must_catch "$d" "a CJK fragment does not excuse a missing file" "does not exist"

echo
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
