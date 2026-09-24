# `notes/` — every reading, indexed

Forty notes. Each one answers a question that was carried forward, gives the
answer first with addresses, and ends with **how its first version was wrong**.
That last section is not optional here and it is the reason these are worth
reading rather than skimming.

**This index exists because twelve of them were reachable from nothing.** The
`README` listed a subset in a forty-row table that was long enough not to be
read and still incomplete — including
[`uninit-credential-pair.md`](uninit-credential-pair.md), which is the most
likely original finding in the project. A file nobody can navigate to is a file
that was not written.

## Read these four first

| | |
|---|---|
| [`uart-findings.md`](uart-findings.md) | **The build nobody had.** What the boot log says, and what that costs every static reading taken before it |
| [`dump-vs-official.md`](dump-vs-official.md) | **The 4 MiB dump against the published images** — a five-year vendor remediation caught mid-step |
| [`uninit-credential-pair.md`](uninit-credential-pair.md) | **Two credential pairs, and nothing ever writes the second.** An empty user name and an empty password compare successfully and skip the authorisation block. 2015 yes, 2018 yes, 2020 gone |
| [`three-way-read.md`](three-way-read.md) | 2015, 2018, 2020 side by side — which conclusions transferred and which did not |

## The hardware

| | |
|---|---|
| [`hardware-inspection.md`](hardware-inspection.md) | The five ICs, the 4 MiB flash W01 predicted, and a second-source column that is still partly empty |
| [`uart-pinout.md`](uart-pinout.md) | Pin-out with two sources per pin, baud measured from pulse width, and why the console gives no shell |
| [`flash-layout.md`](flash-layout.md) | The flash map read off the device — W01's three predicted burn addresses, all three hit |
| [`loader-chip-table.md`](loader-chip-table.md) | Why this unit boots from a part its own boot loader cannot name |
| [`loader-tftp-and-commands.md`](loader-tftp-and-commands.md) | What the loader serves over TFTP, and from where |
| [`loader-interrupts-and-console.md`](loader-interrupts-and-console.md) | The loader's interrupts, and the prompt that is not a prompt — including a reading that concluded the exact opposite from correct observations |

## How the firmware is built

| | |
|---|---|
| [`anatomy-n150rt.md`](anatomy-n150rt.md) | Container format, flash map, binaries, mitigations |
| [`dispatch-table.md`](dispatch-table.md) | `root_form[]` recovered — every `/boafrm/` route, and what changed between builds |
| [`mib-and-config-dat.md`](mib-and-config-dat.md) | The MIB table, and what `config.dat` actually is |
| [`compcs-decode.md`](compcs-decode.md) | The configuration region decoded — CVE-2019-19823 from a citation to an address |
| [`wlan-root.md`](wlan-root.md) | `WLAN_ROOT`: the other half of the configuration, which nothing had decoded |
| [`w6cg-web-ui.md`](w6cg-web-ui.md) | The shipped web UI, read across three builds |
| [`emulation-2018.md`](emulation-2018.md) | Emulating the resident build — what the dump turned into, and what it cost |

## Authentication and authorisation

| | |
|---|---|
| [`auth-flow-2018.md`](auth-flow-2018.md) | **How the build on this unit decides you are allowed in.** The one that describes this hardware |
| [`auth-flow.md`](auth-flow.md) | The same read on the published 2015 build |
| [`auth-flow-2020.md`](auth-flow-2020.md) | …and on the published 2020 build |
| [`uninit-credential-pair.md`](uninit-credential-pair.md) | The second credential pair, never written |
| [`auth-session-ip.md`](auth-session-ip.md) | The session is keyed on the source IP address, and it expires after ten minutes |
| [`credentials.md`](credentials.md) | Where the credentials actually are |
| [`password-page-credentials.md`](password-page-credentials.md) | `password.htm` hands the client the plaintext credentials by SSI — and only this build does |
| [`config-failopen.md`](config-failopen.md) | When both settings regions are invalid, the boot script turns telnet on |

## Where input reaches something dangerous

| | |
|---|---|
| [`sink-inventory.md`](sink-inventory.md) | Where user input can reach a shell or a fixed buffer |
| [`submit-url-overflow.md`](submit-url-overflow.md) | `submit-url`: four CVEs, one idiom, thirty-odd handlers |
| [`absent-parameter-strcpy.md`](absent-parameter-strcpy.md) | The absent parameter, the read-only literal, and the one that gives you `$pc` — corrected twice, sharper each time |
| [`formSysCmd-analysis.md`](formSysCmd-analysis.md) | **A negative result**, kept |
| [`skt-analysis.md`](skt-analysis.md) | `/bin/skt` — the 2015 backdoor, decoded |
| [`three-unread-binaries.md`](three-unread-binaries.md) | `/bin/auth`, `/bin/miniigd`, `/bin/dnsspoof` — the three nobody had read |
| [`firmware-upgrade-path.md`](firmware-upgrade-path.md) | What this build checks before writing a firmware image: an unkeyed additive sum, over plain HTTP, from a hard-coded host |
| [`mips-ret2libc.md`](mips-ret2libc.md) | Where uClibc is mapped on this unit, read off two console lines |
| [`host-header-and-redirect.md`](host-header-and-redirect.md) | `check_host` is present, correct, and unreachable |
| [`xss-escaping.md`](xss-escaping.md) | The escaper exists, it is correct, and only Boa's own pages call it |

## Method, triage and status

| | |
|---|---|
| [`bughunt.md`](bughunt.md) | The systematic hunt — twenty-four verdicts, each pointing at a file under [`../reports/`](../reports/) |
| [`cve-status.md`](cve-status.md) | Per-CVE against the build this unit runs: five located in its own binary, two refuted by it, two endpoint names that exist in no dispatch table |
| [`prior-art.md`](prior-art.md) | Who disclosed what, and when — and which of this project's claims survived contact with it |
| [`attack-surface.md`](attack-surface.md) | Where to look, ranked |
| [`ghidra-triage.md`](ghidra-triage.md) | Which functions to open first, with the three W01 calls W03 overturned |
| [`oracle-design.md`](oracle-design.md) | Observation channels for a blind injection — five oracles, four rehearsed |
| [`img/`](img/) | Board photographs, the annotation spec they render from, and what had to be painted out before publication |

## A note on scope

Several of these were written in W03 and W04, **before this unit was opened**,
and describe the two published images rather than the build in its flash. They
carry a scope block saying so and pointing at the resident-build equivalent.
[`tools/check-expired.py`](../tools/check-expired.py) exists because that block
was wrong in eight of them for six weeks: they still said *"no device has been
powered on"* about a device that had been serving since 2026-08-15.
