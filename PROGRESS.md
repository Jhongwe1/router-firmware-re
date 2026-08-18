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

---

## W07 Day 2 — the desk half, and a bypass that needs no credentials — 2026-08-18

A session with no hardware in it at all, by choice: the bench block moved to the
next sitting so that every prediction it will test could be frozen first. Eleven
of W07's fifty-seven register rows are now closed, up from two, and **none of the
work below required the device**.

### `P2-9` — the Basic-auth path has a second credential pair, and nothing writes it

`process_header_end` compares supplied credentials against **two** pairs of stack
buffers. The real one is `apmib_get(0xb6)` / `apmib_get(0xb7)` into `sp+0x58` and
`sp+0x78`, compared at `0x0040bdb8` and `0x0040be00`, granting `req->0xb0 = 1`.
The other is `sp+0x18` and `sp+0x38`, compared **first** at `0x0040bd48` and
`0x0040bd90`, granting `req->0xb0 = 2` — a higher level.

Across all 1,964 bytes of that function the only instructions touching those two
offsets are three reads. No `sw`, `sb`, `sh`, no `apmib_get`, no `strcpy`.

With the stored credentials at `admin` / `admin` — both non-empty, read back
through the vendor's own `/bin/flash` in the same run — a `Basic` header whose
username and password are **both empty** returns 200 and 333 bytes on a gated
page, byte-identical to the real credentials, while no header, an empty user with
a password, a user with an empty password, a wrong pair, and `admin` with a wrong
password all return 302. `/password.htm` goes from 302 to 200 with 5,332 bytes of
real HTML.

**It reproduces on the published V2.1.2 image** — a different `boa`, five years
older, flash rebuilt by `mkflash`, no dump involved. **And V3.4.0 removed it**:
`FUN_00409fd8` has one comparison, both halves filled by `apmib_get` immediately
above, and no second level.

> ⚠️ **Emulated, on two profiles but one emulator.** The buffers are almost
> certainly zero for a structural reason — `process_header_end` has the deepest
> frame in the request path and Linux hands out zero-filled stack pages — but
> that is a mechanism story, not a measurement. Device confirmation is three
> requests and no power cycle, and it is the first item of the next bench visit.
> **Prior art has not been searched.** Until it has, this is "found here", not
> "new", and nothing goes to anyone.

W03 saw the same shape in V2.1.2 at `sp+0x40` / `sp+0x60` and correctly refused
to call it a finding. What was wrong was not the caution: the candidate then sat
for weeks while an environment able to fire it was built for an unrelated
purpose, and nobody pointed it here.
→ [`uninit-credential-pair.md`](notes/uninit-credential-pair.md)

### The firmware upgrade path checks a 16-bit sum, and the trigger is outside the gate

`UpgradeByData` at `0x00460798` is 1,608 bytes and the whole acceptance is a
4-byte tag `memcmp` — `cr6c`, `w6cg`, `r6cr` — plus a checksum: `FUN_00460600`
at `0x00460a98` sums big-endian halfwords and requires zero, `FUN_00460690` at
`0x00460aec` sums bytes and requires zero. **No signature, no `hw_version`, no
anti-rollback**, and `strings` over the whole binary has no match for any of
them. `form_formUpload` passes the model string `TOTOLINK-N150RT-V2.1.0` — older
than, and different from, the version this unit reports.

`/bin/batchRemoteUpgrade`, 15 KB and never read by this project, fetches firmware
over **plain HTTP**. The same job is inside `boa`: `FUN_0044f7b4`, reached from
`form_formSaveConfig`, reads `submit_rfw_check` / `submit_rfw_download` /
`submit_rfw_upgrade` and calls `CheckRFW` with the hard-coded host
`sl.totolink.software`. `POST /boafrm/formSaveConfig` does not enter the gate on
this build.
→ [`firmware-upgrade-path.md`](notes/firmware-upgrade-path.md)

### `check_host` is correct code that nothing calls

It exists at `0x00410470`, it is strict, and its verdict **is** enforced —
`process_header_end` tests it at `0x0040bca4` and a failure reaches
`send_r_bad_request`. And it never runs: `0x0040bbec` branches past the entire
host block when `vhost_root` is NULL, landing on the same label the success path
uses, and `VHostRoot` is commented out in both `/etc/boa/boa.conf.bak` line 150
and the runtime `/var/boa.conf`. **Seventeen `Host` values, nine of which
`check_host` would reject — empty, 300 characters, spaces, underscores,
punctuation — all returned 200.**

Separately: the client's `Host` is copied verbatim into the gate's redirect
`Location`, an unauthenticated open redirect on every gated path. **It is not
XSS** — both sinks encode, URL-encoding in the header and HTML entities in the
body — and saying so is the point.
→ [`host-header-and-redirect.md`](notes/host-header-and-redirect.md)

### The three unread binaries, and one was not what four weeks of notes assumed

| | |
|---|---|
| `/bin/auth` | **the 802.1X / WPA authenticator**, not a credential checker — `RTLAuthenticator`, `lib1x_do_authenticator`, `lib1x_control_STA_SetGTK`, `libnet_*`. W01 called it "the likely credential check"; W04 filed it "off the critical path". W04's conclusion was right and its reasoning was luck. It is the daemon W08's `P7-5` and `P7-6` attack |
| `/bin/miniigd` | behind **52869/tcp**, which `P1-2` found open and no prediction had mentioned. `FUN_004083a8` parses five SOAP values and puts them into `sprintf("echo \"%s,%s,%s,%s,NA,%s\" >> %s")` then `system()` at `0x004085fc`, with an unbounded `strcpy` on the same path and **nothing in between**. Almost certainly CVE-2014-8361 — CISA KEV, a Mirai payload since 2015 — so the finding is "a 2018 build ships it on an open port", which is verification, not discovery |
| `/bin/dnsspoof` | 3,820 bytes, started when the WAN drops and startable by `boa`. It appends a fixed 16-byte record at `buffer + n` past a **256-byte** stack buffer, so a query of 245 bytes or more corrupts three pointers set once before the loop — one dereferenced by the next query's name scan, one a `memcpy` destination. **Bounded**: `recvfrom` caps `n` at 256 and the saved `ra` is forty bytes out of reach, so this is not a return-address overwrite |

Also corrected: this `miniigd`'s SOAP control endpoint is
`/upnp/control/WANIPConnection`. The working notes carried `miniupnpd`'s
`/upnp/control/WANIPConn1`; a bench probe of the documented path would have
returned a clean negative with the port open the whole time.
→ [`three-unread-binaries.md`](notes/three-unread-binaries.md)

### The XSS five are one omission, and the escaper is already in the binary

`boa` ships `req_write_escape_html` with an entity table for `"`, `'`, `\`, `<`
and `>`. It has **six callers** and every one is an upstream Boa status page —
403, 404, 301, 302, 411 — plus `send_redirect_perm`. **No Realtek ASP list
renderer calls it**, and `boa` carries 105 table-markup format strings whose
data-bearing ones are raw `%s`, two of them inside HTML attribute values.

So CVE-2025-3994 / 3995 / 3996 / 4460 / 4461 are five instances of one omission
across roughly thirty render functions. **Same shape as W03 turning "`.dat` files
are not restricted" into "everything without `htm` in the path"** — the second
time the difference between reading an advisory and reading the binary has been a
factor of six.

And the plan's method for this could not have worked: `dhcptbl.htm` contains no
field, only `<% dhcpClientList(); %>`. The value is written by a C function, so
grepping 146 template files would have returned nothing and proved nothing.
→ [`xss-escaping.md`](notes/xss-escaping.md)

### `P8-24` — the boot script turns telnet on when both settings regions are invalid

New register case, **frozen before the experiment**. `/bin/startup.sh` lines
19–47: `flash test-dsconf` fails **and** `flash test-csconf` fails, and the
script loads factory defaults and runs `flash set TELNET_ENABLED 1` — while
`/etc/passwd.org` has carried `root` / `123456` and `onlime_r` / `12345`, both
uid 0, unchanged since 2015.

Seven damage states measured. **The branch is entered**: with both signatures
zeroed, `startup.sh` printed its own line 23. **What it writes is not
observable** — `flash default-sw` and `flash reset1` both die on a `qemu-user`
SIGBUS, while a plain `flash set WAN_DHCP 7` in the same environment writes and
reads back, which is what makes that a statement about the recovery path rather
than the environment.

Two refinements the prediction did not have: `test-dsconf` checks the
**decompressed** header — it prints `Expect [sig=6G, ver=3, len=31878]` — and
tolerates a flipped payload byte, while `test-csconf` also runs `mib_tlv_init`
and does not, so reaching the branch needs `COMPDS`'s header damaged
specifically. And `startup.sh:25` is `eval \`flash get WLAN_BAND2G5G_SELECT\``,
which executed: the transcript shows the shell reporting `eval: line 1: Invalid:
not found` — `flash`'s own error text run as a command.

**It flips `P8-12`**, which records the config-upload chain as blocked on this
project having no `COMPCS` encoder. This path does not want a valid blob; it
wants an invalid `COMPDS`, and invalid bytes need no encoder.
→ [`config-failopen.md`](notes/config-failopen.md)

### `P8-8` and `P8-18` refuted, `P10-7` refuted, and each for a different reason

- **`P8-8`** — the playbook named three boot-script sites and all three are dead.
  `snmpd.sh` has the strongest sink, nine `eval` calls over `flash get` results,
  and **none of its nine MIB names exists in this build's table**: the recovered
  `libapmib` table has `SNMP_RO_COMMUNITY`, the script asks for
  `SNMP_ROCOMMUNITY`, and `/bin/flash` itself answers the latter with a usage
  dump. `smb.sh`/`smbbak.sh` have no `eval` — and `smbd`, `smbpasswd`, `nmbd` and
  `snmpd` are all absent from `/bin` while three scripts driving them ship.
- **`P8-18`** — `FUN_0044f360` returns an integer offset on every path.
  `filename=` is a landmark it searches past; the value is never copied.
  `formUploadConfig` is a **different** handler, still unread, and belongs to
  `P8-12`.
- **`P10-7`** — the register's premise is wrong for this unit. It ships **one**
  factory key, `/etc/dropbear_rsa_host_key`, and **no SSH daemon at all**, while
  `sysconf` still installs the key to `/var/dropbear` on every boot.

### Instrument bugs 37 through 39

**37. `qemu-env.sh reset` could not remove what `serve` deliberately creates.**
`reset` ended with `rm -f "$ENVDIR/var/web/config.dat"`, and `cmd_serve` makes
that path a **directory** — the `P0-9` trick that makes `boa`'s start-up `open()`
return `EISDIR`. `rm -f` cannot remove a directory, so after any `serve`, `reset`
returned non-zero with every restore above that line having succeeded, and the
leftover survived a reset that promises to restore both pieces of state. It had
been that way since `serve` was written; **nothing noticed because no caller had
ever checked `reset`'s exit status.**

**38. A probe that produced seven complete, plausible, empty measurements.**
`failopen-probe.sh` ran the boot script as `qemu-env.sh run /bin/startup.sh`, and
`run` executes under `qemu-mips-static`, which wants an ELF. The first working run
printed seven neatly formatted damage states in which the boot script said
nothing and changed nothing — **including the one state the probe was written to
detect.** What caught it was that the control state and the both-damaged state
produced identical output, which cannot be true if the branch exists. It now runs
`echo SHELL_RUNS` through the same path first and refuses if it does not come
back.

**39. A binary vanished from the extracted rootfs mid-read.** `bin/miniigd` was
listed and `strings`-ed successfully and twenty minutes later `cp` reported no
such file, while the copy inside the built emulation environment was still there.
Restored by re-running `unsquashfs`; the fresh extraction's SHA-256 matches the
environment copy byte for byte, so nothing measured is in doubt. **What removed
it is not known** and guessing would be worse than saying so — only `strings`,
`readelf` and a failed Ghidra import had touched that path. The lesson is not the
file: **nothing in this repository checks that the extracted tree still matches
the SquashFS it came from**, so a tree that loses a file looks exactly like one
that does not, and the extracted rootfs has been treated as evidence when it is
derived data.

That is thirty-nine recorded, and the tally by *how* they were caught is
unchanged in shape: comparing two things that should have agreed, a check written
to fail, or asking what a checker does not read. **Number 39 was caught by none of
those** — it was caught by a `cp` that failed for an unrelated reason, which is
luck, and luck is why the missing check is written down above.

### Corrections to the plan

| W07's plan says | What happened |
|---|---|
| Day 2 allots a day to standing up **six emulation profiles** for differential fuzzing | The one differential answer this week needed — does 2020 have the credential pair — came from **twenty minutes reading three binaries**. The harness is still worth building, for divergences nobody thought to look for, but the cheap version should have run first |
| Day 4: *"grep three corpora for which templates **output** that field"* | There is nothing to grep. The templates call `<% dhcpClientList(); %>`; the value is written by a C function inside `boa`. The plan's *method* — parameter → MIB field → output site — is right and is what turned five CVEs into one class; its idea of where the output site lives is wrong |
| Day 5 lists `/bin/auth` as a **credential check** worth reading for that reason | It is the 802.1X authenticator. Worth reading, for a different week |
| Day 1's residue is *"this week's work list"* | 63 of the 91 are the `submit-url` class already refuted on this build, and four more parameters are named in `P4-4`'s frozen prediction. What is left uncharacterised is about a dozen parameters |

### Deliberately not done

| Item | Why |
|---|---|
| Everything needing the device | Moved to the next sitting **on purpose**, so that the eleven register rows with no refutation condition could be written and frozen first. Writing them the night before the visit rather than after it is the entire reason the register exists |
| The `P4`/`P5` exploitation block, 9 cases | No offset measured, no `epc` shown controllable, no chain assembled. The environment exists on two profiles. Not started rather than half-done |
| The six-profile differential harness | See *Corrections*. `mkflash` makes a V3.4.0 profile cheap and its control set has to be derived from that build rather than copied — *"a profile whose control cannot fail is not a second environment, it is a second way to believe the first one"* |
| Recording the bench-blocked cases as `partial` | `P6-1`, `P6-10`, `P8-2`, `P8-19` all have a completed white-box half and a refutation condition phrased about behaviour. Recording them would mark them done in `make todo` and hide the work still owed |
| Reporting anything to anyone | Three items are candidates for being original and **none has had the per-handler prior-art search** step 2 of `docs/disclosure.md` requires. That search took one query and overturned `D-1` |

### Open, carried forward

50. **Does the empty-credential bypass fire on silicon?** Three requests, no
    power cycle. The most valuable question this session produced.
51. **Prior art for the uninitialised credential pair**, and for the `dnsspoof`
    write. Neither has been searched, and `notes/prior-art.md` has been wrong once.
52. **What `req->0xb0 = 2` buys over `= 1`.** The finding is "authenticates", not
    "authenticates as something better", and the wording stays there until this is
    read.
53. **Can the two uninitialised buffers be made to hold *chosen* bytes** rather
    than zero? That would be a different and worse thing.
54. **Which of `dnrd`, `dnsmasq`, `dns_protocl` and `dnsspoof` is bound to 53.**
    `P1-2` found 53/udp `open|filtered` and did not say by what. `P6-10` cannot
    close before this.
55. **UDP 9034 has never actually been probed over UDP.** `runsheet.md:1740` uses
    `nmap -sT`, a TCP connect scan, while `P6-4` is about CVE-2021-35394's UDP
    daemon and the W05 UDP list was ten ports that did not include it. A TCP RST
    says nothing about a UDP listener.
56. **Nothing verifies the extracted rootfs against its SquashFS.** See instrument
    bug 39.
57. **`formUploadConfig` is still unread**, and `P8-12`'s chain now has a second
    route through `P8-24` that needs no encoder.

### Where W07 stands, and what the next session does

The register reads **W07 11 of 57**. Everything remaining that does not need the
device is the `P4`/`P5` block and `P5-7`/`P8-21`/`P8-23`; everything else is the
bench.

