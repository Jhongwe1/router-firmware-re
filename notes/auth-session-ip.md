# The gate has a session, it is keyed on the source IP address, and it stops working ten minutes after boot

**The answer, with addresses.** The authorisation block in `process_header_end`
has three arms, not two. W03 and W04-2 established the first two — a URI without
`htm` or `asp` in it skips the gate, and eleven named pages are exempt. The third
arm was never read:

```
0040bff8  lw    v1, 0x004899e0          ; nowuptime      <- written at 0040be54 from sysinfo()
0040c000  lw    v0, 0x004899dc          ; beforeuptime
0040c008  subu  v0, v1, v0
0040c00c  sltiu v0, v0, 0x259           ; is the difference < 601 seconds?
0040c010  bne   v0, zero, 0x0040c034    ;   yes -> keep the session
0040c018  strcpy(authipaddr, "0.0.0.0") ;   no  -> throw it away

0040c034  lw    a0, authipaddr
0040c03c  lbu   v0, 0(a0)
0040c044  beq   v0, zero, 0x0040c068    ; empty -> unauthorised
0040c04c  strcmp(authipaddr, req+0x4bd) ; req+0x4bd is the client's address
0040c060  beq   v0, zero, 0x0040c0a0    ; equal -> ALLOWED, straight to translate_uri
0040c068  ...   send_r_unauthorized
```

So a gated page is served to **whichever IP address logged in most recently**,
with no credentials on the request, for as long as the session is considered
live. `authipaddr` is written by `form_formLogin` at `0x0044f13c` and cleared by
`form_formLogout` at `0x0044cd48`.

**And `beforeuptime` is never written.** Across the whole binary,
`0x004899dc` has exactly one reference — the `lw` at `0x0040c000` above.
Measured twice, by tools that share no code: Ghidra's reference model, and
[`tools/mipsref.py`](../tools/mipsref.py), which decodes instruction encodings
and has no symbol table, no analysis database and no reference model. The control
address in the same run (`nowuptime`, `0x004899e0`) comes back with one read and
one write, so the scan is not simply blind.

`beforeuptime` therefore stays 0 for the life of the process, and
`nowuptime - beforeuptime` is not "seconds since the session was refreshed" — it
is **the system uptime**. Which makes the whole of it:

| uptime | what happens to a gated page requested without credentials |
|---|---|
| **under 601 s** | `authipaddr` survives. If anybody has logged in, every request from that address is served |
| **601 s and after** | `authipaddr` is overwritten with `"0.0.0.0"` *before* it is compared, on every request. It never matches a real client, so the IP session can never succeed again until the device reboots |

## 1. Why this repository concluded "per-request HTTP Basic", and why that was right

`P2-7` recorded that this device never sends `Set-Cookie` and that authorisation
is per-request HTTP Basic. Both halves are true and the conclusion is correct in
practice — because by the time anybody measures it, the device has been up for
more than ten minutes and the IP-session arm is dead. Every observation this
project has made was taken in that regime.

What was missing is that the reason is a bug rather than a design. The vendor
wrote a session with an idle timeout; the variable that would make it an *idle*
timeout is never assigned, so it degraded into "sessions work for the first ten
minutes of uptime and never again". That is the same authoring mistake as the
supervisor credential pair in [`uninit-credential-pair.md`](uninit-credential-pair.md)
— **a comparison against a variable nothing writes — twice, in one function.**

## 2. What it changes for the cases that are still open

- **`P8-3` / `P8-4`, CSRF.** The session being keyed on *source IP* rather than
  on a cookie means a drive-by request from the victim's browser inherits the
  victim's authorisation without needing one. Within the first ten minutes of
  uptime that is the mechanism; after it, `P2-1` already shows `/boafrm/*` is
  outside the gate entirely, so the request needs no authorisation at all. **The
  conclusion "CSRF works" is unchanged; the reason it works differs by uptime**,
  and a bench measurement taken at one uptime does not describe the other.
- **`P8-6`, DNS rebinding.** Its stated value was "reading the response". An
  IP-keyed session does not change that: the attacker's script runs in the
  victim's browser, which already has the victim's address.
