# Disclosure register

What this project has that might be new, what state each item is in, and the
rule that decides what gets published here and what does not.

This file exists because the policy in `README.md` — *anything genuinely new
goes to TWCERT/CC before any public discussion* — had no list attached to it.
A policy with no register is a sentence, not a process: nothing records which
findings it applies to, so nothing can be checked against it later.

## The publication rule

Three categories, and the line between them is the thing to argue with:

| | what it is | published here |
|---|---|---|
| **Finding** | "this handler takes this parameter into `system()`, at this address, in this binary" | **yes.** That is the research, and stating it is how anyone else can check it |
| **Reproduction** | a procedure that produces the effect, with a request that can be copied | **only once the issue is public.** For a CVE disclosed in 2024, a `poc/` directory is a reproduction of published work. For something unreported, it is a zero-day recipe |
| **Tradecraft** | persistence, anti-forensics, lateral movement, credential harvesting on a live host | **no.** No gate in this project asks for it, it produces no checkable fact about this device, and `README.md` scopes it out. Nine such items are listed with their reasons in [`test-ledger.md`](../test-ledger.md) |

The rule is one sentence: **findings are published, reproductions follow the
disclosure state, tradecraft is not published at all.**

It has a consequence worth stating plainly, because a reader will notice it
anyway: several items below are **already named in `PROGRESS.md` and under
`notes/`**, with addresses. That is deliberate and consistent with the rule —
naming a defect is a finding. What is held back is the reproduction: the
request, the payload, the ordering.

## Status of the candidate originals

"Candidate" is the operative word. Every entry here is a **static reading of a
binary; nothing has been demonstrated on the hardware**, and the literature
search that missed CVE-2024-51228 for two weeks is recent enough to assume
another one may be missed. An item is not original because a search came up
empty; it is original when a search that *would* have found prior art comes up
empty. That search is [`notes/prior-art.md`](../notes/prior-art.md), and it has
been wrong once.

