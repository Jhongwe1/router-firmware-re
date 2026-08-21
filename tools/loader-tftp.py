#!/usr/bin/env python3
"""Talk TFTP to the RealTek boot loader's rescue service.

Which end is the server, and how that was got wrong
---------------------------------------------------
On 2026-08-21 this was designed the other way round, on the strength of two
format strings in the loader's own LZMA second stage::

    **TFTP Client Upload, File Name: %s
    *TFTP Client Download Success! File Size = %X Bytes

"Client" was read as naming the loader, and a note went into two committed files
saying the work here was a TFTP *server* on the workstation. **It names the peer.**
The loader is the server, and this repository had already measured that on
2026-08-17 (`BENCH-LOG.md` `T-09`)::

    TFTP RRQ(a filename that does not exist) -> 516 bytes DATA (opcode 3) from :2098

A read request was answered with data. Nothing else has to be argued. The same
card records two more things that shape this tool:

  * **the filename is ignored.** A name that exists nowhere still returned a
    full first block, so the transfer is defined by the loader's load address
    and not by what is asked for;
  * the 516 bytes matched the ``cr6c`` payload at flash ``0x060010`` byte for
    byte, which was filed as an open question and not pursued.

The other strings agree once "Client" is read as the peer:
``**TFTP GET File %s,Size %X Byte`` states a size for a file it is about to
*send*, and ``LOADADDR`` / ``Set TFTP Load Addr 0x%x`` only mean something if an
arriving upload needs somewhere to land.

What this is for
----------------
``get``   ``FLR`` moves flash into RAM and this moves RAM to the workstation.
          The console path (``DB`` over 38400 8N1) took **105 minutes** for
          4 MiB; this is the same bytes over Ethernet. It is emphatically **not**
          a second instrument — both paths read the die through the SoC's own SPI
          controller — but it *is* a second **transport**, which rules out the
          serial line as a source of corruption and rules out nothing else.
          Say it that way or do not say it.

``put``   ``P9-12``: with ``AUTOBURN 0``, an image uploaded here lands in RAM and
          **not one flash byte is written**. ``J <LOADADDR>`` then hands control
          to it. That is a demonstration that this device will execute an image
          it has never seen, without altering the device.

``probe`` One request, one reply, no file written. Reproduces `T-09` and reports
          the server's transfer id, which is the one protocol detail this
          loader's behaviour makes load-bearing (below).

The transfer id, which is why this is not `curl`
------------------------------------------------
TFTP's reply comes from a different port than the request went to — the bench saw
``:2098``. Everything after the first packet is addressed to that port. A client
that filters on 69 sees nothing and reports the service as dead, and a firewall
rule written for 69 alone does the same. So: the peer **address** is pinned and
checked on every packet; the peer **port** is learned from the first reply and
pinned from then on.

This file said "a fresh **ephemeral** port" until 2026-08-21, which was a guess
dressed as a measurement. 2098 is a **constant in the loader**::

    80401de0  li  v1,2098
    80401de8  sh  v1,-8928(v0)        ; 0x8040DD20, the source port it answers from
    80401ad4..80401ae4  lhu/addiu 1/sh ; and it increments after each completed upload

so the second transfer of a session comes from 2099, not from something random.
Nothing in the client changes — learning the port from the first reply covers
both — but "ephemeral" would have made a reader expect a number that means
nothing, and this one means "how many uploads have finished".

How this is allowed to fail
---------------------------
* the host must be a dotted quad, and every datagram must come from it;
* block numbers must be consecutive. A gap is an error, not a hole to paper over
  — the console parser next door exists because of exactly that failure mode;
* an ERROR packet is an *answer*: its code and message are reported, and it is
  never rendered as an empty or short transfer;
* a transfer with no final short block is bounded by ``--max-bytes`` rather than
  running until something else stops it;
* ``octet`` is the only mode, and there is no flag for ``netascii`` — that mode
  rewrites line endings and would corrupt an image in a way no checksum here
  would catch;
* ``put`` refuses to run without a `console-dump.py rescue` transcript that
  **this tool parses** and finds ``AutoBurning=0`` in, for the same host. This
  tool cannot see the console, so it does not pretend to: it requires the other
  tool's evidence and checks it.

Usage
-----
  tools/loader-tftp.py probe --host 10.1.1.1
  tools/loader-tftp.py get   --host 10.1.1.1 -o $FWRE_WORK/dumps/ram.bin
  tools/loader-tftp.py put   --host 10.1.1.1 --image img.bin \\
                             --rescue-report $FWRE_WORK/dumps/rescue.json --yes
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import struct
import sys
import time

TFTP_PORT = 69
BLOCK_SIZE = 512
#: `octet` and nothing else. See the module note.
MODE = b"octet"

OP_RRQ, OP_WRQ, OP_DATA, OP_ACK, OP_ERROR = 1, 2, 3, 4, 5

#: RFC 1350 s.4. Reported by number *and* name, because a loader is free to
#: return a code this table does not have and "unknown code 9" is information.
ERROR_NAMES = {
    0: "not defined",
    1: "file not found",
    2: "access violation",
    3: "disk full or allocation exceeded",
    4: "illegal TFTP operation",
    5: "unknown transfer ID",
    6: "file already exists",
    7: "no such user",
}

#: Twice the size of this unit's flash. A bound that can be raised deliberately
#: rather than a loop that ends when something else gets bored.
DEFAULT_MAX_BYTES = 8 * 1024 * 1024
DEFAULT_TIMEOUT = 3.0
DEFAULT_RETRIES = 4

#: Filenames this loader's *upload* path tests for by name, at 0x80401208 and
#: 0x8040122C in the decompressed second stage. A match sets the "run it when
#: the transfer finishes" flag at 0x8040D390, and `boot.img` additionally forces
#: the load address at 0x8040D3A8 to 0x80000000::
#:
#:     80401208  move  a0,s0            ; the filename out of the WRQ
#:     80401210  jal   0x80406d7c       ; against "nfjrom"
#:     80401228  sw    v1,-11376(v0)    ; 0x8040D390 = 1  -> execute on completion
#:     8040122C  addiu a0,s1,30
#:     80401234  jal   0x80406c40       ; against "boot.img"
#:     80401250  lui   v1,0x8000
#:     80401258  sw    v1,-11352(v0)    ; 0x8040D3A8 = 0x80000000
#:
#: So the name is not cosmetic on this loader: two of them turn an upload into
#: an execution with no console step at all. `J` is kept in a human's hands on
#: purpose, and a default filename is not where that decision should be lost.
AUTOEXEC_FILENAMES = ("nfjrom", "boot.img")

#: `AUTOBURN 0` is RAM state in the loader and does not survive a power cycle,
#: so a transcript proving it was sent proves it about *that* boot. This bounds
#: how old the evidence may be; it does not establish same-boot, and the tool
#: says so rather than implying otherwise.
DEFAULT_MAX_RESCUE_AGE = 3600.0


class TftpError(RuntimeError):
    """The transfer did not happen. Raised, never returned as a short file."""


def fail(msg: str) -> None:
    print(f"  FAIL  {msg}", file=sys.stderr)
    raise SystemExit(1)


def check_host(host: str) -> str:
    parts = host.split(".")
    if len(parts) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
        fail(f"--host {host!r} is not a dotted quad. The loader synthesises its "
             f"MAC from the address IPCONFIG was given, so this is the address "
             f"the console was told, not a name to resolve")
    return host


def _request(op: int, filename: str) -> bytes:
    return struct.pack("!H", op) + filename.encode() + b"\0" + MODE + b"\0"


def _parse_error(pkt: bytes) -> str:
    if len(pkt) < 4:
        return "malformed ERROR packet"
    (code,) = struct.unpack_from("!H", pkt, 2)
    msg = pkt[4:].split(b"\0", 1)[0].decode(errors="replace")
    return f"ERROR {code} ({ERROR_NAMES.get(code, 'unknown code')}): {msg}"


class Session:
    """One TFTP conversation, with the peer address pinned and the port learned.

    The address is fixed by the caller and every datagram is checked against it.
    The port is whatever answered first and is fixed from then on: that is the
    transfer id, and this loader picks a high one (`:2098` when the bench looked).
    """

    def __init__(self, host: str, timeout: float, retries: int, verbose: bool,
                 server_port: int = TFTP_PORT):
        self.host = host
        self.server_port = server_port
        self.timeout = timeout
        self.retries = retries
        self.verbose = verbose
        self.tid: int | None = None
        self.retransmits = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(timeout)

    def close(self) -> None:
        self.sock.close()

    def _send(self, pkt: bytes, port: int) -> None:
        self.sock.sendto(pkt, (self.host, port))

    def exchange(self, pkt: bytes, port: int) -> bytes:
        """Send, and return the first datagram from the pinned peer.

        Retransmits on timeout. A datagram from another address is not an error
        to abort on and not something to accept either -- it is dropped, counted
        and reported, because on a lab segment the other thing talking is
        usually the operator's own second interface.
        """
        for attempt in range(self.retries):
            if attempt:
                self.retransmits += 1
                if self.verbose:
                    print(f"        retransmit {attempt}/{self.retries - 1}")
            self._send(pkt, port)
            deadline = time.monotonic() + self.timeout
            while time.monotonic() < deadline:
                try:
                    self.sock.settimeout(max(0.05, deadline - time.monotonic()))
                    data, addr = self.sock.recvfrom(65535)
                except TimeoutError:
                    break
                if addr[0] != self.host:
                    if self.verbose:
                        print(f"        ignored a datagram from {addr[0]}, "
                              f"expected {self.host}")
                    continue
                if self.tid is None:
                    self.tid = addr[1]
                    if self.verbose:
                        print(f"  ok    transfer id {self.tid} "
                              f"(the reply does NOT come from {self.server_port})")
                elif addr[1] != self.tid:
                    raise TftpError(
                        f"a datagram arrived from {self.host}:{addr[1]} but this "
                        f"transfer belongs to port {self.tid}. RFC 1350 calls "
                        f"that a different transfer; it is not merged in here")
                return data
        raise TftpError(
            f"no reply from {self.host} after {self.retries} attempts at "
            f"{self.timeout}s. The loader answers TFTP and implements no ICMP at "
            f"all (measured 2026-08-17), so a failed ping proves nothing either "
            f"way -- check `ip neigh` and the interface rx counter instead")


def read_transfer(sess: Session, filename: str, max_bytes: int,
                  first_block_only: bool = False) -> tuple[bytes, int]:
    """RRQ, then ACK each block. Returns (payload, blocks)."""
    pkt = sess.exchange(_request(OP_RRQ, filename), sess.server_port)
    out = bytearray()
    blocks = 0
    expected = 1
    while True:
        (op,) = struct.unpack_from("!H", pkt, 0)
        if op == OP_ERROR:
            raise TftpError(_parse_error(pkt))
        if op != OP_DATA:
            raise TftpError(f"expected DATA (opcode {OP_DATA}), got opcode {op}")
        (block,) = struct.unpack_from("!H", pkt, 2)
        # 16 bits wraps at 8,192 blocks x 512 = 4 MiB, which is exactly this
        # part's size, so a full-flash transfer sits on the boundary rather than
        # safely inside it. Compare modulo instead of assuming it never happens.
        if block != (expected & 0xFFFF):
            raise TftpError(
                f"block {block} arrived where {expected & 0xFFFF} was expected "
                f"after {len(out)} bytes. A gap is not a hole to fill in: every "
                f"offset after it would be wrong and the file would still look "
                f"like a file")
        payload = pkt[4:]
        out += payload
        blocks += 1
        if len(out) > max_bytes:
            raise TftpError(
                f"more than --max-bytes ({max_bytes}) received and no short "
                f"block yet. Either the loader is serving more than expected or "
                f"this never terminates; both need a decision, not a bigger read")
        ack = struct.pack("!HH", OP_ACK, block)
        if len(payload) < BLOCK_SIZE or first_block_only:
            sess._send(ack, sess.tid or sess.server_port)
            return bytes(out), blocks
        expected += 1
        pkt = sess.exchange(ack, sess.tid or sess.server_port)


def write_transfer(sess: Session, filename: str, data: bytes) -> int:
    """WRQ, then send blocks as each is acknowledged. Returns blocks sent."""
    pkt = sess.exchange(_request(OP_WRQ, filename), sess.server_port)
    (op,) = struct.unpack_from("!H", pkt, 0)
    if op == OP_ERROR:
        raise TftpError(_parse_error(pkt))
    if op != OP_ACK:
        raise TftpError(f"expected ACK (opcode {OP_ACK}) to the write request, "
                        f"got opcode {op}")
    (block,) = struct.unpack_from("!H", pkt, 2)
    if block != 0:
        raise TftpError(f"the write request was acknowledged with block {block}, "
                        f"not 0, so the peer is not where this transfer thinks "
                        f"it is")

    sent = 0
    offset = 0
    number = 1
    while True:
        chunk = data[offset:offset + BLOCK_SIZE]
        pkt = sess.exchange(
            struct.pack("!HH", OP_DATA, number & 0xFFFF) + chunk,
            sess.tid or sess.server_port)
        (op,) = struct.unpack_from("!H", pkt, 0)
        if op == OP_ERROR:
            raise TftpError(_parse_error(pkt))
        if op != OP_ACK:
            raise TftpError(f"expected ACK, got opcode {op} after {offset} bytes")
        (ack,) = struct.unpack_from("!H", pkt, 2)
        if ack != (number & 0xFFFF):
            raise TftpError(f"block {number & 0xFFFF} was answered with an ACK "
                            f"for {ack}")
        sent += 1
        offset += len(chunk)
        number += 1
        if len(chunk) < BLOCK_SIZE:
            return sent


# ------------------------------------------------------------------ commands

def _report(args, body: dict) -> None:
    if not getattr(args, "report", None):
        return
    body["producer"] = "loader-tftp"
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(body, fh, indent=2)
    print(f"  ok    transcript -> {args.report}")


def attribute(data: bytes, dump_path: str) -> dict:
    """Where, if anywhere, do these bytes sit in a flash dump?

    Open question 96 asks what the loader serves and from where.  The loader's
    own DATA sender reads ``[0x8040D3A8] + (block-1)*512`` for ``[0x8040DD28]``
    bytes (0x80401ED4), so what arrives is RAM -- but RAM at the load address is
    where the loader stages the kernel out of flash before it offers the
    interrupt window, so a transfer matching flash is exactly what a *staged
    copy* looks like too.

    This therefore reports **an offset, not a conclusion**.  What separates the
    two is the FLR step next to it in the runsheet, and the caller is told so.

    Exactly one match, or it says so: a byte string that occurs twice in 4 MiB
    has not been located, and one that occurs nowhere is a finding rather than
    an error.
    """
    if not data:
        return {"searched": os.path.basename(dump_path), "result": "empty transfer",
                "offsets": []}
    with open(dump_path, "rb") as fh:
        blob = fh.read()
    offsets, at = [], 0
    while len(offsets) < 3:
        i = blob.find(data, at)
        if i < 0:
            break
        offsets.append(i)
        at = i + 1
    return {"searched": os.path.basename(dump_path), "dump_bytes": len(blob),
            "offsets": offsets, "bytes": len(data)}


def report_attribution(att: dict) -> None:
    offs = att.get("offsets", [])
    where = att["searched"]
    if att.get("result") == "empty transfer":
        print(f"  --    nothing to look for in {where}: the transfer was empty")
        return
    if not offs:
        print(f"  ok    these {att['bytes']} bytes occur NOWHERE in {where}. Whatever is "
              f"at the load address is not a copy of this part's contents")
    elif len(offs) == 1:
        print(f"  ok    these {att['bytes']} bytes are flash[{offs[0]:#08x} : "
              f"{offs[0] + att['bytes']:#08x}] in {where}, and occur there exactly once")
        print("        That is an offset, not a source: the loader stages the kernel from "
              "flash into RAM at the load address before the interrupt window, so a match "
              "is what both answers look like. The FLR step is what separates them")
    else:
        print(f"  --    these bytes occur at {len(offs)}+ offsets in {where} "
              f"({', '.join(hex(o) for o in offs)}); that is not a location")


def cmd_probe(args) -> int:
    host = check_host(args.host)
    sess = Session(host, args.timeout, args.retries, args.verbose, args.port)
    print(f" ==>   one read request to {host}:{args.port}, first block only, "
          f"nothing written")
    try:
        data, blocks = read_transfer(sess, args.filename, BLOCK_SIZE * 2,
                                     first_block_only=True)
    except TftpError as e:
        fail(str(e))
        return 1
    finally:
        sess.close()
    digest = hashlib.sha256(data).hexdigest()
    print(f"  ok    DATA opcode {OP_DATA} from {host}:{sess.tid}, "
          f"{len(data)} bytes in {blocks} block")
    print(f"  ok    sha256 {digest}")
    print(f"        the filename asked for was {args.filename!r}. This loader "
          f"ignores it on the READ path (2026-08-17), so a name that exists "
          f"nowhere still returns data -- which means a reply here says the "
          f"service answers, not that the file was found. On the WRITE path it "
          f"does not ignore it: see AUTOEXEC_FILENAMES")
    att = None
    if args.attribute:
        att = attribute(data, args.attribute)
        report_attribution(att)
    _report(args, {"op": "probe", "host": host, "tid": sess.tid,
                   "filename": args.filename, "bytes": len(data),
                   "blocks": blocks, "sha256": digest,
                   "retransmits": sess.retransmits, "attribution": att})
    return 0


def cmd_get(args) -> int:
    host = check_host(args.host)
    if os.path.exists(args.output) and not args.force:
        fail(f"{args.output} exists. Refusing to overwrite a dump; --force if "
             f"that is really what you want")
    sess = Session(host, args.timeout, args.retries, args.verbose, args.port)
    print(f" ==>   read {args.filename!r} from {host} (the name is ignored by "
          f"this loader; the load address decides what arrives)")
    started = time.monotonic()
    try:
        data, blocks = read_transfer(sess, args.filename, args.max_bytes)
    except TftpError as e:
        fail(str(e))
        return 1
    finally:
        sess.close()
    elapsed = time.monotonic() - started
    with open(args.output, "wb") as fh:
        fh.write(data)
    digest = hashlib.sha256(data).hexdigest()
    print(f"  ok    {len(data)} bytes in {blocks} blocks from {host}:{sess.tid} "
          f"in {elapsed:.2f}s")
    print(f"  ok    sha256 {digest}")
    print(f"  ok    -> {args.output}")
    print("        This is a second TRANSPORT for the same read, not a second "
          "instrument: both this and `FLR`+`DB` reach the die through the SoC's "
          "own SPI controller. It rules out the serial line and nothing else")
    att = None
    if args.attribute:
        att = attribute(data, args.attribute)
        report_attribution(att)
    _report(args, {"op": "get", "host": host, "tid": sess.tid,
                   "filename": args.filename, "output": args.output,
                   "bytes": len(data), "blocks": blocks, "sha256": digest,
                   "seconds": round(elapsed, 3), "retransmits": sess.retransmits,
                   "attribution": att})
    return 0


def check_rescue_report(path: str, host: str, max_age: float) -> dict:
    """The evidence `put` requires, because this tool cannot see the console.

    `console-dump.py rescue` sends `AUTOBURN 0`, refuses to continue unless the
    loader echoes `AutoBurning=0`, and writes what it sent and saw. That file is
    the only thing standing between an upload that lands in RAM and an upload
    that is written to flash, so it is parsed here rather than trusted: the
    right host, and the right echo, or nothing is sent.

    Version 1 checked the host and the echo and nothing else, and that is a
    guard that cannot fail in the way that matters. `AUTOBURN` is a **RAM
    variable in the loader** -- `runsheet.md` `A2.4` says so in its own header --
    written at 0x8040D4A0 and read at exactly one place, 0x80401B9C, on the path
    that decides whether a completed upload is burned. A power cycle clears it.
    So a transcript from four days ago satisfied every check while saying
    nothing whatever about the loader now listening, and the consequence of
    being wrong is a flash write to the only unit there is.

    Bounding the age does not establish same-boot and this does not pretend it
    does: it converts "any transcript that ever existed" into "one written in
    the last hour", and the operator is told which of those two it is.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            rep = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        fail(f"--rescue-report {path}: {e}")
        return {}
    if rep.get("ip") != host:
        fail(f"--rescue-report is for {rep.get('ip')!r} and --host is {host!r}. "
             f"A transcript from a different address says nothing about this one")
    replies = " ".join(str(s.get("reply", "")) for s in rep.get("steps", []))
    if "AutoBurning=1" in replies:
        fail("the rescue transcript contains AutoBurning=1. With autoburn on, "
             "an upload is written to flash. Sending nothing")
    if "AutoBurning=0" not in replies:
        fail("the rescue transcript does not contain AutoBurning=0, so the state "
             "of the switch that decides whether this upload reaches flash is "
             "unknown. Run `console-dump.py rescue --output ...` first")
    try:
        age = time.time() - os.path.getmtime(path)
    except OSError as e:
        fail(f"--rescue-report {path}: cannot read its age: {e}")
        return {}
    if max_age > 0 and age > max_age:
        fail(f"the rescue transcript is {age / 60:.0f} minutes old and --max-rescue-age "
             f"is {max_age / 60:.0f}. AUTOBURN is RAM state in the loader (0x8040D4A0) "
             f"and a power cycle clears it, so this file says nothing about the loader "
             f"that is listening now. Re-run `console-dump.py rescue --at-prompt "
             f"--ip {host} -o {path}` in this session")
    rep["_age_seconds"] = round(age, 1)
    return rep


