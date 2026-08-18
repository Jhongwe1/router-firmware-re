#!/usr/bin/env bash
#
# setup-wsl.sh — provision the firmware-RE toolchain on Ubuntu 24.04 (WSL2 or bare metal).
#
# Design notes
#   * Idempotent: safe to re-run. Every step checks before it acts.
#   * Staged: run one stage at a time while iterating, or `all` for a cold machine.
#   * Pinned: third-party artefacts are pinned to a release tag, not "latest", so the
#     toolchain that produced a result can be rebuilt months later. See docker/Dockerfile
#     for the same pins in container form.
#
# Usage:
#   ./setup-wsl.sh all
#   ./setup-wsl.sh apt | rust | binwalk | sasquatch | unblob | verify
#
set -euo pipefail

# ---------------------------------------------------------------- pinned versions
SASQUATCH_TAG="sasquatch-v4.5.1-6"          # onekey-sec prebuilt; upstream devttys0 does not build on GCC 13
RUST_TOOLCHAIN="stable"
BINWALK_GIT="https://github.com/ReFirmLabs/binwalk"
BINWALK_TAG="v3.1.0"

CACHE="${HOME}/.cache/fwre-setup"
mkdir -p "$CACHE"

# ---------------------------------------------------------------- output helpers
c_ok()   { printf '\033[32m  ok  \033[0m %s\n' "$*"; }
c_run()  { printf '\033[36m ==>  \033[0m %s\n' "$*"; }
c_warn() { printf '\033[33m warn \033[0m %s\n' "$*"; }
c_err()  { printf '\033[31m FAIL \033[0m %s\n' "$*" >&2; }
have()   { command -v "$1" >/dev/null 2>&1; }

# ---------------------------------------------------------------- stages
stage_apt() {
  c_run "apt: updating package index"
  sudo apt-get update -qq

  # Grouped by why we need them, so the list stays auditable rather than a mystery blob.
  local pkgs=(
    # build toolchain (sasquatch fallback, native helper builds)
    build-essential git curl wget ca-certificates pkg-config
    # archive / container formats found inside firmware images
    p7zip-full unzip cpio unar lzop lz4 zstd xz-utils lziprecover
    # squashfs: mksquashfs/unsquashfs handle standard images; sasquatch handles Realtek's
    squashfs-tools
    # compression dev headers (needed if we ever build sasquatch/binwalk extractors ourselves)
    zlib1g-dev liblzma-dev liblzo2-dev libbz2-dev liblz4-dev libzstd-dev libssl-dev
    # filesystem images occasionally embedded in routers
    e2fsprogs android-sdk-libsparse-utils
    # emulation of MIPS user-space binaries (W05 dynamic analysis; used early to smoke-test ABI)
    qemu-user-static binfmt-support
    # W07 exploitation block: qemu-user exposes a gdbstub with -g, and the debugger
    # attaching to it has to speak MIPS *big*-endian. Plain gdb on amd64 does not,
    # and a mipsel toolchain silently produces objects this SoC will not run --
    # which is exactly what P5-4's refutation condition says to check first.
    gdb-multiarch gcc-mips-linux-gnu binutils-mips-linux-gnu
    # hardware access (W02): SPI flash reads and UART console
    flashrom picocom minicom
    # binary inspection
    binutils file bsdmainutils srecord
    # binwalk v3 renders entropy plots via plotters -> fontconfig/freetype.
    # Without these the cargo build dies in yeslogic-fontconfig-sys's build.rs.
    libfontconfig1-dev libfreetype-dev
    # scripting / reporting
    python3-venv python3-pip pipx jq bc
  )

  c_run "apt: installing ${#pkgs[@]} packages"
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${pkgs[@]}"
  c_ok "apt packages installed"

  # pipx puts shims in ~/.local/bin, which is not on PATH in a default Ubuntu shell.
  pipx ensurepath >/dev/null 2>&1 || true
}

