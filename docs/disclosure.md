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
| **Tradecraft** | persistence, anti-forensics, lateral movement, credential harvesting on a live host | **no.** No gate in this project asks for it, it produces no checkable fact about this device, and `README.md` scopes it out. Nine such items are listed with their reasons in [`test-ledger.md`](../test-ledger.md) |

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
| **D-1** | ~~`form_formRoute` / `subnet` reaches `system()` in **all three** builds~~ | `BoaGate` R2 — **and the tool was wrong** | yes — PROGRESS open #6 | ❌ **withdrawn 2026-08-17** | Two independent reasons, and the order they arrived in matters. **Prior art, found before the test:** Cisco Talos TALOS-2023-1894 / CVE-2023-41251 reports this exact parameter in the same Realtek rtl819x SDK family as a 100-byte `sprintf` stack overflow with **no `system()` anywhere** — published 2023, and a search by *handler* found it on the first page where a search by *product* had returned nothing. **Then the measurement:** `P3-2` fired on the device produced zero command execution, while `localPin` on `formWsc` produced four ICMP echo requests through the same oracle. `BoaGate` R2 mis-classified an `sprintf` site as a `system()` site, and that rule feeds conclusions about all three builds |
| **D-2** | ~~Omitting `submit-url` makes the handler copy into a read-only literal — a one-request unauthenticated crash~~ | W04, measured on V2.1.2 | yes — README G3 notes | ❌ **does not reproduce on this build, 2026-08-17** | Register `P4-1`, and this row's own text said what to do: *"if it does not reproduce on this build it is a V2.1.2 finding and nothing more."* It does not. A POST body omitting `submit-url` returns 200 on `formNtp` and `formWlanSetup` and the server survives. `P4-3` went further and refuted the mechanism with a **positive** witness: `formNtp` echoes `submit-url` into its `Location` header, and 800 bytes come back as 799 `A`s with no truncation at 100 — so the value provably reaches the code that consumes it and nothing happens. This build does not use the `lastUrl[100]` idiom W04 measured in 2015 |
| **D-3** | The authorisation gate's exemption comparison is an unanchored substring test, so an exempt string placed anywhere in a path may satisfy it | [`auth-flow-2018.md`](../notes/auth-flow-2018.md), instruction level | yes — the mechanism is described | **held** | Register `P2-2`. The 2020 build has the same shape, which is why this one matters beyond this unit |
| **D-4** | An empty stored administrator password skips the credential comparison entirely, **and an unauthenticated request can set it empty** | measured on the device 2026-08-17; the branch at `0x0040bd18` read at instruction level in W04-2 | no — and this is the one entry that must stay that way for now | **held, and it is now the most serious item in this table** | Register `P10-4` **and `P10-3`**, and the pair is the finding. This row used to say *"reachability matters more than the branch: if no unauthenticated path can set it empty, this is a curiosity"*. **There is such a path and it needs nothing.** `formPasswordSetup` carries `Cusername`/`Cpassword` fields for the current credentials and the handler does not check them, so an unauthenticated POST that does not know the current password changes it. Set it empty and `password.htm` returns 200 and 5,322 bytes of real HTML with no `Authorization` header at all — and a **wrong** password is also accepted, so the comparison is skipped rather than matched. Next step is the per-handler prior-art search, not a report: the search that found Talos for D-1 has not been run for this handler |
| **D-5** | Two published advisories name endpoints that exist in no dispatch table (`formWlwds`, `fromStaticDHCP`) | three `root_form[]` recoveries | yes — [`cve-status.md`](../notes/cve-status.md) | **publishable now** | Not a vulnerability: a correction to a public record. It goes to the CNA/MITRE, not to TWCERT/CC, and nothing is embargoed |
| **D-6** | CVE-2024-51228 is scored `PR:H`; it requires no credentials at all | **demonstrated on the device 2026-08-17** — [`poc/02-command-injection.md`](../poc/02-command-injection.md) | yes | ✅ **publishable now, and published** | `P3-3` fired: a POST carrying no `Authorization` header made the router send ICMP echo **requests** to the bench host, and returned `cat /etc/version` through the document root. **And the same request WITH valid credentials behaves identically**, which is what rules out "something else was carried in" — an unauthenticated success on its own does not. If `PR:N` is right the base score is **8.8 HIGH** rather than 6.8 MEDIUM. The vulnerability itself has been public since 2024-11-27, so nothing is embargoed and the reproduction ships in `poc/`. This is a correction to a public record and it goes to the CNA, not to TWCERT/CC |
| **D-7** | `wan_disconnect` invokes a DNS-spoofing helper that is present in this rootfs | [`n150rt-unit-2018.json`](../reports/n150rt-unit-2018.json) | yes — `notes/` | **not a finding yet** | Register `P6-10`. Currently a behaviour nobody has looked at, not a defect |
| **D-8** | Three unread areas: the remote-upgrade helper's outbound connections, the upload handler's `filename` field, two shipped factory private keys | inventory only | yes | **not findings yet** | Register `P8-10`, `P8-18`, `P10-7`. Listed so that "unexamined" does not quietly become "clean" |
| **D-9** | An unauthenticated, **well-formed** POST carrying only `submit-url` holds the device's single-process web server for 4.7–9.7 s; about forty-five in sequence stop it answering entirely, and nothing respawns it | measured twice on the device, [`BENCH-LOG.md`](../BENCH-LOG.md) 2026-08-17 afternoon; per-request `elapsed_ms` in the transcripts | yes — the numbers are in `PROGRESS.md` and `BENCH-LOG.md` | **held, and deliberately unclassified** | Distinct from **D-2**: that one omits `submit-url` and writes into a read-only literal. This one is a legal request. Three things are unmeasured and all three change what it is — whether *one* request suffices, how long a single stall lasts, and whether prior art already covers it. Register: none yet; it came out of `P1-4` |
| **D-10** | An unauthenticated configuration write also overwrites the **factory-default** region: `COMPDS` moved in the same 19 fields as `COMPCS` plus the four that had distinguished them, each to `COMPCS`'s value. So "restore factory defaults" would restore whatever was last written | 64 KiB snapshots either side, attributed field by field; `libapmib`'s own checksum passes on both regions | yes — `PROGRESS.md` W05 close-out | **held** | The impact claim depends on `P9-9` (does reset actually restore from `COMPDS`), which is scheduled W07 and is destructive. Until that runs, the mechanism is measured and the *consequence* is inference. Also answers W04-2 open #20 — what persists `COMPCS` |

