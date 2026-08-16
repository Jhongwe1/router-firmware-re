# Disclosure register

What this project has that might be new, what state each item is in, and the
rule that decides what gets published here and what does not.

This file exists because the policy in `README.md` — *anything genuinely new
goes to TWCERT/CC before any public discussion* — had no list attached to it.
A policy with no register is a sentence, not a process: nothing records which
findings it applies to, so nothing can be checked against it later.

## The publication rule

Three categories, and the line between them is the thing to argue with:

| | what it is | published here |
|---|---|---|
| **Finding** | "this handler takes this parameter into `system()`, at this address, in this binary" | **yes.** That is the research, and stating it is how anyone else can check it |
| **Reproduction** | a procedure that produces the effect, with a request that can be copied | **only once the issue is public.** For a CVE disclosed in 2024, a `poc/` directory is a reproduction of published work. For something unreported, it is a zero-day recipe |
| **Tradecraft** | persistence, anti-forensics, lateral movement, credential harvesting on a live host | **no.** No gate in this project asks for it, it produces no checkable fact about this device, and `README.md` scopes it out. Nine such items are listed with their reasons in [`study/test-ledger.md`](../study/test-ledger.md) |

The rule is one sentence: **findings are published, reproductions follow the
disclosure state, tradecraft is not published at all.**

It has a consequence worth stating plainly, because a reader will notice it
anyway: several items below are **already named in `PROGRESS.md` and under
`notes/`**, with addresses. That is deliberate and consistent with the rule —
naming a defect is a finding. What is held back is the reproduction: the
request, the payload, the ordering.

## Status of the candidate originals

"Candidate" is the operative word. Every entry here is a **static reading of a
binary; nothing has been demonstrated on the hardware**, and the literature
search that missed CVE-2024-51228 for two weeks is recent enough to assume
another one may be missed. An item is not original because a search came up
empty; it is original when a search that *would* have found prior art comes up
empty. That search is [`notes/prior-art.md`](../notes/prior-art.md), and it has
been wrong once.

| # | finding | evidence | already stated publicly here | status | what changes it |
|---|---|---|---|---|---|
| **D-1** | `form_formRoute` / `subnet` reaches `system()` in **all three** builds | `BoaGate` R2, [`ghidra-gate-unit-2018.json`](../reports/ghidra-gate-unit-2018.json) | yes — PROGRESS open #6 | **held** | Demonstrated on the device (register `P3-2`), then a prior-art search specifically for this handler. Still present in the 2020 build, so unlike the rest it is not end-of-life-only |
| **D-2** | Omitting `submit-url` makes the handler copy into a read-only literal — a one-request unauthenticated crash | W04, measured on V2.1.2; unverified on this build | yes — README G3 notes | **held** | Register `P4-1`. If it does not reproduce on this build it is a V2.1.2 finding and nothing more |
| **D-3** | The authorisation gate's exemption comparison is an unanchored substring test, so an exempt string placed anywhere in a path may satisfy it | [`auth-flow-2018.md`](../notes/auth-flow-2018.md), instruction level | yes — the mechanism is described | **held** | Register `P2-2`. The 2020 build has the same shape, which is why this one matters beyond this unit |
| **D-4** | An empty stored administrator password appears to skip the credential comparison entirely | the branch at `0x0040bd18`, read at instruction level | no | **held** | Register `P10-4`. Reachability matters more than the branch: if no unauthenticated path can set it empty, this is a curiosity |
| **D-5** | Two published advisories name endpoints that exist in no dispatch table (`formWlwds`, `fromStaticDHCP`) | three `root_form[]` recoveries | yes — [`cve-status.md`](../notes/cve-status.md) | **publishable now** | Not a vulnerability: a correction to a public record. It goes to the CNA/MITRE, not to TWCERT/CC, and nothing is embargoed |
| **D-6** | CVE-2024-51228 is scored `PR:H`; the researcher and this binary both read as no authorisation required | [`auth-flow-2018.md`](../notes/auth-flow-2018.md), [`prior-art.md`](../notes/prior-art.md) | yes | **publishable after `P3-3`** | The vulnerability has been public since 2024-11-27, so nothing is embargoed; only the score is in question. One request settles it |
| **D-7** | `wan_disconnect` invokes a DNS-spoofing helper that is present in this rootfs | [`n150rt-unit-2018.json`](../reports/n150rt-unit-2018.json) | yes — `notes/` | **not a finding yet** | Register `P6-10`. Currently a behaviour nobody has looked at, not a defect |
| **D-8** | Three unread areas: the remote-upgrade helper's outbound connections, the upload handler's `filename` field, two shipped factory private keys | inventory only | yes | **not findings yet** | Register `P8-10`, `P8-18`, `P10-7`. Listed so that "unexamined" does not quietly become "clean" |

**Nothing in the table is reported to anyone yet, and nothing should be.** All
of it is static. The project's own rule is that a static reading goes nowhere
until W05/W06 demonstrates it on the hardware, and that rule is the reason this
register can be published at all: an unreported finding stated without a
reproduction, on an end-of-life device the author owns, is a research note.

## Not original, and worth saying so

- **CVE-2024-51228 is not this project's discovery.** It names this exact build
  string and was published on 2024-11-27. The reachability result here is an
  independent derivation of a disclosed claim. `notes/prior-art.md` had no 2024
  entries at all when the work was done, and the gap is recorded there rather
  than smoothed over.
- **The `submit-url` overflow idiom, the `localPin` injection, the plaintext
  credentials and the 2015 backdoor account all have identifiers.** Locating
  them in a third build is verification work, not discovery.

## Procedure when something does become reportable

1. Demonstrate it on the hardware, with the request and response recorded, and
   register the result (`tools/rtcase.py record`) so the claim carries evidence.
2. Re-run the prior-art search **for that specific handler and parameter**, not
   for the product. The 2024 miss happened because the search was by product
   name and label rather than by the build string in hand.
3. Report to **TWCERT/CC** with the reproduction. The device is end-of-life and
   the vendor's history here is a five-year, three-step remediation, so plan for
   no vendor response rather than treating silence as an anomaly.
4. Hold public discussion of the reproduction until the coordinator closes the
   case or 90 days pass from the report, whichever is first. Record the date the
   clock started **in this file**, in the same commit as the report.
5. If the coordinator declines the case — plausible for end-of-life hardware —
   that is a decision, and it gets written here with its date. It is not a
   licence to publish immediately; it is the point at which the author decides,
   on the record.

## What this file is not

It is not a list of everything wrong with the device. That is
[`notes/cve-status.md`](../notes/cve-status.md), and most of it has been public
for years. This file tracks only the subset where **this project might be the
first to say something**, because that is the only subset the disclosure policy
constrains.
