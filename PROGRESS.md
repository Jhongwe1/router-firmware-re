# Progress

| Week | Theme | Gate | Status |
|---|---|---|---|
| **W01** | Recon & unpacking | **G0 + G1** | ✅ **passed** — 2026-08-07 |
| W02 | Hardware access: UART + SPI dump | G2 | ⏸ blocked on hardware delivery |
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
2. Real flash part and size (W02).
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

1. Which firmware build is on my unit — only a flash dump decides (W02).
2. Real flash part and size (W02).
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