| Next | Needs the device? | Note |
|---|---|---|
| **1. The three-request credential check** | ✅ | Empty pair, real pair, wrong password, on a gated page. No power cycle, no write. Settles `P2-9` and open #50 |
| **2. The UDP sweep that has never run** | ✅ | 9034, 20005, 9999 **over UDP**, with a known-open UDP port answering in the same sweep as the positive control. Settles `P6-4` and `P6-12`, and open #55 |
| **3. The UPnP block** | ✅ | 52869 SOAP on `/upnp/control/WANIPConnection`, 1900 SSDP, 52881 wscd. `P6-1`, `P6-2`, `P6-3`, `P8-7`, and `P8-2`'s UPnP point |
| **4. The rest of the network block, then the destructive batch** | ✅ | Read-only first, then the config-changing ones, then the handler sample, then `P8-4`, and `P9-9` **last** because it wipes the settings every other test is standing on |
| **5. `P5-6` and the `P4`/`P5` block** | ❌ | Desk work, and the screening tool leads it |
| **6. Prior-art searches** | ❌ | Before anything is reported, and it gates `D-15`, `D-16`, `D-17` |

---

## W07 Day 3 — the SDK's own source, and an emulator divergence that had been shaping results — 2026-08-18

A second desk-only session, and the two largest results both came from asking a
question the project had never asked rather than from running something harder.
**No register row was recorded**: the week still reads **W07 11 of 57**, and the
reason is in *Deliberately not done*.

### The two never-written buffers are a supervisor account, and the source that says so is public

`D-15` was *"a comparison against two stack buffers nothing writes"*. It is now
*"a feature deleted from the data and left in the control flow"*, which is a
different claim because it says what the code was **for**.

The Realtek rtl819x SDK's `boa` source is on GitHub, in **two independent GPL
drops from unrelated vendors** — neither of them TOTOLINK's. Its
`users/boa/src/request.c` fetches **four** MIB values into four buffers —
`MIB_SUPER_NAME` (180) and `MIB_SUPER_PASSWORD` (181) into `admin_name` /
`admin_password`, `MIB_USER_NAME` (182) and `MIB_USER_PASSWORD` (183) into
`user_name` / `user_password` — and compares the **SUPER** pair first, granting
`auth_flag = 2`, then the USER pair, granting `1`.

This unit's binary makes **two** of those four calls — `0xb6` and `0xb7`, into
`sp+0x58` and `sp+0x78` — and fetches 180 and 181 nowhere. So `sp+0x18` and
`sp+0x38` are `admin_name` and `admin_password` with their only initialiser
deleted.

Scanned across the family with an encoding scan that needs no symbol table:
**no build in this product line has ever fetched MIB 180 or 181.** V2.1.2, this
unit, and V3.4.0 all report zero sites. What 2020 removed is the dangling
comparison, not a working supervisor account — which is smaller and more accurate
than what W07 Day 2 recorded, and it changes what to look for in other vendors'
builds of the same SDK.

Two more things fell out of reading the source, and neither was being looked for:

- **The MIB table this project recovered from this unit's own `libapmib.so` now
  has an outside witness.** `apmib.h` gives `SUPER_NAME` 180, `SUPER_PASSWORD`
  181, `USER_NAME` 182, `USER_PASSWORD` 183; the recovered table's entries 182
  and 183 are `USER_NAME` and `USER_PASSWORD`. That table had never been checked
  against anything outside this repository.
- **`check_auth_flag` is an upstream missing-brace defect.** The source assigns a
  global alongside `req->auth_flag` with no braces, so matching only the
  *username* sets it whatever the password is, in all four arms. This binary
  compiles it faithfully — `0x0040bda8` branches unconditionally with `v1 = 2` in
  the delay slot, `0x0040be20` stores it. **It is dead here**: `0x004899d8` has
  exactly one reference in the whole 485,012-byte binary and it is that write.

> **Open #52 is settled, and the answer deflates the finding by one notch and
> inflates it by another.** `req->auth_flag` is read at two instructions, both
> inside `process_header_end`; the second, `0x0040be24` / `0x0040be2c`, branches
> to `translate_uri` on **any** non-zero value. So 2 and 1 are equivalent — the
> wording stays "authenticates", never "as an administrator" — and what the empty
> pair actually buys is that the **entire** authorisation block does not run.

→ [`uninit-credential-pair.md`](notes/uninit-credential-pair.md) §3, §4

### The gate has a third arm, it is keyed on the client's IP, and it dies 601 seconds after boot

Found by reading forty instructions past the question the listing was generated
for. After the `.htm` / `.asp` test and the eleven exempt pages,
`process_header_end` does this:

```
0040bff8  lw    v1, nowuptime           ; written at 0040be54 from sysinfo()
0040c000  lw    v0, beforeuptime
0040c008  subu  v0, v1, v0
0040c00c  sltiu v0, v0, 0x259           ; difference < 601 seconds?
0040c010  bne   v0, zero, keep
0040c018  strcpy(authipaddr, "0.0.0.0")
0040c04c  strcmp(authipaddr, req+0x4bd) ; the client's address
0040c060  beq   -> allowed
```

`authipaddr` is written by `form_formLogin` at `0x0044f13c` and cleared by
`form_formLogout` at `0x0044cd48`. **And `beforeuptime` is never written** — one
reference in the binary, the read above, confirmed by Ghidra and by an
independent encoding scan whose control in the same run returns a read *and* a
write. So the difference is the system uptime, and after ten minutes the address
is overwritten with `"0.0.0.0"` before every comparison and the arm can never
succeed again.

**Which is why this repository concluded "per-request HTTP Basic", and it was
right.** Every measurement it has ever taken was made past the ten-minute mark.
What was missing is that the reason is a bug: a session with an idle timeout
whose timer variable nobody assigns. **That is the same authoring mistake as the
supervisor pair — a comparison against a variable nothing writes — twice, in one
function.**

The consequence is a device state nobody has measured: for the first 601 seconds
of uptime, a gated page is served to whichever address logged in last, with no
credentials on the request. **The emulator cannot reach it** — `sysinfo()` under
`qemu-user` returns the host's uptime — so it needs `A3.2`, the only station that
owns the clock.
→ [`auth-session-ip.md`](notes/auth-session-ip.md), `docs/disclosure.md` `D-18`

### `P4-7`'s thirty-nine deaths were the emulator

`handler-sweep.py` reported **39 of 57 handlers dying on a single well-formed
POST**. The tool wrote `died_under_emulation` and said in as many words that it
could not turn that into a claim about the device. Attaching `gdb-multiarch` to
`qemu-mips-static`'s gdbstub and letting the fault happen answers it:

```
Program received signal SIGBUS, Bus error.
=> 0x2b2c87dc:  sh  s7,0(s8)
```

`libapmib.so + 0x27d0`, inside **`mib_write_to_raw`** — the TLV serialiser that
packs the MIB into the raw flash buffer. Variable-length records, so field
offsets are odd as a matter of routine. Linux/MIPS fixes unaligned user-space
accesses up in the kernel and the device never notices; `qemu-user` raises
SIGBUS, and `boa`'s own handler dumps core and aborts.

**So the 39 are the handlers that reach the config serialiser, and the 19
"survivors" are the ones that bail out early because the probe body carried only
`submit-url`.** `formSysCmd` being among the survivors stops being a curiosity.

`tools/alignfix/` removes the divergence — a freestanding MIPS-BE `LD_PRELOAD`
shim, raw syscalls, no libc dependency, which decodes the faulting
`lh`/`lhu`/`sh`/`lw`/`sw` and performs it a byte at a time, and interposes
`sigaction` / `signal` so `boa` cannot take SIGBUS back. With it loaded `formNtp`
returns **302 and the server survives**, and the log shows **24 fix-ups, all at
one pc, every address odd**.

**It also explains `P8-24`.** That row records the fail-open recovery write as
"not observable, because `flash default-sw` dies on a `qemu-user` SIGBUS". Same
binary path, same cause. **Two separately-recorded observations were one bug.**

**And the re-run, with a pristine flash before every probe, gives the number this
week's method was supposed to produce.** 58 handlers probed, 58 restarts, **0
failed, 57 survived, and exactly one died: `formSchedule`.** All three controls
held, and the post-sweep `env_intact_after_sweep` check passed — so no probe left
state behind, which is bug 41's fix proving itself in the same run that needed it.

> 🏆 **`D-11` measured on the hardware that *one* unauthenticated, well-formed
> POST removes the web server until a power cycle, and could not say which
> handler it belonged to.** The emulated list was thirty-nine, which is not a
> lead. It is now **one, named** — and the device measurement and the emulated
> candidate now agree on both shape and count. The bench sample that open #47
> asks for has an obvious first pick instead of a lottery.

`bughunt.md` row 16 is rewritten rather than simply withdrawn: the original claim
was a property of the emulator, and correcting the emulator did not delete the
finding, it **sharpened it by a factor of thirty-nine**. That is the third of this
project's own results to be overturned, and the first overturned by building an
instrument that could tell the emulator from the firmware rather than by arguing
about a caveat the report already carried.
→ [`emulation-2018.md`](notes/emulation-2018.md) §7a ·
[`reports/handler-sweep-unit-2018-alignfix.json`](reports/handler-sweep-unit-2018-alignfix.json)

### Prior art: three searched, one matched, and the method that found the most was new

| | outcome |
|---|---|
| `D-15` | **nothing**, searched four ways. Talos's fifteen rtl819x reports contain no authentication defect of any kind; CVE-2007-4915 is the same function with the opposite mechanism |
| `D-17`, the `dnsspoof` write | **nothing**, searched by behaviour because the binary name collides with dsniff's tool |
| `D-12`, image-validation half | **matched — CVE-2023-34435 / TALOS-2023-1874**, CWE-347, on this SDK. `bughunt.md` row 13 is not this project's finding. What survives is narrower and better: *which* check exists and at what address |
| `D-12`, plain-HTTP fetch half | **nothing**, searched by domain, by symbol and by binary name |

**And one found while looking for something else:** CVE-2023-47677 reports CSRF
on this SDK's `boa`. `P8-3` and `P8-4`'s frozen predictions say there is no CSRF
protection; a published advisory says there is one and that it is bypassable.
Their results will have to cite it rather than read as discoveries. The mechanism
Talos describes is not the one in this binary, and that is said rather than
resolved.

> **The method result is the one to keep.** `docs/disclosure.md` step 2 says
> search by *handler*, because `D-1`'s search by product found nothing and by
> handler found Talos on the first page. That was still too narrow. **Searching
> by *symbol* finds source.** Step 2a now says so.

### Instrument work

- **`tools/alignfix/`** — the shim above, plus `build.sh`, which checks the
  object is big-endian MIPS32 with an init entry and no undefined symbols before
  it says "built". That check is `P5-4`'s refutation condition mechanised.
- **`tools/test-alignfix.sh`**, 8 cases, in `make ci` as `alignfix-test`. It
  builds a deliberately mis-offset shim to prove the refusal path is reachable,
  points the build's architecture checks at a host x86-64 object to prove they
  discriminate, and asserts the flag is still **off by default** — because a
  future edit that turned it on silently would make every pre-2026-08-18
  emulated measurement incomparable without anyone noticing.
- **`tools/mipsref.py`** — "who references this address", from instruction
  encodings alone: no symbol table, no analysis database, no reference model, so
  it is genuinely independent of Ghidra. Three addressing forms, because missing
  one looks exactly like a clean answer, and `gp` comes from the ELF's own
  `DT_PLTGOT + 0x7ff0` rather than from Ghidra. `--control` names an address that
  **must** come back with a read and a write, else it exits 2. `--segments`
  answers the RELRO / NX / GOT question as a second source: the GOT sits in a
  `RW-` PT_LOAD, there is no `PT_GNU_RELRO`, and `GNU_STACK` is `RWX` — in all
  three builds, which is `P5-3`'s static half and part of `P5-7`'s.
- **`gdb-multiarch` and the MIPS-BE cross toolchain** are installed, in
  `setup-wsl.sh`, and verified by `make verify` — including
  `mips-linux-gnu-objdump`, because `mipsel` compiles the same source just as
  happily and produces something the SoC will not run.
- `handler-sweep.py` gained `--alignfix` and `--reset-each`, and a post-sweep
  control that re-runs the profile's own `check`.

### Instrument bugs 40 through 43 — 41 and 42 were created by fixing 40, and 43 was found by asking GitHub

**40. The emulation environment could not execute a single configuration write,
and nothing said so.** Not a wrong answer — a missing capability that looked like
a result. Every handler that saved settings appeared to crash, `P8-24`'s recovery
write appeared unobservable, and both were recorded as bounded observations with
honest caveats. The caveats were right and they were not enough: **a limit
described in prose next to each affected result is not the same as a limit the
environment declares once.** `serve` now prints its alignment mode on every start.

**41. Removing the crash removed a guarantee that was resting on it.** With
`--alignfix` the handlers no longer die, so the restart no longer happens, so the
`reset` inside the restart no longer happens — and probe *N* began reading what
probes 1..N-1 had written. The sweep's per-probe pristine flash had never been an
intended property; it was the crash doing it by accident. Caught within one run
by the environment's own positive control returning `USER_NAME=""` instead of
`"admin"`.

**42. `reset` restores the flash and the SysV segments and does not restore
`/var`.** Once handlers could write, one of them re-ran the
`cp -a /etc/boa/boa.conf.bak /var/boa.conf` half of `sysconf`'s job **without**
the `echo 'Port 80' >>` that `build` appends. The runtime config went back to the
upstream sample, in which `Port` is commented out, so `serve`'s
`sed s/^Port .*/` matched nothing and `boa` bound port 0. Every probe afterwards
timed out **while the environment reported itself healthy** — `check` passed all
three controls, because the flash really was fine. Two sweeps were lost to it
before the log line `boa: starting server pid=…, port 0` was read closely enough.

**43. `make ci` and the GitHub workflow were two lists both calling themselves
"everything CI checks", and neither contained the other.** Found by the author
asking `gh` whether the push had actually landed. It had; the branch was green
locally and **red on GitHub**, twice.

- **Missing locally:** the ledger check. `test-ledger.md` is generated from the
  register, the workflow re-renders it and fails on a diff, and `make ci` did
  not. The staleness it caught was **not from this session** — the previous one
  recorded `P8-1`'s result and never re-rendered, so the committed ledger had
  said `W07 10/57` and `已執行 62` since then. Nothing local could see it.
- **Missing remotely:** `test-failopen-probe.sh` and `test-alignfix.sh` — one
  added last session, one added today, both wired into `make ci` and neither into
  the workflow. So the two newest guard suites had never run on a push.

`make ci` now has `check-ledger`, doing exactly what the workflow does, and the
workflow now runs both suites — with an `apt-get` for the MIPS cross-compiler,
because a suite that skips cannot prove a little-endian object would be rejected.

> **This is the third time this exact divergence has been recorded**, and the
> bench-guards job's own header says so in as many words: *"local green has to
> mean CI green, or running the local check stops being a check."* It was
> written into the file that then diverged again. **A comment is not a checker**,
> and the honest statement is that the two lists still have no machine keeping
> them equal — the fix was to make them equal by hand, which is the same fix
> that failed twice before.

That is forty-three recorded. **Three of the last four were created by this
project**, two of them in this session, and each was caught by something that
already existed: 41 by the profile's own value check, 42 by a server that would
not answer, 43 by `gh run list`. The lesson 40–42 share is one sentence — *a
restore is only as good as the list of things it restores, and that list is never
revisited until something starts writing* — and 43 adds a second: **a list that
describes another list, in prose, drifts from it.**

### Corrections to the plan