| # | finding | evidence | already stated publicly here | status | what changes it |
|---|---|---|---|---|---|
| **D-1** | ~~`form_formRoute` / `subnet` reaches `system()` in **all three** builds~~ | `BoaGate` R2 — **and the tool was wrong** | yes — PROGRESS open #6 | ❌ **withdrawn 2026-08-17** | Two independent reasons, and the order they arrived in matters. **Prior art, found before the test:** Cisco Talos TALOS-2023-1894 / CVE-2023-41251 reports this exact parameter in the same Realtek rtl819x SDK family as a 100-byte `sprintf` stack overflow with **no `system()` anywhere** — published 2023, and a search by *handler* found it on the first page where a search by *product* had returned nothing. **Then the measurement:** `P3-2` fired on the device produced zero command execution, while `localPin` on `formWsc` produced four ICMP echo requests through the same oracle. `BoaGate` R2 mis-classified an `sprintf` site as a `system()` site, and that rule feeds conclusions about all three builds |
| **D-2** | ~~Omitting `submit-url` makes the handler copy into a read-only literal — a one-request unauthenticated crash~~ | W04, measured on V2.1.2 | yes — README G3 notes | ❌ **does not reproduce on this build, 2026-08-17** | Register `P4-1`, and this row's own text said what to do: *"if it does not reproduce on this build it is a V2.1.2 finding and nothing more."* It does not. A POST body omitting `submit-url` returns 200 on `formNtp` and `formWlanSetup` and the server survives. `P4-3` went further and refuted the mechanism with a **positive** witness: `formNtp` echoes `submit-url` into its `Location` header, and 800 bytes come back as 799 `A`s with no truncation at 100 — so the value provably reaches the code that consumes it and nothing happens. This build does not use the `lastUrl[100]` idiom W04 measured in 2015 |
| **D-3** | The authorisation gate's exemption comparison is an unanchored substring test, so an exempt string placed anywhere in a path may satisfy it | [`auth-flow-2018.md`](../notes/auth-flow-2018.md), instruction level | yes — the mechanism is described | **held** | Register `P2-2`. The 2020 build has the same shape, which is why this one matters beyond this unit |
| **D-4** | An empty stored administrator password skips the credential comparison entirely, **and an unauthenticated request can set it empty** | measured on the device 2026-08-17; the branch at `0x0040bd18` read at instruction level in W04-2 | **yes, and that is a defect** — `runsheet.md` `A3.11.2` carries the complete request. This column said `no` until 2026-08-18 | **held** | Register `P10-4` **and `P10-3`**, and the pair is the finding. This row used to say *"reachability matters more than the branch: if no unauthenticated path can set it empty, this is a curiosity"*. **There is such a path and it needs nothing.** `formPasswordSetup` carries `Cusername`/`Cpassword` fields for the current credentials and the handler does not check them, so an unauthenticated POST that does not know the current password changes it. Set it empty and `password.htm` returns 200 and 5,322 bytes of real HTML with no `Authorization` header at all — and a **wrong** password is also accepted, so the comparison is skipped rather than matched. Next step is the per-handler prior-art search, not a report: the search that found Talos for D-1 has not been run for this handler |
| **D-5** | Two published advisories name endpoints that exist in no dispatch table (`formWlwds`, `fromStaticDHCP`) | three `root_form[]` recoveries | yes — [`cve-status.md`](../notes/cve-status.md) | **publishable now** | Not a vulnerability: a correction to a public record. It goes to the CNA/MITRE, not to TWCERT/CC, and nothing is embargoed |
| **D-6** | CVE-2024-51228 is scored `PR:H`; it requires no credentials at all | **demonstrated on the device 2026-08-17** — [`poc/02-command-injection.md`](../poc/02-command-injection.md) | yes | ✅ **publishable now, and published** | `P3-3` fired: a POST carrying no `Authorization` header made the router send ICMP echo **requests** to the bench host, and returned `cat /etc/version` through the document root. **And the same request WITH valid credentials behaves identically**, which is what rules out "something else was carried in" — an unauthenticated success on its own does not. If `PR:N` is right the base score is **8.8 HIGH** rather than 6.8 MEDIUM. The vulnerability itself has been public since 2024-11-27, so nothing is embargoed and the reproduction ships in `poc/`. This is a correction to a public record and it goes to the CNA, not to TWCERT/CC |
| **D-7** | `wan_disconnect` invokes a DNS-spoofing helper that is present in this rootfs | [`n150rt-unit-2018.json`](../reports/n150rt-unit-2018.json) | yes — `notes/` | **not a finding yet** | Register `P6-10`. Currently a behaviour nobody has looked at, not a defect |
| **D-8** | ~~Three unread areas: the remote-upgrade helper's outbound connections, the upload handler's `filename` field, two shipped factory private keys~~ | inventory only | yes | ⚙️ **two of three resolved 2026-08-18** | Register `P8-10`, `P8-18`, `P10-7`. The upload `filename` came back **empty** — `FUN_0044f360` returns an offset and never copies the value (`P8-18` refuted, [`firmware-upgrade-path.md`](../notes/firmware-upgrade-path.md)), and the remote-upgrade helper came back **loaded**, which is now **D-12**. `P10-7` also closed the same day and also empty: this unit ships **one** factory key, `/etc/dropbear_rsa_host_key`, and **no SSH daemon at all** — no `dropbear`, no `sshd` — while `sysconf` still installs the key to `/var/dropbear` on every boot. `P6-11` measured port 22 closed, which is the same answer from the other side. It remains a shipped-identical-key item for other models that *do* run dropbear, which is `P8-21`'s question and not this unit's. So: three unread areas, one of them worth the reading, and the row could not have told you which |
| **D-9** | An unauthenticated, **well-formed** POST carrying only `submit-url` holds the device's single-process web server for 4.7–9.7 s; about forty-five in sequence stop it answering entirely, and nothing respawns it | measured twice on the device, [`BENCH-LOG.md`](../BENCH-LOG.md) 2026-08-17 afternoon; per-request `elapsed_ms` in the transcripts | yes — the numbers are in `PROGRESS.md` and `BENCH-LOG.md` | **held, and deliberately unclassified** | Distinct from **D-2**: that one omits `submit-url` and writes into a read-only literal. This one is a legal request. Three things are unmeasured and all three change what it is — whether *one* request suffices, how long a single stall lasts, and whether prior art already covers it. Register: none yet; it came out of `P1-4` |
| **D-10** | An unauthenticated configuration write also overwrites the **factory-default** region: `COMPDS` moved in the same 19 fields as `COMPCS` plus the four that had distinguished them, each to `COMPCS`'s value. So "restore factory defaults" would restore whatever was last written | 64 KiB snapshots either side, attributed field by field; `libapmib`'s own checksum passes on both regions | yes — `PROGRESS.md` W05 close-out | **held** | The impact claim depends on `P9-9` (does reset actually restore from `COMPDS`), which is scheduled W07 and is destructive. Until that runs, the mechanism is measured and the *consequence* is inference. Also answers W04-2 open #20 — what persists `COMPCS` |

