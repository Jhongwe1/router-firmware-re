"""Parser for the Realtek SDK firmware container used by TOTOLINK ``.web`` images.

Format
------
Realtek's ``cvimg`` packaging tool prefixes each flashable region with a 16-byte
big-endian header. The SDK declares it as::

    typedef struct {
        unsigned char signature[4];   /* e.g. "cr6c", "r6cr", "w6cg" */
        unsigned int  startAddr;      /* load address in RAM        */
        unsigned int  burnAddr;       /* destination offset in flash */
        unsigned int  len;            /* payload length, header excluded */
    } IMG_HEADER_T;

An image is simply those regions concatenated, optionally followed by a trailing
ASCII product tag that the vendor's upgrade CGI uses to reject images meant for
a different model.

Everything above was recovered by inspection of the two N150RT images rather
than taken on faith: ``burnAddr`` values line up with the flash map, and each
section's ``len`` lands exactly on the next section's signature, which is a
strong self-consistency check. :func:`parse` re-runs that check on every image
and reports where it fails instead of assuming the layout holds.

Why parse this at all when binwalk finds the payloads by signature scanning?
Because signature scanning tells you *what* is in the file, not *where the
device will put it*. ``burnAddr`` is what maps a firmware offset onto a flash
offset, and that mapping is what lets a flash dump taken off the real board be
compared against a vendor image.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

HEADER_SIZE = 16

# Signatures observed in the wild across Realtek-SDK vendors. Unknown 4-byte
# ASCII tags are still accepted — the structural checks decide validity, not
# this list — but a known tag raises confidence and supplies a description.
KNOWN_TAGS: dict[bytes, str] = {
    b"cs6c": "kernel (Realtek SDK, older naming)",
    b"cr6c": "kernel image (LZMA-compressed, preceded by a raw boot stub)",
    b"r6cr": "root filesystem",
    b"w6cg": "web resource bundle",
    b"csys": "system image",
    b"boot": "bootloader",
}

# SquashFS 4.0 is defined as little-endian *on disk* regardless of host CPU
# endianness — the kernel driver byte-swaps on big-endian systems. So an
# 'hsqs' superblock inside a big-endian MIPS firmware is correct, not a
# contradiction, and is worth stating explicitly because it looks like one.
SQUASHFS_MAGIC_LE = b"hsqs"
SQUASHFS_MAGIC_BE = b"sqsh"
SQUASHFS_COMPRESSION = {
    1: "gzip", 2: "lzma", 3: "lzo", 4: "xz", 5: "lz4", 6: "zstd",
}

PAYLOAD_MAGICS: tuple[tuple[bytes, str], ...] = (
    (b"BZh", "bzip2"),
    (b"\xfd7zXZ\x00", "xz"),
    # Require the deflate method byte too: a bare \x1f\x8b is only 16 bits and
    # fires constantly inside compressed kernels. It did exactly that on the
    # 2015 image, reporting a phantom gzip stream inside the LZMA kernel.
    (b"\x1f\x8b\x08", "gzip"),
    (b"hsqs", "squashfs (little-endian superblock)"),
    (b"sqsh", "squashfs (big-endian superblock)"),
    (b"\x7fELF", "elf"),
    (b"\x5d\x00\x00", "lzma (alone format, lc=3 lp=0 pb=2)"),
)


@dataclass
class SquashfsInfo:
    offset: int
    version: str
    compression: str
    inodes: int
    block_size: int
    fragments: int
    bytes_used: int
    mkfs_time_raw: int
    mkfs_time_utc: str | None
    anomalies: list[str] = field(default_factory=list)


@dataclass
class Section:
    index: int
    offset: int              # where the header sits in the file
    tag: str
    description: str
    start_addr: int          # RAM load address
    burn_addr: int           # flash destination offset
    length: int              # declared payload length
    payload_offset: int
    payload_actual: int      # bytes really available (differs if image truncated)
    payload_type: str
    inner_findings: list[str] = field(default_factory=list)
    squashfs: SquashfsInfo | None = None
    anomalies: list[str] = field(default_factory=list)


@dataclass
class ImageReport:
    path: str
    size: int
    sections: list[Section] = field(default_factory=list)
    trailer: str | None = None
    trailer_offset: int | None = None
    flash_map: list[dict] = field(default_factory=list)
    min_flash_size: int = 0
    anomalies: list[str] = field(default_factory=list)


def _looks_like_tag(raw: bytes) -> bool:
    return len(raw) == 4 and all(0x20 <= b < 0x7F for b in raw)


def _identify(payload: bytes) -> str:
    for magic, name in PAYLOAD_MAGICS:
        if payload.startswith(magic):
            return name
    return "raw/unrecognised"


def _scan_inner(payload: bytes, limit: int = 0x20000) -> list[str]:
    """Look a little way into a raw payload for a nested known format.

    The kernel section starts with a position-dependent boot stub and only then
    holds the compressed kernel, so the section's own leading bytes never
    identify it.
    """
    findings: list[str] = []
    window = payload[:limit]
    for magic, name in PAYLOAD_MAGICS:
        idx = window.find(magic, 1)
        if idx > 0:
            findings.append(f"{name} at +0x{idx:x}")
    return findings


def _parse_squashfs(data: bytes, offset: int) -> SquashfsInfo | None:
    blob = data[offset:offset + 96]
    if len(blob) < 96:
        return None
    if blob[:4] == SQUASHFS_MAGIC_LE:
        e = "<"
    elif blob[:4] == SQUASHFS_MAGIC_BE:
        e = ">"
    else:
        return None

    inodes, mkfs_time, block_size, fragments = struct.unpack_from(e + "4I", blob, 4)
    compression, block_log, _flags, _no_ids, s_major, s_minor = \
        struct.unpack_from(e + "6H", blob, 20)
    (bytes_used,) = struct.unpack_from(e + "Q", blob, 40)

    anomalies: list[str] = []
    stamp: str | None = None
    try:
        dt = datetime.fromtimestamp(mkfs_time, UTC)
        stamp = dt.isoformat()
        # A build stamp in the future is a build-system defect, not a filesystem
        # one, but it matters here: it means the image cannot be dated from its
        # own metadata and the vendor's filename is the only date we have.
        if dt.year >= 2038 or dt.year < 2000:
            swapped = int.from_bytes(struct.pack(e + "I", mkfs_time), "big")
            anomalies.append(
                f"mkfs_time is implausible ({stamp}); raw=0x{mkfs_time:08x}. "
                f"Byte-reversed it reads 0x{swapped:08x}, which is suspiciously "
                "close to the filesystem size - possibly a vendor build-script "
                "bug writing a size into this field."
            )
    except (OverflowError, OSError, ValueError):
        anomalies.append(f"mkfs_time 0x{mkfs_time:08x} is not a representable time")

    if block_log and (1 << block_log) != block_size:
        anomalies.append(f"block_log {block_log} disagrees with block_size {block_size}")

    return SquashfsInfo(
        offset=offset,
        version=f"{s_major}.{s_minor}",
        compression=SQUASHFS_COMPRESSION.get(compression, f"unknown({compression})"),
        inodes=inodes,
        block_size=block_size,
        fragments=fragments,
        bytes_used=bytes_used,
        mkfs_time_raw=mkfs_time,
        mkfs_time_utc=stamp,
        anomalies=anomalies,
    )


def parse(path: str | Path) -> ImageReport:
    p = Path(path)
    data = p.read_bytes()
    rep = ImageReport(path=str(p), size=len(data))

    offset = 0
    index = 0
    while offset + HEADER_SIZE <= len(data):
        tag_raw = data[offset:offset + 4]
        if not _looks_like_tag(tag_raw):
            break

        start_addr, burn_addr, length = struct.unpack_from(">3I", data, offset + 4)

        # Structural sanity: a header whose length runs wildly past the file is
        # almost certainly a false positive from four printable bytes.
        if length == 0 or length > len(data):
            break

        payload_offset = offset + HEADER_SIZE
        available = max(0, min(length, len(data) - payload_offset))
        payload = data[payload_offset:payload_offset + available]

        sec = Section(
            index=index,
            offset=offset,
            tag=tag_raw.decode("ascii"),
            description=KNOWN_TAGS.get(tag_raw, "unknown section type"),
            start_addr=start_addr,
            burn_addr=burn_addr,
            length=length,
            payload_offset=payload_offset,
            payload_actual=available,
            payload_type=_identify(payload),
        )

        if available < length:
            sec.anomalies.append(
                f"declared length {length} exceeds available bytes {available} "
                f"by {length - available}: image is truncated or the length field "
                "covers a trailer this copy lacks"
            )

        if sec.payload_type == "raw/unrecognised":
            sec.inner_findings = _scan_inner(payload)

        if payload[:4] in (SQUASHFS_MAGIC_LE, SQUASHFS_MAGIC_BE):
            sec.squashfs = _parse_squashfs(data, payload_offset)

        rep.sections.append(sec)
        index += 1
        offset = payload_offset + length

    # Anything left over that is printable is the vendor's product tag.
    if 0 < offset < len(data):
        tail = data[offset:offset + 128]
        printable = bytes(b for b in tail if 0x20 <= b < 0x7F or b in (0x0A, 0x0D))
        if len(printable) >= max(4, len(tail.rstrip(b"\x00\n\r")) // 2):
            rep.trailer = printable.decode("ascii", "replace").strip()
            rep.trailer_offset = offset
        else:
            rep.anomalies.append(
                f"{len(data) - offset} unparsed bytes at 0x{offset:x}")
    elif offset > len(data):
        rep.anomalies.append(
            f"section table overruns end of file by {offset - len(data)} bytes")

    # The flash map is the point of the exercise: burnAddr tells you where each
    # region lands on the SPI part, which sets the minimum part size and gives
    # the offsets to compare a physical dump against.
    for s in rep.sections:
        rep.flash_map.append({
            "tag": s.tag,
            "flash_offset": s.burn_addr,
            "flash_offset_hex": f"0x{s.burn_addr:06x}",
            "length": s.length,
            "end": s.burn_addr + s.length,
            "ram_load_addr": f"0x{s.start_addr:08x}",
        })
    rep.min_flash_size = max((e["end"] for e in rep.flash_map), default=0)

    if not rep.sections:
        rep.anomalies.append("no Realtek IMG_HEADER_T sections recognised")

    return rep
