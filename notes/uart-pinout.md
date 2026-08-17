# UART — pinout, baud, and what the console will and will not do

Answers the first half of G2: the serial console is located, measured and read.

```
        ┌─────────────────────────────┐
        │  ▽  1     2     3     4      │   ▽ = triangle on the silkscreen
        │  ┌──┐ ┌──┐ ┌──┐ ┌──┐         │       marking pin 1
        │  │██│ │██│ │██│ │██│         │
        └──┴──┴─┴──┴─┴──┴─┴──┴─────────┘
           VCC   TX    RX   GND
          3.3V  out    in   0V
         DO NOT  →     ←
         CONNECT
```

| Pin | Function | Unpowered, Ω to GND | Powered, V to GND | Confidence |
|---|---|---|---|---|
| 1 | **VCC 3.3 V** | 181 Ω | **3.3 V** steady | two sources |
| 2 | **TX** (board → you) | 18 kΩ | 0–3.3 V, moving | two sources |
| 3 | **RX** (you → board) | 15 kΩ | 0 V | **two sources** — driven 2026-08-16 |
| 4 | **GND** | **0.2 Ω** | **0.000 V** | two sources |

**38400 8N1.** Header is a populated 4-pin 2.54 mm strip at the board's bottom
edge, silkscreened `UART`. **No soldering was required anywhere in W02.**

---

## 1. How each pin was settled

The board has **no shield can and plastic RJ45 housings**, so the usual
"probe the chassis or the RJ45 metal frame" route for finding ground does not
exist here. Ground came from two parts that are always ground on this class of
board, cross-checked against each other:

- the **DC barrel jack's outer sleeve**, and
- the **negative (striped) lead of the bulk input electrolytic**.

Continuity between those two established the reference. The black probe then
stayed clipped there while the red probe swept the header.

