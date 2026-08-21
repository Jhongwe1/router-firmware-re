# 9. Making it move: a real flash as `/dev/mtdblock0`

## First, a reason that gets repeated and is wrong

The standard explanation for why Realtek MIPS firmware will not emulate is that
**Lexra cores lack the unaligned load and store instructions**, so QEMU cannot
run the binaries.

That is backwards. Lexra's ISA is a *subset*: it omits `lwl`/`lwr`/`swl`/`swr`.
**A subset always runs on an emulator for the superset.** If the binaries only
use instructions Lexra has, and QEMU implements all of MIPS-I, then QEMU
implements all of the instructions in the binaries. The missing instructions are
a problem for *compiling* for these parts, not for emulating them.

And this project measured it rather than arguing: at the end of week 1,
`qemu-mips-static` in a chroot ran `/bin/busybox` and `/bin/boa --help`, and
`boa` printed its real usage text including `-c serverroot` and `-f configfile`.

The real obstacle is somewhere else entirely.

## The real obstacle

`libapmib.so` — which every vendor binary links, and which `boa` calls during
start-up — reads the configuration out of `/dev/mtd*`. Those do not exist in a
chroot. `apmib_init()` fails, and `boa` exits before it binds.

The fix is not a stub. **It is a file**: this project has a byte-for-byte copy
of the flash, and the MTD device is a block device over exactly those bytes.
Presented with one, `apmib_init()` succeeds, 2,399 MIB entries load, `boa` binds,
and the authorisation gate behaves the way chapter 6 read it: `login.htm` 200,
`blank.htm` 302, `status.htm` 200.

An unauthenticated `POST /boafrm/formSysCmd` with
`sysCmd=cat /etc/version > /var/web/w06emu.txt;#` returns the build string
through the document root. The gate model that was read at instruction level in
week 4 is reproduced with no device attached.

## Doing it from published images only

The environment above uses this unit's dump, which nobody else has. So it was
also built a second way, from **published images only** — and that half is more
interesting, because it fails first and the failure is the finding.

A flash assembled purely from the vendor container's three sections gets exactly
this far:

```
Invalid hw setting signature [sig=  ]!
Initialize AP MIB failed!
```

which is a prediction that was **frozen and committed before the environment
existed**, down to the string. The first 64 KiB of this flash — boot loader,
`H601`, `COMPDS`, `COMPCS` — is in **none** of the container's sections. It is
written at manufacture.

Synthesising those three regions with zeroed payloads and vendor-rule checksums
brings it up. The image supplies **82.9%** of the flash; 144 of 144 web pages
come out of the public container. No byte comes from any physical unit.

## What was patched, and what that costs

This table matters more than "it runs".

| what was supplied | why | what it distorts |
|---|---|---|
| a real flash image as `/dev/mtdblock0` | `apmib_init()` reads MTD | nothing for the gate; **everything** for claims about a device with different configuration |
| `/web/config.dat` made a directory | that one `open()` SIGBUSes under `qemu-user` on an odd address | **`/config.dat` cannot be fetched from the emulated server** — the file standing in for it is the thing keeping `boa` alive |
| synthesised `H601`/`COMPDS`/`COMPCS` (published-image build only) | not in any downloadable image | per-unit values are all zero, so nothing about MACs, calibration or credentials transfers |
| — | `flash default` SIGBUSes under `qemu-user` at `0x004332a7` | the real MIPS kernel's trap handler fixes that alignment; the emulator does not |

The SIGBUS is worth one more line, because it is a genuine measurement rather
than an annoyance: `-strace` shows it firing at an odd address **immediately
after** `open("/web/config.dat", O_RDWR|O_CREAT|O_TRUNC)` at start-up — that is,
while *generating* `config.dat`, not while serving it. The alignment trap is
real and it is confined to one path.

And a consequence that is one step shorter than this repository had assumed:
**`boa` creates `/web/config.dat` during start-up, before it listens.** The
exposure half of CVE-2019-19822 on this hardware needs no request at all.

> **Where this chapter stops:** the emulated server reproduces the *gate* and
> the *injection primitive*. It cannot reproduce links 1 and 2 of chapter 10's
> chain, because the file those links fetch is the one being used to keep the
> process alive. `tools/qemu-env.sh serve` refuses to report success unless both
> gate controls hold — a fixture that comes up but answers wrongly is worse than
> one that does not come up.
