# firmware/

**No firmware binaries are stored here.** Vendor images for an EOL consumer
router are not mine to redistribute.

What is stored is everything needed to obtain byte-identical copies and prove
you got them:

| File | Role |
|---|---|
| `SOURCES.json` | Hand-curated: where each image comes from, what it should hash to, and *why this project analyses it* |
| `MANIFEST.json` | Generated: what was actually downloaded, its hashes, and when |

Keeping intent and observation in separate files is the point. When a mirror
silently replaces a file, that shows up as a mismatch between the two rather
than quietly invalidating every downstream result.

## Fetching

```bash
make fetch          # or: FWRE_WORK=~/fwre-work bash tools/fetch-firmware.sh
```

Images land in `$FWRE_WORK/firmware/` (default `~/fwre-work/firmware`), outside
the repository. The script verifies every hash that `SOURCES.json` declares and
refuses to record anything that fails.

## The two images

| ID | Built | Role |
|---|---|---|
| `n150rt-2.1.2-b20150825` | 2015-08-25 | Five weeks after Pierre Kim's disclosure — the vendor's response build |
| `n150rt-3.4.0-b20201030` | 2020-10-30 | Nine months after the Realtek SDK full disclosure — the post-fix build |

Together they bracket both public disclosure events affecting this device,
which is what makes a diff meaningful rather than merely descriptive.

## Verifying independently

The 2015 image's MD5 and SHA-1 in `SOURCES.json` were taken from the Internet
Archive's item metadata API, not computed from the download. They can therefore
be checked against a source we do not control:

```bash
curl -s https://archive.org/metadata/TOTOLINKN150RTV2.1.2B20150825.1601 \
  | jq '.files[] | select(.name|endswith(".web")) | {name, size, md5, sha1}'
```

The 2020 image has no publisher-supplied hash; its SHA-256 was pinned on first
fetch and any later change is treated as a supply-chain signal, not a silent
update.
