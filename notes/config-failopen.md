# When the settings regions are invalid, the boot script turns telnet on

**The answer, with addresses.** `/bin/startup.sh` — which `/etc/init.d/rcS` runs
before anything else on this unit — contains this, at lines 19–47:

```sh
19  $TOOL test-dsconf                                  # flash test-dsconf
20  if [ $? != 0 ]; then
21  $TOOL test-csconf                                  # flash test-csconf
22  if [ $? != 0 ]; then
23      echo 'Default configuration invalid, reset default!'
24      $LOADDEFSW                                     # flash default-sw
25  eval `$GETMIB WLAN_BAND2G5G_SELECT`                # <- a shell eval, see §4
26      flash set WAN_DHCP 1
    ...
43      flash set TELNET_ENABLED 1                     # <- this line
44  else
45      echo 'Default configuration invalid, write current configuration ...'
46      $LOADWC                                        # flash write-current
47  fi
```

Both settings regions invalid — `COMPDS` at flash `0x008000` **and** `COMPCS` at
`0x00C000` — and this unit boots on hardcoded defaults **and enables telnet**.
W02's three-way read established that `/etc/passwd.org` has carried
`root` / `123456` and `onlime_r` / `12345`, both uid 0, byte-identical from the
2015 image through this 2018 build; the 2020 build removed only `onlime_r`.

**Register case `P8-24`, recorded `partial`, and the boundary is exact:**

| | measured? |
|---|---|
| the fail-open branch is reached when both regions are invalid | ✅ **yes**, under emulation |
| what the branch then writes | ❌ **no** — the recovery write dies before it completes, and the reason is the emulator, not the device |

Evidence: [`reports/failopen-unit-2018.json`](../reports/failopen-unit-2018.json),
produced by [`tools/failopen-probe.sh`](../tools/failopen-probe.sh) against the
`unit-2018` emulation profile, whose `/dev/mtdblock0` is a copy of this unit's
own 4 MiB flash dump.

---

## 1. Seven damage states, and what each one makes the boot script do

Each row is a fresh restore from `.mtd-pristine.bin`, then damage, then the
vendor's own `/bin/startup.sh` run under `qemu-user`.

| damage | `test-dsconf` | `test-csconf` | branch `startup.sh` took |
|---|---|---|---|
| none (control) | 0 | 0 | *(no branch)* |
| `COMPDS` signature zeroed | **255** | 0 | line 45 — `write-current` |
| `COMPCS` signature zeroed | 0 | **255** | the trailing check — `reset1` |
| **both signatures zeroed** | **255** | **255** | **line 23 — `reset default!`** |
| `COMPDS` payload byte flipped | **0** | 0 | *(no branch)* |
| `COMPCS` payload byte flipped | 0 | **255** | the trailing check — `reset1` |
| both payload bytes flipped | **0** | **255** | the trailing check — `reset1` |

Two readings fall out of the table, and the second one is the useful one.

**The branch is reached.** With both signatures destroyed, `startup.sh` printed
its own line 23 verbatim:

```
Default configuration invalid, reset default!
```

**The two validity tests are not equally strict, and that decides how narrow
the attack is.** `test-dsconf` reports what it wants:

```
Invalid default setting signature or version number [sig=, ver=-1, len=0]!
Expect [sig=6G, ver=3, len=31878]!
```

It checks the **decompressed** header — signature `6G`, version 3, declared
length 31,878 — which is why a single flipped byte deep in the LZSS payload does
not disturb it: the stream still decompresses and the header still reads right.
`test-csconf` fails on the same flip, and says why:

```
mib_tlv_init fail!!
```

so it walks the TLV records as well.

**Consequence.** Reaching the fail-open branch is not "corrupt the settings
area". It is specifically **damage `COMPDS`'s decompressed header**, at
`0x008000` and the bytes the container header points at. `COMPCS` is the easy
one and it is not the one that matters — damaging it alone lands on `reset1`,
which restores from defaults and leaves telnet where it was.

## 2. What the emulator cannot say, and the control that proves the boundary is real

Every damaged state ends the same way:

```
qemu: uncaught target signal 10 (Bus error) - core dumped
```

`flash default-sw` and `flash reset1` both take an unaligned access that the
device's MIPS kernel fixes in its trap handler and `qemu-user` does not. So the
flash image is byte-identical before and after in **all seven** states, and
`flash get TELNET_ENABLED` answers `unreadable` for as long as the region stays
damaged.

There are two ways to read that, and they lead to opposite conclusions:

1. this environment cannot write flash at all, so the SIGBUS says nothing; or
2. the **recovery** write specifically dies.

The probe separates them with a control that must pass before anything else is
believed: on a healthy image, `flash set WAN_DHCP 7` writes and reads back as
`7`. **Plain writes work here.** So it is (2), and the boundary is the recovery
path, not the environment.

**Therefore this note may not say what the device does.** It says the branch is
entered. Whether `flash default-sw` succeeds on silicon and whether
`flash set TELNET_ENABLED 1` survives the `reset1` that runs afterwards is a
question for the hardware, and it is a small one:

> **What would confirm it.** With a current 64 KiB snapshot of the settings area
> taken first, zero the eight bytes at `0x008000` and at `0x00C000` through the
> boot loader's `FLW`, boot, and read `TELNET_ENABLED` — over the console if the
> web server does not come up, over telnet if it does. Restore from the snapshot
> either way. The recovery path this depends on is the one `P0-3` rehearsed on
> 2026-08-17.

## 3. Why this matters to `P8-12`

`P8-12` records the "upload a config, get telnet" chain as blocked on this
project's own tooling: `fwrecon compcs` can decode but not encode, so a **valid**
settings blob with `TELNET_ENABLED=1` cannot be produced, and the case says the
chain is stuck on the tool rather than on the device.

This path does not want a valid blob. It wants an invalid one, and specifically
an invalid `COMPDS`. Producing invalid bytes needs no encoder at all.

That does not make `P8-12` wrong — it makes the *goal* wrong. The two chains want
opposite things from the same file format, and only one of them needs the missing
half of the tool.

## 4. The `eval`, which was found while looking for something else

`P8-8` asked whether any MIB value is interpolated into a shell command by the
boot scripts. The complete inventory of `flash get` in this rootfs is nine sites,
and only two of them are `eval`:

| site | field(s) | how the value is used | reaches a shell? |
|---|---|---|---|
| `snmpd.sh:36–44` | nine `SNMP_*` names | **`eval`** | ❌ none of the nine resolves in this build |
| `startup.sh:25` | `WLAN_BAND2G5G_SELECT` | **`eval`** | ✅ resolves, and the eval runs — see below |
| `smbbak.sh:2,47` | `SAMBA_TYPE`, `SAMBA_PASSWORD` | backtick capture → `[ ]` test, and argv after word-splitting | ❌ no `eval`; and `smbpasswd` is not in this rootfs |
| `smb.sh:2,4,7` | `IP_ADDR`, `SAMBA_USER`, `SAMBA_TYPE` | backtick capture → written into a config file | ❌ |
| `mp.sh:8,10,12` | `HW_NIC0_ADDR` | commented out | — |

`snmpd.sh` is the site the playbook expected to be live, and it is the one with
the strongest sink — `eval`, not interpolation, and `flash get` prints string
values inside double quotes, where a backtick still executes. It is dead anyway,
and for a reason nobody predicted: **the nine names do not exist in this build's
MIB table.** Two instruments agree —

- the table recovered from `libapmib.so`
  ([`mib-table-unit-2018.json`](../reports/mib-table-unit-2018.json), 344 entries)
  holds `SNMP_RO_COMMUNITY` and `SNMP_RW_COMMUNITY` and nothing else beginning
  `SNMP`;
- the vendor's own `/bin/flash`, asked directly, answers `flash get SNMP_NAME`
  with a usage dump and `rc=255`.

The script asks for `SNMP_ROCOMMUNITY`. The table has `SNMP_RO_COMMUNITY`. One
underscore, and the scripts and the MIB table are from different SDK vintages —
which is also why `snmpd`, `smbd`, `smbpasswd` and `nmbd` are absent from `/bin`
while three scripts that drive them are shipped.

`startup.sh:25` is the live one, and the fail-open experiment demonstrated the
mechanism by accident. With the configuration invalid, `flash get
WLAN_BAND2G5G_SELECT` prints its error text instead of an assignment, and the
transcript shows the shell trying to run it:

```
/bin/startup.sh: eval: line 1: Invalid: not found
```

That is `eval` executing the first word of `Invalid default setting signature
or version number ...` as a command. **The sink is real and it is on the boot
path.** What it currently carries is a vendor error string, so there is nothing
to exploit — but "whatever `flash get WLAN_BAND2G5G_SELECT` prints becomes shell
input at boot" is a different statement from "this is dead code", and it is the
one the evidence supports.

## 5. How the first version of this was wrong

**Twice, and the first one produced a complete-looking table of nothing.**

`tools/failopen-probe.sh` ran the boot script as `qemu-env.sh run
/bin/startup.sh`. `run` executes its argument under `qemu-mips-static`, which
wants an ELF; handed a `#!/bin/sh` file it fails quietly. The first working run
printed seven neatly formatted states in which `startup.sh` said nothing and
changed nothing — including the one state the probe was written to detect. The
numbers were plausible, the table was complete, and the script had never
executed. What caught it was that the *control* state and the *both-damaged*
state produced identical output, which cannot be true if the branch exists.

The fix is `run /bin/sh /bin/startup.sh`, and the probe now runs
`echo SHELL_RUNS` through the same path first and refuses if it does not come
back — because "the boot script said nothing" and "nothing can say anything
here" are indistinguishable without it.

**And a second one, in a tool this note did not set out to touch.**
`qemu-env.sh reset` ended with `rm -f "$ENVDIR/var/web/config.dat"`, while
`cmd_serve` deliberately creates that path as a **directory** — the trick from
`P0-9` that makes `boa`'s start-up `open()` return `EISDIR` and keeps it alive
under emulation. `rm -f` cannot remove a directory, so after any `serve`,
`reset` returned non-zero even though every restore above that line had
succeeded, and the leftover directory survived a reset that promised to
"restore BOTH pieces of state". It had been that way since `serve` was written;
nothing noticed because no caller had ever checked `reset`'s exit status.
Instrument bug 37.
