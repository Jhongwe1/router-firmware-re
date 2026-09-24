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
silent=""
for f in tools/test-*.sh; do
  n="$(bash "$f" 2>/dev/null | grep -oE '[0-9]+ passed' | tail -1 | grep -oE '^[0-9]+')"
  # A suite that printed no count did not run. `${n:-0}` used to turn that into
  # "zero checks" and add it to the total, so the number degraded silently in
  # any environment missing a dependency - 468 on a GitHub runner against 626
  # here, with nothing to tell the two apart. It is recorded as unmeasured now,
  # because a tool reporting 0 is making a claim.
  if [ -z "$n" ]; then
    silent="$silent $(basename "$f")"
    [ "$quiet" -eq 1 ] || printf '  %-32s %4s\n' "$(basename "$f")" "--"
    continue
  fi
  [ "$quiet" -eq 1 ] || printf '  %-32s %4s\n' "$(basename "$f")" "$n"
  total=$((total + n))
done

pt="$(cd tools/fwrecon && "$PY" -m pytest 2>/dev/null \
      | grep -oE '[0-9]+ passed' | tail -1 | grep -oE '^[0-9]+')"
if [ -z "$pt" ]; then
  silent="$silent fwrecon-pytest"
  [ "$quiet" -eq 1 ] || printf '  %-32s %4s\n' 'fwrecon pytest' "--"
  pt=0
else
  [ "$quiet" -eq 1 ] || printf '  %-32s %4s\n' 'fwrecon pytest' "$pt"
fi
total=$((total + pt))

if [ -n "$silent" ]; then
  # The marker check-numbers.py reads. It must be unambiguous and it must be on
  # its own line, because the alternative is a checker inferring completeness.
  echo "INCOMPLETE:$silent"
fi

if [ "$quiet" -eq 1 ]; then
  echo "$total"
else
  echo "  --------------------------------------"
  printf '  %-32s %4s\n' 'total' "$total"
  echo
  echo "  REPRODUCE.md quotes this number, and since 2026-09-25 CI checks that"
  echo "  it does: tools/check-numbers.py compares the prose against this"
  echo "  recount. The old note here said the check was omitted on purpose,"
  echo "  because a suite that grows should not redden the build - true of"
  echo "  asserting a CONSTANT, and not of asserting an AGREEMENT, which goes"
  echo "  red only when the prose is stale. Where this cannot run every suite"
  echo "  the line above says INCOMPLETE and the comparison is skipped, because"
  echo "  a total with an unrunnable suite counted as zero is a floor, not a"
  echo "  count - it read 468 on a GitHub runner against 626 here."
fi

# A suite that reports zero is a claim too, and it is usually a broken suite
# rather than an empty one.
[ "$total" -gt 0 ]
