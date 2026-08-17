# Emulating the build this unit runs — what the flash dump turned into, and what it cost

Three questions this repository had been carrying are answered by *running* the
resident firmware rather than reading it, so they go first.

| | |
|---|---|
| **W04-2 open #8** — does `POST /boafrm/formSaveConfig` create a servable `/web/config.dat`? | **Nothing has to POST anything.** `boa` opens `/web/config.dat` with `O_RDWR\|O_CREAT\|O_TRUNC` during start-up, immediately after reading the `COMPCS` region at flash `0x00C000` and **before it creates a listening socket**. The file is in the document root from the moment the web server is up |
| **W05 Day 0 open #13** — "this unit has no `nc` and no `tftp`" rested on an ELF inventory that cannot see busybox applets | **Confirmed, by the right instrument**: busybox printing its own compiled-in applet list. 48 applets, no `nc`, no `tftp`, no `wget` — **and `telnetd`, `ping`, `login` and `chpasswd` are all there** |
| **W05 Day 0 open #15** — `SNMP_RO_COMMUNITY` / `SNMP_RW_COMMUNITY` decode as all-zero strings, and no `SNMP_ENABLED` was recovered. Decoder fault, or the truth? | **Not a decoder fault.** The vendor's own `/bin/flash all` prints `SNMP_RO_COMMUNITY=""` and `SNMP_RW_COMMUNITY=""`, and across all **2,317** lines it emits there is no `SNMP_ENABLED` under any spelling |

And the risk the W05 plan rated highest for this work did not materialise:
**`libapmib` reaches the flash with `lseek()` + `read()`, not `ioctl()`**, so an
ordinary file is a sufficient stand-in for `/dev/mtdblock0`:

```
429 open("/dev/mtdblock0",O_RDONLY) = 3
429 lseek(3,24576,SEEK_SET) = 24576        <- 0x6000, the H601 hardware block
429 read(3,0x2b2a6de8,6) = 6
...
429 lseek(3,32768,SEEK_SET) = 32768        <- 0x8000, COMPDS
```

Those two offsets are the ones W02 derived from the data. **The vendor's binary
seeks to them by itself**, which is a second source for the flash map that does
not go through any tool written here.

Build it with [`tools/qemu-env.sh`](../tools/qemu-env.sh); the guard suite is
[`tools/test-qemu-env.sh`](../tools/test-qemu-env.sh).

---

## 1. What the environment is

`qemu-mips-static` (8.2.2, big-endian) running the **unit-2018 rootfs** in a
chroot — the filesystem read out of this unit's own flash in W02, not a
downloaded image. Every piece of set-up below is copied from the device's own
boot, and the note says where each line came from:

| step | taken verbatim from |
|---|---|
| `mkdir /var/{tmp,web,log,run,…}` | `/etc/init.d/rcS` |
| `cp /etc/shadow.sample /var/shadow` | `/etc/init.d/rcS` |
| `cp /etc/passwd.org /var/passwd` | `/bin/sysconf`'s string table |
| `cp -a /etc/boa/boa.conf.bak /var/boa.conf` then `echo "Port 80" >>` | `/bin/sysconf`'s string table |
| `cd /web ; flash extr /web` | `/etc/init.d/rcS` |

`/etc/boa/boa.conf` is a **dangling symlink to `/var/boa.conf`**, which is why
the config had to be constructed rather than found; `/web` is a dangling symlink
to `/var/web`, which is a ramfs on the device. The effective configuration is
fourteen lines, and two of them matter here: `DocumentRoot /web` and
`User root / Group root`.

**The one thing that is not the device's own is the flash partition**: a copy of
`flash-n150rt-console-1.bin` (`sha256 a800059a…`) placed at `/dev/mtdblock0`.
The real dump is verified against its recorded hash and never written to.

---

## 2. What was faked, and whether it distorts the result

This is the table the week was for. A substitution with no entry here is a
result nobody can bound.