stage_rust() {
  if have cargo; then
    c_ok "rust already present ($(cargo --version))"
    return
  fi
  # Deliberately NOT `curl | sh`: piping straight into a shell discards curl's exit
  # status behind pipefail ambiguity and gives no artefact to inspect when it fails.
  # Download first, then execute, so a transient network error is distinguishable
  # from an installer error.
  local init="$CACHE/rustup-init"
  c_run "rust: fetching rustup-init"
  curl --proto '=https' --tlsv1.2 -fsSL --retry 3 --retry-delay 2 \
    -o "$init" https://static.rust-lang.org/rustup/dist/x86_64-unknown-linux-gnu/rustup-init
  chmod +x "$init"
  c_run "rust: installing toolchain ${RUST_TOOLCHAIN}"
  "$init" -y --default-toolchain "$RUST_TOOLCHAIN" --profile minimal --no-modify-path
  # shellcheck disable=SC1091
  source "$HOME/.cargo/env"
  c_ok "rust installed ($(cargo --version))"
}

stage_binwalk() {
  if have binwalk; then
    c_ok "binwalk already present ($(binwalk --version 2>&1 | head -1))"
    return
  fi
  # shellcheck disable=SC1091
  [ -f "$HOME/.cargo/env" ] && source "$HOME/.cargo/env"
  c_run "binwalk: cargo install from ${BINWALK_GIT} @ ${BINWALK_TAG}"
  cargo install --locked --git "$BINWALK_GIT" --tag "$BINWALK_TAG" binwalk
  c_ok "binwalk installed"
}

stage_sasquatch() {
  if have sasquatch; then
    c_ok "sasquatch already present"
    return
  fi
  # Realtek SDK images use LZMA-compressed SquashFS with a non-standard header. Stock
  # unsquashfs rejects them; sasquatch is a patched unsquashfs that tolerates the variants.
  # We use ONEKEY's prebuilt .deb because devttys0/sasquatch does not compile under GCC 13
  # (misleading-indentation in unsquashfs.c, dangling-pointer in LzmaEnc.c).
  local deb="$CACHE/sasquatch_${SASQUATCH_TAG}_amd64.deb"
  local url="https://github.com/onekey-sec/sasquatch/releases/download/${SASQUATCH_TAG}/sasquatch_1.0_amd64.deb"
  c_run "sasquatch: fetching ${SASQUATCH_TAG}"
  [ -f "$deb" ] || curl -fsSL -o "$deb" "$url"
  sudo dpkg -i "$deb" || sudo apt-get -f install -y
  c_ok "sasquatch installed"
}

stage_unblob() {
  if have unblob; then
    c_ok "unblob already present ($(unblob --version 2>&1 | head -1))"
    return
  fi
  c_run "unblob: pipx install"
  pipx install unblob
  export PATH="$HOME/.local/bin:$PATH"
  c_ok "unblob installed"
}

stage_path() {
  # rustup ran with --no-modify-path and pipx installs into ~/.local/bin, so a
  # shell would not see binwalk or unblob. Write one idempotent snippet rather
  # than letting each installer append its own.
  #
  # ~/.profile AND ~/.bashrc, and the first one is the whole point. Until
  # 2026-08-17 this wrote only ~/.bashrc, and Ubuntu's ~/.bashrc opens with
  #
  #     case $- in *i*) ;; *) return;; esac
  #
  # so it returns immediately in a NON-INTERACTIVE shell -- which is every
  # `wsl -d Ubuntu-24.04 -- bash -lc '...'`, the exact form CLAUDE.md prescribes
  # and the exact form that was documented as working *because* of `-l`. It never
  # did. `command -v binwalk` came back empty from a login shell for ten days
  # while ~/.cargo/bin/binwalk sat there executable, and the failure was read as
  # "binwalk is missing" more than once.
  #
  # `bash -l` reads ~/.profile (there is no ~/.bash_profile here), and ~/.profile
  # is not interactivity-guarded. So the snippet goes there too.
  local marker='# >>> fwre toolchain path >>>'
  local snippet
  snippet="$(cat <<'EOF'

# >>> fwre toolchain path >>>
# Added by tools/setup/setup-wsl.sh — cargo (binwalk v3) and pipx (unblob) shims.
# In ~/.profile as well as ~/.bashrc on purpose: ~/.bashrc returns early for a
# non-interactive shell, and `bash -lc` is non-interactive.
case ":$PATH:" in
  *":$HOME/.cargo/bin:"*) ;;
  *) PATH="$HOME/.cargo/bin:$PATH" ;;
