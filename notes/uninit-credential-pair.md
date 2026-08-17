# The Basic-auth path compares against two credential pairs, and one of them is never written

**The answer, with addresses.** `process_header_end` in this unit's `/bin/boa`
compares the credentials a client supplies against **two** pairs of stack
buffers, in this order:

```
0040bce0  apmib_get(0xb6, sp+0x58)      ; USER_NAME     -> the real pair
0040bcf8  apmib_get(0xb7, sp+0x78)      ; USER_PASSWORD

0040bd48  strcmp(supplied_user, sp+0x18)          <-- FIRST comparison
0040bd54    != 0 -> fall through to the real pair
0040bd6c    supplied password non-empty?
0040bd90      yes: strcmp(supplied_pw, sp+0x38)   <-- and its partner
0040bd7c      no:  read the single byte at sp+0x38
0040bda4    match -> req->0xb0 = 2                <-- authenticated, level 2

0040bdb8  strcmp(supplied_user, sp+0x58)          <-- the real pair, second
0040be00  strcmp(supplied_pw,   sp+0x78)
0040be18    match -> req->0xb0 = 1                <-- authenticated, level 1
```

**`sp+0x18` and `sp+0x38` are never written.** Across the whole of
`process_header_end` — `0x0040bb1c` to `0x0040c2d0`, 1,964 bytes — the only
instructions touching those two offsets are the three that *read* them:
`addiu a1,sp,0x18` at `0x0040bd4c`, `lb v0,0x38(sp)` at `0x0040bd7c`, and
`addiu a1,sp,0x38` at `0x0040bd94`. No `sw`, `sb`, `sh`, no `apmib_get`, no
`strcpy` into either.

**And the pair that is never written grants the higher level.** The real
credentials reach `req->0xb0 = 1`. The uninitialised pair reaches
`req->0xb0 = 2`.

Register: **`P2-9` confirmed** (emulated). Its prediction said *"both tools agree
this pair is read and never written; but 'read' is not 'externally
controllable'"*, and its refutation said that if no input reaches that stack it
stays a candidate and **the wording is not to be upgraded**. An input does reach
it, so the wording is upgraded — and §4, on what is still not established, is
longer than the finding.

---

## 1. Fired, and it needs no prior write to anything

Measured against `tools/qemu-env.sh serve` on the `unit-2018` profile: this
unit's own `/bin/boa` on this unit's own flash image. `GET /blank.htm`, a gated
page. The stored credentials are `admin` / `admin`, **both non-empty**, read back
through the vendor's own `/bin/flash` in the same run.

| `Authorization` | result |
|---|---|
| *absent* (control) | **302**, 138 bytes — redirected to `login.htm` |
| `Basic`, username **empty**, password **empty** | **200**, 333 bytes |
| `Basic`, username empty, password `t` | 302 |
| `Basic`, username `t`, password empty | 302 |
| `Basic`, `nosuchuser` / `nosuchpass` | 302 |
| `Basic`, `admin` / `admin` (positive control) | **200**, 333 bytes |
| `Basic`, `admin` / wrong password | 302 |

Byte for byte the same response as the real credentials. Repeated on
`/password.htm`: 302 unauthenticated, **200 and 5,332 bytes** of real HTML with
the empty pair. `/wizard.htm` answers 404 for both authenticated cases, which is
the file layer talking — the gate was passed and the file does not exist.

The header was sent by hand as well as through `curl -u`, in case the client was
adding something of its own. Same result.

**This is not `D-4`.** That one is *"an empty stored administrator password skips
the comparison"*, and its branch is `0x0040bd18`, reached only when `sp+0x78` —
the value `apmib_get(0xb7)` has just written — is empty. Here the stored password
is `admin`, that branch is not taken, the comparison **does** run, and it
succeeds against a buffer nothing filled in.

## 2. It reproduces on an image anyone can download

