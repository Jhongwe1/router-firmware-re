# `submit-url`: four CVEs, one idiom, thirty-odd handlers

**Question carried out of W03:** `sink-inventory.md` ranked `formWsc` first and
said triaging the other 47 handlers that contain a `strcpy` "is the shape of a
W07 systematic hunt, not something to eyeball now". Meanwhile four 2025 CVEs
against this model — 3990, 3991, 3992, 3993 — all name the parameter
`submit-url` in four different handlers, which is not what four independent bugs
look like.

**Answer:** it is not four bugs. It is one three-line tail idiom, copy-pasted
into **34 handlers in V2.1.2 and 26 in V3.4.0**, and it contains **two** defects.
The CVE database has so far assigned IDs to four instances of one of them.

```c
/* the tail of form_form2ndSetup @0x0041434c, V2.1.2 — and of 33 others */
pcVar1 = req_get_cstream_var(param_1, "submit-url", "");
needReboot = 1;
if (*pcVar1 == '\0') {
    strcpy(pcVar1, "/status.htm");          /* (A) @0x00414594 */
}
strcpy(&lastUrl, pcVar1);                    /* (B) @0x004145ac */
send_redirect_perm(param_1, "/msg.htm");
```

> **Scope.** Static only. No device has been powered on — W02 is blocked on
> hardware. Everything below is "the code reads this way"; the confirming
> requests are listed at the end. Nothing here has been reported to anyone.

Recovered by [`BoaArgTrace.java`](../ghidra/scripts/BoaArgTrace.java) into
[`reports/ghidra-argtrace-2.1.2.json`](../reports/ghidra-argtrace-2.1.2.json)
and [`reports/ghidra-argtrace-3.4.0.json`](../reports/ghidra-argtrace-3.4.0.json).

## (B) — the one the CVEs describe

`lastUrl` is not an anonymous global. V2.1.2 keeps a symbol table, and it is
exact:

```
$ readelf -sW bin/boa | grep -E 'lastUrl|needReboot|run_init_script_flag'
   421: 0049087c   100 OBJECT  GLOBAL DEFAULT   23 lastUrl
   241: 004908e0     4 OBJECT  GLOBAL DEFAULT   23 needReboot
        004908e4     4 OBJECT  GLOBAL DEFAULT   23 run_init_script_flag
```

`0x49087c + 100 = 0x4908e0`. So the destination is **100 bytes in `.bss`,
immediately followed by `needReboot` and then `run_init_script_flag`** — and
`needReboot` is assigned on the line above the copy.

`strcpy` is unbounded and `submit-url` is an arbitrary POST parameter, so a
101-byte value writes the 101st byte into `needReboot`, and it continues from
there through `.bss` for as long as the value runs.

Two things follow that are worth stating separately, because they are different
claims:

- **This is a data overflow, not a return-address overflow.** `lastUrl` is in
  `.bss`, so no stack canary question arises and no saved `ra` is nearby. What
  it corrupts is adjacent globals; `.bss` runs from `0x0048b750` for `0x1b2c8`
  bytes, so there is a great deal of it after `lastUrl`.
- **The nearest two neighbours are control flags**, not padding. Whether
  setting them from a request is interesting depends on who reads them, which is
  a question this note does not answer.

### Which CVEs this is

Every one of these names `TOTOLINK N150RT 3.4.0-B20190525` — this model, not a
sibling. The endpoint column is the CVE's own text.

| CVE | endpoint as published | present in our table? |
|---|---|---|
| CVE-2025-3990 | `/boafrm/formVlan` | yes |
| CVE-2025-3991 | `/boafrm/formWdsEncrypt` | yes |
| CVE-2025-3992 | `/boafrm/formWlwds` | **no — the handler is `formWlWds`** |
| CVE-2025-3993 | `/boafrm/formWsc` | yes |

`handleForm` matches names with `strlen(a) == strlen(b) && memcmp(a, b, n) == 0`
and consults no second table ([`dispatch-table.md`](dispatch-table.md)). So
**`POST /boafrm/formWlwds` returns 404 on this firmware**: the bug CVE-2025-3992
describes is real and is in `formWlWds`, but the endpoint as published cannot
reach it. The same applies to CVE-2025-3995's `fromStaticDHCP` (the handler is
`formStaticDHCP`). W01 flagged both spellings as "verify before believing"; this
is the verification, and the spellings are wrong.

The other 30 handlers carrying the identical copy have no CVE. The four that do
are a sample, not a set.

## (A) — the defect the CVEs do not describe

`strcpy(pcVar1, "/status.htm")` writes **into the buffer the accessor returned**,
and that buffer is not sized for it. `req_get_cstream_var` @ `0x0041323c`:

