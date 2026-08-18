# Systematic bug hunt

W07's deliverable. The rule for this file is that **every verdict points back to
a file under `reports/`**, and a row that cannot is deleted rather than softened.

## Method, and why it is not a CVE list

The work list was **computed, not chosen**. Three sources, in this order:

1. **The CI gate's own output.** `BoaGate` reports 134 findings on this unit's
   build. Subtract every site a published advisory explains and **91 remain, of
   which zero are R2** — the rule meaning "reaches `system()`". Every
   command-execution candidate the gate can see is already accounted for by a
   CVE or by a finding this project has itself withdrawn.
   → [`reports/bughunt.json`](../reports/bughunt.json)
2. **The islands.** Handlers in `root_form[]` that no shipped page names —
   14 on this build, 11 on V2.1.2 — computed against the docroot the vendor's own
   `flash extr` produces, because `/web` in the extracted rootfs is a symlink to
   an empty `/var/web` and a naive grep would call every handler an island.
   → [`reports/bughunt.json`](../reports/bughunt.json)
3. **The blank areas** — binaries and code paths nobody had read, listed in
   `docs/disclosure.md` as `D-8` precisely so that *unexamined* could not quietly
   become *clean*. Three were listed; **one of the three paid**, and the row
   could not have told you which in advance.

The fourth source turned out to be the productive one and it was not in the plan:
**asking what the device connects *out* to.** Everything above looks at what can
be sent to it.

And a fifth arrived on 2026-08-18, later than it should have: **reading the
vendor's SDK source.** The Realtek rtl819x `boa` source ships in at least two
public GPL drops from unrelated vendors. This project reads binaries because
TOTOLINK publishes no source, and it had never asked whether *somebody else's*
drop of the same SDK was public. One afternoon with it named the mechanism behind
row 5, cross-checked this project's recovered MIB table against an outside source
for the first time, and produced row 20 — which nobody was looking for.
→ [`prior-art.md`](prior-art.md) §2026-08-18

---

## Verdicts

Twenty-two rows. `E` = exploitable on this hardware, `C` = conditionally
exploitable, `N` = not exploitable, `?` = mechanism established, effect not
demonstrated.

