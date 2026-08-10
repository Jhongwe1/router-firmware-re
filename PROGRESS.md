# Progress

| Week | Theme | Gate | Status |
|---|---|---|---|
| **W01** | Recon & unpacking | **G0 + G1** | ✅ **passed** — 2026-08-07 |
| W02 | Hardware access: UART + SPI dump | G2 | ⏸ blocked on hardware delivery |
| **W03** | Static reversing, upper half | — (DoD) | ✅ **DoD met** — 2026-08-10 |
| W04 | CVE root-cause location | G3 | ▶ next — most of G3 already answered |
| W05 | Dynamic analysis, upper half | — | |
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
   it is registered nowhere.**
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