| W07's plan says | What happened |
|---|---|
| Day 2's differential fuzzing stands up six emulation profiles | Still not built, and the reason has grown: the two differential answers needed this week came from an encoding scan of three binaries. **But `--alignfix` changes the case for it** — before today no profile could execute a config write, so a differential harness would have compared three environments that all stopped at the same instruction |
| Day 1 treats the gate as `.htm` / `.asp` plus an exemption list | There is a **third arm**, and it had been read past three times |
| The scan list is "the CI gate's own output, the islands, the blank areas" | The productive fifth source was **the vendor's SDK source**, public the whole time, and nothing in the plan or in `docs/disclosure.md` said to look for it |

### Deliberately not done

| Item | Why |
|---|---|
| **Recording any register result** | The `P4` / `P5` block's input — the re-run sweep with `--alignfix` — landed in the session's last minutes, after two interruptions by bugs 41 and 42, and there was no time left to run the block it feeds. Recording `P5-3`, `P5-7`, `P1-9` and the `P3-8`…`P3-12` static halves without it would split one afternoon across two commits and put half a week's results in before the other half was measured. **The sweep artefact is committed**; nothing is recorded against it yet |
| Everything needing the device | 32 rows, one visit, and **three of its predictions did not exist this morning**: the empty-pair bypass on silicon, the 601-second window, and whether the 39 survive on silicon — which now has a mechanism behind it rather than a coin flip. Freezing them before the visit is the whole reason the register exists, and W07 Day 2 was a desk-only session for exactly this reason |
| The V3.4.0 emulation profile | Started and stopped deliberately. Its COMPDS length **must** be derived from V3.4.0's own `libapmib` — the 32858 in `mkflash` is V2.1.2's library's statement about itself — and copying it would produce "a second way to believe the first environment" |
| Reporting anything to anyone | `D-15` and `D-18` are the two most serious items in the register and both are static or emulated |

### Open, carried forward

58. **Nothing has ever entered the 601-second window.** The device has a
    different authorisation state for the first ten minutes after every boot and
    no measurement in this repository describes it. The emulator cannot reach it.
59. **Can an attacker install their own address as `authipaddr` during that
    window?** `formLogin` is one of the eleven exempt strings, so the gate does
    not stop the request reaching the handler. Untraced.
60. **`aspvar_dhcpCloneMacList` reads `authipaddr` twice** (`0x0041387c`,
    `0x00413894`) and nothing explains why a page renderer needs the authorised
    client's address.
61. **The fix-up count is a new number with no reference.** Twenty-four unaligned
    stores for one `formNtp` POST is a measurement of `libapmib`'s serialiser, and
    nothing says what it should be. A count that changed between builds, or
    between handlers, would mean something — and there is no baseline to notice
    it against.
62. **What else does `reset` not restore?** Bug 42 was found by a symptom. The
    list of state the environment holds outside the flash image has never been
    enumerated, and `/var` is where the runtime config, the document root and the
    pid files all live.

### Where W07 stands, and what the next session does first

The register still reads **W07 11 of 57**. The desk block is roughly two-thirds
measured and none of it is recorded; the bench block has not started.

| Next | Needs the device? | Note |
|---|---|---|
| **1. ~~Finish the `--alignfix` sweep~~** | ❌ | **Done, at the end of the session.** 58 probed, 58 restarts, **0 failed, 57 survived, one died: `formSchedule`.** All three controls held and `env_intact_after_sweep` is true, so no probe left state behind — which is bug 41's fix proving itself. The emulated candidate list for `D-11` is now **one handler instead of thirty-nine**, and it is computed rather than chosen. → [`reports/handler-sweep-unit-2018-alignfix.json`](reports/handler-sweep-unit-2018-alignfix.json) |
| **2. Record the desk block** | ❌ | `P1-9`, the `P3-8`…`P3-12` static halves, `P5-3`, `P5-7`, `P5-6`, then the `P4` / `P5` chain. `P4-7` now has a second, better result to record against it |
| **3. Freeze the bench predictions** | ❌ | Three are new as of today, and one — the 601-second window — has no runsheet step at all. **This gates the visit** |
| **4. The bench visit** | ✅ | 32 rows, station order per `runsheet.md` Part B `B-W07`, `P9-9` last |

## W07 Day 4 — the refutation that inherited a coverage nobody wrote down — 2026-08-18

**Register: W07 goes 11/58 → 28/58.** Every row closed today is desk work; the
bench visit still has not happened. One case is new (`P2-11`) and one frozen
prediction was edited before firing (`P4-9`), both with the hash changed in the
same commit.

### The result: `P4-1` was refuted correctly, and the class is alive

W06 measured, on the device, that omitting `submit-url` from a POST to `formNtp`,
`formWlanSetup` and `formSelLang` does nothing. `P4-1` went down `refuted` and
`bughunt.md` row 18 wrote the class off. **That measurement stands and the
conclusion drawn from it does not.**

With `tools/alignfix/` making configuration writes executable at last, the sweep
was re-run with an **empty body** instead of a well-formed `submit-url`:
**five of 58 handlers remove the web server** — `formSchedule`,
`formAdvanceSetup`, `formDnsv6`, `formOpMode2`, `formSSH` — against three
controls that held. `tools/crash-triage.py`, written today, then put a number on
each of them by driving `qemu-user`'s gdbstub instead of reading a log:

| | |
|---|---|
| all five | `pc = 0x2b32721c` (uClibc `strcpy`), `sb v1,0(a2)`, store target **`0x004725d0`** |
| `0x004725d0` | the pooled `""` literal — **815** `addiu` references, and it lives inside the `R-X` `PT_LOAD` (`0x00400000`–`0x00473044`) |
| five distinct `ra` | `0x00445974` `0x0044740c` `0x00459f4c` `0x00452814` `0x004546bc` — five call sites, one defect |

**The control is the part worth keeping.** Send `webpage=` — *present and
empty*. Same branch, `*s2` still `'\0'`, `strcpy` still runs, **server
survives**. The only difference is where the pointer points. So the finding is
not "this handler crashes"; it is *the accessor's default for an absent
parameter is the address of a literal, and the code writes through it*.

**Why W06 could not have found it.** 47 of 57 handlers carry the idiom and only
**5** reach it on a parameter-free POST; the other 42 return earlier. Three
handlers drawn from 47 had roughly one chance in four each. And the fifth,
`formSchedule`, was unreachable by that method at all — **its parameter is
`webpage`, so it dies with a perfectly well-formed `submit-url` present.**

> **This is the third of this project's own results overturned, and the first
> overturned by widening the sample rather than by fixing an instrument.** The
> transferable sentence is not "the earlier test was sloppy". It is: **a
> refutation inherits the coverage of whatever produced it, and three
> hand-picked handlers is a coverage nobody wrote down.**
→ [`notes/absent-parameter-strcpy.md`](notes/absent-parameter-strcpy.md)

### And one that is a different defect entirely

The length ladder — the same run, a different dimension — found `form_formWsc`'s
`localPin` dying at 800 bytes and surviving at 260. A de Bruijn pattern read the
frame straight off:

```
localPin = 800 x 'A'   ->   pc = ra = s0..s6 = 0x41414141
offsets:  s0 481 · s1 485 · s2 489 · s3 493 · s4 497 · s5 501 · s6 505 · ra 509
```

509 is consistent with `BoaGate`'s own `sp-540` for that parameter. No canary,
no `PT_GNU_RELRO`, no PIE, `RWX` `GNU_STACK`, in all three N150RT builds.
**Unauthenticated, one POST, no chain: the program counter and seven saved
registers are attacker-controlled — under emulation.**

Nothing has been jumped to, no payload exists, `qemu-user`'s address space is
not the device's, and whether an overflow on `localPin` is already published has
**not been searched**. The request itself is not in this repository; it is in
`$FWRE_WORK/disclosure/`, under the same rule as `D-15`.

### The dispatch table has a second source, and it changed a sentence

`root_form[]` decided what "the attack surface" means in every week so far, and
until today it had exactly **one** producer. These binaries are `sstrip`'d —
`readelf -S` returns nothing — so no standard tool could cross-read it.

`tools/formtable-scan.py` reads program headers and looks for the *shape* of the
table in the writable segment: no decompiler, no analysis database, no symbol
table. On this unit it recovers **57 of 57, at the same address, with zero
disagreement** against the Ghidra report.

The author downloaded three sibling images this afternoon, so the scan ran on
six builds:

| 2015-08 N150RT | 2016-05 N300RT | 2017-11 this unit | 2018-03 N200RE | 2019-03 N300RT | 2020-10 N150RT |
|---|---|---|---|---|---|
| 59 | 61 | **57** | 60 | 50 | 49 |

- **This unit's 57 are a strict subset of N300RT V2.1.6's 61**, and of N200RE
  V3.2.0's 60. `P8-21` asked whether CVE-2024-51228's six products are one
  codebase; "strict subset" is a stronger answer than "different".
- **`formSysCmd` is absent from V2.1.2 (2015), present in 2016/2017/2018, still
  present in N300RT V3.4.0-B20190315, and absent from N150RT V3.4.0-B20201030.**
  So *"3.4.0 removed it"* is false as stated — the removal is **per product**,
  and only six builds side by side show it. `bughunt.md` row 22.

> ⚠️ **The method is validated on one build and assumed on five.** `--compare`
> proves it against Ghidra on `unit-2018`; the other five have no reference. The
> only indirect evidence is the subset relation itself — a scanner that
> truncated tables would produce scattered gaps, not a clean subset. **That is
> not a proof and the claim carries the sentence.**

### Instrument work

- **`tools/crash-triage.py`** — signal, registers, faulting instruction, and the
  store target classified against the binary's own program headers. Refuses to
  run without a control. Two costs paid to write it: `boa` daemonises, so gdb
  followed a parent that exits (`-d` fixes it, and the flag is in the binary's
  own usage string); and SIGBUS must be passed through, because with
  `--alignfix` the firmware takes dozens per configuration write by design.
- **`tools/paramfuzz.py`** — four dimensions, input set computed from
  `BoaGate`'s own findings. The `absent` dimension is the one that pays and it
  is new: a length ladder cannot find a value that is *missing*.
- **`tools/formtable-scan.py`** — above. `--expect` names a symbol that must be
  found, so a wrong stride or a wrong image base exits 2 instead of returning a
  confident empty answer.
- **`tools/bench-probe.py`'s POST guard was keyed on the wrong thing.** It
  refuses a POST without `submit-url`, citing this exact mechanism — and
  `formSchedule` reads `webpage`, so the one handler that most needed the guard
  went through it. Now a per-handler map.
- **`tools/check-runsheet.py`** gained the rule below, and `tools/qemu-env.sh`
  had its environment check moved above the `--alignfix` block.

### The runsheet had never been written before a session, and nothing could say so

The coverage rule added on 2026-08-17 keys on `executed`. So a row acquires a
result, and *only then* does anything demand a procedure for it. Measured today:

| week | live | executed | claimed by a step | exempted | **gap** |
|---|---|---|---|---|---|
| W05 | 27 | 27 | 27 | 0 | 0 |
| W06 | 20 | 20 | 18 | 2 | 0 |
| **W07** | **58** | **11** | **2** | 11 | **47** |

**W05 and W06 read as covered because they are finished. W07 read as covered
because it had not started** — and 32 of those 47 were scheduled for a bench
visit the same evening, including `P2-11`, whose own bench plan says in as many
words that it has no procedure and cannot be improvised on the night.

`check-runsheet.py` now applies the same rule one step earlier: every **live**
row scheduled for a week the runsheet claims to cover needs a step or a written
reason, whether or not it has run. Part B is append-only, so adding a `## B-W0N`
block is the act that turns the requirement on for that week and it cannot be
quietly turned off. It fired on all 47; **all 47 now have a step** — five new
desktop sections (`A1.5`–`A1.9`) and eleven new bench sections
(`A3.14`–`A3.24`), each paired one-to-one with a new `RUNBOOK` §8.12.x.

> **Back-filling a runsheet is not the same document as following one, and only
> the second kind can be wrong in a way you find out about in time.**

### Instrument bug 44 — the refusal that knew the answer fired second

A probe matrix wrapped in its own `sudo` produced seven rows of "the server did
not answer" and nothing else. The cause is the documented nested-`sudo` trap:
`SUDO_USER` becomes `root`, `$WORK` moves to `/root/fwre-work`, and the
environment is not there. **`qemu-env.sh` says exactly that — one check below the
one that fires.** The `--alignfix` block runs first, finds no `alignfix.so` under
a directory that does not exist, tries to build one there, and dies with
*"alignfix: build failed. Run it directly to see why"*. Running it directly
writes to `/tmp` and **succeeds**, which confirms the wrong diagnosis.

The first hypothesis it suggested — `ETXTBSY` on a mapped `alignfix.so` — was
tested and **refuted** before the real cause was found: the build succeeds while
`boa` is running. The environment check now runs first.

> **When two refusals can fire for the same cause, the one that names the cause
> has to be the one that fires.**

### Corrections to the register, both made before anything was sent

| | |
|---|---|
| **`P4-9`'s `refute` was replaced** | It named "P4-3's known crash" as the positive control. P4-3 is `refuted` on this build — `formNtp` echoes `submit-url` into `Location`, 800 bytes come back as 799, no crash at any length. **The control did not exist**, so the second clause was permanently true and the whole condition degraded into "zero crashes means the harness is broken" — which reads a correct negative result as an instrument failure. Replaced with `formSchedule`, which is measured. `[freeze].sha256` changed in the same commit |
| **`P2-11` is new** | The 601-second IP session window. Frozen **before** the visit that is the only thing able to answer it, with the emulator excluded inside the refutation rather than left as an option, because `qemu-user`'s `sysinfo()` returns the host's uptime. Its refutation runs in two directions and the second accuses this project's own instruments |

### Deliberately not done

| Item | Why |
|---|---|
| **The V2.1.2 reproduction of the `formWsc` overflow** | Started and it did not run: `reset` refused because a leftover guest process from the `unit-2018` profile was still alive, which is the tool being right. **This is the single most valuable outstanding desk measurement** — it decides whether the finding is reproducible by anyone or only on a build nobody can download |
| **`P8-23`, the settings-region differential** | `A1.9` is written and was not executed. It is the first row this environment can answer that it never could before |
| **`P5-2` ret2libc** | It needs the libc base to be stable across restarts, and the honest version of that question is about the device, not about `qemu-user`'s mmap layout |
| **Any prior-art search for the two new findings** | `docs/disclosure.md` step 2 requires it before anything is reported, and nothing is being reported. **CVE-2019-19824 names `localPin` for command injection; whether an overflow on it is published is unknown and must not be assumed either way** |
| **Reporting anything to anyone** | Both new findings are emulated. The rule has not moved |

### Open, carried forward

63. **Does the `formWsc` overflow reproduce on the published V2.1.2 image?** If
    it does, this is the first memory-corruption finding here that a reader can
    check without owning the hardware. `tools/crash-triage.py --profile v2.1.2`
    is written and has not been run.
64. **Is the `localPin` overflow already published?** Not searched. The
    parameter is famous for a different defect, which is exactly the shape that
    produced the `CVE-2023-34435` correction three days ago.
65. **Why do 42 of the 47 handlers carrying the idiom return before reaching
    it?** The five that do not are `formSchedule`, `formAdvanceSetup`,
    `formDnsv6`, `formOpMode2`, `formSSH`, and nothing explains what they have in
    common beyond "no early return".
66. **`formtable-scan.py` is validated on one build of six.** The other five
    have no independent reference at all.
67. **`formSysCmd` is absent from the 2015 build and present from 2016.** It was
    *added*, and nothing here says why or by whom.

### Where W07 stands, and what the next session does first

| Next | Needs the device? | Note |
|---|---|---|
| **1. `A1.7.2` on the `v2.1.2` profile** | ❌ | Open #63. `sudo tools/qemu-env.sh --profile 2018 reap` first — that is what stopped it |
| **2. `A1.9`** | ❌ | `P8-23`, and it is the first thing `--alignfix` made possible that has not been spent |
| **3. Prior-art, per handler, four ways** | ❌ | Open #64. Required by `docs/disclosure.md` step 2 before either new finding is worth a draft |
| **4. The bench visit** | ✅ | 30 rows, and **every one of them now has a written step**. Station order per `runsheet.md` Part B `B-W07` + its 2026-08-18 supplement; `A3.2` moved forward for the 601-second window; `P9-9` last |

