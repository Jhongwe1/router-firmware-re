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

## 3. What those two buffers are, and why nothing writes them

**They are the supervisor account.** Added 2026-08-18, and it turns the finding
from *"a comparison against uninitialised stack"* into *"a feature was deleted
from the data and left in the control flow"* — which is a different and much
more defensible claim, because it says what the code was supposed to do.

The Realtek rtl819x SDK that this `boa` is built from is public, in at least two
independent mirrors of different vendors' GPL drops. Its `users/boa/src/request.c`
carries this, in a block the vendor's own comment marks `// davidhsu`:

```c
char admin_name[MAX_NAME_LEN], admin_password[MAX_NAME_LEN];
char user_name[MAX_NAME_LEN],  user_password[MAX_NAME_LEN];

apmib_get(MIB_SUPER_NAME,     admin_name);       /* 180 */
apmib_get(MIB_SUPER_PASSWORD, admin_password);   /* 181 */
apmib_get(MIB_USER_NAME,      user_name);        /* 182 */
apmib_get(MIB_USER_PASSWORD,  user_password);    /* 183 */
if (strcmp(user_name, "") || strcmp(user_password, "")) {
    if (req->auth_flag == 0) {
        if (req->userName) {
            if (!strcmp(req->userName, admin_name)) {         /* the SUPER pair */
                ...  req->auth_flag = 2;
            }
            else if (!strcmp(req->userName, user_name)) {     /* the USER pair */
                ...  req->auth_flag = 1;
            }
```

**Four `apmib_get` calls in the source; this binary makes two.** It fetches
`0xb6` and `0xb7` — 182 and 183, `USER_NAME` and `USER_PASSWORD` — into
`sp+0x58` and `sp+0x78`, and it fetches 180 and 181 **nowhere**. The two SDK
mirrors agree on the ids, and the id-to-name mapping matches the MIB table this
project recovered from *this unit's own* `libapmib.so` byte for byte: entry 182
is `USER_NAME`, entry 183 is `USER_PASSWORD`. That table had never been checked
against anything outside this repository before.

So `admin_name` and `admin_password` are locals whose only initialiser the
vendor deleted, while the `strcmp` against them survived. The buffers hold
whatever the frame held.

Measured across the family, with a scan that reads instruction encodings and
needs no symbol table
([`tools/mipsref.py`](../tools/mipsref.py) and the `apmib_get` argument scan):

| build | `apmib_get(180)` | `apmib_get(181)` | `apmib_get(182)` | `apmib_get(183)` | SUPER comparison present |
|---|---|---|---|---|---|
| V2.1.2 (2015) | **0 sites** | **0 sites** | 5 | 5 | **yes** |
| this unit (2018) | **0 sites** | **0 sites** | 5 | 6 | **yes** |
| V3.4.0 (2020) | **0 sites** | **0 sites** | 7 | 8 | no |

**No build in this family has ever fetched the supervisor credentials.** The
2020 build is not "the one that stopped populating them" — it is the one that
also removed the dangling comparison. That is a smaller and more accurate claim
than §3a's first version made, and it changes what a reader should look for in
other vendors' builds of the same SDK: the question is not *"do they set
`SUPER_NAME`"*, it is *"did they delete the `strcmp` too"*.

**What is still an argument rather than a measurement** is why the buffers read
as *zero* rather than as garbage. `process_header_end` has the deepest frame
reached in the request path, Linux hands out zero-filled stack pages, and nothing
in `boa` writes that depth afterwards — which is also why it keeps working across
many requests in one run rather than only the first. That it reproduces on two
different binaries over two unrelated flash images supports the same reading.
**But a mechanism story is not a measurement.**

