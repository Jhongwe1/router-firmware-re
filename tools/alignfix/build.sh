#!/usr/bin/env bash
# Build alignfix.so for the SoC this unit runs, and prove it is for that SoC.
#
# The endianness check is not ceremony. `mips-linux-gnu-gcc` and
# `mipsel-linux-gnu-gcc` both exist on a Debian-family box, both compile this
# file without a word of complaint, and exactly one of them produces something
# an RTL8196E will execute. Register case P5-4's refutation condition says so in
# as many words: "if the binary will not run on the device, check endianness and
# ABI before suspecting the payload". So the build checks first and the check is
# what fails, not the target.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
out="${1:-$here/alignfix.so}"
cc="${CC:-mips-linux-gnu-gcc}"
# Extra -D flags. The guard suite uses this to build a shim with deliberately
# wrong ucontext offsets, which is the only way to reach the handler's refusal
# paths on purpose.
extra="${ALIGNFIX_CFLAGS:-}"
# Skip compiling and run the checks below against a file that already exists.
# Without this hook the checks can only ever be run on output the compiler just
# produced correctly, so nothing shows they discriminate.
check_only="${ALIGNFIX_CHECK_ONLY:-}"

if [ -n "$check_only" ]; then
  out="$check_only"
  echo "checking $out (no compile: ALIGNFIX_CHECK_ONLY is set)"
fi

[ -n "$check_only" ] || command -v "$cc" >/dev/null || {
  echo "build.sh: $cc not found. Install it with:" >&2
  echo "  sudo apt-get install -y gcc-mips-linux-gnu binutils-mips-linux-gnu" >&2
  echo "or run: bash tools/setup/setup-wsl.sh apt" >&2
  exit 1
}

# -nostdlib: raw syscalls only, so the result does not care that the target
#            links uClibc 0.9.30 and this toolchain targets glibc.
# -msoft-float: the SoC has no FPU and uClibc here is soft-float; a hard-float
#            object makes ld-uClibc refuse the library outright.
# -Wl,-init: DT_INIT as well as .init_array, because uClibc 0.9.30's loader is
#            old enough that relying on only one of them is a coin flip. Running
#            the constructor twice is harmless -- installing the same handler
#            twice is idempotent -- and seeing the banner twice is how you know
#            which paths the loader took.
if [ -z "$check_only" ]; then
  # shellcheck disable=SC2086  # $extra is a deliberate word-split of -D flags
  "$cc" -shared -fPIC -nostdlib -Os \
        -march=mips32 -mabi=32 -EB -msoft-float \
        -Wl,-init,alignfix_init \
        -Wall -Wextra $extra \
        -o "$out" "$here/alignfix.c"
  echo "built $out"
fi

hdr="$(readelf -hW "$out")"
fail=0
check() {  # check <description> <needle>
  if printf '%s' "$hdr" | grep -q "$2"; then
    printf '  ok    %s\n' "$1"
  else
    printf '  FAIL  %s (looked for: %s)\n' "$1" "$2" >&2
    fail=1
  fi
}
check "big-endian"            "big endian"
check "32-bit"                "ELF32"
check "MIPS machine"          "MIPS"
check "shared object"         "DYN (Shared object file)"

# The loader will only run it if one of these exists. Both is the intent.
if readelf -dW "$out" | grep -qE '\(INIT\)|\(INIT_ARRAY\)'; then
  printf '  ok    has an init entry (DT_INIT and/or DT_INIT_ARRAY)\n'
else
  printf '  FAIL  no DT_INIT and no DT_INIT_ARRAY: the constructor will never run\n' >&2
  fail=1
fi

# Freestanding means freestanding. An accidental libc dependency would resolve
# against uClibc at runtime with a different struct layout and fail silently.
undef="$(readelf --dyn-syms -W "$out" | awk '$7 == "UND" && $8 != "" {print $8}' | sort -u || true)"
if [ -n "$undef" ]; then
  printf '  FAIL  unexpected undefined symbols: %s\n' "$(echo "$undef" | tr '\n' ' ')" >&2
  fail=1
else
  printf '  ok    no undefined symbols (raw syscalls only)\n'
fi

exit "$fail"
