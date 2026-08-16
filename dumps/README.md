# Dumps

Raw reads from **my own unit** — UART boot logs and SPI flash images.

## What is here and what is not

| | |
|---|---|
| **In git** | this file, `MANIFEST.json` (hashes + provenance), **both UART console logs**, and findings quoted inside `notes/` |
| **Not in git** | every raw flash image. [`.gitignore`](../.gitignore) keeps `dumps/*` out, and `*.bin` is blocked a second time independently |

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

## 2026-08-16 (W04-2): one reason expired and the other did not

The disclosure policy changed to a per-field decision, and for this unit the
answer is publish: it is self-purchased, end of life, was never deployed, and its
live configuration differs from the factory defaults in **21 bytes out of
45,226**. That kills reason 2 above outright.

**Reason 1 is untouched, so nothing about the raw image changes.**

That is the whole point of having written the two reasons as independent and
labelled them *either one is sufficient*. When one of them expired there was no
argument to re-run and no risk of quietly losing the other in the rewrite — the
answer was already on the page, from before it was needed. It is the clearest
case in this project of a piece of documentation discipline paying for itself.

### What did change

**Both UART logs are now committed.** They had never been added, on a general
rule about per-unit data rather than on anything they contain — and
`MANIFEST.json` recorded `contains_unit_identifiers: false` for both all along.
They were re-screened against the files before being added rather than trusted
from the manifest, because that field was *last* time's conclusion:

```sh
grep -ainE '([0-9a-f]{2}:){5}[0-9a-f]{2}' dumps/uart-boot.log   # MAC, colon form
grep -ainE '[0-9a-f]{12}' dumps/uart-boot.log                   # MAC, bare hex
grep -ainE 'pin|psk|passw|secret|serial' dumps/uart-boot.log
```

No hits in either file; the only `wps` match is a version banner. Note the `-a`:
`uart-boot.log` contains three non-printable bytes, so plain `grep` calls it
binary and prints `binary file matches` **without showing what matched** — which
reads exactly like a finding when it is the opposite.

### What deliberately did not change

- **The raw flash image stays out**, per reason 1.
- **EXIF stays stripped from the photographs.** The new argument is "this device
  is retired"; GPS locates a *person*, and people do not reach end of life. A
  reason that does not transfer is not a reason.
- **`fwrecon compcs --disclosure protect` and `flashdump`'s digest-only
  reporting both stay, each with a test that fails if a byte escapes.** What
  changed is a policy, not a capability. A mechanism deleted because the policy
  relaxed does not grow back when the policy tightens, and the next device may
  not be mine.

> Decide before `git add`. A redaction applied after a push is not a redaction.

## What does get committed

- `MANIFEST.json` — for each dump: file name, size, SHA-256, when and how it was
  read, and **the hash of the second read**. Two reads of the same flash must hash
  identically; if they do not, the dump is not evidence.
- Findings derived from a dump, in `notes/`, with the per-unit values removed.
