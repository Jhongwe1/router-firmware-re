# Ghidra triage — W01 baseline

A headless pass, not a reversing session. The goal is to turn "these strings
exist somewhere in a 522 KB binary" into "these specific functions are worth
opening in W03".

Reproduce:

```powershell
.\ghidra\import.ps1 -Label 2.1.2 `
  -Binary \\wsl$\Ubuntu-24.04\home\<user>\fwre-work\extracted\v2.1.2\squashfs-root\bin\boa
```

Output: [`reports/ghidra-strings-2.1.2.json`](../reports/ghidra-strings-2.1.2.json),
[`reports/ghidra-strings-3.4.0.json`](../reports/ghidra-strings-3.4.0.json)

## Load confirmation

| | V2.1.2 | V3.4.0 |
|---|---|---|
| Language | `MIPS:BE:32:default` | `MIPS:BE:32:default` |
| Image base | `0x00400000` | `0x00400000` |
| Functions recovered | 809 | 980 |
| Defined strings | 3,337 (360 matched) | 3,044 (363 matched) |
| Named functions | some survive | **none** |

Ghidra's language matches the ELF header established independently in
[`anatomy-n150rt.md`](anatomy-n150rt.md). Two tools, one answer.

In V2.1.2 some symbols survived stripping — `handleForm`, `translate_uri`,
`FirmwareUpgrade`, `tcpipWanHandler`, `tcpipLanHandler`. Those are free
labelling; start there.

V3.4.0 has **no** named functions, matching its `sstrip`'d section-header-less
ELF. Everything must be reached through data references, which is exactly what
this script produces.

## The functions to open first

| Function | Reached via | Why |
|---|---|---|
| `handleForm` | `"/boafrm/"` (9 xrefs) | **The dispatcher.** Everything under `/boafrm/<name>` routes through here. Recovering how it maps a name to a handler answers the `formSysCmd` question. |
| `translate_uri` | `"boafrm"` | Boa's URI translation — where the `/boafrm/` prefix is recognised, and the place an authentication check would sit if one existed. |
| `FUN_0044c610` | `"/tmp/syscmd.log"` | **Strongest candidate for the CVE-2019-19824 handler.** It is the only function referencing the syscmd log path. |
| `FUN_00450254` | `"/config.dat"` | The only function referencing the config path — CVE-2019-19822's serving side. |
| `FUN_00433880` | `"sysCmdselect"`, `"%s[%d]=%s;\n"` (21 xrefs) | Emits page variables. Explains why `sysCmdselect` exists as a string: the syscmd UI generator is compiled in, even where the page is not shipped. |
| `FirmwareUpgrade`, `FUN_00423e14`, `FUN_0044ebac`, `FUN_0044f2d0`, `FUN_00452d08` | `"COMPCS"` (6 xrefs) | The apmib config (de)serialisers — CVE-2019-19823's storage format. |

## The same map for V3.4.0

Different addresses, same shape — and one entry the 2015 build does not have.

| Function | Reached via | Why |
|---|---|---|
| `FUN_00443090` | `"/tmp/syscmd.log"` | formSysCmd handler candidate, 2020 build |
| `FUN_0040ab18` | `"/config.dat"` | serves the config path |
| `FUN_00440eec` | **`"cp /var/web/config.dat %s"`** and `"rm -rf /var/config.dat >/dev/null 2>&1"` | Config backup/restore. Two shell command strings in one function, one of them with a `%s`. If that `%s` is filled from a request parameter and the result reaches `system()`, it is a command injection. **Highest-value single function found in W01.** |
| `FUN_004413d8` | `"COMPCS"`, `"INVALID config.data FILE"` | the apmib config parser — CVE-2019-19823's format |
| `FUN_004451f8` | `"setting/getSanvas"` | CVE-2019-19825's CAPTCHA endpoint, absent from 2015 |
| `FUN_0042c2cc` | `"sysCmdselect"` | page-variable emitter, same role as 2015's `FUN_00433880` |
| `FUN_00409870` | `"/boafrm/formUpload"`, `"/boafrm/formUploadFile"` | upload paths, one new in 2020 |

## A cheap census of the handler surface

`"submit-url"` has **50 cross-references**, and every one of them is a distinct
function. Realtek's `form*` handlers all read that parameter to decide where to
redirect after processing, so its xref set is effectively a list of the handler
implementations — recoverable without knowing a single handler's name.

Two more strings corroborate it: the boilerplate response templates
`"<html><body><blockquote><h4>%s</h4>"` and its matching OK-button form each
have **41 xrefs**, overlapping heavily with the `submit-url` set. Around 40–50
functions in this binary are request handlers.

The 2020 build gives **40** `submit-url` xrefs against 49 `form*` name strings.
The 2015 build gives 50 against 59. Both approaches agree to within about 20%,
in the same direction — a useful cross-check, and a reminder that neither count
is authoritative: a name string can exist without a handler behind it, and a
handler can exist without its name in the string table. That second case is
precisely the `formSysCmd` situation.

## What this does *not* yet show

- **No decompilation has been read.** Every entry above is an xref, not an
  understood code path.
- **`formSysCmd` is still not resolved.** The evidence says the feature is
  compiled in (`sysCmdselect`, `sysCmdLog`, `/tmp/syscmd.log`) and that
  `FUN_0044c610` is the likely handler, but the mapping from URI to function
  lives inside `handleForm` and has not been read.
- **Whether `.dat` requests are authenticated** is a property of
  `translate_uri` / `process_requests`, which has not been read either.

Those three are W03's opening tasks, in that order.
