# `journal/` — the working record, published on purpose

Six files, about two megabytes, mostly Traditional Chinese. They are not the
deliverable. They are what the deliverable is checkable against.

## Why this is public at all

This project's central claim is that **every conclusion can be traced back to
the measurement it came from**. A document that carries only conclusions cannot
support that claim — it asks to be believed. These files are the other half:
every wrong turn, every instrument that lied, every session that measured
nothing, in the order it happened.

So if you want to find out where this project is wrong, start here rather than
in [`writeup/`](../writeup/). `PROGRESS.md` ends most sessions with a
`Corrections` block. [`writeup/12`](../writeup/12-instruments.md) lists
sixty-one of my own broken instruments. **That is the design, not an accident,
and it is the reason this directory is not in `.gitignore`.**

## What is in each file

| file | what it owns | shape |
|---|---|---|
| [`PROGRESS.md`](PROGRESS.md) | Gates, weeks, and the carried-forward questions. Each session ends with what changed and what was corrected | edited freely, chronological |
| [`LOG.md`](LOG.md) | Every dead end, at the length it deserves | append-mostly |
| [`BENCH-LOG.md`](BENCH-LOG.md) | What was actually typed and seen at the device on a given day — **and the plan written before anything was touched** | **append-only**; never normalised, never rewritten |
| [`RUNBOOK.md`](RUNBOOK.md) | Why each step of a procedure exists, and how it went wrong the first time | edited freely; carries no command blocks, and CI enforces that |
| [`runsheet.md`](runsheet.md) | The exact commands, their verbatim expected output, and the stop condition for each — five stations, where the station number *is* the state of the device | Part A edited freely, Part B append-only |
| [`test-ledger.md`](test-ledger.md) | **Generated.** Rendered from [`../test-cases.toml`](../test-cases.toml); edit the register, not this | `make ledger` |

## The rule these files exist to enforce

**One piece of state has exactly one owner.** A gate may *cite* a test; it may
not restate its row. `runsheet.md` owns the commands and `RUNBOOK.md` owns the
reasoning, so the same procedure is never described twice. The rule is here
because on 2026-08-16 one piece of state had two owners, they drifted, and
nothing noticed — which is also why four of the checks in `make ci` exist to
compare documents against each other rather than against reality.

## Language

Traditional Chinese, deliberately: these are operating notes written at speed,
for the person operating. Everything a reader needs in order to *check a
conclusion* — [`README`](../README.md), [`REPRODUCE`](../REPRODUCE.md),
[`writeup/`](../writeup/), [`notes/`](../notes/), [`poc/`](../poc/) — is in
English, and each of those points back here by file and date rather than asking
anyone to read Chinese to follow an argument.

`BENCH-LOG.md` is the one file that is never tidied, not even for punctuation:
it is evidence, and evidence that gets edited afterwards is not evidence.
