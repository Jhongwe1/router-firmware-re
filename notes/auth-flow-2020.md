# How the 2020 build decides you are allowed in

**Question carried out of W03:** [`auth-flow.md`](auth-flow.md) ended by saying
the V3.4.0 authorisation code was *replaced*, not recompiled — `AUTHG_IP_ADDR`,
`formLogin.htm`, `notice_frame.htm` and `countDownPageWizard.htm` are all absent
from its string table — and that "saying *the 2020 build fixed it* or *did not
fix it* would both be guesses right now."

**Answer: it fixed the hole W03 found, kept the technique that caused it, and
grew a new hole of the same species.** The gate is
`FUN_00409fd8` @ `0x00409fd8` (V3.4.0's `process_header_end`, identified by the
string `"No logline in process_header_end"`).

```c
if ((cfg_user[0] != '\0' || cfg_pass[0] != '\0') && req->authorized == 0) {
    /* ... HTTP Basic against USER_NAME / USER_PASSWORD ... */
    if (!authorised) {
        if ( (strstr(uri, ".htm") || strstr(uri, ".asp") || req->method == M_POST)
             && !strstr(uri, "wan_status.htm")
             && session_lookup(req) in { 0 /*absent*/, -1 /*expired*/ } )
        {
            if (!strstr(uri, "login") && !strstr(uri, "forgot.asp")
                                      && !strstr(uri, "Login")) {
                send_redirect_302(req, mobile ? "/mobile/login.asp" : "login.htm");
                return 0;                                   /* <- the only stop */
            }
            if (captive_portal_host(req->header_host)) { send_200_ok(req); return 0; }
        }
    }
}
translate_uri(req);      /* everything that did not stop above arrives here */
```

> **Scope.** Static. No device has been powered on — W02 is blocked on hardware
> delivery. Every claim here is "the code reads this way". The confirming
> requests are at the end. Nothing has been reported to anyone.

## What changed, and what did not

| | V2.1.2 (2015) | V3.4.0 (2020) |
|---|---|---|
| gate applies when the URI… | contains `htm` | contains `.htm` **or** `.asp` **or the method is POST** |
| so `POST /boafrm/form*` is | **not checked** | **checked** |
| so `GET /config.dat` is | **not checked** | **not checked** |
| exempt list | 7 page names | `wan_status.htm`, `login`, `Login`, `forgot.asp` |
| exemption test | `strstr` | `strstr` |
| "session" | one IP in MIB `AUTHG_IP_ADDR`, 600 s | **5-slot in-memory IP table**, 600 s |
| unauthenticated response | 301 → `/login.htm` | 302 → `/login.htm` or `/mobile/login.asp` |
| supervisor (`authorized = 2`) path | present, compares uninitialised stack | **removed** |
| stock `send_r_unauthorized` (401 + `WWW-Authenticate`) | replaced by a redirect | present in the binary, **zero callers** |

The 2015 finding — 59 handlers outside the gate because their URIs contain no
`htm` — **is fixed**: any POST now enters the check. That is a real repair, and
it should be said plainly.

The technique did not change. Both builds decide authorisation by running
`strstr` over the request URI, and in both builds the bug is in that decision.
In 2015 the *inclusion* test was too narrow. In 2020 the inclusion test was
widened and the *exemption* tests became the narrow part.

## The exemption is a substring of the whole URI

Confirmed at instruction level rather than from the decompiler, because branch
polarity is the entire claim:

```
0040a25c  jal strstr                  ; strstr(uri, ".htm")
0040a264  bne v0,zero,0x0040a290      ; matched -> enter the gate
0040a270  jal strstr                  ; strstr(uri, ".asp")
0040a278  bne v0,zero,0x0040a290      ; matched -> enter the gate
0040a27c  _li v0,0x4
0040a280  lw v1,0xc(s0)               ; v1 = req->method
0040a288  bne v1,v0,0x0040a378        ; not POST -> SKIP THE GATE ENTIRELY
LAB_0040a290:
0040a298  jal strstr                  ; strstr(uri, "wan_status.htm")
0040a2a0  bne v0,zero,0x0040a378      ; matched -> skip
0040a2a8  jal FUN_00445114            ; session lookup on req->remote_ip
0040a2b0  beq v0,zero,0x0040a2cc      ; 0 = no session -> keep going
0040a2c4  bne v0,v1,0x0040a378        ; not -1 (expired) -> authorised, skip
LAB_0040a2cc:
0040a2cc  move a0,s1                  ; a0 = the request URI
0040a2d0  jal strstr
0040a2d4  _addiu a1,a1,0x8a0          ; "login"
0040a2d8  bne v0,zero,0x0040a354      ; CONTAINS "login" -> jump past the redirect
...
0040a330  jal 0x0040b484              ; 302 redirect to the login page
LAB_0040a354:
0040a358  jal FUN_004213e4            ; captive-portal Host check
0040a360  beq v0,zero,0x0040a378      ; ordinary Host -> fall through to translate_uri
0040a378  jal 0x00403860              ; translate_uri: the request proceeds
```

`s1` is the request URI throughout (`req + 0xf8`, the same field `handleForm`
reads). `s0` is the request. `req->method == 4` is POST — the same field and
value the function's own POST-body branch tests 200 instructions later.

