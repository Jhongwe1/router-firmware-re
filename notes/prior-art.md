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
> That is wrong; they are Adamczyk's. Corrected here because an interviewer who
> knows the field will notice, and because the two disclosures point at
> different binaries.

---

## 2015 — Pierre Kim

Four write-ups covering backdoor accounts, RCE across 15 models, a
backdoor binary, and CSRF/XSS. N150RT-V2 is listed among the affected models.

Relevant claims to verify against our own images:

| Claim | Where it should show up | Status in our images |
|---|---|---|
| Hard-coded Telnet credentials (`root` / `onlime_r`, password `12345`) | `/etc/passwd`, or hard-coded in a binary | **`/etc/passwd` does not exist** in either image — so authentication cannot be libc-based. Whatever credential check exists lives inside a binary. Open item for W03. |
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

| CVE | Endpoint / parameter | Class |
|---|---|---|
| CVE-2025-6299 | `/boa/formWSC` → `targetAPSsid` | command injection |
| CVE-2025-4462 | `/boafrm/formWsc` → `localPin` | buffer overflow |
| CVE-2025-3992 | `/boafrm/formWlwds` → `submit-url` | buffer overflow |
| CVE-2025-3995 | `/boafrm/fromStaticDHCP` → `Hostname` | XSS |

Naming check against our own handler inventory: both images export `formWsc`
and `formStaticDHCP`; **neither exports `formWlwds`** (both have `formWlWds`,
different capitalisation) and neither exports `fromStaticDHCP`. Endpoint names
in CVE records are frequently transcribed from a PoC rather than from the
binary, so these need confirming against the dispatch table before any of them
is treated as an N150RT finding.

---

## Sources

- Pierre Kim, TOTOLINK series, 2015-07-16 — <https://pierrekim.github.io/blog/2015-07-16-backdoor-credentials-found-in-4-TOTOLINK-products.html> and companion posts
- Błażej Adamczyk, "TOTOLINK and other Realtek SDK based routers — full takeover", 2019-12-16 — <https://sploit.tech/2019/12/16/Realtek-TOTOLINK.html>
- Full Disclosure posting, 2020-01-23 — <https://seclists.org/fulldisclosure/2020/Jan/36>
- CVE-2019-19824 — <https://www.tenable.com/cve/CVE-2019-19824>