- **The `A3.2` cold-boot timing section** now has a second reason to exist. The
  first 601 seconds after power-on are a different security state, and the
  runsheet's timing station is the only place that state is reachable.

## 3. Prior art, and a resemblance that is not a match

Cisco Talos's **CVE-2023-47677** (TALOS-2023-1872), on the same SDK family,
describes a CSRF protection in `boa` that "attempts to prevent API calls until an
HTML form page loads first", bypassable by loading the page in an `iframe`.

That is **not this mechanism** as far as the code here shows: what is here is an
address comparison with an uptime-derived expiry, not a page-load precondition,
and the bypass Talos describes does not apply to it. The two may be the same
feature described from the outside, or the SDK v3.4.11 they read may carry
something this 2018 build does not. **Not resolved**, and the honest statement is
that a published advisory exists in the neighbourhood and its mechanism does not
match the instructions above.

## 4. What is not established

- **Everything here is static.** No request has been sent to a device inside the
  601-second window, and the emulation environment cannot enter it: `sysinfo()`
  under `qemu-user` returns the **host's** uptime, which on any working desk is
  already past the threshold. That is why the emulated server behaves exactly as
  the device does at the bench — and why neither of them exercises this arm.
- **What `req+0x4bd` holds** is read as the client address from context — it is
  the buffer the comparison uses and the same structure offset the gate's other
  arms take strings from. It has not been confirmed at instruction level in the
  code that fills it.
- **Whether `form_formLogin` on this build is reachable unauthenticated**, and so
  whether an attacker can *install* their own address as `authipaddr` during the
  window, has not been traced. `formLogin` is one of the eleven exempt strings,
  so the gate does not stop the request reaching the handler.

> **What would confirm it on the device.** Power on, and inside the first ten
> minutes: log in from host A, then request a gated page from host A with **no**
> credentials (expect 200) and the same page from host B (expect 302). Then wait
> past 601 s of uptime and repeat host A's credential-free request (expect 302).
> Three requests and a wait, no writes, no power cycle beyond the one that starts
> it. It belongs in `A3.2`, the cold-boot timing station, because that is the
> only section that owns the clock.

## 5. How the first version of this was wrong

It did not exist, and that is the failure worth recording. The gate had been read
three times — W03 on V2.1.2, W04-2 on this build at instruction level, and W07
Day 2 for `check_host` — and all three stopped at the exemption list, because the
exemption list is where the interesting answer was each time. The listing was
regenerated for a different question entirely (counting `apmib_get` calls in
`process_header_end`), and the session block was simply the next forty
instructions on the page.

**A range that was disassembled for one question, read to the end, answered
another.** The cost of not doing that is visible in `P2-7`'s record, which is
correct about the behaviour and silent about the mechanism, and in
`notes/auth-flow-2018.md`, which describes the gate as two arms.

## 6. Measured, and the expiry is not what §1 said — 2026-08-19

**Answer first.** The window is **login + 601 seconds**, not uptime 601. It
reopens on every successful login, indefinitely. `beforeuptime` (`0x004899dc`) is
**written at `0x0044f140`, inside `form_formLogin`** — eight bytes from the
`authipaddr` line this note already named.

The device settled it before the disassembly did. Two anchors 706 seconds apart:
a login at uptime 232.9 left the window open through 809.3, and a second login at
uptime 939.5 — 338 s past the point this note said the arm could never work again
— reopened it, closing between samples at 1538.1 and 1541.2 against
login + 601 = 1540.5.

### The instruction sequence, at instruction level

`ghidra/scripts/BoaListing.java` over `0x0044f0e0`–`0x0044f190`:

```text
0044f118  lw   t9,-0x7ae8(gp)      -> PTR_sysinfo
0044f120  jalr t9                  -> sysinfo
0044f124  _addiu a0,sp,0x5c        (the struct sysinfo on the stack)
0044f12c  lw   v0,0x5c(sp)         <- info.uptime, the first field
0044f134  lw   v1,-0x7ef8(gp)      -> PTR_beforeuptime_004860e8
0044f13c  lw   a0,-0x7d70(gp)      -> PTR_authipaddr_00486270
0044f140  sw   v0,0x0(v1)          -> beforeuptime          <- the store
0044f144  lw   v1,-0x7f3c(gp)      -> PTR_nowuptime_004860a4
0044f148  jalr t9                  -> strcpy                 (a0 = authipaddr)
0044f14c  _sw  v0,0x0(v1)          -> nowuptime              (delay slot)
0044f160  jalr t9                  -> system   "killall -9 dnsspoof 2> /dev/null"
0044f178  jalr t9                  -> system   "rm -f /var/run/dnsspoof.pid 2> /dev/null"
```

