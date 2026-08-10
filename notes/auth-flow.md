# How Boa decides you are allowed in

**Question carried out of W01:** does Boa authenticate requests for `.dat`
paths? W01 could prove only that `/web/config.dat` is a symlink into the served
document root — a statement about the filesystem, not about access control.

**Answer, from V2.1.2:** there is exactly one authorisation gate in the request
path, it lives in `process_header_end`, and **it only runs when the request URI
contains the substring `htm`.** `.dat` is not specially unprotected. Nothing
without `htm` in its path is protected at all — which includes `/config.dat`,
`/ca.cer`, and every one of the 59 `/boafrm/form*` endpoints.

> **Scope of everything below.** These are static results read out of firmware
> images. No device has been powered on — the hardware has not arrived (W02).
> Nothing here has been confirmed against a live HTTP server, and the last
> section says exactly what would confirm it.

## The request path

```
process_requests()            state machine, stock Boa
  └─ read_header()
       └─ process_logline() ──> process_header()      parses AUTHORIZATION, REFERER, …
       └─ process_header_end()        <-- the only authorisation gate
            ├─ 401 send_r_unauthorized()   … or …
            └─ translate_uri()        stock Boa alias.c: path translation, no auth
                 └─ init_get / init_get2 / init_cgi
                      └─ write_body() ─> handleForm()    dispatch, no auth
                                           └─ handler(req, 0, 0)
```

`translate_uri` was read in full. It is stock Boa `alias.c` — its debug output
still prints `"alias.c"` and source line numbers — plus a Realtek addition that
tracks a firmware-upgrade countdown page. It contains no credential check.
`handleForm` contains no credential check
([`dispatch-table.md`](dispatch-table.md)). So the gate below is the whole of it.

## The gate

`process_header_end` @ `0x0040be0c`, V2.1.2. Decompiled, then confirmed against
the disassembly in
[`BoaListing`](../ghidra/scripts/BoaListing.java) output because the decompiler
raised three "Heritage AFTER dead removal" warnings on this function and its
output could not be taken at face value here.

```c
apmib_get(0xb6, username);          /* configured admin username */
apmib_get(0xb7, password);          /* configured admin password */
if (username[0] != '\0' || password[0] != '\0') {       /* is auth configured? */

    /* --- HTTP Basic path: see "the uninitialised compare" below --- */

    if (req->authorized == 0) {
        apmib_get(0x1ed, stored_user);      /* user recorded at login  */
        apmib_get(0x1ee, stored_pass);      /* pass recorded at login  */

        if (   !strstr(uri, "countDownPage.htm")
            && !strstr(uri, "countDownPageWizard.htm")
            && !strstr(uri, "status.htm")
            && !strstr(uri, "login.htm")
            &&  strstr(uri, "htm") != NULL          /* <=== THE GATE */
            && !strstr(uri, "formLogin.htm")
            && !strstr(uri, "notice_frame.htm")
            && !strstr(uri, "notice.htm"))
        {
            if (nowuptime - beforeuptime > 600) {           /* 10 min idle */
                apmib_set(0x1ec, "0.0.0.0");
                system("flash set AUTHG_IP_ADDR \"0.0.0.0\"");
            }
            apmib_get(0x1ec, logged_in_ip);
            if (logged_in_ip[0] == '\0'
             || strcmp(logged_in_ip, req->remote_ip) != 0
             || strcmp(stored_user, username) != 0
             || strcmp(stored_pass, password) != 0) {
                strcpy(&DAT_0048e9f8, uri);
                send_r_unauthorized(req, "");
                return 0;
            }
        }
    }
}
translate_uri(req);
```

Confirmed at instruction level — the branch polarity is the whole finding, so it
is quoted rather than paraphrased:

```
0040c234  lw t9,-0x7cbc(gp)        -> PTR_strstr_0048b2f4
0040c238  addiu a1,a1,-0x2be0        "htm"
0040c23c  jalr t9                  -> strstr
0040c240  _move a0,s1                             ; a0 = request URI
0040c244  lw gp,0x10(sp)
0040c248  beq v0,zero,0x0040c3a0   -> LAB_0040c3a0    ; NULL -> skip the check
```

`LAB_0040c3a0` is where every whitelisted page also branches to: past the
authorisation block, into `translate_uri`. Every other test in the chain uses
`bne v0,zero` — *matched a whitelisted page, skip*. This one is `beq v0,zero` —
**did not contain `htm`, skip**.

### What that means

| Request | contains `htm`? | authorisation |
|---|---|---|
| `GET /home.htm` | yes | checked |
| `GET /config.dat` | no | **not checked** |
| `GET /ca.cer` | no | **not checked** |
| `POST /boafrm/formPasswordSetup` | no | **not checked** |
| `POST /boafrm/formSaveConfig` | no | **not checked** |
| …all 59 handlers | no | **not checked** |

The published advisory for CVE-2019-19822 states that "the access control
verifies credentials only for some URLs but `.dat` files are not restricted."
That is the observed symptom. The cause is one line: authorisation is keyed on
a **substring of the URI**, so it covers the HTML UI and nothing else. `.dat`
was never singled out; it simply is not an `.htm`.

None of the 59 handlers re-checks authorisation itself. Searched for across all
59 decompiled handler bodies: only `formLogin` and one ASP emitter touch MIB
`0x1ec`/`0x1ed`/`0x1ee` at all.

## The "session" is a stored IP address

There is no cookie, no token, no nonce. `formLogin` @ `0x0044e78c`:

