# The dump against the vendor images

Answers G2's third checkbox — *dump vs vendor image compared* — and the question
W01 opened and could not close: **which build is on my unit.**

**It is neither of them, and it has a name:
`TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002`** — 41 bytes, `cat`, from
`/etc/version` in the rootfs carved out of this unit's own flash. A second file
in the same tree agrees without sharing a failure mode: `/bin/boa` carries the
compiled-in string `Model No. N150RT (Firmware V2.1.6)`, and a text file can be
edited where a string linked into an executable cannot.

That image, read out of the device on 2026-08-16, carries a `/bin/boa` built
**2018-01-10 14:57:54**, 485,012 bytes, `sha256 19fe29d7…`. V2.1.2's is 522,556
bytes and V3.4.0's is 404,904. This binary has never appeared in this
repository.

**Two identifiers, seven weeks apart, and the difference is not cosmetic.** The
vendor's own label says `B20171121` (2017-11-21); every binary in the tree is
stamped 2018-01-10. This repository labels the build `unit-2018`, i.e. after the
timestamp — **and the timestamp is the identifier nobody can search.** The
version string is the one that turns up CVE-2024-51228, which names this exact
build and which this project read past for two weeks
([`prior-art.md`](prior-art.md)). Why the label precedes the binaries by seven
weeks is `PROGRESS.md` open #4, and it is unanswered.

**Is it on a download page?** The *version* is; **this build is not.** The
published V2.1.6 is `TOTOLINK-N150RT-V2.1.6-B20160516.1233.web` — same product
version, a build eighteen months earlier, and without the `CX`. W02's original
"the resident build is on no download page" survives with that precision, and
the measurement behind it is §2.1 below.

The comparison that follows is only possible because of that middle point:

| | V2.1.2 (2015-08-25) | **this unit (2018-01-10)** | V3.4.0 (2020-10-30) |
|---|---|---|---|
| `/bin/skt` — the socket-driven `system()` backdoor | **shipped, executable** | **deleted** | absent |
| `#skt&` in `/etc/init.d/rcS` | commented out | **still there, line 110** | removed |
| `onlime_r`, uid 0 | **present** | **present** | **removed** |
| password template | `/etc/passwd.org` | `/etc/passwd.org` — **byte-identical**, `sha256 e769c562…` | `/etc/passwd_orig` (renamed) |
| `root` hash `zhxPr1e7Npazg` | present | present | **present** |
| `ftpshare` / `sambashare` accounts | present | present | removed |

**The vendor's response to Pierre Kim's July 2015 disclosure took three steps
across five years, and the middle one is only visible from this device:**

1. **2015-08**, five weeks after disclosure — comment out one line in `rcS`.
   The binary still ships and is still executable; the account is untouched.
2. **by 2018-01** — **delete `/bin/skt`.** The account is *still* untouched, and
   the dead `#skt&` line is left in the startup script as a fossil.
3. **by 2020-10** — remove `onlime_r`, remove the dead line, rename the template.

CVE-2015-9550 (the backdoor account) and CVE-2015-9551 (the `formSysCmd` RCE)
were disclosed together. **Two and a half years later the vendor had fixed one
of them.** `root:zhxPr1e7Npazg` — which W04 established is `123456` — is
byte-identical in all three.

---

## 1. What was read, and how far it can be trusted

| | |
|---|---|
| file | `flash-n150rt-console-1.bin`, 4,194,304 bytes |
| `sha256` | `a800059a9b8c414df026a22b8423a5939d0f9bb793109d0f7ce086f6810f37ea` |
| method | boot loader `FLR` + `DB` over the 38400 console — **no clip, no programmer, no risk to the board** |
| tool | [`tools/console-dump.py`](../tools/console-dump.py), 256 chunks of 16 KiB, 105 minutes |
| retries | **0** — not one chunk had to be re-read |

