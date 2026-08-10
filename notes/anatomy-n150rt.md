# Anatomy of the TOTOLINK N150RT firmware

Everything here was measured from the images listed in
[`firmware/MANIFEST.json`](../firmware/MANIFEST.json), not taken from a spec
sheet. Where a published spec disagrees with the measurement, both are shown.

Reproduce with:

```bash
make fetch unpack recon
```

---

## The seven questions (G1)

| # | Question | Answer | How it was established |
|---|---|---|---|
| 1 | SoC | Realtek RTL8196-class (**unconfirmed** — needs the board) | Firmware evidence is consistent with it: MIPS-I, `0x80c00000` kernel load address, Realtek `cvimg` container. The chip marking is a W02 task. |
| 2 | CPU architecture | **MIPS32, MIPS-I ISA, o32 ABI** | `e_machine=8`, `e_flags` arch bits = `mips1`, `EF_MIPS_ABI_O32` set |
| 3 | Endianness | **Big endian** | `e_ident[EI_DATA] = ELFDATA2MSB` on every ELF in both images |
| 4 | Load base / entry | Load base `0x00400000`; `/bin/boa` entry `0x00404020` (2.1.2) / `0x004034d0` (3.4.0) | lowest `PT_LOAD` vaddr and `e_entry` |
| 5 | Root filesystem | **SquashFS 4.0**, 128 KiB blocks. 2.1.2 → **LZMA**; 3.4.0 → **XZ** | SquashFS superblock parsed directly |
| 6 | Web server | **`/bin/boa`, banner `Boa/0.94.14rc21`** in both builds | version string in the binary; `DocumentRoot` from `boa.conf` |
| 7 | Configuration storage | `/lib/libapmib.so`, linked by Boa; serialised in **`COMPCS`** format; surfaced at **`/web/config.dat`** (a symlink to `/var/config.dat` in 3.4.0) | `DT_NEEDED`, string table, filesystem inspection |

### Say it out loud

> It is a big-endian MIPS-I device built on the Realtek SDK. The firmware is a
> Realtek `cvimg` container: a 16-byte `IMG_HEADER_T` per region, each carrying
> the flash offset it burns to. The root filesystem is SquashFS 4.0 — LZMA in
> the 2015 build, XZ in the 2020 one. The web server is Boa 0.94.14rc21 running
> as root, dispatching `POST /boafrm/<name>` to about fifty `form*` handlers.
> Configuration lives in the `apmib` library in a plaintext `COMPCS` structure,
> and in the 2020 build that structure is reachable from the web document root
> through a symlink into `/var`.

---

## Container format: Realtek `IMG_HEADER_T`

Each region is prefixed by a 16-byte **big-endian** header:

```c
typedef struct {
    unsigned char signature[4];   /* "cr6c", "r6cr", "w6cg"          */
    unsigned int  startAddr;      /* load address in RAM             */
    unsigned int  burnAddr;       /* destination offset in flash     */
    unsigned int  len;            /* payload length, header excluded */
} IMG_HEADER_T;
```

The layout was recovered by inspection and then *checked*: every section's
`payload_offset + len` lands exactly on the next section's signature. If the
field order were wrong, that chain would not close.

### V2.1.2 (2015-08-25)

| # | Tag | File offset | Flash offset | RAM addr | Length | Payload |
|---|---|---|---|---|---|---|
| 0 | `w6cg` | `0x00000000` | `0x010000` | `0x00010000` | 308,866 | bzip2 — **web UI resource bundle** |
| 1 | `cr6c` | `0x0004b692` | `0x060000` | `0x80500000` | 985,090 | boot stub + LZMA kernel at `+0x2808` |
| 2 | `r6cr` | `0x0013bea4` | `0x180000` | `0x002d0000` | 2,174,978 | SquashFS 4.0 / LZMA |

Trailer at `0x34eeb6`: `TOTOLINK-N150RT-V2.1.0`

