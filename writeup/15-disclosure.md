# Disclosure · References · Thanks

## Disclosure

This device is **end of life and no longer vendor-supported**. Every defect this
document *locates* is already public; what is new here is the location, the
build it applies to, and — in one case — a disagreement with a published score.

The register is [`docs/disclosure.md`](../docs/disclosure.md), and it carries a
per-item state rather than a blanket policy. Three rules decide what appears
here:

1. **Findings are published.** Naming a defect and its address is research.
2. **Reproductions follow the disclosure state of the item.** A copy-pasteable
   request for something already fully disclosed is a reproduction; the same
   request for something unreported is not, and does not appear.
3. **Tradecraft is not published at all**, in either case.

One item in the register has had **no prior-art search**. It is therefore not
reportable, has not been reported, and is not in this document as a finding.

**CVE-2024-51228** is the one place this project has something to say back to the
public record. NVD scores it `PR:H` — privileges required, high — for 6.8
MEDIUM. The original researcher writes "without credentials". The
instruction-level read agrees with the researcher: `/boafrm/formSysCmd` contains
neither `.htm` nor `.asp`, so the authorisation gate does not run on it. If the
researcher is right, the vector is `PR:N` and the score is 8.8 HIGH. That is a
narrow, checkable claim and it is the only one made here.

## References

**Prior art**, with what each contributed, is
[`notes/prior-art.md`](../notes/prior-art.md).

* **Pierre Kim** — the 2015 disclosure of the uid 0 account (CVE-2015-9550) and
  `/bin/skt` (CVE-2015-9551). Chapter 5 is a five-year answer to a question he
  asked, and this project would not have known which line of `rcS` to look at
  without it. An early version of this work misattributed the 2019 CVEs to him;
  that correction is in the record.
* **Błażej Adamczyk** (sploit.tech, December 2019) — the Realtek SDK disclosure
  behind CVE-2019-19822/23/24/25, which is what makes 2015-versus-2020 a
  before-and-after rather than a comparison.
* the researcher behind **CVE-2024-51228**, whose report names this exact build
  string — the only public document that does.
* **OpenWrt's wiki** and the Realtek `rtl819x` bootcode published under the GPL
  by other vendors, which named the boot loader's recovery flow and its
  `nfjrom` / `boot.img` filenames. Chapter 13's last paragraph is not a
  discovery, and saying so is the point.
* **flashrom**, **binwalk**, **unblob**, **sasquatch**, **Ghidra**, **QEMU** —
  and one of them, flashrom, is also the subject of two entries in chapter 12,
  which is not a complaint about it.

## Thanks

To the vendors who publish their GPL boot code, because a second source for a
constant is worth more than a clever inference about it.

To whoever wrote the Coverity annotation still sitting in Realtek's `monitor.c`
next to a `memset(argv[0], 0, sizeof(argv[0]))` — a `sizeof` on a pointer,
flagged, and still in the shipped binary eight years later. It is the single
clearest illustration in this whole document of the difference between a check
that runs and a check that is heeded.

## Reproducing this

[`REPRODUCE.md`](../REPRODUCE.md) — three tiers, and **what each tier cannot
verify**, on page one.

```bash
make doctor    # is this machine ready? every failure names the command that fixes it
make ci        # 592 checks - 462 of them exist to prove the tools can refuse
```

If you have five minutes and no hardware:

```bash
bash tools/test-loader-unpack.sh
```

Thirty-four cases, no device and no downloads. It builds deliberately broken
synthetic boot-loader images and requires the unpacker to refuse each **for the
right reason**, then unpacks a good one as the positive control — because a tool
that always refuses and a tool that refuses correctly are indistinguishable in a
suite made only of refusals.