The programmer was measured and **not** used: the CH341A on this desk is an
un-modded 5 V board (`CS#`/`CLK`/`DI` at 5 V into a 3.3 V part, and `DO` — the
flash's own output — held 1.7 V above its supply). A 3.3 V mod was attempted and
did not take; the cause was not isolated. See `PROGRESS.md` § Day 4.

Four things stand behind the image, and none of them is "the tool said it
worked":

1. **A positive control with a known answer.** Flash `0x000000` was read first
   and its first four bytes had to be `0b f0 00 04` — recorded by an unrelated
   console session on 2026-08-15.
2. **Per-chunk structural validation.** Every `DB` transcript had to have
   continuous addresses at a 16-byte stride, exactly 16 bytes per line, and the
   requested total. A chunk that failed was re-read; **had any chunk failed
   repeatedly, no output file would have been written at all.**
3. **A sampled second pass.** 12 of the 256 chunks were re-read over the wire
   after the fact and compared. All 12 identical. This is the layer that can see
   a corrupted byte inside a well-formed line, which no parser can.
4. **Structure, checked against expectations written down before the image
   existed** — `fwrecon flashdump`, 21 hard checks, all passed:
   W01's burn addresses derived from the vendor containers three weeks before
   the hardware arrived, and every offset the 2026-08-15 console session read.

**And the strongest one is not in that list: the SquashFS at `0x180000`
decompresses.** 1.8 MiB of LZMA does not decompress by accident from a corrupted
read. 161 files, 20 directories, 88 symlinks came out.

### What is still missing, and it is not a formality

**A second, independent instrument has not read this chip.** The 2026-08-15
windows used the same `FLR`+`DB` path, so agreeing with them is *cross-session
repeatability*, not corroboration by a different route. A second full read was
taken to satisfy G2's literal wording — two reads, hashes compared — but it runs
through the same boot loader, so it tests the transport and the SPI read, **not
whether `FLR` itself is systematically wrong.** Only the programmer answers that,
and the column stays empty until it does.

## 2. Structure: this is a late 2015-family image, not an early 2020 one

Read off the device and checked against both vendor containers:

| | V2.1.2 | **this unit** | V3.4.0 |
|---|---|---|---|
| `w6cg` @ `0x010000` | 308,866 | **277,012** | absent |
| `cr6c` | `0x060000`, 985,090 | **`0x060000`, 987,138** | `0x010000`, 1,234,946 |
| rootfs @ `0x180000` | 2,174,978 | **1,876,033** | 2,158,594 |
| compression | LZMA | **LZMA** | XZ |
| inodes | 582 | **567** | 827 |
| image ends at | 3.574 MiB | **3.29 MiB** | 3.559 MiB |

It has a web-resource section and its kernel is at `0x060000` — the 2015
arrangement, which the 2020 build dropped. Every figure differs from both.

**Two gaps that `flash-layout.md` recorded as "assumed to be padding, not read"
are now measured**: `0x053A24`–`0x05FFFF` (50,652 bytes) and
`0x151012`–`0x17FFFF` (192,494 bytes) each hold a single repeated value. The
assumption was right, and it is no longer an assumption.

The tail is erased from `0x350000` to the end of the part — **the whole tail,
not the two 64-byte windows W02 Day 2–3 could reach.**

## 2.1 A fourth image: the published V2.1.6, obtained 40% complete

Softpedia serves the V2.1.6 the unit's version string names, but not the unit's
build. Every scripted fetch gets 403 (PowerShell `HEAD`, `curl` under three
user-agents, `WebFetch`); a browser session succeeds, and the one obtained on
2026-08-16 stopped at **1,390,332 of a declared 3,447,222 compressed bytes**.
There is no central directory, so `unzip` rejects the file outright — which
reads as *corrupt* and means *truncated*, two different things. Deflate is a
stream, so the prefix still decompresses:
[`tools/zipprefix.py`](../tools/zipprefix.py), procedure in
[`RUNBOOK.md` §8.8.4](../RUNBOOK.md).

**What the prefix actually contains is more than "section lengths".** Two of the
three sections are byte-complete; only the rootfs is cut:

| section | declared | present | |
|---|---|---|---|
| `w6cg` (web UI, bzip2) | 296,804 | 296,804 | **complete** |
| `cr6c` (kernel) | 986,114 | 986,114 | **complete** — inner LZMA decompresses to 3,374,608 bytes, `eof=True` |
| `r6cr` (rootfs) | — | — | truncated: no `/etc/version`, no `boa` |

So the four-way section comparison can be made, and the rootfs one cannot:

| | V2.1.2 (2015-08) | **V2.1.6-B20160516** | this unit (2018-01) | V3.4.0 (2020-10) |
|---|---|---|---|---|
| `w6cg` | 308,866 | **296,804** | 277,012 | absent |
| `cr6c` | 985,090 | **986,114** | 987,138 | 1,234,946 |

### The continuity argument, and why its first form was wrong

The reason to line those numbers up is the question a mirror always raises:
*how do you know the file was not tampered with?* The first version of this
argument said the kernel lengths run 985,090 → 986,114 → 987,138, **exactly
1,024 bytes apart at each step**, and that a tampered file would not land on
that line. **That is not evidence, and adding the fourth build shows why:**

```
2.1.2 (2015-08)    985090 =  962*1024 + 2
2.1.6-B20160516    986114 =  963*1024 + 2
unit-2018          987138 =  964*1024 + 2
3.4.0 (2020-10)   1234946 = 1206*1024 + 2
```

All four are ≡ 2 (mod 1024). The section is padded to a 1 KiB grid, so "1,024
apart" is three consecutive grid points, not a coincidence — and **between the
2015 and 2018 values there is exactly one grid point**, so any correctly built
kernel of roughly that size lands on 986,114 by construction. A tampered one
would too. The regularity that made the argument persuasive is the thing that
empties it.

`w6cg` is not on a grid (remainders 642 / 868 / 532) and does fall between its
neighbours, which is real but weak: an ordering test across a ~32 KiB window.

### What does carry weight

| source | value | why it is not the same source as the filename |
|---|---|---|
| ZIP local file header, DOS timestamp | `2016-05-16 12:34:30` | the filename's `B20160516` is text a mirror can type; this is a separate binary field the packer writes |
| inside the compressed kernel | `Linux version 2.6.30.9 (acer1@localhost.localdomain) … #1338 Thu May 12 21:05` | renaming a file cannot reach it; 2016-05-12 was a Thursday, four days before packaging |
| the same kernel's cmdline | `console=ttyS0,38400 root=/dev/mtdblock1` | agrees with the 26 µs bit time measured on **this hardware** in W02 |

**The ceiling is unchanged and it is low.** TOTOLINK publishes no signature, so
none of this shows the bytes came from the vendor — it raises the cost of a
forgery from renaming a file to rebuilding a kernel, and no further.
[`firmware/SOURCES.json`](../firmware/SOURCES.json) states that limit and
records the download's provenance from the file's own `Zone.Identifier` stream,
which the operating system wrote at fetch time.

## 3. What this costs the W03/W04 findings

Nothing, and the repository has always named its images — but it has to be said
in one place: **every claim this project makes about `boa` describes V2.1.2 or
V3.4.0.** The `strstr(uri, "htm")` gate, the 59-entry `root_form[]`,
`lastUrl[100]`, the `submit-url` idiom, the 2020 rewrite's three unanchored
`strstr` calls — all of them are statements about two binaries **this device has
never run**.

`19fe29d7…` is a third binary. Whether it carries the same defects is now a
question that can be answered rather than assumed, and W05/W06 against this
hardware will be testing it, not them.

## 4. Not done here

- **Decoding `COMPCS`.** It is at flash `0x00C000` with its factory twin at
  `0x008000`, and both are now in hand. Reading it is W04/W07 work.
- **The 2018 `boa` in Ghidra.** Extracted and hashed; the three-way read is W03
  work redone against the binary that matters.
- **`TELNET_ENABLED` / `SSH_ENABLED` defaults.** They live in the `COMPDS` block,
  so they are blocked on the same decode. That question decides what
  `root` / `123456` is actually worth on this unit.

> 📌 **Superseded 2026-08-16 (W04-2).** This note previously read
> "`0x006000`–`0x010000` is never published". The policy is now decided **per
> field**, and for this unit those fields are published — it is self-purchased,
> end-of-life, never deployed, and a MAC is an identifier rather than a
> credential. The decoded configuration is in
> [`compcs-decode.md`](compcs-decode.md) and
> [`reports/compcs-unit-2018.json`](../reports/compcs-unit-2018.json).
>
> The *mechanism* is unchanged, because what changed was a policy and not a
> capability: `fwrecon flashdump` still reports those regions by digest, and
> `fwrecon compcs --disclosure protect` still withholds per-unit identifiers,
> each with a test that fails if a byte escapes. The next device may not be mine.
>
> **The raw image is still not committed**, for the one reason that did not
> expire: this project does not redistribute vendor firmware. See
> [`dumps/README.md`](../dumps/README.md).

---

## How the first version of this note was wrong

**It repeated W01's exact mistake, in a repository that already carries the
correction for it.**

The first pass compared `/etc/passwd.org` across the three trees. It came back:

```
2015  present
2018  present, byte-identical
2020  cat: .../etc/passwd.org: No such file or directory
```

The obvious reading — and the one nearly written — is *"the 2020 build removed
the password template"*. It did not. **It renamed it to `passwd_orig`**, and the
file is still there with `root:zhxPr1e7Npazg` in it.

That is the same error W01 made when it concluded **"there is no `/etc/passwd`
in either image"** — a dangling symlink read as an absent file — which W04
overturned. Two years of project time apart, the same shape: *one path tested,
absence concluded.*

What caught it was not care. It was **searching for the string `onlime_r` across
the whole tree instead of testing a filename.** The account is the thing being
asked about; the file it lives in is an implementation detail, and an
implementation detail is exactly what a vendor changes between builds.

There is a second, sharper version of the same trap in this note's subject
matter. `/bin/skt` is absent from the 2018 build. Stopping there gives *"the 2018
build fixed the 2015 backdoor"* — **and it is wrong, because there are two
backdoors from that one disclosure.** CVE-2015-9551 is the RCE binary and
CVE-2015-9550 is the account; the 2018 build fixed the first and left the second
untouched, byte for byte. **Finding one of a pair repaired says nothing about the
other, and the pleasure of finding a fix is precisely when you stop looking.**

**Third: this note answered "which build is on my unit" without ever writing
down what the vendor calls it.** It identified the build by a timestamp
(2018-01-10) and a hash, both correct, and the version string sat unread in
`/etc/version` in the same tree. That is not a cosmetic omission — a timestamp
cannot be searched and a build string can. The version string is what returns
CVE-2024-51228, disclosed 2024-11-27 against this exact build, and this project
read past it for two weeks. **The identifier you record determines the
literature you find**, and the note picked the one that finds nothing.

**Fourth, and it is the same error in a different costume: §2.1's first
continuity argument treated a quantisation grid as a coincidence.** Three kernel
lengths 1,024 bytes apart looked like a fingerprint; a fourth build showed all
of them sitting on a 1 KiB boundary, which makes the spacing a property of the
format rather than of these files. Three points looked like a trend and four
points showed a grid. The general form is worth keeping: *before calling a
pattern improbable, check whether it is simply what the format always does.*
Every previous instance of this failure in this repository was an instrument
lying; this one was an argument, and no instrument was going to catch it.