def cmd_put(args) -> int:
    host = check_host(args.host)
    # Before anything is opened: the name decides whether a human gets to make
    # the next decision. See AUTOEXEC_FILENAMES.
    lowered = args.filename.lower()
    hit = next((n for n in AUTOEXEC_FILENAMES if n in lowered), None)
    if hit and not args.allow_autoexec:
        fail(f"--filename {args.filename!r} contains {hit!r}, which this loader's upload "
             f"path tests for by name (0x80401208 / 0x8040122C). On a match it sets the "
             f"flag at 0x8040D390 and jumps to the load address the moment the transfer "
             f"completes -- no `J`, nobody at the console"
             + (", and 'boot.img' also forces the load address to 0x80000000"
                if hit == "boot.img" else "")
             + ". Pick another name, or pass --allow-autoexec having decided to")
    rep = check_rescue_report(args.rescue_report, host, args.max_rescue_age)
    print(f"  ok    rescue transcript for {host} shows AutoBurning=0 "
          f"({rep.get('_age_seconds', 0) / 60:.0f} minutes old)")
    # Where this lands, and therefore what `J` has to be given. The tool cannot
    # send `J` and should not; what it can do is refuse to leave the operator
    # guessing the number.
    recorded = rep.get("load_addr")
    if args.expect_load is not None:
        want = f"{args.expect_load:#010x}"
        if recorded is None:
            fail(f"--expect-load {want} was given but the rescue transcript does not "
                 f"record a load address. Re-run `console-dump.py rescue --load-addr "
                 f"{args.expect_load:08X} ...` so that the address J will be given comes "
                 f"from the loader's own echo rather than from memory")
        if int(recorded, 16) != args.expect_load:
            fail(f"the loader was told to load at {recorded} and --expect-load says "
                 f"{want}. One of those is the address J would be given, and this tool "
                 f"cannot tell which")
        print(f"  ok    the transcript records the loader's load address as {recorded}, "
              f"which is what J must be given")
    elif recorded:
        print(f"  note  the transcript records load address {recorded}; that is what J "
              f"must be given afterwards. --expect-load makes that a check")
    else:
        print("  note  the transcript does not record a load address, so the number for "
              "`J` is not on the record. This loader's default is 0x80500000")
    try:
        with open(args.image, "rb") as fh:
            data = fh.read()
    except OSError as e:
        fail(str(e))
        return 1
    if not data:
        fail(f"{args.image} is empty")
    digest = hashlib.sha256(data).hexdigest()
    print(f" ==>   upload {len(data)} bytes, sha256 {digest}")
    print("        With autoburn off this lands at the loader's LOADADDR in RAM "
          "and writes no flash. That is the whole point of the row: an image "
          "the device has never seen, executed, with the part unmodified")
    if not args.yes:
        fail("refusing without --yes. This is the one subcommand here that "
             "sends bytes the device will act on")
    sess = Session(host, args.timeout, args.retries, args.verbose, args.port)
    started = time.monotonic()
    try:
        blocks = write_transfer(sess, args.filename, data)
    except TftpError as e:
        fail(str(e))
        return 1
    finally:
        sess.close()
    elapsed = time.monotonic() - started
    print(f"  ok    {len(data)} bytes in {blocks} blocks to {host}:{sess.tid} "
          f"in {elapsed:.2f}s")
    print("        Next is `J <LOADADDR>` on the console, and this tool does "
          "not send it: a jump is a state change on the only unit there is, "
          "and it belongs where a human is watching the console")
    _report(args, {"op": "put", "host": host, "tid": sess.tid,
                   "filename": args.filename, "image": args.image,
                   "bytes": len(data), "blocks": blocks, "sha256": digest,
                   "seconds": round(elapsed, 3), "retransmits": sess.retransmits,
                   "rescue_report": args.rescue_report,
                   "rescue_ip": rep.get("ip")})
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="TFTP to the RealTek boot loader's rescue service "
                    "(the loader is the server; see the module note)")
    p.add_argument("--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--host", required=True,
                        help="the address IPCONFIG was given, e.g. 10.1.1.1")
        # 69 on the device; settable so the guard suite can drive every branch
        # of this file against a stand-in server with no hardware attached. A
        # network tool that can only be exercised by plugging in the only unit
        # there is, is a network tool that gets exercised for the first time at
        # the bench.
        sp.add_argument("--port", type=int, default=TFTP_PORT,
                        help=f"the port the request goes to (default {TFTP_PORT}); "
                             f"the reply comes from a different one either way")
        sp.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                        help=f"seconds per attempt (default {DEFAULT_TIMEOUT})")
        sp.add_argument("--retries", type=int, default=DEFAULT_RETRIES,
                        help=f"attempts per packet (default {DEFAULT_RETRIES})")
        sp.add_argument("--report", help="write a JSON transcript here")
        sp.add_argument("--verbose", action="store_true")

    def attribution(sp):
        sp.add_argument("--attribute", metavar="DUMP",
                        help="after the transfer, say where these bytes sit in DUMP -- "
                             "exactly one offset, or it says it could not locate them. "
                             "An offset, not a source: see open question 96")

    pp = sub.add_parser("probe", help="one read request, first block only, "
                                      "nothing written")
    common(pp)
    attribution(pp)
    pp.add_argument("--filename", default="probe",
                    help="ignored by this loader on the READ path; sent anyway "
                         "(default: probe)")
    pp.set_defaults(func=cmd_probe)

    pg = sub.add_parser("get", help="read the loader's memory to a file")
    common(pg)
    attribution(pg)
    pg.add_argument("--filename", default="ram",
                    help="ignored by this loader on the READ path")
    pg.add_argument("-o", "--output", required=True)
    pg.add_argument("--force", action="store_true",
                    help="overwrite an existing output file")
    pg.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES,
                    help=f"stop rather than run on (default {DEFAULT_MAX_BYTES})")
    pg.set_defaults(func=cmd_get)

    pu = sub.add_parser("put", help="upload an image into the loader's RAM")
    common(pu)
    pu.add_argument("--filename", default="image",
                    help="NOT ignored on the write path: two names make this loader "
                         "execute the upload with no console step (default: image)")
    pu.add_argument("--allow-autoexec", action="store_true",
                    help=f"permit a filename containing one of {AUTOEXEC_FILENAMES}, "
                         f"which hands the jump to the loader instead of to a person")
    pu.add_argument("--image", required=True)
    pu.add_argument("--rescue-report", required=True,
                    help="the JSON console-dump.py rescue wrote; it must show "
                         "AutoBurning=0 for this same host, recently")
    pu.add_argument("--max-rescue-age", type=float, default=DEFAULT_MAX_RESCUE_AGE,
                    help=f"seconds; refuse an older transcript, because AUTOBURN is RAM "
                         f"state that a power cycle clears (default "
                         f"{DEFAULT_MAX_RESCUE_AGE:.0f}). 0 disables the bound")
    pu.add_argument("--expect-load", type=lambda s: int(s, 16), metavar="HEX",
                    help="the address you are going to give J. Checked against the load "
                         "address the rescue transcript recorded, so the number is the "
                         "loader's own echo rather than a memory")
    pu.add_argument("--yes", action="store_true",
                    help="required: this subcommand sends bytes the device acts on")
    pu.set_defaults(func=cmd_put)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