| **D-11** | **A single unauthenticated, well-formed POST to one form handler removes the web server until the device is power-cycled.** No payload, no overlong parameter, no credentials | measured on the device 2026-08-17 with a control: three POSTs of the same shape to a different handler immediately before it were all served normally, then one to the handler in question returned nothing at all and the listening socket was gone 30 s later, while ICMP to the device stayed at 1.6 ms | the numbers and the mechanism are in `PROGRESS.md`; **the handler name is not published here** | **held** | Distinct from **D-9** (a legal POST *stalls* the single-process server 4.7–9.7 s, and roughly forty-five in sequence stop it) and from the withdrawn **D-2**. This is **one** request and the effect is permanent, because `rcS` starts `boa` once and nothing respawns it. It also revises W05's own reading of its data: that session attributed the outage to *volume*. Whether the W05 transcript shows this same handler is a re-reading of that record, not something 2026-08-17 measured. No register row yet — it came out of a handler census, not a planned test |

| **D-12** | **The firmware upgrade path accepts an image on an unkeyed additive checksum, fetches it over plain HTTP from a hard-coded host, and the handler that starts the fetch is outside the authorisation gate** | [`firmware-upgrade-path.md`](../notes/firmware-upgrade-path.md) — `UpgradeByData` @ `0x00460798` read at instruction level; the two checksum functions at `0x00460600` and `0x00460690`; the trigger at `FUN_0044f7b4` from `form_formSaveConfig` | the mechanism and the addresses are published; **no request that performs it is** | **held — static only** | Register `P9-13` + `P8-10`. Three facts stack: acceptance is `memcmp` on a 4-byte section tag plus a sum-to-zero checksum, with no signature, no `hw_version` and no anti-rollback anywhere in the binary; the transport is `http://sl.totolink.software`, hard-coded, with no TLS library in the rootfs; and `POST /boafrm/formSaveConfig` does not enter the gate on this build (`auth-flow-2018.md`, and `P2-1` measured it). **Nothing has been executed.** What changes it: the DNS-redirect demonstration on the isolated segment, which is `P8-10`'s device half. The *write* half stays with `P9-10` in W08 — this unit is the single point of failure for G2 and G4 and a failed reflash ends the project, not just the test. **Prior art, searched 2026-08-18, and it splits this row in two.** The *image-validation* half is **not original**: Cisco Talos **CVE-2023-34435 / TALOS-2023-1874** reports arbitrary firmware update on `/boafrm/formUpload` in this same SDK, filed CWE-347, *"never checks the validity of the uploaded firmware"*. What survives as this project's own contribution there is narrower and more useful — *which* check exists and at what address, because "there is no check" and "the check is an unkeyed additive sum at `0x00460a98`" are different sentences. The *plain-HTTP remote fetch* half — `sl.totolink.software`, `CheckRFW`, `batchRemoteUpgrade` — was searched by domain, by symbol and by binary name and **nothing matched**. One disagreement worth keeping: Talos scores CVE-2023-34435 `PR:H`, and on this build the remote-update trigger is a `POST /boafrm/formSaveConfig`, which `P2-1` measured as outside the gate — the same `PR` disagreement as `D-6` |
| **D-13** | **With both settings regions invalid, the boot script loads factory defaults and enables telnet — and `root` / `123456` (uid 0) has been byte-identical since 2015** | [`config-failopen.md`](../notes/config-failopen.md) — `/bin/startup.sh` lines 19–47, and seven damage states measured under emulation with [`failopen-probe.sh`](../tools/failopen-probe.sh) | the branch and the line numbers are published | **held — the branch is measured, the outcome is not** | Register `P8-24`, recorded `partial`. The fail-open branch **is** entered: with both region signatures zeroed, `startup.sh` printed its own line 23. What it then writes could not be observed, because `flash default-sw` and `flash reset1` die on a `qemu-user` SIGBUS while a plain `flash set` in the same environment succeeds — so the boundary is the recovery path, not the emulator in general. Reaching the branch needs `COMPDS`'s **decompressed header** damaged specifically: `test-dsconf` checks `sig=6G, ver=3, len=31878` and tolerates a flipped payload byte, while `test-csconf` also runs `mib_tlv_init` and does not. What changes it: the device experiment named in the note, which needs a settings-area snapshot first and is not scheduled before W08 |
| **D-18** | **The gate's session arm is keyed on the client's IP address and expires against a variable nothing writes, so it stops working 601 seconds after boot** | [`auth-session-ip.md`](../notes/auth-session-ip.md) — the comparison at `0x0040bff8`–`0x0040c060`; `beforeuptime` at `0x004899dc` has **one** reference in the whole binary and it is the read, confirmed by Ghidra and by an independent encoding scan whose control in the same run returns a read *and* a write | mechanism and addresses | **held — static only** | No register row: it came out of reading forty instructions past the question the listing was generated for. Two consequences and the second is the one that matters. **First**, `P2-7`'s "authorisation is per-request HTTP Basic" is correct in practice and incomplete in mechanism — there is a second arm and it is dead. **Second**, for the first ten minutes of uptime it is *not* dead, so the device has a security state nobody has measured: a gated page served to whichever address logged in last, with no credentials on the request. The emulator cannot reach that state — `sysinfo()` under `qemu-user` returns the **host's** uptime — so this needs the bench, in `A3.2`, which is the only station that owns the clock. Prior art: Talos's CVE-2023-47677 describes a CSRF protection on this SDK's `boa` with a *different* mechanism; not resolved whether they are the same feature |
| **D-15** | **The Basic-auth path compares the supplied credentials against a second pair of stack buffers that nothing ever writes, and a request whose username and password are both empty matches them — skipping the whole authorisation block** | [`uninit-credential-pair.md`](../notes/uninit-credential-pair.md) — the three reads at `0x0040bd4c`, `0x0040bd7c`, `0x0040bd94` and the absence of any write across all 1,964 bytes of `process_header_end`; fired on **two** emulation profiles | the mechanism and the addresses; **no ready-to-send request appears anywhere in this repository, and none is to be added while this row says "held"** | 🔴 **held — and it is the most serious item in this table** | Register `P2-9`. Distinct from `D-4`: there the *stored* password is empty and the comparison is skipped at `0x0040bd18`; here the stored password is `admin`, the comparison runs, and it succeeds against a buffer nothing filled in. It reproduces on the **published** V2.1.2 image with a different `boa` binary, so it is not a property of this unit's unpublished build — and **V3.4.0 does not have it**: its `process_header_end` equivalent `FUN_00409fd8` carries one credential pair, both halves filled by `apmib_get` immediately above the comparison, and no `req->0xb0 = 2` branch at all. So the window is 2015 → 2018 present, 2020 removed, which bounds who to tell and also means the vendor may already know. **Two of the three preconditions are now met, 2026-08-18.** (a) *What the higher level buys:* **nothing.** `req->0xb0` is read at exactly two instructions, both inside `process_header_end`, and the second — `0x0040be24`/`0x0040be2c` — branches past the entire authorisation block on any non-zero value, so 2 and 1 are equivalent. The row's wording is corrected above from "at a higher privilege level" to "skipping the whole authorisation block", which is both more accurate and more serious. (b) *Prior art:* searched four ways — by function (`process_header_end` + uninitialised stack), by version (`Boa/0.94.14rc21`), by SDK (rtl819x Jungle + auth bypass), by symbol (`check_auth_flag`) — and **nothing matches**; Talos's fifteen reports on this SDK contain no authentication defect at all, and CVE-2007-4915 is the same function with the opposite mechanism. **What is now known that weakens "original":** the SDK source is public (two vendors' GPL drops on GitHub), and it shows the buffers are `admin_name`/`admin_password` fed by `MIB_SUPER_NAME`/`MIB_SUPER_PASSWORD` — which **no build in this family fetches**, 2015 included. So the defect is visible to anyone reading the source next to any of these binaries. (c) *Still outstanding:* **confirmation on the device**, three requests and no power cycle. Nothing goes to anyone before that |
| **D-16** | **`miniigd` puts five SOAP-supplied values into a double-quoted shell string and calls `system()`**, on 52869/tcp — open 2026-08-16 (`P1-2`), **closed** 2026-08-18, **open again and measured** 2026-08-19; see the status column | [`three-unread-binaries.md`](../notes/three-unread-binaries.md) — `FUN_004083a8`, the whole `AddPortMapping` handler read at instruction level: `GetValueFromNameValueList` ×5 → `strcpy` (unbounded) → `sprintf("echo \"%s,%s,%s,%s,NA,%s\" >> %s")` → `system` at `0x004085fc` | yes — mechanism and addresses | **held, and probably NOT original** | **The port state in this row carried no date until 2026-08-19, and that was wrong in a way that would have travelled.** `P1-2` found 52869 open on 2026-08-16 and this row said so in the present tense. On 2026-08-18 `P6-1` and `P8-7` found it **closed**, `miniigd` absent from `ps` and no `InternetGatewayDevice` answering SSDP — because `UPNP_ENABLED` read `0`, which **this project's own W05 unauthenticated POST round** had written, and this build ships no UPnP page through which a user could put it back. Both measurements were correct when taken; neither sentence carried a *when*, and six committed files repeated the first one. The 2026-08-19 reset restored `COMPCS` byte-for-byte to its 2026-08-16 content, so the flag is `1` again and the port is very probably open again — **and nobody has measured it**, which is worse than being out of date: a claim that came back true by accident is indistinguishable from one that was checked. A reported open port has to be a port someone looked at, so this row was not reportable on its network state until the next bench visit re-ran `P6-1`. **That visit happened the same night, and it changed this row twice over.** 52869 answers, the IGD description document is served, and the code half stands — the SOAP value reaches an `iptables` rule with **no validation whatever**, visibly: a `NewInternalClient` of twenty-two `A` characters becomes `DNAT … to:255.255.255.255:83`, which is `inet_addr()` returning `INADDR_NONE` and the value being used regardless. **But the command execution this row is about did not happen.** The ICMP oracle — proved good on the same boot minutes earlier through an independent `formSysCmd` injection — stayed silent, and `/bin/miniigd` **terminates** instead: `ps` two minutes later shows no such process. So **CVE-2014-8361 is not reproduced on this build**, and what is on the record instead is `D-19`. This row keeps its *static* claim (the `system()` call at `0x004085fc` with five unescaped SOAP values on the path) and loses its dynamic one, and that split is the whole of what tonight added. Register `P6-1`, still open because its refutation is phrased about device behaviour and reading code cannot satisfy it. This is almost certainly **CVE-2014-8361**, the Realtek SDK `miniigd` SOAP command execution — CISA KEV, and a Mirai payload since 2015. If so the finding is *"a 2018 build ships it on an open port"*, which is verification, not discovery, and the prior-art search must run before anything is reported. Also corrected here: the control endpoint on this binary is `/upnp/control/WANIPConnection`, not `miniupnpd`'s `/upnp/control/WANIPConn1` that the working notes carried — a bench probe of the documented path would have returned a clean negative with the port open the whole time |
| **D-17** | **`dnsspoof` appends a fixed 16-byte record at `buffer + n` where `n` is the received length and the buffer is 256 bytes**, so a DNS query of 245 bytes or more writes past it and corrupts three pointer locals | [`three-unread-binaries.md`](../notes/three-unread-binaries.md) §3 — the whole 3,820-byte binary read; frame at `sp-0x190`, buffer at `sp+0x54`, the three pointers at `sp+0x158`/`sp+0x15c`/`sp+0x160`, `memcpy` at `0x00400ae4` | yes — mechanism and offsets | **held — candidate original, and bounded** | Register `P6-10`. Two of the corrupted pointers are live: one is dereferenced by the next query's name scan, the other is a `memcpy` destination, and neither is re-initialised per iteration. **The limit is stated with the finding**: `recvfrom` caps the read at 256, so the furthest write is `sp+0x163` while the saved `ra` is at `sp+0x18c` — forty bytes out of reach, and the bytes that land are the answer record's own, so this is not a return-address overwrite. Reachable only while the daemon runs, which is when the WAN is down — and `boa` can start it (`dnsspoof_enb`). Nothing executed; `P6-10` cannot close until the device says which of four DNS binaries is actually bound to 53. **Prior art searched 2026-08-18 by behaviour rather than by binary name** — the name collides with dsniff's tool — using *Realtek captive-portal DNS responder*, `wan_disconnect`, `StartDnsSpoof`: **nothing matched.** Everything returned was CVE-2022-27255 (eCos SIP ALG) or the 2021 UPnP/SSDP series |
| **D-19** | **One unauthenticated SOAP request terminates `/bin/miniigd`**, and the trigger is any `NewInternalClient` that `inet_addr()` rejects — not a shell metacharacter | [`three-unread-binaries.md`](../notes/three-unread-binaries.md) §2, 2026-08-19 subsection, and `BENCH-LOG.md` `T-79` / `T-82` / `T-83`. Three requests on three boots, each ending in a closed connection with no response and `52869` refusing afterwards; `ps` over a telnet shell two minutes later shows **no `miniigd` process at all** and nothing respawns it, so only a power cycle brings the daemon back. The control is what makes it a result: `NewInternalClient=10.1.1.1` is answered HTTP 200 and the daemon survives it and a subsequent read, while twenty-two `A` characters — **no metacharacter anywhere** — kill it exactly as a backtick payload does | **no** — the mechanism is named here and nothing else | ⏸ **held, and NOT SEARCHED** | **This row is not reportable and has not been reported**, because [`notes/prior-art.md`](../notes/prior-art.md) has not been run against it. The search has to cover UPnP/IGD denial of service on the Realtek `rtl819x` SDK by behaviour rather than by binary name, the way `D-17` had to, because `miniigd` self-reports `Server: miniupnpd/1.4` and that is a different codebase's name. Two things also unmeasured, and both change the severity: **why** it dies — the unbounded `strcpy` at `0x0044851c` is on the same path but a 22-byte value is a poor fit for it — and whether the daemon is reachable from the WAN at all, which `P8-7`'s second half has not settled. Reported severity would be "LAN-side, single request, recoverable by power cycle", and the honest framing is that a device whose owner never touches UPnP loses a service they were not using |
| **D-14** | The gate's redirect copies the client's `Host` header verbatim into `Location`, on every gated path, unauthenticated | [`host-header-and-redirect.md`](../notes/host-header-and-redirect.md) — seventeen `Host` values against the emulated server, with exempt/gated controls holding | yes | **held — low, and stated as low** | Register `P8-5`. An open redirect and nothing more: **both sinks encode correctly**, URL-encoding in the header and HTML entities in the body, so it is not XSS and the note says so as plainly as it states the finding. Its real weight is that it settles `P8-6`'s precondition — an arbitrary `Host` is accepted because `check_host` at `0x00410470`, which would reject nine of the seventeen, sits behind `if (vhost_root != NULL)` and `VHostRoot` is commented out in this build's `boa.conf`. Correct code that nothing calls |