> **What would confirm it on the device.** One `GET` of a gated page carrying a
> `Basic` header with both fields empty, the same request with the real
> credentials as the positive control, and one with a wrong password as the
> negative. Three requests. No power cycle, no configuration change, nothing
> written. It belongs at the top of the next bench visit, because everything in
> §1 and §2 is emulation.
>
> And a question the desk can answer before that: **does the 2020 build do this
> too?** It does not — see §3a, added the same afternoon. It did not need the
> emulation profile after all.

## 3a. The 2020 build removed it, and that is the whole differential thesis in one function

Added later the same afternoon, statically, on V3.4.0's `/bin/boa` — which is
`sstrip`'d, so the function has no name: it is `FUN_00409fd8`, located by the
same `host invalid!` string the 2018 gate carries, 1,312 bytes against 2018's
1,964.

```
0040a130  apmib_get(0xb6, sp+0x44)                ; USER_NAME
0040a13c  apmib_get(0xb7, sp+0x64)                ; USER_PASSWORD
0040a184  strcmp(supplied_user, sp+0x44)          ; the only username comparison
0040a1c0  strcmp(supplied_pw,   sp+0x64)          ; the only password comparison
0040a1cc  match -> req->0xb0 = 1
```

**One pair, both halves filled by `apmib_get` immediately above, and no second
level.** The `req->0xb0 = 2` branch does not exist in this build. Every `a1`
loaded with a stack address in that function is either one of those two `strcmp`
arguments or an `apmib_get` destination — `sp+0x24`, `sp+0x20`, `sp+0x1c` at
`0x0040a1e8`, `0x0040a1f4`, `0x0040a200`, for MIB ids `0xc5`, `0xaa`, `0xab`,
which is a different feature further down.

So the lifecycle is:

| | V2.1.2 (2015) | **this unit (2018)** | V3.4.0 (2020) |
|---|---|---|---|
| second credential pair | `sp+0x40` / `sp+0x60` | `sp+0x18` / `sp+0x38` | **absent** |
| written by anything | no | no | — |
| level it grants | supervisor | `req->0xb0 = 2` | — |
| fires with empty credentials | ✅ measured | ✅ measured | — |

> **Corrected the same day by §3.** "The vendor removed it" is right about the
> comparison and wrong about the pair: **no build in this family ever populated
> it**, because none of the three fetches MIB 180 or 181. What 2020 removed is
> the dangling `strcmp`, not a working supervisor account. The row *"level it
> grants: supervisor"* below is the SDK's intent, not this binary's behaviour —
> see §4.

**The vendor removed it.** Nothing in the repository says when between January
2018 and October 2020, or whether they knew what they were removing — the same
question W02's `/bin/skt` timeline left open, and the same shape: a defect
visible in two builds and gone in the third, which no CVE search finds because
nobody diffs three builds of one product.

This is what W07's plan calls the differential line, and it arrived without the
emulation harness that line was going to be built on. **A three-way static read
answered in twenty minutes what a six-profile fuzzing bench was scheduled a day
for.** The bench is still worth building — it finds divergences nobody thought
to look for, which is not what happened here — but the cheap version ran first
and that ordering should have been obvious.

## 4. What level 2 buys, and what it does not

**Nothing over level 1, and everything over level 0.** Settled 2026-08-18 by
measurement rather than by reading around it.

`req->auth_flag` is at offset `0xb0` of the request structure. A scan of every
`lw`/`sw` in the text segment with displacement `0xb0` finds **31 instructions,
and exactly four of them use a base register that is not `sp` or `fp`** — all
four inside `process_header_end`, all four with `s0` (the request pointer):

```
0040bd20  lw  v0,0xb0(s0)     ; the "if (req->auth_flag == 0)" test
0040bda4  sw  v0,0xb0(s0)     ; = 2, from the SUPER pair
0040be18  sw  v0,0xb0(s0)     ; = 1, from the USER pair
0040be24  lw  v0,0xb0(s0)     ; and this one is the whole story
0040be2c  bne v0,zero,0x0040c0a0
```

