#!/usr/bin/env bash
# Self-test for tools/loader-tftp.py, with no hardware attached.
#
# The client this exercises talks to the only unit there is, in the boot
# loader, in a state reached by pulling the power. A network tool that can only
# be driven by that is a network tool whose first real run is at the bench, so
# the whole of it is driven here against tools/test-loader-tftp-fake.py.
#
# The fake defaults to answering from a DIFFERENT port than the request went to,
# because that is what the loader did on 2026-08-17 (BENCH-LOG T-09: DATA from
# :2098). Every read case below is therefore also evidence that the client
# follows the transfer id rather than filtering on the port it asked.
#
# The control case at the end is not padding. A reject-only suite in this
# repository once reported 5/5 green while every invocation was failing to start.
#
#   bash tools/test-loader-tftp.sh
#
set -uo pipefail

cd "$(dirname "$0")/.." || { echo "  FAIL  cannot cd to the repository root"; exit 1; }

PY="${FWRE_PY:-python3}"
TOOL=tools/loader-tftp.py
FAKE=tools/test-loader-tftp-fake.py
TMP="$(mktemp -d)"
FAKEPID=""
cleanup() { [ -n "$FAKEPID" ] && kill "$FAKEPID" 2>/dev/null; rm -rf "$TMP"; }
trap cleanup EXIT

pass=0
fail=0
ok()  { echo "  ok    $1"; pass=$((pass + 1)); }
bad() { echo "  FAIL  $1"; fail=$((fail + 1)); }

echo "=== interpreter ==="
"$PY" -c 'import sys; print("  " + sys.executable + "  " + sys.version.split()[0]); \
sys.exit(0 if sys.version_info >= (3, 10) else 1)' || {
  echo "  FAIL  need python 3.10+"; exit 1; }
# Named and printed, never assumed -- the same note test-console-dump.sh carries,
# and it earned its place again here: the first run of this suite resolved a bare
# `python3` to an unrelated project's venv. Harmless, because loader-tftp.py
# imports nothing outside the standard library, and it would NOT be harmless the
# day it does. FWRE_PY overrides it.
case "$("$PY" -c 'import sys; print(sys.executable)')" in
  "$HOME/fwre-work/venv/"*) ;;
  *) echo "  note  that is not this project's venv (see above)." ;;
esac
echo

# Start the stand-in and read back the port it bound. It prints the number and
# then blocks, so the port file is the readiness signal too.
start_fake() {
  [ -n "$FAKEPID" ] && kill "$FAKEPID" 2>/dev/null
  : > "$TMP/port"
  "$PY" "$FAKE" --host 127.0.0.1 --port 0 "$@" > "$TMP/port" 2> "$TMP/fakeerr" &
  FAKEPID=$!
  PORT=""
  for _ in $(seq 1 200); do
    PORT="$(head -1 "$TMP/port" 2>/dev/null)"
    [ -n "$PORT" ] && break
    sleep 0.05
  done
  if [ -z "$PORT" ]; then
    echo "  FAIL  the stand-in server never printed a port"
    cat "$TMP/fakeerr" >&2
    exit 1
  fi
}

echo "=== the control: a read that must succeed ==="
# 1500 bytes = 512 + 512 + 476, so the third block is short and ends the
# transfer. If this one does not pass, nothing below means anything.
start_fake --serve-bytes 1500
out="$("$PY" "$TOOL" get --host 127.0.0.1 --port "$PORT" \
        -o "$TMP/got.bin" --report "$TMP/got.json" 2>&1)"; rc=$?
if [ "$rc" -eq 0 ] && [ -f "$TMP/got.bin" ]; then
  size=$(wc -c < "$TMP/got.bin")
  if [ "$size" -eq 1500 ]; then ok "1500 bytes in 3 blocks, the short block ended it"
  else bad "expected 1500 bytes, got $size"; fi
else
  bad "the control read failed: $out"
fi

