# Prior art: who found what, and when

Two separate bodies of work are routinely conflated when people write about
TOTOLINK vulnerabilities. Getting the attribution right is not politeness — the
two disclosures describe **different bugs, in different subsystems, five years
apart**, and confusing them leads to looking for the wrong code.

| | 2015 | 2019–2020 |
|---|---|---|
| **Researcher** | Pierre Kim | Błażej Adamczyk (`br0x`, sploit.tech) |
| **Scope** | TOTOLINK-specific additions | The **Realtek SDK** web stack, across many vendors |
| **Headline bugs** | hard-coded Telnet credentials, `/bin/skt` backdoor service, CSRF/XSS | unauthenticated config disclosure, plaintext password storage, authenticated RCE, CAPTCHA bypass |
| **Disclosure** | 2015-07-16 | reported 2019-12-17, full disclosure 2020-01-23 |

> The project's original plan attributed CVE-2019-19822/23/24/25 to Pierre Kim.
> That is wrong; they are Adamczyk's. Corrected here because anyone who
> knows the field will notice, and because the two disclosures point at
> different binaries.

---

## 2015 — Pierre Kim

Four write-ups covering backdoor accounts, RCE across 15 models, a
backdoor binary, and CSRF/XSS. N150RT-V2 is listed among the affected models.

Relevant claims to verify against our own images:

His advisory `2015-totolink-0x02.txt` names **N150RT-V2** explicitly, and reports
it vulnerable *"until last firmware `TOTOLINK-N150RT-V2.1.1-B20150708.1548.web`"*
— which places our V2.1.2 image (2015-08-25) one build later. Two CVE ids came
out of it, and this project uses them from W04 onward:

| CVE | what it is | our images |
|---|---|---|
| **CVE-2015-9550** | `/bin/skt`, TCP 5555, `hel,xasf` opens :80 on the WAN | binary shipped, autostart commented out ([`skt-analysis.md`](skt-analysis.md)) |
| **CVE-2015-9551** | unauthenticated RCE via `/boafrm/formSysCmd` | handler **absent** from the dispatch table ([`formSysCmd-analysis.md`](formSysCmd-analysis.md)) |

| Claim | Where it should show up | Status in our images |
|---|---|---|
| Hard-coded credentials (`root` / `onlime_r`, password `12345`) | `/etc/passwd`, or hard-coded in a binary | ~~**`/etc/passwd` does not exist** in either image~~ — **W01 was wrong.** Both images ship it as a symlink into `/var`, populated at boot by `/bin/sysconf`. V2.1.2's template contains **`onlime_r`, uid 0, hash `$1$01OyWDBw$Hrxb2t.LtmiiJD49OBsCU/`** — byte for byte the hash Pierre Kim published. → [`credentials.md`](credentials.md) |
| `/bin/skt` backdoor: listens, accepts a command, runs it | `/bin/skt` + an init script line | **Confirmed present in V2.1.2.** Imports `TcpServer`, `TcpClient`, `socket`, `listen`, `accept`, `connect`, `strcmp`, `system` — exactly a network-driven command runner. |
| `skt` started at boot | `/etc/init.d/rcS` | **Started line is commented out**: `#skt&`. The binary still ships. See below. |

### The most interesting thing in the 2015 image

V2.1.2 was built **2015-08-25** — about five weeks *after* Pierre Kim's
2015-07-16 disclosure. It is, in other words, the vendor's response build.

The response was to comment out one line:

```
109:boa
110:#skt&
```

**W04 adds the rest of that ledger.** Of the three things his advisory names,
V2.1.2 fixed one properly:

| disclosed | what V2.1.2 did |
|---|---|
| CVE-2015-9551, `formSysCmd` RCE | **removed** — the handler is not in `root_form[]` |
| CVE-2015-9550, `/bin/skt` backdoor | autostart commented out, binary still shipped and executable |
| `onlime_r` / `12345`, uid 0 | **still there**, in `/etc/passwd.org` |

And `root`'s password, which he publishes as `12345`, is `123456` in this build —
and still `123456` in the 2020 one.

