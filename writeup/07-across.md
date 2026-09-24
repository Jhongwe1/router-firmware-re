# 7. Reading across, not down: three builds in depth, six in breadth

Chapter 5 forced this chapter into existence. Two weeks of reverse engineering
described binaries this device has never run, so every claim had to be re-made
against the build in its flash — and the interesting part is not that the work
was repeated. It is **which conclusions transferred and which did not**.

## The table

| | 2015 (V2.1.2) | 2018 (this unit) | 2020 (V3.4.0) |
|---|---|---|---|
| `root_form[]` entries | 59 | **57** | 49 |
| `formSysCmd` present | no | **yes**, `0x004838a8` | no |
| authorisation gate test | `strstr(uri,"htm")` | **`.htm` or `.asp`** | `strstr(uri,"htm")` + POST arm |
| `/bin/skt` shipped | **yes**, and executable | **deleted** | absent |
| `#skt&` in `rcS` | present, commented | **still present, still commented** | absent |
| uid 0 backdoor account | **present** | **present, byte-identical** | removed |
| `USER_PASSWORD` storage | plaintext TLV | plaintext TLV | plaintext TLV |
| gate rule R2 (parameter → shell) | 5 sites | 6 sites | **8 sites** |

## What transferred

**The gate mechanism.** All three builds decide authorisation with an unanchored
substring test on the URI. The *string* differs; the *technique* does not, and
the technique is the defect.

**The credential storage.** `USER_PASSWORD` is a plain TLV in a compressed
region in all three. No hashing step exists on that path in any of them —
chapter 8.

**The container layout.** Week 1's three burn addresses hold on a build week 1
had never seen.

## What did not transfer

**`formSysCmd`.** The one that matters. It is in this unit's dispatch table and
in neither published **N150RT** image — a qualifier this chapter did not carry
until the six-build scan below forced it — which means:

> Reproducing CVE-2019-19824 from firmware anybody can download gives the wrong
> answer about this hardware — in the *safe* direction, which is worse, because
> the answer you get is "not affected".

**The gate string.** 2018 checks `.htm` or `.asp`. That is 2015's *outcome*
reached by 2020's *mechanism*, and it is a third answer rather than a point on a
line between the other two. A two-point comparison would have interpolated and
been wrong.

**Everything with a hit count in it.** The sink census, the exemption list
length, the handler ordering — all three differ, and none of the differences is
predictable from the other two builds.

## The prediction hit rate, and why it is reported at all

Before W04-2 ran, each finding from W03/W04 was labelled **will transfer** or
**will not**. The list was frozen, then checked. Reporting the rate matters less
than the shape of the misses: the ones that failed were the ones expressed as
*counts* rather than as *mechanisms*. A mechanism survives a rebuild; a number
does not.

## Two weeks lost to two letters

CVE-2024-51228 names `/boafrm/formSysCmd` and lists
`TOTOLINK-CX-N150RT V2.1.6-B20171121.1002` — byte-for-byte this unit's
`/etc/version`. This project independently derived the same reachability result
from the binary, and did not find the CVE for two weeks.

The mechanism is not carelessness. It is that **the prior-art survey was
organised around disclosure events** — Pierre Kim 2015, Realtek SDK 2019 — and a
2024 CVE against a 2018 build fits neither. And the string that would have found
it, `CX`, appears in exactly one file in the root filesystem and in nothing the
device puts on the network. `boa` reports the build *without* the `CX`, and that
is what an unauthenticated `status.htm` returns.

So: **search the version string, never the label you gave the build.**

There is a narrower thing this project can claim about that CVE, and it is
checkable. NVD scores it `PR:H` — privileges required, high — for 6.8 MEDIUM.
The original researcher writes "without credentials". The instruction-level read
agrees with the researcher: `/boafrm/formSysCmd` contains neither `.htm` nor
`.asp`, so the gate does not run on it. If the researcher is right the vector is
`PR:N` and the score is 8.8 HIGH.

## The three columns were not enough, and the fourth read says so

Everything above compares three N150RT builds. That is the right corpus for
*this device*, and it is the wrong corpus for the sentence the table was being
used to support. **"V3.4.0 removed `formSysCmd`" is false as stated.**

