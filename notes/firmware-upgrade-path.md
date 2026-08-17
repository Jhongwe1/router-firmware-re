# What this build checks before it writes a firmware image to flash

**The answer, with addresses.** Two things, and nothing else:

| # | check | where | what it is |
|---|---|---|---|
| 1 | section tag | `memcmp` at `0x004608cc`, `0x00460924`, `0x0046097c` | four bytes: `cr6c`, `w6cg` or `r6cr` |
| 2 | checksum | `FUN_00460600` called at `0x00460a98`, branch `0x00460aa4` | **16-bit sum of big-endian halfwords == 0** (for `cr6c` and `r6cr`) |
| 2′ | checksum | `FUN_00460690` called at `0x00460aec`, branch `0x00460af8` | **8-bit sum of bytes == 0** (for `w6cg`), length capped at `0x800000` |
| 3 | trailer | `strncmp` at `0x00460a04` | the caller's model string, and `form_formUpload` passes the literal **`TOTOLINK-N150RT-V2.1.0`** |

**No signature. No `hw_version`. No anti-rollback.** Those are not absent from the
listing by accident of where this note stopped reading: `strings` over the whole
of `/bin/boa` returns no match for `signature`, `RSA`, `pubkey`, `.pem`,
`hw_version` or `verify` in any upgrade-related sense — the only two `verify`
hits are user-facing messages about a URL. The acceptance function
`UpgradeByData` is 1,608 bytes at `0x00460798` and the four rows above are all
of it.

Register: **`P9-13` confirmed** (static), **`P8-10` confirmed** (static),
**`P8-18` refuted** (static). Measured on `/bin/boa` from this unit's own flash
dump, `sha256 19fe29d7…`.

---

## 1. `UpgradeByData` — the acceptance function, read at instruction level

The decompiler was not asked. Every branch below is from
[`BoaListing.java`](../ghidra/scripts/BoaListing.java) output over
`0x00460798`–`0x00460de0`.

```
loop:
  0x004608cc  memcmp(p, "cr6c", 4) == 0  -> type = 1
  0x00460924  memcmp(p, "w6cg", 4) == 0  -> type = 2
  0x0046097c  memcmp(p, "r6cr", 4) == 0  -> type = 3
  0x00460a04  strncmp(p, model, strlen(model)) == 0 -> type = 4, LEAVE THE LOOP
  0x00460a30  otherwise, if nothing has matched yet:
              "Invalid file format."  -> return -1

  a tag matched:
  0x00460a60  type == 1 ────┐
  0x00460a70  type == 3 ────┤-> 0x00460a98  FUN_00460600(p + 0x10, len)
                            │   0x00460aa4  non-zero -> accept
                            │   0x00460ab0  zero     -> "Image checksum mismatched." return -1
  0x00460a70  type == 2 ────┴-> 0x00460aec  FUN_00460690(p + 0x10, len)
                                0x00460af8  non-zero -> accept
                                0x00460b04  zero     -> "Image checksum mismatched." return -1

  0x00460b2c  type == 3 ? "/dev/mtdblock1" : "/dev/mtdblock0"
  ...records the section into the 0x90-byte struct at DAT_0048c284...
  0x00460ce8  bne v0,zero,0x00460854          <- back edge: next section

after the loop:
  0x00460d04  nothing accepted        -> "No valid image."  return -1
  0x00460d4c  model string given and the walk did not end on it
                                      -> "Invalid firmware." return -1
  0x00460d98  WriteDataToFile("/var/fwd.conf", DAT_0048c284, 0x90)
  0x00460db4  sync()
              return 0
```

`/bin/fwd` then reads `/var/fwd.conf`, attaches the shared-memory segment
holding the image, kills every daemon on the box — its string table is 40
consecutive `killall -9` lines — and writes to the mtd device. `boa` never
writes flash itself.

### The two checksums, decompiled from the listing

`FUN_00460600` @ `0x00460600`, 144 bytes:

```c
uint16_t sum = 0;
for (i = 0; i < len; i += 2)      /* lhu — big-endian halfwords */
    sum += *(uint16_t *)(buf + i);
return (sum == 0);                /* sltiu v0,v0,1 at 0x00460678 */
```

`FUN_00460690` @ `0x00460690`, 216 bytes: the same shape one byte at a time,
plus a length guard — `len < 0` or `len > 0x800000` returns 0 immediately
(`0x004606b0`, `0x004606c8`).

**Both are additive checksums with no key and no diffusion.** Changing any byte
of an image and compensating in any other byte of the same parity produces
another accepted image. That is the whole of the integrity story.

### `TOTOLINK-N150RT-V2.1.0`, and why that string is interesting

`form_formUpload` at `0x0044f470` passes it as the fourth argument
(`0x0044f4dc`), so it is the trailer the section walk must end on. This unit
reports `TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002` — its own `/etc/version`,
and the string CVE-2024-51228 names.

**The image the upgrade path accepts is labelled with a different, older product
string than the one the unit reports.** There is no comparison between the two,
and no field anywhere in the path that a rollback could fail. `V2.1.0` is
published and downloadable; `V2.1.6-B20171121.1002` is not.