`/bin/skt` is still in the filesystem, still executable, still linked against
`system()`. Nothing starts it, so it is not remotely reachable on its own — but
"we removed the backdoor" and "we stopped launching the backdoor" are different
security properties, and only the second one happened. Anything that gains
command execution by another route finds a ready-made tool waiting.

This is the observation that made `fwrecon` report commented-out init lines as a
first-class finding rather than ignoring them.

---

## 2019–2020 — Błażej Adamczyk (Realtek SDK)

Four CVEs, forming a chain. Affected list includes **N150RT through 3.4.0**.

### CVE-2019-19822 — configuration disclosure / access-control bypass
`GET /config.dat`, unauthenticated.

Root cause per the advisory: the `apmib` library dumps its configuration
structure to `/web/config.dat`, and Boa's form-based authentication does not
restrict `.dat` files the way it restricts other URLs.

**What our images show.** In V3.4.0, `/web/config.dat` is a **symlink to
`/var/config.dat`**, and `/etc/init.d/rcS` copies `/web/*` into the runtime
document root:

```
56: cp -rf /web/* /var/web/
```

So the exposure path is structurally present in a build dated **2020-10-30 —
nine months after full disclosure**. `/bin/boa` in that build also gained new
config.dat handling strings absent from 2015, including
`cp /var/web/config.dat %s` and `rm -rf /var/config.dat >/dev/null 2>&1`.

That is *not yet* a claim that the CVE is unfixed: the fix could live in Boa's
request-authorisation path rather than in the filesystem layout. Establishing
which is a W03/W04 task — the question to answer in Ghidra is whether the
request handler applies an authentication check before serving `.dat`.
Recording the structural evidence now, and the limits of what it proves.

### CVE-2019-19823 — plaintext password storage
Passwords stored unencrypted in the apmib `COMPCS` structure.

`COMPCS` appears as a literal string in `/bin/boa` in **both** images, and
`/lib/libapmib.so` is present in both and linked by Boa. The format is therefore
reachable for analysis without a running device.

### CVE-2019-19824 — authenticated OS command execution
`POST /boafrm/formSysCmd`, parameter `sysCmd`. Requires valid credentials —
which is why it chains behind 19822.

Published PoC:

```
curl 'http://target/boafrm/formSysCmd' --user "admin:password" \
  --data 'submit-url=%2Fsyscmd.htm&sysCmdselect=5&sysCmdselects=0&save_apply=Run+Command&sysCmd=<cmd>'
```

**What our images show — and this is the sharpest open question of W01.**
The literal string `formSysCmd` is **not present** in either `/bin/boa`. But the
surrounding machinery is, in both:

```
sysCmdLog
sysCmdselect
/tmp/syscmd.log
```

`sysCmdselect` is a parameter name straight out of the published PoC. So the
feature exists; only the handler's name string is missing from the binary's
string table. Either the dispatch name is assembled at runtime, or handlers are
registered through a table that stores the name differently.

The advisory itself hints at this, noting the bug is reachable "even if the GUI
(`syscmd.htm`) is not available" — the endpoint outliving its UI is exactly the
shape of this evidence. **W03 target: find the handler dispatch table in Boa and
recover the real registration names.**

### CVE-2019-19825 — CAPTCHA bypass
`POST /boafrm/formLogin` with `{"topicurl":"setting/getSanvas"}` returns the
CAPTCHA in plaintext; HTTP Basic auth skips it entirely.

`getSanvas` is absent from V2.1.2 and **present in V3.4.0**. The CAPTCHA was
added between the two builds, and the JSON login path matches V3.4.0's new
dependency on `libcjson.so`. A control introduced after 2015, weak by
construction.

---

## Later CVEs listed against the N150RT line

Carried from the project plan; **none verified yet** against these images, and
several were filed against other TOTOLINK models where the endpoint naming
differs. To be checked in W07, not assumed.

~~Carried from the project plan; **none verified yet**~~ — **W04 corrected this
section twice over.**