esac
case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) PATH="$HOME/.local/bin:$PATH" ;;
esac
export PATH
# <<< fwre toolchain path <<<
EOF
)"
  local wrote=0
  for rc in "$HOME/.profile" "$HOME/.bashrc"; do
    if grep -qF "$marker" "$rc" 2>/dev/null; then
      c_ok "PATH snippet already in $(basename "$rc")"
      continue
    fi
    c_run "shell: adding toolchain PATH to $(basename "$rc")"
    printf '%s\n' "$snippet" >> "$rc"
    wrote=$((wrote + 1))
  done
  [ "$wrote" -gt 0 ] && c_ok "PATH snippet written (takes effect in a new shell)"
  # And prove it, rather than trusting it: a login shell must now find binwalk.
  if [ -x "$HOME/.cargo/bin/binwalk" ]; then
    if bash -lc 'command -v binwalk' >/dev/null 2>&1; then
      c_ok "a non-interactive login shell now finds binwalk"
    else
      c_warn "binwalk exists but \`bash -lc\` still cannot see it — check $HOME/.profile"
    fi
  fi
}

# ---------------------------------------------------------------- verification
# G0 is not "I typed the install commands" — it is "every tool answers when called".
stage_verify() {
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  local fail=0
  check() {
    local name="$1"; shift
    if have "$name" && "$@" >/dev/null 2>&1; then
      c_ok "$(printf '%-22s' "$name") $(command -v "$name")"
    else
      c_err "$(printf '%-22s' "$name") MISSING or non-functional"
      fail=1
    fi
  }
  echo
  echo "=== G0 gate: toolchain verification ==="
  check binwalk            binwalk --version
  check unblob             unblob --version
  # squashfs-tools (and sasquatch, which is a fork of it) print the version banner
  # for -version and then exit 1. Probing with -version therefore reports a working
  # tool as broken; -help is the flag that actually returns 0.
  check sasquatch          sasquatch -help
  check sasquatch-v4be     sasquatch-v4be -help
  check unsquashfs         unsquashfs -help
  check qemu-mips-static   qemu-mips-static --version
  check qemu-mipsel-static qemu-mipsel-static --version
  check gdb-multiarch      gdb-multiarch --version
  check mips-linux-gnu-gcc mips-linux-gnu-gcc --version
  # The endianness check, not a presence check. `mips-linux-gnu-gcc` and
  # `mipsel-linux-gnu-gcc` both exist, both compile, and only one of them
  # produces something this SoC will execute. Ask the assembler what it emits.
  check mips-linux-gnu-objdump mips-linux-gnu-objdump --version
  check flashrom           flashrom --version
  check picocom            picocom --help
  check 7z                 7z i
  check cpio               cpio --version
  check readelf            readelf --version
  check strings            strings --version
  check jq                 jq --version
  echo
  if [ "$fail" -eq 0 ]; then
    c_ok "G0 GREEN — all tools functional"
  else
    c_err "G0 RED — see MISSING entries above"
    return 1
  fi
}

# ---------------------------------------------------------------- driver
main() {
  local stage="${1:-all}"
  case "$stage" in
    apt)       stage_apt ;;
    rust)      stage_rust ;;
    binwalk)   stage_binwalk ;;
    sasquatch) stage_sasquatch ;;
    unblob)    stage_unblob ;;
    path)      stage_path ;;
    verify)    stage_verify ;;
    all)
      stage_apt
      stage_rust
      stage_binwalk
      stage_sasquatch
      stage_unblob
      stage_path
      stage_verify
      ;;
    *) c_err "unknown stage: $stage"; exit 2 ;;
  esac
}

main "$@"
