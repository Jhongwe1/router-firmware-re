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
endpoint named by the CVE does not exist. The advisory covers a family of
Realtek-SDK devices, not this model specifically; the SDK's `root_form[]` is
assembled per-product from build-time feature flags, and this product was built
without the handler while keeping the log-viewer variable and the
`sysCmdselect` page fragment. Vendors ship the parts of the SDK they configure,
and the leftovers are evidence of the configuration, not of the feature.

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
