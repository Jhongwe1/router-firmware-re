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
`0x8040DBC0`, 17 entries of 16 bytes:

```c
typedef struct {            /* offsets measured, not assumed -- see below */
    const char *cmd;        /* +0  */
    int         n_arg;      /* +4  */
    int       (*func)(int argc, char *argv[]);   /* +8  */
    const char *msg;        /* +12 */
} COMMAND_TABLE;
```

**Version 1 of this note wrote `{name, help, argc, handler}` and that is wrong**
— it is `{name, argc, handler, help}`. The values in the table below were right;
the sentence describing the record was not, and nothing in the repository could
have caught it because the table had been transcribed by hand. It is decoded now:
`tools/loader-unpack.py --commands`, which derives the field order from the shape
of the four columns and refuses when it cannot narrow the layout to one.

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
| 11 | `FLW` | 4 | `0x80409B6C` | `FLW <dst_ROM_offset><src_RAM_addr><length_Byte> <SPI cnt#>: Write offset-data to SPI from RAM` |
| 12–16 | `MDIOR` `MDIOW` `PHYR` `PHYW` `PORT1` | 0/0/2/3/3 | `0x80409C54` … `0x8040A294` | PHY and switch access |

Version 1 of this note truncated `FLW`'s help string at `<SPI cnt#>`. The tail
`: Write offset-data to SPI from RAM` is in the binary and it names the field.

Two things fall out of the table that the help text does not say:

* **`FLR`'s first argument is the destination.** The handler parses
  `argv[0]` → `s2`, `argv[1]` → `s1`, `argv[2]` → `s0`, all base 16, then prints
  `Flash read from %X to %X with %X bytes` with `s1` first. RUNBOOK §8.7.8 and
  four bench transcripts already said so; this is the third source, and it is
  the one that settles the argument order without a device.
* **The `n_arg` column is dead.** Exactly two instructions in the whole image
  build the address of this table — `0x80409170` (the dispatcher) and
  `0x80409AC4` (the `?` printer) — and between them they load offsets 0, 8 and
  12. **Nothing loads offset 4.** So the count each row declares is documentation
  and the dispatcher hands the handler whatever the operator typed:
  `0x804091FC` computes `argc = tokens - 1` and `0x8040923C` passes `argv + 1`,
  with no comparison against the row.

---

## `FLW`'s fourth argument, which the handler does not read

**Open #98, answered.** `argc = 4` in the table, `<SPI cnt#>` in the help, and
the handler at `0x80409B6C` parses `argv[0]`, `argv[1]`, `argv[2]` and stops:

```
80409b8c  jal   strtoul(argv[0],0,16)   -> s2   dst_ROM_offset
80409ba0  jal   strtoul(argv[1],0,16)   -> s1   src_RAM_addr
80409bb4  jal   strtoul(argv[2],0,16)   -> s0   length
80409be4  li    a2,1                    ; the %d in "SPI flash#%d" -- a CONSTANT
80409be8  jal   printf(0x8040B50C, s0, 1, s2, 0xBD000000+s2, s1, s1+s0)
80409bfc  jal   0x80409B18              ; (Y)es, (N)o->
80409c0c  jal   0x80404E20              ; spi init, chip 0
80409c14  move  a0,zero                 ; the chip index -- also a CONSTANT
80409c20  jal   0x80404FE4              ; write(chip=0, dst, src, len)
```

`0x80404FE4` is a per-chip dispatcher: `a0 * 72` indexes a descriptor array at
`0x8040FBD4` and calls its `+0x38` method, so the loader really can address more
than one SPI chip — and its own auto-burn path does, at `0x80401848`
(`li a0,1`) with `a1 = 0`, which is how an image that overruns chip 0 gets its
tail written to the start of chip 1. **The interactive `FLW` is the one path
that cannot reach it.** The printed `#1` and the passed `0` differ by one and
are both literals; the vendor source explains why (below).

**So `A2.5`/`A2.6` sending three arguments is not a shortcut that happens to
work. Three is the only form there is**, and a fourth token is tokenised, stored
and never loaded.

The hazard in that section is the opposite of the one #98 was worried about:
**`FLW` never checks `argc`.** Six of the seventeen handlers dereference `argv`
with no test of the count they were handed — `AUTOBURN`, `LOADADDR`, `FLR`,
`FLW`, `PHYR`, `PHYW` — and the tokeniser at `0x80407248` `memset`s its 20-slot
array to zero on every line. `FLW` with two arguments therefore reaches
`strtoul(NULL, …)`, which dereferences at `0x80406F08`. That happens **before**
the `(Y)es, (N)o->` prompt, so it cannot corrupt flash; it costs a power cycle.

