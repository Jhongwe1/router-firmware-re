#!/usr/bin/env bash
# Prove the alignment shim and its build checks can fail.
#
# alignfix.so changes what the emulation environment IS: with it on, code paths
# that could not run before do run, and results taken with it are not comparable
# to results taken without it. A component with that much leverage needs a suite
# that shows its guards are load-bearing rather than decorative -- the same
# reason test-qemu-env.sh and test-failopen-probe.sh exist.
#
# Split, like test-failopen-probe.sh: everything here needs a cross-compiler and
# nothing here needs root, the flash dump, or a built profile. The two in-run
# controls -- that a correct shim fixes the known unaligned store, and that a
# wrong one refuses instead of corrupting registers -- need the environment and
# are enforced there.
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$REPO/tools/alignfix/build.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
ok()   { printf '  ok    %s\n' "$1"; pass=$((pass + 1)); }
bad()  { printf '  FAIL  %s\n' "$1" >&2; fail=$((fail + 1)); }
want_ok()   { if "$@" >"$TMP/log" 2>&1; then return 0; else return 1; fi; }

if ! command -v mips-linux-gnu-gcc >/dev/null; then
  echo "test-alignfix: mips-linux-gnu-gcc is not installed."
  echo "  sudo apt-get install -y gcc-mips-linux-gnu binutils-mips-linux-gnu"
  echo "  (or: bash tools/setup/setup-wsl.sh apt)"
  exit 1
fi

echo "=== alignfix guard suite ==="

# 1. The real build succeeds and every header check passes.
if want_ok bash "$BUILD" "$TMP/alignfix.so"; then
  ok "the shipped source builds for MIPS big-endian"
else
  bad "the shipped source does not build"; cat "$TMP/log" >&2
fi

# 2. The output really is the architecture claimed, checked without build.sh.
if readelf -hW "$TMP/alignfix.so" 2>/dev/null | grep -q "big endian"; then
  ok "readelf agrees the object is big-endian"
else
  bad "readelf does not call the object big-endian"
fi

# 3. ...and the checks discriminate. Point them at a host object -- x86-64,
#    little-endian -- and they must fail. A check that passes on anything is
#    not a check, which is how BoaGate first reported 0 findings on a build with
#    34 known defects.
host_obj=""
for c in /bin/true /usr/bin/env /bin/ls; do
  [ -f "$c" ] && { host_obj="$c"; break; }
done
if [ -z "$host_obj" ]; then
  bad "no host binary found to test the checks against"
elif ALIGNFIX_CHECK_ONLY="$host_obj" bash "$BUILD" >"$TMP/log2" 2>&1; then
  bad "the build checks PASSED on a host x86-64 object -- they do not discriminate"
else
  if grep -q "FAIL  big-endian" "$TMP/log2"; then
    ok "the build checks reject a host x86-64 object, naming endianness"
  else
    ok "the build checks reject a host x86-64 object"
  fi
fi

# 4. A shim built with wrong ucontext offsets still builds. That matters because
#    the runtime refusal path is only reachable if such a build is possible; if
#    the override did not work, the in-run control could never be exercised.
if want_ok env ALIGNFIX_CFLAGS="-DALIGNFIX_UC_PC_LO=4 -DALIGNFIX_UC_REGS_LO=8" \
        bash "$BUILD" "$TMP/wrong.so"; then
  ok "a deliberately mis-offset shim builds, so the refusal path is reachable"
else
  bad "the offset override does not compile; the refusal path cannot be tested"
  cat "$TMP/log" >&2
fi

# 5. And it is actually a different object. If the -D had been ignored the two
#    files would be byte-identical and test 4 would have proved nothing.
if [ -f "$TMP/wrong.so" ] && [ -f "$TMP/alignfix.so" ]; then
  if cmp -s "$TMP/alignfix.so" "$TMP/wrong.so"; then
    bad "the mis-offset build is byte-identical to the correct one: -D was ignored"
  else
    ok "the mis-offset build differs from the correct one"
  fi
fi

# 6. Both refusal paths exist in the source. Cheap, and it catches the specific
#    regression of someone 'simplifying' the handler by deleting a check.
src="$REPO/tools/alignfix/alignfix.c"
if grep -q "not a fixable load/store" "$src" && grep -q "is already aligned" "$src"; then
  ok "both refusal paths are present in the source"
else
  bad "a refusal path is missing from alignfix.c"
fi

# 7. The handler must not silently continue after refusing: it reinstalls the
#    default disposition so the process dies exactly as it did before.
if grep -q 'install((void \*)0)' "$src"; then
  ok "refusing restores SIG_DFL, so a broken shim cannot look like a working one"
else
  bad "refusal does not restore the default handler"
fi

# 8. Off by default. If serve ever starts preloading it unasked, every result
#    recorded before 2026-08-18 becomes incomparable without anyone noticing.
if grep -q 'alignfix=0' "$REPO/tools/qemu-env.sh"; then
  ok "qemu-env.sh serve leaves alignfix off unless asked"
else
  bad "qemu-env.sh no longer defaults alignfix to off"
fi

echo
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ]
