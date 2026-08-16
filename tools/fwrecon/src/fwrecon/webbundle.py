"""Parser for the ``w6cg`` web-resource bundle carried by 2015-family images.

Format
------
``w6cg`` holds one bzip2 stream. Decompressed, it is a flat archive with no
index and no terminator: a fixed 64-byte header followed immediately by the
file's bytes, repeated to the end.

    offset  size  meaning
    +0x00     ~   file name, NUL-terminated, path separators included
    +0x3c     4   content length, **big-endian**
    +0x40   len   content

The other header fields carry a duplicated pair of 32-bit timestamps and two
equal size-like values, all **little-endian** — the length at +0x3c is the only
big-endian field, which is the sort of detail that makes a guessed layout fail
loudly rather than quietly. Nothing here depends on those fields, so they are
reported raw rather than named.

Why this is trustworthy
-----------------------
The layout was recovered by inspection, so it needs a check that can fail. The
archive has no entry count to compare against, but it has something better:
because every stride is ``64 + length``, walking the chain either lands exactly
on the final byte or it does not. A wrong offset for the length field derails
within one or two entries and cannot recover. :func:`parse` walks to the end and
records ``exact`` only when zero bytes remain — on the three bundles this
project holds (2015, 2016, 2018) it consumes 1,720,168 / 1,704,011 / 1,417,000
bytes with nothing left over, and the 2018 count of 143 entries independently
reproduces a figure `notes/auth-flow-2018.md` had obtained by hand.

W01 recorded this format as "decompressed but its archive format not parsed"
and left it open. This closes it.
"""

from __future__ import annotations

import bz2
import hashlib
import struct
from dataclasses import dataclass, field
from pathlib import Path

HEADER_SIZE = 64
LENGTH_OFFSET = 0x3C
W6CG_TAG = b"w6cg"
IMG_HEADER_SIZE = 16


@dataclass
class WebEntry:
    index: int
    name: str
    offset: int          # of the header, within the decompressed archive
    length: int
    sha256: str

    @property
    def content_offset(self) -> int:
        return self.offset + HEADER_SIZE


@dataclass
class WebBundleReport:
    path: str
    source_sha256: str           # of the whole source file, never of the bundle
    section_offset: int          # where the w6cg header sat in the source file
    compressed_bytes: int
    decompressed_bytes: int
    entries: list[WebEntry] = field(default_factory=list)
    bytes_unconsumed: int = 0
    self_check: str = "unrun"
    anomalies: list[str] = field(default_factory=list)
    producer: str = "fwrecon:webbundle"

    def find(self, name: str) -> WebEntry | None:
        return next((e for e in self.entries if e.name == name), None)


def _locate_w6cg(data: bytes, at: int | None) -> tuple[int, bytes]:
    """Return (header offset, bzip2 payload). ``at`` forces a flash offset."""
    if at is not None:
        if data[at:at + 4] != W6CG_TAG:
            raise ValueError(f"no w6cg signature at 0x{at:x}")
        _start, _burn, length = struct.unpack(">3I", data[at + 4:at + IMG_HEADER_SIZE])
        return at, data[at + IMG_HEADER_SIZE:at + IMG_HEADER_SIZE + length]

    # Otherwise walk the container the way rtlimage does, but without importing
    # it: a bundle can be handed in on its own, and this keeps the dependency
    # one-way.
    off = 0
    while off + IMG_HEADER_SIZE <= len(data):
        tag = data[off:off + 4]
        if not (len(tag) == 4 and all(0x20 <= b < 0x7F for b in tag)):
            break
        _start, _burn, length = struct.unpack(">3I", data[off + 4:off + IMG_HEADER_SIZE])
        if length == 0 or length > len(data):
            break
        if tag == W6CG_TAG:
            return off, data[off + IMG_HEADER_SIZE:off + IMG_HEADER_SIZE + length]
        off += IMG_HEADER_SIZE + length
    raise ValueError("no w6cg section found; 2020-family images do not carry one")


def parse(path: str | Path, at: int | None = None) -> WebBundleReport:
    """Decompress and walk a ``w6cg`` bundle out of ``path``.

    ``at`` names a flash offset, for reading the section straight out of a raw
    dump rather than a ``.web`` container.
    """
    p = Path(path)
    data = p.read_bytes()
    section_offset, payload = _locate_w6cg(data, at)

    rep = WebBundleReport(
        path=str(p),
        source_sha256=hashlib.sha256(data).hexdigest(),
        section_offset=section_offset,
        compressed_bytes=len(payload),
        decompressed_bytes=0,
    )

    try:
        blob = bz2.decompress(payload)
    except (OSError, ValueError) as exc:
        rep.self_check = "undecompressible"
        rep.anomalies.append(f"bzip2 stream did not decompress: {exc}")
        return rep
    rep.decompressed_bytes = len(blob)

    off = 0
    index = 0
    while off + HEADER_SIZE <= len(blob):
        header = blob[off:off + HEADER_SIZE]
        name = header.split(b"\x00", 1)[0].decode("ascii", "replace")
        (length,) = struct.unpack(">I", header[LENGTH_OFFSET:LENGTH_OFFSET + 4])

        if not name:
            rep.anomalies.append(f"empty name at 0x{off:x}: the walk has derailed")
            break
        if off + HEADER_SIZE + length > len(blob):
            rep.anomalies.append(
                f"entry {index} ({name!r}) at 0x{off:x} declares {length} bytes but only "
                f"{len(blob) - off - HEADER_SIZE} remain: the walk has derailed"
            )
            break

        content = blob[off + HEADER_SIZE:off + HEADER_SIZE + length]
        rep.entries.append(WebEntry(
            index=index,
            name=name,
            offset=off,
            length=length,
            sha256=hashlib.sha256(content).hexdigest(),
        ))
        off += HEADER_SIZE + length
        index += 1

    rep.bytes_unconsumed = len(blob) - off
    # The whole point. There is no entry count and no terminator in this format,
    # so "the strides added up to exactly the file length" is the only evidence
    # that the layout was read correctly — and it is strong evidence, because a
    # wrong length offset cannot walk hundreds of entries and still land on the
    # last byte.
    if rep.bytes_unconsumed == 0 and rep.entries:
        rep.self_check = "exact"
    else:
        rep.self_check = "derailed"
        if rep.bytes_unconsumed and not rep.anomalies:
            rep.anomalies.append(
                f"{rep.bytes_unconsumed} bytes left unconsumed after "
                f"{len(rep.entries)} entries: the layout does not hold"
            )
    return rep


def contents(path: str | Path, entry: WebEntry, at: int | None = None) -> bytes:
    """Re-read one entry's bytes. Kept separate so a report stays cheap to hold."""
    data = Path(path).read_bytes()
    _off, payload = _locate_w6cg(data, at)
    blob = bz2.decompress(payload)
    return blob[entry.content_offset:entry.content_offset + entry.length]


def grep(path: str | Path, needle: bytes, at: int | None = None) -> list[tuple[WebEntry, int]]:
    """Entries whose *content* contains ``needle``, with the number of hits.

    Searching per entry rather than over the decompressed blob matters: it is
    the difference between "the string is in the bundle somewhere" and "this
    file contains it", and a comment banner naming a page is not the page.
    """
    rep = parse(path, at)
    data = Path(path).read_bytes()
    _off, payload = _locate_w6cg(data, at)
    blob = bz2.decompress(payload)
    out: list[tuple[WebEntry, int]] = []
    for e in rep.entries:
        content = blob[e.content_offset:e.content_offset + e.length]
        n = content.count(needle)
        if n:
            out.append((e, n))
    return out