### The second source, and what it settles

`rtl819x/bootcode/boot/monitor/monitor.c` in a published GPL drop
(`jameshilliard/WECB-VZ-GPL`) carries the same table and the same handler. It is
a **later SDK for a different SoC**, so it is corroboration of *why*, never a
substitute for this unit's own binary — but it explains every constant above:

```c
int CmdSFlw(int argc, char* argv[])
{
    unsigned int cnt2=0;//strtoul((const char*)(argv[3]), (char **)NULL, 16);
    ...
    printf("Write 0x%x Bytes to SPI flash#%d, offset 0x%x<0x%x>, ...",
           length, cnt2+1, ...);
    ...
    spi_flw_image(cnt2, dst_flash_addr_offset, (unsigned char*)src_RAM_addr, length);
}
```

**The line that would read `argv[3]` is commented out in the vendor's own
source.** `cnt2` is a hard `0`; `cnt2+1` is the `1` the console prints. And the
dispatcher's missing count check is `#if 0`'d in the same file:

```c
#if 0
    if (MainCmdTable[i].n_arg != (argc - 1))
        printf("%s\n", MainCmdTable[i].msg);
    else
#endif
    retval = MainCmdTable[i].func( argc - 1 , argv+1 );
```

Two further details of this binary match that file line for line and were not
looked for until after the disassembly said them: the four `sb zero` at
`0x80409248`–`0x80409258` are `memset(argv[0],0,sizeof(argv[0]))` — a
`sizeof(char*)` the vendor's own Coverity annotation flags as wrong — and
`COMMAND_TABLE` in `boot/include/monitor.h` is `{cmd, n_arg, func, msg}`, the
field order this note got backwards.

`SWB`'s help string in the same table is what names the units:
`SWB <SPI cnt#> (<0>=1st_chip,<1>=2nd_chip)`.

### What every handler reads, measured rather than transcribed

`python3 tools/loader-unpack.py <dump> --commands`. `says` is the table's
`n_arg`; `reads` is the constant `argv` displacements the handler loads, with
`+k+n` for an index computed at run time.

| | says | reads | checks argc |
|---|---|---|---|
| `?` | 0 | — | no (argv still live at a call; not followed) |
| `DB` `DW` | 2 | 0,1 | yes |
| `EB` `EW` | 2 | 0, then 1+n | yes — the count bounds the loop |
| `CMP` | 3 | 0,1,2 | yes |
| `IPCONFIG` | 2 | 0 | yes |
| `AUTOBURN` `LOADADDR` | 1 | 0 | **no** |
| `J` | 1 | 0 | yes |
| `FLR` | 3 | 0,1,2 | **no** |
| **`FLW`** | **4** | **0,1,2** | **no** |
| `MDIOR` | 0 | 0 | yes |
| `MDIOW` | 0 | 0,1,2 | yes |
| `PHYR` | 2 | 0,1 | **no** |
| `PHYW` | 3 | 0,1,2 | **no** |
| `PORT1` | 3 | — | no (argv still live at a call; not followed) |

Five rows disagree with their own declared count — `IPCONFIG`, `FLW`, `MDIOR`,
`MDIOW`, `PORT1` — which is what a field nobody reads looks like after a few
years of edits.

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
804092a8  sw    zero,0xB8003000     ; GIMR0 := 0 -- mask every interrupt
804092b0  mfc0/ori/xori/mtc0 $12    ; and clear IE in CP0 status
804092d8  bne   v1,0xBFC00000 ...   ; target == 0xBFC00000 -> kick the watchdog and spin
804092f4  0xBB804104..0xBB804114 &= ~1   ; PCRP0..PCRP4 &= ~EnablePHYIf
80409358  jal   0x80406728          ; cache maintenance
80409360  jalr  s0                  ; go -- and note it is jalr, not jr
```

Version 1 of this note called `0xB8003000` "stop the timer". It is the global
interrupt mask: the vendor source writes `outl(0, GIMR0); // mask all interrupt`
at exactly that point, and the `mtc0` on the next line is the second half of the
same `cli()`, not a separate action.

`0xBB804104`–`0xBB804114` are `PCRP0`–`PCRP4`, the five per-port configuration
registers (`SWCORE_BASE + 0x4100 + 4*(port+1)`), and the bit cleared is
`EnablePHYIf = (1<<0)`. The vendor's comment says what it is for: *"disable PHY
to prevent from ethernet disturb Linux kernel booting"*. **What that is not yet
is an attribution.** `J` masks interrupts, clears `IE`, disables the PHY
interfaces and replaces the running program, and any one of those alone would
end a TFTP transfer — so "the network is dead after `J`" does not name a cause.
`P9-15` separates them by clearing and restoring those five bits **without
jumping**, with interrupts left alone.

