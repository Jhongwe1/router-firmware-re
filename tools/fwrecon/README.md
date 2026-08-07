# fwrecon

Structured reconnaissance for Realtek-SDK router firmware. Built for the
TOTOLINK N150RT teardown; nothing in it is model-specific.

```bash
fwrecon image  fw.web                          # parse the Realtek container
fwrecon elf    squashfs-root/bin/boa           # one binary: arch, imports, hardening
fwrecon rootfs squashfs-root --label v3.4.0    # attack-surface inventory
fwrecon report --image fw.web --rootfs squashfs-root -f json -o out.json
fwrecon diff   old.json new.json -f md         # what changed between builds
```

## Design choices worth knowing about

**No runtime dependencies.** ELF and the Realtek container are parsed in
process. A report produced today can be reproduced years from now from a bare
Python install, without hoping that `apt install binwalk` still yields the same
binary.

**ELF is read the way the loader reads it** — program headers and `PT_DYNAMIC`
only, never the section header table. This is not purism. The 2020 N150RT ships
a `/bin/boa` processed with `sstrip` (`e_shnum == 0`), and against it:

```
$ readelf --dyn-syms bin/boa     # prints nothing, exits 0
$ nm -D bin/boa | grep system    # U system
```

A tool that returns an empty list where it cannot answer will have its caller
record "no dangerous imports" and move on. That happened during this project's
first pass, and it is why this module exists. Section headers are used when
present, never depended on.

**Imports are classified by `st_shndx` alone.** On MIPS an undefined function
carries the address of its lazy-binding stub in `st_value`, so requiring
`st_value == 0` misfiles most imports as exports — 165 of `/bin/boa`'s 181, on
the real image. The test fixtures reproduce that trap deliberately.

**Observations are not vulnerability claims.** `derive_findings` reports
structural facts about the image — a symlink from the document root into
writable storage, an init line commented out with the binary still shipped.
Whether any of them is exploitable is settled by reversing the binary, not by
an inventory tool. Keeping that line sharp is what stops it becoming a
false-positive generator.

## Layout

```
src/fwrecon/
  rtlimage.py   Realtek IMG_HEADER_T container + SquashFS superblock
  elf.py        ELF32 reader (program headers / PT_DYNAMIC)
  rootfs.py     attack-surface inventory of an unpacked filesystem
  report.py     JSON report + Markdown rendering
  diff.py       cross-version comparison
  cli.py        command line
tests/
  fixtures.py   synthetic binaries built in memory
```

## Tests

```bash
pip install -e '.[dev]'
pytest -q
ruff check src tests
```

Vendor firmware is not redistributable, so every structure the tests need — a
section-header-stripped big-endian MIPS ELF, a Realtek container, a SquashFS 4.0
superblock, a truncated image — is constructed in `tests/fixtures.py`. That is
an advantage rather than a workaround: each fixture encodes exactly the property
under test, including the awkward cases a real sample would only supply by luck.
