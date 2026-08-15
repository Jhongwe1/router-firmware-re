# Progress

| Week | Theme | Gate | Status |
|---|---|---|---|
| **W01** | Recon & unpacking | **G0 + G1** | ✅ **passed** — 2026-08-07 |
| W02 | Hardware access: UART + SPI dump | G2 | ▶ **in progress** — live bootlog + boot-loader console; SPI dump outstanding |
| **W03** | Static reversing, upper half | — (DoD) | ✅ **DoD met** — 2026-08-10 |
| **W04** | CVE root-cause location | **G3** | ✅ **passed** — 2026-08-11 |
| W05 | Dynamic analysis, upper half | — | ▶ next |
| W06 | PoC reproduction | G4 | |
| W07 | Systematic bug hunt | — | |
| W08 | Write-up draft | — | |
| W09 | Write-up publication | G5 | |
| W10 | Buffer / disclosure / close-out | — | |

---

## W01 — 2026-08-07

### G0 — toolchain green

Verified by `make verify` (Linux) and `tools\setup\setup-windows.ps1 verify`
(Windows). Every tool is checked by *running* it, not by testing for a file.

| Tool | Version | Where |
|---|---|---|
| binwalk | 3.1.0 (Rust) | cargo, pinned to `v3.1.0` |
| unblob | 26.6.4 | pipx |
| sasquatch | 4.5.1 (+ `sasquatch-v4be`) | ONEKEY prebuilt `.deb`, tag `sasquatch-v4.5.1-6` |
| squashfs-tools | 4.6.1 | apt |
| qemu-user-static | 8.2.2 (mips + mipsel) | apt |
| flashrom | 1.3.0 | apt |
| picocom | 3.1 | apt |
| Ghidra | 12.1.2 | pinned + SHA-256 verified |
| Temurin JDK | 21.0.12+8 | portable ZIP, SHA-256 verified, no admin rights needed |

### G1 — seven elements, answered from measurement

| # | Question | Answer |
|---|---|---|
| 1 | SoC | Realtek RTL8196-class — **firmware-consistent, not yet confirmed on silicon** (W02) |
| 2 | Architecture | MIPS32, MIPS-I ISA, o32 ABI |
| 3 | Endianness | **Big endian** |
| 4 | Load base / entry | `0x00400000` / `0x00404020` (2.1.2), `0x004034d0` (3.4.0) |
| 5 | Filesystem | SquashFS 4.0 — LZMA (2015), XZ (2020) |
| 6 | Web binary | `/bin/boa`, `Boa/0.94.14rc21`, running as root |
| 7 | Config storage | `libapmib.so` → `COMPCS` → `/web/config.dat` |

Full working: [`notes/anatomy-n150rt.md`](notes/anatomy-n150rt.md)

### Delivered beyond the plan

- **Two firmware versions instead of one** — V2.1.2 (2015-08-25) and V3.4.0
  (2020-10-30), straddling the December 2019 Realtek SDK disclosure. That turns
  a single-image teardown into a before/after comparison.
- **`fwrecon`** — a zero-runtime-dependency analysis tool: Realtek container
  parser, ELF reader that works on `sstrip`'d binaries, rootfs attack-surface
  inventory, JSON + Markdown reports, cross-version diff. 58 tests.
- **Ghidra headless triage** producing committed, diffable JSON rather than a
  GUI session that lives on one machine.
- **Reproducibility** — pinned `docker/Dockerfile` and GitHub Actions CI.

### Corrections to the original plan

| Plan said | Reality |
|---|---|
| CVE-2019-19822/23/24/25 are Pierre Kim's | They are **Błażej Adamczyk's** (sploit.tech, 2019-12). Pierre Kim's work is the separate 2015 series. |
| 2 MB SPI NOR flash | The flash map needs **≥ 3.57 MiB**, so ≥ 4 MB. To be settled physically in W02. |
| Backdoor account in `/etc/passwd` | **There is no `/etc/passwd`** in either image. The credential check is inside a binary. |
| `formSysCmd` is the RCE entry point | The string is **absent** from both `/bin/boa` binaries, though `sysCmdselect`, `sysCmdLog` and `/tmp/syscmd.log` are all present. Handler name resolution is now a W03 task. |

### Deliberately not done in W01

The plan listed these as W01 tasks. Each is deferred with a reason, so that a
later session finds a decision rather than an oversight.

| Item | Plan slot | Needed for | Why deferred |
|---|---|---|---|
| `usbipd-win` | Day 6 | **W02** — attaching the USB-TTL serial adapter to WSL | The adapter has not arrived. Installing it needs elevation, so it belongs in the same sitting as the rest of the hardware setup. **First thing W02 does.** |
| FirmAE | Day 1 | W05 — dynamic analysis | A 30–60 minute install that pulls its own toolchain — and probably the wrong tool here. `qemu-mips-static` plus a chroot into the extracted rootfs is already installed and **was verified working at W01 close-out** (see below). The plan's own risk table rates FirmAE "impact: low, does not affect this week". |
| PuTTY | Day 6 | W02 — serial console | Not needed. `picocom` is installed and does the same job from inside WSL, where the rest of the tooling lives. |

