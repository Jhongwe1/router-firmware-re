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

---

## Sources

- Pierre Kim, TOTOLINK series, 2015-07-16 — <https://pierrekim.github.io/blog/2015-07-16-backdoor-credentials-found-in-4-TOTOLINK-products.html> and companion posts
- Błażej Adamczyk, "TOTOLINK and other Realtek SDK based routers — full takeover", 2019-12-16 — <https://sploit.tech/2019/12/16/Realtek-TOTOLINK.html>
- Full Disclosure posting, 2020-01-23 — <https://seclists.org/fulldisclosure/2020/Jan/36>
- CVE-2019-19824 — <https://www.tenable.com/cve/CVE-2019-19824>
- Pierre Kim, advisory text naming N150RT-V2 — <https://pierrekim.github.io/advisories/2015-totolink-0x02.txt>
- The 2025 series against this model — <https://nvd.nist.gov/vuln/detail/CVE-2025-4462> and neighbours
