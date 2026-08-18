# Where uClibc is mapped on this unit, and how that was read off two console lines

**Answer first.** On the unit running
`TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002`, `libuClibc-0.9.30.3.so` is mapped at
**`0x2aae3000`** in `boa` and at **`0x2aabe000`** in `wscd`, and `system` is
therefore at **`0x2ab08460`** in `boa` (`st_value` `0x25460`).

**Those numbers were computed before they were measured, and that ordering is
the point.** §1–§4 derive them from two kernel fault messages already sitting in
`BENCH-LOG.md` — recorded on 2026-08-18 for other rows — plus the ELF files, with
nothing sent to the device. §5 is the device printing its own `/proc/<pid>/maps`
four boots later and agreeing to the byte, including on a base that was
*predicted* rather than observed.

| | |
|---|---|
| register row | `P5-2` — **confirmed** 2026-08-19; `partial` until the maps read, and §5 says why |
| instrument | [`tools/libbase.py`](../tools/libbase.py), 27 guard cases in [`tools/test-libbase.sh`](../tools/test-libbase.sh) |
| report | [`reports/libbase-unit-2018.json`](../reports/libbase-unit-2018.json) |
| desk inputs | `BENCH-LOG.md` `T-50` (wscd) and `T-60` (boa), both station 3 boot 2 (cycle 3), 2026-08-18 |
| device check | `BENCH-LOG.md` `T-83`, 2026-08-19, `/proc/350/maps` and `/proc/217/maps` |

---

## 1. The two lines

Neither of them names a library. That is the whole problem.

```
do_page_fault() #2: sending SIGSEGV to wscd for invalid read access
         from 4187c8bc (epc == 2aae1f38, ra == 2aae1e64)
do_page_fault() #2: sending SIGSEGV to boa for invalid write access to
         004725d0 (epc == 2aafe218, ra == 00445974)
```

`boa`'s `ra` is inside `boa`'s own text, which is not relocated — the binary is
`ET_EXEC` at `0x00400000`. Both `epc` values, and `wscd`'s `ra`, are in the
`0x2aaxxxxx` range where this kernel puts shared libraries. Turning one of those
into a base needs a symbol to anchor it, and picking the symbol is where this
can go wrong quietly.

## 2. The four bytes that make the device and qemu-user agree

`P5-6` fired the same request under `qemu-user` and got a fault the triage
report records with its disassembly:

```
0x2b327214:  addu  a2,a1,a0
0x2b327218:  bnez  v1,0x2b32720c
0x2b32721c:  sb    v1,0(a2)        <= faulting
```

So qemu says the faulting instruction is at `strcpy+0x1c` and the device says
`epc` is `strcpy+0x18`. Four bytes apart, on what is supposed to be the same
fault.

They are the same fault, and the difference is **predicted**: the store sits in
the **delay slot** of the `bnez` above it, and on MIPS a fault taken in a delay
slot sets `Cause.BD` and leaves `EPC` on the *branch*, because restarting
execution has to re-execute the branch. The console line does not print `BD`, so
`tools/libbase.py` carries both readings until one of them resolves.

That is also the control. The two words are read back out of `libuClibc` at the
derived offsets and decoded independently of Ghidra and of qemu:

| offset | word | decodes as |
|---|---|---|
| `strcpy+0x18` | `0x1460fffc` | `bne v1,$zero,…` → `bnez v1` |
| `strcpy+0x1c` | `0xa0c30000` | `sb v1,0(a2)` |

Same source register `v1` in both. If those bytes were anything else, "the fault
is in `strcpy`" would be an assumption and every address in this note would be
void; the tool refuses to build the report, and `check-reports.py` refuses the
file, when `control_ok` is not true.

## 3. Choosing `strcpy` is a measurement, not a recollection

An implied base must be page-aligned, because that is what `mmap` returns. That
filter is worth publishing rather than asserting, because its selectivity is
`size / 4096` per symbol and for a 40-byte function that is about 1%:

| filter | survivors |
|---|---|
| dynamic symbols in `libuClibc` | **663** |
| …admitting a page-aligned base for `0x2aafe218` | **22** |
| …putting a *store* at the `epc` or in the delay slot of a branch there — which is what `invalid **write** access` requires | **5** |
| …matching qemu-user's instruction pair (`bnez R` then `sb R,0(reg)`) | **1** |

The five are `strcpy`, `if_indextoname`, `putc`, `fputc` and `vfscanf`. The last
step is the only one that is not a property of this file — it is a second
executor, on a different host, of the same input — and it is what separates a
second observer from a second guess.

## 4. The prediction that could have failed

The two processes do **not** share a base, and expecting them to is the trap
(§6). They link different libraries:

```
boa   NEEDED: libapmib.so, libc.so.0, libgcc_s.so.1
wscd  NEEDED:              libc.so.0, libgcc_s.so.1
```

If the loader allocates bottom-up and nothing is randomised, then the two `libc`
bases differ by exactly the mapped span of the one object that differs — and
that number comes from `libapmib.so`'s own program headers, with no reference to
either fault:

```
LOAD  vaddr 0x00000000  memsz 0x0a554   R-X
LOAD  vaddr 0x0001b000  memsz 0x09b00   RW-     -> 0x24b00, page-rounded 0x25000
```

**Predicted:** `0x2aae3000 − 0x25000 = 0x2aabe000`.
**Consequence:** `wscd`'s `epc` must then be `libc+0x23f38` and its `ra`
`libc+0x23e64`.
**Measured:** `free+0x12c` and `free+0x58` — both inside one function, and the
kernel called that fault an *invalid **read*** from `0x4187c8bc`, which is what
a corrupted chunk header looks like from inside `free()`.

