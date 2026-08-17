# Report draft — TWCERT/CC

**Status: drafted 2026-08-17, NOT sent. The 90-day clock has not started.**

This file is the report's *structure and content*. It deliberately does **not**
contain the three request bodies: it is committed to a public repository, and
`docs/disclosure.md` says a reproduction for something unreported does not get
published. The requests live in `$FWRE_WORK/disclosure/` — off-repo, like every
other artefact — and are attached to the mail rather than pasted into it.

Two of the items below are **blocked on step 2 of the procedure**, not on
writing. That is stated at the end and it is the reason this is a draft.

---

## What would be reported

Three items, and they are not equally ready.

| # | finding | register | ready to send? |
|---|---|---|---|
| **A** | An unauthenticated POST changes the administrator password. The form carries fields for the *current* credentials and the handler does not check them. | `P10-3` | prior-art search **not done** |
| **B** | With the stored administrator password empty, the credential comparison is skipped for every request — a *wrong* password is accepted too. **A + B is a complete unauthenticated takeover.** | `P10-4` | prior-art search **not done** |
| **C** | A single unauthenticated, well-formed POST to one form handler removes the web server until the device is power-cycled. | none — it came out of a handler census | prior-art search **not done** |

**A fourth item is deliberately not here.** The command execution
(CVE-2024-51228) is already public and needs no report; what this project has to
say about it is that its CVSS vector is wrong, and **a score correction goes to
the CNA, not to a national CERT.** Mixing the two in one mail would ask the wrong
organisation to do the wrong thing.

---

## Affected

```yaml
vendor:      TOTOLINK (Zioncom)
product:     N150RT
firmware:    TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002
             # as printed by /etc/version. NOTE the -CX-: the web interface
             # reports TOTOLINK-N150RT-V2.1.6-B20171121.1002 WITHOUT it, so the
             # only identifier a remote observer can obtain does not match the
             # string the vendor's own file uses. This is why an existing CVE
             # naming this build was not found by searching the product name.
binary:      /bin/boa, 485,012 bytes, sha256 19fe29d7…, built 2018-01-10 14:57:54
kernel:      Linux 2.6.30.9, built 2018-01-10 14:50:54, gcc 4.4.5-1.5.5p2
soc:         Realtek RTL8196E, MIPS big-endian
web server:  Boa/0.94.14rc21, running as root
```

**Scope of the claim.** Everything above was measured on **one physical unit the
author owns**, on an isolated segment with nothing else attached. This firmware
build is on no vendor download page, so:

- **other N150RT units may run different builds** and the results may not carry;
- the five other products CVE-2024-51228 names (A3002RU, N300RT, N302RE and
  others) are **untested** — but they are `-CX-` builds from the same SDK
  generation, so the vendor is better placed than the author to say whether the
  same code ships there;
- nothing here was tested against any device the author does not own.

---

## Impact, stated without inflation

**A + B together are an unauthenticated administrative takeover of the web
interface**, reachable from the LAN with no credentials and no prior knowledge.
Combined with the already-public command execution on this build, that is root
on the device.

**C is a denial of service that persists until someone physically power-cycles
the router.** `rcS` starts the web server once and nothing respawns it; the
device continues to route traffic, so a user's first symptom is that the
administration page has stopped existing while the internet still works.

**What this is not.** None of the three is reachable from the WAN in the default
configuration as measured here: `PING_WAN_ACCESS_ENABLED` and remote
administration were off on this unit. The realistic attacker is on the LAN or
behind a browser that can reach it — and this build has **no session and no CSRF
token**, so a browser that has cached HTTP Basic credentials re-sends them by
itself.

**And a limit worth stating to the coordinator rather than hiding.** The device
is end-of-life. This report is not expecting a patch; it is filing the facts so
they exist on the record, and so that anyone still running the model can be told.

---

## Timeline

| date | |
|---|---|
| 2026-08-16 | flash read off the unit; the build identified as one that is on no download page |
| 2026-08-17 | A, B and C measured on the hardware, each against a refutation condition frozen before the first packet |
| 2026-08-17 | prior-art search **by handler** run for a fourth candidate — it returned a 2023 Cisco Talos advisory on the first page and **that finding was withdrawn**. The same search has not yet been run for A, B and C |
| — | report sent · **not yet** |
| — | 90-day public-discussion clock starts on the send date, recorded in `docs/disclosure.md` in the same commit |

---

## What is attached, and what is not

| | |
|---|---|
| attached | the three request bodies, the response transcripts, and the before/after 64 KiB flash snapshots with per-field attribution |
| attached | the decoded configuration structure showing where the credential is stored, **with this unit's own values removed** |
| **not attached** | the flash image. It contains this unit's MAC addresses and radio calibration, which identify one physical device |
| **not attached** | anything about the four items in `docs/disclosure.md` that are static readings only |

---

## Before this can be sent — the blocking step

`docs/disclosure.md` step 2: **re-run the prior-art search for the specific
handler and parameter, not for the product.**

That is not a formality here. On the evening these three were measured, the same
search was run for a fourth candidate this project had been calling its own for
two weeks:

- by product name → nothing;
- **by handler name → Cisco Talos TALOS-2023-1894 / CVE-2023-41251 on the first
  page**, describing the same parameter as a different defect class, published in
  2023.

That finding was withdrawn the same night. A second search, for a different
handler, turned up a published authentication bypass against **this exact Boa
version** that nobody here had tested — it turned out not to apply, but it was
not known not to apply until it was measured.

**So: two searches, two things this project did not know, in one evening.**
Sending A, B or C before doing the same for each of them would risk claiming
something disclosed years ago — for the second time.

**Owner: the author. This file is not sent by anyone else.**
