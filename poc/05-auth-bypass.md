# PoC 05 — the authorisation gate is passed by an empty username and an empty password

`D-15` · register `P2-9`. **The strongest candidate in
[`docs/disclosure.md`](../docs/disclosure.md) for being this project's own**: it
has survived eight prior-art search angles across two days and nothing matched.
It is still not called *new* — the SDK source carrying it has been public the
whole time, in other vendors' GPL drops.

Published 2026-08-23 under §"The decision of 2026-08-23". **Not reported to
anyone.**

## Scope

| | |
|---|---|
| verified on hardware | **2026-08-18 19:44**, `BENCH-LOG.md` `T-43`, six requests, no power cycle, nothing written |
| verified in emulation | yes, two `qemu-user` profiles, 2026-08-18 |
| **present** | V2.1.2-B20150825 (**published, downloadable**) and this unit's 2018 build |
| **absent** | V3.4.0-B20201030 — `FUN_00409fd8` carries one credential pair, both halves filled by `apmib_get` immediately above the comparison, and no second level at all |
| not tested at all | the five other `-CX-` models CVE-2024-51228 names |

## The mechanism

`process_header_end` in `/bin/boa` compares the supplied credentials against
**two** pairs of stack buffers. Only one pair is ever filled in.

```text
0040bce0   apmib_get(0xb6, sp+0x58)          USER_NAME       -> the real pair
0040bcf8   apmib_get(0xb7, sp+0x78)          USER_PASSWORD

0040bd48   strcmp(supplied_user, sp+0x18)    <- compared FIRST
0040bd90   strcmp(supplied_pw,   sp+0x38)
0040bda4   match -> req->0xb0 = 2

0040bdb8   strcmp(supplied_user, sp+0x58)
0040be00   strcmp(supplied_pw,   sp+0x78)
0040be18   match -> req->0xb0 = 1
```

Across all **1,964 bytes** of that function the only instructions touching
`sp+0x18` and `sp+0x38` are three **reads**. No `sw`, `sb`, `sh`, no
`apmib_get`, no `strcpy`. Confirmed by Ghidra and by an independent encoding
scan whose control in the same run returns a read *and* a write.

**What the higher level buys: nothing.** `req->0xb0` is read at exactly two
instructions, both inside this function, and the second — `0x0040be24` /
`0x0040be2c` — branches past the **entire** authorisation block on any non-zero
value. So 2 and 1 are equivalent, and the accurate description is not
*"authenticates at a higher privilege level"* but **"skips the authorisation
block"**, which is both simpler and worse.

**Why the buffers are zero**, from the SDK source rather than from the binary:
they are `admin_name` / `admin_password`, fed by `MIB_SUPER_NAME` /
`MIB_SUPER_PASSWORD` — a supervisor account that **no build in this family
fetches**, 2015 included. The comparison outlived the account.

## The request

A `Basic` credential whose decoded value is a single colon: empty username,
empty password.

```http
GET /blank.htm HTTP/1.1
Host: <device>
Authorization: Basic Og==
```

## On the device — six requests, and the last two are the ones that matter

Stored credentials `USER_NAME` / `USER_PASSWORD` were five characters each and
**both verified non-empty** in the same run, decoded from that night's own 64 KiB
flash snapshot rather than assumed.

```text
label                              code  bytes  sha256-16
none (no header)                    302    132  ada993dce7920b0a
real credentials                    200    333  bc56c91c2cd06b83
wrong password                      302    132  ada993dce7920b0a
bypass (both halves empty)          200    333  bc56c91c2cd06b83   <- the finding
empty user, non-empty password      302    132  ada993dce7920b0a
non-empty user, empty password      302    132  ada993dce7920b0a
```

The bypass body is **byte-identical** to the real-credential body.

**The last two rows are why this is a result and not a coincidence, and the
register did not ask for them.** The emulated run sent four requests. Four cannot
separate *"the comparison was skipped"* from *"the comparison ran and matched a
buffer nobody wrote"* — both give a 200. `empty:t` and `t:empty` both returning
302 prove the comparison **ran**. That is the cut that separates this from
[`04-auth-takeover.md`](04-auth-takeover.md) §B, where the stored password is
empty and the comparison is skipped at `0x0040bd18`.

On a gated page with real content:

```text
GET /password.htm    no header  ->  302 /   132
                     bypass     ->  200 / 5,332
```

`/wizard.htm` answers 404 for both authenticated cases — the gate was passed and
the file does not exist, which is the file layer talking rather than the gate.

**One difference measured before it was explained:** the 302 body is 138 bytes
under emulation and 132 on this unit. That is the `Location` length, not the
finding — recorded because "roughly the same" is how a real discrepancy gets
skipped.

## What this reads, and why it is not an escalation

`/password.htm` on this build inlines the plaintext administrator username *and*
password into two JavaScript variables
([`password-page-credentials.md`](../notes/password-page-credentials.md)). So the
page this bypass unlocks contains the credentials.

**And it changes nothing an attacker could do.** `GET /config.dat` has returned
those same two values unauthenticated, with no bypass, since **CVE-2019-19822**
in 2019 — reproduced on this unit in
[`01-config-disclosure.md`](01-config-disclosure.md) — and this build also
carries public unauthenticated root via CVE-2024-51228. This finding is about the
**authorisation code**, not about access to the device.

That distinction is the one worth keeping: `/config.dat` is served because the
gate **never runs** for a path containing neither `htm` nor `asp`. This is the
gate **running and being defeated**. A vendor who fixed the first — by bringing
`.dat` inside the gate — would still ship the second.

## What is not established

* **Whether the buffers can be made to hold *chosen* bytes** rather than zero.
  Unknown, and it would be a different and worse defect. Nothing here claims it.
* **Whether the five other `-CX-` models carry the same function.** Untested.
  The window is 2015 → 2018 present, 2020 absent, and **one device has been
  measured.**
* **WAN reachability.** Every measurement is LAN-side in this unit's shipped
  configuration.
* **That it is new.** Eight search angles came back empty; the source has been
  public throughout. *"Nobody published it"* is not *"nobody could see it"*.
