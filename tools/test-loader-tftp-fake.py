#!/usr/bin/env python3
"""A stand-in TFTP server for tools/test-loader-tftp.sh. Not a tool.

It exists so the client next door can be driven through every branch without the
router, and it is deliberately able to *misbehave*: a client whose tests only
ever meet a well-behaved peer has no evidence that its refusals fire.

The default behaviour copies what the loader actually did on 2026-08-17
(`BENCH-LOG.md` `T-09`): the reply comes from a **fresh ephemeral port**, and the
filename in the request is **ignored**. Both are load-bearing. A client that
expects the answer to come back from port 69 sees nothing at all.

  python3 tools/test-loader-tftp-fake.py --port 0 --serve-bytes 1500
"""

from __future__ import annotations

import argparse
import socket
import struct
import sys

OP_RRQ, OP_WRQ, OP_DATA, OP_ACK, OP_ERROR = 1, 2, 3, 4, 5
BLOCK = 512


def pattern(n: int) -> bytes:
    """Deterministic, non-repeating enough that a shifted copy is not equal."""
    return bytes((i * 7 + (i >> 8) * 31) & 0xFF for i in range(n))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=0,
                    help="0 lets the OS choose; the number is printed on stdout")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--serve-bytes", type=int, default=1500,
                    help="how much a read request is answered with")
    ap.add_argument("--file",
                    help="serve the contents of this file instead of the generated "
                         "pattern, so that the --attribute cases have bytes whose "
                         "position in a stand-in dump is known")
    ap.add_argument("--error", type=int,
                    help="answer every request with this ERROR code instead")
    ap.add_argument("--wrong-block", action="store_true",
                    help="skip a block number, to prove the client notices")
    ap.add_argument("--same-port", action="store_true",
                    help="reply from the request port, which the real loader "
                         "does not do; here to show the test would still pass "
                         "and therefore proves nothing on its own")
    ap.add_argument("--never-short", action="store_true",
                    help="never send a final short block, to drive --max-bytes")
    ap.add_argument("--capture", help="write an upload here")
    ap.add_argument("--drop-first", action="store_true",
                    help="ignore the first request, to drive the retransmit path")
    args = ap.parse_args(argv)

    listen = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen.bind((args.host, args.port))
    port = listen.getsockname()[1]
    print(port, flush=True)

    listen.settimeout(20.0)
    try:
        req, peer = listen.recvfrom(65535)
        if args.drop_first:
            req, peer = listen.recvfrom(65535)
    except TimeoutError:
        print("fake: no request arrived", file=sys.stderr)
        return 2

    # The transfer id: a *different* socket, so the reply comes from a different
    # port. This is the one thing about the real loader that breaks naive clients.
    work = listen if args.same_port else socket.socket(socket.AF_INET,
                                                       socket.SOCK_DGRAM)
    if work is not listen:
        work.bind((args.host, 0))
    work.settimeout(20.0)

    (op,) = struct.unpack_from("!H", req, 0)

    if args.error is not None:
        work.sendto(struct.pack("!HH", OP_ERROR, args.error) + b"nope\0", peer)
        return 0

    if op == OP_RRQ:
        if args.file:
            with open(args.file, "rb") as fh:
                data = fh.read()
        else:
            data = pattern(args.serve_bytes)
        number = 1
        offset = 0
        while True:
            chunk = data[offset:offset + BLOCK]
            sent_number = number + 1 if (args.wrong_block and number == 2) else number
            work.sendto(struct.pack("!HH", OP_DATA, sent_number & 0xFFFF) + chunk,
                        peer)
            if len(chunk) < BLOCK and not args.never_short:
                return 0
            if args.never_short and offset + BLOCK >= len(data):
                offset = 0                      # keep serving, never terminate
                data = pattern(args.serve_bytes)
            else:
                offset += BLOCK
            try:
                ack, _ = work.recvfrom(65535)
            except TimeoutError:
                return 0
            (aop,) = struct.unpack_from("!H", ack, 0)
            if aop != OP_ACK:
                return 3
            number += 1

    if op == OP_WRQ:
        work.sendto(struct.pack("!HH", OP_ACK, 0), peer)
        got = bytearray()
        while True:
            try:
                pkt, _ = work.recvfrom(65535)
            except TimeoutError:
                break
            (dop,) = struct.unpack_from("!H", pkt, 0)
            if dop != OP_DATA:
                return 4
            (blk,) = struct.unpack_from("!H", pkt, 2)
            payload = pkt[4:]
            got += payload
            work.sendto(struct.pack("!HH", OP_ACK, blk), peer)
            if len(payload) < BLOCK:
                break
        if args.capture:
            with open(args.capture, "wb") as fh:
                fh.write(got)
        return 0

    return 5


if __name__ == "__main__":
    sys.exit(main())
