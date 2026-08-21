# The Build Nobody Had

*Reading a vendor's five-year fix off the chip — and what fifty-four broken
instruments taught me about my own results*

**Draft.** Every chapter has content; the prose is a first pass and W09 is the
editing week. Nothing here is a claim this repository does not already carry
evidence for, and where a chapter says *"the code reads as"* it means no device
has been asked.

---

## TL;DR

I bought an end-of-life TOTOLINK N150RT, read its 4 MiB SPI flash through the
boot loader's own commands over a serial console, and found it runs a build that
appears on no vendor download page — a 2018 image sitting exactly in the middle
of a five-year, three-step response to a 2015 disclosure. Reading five builds
side by side shows the vendor deleting the backdoor binary **two and a half
years before** removing the uid 0 account it shipped with. Along the way
fifty-four of my own instruments were wrong, and **not one was caught by its own
self-check**.

---

## The fourteen chapters

| | | |
|---|---|---|
| **1** | [Why this device — and what "measured" means here](01-rules.md) | the evidence rules, first, because everything after them depends on them |
| **2** | [Five builds, and where each came from](02-corpus.md) | provenance, including what a hash can and cannot prove |
| **3** | [The board — and four things the spec sheet got wrong](03-board.md) | and one prediction about the physical world, made three weeks early |
| **4** | [A console with no shell, and a loader that reads flash](04-console.md) | the baud was measured, not guessed |
| **5** | [The build nobody had](05-the-build.md) | 🏆 the first result that is only obtainable from silicon |
| **6** | [Inside `boa`: the dispatch table and the substring gate](06-boa.md) | the advisory names a symptom; this is the cause, and it is broader |
| **7** | [Reading across, not down: five builds side by side](07-across.md) | which conclusions transferred, and which did not |
| **8** | [The config blob: `COMPCS` decoded](08-compcs.md) | CVE-2019-19823 turned from a citation into an address |
| **9** | [Making it move: a real flash as `/dev/mtdblock0`](09-emulation.md) | and a widely repeated reason for "you cannot emulate this" that is wrong |
| **10** | [The chain: five links, five layers of evidence](10-chain.md) | 🏆 ending at the bytes that changed on the flash |
| **11** | [Beyond the CVEs](11-bughunt.md) | twenty-four verdicts, three of them my own findings withdrawn |
| **12** | [Fifty-four instruments, fifty-four bugs](12-instruments.md) | 🏆 the chapter that costs me the most and buys the most |
| **13** | [If I were building this router — a gate, not an opinion](13-gate.md) | it runs; the 2020 build still fails it |
| **14** | [What this does not prove](14-limits.md) | the chapter that should be uncomfortable to read |
| — | [Disclosure · References · Thanks](15-disclosure.md) | |

A Traditional Chinese reading guide — what each chapter is *for*, and the three
questions a hostile reader would ask of it — is in
[`study/writeup-導讀.md`](../study/writeup-導讀.md).

---

## Three rules that run through all of it

**1. Every claim points at a product something else can regenerate.** Not "I saw
it in Ghidra" but `reports/ghidra-formtable-unit-2018.json`, and that file
carries the SHA-256 of the binary it describes. CI fails if a report cannot name
its own input.

**2. No screenshots unless the thing is inherently visual.** A screenshot cannot
be re-checked, cannot be grepped, and cannot be regenerated after a tool
upgrade. Disassembly is text. Flows are Mermaid, with the source in the page so
a reader can change it. Boards and logic-analyser captures are photographs,
because those *are* pictures.

**3. Every chapter ends with a line saying where its conclusion stops.** It is
chapter 14 distributed through the document, and it exists because the single
most common way a security write-up misleads is by not saying what it did not
look at.
