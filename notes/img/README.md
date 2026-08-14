# Photographs

Images backing [`../hardware-inspection.md`](../hardware-inspection.md) and G2's
"annotated PCB photograph" checkbox.

## The rule

**Anything read off *this specific unit* is redacted before it is committed.
Only what is true of *the model* is published.**

This board carries two unit-identifying labels, and one of them sits on the very
photograph the gate asks for:

| Where | What |
|---|---|
| PCB bottom, barcode label | 12 hex digits — almost certainly this unit's **MAC address** |
| PCB top, QR + numeric label | unit **serial number** |

The QR is the more dangerous of the two: a printed number has to be read, a QR code
is *decoded automatically* and survives heavy downscaling. It is covered wherever it
appears, including in the wide shot where it is only a few dozen pixels across.

The same rule reaches the two other places this unit's identifiers will surface in
W02:

- the **UART boot log** — MAC addresses, and plausibly the WPS PIN, given W04's
  `flash set HW_WLAN0_WSC_PIN %s` finding in
  [`submit-url-overflow.md`](../submit-url-overflow.md);
- the **SPI flash dump's config partition** — see [`dumps/README.md`](../../dumps/README.md).

Redact **before** `git add`. A redaction applied after a push is not a redaction.

## Inventory

| File | Shows | Redacted |
|---|---|---|
| `01-exterior.jpg` | assembled unit, top | — |
| `02-case-opened-redacted.jpg` | opened case, board in the lower shell, switch pigtail unplugged | serial QR |
| `03-pcb-top-redacted.jpg` | board top, full detail | serial QR |
| `04-pcb-bottom-redacted.jpg` | board bottom, UL and QC marks | **MAC barcode** |
| `05-pcb-top-annotated.jpg` | ← rendered from `03` + `pcb-top-annotations.json` | inherits `03` |
| `ic-soc-rtl8196e.jpg` | SoC die marking | — |
| `ic-flash-en25qh32b-u19.jpg` | `U19`, the 4 MiB SPI NOR | — |
| `ic-sdram-w9825g6kh.jpg` | SDRAM | — |
| `ic-wifi-rtl8188er.jpg` | Wi-Fi radio | — |
| `ic-power-lsp5526.jpg` | the unidentified regulator | — |

Unredacted originals are in `$FWRE_WORK/photos`, outside the repository, alongside
the firmware images and the flash dumps.

## How these were produced

Both steps are scripted rather than done in an image editor, for the same reason
W03 rejected Ghidra screenshots: **an editor produces a file nobody can check,
diff, or regenerate.** Both tools need Pillow in the project venv:

```bash
~/fwre-work/venv/bin/python -m pip install Pillow
```

### Redaction — [`tools/redact-photo.py`](../../tools/redact-photo.py)

Solid fill, never blur or pixelate; a blur is a reversible transform on a known
font, a filled rectangle destroys the information. EXIF is dropped, since a phone
photograph carries GPS and a device id that survive every visual redaction. The
exact regions, so a reader can confirm what was covered:

```bash
PY=~/fwre-work/venv/bin/python

$PY tools/redact-photo.py notes/img/<orig-pcb-bottom>.jpeg \
    notes/img/04-pcb-bottom-redacted.jpg \
    --expect-size 2048x1536 --box 640,710,520,200      # MAC barcode

$PY tools/redact-photo.py notes/img/<orig-pcb-top>.jpeg \
    notes/img/03-pcb-top-redacted.jpg \
    --expect-size 2048x1536 --box 200,870,160,200      # serial QR

$PY tools/redact-photo.py notes/img/<orig-case-open>.jpeg \
    notes/img/02-case-opened-redacted.jpg \
    --expect-size 2048x1536 --box 495,1005,100,120     # serial QR, wide shot
```

The tool verifies its own work by reading the written file back off disk. It cannot
prove the box landed in the *right place* — **that check is human, and it was done
by eye on all three.**

### Annotation — [`tools/annotate-photo.py`](../../tools/annotate-photo.py)

The callouts live in [`pcb-top-annotations.json`](pcb-top-annotations.json), so a
moved box shows up in `git diff` as a changed number and anyone can re-render
against the source photograph:

```bash
$PY tools/annotate-photo.py notes/img/pcb-top-annotations.json \
                            notes/img/05-pcb-top-annotated.jpg
```

The legend is drawn in a strip appended *below* the frame, never over it, so no
annotation can hide part of the evidence it describes.

### Self-test — [`tools/test-photo-tools.sh`](../../tools/test-photo-tools.sh)

```bash
bash tools/test-photo-tools.sh     # 13 cases against a synthetic image
```

Ten cases assert *this must be rejected, and for this reason*; three assert *this
must succeed*. **Both halves are load-bearing.** The reject-only half of this suite
once reported 5/5 passing while every invocation was dying on `import PIL` — a guard
suite without a control can go green with the whole system broken. Written up in
[`LOG.md`](../../LOG.md) and [`study/QA.md`](../../study/QA.md) §9.12.

## Conventions

- Long edge 2048 px. Enough to read silkscreen; the whole directory is ~2.3 MB.
- File names say what the photograph shows **and whether it has been redacted**,
  so an un-redacted file is visible as such in `git status` before it is added.
- The annotated render is a separate file from the clean photograph, so a reader
  can check the annotation against the original.
