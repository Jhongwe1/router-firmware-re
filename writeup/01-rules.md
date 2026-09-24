# 1. Why this device — and what "measured" means here

This chapter is not the motivation. It is the rules, and it comes first because
every sentence after it depends on them.

## The device

A TOTOLINK N150RT, hardware V2.0: a 150 Mbps consumer router, end of life, no
longer vendor-supported, bought second-hand and owned outright. Everything here
was done on my own hardware, on an isolated segment, with the WAN port
disconnected except where a chapter says otherwise.

What makes it worth six weeks is not that it is insecure. It is that it is
**ordinary**: a Realtek SDK build, a Boa 0.94 web server running as root, a
big-endian MIPS-I userland with no exploit mitigations anywhere. Whatever is
true of this device is true of a large family of devices, and the interesting
question was never "can it be broken" — it was "how much of what is publicly
said about it survives being checked".

Not much, as it turns out. That is chapters 5 and 7.

## The rules

**A claim names the binary it was measured on, or it is not made.** This project
spent three weeks reverse-engineering `/bin/boa` before discovering that the
device runs a third build with a different `/bin/boa`. Every finding from those
weeks is still true of the images it names, and **none of it described the
hardware**. So every report carries the SHA-256 of its input, and CI fails a
report that does not.

**No claim from a single tool.** `readelf` and `nm -D` are not independent on an
`sstrip`'d ELF — they read the same section headers. Ghidra and `nm -D` are.
Where only one reader exists, the text says "one source" in as many words.

**A tool reporting `0` is a claim too**, and it is the claim most likely to be
wrong. A sink census that returned **1** where a sibling build returned 589 was
a bug in the census, not a rewrite of the firmware. Chapter 12 is what that
lesson cost.

**Static is not dynamic.** Until a request had actually been served, the only
permitted phrasing for behaviour in this repository was *"the code reads as"*.
That phrase appears throughout, and it is not hedging — it marks exactly which
sentences a device could still refute.

**A prediction is written before the measurement, with a refutation condition,
and the pair is hashed.** 141 registered tests, 127 with a written refutation
condition frozen before the first packet was sent. Changing a prediction after
the fact is allowed and is never allowed to be quiet: the hash changes in the
same commit, so the diff shows two deliberate lines instead of one silent edit.

**Negative results stay.** The wrong turns are in the record at full length,
including the ones that would have been easier to delete. Chapter 12 is the
concentrated form; the rest are scattered through as *"and here is how the first
version of this was wrong"* sections that every note in this project is required
to end with.

## What that buys, and what it costs

It costs speed. A finding takes two sources and a written prediction, and a
third of this project's elapsed time went into instruments whose entire job is
to refuse.

What it buys is that the failures in this document are **legible**. When the
sink census said `1`, the register said what `1` would mean and the cross-build
comparison said it was impossible. When a payload the simulator had certified
printed sixteen bytes of forty-one on real silicon, there was a written
prediction to fail against and a single-variable experiment to fix it with.

> **Where this chapter stops:** these are the rules this project set itself.
> They are not a claim that the results are correct — only that where they are
> wrong, the document should let you find out.
