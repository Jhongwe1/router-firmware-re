# The shipped web UI, read across three builds

**Question carried out of W01:** the `w6cg` bundle was "decompressed but its
archive structure is only sketched"
([`attack-surface.md` §5](attack-surface.md#5-not-yet-examined)). Every
`formSysCmd` statement this project has made was measured on
the `boa` **binaries** — `grep -aoc` giving 0 / 1 / 0 for 2015 / 2018 / 2020,
and the recovered `root_form[]`. **Nobody had opened the UI that posts to it.**

**Opened now, and the two halves turn out to be anti-correlated.**

| | V2.1.2 (2015-08) | V2.1.6-B20160516 (2016) | this unit (2018-01) |
|---|---|---|---|
| `syscmd.htm` in the shipped bundle | **present**, 3,835 bytes | **present, byte-identical** (`sha256 d0b0121a…`) | **absent** |
| its form tag | `<form action=/boafrm/formSysCmd method=POST name="formSysCmd">` | the same bytes | — |
| `formSysCmd` in `boa` | **0** occurrences | *unknown — rootfs truncated* | **1** |
| in `root_form[]` | **absent** (59 entries) | *unknown* | **present**, entry `0x004838a8` |
| bundle entries | 144 | 144 | 143 |

- **2015 and 2016 ship the page and not the handler.** `handleForm` matches the
  URI tail against a NULL-terminated `root_form[]` with `strlen`-then-`memcmp`,
  no prefix rule and no second table ([`dispatch-table.md`](dispatch-table.md)),
  and `formSysCmd` is not in it — so **the form the vendor shipped posts to a
  404** ([`formSysCmd-analysis.md`](formSysCmd-analysis.md)).
- **2018 ships the handler and not the page.** The endpoint is registered and
  reachable, and nothing in the UI points at it.

That is the situation CVE-2024-51228's researcher describes in one clause —
*"even if the GUI (`syscmd.htm`) is not available"*, quoted in
[`auth-flow-2018.md` §2](auth-flow-2018.md#2-what-that-unlocks-and-why-it-is-worse-than-the-advisory-says).
The clause reads as a throwaway. It is the whole shape of the change, and there
is now a measured before/after under it.

**The vendor's response to CVE-2015-9551 was half a fix, and it stayed half for
at least eighteen months.** Removing the route while leaving the page that calls
it is the same signature this repository has already recorded twice: `#skt&`
commented out in `rcS` while `/bin/skt` still shipped executable
([`skt-analysis.md`](skt-analysis.md)), and `onlime_r` left at uid 0 in
`/etc/passwd.org` ([`credentials.md`](credentials.md)). **Three defects from one
disclosure, three partial removals.**

---

## 1. The format, and why the parse is trustworthy

`w6cg` holds one bzip2 stream. Decompressed it is a flat archive — no index, no
entry count, no terminator:

```
offset  size  meaning
+0x00     ~   file name, NUL-terminated (path separators included)
+0x3c     4   content length, BIG-endian
+0x40   len   content
```

The remaining header fields are a duplicated pair of 32-bit timestamps and two
equal size-like values, all **little**-endian. The length at `+0x3c` is the only
big-endian field in the header, which is exactly the kind of detail that makes a
guessed layout fail loudly.

**There is no checksum and no entry count to verify against, so the check had to
come from the structure itself.** Every stride is `64 + length`, so a walk either
lands on the final byte or it does not, and a wrong length offset derails within
one or two entries and cannot recover. `fwrecon web` reports `self_check:
exact` only when zero bytes remain:

```
firmware/TOTOLINK-N150RT-V2.1.2-B20150825.1601.web  144 entries, self_check: exact
firmware/v2.1.6-partial.web                         144 entries, self_check: exact
dumps/flash-n150rt-console-1.bin                    143 entries, self_check: exact
```

1,720,168 / 1,704,011 / 1,417,000 bytes consumed, nothing left over, three
times. The test suite pins this down from the other side: moving
`LENGTH_OFFSET` to `0x38` — a plausible wrong guess — turns `exact` into
`derailed` ([`test_webbundle.py`](../tools/fwrecon/tests/test_webbundle.py)).

**Second source for the count.** [`auth-flow-2018.md`](auth-flow-2018.md) already
reported "the `w6cg` archive parses to 143 entries with zero trailing bytes",
obtained by hand during W04-2. This parser was written without reference to that
figure and reproduces it, on the same image, from the same file. Two
independent walks of an undocumented format agreeing on 143 is worth more than
either alone.

## 2. What was measured

```bash
python -m fwrecon web <image> --grep formSysCmd
python -m fwrecon web dumps/flash-n150rt-console-1.bin --at 0x010000 --grep formSysCmd
```

```
2015  syscmd.htm   3,835 bytes  11 hit(s)
2016  syscmd.htm   3,835 bytes  11 hit(s)
2018  no entry contains it
```

`--grep` searches each entry's *content*, not the decompressed blob, and §4
explains why that distinction is not pedantry.

The full entry lists are committed, so a reader without the firmware can check
the presence and absence directly rather than taking the three lines above on
trust — [`webbundle-2.1.2.json`](../reports/webbundle-2.1.2.json),
[`webbundle-2.1.6-b20160516.json`](../reports/webbundle-2.1.6-b20160516.json),
[`webbundle-unit-2018.json`](../reports/webbundle-unit-2018.json). Each names its
input by SHA-256, and `tools/check-reports.py` refuses to accept one whose
`self_check` is not `exact` — a derailed walk still produces a plausible entry
list, which is exactly why it must not be committed as evidence.

The 2015 and 2016 copies of `syscmd.htm` are **byte-identical** — same length,
same SHA-256. Eighteen months apart, the vendor changed neither the page nor its
form action.

## 3. What this does not say

- **It says nothing about the 2016 `boa`.** That image is a 40% download and the
  truncated section is the rootfs
  ([`dump-vs-official.md` §2.1](dump-vs-official.md)). Whether B20160516's
  dispatch table carries `formSysCmd` is still open, and still needs the other
  60%. The row is marked *unknown* above rather than inferred from 2015.
- **The 2018 removal was not surgical.** Between 2015 and 2018 the bundle loses
  27 entries, gains 26, and 60 of the 117 shared names change content.
  `syscmd.htm` is one removal inside a broad UI rework, and reading it as a
  targeted deletion would be reading intent into a rebuild.
- **Nothing here is dynamic.** No request has been sent to the device. The
  claim "the shipped form posts to a 404" is a statement about a recovered
  dispatch array, not about an observed response, and it stays that way until
  G4.

**And one fossil, because it is the same shape as the others.** The 2018 bundle
no longer has the page, but `language_vn.js`, `language_sc.js` and
`language_sp.js` still carry a `/**** syscmd.htm ****/` banner and its
translated strings. The vendor shipped translations for a page it had removed —
alongside a `#skt&` line left in `rcS` for a binary it had deleted.

## 4. How the first version of this note was wrong

**It nearly contradicted a correct committed claim, on the strength of a
substring.** The first pass searched the *decompressed blob* for `syscmd.htm`
and found it in all three builds, including 2018 — which appeared to refute
`auth-flow-2018.md`'s "the `w6cg` archive parses to 143 entries and `syscmd.htm`
is not one of them". It was about to be written up as a conflict.

It was not a conflict. The 2018 hits are inside `language_*.js`, in a comment
banner naming the page. **A name in a file is not a file**, and the difference
is invisible to a search over a flat blob and obvious to one over parsed
entries. `fwrecon web --grep` searches entries for exactly this reason, and the
test suite asserts that a banner is attributed to the file that contains it and
not to the file it names.

**The lesson is not "grep carefully".** It is that the committed claim was
right, and the instinct on finding a contradiction was to trust the newer
measurement — the one that had not been parsed, checked, or reproduced. The
older claim had a stated method ("parses to 143 entries with zero trailing
bytes") and the newer one had a substring count.

**Second: the header layout was guessed before it was read.** The first attempt
at walking the archive re-derived the container's section header as
`tag / burnAddr / length / startAddr` and got 65,536 for a 296,804-byte section
— the field order is `tag / startAddr / burnAddr / length`, and it was already
written down in [`rtlimage.py`](../tools/fwrecon/src/fwrecon/rtlimage.py). Ten
seconds of reading the project's own parser would have replaced fifteen minutes
of hex. **The repository had the answer; the guess did not consult it.**
