# Attack surface — v2

> **v2 (W04).** The ranking below is the W01 map, kept as written. What W03 and
> W04 measured is folded in as a header on each section, because the *changes*
> are the interesting part: this page ranked `formLogin` and the upload handlers
> above `formWsc`, and `formWsc` is where the unfiltered `system()` calls are.
>
> **Per-handler answers now exist.** Which request parameters reach which sink,
> in both builds, is generated rather than argued:
> [`reports/ghidra-argtrace-2.1.2.json`](../reports/ghidra-argtrace-2.1.2.json),
> [`reports/ghidra-argtrace-3.4.0.json`](../reports/ghidra-argtrace-3.4.0.json)
> — 39 handlers in 2015 and 30 in 2020 are reached by a named request parameter.
> Authorisation status per handler is one answer, not a column:
> **in 2015 no `/boafrm/` handler is behind the gate at all**
> ([`auth-flow.md`](auth-flow.md)); **in 2020 every POST is**, subject to an
> unanchored substring exemption ([`auth-flow-2020.md`](auth-flow-2020.md)).


Derived from [`reports/`](../reports/), which `make recon` regenerates. This is
the **W01 map**: what exists and where to look, not what is exploitable. Nothing
here has been confirmed on a running device.

> **W03 resolved the three questions this page marked "to confirm".** Kept as
> written; the answers live in the new notes:
>
> - **§1.1 "whether Boa applies an authentication check before serving a `.dat`
>   path"** — it does not, and the reason is broader than `.dat`. The single
>   authorisation gate runs only when the URI contains the substring `htm`, so
>   `.dat`, `.cer` and every `/boafrm/` endpoint fall outside it.
>   → [`auth-flow.md`](auth-flow.md)
> - **§1.2 "recovering the real registration name [of `formSysCmd`] is the
>   single highest-value W03 task"** — there is no registration. It is in
>   neither build's dispatch table. → [`formSysCmd-analysis.md`](formSysCmd-analysis.md)
> - **§1.3 "find the callers [of `cp /var/web/config.dat %s`] and trace where
>   the `%s` comes from"** — `/boafrm/formSaveConfig`, and the `%s` is a
>   timestamp-derived filename. Not injectable.
>   → [`sink-inventory.md`](sink-inventory.md) §6
>
> The handler counts in §1.2 (59 and 49) were derived here from string counting
> and are confirmed exactly by the recovered `root_form[]` arrays — two methods,
> one answer. The **ranking** in §1.2 did not survive as well: `formLogin` and
> the upload handlers were ranked above `formWsc`, and `formWsc` is where the
> unfiltered `system()` calls actually are.

Ranking rule used throughout: an entry earns attention from *reachability ×
privilege × evidence of unchecked input*, in that order. Boa runs as root, so
the privilege term is constant and maximal — which means reachability decides.

---

## 1. The unauthenticated web surface

`/bin/boa`, `Boa/0.94.14rc21`, `User root`, `DocumentRoot /var/web`
(3.4.0) or `/web` → `/var/web` (2.1.2). Port 80.

### 1.1 Static files in the document root that are generated at runtime

Highest-value entries in the whole map, because they need **no authentication
and no parameter parsing** — just a GET.

| Path (3.4.0) | Resolves to | Why it matters |
|---|---|---|
| `/config.dat` | `/var/config.dat` | The apmib configuration dump. Per CVE-2019-19823 it holds credentials in plaintext `COMPCS` format. |
| `/ca.cer` | `/var/ca.cer` | CA certificate written at runtime |
| `/user.cer` | `/var/user.cer` | User certificate — if the private material lands here, it is downloadable |

Absent from the 2015 image; introduced by 2020. `/etc/init.d/rcS` line 56 copies
`/web/*` into the live document root, so the symlinks land in the served tree.

**To confirm (W03):** whether Boa applies an authentication check before serving
a `.dat`/`.cer` path. The advisory says form-based auth did not restrict `.dat`.
The symlink proves the file is *in* the docroot; only the request-handling code
proves whether that is reachable unauthenticated.

### 1.2 Handler endpoints

`POST /boafrm/<name>`. 59 handlers in 2.1.2, 49 in 3.4.0.

Ranked starting points:

| Handler | Present in | Why it is interesting |
|---|---|---|
| `formLogin` | both | The authentication boundary. Everything below depends on how it decides. CVE-2019-19825's CAPTCHA bypass lives here; `getSanvas` appears only in 3.4.0. |
| *(`formSysCmd`)* | **name not found in either binary** | The published RCE endpoint. `sysCmdselect`, `sysCmdLog`, `/tmp/syscmd.log` are all present, so the feature exists. Recovering the real registration name is the single highest-value W03 task. |
| `formUpload`, `formUploadConfig`, `formUploadFile` | 2.1.2 / both / 3.4.0 | Firmware and config upload. Reaches flash writes and, via config restore, the apmib parser. `formUploadFile` is new in 3.4.0. |
| `formWsc` | both | WPS. CVE-2025-4462 (`localPin`) and CVE-2025-6299 (`targetAPSsid`) target this family on sibling models. |
| `formWlWds` | both | WDS. CVE-2025-3992 names `formWlwds` — different capitalisation; verify before believing. |
| `formStaticDHCP` | both | CVE-2025-3995 names `fromStaticDHCP`; again a naming mismatch to resolve. |
| `formTR069Config`, `formPortFw`, `formDdns`, `formNtp`, `formRoute` | both | Each takes a string that plausibly ends up in a shell command — DDNS and NTP especially, since both spawn helper processes. |
| `formAjaxGet`, `formAjaxSet` | 3.4.0 only | New JSON API surface, matching the new `libcjson.so` dependency. Newer code, less scrutinised. |

