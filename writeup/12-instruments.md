# 12. Fifty-six instruments, fifty-six bugs — none caught by a self-check

Writing this chapter does nothing for me except one thing: it is the reason to
believe the rest of the document.

Fifty-six times, an instrument this project built or relied on was wrong.
Every one is numbered in [`PROGRESS.md`](../PROGRESS.md) at the point it was
found. **Not one was caught by the instrument's own self-check.** Every single
one was caught by two things that should have agreed, disagreeing — or by a test
written to fail.

Four are worth telling properly.

---

## 1. A sink census that returned 589, then 1

The census walks a binary and counts call sites reaching `strcpy`, `sprintf`,
`system` and friends. On the 2015 build: **589**. On the 2018 build, a sibling
compiled from the same SDK two and a half years later: **1**.

One. Not zero — zero would have looked broken. **One** looks like a firmware
that has been almost entirely rewritten, and that sentence was drafted.

It is impossible. Two builds of one codebase a few years apart track closely;
589 → 1 is not a code change, it is an instrument. The bug was in symbol
resolution on an `sstrip`'d binary, where the section headers the resolver
depended on are gone.

**The rule that came out of it — *read the builds across, not down* — went on to
catch three more.** A number with nothing to compare it to is not a measurement.

---

## 2. A guard suite reporting 5 of 5 while every invocation died on `import PIL`

The photo-redaction tool has a guard suite whose job is to prove it refuses
things: a box outside the image, a wrong `--expect-size`, a missing input. Five
cases, all asserting *this must fail*.

Five of five passed. Every invocation was dying on `import PIL` before reaching
any of the logic under test.

**A suite made only of refusals goes green when the whole system is broken**,
because a crash is a non-zero exit and a refusal is a non-zero exit. What caught
it was adding the one case that asserts *this must succeed* — the positive
control — which failed immediately.

Every guard suite in this project now has one. The reason this bug has its own
number and its own rule is that it is the shape three other bugs turned out to
share: **a check with nothing to work on reports success.**

---

## 3. A parser written from the quotation instead of from the record

A tool was written to parse the boot loader's console output. Its author — me —
wrote the expected format from a **note**, because the note contained the
transcript.

The tool rejected every line the device actually emits.

The note was analysis; quotations in analysis get tidied, reflowed and
abbreviated, and this one had. The **runbook** carried the same transcript
verbatim, because a runbook is an operating record. Both files existed. The
wrong one was read.

> A verbatim record is only worth what it is worth if somebody reads the
> verbatim one.

That lesson recurred two more times and is now a script: `console-lint.py` reads
a console log the way the device's own dispatcher reads it, and reports an
unexplained rejection as an error rather than as silence.

---

## 4. The one from the last session, and it points the wrong way

Deciding whether the boot loader ever enables interrupts began as a search for
Realtek's `sti` idiom — `mfc0 $1,$12 / ori $1,1 / mtc0 $1,$12`. There are none.
There are seven `cli` sites of the matching shape. The sentence written from
that was:

> *the loader runs with interrupts masked, so its TFTP must be polled.*

Every observation in that chain is correct. The conclusion is the opposite of
the truth, because this build writes **`ori $1,0x1f / xori $1,0x1e`** — sets bit
0, clears bits 1 to 4. Same effect, different bytes.

**Notice which way the error pointed.** The night before, a bench measurement had
left three candidate causes for a failure and excluded none of them. That
sentence would have excluded the *correct* one — and excluded it in language
that sounds well-founded: *interrupts cannot be the cause, because this loader
never enables them.*

The fix is not more care. A pattern match answers *"is this the shape I
expected"*, and the question was *"what is bit 0 afterwards"*. The instrument
now evaluates every `mtc0 $12` in the image with a four-valued per-bit lattice —
`0`, `1`, *what `mfc0` read*, *its complement* — so `xori` is exact and the
answer is arithmetic. Two guard fixtures differ in **one bit of one immediate**,
and they look like a duplicate test, which is the point.

---

## The whole list, in one table

| # | what was wrong | what caught it |
|---|---|---|
| 1–9 | the first nine, W01–W03 | two sources disagreeing, every time |
| 10 | sink census 589 → **1** | reading across builds |
| 12 | a freeze check hashing an **empty** list | asking what the check does when it has nothing |
| 13–21 | nine in one day, six of them in code written that day | controls written in the same commit |
| 19 | `AUTOBURN: 0` — the loader rejects the syntax from its own help text | the bench |
| 22 | the runsheet checker **did not read the runbook**, which held twelve stale command blocks, four already refuted | asking what the checker does *not* read |
| 24 | a self-check that passes because it never fires | a case that had to succeed |
| 40–42 | 41 and 42 were **created by fixing 40** | the guard suite for 40 |
| 43 | found by **GitHub**, not locally | `gh run list` after a push |
| 44 | the refusal that knew the answer fired **second** | ordering, not logic |
| 45 | the checker written to catch a broken workflow **shipped a workflow that would not parse** | the workflow, on the first push |
| 46 | a flash **write** tool with a hardcoded verbosity flag | a divergence case |
| 47 | the hardest to see | a second reader |
| 49 | the one this project is supposed to be immune to | — |
| 50 | `[^\n]` inside a POSIX bracket expression is **"neither a backslash nor the letter n"**, so four identification lines had never printed | a case that required them to print |
| 51 | a probe asking flashrom for a verbosity at which the line it parses **is not printed**, which would have sent the operator to re-seat a working clip | flashrom's own `dummy` programmer, no hardware |
| 52 | the `sti` shape match, above | changing the question |
| 53 | a function-entry rule that walked past a routine ending in `rfe` | **the tool's own refusal** — "0 callers" |
| 54 | a brand-new check whose regular expression matched nothing, so it passed on every file including the one it was written for | its own guard case, in the same commit |
| 55 | a packet capture that could not create its output file, printed `0 packets captured`, and **exited 0** — while "nothing is on the wire" was one of the candidate answers to the question being asked | a control: the capture contained zero of **our own outgoing** packets, which were known to have been sent |
| 56 | a guard case whose premise was *a property of live data* — "this week has rows and no results, so only the new rule can fire". The week closed, the premise died, and the case went **red for a reason unrelated to what it tests**, on the day the thing it guards started working | it went red rather than green, which is the only reason this one was cheap. Re-based on a fixture, with a control |

---

## The sentence this chapter exists for

> **Fifty-six instrument bugs. Not one was caught by the instrument's own
> self-check. Every single one was caught by two things that should have agreed,
> disagreeing — or by a test written to fail.**
>
> **A check that never fires never fails.**

The corollary is the operational one, and it is why this project has 462 guard
cases across twenty-one suites plus 130 parser tests, and why `make ci` runs all
of them: **most of the engineering in a reverse-engineering project is not
reverse engineering. It is building the thing that tells you when you are
wrong.**

> **Where this chapter stops:** fifty-six is the count of bugs *found*. It is a
> lower bound on the bugs that existed, and it says nothing about the ones still
> in there. The honest reading of a rising count is not "the instruments are
> getting better" — it is "the search is getting better", and those are
> different.