### Bonus: the W05 emulation risk is already partly retired

The plan flagged emulation as a W05 risk. A ten-minute check at W01 close-out
shows the cheap path works — the 2015 MIPS binaries run on an x86 host under
`qemu-mips-static` in a chroot:

```
$ sudo chroot $ROOTFS /qemu-mips-static /bin/busybox
BusyBox v1.13.4 (2015-08-11 17:26:34 CST) multi-call binary

$ sudo chroot $ROOTFS /qemu-mips-static /bin/boa --help
Usage: /bin/boa [-c serverroot] [-d] [-f configfile] [-r chroot] [-l debug_level]
```

`boa` prints its real usage text, including `-c serverroot` and `-f configfile`
— which is the entry point for standing the web server up under emulation.

Scope of the claim: this shows the binaries **load and start**. Serving an
actual request goes through `libapmib.so`, which reads flash partitions
(`/dev/mtd*`) that do not exist in a chroot. Bridging that is W05's problem.
What is settled is that a full-system emulator is not needed just to get the
target's code executing.

### Open, carried forward

1. Which firmware build is actually on my unit — only a flash dump decides (W02).
2. ~~Real flash part and size~~ → **answered in W02: Eon EN25QH32B, 32 Mbit = 4 MiB.**
   The `≥ 4 MB` derived here was right; the published 2 MB spec was not.
3. ~~Where `formSysCmd` is registered — read `handleForm`~~ → **answered in W03:
   it is registered nowhere.** W04 adds the likely reason: V2.1.2 post-dates the
   last build Pierre Kim reports as vulnerable to CVE-2015-9551.
4. ~~Whether Boa authenticates `.dat` requests — read `translate_uri`~~ →
   **answered in W03: no, and the reason is broader than `.dat`.**
5. ~~`FUN_00440eec` holds `cp /var/web/config.dat %s`; trace the `%s`~~ →
   **answered in W03: it is a `localtime()` filename. Not injectable.**
6. The archive.org V2.1.2 copy declares a rootfs length 9 bytes past EOF — find
   a second source to compare.

---

## W03 — 2026-08-10