```c
apmib_get(0xb6, cfg_user);  apmib_get(0xb7, cfg_pass);
username = req_get_cstream_var(req, "username", "");
userpass = req_get_cstream_var(req, "userpass", "");
if (strcmp(username, cfg_user) == 0) {
    if (strcmp(userpass, cfg_pass) == 0) {
        apmib_set(0x1ec, req + 0x4bd);      /* <- the client's IP address */
        apmib_set(0x1ed, username);
        apmib_set(0x1ee, userpass);
        send_redirect_perm(req, "/home.htm");
        return;
    }
    msg = "ERROR: Password error.";
} else {
    msg = "ERROR: Username error.";
}
```

Consequences, in order of how cheap they are to abuse:

1. **Username enumeration.** `"ERROR: Username error."` and
   `"ERROR: Password error."` are distinguishable responses on the same
   endpoint. Free oracle, no rate limiting seen.
2. **The authenticated party is an IP address.** Anyone sharing the source IP
   the admin logged in from — the same NAT, the same machine, a spoofed source
   on the same L2 segment — is that admin for the next 10 minutes.
3. **Credentials are compared in plaintext against APMIB entries `0xb6`/`0xb7`.**
   This is the "credential check inside a binary" W01 inferred from the absence
   of `/etc/passwd`, now located. It also completes the CVE-2019-19822 →
   CVE-2019-19823 chain: `config.dat` is the serialised APMIB store, so
   retrieving it unauthenticated yields the very entries this comparison reads.
4. **`formLogin` itself is reachable unauthenticated** — it has to be — but so
   is `formPasswordSetup`, by the same gate, and that one changes the password.

## The uninitialised comparison

The HTTP Basic branch of the same function compares the supplied credentials
against two stack buffers, `sp+0x40` and `sp+0x60`, before falling back to
comparing against the configured credentials. Two authorisation levels come out
of it: `req->authorized = 2` for the first pair, `1` for the second — the shape
of a supervisor account beside the ordinary one.

`sp+0x40` and `sp+0x60` are **never written**. Across the whole function the
only three references are:

```
0040c03c  _addiu a1,sp,0x40      ; argument to strcmp
0040c06c  lb    v0,0x60(sp)      ; read first byte
0040c084  _addiu a1,sp,0x60      ; argument to strcmp
```

No store, no `apmib_get` targeting them, and their address is never passed to
anything that could fill them. The frame is `addiu sp,sp,-0x190` and both offsets
are inside it. So the level-2 credential comparison in this build runs against
**whatever the previous call left on the stack**.

What that is worth is not decidable from a static image:

- If the residue at `sp+0x40` happens to begin with NUL, `strcmp(auth_user, "")`
  succeeds only for an empty username; the password side then reads
  `lb v0,0x60(sp)` and, if that byte is also NUL, sets `req->authorized = 2`.
- Boa is single-process and handles requests in a loop, so stack residue at a
  fixed frame offset is far more repeatable than it would be on a threaded
  server.

Whether a reachable request sequence leaves the right bytes there is a
**dynamic** question. It is recorded here as a candidate, not a finding, and
belongs to W05/W06. It has not been reported to anyone and will not be until it
is either demonstrated or disproved.

## One more thing in the 401 path

```c
strcpy(&DAT_0048e9f8, (char *)(param_1 + 0x235));   /* the request URI */
send_r_unauthorized(param_1, "");
```

An unbounded `strcpy` of the attacker-supplied URI into a fixed global, executed
**on the failure path** — i.e. before any authentication succeeds. Boa bounds
the request line elsewhere (`"uri too long!"` at 0x801 in `translate_uri`), so
this is probably capped at ~2 KB rather than unbounded in practice. Sizing the
destination and confirming the cap is a W04 task; it is listed in
[`sink-inventory.md`](sink-inventory.md).

## The 2020 build rewrote this, and it has not been read yet

V3.4.0 does **not** contain the strings the 2015 gate is built from:

| string | V2.1.2 | V3.4.0 |
|---|---|---|
| `AUTHG_IP_ADDR` | present | **absent** |
| `countDownPageWizard.htm` | present | **absent** |
| `notice_frame.htm` | present | **absent** |
| `formLogin.htm` | present | **absent** |
| `status.htm`, `login.htm` | present | present |

So the authorisation code was replaced between the two builds, not merely
recompiled. V3.4.0 does carry HTTP Basic machinery — `AUTHORIZATION` header
parsing in `FUN_0040a4f8`, and `WWW-Authenticate: Basic realm="` emitted from
`FUN_0040b850`.

**Not yet established:** whether the replacement still keys on a URI substring.
Saying "the 2020 build fixed it" or "did not fix it" would both be guesses right
now. The next concrete step is to enumerate callers of `FUN_0040b850` — the
selector used for it returned nothing, which is a tooling result and not an
answer — and read whichever function decides to call it. That is the first W04
task.

## What would actually confirm any of this

Static reading establishes what the code does. It does not establish what the
server does, and the difference has bitten this project before. The confirmation
is one `curl` per row against a running target:

```
GET /config.dat                    expect: 200 + APMIB blob   (if the gate is as read)
GET /home.htm                      expect: 401
POST /boafrm/formPasswordSetup     expect: the password changes, unauthenticated
```

That needs either the physical unit (W02, blocked on delivery) or `boa` serving
under emulation (W05). Until one of those exists, every claim on this page is
"the code reads this way", not "the device behaves this way".
