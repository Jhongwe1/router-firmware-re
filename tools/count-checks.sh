#!/usr/bin/env bash
# How many checks does `make ci` actually run, and by what definition?
#
# REPRODUCE.md's front page tells a stranger the number. It said 276 from
# 2026-08-?? until 2026-08-18, when a recount made it 322 — and the same recount
# put the pre-session figure at 304, so it had been wrong before this session
# touched anything. Nothing was checking it, and a number on the front door that
# nobody can re-derive is worth less than no number.
#
# The definition, stated because it is the only reason two people would ever
# disagree about the total:
#
#   * every `tools/test-*.sh` guard suite, counted by its own "N passed" line;
#   * plus the fwrecon pytest suite.
#
# It does NOT count assertions inside `check-*.py` (they report findings, not
# passes), nor the register/ledger consistency checks, nor the container build.
# Those are checks too; they are just not countable the same way, and mixing two
# counting rules is how a number drifts without anyone editing it.
#
#   bash tools/count-checks.sh          # prints the table and the total
#   bash tools/count-checks.sh --total  # prints only the number
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

quiet=0
[ "${1:-}" = "--total" ] && quiet=1

PY="${PYTHON:-python3}"
VENV_PY="${FWRE_WORK:-$HOME/fwre-work}/venv/bin/python"
[ -x "$VENV_PY" ] && PY="$VENV_PY"

total=0
for f in tools/test-*.sh; do
  n="$(bash "$f" 2>/dev/null | grep -oE '[0-9]+ passed' | tail -1 | grep -oE '^[0-9]+')"
  n="${n:-0}"
  [ "$quiet" -eq 1 ] || printf '  %-32s %4s\n' "$(basename "$f")" "$n"
  total=$((total + n))
done

pt="$(cd tools/fwrecon && "$PY" -m pytest 2>/dev/null \
      | grep -oE '[0-9]+ passed' | tail -1 | grep -oE '^[0-9]+')"
pt="${pt:-0}"
[ "$quiet" -eq 1 ] || printf '  %-32s %4s\n' 'fwrecon pytest' "$pt"
total=$((total + pt))

if [ "$quiet" -eq 1 ]; then
  echo "$total"
else
  echo "  --------------------------------------"
  printf '  %-32s %4s\n' 'total' "$total"
  echo
  echo "  REPRODUCE.md must quote this number. It is not checked in CI on"
  echo "  purpose: a suite that grows should not turn the build red."
fi

# A suite that reports zero is a claim too, and it is usually a broken suite
# rather than an empty one.
[ "$total" -gt 0 ]
