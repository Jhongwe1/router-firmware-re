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

---

## Verdicts

Nineteen rows. `E` = exploitable on this hardware, `C` = conditionally
exploitable, `N` = not exploitable, `?` = mechanism established, effect not
demonstrated.

| # | class | site | address | value | verdict | evidence |
|---|---|---|---|---|---|---|
| 1 | command execution | `formSysCmd` | `0x0044ee2c` | `sysCmd` | **E** — fired on the device, unauthenticated, three independent channels | [`test-results.json`](../reports/test-results.json) `P3-3` · [`poc/02-command-injection.md`](../poc/02-command-injection.md) |
| 2 | command execution | `formWsc` | — | `localPin` | **E** — four ICMP echo requests from the device | [`test-results.json`](../reports/test-results.json) `P3-1` |
| 3 | command execution | `formWsc` | — | `targetAPSsid` | **C** — interpolated inside shell double quotes, length-checked | [`ghidra-argtrace-unit-2018.json`](../reports/ghidra-argtrace-unit-2018.json) |
| 4 | command execution | `miniigd` `AddPortMapping` | `0x004085fc` | `NewInternalClient` + 4 more | **?** — five SOAP values into `sprintf("echo \"%s,…\" >> %s")` then `system()`, nothing between parse and shell; **52869/tcp open**. Almost certainly CVE-2014-8361 | [`ghidra-xref-unit-2018-miniigd.json`](../reports/ghidra-xref-unit-2018-miniigd.json) · [`three-unread-binaries.md`](three-unread-binaries.md) |
| 5 | authentication | `process_header_end` | `0x0040bd48` / `0x0040bd90` | *(none needed)* | **E under emulation** — a second credential pair at `sp+0x18`/`sp+0x38` that nothing writes, matched by empty fields, granting a **higher** level than the real credentials. Reproduces on the published V2.1.2 image; **absent in V3.4.0** | [`uninit-credential-pair.md`](uninit-credential-pair.md) · [`test-results.json`](../reports/test-results.json) `P2-9` |
| 6 | authentication | `formPasswordSetup` | — | *(none needed)* | **E** — unauthenticated password change on the device; the handler ignores its own current-password fields | [`test-results.json`](../reports/test-results.json) `P10-3` |
| 7 | authentication | `process_header_end` | `0x0040bd18` | *(stored value)* | **E** — an empty stored password skips the comparison, and #6 can set it empty | [`test-results.json`](../reports/test-results.json) `P10-4` |
| 8 | authorisation | the gate's exemption list | `0x0040be90`–`0x0040bfe4` | the URI | **C** — thirteen unanchored `strstr` tests on one string | [`auth-flow-2018.md`](auth-flow-2018.md) · `P2-2` |
| 9 | authorisation | `check_host` | `0x00410470` | `Host` | **N as a defence** — correct validator, verdict enforced at `0x0040bca4`, and **unreachable**: `0x0040bbec` branches past the whole block when `vhost_root` is NULL, and `VHostRoot` is commented out. 17 of 17 hosts accepted | [`host-header-and-redirect.md`](host-header-and-redirect.md) · [`ghidra-xref-unit-2018-checkhost.json`](../reports/ghidra-xref-unit-2018-checkhost.json) |
| 10 | open redirect | the gate's redirect | `0x0040e7e4` | `Host` | **E, low** — the client's `Host` is copied verbatim into `Location`, unauthenticated, on every gated path. **Not XSS**: both sinks encode | same as #9 |
| 11 | stored XSS | ~30 ASP list renderers | 105 format strings | any rendered value | **?** — `req_write_escape_html` exists, is correct, and has six callers, all upstream Boa status pages. No Realtek renderer calls it; data goes into `<td>` and into attribute values as raw `%s`. The five 2025 CVEs are five instances of one omission | [`xss-escaping.md`](xss-escaping.md) · [`ghidra-xref-unit-2018-escape.json`](../reports/ghidra-xref-unit-2018-escape.json) |
| 12 | supply chain | `form_formSaveConfig` → `FUN_0044f7b4` | `0x0044f88c` | `submit_rfw_*` | **?** — `http://sl.totolink.software` hard-coded, no TLS in the rootfs, and the trigger is outside the gate | [`firmware-upgrade-path.md`](firmware-upgrade-path.md) · [`ghidra-xref-unit-2018-rfw.json`](../reports/ghidra-xref-unit-2018-rfw.json) |
| 13 | image validation | `UpgradeByData` | `0x00460a98` / `0x00460aec` | the uploaded image | **E as a weakness** — acceptance is a 4-byte tag `memcmp` plus an **unkeyed additive checksum**, 16-bit for `cr6c`/`r6cr` and 8-bit for `w6cg`. No signature, no `hw_version`, no anti-rollback anywhere in the binary | [`firmware-upgrade-path.md`](firmware-upgrade-path.md) · [`ghidra-xref-unit-2018-upgrade.json`](../reports/ghidra-xref-unit-2018-upgrade.json) |
| 14 | memory safety | `dnsspoof` | `0x00400ae4` | a DNS query ≥ 245 bytes | **?** — a fixed 16-byte record appended at `buffer + n` past a 256-byte stack buffer, corrupting three pointers that are set once before the loop. **Bounded**: `recvfrom` caps `n` at 256 and the saved `ra` is 40 bytes out of reach | [`three-unread-binaries.md`](three-unread-binaries.md) · [`ghidra-xref-unit-2018-dnsspoof.json`](../reports/ghidra-xref-unit-2018-dnsspoof.json) |
| 15 | fail-open | `/bin/startup.sh:19–47` | line 43 | the settings regions | **? (partial)** — both regions invalid and the boot script loads defaults and runs `flash set TELNET_ENABLED 1`; the branch is **measured**, the write is not, because the recovery write dies on a qemu SIGBUS while a plain `flash set` in the same environment succeeds | [`config-failopen.md`](config-failopen.md) · [`failopen-unit-2018.json`](../reports/failopen-unit-2018.json) |
| 16 | availability | 39 of 57 handlers | — | one well-formed POST | **? under emulation** — 39 stop answering after a single unauthenticated POST carrying only `submit-url`; 19 survive; `formSysCmd` is among the **survivors** | [`handler-sweep-unit-2018.json`](../reports/handler-sweep-unit-2018.json) · `P4-7` |
| 17 | availability | one handler | — | one well-formed POST | **E** — measured on the device: the web server does not come back without a power cycle | `docs/disclosure.md` `D-11` |
| 18 | memory safety | the `submit-url` idiom | 63 sites | `submit-url` | **N on this build** — 800 bytes come back as 799 with no truncation at 100; the `lastUrl[100]` idiom W04 measured in 2015 is not what this build does | [`test-results.json`](../reports/test-results.json) `P4-1`, `P4-3` |
| 19 | command execution | `form_formRoute` / `subnet` | — | `subnet` | **N — withdrawn.** `BoaGate` R2 mis-classified an `sprintf` site as a `system()` site; published prior art (Talos, CVE-2023-41251) said so before the test, and the device produced zero command execution | `docs/disclosure.md` `D-1` |