## W07 Day 5 — the tool printed a fix its own parser rejects — 2026-08-18

**Register: W07 goes 28/58 → 29/58.** One row closed (`P8-23`), and it is the
first thing this environment could answer that it never could before. Everything
else today was either an open question being closed or an instrument being
repaired, and the repairs are the larger half.

### The measurement that did not run yesterday, and why it could not have

Yesterday's last entry says the V2.1.2 reproduction "started and it did not run:
`reset` refused because a leftover guest process from the `unit-2018` profile was
still alive, which is the tool being right". The tool was right about the
process. Everything it then said about what to do next was wrong, in two
independent ways, and together they are a closed loop:

* `cmd_reset`'s refusal derives the profile name it prints from the environment
  **directory** — `${dir##*qemu-env-}`. The directory is `qemu-env-2018`; the
  profile is `unit-2018`. So it printed `sudo tools/qemu-env.sh --profile 2018
  reap`, and the parser six hundred lines above rejects `2018` with exit 2. The
  same expression is correct for the other profile, whose directory happens to
  match its name — which is why it survived every session in which only one
  profile existed.
* Typed correctly, `reap` **exits 1, prints nothing, and kills nothing.**
  `env_pids`'s last statement was `[ "$target" = "$ENVDIR" ] && printf …`; on the
  final `/proc` entry — never a guest — the test is false, the `&&` list returns
  1, that becomes the function's status, and `set -e` ends the script at
  `pids="$(env_pids)"`, before the first `kill`.

So the reset refused, named a command that is itself refused, and the correct
spelling of that command did nothing without saying so. **Neither half is visible
in the output of a successful run** — which is the property `test-qemu-env.sh`
exists for, and the suite had no case for `reap` at all.

> **A refusal that names the fix is worth exactly what the fix is worth, and
> nothing was checking that the command it printed can be run.**

### It stayed invisible for two reasons, and the first one is embarrassing

The first guard case written for `env_pids` passed against the broken function.
It was written as `if ( set -euo pipefail; …; ); then` — and POSIX disables
`set -e` for everything in the condition of an `if`. **The test reproduced the
mechanism it was written to catch.** So does `cmd_reset`, which calls
`cmd_reap … || true` and therefore ran it with `set -e` inert: reap worked in the
one place its result was discarded, and only there.

The second reason is privilege. As an ordinary user almost every
`/proc/PID/root` is unreadable, `readlink` fails, the iteration ends on
`continue` — status 0 — and the defect does not appear at all. **It exists only
under root, and `reap` requires root.** CI is not root. The cases now stub
`readlink` and simulate the privilege rather than the situation.

Four mutants, each reverting one line, each killed by the case written for it:
the trailing `&&`, the directory-derived hint, a reversed profile map, and an
`env_pids` that reports nothing.
→ `tools/test-qemu-env.sh`, 12 cases unprivileged and 21 with the dump and root

### `chroot` is not isolation, and the host found out three times

With the deadlock cleared, the V2.1.2 run died mid-case and took the whole WSL
virtual machine with it. Three times. Each time it looked like the harness
hanging: partial output, no report written, `/tmp` empty afterwards. Memory was
never below 7 GB — the process count fell from 68 to 36 in one second, which is
an orderly shutdown, not an OOM.

Run inside `unshare --pid --fork`, under `qemu-mips-static -strace`, the guest
says it itself:

```
19 execve("/bin/sh",{"sh","-c","reboot -f",NULL})
```

`busybox reboot -f` is a bare `reboot(2)`. qemu-user hands it to the host kernel,
`qemu-env.sh` runs as root, and there was no namespace between the two. Six
controlled runs, host boot time unchanged throughout:

| profile | request | guest reaches `reboot` |
|---|---|---|
| v2.1.2 | no POST at all | no |
| v2.1.2 | empty body to `formWsc` | no |
| v2.1.2 | `formSelLang`, empty body | no |
| **v2.1.2** | **`formWsc`, `localPin=1234`** | **yes** |
| unit-2018 | no POST | no |
| unit-2018 | `formWsc`, `localPin=1234` | no — `flash write-current`, then `sysconf wlaninit wlaninterface` |

So it is the request and not a timer, and it is per build. **The 2015 build
reboots on a WPS PIN submission; the 2017 build writes 7,495 bytes to
`/dev/mtdblock0` and re-initialises the wireless interface instead.** Both are
now one entry in `tools/bench-probe.py`'s `HAZARDOUS` map, which did not carry
`formWsc` — and either outcome turns every endpoint after it in a sweep into
"connection refused", the exact false negative that file was written to prevent.

Guests now start through one function, `guest()` = `unshare --pid --fork
chroot …`. That broke `serve` immediately and correctly: `boa` daemonises, the
launcher exits, and the launcher was the namespace's init, so the kernel killed
everything else in it. `-d` keeps it in the foreground; the process holding the
socket is then the namespace's own init, so killing it takes its children with
it — which is the orphan problem the comment beside the pidfile was written about.

### Open #63: yes, and the frame is one word larger

`formWsc` is in the dispatch table of all six builds scanned and `localPin` is in
all six binaries' strings. With a clean control on the V2.1.2 profile — and
**neither `formNtp:` nor `formWsc:localPin=1234` is one there**, the first faults
and the second reboots the guest — the answer is unambiguous.

| | unit-2018 (2017-11) | v2.1.2 (2015-08) |
|---|---|---|
| `s0` … `s6` | 481 · 485 · 489 · 493 · 497 · 501 · 505 | 485 · 489 · 493 · 497 · 501 · 505 · 509 |
| **`ra`, and `$pc` is loaded from it** | **509** | **513** |
| `s7` | untouched, `0x0048bb04` | untouched, `0x00490ad4` |

Same registers saved, same order, frame one word larger on the older build. The
`unit-2018` column reproduces yesterday's numbers exactly from a separate run, so
this is also a replication of the measurement it is being compared against.
→ [`reports/crash-triage-v2.1.2-wsc.json`](reports/crash-triage-v2.1.2-wsc.json),
[`reports/crash-triage-v2.1.2-wsc-cyclic.json`](reports/crash-triage-v2.1.2-wsc-cyclic.json),
[`reports/crash-triage-unit-2018-wsc-cyclic.json`](reports/crash-triage-unit-2018-wsc-cyclic.json)

**The absent-parameter class is wider on the published image: seven handlers, not
five.** Same instruction, same verdict, different address — `0x00476418`, in
V2.1.2's `R-X` `PT_LOAD`. The two extra are `formNtp` and `formWlanSetup`, **two
of the three handlers W06 hand-picked to test the class and found clean.** They
were clean; W06 measured the 2017 build. The refutation inherited the coverage of
its handler sample *and* of its build, and widening the first was never going to
show the second.
→ [`reports/crash-triage-v2.1.2.json`](reports/crash-triage-v2.1.2.json)

### Open #64: the answer was in this repository, in two files, since W04

The question was written as "Not searched." **That was false when it was
written.** `notes/prior-art.md` has carried

> `| CVE-2025-4462 | /boafrm/formWsc → localPin | buffer overflow | §1 — the same line of code as 3987 |`

since W04, and `notes/cve-status.md` carries the same row marked 🟥 with the
sentence **"The same line of source as 3987, and identical in the 2015 image."**
Both are committed, both are linked from the README, and one of them is this
project's *prior-art register* — the file whose entire job is to answer exactly
this question.

So the failure was not a search that did not happen. It was a finding written up
without opening the register that already answered it, and then, today, an answer
looked for on the internet rather than in the repository. The internet agreed,
which is the least useful way to be right.

That changes what today's measurement is worth, and **upward, not downward**:
`cve-status.md` predicted from static reading alone that the overflow is
"identical in the 2015 image". Today it is measured on that image, with the frame
offset. **A confirmed static prediction is a better result than a rediscovered
CVE**, and it is what should have been written yesterday.

The surrounding identifiers, all already in `prior-art.md`: **CVE-2025-3987**
(command injection, the same line of source), **CVE-2025-3993** (`submit-url` at
the same handler), **CVE-2019-19824**. New today and not previously in the
register: **CVE-2026-7218** (same parameter, N300RT 3.4.0-B20250430) and
**CVE-2021-35395** as the Realtek-SDK-level name for the `submit-url` class. Both
added to `notes/prior-art.md`.

**What no search found**, in either the register or four web paths: the `(A)`
half — an *absent* parameter making the accessor return the address of a pooled
`""` literal. Every published item is the long-value case. That is a negative
search result and is recorded as one.

### The vendor shipped the mechanism as a macro, and it answers #65

The fourth prior-art path — the Realtek SDK is in other vendors' GPL drops — is
the one that paid. In `rtl819x/users/boa/src/apform.h`:

```c
#define OK_MSG(url) { \
	needReboot = 1; \
	if(strlen(url) == 0) \
		strcpy(url,"/wizard.htm"); \
```

`url` is what `req_get_cstream_var(wp, ("submit-url"), "")` returned. When the
parameter is absent that is the address of the `""` literal, and the macro writes
twelve bytes through it. **This is a third independent source for the mechanism —
Ghidra, the emulated fault, and now the vendor's own source** — and it sits
upstream of every handler that expands the macro rather than being a per-handler
mistake.

It also answers **#65** without another measurement. The sibling macro is
`ERR_MSG(msg)`, which takes a message and never touches `url`: a handler that
fails validation early goes down that path, and only one that reaches a
successful apply calls `OK_MSG`. That is what the 42 have in common. And the
`#else` arm of the same `#ifdef REBOOT_CHECK` has no `strcpy` at all, so whether
a build carries the defect is a **build-time flag** — a sharper prediction than
"some builds do".

The same header also shows the redirect parameter is named per handler —
`submit-url`, `webpage`, `wlan-url`, `mesh-url` — which is the map
`bench-probe.py` had to rediscover empirically yesterday.

### #67, and it is the same mistake a second time in one day

The question was "`formSysCmd` was *added*, and nothing here says why or by
whom." **`notes/formSysCmd-analysis.md` has said why since W04**: Pierre Kim's
2015-07-16 advisory names N150RT-V2 vulnerable "until last firmware
TOTOLINK-N150RT-V2.1.1-B20150708.1548", V2.1.2-B20150825 is the next build six
weeks later, and that note already draws the conclusion — *"the fix, observed"* —
and already states its own falsification: read V2.1.1's `root_form[]`.

So #67 as written was a question this repository had answered, asked again. Twice
in one day, the same shape.

What today adds is not nothing: **a second, independent source for the removal
half.** `formSysCmd-analysis.md` argued it from dates plus one decompiled table.
`formtable-scan.py` reads the table out of the program headers with no decompiler
and no analysis database, across six builds, and produces the whole sequence —
absent 2015-08, present 2016-05, 2017-11, 2018-03 and in N300RT V3.4.0-B20190315,
absent again in N150RT V3.4.0-B20201030. **The reintroduction is the half no note
carried**, and it is the half that needs explaining: a handler removed in the
release that answered a disclosure is back within nine months and then stays for
five years.

### Instrument work

- **Bug 45** — `reap` exits 1 without reaping, silently, and only under root.
  Above.
- **Bug 46** — `cmd_reset`'s refusal prints `--profile <directory suffix>`, which
  its own parser rejects for `unit-2018` and accepts for `v2.1.2`. There is now
  one reverse map, `profile_of_envdir`, and a guard case that walks every profile
  through the parser and back.
- **Bug 47** — guests ran in a `chroot`, as root, with no namespace. Above.
- **Bug 48** — `cmd_serve` reads its control codes with `code="$(curl …)"`. With
  nothing listening curl exits 7, `set -e` ends the script there, and the refusal
  written for exactly that case — the one that names `boa-emu.log` — could never
  print. `serve` exited a bare 7 and said nothing. The listening check now runs
  before the two content controls. Same shape as bug 44.
- **Bug 49** — `crash-triage.py` cleaned up with
  `pkill -f "qemu-mips-static -g 1234"`, which cannot match what the guest forks:
  children go through binfmt as `mips-binfmt-P /bin/ntp_inet`. One of those
  survived a whole session and is what blocked the reset. It now calls `reap`.
- **`tools/config-diff.py`** — new, and it is what closes `P8-23`. It drives the
  write under `--alignfix`, bounds it, and compares the decoded field tables
  rather than the flash bytes. `tools/test-config-diff.sh`, 11 cases, drives the
  comparison directly and needs neither root nor fwrecon.

### The runsheet step that was written and never run

`A1.9` was written yesterday, by the session that added a checker forbidding a
live row with no procedure. Run today, it is wrong twice:

1. **`flash set` on a COMPCS field hangs without `alignfix`.** The guest prints
   `qemu: uncaught target signal 10 (Bus error) - core dumped` and then does not
   exit. The step passed no preload and set no ceiling, so it reads as slow.
2. **It compares two coordinate systems.** `qemu-env.sh diff` reports offsets into
   the flash image, where the region is compressed — 7,478 bytes for 45,226
   decompressed. `fwrecon compcs` reports offsets into the decompressed payload.
   The first run put `0x00c060` beside "offset 91", two apart and nearly right,
   which is worse than being obviously wrong.

> **Writing the procedure before the session was necessary and is not sufficient.
> Yesterday's rule catches a row with no step. Nothing catches a step that has
> never been executed — and a step that has never been executed is a prediction
> about a command, not a command.**

### Corrections to the plan

| | |
|---|---|
| **Two of today's three "answered" open questions were already answered in this repository.** | #64 was in `notes/prior-art.md` and `notes/cve-status.md` from W04; #67 was in `notes/formSysCmd-analysis.md` from W04. Both were re-derived from outside sources today, and the first draft of this section presented both as new. Corrected in place, with what it said before quoted above, because the failure is the interesting part: **this project's own registers are not read before its findings are written.** The rule that follows is now in `docs/disclosure.md`: the prior-art step reads `notes/prior-art.md` *first*, and a web search is what you do when the register comes back empty |
| **The remote CI has not run on this branch since `067d0cc`, two commits before this session started.** | `.github/workflows/ci.yml` triggers on `push: branches: [main]` and on `pull_request`. PR #15 for `w07-bughunt` was **merged** at 06:05 today, so every push to the branch since then — including `e819596`, yesterday's tip, and all four of today's commits — has triggered **nothing**. Local `make ci` is green and that has never been the same claim. Opening a new PR is the only thing that starts a run, and it is left for the author to do rather than done here |
| **The two CI lists had diverged a fourth time**, and this time it was mine. | `tools/test-config-diff.sh`, added today, was in `make ci` and not in `.github/workflows/ci.yml`. Found by diffing the two files with a five-line script, not by noticing. Both lists now reference the same set; the script is in the session scratchpad rather than the repo, which means the fifth divergence will be found the same way |
| **`REPRODUCE.md`'s front page said 276 guard checks. It was 304 before this session and is 322 after.** | The number a stranger reads first, and nothing could re-derive it. `tools/count-checks.sh` now does, states its counting rule, and is wired to `make count-checks`; it is deliberately *not* in `make ci`, because a suite that grows should not turn the build red. Found by trying to update the figure and discovering it matched neither the old total nor the new one |
| **`CLAUDE.md` says the Chinese files were normalised to fullwidth punctuation on 2026-08-17. `RUNBOOK.md` was not, or has drifted since.** | 172 of its 3,852 lines still carry a halfwidth `,` or `:` between two CJK characters, including every section added on 2026-08-18. `runsheet.md` has 11, `LOG.md` 3, `study/QA.md` 6; `BENCH-LOG.md`'s 124 are exempt by rule. Measured, not fixed: 172 lines is not a silent edit, and there is no checker, which is why it drifted back the day after it was done. The new text added today follows the rule, which makes the boundary visible in the diff |