**And the error bar is measured, not asserted.** Sweeping every page-aligned
base across the surrounding megabyte — 256 candidates — **7** of them put both
`epc` and `ra` inside one and the same function:

| base | function |
|---|---|
| `0x2aab7000` | `vfscanf` |
| **`0x2aabe000`** | **`free`** ← predicted |
| `0x2aabf000` | `malloc` |
| `0x2aac2000` | `inet_pton` |
| `0x2aacd000` | `getpwuid_r` |
| `0x2aad0000` | `strftime` |
| `0x2aad1000` | `vsyslog` |

So the landing survived a filter it had roughly a **1-in-36** chance of
surviving by luck. That is not overwhelming on its own, and the honest form is
to say so and name what carries the rest: the fault *kind*. Of those seven, the
predicted base names `free()` — which, with `malloc()` one page away, is where a
wild read in a heap allocator happens. The other five would each need a story
and none was offered.

## 5. Confirmed on the silicon, on a different boot, by the kernel itself

Everything above was written from two console lines and the ELF files, and
recorded `partial` because both lines came from one boot. **On 2026-08-19, four
boots later, the device printed its own answer.** `telnetd` was started through
the `formSysCmd` injection and `/proc/<pid>/maps` read directly:

```
boa, PID 350
  2aaa8000-2aaad000 r-xp  /lib/ld-uClibc-0.9.30.3.so
  2aabe000-2aac9000 r-xp  /lib/libapmib.so
  2aad9000-2aae3000 rw-p  /lib/libapmib.so
  2aae3000-2ab15000 r-xp  /lib/libuClibc-0.9.30.3.so     <-- computed 0x2aae3000
  2ab29000-2ab3c000 r-xp  /lib/libgcc_s.so.1

wscd, PID 217
  2aaa8000-2aaad000 r-xp  /lib/ld-uClibc-0.9.30.3.so
  2aabe000-2aaf0000 r-xp  /lib/libuClibc-0.9.30.3.so     <-- predicted 0x2aabe000
```

| claimed at the desk | how | measured on the device |
|---|---|---|
| `libuClibc` in `boa` at `0x2aae3000` | from one kernel fault message | **`0x2aae3000`** |
| `libuClibc` in `wscd` at `0x2aabe000` | *predicted* from `libapmib.so`'s program headers | **`0x2aabe000`** |
| `libapmib.so` span `0x25000` | its own `PT_LOAD`s | `2aabe000 → 2aae3000` = **`0x25000`** |
| `libuClibc` span `0x46000` | its own `PT_LOAD`s | `2aae3000 → 2ab29000` = **`0x46000`** |
| `system` at `0x2ab08460` | `st_value 0x25460` + base | follows, and no longer boot-specific |

**And the number §6 withdrew is measured too.** `TASK_UNMAPPED_BASE` came out
`0x2aaa8000` from both processes' arithmetic and was kept out of the report
because the MIPS formula `(TASK_SIZE / 3) & ~(PAGE_SIZE − 1)` says `0x2aaaa000`.
`ld-uClibc` is mapped at `0x2aaa8000` in both processes. **Withdrawing it was
right and it is now evidence rather than tidiness** — the formula is what does
not describe this kernel, which is a separate question and still open.

### The contradiction that is worth more than the address

```
# cat /proc/sys/kernel/randomize_va_space
2
```

**Two is full randomisation** — mmap, stack, brk. And the layout above is fully
determined by the ELF files, across two processes and at least four boots.

The sysctl lives in generic kernel code and is writable on any Linux; whether an
architecture *acts* on it is the architecture's business. Linux 2.6.30.9 on MIPS
does not: `arch_pick_mmap_layout` with randomisation arrived on MIPS later, and
this kernel allocates bottom-up from a fixed `TASK_UNMAPPED_BASE`. **So the flag
advertises a mitigation the kernel does not apply.**

That is the practical lesson, and it is not about this router: **a hardening
flag is a claim by a source, and a source is not a measurement.** Reading
`randomize_va_space` and stopping there would have closed `P5-2` as refuted
without a single address being looked at.

## 6. How the first version of this was wrong — three times, and one of them was un-wrong

**It computed the base off by four and nearly filed it as noise.** The first
arithmetic assumed the device's `epc` named the same instruction qemu's `pc`
did, giving `0x2aafe218 − 0x1b21c = 0x2aae2ffc`. That is four bytes below a page
boundary. The reflex was to call it close enough. It is not close enough —
`mmap` never returns `0x…ffc` — and the delay-slot rule explains the four bytes
*exactly* rather than approximately. **A near-miss that has an exact explanation
is not a near-miss, and one that does not is a refutation.**

**It expected the two processes to share a base.** "No ASLR means the same
address in both" is wrong, and the naive test it implies would have come back
`0x2aae3000 ≠ 0x2aabe000` and read as *evidence of randomisation*. The
libraries differ, so the layouts differ; what is invariant is the *allocation
rule*, not the address. The test had to be rebuilt around a difference that is
computable from the files — and the maps above show the rule directly.

**It claimed `TASK_UNMAPPED_BASE` and then withdrew it — and the withdrawal was
correct on the evidence available.** Working backwards through `ld-uClibc`'s
span gave `0x2aaa8000` from both processes, which is tidy, and the MIPS formula
gives `0x2aaaa000`. Two pages unaccounted for and no reading of this kernel to
settle them, so the tidy number stayed out of the report. **The device then
printed it.** The right conclusion is not "I should have claimed it" — it is
that the reason for withholding was the right shape, and what the maps changed
is the evidence, not the standard.