And the arm itself, `0x0040bfe0`–`0x0040c090`:

```text
0040bff8  lw   v1,-0x6620(v0)      -> nowuptime
0040c000  lw   v0,-0x6624(v0)      -> beforeuptime
0040c008  subu v0,v1,v0
0040c00c  sltiu v0,v0,0x259        0x259 = 601, unsigned <
0040c010  bne  v0,zero,0x0040c034  delta < 601 -> skip the reset
0040c018..28   strcpy(authipaddr, "0.0.0.0")     <- expiry poisons the stored address
0040c034  lw   a0, authipaddr
0040c03c  lbu  v0,0x0(a0)          empty? -> unauthorized
0040c054  jalr strcmp(authipaddr, req+0x4bd)
0040c060  beq  v0,zero,0x0040c0a0  equal -> authorised
```

So §1's reading of the *comparison* was right, including the "overwritten before
it is compared" observation. What it got wrong was the consequence: the overwrite
does not end the arm's life, because the next login rewrites both
`beforeuptime` and `authipaddr`.

### Why two independent instruments said "no writes", and why that is the real finding

**The same variable is reached by two addressing modes in one binary.** The gate
uses `lui` + `%lo` direct addressing, which any immediate-matching scanner sees.
`form_formLogin` reaches it through the GOT — `lw $v1,%got(beforeuptime)($gp)`
then `sw $v0,0($v1)` — and **the storing instruction's immediate is `0`**.
Nothing in it names `0x004899dc`.

So "one read, no writes" was never a property of the firmware. It was a property
of a scanner that could see one of the two modes, and of a control address
(`nowuptime`) that happened to be reachable by the mode it could see.

Ghidra's *listing* knew: it annotates `0044f140` with `-> beforeuptime`. Ghidra's
*reference model* — what `BoaXref`'s `refs:` selector queries — counts references
to `PTR_beforeuptime_004860e8`, the GOT pointer, and not to the datum. **The
information was one indirection away inside both tools' own output.**

`tools/mipsref.py` schema 2 reports four classes instead of two, resolves symbols
out of `.dynsym` through `PT_DYNAMIC` (`sstrip` removes section headers, not
these — 423 named symbols on this build), refuses to answer for a GOT slot, and
carries `--control-indirect`, which requires a store found through a register.

### A category error that was in a committed report

`reports/mipsref-unit-2018-authsession.json` used to say `authipaddr` is at
`0x00486270` with **six reads and zero writes**. `0x00486270` is `authipaddr`'s
**GOT slot**; `authipaddr` is at **`0x0048fbd8`**; and all six were
`lw ...($gp)` — six *address materialisations*, no reads at all. Schema 2 reports
it as 0 reads, 0 writes, 6 address-taken and 6 live at a call, which is the
`strcpy` shape and matches what the note says the handler does.

### One thing this section adds that nobody was looking for

`form_formLogin` runs `system("killall -9 dnsspoof")` and
`system("rm -f /var/run/dnsspoof.pid")` on every successful login. `dnsspoof` is
what takes over port 53 and answers every name with `10.1.1.1` when the WAN is
down (`P6-10`). **So logging in stops the DNS hijack**, and nothing in this
repository had noted that the two features touch each other.

### How this section's first version was wrong

It was written from `tools/mipsref.py`'s output plus Ghidra's reference model,
which agreed — and the agreement was the problem. Both tools model references the
same way for a GOT-mediated store, so they are not independent for this question,
which is the exact failure mode `CLAUDE.md`'s "no claim from a single tool" rule
exists to prevent and which the phrasing "two instruments agree" concealed. The
control that was supposed to catch it passed, because it exercised the addressing
mode that worked. **What actually caught it was a device, and a wrong prediction
written down in advance in a form that could fail.**
