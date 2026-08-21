# What the boot loader serves over TFTP, and where from

Answers **open question 96** — *"What does the loader serve, and from where?"* —
carried since 2026-08-21, when `tools/loader-tftp.py` was written with the source
of its own `get` marked as an assumption.

**Measured on:** `$FWRE_WORK/stage2.bin`, 56,592 bytes, the LZMA second stage
decompressed out of flash `0x0012F0` (17,334 compressed) by
`tools/loader-unpack.py` from `dumps/flash-n150rt-console-2.bin`. Linked at
`0x80400000`, so file offset = address − `0x80400000`; its `.bss` begins at
`0x8040DD10`, the first address past the end of the image.

---

## The answer

The loader's TFTP **read** path is one function, `0x80401ED4`, and it computes
the source of every DATA block like this:

```
80401ee8  andi  s0,a1,0xffff        ; a1 = block number
80401eec  sll   v1,s0,0x9           ; block * 512
80401ef4  lw    v0,-11352(v0)       ; 0x8040D3A8  <- the TFTP load address
80401efc  addu  a1,v1,v0
80401f14  addiu a1,a1,-512          ; source = LOADADDR + (block-1)*512
80401f04  lw    v0,-8920(v0)        ; 0x8040DD28  <- the transfer length
80401f0c  addiu v0,v0,512
80401f10  bne   v1,v0,...           ; block*512 == length+512  -> 0-byte last block
80401f34  lw    v1,-8920(v0)        ; length again, for the short block size
80401f48  subu  s2,v1,a0
80401f4c  addiu s2,s2,512           ; short block = length - (block-1)*512
```

So it serves **`[0x8040D3A8]` for `[0x8040DD28]` bytes**, and those two globals
have different owners:

| global | what it is | written by |
|---|---|---|
| `0x8040D3A8` | the TFTP load address | its initialiser in `.data` (**`0x80500000`**, file offset `0xD3A8`); the `LOADADDR` command (`0x80409988`); the `boot.img` upload path (`0x80401258`, forced to `0x80000000`) |
| `0x8040DD28` | the transfer length | **`FLR`'s third argument** (`0x80409A04`); the completion of an upload (`0x80401AB8`); zeroed when a transfer is set up (`0x80401DDC`) |

**Therefore `get` is a fast path for `FLR`'s output only when `FLR`'s
destination happens to equal `LOADADDR`.** What `FLR` lends to TFTP is the
*length*, not the address. That is neither of the two answers open question 96
offered itself, and the experiment it proposed — two `FLR`s into a scratch
address, `get` between them, `cmp` the two files — returns `0` for a reason that
has nothing to do with its stated conclusion.

`.bss` begins at `0x8040DD10`, so `0x8040DD28` is uninitialised: **on a freshly
caught prompt with no `FLR` sent, a read request should return a 0-byte DATA
block.** `runsheet.md` `A2.7` turns all of this into four cells with a
precomputed hash each.

### And it explains `T-09`

2026-08-17 recorded a read request answered with 516 bytes — one full 512-byte
block — matching flash `0x060010` byte for byte, from a filename that exists
nowhere. With the code above, that says two things at once:

* the length global was non-zero, and the session had run a 64 KiB
  `console-dump.py dump` three minutes earlier, which is an `FLR`;
* **RAM at `0x80500000` held a copy of flash `0x060010`.** Nothing in that
  session put it there. The loader did — which means it stages the `cr6c`
  payload into RAM *before* it offers the ESC window, not after. The boot log's
  `+5.84 Jump to image start=0x80500000` is the jump, not the copy.

That last point is a prediction the bench can check in one command
(`DB 80500000 64`), and `A2.7` opens with it.

---

## The command table, recovered rather than transcribed

`?` prints 17 commands and the loader rejects `HELP`. The table behind it is at
`0x8040DBC0`, 17 entries of 16 bytes: `{name, help, argc, handler}`.

| # | name | argc | handler | help string |
|---|---|---|---|---|
| 0 | `?` | 0 | `0x80409A9C` | `HELP (?)  : Print this help message` |
| 1 | `DB` | 2 | `0x804095D0` | `DB <Address> <Len>` |
| 2 | `DW` | 2 | `0x804094B4` | `DW <Address> <Len>` |
| 3 | `EB` | 2 | `0x8040978C` | `EB <Address> <Value1> <Value2>...` |
| 4 | `EW` | 2 | `0x80409650` | `EW <Address> <Value1> <Value2>...` |
| 5 | `CMP` | 3 | `0x80409820` | `CMP: CMP <dst><src><length>` |
| 6 | `IPCONFIG` | 2 | `0x80409378` | `IPCONFIG:<TargetAddress>` |
| 7 | `AUTOBURN` | 1 | `0x80409914` | `AUTOBURN: 0/1` |
| 8 | `LOADADDR` | 1 | `0x8040996C` | `LOADADDR: <Load Address>` |
| 9 | `J` | 1 | `0x8040925C` | `J: Jump to <TargetAddress>` |
| 10 | `FLR` | 3 | `0x804099AC` | `FLR: FLR <dst><src><length>` |
| 11 | `FLW` | 4 | `0x80409B6C` | `FLW <dst_ROM_offset><src_RAM_addr><length_Byte> <SPI cnt#>` |
| 12–16 | `MDIOR` `MDIOW` `PHYR` `PHYW` `PORT1` | 0/0/2/3/3 | `0x80409C54` … `0x8040A294` | PHY and switch access |