| missing | how it was supplied | does it distort the result? |
|---|---|---|
| `/dev/mtdblock0` | a byte-for-byte copy of this unit's flash | **No.** Real data, from this device, and `apmib` reads it the same way it reads the real partition — `lseek`+`read`, confirmed in `strace` |
| `/var` (a ramfs on the device) | an ordinary directory tree | **No** for reachability and content. **Yes** for persistence: on the device `/var` is cleared by a reboot, here it is not |
| `/var/boa.conf` | `sysconf`'s own two commands, run by hand | **No** — the bytes are the device's `boa.conf.bak` plus the same `Port 80` line |
| the document root | `flash extr /web`, the device's own extractor, over the device's own flash | **No.** 143 files, and every one's SHA-256 matches [`webbundle-unit-2018.json`](../reports/webbundle-unit-2018.json) |
| `/etc/TZ` | not supplied; `open()` returns `ENOENT` | **No** for anything measured here. Timestamps in a log would be UTC rather than local |
| `wlan0` | not supplied; `ioctl(SIOCGIWNAME)` returns `ENODEV` | **Yes, and this bounds a whole class.** `boa` queries the wireless interface during start-up. **No wireless-dependent path can be concluded on in this environment** |
| Realtek kernel modules | not supplied | **Yes** — same class as above |
| MTD erase-block semantics | a plain file: every write succeeds and rewrites nothing else | **Yes, in the direction of optimism.** On the device a write to the `H601` block is a read-modify-erase-program cycle over the whole erase block. See §5 |
| the kernel's unaligned-access fixup | **not supplied, and it cannot be** | **Yes — this is where `boa` stops.** §4 |
| **the System V shared-memory MIB cache** | **nothing: it is real, and it is the host's** | **Yes, and it is the trap in this environment.** §3 |

---

## 3. The state that is not in the flash file

`flash`, `boa` and `sysconf` cache the MIB table in **System V shared memory**:

```
429 ipc(2,-734995502,1,1974)   = -1 errno=17 (File exists)     <- semget
429 ipc(23,1009834962,1166,1974) = 1                            <- shmat
429 ipc(21,1,0,724220752) = 0                                   <- shmdt
```

Those segments belong to the **host** kernel. They outlive every guest process,
and restoring `/dev/mtdblock0` does not touch them.

This was not deduced from the strace — it was **found by a measurement going
wrong**. A run that changed only `HW_WLAN0_REG_DOMAIN` produced a diff
containing seven bytes of the WPS PIN field, which the previous test had
written. Restoring the file had restored nothing.

```
$ ipcs -m
key        shmid  owner perms bytes  nattch
0x3c30dbd2 0      root  666   1166
0x3d30dbd2 1      root  666   31878
0x3e30dbd2 2      root  666   31878
```

`qemu-env.sh reset` removes them, and the guard suite has a case asserting that
a value written by a previous run does not survive it. **Restoring the image is
not a reset**, and that sentence is in the tool's own header because it is the
one way to get a wrong number out of this environment while everything looks
fine.

It is worth separating what this is: on the device the same mechanism is
correct and necessary — it is how `boa`, `sysconf` and `flash` see one
configuration. It only becomes a contaminant because the host keeps it across
what were meant to be independent runs.

---

## 4. Where `boa` stops, and exactly why

`boa` loads, links, initialises, reads the configuration out of the flash file
and creates `/web/config.dat` — then dies with `SIGBUS`, deterministically, four
runs out of four, **before `bind()`**:

```
401 open("/dev/mtdblock0",O_RDONLY) = 3
401 lseek(3,49152,SEEK_SET) = 49152        <- 0xC000, COMPCS
401 read(3,0x490018,7490) = 7490
401 open("/web/config.dat",O_RDWR|O_CREAT|O_TRUNC) = 3
--- SIGBUS {si_signo=SIGBUS, si_code=1, si_addr=0x00492b41} ---
```

`si_code=1` is `BUS_ADRALN`, and `0x00492b41` is odd. The faulting instruction,
from qemu's last translation block:

