# The `/boafrm/` dispatch table

**Question carried out of W01:** the string `formSysCmd` is absent from both
`boa` binaries, yet `sysCmdselect`, `sysCmdLog` and `/tmp/syscmd.log` are all
present. W01 could not say which functions are actually reachable as
`/boafrm/<name>`, only which strings looked like they might be.

**Answer:** both builds carry a NULL-terminated array of
`{char *name; void (*handler)(request*, int, char**)}`, and `handleForm` walks
it. Recovering the array turns 59 suggestive strings into 59 confirmed routes.

Regenerate:

```powershell
.\ghidra\import.ps1  -Label 2.1.2 -Binary \\wsl$\Ubuntu-24.04\home\<user>\fwre-work\extracted\v2.1.2\squashfs-root\bin\boa
.\ghidra\analyze.ps1 -Label 2.1.2 -Script BoaFormTable -Binary <same path>
```

Output: [`reports/ghidra-formtable-2.1.2.json`](../reports/ghidra-formtable-2.1.2.json),
[`reports/ghidra-formtable-3.4.0.json`](../reports/ghidra-formtable-3.4.0.json).

| | V2.1.2 | V3.4.0 |
|---|---|---|
| `boa` SHA-256 | `ddda5a4f…d97a` | `2f53eeac…0a21` |
| `root_form[]` | `0x00488720`, **59** entries | `0x004715c0`, **49** entries |
| read by | `handleForm` @ `0x004127f4` | `FUN_0040ee60` |
| ASP page-variable table | `0x004885d0`, 41 entries | `0x00471750`, 39 entries |
| read by | `handleScript` | `FUN_0040ef90` |
| handlers named in the program DB | 98 of 100 | 87 of 88 |

The two remaining entries in each build already carried a symbol that survived
stripping; those are kept and the table name added as a secondary label, because
an original symbol is worth more than a name a script derived.

## The dispatcher

`handleForm`, decompiled from V2.1.2 (symbol survived stripping):

```c
pcVar2 = strstr((char *)(param_1 + 0x8d4), "/boafrm/");
apmib_get(0x68, &DAT_004885c0);
if (pcVar2 != NULL) {
    ppuVar1 = &PTR_s_formWlanSetup_00488720;              /* root_form[] */
    while (ppuVar5 = ppuVar1, __s = *ppuVar5, __s != NULL) {
        __n = strlen(pcVar2 + 8);                          /* skip "/boafrm/" */
        sVar3 = strlen(__s);
        if (__n == sVar3) {
            iVar4 = memcmp(pcVar2 + 8, __s, __n);
            ppuVar1 = ppuVar5 + 2;                         /* +8 bytes: next entry */
            if (iVar4 == 0) {
                send_r_request_ok2(param_1);
                (*(code *)ppuVar5[1])(param_1, 0, 0);      /* call the handler */
                ...
                return;
            }
        }
        else { ppuVar1 = ppuVar5 + 2; }
    }
}
send_r_not_found(param_1);
```

Three things this settles:

1. **Matching is exact**, not prefix: `strlen(uri+8) == strlen(name)` before
   `memcmp`. A handler is reachable under exactly one spelling.
2. **The stride is 8 bytes** — `ppuVar5 + 2` on a `char **`.
3. **`handleForm` performs no authorisation of any kind.** It goes from URI
   match straight to `send_r_request_ok2()` and then the handler. Whatever gates
   this request happened earlier — see [`auth-flow.md`](auth-flow.md).

## Where the published SDK source is wrong for this device

The rtl819x SDK source in circulation declares the element as:

```c
typedef struct { char name[80]; void (*function)(request *, int, char **); } form_name_t;
```

That is 84 bytes per entry with the name stored **inline**. These binaries do
not do that — the name is a pointer and entries are 8 bytes apart, confirmed
twice over: by `ppuVar5 + 2` in the dispatcher, and by the recovered table
having exactly the entry count W01 arrived at independently by counting
`form*` strings (59 and 49).

This is why [`BoaFormTable.java`](../ghidra/scripts/BoaFormTable.java) tests for
the shape `[ptr-to-C-string][ptr-into-executable-memory]` repeating on a stride
rather than assuming either layout. A leaked SDK is a hypothesis about the
binary in front of you, not a specification of it.

## Telling the two tables apart

The form dispatch table and the ASP page-variable table are structurally
identical and adjacent in memory. They are separated here by **who reads them**:
the function referencing the base of one is `handleForm`, the other
`handleScript`. Both symbols survived stripping in V2.1.2, which is what makes
the assignment checkable rather than assumed; the V3.4.0 assignment is carried
across by the same structural relationship.

The distinction matters because the ASP table is *not* request routing. Its
entries are names callable from `<% ... %>` inside a page — `getInfo`,
`wirelessClientList`, `sysCmdLog` — and reaching them requires serving a page
that calls them, which is a different reachability argument entirely.

