# Reading the builds across: 2015, 2018, 2020

**Question carried out of W02 (open #4):** `/bin/boa` on this unit was extracted
and hashed but never read. Every `boa` claim in this repository describes
V2.1.2 or V3.4.0 — two binaries this device has never executed.

This note is the transfer. It measures the same things on the resident build
that W03/W04 measured on the two published ones, and it says which claims moved
across and which did not.

> **Section 1 was written and committed before any measurement script was run
> against the 2018 binary.** That ordering is the point: a prediction recorded
> after the fact is a description. The commit timestamp is the evidence.

---

## 1. Predictions, written 2026-08-16 before the tools ran

The binary under test: `/bin/boa` from this unit's flash,
`sha256 19fe29d71aa1cc1e893627f17a0f14b03ca75f6936318df4062df4fb153909f7`,
485,012 bytes, self-identifying as `boa: server built Jan 10 2018 at 14:57:54`.

**The build it belongs to is `TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002`**
(`/etc/version`, same rootfs), and this note's `unit-2018` label is named after
the binary timestamps rather than that string — the two are seven weeks apart
and why is `PROGRESS.md` open #4. The label is the convenient identifier; **the
version string is the searchable one**, and reading past it cost this project
CVE-2024-51228 for two weeks ([`prior-art.md`](prior-art.md)).

| Measurement | 2.1.2 (known) | **unit-2018 (predicted)** | 3.4.0 (known) |
|---|---|---|---|
| `root_form[]` entries | 59 | **55–59** | 49 |
| `formSysCmd` in the table | no | **no** | no |
| `formWsc` in the table | yes | **yes** | yes |
| `strcpy` call sites | 587 | **500–600** | 577 |
| `submit-url` idiom, handler count | 34 | **28–34** | — |
| `lastUrl` size | 100 | **100** | — |
| `AUTHG_*` in the MIB table | present | **present** | absent |
| the authorisation gate | `strstr(uri, "htm")` | **like 2015** | `.htm`/`.asp`/POST |

### Why these numbers

The 2018 `boa` is 485,012 bytes, between 2015's 522,556 and 2020's 404,904.
Size alone would put it midway. But the flash layout is not midway — it is
**2015's**: this unit has a `w6cg` web-resource section and its kernel is at
`0x060000`, the arrangement the 2020 image abandoned
([`flash-layout.md`](flash-layout.md) §3). Its SquashFS is LZMA like 2015, not
XZ like 2020.

So the prediction is not "halfway between". It is **a late member of the 2015
family**: closer to 59 than to 49, still carrying `AUTHG_*`, still gating on a
bare `htm` substring.

### One prediction in that table is nearly worthless, and it should be said now

**`root_form[]` at 50–59 would have been a non-prediction.** The two known
values are 49 and 59; an interval that spans everything except the low endpoint
cannot fail in any interesting way. It has been tightened to **55–59** on the
strength of the layout evidence above — which makes it able to be wrong, in the
direction that would matter: if the 2018 table has come down into the low 50s,
this build has already started shedding the handlers the 2020 build dropped, and
"a late member of the 2015 family" is the wrong description of it.

The same objection does not apply to `strcpy` at 500–600: that interval brackets
both known values because the honest expectation is "this is the same codebase",
and the informative outcome is a number **outside** it, which would mean either a
real rewrite or — far more likely, on this project's record — the PLT bug again.

### The falsifiable specifics

Interval predictions are cheap. These are the ones that name a thing:

1. **The four handlers W04 left open** — `formDdns`, `formNewSchedule`,
   `formSysLog`, `formWanTcpipSetup` carry the `submit-url` idiom in 2015 and do
   not show it in 2020 while still existing (W04 open #5). **Predicted: all four
   present in the 2018 table and all four still carrying the idiom.**
2. **`formWsc`'s `localPin` line** — `sprintf(buf[100], "flash set
   HW_WLAN0_WSC_PIN %s", localPin); system(buf)` is byte-for-byte identical in
   2015 and 2020. **Predicted: present and unchanged in 2018.** If it is, then
   the line reaches from 2015 to 2020 through a build made by different people in
   between, and CVE-2025-3987/4462 describes something that survived three
   independent release cycles.
3. **`/bin/skt` is deleted from this rootfs but `#skt&` is still in `rcS`**
   (measured in W02). **Predicted: `boa` itself is untouched by that change** —
   no `skt` string, no reference, in any of the three.

### What would make this whole exercise suspicious

If every prediction lands, the correct response is not satisfaction. Three
builds spanning five years, and the middle one made by a different team on a
different day, agreeing on **every** measurement, is more consistent with a tool
reporting the same thing regardless of input than with the firmware. This
project has been burned that way three times, and the tell each time was
agreement, not disagreement.

So the self-check runs first, before the table is filled in: any import whose
call-site count falls to 0 or 1 stops the day. `sstrip`'d-PLT false negatives
have appeared **twice** (`BoaSinks` in W03, `BoaArgTrace` re-implemented in W04),
and the 2018 binary is a third opportunity.

---

## 2. Measurements — 2026-08-16

| Measurement | 2.1.2 | **unit-2018** | 3.4.0 | predicted | |
|---|---|---|---|---|---|
| `root_form[]` entries | 59 | **57** | 49 | 55–59 | ✅ |
| `formSysCmd` in the table | no | **YES** | no | no | ❌ **§2.1** |
| `formWsc` in the table | yes | **yes** | yes | yes | ✅ |
| `strcpy` call sites | 587 | **564** | 577 | 500–600 | ✅ |
| `submit-url` idiom, handlers | 34 | **32** | 27 | 28–34 | ✅ |
| `lastUrl` size | 100 | **100** | — | 100 | ✅ |
| `AUTHG_*` in the MIB table | 4 | **2** | 1 | present | ❌ **§2.4** |
| the authorisation gate | `strstr(uri,"htm")` | **`.htm` or `.asp`** | `.htm`/`.asp`/POST | like 2015 | ❌ **§2.4** |

Three predictions failed. **That is the useful half of the table** — a week in
which every old conclusion transferred cleanly would mean the comparison was
never really done. The two structural ones failed together and for one reason,
which is §2.4.

Regenerate: `analyze.ps1 -Label <label> -Script BoaFormTable|BoaSinks|BoaArgTrace|BoaMnemonics -Binary <boa>`
→ [`reports/`](../reports/).

### 2.1 The prediction that failed loudest: `formSysCmd` is here

It is entry `0x004838a8` in `root_form[]`, handler `0x0044ee2c`, and it is in
**neither** published image.

| | 2.1.2 | **unit-2018** | 3.4.0 |
|---|---|---|---|
| `grep -aoc formSysCmd` on the raw binary | **0** | **1** | **0** |
| in `root_form[]` (`BoaFormTable`) | no | **yes** | no |

Two instruments that share no code. Absent → **present** → absent.

**W04's reading of this is withdrawn.** G3 box 1 recorded the handler's absence
from V2.1.2 as "the vendor's fix", reasoning from dates: V2.1.2 ships after the
last build Pierre Kim reports as vulnerable. A fix does not reappear two and a
half years later. The evidence now supports what W04 explicitly dismissed —
a **build-time option**, present or absent per release rather than removed once.

It also reverses the direction of the advisory question. CVE-2019-19824 lists
"N150RT through 3.4.0" as affected; W03 and W04, reading the two images anyone
can download, concluded the handler was not there. **Both downloadable images
happen to be ones without it.** Anyone reproducing that CVE against this model
from published firmware would conclude "not affected", and would be wrong about
the unit on this desk.

What the handler does, and why it is reachable unauthenticated, is
[`auth-flow-2018.md`](auth-flow-2018.md) §2.

### 2.2 The falsifiable specifics — all three landed

**1. The four handlers W04 left open.** W04 open #5 asked whether `formDdns`,
`formNewSchedule`, `formSysLog` and `formWanTcpipSetup` lost the `submit-url`
idiom in 2020 because they were rewritten, or because a six-hop walk missed it.

| | 2.1.2 | **unit-2018** | 3.4.0 |
|---|---|---|---|
| of those four, carrying `submit-url` | **4** | **4** | **0** |

Same tracer, same `depth:6`, three builds. It finds all four twice and none the
third time. **Rewritten, not a walk limit — W04 open #5 is closed.**

**2. `lastUrl[100]`, then `needReboot`.** From the dynamic symbol table, which
is not Ghidra:

```
2.1.2       0049087c  100  OBJECT  lastUrl        0049087c + 100 = 004908e0
            004908e0    4  OBJECT  needReboot
unit-2018   0048b8ac  100       D  lastUrl        0048b8ac + 100 = 0048b910
            0048b910    4       D  needReboot
            0048b914    4       D  run_init_script_flag
```

Identical shape, different addresses. Ghidra put `lastUrl` at `0x0048b8ac`
independently, with 53 references to it.

**3. `boa` is untouched by the `/bin/skt` deletion.** No `skt` string or
reference in any of the three. The 2018 build deleted the binary and left `#skt&`
in `rcS`; `boa` never knew about either.

### 2.3 Two numbers that were not predicted and should have been

**`system()` call sites: 158 → 194 → 129.** The resident build has more calls to
`system()` than either published image, in *fewer* functions (764 against 813).
No prediction was written for this because the prediction table only listed
`strcpy`. It is consistent with `formSysCmd` being compiled in, but 36 extra
call sites is far more than one handler, and the rest are unaccounted for.
Recorded as an open question rather than explained.

**`sprintf`: 694 / 700 / 694.** Flat across ten years, which is its own comment
on how this codebase was maintained.

### 2.4 Why the two structural predictions failed together

The prediction said "a late member of the 2015 family", reasoning from the flash
layout: this unit has a `w6cg` section, its kernel is at `0x060000`, its
filesystem is LZMA. Every one of those is true and the conclusion was still
wrong.

| axis | which build does 2018 resemble? |
|---|---|
| flash layout, `w6cg`, kernel offset | **2015** |
| SquashFS compression (LZMA) | **2015** |
| `root_form[]` size, `submit-url` idiom, `lastUrl` | **2015** |
| `sstrip`'d, no section headers | **2020** |
| `AUTHG_IP_ADDR` removed from the MIB table | **2020** |
| gate keyed on `.htm`/`.asp` rather than bare `htm` | **2020** |
| `formSysCmd` present | **neither** |

**Packaging and handler code are 2015's; the authorisation path and the build
flags are 2020's.** The lesson is narrow and worth keeping: *structural* family
resemblance — how the image is packed, which compressor, where sections sit —
predicts nothing about *which functions were edited*. They are decided by
different people at different times.

### 2.5 The instrument check ran first, and it caught something

Per §1, the self-check ran before the table was filled in. Sink counts are
consistent across builds (`strcpy` 587 / 564 / 577, `system` 158 / 194 / 129,
21 sinks each, `self_check: consistent`), and the sinks reporting zero report
zero in **all three** — `alloca`, `execle`, `execlp`, `execvp`, `gets`, `scanf`,
`strncat`, `vsprintf`. A real absence, not a resolver failure.

That matters more here than in W03 or W04, because **the 2018 binary is
`sstrip`'d and has no section headers** — the exact condition that produced the
PLT false negatives twice:

| | 2.1.2 | **unit-2018** | 3.4.0 |
|---|---|---|---|
| static symbol table (`nm`) | none | none | none |
| dynamic symbols (`nm -D`) | 436 | **422** | 202 |
| section headers (`readelf -S`) | 29 | **none** | none |
| `handleForm` / `lastUrl` exported | yes | **yes** | no |

So the resident build is stripped like 2020 and *named* like 2015 — which is why
`BoaFormTable` recovered 95 handler names from it without an accessor override,
and why `readelf --dyn-syms` returns nothing for it while `nm -D` returns 422.
Those two are not independent sources on a file in this state; Ghidra and `nm -D`
are, and they agree on `lastUrl`.

**What the check did catch was in the tracer, not the firmware**, and it is
written up in [`PROGRESS.md`](../PROGRESS.md) § Instrument work: unifying the
tracer's spec across the three builds to make their scope counts comparable
silently dropped V3.4.0's accessor override, and its tainted-site count went
49 → 0 with `self_check: consistent`. Same 86 → 0 shape as W04, arriving this
time through how the tool was *called*.

### 2.6 The `lwl` census, and the asymmetry that is the whole answer

New instrument: [`BoaMnemonics.java`](../ghidra/scripts/BoaMnemonics.java).

| | 2.1.2 | **unit-2018** | 3.4.0 | 2018 busybox |
|---|---|---|---|---|
| instructions | 98,873 | 96,040 | 77,542 | 59,283 |
| `lwl`+`lwr`+`swl`+`swr` | **174** | **142** | **0** | **0** |
| coprocessor 2/3 encodings | 0 | **0** | 0 | 0 |
| bytes never decoded | 4,020 (1.01%) | 9,891 (2.10%) | 11,671 (2.94%) | 6,664 (2.48%) |

**The zero that matters most is the coprocessor column.** Lexra's added
instructions — the MAC group, `lt`/`st`/`ltp`, the RADIAX DSP set — live in
opcode space that standard MIPS reserves for coprocessors 2 and 3, which
Ghidra's stock MIPS module *will* decode into something plausible. That is a
silent failure mode sitting underneath every static result in this repository
since W03, and it had never been named. There are none, in any of the four
binaries. The risk was real and it did not materialise; testing it is the point.

**On `lwl` itself, the direction of the evidence is not symmetric:**

- **142 present in the binary this unit runs** — a compiler emitted unaligned
  accesses for this target. That is evidence the toolchain believed the core
  supports them.
- **It is not yet proof the silicon does.** Nothing here shows any of those 142
  sites *executes*. The device boots and `rcS` starts `boa`, but a trapping
  instruction on a cold path would never be reached. BusyBox from the same image
  has **zero**, so "everything in this firmware uses them" is false.
- **Zero would have proved nothing at all** — `-mno-unaligned` and friends
  produce an identical count on a core that supports them perfectly well. V3.4.0
  has zero, and that is a fact about its toolchain, not about any CPU.

**The experiment that settles it is now available and was not before.**
W02 open #6 wants RLX4181 against RLX5281 and records that `/proc/cpuinfo` would
answer it "and there is no shell to run it from". §2.1 has just supplied one:
`POST /boafrm/formSysCmd` with `sysCmd=cat /proc/cpuinfo`. That is a W05 action,
listed here so the connection is on record before it is run.

**And it retires a wrong premise in the W05 plan.** That plan blocks out time for
FirmAE trouble because "Lexra ≠ standard MIPS — missing unaligned load
instructions → FirmAE support is unstable". The reasoning is backwards: a subset
always runs on a superset's emulator, `qemu-mips` implements full MIPS including
`lwl`/`lwr`, and W01 already ran `/bin/boa --help` under `qemu-mips-static`. What
actually blocks emulation is `libapmib` reading `/dev/mtdblock0`, the vendor
kernel modules and the NIC driver — none of it about the instruction set. A wrong
reason stops you in the wrong place.

---

## How the first version of this note was wrong

**Its predictions were wrong three times out of eight, and the interesting part
is that two of the three failed for a single shared reason** (§2.4): the
prediction reasoned from *packaging* to *code*, and on this build those two came
from different places. Recorded rather than quietly rewritten, because the
prediction's reasoning was spelled out in §1 precisely so its failure would be
diagnosable.

**One prediction was withdrawn before it was tested, and it should not have
been in that form at all.** The plan's `root_form[]` interval was 50–59, which
spans everything between the two known values except the low endpoint. §1
tightened it to 55–59 and said why. The answer was 57 — inside both, so the
tightening cost nothing and proved nothing. **A prediction that survives because
the measurement landed mid-interval has not been tested either.** The specific
predictions in §2.2 are the ones that carried weight, and future weeks should
write more of those and fewer intervals.

**And one claim in an earlier draft of this note was simply false.** It said the
2018 build "kept its symbol table". It has no static symbol table at all — no
build here does. What it kept is a 422-entry *dynamic* table while being
`sstrip`'d, which is a different and more useful fact (§2.5). The error came from
seeing Ghidra resolve `handleForm` by name and inferring the mechanism instead of
checking it; `nm` says `no symbols` on all three.
