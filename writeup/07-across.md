# 7. Reading across, not down: five builds side by side

Chapter 5 forced this chapter into existence. Two weeks of reverse engineering
described binaries this device has never run, so every claim had to be re-made
against the build in its flash — and the interesting part is not that the work
was repeated. It is **which conclusions transferred and which did not**.

## The table

| | 2015 (V2.1.2) | 2018 (this unit) | 2020 (V3.4.0) |
|---|---|---|---|
| `root_form[]` entries | 57 | **58** | 57 |
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
in neither published image, which means:

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

> **Where this chapter stops:** four of the five builds are static reads of
> downloaded files. The 2018 column is the only one measured on hardware, and
> where the table gives a count it is a count in one binary rather than a
> property of the family.