## 2. `P8-10` — the router fetches firmware over plain HTTP, and an unauthenticated request starts it

`/bin/batchRemoteUpgrade` (15,164 bytes, never read before this session) carries
its whole flow in its string table:

```
rm -f /tmp/index.htm
wget -q -c http://%s:%s/fw/totolink/%s/ -O /tmp/index.htm
cat /tmp/index.htm | grep %s >/tmp/fwList
wget -c http://%s:%s/fw/totolink/%s/%s -O /tmp/%s -o /var/log.txt
```

It imports `system`, `sprintf` and `strcpy`. `sysconf` starts it as
`batchRemoteUpgrade %s %s %s %s %s %s &`, six arguments.

The same job exists inside `boa`. `FUN_0044f7b4`, reached from
**`form_formSaveConfig`**, reads three POST parameters —
`submit_rfw_check` (`0x0044f804`), `submit_rfw_download` (`0x0044f824`),
`submit_rfw_upgrade` (`0x0044f844`) — and calls

```
0x0044f88c  CheckRFW("sl.totolink.software", …, "TWN150RTV2",
                     "TOTOLINK-N150RT-V2.1.6", "TOTOLINK-N150RT-V2.1.6-B20171121.1002")
0x0044f8ac  DownloadWithPercents(…)
0x0044f948  InitRFWUpgrade(…)
```

Three facts stack here and the third is the one that matters:

1. **The update server is `sl.totolink.software` over `http://`.** No TLS
   anywhere in the path — `boa` links no TLS library and the rootfs ships none.
2. **The image is accepted on an additive checksum** (§1), so controlling the
   response is sufficient; no key is needed.
3. **`/boafrm/formSaveConfig` is outside the authorisation gate on this build.**
   [`auth-flow-2018.md`](auth-flow-2018.md) settles that: the gate runs on
   `strstr(uri, ".htm")` or `strstr(uri, ".asp")`, and a POST to `/boafrm/` does
   not enter it. `P2-1` confirmed that on the hardware.

> ⚠️ **Scope. This is a static reading and it stops at the door.** Nothing here
> has been executed. What would confirm it: on the isolated segment, point the
> lab DNS at the bench host for `sl.totolink.software`, serve a directory index
> and an image whose sections carry a correct additive checksum, send the
> download parameter unauthenticated, and watch for the outbound request. The
> register schedules that as the device half of `P8-10`; the write half belongs
> with `P9-10` in W08 and is **not** to be run on this unit before then.
>
> `docs/disclosure.md` holds the state of this item. No request that would
> perform it appears in this repository.

## 3. `P8-18` — refuted: `filename=` is a landmark, not a value

`FUN_0044f360` at `0x0044f360` is what reads it, and it is 272 bytes:

```
0x0044f388  strstr(body, "/octet-stream\r\n")          -> hit: return (p - body) + 17
0x0044f3a8  strstr(body, "/x-ns-proxy-autoconfig\r\n") -> hit: return (p - body) + 26
0x0044f3c8  strstr(body, "/macbinary\r\n")             -> hit: return (p - body) + 14
0x0044f3e8  strstr(body, "/x-macbinary\r\n")           -> hit: return (p - body) + 16
0x0044f408  strstr(body, "filename=")                  -> miss: return -1
0x0044f424  strchr(p, '"')                             -> miss: return -1
0x0044f440  strstr(p, <4-byte literal>)                -> miss: return -1
            return (p - body) + 4
```

Every path returns an **integer offset**. The filename is never copied, never
passed to `sprintf`, never reaches a path or a shell string. `form_formUpload`
uses the return value as `UpgradeByData`'s third argument and does nothing else
with the multipart headers.

`P8-18`'s refutation condition was written as "讀完發現 filename 沒有被使用 →
空白區關掉". That is what happened. **`formUploadConfig` is a different handler
and this note does not cover it** — `P8-12` owns that one, and it has not been
read.

## 4. How the first version of this was wrong

**The `filename=` selector never reached Ghidra.** `analyze.ps1` was called from
PowerShell with `-ExtraArgs @('string:filename=','string:boundary=')`, and
PowerShell consumed the trailing `=` — the headless log shows
`'string:filename' 'string:boundary'`. The run *worked*, because both strings
are prefixes of the intended ones and matched the same functions. It would not
have worked for a selector where the truncation changed the match, and there
would have been no sign: `BoaXref` reports unresolved selectors, and these
resolved.

**And a real mistake about `check_host`, caught by an existing note rather than
by a tool.** The first reading of this material concluded there is no host
validation in this build, having found `HOST` only in `process_option_line` at
`0x0040b918`, where it is stored and nothing else happens.
[`auth-flow-2018.md`](auth-flow-2018.md) had already named `check_host` as the
first step of the authorisation path, and it is a different function at
`0x00410470`. Writing "there is no `check_host`" would have contradicted a note
in the same repository. What that function actually does, and why it never runs,
is [`host-header-and-redirect.md`](host-header-and-redirect.md).