Full lists: [`reports/n150rt-2.1.2.md`](../reports/n150rt-2.1.2.md),
[`reports/n150rt-3.4.0.md`](../reports/n150rt-3.4.0.md).

### 1.3 Command-execution sinks inside Boa

`/bin/boa` imports `system`, `popen`, `execl`, `execve` in both builds. Two
format strings recovered from 3.4.0's string table are already shaped like
injection candidates:

```
cp /var/web/config.dat %s
rm -rf /var/config.dat >/dev/null 2>&1
```

A `%s` reaching `system()` is the classic pattern. **W03/W04: find the callers
and trace where the `%s` argument comes from.**

---

## 2. The rest of the process surface

33 binaries in 2.1.2 and 17 in 3.4.0 import a command-execution function. They
are not directly network-reachable, but each is a place where data that crossed
the network earlier can reach a shell.

Worth a look after Boa:

| Binary | In | Note |
|---|---|---|
| `/bin/skt` | 2.1.2 only | Pierre Kim's backdoor. Autostart commented out (`#skt&`), binary still shipped. Reads a socket, calls `system()`. |
| `/bin/wscd` | both | WPS daemon — the runtime behind the `formWsc` CVEs |
| `/bin/cwmpClient` | both | TR-069. Talks to a remote ACS and touches `config.dat`. |
| `/bin/miniigd` | both | UPnP IGD. Listed as commented out in `rcS` in both builds. |
| `/bin/udhcpd`, `/bin/dnsmasq` | 2.1.2 | Parse hostnames from the LAN; hostname strings reaching `system()` is a well-worn bug class |
| `/bin/auth` | 3.4.0 only | New, 121 KB, and named after the thing with no `/etc/passwd` behind it. Likely holds the credential check. |
| `/bin/batchUpgrade`, `/bin/UDPserver` | 3.4.0 only | New network-facing code |

---

## 3. Services present but disabled

Reported as `service-disabled-not-removed`. Commenting out an init line stops it
starting; it does not remove the capability.

| Service | 2.1.2 | 3.4.0 |
|---|---|---|
| `skt` (backdoor) | disabled, binary present | removed entirely |
| `telnetd` | — | disabled, busybox applet still present |
| `snmpd`, `miniigd`, TR-069 | disabled | disabled |

`/etc/init.d/rcS_32M`, a variant init script for higher-RAM boards, exists in
3.4.0 and carries its own set of these lines. Worth diffing against `rcS` in
W03 — alternate init paths are a classic place for a forgotten service.

---

## 4. What makes any of this cheap to exploit

From [`anatomy-n150rt.md`](anatomy-n150rt.md): **no canary, no RELRO, no PIE, no
FORTIFY, and no `PT_GNU_STACK` on most binaries** — so an executable stack.
Boa runs as root.

A stack overflow in a handler therefore needs no information leak and no ROP
chain, and lands as root on first try. When reading the 2025 buffer-overflow
CVEs against this device family, that is the exploitation context to assume.

---

## 5. Not yet examined

Named so they are not silently forgotten:

- **The kernel** — carved but not unpacked. LZMA at `+0x2808` inside `cr6c`.
- **The bootloader** — absent from both images; only a flash dump has it (W02).
- **`libapmib.so`** — the `COMPCS` serialiser. Central to 19822/19823 and unread.
- ~~**The `w6cg` web bundle format** (2015) — decompressed but its archive
  structure is only sketched.~~ **Closed 2026-08-16:** 64-byte header, big-endian
  length at `+0x3c`, walked to zero bytes remaining on all three builds by
  `fwrecon web`. The finding it produced is not about the format —
  `syscmd.htm` ships in 2015 and 2016 with the handler absent, and is gone in
  2018 with the handler present ([`w6cg-web-ui.md`](w6cg-web-ui.md)).
- **Wireless firmware / driver** — `/lib/modules`, untouched.
- **The physical surface** — UART, SPI flash, JTAG. W02, blocked on hardware.

### Struck off this list in W04

- ~~`libapmib.so`~~ — the configuration table is recovered and every MIB id in
  this project now has a name ([`mib-and-config-dat.md`](mib-and-config-dat.md)).
  The `COMPCS` compressor is still unidentified.

### Added to it in W04

- **`/etc/scripts/*.sh`** — six handlers `execl` a shell script and pass it *no*
  arguments ([`sink-inventory.md`](sink-inventory.md) §3). The request data
  reaches those scripts through the MIB instead, so `firewall.sh`, `ip_qos.sh`
  and `radvd.sh` are where a `comment` or `ipStart` field is actually
  interpolated. Unread. **W07.**
- **`/bin/sysconf`** — writes `/var/passwd`, `/var/group` and the dropbear host
  key at boot, and holds a large number of `system()` format strings. It is the
  reason `/etc/passwd` exists at runtime and W01 thought it did not.
- **The default-settings blob** — whether `TELNET_ENABLED` / `SSH_ENABLED`
  default on decides how much [`credentials.md`](credentials.md) is worth.
- **`/etc/privateKey.key` and `/etc/dropbear_rsa_host_key`** — shipped private
  keys, identical on every unit.
