# Progress

| Week | Theme | Gate | Status |
|---|---|---|---|
| **W01** | Recon & unpacking | **G0 + G1** | ✅ **passed** — 2026-08-07 |
| **W02** | Hardware access: UART + SPI dump | **G2** | ✅ **passed** — 2026-08-16 |
| **W03** | Static reversing, upper half | — (DoD) | ✅ **DoD met** — 2026-08-10 |
| **W04** | CVE root-cause location | **G3** | ✅ **passed** — 2026-08-11 |
| **W04-2** | Catch-up: move the findings onto the build this unit runs | **G3.5** | ✅ **passed** — 2026-08-17 (the fifth box closed in W05) |
| **W05 Day 0** | Pre-engagement: freeze the predictions before the first packet | **G3.75** | ✅ **passed** — 2026-08-17 |
| **W05** | Dynamic analysis, upper half | — (DoD) | ⚠️ **4 of 5 DoD, 22 / 31 register rows** — 2026-08-17 |
| **W06** | PoC reproduction | **G4** | ⚠️ **4 of 5 — L2 clause not met, 18 / 18 register rows** — 2026-08-17 |
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
| 4 | the prediction ledger frozen before any request | ✅ [`test-ledger.md`](test-ledger.md) — 130 tests, 102 with a written refutation condition, freeze `69c342dc…`, schedule `d68ace7d…` |
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
| `test-ledger.md` | per-test prediction, refutation, result, evidence | a gate's verdict |
| `README.md` | the gate board and one line of numbers | either of the above |
| `plan/W0N_*.md` | **the day-by-day ordering, the commands, the timeboxes, the DoD, the week's technical argument** | any claim about current status — its preconditions have been stale twice |

The last row is the one worth stating explicitly, because "the register owns the
work list" reads at a glance as "the week plan is superseded". It is not.
**Nothing else in the repository records how a week actually runs** — the
ordering, the stop-losses, the exact invocations. The register says which tests
must close; the plan says in what order and with which command. Both are read at
the start of a week, and `CLAUDE.md` now says so in those words.

### The instrument

[`tools/rtcase.py`](tools/rtcase.py) — the register is
[`test-cases.toml`](test-cases.toml), the ledger is generated from
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
15. ~~**`SNMP_RO_COMMUNITY` and `SNMP_RW_COMMUNITY` decode as all-zero strings and
    there is no `SNMP_ENABLED` among the recovered entries.**~~ → **answered in
    W05: not a decoder fault.** The vendor's own `/bin/flash all`, executed over
    the same image, prints both community strings as `""`, and across all 2,317
    lines it emits there is no `SNMP_ENABLED` under any spelling.

---

## W05 — 2026-08-17

**No formal gate. The DoD is five items and three of them are met.** The half of
the week that needs no hardware is done and it produced more than the plan
expected; the half that needs a network segment has not started, and **25 of the
31 registered tests are still `⬜`.** That is the honest shape of the day and the
register prints it on demand.

**G3.5 is closed.** Its fifth box — the `FLW` recovery drill — was executed on
the bench and passed against the criterion frozen for it. That was the gate
blocking everything, and it is the reason the rest of this section is allowed to
exist.

### G3.5 #5 / `P0-3` — the recovery path, executed

| | |
|---|---|
| write | `FLW 3F0000 80530000 8` — `de ad be ef de ad be ef` |
| read back, **to a different RAM address** | byte-identical |
| erase | writing `FF`s over it returns the region to `ff ff ff ff ff ff ff ff` |

Verbatim transcript in [`RUNBOOK.md` §8.9.1](RUNBOOK.md); the session's record
cards are in [`BENCH-LOG.md`](BENCH-LOG.md).
**Both halves of the frozen refutation are satisfied, so `P0-3` passes** — and
the interesting part is what the drill turned up that its own criterion did not
ask about, in *Open, carried forward* #17.

### G3.75 — passed

| # | Required | Result |
|---|---|---|
| 1 | the `FLW` recovery path rehearsed | ✅ above |
| 2 | isolation verified — two MACs, WAN on a fake upstream | ✅ **exactly two MACs**, eight packets each, no DNS and nothing outbound. The control is that the capture recorded 16 packets at all: an earlier 45-second capture recorded **zero**, which proves nothing until the link is known to deliver — and it was not, until ARP replies came back |
| 3 | IoC pre-check | ✅ **both halves.** The live configuration differs from this unit's own factory baseline in **4 of 343** entries, which is the number written down in advance, and every port the register named — 2323, 5555, 9034, 19412, 31412, 48101, 60001, 7547 — is closed |
| 4 | the prediction ledger frozen | ✅ W05 Day 0 |
| 5 | the disclosure register written | ✅ W05 Day 0 |

### W05 DoD — 5 of 5

| # | Required | Result |
|---|---|---|
| 1 | a prediction scorecard committed **before** testing, then scored | ✅ frozen in W05 Day 0; **27 of 27 scored** — 16 confirmed, 5 refuted, 6 partial |
| 2 | one dynamic path standing up | ✅ **two**: the device on an isolated segment, and the emulator |
| 3 | [`notes/emulation-2018.md`](notes/emulation-2018.md) — what was faked and whether it distorts | ✅ |
| 4 | [`notes/oracle-design.md`](notes/oracle-design.md), ≥ 1 oracle rehearsed under emulation | ✅ **four of five** |
| 5 | W06's target with its three conditions | ✅ **all three.** (b) closed in the afternoon: an unauthenticated `POST /boafrm/formSysCmd` carrying only `submit-url` answers `302 -> status.htm` in 10 ms. **Nothing was injected, and the handler's own guard proves nothing ran** — W04-2's decompilation shows `if (*cmd != '\0')` around the `system()` call, and `sysCmd` was absent |

**The register reads 27, not 31.** Four cases scheduled W05 were ones this
week's own plan forbids running — the three command injections it defers to
W06 in the same paragraph that calls them the week's highest risk, and the reset
button, which is destructive. Both decisions were already recorded below under
*Deliberately not done*; the register still said W05, so `make todo WEEK=W05`
could never reach zero without either breaking the plan or editing a field.
They now carry `rescheduled_from`, a reason and a date, and `[schedule].sha256`
makes a week that moves show up in the diff — see *Instrument work*.

**The morning's reading of item 5 was wrong and is corrected here.** It said
*"reaching it means POSTing to it, and that is the proof-of-concept the plan
reserves for W06."* Those are two different acts. A POST carrying no `sysCmd`
demonstrates reachability and executes nothing; the proof of concept is a POST
carrying a command. Conflating them would have left the DoD open for a reason
that does not exist. Recorded in *Corrections to the plan*.

**The scorecard is the week's stated deliverable and it is worth reading as a
number: of 22 scored, four predictions were refuted and four were partial.** The
refuted ones are the return on the exercise — `P2-2`'s substring bypass does not
work, `P2-7`'s session mechanism is not what the disassembly implied, `P2-4`'s
`check_host` is not in the authorisation path, and `P1-3`'s document root is not
the shipped bundle. Each was refuted **by the condition its own author wrote down
before the first packet**, which is the only reason any of them counts.

### The findings

**1. The emulation obstacle was a file, and the file was already on disk.**
`libapmib` reaches the flash with `lseek()`+`read()`, not `ioctl()` — so a copy of
W02's dump placed at `/dev/mtdblock0` is enough, and the risk the plan rated
highest for this week did not materialise. The `strace` also shows the vendor's
binary seeking to `0x6000` and `0x8000` **by itself**, which is a second source
for the flash map that goes through no tool written here.

**2. Two instruments written for this project are now confirmed by the vendor's
own binaries.**

| | |
|---|---|
| `fwrecon web` | `flash extr /web` — the device's own extractor — writes **143 files** and every one's SHA-256 matches [`webbundle-unit-2018.json`](reports/webbundle-unit-2018.json). The format has no checksum and no entry count, so until today the parser's only check was structural |
| `fwrecon compcs` | `flash all` emits 2,317 MIB lines; 316 names appear in both. **249 identical**, 66 explained by exactly four rendering rules *by a script that exits non-zero if any difference is left over*, **1 unexplained** |

Not one of the 66 is a disagreement about a **value**. Two of the four rules are
`fwrecon` being wrong: an all-zero `char[]` renders as hex rather than as the
empty string it is, and a 4-byte integer renders as a dotted quad
(`QOS_MANUAL_DOWNLINK_SPEED` = `0.1.134.160`, which is 100000).

**3. `boa` creates `/web/config.dat` at start-up — W04-2 open #8 is answered, and
the premise in the question was wrong.** The open item asked whether
`POST /boafrm/formSaveConfig` produces a servable file. Nothing has to POST
anything:

```
401 lseek(3,49152,SEEK_SET) = 49152        <- 0xC000, COMPCS
401 read(3,0x490018,7490) = 7490
401 open("/web/config.dat",O_RDWR|O_CREAT|O_TRUNC) = 3
```

The file is in the document root from the moment the web server is up, and the
gate does not run on `.dat` in any of the three builds. **That is the other half
of CVE-2019-19822 on this hardware**, and it is one step shorter than the chain
this repository had assumed.

**4. `flash set` writes flash for hardware MIBs and not for configuration MIBs —
and the line W04 root-caused sets a hardware MIB.** Each row is a separate run
from a reset environment:

| set | bytes changed in 4 MiB | `0x006493` |
|---|---|---|
| `HW_WLAN0_WSC_PIN` `99956042` → `87654321` | **8** — seven digits + the checksum | Δ `+8`, predicted `+8` |
| `HW_WLAN0_REG_DOMAIN` `1` → `5` | **2** — `0x60a5` + the checksum | Δ `−4`, predicted `−4` |
| `DEVICE_NAME` → `TESTNAME` | **0**, and a fresh process reads the new value | unchanged |

**The byte at flash `0x006493` is an 8-bit checksum over the `H601` region.** It
moves by the exact negation of the sum of the changed payload bytes, for two
fields `0x3EE` apart. W04-2 found an 8-bit checksum inside `libapmib.so`'s
`Decode` for the `COMPxx` regions; this locates the hardware block's, at an
address.

**5. The W06 PoC writes into the one region that exists nowhere else.**
`HW_WLAN0_WSC_PIN` is at `0x648a`, inside the `H601` block at `0x006000` — this
unit's MAC addresses and radio calibration, which the vendor image does not
contain and a factory reset does not restore. On the device that write is a
read-modify-erase-program cycle over the containing erase block, not a 3-byte
poke. **Nobody had written this down.** It does not change the plan; it changes
which target is preferred, and the target W04-2 chose from evidence
(`formSysCmd`) turns out to be the only candidate that **writes no flash at all**.

**6. `boa` does not serve a request under emulation, and the reason is worth more
than the failure.** It dies with `SIGBUS`/`BUS_ADRALN` at `libapmib.so+0x27dc`,
deterministically, before `bind()`. The instruction is

```
0x27dc:  a7 d7 00 00      sh  s7,0(s8)      <- store halfword to an odd address
```

Opcode `0x29`: **standard MIPS I**. The encoding was computed by hand
(`0x29<<26 | base<<21 | rt<<16` = `0xa7d70000`) and matched against the raw bytes,
so qemu's disassembler is not the only witness — and the match also confirms the
library's load base rather than assuming it. The W05 plan named a competing
explanation, that qemu had hit a Lexra instruction and failed loudly where Ghidra
fails silently. **It is not that**, and W04-2's coprocessor-2/3 census had already
found zero such encodings. What is left is that `libapmib` performs an unaligned
16-bit store and the device's kernel fixes it up; `qemu-mips-static` has no guest
kernel to do so. No CPU model avoids it.

**7. Four of five oracles rehearsed, and the plan's first-choice payload would
have wasted the afternoon.** BusyBox 1.13.4 here is built with 48 applets and
**`id` is not one of them**. `…;id > /var/web/x.txt;#` creates the file and leaves
it empty, which is indistinguishable from a filtered parameter. `cat /etc/version`
is the better payload: its output both proves execution and names the build.

**And the handler's own redirection beats the payload's.** `formSysCmd` appends
`2>&1 > /tmp/syscmd.log`, and in `sh` the last stdout redirection wins:

| as `system()` receives it | where the output went |
|---|---|
| `ls -l / > /var/web/k.txt 2>&1 > /tmp/syscmd.log` | **`/tmp/syscmd.log`** — the docroot file is created and empty |
| `ls -l / > /var/web/k.txt;# 2>&1 > /tmp/syscmd.log` | the docroot file ✅ |

**Two independent ways to get an empty file**, and the first draft of the oracle
note could not tell them apart. Nine of ten command separators reach the second
command; `||` does not, because `flash set` returns 0 — **its silence is the one
channel that reports the sink's exit status.**

