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
TFTP's reply comes from a **fresh ephemeral port**, not from 69 — the bench saw
``:2098``. Everything after the first packet is addressed to that port. A client
that filters on 69 sees nothing and reports the service as dead, and a firewall
rule written for 69 alone does the same. So: the peer **address** is pinned and
checked on every packet; the peer **port** is learned from the first reply and
pinned from then on.

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
          f"ignores it (2026-08-17), so a name that exists nowhere still "
          f"returns data -- which means a reply here says the service answers, "
          f"not that the file was found")
    _report(args, {"op": "probe", "host": host, "tid": sess.tid,
                   "filename": args.filename, "bytes": len(data),
                   "blocks": blocks, "sha256": digest,
                   "retransmits": sess.retransmits})
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
    _report(args, {"op": "get", "host": host, "tid": sess.tid,
                   "filename": args.filename, "output": args.output,
                   "bytes": len(data), "blocks": blocks, "sha256": digest,
                   "seconds": round(elapsed, 3), "retransmits": sess.retransmits})
    return 0


def check_rescue_report(path: str, host: str) -> dict:
    """The evidence `put` requires, because this tool cannot see the console.

    `console-dump.py rescue` sends `AUTOBURN 0`, refuses to continue unless the
    loader echoes `AutoBurning=0`, and writes what it sent and saw. That file is
    the only thing standing between an upload that lands in RAM and an upload
    that is written to flash, so it is parsed here rather than trusted: the
    right host, and the right echo, or nothing is sent.
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
    return rep


def cmd_put(args) -> int:
    host = check_host(args.host)
    rep = check_rescue_report(args.rescue_report, host)
    print(f"  ok    rescue transcript for {host} shows AutoBurning=0")
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

    pp = sub.add_parser("probe", help="one read request, first block only, "
                                      "nothing written")
    common(pp)
    pp.add_argument("--filename", default="probe",
                    help="ignored by this loader; sent anyway (default: probe)")
    pp.set_defaults(func=cmd_probe)

    pg = sub.add_parser("get", help="read the loader's memory to a file")
    common(pg)
    pg.add_argument("--filename", default="ram", help="ignored by this loader")
    pg.add_argument("-o", "--output", required=True)
    pg.add_argument("--force", action="store_true",
                    help="overwrite an existing output file")
    pg.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES,
                    help=f"stop rather than run on (default {DEFAULT_MAX_BYTES})")
    pg.set_defaults(func=cmd_get)

    pu = sub.add_parser("put", help="upload an image into the loader's RAM")
    common(pu)
    pu.add_argument("--filename", default="image", help="ignored by this loader")
    pu.add_argument("--image", required=True)
    pu.add_argument("--rescue-report", required=True,
                    help="the JSON console-dump.py rescue wrote; it must show "
                         "AutoBurning=0 for this same host")
    pu.add_argument("--yes", action="store_true",
                    help="required: this subcommand sends bytes the device acts on")
    pu.set_defaults(func=cmd_put)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