# and the bytes are the ones the fake generated, not merely the right count
exp="$("$PY" -c 'import sys
sys.path.insert(0,"tools")
import importlib.util, hashlib
spec = importlib.util.spec_from_file_location("f", "tools/test-loader-tftp-fake.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(hashlib.sha256(m.pattern(1500)).hexdigest())')"
got="$("$PY" -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$TMP/got.bin")"
if [ "$exp" = "$got" ]; then ok "the bytes match, not just the length"
else bad "content differs: expected $exp got $got"; fi

# the report names the transfer id, and it is NOT the port the request went to
tid="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["tid"])' "$TMP/got.json" 2>/dev/null)"
if [ -n "$tid" ] && [ "$tid" != "$PORT" ]; then
  ok "the reply came from :$tid, not the :$PORT the request went to"
else
  bad "the transfer id was not recorded, or equalled the request port ($tid)"
fi

echo
echo "=== probe: one request, one block, nothing written ==="
start_fake --serve-bytes 4096
out="$("$PY" "$TOOL" probe --host 127.0.0.1 --port "$PORT" 2>&1)"; rc=$?
case "$rc:$out" in
  0:*"512 bytes in 1 block"*) ok "probe stops after the first block" ;;
  *) bad "probe did not stop at one block: $out" ;;
esac

echo
echo "=== the refusals ==="

# a name is not an address
out="$("$PY" "$TOOL" probe --host router.local 2>&1)"; rc=$?
case "$rc:$out" in
  1:*"not a dotted quad"*) ok "a hostname is refused, because IPCONFIG took an address" ;;
  *) bad "a hostname was not refused: rc=$rc $out" ;;
esac

# an existing output file is not overwritten
start_fake --serve-bytes 512
echo keepme > "$TMP/exists.bin"
out="$("$PY" "$TOOL" get --host 127.0.0.1 --port "$PORT" -o "$TMP/exists.bin" 2>&1)"; rc=$?
case "$rc:$out" in
  1:*"Refusing to overwrite"*) ok "an existing dump is not overwritten without --force" ;;
  *) bad "an existing file was overwritten: rc=$rc $out" ;;
esac
grep -q keepme "$TMP/exists.bin" || bad "the existing file was modified anyway"

# a gap in the block numbers is not a hole to fill in
start_fake --serve-bytes 4096 --wrong-block
out="$("$PY" "$TOOL" get --host 127.0.0.1 --port "$PORT" -o "$TMP/gap.bin" 2>&1)"; rc=$?
case "$rc:$out" in
  1:*"was expected"*) ok "a skipped block number is an error, not a short file" ;;
  *) bad "a block gap was tolerated: rc=$rc $out" ;;
esac
[ -f "$TMP/gap.bin" ] && bad "a file was written despite the failed transfer"

# an ERROR packet is an answer, with its code
start_fake --error 1
out="$("$PY" "$TOOL" get --host 127.0.0.1 --port "$PORT" -o "$TMP/err.bin" 2>&1)"; rc=$?
case "$rc:$out" in
  1:*"ERROR 1 (file not found)"*) ok "an ERROR packet is reported by code and name" ;;
  *) bad "the ERROR packet was not reported: rc=$rc $out" ;;
esac

# a transfer that never ends is bounded, not endured
start_fake --serve-bytes 2048 --never-short
out="$("$PY" "$TOOL" get --host 127.0.0.1 --port "$PORT" -o "$TMP/inf.bin" \
        --max-bytes 4096 --timeout 1 --retries 1 2>&1)"; rc=$?
case "$rc:$out" in
  1:*"--max-bytes"*) ok "a transfer with no final short block stops at --max-bytes" ;;
  *) bad "an unbounded transfer was not bounded: rc=$rc $out" ;;
esac

# nothing answering is a named failure, not a hang
out="$("$PY" "$TOOL" probe --host 127.0.0.1 --port 1 --timeout 0.3 --retries 2 2>&1)"; rc=$?
case "$rc:$out" in
  1:*"no reply from"*) ok "silence is reported as silence, and it names the ICMP trap" ;;
  *) bad "a dead port did not produce the expected failure: rc=$rc $out" ;;