### V3.4.0 (2020-10-30)

| # | Tag | File offset | Flash offset | RAM addr | Length | Payload |
|---|---|---|---|---|---|---|
| 0 | `cr6c` | `0x00000000` | `0x010000` | `0x80c00000` | 1,234,946 | boot stub + LZMA kernel at `+0x2808` |
| 1 | `r6cr` | `0x0012d812` | `0x180000` | `0x002d0000` | 2,158,594 | SquashFS 4.0 / XZ |

Trailer at `0x33c824`: `TOTOLINK-N150RT-V2.1.0`

### Reading the layout

**The flash map falls straight out of `burnAddr`:**

```
0x000000  bootloader                       (not shipped in either image)
0x010000  w6cg  web bundle   [2015 only]
0x060000  cr6c  kernel
0x180000  r6cr  root filesystem
```

**`w6cg` disappears between builds.** The 2015 image ships the web UI as a
separate bzip2 region burned at `0x010000`; decompressed it is 1,720,168 bytes
of `password.htm`, GIFs and friends in a simple name/offset archive. In 2015
`/web` is itself a symlink to `/var/web`, so the document root is populated at
runtime from that partition. By 2020 the pages live in the SquashFS and `rcS`
copies them with `cp -rf /web/* /var/web/`. Same end state, different plumbing —
and it changes where you look for a web asset in each build.

**The RAM load address moved**, `0x80500000` → `0x80c00000`. Both are KSEG0.

**Both images carry the same trailer string, `TOTOLINK-N150RT-V2.1.0`**, even
though one is labelled 2.1.2 and the other 3.4.0. It is a hardware/product
compatibility tag consumed by the upgrade path, not a firmware version. Worth
knowing before treating a version number in a CVE record as if it identified a
specific binary.

### Both builds contradict the published flash size

TechInfoDepot lists the N150RT with **2 MB** of flash. The flash map requires:

| Build | Highest `burnAddr + len` | Minimum part size |
|---|---|---|
| V2.1.2 | 3,747,842 | **3.57 MiB** |
| V3.4.0 | 3,731,458 | **3.56 MiB** |

Neither fits in 2 MB, so the part is at least 4 MB. Either the wiki entry
describes a different board revision, or it is simply wrong. **W02 resolves this
by reading the chip marking and dumping the part**; the flash offsets above are
what the dump gets compared against.

---

## SquashFS notes

Both root filesystems have a **little-endian** superblock (`hsqs`) on a
big-endian CPU. That looks like a contradiction and is not: SquashFS 4.0 defines
its on-disk format as little-endian regardless of host endianness, and the
kernel driver byte-swaps. Version 3 was the endianness-dependent one.

Both superblocks carry an **implausible `mkfs_time`** — 2038-02-22 and
2038-07-17. Byte-reversed, those raw values (`0x802d2100`, `0x80ed2000`) read as
`0x00212d80` and `0x0020ed80`, which land within a couple of hundred bytes of
each filesystem's own size. The likely explanation is a vendor build-script bug
writing a size into the timestamp field. The practical consequence: **these
images cannot be dated from their own metadata**, and the filename is the only
date available.

Extraction detail: `unsquashfs` exits non-zero as a normal user because it
cannot create device nodes or set ownership. File contents and permission bits
are intact. `tools/unpack-firmware.sh` treats "tree exists and contains
symlinks" as the success condition instead of trusting the exit code — and hard
fails if no symlinks survive, because a filesystem that cannot represent them
would invalidate the `/web/config.dat` finding.

---

## Binary landscape