### Deliberately not done

| Item | Why |
|---|---|
| **The bench visit** | Not started. The desk block scheduled ahead of it is finished; the 30 rows are not |
| **`P5-2` ret2libc** | Unchanged: the honest version of the question is about the device, not `qemu-user`'s mmap layout |
| **Reporting anything** | Prior art says the class is published. That lowers the urgency and changes nothing about the rule |
| **Reading V2.1.1** | It would close the "removed, not merely absent" half of #67 directly. Not downloaded |
| **A guard case for `guest()`** | The containment is proved by one measurement and by `serve` failing correctly while it was wrong. Nothing fires if someone deletes `unshare` |

### Open, carried forward

63. ~~**Does the `formWsc` overflow reproduce on the published V2.1.2 image?**~~
    **Answered: yes**, with `ra` at 513 rather than 509. Closed.
64. ~~**Is the `localPin` overflow already published?**~~ **Answered: yes — and
    the answer was already in `notes/prior-art.md` and `notes/cve-status.md`
    when the question was written.** CVE-2025-4462. Closed; the process failure
    it exposes is open as #70.
65. ~~**Why do 42 of the 47 handlers carrying the idiom return before reaching
    it?**~~ **Answered from the vendor's source**: they take `ERR_MSG`, which
    never writes through `url`. Closed.
66. **`formtable-scan.py` is validated on one build of six.** Unchanged.
67. **`formSysCmd` was removed in V2.1.2 and reintroduced by 2016.** The
    removal half was already argued in `notes/formSysCmd-analysis.md` in W04 and
    now has a second, mechanical source. **The reintroduction half is the open
    part** — no note carried it, and nothing says who or why. Falsifiable in one
    command against V2.1.1-B20150708, which is fetchable and has not been fetched.
70. **Nothing makes a finding consult `notes/prior-art.md` before it is written
    up.** Two of today's three closures were re-derivations of W04 conclusions.
    `docs/disclosure.md` step 2 said "search"; it did not say *where first*, and
    a register nobody opens is a register that does not exist.
68. **Is `formWsc` reachable unauthenticated on this unit?** Everything measured
    today was emulated, and the v2.1.2 profile cannot pass `serve`'s gate control
    at all — `blank.htm` returns 200 where the device returns 302. That is most
    likely the synthesised, password-free configuration in that profile rather
    than a difference in the firmware, and "most likely" is not a measurement.
69. **Nothing fires if `unshare` is removed from `guest()`.** The containment is
    correct and unguarded, which is exactly the state bug 45 was in yesterday.

### Where W07 stands, and what the next session does first

| Next | Needs the device? | Note |
|---|---|---|
| **1. The bench visit** | ✅ | 30 rows, station order per `runsheet.md` Part B `B-W07` and its supplements. `A3.2` early for the 601-second window, `P9-9` last. **`formWsc` is now `HAZARDOUS`**: a POST to it writes flash on this build |
| **2. Open a PR so the remote actually runs** | ❌ | Pushed to `origin/w07-bughunt` on 2026-08-18. **No run started**: the workflow fires on `push: main` and on `pull_request`, and PR #15 was merged this morning. `gh pr create --base main --head w07-bughunt`, then `gh run list` — local green has never been the same claim as remote green, and this branch has not had a remote run since `067d0cc` |
| **3. `P8-12`, `P8-23`'s sibling** | ❌ | `config-diff.py` now writes a field and proves where it landed. `P8-12` still needs an *encoder*, which is a different thing, but the differential is no longer the blocker |
| **4. Open #68** | ✅ | The gate question is the one thing today could not answer under emulation at all |

## W07 Day 6 — the bench visit, and five targets this project had already destroyed — 2026-08-18

The first session that touched the device since W06. Twenty-one register rows
closed and four upgraded from emulated to dynamic, across five power cycles and
two cable moves. Three of the results are heavy, and one of them was found while
looking for something else.

### The closure list was under-reporting by four, and the tool says so itself

`make todo WEEK=W07` opened the session at 29 outstanding. Four of the rows it
called **done** were closed on `emulated` evidence and had a silicon step
scheduled for that same night — `P2-9` and `P8-5` under `A3.13`, `P1-7` and
`P5-6` under `A3.23`. `week_summary()` decides `done` on `if c["id"] in latest`,
which asks whether a result exists and never asks what kind, while the same file
carries a constant named `EMULATED_CONFIRMED_MARK` whose comment reads **"it
never becomes the tick"**. Two statements in one file, and the output follows
the weaker one.

`P5-6`'s own note had already said it out loud: *"反證條件（模擬下的崩潰在實體機上
重現不了）只有實機能答，那是 `A3.23`"* — a row whose refutation condition states
that only the device can answer it, sitting on the closed list.

All four were re-recorded with `--evidence dynamic` during the visit. `rtcase
record` appends and `latest_results` takes the last, so this is the path the tool
was built for; the ledger shows the run count. **The outstanding number did not
move on any of the four**, which is the defect demonstrated four times.

### `formSchedule` at the same address, and the guard set above the buffer

Two crash results, and they are different shapes.

`A3.23`'s terminal shot reproduced the emulated crash **at the address the desk
work predicted**: `do_page_fault() #2: sending SIGSEGV to boa for invalid write
access to 004725d0 (epc == 2aafe218, ra == 00445974)`. That is the empty-string
literal in the read-only segment, and the access is a write to it. So the
qemu-user environment is admissible as a filter, and `P5-6`'s refutation did not
fire. The other half mattered more and ran first: `formNtp`, `formDMZ` and
`formWlanSetup` all survive an empty-body POST on silicon, so the alignment
explanation stands and nothing measured with `tools/alignfix` rolls back.

`CVE-2021-35392` reproduces against `wscd` from one unauthenticated UDP datagram.
The first ladder measured nothing while looking like it had: an over-long `ST`
that matches no served service draws no reply, and no reply is indistinguishable
from a length check. The match turned out to be a **prefix** match, so a valid ST
plus padding both matches and overflows; the echoed length tracks the input
exactly, and at total length 271 the reply goes out and the process is dead
immediately after. The fault address is `4187c8bc`, not `41414141` — one byte of
a live pointer overwritten and three original, a partial pointer overwrite.

`CVE-2021-35393`'s vector produced the more interesting reading, and the first
conclusion was wrong. Lengths from 215 to 1047 come back `412 Precondition
Failed` with `wscd` alive, which reads as a length check doing its job. Narrowing
inverted it: 170 is fine, **180 answers 200 and then `wscd` never answers
again**. The guard exists and its threshold sits above the buffer, so the fatal
window is the range long enough to overflow and short enough to pass — and
testing only past the threshold reports the service as protected.

And what happens at 180 is not a crash. The console logged nothing, while it
logged both of the night's real faults; `ps` still shows the process, sleeping;
a restart attempt fails with `Failed to open socket for HTTP. EXITING` because
the sockets are still held. `/proc/net/tcp6` has lost 52881 while
`/proc/net/udp` still shows 1900 bound with 2,088 bytes unread in its receive
queue. The process is out of its select loop and holding both ports. **No fault
to log, no exit for anything to respawn, and nothing else can take the ports.**

### The session arm is real, it expires from the login, and two tools missed the store

`P2-11` is the row only the device could answer, and it half-refuted the reading
it was written from. The IP-keyed third arm exists: a POST to `/boafrm/formLogin`
from `10.1.1.100` makes `/password.htm` return 200 with 5,332 bytes to that
address **carrying no credentials**, while `10.1.1.101` on the same wire gets 302
at every one of sixty-odd samples.

The expiry is not what `notes/auth-session-ip.md` says. Its table states that at
601 s and after, `authipaddr` is overwritten before it is compared, so the IP
session **can never succeed again until the device reboots**. Measured: the first
login at uptime 232.9 left the window open through 809.3, and a second login at
uptime 939.5 — 338 s past the predicted permanent close — reopened it, which the
stated mechanism forbids outright. That second window shut between samples at
1538.1 and 1541.2 against a prediction of login+601 = 1540.5. Two anchors 706
seconds apart, both landing on login+601.

So `beforeuptime` is assigned at login, and refutation branch (b) is what fired:
Ghidra's reference model and `tools/mipsref.py` missed the same store while a
control in the same run reported one read and one write. Per the register's own
instruction the instrument is fixed before this row is argued further. A lead
that costs nothing: that report already renders `authipaddr` at `0x00486270` as
six reads and zero writes, while the note states `form_formLogin` writes it at
`0x0044f13c` — through `strcpy`, so the address is an argument and never stored
to. **A genuinely written global reading as `writes:false` has already happened
once in that file, and it was not read as a limitation of the scanner.**

The first version of the procedure used a Basic-auth GET as the login and
measured 302 straight afterwards. That looks exactly like "the arm is dead on
this unit". The arm is written by the login form handler; Basic auth goes
through `process_header_end` and never reaches it. **A self-inflicted false
negative, one wording away from being written up as the week's heaviest
refutation.**

### Five targets, destroyed by this project's own test, and the fifth is a persistent WAN DoS

W05's unauthenticated POST round swept every non-hazardous endpoint with
parameters absent. Its record lists what changed and concludes that **no field
moved in a dangerous direction**. That sentence is true and it is not the whole
consequence. Four of tonight's rows had no target because of it:

| field | W05 wrote | tonight's row |
|---|---|---|
| `UPNP_ENABLED` | `1 -> 0` | `P6-1`, `P8-7` — `miniigd` not running, 52869 closed |
| `ALG_SIP_ENABLED` | `1 -> 0` | `P6-5` — no SIP helper, no conntrack expectation |
| `SSH_ENABLED`, `TELNET_ENABLED` | `1 -> 0` | background for the command-surface rows |
| **`DHCP_MTU_SIZE`** | **`1500 -> 0`** | **`P8-19`** |

The last one is not a disabled service. With the cable in the WAN port, a rogue
DHCP server running, across a full boot and 160 seconds, **zero packets crossed
the wire** — no DISCOVER, no ARP, nothing, while `udhcpc -i eth1` was in `ps` and
`WAN_DHCP` read 1. `ifconfig` showed `eth1` with `MTU:0` against `eth0`'s 1500,
and `flash get DHCP_MTU_SIZE` returns 0.

The chain is measured rather than inferred. `ifconfig eth1 mtu 1500` took, so
MTU 0 is configuration and not hardware; `udhcpc` was poked; the cable went back
to the same port with the same host and the same server, and the exchange
completed at once — DISCOVER, OFFER, REQUEST, ACK, then an ARP for the gateway.
**One variable changed.**

So an unauthenticated POST with parameters absent writes `DHCP_MTU_SIZE=0` to
flash, the WAN interface comes up unable to transmit, and the router cannot
obtain a WAN address at all — across every reboot since 2026-08-17. And it
composes: a WAN that is down starts `dnsspoof`, which answers **every** name with
`10.1.1.1`, including a name in an invalid TLD. Every LAN client's every lookup
lands on the web server that carries unauthenticated command injection (`P3-3`),
the uninitialised credential pair (`P2-9`) and unauthenticated password change
(`P10-3`). **One request, and rebooting does not clear it.**