## V2.1.2 — `root_form[]`, 59 entries @ `0x00488720`

| name | handler | | name | handler |
|---|---|---|---|---|
| formWlanSetup | `0x00447258` | | formOpMode2 | `0x00453858` |
| formWlanRedirect | `0x0043c590` | | formIpQoS | `0x0041e684` |
| formWep | `0x00447c38` | | formDosCfg | `0x00454148` |
| formWlanMultipleAP | `0x00448f18` | | formRadvd | `0x0045e5dc` |
| formTcpipSetup | `0x0041a3b4` | | formDnsv6 | `0x0045acb0` |
| form2ndSetup | `0x0041434c` | | formDhcpv6s | `0x0045d12c` |
| formPasswordSetup | `0x00453fc8` | | formIPv6Addr | `0x0045b6d0` |
| formNotice | `0x00453540` | | formIpv6Setup | `0x0045c0d0` |
| **formLogin** | `0x0044e78c` | | formTunnel6 | `0x0045a890` |
| formLogout | `0x0044c404` | | formNtp | `0x00452f94` |
| formUpload | `0x0044f2d0` | | formWizard | `0x00451f00` |
| formWlAc | `0x004488b0` | | formWizards | `0x004511c4` |
| formAdvanceSetup | `0x00448dcc` | | formQuickSetup | `0x004507fc` |
| formReflashClientTbl | `0x004133d0` | | formPocketWizard | `0x004505a8` |
| formWlEncrypt | `0x00447d94` | | formRebootCheck | `0x00451798` |
| formStaticDHCP | `0x0041a740` | | formSiteSurveyProfile | `0x004517ec` |
| formVlan | `0x0041c070` | | formSysLog | `0x0045399c` |
| formWanTcpipSetup | `0x004195cc` | | **formSaveConfig** | `0x00450254` |
| formRoute | `0x00456314` | | formBufferMemory | `0x00453dc4` |
| formPortFw | `0x0041c7a8` | | formUploadConfig | `0x00452d08` |
| formFilter | `0x0041d72c` | | formSchedule | `0x00446358` |
| formSpiFwall | `0x0041d04c` | | formRebootSchedule | `0x00446744` |
| formDMZ | `0x0041d2d0` | | formNewSchedule | `0x00446de4` |
| formDdns | `0x00454e18` | | formWirelessTbl | `0x0043c680` |
| formSSH | `0x00455168` | | formStats | `0x0044c48c` |
| formSelLang | `0x0045536c` | | formWlSiteSurvey | `0x0044b768` |
| formOpMode | `0x004516dc` | | formWlSiteSurveys | `0x0044bff4` |
| formOpMode1 | `0x0044e6e8` | | formWlWds | `0x004495a0` |
| | | | formWdsEncrypt | `0x00449b74` |
| | | | **formWsc** | `0x0044a190` |
| | | | formTR069Config | `0x0045f03c` |

Full V3.4.0 listing is in the JSON; the interesting part is the difference.

## What changed between 2015 and 2020

**Removed (16):** `form2ndSetup`, `formBufferMemory`, `formDhcpv6s`,
`formDnsv6`, `formIPv6Addr`, `formIpv6Setup`, `formNotice`, `formOpMode1`,
`formOpMode2`, `formQuickSetup`, `formRadvd`, `formSSH`, `formSelLang`,
`formTunnel6`, `formWizards`, `formWlSiteSurveys`

**Added (6):** `formAjaxGet`, `formAjaxSet`, `formAlgSip`, `formIPTV`,
`formUploadFile`, `formWanStatus`

Two observations worth carrying forward:

- **The entire IPv6 handler family is gone in 2020** — `formRadvd`, `formDnsv6`,
  `formDhcpv6s`, `formIPv6Addr`, `formIpv6Setup`, `formTunnel6`. Cisco Talos
  later published stack-overflow findings against `formDnsv6` and `formRadvd`
  in the rtl819x SDK (TALOS-2023-1876 and neighbours). Those handlers are
  **present in the 2015 image and absent from the 2020 one**, which makes the
  2015 build the interesting target for that bug class on this device. Whether
  removal was a security decision or a feature cut is not knowable from here.
- **`formAjaxGet` / `formAjaxSet` are new**, matching the new `libcjson.so`
  dependency W01 recorded. New parsing code on an old codebase.

## `formSysCmd` is in neither table

Not in the 59, not in the 49. Since `handleForm` matches names **exactly** and
consults no other table, `/boafrm/formSysCmd` on this firmware returns
`send_r_not_found`. See [`formSysCmd-analysis.md`](formSysCmd-analysis.md) for
what *is* there and what that means for CVE-2019-19824.