Six `boa` binaries, one scan
([`reports/formtable-scan-six-builds.json`](../reports/formtable-scan-six-builds.json)):

| `boa` binary | model · version | bytes | candidate entries | `formSysCmd` |
|---|---|---|---|---|
| `v2.1.2` | N150RT V2.1.2 (2015) | 522,556 | 102 | **no** |
| `n300rt-2.1.6` | N300RT V2.1.6 (2016) | 526,732 | 103 | yes |
| `unit-2018` | **this unit** (2018) | 485,012 | 97 | yes |
| `n200re-3.2.0` | N200RE V3.2.0 (2018) | 509,632 | 103 | yes |
| `n300rt-3.4.0` | N300RT V3.4.0 (2019) | 400,424 | 90 | **yes, still** |
| `v3.4.0` | N150RT V3.4.0 (2020) | 404,904 | 89 | **no** |

**"Candidate entries" is not the handler count**, and the difference matters
because the table at the top of this chapter says **57 / 58 / 57**. The scan
walks the table at a fixed stride and counts every slot whose shape *could* be a
`{name, handler}` pair; the per-build reports then discard the ones whose name
pointer does not land in the string table or whose handler is not a function
entry. 102 candidates in the 2015 binary become 57 confirmed routes. Both
numbers are real and they answer different questions — **the candidate count is
a property of the scan, the confirmed count is a property of the firmware** — so
comparing a candidate count against a confirmed one would be an artefact of the
instrument, which is the whole subject of chapter 12.

The handler is **absent from N150RT 2015, present in the middle four, and absent
from N150RT 2020** — and it is *still present* in an N300RT build from **2019**,
a year and a half after this unit's. So the removal is **per product**, not a
platform decision on a date, and a reader who took the three-column table as a
statement about "the vendor's 3.4.0" would have had it backwards for one of the
two products.

This unit's 57 handlers are also a **strict subset** of N300RT V2.1.6's 61,
which is the cleanest evidence in the corpus that these are the same code base
configured differently rather than separate lineages.

> **Where this chapter stops:** five of the six builds are static reads of
> downloaded files, and four of those five came from third-party mirrors rather
> than the vendor's page — chapter 2 says what that is and is not worth. The
> 2018 column is the only one measured on hardware, and where a table gives a
> count it is a count in one binary rather than a property of the family. The
> six-build row does one thing only: it refutes a generalisation this chapter
> was making from three.

## How the first version of this chapter was wrong

Three things, and the second is the one that should worry a reader.

**The title said five builds.** The chapter reads three. There was never a
five-build comparison; `reports/` holds three `BoaGate` reports and three
per-build `formtable` reports, for 2015, this unit's 2018 and 2020. Chapter 13
inherited the same wrong number in its own closing line.

**The `root_form[]` row said `57 | 58 | 57`. It is `59 | 57 | 49`.** Every one
of the three was wrong, and they were wrong *in a shape*: near-identical
counts with this unit one entry above its neighbours. The real numbers say
something quite different — the 2020 build **dropped ten routes**, which is a
visible narrowing of the attack surface and the single most interesting cell in
the table. The fabricated symmetry hid it.

The correct numbers were never in doubt and never hidden. They are in
[`notes/three-way-read.md`](../notes/three-way-read.md) (`59 | 57 | 49`, W04-2),
in [`notes/dispatch-table.md`](../notes/dispatch-table.md) (59 and 49 by
address), and in the three report files themselves. **The chapter did not
disagree with the evidence; it disagreed with the repository's own notes, and
nothing compared the two.** Every other row in that table checks out against
`reports/` — the gate-rule row `5 | 6 | 8` is exactly `findings_by_rule.R2` in
the three gate reports — which is what makes the one wrong row worse rather than
better: a table where everything is checkable and one cell was not checked.

**The six-build scan was missing**, and it refutes a generalisation the chapter
was making. That is the section above.

Found 2026-09-25 by following a count — *five builds* in the write-up against
*six builds* in three notes — rather than by reading the chapter. The general
lesson is the one chapter 12 keeps arriving at from the other direction: **the
numbers are the part of a document that can be checked mechanically, so they are
the part worth chasing when something feels off.** Open item 110 is the missing
checker: nothing compares a count in `writeup/` against the report it came from.
