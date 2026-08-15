# Reading the builds across: 2015, 2018, 2020

**Question carried out of W02 (open #4):** `/bin/boa` on this unit was extracted
and hashed but never read. Every `boa` claim in this repository describes
V2.1.2 or V3.4.0 — two binaries this device has never executed.

This note is the transfer. It measures the same things on the resident build
that W03/W04 measured on the two published ones, and it says which claims moved
across and which did not.

> **Section 1 was written and committed before any measurement script was run
> against the 2018 binary.** That ordering is the point: a prediction recorded
> after the fact is a description. The commit timestamp is the evidence.

---

## 1. Predictions, written 2026-08-16 before the tools ran

The binary under test: `/bin/boa` from this unit's flash,
`sha256 19fe29d71aa1cc1e893627f17a0f14b03ca75f6936318df4062df4fb153909f7`,
485,012 bytes, self-identifying as `boa: server built Jan 10 2018 at 14:57:54`.

| Measurement | 2.1.2 (known) | **unit-2018 (predicted)** | 3.4.0 (known) |
|---|---|---|---|
| `root_form[]` entries | 59 | **55–59** | 49 |
| `formSysCmd` in the table | no | **no** | no |
| `formWsc` in the table | yes | **yes** | yes |
| `strcpy` call sites | 587 | **500–600** | 577 |
| `submit-url` idiom, handler count | 34 | **28–34** | — |
| `lastUrl` size | 100 | **100** | — |
| `AUTHG_*` in the MIB table | present | **present** | absent |
| the authorisation gate | `strstr(uri, "htm")` | **like 2015** | `.htm`/`.asp`/POST |

### Why these numbers

The 2018 `boa` is 485,012 bytes, between 2015's 522,556 and 2020's 404,904.
Size alone would put it midway. But the flash layout is not midway — it is
**2015's**: this unit has a `w6cg` web-resource section and its kernel is at
`0x060000`, the arrangement the 2020 image abandoned
([`flash-layout.md`](flash-layout.md) §3). Its SquashFS is LZMA like 2015, not
XZ like 2020.

So the prediction is not "halfway between". It is **a late member of the 2015
family**: closer to 59 than to 49, still carrying `AUTHG_*`, still gating on a
bare `htm` substring.

### One prediction in that table is nearly worthless, and it should be said now

**`root_form[]` at 50–59 would have been a non-prediction.** The two known
values are 49 and 59; an interval that spans everything except the low endpoint
cannot fail in any interesting way. It has been tightened to **55–59** on the
strength of the layout evidence above — which makes it able to be wrong, in the
direction that would matter: if the 2018 table has come down into the low 50s,
this build has already started shedding the handlers the 2020 build dropped, and
"a late member of the 2015 family" is the wrong description of it.

The same objection does not apply to `strcpy` at 500–600: that interval brackets
both known values because the honest expectation is "this is the same codebase",
and the informative outcome is a number **outside** it, which would mean either a
real rewrite or — far more likely, on this project's record — the PLT bug again.

### The falsifiable specifics

Interval predictions are cheap. These are the ones that name a thing:

1. **The four handlers W04 left open** — `formDdns`, `formNewSchedule`,
   `formSysLog`, `formWanTcpipSetup` carry the `submit-url` idiom in 2015 and do
   not show it in 2020 while still existing (W04 open #5). **Predicted: all four
   present in the 2018 table and all four still carrying the idiom.**
2. **`formWsc`'s `localPin` line** — `sprintf(buf[100], "flash set
   HW_WLAN0_WSC_PIN %s", localPin); system(buf)` is byte-for-byte identical in
   2015 and 2020. **Predicted: present and unchanged in 2018.** If it is, then
   the line reaches from 2015 to 2020 through a build made by different people in
   between, and CVE-2025-3987/4462 describes something that survived three
   independent release cycles.
3. **`/bin/skt` is deleted from this rootfs but `#skt&` is still in `rcS`**
   (measured in W02). **Predicted: `boa` itself is untouched by that change** —
   no `skt` string, no reference, in any of the three.

### What would make this whole exercise suspicious

If every prediction lands, the correct response is not satisfaction. Three
builds spanning five years, and the middle one made by a different team on a
different day, agreeing on **every** measurement, is more consistent with a tool
reporting the same thing regardless of input than with the firmware. This
project has been burned that way three times, and the tell each time was
agreement, not disagreement.

So the self-check runs first, before the table is filled in: any import whose
call-site count falls to 0 or 1 stops the day. `sstrip`'d-PLT false negatives
have appeared **twice** (`BoaSinks` in W03, `BoaArgTrace` re-implemented in W04),
and the 2018 binary is a third opportunity.

---

## 2. Measurements

*(filled in below as each script completes)*