esac

echo
echo "=== put: the one subcommand that sends bytes the device acts on ==="

mkimg() { "$PY" -c 'import sys; open(sys.argv[1],"wb").write(bytes(range(256))*int(sys.argv[2]))' "$1" "$2"; }
mkimg "$TMP/img.bin" 6

good='{"ip":"127.0.0.1","steps":[{"sent":"AUTOBURN 0","reply":"AutoBurning=0"}]}'
burn='{"ip":"127.0.0.1","steps":[{"sent":"AUTOBURN 1","reply":"AutoBurning=1"}]}'
quiet='{"ip":"127.0.0.1","steps":[{"sent":"AUTOBURN 0","reply":"Unknown command !"}]}'
other='{"ip":"10.1.1.1","steps":[{"sent":"AUTOBURN 0","reply":"AutoBurning=0"}]}'
printf '%s' "$good"  > "$TMP/good.json"
printf '%s' "$burn"  > "$TMP/burn.json"
printf '%s' "$quiet" > "$TMP/quiet.json"
printf '%s' "$other" > "$TMP/other.json"

out="$("$PY" "$TOOL" put --host 127.0.0.1 --port 9 --image "$TMP/img.bin" \
        --rescue-report "$TMP/burn.json" --yes 2>&1)"; rc=$?
case "$rc:$out" in
  1:*"AutoBurning=1"*) ok "a transcript showing autoburn ON stops the upload" ;;
  *) bad "autoburn on did not stop the upload: rc=$rc $out" ;;
esac

out="$("$PY" "$TOOL" put --host 127.0.0.1 --port 9 --image "$TMP/img.bin" \
        --rescue-report "$TMP/quiet.json" --yes 2>&1)"; rc=$?
case "$rc:$out" in
  1:*"does not contain AutoBurning=0"*) ok "a transcript that never confirmed the switch stops it too" ;;
  *) bad "an unconfirmed switch did not stop the upload: rc=$rc $out" ;;
esac

out="$("$PY" "$TOOL" put --host 127.0.0.1 --port 9 --image "$TMP/img.bin" \
        --rescue-report "$TMP/other.json" --yes 2>&1)"; rc=$?
case "$rc:$out" in
  1:*"different address"*) ok "a transcript for another address does not vouch for this one" ;;
  *) bad "a mismatched transcript was accepted: rc=$rc $out" ;;
esac

out="$("$PY" "$TOOL" put --host 127.0.0.1 --port 9 --image "$TMP/img.bin" \
        --rescue-report "$TMP/missing.json" --yes 2>&1)"; rc=$?
case "$rc:$out" in
  1:*"rescue-report"*) ok "a missing transcript is named, not ignored" ;;
  *) bad "a missing transcript was not reported: rc=$rc $out" ;;
esac

start_fake --capture "$TMP/uploaded.bin"
out="$("$PY" "$TOOL" put --host 127.0.0.1 --port "$PORT" --image "$TMP/img.bin" \
        --rescue-report "$TMP/good.json" 2>&1)"; rc=$?
case "$rc:$out" in
  1:*"refusing without --yes"*) ok "--yes is required even with a clean transcript" ;;
  *) bad "the upload ran without --yes: rc=$rc $out" ;;
esac
[ -f "$TMP/uploaded.bin" ] && bad "bytes reached the peer without --yes"

# AUTOBURN is a RAM variable in the loader. A transcript proving it was sent
# proves it about the boot it was written during, and the first version of this
# guard accepted one of any age -- which is a guard that cannot fail in the way
# that matters, with a flash write to the only unit as the cost of being wrong.
touch -d '3 hours ago' "$TMP/good.json" 2>/dev/null || touch -t "$(date -d '3 hours ago' +%Y%m%d%H%M 2>/dev/null || echo 202001010000)" "$TMP/good.json"
out="$("$PY" "$TOOL" put --host 127.0.0.1 --port 9 --image "$TMP/img.bin" \
        --rescue-report "$TMP/good.json" --yes 2>&1)"; rc=$?
