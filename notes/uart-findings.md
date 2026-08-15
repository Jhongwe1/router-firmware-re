# What the boot log says — and the build nobody had

Answers W01/W04 open question #1, which has been carried since day one:
**which firmware build is on my unit.**

> **Neither of the two this project has analysed.** The unit runs a **third
> build, from 2018-01-10** — between the 2015 image and the 2020 one, and
> structurally on the 2015 side.

Captured at 38400 8N1 over the console described in
[`uart-pinout.md`](uart-pinout.md), and independently a second time by decoding
the same line with a logic analyser. **The two transcripts are byte-identical.**

---

## 1. The build: four timestamps, one date

| Component | Built |
|---|---|
| BusyBox v1.13.4 | `2018-01-10 14:56:45 CST` |
| WiFi Simple Config v2.18-wps1.0 | `2018.01.10-06:58+0000` |
| MiniIGD v1.09.1 | `2018.01.10-06:58+0000` |
| **`boa` 0.94.14rc21** | **`Jan 10 2018 at 14:57:54`** |

Four binaries, one coherent build. Against the two images on file:

| | BusyBox built | Image dated |
|---|---|---|
| V2.1.2 | 2015-08-11 | 2015-08-25 |
| **this unit** | **2018-01-10** | **—** |
| V3.4.0 | 2020-10-30 09:55 | 2020-10-30 |

**The obvious objection was tested before the conclusion was drawn.** "Maybe
V3.4.0 just ships an old BusyBox" would make the timestamp meaningless — so both
images were checked. V3.4.0's BusyBox is stamped *the same day as its release*,
and V2.1.2's is 14 days before its own. **This vendor rebuilds userland at
release, so the timestamp tracks the build date to within about two weeks.**
The objection is dead and 2018-01-10 stands.

### Why this is the most consequential line in the log

`boa: server built Jan 10 2018` is `/bin/boa` — **the binary this project has
been reverse engineering since W03.**

W03 and W04 read the 2015 and 2020 copies. **The copy on this unit is neither.**
So every finding stated about `boa` — the `strstr(uri, "htm")` authorisation gate,
the 59-entry `root_form[]`, `lastUrl[100]`, the `submit-url` idiom across 34
handlers, the three unanchored `strstr` calls in the 2020 rewrite — **is a claim
about V2.1.2 and V3.4.0, and says nothing yet about the binary actually running
on this desk.**

Those findings are not wrong; the repository has always named its images. But
they do not cover this unit, and **anything demonstrated dynamically against this
hardware in W05/W06 is a test of a third binary.**

That makes the flash dump worth more than a gate checkbox: it is the only way to
get this `boa` into Ghidra and read three builds across instead of two.

---

## 2. Silicon confirmed — and one source that disagrees

```
---RealTek(RTL8196E)at 2014.04.22-16:22+0800 v1.3 [16bit](400MHz)
ramSize: 32M
```

| Claim | Sources |
|---|---|
| **SoC is RTL8196E** | package marking · boot-ROM banner · **the boot code's own ID compare** (below) |
| **RAM is 32 MiB** | package marking (W9825G6KH, 256 Mbit) · `ramSize: 32M` |

The RAM answer also resolves something [`hardware-inspection.md`](hardware-inspection.md)
deliberately left open: *fitted* is not automatically *usable*, so both were to be
recorded separately. Here they agree, and the plan's "16MB" is wrong twice over.

`[16bit]` is the SDRAM bus width, consistent with the W9825G6KH being a ×16 part.

### The third source is the strongest one

The first 64 bytes of flash — read out through the boot loader, see
[`flash-layout.md`](flash-layout.md) — disassemble to:

```
3c 01 b8 00    lui  at, 0xb800      ; Realtek register space
00 01 78 25    or   t7, zero, at
8d ee 00 00    lw   t6, 0(t7)       ; read the chip ID register
3c 01 81 96    lui  at, 0x8196      ; build the constant 0x8196E000
34 21 e0 00    ori  at, at, 0xe000
15 cf 00 0a    bne  t6, t7, ...     ; and compare
```

