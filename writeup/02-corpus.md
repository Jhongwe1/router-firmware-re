# 2. Seven images, six binaries read across, and where each came from

Where an image came from decides what it can be used to prove, so it goes here
rather than in an appendix.

Six images are declared in [`firmware/SOURCES.json`](../firmware/SOURCES.json)
and can be downloaded; the seventh was read off this unit's flash and is not
published. **Six `boa` binaries were read side by side** — the seventh image was
only partially downloaded and contributes its web bundle, not its binary.

| image | date | model | how it was obtained | what it can support |
|---|---|---|---|---|
| **V2.1.2-B20150825** | 2015-08-25 | N150RT | vendor download page, hash in `SOURCES.json` | claims about *a published 2015 build* |
| **V2.1.6-B20160516** | 2016-05-16 | **N300RT** | third-party mirror | the only published image whose *product version* matches this unit's |
| **V3.2.0-B20180330** | 2018-03-30 | **N200RE** | third-party mirror | the nearest-in-time publicly downloadable build to the one this unit runs |
| **this unit's build** | binaries stamped 2018-01-10 | N150RT | **read off this device's flash**, twice, 105 minutes each | claims about *this hardware* |
| **V3.4.0-B20190315** | 2019-03-15 | **N300RT** | third-party mirror | brackets *when* a handler was removed, per product |
| **V3.4.0-B20201030** | 2020-10-30 | N150RT | vendor download page, hash in `SOURCES.json` | claims about *a published 2020 build* |
| **V2.1.6-B20160516** | 2016-05-16 | N150RT | third-party mirror, **downloaded incomplete** | its `w6cg` web bundle only, which is byte-complete. `SOURCES.json` marks it *"do not analyse as if whole"* |

Three of these are **not this device's firmware** — two N300RT and one N200RE,
added 2026-08-18 because register rows need them. A claim derived from one of
them is a claim about an image, never about hardware nobody here has touched.
That distinction does real work in chapter 7: *"V3.4.0 removed `formSysCmd`"* is
**false as stated**, because the removal is per product, and only the six
binaries side by side show it
([`reports/formtable-scan-six-builds.json`](../reports/formtable-scan-six-builds.json)).

## What a hash proves, and what it does not

Every image carries a SHA-256, and for the two vendor downloads that hash is
worth exactly one thing: **you and I have the same bytes.** It is not evidence
that the vendor published them. Nothing here treats a third-party mirror as a
vendor statement, and the four mirrored builds are used for comparison, never as
the sole support for a claim.

**Two of the seven have a recorded fetch hash** in
[`firmware/MANIFEST.json`](../firmware/MANIFEST.json) — the two from the
vendor's own page, which are the two `make fetch` retrieves. The rest carry a
declared expectation in `SOURCES.json` that is pinned on first successful fetch.
That asymmetry is not tidy and it is the true state.

There is one piece of corroboration for the mirrors worth naming, because it
does not depend on trusting anybody: **the six builds' dispatch tables and
string spaces fall on a continuous curve** — 102, 103, 97, 103, 90, 89 candidate
entries against monotonically related binary sizes. A fabricated or corrupted
image does not land between two genuine ones on `root_form[]` size, handler
ordering and string-table growth simultaneously. That is weak evidence and it is
stated as weak evidence.

## The one image with no source, because it came off the chip

The build this device actually runs was not downloaded. It was read out of the
flash through the boot loader's own `FLR` and `DB` commands over a serial
console — 4 MiB, twice, **staged through different RAM addresses** so that a bad
RAM region could not produce the same wrong answer twice, with the SHA-256
recomputed independently of the tool that wrote the file. Both reads are
`a800059a…`; `cmp` finds zero differing bytes.

That image is not in this repository and never will be: it contains this unit's
MAC addresses, its radio calibration and its administrator password. What is
published is the analysis, the offsets and the reports — plus
`dumps/MANIFEST.json`, which says exactly what was read and how. **That is a
redistribution decision, and it is not the disclosure policy**; the two are
argued separately, in [`REPRODUCE.md`](../REPRODUCE.md) and
[`docs/disclosure.md`](../docs/disclosure.md) respectively.

**This is chapter 5's hook.** The version string on that image is published. The
build is not.

## The published identifier is not the searchable one

The device reports itself two different ways depending on who asks:

* `/etc/version` says `TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002`;
* `/bin/boa` says `TOTOLINK-N150RT-…`, and that is what an unauthenticated
  `status.htm` returns to the network.

`CX` appears in exactly one file in the whole root filesystem. That two-letter
difference is why a CVE naming this exact build sat unfound by this project for
two weeks — chapter 7 has the mechanism, and it is not a story about
carelessness. It is a story about which string a search engine indexes.

> **Where this chapter stops:** provenance is about the files, not the findings.
> Four of the seven images come from mirrors and are used accordingly; the one
> that matters most cannot be obtained by anybody who does not own one of these
> routers, and chapter 14 says what that costs the reader.

## How the first version of this chapter was wrong

It was headed **"Five builds"**, it listed five rows, and then a section below
the table called this unit's dump **"the sixth image"** — so the chapter
contradicted its own count inside four hundred words.

Worse, one of the five rows was **`V4.1.5cu`**, *"third-party mirror, later,
cross-family comparison only"*. That string appears in **exactly one file in
this repository: this one.** There is no such image in `SOURCES.json`, no
manifest entry, no report, and no other document mentions it. It was never
obtained and never analysed.

And the three images that *were* obtained and analysed — the two N300RT builds
and the N200RE — were **missing from the table entirely**, while a finding that
depends on all three (chapter 7's per-product removal) was being asserted three
chapters later.

The chapter whose entire job is to say which image supports which claim was the
least accurate document in the repository about which images exist. It was found
on 2026-09-25, in the publication week, by cross-checking a number in the
`README` draft — *five builds* against *six builds* — rather than by reading the
chapter. **Nothing in `make ci` could have caught it**, because no checker
compares a prose corpus list against `firmware/SOURCES.json`, and after this one
still does not. That gap is now open item 110.
