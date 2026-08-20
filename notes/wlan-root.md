# `WLAN_ROOT`: the other half of the configuration

**Question carried out of W08 Day 0 (`PROGRESS.md` open #90), and the blocker
under `P7-7`:** `notes/compcs-decode.md` reported 344 TLVs and read as though the
configuration region were understood. One of those TLVs, `WLAN_ROOT`, is
**22,044 of the 45,226 decompressed bytes** and was reported as its length and
its hex. Half the configuration had never been looked at.

**Answer.** A table-valued entry is the same `{u16 id; u16 len; u8 value[len]}`
stream, repeated once per element, and it nests. `WLAN_ROOT` is **six blocks of
3,674 bytes, remainder zero**, each block 133 TLVs naming one wireless
interface, and each block contains four tables of its own. The names come from a
**second record table inside `libapmib.so`** that the recovery tool had been
reporting as a number and discarding.

| | |
|---|---|
| library | `unit-2018` `lib/libapmib.so`, sha256 `efbb7c3d…c0c2e` |
| main table | file offset `0x00d678`, 344 records |
| **wlan table** | file offset **`0x012754`**, **133 records**, `SSID` … `RX_RESTRICT` |
| `WLAN_ROOT` record | file offset `0x0122e0` — id `0x8065`, type `0x10`, total_size 15156, element_size 2526 |
| region | flash `0x008000` `COMPDS` and `0x00C000` `COMPCS`, `WLAN_ROOT` at payload offset 22955 |

```
fwrecon compcs $FWRE_WORK/dumps/flash-n150rt-console-1.bin --offset 0x008000 \
  --mib $FWRE_WORK/extracted/unit-2018/squashfs-root/lib/libapmib.so \
  -f json -o reports/compds-unit-2018.json
```

Both regions now decode `consistent` with **37 of 37 table-valued entries
expanded and 2,991 nested entries**. Output:
[`reports/compds-unit-2018.json`](../reports/compds-unit-2018.json) ·
[`reports/compcs-unit-2018.json`](../reports/compcs-unit-2018.json) ·
[`reports/mib-table-unit-2018.json`](../reports/mib-table-unit-2018.json).

---

## 1. The runner-up was the answer, and it was in the committed report

`tools/fwrecon/src/fwrecon/mibtable.py` finds the MIB table structurally: parse
every offset that reads as a 60-byte record, chain them into runs of that fixed
stride, take the longest. It then reports the second-longest **as a bare count**:

```json
"table_offset": 54904, "record_size": 60, "segments": 63, "runner_up": 133,
```

`runner_up: 133` has been in `reports/mib-table-unit-2018.json` since W04. Each
`WLAN_ROOT` block is 133 TLVs. The run at `0x012754` is `SSID`(1),
`CHANNEL`(2), `WLAN_MAC_ADDR`(0x18), the four `WEP64_KEY*`, `WPA_PSK`(0x1e),
`WSC_PSK`(0x115) — the name table for exactly those elements. The tool had
found it, printed its length, and thrown its contents away.

There are **twenty-one runs of two records or more** in this library and the
first version kept one. `libapmib` chains them; its own diagnostic string is
`mibtbl->id (%08x) unitsize (%d) totoal size (%d) mibtbl->nextbl %p`, which
says so in the vendor's own words, typo included.

The tool even had a guard for ambiguity — `if runner_up * 2 >= count` — and it
was right not to fire: 133 x 2 < 344, the main table *is* unambiguous. The
defect was not a missing check. It was discarding a result because the question
asked had been "which run is the table" instead of "what are the runs".

## 2. The 24 bytes after the name

A record is 60 bytes. `id` (u32, big-endian) and an inline 32-byte name account
for 36. The rest carries the geometry, and nothing had read it:

```
+36  u32  type            0 byte · 2 string · 4 byte-array · >=0x10 table
+40  u32  struct_offset   where the field sits in the in-memory config struct
+44  u32  total_size      bytes the field occupies
+48  u16  declared_size   the same number again
+50  u16  element_size    size of one element
+52  8 bytes              zero in every record of all six builds
```

so **`count = total_size / element_size`, read off the binary**:

| record | type | total_size | element_size | count |
|---|---|---|---|---|
| `WLAN_ROOT` `0x8065` | `0x10` | 15156 | 2526 | **6** |
| `MACAC_ADDR` `0x8036` | `0x11` | 540 | 27 | 20 |
| `SCHEDULE_TBL` `0x81f9` | `0x1d` | 280 | 28 | 10 |
| `WDS` `0x8041` | `0x1a` | 248 | 31 | 8 |
| `MESH_ACL_ADDR` `0x8246` | `0x1c` | 540 | 27 | 20 |
| `SSID` `0x0001` | 2 | 33 | 1 | `char[33]` |
| `USER_NAME` `0x00b6` | 2 | 31 | 1 | `char[31]` |

`struct_offset` corroborates independently: `USER_NAME` sits at `0xb1` and
`USER_PASSWORD` at `0xd0`, and `0xd0 - 0xb1 = 0x1f` = `USER_NAME`'s size. The
fields are consecutive in the struct, which is what the offsets should look like
if they are offsets.

## 3. The arithmetic that has to close

TLV encoding costs four header bytes per field, at **every depth**:

```
MACAC_ADDR      540 struct + 40 x 4 = 700   ✓ measured 700
SCHEDULE_TBL    280 struct + 50 x 4 = 480   ✓ measured 480
WDS             248 struct + 24 x 4 = 344   ✓ measured 344
MESH_ACL_ADDR   540 struct + 40 x 4 = 700   ✓ measured 700

one wlan block  2526 struct
              +  532  its own 133 headers
              +  616  the four nested tables' headers
              = 3674  ✓ measured 3674          6 x 3674 = 22044, remainder 0
```

Every number on the left comes from `libapmib.so`; every number on the right
comes from the flash. They are two sources and they agree to the byte. That is
what makes this a decode rather than a walk that produced something plausible.

`compcs.py` refuses rather than guesses, and each refusal has a test in
`tools/fwrecon/tests/test_compcs.py` that makes it fire:

* the ids inside a value must match the id set of a recovered run — no match is
  a refusal, and several matches is a refusal **only if they disagree**;
* the matched run's member sizes must sum to `element_size`;
* the TLV count must equal `fields x count`;
* the value length must equal `total_size + 4 x (TLVs at every depth)`;
* each element must consume exactly `len(value) / count` bytes.

## 4. Six blocks: one radio, four virtual APs, one repeater

| block | `SSID` | `WLAN_DISABLED` | `MODE` |
|---|---|---|---|
| 0 | `TOTOLINK N150RT` | 0 | 3 |
| 1–4 | `TOTOLINK N150RT1` … `4` | 1 | 0 |
| 5 | `TOTOLINK N150RT_RPT0` | 1 | 1 |

The vendor's own tool names the same index. `/bin/flash` prints
`get [wlan interface-index] mib-name`, so the six-block layout is documented by
the firmware, not only inferred from it.

**The four nested tables are fixed-size arrays with a separate fill count, and
the two do not have to agree.** `MACAC_NUM` is 0 while `MACAC_ADDR` carries 20
slots; `WDS_NUM` and `MESH_ACL_NUM` are 0 with 8 and 20 slots. `SCHEDULE_TBL_NUM`
is 10 and the array is 10 — which is **not** corroboration, it is the vendor
shipping ten disabled schedule slots. Every unit therefore carries 6 x 88 = 528
empty access-control and WDS slots in the 16 KiB the region gets.

## 5. `P7-7`: there is no factory PSK, because the device ships open

The register's frozen prediction says the factory PSK "is already decoded out of
`COMPDS`", and the refutation condition compares a derivation against that
value. **Neither can be evaluated: the value does not exist.** `COMPDS` block 0:

| field | id | value |
|---|---|---|
| `ENCRYPT` | `0x0019` | **0** |
| `WPA_PSK` | `0x001e` | 65 bytes, all zero |
| `WSC_PSK` | `0x0115` | 65 bytes, all zero |
| `WEP64_KEY1`–`4`, `WEP128_KEY1`–`4` | `0x0004`–`0x000b` | all zero |
| `SSID` | `0x0001` | `TOTOLINK N150RT` — fixed, no per-unit suffix |
| `HIDDEN_SSID` | `0x0015` | 0 |
| `WSC_DISABLE` | `0x010e` | 0 |
| `WSC_METHOD` | `0x010f` | 3 |
| `WSC_CONFIGURED` | `0x0110` | 1 |
| `WSC_REGISTRAR_ENABLED` | `0x0118` | 1 |
| `WSC_UPNP_ENABLED` | `0x0117` | 1 |

**Second source, and it is the device's own.** W07 ran `/bin/flash` on the unit
and `dumps/w07-enc.txt` holds one line: `ENCRYPT=0`. The static decode of the
factory region and the running device's own MIB reader agree.

`COMPCS` block 0 matches `COMPDS` block 0 field for field, so this unit is
running the factory wireless configuration: **an open network with a fixed SSID
and WPS enabled.** That is a stronger result than a derivable PSK would have
been — a derivation is a formula that has to be checked against other units,
while "there is nothing to derive" is a property of the shipped image.

**The scope, stated rather than left to be assumed.** This is a static read of
one unit's flash plus one line from that unit's own tool. It says what the
factory image contains. It does **not** say what the radio is transmitting now —
nothing in this project has yet observed a frame — and `P7-3`/`P7-4` remain the
tests that would.

## 6. Reading across: 2020 added the WPS defences this build does not have

The wlan table is the same size and the same membership in four of the six
builds, and grows by eleven in the two 2020 ones:

| build | wlan table at | records |
|---|---|---|
| `unit-2018` | `0x012754` | 133 |
| `v2.1.2` | `0x012920` | 133 |
| `n300rt-2.1.6` | `0x013920` | 133 |
| `n200re-3.2.0` | `0x013528` | 133 |
| `v3.4.0` | `0x011b94` | **144** |
| `n300rt-3.4.0` | `0x010194` | **144** |

Both 2020 builds add the same twelve records and drop the same one
(`WSC_DISABLES`, the plural one, beside the `WSC_DISABLE` that stays):

```
PEER_BSSID           WSC_LAST_CONFIG_ERR   WSC_AUTO_LOCK_DOWN
WSC_LOCKDOWN_PIN_REACHED   WSC_ER_NUM      WSC_ER_TBL
IEEE80211W           SHA256_ENABLE         SYNCPASSWORD
TXBF_MU              TDLS_PROHIBITED       TDLS_CS_PROHIBITED
```

`WSC_AUTO_LOCK_DOWN` and `WSC_LOCKDOWN_PIN_REACHED` are WPS PIN brute-force
lockout state. `IEEE80211W` is management-frame protection. **The 2018 build
this unit runs has no MIB entry for either**, which is the same shape as the
backdoor timeline in `notes/dump-vs-official.md`: the defence arrives in 2020,
and the build in the middle is the one only readable off the chip.

Presence of a MIB entry is not proof the feature is implemented, and absence is
not proof it is absent from the driver — these are configuration records, not
code. What is established is that this build has no configured lockout and no
configured PMF, which is what an attacker meets.

## 7. `WLAN_ROOT` was not the only one

Twelve other top-level entries were also reported as hex. All of them decode:

| entry | bytes | rows | named by |
|---|---|---|---|
| `PORTFW_TBL` | 2340 | 20 | `PORTFW_IPADDR..` `0xba90` |
| `QOS_RULE_TBL` | 2190 | 10 | `IPQOS_ENTRY_NAME..` `0xc738` |
| `IPFILTER_TBL` | 2140 | 20 | `IPFILTER_IPADDR..` `0xbd9c` |
| `PROFILE_TBL1` / `PROFILE_TBL2` | 1300 each | 5 each | `PROFILE_SSID..` `0xb130` |
| `URLFILTER_TBL` | 1200 | 30 | `URLFILTER_URLADDR..` `0xc378` |
| `TRIGGERPORT_TBL` | 1180 | 20 | `TRIGGERPORT_TRI_FROMPORT..` `0xc198` |
| `DHCPRSVDIP_TBL` | 1080 | 20 | `DHCPRSVDIP_IPADDR..` `0xb040` |
| `PORTFILTER_TBL` | 940 | 20 | `PORTFILTER_FROMPORT..` `0xbf7c` |
| `VLANCONFIG_TBL` | 867 | 17 | `VLANCONFIG_ENTRY_ENABLED..` `0xb8b0` |
| `STATICROUTE_TBL` | 840 | 10 | `STATICROUTE_DSTADDR..` `0xc42c` |
| `MACFILTER_TBL` | 700 | 20 | `MACFILTER_MACADDR..` `0xc0e4` |

The gap was not one entry. It was every entry with bit 15 set.

---

## How the first version of this was wrong

**Twice, and both were caught by the arithmetic rather than by inspection.**

**One: the header charge was counted at one level.** The check compared a
value's length against `total_size + 4 x (top-level TLVs)`. Every table without
nesting passed. `WLAN_ROOT` came out **3,696 bytes short** — and 3,696 is
exactly 6 blocks x 154 nested TLVs x 4, so the size of the miss named its own
cause. Had the check been written as "the walk consumed the buffer" instead,
which it also did, nothing would have been wrong and nothing would have been
verified: the walk consuming its input is a property of the walk, not of the
format. The version that failed usefully is the one that compared against a
number from somewhere else.

**Two: an ambiguity check refused a real answer.** The rule was "the observed
ids must match exactly one recovered run, zero and two are both refusals", and
`PROFILE_TBL1` and `PROFILE_TBL2` were refused for matching two. There really
are two `PROFILE_SSID..PROFILE_PSK_FORMAT` runs, at `0xb130` and `0xb43c`, with
the same twelve ids, the same names and the same sizes — one per profile table.
Refusing that is refusing to choose between two spellings of one word. The rule
now refuses candidates that **disagree**, which is what it was always meant to
say, and the loosening cost a test that pins the disagreeing case.

**And one thing that was not wrong but was overstated for an hour.** Eliding the
parent's hex once its rows are decoded was written up as a size fix. It took the
report from 2.06 MB to 2.00 MB. The report grew from 288 KB because it now holds
3,335 entries instead of 344 — that is content arriving, not overhead. What the
elision actually buys is that the same bytes are no longer asserted in three
places, which is worth doing for its own reason and not for the one first given.