| # | class | site | address | value | verdict | evidence |
|---|---|---|---|---|---|---|
| 1 | command execution | `formSysCmd` | `0x0044ee2c` | `sysCmd` | **E** — fired on the device, unauthenticated, three independent channels | [`test-results.json`](../reports/test-results.json) `P3-3` · [`poc/02-command-injection.md`](../poc/02-command-injection.md) |
| 2 | command execution | `formWsc` | — | `localPin` | **E** — four ICMP echo requests from the device | [`test-results.json`](../reports/test-results.json) `P3-1` |
| 3 | command execution | `formWsc` | — | `targetAPSsid` | **C** — interpolated inside shell double quotes, length-checked | [`ghidra-argtrace-unit-2018.json`](../reports/ghidra-argtrace-unit-2018.json) |
| 4 | command execution | `miniigd` `AddPortMapping` | `0x004085fc` | `NewInternalClient` + 4 more | **?** — five SOAP values into `sprintf("echo \"%s,…\" >> %s")` then `system()`, nothing between parse and shell. Almost certainly CVE-2014-8361. **The port carries a date, and it changed twice**: 52869/tcp open 2026-08-16 (`P1-2`), **closed** 2026-08-18 (`P6-1`, `P8-7` — `UPNP_ENABLED=0`, written by this project's own W05 POST round, and no UPnP page in this build to undo it), flag restored by the 2026-08-19 reset and **not measured since**. The code half is unaffected | [`ghidra-xref-unit-2018-miniigd.json`](../reports/ghidra-xref-unit-2018-miniigd.json) · [`three-unread-binaries.md`](three-unread-binaries.md) |
| 5 | authentication | `process_header_end` | `0x0040bd48` / `0x0040bd90` | *(none needed)* | **E on this hardware** — measured on the silicon 2026-08-18, and this row said `E under emulation` until 2026-08-19 because nobody re-read it after the bench: six requests against `/blank.htm` with both halves of the Basic header empty return **200 / 333 bytes, byte-identical (`sha256 bc56c91c…`) to the real-credential body**, while a wrong password gets 302. The mechanism is the SDK's **supervisor** credential pair (`MIB_SUPER_NAME` / `SUPER_PASSWORD`, ids 180/181), which **no build in this family has ever fetched**, compared first and matched by two empty fields. A non-zero `auth_flag` then branches past the *entire* authorisation block at `0x0040be2c`. Reproduces on the published V2.1.2 image; V3.4.0 removed the dangling comparison | [`uninit-credential-pair.md`](uninit-credential-pair.md) · [`test-results.json`](../reports/test-results.json) `P2-9` |
| 6 | authentication | `formPasswordSetup` | — | *(none needed)* | **E** — unauthenticated password change on the device; the handler ignores its own current-password fields | [`test-results.json`](../reports/test-results.json) `P10-3` |
| 7 | authentication | `process_header_end` | `0x0040bd18` | *(stored value)* | **E** — an empty stored password skips the comparison, and #6 can set it empty | [`test-results.json`](../reports/test-results.json) `P10-4` |
| 8 | authorisation | the gate's exemption list | `0x0040be90`–`0x0040bfe4` | the URI | **C** — thirteen unanchored `strstr` tests on one string | [`auth-flow-2018.md`](auth-flow-2018.md) · `P2-2` |
| 9 | authorisation | `check_host` | `0x00410470` | `Host` | **N as a defence** — correct validator, verdict enforced at `0x0040bca4`, and **unreachable**: `0x0040bbec` branches past the whole block when `vhost_root` is NULL, and `VHostRoot` is commented out. 17 of 17 hosts accepted | [`host-header-and-redirect.md`](host-header-and-redirect.md) · [`ghidra-xref-unit-2018-checkhost.json`](../reports/ghidra-xref-unit-2018-checkhost.json) |
| 10 | open redirect | the gate's redirect | `0x0040e7e4` | `Host` | **E, low** — the client's `Host` is copied verbatim into `Location`, unauthenticated, on every gated path. **Not XSS**: both sinks encode | same as #9 |
| 11 | stored XSS | ~30 ASP list renderers | 105 format strings | any rendered value | **?** — `req_write_escape_html` exists, is correct, and has six callers, all upstream Boa status pages. No Realtek renderer calls it; data goes into `<td>` and into attribute values as raw `%s`. The five 2025 CVEs are five instances of one omission | [`xss-escaping.md`](xss-escaping.md) · [`ghidra-xref-unit-2018-escape.json`](../reports/ghidra-xref-unit-2018-escape.json) |
| 12 | supply chain | `form_formSaveConfig` → `FUN_0044f7b4` | `0x0044f88c` | `submit_rfw_*` | **?** — `http://sl.totolink.software` hard-coded, no TLS in the rootfs, and the trigger is outside the gate | [`firmware-upgrade-path.md`](firmware-upgrade-path.md) · [`ghidra-xref-unit-2018-rfw.json`](../reports/ghidra-xref-unit-2018-rfw.json) |
| 13 | image validation | `UpgradeByData` | `0x00460a98` / `0x00460aec` | the uploaded image | **E as a weakness, and NOT this project's finding** — Talos reported it on this SDK as **CVE-2023-34435**, CWE-347. What is added here is *which* check exists: a 4-byte tag `memcmp` plus an **unkeyed additive checksum**, 16-bit for `cr6c`/`r6cr` and 8-bit for `w6cg`, with no signature, no `hw_version` and no anti-rollback anywhere in the binary. "There is no check" and "the check is an unkeyed sum at this address" are different sentences | [`firmware-upgrade-path.md`](firmware-upgrade-path.md) · [`prior-art.md`](prior-art.md) · [`ghidra-xref-unit-2018-upgrade.json`](../reports/ghidra-xref-unit-2018-upgrade.json) |
| 14 | memory safety | `dnsspoof` | `0x00400ae4` | a DNS query ≥ 245 bytes | **?** — a fixed 16-byte record appended at `buffer + n` past a 256-byte stack buffer, corrupting three pointers that are set once before the loop. **Bounded**: `recvfrom` caps `n` at 256 and the saved `ra` is 40 bytes out of reach | [`three-unread-binaries.md`](three-unread-binaries.md) · [`ghidra-xref-unit-2018-dnsspoof.json`](../reports/ghidra-xref-unit-2018-dnsspoof.json) |
| 15 | fail-open | `/bin/startup.sh:19–47` | line 43 | the settings regions | **? (partial)** — both regions invalid and the boot script loads defaults and runs `flash set TELNET_ENABLED 1`; the branch is **measured**, the write is not, because the recovery write dies on a qemu SIGBUS while a plain `flash set` in the same environment succeeds | [`config-failopen.md`](config-failopen.md) · [`failopen-unit-2018.json`](../reports/failopen-unit-2018.json) |
| 16 | availability | ~~39 of 57 handlers~~ ~~`formSchedule`, and only it~~ **five handlers, one address** | `strcpy` at `libc+0x2721c`, storing to `0x004725d0` | the *absence* of one parameter | **? — corrected twice, and sharper each time.** The 39 were the emulator (unaligned stores in `libapmib`'s TLV serialiser; [`tools/alignfix/`](../tools/alignfix/) removes the divergence). Re-run with a pristine flash and a `submit-url`-only body: **one** died. Re-run with an *empty* body: **five** — `formSchedule`, `formAdvanceSetup`, `formDnsv6`, `formOpMode2`, `formSSH` — and all five fault at the same instruction storing to the same address, the pooled `""` literal, which lives in a `PT_LOAD` mapped `R-X`. The control is the sixth case: `webpage=` *present and empty* takes the same branch and survives, so the finding is the accessor's default, not the branch | [`absent-parameter-strcpy.md`](absent-parameter-strcpy.md) · [`crash-triage-unit-2018.json`](../reports/crash-triage-unit-2018.json) · [`paramfuzz-unit-2018.json`](../reports/paramfuzz-unit-2018.json) · `P4-7` |
| 20 | authorisation | `process_header_end` | `0x0040bff8`–`0x0040c060` | the client's IP address | **? — a session arm nobody had read.** Gated pages are also served to whichever address logged in last, expiring when `nowuptime - beforeuptime >= 601`. **Measured 2026-08-19: the window is login+601, not uptime 601, and it reopens on every login.** The store is at `0x0044f140` inside `form_formLogin`, reached through the GOT, so the storing instruction's immediate is `0` and names no address. The earlier "one reference and it is the read" was a property of the scanners, not of the firmware: the gate uses `lui`+`%lo` and `form_formLogin` uses `%got`, and both instruments modelled only the first. The control passed because `nowuptime` is reachable the way they could see. Expiry does `strcpy(authipaddr,"0.0.0.0")` at `0x0040c018`; the threshold is `sltiu …,0x259` | [`auth-session-ip.md`](auth-session-ip.md) · [`mipsref-unit-2018-authsession.json`](../reports/mipsref-unit-2018-authsession.json) |
| 17 | availability | one handler | — | one well-formed POST | **E** — measured on the device: the web server does not come back without a power cycle | `docs/disclosure.md` `D-11` |
| 18 | memory safety | the `submit-url` idiom | 63 sites | `submit-url` | **N on this build, for the long-value half** — 800 bytes come back as 799 with no truncation at 100; the `lastUrl[100]` idiom W04 measured in 2015 is not what this build does. **This row said "the class" and meant one half of it**; the absent-parameter half is row 16, and on the *published* 2015 image it is seven handlers rather than five | [`test-results.json`](../reports/test-results.json) `P4-1`, `P4-3` · [`crash-triage-v2.1.2.json`](../reports/crash-triage-v2.1.2.json) |
| 19 | command execution | `form_formRoute` / `subnet` | — | `subnet` | **N — withdrawn.** `BoaGate` R2 mis-classified an `sprintf` site as a `system()` site; published prior art (Talos, CVE-2023-41251) said so before the test, and the device produced zero command execution | `docs/disclosure.md` `D-1` |
| 21 | memory safety | `form_formWsc` / `localPin` — **and it is CVE-2025-4462**, which [`prior-art.md`](prior-art.md) has listed since W04 | offset **509** to the saved `ra` on this build, **513** on V2.1.2 | one POST parameter | **? — a controlled program counter, under emulation, and a confirmation rather than a discovery.** [`cve-status.md`](cve-status.md) predicted statically that the overflow is identical in the 2015 image; measured 2026-08-18, it is, one word further out.** 260 bytes survives, 800 bytes gives `pc = ra = s0..s6 = 0x41414141`; a de Bruijn pattern reads the frame off directly (`s0` at 481 through `ra` at 509, four bytes apart), consistent with `BoaGate`'s own `sp-540` for this parameter. No canary, no `PT_GNU_RELRO`, no PIE, `RWX` `GNU_STACK`, in all three N150RT builds. **Nothing has been jumped to.** The address space under `qemu-user` is not the device's — but the device's *is* now known: two kernel fault messages put `libuClibc` at `0x2aae3000` in `boa`, so `system` is at `0x2ab08460` and the target no longer needs a leak. One boot only, so `P5-2` is `partial` ([`mips-ret2libc.md`](mips-ret2libc.md) · [`libbase-unit-2018.json`](../reports/libbase-unit-2018.json)). What is still missing is `a0`: a computed target is not a call | [`absent-parameter-strcpy.md`](absent-parameter-strcpy.md) §4 · [`crash-triage-unit-2018-wsc.json`](../reports/crash-triage-unit-2018-wsc.json) · `P5-1` |
| 22 | vendor timeline | `root_form[]` across six builds | — | — | **N — not a defect, and it corrects one of this project's own sentences.** `formSysCmd` (CVE-2019-19823) is absent from N150RT V2.1.2 (2015), present in N300RT V2.1.6, in this unit's 2018 build and in N200RE V3.2.0, **still present in N300RT V3.4.0-B20190315**, and absent from N150RT V3.4.0-B20201030. So "3.4.0 removed it" is false as stated: the removal is **per product**, and only six builds side by side show it. This unit's 57 handlers are a **strict subset** of N300RT V2.1.6's 61 | [`formtable-scan-six-builds.json`](../reports/formtable-scan-six-builds.json) · `P5-7` · `P8-21` |

> 🏆 **Row 16 is what this week's method was supposed to produce.** The first
> sweep's answer was *"39 of 57 handlers are fragile"*, which is a number nobody
> can act on and which turned out to be a property of the emulator. Removing that
> one divergence turned it into *"one handler, named"* — and `D-11` measured, on
> the hardware, that **one** unauthenticated POST removes the web server until a
> power cycle, without being able to say which handler it belonged to. **The
> emulated list and the device measurement now agree on the shape and the count,
> and the bench sample has one obvious first pick instead of thirty-nine.**

**Three of twenty are withdrawn or refuted findings of this project's own**
(#16, #18, #19), one more (#13) turned out to have a CVE against it, and one
(#9) is a defence that reads as present and is not. A table that only grows is a
table nobody is checking — and #16 is the sharpest of them, because it was
withdrawn by building the instrument that could tell the emulator's behaviour
from the firmware's rather than by arguing about the caveat the report already
carried.

---

## Areas that are relatively safe, and why

This section is the same size as the one above on purpose. **Being able to say
why nothing happens here is what makes "something happens there" worth
believing.**

**`/boafrm/formUpload`'s `filename` is not a value.** `FUN_0044f360` at
`0x0044f360` returns an integer offset on every path; `filename=` is a landmark
it searches past, never copied, never in a path or a shell string. The classic
`system("mv /tmp/%s …")` is not here.
→ [`firmware-upgrade-path.md`](firmware-upgrade-path.md) §3

**The `eval` sites in the boot scripts are dead, each for a different reason.**
`snmpd.sh` is the only script with a real sink — nine `eval` calls over `flash
get` results, and `flash get` prints string values inside double quotes where a
backtick still executes. It is dead because **none of its nine MIB names exists
in this build's table**: two instruments agree, and the script asks for
`SNMP_ROCOMMUNITY` where the table has `SNMP_RO_COMMUNITY`. `smb.sh` and
`smbbak.sh` capture MIB values but feed a config file and argv after word
splitting, with no `eval` — and `smbd`, `smbpasswd`, `nmbd` and `snmpd` are all
absent from `/bin` while three scripts driving them ship.
→ [`config-failopen.md`](config-failopen.md) §4

**The SDK's unbraced `check_auth_flag` assignment is dead here.** The vendor
source sets a *global* alongside `req->auth_flag` and does it with no braces —
the `goto fail` shape — so **matching only the username** sets it regardless of
the password, in all four arms. This binary compiles that faithfully: the branch
at `0x0040bda8` is taken unconditionally with `v1 = 2` in its delay slot, and
`0x0040be20` stores it. It buys nothing, because `0x004899d8` has **exactly one
reference in the whole 485,012-byte binary and it is that write.** Two
instruments agree — Ghidra's reference model and an encoding scan with no symbol
table — and the scan's control address in the same run comes back with a read and
a write, so it is not simply blind. A real upstream defect, unreachable here.
→ [`uninit-credential-pair.md`](uninit-credential-pair.md) §4

**Boa's own status pages escape correctly.** Six functions call
`req_write_escape_html` and all six are the 403/404/301/302/411 pages plus
`send_redirect_perm`. A `Host` carrying markup comes back URL-encoded in
`Location` and entity-encoded in the body. The defect in #11 is not that the
project lacks an escaper.
→ [`xss-escaping.md`](xss-escaping.md)

**Forty-seven handlers carry the `submit-url` idiom and only five reach it on a parameter-free POST.** The other forty-two return earlier — a missing mode, a missing index, a table lookup that fails — so the tail that writes into the defaulted pointer is never executed. That ratio is why W06's refutation of `P4-1` was reasonable: three handlers drawn from forty-seven, none of which happened to be one of the four. **A refutation inherits the coverage of whatever produced it, and three hand-picked handlers is a coverage nobody wrote down.**
→ [`absent-parameter-strcpy.md`](absent-parameter-strcpy.md) §3

**And "return earlier" was the wrong description; the vendor's own source names the mechanism.** In the Realtek SDK the `strcpy` lives inside the `OK_MSG(url)` macro, whose sibling `ERR_MSG(msg)` takes a message and never touches `url`. So the forty-two are not handlers that return early — they are handlers that reach the **error** path. That also makes the defect a property of a macro rather than of any handler, and its `#else` arm carries no `strcpy` at all, so **whether a build has it is a build-time flag.** Measured 2026-08-18: on the published V2.1.2 image the count is **seven, not five**, and two of the extra — `formNtp`, `formWlanSetup` — are handlers W06 used as controls precisely because they survive on *this* build.
→ [`absent-parameter-strcpy.md`](absent-parameter-strcpy.md) §2a · [`crash-triage-v2.1.2.json`](../reports/crash-triage-v2.1.2.json)

**`execl` carries no request data.** Every `execl` in every build is
`(path, "<script>.sh", NULL)`. W04 established it and it has not changed; the
question it redirects to — what those scripts read — is answered above.

**The WAN-side DHCP client does not expand its input into a shell.**
`/usr/share/udhcpc/eth1.bound` is one line: `sysconf conn dhcp $interface $ip
$subnet $router $dns`. The values become argv, not a command, and **`hostname`
and `domain` are not passed at all**. The injection question moves one hop into
`sysconf` and has not been answered there — which is a smaller and better-defined
question than the one it replaced. Register `P8-19`.

**The 2020 build removed the second credential pair.** `FUN_00409fd8` has one
comparison, both halves filled by `apmib_get` immediately above it, and no
higher level. #5 is bounded to 2015 and 2018.
→ [`uninit-credential-pair.md`](uninit-credential-pair.md) §3a

**`test-dsconf` resists a payload byte flip.** The factory-default region's
validity check reads the *decompressed* header — it prints what it wants,
`sig=6G, ver=3, len=31878` — and survives a flipped byte deep in the LZSS
stream, while `test-csconf` also runs `mib_tlv_init` and does not. So #15 needs
`COMPDS`'s header damaged specifically, not "the settings area corrupted".
→ [`config-failopen.md`](config-failopen.md) §1

**The shipped factory key is unusable.** `/etc/dropbear_rsa_host_key` is
installed to `/var/dropbear` on every boot by `sysconf`, and **there is no SSH
daemon in the rootfs at all**. `P6-11` measured port 22 closed, which is the same
answer arrived at from the other side.

**And the largest one: 91 of the gate's 134 findings are residue with no
command-execution site among them.** 63 of the 91 are the `submit-url` class that
row #18 refutes on this build, and four more parameters are named in `P4-4`'s
frozen prediction and were refuted with it. What is left uncharacterised is about
a dozen parameters, `comment` (5 sites) the most frequent.

---

## New — and the searches ran, 2026-08-18

`docs/disclosure.md` step 2 requires a per-handler search before anything is
reported. It ran for all three candidates, four ways each. **One came back
matched.**

| | outcome |
|---|---|
| **#5**, the supervisor credential pair | **no prior art found** — searched by function (`process_header_end` + uninitialised stack), by version (`Boa/0.94.14rc21`), by SDK (rtl819x Jungle + auth bypass) and by symbol (`check_auth_flag`). Talos's fifteen reports on this SDK are ten stack overflows, one heap overflow, two ACE, one CSRF and one firmware-update issue — **no authentication defect of any kind**. CVE-2007-4915 is the same function with the opposite mechanism, a write where this is a missing write. **But**: the SDK source is public in two vendors' GPL drops, so the defect is visible to anyone reading it beside any of these binaries. "Nobody published it" is weaker than "nobody could see it" |
| **#14**, the `dnsspoof` write | **no prior art found** — searched by *behaviour*, because the binary name collides with dsniff's tool. Everything returned was CVE-2022-27255 (eCos SIP ALG) or the 2021 UPnP/SSDP series |
| **#12** + **#13** | **split.** #13's image validation **is CVE-2023-34435** (Talos, CWE-347) on this SDK — not ours. #12's plain-HTTP fetch from `sl.totolink.software`, searched by domain, by symbol (`CheckRFW`, `submit_rfw_upgrade`) and by binary (`batchRemoteUpgrade`), **found nothing**. One disagreement survives and it is the `D-6` shape again: Talos scores CVE-2023-34435 `PR:H`, and on this build the remote-update trigger is a `POST /boafrm/formSaveConfig`, which `P2-1` measured as outside the gate |
| **#20**, the IP-address session arm | **not resolved.** Talos's CVE-2023-47677 reports a CSRF protection in this SDK's `boa` described as "prevents API calls until an HTML form page loads first". That is not the mechanism in these instructions, which is an address comparison with an uptime-derived expiry. Same feature seen from outside, or a different SDK point release — unknown, and said so |

**#4 is almost certainly not new** — CVE-2014-8361 is on CISA's KEV list and has
been a Mirai payload since 2015. The finding there is *"a 2018 build ships it on
an open port"*, and that is verification.

**Nothing has been reported to anyone**, and nothing will be before the device
confirms it: everything in #5 and #20 is static or emulated.

---

## What this week did not do

> **Rewritten 2026-08-19.** Every sentence below was true when it was written on
> 2026-08-18 — *before* two bench visits and the desk session that closed the
> week. Four of them had become false and nothing said so, in the document that
> is this week's own deliverable. That is the same failure the `52869/tcp`
> sentences had, in the same week, and it is why this heading now carries a date.

- **Nothing in rows 4, 11, 12, 14 or 15 has been executed.** They are readings of
  binaries. Register cases stay deliberately open for that reason rather than
  being recorded `partial` to make a count move. **Row 20 came off this list on
  2026-08-19** (the session arm was measured on the device); **row 4 is off it in
  code but not in reach** — 52869/tcp was open on 2026-08-16 and closed on
  2026-08-18 by this project's own POST round, and no SOAP action has ever been
  invoked.
- **~~The `P4`/`P5` exploitation block did not run.~~** It ran. `P5-1` measured
  the frame directly: 800 bytes into `formWsc`'s `localPin` gives
  `pc = ra = s0..s6 = 0x41414141`, and a de Bruijn pattern puts the saved `ra` at
  **offset 509** — under emulation. `P5-6` then showed an emulated crash
  reproducing on the silicon at the same address, which is what makes the
  emulator admissible as a filter. `P5-2` computed the target: `libuClibc` at
  `0x2aae3000` in `boa`, **`system` at `0x2ab08460`**, from two kernel fault
  messages and the ELF files ([`mips-ret2libc.md`](mips-ret2libc.md)).
  **What is still true is the part that matters: nothing has been jumped to.**
  A controlled `pc` and a computed target are not a chain — `a0` would have to
  point at a command string and that has not been shown.
- **The six-profile differential harness was not built**, and this is the one
  item of the week's plan that is simply not met. The two differential answers
  the week needed — does 2020 have row 5, and has *any* build ever fetched the
  supervisor credentials — came from reading three binaries and from a fifty-line
  encoding scan. The harness is still worth building for divergences nobody
  thought to look for, which is a different job, and it is not scheduled.
- **`beforeuptime` is only half-answered.** ~~The dead arm is measured.~~
  **Both arms are now measured, and the register's mechanism was wrong.** On
  2026-08-19 the window turned out to be **login + 601 seconds and to reopen on
  every login**, not 601 seconds after boot — and the store two independent
  instruments had reported as absent is at `0x0044f140` inside `form_formLogin`,
  reached through the GOT so that no instruction names the address.
- **~~The largest gap is unchanged: none of this is on silicon.~~** Two bench
  visits closed 21 rows on the hardware. **Row 5 — the most serious thing in this
  table — is confirmed on the silicon**, not under emulation: an empty-empty
  Basic header returns a gated page byte-for-byte identical to the
  real-credential one. Row 20 likewise.
- **The largest gap now is different, and smaller.** Rows 4, 11, 12, 14 and 15
  are readings, not executions; row 4's target has been unreachable since this
  project disabled it; and `P5-2` rests on a single boot, so the `system` address
  is a property of the 2026-08-18 boot until `runsheet.md` `A3.23.0` runs.