The `v2.1.2` profile is the published container with its flash rebuilt by
[`tools/mkflash.py`](../tools/mkflash.py) — a different `boa` binary, five years
older, no dump involved. Its synthesised settings carry **empty** credentials,
which trips `D-4` instead and makes the gate control fail; `qemu-env.sh serve`
refused to report the server as up, which is that check doing its job. With
`USER_NAME` and `USER_PASSWORD` set to `admin` through the vendor's own
`/bin/flash`:

```
/blank.htm   no auth 302-138   empty pair 200-333   admin:admin 200-333   admin:wrong 302-138
```

**Same behaviour, different binary, published image.** So this is not a property
of the build only this unit runs, and the class is reproducible by a reader with
no hardware — the same standard G4 clause 3a set for the command-injection chain.

## 3. Why the stack is zero there, and why that is an argument rather than a measurement

The obvious objection is that an uninitialised buffer holds whatever happened to
be there, and that under `qemu-user` what was there need not be what is there on
silicon.

The likely mechanism is structural rather than accidental: `process_header_end`
has the deepest frame reached in the request path, Linux hands out zero-filled
stack pages, and nothing in `boa` writes that depth afterwards — which is also
why it keeps working across many requests in one run rather than only the first.
That it reproduces on two different binaries over two unrelated flash images
supports the same reading.

**But that is a mechanism story, and a mechanism story is not a measurement.**

> **What would confirm it on the device.** One `GET` of a gated page carrying a
> `Basic` header with both fields empty, the same request with the real
> credentials as the positive control, and one with a wrong password as the
> negative. Three requests. No power cycle, no configuration change, nothing
> written. It belongs at the top of the next bench visit, because everything in
> §1 and §2 is emulation.
>
> And a question the desk can answer before that: **does the 2020 build do this
> too?** There is no `v3.4.0` profile yet. `mkflash` makes one cheap, and that is
> the differential harness W07 Day 2 was going to build regardless.

## 4. What is not established

- **Prior art has not been searched for this pattern.** [`prior-art.md`](prior-art.md)
  has been wrong once, publicly, and the search that overturned `D-1` took one
  query *by handler* after a search *by product* had returned nothing. Until that
  runs this is "found here", not "new", and nothing goes to anyone.
- **What level 2 buys over level 1 is unread.** `req->0xb0` is set to 2 and 1
  respectively and `DAT_004899d8` receives the same value; who reads it, and
  whether any page or handler treats 2 differently, has not been traced. The
  finding above is "authenticates", not "authenticates as something better", and
  the wording stays there until that is read.
- **Whether the two buffers can be made to hold *chosen* bytes** rather than zero
  is unknown. That would be a different and worse thing, and nothing here has
  looked for it.
- **The `/boafrm/` handlers do not need this.** `P2-1` established that a POST to
  a form handler is outside the gate entirely, so this bypass buys access to
  *pages*, not to actions that were already reachable. Its weight is in what a
  page returns, which is where `/config.dat` and the password page live.

## 5. How the first version of this was wrong

**W03 found this pattern and correctly refused to call it a finding**, in
V2.1.2, at `sp+0x40` / `sp+0x60`: *"A supervisor-level credential comparison
against uninitialised stack, never written. Recorded as a candidate for dynamic
work, not as a finding."* That was the right call on the evidence then — a static
reading cannot separate a live bypass from an unreachable one, and this
repository has several cases that looked live and were not.

What was wrong was not the caution. It is that the candidate then sat for weeks
while an environment able to fire it was built for an unrelated purpose: the
emulation profile `P0-9` produced for command-injection reproduction is what
answered this, and nobody had pointed it here. **The register's own `todo` output
listed `P2-9` every week and the answer cost one afternoon once the environment
existed.**

**And this note's first draft carried the offsets from the wrong build.**
`P2-9`'s title says `sp+0x18` / `sp+0x38`; W03's V2.1.2 reading says `sp+0x40` /
`sp+0x60`. Both are right about their own binary, and quoting either set without
naming the build is exactly the failure `G3.5` exists to prevent.