`FUN_004213e4` is not an authorisation check. It is the Apple captive-portal
host list — `captive.apple.com`, `itools.info`, `ibook.info`,
`appleiphonecell.com`, `thinkdifferent.us`, `airport.us`. For any ordinary
`Host:` header it returns false, and `beq` at `0x0040a360` falls straight through
to `translate_uri`.

So the path from `0x0040a2d8` for a URI containing `login` is: skip the redirect,
fail the captive-portal test, **proceed**.

## What that means

`handleForm` @ `0x0040ee60` locates its route with
`strstr(req->request_uri, "/boafrm/")` and then matches the **eight bytes after
the match** exactly against `root_form[]`. It does not require `/boafrm/` to be
at the start of the URI. And `translate_uri` @ `0x00403860` permits a POST to a
non-CGI path when `strstr(uri, "boafrm")` matches — also a substring, also
anywhere.

Three substring tests, on the same string, with no anchoring in any of them:

```
POST /login/boafrm/formWsc
      ^^^^^  contains "login"  -> gate at 0x0040a2d8 jumps past the redirect
            ^^^^^^^^ contains "boafrm" -> translate_uri allows the POST
            ^^^^^^^^^^^^^^^^ "/boafrm/" + exact "formWsc" -> handleForm dispatches
```

`clean_pathname` runs before the gate and collapses `.` and `..`, but this path
has neither, so it arrives intact.

**As the code reads, that reaches the handler without authentication.** The same
prefix works for all 49 handlers, including `formPasswordSetup` and the `formWsc`
parameters that reach `system()` unfiltered
([`sink-inventory.md`](sink-inventory.md)).

This is stated as carefully as it deserves: it is a static reading of three
`strstr` calls and one dispatcher, it has not been executed, and it is exactly
the kind of claim this project has been wrong about before. It is **not** in any
CVE for this device. If it survives dynamic testing in W05/W06 it goes to
TWCERT/CC before it goes anywhere else, per the disclosure position in the
README — and nothing about it will be published until then.

## `GET /config.dat` is still outside the gate

The `bne v1,v0` at `0x0040a288` skips the entire check when the URI contains
neither `.htm` nor `.asp` **and** the method is not POST. `GET /config.dat` meets
all three conditions.

`/web/config.dat` is a symlink to `/var/config.dat` in this build, and `rcS`
copies `/web/*` into the served document root
([`anatomy-n150rt.md`](anatomy-n150rt.md)). So the exposure CVE-2019-19822
describes reads as **still present in a build dated 2020-10-30, nine months after
Błażej Adamczyk's full disclosure** — and for the same underlying reason as in
2015, not a new one.

What that file contains is [`mib-and-config-dat.md`](mib-and-config-dat.md).

## The 401 that is never sent

V3.4.0 contains stock Boa's `send_r_unauthorized` at `0x0040b850`, complete with
`401 Unauthorized`, `WWW-Authenticate: Basic realm="` and the 401 body. It has
**zero callers.**

Confirmed twice. Ghidra reports no call references; and a scan of the raw ELF for
the MIPS `jal` word that encodes that target —
`0x0C000000 | (0x0040b850 >> 2)` = `0C 10 2E 14` — finds zero occurrences, while
the same scan finds exactly one `jal` to `0x0040a4f8` and one to `0x00408720`,
matching Ghidra's counts for those. The scanner is calibrated; the zero is real.

Whoever added the redirect left the 401 emitter in place. Nothing on this device
ever answers `401` — a browser is redirected to a login page instead, which is
worth knowing before writing a PoC that asserts on status codes.

## What would confirm this

```
GET  /config.dat                        expect: 200 + a COMPCS blob
GET  /home.htm                          expect: 302 -> login.htm   (not 401)
POST /boafrm/formWsc  (no prefix)       expect: 302 -> login.htm
POST /login/boafrm/formWsc              expect: the handler runs
```

The fourth is the whole finding, and the third is its control: if both redirect,
the reading is wrong and it stays in this file as a negative result.

Needs the physical unit (W02) or `boa` under emulation (W05).

## How the first version of this note was wrong

Twice, before it reached a page.

**The 2020 gate was nearly recorded as "no authorisation at all."** The first
measurement was that V3.4.0's 401 emitter has no callers, which invited the
conclusion that the 2020 build dropped authentication. It did not; it replaced a
401 with a 302 and moved on. A missing caller for one function is a fact about
that function.

**And the 2015 note it follows is wrong about its own response code.**
[`auth-flow.md`](auth-flow.md) drew `process_header_end` as
`├─ 401 send_r_unauthorized()`, and listed `GET /home.htm → expect: 401` as a
confirming request. V2.1.2's `send_r_unauthorized` @ `0x0040ecdc` is 64 bytes
long, references exactly one string — `/login.htm` — and reads:

```c
req->response_status = 0x191;          /* 401, for the access log */
if (req->simple != 2)
    return send_redirect_perm(req, "/login.htm");   /* 301 on the wire */
```

The name survived stripping and was taken at face value; the body was never
opened, because the name was the answer W03 expected. The status field really is
set to 401 — which is why the log would say 401 — and the client really does get
a 301. A W06 PoC asserting `401` would have failed against a device behaving
exactly as described.
