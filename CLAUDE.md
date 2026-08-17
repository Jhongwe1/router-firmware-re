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

## Starting a week — two files, both required

When the author says **"let's do W05"** (or W06 / W07 — anything of the form
*finish week N*), **read both of these.** They answer different questions and
neither substitutes for the other.

**1. `plan/W0N_*.md` — how the week runs.** The day-by-day ordering, the actual
commands, the timeboxes and stop-losses, the DoD, and the week's technical
argument. **Nothing else in the repository records any of that**, so skipping it
means inventing an order and re-deriving commands that are already written.
Read it first.

**2. `make todo WEEK=W05` — what the week owes.**

```bash
make todo WEEK=W05        # -> tools/rtcase.py todo, reads test-cases.toml
```

Every registered test scheduled for that week and still outstanding — 31 for
W05, 25 for W06, 60 for W07 — with its section and title. The same schedule is
the top block of `test-ledger.md`, and `make ci` prints the per-week
outstanding counts on every run. **This is the closure list**: a week is not
finished while its rows are still `⬜`, and that is checkable in one command.

**Where the two disagree — and they do.** The plan's **gates** are
authoritative; its **status claims, dates and preconditions** are not.
`plan/W05` still asserts "G3.5 passed" when it is 4 of 5, and its risk table
says the `FLW` drill was rehearsed when it has not been. Check any precondition
against `PROGRESS.md` and the README board before acting on it, and record the
divergence in `PROGRESS.md § Corrections` rather than silently editing either
file.

Then: run each test, record it with `python3 tools/rtcase.py record --id … `
(it refuses a case with no pre-written refutation condition), and
`make ledger`. Procedure with worked examples: `RUNBOOK.md` §8.10.
**Do not write test outcomes into prose in `PROGRESS.md`** — that file owns
gates and weeks, not individual tests.

Nine items were deliberately cut, each with its reason in the register. Do not
quietly reinstate one; if a cut looks wrong, argue with the reason first.

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

## Bench sessions — W06 and W07 have one every week

- **Procedure lives in `RUNBOOK.md` §8.12**, cut into composable sub-sections. A
  week is *which sections, in what order, plus its own extra steps* — **never a
  new `W0N-bench-runsheet.md`.** W05 opened one; 580 of its 1,091 lines were
  reusable procedure, and a second copy would be one state with two owners.
- **What was actually run goes in `BENCH-LOG.md`** (repo root, append-only): the
  session's plan written *before* touching anything, then verbatim excerpts, what
  each step burned, and what is next.
- **Because that record is verbatim, §8.12 may be refined freely** — the evidence
  does not depend on the procedure document still saying what it said.
- Verdicts and evidence links stay owned by `test-cases.toml`, unchanged.

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
- **One piece of state has exactly one owner.** `PROGRESS.md` owns gates, weeks
  and carried-forward questions; `test-cases.toml` owns per-test
  prediction / refutation / result / evidence; the README board owns the gate
  checkboxes and one line of numbers. A gate may **cite** a test, never restate
  its row. This rule exists because the 2026-08-16 sync failure was one piece of
  state with two owners, and a 130-row matrix in two files would repeat it
  weekly. `test-ledger.md` is **generated** — edit the register.
- **A test result is inadmissible without a refutation condition written
  first**, and `tools/rtcase.py check` enforces it in CI along with: an artefact
  that exists, no dynamic tick for a static reading, and no editing a prediction
  after a result was recorded against it. `tools/test-rtcase.sh` proves each
  refusal fires; both run in `make ci`.
- **Findings are published, reproductions follow the disclosure state,
  tradecraft is not published at all.** Naming a defect and its address is
  research; a copy-pasteable request for something unreported is not.
  `docs/disclosure.md` holds the register and the current state of each item.
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
