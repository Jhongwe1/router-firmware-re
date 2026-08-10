# The MIB table, and what `config.dat` actually is

**Question carried out of W03:** `libapmib.so` was "on the path of every finding
this week and completely unread". Every decision in `boa` is a number —
`apmib_get(0xb6, username)` — and W03 described those numbers by what the
surrounding code did with them. That is a guess wearing a fact's clothes:
`0xb6` was called "the configured admin username" because it was compared
against one.

**Answer:** `libapmib.so` carries the table, 413 records in V2.1.2 and 412 in
V3.4.0, and every id `boa` uses now has its real name.

| id | name | where `boa` uses it |
|---|---|---|
| `0xb6` | `USER_NAME` | `process_header_end`, `formLogin` — the web admin user |
| `0xb7` | `USER_PASSWORD` | same — the web admin password |
| `0x1ec` | `AUTHG_IP_ADDR` | the 2015 "session": the IP that logged in |
| `0x1ed` | `AUTHG_USER_NAME` | credentials recorded at login |
| `0x1ee` | `AUTHG_PASS_WORD` | credentials recorded at login |
| `0xaa` | `IP_ADDR` | V3.4.0 gate: the LAN address |
| `0xab` | `SUBNET_MASK` | V3.4.0 gate: `(client ^ IP_ADDR) & SUBNET_MASK` — off-LAN test |
| `0xc5` | `HOST_NAME` | V3.4.0 gate |
| `0x68` | `WAN_DHCP` | read by `handleForm` before every dispatch |
| `0xc1c` | `WEB_LANG` | `formWsc` |

Regenerate:

```bash
fwrecon mib $FWRE_WORK/extracted/v2.1.2/squashfs-root/lib/libapmib.so -f json \
  -o reports/mib-table-2.1.2.json
```

Output: [`reports/mib-table-2.1.2.json`](../reports/mib-table-2.1.2.json),
[`reports/mib-table-3.4.0.json`](../reports/mib-table-3.4.0.json).
Code: [`tools/fwrecon/src/fwrecon/mibtable.py`](../tools/fwrecon/src/fwrecon/mibtable.py).

## The record layout was measured, not assumed

This project has already been burned once by treating a leaked `rtl819x` SDK
header as a description of the binary in front of it
([`dispatch-table.md`](dispatch-table.md)). So the layout came from the bytes,
anchored on the three names Boa's authorisation code must be using:

```
00c818  00 00 01 ec                                    id
00c81c  41 55 54 48 47 5f 49 50 5f 41 44 44 52 00 ...  "AUTHG_IP_ADDR"
...
00c854  00 00 01 ed                                    id   <- exactly 0x3c on
00c858  41 55 54 48 47 5f 55 53 45 52 5f 4e 41 4d 45   "AUTHG_USER_NAME"
```

A 60-byte record: big-endian `uint32` id, then a 32-byte **inline** name. The
names being inline rather than pointed-to is why `strings` shows them running
together with a stray leading byte — `APROFILE_WEP_KEY2`, `dMIB_ROOT` — which is
what made them look like noise in W01.

Bit 15 of an id marks a table-valued entry: `IPFILTER_ENABLED` is `0x74`,
`IPFILTER_TBL` is `0x8076`.

## `/web/config.dat` is a compressed dump of this table

The writer is in `libapmib.so`. Its strings give the whole format:

```
/web/config.dat
Create config file error!
TLV Data len is too long
malloc for Compress buffer failed!!
COMPCS
Write config file error!
```

and three sibling magics for the three flash regions on `/dev/mtdblock0`:

| magic | region |
|---|---|
| `COMPCS` | **c**urrent **s**etting — what `config.dat` contains |
| `COMPDS` | default setting |
| `COMPHS` | hardware setting |

So `config.dat` is: the magic `COMPCS`, then a **compressed TLV stream** of MIB
entries. Not encrypted — compressed. That is the substance of **CVE-2019-19823,
"plaintext password storage"**: `USER_PASSWORD` is an ordinary MIB entry with an
ordinary TLV record, and anyone who can decompress the blob can read it. There is
no hashing step anywhere in the path, which is also why `formLogin` can do
`strcmp(userpass, cfg_pass)` and why `process_header_end` can compare stored
against configured credentials directly.

Chained with the authorisation reading — `GET /config.dat` is outside the gate in
**both** builds ([`auth-flow.md`](auth-flow.md),
[`auth-flow-2020.md`](auth-flow-2020.md)) — that is CVE-2019-19822 → 19823 end to
end, and the second half is now located rather than cited.

**Not done:** the compressor is not identified and the TLV stream has not been
parsed. Naming the algorithm and decoding a real `config.dat` byte-for-byte needs
a real `config.dat`, which needs W02's flash dump or a running server. Until
then the correct statement is "the file is a compressed serialisation of the
table above", not "the password is at offset N".

## Two things the table says that the code did not

**V3.4.0 has no `AUTHG_*` entries at all.** The 2020 table matches 2 of the 5
anchor ids; `AUTHG_IP_ADDR`, `AUTHG_USER_NAME` and `AUTHG_PASS_WORD` are simply
absent. That is an independent confirmation, from a different file, of what
[`auth-flow.md`](auth-flow.md) inferred from `boa`'s string table — and it
explains *why* the 2020 build had to invent the 5-slot in-memory session table
at `0x004785a4`: it no longer had a MIB entry to keep the logged-in IP in.

**V2.1.2 binds id `0x182` to two different names** — `CUSTOM_PASSTHRU_ENABLED`
and `MLD_PROXY_DISABLED`. `apmib_get(0x182)` returns whichever record the lookup
reaches first. This is not a recovery artefact: `libapmib` ships the string
`"MIB Error: %s detect duplicate id in %s"` and exports `mibtbl_check`, so the
vendor tests for exactly this at load time. V3.4.0 has no duplicates.

## How the first version of this note was wrong

The tool it rests on failed its own self-check twice, and both failures were the
check being wrong rather than the walk.

**First**, it required ids to increase monotonically across the table, on the
reasoning that a C array is written in declaration order. That fired instantly:
`0x1ef AUTHG_PHONE` followed by `0x13e DFS_ENABLED`. The reasoning was wrong —
`libapmib` chains sub-tables, and says so in its own diagnostic string
(`mibtbl->nextbl %p`). There are 64 chained segments in V2.1.2 and 57 in V3.4.0,
and a falling id is a boundary, not damage.

**Second**, it anchored the whole recovery on finding the literal
`AUTHG_IP_ADDR` exactly once — and V3.4.0 does not contain that string. The tool
reported "cannot locate the table unambiguously" for a build whose table is
perfectly intact, which is the worst possible failure mode: a real absence in the
firmware presented as a tooling error. Recovery is now structural — parse every
offset that can be read as a record, chain them at the fixed stride, take the
longest run, and refuse if a comparable second run exists — and the anchors are
used only to *check* the result, with an absent anchor reported as absent.

**Third**, and this one was nearly written into the notes: the duplicate `0x182`
was initially reported as `SUSPECT — the walk is reading past the table`. It is a
defect in the vendor's table. Treating it as a tool failure would have thrown
away a finding to protect the tool's reputation.