**8. `/bin/startup.sh` turns telnet on when the configuration is corrupt.** In the
branch taken when `flash test-dsconf` *and* `flash test-csconf` both fail:

```sh
$LOADDEFSW                       # flash default-sw
...
flash set TELNET_ENABLED 1
```

`TELNET_ENABLED` is `0` on this unit and `telnetd` is compiled into its BusyBox,
with `login` and `chpasswd` beside it and `root:123456` still in `passwd.org`. So
a unit whose configuration region is damaged comes back up with the flag set.
**This is a static reading — `flash test-csconf`'s definition of invalid has not
been read** — and it is recorded as a lead, not a result.

### W01/W02/W05-Day-0 claims that W05 overturned

| Said | Actually |
|---|---|
| **W05 Day 0:** "`rcS` starts no daemon on this build" | Its last three lines are `# start web server` / `boa` / `#skt&`. **It starts `boa` directly.** The accurate statement is that `rcS` starts `boa` and delegates every *other* service to `/bin/sysconf` through `init.sh gw all` — and `init.sh` is one line, `sysconf init $*` |
| **plan/W05 Day 5:** "`rcS` does `cp -rf /web/* /var/web/`, so `/var` is writable" | This build does `cd /web ; flash extr /web` — the docroot is unpacked **out of flash by the `flash` binary**, not copied from the rootfs. `/var` is still writable, but the reason given was the 2015 build's |
| **plan/W05 §5 risk 1:** "`apmib` may use `ioctl` rather than `read`, so a plain file will not work" | `lseek`+`read`. Rated the week's top risk; did not occur |
| **plan/W05 Day 5:** the oracle payload is `id` | Not compiled into this BusyBox |
| **`RUNBOOK.md` §8.9:** `FLW` answers `Flash Write Successed!` | A single `.` The real reply names the SPI chip and the mapped address, which is how `0xbd000000` got recorded |
| **`RUNBOOK.md` §8.9:** `EB` taking several bytes "has never been tested" | Tested; it does |
| **W05 Day 0 open #15:** the SNMP community strings may be a decoder failure | They are genuinely empty, and the vendor's binary agrees |
| **W05 Day 0 open #13:** "no `nc`, no `tftp`" is only a prediction | **Confirmed by two instruments**: the rootfs has no ELF for `nc`/`netcat`/`tftp`/`curl`/`telnet`, and BusyBox's own applet table does not carry them — with `uptime` as the control proving `applet not found` means what it says. `/bin/wget` does exist, as the prediction also said |
| **W04-2 `auth-flow-2018.md`:** the gate is decided by 13 **unanchored** `strstr` calls, so an exemption string smuggled anywhere in the URI should be enough | Twelve shapes tried against a page the gate really protects. **None bypassed it.** Unanchored in the disassembly is not unanchored in effect: the comparison is anchored or length-limited somewhere the read did not capture. `P2-2`'s own refutation named this outcome and named its consequence — X-3 does not stand |
| **W04-2:** the 2018 session model is "a global at `0x004899d8`, set to 1 or 2 after a credential match" | The global grants nothing. After a successful authentication, a credential-less request **from the same address** is rejected, no cookie is ever set, and `formLogin` sets no state. Authorisation is stateless HTTP Basic per request. The observation does not say the global is unread — it says it is not authorisation state |
| **`P1-10`'s own working:** UPnP would show up on 1900 | It does, but the services are on **52869** and **52881**, which no prediction named. The reasoning chain (`UPNP_ENABLED = 1` → `sysconf` starts it → UPnP is listening) was right and stopped one step short of asking *where* |
| **This session:** a 45-second capture with zero packets shows an isolated segment | It shows nothing until the link is known to deliver, and at that moment it was not — the interface had received **0 bytes** since it came up. The kernel's own RX counter said so, independently of `tcpdump`. What made the silence evidence was ARP replies afterwards |

### Instrument work

| | |
|---|---|
| [`tools/qemu-env.sh`](tools/qemu-env.sh) | builds the chroot from this unit's rootfs and its own flash image, with a **positive control of three known values** and a `diff` that checks the `H601` checksum still balances. Every set-up step is copied from `rcS` or from `sysconf`'s own string table, and the file says which |
| [`tools/test-qemu-env.sh`](tools/test-qemu-env.sh) | 14 cases. Five need neither root nor the dump and run in CI |
| [`tools/bench-probe.py`](tools/bench-probe.py) | the network round. Refuses a POST to `/boafrm/*` without `submit-url`, refuses shell metacharacters, re-runs its control every 10–20 requests, and takes the endpoint list from the committed Ghidra report rather than from a hardcoded copy |
| [`tools/test-bench-probe.sh`](tools/test-bench-probe.sh) | 8 cases, including a real HTTP server as the control |
| `rtcase` `emulated` | a third evidence grade. **🟪, and it never renders as ✅.** `test-rtcase.sh` goes 22 → 27 cases, three of them about exactly that |

### Instrument bugs 13 through 17

**13. Restoring `/dev/mtdblock0` is not a reset.** `flash`, `boa` and `sysconf`
cache the MIB table in **System V shared memory**, which belongs to the host
kernel and outlives every guest process. A run that changed only
`HW_WLAN0_REG_DOMAIN` produced a diff containing seven bytes of the WPS PIN field
— the previous test's. **Found by a measurement going wrong, not by reading the
`strace` that had shown the `ipc()` calls all along.** Without it the conclusion
would have been "`flash set` rewrites the whole hardware block", which is the
opposite of finding 4, and nothing in the output would have looked wrong.

**14. `$HOME` is `/root` under `sudo`, and the whole tool needs `sudo`.** Three
guard cases reported "refused for the wrong reason" and all three were this one
line. **A suite checking exit status alone would have recorded three passes.**

**15. `set -o pipefail` plus `grep -q` makes a control fail at random.** `grep -q`
exits the moment it matches; the writer then takes `SIGPIPE`; `pipefail` reports
141 for a successful match. So a control line in the middle of a 2,317-line
stream failed and one near the end passed, in the same run. **A control that
fails nondeterministically is worse than no control**, because the first thing
anyone does with it is re-run it until it passes.

**16. A dict literal overwritten by its own spread.** `bench-probe` recorded the
after-the-run control as `{"probe": "control-after", **control(...)}` — and
`control()` sets `"probe"` itself, so the after-run control was indistinguishable
from the before-run one in the transcript. Caught by the guard suite asserting
the record exists.

**17. The ledger's legend indexed its right column by the length of its left
one.** Adding a seventh result marker would have dropped it silently — and the
marker it would have dropped is the one that exists to stop a reader confusing
*executed* with *executed on the device*.

Seventeen recorded. **Fifteen were caught by comparing two things that should
have agreed; two were caught by a check written to fail.**

### Deliberately not done in W05