`/var/info` records the vendor's own view of the middle of that chain: `dnrd cmd
in start_wanphy_dnrd 3 = 192.168.77.1` — the rogue DNS address from the lease
becoming the LAN relay's upstream.

### Two instrument failures, and one of them would have inverted a result

**`/proc/net/tcp` never shows `boa`.** Counting Slowloris connections from it
returns zero while 200 sockets are held, because `boa` listens on a dual-stack
IPv6 socket and IPv4 clients appear in `/proc/net/tcp6` as `::ffff:` mapped
addresses. The same file had already failed to list port 80 as LISTENING earlier
in the session while the server was demonstrably answering — **that impossibility
is what made the second attempt happen**. Counted correctly, `boa` holds 251
established connections and serves throughout, so `P8-16` is refuted through its
second branch and boa's connection handling needs re-reading.

**A short `curl` timeout is indistinguishable from a crash.** `formWlanSetup`
recorded `000` at `-m 6` and returns 200 after 10.3 s. Second occurrence of the
false-negative shape `bench-probe.py`'s own documentation warns about, in one
session.

### `--disclosure reveal` was in three commands, and the checker read the flag rather than the command

`runsheet.md` passed `--disclosure reveal` to `fwrecon compcs` in three places;
the tool accepts `open` and `protect` and argparse kills the command before it
does anything. CI was green throughout, because `tools/check-runsheet.py`
verifies that a flag appears in the tool's own `--help` and stops there —
`--disclosure` is real and `reveal` is not a flag at all. **Same shape as the
`AUTOBURN: 0` failure the checker was written for, arriving through the one gap
the first fix left open.** The checker now recovers `choices=` sets from the help
text and validates the value, with three guard cases in
`tools/test-check-runsheet.sh` — one that must fail, one that must pass, and one
that proves a shell variable is left alone rather than guessed at.

### Instrument work

- **`tools/session-window.sh`** — new. `P2-11` had no procedure anywhere:
  `A3.2`'s heading claims it and the section's own body says the power-up
  delivers *three* things and never mentions it, and `coldboot-timing.sh`'s
  header lists the same three. The tool polls both source addresses across the
  boundary rather than sampling two points, because "it expires at 601" is the
  claim and a two-point test cannot miss by a second.
- **`tools/check-runsheet.py`** — `declared_choices()` plus the value check
  described above.
- **`tools/test-check-runsheet.sh`** — 32 cases to 35.

### Corrections to the plan

| | |
|---|---|
| **The bench visit is 31 device rows, not 30.** | `make todo` says 29 outstanding, of which 2 are desk; the run order in `B-W07 增補` has a slot for 24 of the remaining 27, because **`A3.21` is missing from the 第 3 站 ⑤ list** (`P8-17`, `P8-20`) and **station 2 is not scheduled at all** (`P9-4`). Add the four rows the register calls done on emulated evidence and the night's real card count is 31. `BENCH-LOG.md`'s Day 4 entry says 30, which was correct when it was written and went stale when `P8-23` closed |
| **`A3.2` claims `P2-11` and had no procedure for it.** | The heading says "一次上電餵四項（關 `P1-12` · `P2-11`）"; the body says three things and lists `P1-12`, `P9-1` and a log. `check-runsheet.py` verifies that a heading's claimed ids exist in the register and that executed rows are claimed by some step, and **neither direction can see a step whose body has no procedure for one of the ids it claims**. Written as `A3.2.4` on the night, before it was run |
| **The IoC baseline in this session's own plan entry was wrong, and it would have aborted the visit.** | It said 4 / 343. The correct figure has been 0 / 343 since W05's afternoon POST round overwrote `COMPDS`, and W05 and W06 both recorded it. The same error appears in the 2026-08-18 morning plan entry. Both were copied from the **example value** inside `runsheet.md` `A2.3.4`'s note — whose text says, in bold, that the number is not a constant. Measured 0, matching. Corrected by appending, per the file's own rule |
| **`A3.23`'s two shots are numbered in the order that cannot be run.** | Shot one is terminal for `boa`; shot two needs it alive. Fixed in Part A with the numbering left visible |
| **`--disclosure reveal` appeared in three commands and one explanatory comment.** | All four corrected; the checker extended so it cannot recur silently |

### Deliberately not done

| Item | Why |
|---|---|
| **`P9-9`, the reset button** | The one device row left, and deliberately. It overwrites `COMPCS` with `COMPDS` and erases the ground every other result stands on — and the ground at the end of this session is worth something: `DHCP_MTU_SIZE=0`, `UPNP_ENABLED=0` and `ALG_SIP_ENABLED=0` are all still in place, so pressing reset answers `P9-9`'s own prediction **and** gives the third independent check on `P8-19`'s causal chain in one measurement |
| **`P5-2`, ret2libc** | Unchanged. The honest version of the question is about the device, not `qemu-user`'s mmap layout |
| **`P4-6`** | Desk row, not attempted; the device work took the session |
| **Restoring `UPNP_ENABLED` / `ALG_SIP_ENABLED`** | The only route is a boot-loader write from station 2 — this build's web UI has no page for either, all 31 pages in `menu.htm` were enumerated on the running device |
| **Route injection via DHCP options 33 / 121 / 249** | The device's own DISCOVER requests all three, so it is inside what it accepts, but the crafted lease was never delivered: the 3600 s lease was still live and forcing a renew needs LAN-side access that the WAN cable position denies |
| **Reading `/bin/ntp_inet`** | A 44-byte NTP reply makes the clock land on `0xFFFFFFFF`, a value not in the datagram, while a correct 48-byte reply sets the right time. That is a behavioural observation and the root cause needs the binary |
| **The over-the-air wireless scan** | `P1-11` stays partial. Four device-side sources agree on 2.4 GHz b/g/n with no WPA3, but they are the device describing itself; the refutation asks for a scan, and the host's Wi-Fi needs a Windows privacy setting changed |

### Open, carried forward

66. **`formtable-scan.py` is validated on one build of six.** Unchanged.
67. **`formSysCmd` was reintroduced by 2016 and nothing says who or why.**
    Unchanged — V2.1.1-B20150708 still not fetched.
69. **Nothing fires if `unshare` is removed from `guest()`.** Unchanged.
70. **Nothing makes a finding consult `notes/prior-art.md` first.** The rule is
    in `docs/disclosure.md`; nothing enforces it.
71. **A step may claim a test id and carry no procedure for it, and both
    directions of `check-runsheet.py` are blind to it.** `A3.2` claimed `P2-11`
    for a day with a body that says it delivers three things. The fix is not
    obvious: the checker would have to know which prose belongs to which id.
72. **`beforeuptime` has a write that two independent instruments missed.**
    Measured from the device: the session window expires at login+601, not at
    uptime 601. The lead is that the same report renders a `strcpy`-written
    global as `writes:false`, so the scanner's model of "written" is
    address-taken versus address-stored — and nothing in the repository says so.
73. **W05's POST round wrote `DHCP_MTU_SIZE=0` and the WAN has been dead since.**
    The finding is closed; what is open is that **no measurement in this project
    would have noticed**. Four bench sessions ran between then and now. A
    per-session check that the device can still do its primary job does not exist.
74. **`hopeiot.net`.** The device asks for it within 4 s of getting a WAN lease.
    No document in this repository mentions it, its purpose is unknown, and what
    it sends was never seen because the name was never answered in time.
75. **`wscd` wedges without exiting, and nothing watches it.** One unauthenticated
    SUBSCRIBE removes the WPS/UPnP surface until a power cycle. Whether the
    mechanism is CVE-2021-35393's overflow is not established.

### Where W07 stands, and what the next session does first

**Register: 55 / 58.** Outstanding: `P9-9` (device), `P4-6` (desk), `P5-2`
(deliberately cut in all but name).

| Next | Needs the device? | Note |
|---|---|---|
| **1. `P9-9`, and the H601 snapshots either side of it** | ✅ | `A3.24`. It answers its own prediction and gives `P8-19` a third source in one press. Do it on the dirty machine, not after a clean boot |
| **2. `UPNP_ENABLED` and `ALG_SIP_ENABLED` back to 1 from station 2** | ✅ | The only route; unblocks `P6-1`, `P8-7`, `P6-5` |
| **3. `P4-6`** | ❌ | The last desk row |
| **4. Open #72 — the missing store** | ❌ | Extend `mipsref.py` to report address-taken separately from address-stored, then re-run against `beforeuptime` and `authipaddr` |
| **5. Open #73 — a liveness check** | ❌ | `make doctor` or the runsheet's opening station should notice that the device cannot reach its own WAN |

## W07 Day 7 — the reset button, and a router that would not boot with its own console attached — 2026-08-19

The close-out. `P4-6` on the desk, open items 72 and 73 built and used, and the
one device row W07 had left. Three of the results are worth more than the row
they closed, and one of them is a procedure defect that had been sitting in
`runsheet.md` for a day looking like the most careful step in the file.

### The one step `A3.24` called unskippable was comparing erased flash to erased flash

`A3.24` asks for an `H601` snapshot before and after the reset and says, in
bold, that it is the only step in the section that may not be skipped. The
command it gives dumps `0x3F0000`.

**`H601` is at `0x006000`.** Three sources agree and two of them are in this
repository: `runsheet.md` `A2.3.1`'s own partition diagram, `notes/flash-layout.md`
line 134, and the public Realtek SDK's `apmib.h`, whose `HW_SETTING_OFFSET` is
`0x6000`. Measured on this unit's dump: `0x006000` has **4,093 non-`FF` bytes in
4,096** and opens with the four characters `H601` followed by a run of MAC
addresses; `0x3F0000` has **0 non-`FF` bytes in 4,096**. It is erased.

So the comparison was `0xFF` against `0xFF`. It would have returned UNCHANGED in
every possible world, including the one where the reset wipes the radio
calibration — and "reset 之後 H601 的內容改變" is `P9-9`'s own refutation
condition. **A control that cannot fail, sitting on the only cell the row is
really asking about.** Found at the desk, before the button.

The same command carried `--at-prompt`, which means the board is halted at
`<RealTek>` — 第 2 站 — inside a step filed under 第 3 站. Part A's promise is
that reading `A1.1` → `A4.2` front to back *is* a correct order to run it in, and
a step whose commands need another station's device state breaks that silently.
`check-runsheet.py` now reads a step's **commands** as evidence of the device
state they need, not just its heading, with a deliberate-detour escape that
names the station you are sending the reader to — which is what makes `A3.8`'s
recovery path correct. 35 → 38 guard cases.

The fix is to cite rather than restate: `A2.3`'s 64 KiB snapshot starts at `0x0`,
so `H601` is already inside it, and the "before" is not one snapshot but
**seven**, whose `0x6000` window is byte-identical from 2026-08-16 to 2026-08-18.

### `COMPDS` was overwritten too, so the register's prediction had no discriminating power

Decoding both regions of the previous session's station-2 snapshot showed what
nobody had looked for: W05's unauthenticated, parameter-absent POST round wrote
**the factory-default block as well as the live one**. 25 of 343 fields off the
2026-08-16 read, including `DHCP_MTU_SIZE 1500 → 0`, `UPNP_ENABLED 1 → 0`,
`ALG_SIP_ENABLED 1 → 0` and `SSH_ENABLED 1 → 0`.

`COMPDS` against `COMPCS` was therefore **0 of 343**, and `P9-9`'s prediction —
"reset overwrites `COMPCS` with `COMPDS`" — had already come true. Pressing the
button could not distinguish "the reset worked" from "the reset did nothing".

The prediction was replaced **before the button and before any result**, with
`amended` and `amend_reason` in the register and the freeze hash moving
`ef7ab66d` → `ea8cf733` in commit `b88b932`. The new one follows a chain read
statically: `/bin/reload`, which the previous session's `ps` shows running as
PID 291, polls `/proc/load_default` and executes `flash default-sw`; and
`/bin/flash`'s own usage text separates `default -- write all flash parameters
**from hard code**` from `reset -- reset current setting to default`. The button
takes the former, so it should restore from a compiled-in table rather than from
the block this project had corrupted.

**Both branches were findings.** If the fields came back, `P8-19`'s chain got a
third independent verification for free. If they did not, an unauthenticated
request had pushed the device into a state the vendor's own recovery button
cannot leave, and the only way back is a programmer this project does not own.

### The button restores from hard code, and the device came back byte-for-byte

`P9-9` ✅. One unauthenticated `GET /config.dat` before and after:

| | before | after |
|---|---|---|
| served bytes | 7,510 | **7,490** |
| `DHCP_MTU_SIZE` | `0` | **`1500`** |
| `UPNP_ENABLED` / `ALG_SIP_ENABLED` / `SSH_ENABLED` | `0` / `0` / `0` | **`1` / `1` / `1`** |
| fields off the 2026-08-16 baseline | 20 / 343 | **0 / 343** |
| sha256 | — | **`e09cbf8428aa1594…`, byte-for-byte the 2026-08-16 `COMPCS` region** |

`H601` is unchanged: `flash allhw` returns the MACs, the four WLAN addresses and
every TX power calibration table intact, and `HW_NIC0_ADDR` matches both the ARP
reply on the wire and the raw bytes at flash `0x006000` in all seven snapshots.
Refutation branch (b) did not fire.

And `eth1` came up **`MTU:1500`** — it had been `MTU:0` for two days — which is
`P8-19`'s third independent verification and the only one that changed nothing
by hand.

Three register rows unblocked as a side effect, and **the flash write the
session plan called "the only route" was never needed**: `UPNP_ENABLED` and
`ALG_SIP_ENABLED` came back with everything else, so `A2.5`/`A2.6` — the single
irreversible section, whose `FLW` drill has still never been rehearsed — stayed
shut.

### The device stopped booting, and the cause was its own console cable

Between the two halves of the session the device stopped answering — network and
serial console at the same moment — after a run of eight shell commands that
included `dd if=/dev/mtdblock0 bs=1 … count=7510`, a byte-at-a-time read of the
raw MTD device. Three full power cycles produced **zero bytes** on the console,
and the front LEDs lit together and steady, a state the author had not seen in
either the boot or the boot-loader case.

Nothing this session ran had written flash. `FLR`/`DB` are reads, `dd` is a read,
`flash get` is a read, and the command injection wrote into `/var/web`, a ramfs.

**The fix was the first of three physical tests: unplug the UART adapter from the
board's header.** It booted immediately. A USB-serial adapter's TX pin
back-feeds through the board's RX pin protection when the board is unpowered or
starting, and the runsheet's rule about not connecting `VCC` is one half of that
problem with the other half unwritten. **This makes a whole bench visit look like
a brick**, and it cost three power cycles and about forty minutes before it was
tried. Which of the eight commands wedged the running system is still not
established; the byte-at-a-time MTD read remains the strongest candidate and
that is an assumption, not a measurement.

### An unauthenticated POST leaves bytes of a previous password in flash

Found while comparing two snapshots for something else, and it survives only in
the snapshot because the reset erased the live copy.

`USER_PASSWORD`'s raw field, before and after the previous session's password
change and restore:

```text
2026-08-18 19:28   61 64 6d 69 6e 00 00 00 …      "admin" + NUL + zeros
2026-08-19 23:14   61 64 6d 69 6e 00 66 00 …      "admin" + NUL + 0x66 + zeros
```

The C string is still `admin`, so **every tool that compares decoded values sees
nothing** — this project's own first pass reported "0 of 343 fields differ". The
byte after the terminator is a character of the temporary password the restore
was supposed to erase. The write does not clear the field, so a password shorter
than its predecessor leaves the tail readable, and `GET /config.dat` is
unauthenticated. The same residue appears in `COMPDS`, which is a one-byte
witness that the password write reaches the factory-default block too.

**Not resolved, and it is on the open list**: the serial read at the boot loader
and the HTTP read after boot disagreed about the same region — `comp_len` 7,501
with the residue against 7,498 without it, 7,009 of 7,510 bytes different. Either
the boot rewrites `COMPCS`, or `/config.dat` is not the byte copy of flash that
`A3.6`'s headline result says it is. The station-2 read that would separate those
never happened, because the device stopped booting first.

### Route injection, delivered, and a string used as an IP address

`P8-19` second run. With `DHCP_MTU_SIZE` restored the device sent a spontaneous
DISCOVER 14 s after the cable moved to the WAN port — the previous session could
not get one, because forcing a renew needed LAN access the cable position denied.
`tools/rogue-dhcp.py` answered with options 121, 249 **and** 33 carrying
`10.99.0.0/16` via `192.168.77.66`, and the device installed **both** forms:

```text
10.99.0.0   192.168.77.66   255.255.255.255   UGH   eth1     <- option 33, no mask, host route
10.99.0.0   192.168.77.66   255.255.0.0       UG    eth1     <- classless
```

So a DHCP server upstream of this router installs arbitrary routes into its
forwarding table, unauthenticated, and the router asks for all three option
numbers by name in its own DISCOVER.

The refutation condition — `eth1.bound` quotes every DHCP-provided value — did
not fire, and the file settles it in 95 bytes. Its entire body is
`sysconf conn dhcp $interface $ip $subnet $router $dns`, with none of the four
quoted. **Precisely**: POSIX `sh` does not re-parse the result of an expansion,
so this is *argument* injection into `sysconf`'s argv, not command injection.

And there is a visible consequence, with a control. On 2026-08-18, with no route
options, the three gratuitous ARPs after the lease announced `192.168.77.100` —
the device's own leased address — one second apart. This time, same code path,
same three announcements at the same offset from the ACK, the announced address
was **`32.49.0.49`**: bytes `0x20 0x31 0x00 0x31`, ASCII space, `1`, NUL, `1`,
which is exactly the space-then-`1` boundary inside the string form of the route
option. **Four bytes straddling a separator in a string, used as an IPv4
address.** Which of the three options causes it is not established — all three
were sent at once, deliberately, to guarantee delivery — and it reaches nothing
beyond those three ARPs that this session could find.

### Open 72 closed: the store was in `form_formLogin` the whole time, eight bytes from the line the note already named

`beforeuptime` is written at **`0x0044f140`**. `mipsref` v1 could not see it, and
there were three separate blindnesses, each sufficient on its own:

1. **The address never appears in the storing instruction.** o32 PIC loads a
   global's address out of the GOT and stores through it: `lw $v1,%got(…)($gp)`
   then `sw $v0,0($v1)`. The immediate in the `sw` is `0`.
2. **An address in a register is neither an access nor a non-access.**
   `addiu $a0,$v0,%lo(authipaddr)` materialises an address for a callee to write
   through; v1 scored it `reads:False, writes:False`, indistinguishable in the
   totals from "not referenced".
3. **A GOT slot was reported as though it were the variable.** The committed
   report called `0x00486270` `authipaddr` with "6 reads, 0 writes".
   `0x00486270` is the *slot*; `authipaddr` is at `0x0048fbd8`; and all six were
   address materialisations.

v2 reports four classes instead of two and follows the pointer. `beforeuptime`
is now 1 direct read and 1 indirect store; `authipaddr` is 0 reads, 0 writes, 6
address-taken and 6 live at a call — the `strcpy` shape.

**Two more things came out of it.** `sstrip` removes section headers, not
`.dynsym`: `DT_SYMTAB`, `DT_STRTAB` and `DT_SYMENT` are in `PT_DYNAMIC` because
the loader needs them, and this `boa` has **423 named symbols** with real
addresses. This repository had treated the corpus as symbol-less for four weeks.
And the first control had been green the whole time — `nowuptime` carries a
direct read and a direct store, so `--control` exercised only the addressing form
the scanner could already see. **A control proves the path it travels.** v2 has a
second one that requires a store found through a register, `check-reports.py`
enforces it for schema-2 reports, and it failed on its own first run and was
right to: a `jalr` clobbers caller-saved registers, but its delay slot executes
first, and `nowuptime`'s store is in one.

The reading was confirmed at instruction level with `BoaListing` over
`0x0044f0e0`–`0x0044f190`, where Ghidra's own annotation on the `sw` reads
`-> beforeuptime`. **The information was one indirection away inside the tool's
own output.** The gate's arm reads `sltiu v0,v0,0x259` — 0x259 is 601 — and on
expiry does `strcpy(authipaddr,"0.0.0.0")`, which is why the device measured
login+601 twice, 706 s apart. The same handler also runs
`system("killall -9 dnsspoof")` and `system("rm -f /var/run/dnsspoof.pid")`
immediately after a successful login, which nothing in this repository had noted.

### Open 73 closed: nothing asked the device whether it could still route

`tools/device-liveness.py`. One unauthenticated `GET /config.dat`, decoded with
this project's own decoder, in two halves: named assertions each carrying the
sentence that says what breaks, and drift against the frozen 2026-08-16 baseline
so the next `DHCP_MTU_SIZE` — one nobody has thought of — is visible too. Wired
into `make doctor` at tier 3, where a device that is off is skipped rather than
failed. 19 guard cases, none needing a device.

It earned its place the first time it ran: on the damaged machine it printed

```text
FAIL  the device answered and it is NOT doing its job: DHCP_MTU_SIZE expected 1500 got 0
      -> python3 tools/device-liveness.py   # the failing field names what breaks
