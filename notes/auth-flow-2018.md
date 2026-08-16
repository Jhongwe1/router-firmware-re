# How the build on this unit decides you are allowed in

**Question carried out of W02 (open #4):** every authorisation claim in this
repository was measured on V2.1.2 or V3.4.0. This device runs neither. Does the
2015 reading transfer, does the 2020 reading transfer, or neither?

**Answer: neither, and the difference is not cosmetic.**

The gate is `process_header_end` at **`0x0040bb1c`** in
`sha256 19fe29d7…` (485,012 bytes, `boa: server built Jan 10 2018 at 14:57:54`).
It runs the authorisation check **only if the request URI contains the substring
`.htm` or the substring `.asp`**:

```
0040be90  jalr t9   -> strstr          ; strstr(uri, ".htm")
0040be9c  bne v0,zero,0x0040bec0       ; matched -> fall into the exemption list
0040beac  jalr t9   -> strstr          ; strstr(uri, ".asp")
0040beb8  beq v0,zero,0x0040c0a0       ; NEITHER -> jump past send_r_unauthorized
...
0040c088  jalr t9   -> send_r_unauthorized
0040c098  b 0x0040c104
0040c0a0  jalr t9   -> translate_uri   ; <- normal processing resumes here
```

`s1`, the haystack, is set at `0040bb68` to `req + 0x8d4` — the same field
`handleForm` reads with `strstr(req + 0x8d4, "/boafrm/")`. It is the request URI.

**So every one of this build's 57 `/boafrm/form*` handlers is dispatched with no
authorisation check**, because none of those URIs contains `.htm` or `.asp`.
That is the 2015 outcome reached by 2020's mechanism, and it is not what either
`auth-flow.md` or `auth-flow-2020.md` describes.

---

## 1. The four questions, across three builds

| # | | V2.1.2 (2015) | **this unit (2018)** | V3.4.0 (2020) |
|---|---|---|---|---|
| 1 | what makes the gate run? | `strstr(uri,"htm")` | **`strstr(uri,".htm")` or `strstr(uri,".asp")`** | `.htm` / `.asp` / **POST** |
| 2 | does a `/boafrm/` POST enter the gate? | no | **no** | yes |
| 3 | does `GET /config.dat` enter the gate? | no | **no** | no |
| 4 | how is a logged-in client remembered? | `AUTHG_IP_ADDR` (MIB) | **neither — see §4** | 5-slot in-memory table |

Row 1 is the one that matters and it is genuinely a third answer. 2015 tests a
bare `htm`, so `/foo.htmlish` and `/htm` are inside the gate. 2020 tests `.htm`,
`.asp` **or the request method being POST**, which is what pulled all 49
handlers back inside it. **2018 has 2020's string tests and does not have
2020's POST arm.** There is no request-method test anywhere between `check_host`
and the gate; the whole path is `check_host` → `apmib_get(0xb6)` →
`apmib_get(0xb7)` → credential compare → `.htm`/`.asp` → exemption list →
`send_r_unauthorized`.

### The gate is 13 unanchored substring tests on one string — 14 with `translate_uri`

Two to decide whether to run at all, then eleven exemptions, every one an
unanchored `strstr`, plus `translate_uri`'s `strstr(uri, "boafrm")` below:

```
index.htm  login.htm  formLogin  status.htm  countDownPage.htm
countDownPageWizard.htm  notice_frame.htm  notice.htm
iLogin.htm  iReboot.htm  iLink.htm
```

W04 counted **three** unanchored `strstr` calls in the 2020 authorisation path
and called that the technique the vendor kept while fixing the symptom
([`auth-flow-2020.md`](auth-flow-2020.md)). The build in between uses the same
technique **thirteen** times. `countDownPageWizard.htm` and `notice_frame.htm`
are here, and W03 recorded both as absent from 2020 — so on this axis the 2018
build is the older one.

---

## 2. What that unlocks, and why it is worse than the advisory says

`root_form[]` on this unit is at `0x00483758` and has **57 entries. One of them
is `formSysCmd`** — table entry `0x004838a8`, handler `0x0044ee2c`. It is in
neither published image ([`three-way-read.md`](three-way-read.md) §2).

```c
void form_formSysCmd(req)
{
  submit_url = req_get_cstream_var(req, "submit-url", "");
  sel        = req_get_cstream_var(req, "sysCmdselect", "");
  ...
  cmd = req_get_cstream_var(req, "sysCmd", "");
  if (*cmd != '\0') {
    snprintf(buf, 100, "%s 2>&1 > %s", cmd, "/tmp/syscmd.log");
    unlink("/tmp/syscmd.log");
    system(buf);                      /* no filtering, no escaping */
  }
  send_redirect_perm(req, submit_url);
}
```

`handleForm` at `0x004127f4` performs no authorisation of its own — it matches
the name on an exact-length `memcmp` and calls the handler.

### The step that could have collapsed this, and does not

`handleForm` is not called directly. Boa sets a handler on the request and jumps
to it later, so the chain has one more link than the gate reading alone shows —
and that link contains the string `"POST to non-script is disallowed."`, which is
exactly the shape of a thing that would kill this finding.

It does not. `translate_uri` (`0x004041cc`) ends:

```c
if (*(int *)(param_1 + 0xc) != 4) {         /* not POST -> allowed */
    return true;
}
pcVar10 = strstr(pcVar10, "boafrm");        /* POST: only if the URI says boafrm */
if (pcVar10 != (char *)0x0) {
    return true;
}
send_r_bad_request(param_1);                /* every other POST is rejected */
return false;
```

**It does not reject the POST — it whitelists it**, on a fourth unanchored
`strstr` over the same string. `init_form` (`0x00408c0c`) then handles POST
explicitly (`if (req->method == 4) req[0x1f] = req[0x1e];`) before calling
`handleForm`, and is itself reached from `write_body` at `0x0040ab30` through the
computed jump Boa uses for handlers.

So, as the code reads:

```
POST /boafrm/formSysCmd     sysCmd=<command>
  URI contains no ".htm" and no ".asp"
  -> 0040beb8  beq       skips send_r_unauthorized entirely
  -> translate_uri        method==POST && strstr(uri,"boafrm")  -> allowed
  -> write_body -> init_form (handles POST) -> handleForm (authorises nothing)
  -> form_formSysCmd -> snprintf -> system()
```

**CVE-2019-19824 describes this as requiring an authenticated attacker.** On
this build, as the code reads, no authorisation runs on that path at all. The
advisory's own wording — *"even if the GUI (`syscmd.htm`) is not available"* — is
literally this device's situation: the `w6cg` web-resource section contains 143
files and **`syscmd.htm` is not one of them**, while the handler is registered.

The bound is on the buffer, not on the injection: `snprintf(buf, 100, …)` caps
the write, and the constant tail `" 2>&1 > /tmp/syscmd.log"` is 23 bytes, so an
attacker controls the first ~76 bytes of a string passed to `/bin/sh` by a
process running as `root` (`boa.conf`: `User root`, `Group root`).

> ⚠️ **Scope of this claim.** This is a static reading of the binary extracted
> from this unit's flash. **Nothing has been sent to the device.** No request has
> been served, no `curl` has been run, and the device has never been connected to
> a network in this project. What would confirm it is one POST and a check of
> `/tmp/syscmd.log`, which is G4's job in W05/W06 — and until that happens the
> only defensible phrasing is the one used above: *the code reads as*.

---

## 3. `GET /config.dat` — outside the gate, and there may be nothing there

The gate reading gives it immediately: `/config.dat` contains neither `.htm` nor
`.asp`, so no authorisation runs. That is the third build in a row.

But the exposure is not the same as 2015's or 2020's, and the difference was
nearly missed. **This rootfs has no `/web` directory at all.** `/web` is a
symlink to `/var/web`, a ramfs populated at boot by `rcS`:

```sh
mkdir /var/web
...
cd /web
flash extr /web
```

`boa.conf` sets `DocumentRoot /web`. So the document root is exactly the 143
files in the `w6cg` flash section at `0x010000`, and **`config.dat` is not among
them** — the archive parses to 143 entries consuming 1,417,000 of 1,417,000
bytes with nothing left over, so the list is complete rather than truncated.

In V3.4.0, by contrast, `/web/config.dat` ships as a symlink to
`/var/config.dat`. **On this unit, `GET /config.dat` is unauthenticated and, at
boot, has no file to serve.** What creates one is `formSaveConfig`
(`0x0044f9fc`), which carries the literals `save-cs`, `save-ds`, `save-hs`,
`save-all` and `/config.dat` — and `formSaveConfig` is itself a `/boafrm/`
handler, i.e. also outside the gate. Whether that pair composes into an
unauthenticated read of the live configuration is **not settled here** and is
recorded as the first thing W05 should test, not as a finding.

---

## 4. Question 4 has no clean answer on this build, and that is the answer

2015 keeps the logged-in client's IP in `AUTHG_IP_ADDR`. 2020 has a five-slot
in-memory table. This build has neither:

| | V2.1.2 | **unit-2018** | V3.4.0 |
|---|---|---|---|
| `AUTHG_IP_ADDR` in `libapmib.so` (`grep -c`) | 1 | **0** | 0 |
| `AUTHG_*` names recovered by `fwrecon mib` | `IP_ADDR`, `USER_NAME`, `PASS_WORD`, `PHONE` | **`LOGIN`, `PHONE`** | `LOGIN` |
| MIB records recovered | 413 | **344** | 412 |

Two instruments agree that `AUTHG_IP_ADDR` is gone: `fwrecon mib`'s recovered
table, and `grep` on the raw `.so`, which shares no code with it. W04 used this
same cross-file trick to confirm the 2020 rewrite from a file other than `boa`,
and it works again here.

What the 2018 build does instead is set a global — `DAT_004899d8` at
`0x004899d8` — to 1 or 2 according to which credential pair matched, alongside
`req[0x2c]`. Per-request state plus one global is not a session; **who reads
`0x004899d8`, and whether anything makes the decision persist across
connections, is not answered here.** It goes to W05 with the note that a
`KeepAliveMax 0` server gets a fresh connection per request.

### The credential compare has two pairs and only one of them is initialised

```
0040bcd8  apmib_get(0xb6, sp+0x58)     ; USER_NAME
0040bcf8  apmib_get(0xb7, sp+0x78)     ; USER_PASSWORD
0040bd00  lbu v0,0x58(sp)              ; username[0]
0040bd08  bne v0,zero,0x0040bd20       ; set   -> compare credentials
0040bd10  lbu v0,0x78(sp)              ; password[0]
0040bd18  beq v0,zero,0x0040c0a0       ; EMPTY -> skip authorisation entirely
```

Then the supplied credentials are compared first against `sp+0x18` / `sp+0x38`
(match ⇒ level 2) and only then against the two `apmib_get` buffers (match ⇒
level 1). **`sp+0x18` and `sp+0x38` are read and never written** — the only
instructions that mention them are the two `addiu a1,sp,…` in `strcmp`'s delay
slot and one `lb v0,0x38(sp)`. The decompiler's output agrees: `acStack_110` and
`local_f0` are never assigned.

W03 found exactly this shape in V2.1.2 at `sp+0x40` / `sp+0x60` and filed it as
"a candidate for dynamic work, not a finding". **It transfers to this build**,
at different offsets, with both instruments agreeing. It stays a candidate for
the same reason it was one then: uninitialised stack is not a constant, what is
actually in those 32 bytes at that moment is a dynamic question, and a static
read cannot answer it.

### One thing that does not transfer, and it was nearly reported backwards

A case-sensitive `grep` for `Authorization` returns 2 for V2.1.2 and **0** for
both later builds, which reads as "the 2018 build dropped HTTP Basic auth".
That is wrong. Case-insensitively it is 3 / 1 / 1, and the strings are:

```
v2.1.2    : AUTHORIZATION
            Authorization: Basic YWRtaW46YWRtaW4=      (twice)
unit-2018 : AUTHORIZATION
v3.4.0    : AUTHORIZATION + the 401 Unauthorized page
```

All three parse the header — `AUTHORIZATION` is Boa's own uppercased header
index constant. What V2.1.2 additionally carries, and the later two do not, is
**a hardcoded `Authorization: Basic YWRtaW46YWRtaW4=` literal, twice.** That
base64 decodes to `admin:admin`. Neither W03 nor W04 recorded it. Which function
holds it, and whether `boa` ever sends it, is **not established** — it is listed
in [`PROGRESS.md`](../PROGRESS.md) as carried forward rather than described here,
because a string is not a behaviour.

---

## 5. `send_r_unauthorized` still does not send a 401

W04 corrected W03 on this for V2.1.2. The correction holds here:

```c
uint send_r_unauthorized(uint *req) {
  req[4] = 0x191;                                  /* 401 in the status field */
  req[1] = 2;
  if (req[3] != 2) return send_redirect_perm(req, "/login.htm");   /* 301 */
  ...
}
```

The status field is set to 401 and a **301 to `/login.htm`** goes out. Like
V2.1.2, this binary contains no `401 Unauthorized` string at all; V3.4.0 does.

---

## 6. What the instruments were allowed to say

The decompiler raised **three** warnings on this function — `Heritage AFTER dead
removal`, a global-overlap warning, and `Restarted to delay deadcode elimination`
— the same class it raised on V2.1.2. By this repository's rule that costs it
the last word, so every branch quoted above was read from
[`BoaListing.java`](../ghidra/scripts/BoaListing.java) output at instruction
level first, and the decompiled C is shown only where the two agree.

Independent confirmations used here, none of which share code with Ghidra:

| Claim | Second source |
|---|---|
| `formSysCmd` present in 2018, absent in 2015 and 2020 | `grep -aoc formSysCmd` on the three raw binaries: **0 / 1 / 0** |
| `AUTHG_IP_ADDR` gone | `grep` on `libapmib.so`, against `fwrecon mib`'s recovered table |
| `syscmd.htm` absent from the docroot | the `w6cg` archive parses to 143 entries with **zero** trailing bytes |
| Boa runs as root | `/etc/boa/boa.conf.bak`: `User root` / `Group root` |
| document root is a ramfs filled from flash | `rcS`: `mkdir /var/web`, `flash extr /web`; `web -> /var/web` symlink |

---

## How the first version of this note was wrong

Three ways, and the second is the one worth keeping.

**1. It predicted the wrong build.** [`three-way-read.md`](three-way-read.md) §1,
committed before any script ran, predicted the gate would "look like 2015" —
reasoning that this unit's flash layout, LZMA filesystem and `w6cg` section all
put it in the 2015 family. That reasoning was sound and the conclusion was
wrong: the *packaging* is 2015's and the *authorisation code* is not. Structural
family resemblance does not predict which functions were edited.

**2. It read a case-sensitive `grep` as a finding.** "0 occurrences of
`Authorization` in the 2018 binary" was written down and briefly believed. The
string is there in upper case. The check that caught it was not carefulness —
it was reading the same function's strings a second time for a different reason
and seeing `AUTHORIZATION` in the list. **A `grep` returning 0 is a claim, and
this one was a claim about my own regex.** That is the ninth time in this project
that agreement between two runs of the same tool was mistaken for evidence, and
the first time the tool was `grep`.

**3. It nearly reported `GET /config.dat` as equivalent to 2015's.** The gate
reading is identical, so the sentence "unauthenticated `config.dat` disclosure,
third build running" almost went in. It would have been unfalsifiable at best:
this rootfs has no `/web` at all, and the document root is a ramfs that at boot
contains 143 files, none of them `config.dat`. **The gate being open says nothing
about there being a file behind it** — reachability and existence are two
questions, and the CVE-2019-19822 chain needs both.
