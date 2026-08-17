# What this lab has, what it does not, and what the gaps cost

Fifteen registered tests cannot be run at this desk. Not for lack of time — for
lack of an instrument. This file names each gap, what it blocks, roughly what it
costs to close, and **what the absence costs the conclusions**, because that last
column is the one a reader needs and the one a shopping list usually omits.

## What is here

| | |
|---|---|
| The unit | TOTOLINK N150RT V2.0, `TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002`, self-purchased, never deployed |
| Serial | CP2102 USB–UART bridge, on the 4-pin header. Gives the boot loader console, which is how the flash was read |
| Network | Realtek RTL8153 USB Gigabit Ethernet, handed to WSL with `usbipd` so the host never joins the router's segment |
| Emulation | `qemu-user` MIPS-BE, two profiles — this unit's build, and a published image rebuilt from its container |

That set is enough for everything in W01–W06 and for most of W07.

## What is missing

### 1. A monitor-mode Wi-Fi adapter — blocks 9 tests

`P7-1`…`P7-10`: WPS Pixie Dust, online PIN brute force, malicious beacon into the
site-survey table, malicious WPS IE, PMKID, deauth → 4-way handshake → offline
crack, default PSK derivation, WDS/repeater KRACK, FragAttacks.

The Realtek USB adapter already here is **Ethernet**. Wireless attacks need an
adapter whose driver supports monitor mode *and* frame injection, which most
consumer dongles do not.

| Option | Chipset | Roughly | Notes |
|---|---|---|---|
| Alfa AWUS036NHA | Atheros AR9271 | US$30–40 | 2.4 GHz only — which is all this router has. The reference adapter: `ath9k_htc` is in-tree, so no DKMS, and injection works out of the box |
| TP-Link TL-WN722N **v1** | AR9271 | US$15–25 used | The same chipset for less. **v2 and v3 are Realtek and will not do this** — the version is not on the box, so buying new is a gamble |
| Alfa AWUS036ACM | MT7612U | US$40–50 | Adds 5 GHz, which this target does not use. Only worth it if other devices follow |

**Recommended: AR9271.** The target is 2.4 GHz-only 802.11n, so 5 GHz buys
nothing here, and `ath9k_htc` avoids an out-of-tree driver.

> **What the absence costs.** Every wireless claim in this project is currently
> **static only** — read out of `wscd`, the MIB and the configuration pages. The
> repo says so, and it must keep saying so: with no adapter there is no
> measurement, and "WPS is enabled in the configuration" is not "WPS PIN recovery
> works on this unit."

> ⚠️ **And a scope warning that is not about money.** Wireless attacks radiate.
> Deauthentication and beacon injection reach every device in range, not just the
> one on the bench, and that is a different consent situation from a cable
> between two ports. `P7-3`, `P7-6` and `P7-9` need a shielded setup or a
> genuinely isolated location before they are run at all — the register already
> cut three tests on exactly this ground.

### 2. An SPI flash programmer and a SOIC-8 clip — blocks 4 tests

`P9-5` (direct SPI dump), `P9-6` (direct SPI write), `P9-7` (JEDEC id),
`P9-11` (hold the chip in reset to force the boot loader).

| Option | Roughly | Notes |
|---|---|---|
| CH341A programmer + SOIC-8 test clip | US$8–15 | The usual pairing. **The common black CH341A boards drive 5 V on the data lines and this flash is 3.3 V** — either buy a modified board or add a level shifter. Many sellers now ship a fixed revision; check before powering anything |
| Raspberry Pi Pico + `flashrom` (`serprog`) | US$5 + wires | 3.3 V natively, no modification, and `flashrom` supports it. Slower, and one more thing to build |
| Segger/Dediprog | US$100+ | Correct and unnecessary at this scale |

**Recommended: Pico + `serprog`**, purely because the voltage problem cannot be
got wrong by accident, and this project has exactly one unit.

> **What the absence costs, and it is the interesting one.** The flash was read
> **through the boot loader's own `FLR` command** — the device's code, over the
> device's UART. That is one instrument. `P9-5` exists to read the same chip with
> a *second*, entirely independent one, and the repository's first evidence rule
> is that no claim rests on a single tool. Right now **every byte-level claim
> about this flash has one source.** The two dumps agreeing byte-for-byte is a
> strong internal check, but both came down the same path.
>
> `P9-7` is the cheap half of the same point: a JEDEC id read off the chip is a
> second source for the flash part number, which is currently a package marking
> read with a magnifier.

### 3. An EJTAG adapter — blocks 1 test

`P9-8`. A BusPirate or an FT2232-based probe with `OpenOCD`, US$25–60 — and the
board must expose usable EJTAG pads, which has not been established.

**Not recommended.** The boot loader console already gives memory read and write,
which is most of what EJTAG would add here, and the pads may not exist. This is
the one gap worth leaving open.

## The order to buy in, if any

1. **AR9271 adapter** (~US$30). Unblocks nine tests and an entire phase that is
   currently static-only. Best value by a wide margin.
2. **Pico + SOIC-8 clip** (~US$10). Unblocks four, and one of them repairs the
   single-source weakness in the project's strongest evidence chain.
3. **EJTAG** — no.

Total for the first two: **around US$40**.

## What still could not be done afterwards

Buying all of it does not make this repository reproducible by a stranger, and
that limit is structural rather than financial: **the build this unit runs is
published nowhere.** `REPRODUCE.md` states that on its first page. A reader with
the same hardware and the same instruments reproduces the *procedures* on *their*
bytes, and their build will differ.
