# 2. Five builds, and where each came from

Everything in this document is read out of one of five firmware images. Where
each came from decides what it can be used to prove, so it goes here rather than
in an appendix.

| build | date | how it was obtained | what it can support |
|---|---|---|---|
| **V2.1.2** | 2015-08-25 | vendor download page, hash in `firmware/SOURCES.json` | claims about *a published 2015 build* |
| **V2.1.6-B20160516** | 2016-05-16 | third-party mirror, **partially downloaded** | its `w6cg` web bundle only, which is byte-complete |
| **the unit's own build** | binaries stamped 2018-01-10 | **read off this device's flash**, twice, 105 minutes each | claims about *this hardware* |
| **V3.4.0** | 2020-10-30 | vendor download page, hash in `firmware/SOURCES.json` | claims about *a published 2020 build* |
| **V4.1.5cu** | later | third-party mirror | cross-family comparison only |

## What a hash proves, and what it does not

Every image here carries a SHA-256, and for the two vendor downloads that hash
is worth exactly one thing: **you and I have the same bytes.** It is not
evidence that the vendor published them. Nothing in this document treats a
third-party mirror as a vendor statement, and the two mirrored builds are used
only for comparison, never as the sole support for a claim.

There is one piece of corroboration for the mirrors that is worth naming,
because it is the kind that does not depend on trusting anybody: **the five
builds' dispatch tables and string spaces fall on a continuous curve.** A
fabricated or corrupted image does not land between two genuine ones on
`root_form[]` size, handler ordering and string-table growth simultaneously.
That is weak evidence and it is stated as weak evidence.

## The sixth image has no source, because it came off the chip

The build this device actually runs was not downloaded. It was read out of the
flash through the boot loader's own `FLR` and `DB` commands over a serial
console — 4 MiB, twice, **staged through different RAM addresses** so that a bad
RAM region could not produce the same wrong answer twice, with the SHA-256
recomputed independently of the tool that wrote the file. Both reads are
`a800059a…`; `cmp` finds zero differing bytes.

That image is not in this repository and never will be: it contains this unit's
MAC addresses, its radio calibration and its administrator password. What is
published is the analysis, the offsets and the reports — plus
`dumps/MANIFEST.json`, which says exactly what was read and how.

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
> Two of the five images come from mirrors and are used accordingly; the one
> that matters most cannot be obtained by anybody who does not own one of these
> routers, and chapter 14 says what that costs the reader.
