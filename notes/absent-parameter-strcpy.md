# The absent parameter, the read-only literal, and the one that gives you `$pc`

**Question carried out of W06:** `P4-1` predicted that omitting `submit-url`
from a POST makes the handler `strcpy` into a read-only page — a one-request,
zero-payload, unauthenticated denial of service. It was recorded **`refuted`**
on the device on 2026-08-17, and `bughunt.md` row 18 wrote the whole
`submit-url` class off on this build.

**Answer: the refutation was correct for the sample and the sample was not the
population.** The mechanism is live on this build. It is in **five** of the 57
handlers, all five fault at the same instruction storing to the same address,
and one of the three handlers W06 tested does not reach that code at all.

Everything below is emulated (`tools/qemu-env.sh` + `tools/alignfix/`) or
static. **Nothing here has been measured on the device and nothing has been
reported to anyone.** The bench step that settles it is `runsheet.md` `A3.23`.

---

## 1. The five, and the address they share

| handler | its redirect parameter | `ra` at the fault |
|---|---|---|
| `form_formSchedule` | **`webpage`** | `0x00445974` |
| `form_formAdvanceSetup` | `submit-url` | `0x0044740c` |
| `form_formDnsv6` | `submit-url` | `0x00459f4c` |
| `form_formOpMode2` | `submit-url` | `0x00452814` |
| `form_formSSH` | `submit-url` | `0x004546bc` |

