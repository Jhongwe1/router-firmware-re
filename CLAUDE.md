# CLAUDE.md

TOTOLINK N150RT firmware RE — big-endian MIPS, Realtek SDK, Boa 0.94.14rc21.
**Three builds, not two:** V2.1.2 (2015), V3.4.0 (2020), and
**`TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002`** — read off this unit's own flash
and the only build the device actually runs. Its *version* is published; **this
build is not** (the published V2.1.6 is `B20160516`, eighteen months earlier and
without the `CX`). The repo labels it `unit-2018` after its binary timestamps,
which run seven weeks later than the version string — **always search the
version string, never the label**: that is how CVE-2024-51228, which names this
build, went unfound for two weeks. Repo tour: `README.md`. Current state:
`PROGRESS.md` — read the newest "Open, carried forward" and "Deliberately not
done" first. Nothing volatile is recorded here.

## The rule that outranks the others

The deliverable is not this repo; it is the author's ability to defend every
claim in it, unaided, **against a hostile reader**. **I build the instruments,
the author reads the dials** — extend `ghidra/scripts/*.java` and
`tools/fwrecon/`, never hand over a binary conclusion the author has not seen
the evidence for. When the author states a finding, do not agree: name the tool
that could be lying and the second source that settles it. Three times so far it
was the tool. Be blunt — agreeable understatement is how a claim reaches a
reader undefended.

## Evidence discipline

- **No claim from a single tool.** `readelf` and `nm -D` are not independent on
  an `sstrip`'d ELF; Ghidra and `nm -D` are.
- **A tool reporting `0` is a claim too.** Past instrument failures and how each
  was caught: `PROGRESS.md § Two tooling bugs`, `notes/sink-inventory.md`.
- **Read the builds across, not down.** One codebase a few years apart should
  track closely; wild divergence means suspect the instrument first. This is
  what caught three tracer bugs — 86 → 0 is not a code change.
- **A warning from the decompiler costs it the last word** — confirm at
  instruction level with `BoaListing.java`.
- **Measure before fixing, and make recovery scripts able to fail** (fixed
  stride, exactly-one match, else error). One that cannot fail proves nothing.
- **Negative results stay in place.** The wrong turns are the valuable part.
- **Name the binary a claim was measured on, or do not make the claim.** The
  device has been powered on since 2026-08-15 and G2 passed, but it runs a build
  neither W03 nor W04 read — so every existing `boa` finding describes V2.1.2 or
  V3.4.0 and **not this hardware**. G3.5 (W04-2) is what closes that.
- **Static ≠ dynamic.** Nothing has served a request yet. Until G4 the only
  permitted phrasing for behaviour is "the code reads as X", and behavioural
  notes carry a scope block naming what would confirm them.
- **Every Ghidra report names its input:** always pass `-Binary` to
  `analyze.ps1`, or `tools/check-reports.py` fails CI.

## Operating

- **The Bash tool is Git Bash, not WSL.** Dispatch the Linux side:
  `wsl -d Ubuntu-24.04 -- bash -lc 'cd /mnt/c/Users/Key20/Desktop/router && make verify'`
  (`-lc` matters — `binwalk` is in `~/.cargo/bin`).
- Binaries live in `$FWRE_WORK` = `/home/key/fwre-work`, never in the repo and
  never under `/mnt/c`: the findings are filesystem metadata
  (`docs/workspace-layout.md`).
- Ghidra: `import.ps1` once per label (minutes, cached), `analyze.ps1` per run
  (seconds). Never reason over pasted decompiler output — extend the script,
  regenerate the JSON, commit that.
- Never commit `*.web`, extracted trees, Ghidra project state, `ghidra/decomp/`.
  `plan/` and `archive/` are gitignored — read them, never quote them into
  committed files.

## House style

- **Write for an engineer, never for a hiring panel.** This repo is public and
  its readers are other engineers; a page that reads as a job application
  discounts the technical content sitting on it. So: **no résumé bullets, no
  interview soundbites, no "this proves I can X"** in anything committed —
  state the finding, name the artefact it was measured on, stop. The career
  goal is unchanged and *this is what serves it*: the reviewer worth impressing
  is an engineer first, and looking like you are selling is the fastest way to
  fail their read. `plan/` is gitignored and may address the author directly;
  committed files may not. `study/QA.md` is a design review of the repo's own
  claims — a hostile *reader*, not a hostile interviewer.
- English: `README`, `PROGRESS`, `notes/`, `docs/`, `tools/`, commits.
  Traditional Chinese: `LOG.md`, `RUNBOOK.md`, `study/QA.md`, `plan/`.
- A note answers a carried-forward question, gives the answer first with
  addresses, and ends with **how its first version was wrong**. Not optional.
- `RUNBOOK.md`, `PROGRESS.md` and the README board move in the **same commit**
  as the work; a ticked box carries its evidence link. Hostile questions go to
  `study/QA.md`. Week branches, never `main`.
- **Every week closes with a `study/weekly-results.md` entry** — the one-line
  version, three defensible claims each with its evidence and what it
  demonstrates, and **what that week did not prove**. The last of those three is
  the one that matters; a week whose "did not prove" section is empty has not
  been examined hard enough.
- `plan/` gates are authoritative; its dates and per-day schedules are not —
  W03/W04 ran before the hardware arrived, W02 landed two weeks late, and
  **W04-2 + G3.5 were added after the fact** because W02 found the unit runs a
  third build. When plan and image disagree the image wins, recorded in
  `PROGRESS.md § Corrections`.
