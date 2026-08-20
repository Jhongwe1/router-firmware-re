# The boot loader's flash table — why this unit boots from a part its own loader cannot name

Answers an observation that has been sitting in this project's first boot log
since 2026-08-15 with no explanation attached:

```text
Booting...
chipName: UNKNOWN
ramSize: 32M
---RealTek(RTL8196E)at 2014.04.22-16:22+0800 v1.3 [16bit](400MHz)
```

**The loader asks the chip for its JEDEC id, gets an answer, and has no row for
it.** It carries a table of 32 flash descriptors and the part fitted to this
board is not among them — so it prints the string it prints when the lookup
fails. Nothing is wrong with the flash and nothing is wrong with the boot.

| | |
|---|---|
| Table at | `0x0d764` in the unpacked stage 2, running to `0x0db44` |
| Shape | 32 records, fixed stride `0x20`, eight big-endian words each |
| Key | word `+0x00`, a three-byte JEDEC id with a zero top byte |
| Name | word `+0x18`, a pointer into the string area |
| Stage 2 load base | **`0x80400000`**, recovered from those pointers, not assumed |
| Eon rows | `1c3115` `1c3116` `1c3015` `1c3016` — F16, F32, Q16, **Q32** |
| This unit's part | `EN25Q**H**32B`, JEDEC **`1c7016`** — **no row** |

Report: [`reports/bootloader-unit-2018.json`](../reports/bootloader-unit-2018.json),
`chip_table`. Tool: `tools/loader-unpack.py --chip-table`, and
`--has-id 1c7016` answers the one question this note exists for, with an exit
status rather than prose.

---

## 1. The load base is recovered, and the recovery can end at nothing

A table of names proves very little on its own — a loader could hold 32 part
names for a log message and match on something else entirely. What makes this a
lookup table is that **each name is reached through a pointer, and every pointer
resolves under one and the same load base**.

That base is not assumed. Every (pointer, string) pair in the whole 56,592-byte
stage implies a candidate base; the page-aligned ones are kept, and of those, the
one whose pointers form a run at a fixed `0x20` stride at least 16 deep is the
answer. On this stage the funnel is:

| filter | survivors |
|---|---|
| words in kseg0 | 1,402 |
| …implying a page-aligned base for some string start | 34 bases |
| …whose pointers run at a `0x20` stride, 16+ deep | **1** |

`0x80400000`. The tool refuses at zero survivors and refuses at two — a recovery
that cannot narrow to one has not recovered anything, which is the same shape as
[`tools/libbase.py`](../tools/libbase.py) and for the same reason.

Two readers check each other on the field everything rests on: the regex string
scanner and a byte walk from the pointer must return the same name, or the tool
refuses.

## 2. The absence is checked, not merely observed

This note's headline is that something is **not** there, and the way that claim
goes wrong is a walk that stops early. So the tool asks a second question: is
there any word anywhere in the stage that points into this table's own name
block but is not on the walked stride? **Zero.** Every part name the loader
carries is reached by a row the walk visited.

`tools/check-reports.py` refuses to accept the committed report if that count is
not zero, or if the table was refused, for the same reason it already demanded
the seventeen-command positive control: an absence in a committed report reads
as a result.

## 3. What else fell out of the table

**Three duplicated ids, and one of them is a bug in the vendor's data.**

| id | rows | names |
|---|---|---|
| `c84018` | 3 | `GD25Q128` three times |
| `ef4016` | 2 | `W25Q32` twice |
| **`ef3016`** | 2 | **`W25X32` and `W25X64`** |

`W25X64`'s real JEDEC id is `ef3017`. Its row carries `ef3016`, which is
`W25X32`'s. Whatever the loader matches on, one of those two rows is unreachable
and a W25X64 gets named as a W25X32. It is a copy-paste defect in a table nobody
was ever going to look at, found by decoding it rather than by reading the
strings.

And `20ba17` — a Micron part — has the name string **`MCba17`**, which reads like
somebody typed a model name out of the id and mangled it.

**Every non-Spansion row declares a 4 KiB smallest erase unit**; the four
Spansion rows (`0102xx`, `012018`) declare 64 KiB, so the field is a real
per-part parameter rather than a constant.

## 4. The open question this creates, and it is about writing

G3.5 measured, on this hardware, that the loader's `FLW` has **no erase command
at all** and behaves as a whole-4-KiB read-modify-erase-program cycle. The table
says 4 KiB for every part it knows. **But this chip matches no row**, so the
descriptor `FLW` used was not looked up — it was a default, or a failure path
that still lands on 4 KiB.

Which one is unread. It is `PROGRESS.md` open item 89, and it matters more than
it looks: every flash write this project has performed through the boot loader
went through that path, on a part the loader could not identify.

## 5. How the first version of this note was wrong

**Twice, and both mistakes were the same mistake at different magnifications.**

The first pass found the answer by grepping the unpacked stage for strings that
look like flash part numbers — `MX25L1605D`, `EN25Q32`, `W25X64` — noticed that
no `EN25QH32` was among them, and stopped. That conclusion is *right* and the
evidence for it is *weak*: a list of names does not establish what the loader
matches on, and "I did not find the string I was looking for" is exactly the
shape of a failed grep. The claim only became defensible when the id table was
decoded and the loader was shown to key on three bytes that this chip does not
supply. **The name strings were the clue; they were never the evidence.**

The second was the completeness check. Asking "are there pointers into the string
area outside the run?" returned **89**, which read for a moment as the walk
having missed most of the table. They are two other tables entirely: the
firmware container signature list (`cr6c`, `cs6c`, `w6cp`, `jw6c`, `r6cr`,
`boot`, `cwmp`, `ksap`, `ALL1`, and `ALL2` — "Total Image (no check)"), and a NIC
register-name table. The right question is narrower — pointers into *this
table's own name block* — and that answer is zero. **A completeness check aimed
too wide reports a failure it cannot distinguish from a real one**, which is the
failure mode that would have sent the next session chasing a walk that was
already correct.

> `ALL2` — "Total Image (no check)" — is a firmware image type this loader burns
> without checking, and it turned up as noise in a check about something else.
> It is not pursued here. It belongs to `P9-10`.