| Item | Why |
|---|---|
| **`P3-1`, `P3-2`, `P3-3` — the command injections** | **This is the plan's own rule, not a shortfall.** W05 §5 lists "starting W06's PoC" as the week's highest-probability risk and says: *this week does no formal PoC; Day 5 validates oracles and does not fire at the real target.* All three targets are located, all three have a rehearsed observation channel, and the third — `formSysCmd`, CVE-2024-51228 — is G4's chosen target. Firing them is W06's work and it happens after `docs/disclosure.md` says what state each item is in |
| **`P9-9` — the reset button** | **Destructive, and it would delete evidence.** Reset overwrites `COMPCS` with `COMPDS`, and the 4-of-343 difference measured today is this unit's own state. The prediction (reset restores the configuration but not `H601`) can be tested at the end of W07, when that difference is no longer needed |
| **`P1-4` and `P3-13` — the POST sweeps** | A POST to a form handler **runs** it, and a handler whose parameters are all absent still writes whatever its accessors defaulted to. `bench-probe` refuses to POST without `--allow-post` for that reason. Doing it needs a 64 KiB snapshot either side, which is 3 minutes of console time this session did not have left |
| **`P1-12`, `P9-1`, `P9-3`** | All three need a power cycle with the console attached. `P9-1` (`init=/bin/sh` from the boot loader) is the valuable one: it would answer W02 open #6 (`/proc/cpuinfo`, the Lexra core question) and enumerate what is actually running, in one seating |
| **FirmAE** (the plan's Day 3, 3-hour cap) | **Cut, and the reason is not the timebox.** FirmAE emulates a vendor `.web` image, and this unit's build is on no download page — so a successful FirmAE run would describe V2.1.2 or V3.4.0, which W03 and W04 already cover statically. The qemu path uses *this unit's own rootfs and its own flash*, which is strictly better for every question W05 asks. The 30–60 minute install buys a data point about a different binary |
| **Invoking any UPnP SOAP action** | 52869 is CVE-2014-8361's port and that CVE is in CISA KEV with public weaponised code. Fetching the description document a UPnP device publishes by design is reconnaissance; calling an action on it is not, and it is not scheduled for this week |
| **Making `boa` serve a request** | Blocked on an alignment trap the host kernel would fix and `qemu-user` cannot (finding 6). The route around it is full-system emulation, which is a day's work for a channel §5 of the oracle note reaches without it |
| **The `Encode` side of `libapmib`** | Still unread. What W05 adds is *what a write looks like from outside* — the three bytes and the checksum — which is what W06 needs. `mib_compress_write` and `save_cs_to_file` remain located and unread |
| **Deciding the `L2TP_SERVER_IP_ADDR` type disagreement** | Every byte of the field is zero, so the data cannot arbitrate. Recorded, not resolved |
| **Reporting anything to TWCERT/CC** | Unchanged. **Nothing has been sent to the device.** Every result above is either static or emulated |

### Phase 3 — the device on a segment, and eleven predictions scored

**G3.75 closes.** Isolation verified, the IoC pre-check complete in both halves.
The register goes from 6 to **22 of 31**, and the nine that remain are listed
under *Deliberately not done* with a reason each.

**9. An unauthenticated `GET /config.dat` returns bytes identical to the flash.**

```
GET /config.dat  ->  200, 7,490 bytes, body begins "COMPCS"

served sha256 : e09cbf8428aa15944ed75939e79820c5...
flash@0xC000  : e09cbf8428aa15944ed75939e79820c5...
identical     : True
```

Two things, and the second is the larger one.

CVE-2019-19822 is demonstrated end to end on this hardware, and `fwrecon compcs`
decodes that blob to `USER_PASSWORD` in plaintext — which then **authenticates**
(finding 12). Every link is separately pointable: HTTP response → flash offset
→ field → login.

And **W02 open #11 is answered for that region.** It said no second instrument
had read this flash: every byte came through the boot loader's `FLR`, so a
systematically wrong `FLR` would be invisible. Here `boa` read the same region
through **the kernel's MTD driver** and sent it over **Ethernet**, while W02 read
it through the **boot loader's SPI routine** over **UART**. Two paths sharing no
code, the same 7,490 bytes. That is corroboration rather than repeatability, and
it is the column that has been empty since 2026-08-16. **Scope: `0xC000`–`0xD142`,
not the whole chip.**

**10. Two open TCP ports that no prediction mentioned.**

```
80/tcp     open      52869/tcp  open      52881/tcp  open
Not shown: 65532 closed tcp ports (reset)
```

Everything the prediction *named* was right — 80 open, 22 and 23 and 5555 closed,
9034 closed, and every IoC port in the register closed. **It named too little.**
Four controls (before, after the TCP sweep, after the UDP sweep, at the end) all
returned 200, so the `closed` results are the device's and not a web server that
had been knocked over.

**11. The UPnP daemon reports another project's name.** SSDP answers on 1900:

```
Server: miniupnpd/1.4 UPnP/1.4
Location: http://10.1.1.1:52869/picsdesc.xml
```

But the rootfs contains **`/bin/miniigd` and no `mini_upnpd` binary at all**, and
`miniigd`'s own string table carries `Server: miniupnpd/1.4 UPnP/1.4` beside
`MiniIGD %s (%s).` and `/etc/miniigd.conf`. **The banner is not the codebase.**

`P1-10` had asked for exactly this distinction, in advance, because it decides
which CVEs apply: `miniigd` is Realtek's (CVE-2014-8361, in CISA KEV), while
`miniupnpd` is an unrelated project. **Reading the banner alone gives the wrong
answer.**

- **52869 = `miniigd`.** `GET /picsdesc.xml` → 200 / 2,933 bytes, exposing
  `WANIPConnection:1` and `WANCommonInterfaceConfig:1` — and a
  `urn:schemas-dummy-com:service:Dummy:1` left in the shipped description. `UDN`
  and `serialNumber` are template constants (`uuid:1234…5678`, `00000000`),
  identical on every unit.
- **52881 = `wscd`.** `GET /simplecfg.xml` → 200, and the rootfs's
  `/etc/simplecfgservice.xml` declares `GetDeviceInfo` and **`PutMessage`** —
  the surface CVE-2021-35392/35393 concern. `P6-3`'s refutation was "if `wscd`
  is not running, drop this and P7-4"; **it is running**, so both stay (W07).

> ⚠️ Reconnaissance only — `GET` on documents a UPnP device publishes by design.
> No SOAP action was invoked. 52869 is a KEV port with public weaponised code,
> and exploiting it belongs to W07 and to `docs/disclosure.md`, not to a
> reconnaissance sweep.

**12. The gate is exactly what the instruction-level read said, and the
substring bypass it implied does not work.**

Of the 76 `.htm` pages the bundle ships, **7 are served unauthenticated** and 69
redirect to `login.htm`. The two redirect targets are the gate's fingerprint: an
absent `.htm` goes to `login.htm` (the gate ran), an absent anything-else goes to
`home.htm` (it did not).

`P2-2` predicted that 13 unanchored `strstr` calls would let an exemption string
be smuggled into the path. **Twelve shapes, none worked** — `?login=1`,
`/login.htm/../password.htm`, `/loginpassword.htm`, `/password.htmlogin.htm` and
the rest all get the ordinary treatment. Its refutation named the conclusion in
advance: the exemption comparison is anchored or length-limited, and **X-3 does
not stand.**

`P2-3` is confirmed, and *demonstrated* rather than argued:

```
/config.dat       200, 7,490 B        <- outside the gate
/config.dat.htm   302 -> login.htm    <- adding the extension pushes it IN
/password.HTM     302 -> home.htm     <- case mismatch: gate skipped, file absent
```

Thirteen normalisation variants, none of which made a gated page return content.

**13. There is no session on this build at all.** `admin`/`admin`, decoded from
this unit's own flash, authenticates over HTTP Basic — and then:

| | |
|---|---|
| `.100` with credentials | 200 |
| `.101` with no credentials | 302 |
| `.100` with no credentials, right after a success | **302** |
| `formLogin` POST | sets no cookie |
| any response | **no `Set-Cookie`, ever** |

So authorisation is **stateless Basic on every request** — not 2015's
`AUTHG_IP_ADDR` binding, not 2020's five-slot table, and **not the global at
`0x004899d8`**, which grants nothing. `P2-7`'s refutation fired verbatim and
**open #9's question has to be rephrased**: whatever that global is for, it is
not machine-wide authorisation state.

Two consequences worth separating. **Brute force is unlimited** — fifty
consecutive wrong passwords were all rejected and the fifty-first correct one
still worked, so there is no counter and no lockout. And **"no session" is not
"no CSRF"**: a browser that has cached the Basic credentials re-sends them
automatically, so the cross-site surface survives by a different mechanism.

**14. The identifier visible on the network is not the one the CVE is indexed
under.**

| where | string |
|---|---|
| `/etc/version` | `TOTOLINK-`**`CX`**`-N150RT-V2.1.6-B20171121.1002` |
| `/bin/boa`, `/bin/sysconf` | `TOTOLINK-N150RT-V2.1.6-B20171121.1002` |
| **served unauthenticated on `status.htm`** | `TOTOLINK-N150RT-V2.1.6-B20171121.1002` |
| CVE-2024-51228 names | `TOTOLINK-`**`CX`**`-N150RT V2.1.6-B20171121.1002` |

**`CX` appears in exactly one file in the whole rootfs — `/etc/version` — and the
web interface does not use it.** So the only identifier a remote observer can
obtain does not match the CVE's affected-product string. This repository already
records that CVE-2024-51228 went unfound here for two weeks; **this is the
mechanism, and it generalises to anyone fingerprinting the model.**

`status.htm` also discloses, without credentials: three MAC addresses, the LAN
address and mask, wireless SSID, channel and encryption mode, connected-client
information, DHCP and WAN state. Whether that page's exposure is already covered
by published prior art has **not** been checked, and no novelty is claimed for it
here.

**15. At least one `/boafrm/` route is missing from the recovered dispatch
table.** On GET, all 57 `root_form[]` names return the same 302/131 B as a name
that does not exist — `translate_uri` redirects before `handleForm` is reached,
so GET cannot census them. But of the three extra names `fwrecon`'s string
extraction found and Ghidra's table does not contain:

| | |
|---|---|
| `formOpdRedirect` | **302 / 535 B → `/opmode1.htm`** |
| `formWanRedirect` | **302 / 536 B** |
| `formWlanRedirect2` | 302 / 131 B — indistinguishable from an absent name |

Two of the three behave unlike anything else on the device, so they are handled.
`ghidra-formtable-unit-2018.json` records the `/boafrm/` prefix string being
referenced by **eight** functions, not just `handleForm`, which is where the
second path should be looked for. **Every count resting on 57 / 59 / 49 since W03
needs re-checking** — that is `P1-5`'s refutation, partially fired.

### A process failure: G3.75 was crossed, by me, while building the check for it

**The device answered an HTTP request before G3.75 passed.** The gate's wording
is *nothing is sent to the device until the pre-engagement is done*, and two of
its five boxes — isolation, and the ports half of the IoC pre-check — are still
open. The request was `GET /`, no parameters and no POST, sent to validate a
route check written minutes earlier. **The board was not read first.**

Two things are true and neither excuses it:

- **The state had already changed.** The laptop's USB Ethernet adapter came up on
  the Windows side and took a DHCP lease from the device (`10.1.1.10`), and a
  `ping` had already been answered. "No packet has been sent" stopped being true
  before this request.
- **The request is the least harmful shape available.** It reads one page.

Neither addresses the actual failure, which is that a precondition with its own
checkbox was not checked. **Recorded rather than repaired**, for the same reason
the 2026-08-16 document-sync failure was: the repair is one sentence and the
habit is not — and the habit is the thing the board exists to enforce.

What the request did return is real and is recorded: `Server: Boa/0.94.14rc21`,
which is `P1-3`'s first half and matches what three builds' string tables said.

### A second process failure: the file this session created had the wrong shape

`study/W05-bench-runsheet.md` was written at the start of the day to put one
document in front of the operator for an irreversible flash write. That instinct
was right. **What it became was not**: 1,091 lines holding five kinds of content,
of which **~580 lines were reusable procedure** — and its per-week name would
have forced a `W06-bench-runsheet.md` that copied them.

**That is one state with two owners, the failure this repository has now recorded
three times.** It was caught by the author asking whether it was the right shape,
not by anything here.

The interesting part is *how* it happened. The ownership question **was** asked,
once, and the answer was written into the file's own first paragraph on the first
version — when the file held only the `FLW` drill. **It was not re-asked as Phase
3's procedure, the results, the corrections and the handoff were appended to it.**
Same shape as the 2026-08-16 document-sync failure: *treating a question as a
checkpoint passed once rather than a state that has to keep holding.*

The fix, in the same commit as this note:

| | |
|---|---|
| **procedure** | `RUNBOOK.md` **§8.12**, cut into composable sub-sections — a week is *which sections in what order*, not a new document. §8.9 gains **§8.9.4**, the improved `FLW` steps that had existed only in the runsheet |
| **what was actually run** | **`BENCH-LOG.md`** at the repo root, append-only: the session's plan written before touching anything, then verbatim record cards |
| **verdicts and evidence** | unchanged, `test-cases.toml` |

And the rule that makes refinement safe rather than lossy, now in `CLAUDE.md`:
**because the bench log is verbatim, §8.12 may be refined freely** — the evidence
stands on what was typed and seen, not on the procedure document still saying
what it said. Today alone produced four procedure defects worth fixing, so a
procedure that cannot be corrected is the worse failure mode.

### Corrections to the plan

The plan's Day 1–7 ordering assumed the network came first and emulation second.
It ran the other way round, because G3.5 #5 blocked anything reaching the device
and the emulation needed nothing. **That ordering turned out to be the better
one on its own merits**: three of the payload shapes the plan specifies for the
hardware are wrong (`id`, the unescaped `>`, and `cp -rf /web/*` as the reason
`/var` is writable), and each was found in an environment where being wrong costs
nothing.

`notes/prediction-scorecard.md` was not created — that decision was already
recorded in W05 Day 0, and the twelve predictions live in the register.

### Open, carried forward

W04-2's list stands except #15, which is answered above. Added by this session:

16. **`boa` cannot serve under `qemu-user`.** The alignment trap is understood
    and bounded; what is not decided is whether to spend a day on full-system
    emulation to get past it, or to leave the HTTP layer entirely to the device.
17. **What `FLW` actually does to the sector.** Step 6 returning `FF` proves an
    erase happened; Step 5 showing an untouched neighbour in the same 4 KiB
    sector says the erase preserved it; and **the boot loader's command set
    contains no erase command at all**, so `FLW` must do it. The reading that
    fits all three is read-modify-erase-program of the whole sector — which would
    mean **every `FLW` rewrites 4 KiB**, and `H601` lives inside one.
    **The evidence for Step 5 is also weaker than it looked**: the read-back used
    a RAM address the previous step had already filled with the same pattern,
    which `RUNBOOK.md` §8.7.8 warns about by name. One triple of commands
    settles it — [`RUNBOOK.md` §8.9.3](RUNBOOK.md).
18. **Does `boa` serve a file created in the document root after start-up?**
    `boa.conf` sets `DirectoryCache /tmp`. Oracle 0 depends on the answer and it
    has not been tested.
19. **What `flash test-csconf` counts as invalid**, which decides whether finding
    8 (a corrupt configuration enables telnet) is reachable by anything other
    than physical damage.
20. **`flash set` on a configuration MIB commits nowhere.** `flash write-current`
    did not write either. Something must eventually persist `COMPCS`; what, and
    when, is unread — and W06 writes to that region.
21. ~~**The bench laptop is not on the device's segment.**~~ → **fixed**, and the
    diagnosis is the part worth keeping. The USB Ethernet adapter was bound but
    not attached to WSL, so it came up on the Windows side; packets were routed
    and **the only tell was `ttl=63` where a directly attached host answers 64**
    — while `ping` succeeded and `Cannot find device "eth1"` was true at the same
    moment. `bench-probe` now derives the fact from `/proc/net/route`, records it
    in every transcript, and refuses the SSDP group outright.
22. **Two open TCP ports that nothing predicted: 52869 and 52881.** The register
    reasoned its way to "UPnP is listening" from `UPNP_ENABLED = 1` and got the
    *port* wrong — it named 1900. Both extra ports are UPnP-adjacent and both
    have CVE history against this SDK, so the question is not "what are they"
    but **why the prediction stopped at the SSDP port**. Worth answering before
    W07 predicts anything else about services.
23. **At least one `/boafrm/` route is not in the recovered `root_form[]`.**
    `formOpdRedirect` and `formWanRedirect` answer distinctly; the table has 57
    entries and does not contain them. The `/boafrm/` prefix string is referenced
    by **eight** functions in this build, and only one of them is `handleForm`.
    Every count derived from 57 / 59 / 49 since W03 is provisional until that is
    resolved.
24. **What the global at `0x004899d8` is actually for.** Open #9 asked who reads
    it; the behavioural answer is that it does **not** gate anything — a
    credential-less request is rejected immediately after a successful one, from
    the same address. So the question changes rather than closes.
25. **Is the unauthenticated `status.htm` disclosure already published prior
    art?** It leaks the build string, three MACs, the LAN address, SSID, channel,
    encryption mode, client and WAN state. `notes/cve-status.md` has not been
    checked against it and **no novelty is claimed** until it is.
26. **Does the `CX` discrepancy hold for the other five products in
    CVE-2024-51228?** A3002RU, N300RT and N302RE are all `-CX-` builds. If their
    web interfaces also report the non-`CX` string, the identification gap is a
    property of the vendor's build system rather than of this one unit — and that
    is the difference between an anecdote and a finding.

---

## W05 close-out — 2026-08-17 (afternoon)

**The register reads 27 of 27 and the DoD is 5 of 5.** The five that were
outstanding all needed the device, and all five were run in one seating.
Verbatim record cards: [`BENCH-LOG.md`](BENCH-LOG.md). Verdicts and evidence:
[`test-ledger.md`](test-ledger.md).

### The boot loader's strings were never in the dump

`grep FLR` over the whole 4 MiB finds nothing. So does `grep "COMMAND MODE
HELP"`. That silence had been read as *the loader is small and terse*; it is
not. `0x000000`–`0x0012F0` is stage 1 — DRAM training, `Booting...`, `DTR
Done.` — and at **`0x0012F0` there is an LZMA-alone stream, 17,334 bytes in and
56,592 out**, holding the command interpreter, the TFTP client, the SPI chip
table and the whole help text.

[`tools/loader-unpack.py`](tools/loader-unpack.py) recovers it and **refuses to
write a report** unless exactly one stream is found in the region, the declared
output size matches, the help banner is present, and all seventeen commands the
console's own `?` prints are found by the same scan that reports absences. That
last one is the whole design: this report's headline result *is* an absence.

It also traces `chipName: UNKNOWN`, which
[`notes/uart-findings.md`](notes/uart-findings.md) recorded as explicitly
unconfirmed. **One of its three halves now holds and two still do not.** The
loader's chip table carries Eon parts only as `F` and `Q` families — no `QH` —
and `UNKNOWN` is the table's last entry. The *fallback behaviour* is a claim
about code and this is a string scan; and **which** chip it failed to identify
is still unknown, because the JEDEC ID has never been read
([`notes/hardware-inspection.md`](notes/hardware-inspection.md) still lists it
as outstanding). The silkscreen remains the only source for the part number.

### `P9-1` — refuted, and refuted without spending a boot cycle

The prediction was that the `<RealTek>` prompt could be caught and `init=`
passed from there. The first half is true — it was caught twice. **The second
half has no mechanism**, and three instruments say so without sharing a line of
code:

| | |
|---|---|
| loader stage 2, decompressed | thirteen command-line-shaped needles, **zero hits**. No environment, no `bootargs`, no `setenv`, nowhere to put an `init=` |
| the device's own `?` | sixteen commands, matching the binary's string table entry for entry |
| the kernel, decompressed from flash `0x060010`+`0x2808` (976,470 → 3,374,772, declared size matched) | `console=ttyS0,38400 root=/dev/mtdblock1` at `0x2f9590` — compiled in, **no `init=`** — while `No init found.  Try passing init= option to kernel.` at `0x2d8590` shows the kernel *would* honour one |

And the observation that closes it: **the boot log prints no `Kernel command
line:` line, because that string is not in the kernel image at all.** The
console and the image agree, and the image explains the console.

The route that remains is RAM-only and now fully specified: `AUTOBURN 0`,
`LOADADDR`, TFTP a kernel with a patched command line into RAM, `J`. Zero flash
written. It costs the ability to recompress a kernel, and it is not W05's.

### `P9-3` — and two of my own success conditions were wrong

Rescue mode is enterable. `AUTOBURN 0` gives `AutoBurning=0`; `IPCONFIG
10.1.1.1` gives `Now your Target IP is 10.1.1.1`. **The colon forms the help
prints are both `Unknown command !`** — the loader's string table holds the
command token and the help line separately, which is the third time this
loader's documentation disagrees with its parser.

Its network answers: ARP resolved, and the kernel's own `rx_packets` went 0 to
1, which is a second source for *the link delivered something*. A TFTP read
request for a name that cannot exist came back with **516 bytes of DATA**.

**The plan written that morning said "ping answers and the MAC is this unit's".
Neither happened, and both halves of that condition were mine and wrong.** A
TFTP-only stack owes nobody an ICMP implementation, and the loader synthesises
its MAC from the address it was handed (`0a 01 01 01` is `10.1.1.1`). The
register's frozen condition asks only whether rescue mode can be entered. It
can. Recorded `partial`, because the prediction says `tftp put` and put was not
exercised.

### `P1-12` — 38.76 s, and the margin is the finding

From the first console character to the first HTTP 200, measured by
[`tools/coldboot-timing.sh`](tools/coldboot-timing.sh) with both halves stamped
by one clock. `boa: starting server pid=350, port 80` lands at **+32.50 s and
the first 200 at +38.76 s** — six and a quarter seconds during which the server
has announced itself and answers nobody.

The prediction is "under 40 s" and the refutation says "clearly over", so it
stands. **But t=0 is the first console character, not the moment power was
applied, so 38.76 s is a lower bound with 1.24 s of headroom.** This test exists
to be the baseline for every later "the service did not answer" judgement. The
usable form of it is **wait 45 seconds**, not 40.

### `P3-13` — confirmed, without running a single handler

The claim is about the gate, and the gate decides from the URI in
`process_header_end` before `handleForm` is reached — so `bench-probe writes`
asks with GET, which never reaches dispatch on this build.

All 57 `/boafrm/formX` answer `302 -> home.htm`; all 57 `/boafrm/formX.htm`
answer `302 -> login.htm`. **Write-class and read-class are indistinguishable**,
including the three the test's own text names. One exception, and it is the
week's neatest result: `/boafrm/formLogin.htm` answers **404**, because
`formLogin` is one of the eleven exemption strings W04-2 read at instruction
level. A handler name that happens to contain an exemption token is exempt.

### The gate: this morning's correction was itself wrong

**W04-2's instruction-level read was right in every particular.** Eleven
exemption strings, every comparison an unanchored `strstr`. Five of the `.htm`
names are not shipped in the 143-file bundle, so the model predicts exactly
seven exempt pages — the five listed literally, plus `wan_status.htm` and
`Connect_status.htm`, which are exempt only because `status.htm` is a substring
of them. **Seven predicted, seven observed, sixty-nine blocked, no error either
way across all 76 shipped pages**, and then four more the model had never seen,
all correct.

So the morning's sentence — *"unanchored in the disassembly is not unanchored in
effect: the comparison is anchored or length-limited somewhere the read did not
capture"* — contradicted an accurate disassembly in order to explain twelve
failed bypasses. Fifteen further shapes that afternoon also failed, and the
reason is one line: **the exemption and the file lookup read the same normalised
path.** `/password.htm?x=status.htm` stays `302` because the query is not part
of it; `/password.htm;status.htm` becomes `404` because it *is* exempt and there
is no such file. X-3 does not stand — for that reason, not the recorded one.
Full working in [`notes/auth-flow-2018.md`](notes/auth-flow-2018.md).

### `P1-4` — partial, and it took the web server down twice

Two independent sweeps agreed closely: 34 / 36 POSTs sent, 31 / 32 answered,
**not one 404**, 13 refused by name. `formSysCmd` answered `302 -> status.htm`
in 10 ms, which is DoD item 5.

It is `partial` for two reasons and the second is the finding. **An
unauthenticated POST carrying no parameters at all holds this device's single
web server for four to ten seconds** — `formPortFw` 9,650 ms, `formPocketWizard`
6,359 ms, `formWlanSetup` / `formRoute` / `formSysLog` at the client's 6 s
ceiling. Around forty-five of them in sequence stopped it answering entirely,
both times. `ping` kept working throughout, the console printed **not one
line**, and **`boa` was still absent twenty minutes later**: `rcS` starts it
once and nothing respawns it.

`P1-4`'s refutation said, in advance: *"connections dropping — first confirm
whether you knocked boa over yourself."* We did, and it is provable: per-request
`elapsed_ms`, a control that retries and can tell *busy* from *dead*, and a
console with nothing on it.

This is **not** `P4-1`. That one omits `submit-url` and writes into a read-only
segment. This one carries `submit-url` and is entirely well-formed.

### The one that was not on anyone's list

The POST round changed the configuration, which was planned, snapshotted either
side, and attributed. What it changed was not planned:

```
0x00000-0x06000  boot loader                     UNCHANGED
0x06000-0x08000  H601 (MAC + radio calibration)  UNCHANGED
0x08000-0x0c000  COMPDS factory defaults         7,105 bytes changed
0x0c000-0x10000  COMPCS live configuration       6,963 bytes changed
```

COMPCS moved in 19 fields. **COMPDS moved in 23 — the same 19, plus the four
that used to distinguish it — and in each of those four it moved to COMPCS's
value.** The two regions are now identical across all 343 shared entries, and
both still pass `libapmib`'s own checksum.

**So an unauthenticated configuration write also overwrites the factory-default
region.** Two consequences:

1. **W04-2 open #20 is answered.** It asked what eventually persists `COMPCS`,
   given that `flash set` and `flash write-current` did not. The answer is a
   POST to a form handler, and it persists both regions.
2. **On this build, "restore factory defaults" would restore the attacker's
   configuration.** `P9-9` predicts reset overwrites COMPCS from COMPDS; if that
   holds, and COMPDS is a copy of the modified COMPCS, the reset button is not a
   recovery path. The only recovery is rewriting from a copy held off the device.

**Nothing moved in a dangerous direction** — `SSH_ENABLED`, `UPNP_ENABLED`,
`PING_WAN_ACCESS_ENABLED` and the three `VPN_PASSTHRU_*` flags all went 1 to 0.
One field is worth its own line: **`NOTICE_ENABLED` went 0 to 208.** A boolean
holding 208 means a handler wrote whatever its accessor returned for an absent
parameter, and that value was neither 0 nor 1.

> **And `P9-9` was deferred to W07 precisely to protect the 4-of-343 difference
> that this destroyed.** The guarded action was guarded; the unguarded one
> reached the same evidence through a door nobody had labelled. That is how a
> risk register fails — not by missing the dangerous thing, but by writing the
> danger on the loud one.

The pre-sweep 64 KiB snapshot is byte-identical to the 2026-08-16 full dump, so
**nothing is lost**; restoring COMPDS is a 16 KiB `FLW`, and W06 opens with it.

### Open #17 — settled, with a control the first attempt did not have

`DB` after `FLR` of flash `0x3F0100` into a fresh RAM address returns
`ca fe ba be ca fe ba be`: the neighbour written on the morning of 2026-08-17
survived an `FLW` to `0x3F0000` in the same 4 KiB sector. **`FLW` is
read-modify-erase-program of the containing sector and it preserves the rest of
it.**

The evidence is stronger than the morning's for a reason worth keeping. The
morning's flaw was reading back into a RAM address that already held the
expected pattern; the obvious fix is "use an address you have not used", and
that is still weak — you do not know what is in it. `console-dump.py dump` runs
a positive control first, reading flash `0x000000` into **the same** address and
matching `0b f0 00 04`. So before the real read that RAM held a **third** thing,
neither of the two answers. The control that proves `FLR` works also proves the
destination was not already the answer.

For W06: writing `HW_WLAN0_WSC_PIN` will not disturb the rest of `H601` — but
power lost mid-cycle costs the whole 4 KiB, not eight bytes.

### Instrument work

| | |
|---|---|
| [`tools/loader-unpack.py`](tools/loader-unpack.py) | unpacks the loader's LZMA stage 2 from a flash dump. Refuses on: no stream, more than one stream, a size that does not match, a missing help banner, or any of the seventeen commands not found. `tools/test-loader-unpack.sh`, 7 cases, needs no dump |
| `console-dump.py rescue` | the one write this reader is allowed to make. It can emit **only** `AUTOBURN 0` — no flag turns it on and the string does not exist in the file — and it asserts the reply before touching the network |
| `bench-probe` refusal list | thirteen handlers refused **by name with a reason each**, the skipped names recorded in the transcript's first record, overridable only by a second flag that is also recorded |
| `bench-probe writes` | answers `P3-13` with GET, so no handler runs. Its classifier is reported as the proxy it is — splitting on "reaches a process-spawning sink" calls `formPasswordSetup` quiet — so it also probes the three endpoints the test's own text names, and refuses to run if the table lacks them |
| `rtcase` `[schedule].sha256` | a week may move and may not move quietly. `rescheduled_from` + reason + date required, hash re-declared in the same commit. `test-rtcase.sh` 27 to 33 cases |
| [`tools/coldboot-timing.sh`](tools/coldboot-timing.sh) | one power cycle feeding `P1-12`, `P9-1`'s dynamic half and a timestamped boot log, both clocks the same clock |

### Instrument bugs 18 through 21

**18. A guard that pushes the dangerous action onto a human is inverted.**
`console-dump.py` refused `AUTOBURN` because it is a write — correct for a tool
that only reads. But `AUTOBURN 0` is the command that makes every later command
safe, and refusing it meant typing it into picocom next to the opposite value,
on the only unit there is.

**19. The help text is not the syntax.** `AUTOBURN: 0` and `IPCONFIG:<addr>`
are both `Unknown command !`. The loader stores the command token and the help
line as separate strings, and the accepted forms use a space. Third instance of
the same trait on this loader.

**20. A run that stopped wrote nothing.** `bench-probe` detected the most
interesting event of the session — the web server ceasing to answer — and
discarded the evidence of it in the same action: fifty-nine responses with the
`elapsed_ms` that would have named the slow one. **Detecting an event and
destroying its record should not be the same code path.** The journal and the
records now live at module scope and are written on every exit.

**21. `set -o pipefail` plus `grep -q`, reintroduced by me, into a guard
suite, on the day this file recorded it as bug 15.** `grep -q` exits on match,
the writer takes `SIGPIPE`, and the pipeline reports 141 for a *successful*
match — so two refusals that fired correctly were reported as failures. Knowing
a failure mode and not recognising it are different things, and a guard suite is
the worst place to find that out.

Twenty-one recorded. **Seventeen were caught by comparing two things that should
have agreed; four by a check written to fail.**

### The control that made the attribution possible, and it cost nothing

The 11:02 snapshot was byte-identical to the 2026-08-16 dump — after two boots,
a full unauthenticated GET round and a successful login had happened in between.
**So booting and reading change nothing in the first 64 KiB**, which is what
makes every byte of the post-sweep difference attributable to the POST round.
That control was not run for the purpose; it was the routine pre-flight
snapshot, and it happened to answer the question the afternoon needed.

### Deliberately not done in the close-out

| Item | Why |
|---|---|
| **Restoring `COMPDS`** | It is a flash write, and this session's ceiling was non-destructive by the author's decision. The data exists twice off the device. W06 opens with the restore, where a write procedure and a verification step already have to exist |
| **A third POST sweep** | Two runs agreed closely and the incremental information is nil against more configuration change. `P1-4` is `partial` and says why |
| **Chasing the TFTP read** | `IPCONFIG` plus a TFTP read request for a nonexistent name returned 516 bytes matching flash `0x060010` exactly. If the served address follows `LOADADDR`, that is a flash read in seconds where the console path takes 105 minutes — an instrument question big enough to deserve its own plan, not the last hour of a week |
| **Characterising the POST stall as a defect** | It is recorded with numbers and left unclassified. Whether one request suffices, how long it lasts and whether it is already published are W06/W07 questions, and `docs/disclosure.md` holds the item |
| **Reporting anything to TWCERT/CC** | Unchanged |

### Corrections to the plan

| Said | Actually |
|---|---|
| **This morning:** "reaching `formSysCmd` means POSTing to it, and that is the proof-of-concept the plan reserves for W06" | Two different acts. A POST with no `sysCmd` demonstrates reachability and executes nothing — the handler's own guard is in W04-2's decompilation. The DoD would have stayed open for a reason that does not exist |
| **This morning:** the exemption comparison "is anchored or length-limited somewhere the read did not capture" | Nothing was missed. It is an unanchored substring test on the normalised path, and it is not a bypass because that path is also what the file lookup uses |
| **`RUNBOOK.md` §8.9.2:** `Flash Write Successed!` is simply the wrong string | It exists, at stage-2 `0x0a861`, in the TFTP auto-burn cluster. The interactive `FLW`'s message is 2.7 KiB away beside `Flash Read Successed!` — which *is* what the interactive `FLR` prints. The original expectation was not invented; it was the other path in the same binary |
| **The register:** `P3-1`, `P3-2`, `P3-3` are W05 items | W05's own plan forbids them. Moved to W06 with a reason on the record |
| **The register:** `P9-9` is a W05 item | Destructive, and it deletes evidence other tests depend on. Moved to W07 |
| **`BENCH-LOG.md`'s header:** "per-unit identifiers are not written here" | The 2026-08-17 morning entry records two MAC addresses. The file is append-only, so the entry stands and the contradiction is recorded rather than repaired — either the rule is too broad or the entry is a breach, and that is the author's call, not a footnote |

### Open, carried forward

W04-2's list stands except #20, answered above. From the morning: #16, #17
(**answered above**), #18, #19, #21 (fixed), #22, #23 (**answered below**), #24,
#25, #26. Added or changed by the close-out:

23. ~~**At least one `/boafrm/` route is not in the recovered `root_form[]`.**~~
    → **answered.** `formOpdRedirect` and `formWanRedirect` are referenced by
    `init_get` (`0x00407b7c`) and `process_header_end` (`0x0040bb1c`), not by
    `handleForm`; `init_get` holds `redirect-url=`, `&wlan_id=`, `tcpipwan.htm`
    and `opmode1.htm` beside them. **`root_form[]`'s 57 entries are not short —
    they are complete for `handleForm`, and there is a second, earlier route.**
    `formWlanRedirect2` resolves to no function at all: the string is in
    `.rodata`, nothing references it, and the device answers it exactly like an
    absent name. Every count derived from 57 / 59 / 49 since W03 can stand.
    [`reports/ghidra-xref-unit-2018-redirects.json`](reports/ghidra-xref-unit-2018-redirects.json)
    — whose `self_check` reads `SUSPECT` **by design**, because two selectors
    resolved to nothing and one of them is the negative control.
27. **The boot loader's TFTP serves memory to a read request for any name.**
    516 bytes came back matching flash `0x060010` byte for byte. Whether the
    address follows `LOADADDR` decides whether this is a curiosity or a flash
    read that takes seconds instead of 105 minutes. It needs console access, so
    it is not remotely reachable — it is an *instrument* question.
28. **An unauthenticated, parameter-less POST stalls the only web server for
    seconds, and about forty-five in sequence remove it until a power cycle.**
    Distinct from `P4-1`. Unclassified on purpose: whether one request suffices,
    how long the stall lasts, and whether prior art covers it are all unmeasured.
29. **`NOTICE_ENABLED` holds 208.** A boolean written by a handler whose
    parameter was absent, so the accessor's default for that field is neither 0
    nor 1. `form_formNotice` is the only handler whose sole tracked sink is
    `system()`.
30. **Which handlers write MIB, as opposed to spawning processes.** The
    `bench-probe writes` classifier splits on process-spawning because that is
    what a committed report can measure, and it therefore calls
    `formPasswordSetup` quiet. Naming the real set needs an `apmib_set` caller
    census, which no report carries.
31. **`SSH_ENABLED` was 1 on this unit** — before the POST round set it to 0 —
    while port 22 is closed and no `sshd` or `dropbear` appears in the port scan.
    Either the flag means something else or the daemon is absent. Noticed while
    attributing the diff; not chased.
32. **Five of the gate's eleven exemption strings name pages the bundle does not
    ship**, and `formUpload` / `formUploadConfig` are referenced by
    `process_header_end` without behaving as exemptions —
    `/boafrm/formUpload.htm` is still blocked while `/boafrm/formLogin.htm` is
    not. Same function, three different uses of a string, and only one of them
    read.
33. **Thirty-five guard cases are not wired into `make ci`** —
    `test-console-dump.sh` (18), `test-photo-tools.sh` (13),
    `test-flash-tools.sh` (4). The first two need no hardware, so this is a gap
    rather than a constraint: the flash parser's guard suite — the one covering
    the code path every byte of this unit's dump came through — is the largest
    of the three and CI does not run it. Found while recounting the totals, not
    by anything checking.
34. **`tools/check-runsheet.py` reads two files, and there are more.**
    `REPRODUCE.md`, `README.md` and `docs/` all carry command blocks that
    nothing reads as commands. §8.12 was the case where an unread file held a
    refuted command; there is no reason to think it is the only one.

---

## W05 close-out, second pass — 2026-08-17 (evening)

**A documentation pass, and it found an instrument gap that mattered more than
the formatting it set out to fix.**

### Instrument bug 22 — the checker's blind spot held the bug it was written for

`tools/check-runsheet.py` exists because on 2026-08-17 a step shipped with
`AUTOBURN: 0`, which the boot loader rejects, and nothing in the repository read
the commands as commands. **It reads `runsheet.md`. It did not read
`RUNBOOK.md`.**

`RUNBOOK.md` §8.12 opened by declaring that the commands had moved out to the
runsheet — and then carried **twelve command blocks**, of which **four had
already been refuted by the bench the same day**:

| §8.12 said | The bench measured |
|---|---|
| `AUTOBURN: 0` / `IPCONFIG:10.1.1.1` | Both `Unknown command !` — instrument bug 19, recorded above, still live in the file that recorded it |
| Rescue success = "`ping` answers" and "the MAC is this unit's" | Neither holds. No ICMP in the loader's stack; the MAC is synthesised from the IP |
| "Linux always prints `Kernel command line:`" | The string is not in this kernel image at all, so it never prints |
| Two terminals, one capturing and one polling | Two terminals cannot share a clock; `coldboot-timing.sh` exists for that reason |

**The fix is not to check the commands there.** It is to forbid them: CI now
fails if §8.12 contains any command fence, so a section that may not hold a
command cannot hold a stale one. Paired with it, every step names one `§8.12.x`
and every `§8.12.x` names exactly one step, one-to-one, checked from both ends.
`tools/test-check-runsheet.sh` went from 15 cases to 29 — five of the new ones
are for these rules, and each fails the checker on a doctored copy of the real
RUNBOOK rather than a fixture, because the fixture is where the previous version
of this bug hid.

**Twenty-two recorded. Eighteen were caught by comparing two things that should
have agreed; four by a check written to fail.** This one was neither: it was
caught by asking what the checker does *not* read.

### The runsheet was renumbered, and the reason is not tidiness

Part A was `A0`–`A14` with `A1.6`, `A1.7`, `A8.5` and `A11.5` inserted later —
numbers recording edit order rather than structure, plus an `A8.5-預告`
subsection inside `A8` that was a different section from the `A8.5` after it.
**The load-bearing defect was that the document's order was not the run order**:
Part A read `A0`→`A14` while Part B's actual session ran
`A0`→`A2`→`A3`→`A5`→`A4`→…, because `A5` needs the board stopped at `<RealTek>`
and `A4` needs the network adapter. A stranger reading front to back would have
run them in the wrong order and nothing in the file would have stopped them.

**Part A is now four stations, and the first digit of a step is the device state
it needs** — `A1.x` desktop, `A2.x` stopped at `<RealTek>`, `A3.x` booted and
serving, `A4.x` wrapping up. Front to back is now a correct order by
construction, and CI checks that a step sits under the station its own number
names. Entering a station costs one power cycle, which is why its steps are
grouped: the ordering mistakes this project has made were all steps run in the
wrong device state. Old→new mapping is `runsheet.md` Part B `B-0`.

### Corrections to the plan

| Said | Actually |
|---|---|
| **`RUNBOOK.md` §8.12's own header:** "the commands moved out, this section is why only" | Twelve command blocks remained, four of them refuted the same day. The claim was made and not enforced, which is the shape of a self-check that reports success with nothing to work on |
| **`runsheet.md` and `REPRODUCE.md`:** "95 guard cases, 205 checks" | Undercounted, and not reproducible from any command. `REPRODUCE.md`'s own per-suite table summed to 95 because it **omitted `test-check-runsheet.sh` entirely** — the guard suite for the checker that guards the runsheet. Measured: **124 guard cases across eight suites**, of which **`make ci` runs 89**; plus 110 parser tests = 199 for `make ci`. Every number now carries the command that recounts it |
| **`Makefile`:** `runsheet-test` "(18 cases)", `rtcase-test` "(22 cases)" | 29 and 33. Help text that counts things drifts the moment a case is added, and nothing was reading it |

### Deliberately not done in this pass

| Item | Why |
|---|---|
| **Reformatting `BENCH-LOG.md`'s punctuation** | It is append-only and verbatim. Changing its punctuation is changing evidence, and the CJK/ASCII mix inside it is now a deliberate exception rather than an oversight |
| ~~**`LOG.md` and `study/QA.md` punctuation**~~ | **Done, in its own commit** — 1,554 and 2,230 sites. Folding them into the restructure commit would have made `git blame` useless on both, so they went first and alone |
| **Renumbering `§8.12.x`** | `BENCH-LOG.md` cites those numbers and is append-only, so they are frozen. Three numbering schemes still exist; the bridge between two of them is now machine-checked, and the third stays in the verbatim record |

---

## W06 — 2026-08-17 (night)

**G4: four of five.** The chain is closed on this hardware and the evidence
reaches the silicon, but the gate's third clause — *an L2 reproduction path on a
downloadable image* — is not met, and the reason is a finding rather than a
shortfall.

The register reads **18 of 18** for the week: 17 run tonight, and 10 items
rescheduled to W07 with a reason each. The 10 are not a shortfall either; W06's
own plan forbids fuzzing outright, and the register had inherited them from the
playbook's section numbering rather than from the week plan — the same failure
found in W05 on 2026-08-16, fixed the same way.

### G4 — five clauses, and the one that failed

| # | Required | Result |
|---|---|---|
| 1 | one chain on the hardware, each link separately pointable | ✅ and it is **shorter** than planned — see below |
| 2 | at least one link evidenced **out of band**, not from the HTTP response | ✅ **two**: ICMP echo requests sourced from the router, and nine named bytes on the SPI NOR |
| 3 | an L2 path: anyone, a **published** image, emulation | ❌ **not met.** `formSysCmd` is in *neither* downloadable image's dispatch table, so the chain cannot exist there. The route is now open — `boa` does serve under `qemu-user`, proven tonight — but it was proven with *this unit's* rootfs |
| 4 | every PoC document opens with a scope table | ✅ four documents, and one of them is a stub that carries no request on purpose |
| 5 | `poc/run.sh` fails, and names which step | ✅ run in both modes; it caught two defects **in itself** on its first run |

> ⚠️ **Clause 3 failing is worth more than clause 3 passing would have been.**
> The plan assumed L2 would run the `localPin` line, which *is* byte-identical in
> the 2015 and 2020 images. W04-2 then moved G4's target to `formSysCmd` for good
> reasons — it is the CVE that names this build — and nobody noticed that the new
> target exists in no image anyone can download. **The two decisions were each
> correct and their combination was not**, which is a thing a gate is supposed to
> catch and did.

### The chain, and the two ways it turned out shorter than drawn

```text
① GET /config.dat, unauthenticated         200, 7,507 bytes, magic COMPCS
② decode                                   USER_NAME / USER_PASSWORD, plaintext
③ authenticate with them                   200 — and ④ does not need this
④ POST /boafrm/formSysCmd, no credentials  ICMP echo requests from the router
⑤ read the flash before and after          nine bytes, named, and reversed
```

**Link ③ is optional.** ④ works with no credentials, and the identical request
*with* credentials behaves identically — which is the measurement that rules out
"something else was carried in". An unauthenticated success on its own does not.

**And there is a second chain that needs neither ① nor ②.** `formPasswordSetup`
carries `Cusername` / `Cpassword` fields for the current credentials, and the
handler does not check them: an unauthenticated POST that does not know the
current password changes it. Reading the password out of `config.dat` first is
not necessary for takeover. → `poc/04-auth-takeover.md`, held.

### 1. Nine bytes on the flash, and they are in the wrong region

**`flash set HW_WLAN0_WSC_PIN` writes `H601`, not `COMPCS`.** `plan/W06` §2 drew
link ⑤ as *"`flash set` writes the `COMPCS` block"*. It does not: `HW_WLAN0_*`
ids live in the **hardware** MIB at `0x6000`–`0x8000`.

```text
0x00648a  71 -> 61        (cmp -l prints octal: '9' -> '1')
 …
0x006491  62 -> 70
0x006493  15 -> 25        <- the region's checksum, recomputed by the device

before: 99956042      after: 13572468
```

The evidence was already here. W05's emulation run printed `0x00648a`,
`0x00648b` and `0x006493` and annotated the third as *"the H601 region's 8-bit
checksum"* — **the region was named on the same line as the offsets**, and nobody
joined the two sentences, this author included, who fired the first shot at the
device without doing so.

**That makes the finding worse, and the difference is the point.** `COMPCS` is
configuration: rewritten by any handler, and restored by a factory reset. `H601`
holds this unit's **MAC addresses and radio calibration**, measured at
manufacture, present in no vendor image, and not restored by a reset.

> 🔴 **The guard protected the instrument, not the device.** This morning
> `tools/console-write.py` was built with an allow-list that makes `H601`
> unreachable by construction, with no flag that widens it. Tonight the device's
> own `flash set`, driven by one unauthenticated HTTP request, wrote it anyway.

Reversal is half the claim and it holds: the final read is byte-identical to the
pre-injection snapshot **and** to the 2026-08-16 full dump, taken before this
project had ever written to the device. Restored through the device's own MIB
writer, so the checksum is recomputed by the code that owns it.

### 2. One request removes the web server, permanently

A single unauthenticated, **well-formed** POST to one form handler — only
`submit-url`, no payload, no overlong parameter — and `boa` is gone until a power
cycle. Three POSTs of the same shape to a different handler immediately before it
were served normally; the fourth returned nothing at all, and thirty seconds
later the listening socket was still gone while ICMP to the device answered in
1.6 ms. `rcS` starts `boa` once and nothing respawns it.

This also revises W05's reading of its own data: that session attributed the
outage to **volume** ("around forty-five in sequence"). Whether the W05
transcript shows this same handler is a re-reading of that record, not something
tonight measured. → `docs/disclosure.md` **D-11**, held.

### 3. Two project-original findings withdrawn, one of them by prior art

- **`D-1` withdrawn.** `form_formRoute` / `subnet` produced no command execution,
  while `localPin` on `formWsc` produced four ICMP echo requests through the same
  oracle in the same session — a discriminating control, not an absence.
  `BoaGate`'s R2 rule mis-classified an `sprintf` site as a `system()` site, and
  that rule feeds conclusions about all three builds.
- **`D-2` does not reproduce on this build**, and `P4-3` refuted the mechanism
  with a **positive** witness rather than an absence: `formNtp` echoes
  `submit-url` into its `Location` header, and 800 bytes come back as 799 `A`s
  with no truncation at 100. The value provably reaches the code that consumes it
  and nothing happens. This build does not use the `lastUrl[100]` idiom W04
  measured in 2015.

### 4. `boa` serves under `qemu-user` after all

W05 recorded that it could not, blocked on an alignment trap. The trap is real
and it is an unaligned halfword store, but it is not where that sentence puts it:

```text
open("/dev/mtdblock0") lseek(49152) read(7490)      <- COMPCS
open("/web/config.dat", O_RDWR|O_CREAT|O_TRUNC) = 3
--- SIGBUS si_addr=0x00492b41 ---                   <- odd address
```

It dies **generating `/web/config.dat` at start-up**, not serving. Make that one
`open()` fail and it binds and answers: `login.htm` 200, `blank.htm` 302 — the
gate model W04-2 read at instruction level, reproduced with no device attached.
The command injection reproduces there too, including the empty-file trap that
follows from the format string.

> **The irony is exact**: the line that produces this project's best evidence
> chain — an unauthenticated `GET /config.dat` — is the same line that makes it
> the one link emulation cannot reproduce.

### 5. The kernel banner, from a channel that did not exist before tonight

```text
Linux version 2.6.30.9 (admin@office.hopeiot) (gcc 4.4.5-1.5.5p2) #1526
  Wed Jan 10 14:50:54 CST 2018
MemTotal: 26052 kB
```

The kernel is stamped **seven minutes before `boa`**, so kernel and userland come
from one build session — corroborating W02's timestamp argument from a source W02
never read. And `MemTotal` refines a W02 claim: W02 said `ramSize: 32M` settles
*fitted vs usable* and "here they agree". **32 MiB is what the boot loader
detects; 25.4 MiB is what Linux has.** Two different measurements.

`/proc/cpuinfo` does **not** answer the Lexra question: `cpu model` is a decimal
number (`52481`), not a core name, and `system type` reads `RTL819xD` — a third
distinct naming beside the silicon ID's `8196E` and the Ethernet driver's
`8196C`. `/proc/cpu` does not exist, so there is no alignment-fixup counter, and
`dmesg` returns zero bytes.

### Claims that W06 overturned

| Said | Actually |
|---|---|
| **`plan/W06` §2:** "`flash set` writes the `COMPCS` block" | It writes `H601` — MACs and radio calibration live in the same 8 KiB |
| **W05 finding 6 / open #16:** `boa` cannot serve under `qemu-user` | It can. The trap is confined to the `config.dat` generation path at start-up |
| **`docs/disclosure.md` D-1:** `formRoute`/`subnet` reaches `system()` in all three builds | Refuted on the device, and predicted with a mechanism beforehand by a Talos advisory that a by-handler search found in one query |
| **`docs/disclosure.md` D-2:** omitting `submit-url` is a one-request crash | Not on this build. 800 bytes echo back intact and the server survives |
| **W05:** the web server outage was caused by request *volume* | One request to one handler is enough, with a three-request control immediately before it |
| **W02:** `ramSize: 32M`, so fitted and usable agree | The boot loader detects 32 MiB; Linux reports 26,052 kB |
| **`runsheet.md` A2.6, written the same morning:** restoring `COMPDS` returns the difference to 4 of 343 | 23. The difference is *between two regions* and the section restores one of them: 4 original + 19 the POST round changed in `COMPCS` |
| **`plan/W06` §3:** L2 runs the same chain on V2.1.2 | The chain's target handler is in neither downloadable image |

### Instrument work

| | |
|---|---|
| [`tools/console-write.py`](tools/console-write.py) | The flash **writer**, which did not exist this morning although `runsheet.md` A2.6 had specified it. An allow-list of two ranges — the drill sector and the config region — so the boot loader and `H601` are unreachable by construction. Positive control before every run, staged RAM read back before every `FLW`, and the written range read into a third address afterwards |
| [`tools/test-console-write.sh`](tools/test-console-write.sh) | 28 cases. First run: 19 passed, 6 failed, and all six were real |
| `qemu-env.sh serve` / `stop` | Stands `boa` up and **refuses to report it up** unless a gated page redirects *and* an exempt page is served. `stop` uses a pidfile, because `pkill -f` matches the calling shell's own command line and kills it |
| [`poc/run.sh`](poc/run.sh) | Two modes, preconditions that name the failing step, an RFC 1918 check, a banner check, and a refusal to start without `--i-own-this-device` |
| `rtcase` schedule hash | now covers the reschedule **reason**, not just `(id, week)` |

### Instrument bugs 23 through 27

**23. A refuted claim living inside a tool's own output.** `console-dump.py`'s
rescue path still told the operator that a `ping` reply is the whole of what
`P9-3` asks. The bench refuted that on the day it was written — this loader has
TFTP and no ICMP, and synthesises its MAC from the address it was handed.
`check-runsheet.py` reads `runsheet.md` and `RUNBOOK.md`; **nothing reads what
the tools themselves print.** Same shape as bug 22, one file further out.

**24. A dead branch holding the only correct message.** `make doctor`'s
direct-attachment check asked `/proc/net/route` whether `10.1.1.1` has a route. A
default route matches every destination, so the "no route" branch was
unreachable — and the check FAILED in the state every session begins in, telling
the operator to attach an adapter they had just attached. **A check whose failure
names the wrong fix is worse than no check**, because the real cause then looks
like the one you just ruled out.

**25. `BoaGate` R2 has false positives.** Two of the six sites it names in
`formWsc` / `formRoute` produce no execution on the device, and published prior
art explains one of them as an `sprintf` misread as a `system()`. This is the
first instrument bug in this project found by an **external** source rather than
by comparing two of its own instruments.

**26. A dry run that printed the bytes it promised to withhold.**
`console-write.py`'s first dry run printed the header *"this range is per-unit
secret: offsets and digests are logged, bytes are not"* and then every `EB` line
carried sixteen of those bytes — which for `0x8000` includes a copy of `COMPCS`
and therefore this unit's admin password. **A tool that states a guarantee and
breaks it on the next line is worse than one that never claimed it**, because the
claim is what stops the reader looking.

**27. Controls that could not distinguish what they were written to distinguish.**
Three tonight, the same mistake in different clothes: a liveness line formatted
with a leading `000` so it was indistinguishable from a failed request in the
distribution; `poc/run.sh`'s "did nothing get created" check testing whether the
body was empty, when this server answers a missing file with a redirect **page**;
and the `P4-3` ladder fired at `formWlanRedirect`, which is in `root_form[]` but
is **not** one of the 43 functions referencing `lastUrl` — the "or this path was
never walked" half of that test's own refutation, arrived at by accident.

**Twenty-seven recorded. Twenty were caught by comparing two things that should
have agreed, four by a check written to fail, one by asking what a checker does
not read, and one by an outside advisory.**

### A mistake worth more than the finding it nearly cost

Ninety minutes before measuring it, this session moved ten cases out of W06 and
wrote, into a machine-hashed field, that `P4-9` and `P5-6` were blocked because
*"`boa` cannot complete one GET under `qemu-user`"*. **That had not been run.** It
was read out of W05's prose and written down as a measurement, in a repository
whose first evidence rule is that no claim rests on one tool. When it was run,
`P0-9` came back **confirmed** and four of the ten reasons were wrong.

Correcting them moved nothing, because `[schedule].sha256` covered only
`(id, week)`. So a reason could be rewritten afterwards with no trace, and *"I
could not do this"* could quietly become *"I chose not to"* — the
prediction-freeze problem one field over. The hash now covers the reschedule
record, and `test-rtcase.sh` gains the case that proves it can fail.

### Deliberately not done in W06

| Item | Why |
|---|---|
| **Reporting anything to TWCERT/CC** | `docs/disclosure.md` step 2 requires a prior-art search **for the specific handler**, and it has not been run for `D-4` or `D-11`. The one run for `D-1` this evening took a single query and withdrew a finding; running it after a report would be the wrong order. The 90-day clock has not started |
| **A request for `D-4` or `D-11` in any committed file** | Neither has been reported. `poc/04-auth-takeover.md` names the findings and carries no request, which is the first time this project's own rule has cost it something it wanted to write |
| **The L2 environment on a published image** | G4 clause 3. The route is proven and the work is scoped: build a `qemu-env` from the extracted V2.1.2 rootfs and run the `localPin` chain, which is byte-identical in 2015 and 2020. A desktop task, and W07's opening |
| **`P4-5` onwards, `P5-1`–`P5-4`, `P5-6`, `P4-9`** | Moved to W07 with a reason each. `P5-1`'s is load-bearing: this unit has no shell and no gdbserver, so an `epc` oracle does not exist **on the device** — though it does under emulation now, which is why `P5-6` leads that block rather than trailing it |
| **A second shot to characterise D-11 further** | Whether it is a crash or a hang, and which parameter shape triggers it, are W07 questions. Tonight's measurement is deliberately one request and one control |
| **Re-reading the W05 POST-sweep transcript** | It would probably show whether the same handler caused that outage. It is a records question, not a bench question, and mixing the two is how tonight's measurement would stop being about tonight |

### Open, carried forward

W05's list stands except #16, answered above. Added or changed by W06:

35. **Are other `HW_*` MIB ids reachable the way `HW_WLAN0_WSC_PIN` is?** The MAC
    addresses are in the same region and the same table. One field was written;
    the generalisation is untested, and it is the obvious next question.
36. **`BoaGate` R2's other four sites.** Two of six are false positives. The
    remaining four have not been checked, and the rule's output is cited in three
    builds' worth of conclusions.
37. **Which handler kills `boa` in one request, and how.** Named in the register
    and in `docs/disclosure.md` D-11, not here. Whether it is a crash or a hang is
    unmeasured; `boa` writes no core and this kernel's `dmesg` is empty.
38. **`cpu model : 52481`.** Not a core name. The decisive test for the Lexra
    question is now a string scan of the decompressed kernel — which needs no
    device and was not run tonight.
39. **Does the W05 outage have the same cause as tonight's?** W05 attributed it to
    volume. Its transcripts carry per-request `elapsed_ms` and would settle it.
40. **`formSelLang` ignores `submit-url` entirely** and redirects to a hardcoded
    `countDownPage.htm`, while `formNtp` echoes it back in full. Both reference
    `lastUrl`. So "references `lastUrl`" and "uses `submit-url`" are different
    sets, and the 34-handler count from W04 describes the first.

### A gap found while auditing the close-out, not by any check

The question was whether the disclosure rule had cost this session any *record*.
It has not: for the three held findings the verdict, the frozen refutation
condition, every observation channel and the list of what was burned are all in
public files — `BENCH-LOG.md` cards `T-32`, `T-33` and `T-36`, and the register
rows for `P10-3` and `P10-4`. **The only thing withheld anywhere is the
copy-pasteable request**, which is what the rule says to withhold.

Checking that turned up something else.

**`D-11` has no row in the register at all.** Not because of disclosure —
because of the *freeze*. It came out of a handler census rather than a question
somebody wrote down first, so no prediction was ever frozen for it, and
`rtcase record` correctly refuses a case with no pre-written refutation
condition. The same is true of the Boa `HEAD`-method test, which is recorded only
in [`notes/prior-art.md`](notes/prior-art.md).

So:

> **The register holds only what was predicted. Anything found by looking rather
> than by asking falls outside it** — and the two most interesting results of
> this week, the single-request denial of service and the discovery that
> `flash set` writes `H601` rather than `COMPCS`, were both found by looking.

The concrete break is a missing cross-check: `docs/disclosure.md` carries `D-11`,
`test-cases.toml` has no corresponding row, and **nothing notices**.
`tools/check-runsheet.py` enforces the equivalent rule in one direction — every
executed register item must have a procedure that reaches it — and there is no
checker at all for the direction that runs between the disclosure register and
the test register.

41. **Every `D-*` entry should name either a register id or an explicit reason
    for having none**, checked mechanically, in the same shape as the runsheet's
    `<!-- no-procedure: … -->` blocks. Until that exists, a finding can live in
    the disclosure register with no test behind it and no count that would show
    the absence.
42. **And the deeper question that one exposes:** the freeze makes the register
    trustworthy by refusing unpredicted results, which also makes it structurally
    blind to discovery. A second class — recorded, counted, and *never* renderable
    as a confirmed prediction — would close it, but it has to be designed so that
    it cannot become a back door for filling in predictions afterwards. That is
    the whole reason the freeze exists, so this is not a small change and it is
    not being made at one in the morning.

---

## W07 Day 0 — G4 closed — 2026-08-18

**G4 passes at five of five, and the third clause was split rather than
satisfied.** `3a` — an L2 path for the command-injection *primitive*, on an image
anyone can download — is met. `3b` — an L2 path for the *L1 chain* — is closed as
**impossible by construction**: `formSysCmd` is in this unit's `root_form[]` at
`0x0044ee2c` and in neither published image. A CVE that names a build nobody can
download is not reproducible by anybody who does not already own one, and that
is a property of the disclosure rather than a shortfall in the work.

The register reads **W06 20 of 20**. It read 18 of 18 yesterday with the same
clause open, because the clause had no case behind it — open item #41's counting
failure, one register over.

### The environment, and what a download does not contain

The published V2.1.2 container has exactly three sections, each declaring the
flash offset it burns to: `w6cg`@`0x010000`, `cr6c`@`0x060000`, `r6cr`@`0x180000`.
**The first 64 KiB is in none of them.** Boot loader, `H601`, `COMPDS` and
`COMPCS` are written at manufacture. A flash built from the container alone gets
exactly this far:

```text
Invalid hw setting signature [sig=  ]!
Initialize AP MIB failed!
```

which is `P0-11`'s prediction — frozen and committed before the environment
existed — down to the string. 82.9 % of the image is reconstructed from the
download; three regions are synthesised with zeroed payloads and **no byte comes
from any physical unit**. [`reports/mkflash-2.1.2.json`](reports/mkflash-2.1.2.json)
names every range and its origin.

`libapmib` states its own requirement when it refuses the next check —
`Expect [sig=6G, ver=3, len=32858]!` — and 32,858 is not this unit's 45,218. The
two builds do not agree on how large the MIB is.

### The chain link, and the controls that carry it

An unauthenticated `POST /boafrm/formWsc` carrying `localPin` executed a command.
The primary evidence is `qemu`'s own syscall trace, because the HTTP response
carries nothing:

```text
3540 fork() = 3550
3550 execve("/bin/sh",{"sh","-c",
     "flash set HW_WLAN0_WSC_PIN 1;cat /etc/version > /var/web/l2pin.txt;#",NULL})
```

The second channel is the document root: the file exists and holds
`TOTOLINK-N150RT-V2.1.2` — **the published build naming itself through a command
it was made to run**.

| same handler, same session, one field different | executed |
|---|---|
| `localPin` | **yes** |
| `peerPin` | no |
| `targetAPSsid` | no |

That is the **same three-way discrimination W06 measured on silicon** — `P3-1`
refuted, `P3-4` not an injection, `P3-5` confirmed. Two environments five years
of firmware apart agree on which parameter is the defect.

### An independent confirmation nobody planned

`serve` refused to report the server up: `login.htm` 200 but `blank.htm` **200
instead of 302**, so the gate was not gating. The environment was not broken —
the synthetic MIB has an empty `USER_PASSWORD`, and with no password configured
the gate lets everything through:

| `USER_PASSWORD` | `blank.htm` |
|---|---|
| `""` | **200** — ungated |
| set through the vendor's own `flash set` | **302** — gated |

`P10-4` — *setting the admin password to empty leaves the whole device
unauthenticated* — was this project's own finding on the 2018 build. It is now
confirmed on a **different build, from a published image**, and it arrived
because a control refused to lie about an environment.

### Why Realtek SDK userland resists emulation, measured rather than asserted

The vendor's own `flash default` generates a real configuration "from hard code".
It **cannot run under `qemu-user`**: `SIGBUS`, `si_addr=0x004332a7`, an unaligned
store at an odd address. The device's MIPS kernel fixes those in its trap
handler; `qemu-user` raises the signal. The same trap is why `flash set` prints
`Bus error` **after** its write has already landed, and why `boa` does not
survive the handler it just executed a command for.

This generalises past this device, and it is why "just run the firmware under
qemu" fails so often on this SDK: the userland depends on a kernel service that
user-mode emulation does not provide.

### Instrument work

| | |
|---|---|
| [`tools/mkflash.py`](tools/mkflash.py) | Builds a flash image from a published container and emits a provenance map — every range labelled `published-image`, `overlay` (mandatory origin string, sha256) or blank `0xFF`. Refuses overlapping sections, an overlay colliding with the image, a section below the `0x010000` floor, and a magic that is not where the section table said it would be |
| [`tools/mkhwsetting.py`](tools/mkhwsetting.py) | A structurally valid, content-free `H601`. `--verify-format-against` re-derives the header from a real dump and compares **structure only** — no payload byte is read, printed or compared, because that region is per-unit |
| [`tools/mkcompds.py`](tools/mkcompds.py) + `fwrecon.compcs.lzss_encode` | The encoder this project has never had. `P8-12` has been parked as "blocked, `fwrecon` has no encoder" since the register was written, and it is no longer blocked. Every region is round-tripped through the vendor's **own** decoder before it is written |
| `qemu-env.sh --profile` | Two environments: `unit-2018` unchanged and re-verified, `v2.1.2` new. A profile must declare where its flash came from and a control that can fail; the new one refuses to `check` at all until its controls are measured |
| `qemu-env.sh mkflash` | The whole L2 build as one deterministic command with its sha256 pinned, so "anyone can do this" is checkable rather than asserted |

### Instrument bugs 28 through 30

**28. A refuted claim living in the register's own header.** `[schedule].note`
still read *"P0-9 refuted — boa cannot complete one GET under qemu-user"*. P0-9
came back `confirmed` on 2026-08-17 and every **hashed** field was corrected that
night. The note was not, because the schedule hash covers
`(id, week, rescheduled_from, reschedule_date, reschedule_reason)` and not the
prose that summarises them. The register's own header therefore asserted, for a
day, the claim its own rows twenty lines below had already withdrawn. Same shape
as bug 23, one file further in.

**29. `rm -rf` through a live mountpoint.** `cmd_build` deletes the environment
before rebuilding, and a previous build leaves `/proc` mounted inside it. The
delete failed on every procfs entry and left a half-deleted tree; the copy merged
into the wreckage and the *next* command reported `./qemu-mips-static: No such
file or directory`. **The message pointed nowhere near the cause.** It now
unmounts first and refuses to delete if the unmount did not take — a refusal
rather than a retry, because `rm -rf` through a live mountpoint is how a tool
deletes things outside the directory it was aimed at.

**30. The vendor's constant, copied, would have been a heap overflow.** The
encoder defaulted `comp_rate` to 7 because that is what the vendor's images
carry. It is not a format field — `libapmib` does `malloc(comp_rate * comp_len)`
and does not check — and 7 suits the vendor's 6.05× on a real configuration. An
all-zero blob compresses 8.4×, so 7 would have had the library allocate 27,279
bytes and decode 32,866 into it. Caught by a check written into the encoder
before it was ever run. **Copying the vendor's constant looked like fidelity.**

### A measurement failure, and what caught it

The first `localPin` run reported **no execution**, which would have refuted
`P3-14`. It was wrong, and the harness caused it: the script fired a *control*
request first, `boa` does not survive this handler, and the real payload went to
a dead server. Both requests returned `HTTP 000`, and the null looked exactly
like a negative result.

What caught it was refusing to accept "it did not work" without a location.
Under `-strace` the `execve` was on screen with the interpolated string in it.
**A negative result whose mechanism you cannot name is not a result yet** — and
this one was a paragraph away from being written down as the refutation of a
claim that is true.

### Deliberately not done

| Item | Why |
|---|---|
| An LD_PRELOAD unaligned-access fixup for `qemu-user` | It would let `flash default` run and give the L2 environment a real configuration. It is also a MIPS-BE cross-compilation project (`P5-4`) against uClibc, and 3a does not need it — the injection reproduces without it |
| `qemu-system-mips` with the container's own kernel | The correct fix, since the kernel is what does the fixup. RTL8196 is not a QEMU machine model, so it is a research project rather than an afternoon |
| Concluding anything about shipped defaults from this environment | Every value in the synthetic MIB is zero. It is not a configuration, and `poc/05`'s scope table says so |

### Open, carried forward

43. **Does `boa` survive `formWsc` on the *device*?** Under emulation it does
    not. W06 measured a one-request outage on a **different** handler (`D-11`).
    Whether they share a mechanism is unmeasured, and the question is sharper now
    than it was, because emulation yields a fault address and the device does not.
44. **How much of the MIB does a handler actually need?** The synthetic
    configuration is all zeros and `formWsc` ran anyway. Which handlers tolerate
    an empty MIB and which crash on it would map how much of this firmware is
    reachable from a download alone.
45. **`libapmib` has no compiled-in hardware-setting default.** `apmib_init()`
    fails hard rather than falling back, which is why a blank flash is fatal and
    why the factory programming jig is load-bearing. Whether the *software*
    defaults have a compiled-in fallback is a separate question, and `flash
    default`'s existence suggests they do.
46. **A desk procedure has no machine-checked home.** `check-runsheet.py`
    enforces "every executed test has a procedure that reaches it" by reading
    `runsheet.md` — and `runsheet.md` is the *bench* document, its four stations
    being four device states. `P0-11` and `P3-14` needed no device, so they went
    into the `no-procedure` exemption despite having a perfectly good procedure
    in `poc/05` and `REPRODUCE.md` T1. The exemption is honest but it is the
    wrong shape: it says "there is no procedure" when what is true is "the
    procedure is not in this file". The bench half is checked and the desk half
    is not, and W07 is mostly desk work — so this gets worse before it gets
    better.

---

## W07 Day 1 — the work list, computed — 2026-08-18

W07's premise is that the hunting instruments already exist and what is missing
is the arithmetic. Two numbers came out of it, and the second is the one worth
having.

### The residue: 91 sites, and none of them is command execution

`BoaGate` reports 134 findings on this unit's build. Subtract every site a
published advisory explains and **91 remain — of which zero are R2**, the rule
that means "reaches `system()`/`popen()`". Every command-execution candidate the
gate can see on this build is already accounted for by a CVE or by a finding this
project has itself withdrawn.

That is a negative result and it is worth stating plainly, because the opposite
would have been the week's headline. The residue is also less interesting than
its size suggests: **63 of the 91 are `submit-url`**, the class W06 already
measured and refuted on this build (`P4-1`, `P4-3`), and four more parameters —
`ifname`, `wlan_id`, `webpage`, `wlan-url` — are named in `P4-4`'s prediction and
were refuted with it. What is left uncharacterised is roughly a dozen parameters,
`comment` (5 sites) the most frequent.

> A correction made in the hour it was needed: `webpage` was written up here as a
> parameter nobody had ever sent, and it is not — `P4-4`'s frozen prediction
> names it explicitly. **The register caught a claim the analysis had not.**

### Islands, in both directions

A handler in `root_form[]` that no shipped page names. Computed rather than
hand-picked, and the UI side comes from the docroot the vendor's **own**
`flash extr` produced — `/web` in the extracted rootfs is a symlink to an empty
`/var/web`, so a grep over the rootfs finds nothing and would make every handler
look like an island.

| | unit-2018 | V2.1.2 |
|---|---|---|
| handlers in the dispatch table | 57 | 59 |
| named by no page | **14** | **11** |
| pages posting to a handler that does not exist | **3** | **7** |

The boring explanations are excluded mechanically: every `action=` in both
docroots is a literal `/boafrm/...`, so nothing is assembled in JavaScript where
a grep would miss it.

**W04-2 already found the interesting one by hand** — `syscmd.htm` posts to
`formSysCmd`, which V2.1.2's dispatch table does not contain
([`notes/w6cg-web-ui.md`](notes/w6cg-web-ui.md), *"the form the vendor shipped
posts to a 404"*). What is new is that it is **a pattern rather than an oddity**:
ten pages across the two builds post to handlers that do not exist, and the 2015
UI shipped a page for a handler that only appears in 2018.

And the deflation, which matters more than the count: **13 of the 14 islands take
`submit-url` and nothing else.** An island is a handler with no menu entry, not a
handler with a secret.

### `P4-7`: 39 of 57 handlers, one request each

The sweep W06 could not afford. On the device nothing respawns `boa` and recovery
is a power cycle, so 57 endpoints is a session spent almost entirely on power
cycles; under emulation the state is a file and a restart costs a second. That
trade was the argument for building the environment, and this is the first thing
to spend it.

**39 of 57 handlers stop answering after a single well-formed unauthenticated
POST carrying only `submit-url=/wireless.htm`.** 19 survive; 39 restarts, none
failed. Controls held throughout: a real handler answered and lived, a fake one
404'd.

`P4-7` predicted that the four handlers carrying CVE ids are "a sample, not the
set". Thirty-nine is not four.

> ⚠️ **This is not a claim about the device, and the tool refuses to phrase it as
> one.** The JSON field is `died_under_emulation`. `qemu-user` raises `SIGBUS` on
> unaligned accesses that the device's MIPS kernel fixes in its trap handler, so
> a handler that dies here has not been shown to die on silicon. What this is: a
> **candidate list** — and W06 measured a one-request outage on the hardware
> (`docs/disclosure.md` D-11) without being able to say which class of handler it
> belonged to.
>
> Note also that `formSysCmd`, the handler carrying the CVE, is among the
> **survivors**. "Crashes" and "is the defect" are different sets.

### Instrument bugs 28 through 36

Nine, and six are in code written today. The count is the point: a session that
builds five new instruments and finds no bugs in them has not looked.

**28. A refuted claim in the register's own header.** Recorded under W07 Day 0.

**29. `rm -rf` through a live procfs mountpoint.** Recorded under W07 Day 0.

**30. The vendor's constant, copied, would have been a heap overflow.** Recorded
under W07 Day 0.

**31. A checker defeated by its own documentation.** `check-runsheet.py` located
the `<!-- no-procedure: ... -->` block with `re.search` — first match wins — and
the appendix paragraph *explaining* that block quotes the marker inline, earlier
in the file. The real block was never read, two properly exempted cases were
reported as gaps, and the escape hatch could not be used at all. The guard suite
went 29 → 30 cases and the new case was watched failing before it was left
passing.

**32. A tool that read a third of its input and reported a whole answer.**
`bughunt.py` walked the docroot as an ordinary user, met root-owned
subdirectories that `flash extr` had created, silently skipped them, and computed
an island list from **91 of 146 files**. Every handler whose only mention lived in
an unreadable directory would have been reported as an island — a fabricated
finding manufactured by a permission error. It refuses now instead of skipping.
The island count was unchanged once fixed, which is luck rather than a defence.

**33. Nested `sudo` moves the work directory.** `handler-sweep.py` runs as root
and shelled out to `sudo qemu-env.sh`; `sudo` from root sets `SUDO_USER=root`, so
`$WORK` resolved to `/root/fwre-work` and every restart failed with *"no
/var/boa.conf; run build"* — sending the operator to rebuild an environment that
was perfectly fine. Fifty-five times. Instrument bug 24's lesson exactly: **a
failure that names the wrong fix is worse than no message at all.**

**34. The pidfile held the wrong pid, and the control could not tell.** `boa`
daemonises, so the pid the shell returns is the launcher's while the process
holding the socket is its child. `stop` had **always** killed the launcher,
reported success, and left the server running — harmless in short sessions, and
across one 58-handler sweep it produced **32 orphans** with the port held by an
arbitrary old one. Every probe after the first crash was answered by a server
carrying state from earlier in the run.

> **And `serve`'s control passed the entire time**, because it verified that
> *something* on the port served an exempt page and redirected a gated one. That
> is a property of the port, not of the process it started, and those are
> different claims. It now checks `/proc/<listener>/root` against the profile's
> own environment directory, and the pidfile holds the pid that owns the socket.

**35. `reset` is host-global, and a second profile made that matter.** SysV shared
memory and semaphores have no namespace here, so resetting one profile destroys
the segments the other profile's running `boa` holds. That process then spins on
`APMIB Semaphore Lock semop() failed !! [Invalid argument]` and never binds. The
symptom is a `serve` that times out, which is indistinguishable from a broken
restart — and that is what it was mistaken for. `reset` now reaps its own
environment first and **refuses** while another profile still has processes.

**36. A guard that silently killed the thing it guarded.** `port_holder` ends in a
`grep` that exits non-zero when the port is *free*, which is the ordinary case;
under `set -euo pipefail` that failed the pipeline, failed the assignment, and
exited `serve` with status 1 **and no output whatsoever**. Written today to
prevent bug 34, and for an hour it was the worse bug of the two.

**Thirty-six recorded. Twenty were caught by comparing two things that should
have agreed, seven by a check written to fail, two by asking what a checker does
not read, one by an outside advisory, and six by an instrument disagreeing with
itself between two runs of the same measurement.**

### Three invalid measurements, and why they are named rather than discarded

The `P4-7` sweep ran four times. The first three produced confident,
well-formatted, entirely worthless output — 1 of 58, then 31 of 58 with five
handlers returning `404` that had answered `302` an hour earlier, then 18 of 58.
Only the fourth is real.

They are in the record because **each of them looked exactly like data.** The
tell was never the numbers, which were plausible throughout; it was that two runs
of the same measurement disagreed about `formSysCmd`. A result that cannot be
obtained twice is not a result, and this repository's own rule — no claim from a
single tool — turns out to have a sibling: no claim from a single *run*.

### Deliberately not done

| Item | Why |
|---|---|
| Firing the 39 at the device | Each crash costs a power cycle. A *sample* chosen from the list is the right bench task, and this session was ended before hardware on purpose |
| The differential harness across five builds | `mkflash` makes it possible now: a V3.4.0 profile is a few lines. It is W07 Day 2 and it wants a clean session |
| `bughunt.md` | The week's DoD document. Its judgement column is worth writing once the bench results exist, not before |
| Everything needing RF or an SPI programmer | `P7-*` and `P9-5`…`P9-12`. Rescheduled to W08 with the instrument named against each — see [`docs/lab-inventory.md`](docs/lab-inventory.md) |

### Open, carried forward

47. **Do any of the 39 die on silicon?** The most valuable question this session
    produced, and it needs the device. `formWsc` is the first pick: it dies under
    emulation on both profiles, and W06 fired it at the hardware without
    recording whether the server survived.
48. **`comment`, five sites, uncharacterised.** The most frequent parameter in the
    residue that no prediction has ever named.
49. **Ten pages posting to handlers that do not exist**, across two builds. W04-2
    explained one. Whether the rest are UI-ahead-of-code, code-removed-under-UI,
    or shared-across-models has not been asked.

### Where W07 stands, and what the next session does first

The register reads **W07 2 of 56** — `P4-7` and `P8-15`. Fifteen cases moved to
W08 with the missing instrument named against each; `docs/lab-inventory.md` is
the shopping list and its recommendation is about US$40 for the two that matter.

> This paragraph named `P0-9` instead of `P8-15` when it was written, and
> `P0-9`'s `week` field says `W06`. Corrected 2026-08-18 from the register,
> which owns the field. The count was right and one of the two ids was not —
> which is what restating a register row into prose does, and why the rule says
> cite rather than restate.

Nothing below needs re-deriving. In order:

| Next | Needs the device? | Where it picks up |
|---|---|---|
| **1. A sample of the 39 at the device** | ✅ **yes** | `reports/handler-sweep-unit-2018.json` is the candidate list. Pick 3–4, not 39 — each crash is a power cycle. `formWsc` first (open #47). This is what settles whether the sweep transfers, and it answers `D-11` / open #37 |
| **2. The differential harness, W07 Day 2** | ❌ | `qemu-env.sh` already takes profiles and `mkflash` builds a flash from any container. A V3.4.0 profile is a few lines; then the same input goes to three builds and the divergences are the work list. `reports/bughunt.json` already holds 81 sites present in some builds and not others |
| **3. `P5-6`, then the `P4`/`P5` block** | ❌ | The reschedule reasons say `P5-6` leads that block because it is the screening tool. The environment it needed now exists on two profiles |
| **4. The network block** | ✅ **yes** | `P6-*`, `P8` network, `P1-7`, `P1-11`, `P2-10` — about 18 cases, one bench visit, station order per `runsheet.md` Part A |
| **5. `bughunt.md`** | — | W07's DoD. Deliberately last: its judgement column is worth writing once 1 and 4 have run, not before |

Two things a fresh session should not have to rediscover:

- **`sudo tools/qemu-env.sh --profile <p> reap` between measurements.** `boa`
  daemonises and does not survive many of its own handlers; without a reap the
  orphans hold the port and answer for a server that no longer exists.
- **`FWRE_WORK` explicitly when shelling out under sudo.** Nested `sudo` sets
  `SUDO_USER=root` and moves the work directory to `/root`.
