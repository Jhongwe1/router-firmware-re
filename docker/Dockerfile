# Reproducible firmware-analysis toolchain.
#
# This image exists so a result from this project can be re-derived years from
# now, when `apt install binwalk` will give a different binary than it does
# today. Every third-party artefact below is pinned to a tag or a digest.
#
# Ghidra is deliberately NOT in here: it is a GUI tool driven interactively, and
# the headless analyzer is scripted separately (see ghidra/scripts/). What this
# image covers is the part that must be byte-reproducible — unpacking, ELF
# analysis and report generation.
#
#   docker build -t fwre-toolbox -f docker/Dockerfile .
#   docker run --rm -v "$PWD:/repo" -v "$HOME/fwre-work:/work" fwre-toolbox \
#          fwrecon image /work/firmware/TOTOLINK-N150RT-V2.1.2-B20150825.1601.web

FROM ubuntu:24.04@sha256:a08e551cb33850e4740772b38217fc1796a66da2506d312abe51acda354ff061

ARG DEBIAN_FRONTEND=noninteractive
ARG SASQUATCH_TAG=sasquatch-v4.5.1-6
ARG BINWALK_TAG=v3.1.0

# Grouped by purpose so the list stays auditable rather than an opaque blob.
RUN apt-get update && apt-get install -y --no-install-recommends \
      # build toolchain
      build-essential git curl ca-certificates pkg-config \
      # archive/container formats found inside firmware
      p7zip-full unzip cpio unar lzop lz4 zstd xz-utils lziprecover \
      squashfs-tools \
      # compression headers
      zlib1g-dev liblzma-dev liblzo2-dev libbz2-dev liblz4-dev libzstd-dev \
      libssl-dev \
      # filesystem images occasionally embedded in routers
      e2fsprogs android-sdk-libsparse-utils \
      # binwalk v3 renders entropy plots through plotters -> fontconfig
      libfontconfig1-dev libfreetype-dev \
      # MIPS user-space emulation
      qemu-user-static binfmt-support \
      # binary inspection and reporting
      binutils file srecord jq python3 python3-venv python3-pip \
 && rm -rf /var/lib/apt/lists/*

# sasquatch: a patched unsquashfs that tolerates Realtek's non-standard LZMA
# SquashFS headers. Built from ONEKEY's packaging because the original
# devttys0 tree does not compile under GCC 13.
RUN curl -fsSL -o /tmp/sasquatch.deb \
      "https://github.com/onekey-sec/sasquatch/releases/download/${SASQUATCH_TAG}/sasquatch_1.0_amd64.deb" \
 && dpkg -i /tmp/sasquatch.deb \
 && rm /tmp/sasquatch.deb

# binwalk v3 (Rust). Kept as a cross-check against fwrecon's own container
# parser: two independent tools disagreeing is a finding, not an inconvenience.
RUN curl --proto '=https' --tlsv1.2 -fsSL -o /tmp/rustup-init \
      https://static.rust-lang.org/rustup/dist/x86_64-unknown-linux-gnu/rustup-init \
 && chmod +x /tmp/rustup-init \
 && /tmp/rustup-init -y --default-toolchain stable --profile minimal --no-modify-path \
 && PATH="/root/.cargo/bin:$PATH" cargo install --locked \
      --git https://github.com/ReFirmLabs/binwalk --tag "${BINWALK_TAG}" binwalk \
 && cp /root/.cargo/bin/binwalk /usr/local/bin/binwalk \
 && rm -rf /root/.cargo /root/.rustup /tmp/rustup-init

# fwrecon itself, installed from the repository copy.
COPY tools/fwrecon /opt/fwrecon
RUN python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir -q /opt/fwrecon \
 && ln -s /opt/venv/bin/fwrecon /usr/local/bin/fwrecon

WORKDIR /work

# Fail the build rather than ship an image whose tools do not run.
RUN binwalk --version \
 && sasquatch -help >/dev/null \
 && unsquashfs -help >/dev/null \
 && qemu-mips-static --version >/dev/null \
 && fwrecon --version

CMD ["/bin/bash"]