No formal gate this week; the plan's Definition of Done was "dispatch table
found + ≥ 1 auth candidate". All five DoD items are met, and four of G3's eight
boxes (W04's gate) fell out with them.

### W03 DoD

| # | Required | Result |
|---|---|---|
| 1 | Dispatch table found, ≥ 10 handlers listed | ✅ **59** handlers (V2.1.2) and **49** (V3.4.0), both tables recovered with their addresses and their reader function |
| 2 | ≥ 1 authentication candidate function | ✅ `process_header_end` @ `0x0040be0c` — the *only* gate in the request path, read end to end |
| 3 | `formSysCmd` handler reversed | ✅ as a **negative result**: it is in neither dispatch table |
| 4 | `notes/sink-inventory.md` | ✅ 1,686 / 1,713 call sites across 21 sinks, both builds |
| 5 | ≥ 5 functions renamed in Ghidra | ✅ **185** named from table evidence (98 + 87), persisted in the project database, not typed into a GUI |

### The finding

**Boa's authorisation gate is keyed on the substring `htm` in the request URI.**

```
0040c23c  jalr t9                  -> strstr        ; strstr(uri, "htm")
0040c248  beq v0,zero,0x0040c3a0                    ; NULL -> skip the auth check
```

Everything whose path does not contain `htm` is served without an
authorisation check: `/config.dat`, `/ca.cer`, and all 59 `/boafrm/form*`
handlers. The advisory for CVE-2019-19822 records the symptom — "`.dat` files
are not restricted" — this is the cause, and it is much broader than `.dat`.

Confirmed at instruction level rather than from decompiler output, because the
decompiler raised three warnings on this function.

### Also found

- **`/bin/skt` fully decoded.** Listens on TCP **5555**; `hel,xasf` runs
  `iptables -I INPUT -p tcp --dport 80 -i eth1 -j ACCEPT`, `oki,xasf` removes
  it. A reachability backdoor that exposes the admin interface, shipped
  executable in the image released five weeks after the 2015 disclosure with
  only its `rcS` autostart commented out.
- **`formWsc` is the real command-execution surface**, not `formSysCmd`.
  `localPin` and `peerPin` reach `system()` with no filter and no length check;
  `targetAPSsid` is length-checked but interpolated inside shell double quotes
  unescaped. Present **identically in both builds**, five years apart.
- **A supervisor-level credential comparison against uninitialised stack** in
  V2.1.2's Basic-auth path (`sp+0x40`, `sp+0x60`, never written). Recorded as a
  candidate for dynamic work, not as a finding.
- **The 2020 build rewrote the authorisation code** — `AUTHG_IP_ADDR`,
  `countDownPageWizard.htm`, `notice_frame.htm` and `formLogin.htm` are all
  absent from it. Whether the replacement repeats the substring mistake is
  **not yet known** and is W04's first task.

Working: [`notes/dispatch-table.md`](notes/dispatch-table.md) ·
[`notes/auth-flow.md`](notes/auth-flow.md) ·
[`notes/formSysCmd-analysis.md`](notes/formSysCmd-analysis.md) ·
[`notes/sink-inventory.md`](notes/sink-inventory.md) ·
[`notes/skt-analysis.md`](notes/skt-analysis.md)

### W01 claims that W03 overturned

| W01 said | W03 found |
|---|---|
| `FUN_0044c610` is the strongest `formSysCmd` handler candidate | It is `sysCmdLog` in the ASP page-variable table — the log viewer, not a handler |
| `FUN_00440eec` (`cp /var/web/config.dat %s`) is the highest-value function found | It is `formSaveConfig`; the `%s` is a `localtime()` filename. Not injectable |
| ~40–50 request handlers, estimated from `submit-url` xrefs | Exactly 59 and 49, from the recovered arrays |
| The published rtl819x SDK declares `char name[80]` inline in the table element | These binaries use `char *name`, 8 bytes per entry — confirmed by the dispatcher's own `+2` stride |

### Two tooling bugs found and fixed

- **W01's `import.ps1` destroyed its own output.** `analyzeHeadless -import`
  names a program after the file, so both firmware versions imported as `boa`
  and `-overwrite` made the second import silently replace the first. The
  committed W01 reports were still correct — each was written during its own
  import — but the project could not be reopened to check them, and both files
  record `"program": "boa"` with nothing to say which binary they describe.
  Fixed: per-version project folders, and every Ghidra report now carries the
  analysed binary's SHA-256, which `tools/check-reports.py` enforces.
- **The first sink census was a false negative.** It reported 589 `strcpy` call
  sites in V2.1.2 and **1** in V3.4.0. The 2020 binary is `sstrip`'d and has a
  real PLT (`DT_MIPS_PLTGOT`), which Ghidra only partly recovers without section
  headers, so callers reached an unnamed stub. Fixed by constructing the
  16-byte MIPS PLT signature for each import's GOT slot and requiring exactly
  one match. Corrected figures agree across builds (587 vs 577). The report now
  carries a `self_check` that marks the file `SUSPECT` when an imported symbol
  appears to have no callers.

### Deliberately not done in W03

| Item | Plan slot | Why |
|---|---|---|
| Ghidra GUI screenshots (3 were asked for) | Day 4 | Replaced by [`BoaListing.java`](ghidra/scripts/BoaListing.java), which emits the same listing as diffable, greppable text with resolved call targets and string literals. A screenshot cannot be re-checked by a reader or regenerated after a Ghidra upgrade. |
| Committing the decompiled C corpus | — | Decompiler output is a derivative of the vendor binary; committing all of it redistributes the firmware by another route, against this project's stated position. `ghidra/decomp/` is gitignored; excerpts are quoted in the notes with commentary. |
| Tracing `execl` argument vectors in six handlers | Day 5 | Real work, not a quick check — `execl` needs no shell, so each one needs its argv built and read. Listed in `sink-inventory.md` §3 for W04. |
| Reading `libapmib.so` | — | On the path of every finding this week and completely unread. W04. |

---

## W04 — 2026-08-11

**G3 passed.** All five gate boxes met, and the two questions W03 left open
closed in the opposite direction to what W03 expected.

### G3 — point at the line in the binary

| # | Required | Result |
|---|---|---|
| 1 | CVE-2019-19824 / `formSysCmd`: the `system()` line and why it is reachable | ✅ as a **negative result** — the handler is in neither dispatch table. W04 dates it: V2.1.2 ships **after** the last build Pierre Kim reports as vulnerable, so this reads as the vendor's fix, not a build flag |
| 2 | CVE-2019-19822 / `config.dat`: why no auth check runs | ✅ **both builds**. 2015: the gate runs only for URIs containing `htm`. 2020: only for `.htm`, `.asp` or POST — `GET /config.dat` is outside both |
| 3 | Backdoor account (CVE-2015-9550/9551): where the credentials are | ✅ `/etc/passwd` → `/var/passwd`, written at boot by `/bin/sysconf` from `passwd.org`. **`onlime_r` / `12345`, uid 0**, hash byte-identical to Pierre Kim's published one |
| 4 | `auth-flow.md` complete | ✅ for both builds — [`auth-flow.md`](notes/auth-flow.md) + [`auth-flow-2020.md`](notes/auth-flow-2020.md) |
| 5 | ≥ 1 CVE-2025 root-caused | ✅ **twelve of the fourteen**, and they turn out to be **three** defects |

### The findings

**1. The 2025 CVE series names this exact model, and W03 recorded that it did
not.** CVE-2025-3987 through 3996, 4460/4461/4462 and 6299 all name
`TOTOLINK N150RT 3.4.0-B20190525`. W01, W03 and the project plan all filed them
as belonging to sibling models. Twelve of them collapse to three defects:

- `sprintf(buf[100], "flash set HW_WLAN0_WSC_PIN %s", localPin); system(buf)` —
  **one line**, which is CVE-2025-3987 (unfiltered) *and* CVE-2025-4462
  (unbounded), and which is **identical in the 2015 image**, ten years before
  either id was assigned;
- `targetAPSsid` interpolated inside shell double quotes, unescaped —
  CVE-2025-6299;
- the `submit-url` tail idiom — four ids, **34 handlers**.

**2. `submit-url` is one idiom repeated 34 times, with two defects in it.**
`strcpy(&lastUrl, submit_url)` copies an arbitrary POST parameter into a
**100-byte `.bss` buffer** — `lastUrl`, sized exactly by the symbol table and
immediately followed by `needReboot` and `run_init_script_flag`. Separately, when
the parameter is *absent*, the handler runs `strcpy(p, "/status.htm")` into the
accessor's default return value — the `""` literal in `.rodata`, which lives in
an `R E` segment. As the code reads, that is a one-request unauthenticated crash
of the web server on the 2015 build.
→ [`submit-url-overflow.md`](notes/submit-url-overflow.md)

**3. The 2020 build fixed W03's hole and kept the technique that caused it.**
Every POST now enters the gate, so the 59-handlers finding **is repaired** — that
should be said plainly. But the gate still decides by running `strstr` over the
URI, and its exemption list is unanchored: `strstr(uri, "login")` skips the
redirect, `translate_uri` allows a POST when `strstr(uri, "boafrm")` matches, and
`handleForm` finds its route with `strstr(uri, "/boafrm/")`. Three unanchored
substring tests on one string. And `GET /config.dat` is still outside the gate
entirely, in a build dated nine months after full disclosure.
→ [`auth-flow-2020.md`](notes/auth-flow-2020.md)

**4. Every MIB id in this project now has a name.** `libapmib.so` carries a
413-record table; `0xb6` is `USER_NAME`, `0xb7` is `USER_PASSWORD`. `config.dat`
is a `COMPCS`-magic compressed TLV dump of that table — CVE-2019-19823 located
rather than cited. The 2020 table has **no `AUTHG_*` entries at all**,
independently confirming from a second file what Boa's string table implied.
→ [`mib-and-config-dat.md`](notes/mib-and-config-dat.md)

**5. Two shipped private keys, found while looking for something else.**
`/etc/privateKey.key` (V3.4.0, 2048-bit RSA, certificate **expired 2014**, CN
`192.168.1.254` — a Realtek sample key) and `/etc/dropbear_rsa_host_key`
(V2.1.2). Identical on every unit of the model. No CVE against this device.
→ [`credentials.md`](notes/credentials.md)

### W01 and W03 claims that W04 overturned

| Said | Actually |
|---|---|
| **W01:** "There is no `/etc/passwd` in either image" | Both ship it, as a symlink to `/var/passwd`, written at boot by `/bin/sysconf`. A dangling symlink was read as an absent file |
| **W01:** "the credential check lives inside a binary" | True of the *web* login only, and reached from the false premise above. There are **two** credential systems on this device |
| **W01:** "Most binaries have no `PT_GNU_STACK` at all" | Backwards. 56 of 64 (2015) and 46 of 50 (2020) **have** it, every one marked `RWE`. Same conclusion, inverted evidence |
| **W03:** `process_header_end` sends a **401** | `send_r_unauthorized` @ `0x0040ecdc` sets the status field to 401 and sends a **301 to `/login.htm`**. V2.1.2 contains no `401 Unauthorized` string at all |
| **W03:** the 2025 CVEs "are assigned to sibling models" | Fourteen of them name this model and this firmware string |
| **W03:** `execl` argv "built from request parameters" | Every `execl` in both builds is `(path, "<script>.sh", NULL)`. No request data in any argv |
| **W03:** the 401-path `strcpy` is capped by `translate_uri` | It is not — the copy precedes that call. But the destination has 4,264 bytes of unnamed `.bss` before the next named global, so it is a non-finding for the opposite reason |
| **W03:** `formSaveConfig`'s buffers are 8 bytes apart | 100 bytes apart, for a ~47-character format. Ghidra's *inferred* frame was wrong; the storage it actually assigns is not |
| **W03:** `formSysCmd` absent because "this product was built without the handler" | Speculation. The dates make the vendor's fix the likelier reading, and name the experiment that settles it |

### Instrument work

Three new instruments — and **three bugs found in the newest one**, none by its
own self-check, all by comparing the two builds against each other.

| | |
|---|---|
| [`BoaXref.java`](ghidra/scripts/BoaXref.java) | callers, callees, strings, data-reference direction, bounded reverse reachability. Exists because W03 had to write "the selector returned nothing, which is a tooling result and not an answer" |
| [`BoaArgTrace.java`](ghidra/scripts/BoaArgTrace.java) | per-argument provenance from the decompiler's SSA form: literal, stack slot with frame offset, global, or **request parameter by name** |
| [`BoaPlt.java`](ghidra/scripts/BoaPlt.java) | the single place that knows how a call reaches libc in an `sstrip`'d binary. Extracted after the PLT bug W03 fixed in `BoaSinks` reappeared in a re-implementation |
| [`fwrecon mib`](tools/fwrecon/src/fwrecon/mibtable.py) | recovers the APMIB id/name table. 12 new tests, all of them about making it fail |

The `BoaArgTrace` failures, in order: two copies of one resolver that drifted
(1 tainted site out of 304, against three W03 had already found by hand); an
`accessor:` option compared against a lower-cased name, so it matched nothing
(86 tainted sites in 2015 versus **0** in 2020, `self_check: consistent`
throughout); and the `sstrip`'d-PLT bug again (`strcpy`: 151 sites in 2015, 0 in
2020). **A check that never fires never fails.** Written up in full at the end of
[`submit-url-overflow.md`](notes/submit-url-overflow.md).