**Unpowered, resistance.** Three clearly separated magnitudes, which is what
makes the reading safe: `0.2 Ω` (the ground plane itself) · `181 Ω` (a 3.3 V rail
loaded with decoupling capacitance and the SoC's supply pins) · `15–18 kΩ`
(signal pins behind pull resistors).

> ⚠️ **The 3.3 V rail reads *low*, not open.** A few hundred ohms to ground is
> normal for a powered-down supply rail and it is the single easiest reading to
> mistake for a ground.

**Powered, voltage.** `pin 4 = 0.000 V` and `pin 1 = 3.3 V steady` gave each of
those pins a second, independent source. `pin 1` also settles the logic level:
**3.3 V, not 1.8 V and not 5 V**, which is what a USB-TTL adapter has to match.

**pin 2 = TX** was visible on a meter as a value moving between 0 and 3.3 V —
a multimeter sampling two or three times a second showing the *average* of a line
that is actually transmitting. That is suggestive, not conclusive; the logic
analyser settled it.

---

## 2. Baud measured, not guessed

Narrowest pulse on pin 2: **26 µs**. `1 / 26 µs = 38.46 kHz`; standard 38400
has a bit time of 26.042 µs, so the reading is 0.16 % off.

**The self-consistency check is what makes it a measurement rather than a
guess:** a second pulse in the same capture measures **52 µs, exactly 2 × 26**.
If 26 µs were two bit-times rather than one, there would have to be a 13 µs pulse
somewhere, and there cannot be half a bit.

That check is not academic. **The nearest wrong answer is 19200, whose bit time
is 52.08 µs** — pick the 52 µs pulse as the unit and you get 19200, set the
decoder to it, and spend the evening looking at garbage.

Confirmed a third time by the decoder itself: at 38400 the capture decodes to
readable ASCII. Wrong parameters give noise, and there is no middle ground.

Both steps are photographed rather than asserted:
[`img/10-pulse-width-26us-52us.png`](img/10-pulse-width-26us-52us.png) is the capture
with both pulses measured, and
[`img/11-async-serial-decode.png`](img/11-async-serial-decode.png) is the same wire
decoded by the analyser's own Async Serial decoder — the second, independent read of
the boot log.

---

## 3. The console does not give you a shell

After boot completes, sending `\r` produces **echo and nothing else**:

```
sent : \r \r \r\n  echo MARKER_1234\r
back : CR LF ×4 then "echo MARKER_1234" CR LF
```

Every character comes back, CR is translated to CR+LF — that is the Linux tty
line discipline echoing. But **the command never runs and no prompt is printed**.

**Reading: the kernel has the console open, and nothing is reading it.** No getty,
no shell. The boot log agrees — there is no BusyBox
`Please press Enter to activate this console` anywhere in it.

> This is worth being precise about, because "the console echoes" feels like
> success. It is not. Echo comes from the tty layer whether or not a process is
> listening.

## 4. The boot loader console *is* interactive

Hold **ESC** streaming across power-on and the boot takes a different path:

```
---RealTek(RTL8196E)at 2014.04.22-16:22+0800 v1.3 [16bit](400MHz)
P0phymode=01, embedded phy
---Ethernet init Okay!
<RealTek>
```

It initialises Ethernet for TFTP recovery instead of jumping to the kernel.
The interrupt window is about a second wide and opens immediately at power-on,
so ESC has to already be streaming before the board comes up — pressing it after
you see output is too late.

Command set, from `?` (**not** `HELP`, which the help text itself lists and which
returns `Unknown command !`):

| | |
|---|---|
| `DB <addr> <len>` / `DW` | display memory, byte / word |
| `FLR <dst_ram> <src_flash> <len>` | **flash → RAM** |
| `CMP <dst> <src> <len>` | compare |
| `J <addr>` | jump |
| `IPCONFIG` · `LOADADDR` | TFTP recovery |
| `MDIOR` · `MDIOW` · `PHYR` · `PHYW` | PHY registers |
| ⚠️ `EB <addr> <v1> <v2>…` · `EW` | **write memory.** Several values in one command: **measured 2026-08-17**, eight bytes accepted |
| ⚠️ `FLW <dst_flash> <src_ram> <len> [SPI#]` | **write flash. Executed 2026-08-17** — see below |
| ⚠️ `AUTOBURN 0/1` | |

> ### `FLW`, executed 2026-08-17
>
> Write → read back → erase, at `0x3F0000` (erased in the whole tail from
> `0x350000`, so nothing reads it). Verbatim transcript in
> [`RUNBOOK.md` §8.9.1](../RUNBOOK.md); it closed G3.5's fifth box.
>
> **Three things the command set alone does not tell you:**
>
> 1. **`FLW` answers with a single `.`**, not a success message. What it *does*
>    print first is `Write 0x00000008 Bytes to SPI flash#1, offset
>    0x003f0000<0xbd3f0000>, from RAM 0x80530000 to 0x80530008` — so **the SPI
>    flash is memory-mapped at `0xbd000000`** (KSEG1, uncached), which is not
>    recorded anywhere else in this repository.
> 2. **`FLW`'s confirmation prompt is `(Y)es, (N)o->`**, while `FLR`'s is
>    `(Y)es , (N)o ? -->`. Two adjacent commands, two punctuations — the same
>    shape of trap as the two radices below.
> 3. **There is no erase command in the set at all**, and writing `FF`s over a
>    written region *does* return it to `FF`. On NOR flash a program can only
>    clear bits, so `FLW` must be erasing for itself — which points at a
>    read-modify-erase-program cycle over the whole 4 KiB sector. Not settled;
>    `PROGRESS.md` open #17 and [`RUNBOOK.md` §8.9.3](../RUNBOOK.md) have the one
>    command triple that decides it.

**`FLR` + `DB` is a complete flash read path that needs no SOIC-8 clip** — the
plan listed this only as a Day 6 "if both worked" bonus. See
[`flash-layout.md`](flash-layout.md) for what it produced.

`FLR` asks `(Y)es , (N)o ?` and **eats the next line as the answer**, so a script
that sends the next command instead of `Y` gets `Abort!` and then a spurious
`Unknown command !`.

> ### The radix trap
>
> **`FLR` takes hex for both the addresses and the length. `DB` takes a hex
> address and a *decimal* length.** `DB <addr> 100` returns 100 bytes, not 0x100.
>
> Two radices in one command set, on adjacent commands, in a tool whose whole job
> is copying bytes from one place to another. Nothing warns you — you get a
> plausible dump of the wrong size.

### 4.1 What `DB` actually prints

Captured from the device on 2026-08-16, in full, because the shortened version
of this transcript caused a bug — see below:

```
DB 80500000 64
 [Addr]   .0 .1 .2 .3 .4 .5 .6 .7 .8 .9 .A .B .C .D .E .F
80500000: 00 00 00 00 00 00 80 21 40 90 60 00 00 00 00 00     .......!@.`.....
80500010: 00 00 00 00 00 00 00 00 3c 10 80 5f 26 10 10 00     ........<.._&...
<RealTek>
```

A column header, then `AAAAAAAA:` followed by 16 space-separated bytes, **then
at least two spaces and a 16-character ASCII column**. 81 characters carry 16
bytes of payload — a **5.06× expansion**, which is what sets the read rate:
38400 8N1 delivers 3840 B/s, so the payload ceiling is ~759 B/s and a 4 MiB read
takes about 95 minutes. Measured rate: **723 B/s**. The line is saturated; the
host is not the bottleneck and no amount of tuning on this side will help.
(`DW` prints 4-byte words and would cost ~19 % fewer characters. Not used here —
it needs its own parser and its own guard cases, and correctness came first.)

> ### The interrupt technique poisons the next command
>
> Catching the boot loader means **streaming** ESC across power-on, because the
> window is about a second wide. The loader consumes one ESC to break out of the
> boot — **and the rest stay queued in its input buffer.** The first command you
> send afterwards therefore arrives with a pile of ESCs in front of it and comes
> back `Unknown command !`.
>
> This was found on 2026-08-16 the confusing way round: `?` returned
> `Unknown command !`, contradicting the 2026-08-15 session where `?` printed
> the whole command set. Two sessions disagreeing about one device is the
> instrument talking. **Send a bare `\r` and read to the prompt before issuing
> anything real** — [`tools/console-dump.py`](../tools/console-dump.py) does this
> in `settle()`.
>
> It matters more than it looks: the first command of an automated dump is the
> positive control, and a control that silently does not run is worse than no
> control at all.

---

## 5. What is still not established

- ~~**pin 3 = RX is inferred, not measured.**~~ → **answered 2026-08-16.** It was
  identified by elimination — pins 1, 2 and 4 were settled, it is a 4-pin header
  silkscreened `UART`, and nothing else was left for pin 3 to be. That is an
  argument, not a measurement. It became a measurement when ESC streamed into
  pin 3 interrupted the boot and `FLR`/`DB` commands sent into it were executed:
  **the pin accepted input and the board acted on it.** Elimination said what it
  could not be; the flash dump is what proves what it is.
- Whether the absent console shell is a build option or an `inittab` choice.
  Answering it needs the rootfs off the flash.

---

## How the first version of this note was wrong

The procedure this note replaces came from the project plan, and **three of its
steps do not survive contact with this board**:

1. **"Find GND: touch one probe to the chassis or the RJ45 metal frame."**
   There is no shield can and the RJ45 housings are plastic. The step as written
   is impossible here, and it fails *silently* — you get no beep and conclude
   there is no ground on the header.
2. **"Solder a 2.54 mm header, GND first to tack it."** The header is already
   populated, so the step is moot — but the advice is also backwards. GND is tied
   to the ground plane and is the *hardest* of the four pins to heat; using it as
   the tacking pin means fighting the biggest thermal load while the part is still
   loose.
3. **"Guess TX/RX: the one that jumps at power-on is TX."** A multimeter samples
   two or three times a second and the burst lasts a couple of seconds; it can
   miss entirely, and RX often sits at 3.3 V too. It happened to work here. That
   is luck, not method, and the analyser is what actually decided it.

And one mistake that was mine, not the plan's: the first powered sweep was taken
on the meter's **200 mV** range while looking for 3.3 V — 16× over range. What it
returned was not an over-range indication but a plausible-looking `0.x` that
drifted, which is exactly the shape of a real reading. **The fix was not a better
probe technique; it was measuring a battery first** — a known quantity, to prove
the instrument before trusting it on an unknown one.

**And one this note caused elsewhere, added 2026-08-16.** Section 4 listed the
command set but never recorded what `DB` *prints*, and the transcripts quoted in
[`flash-layout.md`](flash-layout.md) had their ASCII column trimmed to fit the
page. An automated dumper was then written from those quotes, its line parser
had no ASCII column in it, and it rejected **every** line the device produced —
dying on its own positive control with "no data lines at all".

**The uncomfortable part: the raw format was already in this repository.**
`RUNBOOK.md` §8.7.8 carries a verbatim `DB` transcript, ASCII column and all,
written the day the console first came up. Nothing was lost — the wrong document
was read. The notes are analysis, and their quotes are edited for a human
reader; the RUNBOOK is the operational record, and its transcripts are verbatim.
**Confusing the two is how a summary gets used as a specification.** §4.1 above
now carries the format here too, so the operational fact lives in both places.

The same rule this project already applies to decompiler output and to
`flashrom`'s chip database applies to its own notes: *second-hand is not a
source.*

Worse, the guard suite for that parser was written from the same quotes. It
passed 10/10 against a format the device does not emit. **A test that shares an
assumption with the code it tests is not a second source; it is the same source
twice** — which is the identical failure the sink census hit in W03 and the
argument tracer hit in W04, arriving this time through documentation rather
than through code.