```

### `P4-6`: six of the 2025 series match verbatim, four do not address anything on this build

`tools/cve-endpoints.py` reads the advisory list out of `notes/cve-status.md` —
the file that owns it — and checks each against this unit's own `root_form[]` and
the same table across all six scanned builds. Six match verbatim. `CVE-2025-3989`
publishes `Hostname` where the handler at `0x0041af20` references `hostname`, and
form field names are case-sensitive here. `CVE-2025-3988` publishes
`service_type` where the handler at `0x0041d110` references `comment`. Three name
a route that exists in **none** of the six builds, and for two of them the tool
names the neighbour they were mis-transcribed from: `formWlWds` (capital W) and
`formStaticDHCP` (`form`, not `from`). `CVE-2019-19825`'s `getSanvas` is absent
too: this build's `formLogin` references `username` and `userpass` only.

### Instrument work

- **`tools/mipsref.py`** — schema 2: four access classes, `.dynsym` through
  `PT_DYNAMIC`, GOT-slot detection that refuses to answer for a slot, a
  dereference pass, and `--control-indirect`. `make mipsref-reports` regenerates
  the two committed reports, because hand-typing that command is part of how the
  first one came to name a GOT slot as a datum.
- **`tools/device-liveness.py`** + `tools/test-device-liveness.sh` (19 cases),
  `make liveness`, and a new `make doctor` block.
- **`tools/cve-endpoints.py`** with three controls: a parse floor, a positive
  control (`formSysCmd`/`sysCmd`) and a negative control.
- **`tools/rogue-dhcp.py`** — a WAN-side DHCP server whose first refusal is the
  important one: it will not serve on the interface carrying the default route.
- **`tools/check-runsheet.py`** — commands as evidence of the device state they
  need. **`tools/check-reports.py`** — the schema-2 controls.

### Corrections to the plan

| | |
|---|---|
| **`A3.24`'s `H601` snapshot dumped erased flash.** | `0x3F0000` instead of `0x006000`; 0 non-`FF` bytes against 4,093. The step the section called unskippable could not fail. Fixed by citing `A2.3` rather than restating it |
| **`A3.24` ran a 第 2 站 command from 第 3 站.** | `--at-prompt` means the board is halted at `<RealTek>`. `check-runsheet.py` now catches this class, with an escape for a deliberate detour |
| **`P9-9`'s original prediction was untestable today.** | `COMPDS` and `COMPCS` differ in 0 of 343 fields, because W05's POST round wrote both. Amended before the button, freeze `ef7ab66d` → `ea8cf733` |
| **The previous session's last three cards carry times that had not happened.** | `T-61`, `T-62` and `T-63` are stamped `2026-08-19 00:1x`–`02:2x`; the commits that carried them are `2026-08-18 21:55` and `22:04`, and the pcaps they cite are `21:25`–`21:39`. Corrected by appending, per the file's own rule. **This session's own plan heading had the same error** and is corrected in the same place |
| **`P4-6`'s first record carried tomorrow's date.** | Re-recorded on `2026-08-18`; `rtcase record` appends and `latest_results` takes the last, which is the path the tool was built for |
| **The session plan said the station-2 flash write was "the only route" for `P6-1`, `P8-7` and `P6-5`.** | All three were already recorded `na` on 2026-08-18, so they were not W07's business; and the reset restored the fields anyway. The single irreversible section was never opened |
| **The USB Ethernet adapter fell back to the Windows side mid-session.** | Caught by `ip route get` and `ttl=63` — instrument bug 21, exactly as documented. Every measurement between the fallback and the fix went through Windows; the bytes are unaffected but the isolation guarantee was not, and one of them was a `make liveness` run |

### Deliberately not done

| Item | Why |
|---|---|
| **`P5-2`, ret2libc** | Unchanged, and now the only outstanding W07 row. The honest version of the question is about the device, not `qemu-user`'s mmap layout |
| **The byte-level `H601` comparison** | It needs a second station-2 dump, and the serial adapter is what stopped the board booting. The decoded second source (`flash allhw`) was taken instead, and the seven-snapshot "before" does not go stale |
| **The state of `COMPDS` after the reset** | Same reason. It is a new open item rather than an assumption |
| **Isolating which of options 33 / 121 / 249 produces the bogus ARP** | All three were sent together on purpose, to guarantee delivery on the one lease this session could get |
| **A `dd` of the MTD device to settle the serial-vs-HTTP disagreement** | That is the command most likely to have wedged the device |

### Open, carried forward

66. **`formtable-scan.py` is validated on one build of six.** Unchanged.
67. **`formSysCmd` was reintroduced by 2016 and nothing says who or why.**
    Unchanged — V2.1.1-B20150708 still not fetched.
69. **Nothing fires if `unshare` is removed from `guest()`.** Unchanged.
70. **Nothing makes a finding consult `notes/prior-art.md` first.** Unchanged.
71. **A step may claim a test id and carry no procedure for it.** *Half closed.*
    `check-runsheet.py` now catches a step whose **commands** need another
    station's device state, which is one mechanical shape of the problem. The
    other shape — a heading claiming an id whose procedure is absent — still
    needs the checker to know which prose belongs to which id.
72. **~~`beforeuptime` has a write two independent instruments missed.~~**
    **Closed.** `0x0044f140`, in `form_formLogin`. See above.
73. **~~No measurement would notice that the device cannot route.~~**
    **Closed.** `tools/device-liveness.py`, in `make doctor`.
74. **`hopeiot.net`.** Unchanged; the device asks for it within 4 s of a WAN
    lease and nothing in this repository knows what it is.
75. **`wscd` wedges without exiting, and nothing watches it.** Unchanged.
76. **Is `COMPDS` repaired?** `flash default-sw` restored `COMPCS` byte-for-byte,
    but the factory-default block was corrupted too and nothing has read it since.
    If it is still damaged, then `P0-5`'s IoC baseline — the difference between
    the two regions — means something different from what this project has
    assumed since W02, and it needs one station-2 dump to settle.
77. **Which DHCP option turns a string into an IP address.** Options 33, 121 and
    249 were sent together. The bogus ARP is reproducible; the attribution is not.
78. **`eth1.bound` expands four attacker-controlled values unquoted.** Option 6
    may carry several addresses, so `$dns` becomes a list and `sysconf`'s argument
    positions shift. What `sysconf` does with the extra argument is unmeasured.
79. **A UART adapter on the header stops this board booting, and no document
    says so.** It cost three power cycles and forty minutes, and it is
    indistinguishable from a brick. The runsheet's `VCC` rule is one half of it.
80. **Two reads of `COMPCS` disagreed and nothing settled it.** The boot loader
    saw `comp_len` 7,501 with a password residue; HTTP after boot saw 7,498
    without it. Either the boot rewrites the region, or `/config.dat` is not the
    byte copy of flash that `A3.6`'s headline result claims. One station-2 dump
    separates them, and it is the same dump item 76 needs.
81. **`check-benchlog.py` checks that a card carries a time, not that the time is
    possible.** A card stamped later than the commit that carried it is
    mechanically detectable, and three of them exist.

### Where W07 stands

**Register: 57 / 58.** The one outstanding row is `P5-2`, cut in all but name.

| | |
|---|---|
| Closed this session | `P4-6` (desk), `P9-9` (device), `P8-19` re-run with the route-injection half |
| Open items closed | 72, 73 |
| Open items opened | 76, 77, 78, 79, 80, 81 |
| New instruments | `device-liveness.py`, `cve-endpoints.py`, `rogue-dhcp.py`; `mipsref.py` to schema 2 |
| Guard cases | +19 (liveness), +3 (runsheet), and the schema-2 report checks |

---

## W07 close — the last register row, and six files that said "open" in the present tense — 2026-08-19

**Desk only. The device was not powered on.** Two things closed and one was
found; the found one is the serious one, and it was not on any list.

**W07 is 58 / 58.**

### `P5-2` was answerable from evidence this repository already had

The row was "cut in all but name" in the previous session's own words, on the
grounds that a `ret2libc` target needs an observation channel this device does
not offer. It needed no channel. Two kernel fault messages were already in
`BENCH-LOG.md`, recorded on 2026-08-18 for other rows:

```text
（card T-50）SIGSEGV to wscd ... (epc == 2aae1f38, ra == 2aae1e64)
（card T-60）SIGSEGV to boa  ... (epc == 2aafe218, ra == 00445974)
```

Neither names a library. Turning one into a load base is
[`tools/libbase.py`](tools/libbase.py); the reasoning and the addresses are
[`notes/mips-ret2libc.md`](notes/mips-ret2libc.md); the report is
[`reports/libbase-unit-2018.json`](reports/libbase-unit-2018.json).

**`boa`'s `epc` is `strcpy+0x18`, which puts `libuClibc` at `0x2aae3000`, and
`system` at `0x2ab08460`.** The four bytes between that and qemu-user's own `pc`
for the same fault (`0x2b32721c`, `strcpy+0x1c`) are *predicted*, not tolerated:
the store sits in the delay slot of the `bnez` above it, and a MIPS fault taken
in a delay slot leaves `EPC` on the branch because restarting has to re-execute
it. The two words were read back out of the ELF and decoded independently —
`0x1460fffc` and `0xa0c30000`, source register `v1` shared — and the tool refuses
to build the report when they do not match.

**Choosing `strcpy` is a funnel and the funnel is published**, because "I picked
the one I already knew" is what this looks like otherwise:

| filter | survivors |
|---|---|
| dynamic symbols in `libuClibc` | 663 |
| …admitting a **page-aligned** base for `0x2aafe218` | 22 |
| …putting a **store** at the `epc` or in a branch delay slot there | 5 |
| …matching qemu-user's instruction **pair** | 1 |

**And the prediction that could have failed.** `boa` needs `libapmib.so`,
`libc.so.0`, `libgcc_s.so.1`; `wscd` needs the last two. If nothing is
randomised and the loader allocates bottom-up, the two `libc` bases differ by
exactly `libapmib.so`'s mapped span — `0x25000`, out of its own program headers,
with no reference to either fault. Predicted `0x2aabe000`; it puts `wscd`'s `epc`
at `free+0x12c` and its `ra` at `free+0x58`, both inside one function, against a
kernel line that called the fault an invalid **read** from `0x4187c8bc`.

**The error bar is measured, not asserted.** Sweeping all 256 page-aligned bases
in the surrounding megabyte, **7** put both `epc` and `ra` inside one and the
same function. So the landing survived a filter it had about a **1-in-36** chance
of surviving by luck, and the rest of the weight is the fault *kind*: of the
seven, the predicted base names `free()`.

**Recorded `partial`, and that is the point.** The register's refutation is "the
base differs across two reboots"; both messages come from **one** boot. Scoring a
refutation that could not have fired is precisely what `A3.24` was caught doing
two days ago, comparing erased flash against erased flash. What is established is
per-`execve` determinism — which is what ASLR actually is — and one
`cat /proc/<pid>/maps` on the post-reset boot closes the rest. That is now
`runsheet.md` `A3.23.0`.

### Six committed files said `52869/tcp open` in the present tense, and one of them was the disclosure register

`P1-2` found it open on 2026-08-16. `P6-1` and `P8-7` found it **closed** on
2026-08-18 — `miniigd` absent from `ps`, no `InternetGatewayDevice` answering
SSDP — because `UPNP_ENABLED` read `0`, which **this project's own W05
unauthenticated POST round wrote**, and this build ships no UPnP page through
which a user could put it back. Both measurements were right when taken.
**Neither sentence carried a *when***, and the first one had been copied into:

`docs/disclosure.md` `D-16` · `notes/bughunt.md` · `notes/cve-status.md` ·
`notes/attack-surface.md` · `notes/three-unread-binaries.md` (×3) ·
`PROGRESS.md` §W07 Day 5

All six now carry the dates and the mechanism. `D-16` additionally says it is
**not reportable on its network state** until a bench visit re-measures it —
a reported open port has to be a port somebody looked at.

**And the second layer is worse than the first.** The 2026-08-19 reset restored
`COMPCS` byte-for-byte, so the flag is `1` again and the port is very probably
open again. A claim that has come back true **by accident** is indistinguishable
from one that was checked, and nothing in this repository could tell those apart.
That is why the fix is a date on every sentence rather than flipping "open" to
"closed".

### The fifth divergence between `make ci` and CI, and this time it gets a checker

`tools/test-device-liveness.sh` (19 cases) and `tools/test-rogue-dhcp.sh` (12
cases) were in `make ci` from 2026-08-18 and 2026-08-19 and were **never** in
`.github/workflows/ci.yml`. The workflow's own comment above the `config-diff`
step reads "it is the fourth time these two lists have diverged."

RUNBOOK 10.21 made it a rule. A rule broken five times is a reminder, and this
repository's answer to a broken reminder is already on the record —
`tools/check-benchlog.py` replaced one. So:
[`tools/check-ci-parity.py`](tools/check-ci-parity.py) compares which `tools/`
scripts each file runs, in **both** directions, with one-sided entries recorded
as decisions in a `DELIBERATE` table rather than tolerated silently. It fired on
its first run and named all three. 13 guard cases, and two of them exist because
the workflow *names four suites in prose*: counting a comment as a step is how
the fifth divergence stayed invisible.

### Instrument work

| | |
|---|---|
| `tools/libbase.py` | new. Its own ELF reader through `PT_DYNAMIC` — deliberately not an import of `mipsref.py`, so the symbol address that everything rests on has two readers, and `test-libbase.sh` asserts they agree |
| `tools/test-libbase.sh` | 27 cases. Four failed on the first run and **all four were the fixture, not the tool** — including one that taught the filter's own selectivity: a 40-byte symbol covers 40 consecutive bases, so page alignment rejects about 99 % of addresses, not all but one |
| `tools/check-ci-parity.py` + suite | new, 13 cases |
| `tools/check-reports.py` | a `libbase` block: no `control_ok`, no file |
| `Makefile` / workflow | `libbase-test`, `libbase-report`, `check-ci-parity`, `ci-parity-test`; the three missing suites added to CI |

### Corrections to the plan

- **`P5-2` was described as "cut in all but name" and it was not cut.** The
  previous session's `BENCH-LOG.md` closing block and `study/weekly-results.md`
  both say so; both were written before anyone tried the desk route. Corrected by
  appending, in `BENCH-LOG.md` 2026-08-19 §1.
- **`P5-2`'s refutation condition is aimed at the wrong axis** — reboots rather
  than `execve`s. **It was not amended.** The evidence it would be amended
  against already existed on 2026-08-18, and amending a condition after its
  evidence exists is exactly what the freeze prevents, even when the amendment
  would be an improvement. It is reported as inadequate in the result note and
  scored against as written.
- **`notes/bughunt.md` understated its own most serious row, and its closing
  section had gone false in four places.** Row 5 — the supervisor credential
  pair — read **`E under emulation`** until today. `P2-9` has carried a second
  result since 2026-08-18, `confirmed` / **`dynamic`**: on this hardware, a Basic
  header with both halves empty returns `/blank.htm` as **200 / 333 bytes,
  `sha256 bc56c91c…`, byte-identical to the real-credential body**, while a wrong
  password gets 302. The row is now `E on this hardware`. Its *What this week did
  not do* section still said the `P4`/`P5` block had not run, that no `epc` had
  been shown controllable, and that **"none of this is on silicon"** — all
  written on 2026-08-18, all false after two bench visits, in the document that
  *is* this week's deliverable. Rewritten with a dated header saying so. **This
  is the same defect as the `52869` sentences, found the same day, in the file
  the week is judged on** — which is the argument for open item 82 being real
  rather than tidy-minded.

### Deliberately not done

- **The device was not powered on.** Every prediction for the next visit is in
  `BENCH-LOG.md` 2026-08-19 §4, written before the cable.
- **`A2.5` / `A2.6` stay shut.** The three rows the previous plan said needed a
  flash write do not need one. Second session running.
- **`TASK_UNMAPPED_BASE` is not claimed.** Working back through `ld-uClibc`'s span
  gives `0x2aaa8000` from both processes; the MIPS formula
  `(TASK_SIZE / 3) & ~(PAGE_SIZE − 1)` gives `0x2aaaa000`. Two pages unaccounted
  for and no reading of this kernel to settle them, so only the *difference* is
  claimed as predicted and the tidy number is out of the report.

### Open, carried forward

66, 67, 69, 70, 71, 74, 75, 77, 78, 79, 81 — unchanged.

76. **Is `COMPDS` repaired?** Unchanged, and now it has a number attached. If
    `flash default-sw` left the factory-default block alone, the next IoC
    precheck reads **20 / 343**; if it repaired it, **4 / 343**. Two hypotheses,
    two numbers already on the record.
80. **Two reads of `COMPCS` disagreed.** Unchanged. The post-reset `/config.dat`
    is 7,490 bytes, so a station-2 `comp_len` of 7,490 settles it one way.
82. **A claim's tense outlived its measurement, and nothing checks tense.** Six
    files, one of them the disclosure register. `check-reports.py` validates that
    a report names its binary; nothing validates that a *sentence* names its
    date. Whether that is checkable at all is the open question — the mechanical
    version ("every present-tense claim about device state cites a test id and a
    date") would be a large false-positive surface.
83. **`P5-2` rests on one boot.** `A3.23.0` closes it in two `cat`s and the
    prediction is written down. Until then the `system` address is a property of
    the 2026-08-18 boot.
84. **Nothing has been jumped to.** `system` is computed, not reached, and `a0`
    would have to point at a command string — which `P5-1`'s `localPin` frame has
    not been shown to allow. Not W07's row and not scheduled.

### Where W07 stands

**Register: 58 / 58. Closed.**

| | |
|---|---|
| Closed this session | `P5-2` (desk, `partial`) |
| Open items closed | none |
| Open items opened | 82, 83, 84 |
| New instruments | `libbase.py`, `check-ci-parity.py` |
| Guard cases | +27 (libbase), +13 (parity) |
| Found, not on any list | six files dating a port state; the fifth CI divergence |

---

## W07 close, the bench half — the desk computation was right, and the row it was right about was not the interesting one — 2026-08-19

**Four boots, three rows upgraded off `na`, two open items closed, and one
finding nobody was looking for.** The register stays **58 / 58**; what changed is
the *quality* of four rows and the amount of the desk work that survived contact.

### `P5-2`: everything computed at the desk, confirmed to the byte by the device

`telnetd` was started through the `formSysCmd` injection and `/proc/<pid>/maps`
read directly, four boots after the fault messages the desk work used:

| claimed this morning | how | measured tonight |
|---|---|---|
| `libuClibc` in `boa` at `0x2aae3000` | one kernel fault message | **`0x2aae3000`** |
| `libuClibc` in `wscd` at `0x2aabe000` | **predicted** from `libapmib.so`'s program headers | **`0x2aabe000`** |
| `libapmib.so` span `0x25000` | its own `PT_LOAD`s | `2aabe000 → 2aae3000` |
| `libuClibc` span `0x46000` | its own `PT_LOAD`s | `2aae3000 → 2ab29000` |
| `TASK_UNMAPPED_BASE` `0x2aaa8000` | derived, then **withdrawn** for disagreeing with the MIPS formula | `ld-uClibc` mapped there in both processes |

`P5-2` goes `partial` → **`confirmed`**, and by the register's own literal
refutation condition rather than the stronger one the note argued for: two boots,
same base, refutation did not fire. `system` is at `0x2ab08460`.

**And the sysctl says the opposite.** `/proc/sys/kernel/randomize_va_space` reads
**2** — full randomisation — while the layout is fully determined by the ELF
files across two processes and four boots. **This device does not act on that
flag, and *why* is unread** — the obvious explanation is that MIPS had no
randomising `arch_pick_mmap_layout` at 2.6.30, and that is a hypothesis about a
kernel source nobody here has opened. It is open item 86, with a test that needs
no device. **Reading the flag and stopping would have closed this row as refuted
without one address being looked at**, which is the general lesson: a hardening
flag is a claim by a source, and a source is not a measurement. It is now
`notes/bughunt.md` row 24.

### `P6-1`: not CVE-2014-8361, and the thing that made that legible was a control

The prediction's literal words are **confirmed**: the SOAP value is concatenated
into an `iptables` command with no validation whatever. A `NewInternalClient` of
twenty-two `A` characters produces, in the device's own NAT table,
`DNAT … to:255.255.255.255:83` — `inet_addr()` returning `INADDR_NONE` and the
value being used regardless.

**Command execution did not happen.** The ICMP oracle stayed silent across two
injection attempts, and it was proved good on the same boot minutes earlier by an
independent route: a `formSysCmd` injection made the device send four echo
requests and the pcap has them. What happens instead is that **`/bin/miniigd`
terminates** — `ps` over telnet two minutes later shows no such process, which is
a *different* failure from `P6-3`'s `wscd`, where the process survived with its
listener closed. Telling those two apart is why `ps` was run rather than another
connection attempt; from outside they are the same `connection refused`.

**The control is what makes any of this a result.** The obvious reading after the
first shot was "the backtick crashes it". Twenty-two `A` characters — no
metacharacter anywhere — kill it identically, and `NewInternalClient=10.1.1.1` is
answered `200` with the daemon surviving a subsequent read. Three points: a valid
IP lives, a metacharacter value dies, a plain non-IP value dies. **Any two of
them would have supported the wrong conclusion.**

New row `D-19`, and it is **not reported and not reportable**: no prior-art search
has been run, and the mechanism is unmeasured — the unbounded `strcpy` at
`0x0044851c` is on the path and a 22-byte value is a poor fit for it.

### `P8-7`: no source check, and the other half is still open for a stated reason

`AddPortMapping` from `10.1.1.100` naming `10.1.1.1` as the internal client is
accepted `200` and reads back **unchanged**, `NewLeaseDuration=0` included. The
register's first refutation branch — the version rewrites it to the request
source — did not fire.

The second branch is the live one and it did **not** get a clean answer: the
`MINIUPNPD` chain shows `(0 references)` and `ip_forward` is `0`, **but the WAN
cable was not connected**. A router with no WAN not forwarding is not evidence
about a router with one. Recorded `partial` for exactly that, rather than
claiming the stronger reading that was available.

### `P6-5`: the flag is back, the helper is absent, the packet was not sent

`ALG_SIP_ENABLED` reads `1` after the reset, so the 2026-08-18 blocker is gone.
`/proc/net/nf_conntrack_expect` is empty, `/proc/sys/net/netfilter/` holds only
the generic, icmp, tcp and udp knobs with **no SIP entry**, and `/proc/modules`
does not exist — this kernel has no loadable modules, so a helper is compiled in
or absent, and nothing named SIP is compiled in. That is stronger than the
previous reading, which rested on the flag being `0`. It is still not an answer:
the vector is one UDP packet to 5060 **from the WAN**, there was one cable and it
was in a LAN port, and the register's refutation could not have fired. `partial`.

### Open items 76 and 80, both closed by one station-2 dump

- **76 — is `COMPDS` repaired?** **Yes, and the prediction written before the
  cable was wrong.** `flash default-sw` rewrote **both** regions from hard code:
  `COMPDS` payload `sha 8d84f2c7…` and `COMPCS` payload `sha e09cbf84…`, each
  byte-identical to the 2026-08-16 read. The IoC precheck reads **4 / 343** with
  the same four field names it had before 2026-08-17. **`P0-5`'s baseline, which
  this project destroyed with its own unauthenticated POST round, was restored by
  the vendor's reset button.** The prediction said 20 / 343 on the reasoning that
  `default-sw` writes only the live region; that reasoning was wrong and the
  refutation condition was written to catch it.
- **80 — two reads of `COMPCS` disagreed.** Closed, and the answer is neither of
  the two options the item offered. Post-reset, `/config.dat` (7,490 bytes) is
  byte-identical to `flash[0:7490]`. Pre-reset, on 2026-08-18, **7,009 of 7,510
  bytes differed and the divergence starts at `+0xb`** — inside the `comp_len`
  field itself. So the boot does not rewrite the region: **`/config.dat` is not
  served from the flash blob at all**, and the two agree only when flash and the
  live MIB agree. `A3.6`'s headline chain holds where it was measured and is not
  the general statement it reads as.
- **`P9-9`'s own NOT-done item** is closed too: `H601` at `0x006000`, 8,192 bytes,
  **byte-identical** to the 2026-08-16 read. `P9-9` had only `flash allhw`'s
  decoded values, which is a second source; this is the authoritative one.

### Instrument work

| | |
|---|---|
| `tools/upnp-soap.py` | new. Reads the control URL out of the device's description document rather than typing it, refuses an action it does not know, and separates a benign run from an injection by flag rather than by string |
| `--arg-file` | added **during** the session, because the first `P6-1` attempt was destroyed by the local shell expanding a backtick payload: 431 bytes of a local `ping`'s stdout went out instead of 25. Same defect the `P9-9` result note records, one day later and one tool over |
| `tools/test-upnp-soap.sh` | 14 cases against a local server, including that `--arg-file` reads bytes verbatim and refuses without `--inject` |
| `runsheet.md` `A3.15` | rewritten from prose to the commands that were actually run, with the cost model corrected: the unit of this section is a power cycle, not a request |

### Corrections to the plan

- **The pre-cable prediction for open item 76 was wrong**, and it is left in
  `BENCH-LOG.md` as written with the refutation firing against it. The reasoning
  that failed is named: `/bin/flash`'s usage text separates `default` from
  `reset`, and "write all flash parameters from hard code" was read as scoping to
  the live region. `-sw` is wider than that.
- **`A3.15` said "delete the mapping in the same section" and that was not
  possible.** A dead daemon cannot be sent `DeletePortMapping`. Both mappings were
  removed by power cycles, and the record card says so rather than claiming the
  clean version.

### Deliberately not done

- **The WAN phase.** `P6-5`'s vector and `P8-7`'s second half both need the cable
  in the WAN port, and the session stopped at 03:00 with the predictions written
  down instead. That is a W08 item and it is one trip, not two.
- **Bisecting what kills `miniigd`.** Each attempt costs a power cycle. Three
  points were enough to refute "it is the metacharacter"; a fourth would need a
  prediction written first, and it was not.
- **The prior-art search for `D-19`.** Not started, so the item is not reportable.

### Open, carried forward

66, 67, 69, 70, 71, 74, 75, 77, 78, 81, 82, 84 — unchanged.

- **76, 80 — closed.** See above.
- **79 — `A UART adapter on the header stops this board booting`.** *Not closed,
  and one clean boot does not close it.* The only thing done differently was
  reseating the three jumpers, GND especially, which is what `A2.2`'s hypothesis
  names. One success supports it and cannot prove it.
- **83 — `P5-2` rests on one boot.** **Closed.** Four boots, same base.
- 85. **Why does `miniigd` die?** The unbounded `strcpy` at `0x0044851c` is on the
  path and a 22-byte value is a poor fit for it, so the mechanism is unknown.
  Each hypothesis costs a power cycle to test, so the next attempt needs its
  prediction written first.
- 86. **`randomize_va_space` reads 2 and nothing is randomised.** Measured, not
  explained. Reading this kernel's `arch_pick_mmap_layout` would turn an
  observation into an explanation, and it needs no device.
- 87. **`/config.dat` is not the flash blob.** Which code path serves it is
  unread, and `A3.6`'s chain is described in this repository as one of its
  strongest. It holds where measured; the general form does not.
- 88. **`MINIUPNPD` has `(0 references)` with no WAN.** Whether a WAN lease
  installs the jump from `PREROUTING` is untested, and `P8-7`'s severity depends
  entirely on it.

### Instrument bug 45 — the checker written to catch a broken workflow shipped a workflow that would not parse

`tools/check-ci-parity.py` was written earlier the same day to stop `make ci` and
`.github/workflows/ci.yml` drifting apart for a sixth time. The commit that added
it also added a step to the workflow:

```
      - name: `make ci` and this file run the same suites