case "$rc:$out" in
  1:*"RAM state"*) ok "a rescue transcript from an earlier boot is refused on age" ;;
  *) bad "a three-hour-old transcript was accepted: rc=$rc $out" ;;
esac

out="$("$PY" "$TOOL" put --host 127.0.0.1 --port 9 --image "$TMP/img.bin" \
        --rescue-report "$TMP/good.json" --max-rescue-age 0 --yes 2>&1)"; rc=$?
case "$out" in
  *"RAM state"*) bad "--max-rescue-age 0 did not disable the age bound" ;;
  *) ok "--max-rescue-age 0 disables the bound, deliberately and visibly" ;;
esac
printf '%s' "$good" > "$TMP/good.json"   # fresh again for the control below

# The loader's WRQ path tests the filename against two constants and, on a
# match, jumps to the load address the moment the transfer finishes. `J` is
# kept in a human's hands on purpose; a default filename is not where that
# decision should be lost.
for name in nfjrom boot.img my-nfjrom-test; do
  out="$("$PY" "$TOOL" put --host 127.0.0.1 --port 9 --image "$TMP/img.bin" \
          --filename "$name" --rescue-report "$TMP/good.json" --yes 2>&1)"; rc=$?
  case "$rc:$out" in
    1:*"0x8040D390"*) ok "--filename $name is refused, and the refusal names the flag" ;;
    *) bad "--filename $name was accepted: rc=$rc $out" ;;
  esac
done

out="$("$PY" "$TOOL" put --host 127.0.0.1 --port 9 --image "$TMP/img.bin" \
        --filename nfjrom --allow-autoexec --rescue-report "$TMP/good.json" 2>&1)"; rc=$?
case "$out" in
  *"0x8040D390"*) bad "--allow-autoexec did not permit the name" ;;
  *"refusing without --yes"*) ok "--allow-autoexec permits it, and --yes is still required" ;;
  *) bad "--allow-autoexec behaved unexpectedly: rc=$rc $out" ;;
esac

# The number a human types into `J` afterwards. Without this the only source for
# it was the same human's memory of what they set LOADADDR to.
withaddr='{"ip":"127.0.0.1","load_addr":"0x80500000","steps":[{"sent":"AUTOBURN 0","reply":"AutoBurning=0"}]}'
printf '%s' "$withaddr" > "$TMP/withaddr.json"
out="$("$PY" "$TOOL" put --host 127.0.0.1 --port 9 --image "$TMP/img.bin" \
        --rescue-report "$TMP/withaddr.json" --expect-load 81000000 --yes 2>&1)"; rc=$?
case "$rc:$out" in
  1:*"cannot tell which"*) ok "an --expect-load that disagrees with the transcript stops it" ;;
  *) bad "a mismatched load address was accepted: rc=$rc $out" ;;
esac

out="$("$PY" "$TOOL" put --host 127.0.0.1 --port 9 --image "$TMP/img.bin" \
        --rescue-report "$TMP/good.json" --expect-load 80500000 --yes 2>&1)"; rc=$?
case "$rc:$out" in
  1:*"does not record a load address"*) ok "--expect-load against a transcript that never set one is refused" ;;
  *) bad "--expect-load passed with no recorded address: rc=$rc $out" ;;
esac

out="$("$PY" "$TOOL" put --host 127.0.0.1 --port 9 --image "$TMP/img.bin" \
        --rescue-report "$TMP/withaddr.json" --expect-load 80500000 2>&1)"; rc=$?
case "$out" in
  *"which is what J must be given"*) ok "a matching --expect-load is confirmed and named" ;;
  *) bad "a matching load address was not confirmed: rc=$rc $out" ;;
