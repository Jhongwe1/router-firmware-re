# Flash layout, read off the device

Answers W01/W04 open question #2's second half, and closes the loop on a
prediction W01 made three weeks before the hardware existed on this desk.

**Read through the boot loader — `FLR` (flash → RAM) then `DB` (show RAM) — with
no SOIC-8 clip and no risk to the board.** Commands and their traps are in
[`uart-pinout.md`](uart-pinout.md#4-the-boot-loader-console-is-interactive).

| Flash offset | Contents | Evidence |
|---|---|---|
| `0x000000` | boot loader, MIPS code | `0b f0 00 04` = `j`, then a chip-ID compare against `0x8196E000` |
| `0x010000` | **`w6cg`** header + bzip2 web resources, `len = 0x043A14` (277,012) | magic `77 36 63 67`, payload starts `42 5a 68 39` = `BZh9` |
| `0x060000` | **`cr6c`** header + kernel, `len = 0x0F1002` (987,138), `startAddr = 0x80500000` | magic `63 72 36 63` |
| `0x180000` | **SquashFS 4.0**, LZMA, 567 inodes, `bytes_used = 0x1CA041` (1,876,033) | magic `68 73 71 73` = `hsqs` |
| `0x3F0000` | erased | all `FF` |

Image ends at `0x180000 + 0x1CA041 = 0x34A041` — **3.29 MiB**.

---

## 1. W01's derivation, checked against silicon

W01 never saw this device. It parsed the two vendor `.web` containers, read the
`burnAddr` field out of each 16-byte section header, and produced a flash map.
Those offsets were a **prediction**, and this is the test:

| W01 predicted, from the vendor images | Found on the device |
|---|---|
| `w6cg` at `0x010000` (2015-style images only) | ✅ `w6cg` at `0x010000` |
| `cr6c` at `0x060000` (2015-style) / `0x010000` (2020-style) | ✅ `cr6c` at `0x060000` |
| rootfs at `0x180000` (both) | ✅ SquashFS at `0x180000` |

**Three for three.** The container format W01 reverse engineered — with no
documentation, from two files — describes where a *third, unseen* build actually
sits in flash.

And the headline number survives: the resident image needs **3.29 MiB**. The
published specification says 2 MB. **W01's "the spec is impossible, expect ≥ 4 MB"
was right, and this is the second independent confirmation** after the package
marking.

## 2. Two structural findings the images could not have told us

**The 16-byte `IMG_HEADER_T` is written to flash for `w6cg` and `cr6c`.** It is
not stripped at flashing time. `cr6c`'s `startAddr` field reads `0x80500000` — the
exact address the boot log prints as `Jump to image start=0x80500000`. The
container field and the loader's behaviour agree.

**The rootfs is written *without* one.** At `0x180000` the SquashFS magic is at
offset 0; there is no `r6cr` header in front of it. The two treatments differ
because the uses differ: the boot loader parses `w6cg` / `cr6c` headers to know
where to load, while the rootfs is mounted as an MTD partition and a squashfs must
begin exactly at the partition boundary — 16 bytes of header would break the
mount.

> This also corrects how W01's `flash_map` should be read. It records each
> section's *payload* length; in flash, `w6cg` and `cr6c` occupy **length + 16**.

## 3. This unit uses the 2015 layout

The 2020 image dropped the web-resource section entirely and moved the kernel down
to `0x010000`. **This 2018 build did not.** It has `w6cg`, and its kernel is at
`0x060000` — the 2015 arrangement.

| | V2.1.2 (2015) | **this unit (2018)** | V3.4.0 (2020) |
|---|---|---|---|
| `w6cg` @ `0x010000` | 308,866 | **277,012** | absent |
| `cr6c` | `0x060000`, 985,090 | **`0x060000`, 987,138** | `0x010000`, 1,234,946 |
| rootfs @ `0x180000` | 2,174,978 | **1,876,033** used | 2,158,594 |
| SquashFS compression | LZMA | **LZMA** | XZ |
| inodes | 582 | **567** | 827 |
| fragments | 28 | **20** | 43 |
| image ends at | 3.574 MiB | **3.29 MiB** | 3.559 MiB |

**Every figure differs from both.** This is a third, distinct filesystem — smaller
than either, with fewer inodes, still on LZMA. Structurally it is a late member of
the 2015 family, not an early member of the 2020 one.

## 4. A W01 "possibly" that is now a finding

W01 flagged an anomaly in V3.4.0's SquashFS superblock and hedged it:

> `mkfs_time` is implausible (2038-07-17); raw = `0x80ed2000`. Byte-reversed it
> reads `0x0020ed80`, which is suspiciously close to the filesystem size —
> **possibly** a vendor build-script bug writing a size into this field.

This unit's superblock reads `mkfs_time = 0x80AD1C00`. Byte-reversed:
`0x001CAD80` = **1,879,424**, against a `bytes_used` of **1,876,033**.

| Build | `mkfs_time` raw | byte-reversed | `bytes_used` | delta |
|---|---|---|---|---|
| V3.4.0 | `0x80ED2000` | 2,157,952 | 2,155,236 | 2,716 |
| **this unit** | `0x80AD1C00` | **1,879,424** | **1,876,033** | **3,391** |

Same relationship, same order of magnitude, on an image built by a different
person on a different day. **Three builds now carry it. The hedge can come off:
that field holds a byte-swapped size, not a timestamp.**

## 5. The read path validated itself

Before the first `FLR`, RAM at `0x80500000` was dumped as a control — the only way
to distinguish "`FLR` copied the flash" from "that is whatever was already there".

The control read:

```
80500000: 00 00 00 00 00 00 80 21 40 90 60 00 00 00 00 00
80500010: 00 00 00 00 00 00 00 00 3c 10 80 5f 26 10 10 00
```

Later, reading flash `0x060000` — the `cr6c` section — the payload after its
16-byte header is:

```
        : 00 00 00 00 00 00 80 21 40 90 60 00 00 00 00 00
        : 00 00 00 00 00 00 00 00 3c 10 80 5f 26 10 10 00
```

**Byte-identical.** The control was the kernel's raw boot stub, already placed in
RAM by the boot loader, and it matches what `FLR` independently read out of flash.
Two unrelated paths, the same bytes.

---

## 6. The config region — found, and it is not where the plan said

The tail of the part is erased (`0x3F0000` and `0x350000` both read all `FF`), so
"config lives at the end of the flash" is wrong. The Realtek SDK puts it **below
`0x010000`**, inside what looks from the outside like the boot loader's 64 KB:

| Offset | Magic | Length | What it is |
|---|---|---|---|
| `0x006000` | `H601` | — | **HW setting** — MAC addresses and radio calibration |
| `0x008000` | `COMPDS` | `0x1D39` (7,481) | **CO**M**P**ressed **D**efault **S**etting — factory defaults |
| `0x00A000` | — | — | written zeros (not `FF`: allocated, not erased) |
| `0x00C000` | **`COMPCS`** | `0x1D36` (7,478) | **CO**M**P**ressed **C**urrent **S**etting ← **this is `config.dat`** |
| `0x00E000` | — | — | written zeros |

### This unblocks W04's first deferred item

W04 recorded, under *Deliberately not done*:

> Decoding the `COMPCS` compressor and parsing a real `config.dat` — **needs a
> real `config.dat`, which needs W02's flash dump.**

It is at `0x00C000`, it is 7,478 bytes, and it is now reachable. W04 located
`USER_NAME` (`0xb6`) and `USER_PASSWORD` (`0xb7`) inside the MIB table that this
blob is a serialisation of; the blob itself was the missing half.

### And the layout hands over a differential

`COMPDS` and `COMPCS` are the **factory defaults** and the **live configuration**
of the same table, stored the same way, 3 bytes apart in length. Their first 58
payload bytes are identical except for **one byte** (`0x47` against `0x67` — `G`
against `g`).

Two near-identical compressed blobs where one is known to be "as shipped" and the
other "as running" is close to an ideal setup for working out an undocumented
format — far better than attacking a single blob cold. **That is a W04/W07 lead,
not a W02 deliverable**, and it is recorded here rather than pursued.

It also says something about the unit: **its live configuration is barely
distinguishable from factory defaults.** It was reset, or never meaningfully
configured.

### The PCB barcode is confirmed to be the MAC

`hardware-inspection.md` called the 12 hex digits on the bottom-side label
"**almost certainly** this unit's MAC address" and noted that confirming it had
not been done.

**The `H601` block at `0x006000` opens with a run of MAC addresses, and the first
of them is byte-for-byte the string printed on that label.** Inference upgraded to
measurement, from a completely independent source — and the redaction applied to
that photograph was, in hindsight, not optional.

> ⚠️ **The values are not reproduced here, in this repository, or in any log that
> leaves this machine.** `0x006000`–`0x008000` is the one region of this flash that
> must never be published: per-unit MACs and radio calibration. Same rule as the
> photographs — see [`img/README.md`](img/README.md).

## 7. What is not settled

- **No full dump exists yet.** Everything above is 64-byte windows at chosen
  offsets. A full 4 MiB image — by CH341A, or by `FLR`+`DB` over the console at
  roughly 80 minutes — is what W05/W06 needs, and it is the only way to get this
  unit's `boa` into Ghidra. See [`uart-findings.md`](uart-findings.md#why-this-is-the-most-consequential-line-in-the-log).
- Whether `chipName: UNKNOWN` in the boot log refers to this flash part.
- The gaps at `0x053A24–0x05FFFF` and `0x151012–0x17FFFF` are assumed to be
  padding to the next 64 KB boundary. Not read.

---

## How the first version of this note was wrong

Its first version was the plan's, and it was wrong in a way that would have
produced confident, corrupt output rather than an error:

> ```
> # 典型 RTL8196C flash layout(2MB):
> # 0x000000 - 0x00FFFF : bootloader (64KB)
> # 0x010000 - 0x0FFFFF : kernel + rootfs
> # 0x1F0000 - 0x1FFFFF : config (64KB)
> dd if=flash.bin bs=1 skip=$((0x1F0000)) of=config-region.bin
> ```

Every offset in it is for a 2 MB part. On this 4 MiB device `0x1F0000` lands in
the middle of the kernel, and the `dd` would have produced a perfectly
well-formed file of the wrong thing. **The failure mode is not a crash, it is a
plausible artefact** — which is the kind this project keeps having to catch.

The correction that matters is not the numbers. It is that **the offsets should
never have been typed from a template at all.** They were available two ways
before any of this was read: derived from the vendor container by W01, and
printed by the device itself. A layout you copied from a blog post about a
different chip is not a source.

And one mistake that was mine: I predicted the config region would be at the tail
of the part, at `0x3F0000`, on nothing better than "that is where config usually
goes". It is erased. The Realtek convention had it below `0x10000` the whole time.
