# `/bin/auth`, `/bin/miniigd`, `/bin/dnsspoof` — the three nobody had read

W07's Definition of Done asks for these three. All three are on this unit, none
had been opened, and two of the three turned out to matter. The third turned out
to be something other than what the project had assumed for four weeks.

**Answers first.**

| binary | what it is | what is in it |
|---|---|---|
| `/bin/auth` 141,552 B | **not** the web credential checker — it is the **802.1X / WPA authenticator** | `RTLAuthenticator`, `lib1x_do_authenticator`, `lib1x_control_STA_SetGTK`, `lib1x_control_RSNIE`, `libnet_*`. W01 guessed "credential check", W04 filed it "off the critical path". Both were reasoning without reading. It is the daemon W08's `P7-5` (PMKID) and `P7-6` (4-way handshake) talk to |
| `/bin/miniigd` 97,100 B | the UPnP IGD daemon, listening on **52869/tcp** (`P1-2` measured it open) | **SOAP-supplied values reach `system()` with no escaping**, and an unbounded `strcpy` sits on the same path. §2 |
| `/bin/dnsspoof` 3,820 B | a captive-portal DNS responder started when the WAN drops | **a bounded out-of-bounds write past a 256-byte stack buffer**, landing on three pointer locals whose offset the attacker chooses. §3 |

Everything below is **static**. Nothing has been executed. `P6-1` and `P6-10`
stay open in the register on purpose: both of their refutation conditions are
about behaviour on the device, and reading the code does not satisfy them.

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

## 2. `/bin/miniigd` — SOAP values reach `system()`, and the port is open

`P1-2` found **52869/tcp open** on this unit and no prediction had mentioned it.
`P1-10` confirmed the daemon answers SSDP. This is what is behind that port.

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
52869 open the whole time.
