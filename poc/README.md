# `poc/` — what is here, and what is deliberately not

Four reproductions, one script, and a rule that decides what a file in this
directory may contain.

## The rule

`docs/disclosure.md` splits everything this project finds into three:

| | published here |
|---|---|
| **Finding** — "this handler takes this parameter into `system()`, at this address, in this binary" | **yes**, that is the research |
| **Reproduction** — a procedure that produces the effect, with a request that can be copied | **only once the issue is public** |
| **Tradecraft** — persistence, anti-forensics, credential harvesting on a live host | **no**, and no gate here asks for it |

So this directory holds reproductions of **already-public** issues, and it holds
no request at all for anything unreported. That is not a stylistic choice; it is
the rule biting. `P3-2` (`formRoute` / `subnet`) was tested on the same evening
as everything else and its request appears in no file in this repository,
because at the time it was tested nothing about it had been reported to anyone.

## What each file covers

| file | issue | public since |
|---|---|---|
| [`01-config-disclosure.md`](01-config-disclosure.md) | CVE-2019-19822 (unauthenticated configuration disclosure) + CVE-2019-19823 (plaintext credential storage) | 2019-12 |
| [`02-command-injection.md`](02-command-injection.md) | CVE-2024-51228 (`formSysCmd` → `system()`), and why its CVSS vector is wrong | 2024-11-27 |
| [`03-flash-evidence.md`](03-flash-evidence.md) | the part that is this project's own: pointing at the bytes one HTTP request changed on the SPI NOR | — |
| [`04-auth-takeover.md`](04-auth-takeover.md) | **held.** Unauthenticated administrator password change, and an empty password disabling authentication device-wide | **not reported yet** |
| [`run.sh`](run.sh) | the two public chains, with preconditions that fail loudly | |

`04` is a stub on purpose. It names the finding and points at the register row;
it carries no request. It becomes a reproduction if and when
`docs/disclosure.md` says so.

## Scope

Every document here opens with the same table, and it is not decoration:

| | |
|---|---|
| verified on hardware | the 2018-01-10 build, `/bin/boa` `sha256 19fe29d7…` |
| verified in emulation | the same build under `qemu-user`, this unit's own flash as `/dev/mtdblock0` |
| present statically, **not executed** | V2.1.2-B20150825, V3.4.0-B20201030 |
| not tested at all | every other build |

**The reason that table exists is that this unit's firmware is on no download
page.** Anyone can read the two published images; nobody else can obtain the one
these results were measured on. Saying which is which is the whole of what makes
the results checkable — see [`REPRODUCE.md`](../REPRODUCE.md) for the three
tiers and what each of them cannot verify.

## Running it

```bash
./run.sh --emulated                       # needs no device
./run.sh --target 10.1.1.1 --i-own-this-device
```

`--target` refuses anything outside RFC 1918, refuses a target that is not
directly attached, and refuses to start without `--i-own-this-device`. It checks
the server's banner before sending anything, because pointing this at a device
that is not an N150RT is the mistake that matters.
