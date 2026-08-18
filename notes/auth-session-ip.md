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