All five: `pc = 0x2b32721c` (uClibc's `strcpy` inner loop), faulting instruction
`sb v1,0(a2)`, store target **`0x004725d0`**, source `a1 = 0x00466cd9`
(`"/status.htm"` at `0x00466cd8`).

→ [`reports/crash-triage-unit-2018.json`](../reports/crash-triage-unit-2018.json)

`0x004725d0` is the pooled empty-string literal. Two independent facts pin it:

* `tools/mipsref.py --addr 0x004725d0` returns **815 references**, every one an
  `addiu` low-half — the shape of a constant whose address is taken, not of a
  variable;
* it lies inside the **first** `PT_LOAD`, `0x00400000`–`0x00473044`, mapped
  **`R-X`**. The writable segment starts at `0x00483044`.

So the store faults **by protection**. That matters more than it looks: the
device's MIPS kernel fixes up *unaligned* user-space accesses — that is what
`tools/alignfix/` exists to reproduce — but it does not fix up a write to a
read-only page. **This is one of the few emulated crashes whose mechanism
transfers to silicon by construction rather than by hope**, and it still has to
be measured there.

## 2. The instruction, and the control that makes it an argument

```
445950:  lb    v0,0(s2)          ; is the buffer the accessor returned empty?
445958:  bnez  v0,0x44597c       ; not empty -> skip
445960:  lw    t9,-31080(gp)     ; t9 = strcpy
445968:  addiu a1,a1,27864       ; a1 = 0x466CD8 = "/status.htm"
44596c:  jalr  t9
445970:  move  a0,s2             ; delay slot: destination = s2
445974:  lw    gp,16(sp)         ; <- the ra observed at the fault
```

This is the `(A)` half of the idiom [`submit-url-overflow.md`](submit-url-overflow.md)
recovered from V2.1.2 in W04:

```c
pcVar1 = req_get_cstream_var(param_1, "submit-url", "");
if (*pcVar1 == '\0') { strcpy(pcVar1, "/status.htm"); }   /* (A) */
strcpy(&lastUrl, pcVar1);                                  /* (B) — the CVEs */
```

**The control is the sixth case and it costs nothing.** Send
`webpage=` — *present and empty*. The same branch is taken, `*s2` is still
`'\0'`, `strcpy` still runs — and the server survives with a 302. The only
difference is where `s2` points: into the request's own writable parse buffer
instead of into `.rodata`.

> **So the finding is not "this handler crashes". It is "the accessor's default
> for an absent parameter is the address of a literal, and the code writes
> through it".** A crash is what that looks like from outside.

## 3. Why W06 refuted it, and why that was not a mistake

`P4-1` was tested on `formNtp`, `formWlanSetup` and `formSelLang` with
`submit-url` omitted. All three survived, on the device, repeatedly. That
measurement stands.

What it could not see: **47 of the 57 handlers carry the `submit-url` idiom and
only 4 of them reach `(A)` on a parameter-free POST.** The other 43 return
earlier — a missing mode, a missing index, a table lookup that fails. So three
handlers drawn from 47 had roughly a 1-in-4 chance each of landing on one that
reaches it, and none did.

**The fifth, `formSchedule`, could not have been found that way at all**, because
its parameter is not `submit-url`. It dies with a perfectly well-formed
`submit-url` present.

> This is the third of this project's own results to be overturned, and the
> first overturned by **widening the sample rather than by correcting an
> instrument**. The lesson is not "the earlier test was sloppy" — it is that a
> refutation inherits the coverage of the thing that produced it, and three
> hand-picked handlers is a coverage nobody wrote down.

## 4. `formWsc` / `localPin` — a different defect, in the same sweep

The length ladder found one handler that dies on a **long** value rather than an
absent one, and it is not in the five:

```
localPin = 260 bytes   ->  survives
localPin = 800 bytes   ->  pc = ra = s0..s6 = 0x41414141
```

A de Bruijn pattern reads the frame straight off:

| offset | register |
|---|---|
| 481 | `s0` |
| 485 | `s1` |
| 489 | `s2` |
| 493 | `s3` |
| 497 | `s4` |
| 501 | `s5` |
| 505 | `s6` |
| **509** | **`ra`** — and `$pc` is loaded from it |

`s7` is untouched (`0x0048bb04`), so the frame saves `s0`–`s6` and `ra`. 509 is
consistent with `BoaGate`'s own report of `sp-540` for this parameter.

**Unauthenticated, one POST, no chain: full control of the program counter and
of seven saved registers**, on a binary with no stack canary, no `PT_GNU_RELRO`,
no PIE and an `RWX` `GNU_STACK` — in all three N150RT builds.
→ [`reports/crash-triage-unit-2018-wsc.json`](../reports/crash-triage-unit-2018-wsc.json)

**What this is not.** It is not an exploit: nothing has been jumped to, no
payload exists, and the address space under `qemu-user` is not the device's. It
is not known to be new — `localPin` is the parameter CVE-2019-19824 names for
*command injection*, and whether anyone has reported an overflow on it has not
been searched yet. And it is not measured on hardware.

The request itself is deliberately **not** in this repository, under the same
rule as `D-15`: it lives in `$FWRE_WORK/disclosure/`, outside the tree.

## 5. What this changes in the instruments, today

`tools/bench-probe.py` refuses to POST to `/boafrm/*` without `submit-url`, and
its docstring cites `submit-url-overflow.md` as the reason. **That guard has
exactly one hole and it is the handler that most needs it**: `formSchedule`
reads `webpage`, so the guard waved it through — and `formSchedule` is also the
one that dies *with* a well-formed `submit-url`. The guard is now keyed on a
per-handler map (`REDIRECT_PARAM`) rather than on one name.

## 6. How the first version of this note was wrong

The first version said the five handlers die because the *`webpage`* parameter
is absent, and generalised from `formSchedule` alone. That was wrong twice
over: four of the five take `submit-url`, and the `webpage` spelling is unique
to one handler in all 57. The correction came from the sweep's own data — the
`absent` dimension names the parameter per handler — and not from re-reading
the binary, which is the order this project keeps getting right by accident and
should do on purpose.

It also asserted, for about ten minutes, that `serve` was failing because a
running guest held `alignfix.so` open (`ETXTBSY`). That was tested and refuted:
the build succeeds while `boa` runs. The real cause was a nested `sudo` moving
`$ENVDIR` to `/root/fwre-work` — instrument bug 44, and the refusal that names
it was sitting one check *below* the one that fired.