| **D-11** | **A single unauthenticated, well-formed POST to one form handler removes the web server until the device is power-cycled.** No payload, no overlong parameter, no credentials | measured on the device 2026-08-17 with a control: three POSTs of the same shape to a different handler immediately before it were all served normally, then one to the handler in question returned nothing at all and the listening socket was gone 30 s later, while ICMP to the device stayed at 1.6 ms | the numbers and the mechanism are in `PROGRESS.md`; **the handler name is not published here** | **held** | Distinct from **D-9** (a legal POST *stalls* the single-process server 4.7–9.7 s, and roughly forty-five in sequence stop it) and from the withdrawn **D-2**. This is **one** request and the effect is permanent, because `rcS` starts `boa` once and nothing respawns it. It also revises W05's own reading of its data: that session attributed the outage to *volume*. Whether the W05 transcript shows this same handler is a re-reading of that record, not something 2026-08-17 measured. No register row yet — it came out of a handler census, not a planned test |

**Nothing in the table has been reported to anyone, and the two that changed
state on 2026-08-17 changed in opposite directions.** `D-6` became publishable
because the hardware demonstrated it and the underlying CVE is two years public.
`D-1` and `D-2` were **withdrawn** — one because a tool was wrong and published
prior art said so before the test ran, the other because the defect simply is not
in this build. That is what this register is for: it is as much a record of
claims retracted as of claims made, and a table that only ever grows is a table
nobody is checking.

**`D-4` and `D-11` are the ones that now matter**, and neither has had the
per-handler prior-art search that step 2 of the procedure below requires. The
search that produced Talos for `D-1` took one query and overturned a finding;
running it *after* a report would be the wrong order.

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