**First: they are not "listed against the N150RT line". Fourteen of them name
this exact model and firmware string, `TOTOLINK N150RT 3.4.0-B20190525`.** The
project plan, W01 and W03 all treated the 2025 series as belonging to sibling
models with different endpoint naming. It does not.

| CVE | endpoint / parameter | class | located in our images |
|---|---|---|---|
| CVE-2025-3987 | `/boafrm/formWsc` → `localPin` | command injection | [`sink-inventory.md`](sink-inventory.md) §1 |
| CVE-2025-4462 | `/boafrm/formWsc` → `localPin` | buffer overflow | §1 — **the same line of code as 3987** |
| CVE-2025-6299 | `/boa/formWSC` → `targetAPSsid` | command injection | §2 |
| CVE-2025-3988 | `/boafrm/formPortFw` → `service_type` | buffer overflow | argtrace, V3.4.0 |
| CVE-2025-3989 | `/boafrm/formStaticDHCP` → `Hostname` | buffer overflow | argtrace, both builds |
| CVE-2025-3990 | `/boafrm/formVlan` → `submit-url` | buffer overflow | [`submit-url-overflow.md`](submit-url-overflow.md) |
| CVE-2025-3991 | `/boafrm/formWdsEncrypt` → `submit-url` | buffer overflow | same idiom |
| CVE-2025-3992 | `/boafrm/formWlwds` → `submit-url` | buffer overflow | same idiom |
| CVE-2025-3993 | `/boafrm/formWsc` → `submit-url` | buffer overflow | same idiom |
| CVE-2025-3994/3996 | `/home.htm` → `Comment` | XSS | not examined |
| CVE-2025-3995 | `/boafrm/fromStaticDHCP` → `Hostname` | XSS | not examined |
| CVE-2025-4460/4461 | URL-filtering / virtual-server pages | XSS | not examined |

**Second: the naming check W01 asked for was worth asking, and two of them are
wrong.** `handleForm` matches route names *exactly*
([`dispatch-table.md`](dispatch-table.md)), and neither build exports
`formWlwds` (both have `formWlWds`) or `fromStaticDHCP` (both have
`formStaticDHCP`). So **CVE-2025-3992 and CVE-2025-3995, as published, name
endpoints that return 404 on this firmware** — while the bugs they describe are
real and live at the correctly-spelled handlers. Endpoint names in CVE records
are transcribed from a PoC, not from the binary.

**Third, and the part worth carrying into the write-up:** CVE-2025-3987 and
CVE-2025-4462 are two CVE ids for **one line**:

```c
sprintf(acStack_220, "flash set HW_WLAN0_WSC_PIN %s", localPin);  /* 100-byte buffer */
system(acStack_220);
```

unfiltered (3987) and unbounded (4462). That line is **identical in the 2015
image**, which predates both CVEs by ten years. And the four `submit-url` CVEs
are four samples of one idiom that appears in 34 handlers. Twelve of the
fourteen 2025 records describe three defects.

> 📌 **Per-CVE status against the build this unit actually runs** — including
> the upstream Realtek/Boa advisories this section does not cover, and the two
> that this unit's dump refutes — is in
> [`cve-status.md`](cve-status.md). The naming errors above hold on the third
> build too: `formWlWds` and `formStaticDHCP`, all three tables.

---

## 2024 — CVE-2024-51228, and the gap that let it be missed

**This section exists because it was missing, and its absence cost W04-2 a day
of rediscovering something already published.**

> **CVE-2024-51228** (NVD, published 2024-11-27). "An issue in
> TOTOLINK-CX-A3002RU V1.0.4-B20171106.1512 **and TOTOLINK-CX-N150RT
> V2.1.6-B20171121.1002** and TOTOLINK-CX-N300RT V2.1.6-B20170724.1420 and
> TOTOLINK-CX-N300RT V2.1.8-B20171113.1408 and TOTOLINK-CX-N300RT
> V2.1.8-B20191010.1107 and TOTOLINK-CX-N302RE V2.0.2-B20170511.1523 allows a
> remote attacker to execute arbitrary code via the `/boafrm/formSysCmd`
> component."

