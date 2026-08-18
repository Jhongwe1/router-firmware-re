#!/usr/bin/env bash
# P2-11: the IP-keyed third arm of the gate, and the 601 seconds it lives for.
#
# What this measures, and why two probes are not enough
# -----------------------------------------------------
# `process_header_end` carries a third arm keyed on the client's address:
# form_formLogin writes the source address into `authipaddr` on a successful
# login, and a later request from that same address is let through with no
# credentials at all. The arm expires on `nowuptime - beforeuptime >= 601`, and
# `beforeuptime` has no write anywhere in the binary, so the comparison is
# against system uptime and the window closes 601 seconds after the kernel
# starts.
#
# The register asks for three states: inside the window the logged-in address
# gets 200 without credentials, a second address gets 302 at the same instant,
# and after the window the first address gets 302 again. Two probes would
# satisfy that and still not say when it flipped -- and "it flipped at 601"
# is the whole claim. So this polls on a fixed interval across the boundary and
# reports the transition, which is a prediction that can miss by a second.
#
# The second address is the control that separates "the window closed" from
# "the server stopped answering". Both are sampled at every tick.
#
# This cannot be run under emulation: qemu-user's sysinfo() reports the HOST's
# uptime, which on any desktop that has been on for a day is already past 601,
# so the arm always reads as dead there. That is why the register marks it
# silicon-only.
#
# Usage:
#   bash tools/session-window.sh --host 10.1.1.1 --page /password.htm \
#        --user admin --password admin --src-a 10.1.1.100 --src-b 10.1.1.101 \
#        --kernel-t0 1755500000.123 --until 800 --interval 10 -o out.json
#
#   Optional, for a build whose login handler is named differently:
#        --login-path /boafrm/formLogin --user-field username --pass-field userpass
set -uo pipefail

HOST=10.1.1.1
PAGE=/password.htm
USERNAME=""
PASSWORD=""
SRC_A=""
SRC_B=""
KERNEL_T0=""
UNTIL=800
INTERVAL=10
OUT=""
LOGIN_PATH=/boafrm/formLogin
USER_FIELD=username
PASS_FIELD=userpass

usage() {
    awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 && !/^#/ {exit}' "$0"
    exit "${1:-0}"
}

while [ $# -gt 0 ]; do
    case "$1" in
        --host)      HOST="$2"; shift 2 ;;
        --page)      PAGE="$2"; shift 2 ;;
        --user)      USERNAME="$2"; shift 2 ;;
        --password)  PASSWORD="$2"; shift 2 ;;
        --src-a)     SRC_A="$2"; shift 2 ;;
        --src-b)     SRC_B="$2"; shift 2 ;;
        --kernel-t0) KERNEL_T0="$2"; shift 2 ;;
        --until)     UNTIL="$2"; shift 2 ;;
        --interval)  INTERVAL="$2"; shift 2 ;;
        --login-path)  LOGIN_PATH="$2"; shift 2 ;;
        --user-field)  USER_FIELD="$2"; shift 2 ;;
        --pass-field)  PASS_FIELD="$2"; shift 2 ;;
        -o|--output) OUT="$2"; shift 2 ;;
        -h|--help)   usage 0 ;;
        *) echo "unknown argument: $1" >&2; usage 1 ;;
    esac
done

for req in SRC_A SRC_B KERNEL_T0 OUT USERNAME PASSWORD; do
    if [ -z "${!req}" ]; then
        echo "missing --${req,,} (all of --src-a --src-b --kernel-t0 --user --password -o are required)" >&2
        exit 2
    fi
done

probe() {  # $1 = source address, $2 = "auth" or "noauth"
    if [ "$2" = auth ]; then
        curl -s -o /dev/null -w '%{http_code}' -m 4 --interface "$1" \
             -u "$USERNAME:$PASSWORD" "http://$HOST$PAGE"
    else
        curl -s -o /dev/null -w '%{http_code}' -m 4 --interface "$1" \
             "http://$HOST$PAGE"
    fi
}

# The arm is written by the login FORM HANDLER, not by any authenticated
# request. A Basic-auth GET authenticates through process_header_end and never
# reaches form_formLogin, so it never touches authipaddr -- the first run of
# this script did exactly that, measured 302 straight after a successful login,
# and would have been recorded as "the arm is dead on this unit" if the
# prediction had not named the handler.
form_login() {  # $1 = source address
    curl -s -o /dev/null -w '%{http_code}' -m 8 --interface "$1"          -d "$USER_FIELD=$USERNAME" -d "$PASS_FIELD=$PASSWORD"          -d "submit-url=/index.htm" "http://$HOST$LOGIN_PATH"
}

now_uptime() { awk -v t0="$KERNEL_T0" 'BEGIN{ "date +%s.%N" | getline n; printf "%.1f", n - t0 }'; }

echo "  ==>   step 1: a control BEFORE any login -- both addresses, no credentials"
printf '        uptime %-8s A(%s) %s   B(%s) %s\n' \
    "$(now_uptime)" "$SRC_A" "$(probe "$SRC_A" noauth)" "$SRC_B" "$(probe "$SRC_B" noauth)"

echo "  ==>   step 2: one successful login from A only, through $LOGIN_PATH"
LOGIN_CODE="$(form_login "$SRC_A")"
LOGIN_AT="$(now_uptime)"
echo "        uptime ${LOGIN_AT}  A posts to the login handler -> $LOGIN_CODE"
if [ "$LOGIN_CODE" != 200 ]; then
    echo "  FAIL  the login handler did not return 200. Stop: the credentials are wrong," >&2
    echo "        or --login-path is not this build's login handler. Nothing below means anything." >&2
    exit 3
fi

echo "  ==>   steps 3-5: poll both addresses without credentials across the boundary"
printf '        %-9s %-6s %-6s %s\n' uptime "A" "B" note
: > "${OUT}.tsv"
FLIP=""
while :; do
    U="$(now_uptime)"
    CA="$(probe "$SRC_A" noauth)"
    CB="$(probe "$SRC_B" noauth)"
    NOTE=""
    if [ -z "$FLIP" ] && [ "$CA" != 200 ]; then FLIP="$U"; NOTE="<- A stopped being let through"; fi
    printf '        %-9s %-6s %-6s %s\n' "$U" "$CA" "$CB" "$NOTE"
    printf '%s\t%s\t%s\n' "$U" "$CA" "$CB" >> "${OUT}.tsv"
    awk -v u="$U" -v lim="$UNTIL" 'BEGIN{exit !(u>=lim)}' && break
    sleep "$INTERVAL"
done

{
    printf '{"producer":"session-window.sh","host":"%s","page":"%s",' "$HOST" "$PAGE"
    printf '"src_a":"%s","src_b":"%s","kernel_t0":"%s","interval_s":%s,' "$SRC_A" "$SRC_B" "$KERNEL_T0" "$INTERVAL"
    printf '"login_at_uptime":"%s","first_uptime_A_not_200":"%s","samples":[' "$LOGIN_AT" "${FLIP:-none}"
    awk -F'\t' 'NR>1{printf ","} {printf "{\"uptime\":%s,\"a\":%s,\"b\":%s}", $1, $2, $3}' "${OUT}.tsv"
    printf ']}\n'
} > "$OUT"
echo "  ok    transcript -> $OUT"
echo "  ==>   A stopped returning 200 at uptime ${FLIP:-'(never -- it never returned 200, or never stopped)'}"
echo "        the register predicts the flip at 601 s. B must be 302 at every single tick."