Four things follow, all of which change `runsheet.md` `A2.7`:

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
  hurt the current state in the whole of `A2.7`. The vendor source has the same
  hole and an `#ifdef AEI_COVERITY_FIX` that plugs it; this build does not
  define it.
* **`J` is a call, not a jump.** `0x80409360` is `jalr s0`, so `ra` is
  `0x80409368`, where the handler restores `ra` and `s0` and returns into the
  dispatcher loop. **A payload that ends in `jr ra` comes back to the
  `<RealTek>` prompt with no power cycle** — which `runsheet.md` Part B
  `B-W08 進站實錄` denies in as many words ("`J` 之後沒有軟體的路回去"), because
  `P9-12`'s payload looped forever and the only observed way back was the power
  switch. Reading the instruction is not the same as coming back from one, so
  this is `P9-16` rather than a correction: an eight-byte `jr ra; nop` payload
  settles it in one command, and it matters because `P9-10`'s implant work is
  a sequence of RAM payloads.

And `J BFC00000` is a clean console reset: it kicks the watchdog at `0xB800311C`
and spins until it fires.

---

## What this is, and what it is not

* **Version 1 was one tool** — `mips-linux-gnu-objdump` over one binary — and
  said so. The command table half now has three readers that do not share code:
  objdump, `tools/loader-unpack.py --commands` (its own MIPS decoder, no
  objdump), and the vendor's C. Where the three disagreed, the binary won and
  the note was wrong twice; both are recorded above rather than edited away.
  Other second sources, unchanged: the `FLR` argument order against RUNBOOK
  §8.7.8's bench transcripts, the `0x80500000` load address against the `cr6c`
  header's `startAddr` and the boot log, port 2098 against `T-09`, the `nfjrom`
  mechanism against Realtek's published SDK.
* **The code reads as** described. Nothing here has been sent to the device.
  `runsheet.md` `A2.7` is the confirmation, and every cell of it carries a
  sha256 computed from `dumps/flash-n150rt-console-2.bin` before the visit —
  which means the reading can be **refuted**, not merely illustrated.
* **The scope of what a bench run would settle**: it would confirm the read
  path's source and length globals and the `LOADADDR` coupling. It would *not*
  confirm the burn routine's behaviour under `AUTOBURN 1` (nothing here sends
  it) nor the auto-execute filenames (deliberately avoided). That sentence used
  to end "nor what `FLW`'s fourth argument does" — settled 2026-08-21 and
  registered as `P9-14`, `P9-15`, `P9-16`, none of which has been sent to the
  device either.

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

### And how *this* note's first version was wrong, three ways

Written the same day, 2026-08-21, and all three have the same cause: **the
command table was transcribed by hand out of a hex dump, and a hand
transcription is a claim with no instrument behind it.**

1. **The record layout was backwards.** It said `{name, help, argc, handler}`.
   The dispatcher loads the handler from `+8` and the `?` printer loads the help
   from `+12`, so it is `{name, argc, handler, help}` — and the vendor's own
   header says the same. The *values* in the table were right, which is why
   nothing caught it: a wrong sentence about a right table reads exactly like a
   right one.
2. **`FLW`'s help string was truncated** at `<SPI cnt#>`, dropping
   `: Write offset-data to SPI from RAM` — the six words that name the field.
3. **`0xB8003000` was called "stop the timer".** It is `GIMR0`, the global
   interrupt mask, and the `mtc0` on the following line is the other half of the
   same `cli()`. Two adjacent lines described as two actions when they are one.

The fix is not a better transcription. `tools/loader-unpack.py --commands`
derives the stride, the record start, the field order and every handler's `argv`
use from the bytes, refuses when it cannot narrow any of them to one answer, and
is held to that by seven mutants in `tools/test-loader-unpack.sh` — including the
one that matters most, a fixture whose reader **does** load `+4`, so the headline
absence has to come back `true` when the loader earns it.

A fourth, and it is the one to remember: **this note declared itself "one tool"
and then went on to make an argument about the whole command set anyway.**
Naming a weakness is not the same as answering it. The `FLW` half is now three
readers; the `IPCONFIG`, `EB` and `PORT1` rows in particular were wrong under a
straight linear scan and only came out right under a walk that follows both arms
of a branch, which is a difference no amount of care in reading a listing would
have produced.