**`TOTOLINK-CX-N150RT V2.1.6-B20171121.1002` is byte-for-byte the contents of
`/etc/version` in this unit's flash dump.** The CVE names this exact build.

### What that does to W04-2's headline

W04-2 read the resident `boa`, found `formSysCmd` in its dispatch table, traced
`sysCmd` to `system()`, and established at instruction level that the
authorisation gate never runs on that URI. That work stands and its evidence is
in [`auth-flow-2018.md`](auth-flow-2018.md).

**But it is a rediscovery, not a discovery**, and this note is where it should
have been caught before the work started. The correct description of the result
is: *an independent derivation, from the binary, of a claim disclosed in 2024* —
which is exactly what a reproduction project is for, and is a weaker claim than
the one W04-2's first draft made.

### The part that is not a rediscovery

**All three descriptions of this bug disagree about whether it needs
credentials, and the CVSS vector is the odd one out.**

| source | says |
|---|---|
| NVD CVSS 3.1 vector | `AV:A/AC:L/**PR:H**/UI:N/S:U/C:H/I:H/A:H` → 6.8 MEDIUM. **Privileges Required: HIGH** |
| the original researcher, [yckuo-sdc](https://github.com/yckuo-sdc/totolink-boa-api-vulnerabilities) | "An attacker may inject arbitrary shell commands **without credentials**" |
| this project, read from the binary named above | no authorisation runs on `/boafrm/*` in this build — [`auth-flow-2018.md`](auth-flow-2018.md) |

Two of three say no credentials, and the two that agree are the disclosure
itself and an independent reading of the firmware. **If they are right the
vector should be `PR:N`, and the base score is 8.8 HIGH rather than 6.8
MEDIUM.**

That is a checkable disagreement with a published record, and it is the kind
this project has already found twice — `CVE-2025-3992` and `CVE-2025-3995` name
endpoints that 404 on this firmware because their names were transcribed from a
PoC rather than from the binary. A CVSS vector is transcribed the same way.

> **Scope.** The reading is static. It goes to no one until W05/W06 demonstrates
> it on the hardware, and a score correction is worth exactly nothing without
> that.

### How this note failed, and what changes

The CVE list here jumped from 2019–2020 straight to 2025. **Nothing in this
project had ever searched the 2024 series**, and the reason is visible in the
section heading above it: the searches were organised around *disclosure events*
this project already knew about — Pierre Kim 2015, Adamczyk 2019, the 2025 batch
— rather than around the product. A survey anchored on events finds the events
you started with.

Two things follow, and the second matters more:

1. The 2024 series is now in this table.
2. **The trigger for re-surveying is no longer "a new week starts" but "a new
   build string is identified".** W02 read `2018-01-10` off four binaries and
   nobody searched for it; W04-2 read `V2.1.6-B20171121.1002` out of
   `/etc/version` and the CVE that names that string was found by the author
   pasting a link, not by this project. **A build string is a search term, and
   this project had one for two weeks without using it.**

---

## 2023 — `formRoute` / `subnet` was already published, and it is not the defect this project recorded

**Searched 2026-08-17, before the test that would have decided it.** This is the
first time the rule the section above ends with was applied deliberately rather
than in hindsight, and it changed an answer inside one query.

| how it was searched | what came back |
|---|---|
| `TOTOLINK N150RT formRoute subnet` — **by product** | nothing about `formRoute`. Every result was a `formWsc` CVE |
| `formRoute boafrm Realtek SDK subnet` — **by handler** | **Cisco Talos TALOS-2023-1894 / CVE-2023-41251**, first page |

Talos read the Realtek **rtl819x Jungle SDK v3.4.11** (via the LevelOne
WBR-6013, `RER4_A_v3411b_2T2R_LEV_09_170623`) and reported, in `formRoute`, on
the `subnet` parameter:

> a fixed 100-byte stack buffer `tmpBuf`, formatted with `sprintf()` into
> `"Invalid Netmask: <subnet>"` with no bounds check, reached when the netmask
> validation fails. **Purely memory corruption — no `system()`, no shell.**

**Three consequences, and the second is the one that costs this project
something.**

1. **The handler and the parameter are not unexamined ground.** `D-1` in
   [`docs/disclosure.md`](../docs/disclosure.md) is described as this project's
   own, with no CVE. The *parameter* has had one since 2023.
2. **It predicts, with a mechanism, that `P3-2` is a tooling artefact.**
   `BoaGate`'s R2 rule flags `form_formRoute` / `subnet` as reaching `system()`
   in all three builds, and W04's hand reading never saw it. Talos, reading the
   same SDK family, found a `sprintf` into a fixed buffer at that parameter.
   **An `sprintf` site mis-classified as a `system()` site is the cheapest
   explanation available**, and `P3-2`'s refutation condition — frozen before any
   packet was sent — says exactly that: *the tool is wrong, R2 has to be
   rewritten, and it affects the other two builds' conclusions too.*
3. **It does not settle it.** Different vendor, different SDK point release, and
   `sprintf`-into-a-buffer and `system()`-on-a-string can both exist in one
   handler. What it does is turn `P3-2` from "does this fire?" into "does this
   fire, *and* is our tool reading the same line Talos read?" — which is a better
   question and needs the same single request to answer.

> **The prediction was not touched.** It is frozen and hashed, and finding prior
> art that argues against it is not a licence to edit it. The prior art is
> recorded here with its date; the test runs as written. Either the instrument
> is vindicated or this is instrument bug 25 — and the second outcome is worth
> more, because R2's count feeds three builds' worth of conclusions.

**And the meta-result stands on its own:** the by-product search returned
nothing and the by-handler search returned a Talos advisory on the first page.
That is the 2024 lesson — *a build string is a search term* — generalised: **a
handler name is a search term too, and it crosses vendors while a product name
does not.** This SDK ships under dozens of brands; anything found by grepping
`/bin/boa` should be searched the way the SDK is written, not the way the box is
labelled.

---

## 2023 — a published bypass against this exact Boa version, and it does not apply

**Searched 2026-08-17 night, while running the per-handler search
`docs/disclosure.md` step 2 requires before reporting anything.** The search was
for the password handler; what it surfaced was a version match.

**exploit-db 51139 — Boa Web Server 0.94.13–0.94.14, authentication bypass by
HTTP method.** Upstream Boa parses `HEAD` without applying the security
constraint that protects `GET` and `POST`; the response functions then test
`if (req->method != M_HEAD)` only to decide whether to send a body. So a `HEAD`
request reaches protected resources without credentials.

**This unit runs `Boa/0.94.14rc21`.** That is inside the affected range, and
nothing in this project had ever sent a `HEAD` request.

Measured under emulation (`tools/qemu-env.sh serve`, this unit's own binary and
its own flash, no device attached):

| request | result |
|---|---|
| `GET /password.htm` (gated) | `302` |
| **`HEAD /password.htm` (gated)** | **connection closed, no response at all** |
| `HEAD /login.htm` (exempt) | `HTTP/1.0 200 OK` |
| `OPTIONS` / `PUT` / `FOO` on a gated page | `501 Not Implemented` |

**The bypass does not apply to this build.** `HEAD` on a protected page returns
nothing rather than the content — verified on the wire with `nc`, not just
through `curl`'s status code — while `HEAD` on an exempt page is served
normally and `boa` survives all of it. Three methods, three different
treatments, which is itself a fingerprint.

Why the upstream flaw does not carry over is not settled here: this build's
authorisation is Realtek's `process_header_end`, not upstream Boa's, so the code
the advisory describes may simply not be the code that runs. **That is an
inference, and the instruction-level reading has not been done.**

> 🔴 **This measurement was taken without a frozen refutation condition, and
> that breaks this project's one non-negotiable rule.** The register exists so
> that "what would failure look like" is written before the request is sent;
> here the search turned up a candidate and it was tested in the same minute.
> So it is **not** recorded in `test-cases.toml` — `rtcase record` would need a
> prediction that was never frozen, and back-filling one is precisely the thing
> the freeze hash exists to prevent.
>
> It is written here as what it is: an observation made outside the discipline.
> A W07 case gets frozen first and then run **on the device**, because
> everything above is emulated and the scope has to say so.
>
> Second time in one night. The other was reading a previous week's prose as a
> measurement — see `PROGRESS.md` W06. Both times the rule was known and neither
> time was it applied, which is the difference between having a rule and having a
> checker.

---

## Not searched yet — three items, and this section exists because of §"How this note failed"

**2026-08-18.** Three findings from W07 Day 2 are candidates for being this
project's own, and **none has had the by-handler search**. Listing them here
rather than only in `docs/disclosure.md` is the change §"How this note failed"
promised: the gap that let CVE-2024-51228 go unfound for two weeks was that this
file had no 2024 entries and nothing recorded that it had not looked.

| finding | register | what to search, and it is not the product name |
|---|---|---|
| A second credential pair compared against never-written stack, matched by empty fields | `P2-9` · `D-15` | `boa` + "uninitialised"/"uninitialized stack" + authentication; Realtek rtl819x SDK + Basic auth bypass; the `process_header_end` symbol; and **`Boa 0.94.14rc21` on its own** — the 2023 search in §"a published bypass against this exact Boa version" found one that did not apply, and the next one might |
| A 16-byte append past a 256-byte buffer in `dnsspoof` | `P6-10` · `D-17` | the binary name is generic and collides with the well-known dsniff tool, so search the *behaviour*: Realtek captive-portal DNS responder, `wan_disconnect`, `StartDnsSpoof` |
| Plain-HTTP firmware fetch on an unauthenticated trigger, with additive-checksum-only image validation | `P8-10` + `P9-13` · `D-12` | `sl.totolink.software`; `batchRemoteUpgrade`; `submit_rfw_upgrade`; TOTOLINK + firmware update + MITM |

**A fourth is already known not to be ours.** `miniigd`'s SOAP `system()` site
(`D-16`) is almost certainly **CVE-2014-8361** — CISA KEV, a Mirai payload since
2015. It is listed under the CVE table above, not here.

**The rule this section is enforcing**: a search by *product* returned nothing
for `D-1` and a search by *handler* returned Cisco Talos on the first page. Until
each row above has had the second kind, none of them is described as new, in this
repository or anywhere else.

## Sources

- Pierre Kim, TOTOLINK series, 2015-07-16 — <https://pierrekim.github.io/blog/2015-07-16-backdoor-credentials-found-in-4-TOTOLINK-products.html> and companion posts
- Cisco Talos, TALOS-2023-1894 / CVE-2023-41251, `boa formRoute` stack overflow in the Realtek rtl819x Jungle SDK — <https://talosintelligence.com/vulnerability_reports/TALOS-2023-1894>
- Boa 0.94.13–0.94.14 HEAD-method authentication bypass — <https://www.exploit-db.com/exploits/51139>
- Błażej Adamczyk, "TOTOLINK and other Realtek SDK based routers — full takeover", 2019-12-16 — <https://sploit.tech/2019/12/16/Realtek-TOTOLINK.html>
- Full Disclosure posting, 2020-01-23 — <https://seclists.org/fulldisclosure/2020/Jan/36>
- CVE-2019-19824 — <https://www.tenable.com/cve/CVE-2019-19824>
- Pierre Kim, advisory text naming N150RT-V2 — <https://pierrekim.github.io/advisories/2015-totolink-0x02.txt>
- The 2025 series against this model — <https://nvd.nist.gov/vuln/detail/CVE-2025-4462> and neighbours
- CVE-2024-51228 — <https://nvd.nist.gov/vuln/detail/CVE-2024-51228>
- yckuo-sdc, TOTOLINK Boa API vulnerabilities — <https://github.com/yckuo-sdc/totolink-boa-api-vulnerabilities>