**The `RTL8196E` in the banner is not a compile-time string. It is derived from a
register read compared against `0x8196E000`.** That is the silicon identifying
itself, which outranks both the ink on the package and any driver's opinion.

### `chip name: 8196C` — and why it loses

```
Probing RTL8186 10/100 NIC-kenel stack size order[3]...
chip name: 8196C, chip revid: 0
```

Three sources say **E**; the Linux Ethernet driver says **C**.

**The driver disqualifies itself two lines earlier.** It announces that it is
probing an **RTL8186** — a whole generation older than either candidate. This
driver prints the name of its own code lineage, not the part it is running on,
and it does so consistently. Its strings are not evidence about this chip.

The resolution is not a majority vote. It is that the dissenting source is
demonstrably naming something else in the same breath.

### One line still unexplained

```
chipName: UNKNOWN
```

Printed in the hardware-detection block immediately before `ramSize`. The most
likely reading is **the SPI flash**: the boot ROM's flash ID table does not
contain the EN25QH32B, so it falls back to generic SPI commands and boots anyway.
If that is right it may also explain the published "2 MB" specification — an
earlier part, and a table never updated.

**Not confirmed.** `chipName` has not been traced to a source, and this note is
not going to assert which chip it failed to identify.

---

## 3. What the box actually runs

```
init started: BusyBox v1.13.4 (2018-01-10 14:56:45 CST)
sysconf init gw all
WiFi Simple Config v2.18-wps1.0
IEEE 802.11f (IAPP) using interface br0 (v1.8)
wan_disconnect: StartDnsSpoof
MiniIGD v1.09.1
boa: starting server pid=350, port 80
```

| Observation | Why it matters here |
|---|---|
| `sysconf init gw all` | W04 identified `/bin/sysconf` as the thing that writes `/var/passwd` from `passwd.org` at boot. **It runs on this unit.** |
| `WiFi Simple Config` | WPS is live — the surface behind W04's `HW_WLAN0_WSC_PIN` line |
| `MiniIGD` | UPnP IGD, listening. Not yet examined anywhere in this project |
| `wan_disconnect: StartDnsSpoof` | DNS redirection on WAN loss. Not seen in either analysed image's notes; unexamined |
| `bind: Address already in use` | something lost a port race at boot. Unexplained |
| `boa ... port 80`, and W01 established it runs as root | the web attack surface is up |

Five Ethernet ports, matching the three magnetics counted on the board:
`eth1` on VLAN 8 (WAN, aliased `peth0`), `eth0/2/3/4` on VLAN 9 (LAN).

**No boot loop.** `Booting...` appears exactly once in a 90-second capture, which
closes the question raised by an unstable reading across the bulk input capacitor
— that was probe contact, not a collapsing rail.

---

## 4. Handling

This particular log contains **no MAC address and no WPS PIN**, which is luckier
than it should be — the expectation going in was that it would. The raw capture
stays in `$FWRE_WORK/dumps` under the rule in [`dumps/README.md`](../dumps/README.md);
its hash is in `dumps/MANIFEST.json` and the substantive content is quoted here.

---

## How the first version of this note was wrong

There was no first version — there was a **prediction**, written in
[`hardware-inspection.md`](hardware-inspection.md#6-date-codes--a-prediction-written-before-the-dump)
before any of this was measured:

> The firmware resident on this unit is neither V2.1.2 nor V3.4.0, but a build
> from around 2018. Two ways this can be wrong: a previous owner updated it, or
> the production line flashed an image months older than the board.

**It holds** — and the second failure mode is what actually happened. The board's
newest date code is 2018 week 37 (September); the firmware is 2018-01-10. The
line flashed an image **eight months old**, exactly the lag that was written down
as a way the prediction could mislead.

The part that was wrong was narrower and worth keeping: the prediction was framed
as *which of the known images is closest*. It is not close to either. The unit
runs a build that **no copy of exists anywhere in this project**, and until the
flash is dumped, the most-analysed binary in the repository is one this device has
never run.
