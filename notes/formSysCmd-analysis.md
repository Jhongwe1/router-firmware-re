# `formSysCmd` — a negative result

W01 left this open: the string `formSysCmd` is absent from both `boa` binaries,
but `sysCmdselect`, `sysCmdLog` and `/tmp/syscmd.log` are all present, so the
CVE-2019-19824 feature looked compiled-in with only its dispatch name missing.
The W01 triage note nominated `FUN_0044c610` — the only function referencing
`/tmp/syscmd.log` — as "the strongest candidate for the CVE-2019-19824 handler".

**That was wrong, and the dispatch table says why.**

## `/boafrm/formSysCmd` is not routed on this firmware

`handleForm` compares the URI tail against `root_form[]` with
`strlen(a) == strlen(b) && memcmp(a, b, n) == 0` — an exact match against a
NULL-terminated array, with no fallback, no prefix rule and no second table
([`dispatch-table.md`](dispatch-table.md)). The recovered arrays hold **59**
entries in V2.1.2 and **49** in V3.4.0, and `formSysCmd` is in neither. So
`POST /boafrm/formSysCmd` reaches `send_r_not_found`.

This is a stronger statement than W01's "the string is absent". A missing string
is consistent with a handler registered under a name built at runtime, or with a
name the string scanner failed to type as a string. A recovered, exhaustive,
NULL-terminated dispatch array is not: if it is not in the table, `handleForm`
cannot reach it.

## What `FUN_0044c610` actually is

It is in the **ASP page-variable table** at `0x004885d0`, registered under the
name `sysCmdLog`, and read by `handleScript` — not by `handleForm`.

```
table entry 00488708   sysCmdLog -> 0044c610
```

So it is the *output* side of the feature: the thing that renders
`/tmp/syscmd.log` into a page when a page asks for `<% sysCmdLog %>`. The
half that would *run* a command is the part that is missing.

That is the correction. W01 reached a plausible hypothesis from an xref;
recovering the table structure replaced it with a role.

## What this does and does not say about CVE-2019-19824

**Says:** on TOTOLINK N150RT V2.1.2 and V3.4.0, the `/boafrm/formSysCmd`
endpoint named by the CVE does not exist.

**W04 correction — the dates say why, and it is not what this note first said.**
The first version of this page explained the absence as a build-time feature
flag: "this product was built without the handler". That is a guess, and a
weaker one than the evidence supports. Pierre Kim's 2015 advisory
(`2015-totolink-0x02.txt`) names **N150RT-V2** and reports it vulnerable to
**CVE-2015-9551** — unauthenticated RCE via `/boafrm/formSysCmd` — *"until last
firmware `TOTOLINK-N150RT-V2.1.1-B20150708.1548.web`"*. Our V2.1.2 image is
dated **2015-08-25**, i.e. the build after the last one he reports as
vulnerable, and in it the handler is gone from the dispatch table.

So the likeliest reading is not a feature flag. It is **the fix, observed**: the
vendor removed the handler in the release that answered the disclosure — the same
release that commented out `#skt&` and kept the binary
([`skt-analysis.md`](skt-analysis.md)), and that kept `onlime_r` in
`/etc/passwd.org` ([`credentials.md`](credentials.md)). One of three things
fixed properly.

**This is falsifiable and not yet falsified.** V2.1.1-B20150708 would settle it
in one command: recover its `root_form[]` and see whether `formSysCmd` is there.
That image is a fetchable artefact and the check is listed as the next step.

**Does not say:** that this device is not vulnerable to command execution.
[`sink-inventory.md`](sink-inventory.md) lists 158 `system()` call sites in
V2.1.2 with nine of them inside request handlers, and at least two request
parameters reach `system()` with no metacharacter filtering at all. The RCE on
this device is not `formSysCmd`; it is `formWsc`.

**Also does not say** that the feature could not be reachable another way. Not
yet ruled out, and listed as W04 work:

- a second binary in the image serving its own `/boafrm/`-style routes;
- `formAjaxSet` (V3.4.0 only) accepting an operation name in its JSON body;
- the CGI path — `translate_uri` still honours `application/x-httpd-cgi`, so
  anything executable that lands in the docroot is a separate surface.

## Why this belongs in the write-up

The interesting result here is the method, not the endpoint. Three artefacts —
a missing string, a suggestive log path, and a compiled-in page fragment — all
pointed the same way, and the direction was wrong. What settled it was
recovering the data structure that does the routing, rather than accumulating
more circumstantial references to it.

The cost of not doing that would have been a write-up claiming a known CVE
reproduces on a device where the endpoint returns 404.
