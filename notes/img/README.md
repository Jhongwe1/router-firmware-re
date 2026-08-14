# Photographs

Images backing [`../hardware-inspection.md`](../hardware-inspection.md) and G2's
"annotated PCB photograph" checkbox.

## The rule

**Anything read off *this specific unit* is redacted before it is committed.
Only what is true of *the model* is published.**

This board carries at least two unit-identifying labels:

| Where | What |
|---|---|
| PCB bottom, barcode label | 12 hex digits — almost certainly this unit's **MAC address** |
| PCB top, QR + numeric label | unit **serial number** |

Both are redacted — painted over, not cropped to the edge and not blurred, since a
blur can sometimes be reversed and a crop can be undone if the original is ever
published by accident.

The same rule applies to the two other places this unit's identifiers will surface
later in W02:

- the **UART boot log** — MAC addresses, and plausibly the WPS PIN, given W04's
  `flash set HW_WLAN0_WSC_PIN %s` finding in
  [`submit-url-overflow.md`](../submit-url-overflow.md);
- the **SPI flash dump's config partition** — which is one of the reasons
  [`.gitignore`](../../.gitignore) keeps `dumps/*` out of the repository entirely.

Redact **before** `git add`. A redaction applied after a push is not a redaction.

## Conventions

- **Downscale to ~1600 px on the long edge** before committing. Phone originals are
  3–5 MB each; this repository is text and should stay that way.
- Keep the originals in `$FWRE_WORK`, outside the repository, alongside the dumps.
- File names say what the photograph shows and whether it has been redacted:
  `pcb-top.jpg`, `pcb-bottom-redacted.jpg`, `uart-header.jpg`, `ic-<part>.jpg`.
- The annotated overlay is a separate file from the clean photograph, so a reader can
  check the annotation against the original.

## Inventory

| File | Shows | Redacted? |
|---|---|---|
| _(none committed yet)_ | | |

W02 Day 1 produced: exterior, opened case, board top, board bottom, and close-ups of
the five ICs. None are committed yet — the bottom-side and top-side label redactions
are outstanding.
