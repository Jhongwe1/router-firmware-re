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

### 2026-08-20: this section was written as if a Wi-Fi adapter were the only kind of radio

**It says "nine tests" and the number was two too high, because the gap was
described in terms of a product category instead of a capability.** On
2026-08-20 the eight remaining `P7` rows were cut on the strength of this
section, with the reasoning "the only radio on the workstation is an Intel
AX201, it is PCIe so `usbipd` cannot reach it, and `iwlwifi` has no injection".
Every clause of that is true and the conclusion did not follow. **There is an
ESP8266 on the same desk**, and two of the eight were runnable on it all along.

**The line that actually matters is management frames versus data frames**, and
writing it that way makes the inventory answerable by capability rather than by
shopping:

| capability | AR9271 | **ESP8266** | **ESP32** | AX201 (fitted) |
|---|---|---|---|---|
| transmit arbitrary **management** frames | ✅ | ✅ `wifi_send_pkt_freedom` | ✅ | ❌ no injection |
| receive **management** frames in full | ✅ | ✅ | ✅ | ✅ monitor mode |
| receive **data** frames in full (EAPOL) | ✅ | ❌ **802.11 header only** | ✅ | ✅ |
| act as a channel-MITM rogue AP | ✅ | ❌ | ~ | ❌ |
| reachable from WSL | ✅ USB | ✅ serial | ✅ serial | ❌ **PCIe** |

So, against the nine rows: `P7-3` and `P7-4` ride in beacons and are **ESP8266
work**. `P7-5` (PMKID) and `P7-6`'s capture half sit in EAPOL, which is a data
frame — **an ESP32 reaches them and an ESP8266 does not**, and an ESP32 is about
US$5. `P7-1`, `P7-2`, `P7-9`, `P7-10` still need the AR9271. `P7-7` needs no
radio at all and never did.

> **What the mistake costs, since that is this file's own column.** Two rows sat
> cut for part of one day on a reason that named a product rather than a
> requirement. The register's `cut_reason` mechanism is what made it cheap to
> reverse — the rows were still there, with a reason attached that could be
> argued with, rather than deleted. **A cut with a reason is reversible; a
> quietly dropped row is not.**
>
> And the buying advice changes: the first purchase is no longer the AR9271. It
> is an **ESP32** at about US$5, which unblocks two rows and makes a third
> half-possible, and the AR9271 becomes the second purchase rather than the
> first.

> ⚠️ **None of this touches the radiation half.** A beacon is a broadcast and an
> ESP8266 broadcasts exactly as far as an AR9271 does at the same power.
> `P7-3`'s second reason — that injection reaches every device in range —
> survives intact and has to be answered on its own.

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

> ✅ **Closed 2026-08-20, and not the recommended way.** The CH341A already on the
> desk was re-worked instead: the 5 V feed cut on the back of the board, 3.3 V
> jumpered into the pin it used to supply. It is verified at **two** points —
> all eight socket pins at 3.3 V, and pin 28, the CH341A's own I/O supply, at
> 3.3 V. `BENCH-LOG.md` `T-84`.
>
> **The recommendation above is left standing rather than rewritten**, because it
> was right about the risk and this outcome does not make it wrong. A Pico still
> cannot get the voltage wrong by accident; a CH341A still can, and this one took
> two attempts and four days to stop getting it wrong. What settled it was a
> measurement at two points, not the second attempt being more careful than the
> first.

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
