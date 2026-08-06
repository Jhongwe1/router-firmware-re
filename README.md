# Router Firmware Reverse Engineering — TOTOLINK N150RT

> **Status:** 🚧 In progress — project just started (independent learning / portfolio project)

A hands-on firmware reverse-engineering study of a consumer router I own, for
**learning and portfolio purposes**. The goal is to take a real, end-of-life
embedded device, rebuild an understanding of its firmware from scratch, and
reproduce **already-publicly-disclosed** vulnerabilities down to the exact
function in the binary — then document the root-cause analysis.

This is the "break" half of a personal skills portfolio (the other half is a
system I built). The point is not the specific device — it is demonstrating that
I can take an undocumented binary system on an unfamiliar architecture, build
understanding from zero, and reason about its security.

## Target

- **Device:** TOTOLINK N150RT (V2 hardware) — a 2018, 150 Mbps consumer router
- **Support status:** End-of-life / no longer vendor-supported
- **Ownership:** Personally owned; all work is performed on my own hardware
- **Platform:** Realtek SDK · MIPS · Boa HTTP server (`Boa/0.94.14rc21`-class) ·
  CGI handlers under `/boafrm/form*` · SquashFS root filesystem

## Scope & ethics

- Work is limited to **hardware I own**, in an **isolated lab environment** — no
  connection to production networks or the public internet during testing.
- The focus is **reproducing and understanding publicly disclosed CVEs**, not
  developing or releasing novel weaponized exploits.
- I do **not** test third-party, production, or ISP-owned devices.
- **Coordinated disclosure:** anything genuinely new is reported through
  **TWCERT/CC** before any public discussion. No 0-day is published directly.
- Stock firmware images are **not redistributed** in this repository.

## Approach / methodology

1. **Firmware acquisition** — obtain the stock firmware image (vendor download or
   on-device dump).
2. **Unpacking** — `binwalk` / `unblob` to extract the SquashFS root filesystem.
3. **Static analysis** — load the Boa web-server binary and its `/boafrm/form*`
   handlers into **Ghidra**; map how request parameters flow toward sinks.
4. **CVE mapping** — for each publicly disclosed issue (e.g. OS command injection
   via the `formSysCmd` handler, buffer overflows in various `form*` handlers,
   plaintext config/credential disclosure on Realtek-SDK Boa devices), trace the
   public description down to the responsible function in the binary.
5. **Reproduction** — reproduce known issues in an **isolated / emulated**
   environment (e.g. FirmAE where supported) to confirm understanding.
6. **Write-up** — document the root cause, the vulnerable code path, and the
   defensive lessons ("if I were building this firmware…").

## Tooling

`binwalk` · `unblob` · Ghidra · QEMU / FirmAE · flashrom + CH341A (if SPI NOR) ·
USB-TTL UART (3.3V)

## Planned deliverables

- A full technical write-up (primary deliverable).
- Root-cause analysis of at least one known CVE, traced to the binary, with a
  reproduction in an isolated environment.
- A running notes / error-diagnosis log (`LOG.md`) — including the wrong turns,
  not just the successes.
- (Optional) small analysis tooling for firmware unpacking / attack-surface
  enumeration.

## Repository structure (planned)

```
firmware/    stock firmware images (NOT redistributed)
dumps/       flash / UART dumps from my own device
ghidra/      Ghidra project + analysis scripts
notes/       per-CVE analysis notes
poc/         minimal reproductions (isolated-lab only)
LOG.md       running log, including dead ends
```

## Legal

This project targets a personally owned, end-of-life device and is conducted in
an isolated environment for educational and defensive-research purposes. Firmware
is not redistributed. New findings follow coordinated disclosure via TWCERT/CC.