```

**A backtick cannot start a YAML plain scalar.** GitHub failed the entire run in
**0 s** — not a step failure, a parse failure, so no job started and no log
exists to read. `make ci` had been green, `check-ci-parity.py` had been green,
and both were green *on a file the real consumer cannot read*.

**The reason is one line of design and it generalises past this repository: the
checker reads the workflow with a regular expression, and a regular expression
does not care whether the document is valid.** Any local checker that parses a
config file with a pattern will pass on a file the real consumer rejects, and it
will do so most confidently on exactly the change that broke it.

Fixed by showing the file to a parser: `workflow_parses()` runs `yaml.safe_load`
and refuses everything downstream when it throws, printing *"nothing below this
line means anything until that is fixed"*. Where PyYAML is unavailable it returns
`None` and the run reports **skip**, not ok — a check that could not run has not
run. Three guard cases, one of them the exact line that shipped.

**And it was the fourth time in one session that a backtick destroyed something.**
The first cost a test and a power cycle (`P6-1`, the payload expanded by the local
shell); the second and third were a heredoc and a `sed` expression that executed
`make ci` mid-command; this one cost a red remote build. The memory note for this
harness now carries the rule that a payload must never appear on a command line —
and the wider version, which this bug is the proof of, is that **a backtick is
never inert: some layer between the keyboard and the destination will run it.**

**And the fix had the same shape as the bug, one layer down.** `workflow_parses()`
uses PyYAML, **which a GitHub runner's `setup-python` does not ship** — so on the
remote, the check that exists to validate this workflow reported *"the workflow
was NOT parsed"* and skipped. Honestly reported, and skipped in **exactly the
environment whose parser is about to judge the file**. Two of the new guard cases
then failed there while passing on WSL, which is what surfaced it: the suite went
red remotely on a repository whose `make ci` was green.

Fixed twice over, because the two halves are different problems. The workflow now
installs PyYAML, so the parse check actually runs where it matters. And the guard
suite **skips** those two cases when no parser is present rather than failing or
quietly dropping them — verified by shimming `yaml.py` to raise `ImportError`,
which produces `14 passed, 0 failed, 2 skipped` and a checker line reading `skip`
rather than `ok`.

*The general form, and it is the third time this session:* **a check that degrades
to a skip has not run, and the environments where it degrades are not random —
they are the ones with the fewest tools, which are usually the ones that matter.**

*Found by:* `gh run list` after the push. `make ci` could not have found it, and
that is the point of checking the remote rather than trusting local green — the
same rule `RUNBOOK` 10.21 records and the one this checker exists to enforce.

### Where W07 stands

**Register: 58 / 58. Closed. DoD 5 of 6** — the six-build differential harness was
never built, and `notes/bughunt.md` has said so with its reason since 2026-08-18.

| | |
|---|---|
| Upgraded this session | `P5-2` → `confirmed`; `P6-1`, `P8-7`, `P6-5` off `na` |
| Open items closed | 76, 80, 83, and `P9-9`'s own NOT-done `H601` comparison |
| Open items opened | 85, 86, 87, 88 |
| New instruments | `upnp-soap.py` + 14 guard cases |
| `notes/bughunt.md` | 22 → **24** rows |
| Disclosure register | `D-19` added, **unsearched and unreported** |