Two of nineteen were **withdrawn or refuted findings of this project's own**
(#18, #19), and one more (#9) is a defence that reads as present and is not.
A table that only grows is a table nobody is checking.

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

**Boa's own status pages escape correctly.** Six functions call
`req_write_escape_html` and all six are the 403/404/301/302/411 pages plus
`send_redirect_perm`. A `Host` carrying markup comes back URL-encoded in
`Location` and entity-encoded in the body. The defect in #11 is not that the
project lacks an escaper.
→ [`xss-escaping.md`](xss-escaping.md)

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

## New, subject to a prior-art search that has not run

Three items are candidates for being this project's own, and **none has had the
per-handler search that step 2 of `docs/disclosure.md`'s procedure requires**.
That search took one query and overturned a finding once already.

| | why it might be new | why it might not |
|---|---|---|
| **#5**, the uninitialised credential pair | W03 saw the shape in V2.1.2 and correctly refused to call it a finding; nothing in `notes/prior-art.md` covers it | it is in a published image anyone can download, so anyone could have found it |
| **#14**, the `dnsspoof` write | a 3.8 KB binary specific to this vendor's build | Realtek SDK components are widely analysed |
| **#12** + **#13**, plain-HTTP update on an unauthenticated trigger with an additive-checksum-only image check | the combination is specific to this build | each half is a common embedded pattern and #4 shows this SDK's history is already documented |

**#4 is almost certainly not new** — CVE-2014-8361 is on CISA's KEV list and has
been a Mirai payload since 2015. The finding there is *"a 2018 build ships it on
an open port"*, and that is verification.

---

## What this week did not do

- **Nothing in rows 4, 11, 12, 14 or 15 has been executed.** They are readings of
  binaries. Five register cases stay deliberately open for that reason rather
  than being recorded `partial` to make a count move.
- **The `P4`/`P5` exploitation block did not run.** No offset was measured, no
  `epc` was shown controllable, no chain was assembled. The environment for it
  exists on two profiles and the work is scheduled.
- **The six-profile differential harness was not built.** The one differential
  answer this week needed — does 2020 have #5 — came from twenty minutes of
  reading three binaries. The harness is still worth building for divergences
  nobody thought to look for, which is a different job.