**Nothing in the table has been reported to anyone, and the two that changed
state on 2026-08-17 changed in opposite directions.** `D-6` became publishable
because the hardware demonstrated it and the underlying CVE is two years public.
`D-1` and `D-2` were **withdrawn** — one because a tool was wrong and published
prior art said so before the test ran, the other because the defect simply is not
in this build. That is what this register is for: it is as much a record of
claims retracted as of claims made, and a table that only ever grows is a table
nobody is checking.

**`D-15` is now the most serious item here, and `D-4`, `D-11` and `D-12` are next.**

**The prior-art searches ran on 2026-08-18** — `D-15`, `D-17` and both halves of
`D-12` — and the outcome is recorded in each row and in
[`notes/prior-art.md`](../notes/prior-art.md). Two of the four came back empty,
one came back matched (`D-12`'s image validation is CVE-2023-34435), and the
method that produced the most is one the procedure below did not name: **search
for the SDK's *source*, not only for its advisories.** The rtl819x `boa` source
is in two vendors' public GPL drops, and reading it is what turned `D-15` from
"a comparison against uninitialised stack" into "a deleted supervisor account
whose comparison stayed". Step 2 of the procedure is amended accordingly.

**`D-4` and `D-11` still have not had theirs.** The search that produced Talos
for `D-1` took one query and overturned a finding; running it *after* a report
would be the wrong order.

`D-12` arrived on 2026-08-18 and it is the first item in this table whose class
is *supply chain* rather than *memory safety* or *authorisation*. That is worth
noting because the whole table above was produced by looking at what can be sent
**to** the device, and this one came from asking what the device connects **out**
to — a question the project had listed as unexamined since W04-2 and never
asked. Three rows of `D-8` were opened on the same principle and one of the three
paid.

### A governance defect, found 2026-08-18 by writing the next bench step

**This file's own rule and this repository's practice have disagreed since
`A3.11.2` was written, and nothing would have caught it.**

The rule at the top of this file says a **reproduction** — *"a procedure that
produces the effect, with a request that can be copied"* — is published **only
once the issue is public**. `D-4` is not public. `runsheet.md` `A3.11.2` carries
the complete `curl` that performs it, and this file's `already stated publicly
here` column for `D-4` said `no`.

Both statements were in the repository at the same time and only one could be
true. The column is corrected above.

**Why no check found it.** `tools/check-runsheet.py` reads `runsheet.md` and
`RUNBOOK.md` and verifies that every command is real and every cross-reference
resolves. It does not read this file. `tools/rtcase.py` reads the register. **No
tool reads `docs/disclosure.md` at all**, so a claim in it can contradict a
command in the runsheet indefinitely.

That is the same shape as instrument bug 22 — *"a checker's blind spot held the
bug it was written for"* — and as bug 28, a refuted claim surviving in a place no
checker reads. This one is worse than either, because what it governs is what
gets published about an unreported defect in shipping firmware.

**Decided, and applied from here on:** the reasoning, the addresses, the expected
result and the controls go in `runsheet.md`, which is what makes a step
executable and checkable. **The sendable request goes to a gitignored path**, and
the runsheet points at it. `D-15`'s bench step is written that way and is the
first one that is.

**Not decided:** whether `A3.11.2` should be redacted retroactively. `P10-3` and
`P10-4` were run from it and recorded, so removing it now would leave two results
whose procedure is not in the repository — which is its own kind of dishonesty.
Left as the author's call, and left visible rather than quietly fixed.

## Not original, and worth saying so

- **CVE-2024-51228 is not this project's discovery.** It names this exact build
  string and was published on 2024-11-27. The reachability result here is an
  independent derivation of a disclosed claim. `notes/prior-art.md` had no 2024
  entries at all when the work was done, and the gap is recorded there rather
  than smoothed over.
- **The `submit-url` overflow idiom, the `localPin` injection, the plaintext
  credentials and the 2015 backdoor account all have identifiers.** Locating
  them in a third build is verification work, not discovery.
- **The `localPin` *overflow* has one too, and it was already in this
  repository.** On 2026-08-18 this project measured full `$pc` and `s0`–`s6`
  control from a single unauthenticated POST to `/boafrm/formWsc`, on two builds,
  and wrote it up as an unsearched finding. It was not unsearched:
  [`notes/prior-art.md`](../notes/prior-art.md) has listed **CVE-2025-4462**
  against `/boafrm/formWsc` → `localPin` since W04, and
  [`notes/cve-status.md`](../notes/cve-status.md) carries the same row marked 🟥
  with the sentence *"The same line of source as 3987, and identical in the 2015
  image."* **The register answered the question and nobody opened it.** A web
  search run the next day returned the same identifier, which is the least useful
  way to be right:

  | identifier | what it names |
  |---|---|
  | **CVE-2025-4462** | N150RT 3.4.0-B20190525, `/boafrm/formWsc`, `localPin`, buffer overflow, remote, public PoC, disclosed 2025-05-09 |
  | CVE-2026-7218 | the same parameter on N300RT 3.4.0-B20250430 |
  | CVE-2025-3987 | command injection at the same endpoint |
  | CVE-2019-19824 | the `localPin` command injection already tracked here |
  | CVE-2021-35395 | the Realtek SDK `submit-url` overflow — the `(B)` half of the idiom |

  Of those, only CVE-2026-7218 and CVE-2021-35395 were new to this repository;
  the rest were already in the register.

  Neither build measured here is a build any of those name, and the frame offsets
  (`ra` at 509 on the 2017 build, 513 on the 2015 one) are not published anywhere
  the four search paths reached. **That is a smaller claim than the one that was
  nearly written, and it is the true one** — but it is also, read the other way,
  a *larger* one than "we rediscovered a CVE": `cve-status.md` predicted
  statically that the overflow is identical in the 2015 image, and that
  prediction is now measured. A confirmed static prediction is worth more than a
  rediscovery, and it is what should have been written.

  **Step 2 of the procedure below is amended because of this.** It used to say
  "search". Searching the internet first is what produced a day-late answer to a
  question this repository had already answered, twice in one day — the second
  being `formSysCmd`, where `notes/formSysCmd-analysis.md` had carried the
  conclusion since W04. The order is now: **`notes/prior-art.md` first, then
  `notes/cve-status.md`, then outside sources** — and a web result that merely
  agrees with the register is not a finding, it is a check.
- **What the search did *not* find** is the `(A)` half: a *missing* parameter
  making the accessor return the address of a pooled `""` literal, which the
  vendor's `OK_MSG` macro then writes twelve bytes through. Every published item
  above is the long-value case. A negative search result is not a claim of
  novelty and is recorded here as what it is — four paths, nothing found,
  `notes/absent-parameter-strcpy.md` §4.

## Procedure when something does become reportable

> **Step 0, added 2026-08-18 and out of order on purpose: open
> [`notes/prior-art.md`](../notes/prior-art.md) before writing the finding up,
> not before reporting it.** The register is searchable by handler and by
> parameter and it is 30 KB of work already done. Twice on 2026-08-18 a
> conclusion was re-derived from outside sources that the register already held,
> and in both cases the write-up had already been committed by the time anyone
> looked. **A register nobody opens is a register that does not exist.**

1. Demonstrate it on the hardware, with the request and response recorded, and
   register the result (`tools/rtcase.py record`) so the claim carries evidence.
2. Re-run the prior-art search **for that specific handler and parameter**, not
   for the product. The 2024 miss happened because the search was by product
   name and label rather than by the build string in hand.
   **2a. And search for the SDK's source, not only for advisories about it.**
   Added 2026-08-18. The rtl819x `boa` source ships in several vendors' public
   GPL drops; reading one of them named the defect behind `D-15`, cross-checked
   this project's recovered MIB table against an outside source for the first
   time, and surfaced a second defect nobody had looked for. A search by
   *symbol* — a function or variable name out of the binary — is what finds
   source, where a search by handler finds advisories and a search by product
   finds nothing. All three are now cheap and none substitutes for another.
3. Report to **TWCERT/CC** with the reproduction. The device is end-of-life and
   the vendor's history here is a five-year, three-step remediation, so plan for
   no vendor response rather than treating silence as an anomaly.
4. Hold public discussion of the reproduction until the coordinator closes the
   case or 90 days pass from the report, whichever is first. Record the date the
   clock started **in this file**, in the same commit as the report.
5. If the coordinator declines the case — plausible for end-of-life hardware —
   that is a decision, and it gets written here with its date. It is not a
   licence to publish immediately; it is the point at which the author decides,
   on the record.

## What this file is not

It is not a list of everything wrong with the device. That is
[`notes/cve-status.md`](../notes/cve-status.md), and most of it has been public
for years. This file tracks only the subset where **this project might be the
first to say something**, because that is the only subset the disclosure policy
constrains.
