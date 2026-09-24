# `poc/` — what is here, and what is deliberately not

Five reproductions across six files, one script, and a rule that decides what a file in this
directory may contain. **The rule changed on 2026-08-23** and the change is
recorded below rather than applied silently.

## The rule

`docs/disclosure.md` splits everything this project finds into three:

| | published here |
|---|---|
| **Finding** — "this handler takes this parameter into `system()`, at this address, in this binary" | **yes**, that is the research |
| **Reproduction** — a procedure that produces the effect, with a request that can be copied | **yes, since 2026-08-23** — it was *only once the issue is public* until then |
| **Tradecraft** — persistence, anti-forensics, credential harvesting on a live host | **no**, and no gate here asks for it. **This line did not move** |

**What changed and what did not.** From 2026-08-17 to 2026-08-23 this directory
held reproductions of already-public issues only, and `04` was a stub carrying no
request. On 2026-08-23 the author decided to report nothing and publish
everything, and the argument — including the four things it does **not** cover —
is `docs/disclosure.md` §"The decision of 2026-08-23". The one-line version:
these builds already carry public unauthenticated root (CVE-2024-51228, public
PoC naming this exact build string) and public unauthenticated plaintext
credentials (CVE-2019-19822, one `GET`), so **nothing published here adds a
capability against them**.

That rule did bite while it stood, and the mark is left in place: `P3-2`
(`formRoute` / `subnet`) was tested on the same evening as everything else and
its request appears in no file in this repository, because at the time it was
tested nothing about it had been reported to anyone. It has since been withdrawn
for other reasons and there is nothing to publish.

## What each file covers

| file | issue | public since |
|---|---|---|
| [`01-config-disclosure.md`](01-config-disclosure.md) | CVE-2019-19822 (unauthenticated configuration disclosure) + CVE-2019-19823 (plaintext credential storage) | 2019-12 |
| [`02-command-injection.md`](02-command-injection.md) | CVE-2024-51228 (`formSysCmd` → `system()`), and why its CVSS vector is wrong | 2024-11-27 |
| [`03-flash-evidence.md`](03-flash-evidence.md) | the part that is this project's own: pointing at the bytes one HTTP request changed on the SPI NOR | — |
| [`04-auth-takeover.md`](04-auth-takeover.md) | unauthenticated administrator password change (**CVE-2018-13315**, and this project did not know that until 2026-08-23), an empty stored password disabling authentication device-wide, and one legal POST to `formSchedule` that removes the web server until power cycle | 2018-07 for the first; **never reported** for the other two |
| [`05-auth-bypass.md`](05-auth-bypass.md) | an empty username and an empty password pass the authorisation gate — a second credential pair that nothing writes | **never reported** |
| [`05-l2-published-image.md`](05-l2-published-image.md) | **the same class of chain on an image anyone can download** — G4's third clause, and the honest form of it is narrower than the clause assumed | — |
| [`run.sh`](run.sh) | the two public chains, with preconditions that fail loudly | |

`04` was a stub from 2026-08-17 to 2026-08-23 and said so in its own text; it now
carries its three requests. `05` is new on 2026-08-23. **`05-l2` was in this
directory and in no index**: this table said *"Five reproductions"* and listed
five of the six files, with `05-l2` appearing in it zero times — found 2026-09-25, and
it is the reason [`../notes/README.md`](../notes/README.md),
[`../tools/README.md`](../tools/README.md) and
[`../reports/README.md`](../reports/README.md) now exist. **`run.sh` still runs only
the two public chains** — it was not extended to the newly published items,
because a script that fires an authentication bypass is a different artefact from
one that reproduces a documented CVE, and nothing in this project needs it.

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
