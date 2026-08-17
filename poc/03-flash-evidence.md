# PoC 03 — nine bytes on the SPI NOR, and which HTTP request put them there

The part of this week that is not a reproduction of somebody else's work.

## Scope

| | |
|---|---|
| verified on hardware | 2018-01-10 build, four 64 KiB flash reads through the boot loader across one session |
| verified in emulation | the byte offsets only — W05 measured `0x648a` / `0x648b` / `0x6493` under `qemu-user` before any of this ran on silicon |
| present statically, **not executed** | the same `sprintf`/`system()` line is byte-identical in V2.1.2 and V3.4.0 ([`submit-url-overflow.md`](../notes/submit-url-overflow.md)) |
| not tested at all | whether other `HW_*` MIB ids are reachable the same way |

## The claim

An unauthenticated HTTP request changed **nine specific bytes** of this device's
SPI NOR flash, and every one of them can be named.

```bash
curl -s -o /dev/null -X POST http://10.1.1.1/boafrm/formWsc \
  --data-urlencode 'localPin=13572468' --data 'submit-url=/wireless.htm'
```

That reaches `sprintf(buf[100], "flash set HW_WLAN0_WSC_PIN %s", localPin);`
followed by `system(buf)` — the line W04 root-caused, which carries two CVE
identifiers at once (CVE-2025-3987 for the injection, CVE-2025-4462 for the
overflow) and which is **identical in the 2015 image, ten years before either id
was assigned**.

No separator, no metacharacter. This is the *normal* path: the point is not that
a parameter can be injected — [`02`](02-command-injection.md) settles that — but
that a value chosen by an unauthenticated client reaches non-volatile storage.

The request takes **14.0 seconds**, the longest well-formed request measured on
this device.

## The evidence

Read before and after through the boot loader's `FLR` + `DB` over the serial
console — a path that shares no code with the web server, the kernel, or
Ethernet:

```text
region                     before             after              same
boot loader 0x0-0x6000     8d305a9afd226084   8d305a9afd226084   same
H601 0x6000-0x8000         6e2d3233d809ae4c   cf5af09374706898   DIFF
```

```text
0x00648a  71 -> 61      (cmp -l prints octal: 0x39 '9' -> 0x31 '1')
0x00648b  71 -> 63
0x00648c  71 -> 65
0x00648d  65 -> 67
0x00648e  66 -> 62
0x00648f  60 -> 64
0x006490  64 -> 66
0x006491  62 -> 70
0x006493  15 -> 25      <- the region's checksum, recomputed by the device
```

```text
before: 99956042
after : 13572468
```

Eight ASCII digits and a checksum byte. **The value that arrived over HTTP is
the value in the flash.**

## The correction this PoC exists to make

`plan/W06` drew this link as *"`flash set` writes `COMPCS`"* — the configuration
region at `0xC000`. **That is wrong.** `HW_WLAN0_*` ids live in the **hardware**
MIB, `H601`, at `0x6000`–`0x8000`, and the measurement above is inside it.

The evidence was already in this repository. W05's emulation run printed the
offsets `0x00648a`, `0x00648b` and `0x006493` and the note beside them said
*"`0x006493` is the H601 region's 8-bit checksum"* — the region was named on the
same line as the offsets. Nobody joined the two sentences, and this author fired
the first shot at the device without doing so either.

**That makes the finding worse, not better, and the difference matters:**

- `COMPCS` is configuration. It is rewritten by any handler, backed up, and
  restored by a factory reset.
- **`H601` holds this unit's MAC addresses and its radio calibration constants.**
  They were measured at manufacture. They exist nowhere else. A factory reset
  does not restore them, and no vendor image contains them.

So: **an unauthenticated HTTP POST writes into the one region of this device
that cannot be recovered from any source outside the device itself.** This
project spent a morning building a flash writer whose allow-list makes `H601`
unreachable by construction, with no flag to widen it — and then the device's
own `flash set`, driven by one unauthenticated request, wrote it anyway. The
guard protected the instrument, not the device.

## Reversal, which is half the claim

```text
H601, final read vs before the injection : 0 differing bytes
H601, final read vs the 2026-08-16 dump  : byte-identical
PIN as text, before: 99956042    after restore: 99956042
```

Restored with the device's own MIB writer — `flash set HW_WLAN0_WSC_PIN
99956042` through the same injection — so the checksum is recomputed by the code
that owns it rather than by hand. All nine bytes returned, checked against a
dump taken **before this project had ever written to the device**.

**Changed, pointed at, and reversed, all three on silicon.** The reversal is
what turns "it happened" into "it is repeatable, controlled and reversible" —
and a controlled experiment you cannot undo is an accident with a write-up.

## What this does not show

- **The defect is not novel.** Two 2025 CVEs name this line. What is this
  project's own is the evidence *route*: HTTP parameter → `system()` → the
  device's MIB writer → nine bytes on a flash chip, read back over a serial
  console, decoded into a named field.
- **The `H601` reachability has had no prior-art search of its own yet.** That it
  is worse than the configuration write is an argument, not a citation.
- One field was written. Whether other `HW_*` ids — the MAC addresses among them
  — are reachable the same way is **untested**, and it is the obvious next
  question rather than a claim made here.
