# Dumps

Raw reads from **my own unit** — UART boot logs and SPI flash images.

## What is here and what is not

| | |
|---|---|
| **In git** | this file, `MANIFEST.json` (hashes + provenance), and redacted text extracts quoted inside `notes/` |
| **Not in git** | every raw dump. [`.gitignore`](../.gitignore) keeps `dumps/*` out, and `*.bin` is blocked a second time independently |

Raw dumps live in `$FWRE_WORK` alongside the firmware images — see
[`docs/workspace-layout.md`](../docs/workspace-layout.md).

## Why a flash dump is never committed

**Two independent reasons, and either one is sufficient:**

1. **It is the vendor's firmware.** This project does not redistribute it — only the
   provenance and hashes needed to obtain and verify identical bytes. A full flash
   read is the same content by another route. See "Scope & ethics" in the
   [README](../README.md).
2. **It contains this unit's secrets.** The config partition holds the admin
   credentials, the Wi-Fi PSK, the WPS PIN and the MAC addresses of *this* device.
   W04 located every one of those fields by name in the APMIB table — see
   [`notes/mib-and-config-dat.md`](../notes/mib-and-config-dat.md), where `0xb6` is
   `USER_NAME` and `0xb7` is `USER_PASSWORD`.

The same rule reaches the boot log, which is text and *would* otherwise be
committable: **it is expected to print MAC addresses, and plausibly the WPS PIN**,
given W04's `flash set HW_WLAN0_WSC_PIN %s` finding. Read it before adding it, and
redact per-unit identifiers.

> **One rule, three places** — photographs, boot log, flash dump:
> anything read off *this specific unit* is redacted before it is committed.
> Only what is true of *the model* is published.
>
> Decide before `git add`. A redaction applied after a push is not a redaction.

## What does get committed

- `MANIFEST.json` — for each dump: file name, size, SHA-256, when and how it was
  read, and **the hash of the second read**. Two reads of the same flash must hash
  identically; if they do not, the dump is not evidence.
- Findings derived from a dump, in `notes/`, with the per-unit values removed.