Two things fall out of the table that the help text does not say:

* **`FLR`'s first argument is the destination.** The handler parses
  `argv[0]` → `s2`, `argv[1]` → `s1`, `argv[2]` → `s0`, all base 16, then prints
  `Flash read from %X to %X with %X bytes` with `s1` first. RUNBOOK §8.7.8 and
  four bench transcripts already said so; this is the third source, and it is
  the one that settles the argument order without a device.
* **`FLW`'s `argc` is 4**, and `runsheet.md` `A2.5`/`A2.6` send it three
  arguments. Those sections were run successfully on 2026-08-17, so `argc` is
  evidently not a hard requirement — but the disagreement is real and it is now
  `PROGRESS.md` open #98 rather than a surprise in the middle of the only
  irreversible section in the file.

---

## The write path, and the switch that decides whether it reaches flash

An upload's last block (`< 512` bytes) lands at `0x80401A68`, and the completion
block does five things: prints `**TFTP Client Upload File Size = %X Bytes at %X`
with the length and the load address, resets the write pointer, stores the total
into `0x8040DD28`, increments the source port at `0x8040DD20`, and then branches
on `0x8040D390`:

```
80401b08  bne   v1,v0,0x80401b9c    ; 0x8040D390 != 1 -> the autoburn path
80401b78  jal   0x80406728          ; == 1: flush, then
80401b8c  jalr  v0                  ;       jump to the load address
80401b9c  lw    v0,-11104(v0)       ; 0x8040D4A0  <- AUTOBURN
80401ba4  beqz  v0,0x80401bc0       ; 0 -> return. Nothing is written
80401bb8  jal   0x80401318          ; else: burn(load address, length)
```

**Autoburn is read exactly once in the whole image, here.** `P9-12`'s frozen
prediction — *"`AUTOBURN 0` + IPCONFIG + upload + `J` hands control to the
uploaded image and not one flash byte is written"* — now has an instruction-level
argument behind it and not only the loader's own usage text. Its refutation (a)
would require that `beqz` to be reading something other than what `AUTOBURN 0`
writes; `0x80409944` writes `0x8040D4A0` and `0x80401B9C` reads `0x8040D4A0`.

### Two filenames that take the decision away from the operator

The WRQ handler compares the requested filename against two constants before any
of that:

```
80401208  move  a0,s0               ; the filename from the request
80401210  jal   0x80406d7c          ; against "nfjrom"   (0x8040A6A0)
80401228  sw    v1,-11376(v0)       ; 0x8040D390 = 1
8040122c  addiu a0,s1,30
80401234  jal   0x80406c40          ; against "boot.img" (0x8040A6A8)
8040124c  sw    v1,-11376(v0)       ; 0x8040D390 = 1
80401250  lui   v1,0x8000
80401258  sw    v1,-11352(v0)       ; 0x8040D3A8 = 0x80000000
```

With `0x8040D390` set, the completion path above **jumps to the load address the
moment the transfer ends** — no `J`, nobody at the console.

**This is not a discovery, and saying so is the point.** `nfjrom` is Realtek's
own name for the MP image in the rtl819x SDK; there is an `nfjrom.script` in
Realtek bootcode trees published under the GPL by other vendors, and the
loader's TFTP recovery flow — including the `192.168.1.6` default this build
still carries at `0x8040EDC0` (`0x80401D1C`: `lui v0,0xc0a8; ori v0,v0,0x106`)
and the `0x80500000` load address — is documented on the OpenWrt wiki. The
register (`notes/prior-art.md`) had nothing on the boot loader, so the search
went outside it, and it came back full. What is specific to this build is the
address list above, and that is all this note claims.

It also does not describe a remote defect: the loader answers on the network
only after `IPCONFIG` has been typed at the console, so reaching it already
requires the UART. It is recorded because it changes how a **tool** should
behave — `loader-tftp.py put` now refuses a filename containing either name
unless `--allow-autoexec` is passed — and because a default filename is not
where the decision to execute an image should be lost.

