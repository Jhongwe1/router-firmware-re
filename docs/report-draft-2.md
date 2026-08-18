# Report draft 2 — the authentication bypass

**Status: drafted 2026-08-18, NOT sent. Not sendable yet, and for two reasons
rather than one.**

This is a second draft rather than a fourth item appended to
[`report-draft.md`](report-draft.md), because it goes to a different set of
people. `report-draft.md`'s three findings were measured on **one physical unit
running a build that is on no download page**, so its scope section says so and
its impact is bounded to that unit's owner. **This one reproduces on a firmware
image anyone can download**, which changes who is affected and therefore who has
to be told.

Same rule as the first draft: this file is the mail's structure and content, and
it **does not contain the request**. That lives at
`$FWRE_WORK/disclosure/D-uninitialised-credential-pair.txt`, mode 600, off-repo,
and is attached rather than pasted.

---

## What would be reported

One finding.

| | |
|---|---|
| **D** | `/bin/boa`'s HTTP Basic path compares the supplied credentials against **two** pairs of stack buffers. The second pair is never written by anything, is compared **first**, and a match sets a **higher** privilege level than the real credentials do. A request whose username and password are both empty matches it. |
| register | `P2-9` |
| ready to send? | **no** — two blockers, below |

## Affected, and this is the part that differs from draft 1

```yaml
vendor:      TOTOLINK (Zioncom)
product:     N150RT
affected:    V2.1.2-B20150825          # PUBLISHED, downloadable
             TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002   # this unit; not published
not affected: V3.4.0-B20201030         # published; the second pair is gone
```

**The 2020 build does not have it.** `FUN_00409fd8` — the same function, located
by the same `host invalid!` string, `sstrip`'d so it has no name — carries one
credential comparison with both halves filled by `apmib_get` immediately above
it, and no second level. So the window is **2015 → 2018 present, 2020 removed**.

Two consequences the coordinator should be told rather than left to infer:

1. **The vendor may already know.** Something removed that code between January
   2018 and October 2020. Nothing here says whether it was removed deliberately.
2. **The advice is "upgrade", and it may actually be available.** That is
   unusual for this device — the rest of this project's findings are on an EOL
   product with no fix path.

**Other products are untested.** CVE-2024-51228 names six `-CX-` builds from the
same SDK generation. This project owns one of them and makes no claim about the
other five — but the vendor is far better placed to check whether the same
function ships there, and the report should ask that rather than assert it.

## Impact, stated without inflation

An unauthenticated request reaches pages the authorisation gate is supposed to
protect, including the administration password page, which returns 5,332 bytes of
real HTML.

**What it is not:**

- **It is not a privilege escalation past what this device already gives away.**
  `P2-1` established that `POST /boafrm/*` does not enter the gate at all on this
  build, so the *actions* were already unauthenticated. What this adds is
  **reading**: pages, and what they contain.
- **It is not remote from the WAN** in the configuration measured here.
- **It is not the same defect as `report-draft.md`'s finding B.** That one needs
  the stored password to be empty. This one works with a real password set, and
  both were verified non-empty through the vendor's own `/bin/flash` in the same
  run.

## Timeline

| date | |
|---|---|
| 2026-08-10 | W03 reads the V2.1.2 Basic-auth path, finds a comparison against uninitialised stack, and **records it as a candidate rather than a finding** — correctly, on the evidence then |
| 2026-08-18 | fired under emulation on this unit's build, then reproduced on the published V2.1.2 image; V3.4.0 read and found not to have it |
| — | prior-art search by handler · **not done** |
| — | confirmed on hardware · **not done** |
| — | report sent · **not yet** |
| — | 90-day clock starts on the send date, recorded in `docs/disclosure.md` in the same commit |

## What is attached, and what is not

| | |
|---|---|
| attached | `$FWRE_WORK/disclosure/D-uninitialised-credential-pair.txt` — the request, the six-row response table with its positive and negative controls, the three-build scope, and the four things that are **not** established |
| attached | the instruction-level listing of the two comparisons, from `ghidra/scripts/BoaListing.java`, naming the binary's SHA-256 |
| **not attached** | the flash image, for the same reason as draft 1 — it carries this unit's MAC addresses and radio calibration |
| **not attached** | anything about `D-12`, `D-13`, `D-14`, `D-16` or `D-17`. They are static readings or emulation-only and belong in no report yet |

## Before this can be sent — two blocking steps, not one

**1. The prior-art search, by handler and by pattern.** `docs/disclosure.md`
step 2, and this project has already been taught what it costs to skip: a search
by *product* returned nothing for `D-1` and a search by *handler* returned a 2023
Cisco Talos advisory on the first page, and that finding was withdrawn the same
night. A second search the same evening found a published authentication bypass
against **this exact Boa version** — it turned out not to apply, but nobody knew
that until it was measured.

An authentication bypass in a widely-forked Realtek SDK web server is exactly the
sort of thing that has been written up before under a name nobody here searched.

**2. Confirmation on the device.** Everything measured is `qemu-user`. Two
profiles agree, but they share one emulator, and the finding depends on what an
uninitialised stack buffer contains. The argument that it is zero for a
structural reason is in the notes and it is an argument.

**Cost: three requests, no power cycle, no configuration change, nothing
written.** It is the first item of the next bench session. **Until it has run,
this draft does not go anywhere** — reporting an emulation artefact as a
vulnerability in shipping firmware would be worse than not reporting at all, and
it is the specific failure this project's static-versus-dynamic rule exists to
prevent.

**Owner: the author. This file is not sent by anyone else.**
