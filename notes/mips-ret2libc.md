# Where uClibc is mapped on this unit, and how that was read off two console lines

**Answer first.** On the unit running
`TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002`, `libuClibc-0.9.30.3.so` is mapped at
**`0x2aae3000`** in `boa` and at **`0x2aabe000`** in `wscd`, and `system` is
therefore at **`0x2ab08460`** in `boa` (`st_value` `0x25460`). Nothing was
leaked and nothing new was sent to the device to get those numbers: they come
out of two kernel fault messages already sitting in `BENCH-LOG.md`, recorded on
2026-08-18 for `P6-2` and `P5-6`, plus the ELF files.

| | |
|---|---|
| register row | `P5-2` — **partial**, and §5 says why not confirmed |
| instrument | [`tools/libbase.py`](../tools/libbase.py), 27 guard cases in [`tools/test-libbase.sh`](../tools/test-libbase.sh) |
| report | [`reports/libbase-unit-2018.json`](../reports/libbase-unit-2018.json) |
| inputs | `BENCH-LOG.md` `T-50` (wscd) and `T-60` (boa), both station 3 boot 2 (cycle 3), 2026-08-18 |

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

## 5. What this does and does not settle about ASLR

**It settles the axis the register did not ask about, and that is the useful
one.** Randomisation on Linux is applied per `execve`, in `load_elf_binary`, not
per boot. Two independent `execve`s here produced a layout **fully determined by
the ELF files**: one measured base, one predicted from a program header, and the
prediction landed. With `randomize_va_space` non-zero the difference between the
two would be an arbitrary number of pages, not exactly `libapmib`'s span.

**It does not settle the register's literal refutation.** `P5-2` says "the libc
base differs across two reboots"; both fault messages come from **one** boot —
station 3, boot 2 (cycle 3), 20:35 and 23:4x on 2026-08-18. Scoring a refutation
condition that could not have fired is what `A3.24` was caught doing on
2026-08-19, comparing erased flash against erased flash on the one question its
row existed to answer. So the row is **partial**, and one crash fired after the
2026-08-19 reset with the console attached closes it in a single observation.

**Nothing has been jumped to.** `system`'s address is computed, not reached.
`a0` would have to point at a command string, and `P5-1`'s `localPin` frame has
not been shown to allow that. That is a different row.

## 6. How the first version of this was wrong — three times

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
computable from the files.

**It claimed `TASK_UNMAPPED_BASE` and then withdrew it.** Working backwards
through `ld-uClibc`'s span gives `0x2aaa8000` from both processes, which is
tidy — and the MIPS formula `(TASK_SIZE / 3) & ~(PAGE_SIZE − 1)` gives
`0x2aaaa000`, which is not it. Two pages unaccounted for, and no reading of this
kernel to settle them. So the absolute base stays *measured*, only the
*difference* is claimed as predicted, and the tidy number is not in the report.
