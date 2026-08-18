# `/bin/auth`, `/bin/miniigd`, `/bin/dnsspoof` — the three nobody had read

W07's Definition of Done asks for these three. All three are on this unit, none
had been opened, and two of the three turned out to matter. The third turned out
to be something other than what the project had assumed for four weeks.

**Answers first.**

| binary | what it is | what is in it |
|---|---|---|
| `/bin/auth` 141,552 B | **not** the web credential checker — it is the **802.1X / WPA authenticator** | `RTLAuthenticator`, `lib1x_do_authenticator`, `lib1x_control_STA_SetGTK`, `lib1x_control_RSNIE`, `libnet_*`. W01 guessed "credential check", W04 filed it "off the critical path". Both were reasoning without reading. It is the daemon W08's `P7-5` (PMKID) and `P7-6` (4-way handshake) talk to |
| `/bin/miniigd` 97,100 B | the UPnP IGD daemon, on **52869/tcp** — open 2026-08-16 (`P1-2`), **closed** 2026-08-18 (`P6-1`), **open again 2026-08-19** after the reset; §2 has why it moved and what one request does to it | **SOAP-supplied values reach `system()` with no escaping**, and an unbounded `strcpy` sits on the same path. §2 |
| `/bin/dnsspoof` 3,820 B | a captive-portal DNS responder started when the WAN drops | **a bounded out-of-bounds write past a 256-byte stack buffer**, landing on three pointer locals whose offset the attacker chooses. §3 |

**§1 and §3 are static — nothing in them has been executed**, and `P6-10` stays
open in the register on purpose because its refutation condition is about
behaviour on the device. **§2 is no longer static**: `P6-1` and `P8-7` were run
against the hardware on 2026-08-19 and the subsection dated that day says what
came back, including one result the register did not anticipate.

---

## 1. `/bin/auth` is the wireless authenticator, and a four-week-old assumption was wrong

W01 named `/bin/auth` (V3.4.0, 121 KB) "the likely credential check". W04 wrote
it off: *"with `USER_NAME`/`USER_PASSWORD` located in the MIB and `/etc/passwd`
explained, it is off the critical path. Still unread."*

Its import table settles it without a decompiler:

```
RTLAuthenticator     lib1x_do_authenticator   lib1x_do_supplicant
lib1x_load_config    lib1x_init_authGlobal    lib1x_init_authRSNConfig
lib1x_control_RSNIE  lib1x_control_STA_SetGTK lib1x_control_InitQueue
lib1x_init_authTimer lib1x_print_etheraddr
libnet_open_link_interface  libnet_get_hwaddr  libnet_get_ipaddr
oursvr_addr  oursupp_addr  udp_svrport  svraddr  RTLClient
```

This is Realtek's `lib1x` — the 802.1X state machine, both authenticator and
supplicant halves, with `libnet` for raw frame injection. It handles the 4-way
handshake, the RSN information element and the group key.

**W04's conclusion was right and its reasoning was luck.** "Off the critical
path" was inferred from where the *web* credentials live; the actual reason it is
off the web path is that it is not a web component at all. The correction that
matters is forward-looking: this is the binary the W08 wireless block is
attacking, and it was sitting in the "unread" column while `P7-1`…`P7-10` were
scheduled against it.

## 2. `/bin/miniigd` — SOAP values reach `system()`, and the port opened, closed, and was not looked at again

`P1-2` found **52869/tcp open** on 2026-08-16 and no prediction had mentioned
it. `P1-10` confirmed the daemon answers SSDP. This is what is behind that port.

> **The port state has a date on it now, because it moved twice and the first
> version of this section said "is open" in the present tense.** On 2026-08-18
> `P6-1` and `P8-7` found 52869 **closed**, `miniigd` absent from `ps`, and no
> `InternetGatewayDevice` reply to an `M-SEARCH` — because `UPNP_ENABLED` read
> `0` in the live configuration, which **this project's own W05 unauthenticated
> POST round wrote**, and this build's web UI has no UPnP page anywhere in its
> 31 enumerated pages through which a user could set it back. The 2026-08-19
> reset restored `COMPCS` byte-for-byte to its 2026-08-16 content, so the flag is
> `1` again — **and at the time this paragraph was written the port had not been
> measured since**. That state was the dangerous one: a sentence that has become
> true again by accident reads exactly like a sentence that was checked. It was
> measured the same night; the paragraph stays as written because the gap between
> "true again" and "checked again" is the thing worth remembering, and §2's
> 2026-08-19 subsection is what closed it.

