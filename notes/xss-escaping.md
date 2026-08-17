# The escaper exists, it is correct, and only Boa's own pages call it

**The answer.** `/bin/boa` on this unit contains a proper HTML escaper —
`req_write_escape_html`, with an entity table covering `"`, `'`, `\`, `<` and
`>` (`&quot;`, `&#39;`, `&#92;`, `&#60;`, `&#62;`). It has **exactly six
callers**, and every one of them is an upstream Boa 0.94 status page:

| caller | what it is |
|---|---|
| `send_r_forbidden` `0x0040e438` | 403 |
| `send_r_not_found` `0x0040e320` | 404 |
| `send_r_moved_temp` `0x0040e634` | 302 |
| `send_r_moved_perm` `0x0040eac4` | 301 |
| `FUN_0040ee98` `0x0040ee98` | 411 |
| `send_redirect_perm` `0x0040e7e4` | Realtek's own 302 — and the only Realtek-side caller |

**Not one of the ASP list functions that render device data calls it.** The
docroot uses about thirty of them, and `boa` carries **105 table-markup format
strings**, every data-bearing one a raw `%s`:

```
<td>%s</td>
<tr align=center><td>%s</td><td>%s</td><td>%s</td></tr>
<td><input type="hidden" id="clonemac%d" value="%s" >%s</td>
<tr align=center><td>%s</td><td>%s</td><td><input name=selected onclick=selectFromPopup("%s","%s") type=radio></td></tr>
```

The third and fourth are worse than the first two: the `%s` is **inside an HTML
attribute value**, where a single `"` ends the attribute without needing `<`.

This is the answer to CVE-2025-3994, 3995, 3996, 4460 and 4461 — and it is much
broader than those five. **They are five instances of one omission.**

---

## 1. Why the templates were the wrong place to look

W07's plan says to read the five advisories' injection points, follow each to its
MIB field, and then grep the templates for pages that output it. The first two
steps hold. The third does not, and one file shows why:

```html
<!-- dhcptbl.htm -->
<table border="1">
<% dhcpClientList(); %>
</table>
```

The template contains no field at all. It calls a C function inside `boa`, and
that function writes the whole table. **So escaping is not a property of the
docroot; it is a property of `boa`, and grepping 146 template files for the
value would have found nothing and proved nothing.**

The complete set of ASP calls the docroot makes, by frequency:

```
getIndex 1371   getInfo 529   getVirtualInfo 200   getVirtualIndex 181
getIPv6Info 85  getIPv6WanInfo 57   getIPv6BasicInfo 18   wlSchList 10
getIPv6Status 8   wirelessClientList 5   dhcpCloneMacList 3
wlSiteSurveyTbl 2  ipFiltersList 2  getVlanList 2  getScheduleInfo 2
getModeCombobox 2  dhcpClientList 2
… and one call each: wlWdsList, wlProfileTblList, wlProfileList, wlAcList,
wirelessClientListFW, wdsList, urlFilterList, sysLogList, staticRouteList,
portFwList, portFilterList, macFilterList, l7QosList, kernelRouteList,
ipQosList, ipFilterList, getDHCPModeCombobox, dhcpRsvdIp_List,
dhcpClientListFW, arpTableListFW, arpTableList
```

Every one of those that renders a value an outsider can influence is a candidate
for the same class:

| function | the value that is not the device's own |
|---|---|
| `dhcpClientList`, `dhcpClientListFW` | the **DHCP hostname** a client asks for — CVE-2025-3995, register `P8-1` |
| `dhcpRsvdIp_List` | static-DHCP entries, which is what `formStaticDHCP` writes |
| `wirelessClientList`, `wirelessClientListFW` | wireless client names |
| `wlSiteSurveyTbl` | **SSIDs seen over the air** — a beacon field, register `P7-3`, W08 |
| `portFwList`, `portFilterList`, `macFilterList`, `urlFilterList`, `ipFilterList`, `ipFiltersList` | the filter and virtual-server description fields the other four CVEs name |
| `sysLogList` | log lines, which carry request-derived text |
| `arpTableList`, `arpTableListFW` | ARP entries |

## 2. What this does and does not establish

**Established, statically:** the escaper exists, six functions call it, and none
of them is a Realtek list renderer; the list renderers write raw `%s` into
markup, including into attribute values.

**Not established:**

- **That any particular value survives the trip.** A hostname with `<` in it has
  to be accepted by `udhcpd`, stored in the lease table, and read back by
  `dhcpClientList` before the missing escape matters. Filtering at the *write*
  side would close an injection point just as effectively as escaping at the read
  side, and nothing here has looked at the write side. Register `P8-2` says this
  in its refutation and it is the reason that case stays open.
- **Which of the five advisories maps to which function.** The advisories name
  page fields; this note names render functions. Joining them takes reading each
  handler's writer, and it changes nothing about the class.
- **Anything on the device.** This is a reading of one binary.

> **What would confirm it.** For `P8-1`: request a lease with markup in the
> hostname from the isolated segment, then fetch the client-list page and look at
> the bytes. Two commands, no power cycle, no configuration change. It is on the
> bench list.

## 3. Why this is the same shape as W03's finding, and worth saying so

W03 read CVE-2019-19822's advisory — *"`.dat` files are not restricted"* — and
found the cause was broader: the gate keys on the substring `htm`, so
**everything** without `htm` in its path is exempt, not just `.dat`.

The same thing has happened here. Five advisories name five fields. The cause is
that a correct escaper shipped in the same binary and the vendor's own code never
calls it, so the exposure is every list the vendor renders — roughly thirty
functions — and the five named fields are a sample of it.

**That is the difference between reading an advisory and reading the binary**,
and it is the second time in this project that the difference has been a factor
of six or more.

## 4. How the first version of this was wrong

**It went looking in the templates, because the plan said to.** W07's Day 4
timebox is written around grepping three docroot corpora for the MIB field a
parameter lands in, and the note's first outline followed it. That approach
cannot work on this codebase and the reason is visible in the first template
opened: the value never appears in the file.

The plan is not wrong about the *method* — parameter → MIB field → output site is
exactly right, and it is what turned five CVEs into one class. It is wrong about
where the output site lives, and it says so with confidence: *"哪些樣板**輸出**
那個欄位（`grep` 三個語料）"*. There is nothing to grep. Two of the three corpora
would have returned nothing and the third would have returned the ASP call, which
is a pointer and not an answer.