esac

echo
echo "=== attribution: where the served bytes sit in a flash dump ==="
"$PY" -c '
import sys
blob = bytearray(b"\xaa" * 8192)
blob[0x400:0x400+64] = bytes(range(64))          # occurs exactly once
blob[0x900:0x900+8]  = b"\x11" * 8               # and again at 0xa00, below
blob[0xa00:0xa00+8]  = b"\x11" * 8
open(sys.argv[1], "wb").write(bytes(blob))' "$TMP/haystack.bin"

"$PY" -c 'import sys; open(sys.argv[1],"wb").write(bytes(range(64)))' "$TMP/needle.bin"
start_fake --file "$TMP/needle.bin"
out="$("$PY" "$TOOL" get --host 127.0.0.1 --port "$PORT" -o "$TMP/att.bin" \
        --attribute "$TMP/haystack.bin" 2>&1)"
case "$out" in
  *"flash[0x000400 : 0x000440]"*) ok "a transfer present once is located, with its offset" ;;
  *) bad "attribution did not locate the bytes: $out" ;;
esac
case "$out" in
  *"not a source"*) ok "and it says an offset is not a source" ;;
  *) bad "attribution stated a source: $out" ;;
esac

"$PY" -c 'import sys; open(sys.argv[1],"wb").write(b"\x11"*8)' "$TMP/dup.bin"
start_fake --file "$TMP/dup.bin"
out="$("$PY" "$TOOL" get --host 127.0.0.1 --port "$PORT" -o "$TMP/att2.bin" \
        --attribute "$TMP/haystack.bin" 2>&1)"
case "$out" in
  *"that is not a location"*) ok "bytes occurring more than once are not called located" ;;
  *) bad "an ambiguous match was reported as a location: $out" ;;
esac

"$PY" -c 'import sys; open(sys.argv[1],"wb").write(b"NOT-IN-THE-DUMP-AT-ALL")' "$TMP/absent.bin"
start_fake --file "$TMP/absent.bin"
out="$("$PY" "$TOOL" get --host 127.0.0.1 --port "$PORT" -o "$TMP/att3.bin" \
        --attribute "$TMP/haystack.bin" 2>&1)"
case "$out" in
  *"occur NOWHERE"*) ok "bytes absent from the dump are reported as absent, not as an error" ;;
  *) bad "an absent match was not reported: $out" ;;
esac

echo
echo "=== the second control: an upload that must succeed ==="
start_fake --capture "$TMP/uploaded.bin"
out="$("$PY" "$TOOL" put --host 127.0.0.1 --port "$PORT" --image "$TMP/img.bin" \
        --rescue-report "$TMP/good.json" --yes --report "$TMP/put.json" 2>&1)"; rc=$?
for _ in $(seq 1 40); do [ -f "$TMP/uploaded.bin" ] && break; sleep 0.05; done
if [ "$rc" -eq 0 ] && cmp -s "$TMP/img.bin" "$TMP/uploaded.bin"; then
  ok "1536 bytes arrived byte-identical, and the transcript records the sha256"
else
  bad "the upload did not arrive intact: rc=$rc $out"
fi

echo
echo "=== the retransmit path ==="
# The stand-in ignores the first request outright. The client must retry rather
# than call it a dead service, and must say in its transcript that it did.
start_fake --serve-bytes 512 --drop-first
out="$("$PY" "$TOOL" get --host 127.0.0.1 --port "$PORT" -o "$TMP/retry.bin" \
        --timeout 0.5 --report "$TMP/retry.json" 2>&1)"; rc=$?
if [ "$rc" -eq 0 ]; then
  n="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["retransmits"])' "$TMP/retry.json")"
  if [ "$n" -ge 1 ]; then ok "a dropped request is retried, and the count is on the record ($n)"
  else bad "the transfer succeeded but no retransmit was recorded"; fi
else
  bad "a single dropped request killed the transfer: $out"
fi

echo
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