### 2026-08-19: the port is open again, and one request takes the daemon down

**The port state, measured rather than inherited.** After the 2026-08-19 factory
reset restored `UPNP_ENABLED` to `1`, `52869/tcp` answers again and
`GET /picsdesc.xml` returns the 2,933-byte `Internet Gateway Device` description
with `<controlURL>/upnp/control/WANIPConnection</controlURL>` and
`Server: miniupnpd/1.4`. The daemon came back on its own across three further
power cycles, which is the second and third confirmation of `P1-10`'s mechanism
— the flag went `1 → 0 → 1` and `sysconf` followed it every time.

**`AddPortMapping` does not check `NewInternalClient` against the request
source.** A mapping created from `10.1.1.100` naming `10.1.1.1` as the internal
client is accepted with HTTP 200 and reads back unchanged through
`GetGenericPortMappingEntry`, with `NewLeaseDuration=0`. That is `P8-7`'s first
refutation branch not firing. (`NewPortMappingDescription` is *not* stored: it
comes back as the literal `miniupnpd` whatever was sent.)

**The value is not validated at all, and the failure is visible in the firewall.**
A `NewInternalClient` of twenty-two `A` characters produces, in the device's own
`iptables -t nat -L -n`:

```
Chain MINIUPNPD (0 references)
DNAT  tcp -- 0.0.0.0/0  0.0.0.0/0  tcp dpt:8083 to:255.255.255.255:83
```

`255.255.255.255` is `INADDR_NONE` — what `inet_addr()` returns on a string it
cannot parse — used as an address regardless. So the SOAP value reaches a
firewall rule with no filtering, which is the half of `P6-1`'s prediction that
is confirmed.

**And then the process is gone.** Every request carrying a `NewInternalClient`
that `inet_addr()` rejects ends with the TCP connection closed and no response,
`52869` refusing connections afterwards, and — checked over a telnet shell two
minutes later — **no `miniigd` in `ps` at all**, with nothing respawning it. Only
a power cycle brings it back. Three separate requests on three boots produced
this; a request with `NewInternalClient=10.1.1.1` did not, and the daemon
answered a subsequent read.

**It is not the shell metacharacter.** The first attempt used a backtick payload
and the obvious reading was CVE-2014-8361 crashing rather than executing. The
control refutes that: twenty-two `A` characters, no metacharacter anywhere, kill
it identically. Three points define the line — a valid IP survives, a
metacharacter value dies, a plain non-IP value dies — and any two of them would
have supported the wrong conclusion.

**What did NOT happen: command execution.** The ICMP oracle stayed silent across
both injection attempts, and it was proved good on the same boot minutes earlier
by an independent route — a `formSysCmd` injection made the device send four
echo requests, and the pcap has them. So **CVE-2014-8361 is not reproduced on
this build**: the daemon dies before `system()` is reached. Neither of `P6-1`'s
refutation branches fired, and the second one is mis-worded for this device —
nothing is *filtered*, the value goes straight into a rule.

> ⚠️ **Not reported, and not reportable yet.** An unauthenticated single-request
> termination of a UPnP daemon has had **no prior-art search**, and this repository
> does not report what it has not searched for. `docs/disclosure.md` holds the
> item and its state. What is also untested is *why* it dies: the unbounded
> `strcpy` at `0x0044851c` on this path is a candidate and a 22-byte value is a
> poor fit for it, so the mechanism is an open question rather than a conclusion.

The SOAP control endpoint is **`/upnp/control/WANIPConnection`**. (The working
notes carried `/upnp/control/WANIPConn1`, which is `miniupnpd`'s path and not
this binary's. Anyone probing with the wrong path would record a clean 404 and
conclude the surface is absent.)

`AddPortMapping` is handled by `FUN_004083a8`, 736 bytes, and the whole of it
reads:

```
004083fc  ParseNameValue(soap_body, ...)
00408418  GetValueFromNameValueList(list, "NewInternalClient")
00408424    NULL -> "Invalid Args"
0040845c  GetValueFromNameValueList(list, "NewInternalPort")
00408478  GetValueFromNameValueList(list, "NewExternalPort")
00408494  GetValueFromNameValueList(list, "NewProtocol")
004084b0  GetValueFromNameValueList(list, "NewPortMappingDescription")
004084cc  GetValueFromNameValueList(list, "NewEnabled")
004084e4  atoi(...)          00408500  atoi(...)
0040851c  strcpy(...)                     <-- unbounded, on a SOAP value
00408538  atoi(...)          00408580  atoi(...)
004085a8  upnp_redirect(...)
004085e4  sprintf(buf, "echo \"%s,%s,%s,%s,NA,%s\" >> %s", ...)
004085fc  system(buf)                     <-- the shell
```

**There is nothing between `GetValueFromNameValueList` and `sprintf`.** No
escaping function, no character filter, no length check on the string path. Five
`%s` inside a double-quoted shell string, and a shell metacharacter in any of
them is interpreted rather than stored.

`miniigd`'s other `system()` callers, for completeness — the whole set, found by
`callers:system` rather than by grepping for likely-looking strings:

| function | what it runs |
|---|---|
| `FUN_004083a8` | `echo "%s,%s,%s,%s,NA,%s" >> /tmp/upnp_info` — **the one above** |
| `FUN_00408008` | `echo "" > %s`, `echo -n "%s" >> %s`, `cp %s %s`, `rm %s` — `DeletePortMapping`, same shape |
| `upnp_redirect` | `echo %s > /proc/filter_upnp_br` |
| `FUN_00402a50` | `iptables -t nat -A PREROUTING -d %s -i %s -j MINIUPNPD`, `echo -n "%s," > %s` |
| `FUN_00402b98` | `iptables -t nat -N MINIUPNPD` — chain setup, constant |
| `FUN_004025a0` | `iptables -t nat -X MINIUPNPD` — teardown, constant |
| `main` | option handling |

### What this is, and what it is not

**It is almost certainly CVE-2014-8361** — the Realtek SDK `miniigd` SOAP command
execution, on CISA's KEV list and the payload of several Mirai variants since
2015. This project has not discovered it; it has found a 2018 build shipping it
on an open port. That is verification work and the register says so.

**What is not established, and both matter:**

- Whether it actually executes on the device. The register's `P6-1` refutation is
  *"responds but the SOAP fields are filtered → this version is fixed"*, and code
  reading cannot satisfy a condition phrased about behaviour. It stays open.
- Whether `AddPortMapping` validates `NewInternalClient` against the requester's
  own address, which is `P8-7`'s question (turning LAN-only into WAN-reachable)
  and a different one from injection. `upnp_redirect` is called before the
  `sprintf`; what it checks has not been read.

> ⚠️ **Scope.** LAN-side, on the isolated segment, with the WAN port on the fake
> ISP. `docs/disclosure.md` carries the item and no request that performs it
> appears in this repository.

## 3. `/bin/dnsspoof` — 3,820 bytes, and an out-of-bounds write in all of them

Started as `dnsspoof %s &` by `/bin/sysconf`, `/bin/boa`, `/bin/udhcpd` and
`/bin/timelycheck`; `sysconf` carries the string `wan_disconnect:
StartDnsSpoof`, and `boa` carries `dnsspoof_enb`. So it runs when the WAN drops,
and the web server can start it directly.

Its entire import set is `socket`, `bind`, `recvfrom`, `memcpy`, `sendto`,
`perror`, `close`, `strtol`, `puts`. One function does the work,
`FUN_00400910`, and its frame is exactly this:

```
sp+0x190   frame size 400
sp+0x18c   saved ra
sp+0x188 .. sp+0x170   saved s8..s2
sp+0x160 = sp+0x50     pointer: the A-record's 4-byte RDATA slot
sp+0x15c = sp+0x60     pointer: into the query, past the 12-byte DNS header
sp+0x158 = sp+0x20     pointer: recvfrom's addrlen
sp+0x54    receive buffer, 256 bytes, ending at sp+0x154
sp+0x44    the 16-byte answer record, immediately BEFORE the buffer
```