```
0x2b2c87cc:  lw    v0,0(s0)
0x2b2c87d0:  addu  s8,s2,s8
0x2b2c87d4:  subu  s7,v0,s7
0x2b2c87d8:  andi  s7,s7,0xffff
0x2b2c87dc:  sh    s7,0(s8)      <- store halfword to s2+s8
0x2b2c87e0:  sh    s7,26(sp)
```

`libapmib.so` is mapped at `0x2b2c6000`, so this is **file offset `0x27dc`**.

**The decompiler is not the only witness, and neither is qemu.** The MIPS
encoding of `sh rt, offset(base)` is `0x29 << 26 | base << 21 | rt << 16 | off`;
for `sh s7,0(s8)` that is `0xa7d70000` and for `sh s7,26(sp)` it is `0xa7b7001a`.
The bytes in the file:

```
0027dc  a7 d7 00 00  a7 b7 00 1a  26 31 00 3c  8e 22 00 00
```

Both, exactly, and the match also confirms the load base rather than assuming
it. **Opcode `0x29` is standard MIPS I.** Nothing in the surrounding block is
outside the base ISA.

That matters because the W05 plan named a specific competing explanation:

> Lexra's extra instructions sit in opcode space Ghidra's stock MIPS module does
> not recognise, so **qemu fails loudly where Ghidra fails silently.** A SIGBUS
> is a loud failure.

**It is not that.** W04-2's mnemonic census already found **zero** coprocessor-2
or -3 encodings in these binaries, and the instruction here is decoded
identically by two independent routes. What is left is the ordinary reading:
**`libapmib.so` performs an unaligned 16-bit store while serialising the
configuration**, MIPS raises an address error, and on the device
`arch/mips/kernel/unaligned.c` emulates the store and the process continues.
`qemu-mips-static` has no guest kernel to do that, so the signal reaches the
process.

No CPU model avoids it: `4Kc` and `24Kf` both trap, and `mips32r6-generic` —
where unaligned access is architectural — refuses the binary outright
(`ELF binary's NaN mode not supported by CPU`).

So this is a property of the emulator's scope, **not a defect in the firmware**
and not a limit of the instruction set. It also says something about the device:
this code path takes a kernel trap per store on every boot. `/proc/cpu/alignment`
would count them, and there is still no shell to read it from.

**What that costs:** `boa` does not serve a request here. Section 5 is what was
done instead, and it turns out to reach the thing that mattered by a shorter
route.

---

## 5. What the environment measured anyway

The sink in the line W04 root-caused is `system()`, and `system()` is
`/bin/sh -c`. Both the shell and `/bin/flash` are in hand, so the composed
command can be executed without `boa` in the path:

```
sprintf(buf, "flash set HW_WLAN0_WSC_PIN %s", localPin);  system(buf);
```

```
$ sudo tools/qemu-env.sh run /bin/sh -c \
      'flash set HW_WLAN0_WSC_PIN 1;ls -l / > /var/web/x.txt 2>&1;#'
$ sudo tools/qemu-env.sh diff
3 bytes changed
  0x00648a  0x39 -> 0x31
  0x00648b  0x39 -> 0x00
  0x006493  0x0d -> 0x4e   <- H601 checksum
checksum: delta 65, expected 65 -> balances
```

**One command, both observation channels**: the command's output in the document
root, and the exact bytes it changed in the flash image.

### `flash set` writes flash for hardware MIBs and not for configuration MIBs

Each row is a separate run from a reset environment, because of §3.

| set | bytes changed in the 4 MiB image | checksum at `0x006493` |
|---|---|---|
| `HW_WLAN0_WSC_PIN` `99956042` → `87654321` | **8** — seven digits at `0x648a`–`0x6491` plus the checksum. The fourth digit is `5` in both, and that byte does not change | Δ `+8`, predicted `+8` |
| `HW_WLAN0_REG_DOMAIN` `1` → `5` | **2** — `0x60a5` plus the checksum | Δ `−4`, predicted `−4` |
| `DEVICE_NAME` `RTL8196E` → `TESTNAME` | **0** — and a *fresh process* reads back `TESTNAME` | unchanged |
| the same, followed by `flash write-current` | **0** | unchanged |