| | V2.1.2 | V3.4.0 |
|---|---|---|
| Files / dirs / symlinks | 165 / 20 / 99 | 364 / 33 / 103 |
| `/bin/boa` size | 522,556 | 404,904 |
| Boa banner | `Boa/0.94.14rc21` | `Boa/0.94.14rc21` |
| Boa `DT_NEEDED` | `libapmib.so`, `libc.so.0`, `libgcc_s.so.1` | + `libcjson.so`, `libmtdapi.so` |
| `form*` handlers in Boa | 59 | 49 |
| Binaries importing `system`/`popen`/`exec*` | 33 | 17 |
| uClibc | 0.9.30.3 | 0.9.33 |
| `DocumentRoot` | `/web` (symlink → `/var/web`) | `/var/web` |
| `/etc/passwd` | symlink -> `/var/passwd` | symlink -> `/var/passwd` |
| `/etc/passwd.org` / `passwd_orig` | **present** — `root:123456`, `onlime_r:12345` (uid 0) | **present** — `root:123456` |
| setuid/setgid files | none | none |
| `/bin/skt` | **present**, autostart commented out | removed |
| `/web/config.dat` | absent | **symlink → `/var/config.dat`** |

**Boa runs as `User root` / `Group root`** in both builds. Every handler bug is
therefore a root bug; there is no privilege boundary to cross afterwards.

### Exploit mitigations: none

Across both images, no binary has a stack canary, RELRO, PIE or FORTIFY.

> ⚠️ **W04 correction.** This paragraph originally continued "Most have no
> `PT_GNU_STACK` segment at all, which means the kernel maps the stack
> executable — the toolchain predates the marker." That is backwards. Counted
> over every ELF under `bin/`, `sbin/` and `lib/`:
>
> | | ELF files | with `PT_GNU_STACK` | of those, `RWE` | without |
> |---|---|---|---|---|
> | V2.1.2 | 64 | 56 | **56** | 8 |
> | V3.4.0 | 50 | 46 | **46** | 4 |
>
> Most binaries **do** carry the marker, and every one that does is marked
> `RWE`. The conclusion — an executable stack — is unchanged and is now
> *stated* by the binaries rather than inferred from a missing header. The
> original wording would not have survived one hostile `readelf -lW`.

Practically: a stack overflow in a `form*` handler is directly exploitable with
shellcode on the stack. No ROP chain, no info leak, no ASLR defeat. That is the
context for reading the 2025 buffer-overflow CVEs against this device line.

---

## Open questions carried into W02/W03

1. **Which build is on my unit?** Neither of these, necessarily. The device
   label reads `N150RT`, S/N `18B500419`, H/W `V2.0`. The flash dump decides it.
2. **Actual flash part and size** — resolves the 2 MB contradiction.
3. ~~**Where is `formSysCmd` registered?**~~ → **W03: nowhere.** It is in
   neither dispatch table. W04 adds the likely reason: V2.1.2 post-dates the last
   build Pierre Kim reports as vulnerable to it.
   → [`formSysCmd-analysis.md`](formSysCmd-analysis.md)
4. ~~**Is `.dat` actually served without authentication?**~~ → **W03/W04: no
   authorisation runs for it, in either build**, and for a broader reason than
   `.dat`. → [`auth-flow.md`](auth-flow.md), [`auth-flow-2020.md`](auth-flow-2020.md)
5. ~~**Where is the credential check?** No `/etc/passwd`, so it is inside a
   binary~~ → **answered in W04, and the premise was false.** Both images ship
   `/etc/passwd` as a symlink into `/var`, populated at boot by `/bin/sysconf`
   from `passwd.org` / `passwd_orig`. There are **two** credential systems: the
   shell accounts in that file, and the *web* login, which compares against
   APMIB `USER_NAME`/`USER_PASSWORD`. → [`credentials.md`](credentials.md),
   [`mib-and-config-dat.md`](mib-and-config-dat.md).

   Also unnoticed in W01, in the same directory: a shipped 2048-bit RSA private
   key (`/etc/privateKey.key`, V3.4.0, certificate expired 2014) and a shipped
   dropbear host key (`/etc/dropbear_rsa_host_key`, V2.1.2).
