# 13. If I were building this router — a gate, not an opinion

Every teardown ends with recommendations. Recommendations are cheap; the
difference between somebody who can take a thing apart and somebody who can
build one is whether the recommendation **runs**.

So this chapter's deliverable is a program.

## Three rules

[`ghidra/scripts/BoaGate.java`](../ghidra/scripts/BoaGate.java) scores a binary
on three properties, chosen because each corresponds to a defect this document
demonstrates rather than to a style preference:

| rule | what it looks for | which chapter it comes from |
|---|---|---|
| **R1** | an unbounded copy into a fixed-size buffer reachable from request data | 11 |
| **R2** | **a request parameter reaching a shell** | 6, 10 |
| **R3** | an authorisation decision made by an **unanchored substring test** | 6 |

It is a build gate: it runs on a binary, it emits JSON, and it fails the build.

## The positive control, and why it earned its keep on day one

A gate that returns "0 findings" is indistinguishable from a gate that is
broken. So the script carries a **positive control**: a construct it must find,
in a binary already known to contain it.

That control paid for itself immediately. The gate returned **0 findings on a
build known to be defective — twice, for two unrelated reasons.** Both would
have shipped as "clean". This is instrument bug 12's shape again (chapter 12),
and it is the reason no rule in this project ships without a case that must
succeed.

## The results

| build | R1 | R2 — parameter → shell | R3 | passes? |
|---|---|---|---|---|
| V2.1.2 (2015) | | **5 sites** | | ❌ |
| this unit (2018) | | **6 sites** | | ❌ |
| V3.4.0 (2020) | R1 and R3 nearly halve | **8 sites** | nearly halves | ❌ |

**The 2020 build repairs the authorisation hole the advisory named, and still
fails.**

R1 and R3 improve. R2 — the rule that says a request parameter must not reach a
shell — goes **5 → 6 → 8**. The `sprintf`-into-`system()` idiom that produces it
is unchanged from 2015 to 2020, character for character.

> **The vendor fixed the symptom the advisory described. The gate tests the
> property that produced it.**

That is the whole argument of this chapter in two sentences, and it is why the
deliverable is a program rather than a list. A list of recommendations would
have said "validate input" and the 2020 build would have looked like progress.

## And then the prose part

With the gate in place, the rest is ordinary engineering and worth stating
briefly.

**Credential provisioning.** `USER_PASSWORD` is a plaintext TLV in a compressed
region, and the region is served to unauthenticated clients (chapters 8, 10).
Two independent fixes, and the cheaper one is not the hashing: **the region
should not be in the document root.** `rcS` copies `/web/*` into the live
docroot and `boa` writes `config.dat` there at start-up; moving that file
removes the exposure without touching the credential format at all. Hashing the
password is right too, and it is the more expensive change because every
consumer of the field has to move with it.

**Signed OTA.** The upgrade path checks a checksum. A checksum is an integrity
check against corruption, not against an author. This project built a modified
image with a valid checksum at the desk; whether the device accepts it is
deliberately not yet answered, because that measurement is irreversible and it
is scheduled behind two rehearsed recovery paths.

**Output escaping.** The stored-injection surface exists because values written
through the configuration UI are rendered back into pages without escaping. That
is one function, applied at the boundary, and it is the change with the best
ratio of lines to defects removed in this whole document.

**And one that is not a code change.** The boot loader answers TFTP on a
compiled-in default address the moment somebody catches its escape window, and
its recovery path treats two specific filenames as *"jump to this the moment the
transfer ends"*. That requires physical console access, so it is not a remote
defect — but a default filename is not where the decision to execute an image
should live, and a device that has been in the field for eight years is a device
whose recovery path is now the most attractive thing on it.

> **Where this chapter stops:** three rules, run on five builds, on the `boa`
> binary. It is not a security review of the firmware — the kernel, the radio
> driver and the UPnP daemon are outside it, and the daemon is where chapter 11
> found its most serious defect. A gate that scores one binary and calls the
> product safe would be exactly the failure this chapter is written against.
