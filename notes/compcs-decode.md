# The configuration region decoded

**Question carried out of W04 (deferred) and W02 (open #8):** `config.dat` was
described as "a compressed serialisation of the MIB table", with the explicit
caveat that "the password is at offset N" was *not* what the evidence supported.
W02 located the blob at flash `0x00C000`. This note decodes it.

**Answer.** It is LZSS over a TLV dump of the APMIB table, and both regions
decode byte-perfectly:

| flash | magic | role | compressed | decompressed | TLVs |
|---|---|---|---|---|---|
| `0x006000` | `H601` | hardware setting | — | **not compressed** | — |
| `0x008000` | `COMPDS` | factory defaults | 7,481 | 45,226 | **344** |
| `0x00C000` | `COMPCS` | **live configuration = `config.dat`** | 7,478 | 45,226 | **344** |

```
fwrecon compcs $FWRE_WORK/dumps/flash-n150rt-console-1.bin --offset 0x00C000 \
  --mib $FWRE_WORK/extracted/unit-2018/squashfs-root/lib/libapmib.so \
  -f json -o reports/compcs-unit-2018.json
```

Output: [`reports/compcs-unit-2018.json`](../reports/compcs-unit-2018.json) ·
[`reports/compds-unit-2018.json`](../reports/compds-unit-2018.json).
Code: [`tools/fwrecon/src/fwrecon/compcs.py`](../tools/fwrecon/src/fwrecon/compcs.py).

---

## 1. The format

```
flash region                          decompressed
+0   char   magic[6]  "COMPCS"        +0  char   sig[2]  "6G" default / "6g" current
+6   u16    compRate  7               +2  char   ver[2]  "03", ASCII, sscanf("%02d")
+8   u32    compLen   0x1D36          +4  u32    len     45218  (total = len + 8)
+12  u8     payload[compLen]          +8  TLV stream: { u16 id; u16 len; u8 value[len] }
                                          and sum(payload) & 0xff == 0
```

Payload is Okumura LZSS: a 4,096-byte ring pre-filled with `0x20`, write pointer
starting at 4,078, flag byte consumed LSB-first, 1 = literal, 0 = a two-byte
reference `pos = b0 | ((b1 & 0xf0) << 4)`, `len = (b1 & 0x0f) + 3`.

`compRate` is not a format field. It is an allocation hint: `libapmib` does
`malloc(compRate * compLen)` and decodes into it. 45,226 / 7,481 = 6.05, and the
stored value is 7 — the ratio, rounded up.

Bit 15 of an id marks a table-valued entry, the same convention
[`mib-and-config-dat.md`](mib-and-config-dat.md) records for the id/name table.

## 2. Five checks, and only one of them is this tool's own opinion

| check | result |
|---|---|
| `libapmib`'s 8-bit payload checksum sums to zero | ✅ both regions |
| decompressed length matches the declared `len + 8` | ✅ 45,226 = 45,218 + 8 |
| TLV count against the MIB table recovered from `libapmib.so` | ✅ **344 against 344** |
| ids not present in that table | ✅ **zero** |
| decoding with ring fill `0x00` and `0x20` gives the same bytes | ✅ both regions |

**The checksum is the load-bearing one, and it is the vendor's, not mine.** It
appears nowhere in the data — it is in `_apmib_dsconf` at `0x0001781c`:

```c
cVar6 = 0;
for (p = __src; p != __src + len; p++) cVar6 += *(char *)(p + 8);
if (cVar6 == 0 && mib_tlv_init(...) == 1)
```

A single wrong byte anywhere in 45,218 fails it. It cannot be tuned to pass,
because it was not known while the decoder was being written.

The third check is the next strongest and it crosses files: 344 TLVs in a flash
blob against 344 records recovered from `libapmib.so` by
[`mibtable.py`](../tools/fwrecon/src/fwrecon/mibtable.py), which shares no code
with this decoder. It also reproduces a known defect — the table has **343
distinct ids for 344 records**, because `0x182` is bound to both
`CUSTOM_PASSTHRU_ENABLED` and `MLD_PROXY_DISABLED`. W04 found that duplicate in
V2.1.2 and recorded that V3.4.0 has none. **It is in the 2018 build too**, so the
vendor shipped it for at least two and a half years and fixed it by 2020.

The ring-fill check is free and worth naming: if any back-reference pointed into
window space no literal had written, the two fills would disagree. They do not,
so the stream never depends on uninitialised window content.

## 3. What is actually in it

**`TELNET_ENABLED` = 0. This is W04 open #4, and it decides what `root:123456`
is worth.**

| | value |
|---|---|
| `TELNET_ENABLED` (`0xbbb`) | **0** |
| `SSH_ENABLED` (`0xbb9`) | 1 |
| `SSH_PORT` (`0xbb8`) | 22 |
| `SSH_PASSWORD` (`0xbba`) | **`xa.zioncom`** |
| `USER_NAME` / `USER_PASSWORD` (`0xb6`/`0xb7`) | **`admin` / `admin`, plaintext** |
| `WEB_WAN_ACCESS_ENABLED` (`0xc2`) | 0 |
| `UPNP_ENABLED` (`0x8e`) | 1 |
| `IP_ADDR` / `SUBNET_MASK` | 10.1.1.1 / 255.255.255.0 |

### The second source, because one number from a tool written today is not a finding

`/bin/sysconf` decides it, and the decision is one function:

```c
FUN_00403400() { apmib_get(0xbbb, local_10); return local_10[0]; }   /* TELNET_ENABLED */
```

```
setinit @ 004052ec:
  00407c14  jal 0x00403400
  00407c24  bne v0,v1,0x00407c44        ; v1 = 1  -> not 1, skip
  00407c34  jalr system                 ; system("telnetd & >/dev/null 2>&1")
```

**`telnetd` starts if and only if `TELNET_ENABLED == 1`.** The flag decoded from
flash and the code that reads it are two instruments sharing no path, and they
agree.

So the correct statement about the backdoor account is the narrow one:
**`root:123456` and `onlime_r:12345` are not an entry point on this unit. They
are the second stage of a chain** — something must first turn telnet on. Calling
them an entry point would overstate it by a whole step.

> **Prediction, written 2026-08-16 before any network test.** When W05 runs
> `nmap -p 22,23 <device>`, **port 23 will be closed and port 22 will be
> closed.** 23 because the flag is 0; 22 because `SSH_ENABLED` is 1 but **there
> is no SSH daemon in this rootfs at all** — no `dropbear`, no `sshd`; the only
> mentions are in a `killall` list inside `sysconf` and `timelycheck`. A flag
> with nothing to start.
>
> If 23 is open, either the decode is wrong or something else starts `telnetd`,
> and both are findings.

### `SSH_PASSWORD = xa.zioncom` is a model-level fact, not a per-unit one

It is byte-identical in `COMPDS` and `COMPCS`, i.e. it is the factory default,
i.e. **it is the same on every N150RT of this build**. "zioncom" is TOTOLINK's
parent company, and the same string appears as a literal run inside the
compressed blob.

That makes **three** credential systems on this device, where W04 found two:
the web admin (`admin`/`admin` in the MIB), the Unix accounts
(`root:123456`, `onlime_r:12345` in `/etc/passwd.org` —
[`credentials.md`](credentials.md)), and now this. **No daemon consumes it in
this build**, so it is dormant rather than exploitable here; whether some sibling
model in the same SDK line ships both the flag and a daemon is not something this
project can answer from one device, and it is not claimed.

### CVE-2019-19823, located rather than cited

`USER_PASSWORD` is TLV id `0xb7`, 31 bytes, and its value is the ASCII string
`admin` followed by NULs. There is no hash, no obfuscation and no key — the only
transform between flash and plaintext is the LZSS above, which is a compressor.
That is the whole of "plaintext password storage", now readable byte by byte
rather than inferred from the absence of a hashing step.

It also explains a piece of code W03 read without being able to justify:
`formLogin` does `strcmp(userpass, cfg_pass)` directly. It can, because there is
nothing to compare *against* except the plaintext.

### This unit was never configured, and now that is measured

`flash-layout.md` inferred it from a byte-level comparison of the two compressed
blobs — "its live configuration is barely distinguishable from factory defaults.
It was reset, or never meaningfully configured." Decoded, **4 entries of 344
differ**:

| offset | field | default | live |
|---|---|---|---|
| 91 | `DHCP_LEASE_TIME` | 0 | `0.0.1.224` (480) |
| 387 | `WLAN_SSIDS` | empty | `TOTOLINK N150RT` |
| 4696 | `MIB_VER` | 0 | 1 |
| 5850 | `CHECK_SSID_OK` | 0 | 1 |

21 differing bytes out of 45,226, and two of the four are internal bookkeeping.
**Inference upgraded to measurement, and it landed where the inference said.**

## 4. Disclosure — decided per field, and the reasons do not all transfer

The decision of 2026-08-16 ([`LOG.md`](../LOG.md) § 決策) is that this unit's
values are published: self-purchased, end of life, never deployed, and a MAC is
an identifier rather than a credential.

**The shape of that decision is a table, not a stance.** A stance can only be
argued with; a per-field table can be checked.

| field | published | why |
|---|---|---|
| `USER_PASSWORD` = `admin` | yes | equal to the factory default, so it is public information about the model — and that equality *is* the finding |
| `SSH_PASSWORD` = `xa.zioncom` | yes | factory default, identical on every unit; a model fact |
| `WLAN_SSIDS` = `TOTOLINK N150RT` | yes | the default naming scheme is itself the finding: it leaks the MAC's last six digits on units that keep it |
| `IP_ADDR`, `SUBNET_MASK` | yes | not per-unit |
| `H601` MAC addresses | yes | self-purchased EOL unit, never deployed; identifier, not credential |
| `H601` radio calibration | yes | a *physical measurement* of one silicon die. It describes analogue behaviour and points at no one |
| photograph EXIF | **no — unchanged** | 🔴 **the reason does not transfer.** Today's argument is "this device is retired". GPS locates a *person*, not a device state, and people do not reach end of life |
| the raw 4 MiB image | **no — unchanged** | `dumps/README.md` gave two independent reasons and said either alone sufficed. Per-unit secrecy expired; "this project does not redistribute vendor firmware" did not |

**The mechanism survives the policy.** `fwrecon compcs --disclosure protect`
still replaces per-unit identifiers with a digest, and
[`test_protect_mode_never_emits_mac_derived_fields`](../tools/fwrecon/tests/test_compcs.py)
fails if a known MAC reaches any output. What changed today is a policy about one
device; a capability deleted because a policy relaxed does not grow back when the
policy tightens, and **the next device may not be mine.**

## 5. What this does not settle

- **`/web/config.dat` does not exist on this unit at boot.** The document root
  is a ramfs filled from the `w6cg` flash section, whose 143 files do not include
  it ([`auth-flow-2018.md`](auth-flow-2018.md) §3). The blob decoded here was
  read from flash directly, not fetched over HTTP. Whether
  `POST /boafrm/formSaveConfig` with `save-cs` creates a servable copy — making
  the full CVE-2019-19822 → 19823 chain reachable unauthenticated — is a W05
  test, not a result.
- **`H601` at `0x006000` is not a `COMPHS` blob.** `libapmib` knows a `COMPHS`
  magic and this device does not use it there; the hardware settings are stored
  uncompressed under an `H601` magic. `fwrecon compcs` refuses the offset rather
  than guessing, which is how this was noticed.
- **The `Encode` side is unread.** Only `Decode` was needed. `mib_compress_write`
  and `save_cs_to_file` are located but not analysed, and W06 will write to this
  region.

---

## How the first version of this note was wrong

**The order was wrong, and it worked anyway — which is the least useful way to
be lucky.** The plan for the week said, in bold: read the decompressor out of
`libapmib.so` *first*, then compare against public sources, because this project
has already been burned once by treating a leaked SDK header as a description of
the binary in front of it. What actually happened is that the LZSS parameters
were inferred from the two blobs and only afterwards checked against `Decode` at
`0x00012e98`.

They matched exactly — N=4096, F=18, threshold 2, ring start 4078, even the
`0x20` fill. So the shortcut cost nothing this time. **It could not have been
known to cost nothing until the binary was read**, which is the entire argument
for the rule, and the two things the binary supplied afterwards make the point
better than any argument would:

- **the checksum**, which is invisible in the data and is now the strongest
  correctness check the decoder has;
- **the vendor's own bound** `if (0x3fff < len - 1U) return 0`, which is now the
  tool's bound instead of one invented to look sensible.

Guessing well is not a method. It is the same outcome as a method, on the days
you happen to be right.

**Two smaller things were wrong on the first run of the tool, and both were the
tool, not the data.** It flagged "1 byte left over after the TLV walk" as an
anomaly — that byte is the checksum pad and is always there — and it compared the
TLV count against the number of *distinct* MIB ids rather than the number of
records, so the duplicate `0x182` made a correct decode look off by one. Both
made a byte-perfect decode of the real firmware report `SUSPECT`. **False alarms
are how real alarms get ignored**, and this repository already runs three tools
whose verdict fields are meant to be read.
