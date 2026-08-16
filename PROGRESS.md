# Progress

| Week | Theme | Gate | Status |
|---|---|---|---|
| **W01** | Recon & unpacking | **G0 + G1** | ✅ **passed** — 2026-08-07 |
| **W02** | Hardware access: UART + SPI dump | **G2** | ✅ **passed** — 2026-08-16 |
| **W03** | Static reversing, upper half | — (DoD) | ✅ **DoD met** — 2026-08-10 |
| **W04** | CVE root-cause location | **G3** | ✅ **passed** — 2026-08-11 |
| **W04-2** | Catch-up: move the findings onto the build this unit runs | **G3.5** | ⚠️ **4 of 5** — 2026-08-16 |
| **W05 Day 0** | Pre-engagement: freeze the predictions before the first packet | **G3.75** | ⚠️ **2 of 5** — 2026-08-17 |
| W05 | Dynamic analysis, upper half | — | ▶ next, **after G3.5 #5 / G3.75** |
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

## W02 — 2026-08-14 / 16

**G2 passed.** Hardware arrived 2026-08-14, two days after the week the plan allotted
to it closed. G2 was worked out of order, the same way W03 was.

### G2 — hardware access

| # | Required | Result |
|---|---|---|
| 1 | a live bootlog, **or** a recorded fallback | ✅ captured at 38400 over a **measured** pin-out, and decoded a second time off the same wire by a logic analyser — the two transcripts byte-identical |
| 2 | SPI dump + hash verification, **or** the vendor-firmware main path | ✅ **two** full 4 MiB reads, 105 min each, **zero chunk retries**, staged through **different RAM addresses**. `sha256 a800059a…` both times, recomputed independently of the tool that wrote them; `cmp` finds zero differing bytes |
| 3 | dump vs vendor image compared, **or** the reason recorded | ✅ [`dump-vs-official.md`](notes/dump-vs-official.md) — and the comparison turned up a **five-year, three-step vendor remediation** that neither published image can show |
| 4 | PCB photograph, annotated | ✅ [`notes/img/`](notes/img/) — rendered from a committed JSON spec, MAC and serial painted out with coordinates recorded |

Achieved in the strong form of every clause, not the fallback form — and it took the
programmer being measured and set aside, not used.

> ⚠️ **What G2 does not establish.** Both full reads and the 2026-08-15 windows go
> through the boot loader's `FLR`. **A systematically wrong `FLR` would be invisible
> to all of them.** Two hashes agreeing proves the transport and the SPI read are
> stable; it does not prove the read is right. The independent checks that do not
> route through `FLR` are W01's burn-address predictions landing, and the SquashFS
> decompressing — and neither is the same thing as a second instrument. The JEDEC ID
> is still unread for the same reason.

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

### Day 4 — the programmer measured, and not used

**The CH341A is an un-modded 5 V board, and the measurement says so on its own.**

| pin | signal | measured | driven by |
|---|---|---|---|
| 8 | VCC | 3.3 V | the board's LDO |
| 3 / 7 | WP# / HOLD# | 3.3 V | pulled to the VCC rail |
| **1 / 6 / 5** | **CS# / CLK / DI** | **5 V** | **the CH341A itself** |
| **2** | **DO** | **5 V** | pulled to 5 V |

The reading is not "is there 5 V"; it is the *distribution*. The two pins the
board ties to VCC follow 3.3 V; **every pin the chip drives is at 5 V**, so the
chip runs at 5 V and so does everything it puts on the bus. **`VCC` reading
3.3 V is the trap itself** — it makes the board look safe. The worst pin is
`DO`: that is the flash's *output*, held 1.7 V above its own supply, which is
inside the datasheet's Absolute Maximum Ratings, the table whose heading says
permanent damage.