```c
    __n = find_var(scratch, body, name, 0x1000);
    ...
    if (-1 < (int)__n) {
        param_3 = malloc(__n + 1);          /* exactly the value's length */
        memcpy(param_3, scratch, __n);
        *(char *)((int)param_3 + __n) = 0;
    }
    return param_3;                          /* else: the caller's default */
```

Two cases, and they differ:

| request contains | accessor returns | `strcpy(p, "/status.htm")` writes 12 bytes into |
|---|---|---|
| `submit-url=` (present, empty) | `malloc(1)` | a **1-byte heap chunk** |
| no `submit-url` at all | the caller's `""` literal @ `0x476418` | **`.rodata`** |

`.rodata` sits at `0x00465830`–`0x00477740`, inside the first `PT_LOAD`, and
that segment is `R E`:

```
  LOAD  0x000000 0x00400000 0x00400000 0x77744 0x77744 R E 0x10000
  LOAD  0x078000 0x00488000 0x00488000 0x0368c 0x1ea18 RW  0x10000
```

So the second case is a write to a read-only mapping. Boa is a single process
serving requests from one loop (`process_requests`), so **as the code reads, a
POST to any of these 34 endpoints with no `submit-url` parameter at all kills the
web server** — no authentication needed on the 2015 build, because the gate there
only runs for URIs containing `htm` ([`auth-flow.md`](auth-flow.md)).

That would also explain a detail of the published PoCs for this device family
that otherwise looks like noise: they all carry `submit-url=/something.htm`.
Omitting it does not produce a cleaner request; it produces no response at all.

**This is the part to be most careful about.** "Writes to a read-only page" is a
static reading of segment flags plus a static reading of a return path. It is one
`curl` from being settled and zero experiments from being wrong.

## Read across the two builds

| | V2.1.2 | V3.4.0 |
|---|---|---|
| handlers reached by a request parameter into a sink | 39 | 30 |
| of those, carrying the `submit-url` idiom | 34 | 26 |
| `strcpy` call sites inside handlers | 151 | 140 |
| `sprintf` call sites inside handlers | 114 | 87 |

The handlers that lost the idiom between builds are exactly the ones V3.4.0
deleted — `form2ndSetup`, `formBufferMemory`, the six IPv6 handlers, `formSSH`,
`formWlSiteSurveys` — which is the removal list `dispatch-table.md` derived
independently from the recovered arrays. Two methods, one answer.

Four handlers are the exception: `formDdns`, `formNewSchedule`, `formSysLog` and
`formWanTcpipSetup` still exist in 2020 but no longer show the taint. Either they
were rewritten or the tracer's six-hop walk does not reach through whatever
replaced it. **Not established. Next step: decompile those four and read the
tail.**

## What would confirm any of this

```
POST /boafrm/formWlWds   submit-url=AAAA...×200    -> lastUrl overflows into needReboot
POST /boafrm/formWlWds   (no submit-url at all)    -> expect: no response; boa gone
POST /boafrm/formWlwds   submit-url=/status.htm    -> expect: 404 (the CVE's spelling)
```

The third is the cheapest and the most useful, because it distinguishes "the CVE
is wrong about the endpoint" from "we misread the dispatcher" with one request.

Needs the physical unit (W02, blocked) or `boa` under emulation (W05).

## How the first version of this note was wrong

It did not exist, because W03's census could not see the idiom. The first run of
`BoaArgTrace` reported **1** tainted call site out of 304 — and the one it found
was `formFilter`/`url`, not any of the three `formWsc` parameters W03 had already
read by hand. That mismatch is the only reason the tool was checked instead of
believed.

The cause was two copies of the same resolution logic: `describe()` could turn a
varnode into the string `"targetAPSsid"` and `firstLiteralArg()` could not, so
every parameter that reached a sink through `sprintf` was reported as an
anonymous `call-result`. The fix was to delete one of the copies.

Then the corrected tool reported 86 tainted sites in V2.1.2 and **0** in V3.4.0,
with `self_check: consistent` both times, because the `accessor:` option was
compared against a lower-cased name and silently matched nothing. And when *that*
was fixed it still reported 0 `strcpy` sites in V3.4.0 — the sstrip'd-PLT bug
`BoaSinks` had already solved in W03 and that this script had re-implemented
without the fix.

Three failures, all of the same species: **a check that never fires never fails.**
None was caught by a self-check. All three were caught by the project's own rule
— read the two builds across, not down — because one codebase five years apart
cannot go 86 → 0. The resolution logic now lives once, in
[`BoaPlt.java`](../ghidra/scripts/BoaPlt.java), and the self-check now fails when
a declared option matches nothing.