Three consequences:

1. **The byte at flash `0x006493` is a checksum.** It moves by the exact 8-bit
   negation of the sum of the changed payload bytes, for two fields `0x3EE`
   apart — so it covers at least `0x60a5`…`0x6491`, not just the field beside
   it. W04-2 found an 8-bit checksum in `libapmib.so`'s `Decode` for the
   `COMPxx` regions; this locates the `H601` region's at a concrete offset.
2. **`flash set` on a configuration MIB does not write flash.** It updates the
   shared-memory table only, and `write-current` did not commit it either. The
   commit path is still unread.
3. **The line W04 root-caused sets a *hardware* MIB**, so it *does* write flash
   immediately — which is what makes the flash-difference oracle work, and is
   also §5.1.

### 5.1 The W06 PoC writes into the one region that exists nowhere else

`HW_WLAN0_WSC_PIN` lives at `0x648a`, inside the **`H601` block at `0x006000`** —
the same block as this unit's MAC addresses and radio calibration. W02 recorded
that this block "exists nowhere else in the world; the vendor image does not
contain it and a factory reset does not restore it."

So: **the PoC's write lands in the irreplaceable region**, and on the device it
is not a 3-byte poke but a read-modify-erase-program cycle over the containing
erase block. A power loss inside that window loses the block. Nobody had written
this down. It does not change the plan — the 64 KiB snapshot before every
session already covers it — but it changes which target is preferred, and the
target W04-2 chose from evidence (`formSysCmd` → `system()`, output to
`/tmp/syscmd.log`) turns out to be the one that **writes no flash at all**.

### 5.2 Command separators, against the device's own shell

Ten payload shapes, each the string `boa`'s `sprintf` would produce, executed by
`/bin/sh` from this rootfs (busybox 1.13.4 `ash`). Nine reach the second
command:

| shape | result |
|---|---|
| `1;cmd` · `` 1`cmd` `` · `1$(cmd)` · `1\|cmd` · `1&&cmd` · `1&cmd` · newline · `1>/dev/null;cmd` · `1;{ cmd; }` | executes |
| `1\|\|cmd` | **does not execute** |

`||` failing is not a filter and not a defence. `flash set` **succeeded**, so
`||` short-circuits. **The absence of a result is itself the measurement**: it
reports the sink command's exit status, which none of the other nine do.

### 5.3 The applet list, and a payload that would have wasted an hour

```
ash, bunzip2, bzcat, cat, chpasswd, cp, cut, date, echo, expr, false, free,
getty, grep, halt, head, hostname, ifconfig, init, ip, kill, killall, klogd,
ln, login, ls, mkdir, mount, nice, nslookup, ping, ping6, poweroff, ps, reboot,
renice, rm, route, sed, sh, sleep, syslogd, tail, telnetd, tr, traceroute,
true, umount, uptime, wc
```

**There is no `id`.** The W05 plan's first-choice payload was
`…;id > /var/web/x.txt;#`, and it behaves exactly like a blind injection that
did not land:

```
/bin/sh: id: not found
-rw-r--r--  1 root root  0  /var/web/x.txt
```

The redirection creates the file; the command that would have filled it does not
exist. On hardware that is an empty 200 response and an afternoon spent on the
wrong hypothesis. `ls -l /`, `ps`, `ifconfig` and `cat` all work.

And two entries in that list are the second half of a chain: **`telnetd` is
compiled in**, while `TELNET_ENABLED` is `0`; `login` and `chpasswd` are there
too, and `/etc/passwd.org` still carries `root:123456`.

---

## 6. What this environment confirmed about instruments written here

Both of these were previously supported only by the tools' own internal checks.

**`fwrecon web`'s `w6cg` parser, confirmed byte-for-byte.** The format has no
checksum and no entry count, so the parser's only check was structural — every
stride is `64 + length`, and the walk lands on the last byte or it does not.
`flash extr /web`, the vendor's own extractor, run over the same image:

```
entries declared by fwrecon          : 143
files written by vendor 'flash extr' : 143
sha256 identical                     : 143
declared but not written             : 0
written but not declared             : 0
```

**`fwrecon compcs`, checked against the vendor's `flash all`.** 2,317 MIB lines
against 344 decoded entries; 316 names appear in both.

| | |
|---|---|
| identical | **249** |
| explained: `char[]` rendered as hex by `fwrecon` where the bytes are a C string | 45 |
| explained: 4-byte integer rendered as a dotted quad by `fwrecon` | 11 |
| explained: `fwrecon` punctuates MAC addresses | 6 |
| explained: the vendor escapes spaces as `\ ` for `eval` | 4 |
| **unexplained** | **1** |

The four rules are applied by a script that **exits non-zero if any difference
is left over**, rather than by eye. Not one difference is a disagreement about a
*value* — they are rendering, and on two of the four `fwrecon` is the one that
should change: `DDNS_USER` prints as 102 hex zeros where the field is an empty
string, and `QOS_MANUAL_DOWNLINK_SPEED` prints as `0.1.134.160` where it is
`100000`.

The one left over is **`L2TP_SERVER_IP_ADDR`** (id `0x14d`): `fwrecon`'s
recovered MIB table types it as 64 bytes, the vendor's binary prints it as an
IPv4 address. **Every byte of the field is zero, so the data cannot arbitrate**,
and the note says that rather than picking a winner. It is one entry in 316 and
it is recorded, not resolved.

---

## 7. What this environment cannot decide

- **Anything wireless.** `ioctl(SIOCGIWNAME)` fails at start-up; there are no
  Realtek modules. `formWsc`'s *effects* are out of scope here even though its
  *shell string* is not.
- **Anything about serving a request.** No `bind()` happens. The authorisation
  gate, `translate_uri`, the `.htm`/`.asp` substring test and every Phase 2
  question stay where they were: read from instructions, not executed.
- **Timing, ordering, and anything that depends on the real MTD driver.**
- **Whether the erase-block behaviour in §5.1 is what the device does.** That is
  a statement about the MTD layer, made from the code and from how NOR flash
  works, and it has not been observed on this unit.

---

## 8. How the first version of this note was wrong

**It counted the document root with `ls` and got 90.** `fwrecon` says 143, so
the first draft opened a section on two instruments disagreeing about the same
bytes. They do not: `ls` lists the top level and the bundle has four
directories. `find -type f` gives 143. The comparison script written next was
wrong in the same direction — it compared `fwrecon`'s stored paths
(`icons/ICON/icon_QoS.png`) against `find -printf '%f'` basenames
(`icon_QoS.png`) and reported 55 entries on each side that "only one instrument
had". **Two consecutive false alarms, both mine, neither the tools'**, before
the hash comparison in §6 settled it.

**It restored `/dev/mtdblock0` and called that a reset**, which produced the
contaminated measurement in §3 — a diff containing a field the run had never
written. The result would have read as "`flash set` rewrites the whole hardware
block", which is the opposite of §5's finding, and nothing in the output would
have looked wrong.

**And the guard suite for the tool passed the wrong cases first.** Three
refusal cases were "refused for the wrong reason" — all three were one line
(`$HOME` is `/root` under `sudo`, and every subcommand needs `sudo`), and a
suite that checked exit status alone would have recorded three passes. Then the
positive control began failing *nondeterministically*: `set -o pipefail` plus
`grep -q` means the writer takes `SIGPIPE` when grep exits early on a match, so
the pipeline reports 141 for a match found in the middle of a 2,317-line stream
and 0 for one near the end. **A control that fails at random is worse than no
control**, because the first thing anyone does with it is re-run it until it
passes.

That is instrument bugs 13 through 15 for this project. Thirteen of the fifteen
were caught by comparing two things that should have agreed; this one was caught
by a suite written to fail.