**A 3.3 V mod was attempted and the pins still read 5 V. The cause was not
isolated** — three candidates (the trace not actually cut, a lifted pin still
touching its pad, or the theory being incomplete because `DO`'s pull-up is
independent of the chip's supply), and **one measurement separates them: the
voltage on the CH341A's own pin 28.** That measurement was not taken, so the log
records "cause not isolated", not "the soldering failed". The board is now in a
**modified, unverified** state and must be re-measured before it is used.

**The decision was to read through the boot loader instead, and the reason is
ordering, not caution.** What is irreplaceable is the 4 MiB, not a $3
programmer: `FLR`+`DB` is already proven *on this unit*, a second mod attempt
might fail again, and even a perfect 3.3 V programmer still has to back-power
the whole board through the clip. The console path avoids both problems at once.
The programmer is not cancelled — it is **demoted to the second source and the
last-resort unbrick tool**.

**And the plan was checked rather than assumed: W05–W10 contain no flashing step
at all.** W05/W06 are entirely `curl` and telnet over the network. The only
mention of a programmer in the later plans is a CV line in W10 that already
carries two errors (`2MB`, `RTL8196C`).

> But "nothing writes to flash" is a false premise, and it is why the dump is
> urgent rather than optional: **W06's PoC writes to flash by definition** —
> the line W04 root-caused is `sprintf(buf, "flash set HW_WLAN0_WSC_PIN %s", …);
> system(buf)`, and `flash set` writes the config region. W07's fuzzing more so.
> The `H601` block at `0x006000` — this unit's MACs and radio calibration —
> exists nowhere else in the world; the vendor image does not contain it and a
> factory reset does not restore it. **Today's read is not a dump, it is the
> only backup.**

#### pin 3 = RX, finally measured

`uart-pinout.md` §5 had carried "pin 3 is inferred, not measured" since Day 2:
the other three pins were settled, it is a 4-pin header silkscreened `UART`, and
nothing else was left for it to be. **That is an argument, not a measurement.**
ESC streamed into pin 3 interrupted the boot, and `FLR`/`DB` sent into it were
executed. The pin accepts input and the board acts on it.

#### Instrument work — and three more bugs, numbers 7, 8 and 9

| | |
|---|---|
| [`tools/console-dump.py`](tools/console-dump.py) | `FLR`+`DB` driven over the console with a positive control, per-chunk validation, automatic re-read, sampled second-pass verification, and **no output file unless every chunk validated**. Serial on stdlib `termios` only |
| [`tools/flash-read.sh`](tools/flash-read.sh) | the CH341A path for when the programmer works: read-only by construction, JEDEC id checked against a written-down prediction, screening for the ways a clip lies |
| [`fwrecon flashdump`](tools/fwrecon/src/fwrecon/flashdump.py) | checks a raw image against expectations recorded **before it existed** — W01's derived burn addresses and the 2026-08-15 console windows. Per-unit secret regions are reported by digest and never printed. 11 tests |
| [`tools/test-console-dump.sh`](tools/test-console-dump.sh) · [`tools/test-flash-tools.sh`](tools/test-flash-tools.sh) | guard suites that need no hardware |

**7. The interrupt technique poisons its own next command.** Catching the boot
loader means *streaming* ESC, because the window is a second wide. The loader
eats one and **the rest stay queued in its input buffer**, so the first real
command comes back `Unknown command !`. It surfaced as `?` failing — while the
2026-08-15 session had used `?` to print the whole command set. Two sessions
disagreeing about one device is the instrument talking. It matters because **the
first command of an automated run is the positive control**, and a control that
silently does not run is worse than none.

**8. The parser rejected every line the device produced.** `DB` prints an ASCII
column; the regex had none, so the first run died on its own control with "no
data lines at all". The root cause is not the regex — it is that the format was
copied from the transcript quoted in `flash-layout.md`, which had trimmed the
column to fit the page. **The verbatim format was in the repository the whole
time**, in `RUNBOOK.md` §8.7.8, written the day the console came up. Nothing was
lost; the wrong document was read. Notes are analysis and their quotes are
edited; the runbook is the operational record and its transcripts are verbatim.

**9. The guard suite for that parser passed 10/10 against a format the device
does not emit** — because its fixtures were written from the same trimmed quote.
**A test that shares an assumption with the code it tests is not a second
source; it is the same source twice.** Same shape as W03's sink census and W04's
argument tracer, arriving this time through documentation rather than code. The
fixtures now come from a real capture, plus an adversarial case whose ASCII
column reads like more hex bytes.

That is nine instrument bugs recorded across the project, and **not one was
caught by the tool's own self-check.** Every one was caught by comparing two
things that should have agreed.

### Day 4 — the dump, and a five-year remediation timeline

**4,194,304 bytes off the device in 105 minutes, `sha256 a800059a…`, with zero
chunk retries.** No clip, no programmer, no risk to the board.

Four things stand behind it, and none is "the tool said it worked": a **positive
control** with an answer recorded by an unrelated session (`0b f0 00 04` at flash
`0x000000`); **per-chunk validation** that would have produced no file at all had
any chunk failed repeatedly; a **sampled second pass** re-reading 12 of 256
chunks over the wire, all identical; and **21 hard structural checks** against
expectations written down before the image existed — W01's burn addresses,
derived from the vendor containers three weeks before the hardware arrived, and
every offset the 2026-08-15 console session read.

**The strongest check is not in that list: the SquashFS at `0x180000`
decompresses.** 1.8 MiB of LZMA does not decompress by accident. 161 files,
20 directories, 88 symlinks.

Two things `flash-layout.md` had recorded as assumptions are now measurements:
the gaps at `0x053A24` and `0x151012` are each a single repeated value, and the
erased tail is the whole tail rather than two 64-byte windows.

#### The finding — and it needed the middle build to be visible

| | V2.1.2 (2015) | **this unit (2018)** | V3.4.0 (2020) |
|---|---|---|---|
| `/bin/skt`, the socket `system()` backdoor | **shipped, executable** | **deleted** | absent |
| `#skt&` in `rcS` | commented out | **still there, line 110** | removed |
| `onlime_r`, uid 0 | **present** | **present** | **removed** |
| password template | `/etc/passwd.org` | **byte-identical**, `sha256 e769c562…` | `/etc/passwd_orig` (renamed) |
| `root` hash `zhxPr1e7Npazg` | present | present | **present** |

**The vendor's response to Pierre Kim's July 2015 disclosure took three steps
across five years.** Five weeks after disclosure: comment out one line. **By
January 2018: delete the binary — and leave the uid 0 account untouched, byte for
byte, along with the dead `#skt&` line.** By October 2020: finally remove the
account. CVE-2015-9550 and 9551 were disclosed together; **two and a half years
later the vendor had fixed one of them.** `root` is unchanged in all three.

**That middle step is on no vendor download page.** Without this device the
timeline has a beginning and an end and nothing in between.

`/bin/boa` on this unit: 485,012 bytes, `sha256 19fe29d7…`, and its own string
says `boa: server built Jan 10 2018 at 14:57:54`. V2.1.2's is 522,556 and
V3.4.0's is 404,904. **The most-analysed binary in this repository is still not
this one** — but it is now extracted, hashed, and available to be read.

→ [`dump-vs-official.md`](notes/dump-vs-official.md) ·
[`reports/flashdump-unit-2018.json`](reports/flashdump-unit-2018.json) ·
[`reports/n150rt-unit-2018.md`](reports/n150rt-unit-2018.md)

> ⚠️ **A second independent instrument still has not read this chip.** The
> 2026-08-15 windows used the same `FLR`+`DB` path, so agreeing with them is
> cross-session repeatability, not corroboration by another route. A second full
> read is in flight to satisfy G2's literal wording — but it runs through the
> same boot loader, so it tests the transport and the SPI read, **not whether
> `FLR` is systematically wrong.** That column stays empty until the programmer
> works.

### Deliberately not done in W02

| Item | Why |
|---|---|
| Removing the antenna | The first physical action attempted on this board, at 450 °C, and it serves no G2 checkbox. Abandoned. The coax terminates into the RTL8188ER's output stage, and this unit is a single point of failure for G2 **and** G4 |
| Cutting the power-switch pigtail to hard-wire "on" | Proposed and rejected. The two conductors were never identified, and a working switch is an asset across a week of repeated power cycles, not an obstacle |
| **The JEDEC ID** | Still not read, and now blocked on the programmer rather than on time: the CH341A is a 5 V board and the mod did not take. It remains the only clean second source for the flash part. The full dump adds evidence without settling it — **the whole tail from `0x350000` is erased**, which a 2 MB part with address wrap could not produce, but a part that returns `FF` out of range still could |
| ~~**A full 4 MiB dump**~~ | **Taken 2026-08-16** — see Day 4 above. `0x350000` onwards being erased across the *whole* tail, rather than at two sampled windows, is a by-product |
| Decoding `COMPCS` | Located at `0x00C000` with its factory-default twin at `0x008000`. Reading it is W04/W07 work, not a W02 gate item |
| `LWL`/`LWR`/`SWL`/`SWR` census in `/bin/boa` | Needs a Ghidra mnemonic histogram that does not exist yet. Recorded as a hypothesis, not claimed as a result |
| Looking up the MAC's OUI | Moot: the flash's `H601` block confirmed the barcode is the MAC directly, without anyone having to handle the value against a public database |
| Running the device on a network | Nothing has been connected to any port. W05's problem |
| **`notes/hardware-chapter.md`** — the plan's Day 5 deliverable | It would be a fifth copy of material that already exists in [`hardware-inspection.md`](notes/hardware-inspection.md), [`uart-pinout.md`](notes/uart-pinout.md), [`uart-findings.md`](notes/uart-findings.md), [`flash-layout.md`](notes/flash-layout.md) and [`dump-vs-official.md`](notes/dump-vs-official.md) — and a summary written now goes stale the moment W05 touches the hardware again. **A writeup chapter is W08's job**, and it should be written from the notes rather than alongside them. Recorded as a decision so a later session finds one instead of an oversight |
| Extracting and decoding the config region | The plan's Day 5 asked for `strings` over a config partition it expected at `0x1F0000` on a 2 MB part. The real one is `COMPCS` at `0x00C000`, it is compressed, and it is now in hand — but decoding it is W04's deferred item, not a G2 box |

### Open, carried forward

1. ~~Which firmware build is on my unit~~ → **answered: a 2018-01-10 build, neither
   analysed image.** The Day 1 prediction from the board's date codes holds, and it
   failed in exactly the way that was written down alongside it — the line flashed an
   image eight months older than the board.
2. ~~UART pin assignment and baud rate~~ → **answered.** `VCC·TX·RX·GND`, 38400 8N1.
3. ~~Is 32 MiB fitted actually 32 MiB usable?~~ → **answered: yes.** `ramSize: 32M`.
4. **`/bin/boa` on this unit has never been read** — half answered. The dump has it
   out: 485,012 bytes, `sha256 19fe29d7…`, built 2018-01-10. **Extracted and hashed
   is not read**, and until it goes through Ghidra every `boa` finding in this
   repository still describes two binaries this device has never run.
11. **No second instrument has read this flash.** Everything so far — the 2026-08-15
    windows and both full reads — goes through the boot loader's `FLR`. A
    systematically wrong `FLR` would be invisible to all of it. Only a working 3.3 V
    programmer closes this, and the CH341A on the desk is modified and unverified.
12. **Why the 2018 build deleted `/bin/skt` and kept `onlime_r`.** The dates are
    known now; the reasoning is not. It is the difference between a vendor tracking
    a CVE list and a vendor reading the disclosure.
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

---

## W04-2 — 2026-08-16

**G3.5: four of five.** The fifth is hardware and is not done. Added after the
fact, because W02 found the unit runs a third build and every `boa` finding in
this repository described two images this device has never executed.

### G3.5 — every `boa` claim names the binary it was measured on

| # | Required | Result |
|---|---|---|
| 1 | `root_form[]` + sink census for every build, each carrying its input's SHA-256 | ✅ three builds, `tools/check-reports.py` green |
| 2 | `notes/auth-flow-2018.md`, key branch confirmed at instruction level | ✅ [`auth-flow-2018.md`](notes/auth-flow-2018.md) — the decompiler raised three warnings, so every branch was read from `BoaListing` output first |
| 3 | `COMPDS` decoded, `TELNET_ENABLED`/`SSH_ENABLED` answered with a second source | ✅ [`compcs-decode.md`](notes/compcs-decode.md) — `TELNET_ENABLED = 0`, confirmed by the code that reads it |
| 4 | G4's target chosen **from evidence** | ✅ `POST /boafrm/formSysCmd`, `sysCmd` → `system()`, and the gate does not run on that URI |
| 5 | Recovery path rehearsed — `FLW` write → read-back → erase | ❌ **not done.** Hardware. See *Deliberately not done* |

> ⚠️ **G3.5 is not passed, and W05 does not start until #5 is.** The gate's own
> wording is that W06 writes to flash by definition, and this unit's recovery
> path has never been executed. Not a formality: the `H601` block at `0x006000`
> is this unit's MACs and radio calibration, it exists nowhere else, and a
> factory reset does not restore it.

### The finding

**`formSysCmd` is in this unit's dispatch table, and in neither published
image.**

| | V2.1.2 (2015) | **this unit (2018)** | V3.4.0 (2020) |
|---|---|---|---|
| `grep -aoc formSysCmd` on the raw binary | **0** | **1** | **0** |
| in `root_form[]` | no | **entry `0x004838a8` → `0x0044ee2c`** | no |

Two instruments sharing no code. Absent → **present** → absent.

**This overturns G3 box 1.** W04 recorded the handler's absence from V2.1.2 as
"the vendor's fix", reasoning from dates. A fix does not reappear two and a half
years later; the evidence now supports the reading W04 explicitly dismissed — a
**build-time option**. The advisory for CVE-2019-19824 lists "N150RT through
3.4.0" as affected, and **both downloadable images happen to be ones without
it**, so anyone reproducing that CVE from published firmware would conclude "not
affected" and be wrong about this hardware.

The handler is what the CVE says it is:

```c
cmd = req_get_cstream_var(req, "sysCmd", "");
if (*cmd != '\0') {
  snprintf(buf, 100, "%s 2>&1 > %s", cmd, "/tmp/syscmd.log");
  system(buf);                       /* no filter, no escaping; boa runs as root */
}
```

> 🔴 **This endpoint has its own CVE and W04-2 did not know it while working.**
> **CVE-2024-51228** (NVD, 2024-11-27) names `/boafrm/formSysCmd` and lists
> **`TOTOLINK-CX-N150RT V2.1.6-B20171121.1002`** — byte-for-byte this unit's
> `/etc/version`. So the reachability result below is an **independent
> derivation from the binary of a claim disclosed in 2024**, not a discovery.
> `notes/prior-art.md` had no 2024 entries at all; that gap, and the change that
> follows from it, are recorded in
> [`prior-art.md`](notes/prior-art.md#2024--cve-2024-51228-and-the-gap-that-let-it-be-missed).
>
> **What survives as this project's own contribution is narrower and checkable:**
> NVD scores it `AV:A/AC:L/**PR:H**/UI:N/S:U/C:H/I:H/A:H` = 6.8 MEDIUM, while
> the original researcher writes "without credentials" and the instruction-level
> read below finds no authorisation on the path. Two of three sources agree
> against the vector; if they are right it is `PR:N` and 8.8 HIGH.
>
> And this remains new relative to the published images: **the handler is in
> neither of them**, which is why W04 read its absence as a fix.

**And the gate does not run on that URI.** This build's
`process_header_end` (`0x0040bb1c`) checks authorisation only when the URI
contains `.htm` or `.asp`:

```
0040be90  jalr t9 -> strstr            ; strstr(uri, ".htm")
0040beb8  beq v0,zero,0x0040c0a0       ; neither -> jump past send_r_unauthorized
0040c088  jalr t9 -> send_r_unauthorized
0040c0a0  jalr t9 -> translate_uri     ; normal processing resumes here
```

`/boafrm/formSysCmd` contains neither, and `handleForm` authorises nothing. **As
the code reads, that is unauthenticated OS command execution — where the
advisory itself only claims an authenticated attacker.** The advisory's own
qualifier, *"even if the GUI (`syscmd.htm`) is not available"*, is literally this
device: the `w6cg` web archive holds 143 files and `syscmd.htm` is not one.

> ⚠️ **Nothing has been sent to the device.** This is a static reading of a
> binary extracted from flash. No request has been served and no port has been
> touched in this project. One POST and a look at `/tmp/syscmd.log` settles it,
> and that is G4's job.

### The gate is a third answer, not 2015's and not 2020's

| | 2015 | **2018** | 2020 |
|---|---|---|---|
| what makes the gate run | `strstr(uri,"htm")` | **`.htm` or `.asp`** | `.htm` / `.asp` / **POST** |
| `/boafrm/` POST gated | no | **no** | yes |
| `GET /config.dat` gated | no | **no** | no |
| session model | `AUTHG_IP_ADDR` | **neither — a global at `0x004899d8`** | 5-slot table |

2015's outcome by 2020's mechanism. The gate decides with **13 unanchored
`strstr` calls** on one string; W04 counted three in the 2020 build and called
that the technique the vendor kept while fixing the symptom.

### The configuration region, decoded

`COMPCS` at `0x00C000` is LZSS over a TLV dump of the APMIB table. Confirmed
twice: inferred from the data, then read out of `libapmib.so`'s `Decode` at
`0x00012e98` — which also supplied an 8-bit payload checksum that is invisible in
the data and that both regions pass.

| | |
|---|---|
| `TELNET_ENABLED` | **0** — and `/bin/sysconf` starts `telnetd` iff that flag is 1 |
| `SSH_ENABLED` / `SSH_PORT` | 1 / 22 — **with no SSH daemon anywhere in the rootfs** |
| `SSH_PASSWORD` | **`xa.zioncom`** — factory default, identical in `COMPDS`; a model fact |
| `USER_NAME` / `USER_PASSWORD` | **`admin` / `admin`, plaintext** — CVE-2019-19823 located |
| entries differing from factory | **4 of 344** |

**W04 open #4 is closed, and the answer is the narrow one.** `root:123456` and
`onlime_r:12345` are **not** an entry point on this unit; they are the second
stage of a chain, because something must turn telnet on first. Two independent
sources agree: the decoded flag, and `FUN_00403400 → apmib_get(0xbbb)` guarding
`system("telnetd &")`.

**Prediction, recorded before any network test:** W05's `nmap -p 22,23` finds
both closed — 23 because the flag is 0, 22 because the flag is 1 and there is no
daemon to start.

### A build gate, and the control that caught it being broken

[`BoaGate.java`](ghidra/scripts/BoaGate.java) — R1 unbounded write from a request
parameter, R2 request parameter reaching `system()`/`popen()`, R3 request
parameter into a fixed-size global.

| | 2.1.2 | **unit-2018** | 3.4.0 |
|---|---|---|---|
| R1 | 96 | 92 | 54 |
| **R2** | **5** | **6** | **8** |
| R3 | 38 | 36 | 22 |
| total | 139 | 134 | 84 |
| **would pass CI** | **no** | **no** | **no** |

R1 and R3 nearly halve by 2020 and **R2 rises**. The vendor repaired the
authorisation hole that was published and the property that produces command
injection got worse. R2 finds `formSysCmd`/`sysCmd` in the 2018 build by a route
entirely independent of the dispatch-table work — and `form_formRoute`/`subnet`
in **all three** builds, which appears in none of W04's findings.

### The `lwl` census, and why "none" would have proved nothing

[`BoaMnemonics.java`](ghidra/scripts/BoaMnemonics.java) emits three numbers, not
one.

| | 2.1.2 | unit-2018 | 3.4.0 | 2018 busybox |
|---|---|---|---|---|
| `lwl`+`lwr`+`swl`+`swr` | 174 | **142** | 0 | 0 |
| **coprocessor 2/3 encodings** | **0** | **0** | **0** | **0** |
| bytes never decoded | 1.01% | 2.10% | 2.94% | 2.48% |

**The coprocessor column is the one that was worth writing the script for.**
Lexra's added instructions occupy opcode space that standard MIPS gives to
coprocessors 2 and 3, which Ghidra's stock MIPS module *will* decode into
something plausible — a silent failure mode sitting under every static result
since W03 that had never been named. There are none. The risk was real and did
not materialise, and testing it is the point.

On `lwl` itself the evidence is asymmetric and the note says so: **present is
evidence, absent is only compatibility.** 142 sites in the resident binary is not
yet proof the silicon implements them, because nothing shows one *executes*.
W02 open #6 wants `/proc/cpuinfo` and records that there is no shell to run it
from — the finding above supplies one.

### W01/W03/W04 claims that W04-2 overturned

| Said | Actually |
|---|---|
| **W04:** `formSysCmd`'s absence "reads as the vendor's fix" | It is present in the 2018 build. Absent → present → absent is a build option, not a fix |
| **W02:** "this vendor rebuilds userland at release and the timestamp tracks the build date" | `/etc/version` says `V2.1.6-B20171121.1002` while every binary is stamped 2018-01-10 — seven weeks apart |
| **W02:** the resident build is "on no download page" | `/etc/version` names it **V2.1.6**, and a firmware download page for that version appears in a search index. **The page itself returns 403 to every fetch tried**, so "listed" rests on the index entry and not on reading it — see open #1 for what that is and is not worth |
| **W03:** the uninitialised-stack credential compare is a V2.1.2 curiosity | The same shape is in the 2018 build at `sp+0x18`/`sp+0x38`, read and never written, with both instruments agreeing |
| **This session:** "the 2018 build dropped HTTP Basic auth" | A case-sensitive `grep`. All three parse `AUTHORIZATION`; what 2015 additionally carries is a hardcoded `Authorization: Basic YWRtaW46YWRtaW4=` — base64 `admin:admin` — twice |
| **This session:** "the 2018 build kept its symbol table" | No build here has a static symbol table. It keeps a 422-entry *dynamic* one while being `sstrip`'d |
| **This session:** the mirrored V2.1.6's kernel lengths are "1,024 bytes apart at each step, and a tampered file does not land on that line" | A 1 KiB padding grid. All four builds 2015–2020 are ≡ 2 (mod 1024), and exactly one grid point lies between the neighbours, so a correct kernel of that size lands there *by construction*. Three points looked like a trend; the fourth showed a grid |
| **This session:** the 40% prefix yields "section lengths only" | Two of the three sections are **byte-complete** — `w6cg` and `cr6c`, the latter's LZMA reaching `eof`. Only the rootfs is cut |

### Instrument work — bugs 10, 11 and 12, and the first one caught before it shipped

| | |
|---|---|
| [`BoaMnemonics.java`](ghidra/scripts/BoaMnemonics.java) | mnemonic histogram, coprocessor-2/3 census, undecoded-byte count. Ships the *reading* alongside the number because the number points the wrong way half the time |
| [`BoaGate.java`](ghidra/scripts/BoaGate.java) | three rules as a build gate, with a positive control that fails the run if a build known to be defective produces fewer than N findings |
| [`fwrecon compcs`](tools/fwrecon/src/fwrecon/compcs.py) | the config decoder W04 deferred. 18 tests, most of them about making it fail |
| [`fwrecon web`](tools/fwrecon/src/fwrecon/webbundle.py) | the `w6cg` bundle parser W01 left open. No checksum and no entry count exist in the format, so the check is structural: every stride is `64 + length`, and the walk either lands on the last byte or it does not. `exact` on all three builds; a test moves the length field to a plausible wrong offset and asserts it derails |
| [`tools/zipprefix.py`](tools/zipprefix.py) | truncated-archive recovery that refuses to write an unverified payload, and does not launder the exit code when `--allow-partial` permits the write |

**10. `BoaArgTrace` counted its unmeasured rows without naming them.** The report
said "3 rows are unmeasured" and gave no way to find them, so in practice the
warning was noise. It now emits the site, function and accessor for each.

**11. And it did not record the spec that defined its own scope.** W04 ran it
with one set of sinks and W04-2 with another; 304 against 1,508 reads as a
finding about the firmware until you notice the two answer different questions.
The spec is now in the report, and all three builds were re-run under one.

**12. Unifying that spec broke it, in this project's signature way.** Dropping
V3.4.0's `accessor:` override — needed because the build is `sstrip`'d — took its
tainted-site count from 49 to **0**, with `self_check: consistent`. The existing
check only fired when an override *was* passed and never matched; passing none at
all was invisible. Same 86 → 0 shape as W04, arriving through **how the tool was
called** rather than through what it does. There is now a
`no_accessor_identified` check: zero accessor matches anywhere in scope is
SUSPECT, because every empty result is then a false negative by construction.

**And one that did not ship, which is the difference.** `BoaGate` returned **0
findings on V2.1.2** — a build W03 and W04 read by hand and found defective in 34
handlers — twice, for two unrelated reasons: it matched sinks by *name* when
libc is reached through an `sstrip`'d PLT (the third appearance of that bug
here), and then its literal resolver tested only `isConstant()`, which never
holds for a MIPS lui/addiu string address, so no parameter name was ever read.
Either would have shipped as "this build is clean". **The positive control caught
both on the first run, before a number left the script.** `constAddr` is now
shared from `BoaArgTrace` rather than re-implemented — the same conclusion W04
reached about the PLT, arrived at from the other end.

That is twelve instrument bugs recorded. Eleven were caught by comparing two
things that should have agreed. The twelfth was caught by a check written to
fail.

### Deliberately not done in W04-2

| Item | Why |
|---|---|
| **G3.5 #5 — the `FLW` recovery drill** | Requires the device, a serial console and a person. Written up as a paste-able procedure in [`RUNBOOK.md`](RUNBOOK.md#89--g35-最後一格flw-回復路徑演練還沒做而且要你親手做) with each step's expected output. **Decided 2026-08-16: it runs as W05's first hardware session, not separately** — the console is already needed then, and one seating is fewer chances to mistype an `FLW`. **W05 still does not proceed past it** |
| **Day 6 in its entirety** — CH341A pin 28, CH347T verification, JEDEC ID, TFTP→`DB` | Same reason. The JEDEC ID and the second-instrument column in G2 stay empty |
| Fetching V2.1.1 / 2.1.3 / **2.1.6** | Softpedia returns 403 to scripted fetch and archive.org has only V2.1.2. `SOURCES.json` already recorded this as blocked. **V2.1.6 now matters much more than it did** — see open #1 |
| The `Encode` side of `libapmib` | Only `Decode` was needed. W06 writes to this region, so `mib_compress_write` and `save_cs_to_file` are located but unread |
| W01 open #6 — the 9-byte rootfs overrun | Needed a third container to compare against, and no third container could be fetched |
| The three unread binaries — `/bin/auth`, `MiniIGD`, `dnsspoof` | The plan's own first-to-cut item. Cut, and moved to W07 |
| Reporting anything to TWCERT/CC | Unchanged and reinforced. Everything here is static. It goes nowhere until W05/W06 demonstrates it on the hardware |

### A process failure worth more than most of the findings

**The commit titled "document sync" ran before the week's last two commits, and
nothing re-synced after them.** `PROGRESS.md` recorded open #1 as `answered:
no`; `LOG.md` still ended on *"if the two images match… if they do not…"* — the
same question, presented as open, three files away. **A reader going through the
repository in order hits that contradiction before anyone defending it does.**
`RUNBOOK.md` was worse off: it gained §8.8 and §8.9 in that commit and its own
§14 change log was never given a row for them, so the document's self-check
("§14 變更紀錄補了嗎?") was skipped in the very commit that made it necessary.

The cause is not forgetting. It is **treating "document sync" as a checkpoint
passed once a week rather than a state that has to hold after every commit** —
the exact failure the rule in `CLAUDE.md` exists to prevent, failing in the same
week that rule was rewritten. Recorded rather than quietly repaired, because the
repair is one commit and the habit is not.

### Open, carried forward

0. **Re-download the published V2.1.6. The success criterion is written down in
   advance: `CRC-32 == 0xd20c0622`**, read out of the archive's own local file
   header, and [`tools/zipprefix.py`](tools/zipprefix.py) fails non-zero until it
   matches. Obtained in a browser on 2026-08-16 and **the download is 40.3%
   complete** — 1,390,332 bytes of a declared 3,447,222, no central directory,
   `unzip` rejects it outright, which reads as *corrupt* and means *truncated*.
   Deflate being a stream, the prefix still decompresses, and **two of the three
   sections come out byte-complete** — `w6cg` 296,804/296,804 and `cr6c`
   986,114/986,114, the latter's inner LZMA reaching `eof` at 3,374,608 bytes.
   Only the rootfs is cut, so what is missing is `/etc/version` and `boa` and
   nothing else. Procedure in [`RUNBOOK.md` §8.8.4](RUNBOOK.md), provenance in
   [`firmware/SOURCES.json`](firmware/SOURCES.json).

1. ~~**Is the published V2.1.6 this build?**~~ → **answered: no.** The published
   image is `TOTOLINK-N150RT-V2.1.6-**B20160516**.1233.web`; this unit runs
   `V2.1.6-**B20171121**.1002`. **Same product version, two builds eighteen
   months apart**, and the unit's carries a `CX` the published name does not.
   W02's "the resident build is on no download page" survives with better
   precision: *the version* is published, *this build* is not.

   **The continuity argument first written here was wrong, and the correction is
   the more useful result.** It said the kernel lengths run 985,090 → **986,114**
   → 987,138, *exactly 1,024 bytes apart at each step*, and that a tampered file
   would not land on that line. Adding the fourth build empties it: 2015, 2016,
   2018 and 2020 are `962`, `963`, `964` and `1206` times 1,024, **plus 2 in
   every case**. The section is padded to a 1 KiB grid, so the spacing is the
   format, not a coincidence — and there is exactly one grid point between the
   2015 and 2018 values, so any correctly built kernel of that size lands on it
   by construction. `w6cg` (308,866 → **296,804** → 277,012) is unaligned and
   does fall between its neighbours, which is genuine but weak: an ordering test
   over a ~32 KiB window.

   What replaces it is better sourced. The archive's **DOS timestamp**
   (`2016-05-16 12:34:30`) is a separate header field from the filename's
   `B20160516` text, and inside the *compressed* kernel — where renaming a file
   cannot reach — sits `Linux version 2.6.30.9 (acer1@localhost.localdomain) …
   #1338 Thu May 12 21:05`, four days before packaging, with a cmdline
   (`console=ttyS0,38400`) that agrees with the bit time measured on this
   hardware in W02. **The ceiling is unchanged: TOTOLINK signs nothing**, so this
   raises the cost of a forgery from renaming a file to rebuilding a kernel, and
   no further. Full working in
   [`dump-vs-official.md` §2.1](notes/dump-vs-official.md).

   What is still established only weakly:

   | | |
   |---|---|
   | **measured** | `/etc/version` in this unit's rootfs reads `TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002` (41 bytes, `cat`) |
   | **measured** | four binaries in that same rootfs are stamped `2018-01-10` (W02) — so the label and the build date differ by seven weeks |
   | **measured** | the published V2.1.6 is `B20160516.1233`, from the zip's own local file header — and its DOS timestamp field, a second and independent header field, says `2016-05-16 12:34:30` |
   | **measured** | the published image's `w6cg` and `cr6c` sections are byte-complete in the 40% prefix; its kernel is Linux 2.6.30.9 built `Thu May 12` |
   | **not measured** | the published image's **rootfs**. No `/etc/version`, no `boa`, no `root_form[]`. That is the only thing needing the other 60% |
   | **not measured, and not to be quoted** | a search summary gives a 2.1.6 release date of 2017-05-08. The page could not be read, it disagrees with the build string in the file itself, and a search snippet is not a source |

   **What a complete download would settle:** whether the published B20160516's
   `boa` carries `formSysCmd` in its dispatch table. If it does, the handler was
   present in 2016 and in 2018 and gone by 2020, and the "build option" reading
   gets a third point. If it does not, the `CX` line diverges from the published
   one and that is a different and more interesting story.

   **Narrowed 2026-08-16: the UI half no longer needs the download.** `w6cg` is
   byte-complete in the prefix, and the 2016 bundle ships `syscmd.htm` carrying
   `<form action=/boafrm/formSysCmd …>` **byte-identical to 2015's**. What the
   other 60% is still needed for is exactly one thing: whether B20160516's `boa`
   has the route. See open #11.

2. **CVE-2024-51228 was missed for two weeks by a survey that had the build
   string in hand.** The literature review is now fixed
   ([`prior-art.md`](notes/prior-art.md#2024--cve-2024-51228-and-the-gap-that-let-it-be-missed)),
   but the open item is the CVSS discrepancy: NVD scores `PR:H`, the original
   researcher says "without credentials", and the binary agrees with the
   researcher. **Settling it is a G4 deliverable**, and it is worth nothing until
   then. If it holds, it is a reportable correction to a published record — and
   the *only* thing here that would be, since the vulnerability itself has been
   public since 2024-11-27.

3. **Are the other five products in CVE-2024-51228 the same binary?** A3002RU,
   N300RT (three builds) and N302RE are all `-CX-` builds of the same Realtek
   Boa. This project has one of the six. Nothing here claims anything about the
   other five, and the `CX` marker is unexplained.
4. **Why the binaries are stamped seven weeks after the version label.**
   `B20171121` against a uniform 2018-01-10 build date across four binaries.
5. **`system()` call sites go 158 → 194 → 129.** The resident build has more
   than either published image, in fewer functions. `formSysCmd` accounts for
   one or two; the other ~34 are unexplained.
6. **`form_formRoute` / `subnet` reaches `system()` in all three builds.** Found
   by `BoaGate`, in none of W04's findings, and still present in 2020. W07.
7. **The hardcoded `Authorization: Basic YWRtaW46YWRtaW4=` in V2.1.2**, twice.
   Which function holds it, and whether `boa` ever sends it, is unknown.
8. **Does `POST /boafrm/formSaveConfig` create a servable `/web/config.dat`?**
   This rootfs has no `/web` at all — the docroot is a ramfs whose 143 files do
   not include it. The gate is open; whether there is a file behind it is the
   other half of the CVE-2019-19822 chain.
9. **Who reads the global at `0x004899d8`**, which the 2018 gate sets to 1 or 2
   after a credential match. Per-request state plus one global is not a session.
10. Carried from W02, unchanged: **no second instrument has read this flash**, the
   JEDEC ID is unread, `LSP5526` is unidentified, and the SoC core question is
   open — though #4 above now supplies the means to run `/proc/cpuinfo`.
11. **The shipped UI and the route are anti-correlated, and only one build is
   explained.** `syscmd.htm` ships in 2015 and 2016 (byte-identical) while
   `formSysCmd` is absent from `root_form[]`; in 2018 the page is gone and the
   route is registered at `0x004838a8`
   ([`w6cg-web-ui.md`](notes/w6cg-web-ui.md), entry lists in
   [`webbundle-2.1.2.json`](reports/webbundle-2.1.2.json),
   [`webbundle-2.1.6-b20160516.json`](reports/webbundle-2.1.6-b20160516.json),
   [`webbundle-unit-2018.json`](reports/webbundle-unit-2018.json)).
   The 2015 state is explained — a
   partial fix answering Pierre Kim's disclosure, of a piece with `#skt&` and
   `onlime_r`. **The 2018 state is not: something put the route back three years
   later, and nothing here says what.** And the removal was not surgical —
   2015→2018 drops 27 bundle entries and adds 26, so `syscmd.htm` sits inside a
   rebuild rather than standing out as a deletion. Reading intent into it would
   be reading intent into a rebuild.

---

## W05 Day 0 — 2026-08-17

**G3.75: two of five.** The other three need the hardware and the console, and
run as W05's first session. Added after the fact, and for a reason that is not
"the plan said so": W05–W07 execute on the order of 130 tests, and the plan had
no mechanism for recording what each one predicted before it ran.

### G3.75 — nothing is sent to the device until the pre-engagement is done

| # | Required | Result |
|---|---|---|
| 1 | the `FLW` recovery path rehearsed | ❌ **not done.** This is G3.5 #5, cited rather than restated. It blocks everything below |
| 2 | isolation verified — two MACs on the segment, WAN on a fake upstream | ❌ needs the bench |
| 3 | IoC pre-check — live config against this unit's own factory baseline, plus the ports known botnets leave behind | ❌ needs the device. **Criterion written in advance: the difference stays at 4 of 344 entries** |
| 4 | the prediction ledger frozen before any request | ✅ [`study/test-ledger.md`](study/test-ledger.md) — 128 tests, 98 with a written refutation condition, hash `ba6810e8…` |
| 5 | the disclosure register written | ✅ [`docs/disclosure.md`](docs/disclosure.md) — eight candidates, and the rule that decides what is publishable |

> ⚠️ **G3.75 is not passed.** Box 3 in particular is not a formality: this model
> is named in public botnet tooling, and a unit that is already someone else's
> is an incident, not a test target. The criterion is written down now so that
> it cannot be adjusted after seeing the data.

### The problem this solves, which is a documentation problem

The red-team test corpus arrived as one document that was three documents: a
state table, a body of evidence-bearing analysis, and an attack execution
manual. It did not fit anywhere because those three belong in three places, and
the state table in particular **collided directly with `PROGRESS.md`** — 130
rows of checkbox that this file already claims to own.

That collision is not hypothetical. The process failure recorded one section
above — a "document sync" commit that ran before the week's last two commits and
was never re-run — is the same failure: **one piece of state, two owners.** A
hand-maintained 130-row matrix duplicated into `PROGRESS.md` and `README.md`
would have drifted inside a week.

So the split is by ownership, and it is now written into `CLAUDE.md`:

| file | owns | must not restate |
|---|---|---|
| `PROGRESS.md` | gates, weeks, carried-forward questions | an individual test's status |
| `study/test-ledger.md` | per-test prediction, refutation, result, evidence | a gate's verdict |
| `README.md` | the gate board and one line of numbers | either of the above |

### The instrument

[`tools/rtcase.py`](tools/rtcase.py) — the register is
[`study/test-cases.toml`](study/test-cases.toml), the ledger is generated from
it, and `rtcase check` is a CI gate. What it refuses:

| refusal | why it exists |
|---|---|
| a result whose case has **no pre-written refutation condition** | this is the whole point. A test with no written failure condition is read as a success afterwards, because by then the reader knows what they wanted to see |
| a `confirmed` or `partial` verdict **naming no artefact**, or naming a path that does not exist | the same rule `check-reports.py` applies to Ghidra output: a result that cannot name what it was measured on is not evidence |
| a prediction or refutation **edited after a result was recorded against it** | each result is stamped with a per-case hash of the wording it was judged against. Refining a refutation after seeing the answer is the one way to launder a miss into a hit that leaves no other trace |
| `confirmed` + `evidence_kind: static` **rendered as the dynamic tick** | it renders 🟥 instead. "Static ≠ dynamic" stops being a habit and becomes a column that cannot be left ambiguous |
| a register in which **nothing at all is frozen** | otherwise the freeze check hashes an empty list and passes. That is instrument bug 12's exact shape — a self-check that reports success when it has nothing to work on |

The register-wide freeze hash sits in the register itself, so changing a
prediction means changing the hash **in the same commit**, where `git diff`
shows it as two deliberate lines. This is not tamper-proofing — the author holds
the key. It is the difference between a change that is visible and one that is
not.

**And the gate is proved able to fail.** [`tools/test-rtcase.sh`](tools/test-rtcase.sh)
drives 22 cases: one control that must pass, and 21 that must be rejected *and
rejected for the stated reason* — checking the exit code alone would let a case
pass on an unrelated failure. `make ci` runs both, and so does CI. Writing that
suite caught a real defect in `rtcase record` on its first run: it assumed the
register lived inside the repository and crashed on a temporary copy.

### The nine items that were cut, and why

Cutting them is a decision, so each carries its reason in the ledger rather than
disappearing from it. Grouped:

| | |
|---|---|
| **post-exploitation tradecraft** — the 60-second rule, credential harvesting on a live host, lateral movement / DNS / WAN-management changes, anti-forensics, weaken-to-persist | None produces a checkable fact about this device. The credentials they would collect are **already decoded from flash** ([`compcs-decode.md`](notes/compcs-decode.md)); collecting them again on a live shell learns nothing and produces a copy that should not exist. Anti-forensics and weaken-to-persist exist to make a compromised device read as a badly configured one — the opposite of what a write-up is for |
| **downgrading the unit to reinstall the 2015 backdoor** | Irreversible, and its purpose is to put a known backdoor back into a device that no longer has it. The property it would demonstrate — no firmware signature, no anti-rollback — is already established statically, and reflashing does not make it truer |
| **social engineering an administrator into handing over the device** | The target is a person, not the device. There is no administrator in this lab, so in this environment the test is not falsifiable at all |
| **evil twin, and broadcast wireless DoS** | Both radiate into third-party equipment by construction. Targeted wireless work against this unit's own SSID and this lab's own client stays in, with the constraint written on the case |

**What was kept from the same chapters is the finding, not the method.** A
configuration value interpolated into a boot-time shell command is a
vulnerability class worth locating; how to make it survive a reboot unnoticed is
not.

### What building the register turned up, before any packet was sent

Two claims this repository leans on turn out to have no committed evidence.
Neither was found by looking for problems; both were found by trying to write
down what would refute them.

1. **The boot-script survey of configuration values reaching a shell exists in
   no committed artefact.** `rcS` was reviewed
   ([`skt-analysis.md`](notes/skt-analysis.md),
   [`credentials.md`](notes/credentials.md)), but the `/bin/*.sh` interpolation
   census that the persistence line depends on was never written up. Recorded as
   a **partial** result rather than a pass, which is what the ledger is for.
2. **"This unit has no `nc` and no `tftp`" is not established.** The 55-binary
   inventory in [`n150rt-unit-2018.json`](reports/n150rt-unit-2018.json) counts
   ELF files; busybox applets are symlinks and would not appear in it. The claim
   may well be true — it is now a *prediction*, with a refutation naming exactly
   what a hit would mean.
3. **`rcS` starts no daemon on this build, and every "this service is disabled"
   claim rested on it.** Two documents predicted UPnP in opposite directions —
   one from "`rcS` starts `miniigd`", the other from "`miniigd` is in the
   disabled-services list" — and **both were reading the wrong file**. `rcS`
   contains `mkdir /var/linuxigd` and the comment `##For miniigd`, and nothing
   else; `miniigd` appears in no script in the rootfs. **`/bin/sysconf` is the
   supervisor**, holding `telnetd`, `miniigd`, `mini_upnpd`, `snmpd.sh`, `wscd`,
   `dnsmasq`, `igmpproxy` and `lld2d`, gated on MIB flags — and W04-2 had
   already read that exact mechanism for one of them (`apmib_get(0xbbb)`
   guarding `system("telnetd &")`) without anyone generalising it.

   **`UPNP_ENABLED` is `1`**, in the live config and in the factory default. So
   the expectation flips to *UPnP is listening*, and CVE-2014-8361,
   CVE-2021-35392 and CVE-2021-35393 come back onto the W07 list. Corrected at
   source in [`attack-surface.md`](notes/attack-surface.md) and
   [`cve-status.md`](notes/cve-status.md).

   Three things worth separating here. **The instrument was not wrong** —
   `fwrecon` says "disabled only by commenting out their init line", which is
   what it measured; the word "disabled" was compressed out of that sentence by
   a note, and then by a note written today. **The register's own prediction was
   the one overturned**, not the plan's. And **the telnet conclusion survives on
   different evidence** — its flag was read *and* the code reading it was read,
   which is precisely the second source UPnP does not have.

### Corrections to the plan

**G3.75 did not exist in `plan/`.** It is added here rather than folded into
G3.5, because G3.5 was already reported as 4 of 5 and retroactively widening a
gate would make the earlier report wrong. G3.5 #5 is **not** moved into G3.75 —
it is cited from it. Moving it would have turned a failed box into a passed gate
by renaming, which is the specific thing the board exists to prevent.

The plan's W05 also assumed the test list would be written during W05. Freezing
it first is a change in ordering, and the reason is falsifiability: a prediction
recorded after the observation is not a prediction.

### Deliberately not done in W05 Day 0

| Item | Why |
|---|---|
| **G3.75 boxes 1–3** | Hardware, console, and a person. They run as W05's first session, in one seating, exactly as decided on 2026-08-16 for G3.5 #5 |
| **Refutation conditions for 21 of the scheduled cases** | Mostly Phase 6–8, which run in W07. Writing a refutation for a test whose preconditions are unknown produces a sentence, not a condition. `rtcase check` will not accept a result for any of them, and the ledger prints the list per phase, so the gap cannot go quiet |
| **`poc/`** | G4's deliverable, and it stays absent until something has been demonstrated. An empty directory with a plan in it reads as work done |
| **Reporting anything to TWCERT/CC** | Unchanged. Everything is still static. [`docs/disclosure.md`](docs/disclosure.md) now records what the queue would contain and what has to happen first |

### Open, carried forward

W04-2's list stands unchanged. Added by this session:

12. **The `/bin/*.sh` configuration-to-shell census has no committed artefact.**
    Either it is redone into a note, or the claims resting on it stop being
    made. Ledger `P0-8`, currently 🔶.
13. **The binary inventory measures ELF files, not available commands.** Every
    conclusion of the form "this unit does not have *X*" inherits that
    limitation, and at least three do.
14. **Who calls each of `sysconf`'s eight daemon strings, and on what flag.**
    Only `telnetd`'s gate has been read. Until the others are, "the flag is 1 so
    it runs" is one source — the same standard that made
    `TELNET_ENABLED = 0` reportable requires reading the branch, not just the
    value. `UPNP_ENABLED = 1` is the first case where this matters, because it
    reinstates three CVEs.
15. **`SNMP_RO_COMMUNITY` and `SNMP_RW_COMMUNITY` decode as all-zero strings and
    there is no `SNMP_ENABLED` among the recovered entries.** Either the flag is
    named something else, or the decoder is not recovering it. Both are worth
    knowing before W07 predicts anything about port 161.
