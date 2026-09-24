# Disclosure · References · Thanks

## Disclosure

This unit is **end of life and no longer vendor-supported**. Almost every defect
this document *locates* is already public; what is new is the location, the build
it applies to, and — in one case — a disagreement with a published score. Two
items are not public, and they are named as such below.

**Nothing here was reported to anyone, and everything is published, including
the reproductions.** That was decided on 2026-08-23, and it replaced a policy —
stated in `README.md` until that date — of reporting anything new to TWCERT/CC
first. The register is [`docs/disclosure.md`](../docs/disclosure.md); its
§"The decision of 2026-08-23" carries the argument **and the four things the
argument does not cover**, which is the half worth reading.

The one-line version, and it is checkable rather than rhetorical: on these builds
an unauthenticated attacker on the LAN already has **root** — CVE-2024-51228,
whose public proof of concept names this exact build string — and already has the
**plaintext administrator credentials** from one `GET /config.dat`,
CVE-2019-19822 and CVE-2019-19823, unfixed in a build dated nine months after
full disclosure. Every reproduction published here is reachable from either. It
adds mechanism, not capability.

Two rules decide what appears, down from three:

1. **Findings are published.** Naming a defect and its address is research.
2. **Tradecraft is not published at all** — no persistence, no anti-forensics, no
   lateral movement, no credential harvesting on a live host. That line did not
   move on 2026-08-23 and is the one rule this project has never argued with.

The rule that went was *"reproductions follow the disclosure state of the item"*.
It ran the project for six days, it cost `poc/04` its content for that whole
period, and it was dropped on an argument rather than forgotten.

**Two of this project's own claims were retired by prior art found after they
were written up** — `D-1` by Cisco Talos in 2023, and the unauthenticated
password change by **CVE-2018-13315** in 2018, which a one-query by-handler
search would have refused at any point in the preceding six days. Both are in
[`prior-art.md`](../notes/prior-art.md) with the query that should have run.

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
make ci        # 638 checks - 462 of them exist to prove the tools can refuse
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