### Deliberately not done in W04

| Item | Why |
|---|---|
| Decoding the `COMPCS` compressor and parsing a real `config.dat` | Needs a real `config.dat`, which needs W02's flash dump or a running server. "A compressed serialisation of the MIB table" is what the evidence supports; "the password is at offset N" is not |
| The five XSS CVEs (3994, 3995, 3996, 4460, 4461) | Reflected and stored XSS are decided by the page templates under `/web`, not by `boa`. Different corpus, and it belongs with the W07 hunt |
| Reading `/etc/scripts/*.sh` | The `execl` result redirects the question there rather than answering it. Real work, and W07's |
| `/bin/auth` (V3.4.0, 121 KB) | W01 named it the likely credential check. With `USER_NAME`/`USER_PASSWORD` located in the MIB and `/etc/passwd` explained, it is off the critical path. Still unread |
| Reporting the 2020 substring bypass to anybody | It is a static reading that has never been executed. It goes to TWCERT/CC if and only if W05/W06 demonstrates it, and nowhere else before that |

### Open, carried forward

1. Which firmware build is on my unit — only a flash dump decides (W02). W02 Day 1
   adds a **prediction** from the board's date codes: around 2018, i.e. neither image
   analysed here. See [`hardware-inspection.md`](notes/hardware-inspection.md#6-date-codes--a-prediction-written-before-the-dump).
2. ~~Real flash part and size~~ → **answered in W02: Eon EN25QH32B, 32 Mbit = 4 MiB.**
3. Fetch **V2.1.1-B20150708** and recover its `root_form[]`. One command settles
   whether `formSysCmd`'s absence from V2.1.2 is the vendor's fix or a build flag.
4. Do `TELNET_ENABLED` / `SSH_ENABLED` default on? That decides what
   `root` / `123456` is actually worth.
5. Four handlers — `formDdns`, `formNewSchedule`, `formSysLog`,
   `formWanTcpipSetup` — carry the `submit-url` idiom in 2015 and do not show it
   in 2020 while still existing. Rewritten, or a limit of the six-hop walk?
6. Who reads `needReboot` and `run_init_script_flag`, the two globals sitting
   immediately after `lastUrl`?
7. The archive.org V2.1.2 copy declares a rootfs length 9 bytes past EOF — still
   needs a second source to compare (carried from W01).

---

## W02 — 2026-08-14 / 15 (in progress)

Hardware arrived 2026-08-14, two days after the week the plan allotted to it closed.
G2 is unblocked and is being worked out of order, the same way W03 was.

**Day 1 was identification with the board unpowered.** On Day 2–3 the device was
powered on and a console brought up, so from that section onward the readings are
measurements of running hardware rather than of package markings.

### Day 1 — what the board actually is

| Ref | Part | Function |
|---|---|---|
| — | Realtek **RTL8196E** | SoC, MIPS big-endian |
| `U19` | Eon **EN25QH32B** — 32 Mbit / **4 MiB** SPI NOR | firmware storage |
| — | Winbond **W9825G6KH-6** — 256 Mbit / **32 MiB** SDRAM | system RAM |
| — | Realtek **RTL8188ER** — 1T1R 802.11n | Wi-Fi radio |
| — | LSC **LSP5526** — **not identified**; power, by inference only | regulator |

The UART header is **already populated** with a 4-pin 2.54 mm header, so W02 needs
no soldering anywhere — which removes the week's largest irreversible-damage risk
before it can be taken.

Full working, including the second source each reading is still waiting on:
[`notes/hardware-inspection.md`](notes/hardware-inspection.md)

### W01's flash derivation, confirmed by silicon

W01 never saw this chip. It read the burn addresses out of the vendor's own container
format, found the flash map extends to **3.57 MiB**, and concluded the published
2 MB specification was impossible — predicting **≥ 4 MB** three weeks before the
hardware existed on this desk.

The part is 32 Mbit. **The prediction holds.**

This is the first time in the project that a static derivation made a falsifiable
claim about the physical world, and the physical world agreed.

### Corrections to the plan's hardware spec table

| Plan said | The board says |
|---|---|
| SoC **RTL8196C** | **RTL8196E.** Commonly documented with a different core (RLX5281, against the C's Lexra RLX4181), which bears directly on W01's "MIPS-I" reading — falsifiable test in [`hardware-inspection.md`](notes/hardware-inspection.md#2-soc--rtl8196e-and-what-that-does-to-w01s-mips-i) §2 |
| **2 MB** SPI NOR | **4 MiB** — and W01 had already shown 2 MB impossible from the firmware alone |
| **16 MB** RAM | **32 MiB fitted.** *Fitted* is not *usable*; the kernel banner decides the second number, and the two are recorded separately |
| Wi-Fi **RTL8188RE** | **RTL8188ER** |

### One instrument confirmed, one instrument caught being vague

`flashrom` knows the part — `EN25QH32`, `4096` KiB, `PREW`. **This is not counted as
a second source for the size.** Its chip database is keyed on the part *name*, which
came from the same package ink as everything else; what it establishes is "*if* this
is an EN25QH32, it is 4096 KiB and `flashrom` can read it". The independent
measurement is the JEDEC ID the chip reports over SPI, at Day 4.

Separately: `flashrom --version` prints `flashrom unknown`, while `dpkg` reports
`1.3.0-2.1ubuntu2`. G0's stated rule is that every tool is verified **by running it**
— and this is the one row in the G0 table whose version number did not come from
running the tool. Functionally irrelevant (a Debian packaging artefact), but the
table should say so rather than imply a check that did not happen.

### G2 checkbox 4 met: the annotated PCB photograph

Photographs are in [`notes/img/`](notes/img/), and getting them there took two new
instruments — because the alternative was an image editor, which produces a file
nobody can check, diff, or regenerate. That is the same objection W03 raised against
Ghidra screenshots, and it gets the same answer.

| | |
|---|---|
| [`tools/redact-photo.py`](tools/redact-photo.py) | Paints out the unit's MAC barcode and serial QR. Solid fill, never blur — a blur is a reversible transform on a known font. Drops EXIF, which carries GPS and a device id that survive every *visual* redaction. Verifies its own work by reading the written file back off disk |
| [`tools/annotate-photo.py`](tools/annotate-photo.py) | Renders the callouts from [`notes/img/pcb-top-annotations.json`](notes/img/pcb-top-annotations.json), so a moved box appears in `git diff` as a changed number. The legend is drawn in a strip *below* the frame, never over it, so no annotation can hide the evidence it describes |

**Both were wrong on the first run, and neither noticed.**

1. **The guard suite reported 5/5 passing while every invocation was dying on
   `import PIL`.** On a login shell, bare `python3` resolved to an unrelated
   project's venv that happened to carry Pillow; under `bash script.sh` it did not.
   Five tests that assert "this must fail" all passed — for the wrong reason. What
   caught it was the one line asserting that a *valid* call must still succeed.
   Fixed twice over: the interpreter is now named explicitly, and each guard asserts
   on **its own** failure message rather than on the exit status.
2. **The control case then failed, and it was the checker that was wrong, not the
   redaction.** The post-condition demanded every pixel in the painted box be exactly
   zero on read-back — a condition JPEG can never satisfy, because a hard black
   rectangle re-encodes with ringing against its own edges. Rewritten as two parts:
   a loose bound over the whole box to catch a box that landed somewhere wrong, and
   an exact test on the box inset by two MCUs, which is the part that actually
   guarantees the pixels were replaced.
3. **The annotation tool silently produced an unreadable legend** — two columns
   overprinting each other, labels running off the frame — and reported `ok`. It now
   picks the column count and type size that fit, and **errors** if no combination
   does. A figure that overprints itself still looks finished, which is the worst
   thing a tool can hand you.

The tool can prove a region is solid. **It cannot prove the box landed in the right
place — that check is human, and it was done by eye on all three files.**

This is the fourth, fifth and sixth instrument bug the project has recorded, and the
first three are in [W03](#two-tooling-bugs-found-and-fixed) and
[W04](#instrument-work). The pattern holds: none was caught by the tool's own
self-check.

### Day 2–3 — the console, and a firmware nobody had

**The device has been powered on.** Everything below is measured on running
hardware, which is the first time that sentence has been true in this project.

#### The console

`VCC · TX · RX · GND` from pin 1 (the end with the triangle on the silkscreen),
**38400 8N1**. Each pin carries two sources — resistance to ground with the board
dead, voltage with it live — except RX, which is inferred by elimination and has
never been driven. **The baud was measured, not tried:** narrowest pulse 26 µs,
and a second pulse at exactly 52 µs proves 26 is one bit and not two. The nearest
wrong answer, 19200, has a 52.08 µs bit time.
→ [`uart-pinout.md`](notes/uart-pinout.md)

**There is no shell on the console.** Sending `\r` gets perfect echo and nothing
else — that is the tty line discipline, which echoes whether or not a process is
listening. No getty, no prompt, and no BusyBox `Please press Enter…` anywhere in
the boot log.

**The boot loader console is interactive.** ESC streamed across power-on lands on
`<RealTek>`, whose command set (from `?`, not `HELP`) includes
**`FLR <dst_ram> <src_flash> <len>`** and `DB`. That is **a complete flash read
path requiring no SOIC-8 clip** — which the plan listed only as a Day 6 bonus for
the case where everything else had already worked.

#### The unit runs a third firmware

| | BusyBox built | `boa` built |
|---|---|---|
| V2.1.2 | 2015-08-11 | — |
| **this unit** | **2018-01-10** | **2018-01-10 14:57:54** |
| V3.4.0 | 2020-10-30 | — |

Four binaries on the unit — BusyBox, `wscd`, MiniIGD and **`boa`** — all stamp
2018-01-10. The obvious objection was tested first: V3.4.0's BusyBox is stamped
the same day as its release and V2.1.2's 14 days before its own, so **this vendor
rebuilds userland at release and the timestamp tracks the build date.**

**W01 open #1 is answered, and the answer is "neither".**

**This has to be said plainly: `/bin/boa` on this unit is not a binary this
project has read.** Every W03/W04 finding about `boa` — the `strstr(uri, "htm")`
gate, the 59-entry `root_form[]`, `lastUrl[100]`, the `submit-url` idiom, the 2020
rewrite's three unanchored `strstr` calls — is a claim about V2.1.2 and V3.4.0.
Those claims are not wrong; the repository has always named its images. **They do
not cover this device**, and anything demonstrated against this hardware in
W05/W06 tests a third binary. That makes the flash dump worth more than a
checkbox.
→ [`uart-findings.md`](notes/uart-findings.md)

#### RTL8196E: a third source, and the dissenter disqualified

The first 64 bytes of flash disassemble to a read of the chip-ID register at
`0xB8000000` compared against the constant **`0x8196E000`**. **The `RTL8196E` in
the banner is not a compile-time string — it is the silicon identifying itself.**

Against that, the Linux Ethernet driver prints `chip name: 8196C`. It loses, and
not on a majority vote: **two lines earlier the same driver announces it is
probing an RTL8186** — a generation older than either candidate. That driver
prints its own code lineage, not the part it runs on.

`ramSize: 32M` also confirms the SDRAM marking, and closes the *fitted vs usable*
distinction this project deliberately kept open: here they agree.

#### The flash map: three predictions, three hits

W01 parsed the two vendor containers, read `burnAddr` out of each 16-byte section
header, and produced a map. Read back off the device:

| W01 predicted | Found |
|---|---|
| `w6cg` at `0x010000` | ✅ |
| `cr6c` at `0x060000` | ✅ |
| rootfs at `0x180000` | ✅ SquashFS `hsqs` |

**The container format W01 reverse engineered from two files, with no
documentation, correctly describes where a third, unseen build sits in flash.**
The image ends at **3.29 MiB** — over the published 2 MB again.

This unit uses the **2015 layout** (it has `w6cg`; the 2020 image dropped it), with
a **third, distinct filesystem**: 567 inodes against 582 and 827, LZMA like 2015
rather than XZ like 2020, and smaller than either.

**And a W01 hedge comes off.** W01 flagged V3.4.0's SquashFS `mkfs_time` as
"*possibly* a vendor build-script bug writing a size into this field". This unit's
reads `0x80AD1C00`; byte-reversed that is 1,879,424 against a `bytes_used` of
1,876,033 — the same relationship, on a build made by someone else on another day.
**Three builds carry it.**
→ [`flash-layout.md`](notes/flash-layout.md)

#### The config region located — this unblocks W04

Not at the tail of the part (`0x3F0000` and `0x350000` both read `FF` — my guess,
wrong, recorded). The Realtek SDK puts it **below `0x010000`**:

| Offset | | |
|---|---|---|
| `0x006000` | `H601` | HW setting — MACs and radio calibration |
| `0x008000` | `COMPDS` | factory defaults, 7,481 bytes |
| **`0x00C000`** | **`COMPCS`** | **live configuration, 7,478 bytes — this is `config.dat`** |

W04's first *Deliberately not done* was "decoding the `COMPCS` compressor and
parsing a real `config.dat` — needs a real `config.dat`, which needs W02's flash
dump." **It is at `0x00C000`.** Better still, `COMPDS` and `COMPCS` are the same
table as-shipped and as-running, 3 bytes apart in length and differing by a single
byte in their first 58 — a differential pair, which is a far better way into an
undocumented format than one blob cold.

**And the photograph redaction is retroactively confirmed.** `hardware-inspection.md`
called the bottom-side barcode "almost certainly this unit's MAC". The `H601`
block opens with MAC addresses and the first is byte-for-byte that string. The
redaction was applied while it was still an inference — **which is the right order:
redact on the shape of the thing, confirm afterwards.**

#### Instrument notes

- **`FLR` takes hex for address and length; `DB` takes a hex address and a
  *decimal* length.** Two radices, adjacent commands, in a tool whose only job is
  moving bytes. Nothing warns you; you get a well-formed dump of the wrong size.
- **`FLR` prompts `(Y)es , (N)o ?` and consumes the next line as the answer.** A
  script that sends the next command instead of `Y` gets `Abort!` and a spurious
  `Unknown command !` — and, if you were not reading carefully, a `DB` of stale RAM.
- The flash read validated itself: a control dump of RAM taken **before** the first
  `FLR` turned out to be byte-identical to the `cr6c` payload later read from
  flash. Two unrelated paths, same bytes.

### Deliberately not done in W02

| Item | Why |
|---|---|
| Removing the antenna | The first physical action attempted on this board, at 450 °C, and it serves no G2 checkbox. Abandoned. The coax terminates into the RTL8188ER's output stage, and this unit is a single point of failure for G2 **and** G4 |
| Cutting the power-switch pigtail to hard-wire "on" | Proposed and rejected. The two conductors were never identified, and a working switch is an asset across a week of repeated power cycles, not an obstacle |
| **The JEDEC ID** | The one Day 4 measurement that did not happen, and the only clean second source for the flash part. `0x350000` reading `FF` is supporting evidence — a 2 MB part with address wrap would alias it into the kernel — but it is not the same thing |
| **A full 4 MiB dump** | Everything read so far is 64-byte windows at chosen offsets. The full image is what W05/W06 needs and the only way to get this unit's 2018 `boa` into Ghidra. Two routes exist: CH341A, or ~80 minutes of `FLR`+`DB` over the console |
| Decoding `COMPCS` | Located at `0x00C000` with its factory-default twin at `0x008000`. Reading it is W04/W07 work, not a W02 gate item |
| `LWL`/`LWR`/`SWL`/`SWR` census in `/bin/boa` | Needs a Ghidra mnemonic histogram that does not exist yet. Recorded as a hypothesis, not claimed as a result |
| Looking up the MAC's OUI | Moot: the flash's `H601` block confirmed the barcode is the MAC directly, without anyone having to handle the value against a public database |
| Running the device on a network | Nothing has been connected to any port. W05's problem |

### Open, carried forward

1. ~~Which firmware build is on my unit~~ → **answered: a 2018-01-10 build, neither
   analysed image.** The Day 1 prediction from the board's date codes holds, and it
   failed in exactly the way that was written down alongside it — the line flashed an
   image eight months older than the board.
2. ~~UART pin assignment and baud rate~~ → **answered.** `VCC·TX·RX·GND`, 38400 8N1.
3. ~~Is 32 MiB fitted actually 32 MiB usable?~~ → **answered: yes.** `ramSize: 32M`.
4. **`/bin/boa` on this unit has never been read.** The most-analysed binary in this
   repository is one this device has never run. Only the full dump fixes that, and it
   is the highest-value item left in W02.
5. What `LSP5526` is. Still one multimeter reading, still not taken.
6. The SoC *core* — RLX4181 vs RLX5281. `/proc/cpuinfo` would settle it and there is
   no shell to run it from; the flash dump's kernel would also carry the string.
7. Whether `chipName: UNKNOWN` in the boot log refers to this flash part — and if so,
   whether a stale flash-ID table in the 2014 boot ROM is where the published "2 MB"
   figure came from.
8. What the `COMPCS` blob at `0x00C000` decodes to, against its factory twin at
   `0x008000`.
9. The `LWL`/`LWR`/`SWL`/`SWR` census, and with it whether the Realtek SDK toolchain
   is still pinned to the Lexra subset in the 2020 build.
10. `MiniIGD` (UPnP) and `wan_disconnect: StartDnsSpoof` both run on this unit and
    neither has been looked at anywhere in this project.