---

## `J`, which is safer than it looked and more dangerous than it looked

`0x8040925C`, one argument, base 16:

```
80409264  blez  a0,0x80409290       ; argc <= 0 -> jump WITHOUT parsing anything
80409278  bnez  v0,0x80409290       ; parsed -> the jump path
80409280  jal   printf(" Invalid Address(HEX) value.")
80409290  printf("---Jump to address=%X")
804092a8  sw    zero,0xB8003000     ; stop the timer
804092b0  mfc0/ori/xori/mtc0 $12    ; interrupts off
804092d8  bne   v1,0xBFC00000 ...   ; target == 0xBFC00000 -> kick the watchdog and spin
804092f4  0xBB804104..0xBB804114 &= ~1   ; the five switch ports down
80409358  jal   0x80406728          ; cache maintenance
80409360  jalr  s0                  ; go
```

Three things follow, all of which change `runsheet.md` `A2.7`:

* **`J` prints `---Jump to address=%X` before it jumps.** `P9-12`'s frozen
  refutation says a silent console cannot distinguish "jumped and said nothing"
  from "never jumped". That line distinguishes them. It does not make the
  UART-writing payload unnecessary — the line proves the loader intended to
  jump, not that the target executed — but it splits the failure into two.
* **`J` calls `0x80406728` — the same routine the auto-execute path calls —
  before jumping.** So an image that arrived over TFTP into cached RAM is
  handled by the loader rather than by hope.
* **A bare `J` with no argument jumps to uninitialised stack.** `blez a0` skips
  the parse and `0x80409290` reads `sp+16` regardless. It is the only way to
  hurt the current state in the whole of `A2.7`.

And `J BFC00000` is a clean console reset: it kicks the watchdog at `0xB800311C`
and spins until it fires.

---

## What this is, and what it is not

* **One tool.** Everything above is `mips-linux-gnu-objdump` over one binary.
  Where a second source exists it is named: the `FLR` argument order against
  RUNBOOK §8.7.8's bench transcripts, the `0x80500000` load address against the
  `cr6c` header's `startAddr` and the boot log, port 2098 against `T-09`, the
  `nfjrom` mechanism against Realtek's published SDK.
* **The code reads as** described. Nothing here has been sent to the device.
  `runsheet.md` `A2.7` is the confirmation, and every cell of it carries a
  sha256 computed from `dumps/flash-n150rt-console-2.bin` before the visit —
  which means the reading can be **refuted**, not merely illustrated.
* **The scope of what a bench run would settle**: it would confirm the read
  path's source and length globals and the `LOADADDR` coupling. It would *not*
  confirm the burn routine's behaviour under `AUTOBURN 1` (nothing here sends
  it), nor the auto-execute filenames (deliberately avoided), nor what `FLW`'s
  fourth argument does.

---

## How the first version of this was wrong

**Version 1 is `runsheet.md` `A2.7` as it stood on 2026-08-21 and it was wrong
in four separate ways, three of which would have stopped the section before any
byte moved and the fourth of which would have published a false conclusion.**

1. It hand-wrote `FLR 300000 81000000 1000` — `FLW`'s argument order, not
   `FLR`'s. The loader would have been asked to read flash `0x81000000` into
   `0x00300000`, an unmapped KUSEG address.
2. It sent that through `console-dump.py cmd`, which has no handling for
   `(Y)es , (N)o ?`. The `FLR` would never have executed, and the pending prompt
   would have eaten whatever command came next.
3. It omitted `--at-prompt`, so with the board already at `<RealTek>` the tool
   would have streamed ESC for 120 seconds and then reported *"nothing came back
   at all. TX/RX swapped, wrong port, or the board never powered on"* — three
   causes, none of them the real one.
4. Its truth table had two outcomes: *two files differ → the loader serves RAM
   at the load address; identical → it has a fixed source of its own.* Both
   `FLR`s targeted a scratch address that is not the load address, so the files
   would have been identical **and the section would have concluded the second
   thing.** A correctly executed comparison, mapped to the wrong answer.

The common cause of (1) and (4) is the same one that produced the
"loader is a TFTP client" reversal four hours earlier and is written up in
RUNBOOK §8.12.45: **a command re-stated by hand in a file that does not own it.**
`tools/console-dump.py`'s `flr()` owns the argument order. `A2.7` no longer
contains a hand-typed `FLR` at all.

A fifth: the section named `$HOME/fwre-work/w08-ramboot.bin` as the image `put`
would send, and **nothing in the repository created that file**. `P9-12` cannot
be closed by uploading an arbitrary file — its own refutation condition says so —
so the image had to be built, which is `tools/mkramboot.py`.
