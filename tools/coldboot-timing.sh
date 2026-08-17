#!/usr/bin/env bash
# P1-12: power-on to a web server that answers, measured against the console's
# own first line rather than against when the operator remembered to look.
#
# One power cycle feeds three things, which is why it is a script and not three
# commands typed in a hurry:
#
#   P1-12   the interval from the boot loader's first console output to the
#           first HTTP 200
#   P9-1    the kernel's own `Kernel command line:` line, which is the dynamic
#           half of "can the boot loader pass one" -- the static half is
#           tools/loader-unpack.py reporting zero hits across thirteen needles
#   a log   the whole boot, timestamped, for anything asked later
#
# The two clocks are the same clock: both halves stamp with `date +%s.%N` in
# this shell, so the subtraction is meaningful. Timing the HTTP poll from when
# the script started would measure the operator's reaction time instead, which
# is the mistake this exists to prevent.
#
#   bash tools/coldboot-timing.sh <serial-port> <host> <outdir>
#
set -uo pipefail

PORT="${1:-/dev/ttyUSB0}"
HOST="${2:-10.1.1.1}"
OUT="${3:-$HOME/fwre-work/dumps}"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG="$OUT/coldboot-$STAMP.log"
HTTPLOG="$OUT/coldboot-$STAMP.http"

command -v stty >/dev/null || { echo "no stty"; exit 1; }
stty -F "$PORT" 38400 cs8 -cstopb -parenb -crtscts -ixon -ixoff raw -echo || exit 1

: > "$LOG"; : > "$HTTPLOG"

# Console, one timestamp per line. Not picocom: it has no line timestamps, and
# `ts` from moreutils is not installed everywhere.
( while IFS= read -r line; do
    printf '%s %s\n' "$(date +%s.%N)" "$line"
  done < "$PORT" >> "$LOG" ) &
CONSOLE=$!

# HTTP, polled hard. -m 1 so a hung connect cannot swallow the moment the
# server came up.
( until curl -s -o /dev/null -m 1 "http://$HOST/" 2>/dev/null; do
    sleep 0.2
  done
  printf '%s first-200\n' "$(date +%s.%N)" >> "$HTTPLOG" ) &
POLLER=$!

cleanup() { kill "$CONSOLE" "$POLLER" 2>/dev/null; }
trap cleanup EXIT

echo "  ==>   armed.  console -> $LOG"
echo "  ==>           http    -> $HTTPLOG"
echo
echo "        >>> POWER THE ROUTER ON NOW <<<   (no ESC; let it boot)"
echo
DEADLINE=$((SECONDS + 180))
while [ "$SECONDS" -lt "$DEADLINE" ]; do
  if [ -s "$HTTPLOG" ]; then break; fi
  sleep 0.5
done
sleep 3           # let the console log catch up past the HTTP moment
cleanup

if [ ! -s "$LOG" ]; then
  echo "  FAIL  nothing on the console at all - TX/RX, wrong port, or no power"
  exit 1
fi
T0="$(head -1 "$LOG" | cut -d' ' -f1)"
echo "  ok    first console line at t=0:"
head -1 "$LOG" | cut -d' ' -f2-
if [ ! -s "$HTTPLOG" ]; then
  echo "  FAIL  no HTTP 200 within the window.  That is a result, not a timeout:"
  echo "        P1-12 predicts under 40 s and the refutation names 'clearly over'."
  exit 1
fi
T1="$(cut -d' ' -f1 "$HTTPLOG")"
echo "  ok    first HTTP 200:"
awk -v t0="$T0" -v t1="$T1" 'BEGIN{printf "        %.2f s from the console'\''s first line\n", t1-t0}'

echo
echo "  ==>   P9-1: the kernel's own report of its command line"
if grep -i -m1 'command line' "$LOG"; then :; else
  echo "  FAIL  the kernel printed no 'Kernel command line:' line at all"
fi
echo
echo "  ==>   markers"
grep -nE 'RealTek\(RTL|Linux version|init started|boa: starting|sysconf init|chipName' "$LOG" |
  head -12
echo
echo "  log: $LOG"
