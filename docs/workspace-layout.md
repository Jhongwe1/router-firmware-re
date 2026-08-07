# Workspace layout

Two roots, on purpose.

```
repo   C:\Users\Key20\Desktop\router          text only: notes, tooling, reports
work   ~/fwre-work        (inside WSL, ext4)  binaries: images, unpacked trees
```

`$FWRE_WORK` defaults to `~/fwre-work` and can be overridden.

```
$FWRE_WORK/
  firmware/    downloaded vendor images (hash-verified, never committed)
  extracted/
    v2.1.2/    rootfs.squashfs, squashfs-root/, extract.log
    v3.4.0/
  venv/        analysis virtualenv
```

## Why the artefacts are not in the repo directory

The repository lives on the Windows filesystem, which WSL exposes through DrvFs
at `/mnt/c`. DrvFs does not, by default, carry Linux metadata — symbolic links,
permission bits and setuid flags do not survive a write.

For most projects that is a performance annoyance. Here it would be a
correctness failure, because the findings *are* metadata:

- **`/web/config.dat` is a symlink** to `/var/config.dat`. Extract onto a
  filesystem that cannot represent symlinks and the file either vanishes or
  turns into a plain file. The single highest-severity observation in the
  report disappears — silently, with no error.
- **"No setuid binaries in either image"** is only a statement about the
  firmware if setuid bits survived extraction. On DrvFs it is a statement about
  the filesystem.

So `tools/unpack-firmware.sh` refuses to run when `$FWRE_WORK` is under `/mnt/`,
and after extraction it fails hard if the tree contains no symlinks at all —
a cheap end-to-end check that the target filesystem can represent what was
extracted.

Extraction speed is a real secondary benefit (ext4 is several times faster for
the tens of thousands of small writes involved), but it is not the reason.

## Reaching the artefacts from Windows

Ghidra runs natively on Windows and opens the extracted binaries over the WSL
share:

```
\\wsl$\Ubuntu-24.04\home\<user>\fwre-work\extracted\v2.1.2\squashfs-root\bin\boa
```

One copy of the data, two views of it. Nothing is duplicated across the
boundary, so the Windows and Linux sides cannot drift apart.

## What is committed and what is not

| | Committed | Why |
|---|---|---|
| `notes/`, `docs/`, `tools/` | yes | the work |
| `reports/*.json`, `reports/*.md` | yes | the readable product; a reader without the firmware can still see the findings |
| `firmware/SOURCES.json` | yes | where to obtain each image and what it must hash to |
| `firmware/MANIFEST.json` | yes | what was actually obtained, and when |
| `firmware/*.web` | **no** | vendor firmware is not ours to redistribute |
| `extracted/**` | **no** | large, and reconstructible from the manifest plus the tooling |
| Ghidra project state | **no** | multi-gigabyte and machine-specific; the headless script is committed instead |