`0x0040c0a0` is `translate_uri` — **past the entire authorisation block**: past
the `.htm`/`.asp` test, past the eleven exempt-page `strstr` calls, and past the
session check in §4a. So a non-zero `auth_flag` skips the gate, and 2 and 1 take
the identical branch. **The distinction between supervisor and user exists in the
SDK's design and is inert in this binary**, which is why the wording above stays
"authenticates" and never "authenticates as an administrator".

**`check_auth_flag` is a live defect that this build cannot reach.** The SDK
source sets a *global* alongside `req->auth_flag`, and it does so with no braces:

```c
if (!strcmp(req->password, admin_password))
        req->auth_flag = 2;
        check_auth_flag = 2;      /* not guarded by the if -- goto fail shape */
```

That is compiled into this binary faithfully: at `0x0040bda8` the branch to the
store is taken unconditionally, `v1` is loaded with 2 in its delay slot, and
`0x0040be20` stores it to `0x004899d8`. So **matching only the username sets the
global regardless of the password.** It buys nothing here: two independent
instruments — Ghidra's reference model, and an encoding scan that has neither a
symbol table nor an analysis database — agree that `0x004899d8` has **one
reference in the whole 485,012-byte binary, and it is that write.** Nothing reads
it. The defect is upstream, it is real, and on this build it is dead code. It is
recorded under *"relatively safe"* in [`bughunt.md`](bughunt.md) for that reason.

## 4a. Prior art: searched four ways, nothing found

The rule after `D-1` is that a search by product proves nothing and a search by
*handler* is the one that pays. Run 2026-08-18:

| searched | what came back |
|---|---|
| `process_header_end` + uninitialised stack + authentication | **CVE-2007-4915**, Intersil-extended Boa 0.93.15: a **long username** overwrites the in-memory admin password. Same function, same feature, **different mechanism** — a write, not a missing write. Not this |
| `Boa/0.94.14rc21` on its own | exploit-db 51139, the `HEAD`-method bypass. Already in [`prior-art.md`](prior-art.md) and already refuted on this build |
| Realtek rtl819x Jungle SDK + Basic auth bypass | Cisco Talos's fifteen 2023–24 SDK reports. **Ten stack overflows, one heap overflow, two arbitrary-code-execution, one CSRF, one firmware-update-without-consent — and no authentication defect of any kind** |
| the symbol `check_auth_flag` | nothing |

So: **no prior art found.** That is not the same as *new* — the SDK source
carrying this is on GitHub in two mirrors, so anyone reading it could see the
missing `apmib_get` calls, and "nobody published it" is weaker than "nobody found
it". It is enough to move the item from *"not searched"* to *"searched, and the
search that found Talos for `D-1` on the first page found nothing here"*.

## 4b. What is still not established

- **Whether the two buffers can be made to hold *chosen* bytes** rather than zero
  is unknown. That would be a different and worse thing, and nothing here has
  looked for it. `boa` handles many requests in one process, so the question is
  concrete: does anything reached from the request loop leave data at that depth?
- **The device.** Everything in §1 and §2 is emulated. Three requests settle it.
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

**Its second draft called the buffers uninitialised and stopped there.** They are
`admin_name` and `admin_password`, they belong to a supervisor account, and the
vendor's own SDK source names them — §3. Three things follow from having read it
that could not be said without it: the finding has a *cause* rather than an
accident, the 2020 build turns out never to have been the fix it looked like, and
the neighbouring `check_auth_flag` defect became visible at all. The whole of
that came from one search, by *symbol* rather than by product, on a codebase that
has been on GitHub the entire time.

**And the reason it took until W07 is worth naming**: this project reads binaries
because the vendor does not publish source, and it had never asked whether
*somebody else's* GPL drop of the same SDK was public. `docs/disclosure.md` step 2
says to search by handler before reporting. It does not say to search for the
source, and that omission is now [`prior-art.md`](prior-art.md)'s, not this
note's.
