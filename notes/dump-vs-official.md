# The dump against the vendor images

Answers G2's third checkbox — *dump vs vendor image compared* — and the question
W01 opened and could not close: **which build is on my unit.**

**It is neither of them.** A 4 MiB image read out of the device on 2026-08-16
carries a `/bin/boa` built **2018-01-10 14:57:54**, 485,012 bytes,
`sha256 19fe29d7…`. V2.1.2's is 522,556 bytes and V3.4.0's is 404,904. This
binary has never appeared in this repository, and it is not on any vendor
download page.

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

> ⚠️ **`0x006000`–`0x010000` is never published.** It holds this unit's MAC
> addresses, radio calibration and live configuration. `fwrecon flashdump`
> reports those regions by SHA-256 and refuses to print their contents; there is
> a test that fails if a byte of them reaches the output. Same rule as the
> photographs and the boot log — see [`img/README.md`](img/README.md).

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
