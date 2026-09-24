# 11. Beyond the CVEs

The known advisories are a map of where other people have already looked. This
chapter is the part that was not driven by them.

## The method

Start from the **gate**, not from a CVE list. Chapter 13's `BoaGate.java` scores
three rules over a binary; rule R2 — *a request parameter reaches a shell* —
produces a list of call sites. Subtract the ones a published CVE already names.
What is left is the work list.

That is a different selection principle from "read the advisories and check
them", and it produces a different list, including entries in daemons nobody had
mentioned.

## The differential test bench, and why state is a file

The device is a single-process web server that dies if you look at it wrong
(below), so the throughput of a fuzzing campaign is not the constraint —
**recovery is**. What makes this tractable is that on this device the entire
mutable state is a region of flash, and this project has a byte-for-byte copy of
it. Recovery is a file copy plus a write, not a re-provisioning.

That property is what turns "one router" into "one router you can keep using".

## Twenty-four verdicts

The deliverable is [`notes/bughunt.md`](../notes/bughunt.md): twenty-four rows,
each pointing at a report under `reports/`. The two that arrived last are the
ones worth reproducing.

**`/bin/miniigd` terminates on any `NewInternalClient` that `inet_addr()`
rejects.** One unauthenticated UPnP SOAP request, and the daemon is gone until
someone cuts the power. The natural reading was CVE-2014-8361 — command
injection crashing rather than executing — and it is wrong. **The control
refutes it**: twenty-two `A` characters, no shell metacharacter anywhere, kill
it identically; a well-formed address is answered `200` and the daemon survives.
So the trigger is *any value `inet_addr()` rejects*, which is visible in the
device's own NAT table as `DNAT … to:255.255.255.255` — `INADDR_NONE` being used
as an address.

Three points define that line and any two of them support the wrong conclusion.
The third point cost one power cycle. Skipping it would have cost a disclosure
report naming the wrong CVE.

**And the command execution that same handler's code shape promises does not
happen on this build**, because the daemon dies first.

## Denial of service that outlives the request

An unauthenticated `POST` with **no parameters at all** holds the device's single
web server for four to ten seconds. About forty-five in sequence remove it until
someone cuts the power. `ping` keeps answering, the console prints nothing, and
nothing respawns `boa` — `rcS` starts it once.

And the one this project found by accident, in its own wreckage: an
unauthenticated POST round from week 5 had written `DHCP_MTU_SIZE=0` to flash,
and **this unit could not obtain a WAN address for two days** — through every
reboot, and through four bench sessions that had no reason to look.

The same round overwrote the **factory-default** configuration region with the
current one. So on this build, "restore factory defaults" would restore
whatever was last written — except that the reset button turns out to restore
from a **hard-coded table** instead, which is why the device came back
byte-for-byte to its week-2 state. That was tested rather than assumed, and the
distinction between `/bin/flash default` and `/bin/flash reset` is the whole of
it.

Nothing now starts a session without asking the device whether it can still
route.

## Two open ports nobody predicted

**52869** (`miniigd`, UPnP SOAP) and **52881** (`wscd`, WPS) are open and appear
in no prediction this project wrote. The UPnP daemon answers
`Server: miniupnpd/1.4` while **being `/bin/miniigd`** — a different project
with a different CVE history. A banner is a string, not an identification.

## The relatively safe areas

`notes/bughunt.md` carries a *relatively safe* section the same size as the
verdict table, and it exists because a bug hunt that only reports hits is a
biased sample. Where the code does bound a copy, or does validate a length, or
does escape output, it says so with the address.

## Three of this project's own findings, withdrawn

Three entries were removed after being written up, and one of them turned out to
have a CVE against it already. The withdrawals are in the file next to the
findings rather than deleted.

The last thing this hunt found was not in the firmware: **six committed files,
one of them the disclosure register, asserted `52869/tcp open` in the present
tense**, sourced to a sweep from one date — while the same repository recorded
the port **closed** two days later, because this project's own POST round had
disabled the daemon. Both readings were right when taken. Neither sentence
carried a date. They all do now.

> **Where this chapter stops:** twenty-four verdicts on one unit, one build.
> The wireless surface is not in them — a monitor-mode injection adapter does
> not exist in this lab, and two rows sit unmeasured with that written against
> them rather than quietly dropped. Chapter 14.
