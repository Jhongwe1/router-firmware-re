# Hardware inspection — what the board actually is

Answers, from the board itself, two questions carried forward since W01:

| Carried-forward question | Answer |
|---|---|
| **Real flash part and size** — W01 open #2, W04 open #2 | **Eon (cFeon) EN25QH32B — 32 Mbit = 4 MiB SPI NOR**, reference `U19`, SOP-8 |
| **SoC** — G1 #1 answered as "RTL8196-class, firmware-consistent, *not yet confirmed on silicon*" | **RTL8196E**, now confirmed on silicon. Not the RTL8196**C** the project plan asserted |

It deliberately does **not** answer the third — *which firmware build is on my unit*
(W01 open #1) — but it does write down a dated prediction that the flash dump will
confirm or destroy. See [§6](#6-date-codes--a-prediction-written-before-the-dump).

> ⚠️ **Every row below has exactly one source: the ink on the package.**
> No independent measurement has been taken. **No device has been powered on.**
> The "Second source" column is not decoration — it is the W02 Day 2–4 work list,
> and until it is filled in, everything here is *what the parts claim to be*.

---

## The five ICs

| Ref | Marking on the package | Reading | Function | Second source (pending) |
|---|---|---|---|---|
| — | `RTL8196E` · `I510VG1` · `GF23 TAIWAN` | Realtek **RTL8196E** | SoC — MIPS, big-endian | boot-loader banner; `/proc/cpuinfo` |
| `U19` | `cFeon` · `QH32B-104HIP` · `X703811` · `1750HKB` | Eon **EN25QH32B** — 32 Mbit (4 MiB) SPI NOR | firmware storage | JEDEC ID read over SPI by `flashrom` |
| — | `Winbond` · `W9825G6KH-6` · `1837H` · `6824506000` | Winbond **W9825G6KH** — 256 Mbit SDRAM, 16M × 16 = **32 MiB** | system RAM | kernel memory line; `/proc/meminfo` |
| — | `RTL8188ER` · `I210QP1` · `GF08` | Realtek **RTL8188ER** — 1T1R 802.11n | Wi-Fi radio | driver banner in the boot log |
| — | `LSC` · `LSP5526` · `181525` | **not identified** | power — step-down regulator, *inferred from context only* | multimeter on its output pin |

Photographs: see [§7](#7-photographs).

---

## 1. Flash — the derivation was right and the published spec was wrong

W01 never saw this chip. It read the vendor container's own burn addresses out of
the two `.web` images, found that the flash map extends to **3.57 MiB**, and
concluded that the widely published "2 MB" figure is *impossible* — the firmware
does not fit in the part the spec sheet claims. That went into
[`PROGRESS.md` § Corrections](../PROGRESS.md#corrections-to-the-original-plan)
three weeks before the hardware arrived, as a prediction: **≥ 4 MB**.

The package says 32 Mbit. The prediction holds.

`flashrom` knows the part and will read it:

```
$ flashrom -L | grep -i en25qh
Eon                          EN25QH128                            PREW          16384  SPI
Eon                          EN25QH16                             PREW           2048  SPI
Eon                          EN25QH32                             PREW           4096  SPI
Eon                          EN25QH64                             PREW           8192  SPI
```

`PREW` = probe / read / erase / write all supported; `4096` KiB = 4 MiB.

> 🔎 **`flashrom`'s agreement here is not an independent source, and it must not be
> counted as one.** Its chip database is keyed on the *part name*, and the part name
> came from the same ink as everything else in this note. What the output above
> establishes is "**if** this is an EN25QH32, it is 4096 KiB and `flashrom` can read
> it" — not "this chip is 4 MiB".
>
> The independent measurement is the **JEDEC ID the chip reports over SPI** when
> `flashrom` probes it (Eon's manufacturer ID is `0x1C`). That is W02 Day 4, and
> until then the size has one source.

**Reading risk, recorded so a later reader can check it:** cFeon's `Q` renders
almost exactly like `O` at this magnification, and the photograph reads `OH32B`.
There is no `EN25OH32B`; the part is `EN25QH32B`. This is resolved by the JEDEC ID,
not by looking harder at the photograph.

**Package width matters before the SOIC-8 clip goes on.** SOP-8 exists in 150 mil
and 208 mil bodies, and the clip bundled with a CH341A kit is often the narrow one.
Measure `U19` before forcing anything onto it. The `-104HIP` suffix decodes in the
EN25QH32B datasheet's ordering-information table — that is the first-party source
and it should be read rather than guessed at.

---

## 2. SoC — RTL8196**E**, and what that does to W01's "MIPS-I"

The project plan asserted RTL8196**C** throughout. The die marking says
RTL8196**E**. The board wins.

This is not only a bookkeeping correction. The two parts are commonly documented
with **different CPU cores** — the RTL8196C as a Lexra **RLX4181**, the RTL8196E as
an **RLX5281** — and the older Lexra cores are the ones that omit the
patent-encumbered unaligned load/store instructions `LWL` / `LWR` / `SWL` / `SWR`.

W01 recorded G1 #2 as "MIPS32, **MIPS-I** ISA, o32 ABI", taken from `EF_MIPS_ARCH`
in the ELF header. That field describes **what the compiler targeted**, not what the
silicon can execute. If the silicon is an RLX5281, then a MIPS-I target is a *choice*
— most likely the Realtek SDK toolchain staying on the oldest baseline in the family
— and not a constraint imposed by this chip.

That turns into a cheap, falsifiable test that costs one script:

> **Hypothesis.** `LWL`, `LWR`, `SWL` and `SWR` appear **zero** times in `/bin/boa`,
> in both builds.
>
> **If it holds** — the SDK toolchain is still pinned to the Lexra instruction
> subset in 2020, five years and one SoC generation after it had to be, and that is
> the reason the ELF header says MIPS-I.
>
> **If it fails** — the toolchain was not so pinned, and W01's MIPS-I needs a
> different explanation than the one above.

**Not run.** It needs a mnemonic histogram out of Ghidra, which does not exist yet.
Listed as W02 follow-up, not claimed as a result.

**Second source for the part itself:** the boot-loader banner and `/proc/cpuinfo`,
which on this SDK print the system type and the core name directly. The silicon
naming its own core settles both the part and the RLX4181/RLX5281 question at once.

---

## 3. SDRAM — 32 MiB *installed* is not 32 MiB *usable*

`W9825G6KH-6` is a 256 Mbit SDRAM organised 16M × 16, i.e. **32 MiB**, `-6` being
the 6 ns / 166 MHz speed grade. The plan asserted 16 MB.

**Do not simply overwrite 16 with 32.** The package tells you what is *fitted*.
How much the system actually gets is decided by the boot loader's memory-controller
configuration and reported by the kernel. These are two different facts and both
belong in the record:

- **Fitted:** 32 MiB — source: package marking.
- **Usable:** unknown — source: kernel banner / `/proc/meminfo`, W02 Day 3.

If those two disagree, the disagreement is a finding, not a measurement error.

---

## 4. Radio — RTL8188ER, and the antenna that must stay attached

1T1R 802.11n, consistent with the product's 150 Mbps rating, and **discrete** —
the radio is not integrated into the SoC. The interface it uses to reach the
RTL8196E has not been traced and is not claimed here.

Two consequences worth having written down:

- **The antenna coax terminates into this chip's output stage.** Powering the board
  with that feed removed drives the amplifier into an open circuit. The transmit
  power on a 1T1R 11n part is low and the risk is not dramatic, but the payoff for
  removing the antenna is exactly zero — nothing in G2 needs it gone. It stays.
- This is the radio that W04's `flash set HW_WLAN0_WSC_PIN %s` + `system()` line
  ultimately configures — see [`submit-url-overflow.md`](submit-url-overflow.md).
  A boot log from this unit is therefore likely to print **this device's own WPS
  PIN and MAC addresses**, which is a redaction decision to make *before* a log is
  committed, not after.

---

## 5. Power — LSP5526, unidentified, and that is the honest state

8-pin, sitting among passives with what appears to be a diode (`D3`) alongside.
Everything about its position says switching step-down regulator, and nothing about
it has been confirmed. **I do not know this part, and this note is not going to
pretend otherwise.**

Confirmation costs about thirty seconds once the board is powered: measure its
output pin against ground, and if it is the 3.3 V rail feeding the flash and the
SoC, the question is closed at the level of detail this project needs.

It is the one IC on this board that does not matter to the analysis. Recorded for
completeness of the parts list, and deliberately not investigated further.

---

## 6. Date codes — a prediction written *before* the dump

| Part | Code | Reading |
|---|---|---|
| cFeon flash | `1750HKB` | 2017, week 50 |
| **Winbond SDRAM** | **`1837H`** | **2018, week 37** ← newest |
| U&T magnetics | `1818A`, `1818Q` | 2018, week 18 |
| LSC regulator | `181525` | 2018, week 15 (probable) |
| PCB fab, bottom silkscreen | `18.15` | 2018 |

Five independently sourced parts, five 2017–2018 dates, and a PCB fab mark that
agrees. The newest is September 2018, so **the board was assembled no earlier than
2018-09** — and the spread is tight enough that no single misread code changes the
conclusion.

> **Prediction.** The firmware resident on this unit is neither V2.1.2 (2015-08-25)
> nor V3.4.0 (2020-10-30) — the two images this project has analysed — but a build
> from around 2018. The 2025 CVE series names `N150RT 3.4.0-B20190525`, a May 2019
> build, which sits just after this board's assembly window.

**Two ways this prediction can be wrong, stated up front:**

1. A previous owner — or I — may have updated the firmware. The unit was bought
   used-condition-unknown for this project.
2. Production lines flash whatever image is current at build time, which routinely
   lags the newest release by months.

So the date codes bound the **board**, not the firmware. They give a lower bound on
the build date and nothing more.

**Why it is worth writing down anyway.** If the dump does show a 2018-era build,
this project stops being a two-point before/after comparison and becomes a
three-point timeline — and the third point lands exactly in the gap that matters,
between the 2015 authorisation hole and the 2020 repair described in
[`auth-flow-2020.md`](auth-flow-2020.md). That is a materially better result than
either outcome of guessing after the fact.

**Settled by:** the version string in the SPI dump, or in the boot log. W02 Day 3–4.

---

## 7. The board

![PCB top, annotated](img/05-pcb-top-annotated.jpg)

Rendered from [`img/03-pcb-top-redacted.jpg`](img/03-pcb-top-redacted.jpg) and
[`img/pcb-top-annotations.json`](img/pcb-top-annotations.json) — the callouts are a
committed text file, not strokes in an image editor, so a moved box shows up in
`git diff` and anyone can re-render it against the source photograph. Full set and
handling: [`img/README.md`](img/README.md).

### 7.1 Layout

Single-sided assembly; the bottom is bare copper, solder joints and two labels.

| Feature | Reading |
|---|---|
| Board marking | `0422C` (silkscreen, beside the SDRAM) |
| Ports | **4 × LAN (orange) + 1 × WAN (yellow)** |
| Magnetics | `U&T UTH20T02M` × 2 (two ports each) + `UTH16T01M` × 1 — five ports, consistent with the RTL8196E's integrated switch. Date code `1818` |
| Power input | barrel jack at the board's top-left corner, with a push button beside it |
| Power switch | 2-pin header `J2`, immediately adjacent to the barrel jack — see [§7.4](#74-j2-and-the-power-switch) |
| Antenna | `ANT1` / `ANT2` silkscreened; **one** antenna fitted — see [§7.3](#73-ant1-and-ant2--two-footprints-one-antenna) |
| Serial console | **4-pin header, populated, silkscreened `UART`** — see [§7.2](#72-the-uart-header--populated-and-labelled) |
| Unpopulated | footprints around `U6` are bare. Not investigated |
| PCB bottom | UL `94V-0`, fab mark `JL-2`, date `18.15` — 2018, consistent with everything else |

### 7.2 The UART header — populated, and labelled

The board carries a **4-pin 2.54 mm header, already soldered**, at the bottom edge
next to the LED row, with `UART` printed on the silkscreen beside it.

Two consequences:

- **W02 requires no soldering anywhere.** The single largest irreversible-damage
  risk of the week is removed before it can be taken.
- The vendor labelled it. This is a debug header left in a shipping consumer product
  — not a test point that had to be found, and not one that was obscured.

**What this does *not* settle: the pin assignment.** `UART` on the silkscreen names
the header, not the order of GND / VCC / TX / RX within it. That is measured on Day 2
and must not be assumed from the usual conventions.

### 7.3 `ANT1` and `ANT2` — two footprints, one antenna

Both `ANT1` and `ANT2` appear on the silkscreen; only one antenna is fitted, fed by
a single wire to the board's right edge. The RTL8188ER is a 1T1R part, so a second
antenna would be a diversity position rather than a second stream.

Recorded as an observation, not a finding. Whether the second footprint is populated
on other SKUs of this board is not known and has not been checked.

### 7.4 `J2` and the power switch

`J2` is a 2-pin header sitting **immediately beside the DC barrel jack**. The
red/black pigtail running to the case-mounted switch mates here; it was unplugged
during disassembly and has been plugged back in.

That adjacency is what you would expect if the switch is **in series with the raw DC
rail** — jack → `J2` pin 1 → switch → `J2` pin 2 → regulator. **This is a layout
inference from a photograph and nothing more.** It is settled with a continuity meter
across the pigtail, and with a continuity check from the jack's centre pin to one of
the `J2` pins, both with the adapter unplugged.

It matters because the alternative — a ground-referenced GPIO with a pull-up —
behaves differently when shorted, and shorting an unidentified pair was proposed and
rejected during disassembly. See [`LOG.md`](../LOG.md).

### 7.5 What was redacted, and why

**The board carries two unit-identifying labels, and one of them is on the very
photograph G2 asks for.**

| Where | What | Done |
|---|---|---|
| PCB bottom, barcode label | a 12-hex-digit string — **almost certainly this unit's MAC address**. Confirming that by looking the leading three bytes up as an OUI has *not* been done | painted out |
| PCB top, QR + numeric label | unit serial | painted out, in both the close shot and the wide one |

The QR is the more dangerous of the two, and it is the one that is easy to wave
through: a printed number has to be *read*, a QR code is **decoded automatically**
and survives heavy downscaling. It is covered wherever it appears, including in the
wide shot where it is only a few dozen pixels across.

Solid fill, never blur — a blur is a reversible transform on a known font. Exact
coordinates and the commands that produced each file are in
[`img/README.md`](img/README.md), so a reader can confirm what was covered rather
than take it on trust.

This is not hypothetical tidiness. The same identifiers will appear again, from two
more directions, later in W02:

- the **boot log** will print the MAC addresses, and — given W04's
  `flash set HW_WLAN0_WSC_PIN %s` finding — plausibly the **WPS PIN** as well;
- the **flash dump's config partition** contains all of it, which is a large part of
  why [`.gitignore`](../.gitignore) keeps `dumps/*` out of the repository in the
  first place.

So the rule is one rule, applied in three places: **anything read off this specific
unit is redacted before it is committed; only what is true of the model is published.**
Decide it before the file is added, not after it is pushed.

Handling: see [`notes/img/README.md`](img/README.md).

---

## 8. What is *not* confirmed

Everything, strictly speaking. Listed explicitly so no later reader mistakes this
note for measurement:

- [ ] SoC identity and core (`/proc/cpuinfo`)
- [ ] Flash identity and size (JEDEC ID over SPI)
- [ ] RAM usable size (kernel banner)
- [ ] Radio identity (driver banner)
- [ ] Regulator function (multimeter)
- [x] UART header **located** — populated 4-pin, silkscreened `UART` (§7.2)
- [ ] UART pin assignment — which of the four is GND / VCC / TX / RX
- [ ] Baud rate
- [ ] Whether `J2` is a series power switch or a ground-referenced GPIO (§7.4)
- [ ] Which firmware build is resident
- [ ] `LWL`/`LWR`/`SWL`/`SWR` census in `/bin/boa` (§2)

---

## How the first version of this note was wrong

This is version 1, so the honest answer is that its *de facto* first version was the
hardware specification table in the project plan — written months ago, from published
material, before the device existed as anything but an order. **Three of its five
rows are wrong:** the SoC (RTL8196C, actually E), the flash (2 MB, actually 4 MiB),
and the RAM (16 MB, actually 32 MiB fitted). Every one of the three was copied from
a specification rather than read off a board.

But the useful correction is not the three numbers. It is this:

**The row the plan got most checkably wrong — 2 MB — had already been shown
impossible by W01, three weeks before the hardware arrived, using nothing but the
vendor's own firmware.** The published specification and the vendor's own burn-address
table contradicted each other, and the firmware was right.

The lesson is not "measure the hardware". It is that **the artefact under analysis is
usually a better source about itself than any document written about it** — and that
when a datasheet and a binary disagree, the correct instinct is to suspect the
datasheet. That instinct is what produced a prediction here instead of a surprise.

The second thing version 1 got wrong lives in [`LOG.md`](../LOG.md): the first
physical action taken on this board was an attempt to desolder the antenna feed at
450 °C, for no reason that survives being asked "which gate does this serve?".
