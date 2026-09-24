# How this was built

I used an AI coding assistant on this project, mostly for tool scaffolding and
first drafts of documentation. I am saying so here because it is true, because
you would work it out from the commit cadence anyway, and because the
interesting question is not *whether* I used one but *what I did not delegate*.

## The rule I worked to

> **The tools can be collaborative. The conclusions cannot.**

Every conclusion in this repository is one I can re-derive at a whiteboard, from
the evidence, without the repository open. That is not a claim about effort; it
is a testable one, and the test is that you ask.

## What the assistant did

Tool skeletons and refactors — the argument parsing, the file walking, the
shape of a guard suite. First drafts of prose. Finding the fourth place a
number needed changing.

## What it could not do, and did not

- **Every bench session.** Soldering and wiring the UART header, measuring the
  baud rate off a logic analyser rather than guessing it, seating the SOIC-8
  clip on `U19` and reading 1.70 V on a part specified for 3.3 V, all four flash
  writes and all four restorations, every power cycle.
- **Every decision about the only unit I have.** Whether to reflash it (no —
  `P9-12` had already run unsigned code of my own on the SoC without writing a
  flash byte, and the reflash only buys persistence, paid for with the device).
  Whether to trust an undervolted read (no). Whether to attach the console
  during a reset-button test that then would not boot (that one I got wrong, and
  it is in `journal/PROGRESS.md` under W07 Day 7).
- **The design of the evidence rules** — freezing a prediction and its
  refutation condition before the packet, hashing the pair, refusing a result
  whose refutation field is empty. Those are in
  [`writeup/01-rules.md`](../writeup/01-rules.md) under my own name because they
  are mine.
- **Noticing when a tool was lying.** Sixty times
  ([`writeup/12`](../writeup/12-instruments.md)), and **not one of them was
  caught by the tool's own self-check.** Four of those were caught inside an
  hour on 2026-09-25 by comparing a brand-new checker's output against the file
  it was judging, which is the whole method in one sentence.

## Why `CLAUDE.md` is not in this repository

It was, until 2026-09-25. It is the assistant's configuration file — the same
category as `.vscode/settings.json` or `.cursorrules` — and configuration files
are not portfolio material. Removing it is a filing decision, not a concealment
one, which is why this page exists in the same commit.

What was worth keeping out of it is not configuration at all. *No claim from a
single tool. A tool reporting zero is a claim too. Keep "I chose not to" apart
from "I could not", because collapsing them always flatters.* Those are the
working rules of this project and they are now stated as such, in my own words,
in [`writeup/01-rules.md`](../writeup/01-rules.md).
