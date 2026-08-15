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
| 3 | RX (you → board) | 15 kΩ | 0 V | **inferred** — see below |
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
| ⚠️ `EB` · `EW` | **write memory** |
| ⚠️ `FLW <dst_flash> <src_ram> <len>` | **write flash** |
| ⚠️ `AUTOBURN 0/1` | |

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

---

## 5. What is still not established

- **pin 3 = RX is inferred, not measured.** Pins 1, 2 and 4 are identified, it is
  a 4-pin header labelled `UART`, and nothing else is left for pin 3 to be. It
  reads 15 kΩ to ground and 0 V when powered, which is consistent with an input
  behind a pull-down. It has never been driven and confirmed.
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