The loop:

```
00400a0c  n = recvfrom(sock, sp+0x54, 0x100, ...)
00400a18  n < 0x11        -> drop
00400a30  flags high bit  -> drop
00400a40  QDCOUNT == 0    -> drop
00400a50  scan the QNAME to its terminating NUL
00400a78  qtype must be 0x0001 (A) or 0x001c (AAAA)
00400a90  qclass must be 0x0001 (IN)
00400ac0  memcpy(sp[0x160], <spoof ip arg>, 4)      ; fill the record's RDATA
00400ae4  memcpy(sp+0x54 + n, sp+0x44, 0x10)        ; append the record
00400b10  sendto(..., sp+0x54, n + 0x10, ...)
```

**The append is at `buffer + n` with a fixed 16-byte length and `n` bounded only
by `recvfrom`'s own 256.** The write therefore ends at `sp+0x54 + n + 0x10`, and
the buffer ends at `sp+0x154`. Solving for the first byte past the buffer:

> **a query of 245 bytes or more writes outside the receive buffer**, and a
> 256-byte query writes as far as `sp+0x163`.

That range covers all three pointer locals: `sp+0x158`, `sp+0x15c` and
`sp+0x160`. All three are initialised **once, before the loop** — nothing
re-establishes them per iteration. So the corruption persists into the next
query, where:

- `sp+0x15c` is dereferenced by the QNAME scan (`lb a0,0x0(v0)` at `0x00400a50`)
  — a **read** through a corrupted pointer;
- `sp+0x160` is the destination of `memcpy(dst, ip, 4)` at `0x00400ac0` — a
  **four-byte write** through a corrupted pointer.

**And the honest limit.** `recvfrom` caps `n` at 256, so the furthest write is
`sp+0x163`, while the saved `ra` is at `sp+0x18c` — **forty bytes out of reach**.
This is not a return-address overwrite. The bytes that land on the pointers are
the answer record's own — `0xC00C`, type, class, a zero TTL, an rdlength of 4,
and the spoof address — at whatever alignment the query length selects, so the
attacker chooses *which* of sixteen mostly-fixed bytes lands where, not what they
are.

So: **a remote, unauthenticated, bounded out-of-bounds write that corrupts two
live pointers, in a daemon that runs when the WAN is down.** Whether it reaches
anything beyond a crash is not established and this note does not claim it does.

`P6-10` stays open. Its refutation is *"unplug the WAN and DNS behaviour does not
change → that code is never reached"*, and the first thing to settle is still
which of `dnrd`, `dnsmasq`, `dns_protocl` and `dnsspoof` is actually bound to
port 53 — `P1-2` found 53/udp `open|filtered` and did not say by what.

## 4. How the first version of this was wrong

**A binary disappeared from the extracted rootfs in the middle of reading it.**
`bin/miniigd` was listed and `strings`-ed successfully, and twenty minutes later
`cp` reported no such file — while the copy inside the built emulation
environment was still there. It was restored by re-running `unsquashfs` on
`rootfs.squashfs`, and the fresh extraction's SHA-256 matched the environment's
copy byte for byte, so nothing measured before or after is in doubt. **What
caused it is not known**, and guessing would be worse than saying so: only
`strings`, `readelf` and a failed Ghidra import touched that path.

The lesson is not about the file. It is that **nothing in this repository checks
that the extracted tree still matches the SquashFS it came from**, so a tree that
loses a file — or gains an edited one — looks exactly like a tree that does not.
The extracted rootfs is derived data and has been treated as evidence. The
evidence is `rootfs.squashfs` and the flash dump behind it, and the check that
says so does not exist yet.

**And a smaller one: the SOAP path in the working notes was wrong.**
`/upnp/control/WANIPConn1` is `miniupnpd`'s. This binary answers on
`/upnp/control/WANIPConnection`. A bench session that probed the documented path
would have got a clean negative and recorded "no UPnP control surface" — with
52869 open the whole time, as it was on 2026-08-16.
