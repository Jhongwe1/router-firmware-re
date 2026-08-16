#!/usr/bin/env python3
"""The test register: predictions frozen before the packet, results carrying evidence.

W05-W07 run on the order of 130 individual tests against one device. Kept as a
hand-maintained table, that goes wrong in two specific ways, both of which this
project has already had:

  * **The same state ends up owned by two files and they drift.** PROGRESS.md
    records that happening on 2026-08-16 - a "document sync" commit that ran
    before the week's last two commits and was never re-run - in the same week
    the rule against it was rewritten. A 130-row matrix duplicated into
    PROGRESS.md and README.md would drift by Wednesday.
  * **A test with no pre-written failure condition is read as a success
    afterwards.** By the time the response arrives, the reader knows what they
    wanted to see. The only defence is to write down what "it did not work"
    looks like *before* sending anything, and to make it impossible to record a
    result for a test that has no such line.

So: `study/test-cases.toml` is the single owner of per-test state, this script
is the only thing that writes the readable form of it, and `check` is a CI gate.

What the gate enforces, and why each one exists
-----------------------------------------------

  freeze          The `predict` and `refute` fields of every case that has one
                  are hashed into `[freeze].sha256`. Editing a prediction after
                  the fact therefore requires editing the hash in the same
                  commit, where `git diff` shows it as two deliberate lines
                  rather than one quiet one. This is not tamper-proofing - the
                  author holds the key - it is the difference between a change
                  that is visible and one that is not.

  refute-first    A result may not be recorded for a case whose `refute` is
                  empty. This is the rule above, made mechanical.

  evidence        A `confirmed` or `partial` verdict must name at least one
                  artefact, and every named artefact must exist. Same rule as
                  `check-reports.py` applies to Ghidra output: a result that
                  cannot name what it was measured on is not evidence.

  static-vs-dynamic
                  `evidence_kind` is recorded per result and the renderer will
                  not print the dynamic marker for a static one. CLAUDE.md's
                  "static != dynamic" stops being a habit and becomes a column
                  that cannot be left ambiguous.

  cut-with-reason A case may be dropped, but `cut_reason` must say why, and a
                  cut case may not carry a result. Six months later, a removed
                  row and an overlooked row are indistinguishable; a row with a
                  reason is a decision a reader can argue with.

  the control     If *no* case carries a refutation, the freeze check passes
                  vacuously and proves nothing - the shape of instrument bug 12,
                  where dropping an override took a count to 0 with the
                  self-check still reporting `consistent`. An empty freeze set
                  is therefore a hard failure, not a quiet pass.

Every string a reader sees comes from the register, not from this file. That is
not tidiness: the register is written in Traditional Chinese per the repository's
language split, and a tool that hardcodes its output language cannot render a
second register without being edited.

Usage:
  python3 tools/rtcase.py check    [register]      # the CI gate
  python3 tools/rtcase.py render   [register]      # regenerate the ledger
  python3 tools/rtcase.py freeze   [register]      # print the hash to paste in
  python3 tools/rtcase.py stats    [register]      # one line, for README
  python3 tools/rtcase.py record --id P3-3 --verdict confirmed \\
        --evidence dynamic --date 2026-08-20 --artefact poc/formSysCmd.md \\
        --note "..."                               # append a result

Python 3.11+ (tomllib). No third-party dependencies, for the same reason
fwrecon has none: a result should be reproducible from a bare interpreter.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - the message is the point
    raise SystemExit(
        "rtcase needs Python 3.11+ for tomllib; the venv under $FWRE_WORK has it"
    ) from None

REPO = Path(__file__).resolve().parent.parent
DEFAULT_REGISTER = REPO / "study/test-cases.toml"
DEFAULT_RESULTS = REPO / "reports/test-results.json"

SCHEMA_VERSION = "1"

# The evidence grade a case carried when the register was written - "what was
# known before anything was sent". Deliberately a different axis from a result.
# The marks live here; what each one *means* is written in the register, in
# whatever language the register is written in.
EXIT_MARKS = {
    "dynamic": "✅",
    "static": "\U0001f7e5",
    "other-build": "\U0001f7e7",
    "presumed": "\U0001f7e8",
    "unverified": "\U0001f7e6",
    "refuted": "❌",
    "none": "—",
}

VERDICT_MARKS = {
    "confirmed": "✅",
    "refuted": "❌",
    "partial": "\U0001f536",
    "na": "⬛",
}
TODO_MARK = "⬜"
# A confirmed-by-static-reading result is not the dynamic tick. This is the one
# place a skimming reader sees the difference, so it gets its own mark rather
# than a footnote.
STATIC_CONFIRMED_MARK = EXIT_MARKS["static"]

EVIDENCE_KINDS = ("static", "dynamic")

REQUIRED_CASE_FIELDS = ("id", "phase", "section", "title", "feasibility", "exit_evidence", "week")

# Fallbacks only. A register that leaves these out renders in English rather
# than crashing, which is what makes the tool reusable for a second target.
DEFAULT_TEXT = {
    "stats_heading": "Statistics",
    "stats_registered": "registered",
    "stats_registered_value": "**{total}** ({live} scheduled, {cut} cut)",
    "stats_frozen": "with a refutation condition (frozen)",
    "stats_frozen_value": "**{frozen}** / {live}",
    "stats_executed": "executed",
    "stats_dynamic": "closed on dynamic evidence",
    "stats_verdicts": "confirmed / refuted",
    "stats_freeze": "freeze hash",
    "schedule_heading": "Schedule",
    "schedule_intro": "",
    "schedule_header": "| week | phases | done | |",
    "legend_heading": "Legend",
    "legend_header": "| exit evidence | | | result | |",
    "table_header": "| ID | item | section | feasibility | exit | week | result | evidence |",
    "details_summary": "predictions and refutation conditions ({n}/{total} frozen)",
    "predict_label": "predicts",
    "refute_label": "refuted by",
    "runs_suffix": " x{n}",
    "missing_refute": "> {n} case(s) here have no refutation condition yet: {ids}",
    "id_join": ", ",
    "cut_heading": "Cut, with reasons",
    "cut_intro": "",
    "cut_header": "| ID | item | section | why not |",
    "todo": "todo",
    "generated_banner": "<!-- GENERATED by tools/rtcase.py render -->",
}


def text(ledger: dict[str, Any], key: str) -> str:
    return str(ledger.get("text", {}).get(key, DEFAULT_TEXT[key]))


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------


def load_register(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except FileNotFoundError:
        raise SystemExit(f"no register at {path}") from None
    except tomllib.TOMLDecodeError as exc:
        raise SystemExit(f"{path}: {exc}") from None


def load_results(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"producer": "rtcase", "schema_version": SCHEMA_VERSION, "results": []}
    return json.loads(path.read_text("utf-8"))


def freeze_payload(cases: list[dict[str, Any]]) -> bytes:
    """Canonical bytes over the fields that must not move after the freeze.

    Sorted by id so that reordering the register - which is presentation - does
    not read as tampering, while editing a single character of a prediction
    does.
    """
    frozen = sorted(
        (c["id"], c.get("predict", ""), c.get("refute", ""))
        for c in cases
        if c.get("refute", "").strip()
    )
    return json.dumps(frozen, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def freeze_hash(cases: list[dict[str, Any]]) -> str:
    return hashlib.sha256(freeze_payload(cases)).hexdigest()


def case_freeze(case: dict[str, Any]) -> str:
    """Per-case hash of the frozen fields, stamped onto each result.

    The register-wide hash cannot do this job: adding a new case changes it, so
    every earlier result would look tampered with. This one changes only when
    *this* case's prediction or refutation changes - which, once a result has
    been recorded against them, is exactly the event worth catching.
    """
    payload = json.dumps(
        [case.get("id", ""), case.get("predict", ""), case.get("refute", "")],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def is_cut(case: dict[str, Any]) -> bool:
    return bool(str(case.get("cut_reason", "")).strip())


# --------------------------------------------------------------------------
# check
# --------------------------------------------------------------------------


def check(register_path: Path, results_path: Path) -> int:
    doc = load_register(register_path)
    cases: list[dict[str, Any]] = doc.get("case", [])
    errors: list[str] = []
    warnings: list[str] = []

    if doc.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            f"register schema_version is {doc.get('schema_version')!r}, this script emits "
            f"{SCHEMA_VERSION!r}"
        )
    if not cases:
        errors.append("register holds no cases")

    seen: set[str] = set()
    phases = {str(p) for p in doc.get("ledger", {}).get("phase_titles", {})}
    for case in cases:
        cid = case.get("id", "<no id>")
        for field in REQUIRED_CASE_FIELDS:
            if not case.get(field) and case.get(field) != 0:
                errors.append(f"{cid}: missing required field {field!r}")
        if cid in seen:
            errors.append(f"{cid}: duplicate id")
        seen.add(cid)
        feas = case.get("feasibility")
        if not isinstance(feas, int) or not 1 <= feas <= 5:
            errors.append(f"{cid}: feasibility is {feas!r}, must be an int 1-5")
        if case.get("exit_evidence") not in EXIT_MARKS:
            errors.append(
                f"{cid}: exit_evidence is {case.get('exit_evidence')!r}, "
                f"must be one of {sorted(EXIT_MARKS)}"
            )
        if phases and str(case.get("phase")) not in phases:
            errors.append(f"{cid}: phase {case.get('phase')!r} has no title in [ledger]")
        if (
            case.get("predict", "").strip()
            and not case.get("refute", "").strip()
            and not is_cut(case)
        ):
            warnings.append(f"{cid}: has a prediction but no refutation condition")
        if "cut_reason" in case and not is_cut(case):
            errors.append(f"{cid}: cut_reason is present but empty")

    # The control. If nothing is frozen the freeze check below compares two
    # hashes of an empty list and passes, which is instrument bug 12 exactly: a
    # check that only fires when it has something to work on, reporting success
    # when it has nothing.
    frozen_count = sum(1 for c in cases if c.get("refute", "").strip())
    if cases and frozen_count == 0:
        errors.append(
            "no case carries a refutation condition, so the freeze check would pass "
            "over an empty set and prove nothing"
        )

    declared = str(doc.get("freeze", {}).get("sha256", ""))
    actual = freeze_hash(cases)
    if declared != actual:
        errors.append(
            f"freeze mismatch: register declares {declared[:16] or '<empty>'}..., "
            f"the predictions hash to {actual[:16]}...\n"
            "       If you changed a prediction on purpose, put the new hash in "
            "[freeze].sha256 in the same commit - `python3 tools/rtcase.py freeze` "
            "prints it - so the change shows up in the diff instead of passing quietly."
        )

    results_doc = load_results(results_path)
    if results_doc.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            f"{results_path.name}: schema_version is {results_doc.get('schema_version')!r}"
        )
    by_id = {c["id"]: c for c in cases if "id" in c}
    for res in results_doc.get("results", []):
        rid = res.get("id", "<no id>")
        case = by_id.get(rid)
        if case is None:
            errors.append(f"{results_path.name}: result for unknown case {rid!r}")
            continue
        if is_cut(case):
            errors.append(
                f"{rid}: a result is recorded for a case that was cut. Either the cut was "
                "wrong and cut_reason should go, or this result should not exist"
            )
        if res.get("verdict") not in VERDICT_MARKS:
            errors.append(
                f"{rid}: verdict is {res.get('verdict')!r}, must be one of {sorted(VERDICT_MARKS)}"
            )
        if res.get("evidence_kind") not in EVIDENCE_KINDS:
            errors.append(
                f"{rid}: evidence_kind is {res.get('evidence_kind')!r}, "
                f"must be one of {EVIDENCE_KINDS}"
            )
        if not res.get("date"):
            errors.append(f"{rid}: result has no date")
        # The rule this whole file exists for.
        if not case.get("refute", "").strip():
            errors.append(
                f"{rid}: a result is recorded but the case has no refutation condition. "
                "Write what failure looks like first, or the result is unfalsifiable"
            )
        # The prediction this result was judged against must still say what it
        # said at the time. Refining a refutation after seeing the answer is the
        # single most natural way to launder a miss into a hit, and it leaves no
        # other trace: the register reads consistently afterwards.
        stamped = res.get("case_freeze_sha256")
        if not stamped:
            errors.append(
                f"{rid}: result carries no case_freeze_sha256. Record results with "
                "`rtcase record`, which stamps the prediction the result was judged against"
            )
        elif stamped != case_freeze(case):
            errors.append(
                f"{rid}: this case's prediction or refutation has been edited since the "
                f"result was recorded (stamped {str(stamped)[:16]}..., now "
                f"{case_freeze(case)[:16]}...). Either restore the wording, or update the "
                "stamp in the same commit so the diff shows what was changed after the fact"
            )
        artefacts = res.get("artefacts", [])
        if res.get("verdict") in ("confirmed", "partial") and not artefacts:
            errors.append(
                f"{rid}: verdict {res['verdict']!r} with no artefact - a result that cannot "
                "name what it was measured on is not evidence"
            )
        for art in artefacts:
            if not (REPO / art).exists():
                errors.append(f"{rid}: artefact {art!r} does not exist in the working tree")

    if warnings:
        print(f"{len(warnings)} case(s) predict without a refutation condition:", file=sys.stderr)
        for w in warnings[:10]:
            print(f"  warn  {w}", file=sys.stderr)
        if len(warnings) > 10:
            print(f"  warn  ... and {len(warnings) - 10} more", file=sys.stderr)
        print(
            "  (not an error: a case may be written up before its failure condition is. "
            "It becomes an error the moment a result is recorded for it.)",
            file=sys.stderr,
        )

    if errors:
        for e in errors:
            print(f"  FAIL  {e}", file=sys.stderr)
        return 1

    executed = len({r["id"] for r in results_doc.get("results", [])})
    print(
        f"register OK - {len(cases)} cases, {frozen_count} frozen, {executed} executed, "
        f"freeze {actual[:16]}..."
    )
    # Printed on every `make ci`, so the schedule is in front of whoever is
    # working rather than in a file they have to remember to open.
    summary = week_summary(cases, latest_results(results_doc))
    outstanding = [(w, s) for w, s in sorted(summary.items()) if s["todo"]]
    if outstanding:
        print(
            "  outstanding: "
            + "  ".join(f"{w} {s['done']}/{s['total']}" for w, s in outstanding)
            + "   (`rtcase todo --week W05` lists them)"
        )
    return 0


# --------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------


def latest_results(results_doc: dict[str, Any]) -> dict[str, tuple[dict[str, Any], int]]:
    """Latest result per case id, with how many times that case has been run."""
    out: dict[str, tuple[dict[str, Any], int]] = {}
    ordered = sorted(
        results_doc.get("results", []), key=lambda r: (r.get("date", ""), str(r.get("id")))
    )
    for res in ordered:
        rid = res.get("id")
        count = out[rid][1] + 1 if rid in out else 1
        out[rid] = (res, count)
    return out


def verdict_cell(ledger: dict[str, Any], res: dict[str, Any] | None, runs: int) -> str:
    if res is None:
        return TODO_MARK
    mark = VERDICT_MARKS.get(res.get("verdict", ""), "?")
    if res.get("verdict") == "confirmed" and res.get("evidence_kind") == "static":
        mark = STATIC_CONFIRMED_MARK
    suffix = text(ledger, "runs_suffix").format(n=runs) if runs > 1 else ""
    return f"{mark}{suffix}"


def _rel(from_file: Path, target: str) -> str:
    """Link target relative to the rendered file, so the ledger works on GitHub."""
    return os.path.relpath(REPO / target, from_file.parent).replace("\\", "/")


def render(register_path: Path, results_path: Path) -> int:
    doc = load_register(register_path)
    cases: list[dict[str, Any]] = doc.get("case", [])
    ledger = doc.get("ledger", {})
    latest = latest_results(load_results(results_path))

    out_path = REPO / ledger.get("output", "study/test-ledger.md")
    phase_titles: dict[str, str] = {str(k): v for k, v in ledger.get("phase_titles", {}).items()}
    ev_labels: dict[str, str] = ledger.get("evidence_labels", {})
    vd_labels: dict[str, str] = ledger.get("verdict_labels", {})

    live = [c for c in cases if not is_cut(c)]
    cut = [c for c in cases if is_cut(c)]
    frozen = sum(1 for c in cases if c.get("refute", "").strip())
    executed = len(latest)
    confirmed = sum(1 for r, _ in latest.values() if r.get("verdict") == "confirmed")
    refuted = sum(1 for r, _ in latest.values() if r.get("verdict") == "refuted")
    dynamic = sum(1 for r, _ in latest.values() if r.get("evidence_kind") == "dynamic")

    out: list[str] = []
    add = out.append
    add(f"# {ledger.get('title', 'test register')}")
    add("")
    add(text(ledger, "generated_banner"))
    add("")
    add(str(ledger.get("preamble", "")).strip())
    add("")

    add(f"## {text(ledger, 'stats_heading')}")
    add("")
    add("| | |")
    add("|---|---|")
    add(
        f"| {text(ledger, 'stats_registered')} | "
        + text(ledger, "stats_registered_value").format(
            total=len(cases), live=len(live), cut=len(cut)
        )
        + " |"
    )
    add(
        f"| {text(ledger, 'stats_frozen')} | "
        + text(ledger, "stats_frozen_value").format(frozen=frozen, live=len(live))
        + " |"
    )
    add(f"| {text(ledger, 'stats_executed')} | **{executed}** |")
    add(f"| {text(ledger, 'stats_dynamic')} | **{dynamic}** |")
    add(f"| {text(ledger, 'stats_verdicts')} | **{confirmed}** / **{refuted}** |")
    add(f"| {text(ledger, 'stats_freeze')} | `{freeze_hash(cases)}` |")
    add("")

    # The schedule, at the top, where opening the file is enough. The `week`
    # field is data and nothing executes it; this table is what makes "W07 is
    # done" a checkable statement rather than an impression.
    summary = week_summary(cases, latest)
    if summary:
        add(f"## {text(ledger, 'schedule_heading')}")
        add("")
        intro = text(ledger, "schedule_intro").strip()
        if intro:
            add(intro)
            add("")
        add(text(ledger, "schedule_header"))
        add("|---|---|---|---|")
        for w in sorted(summary):
            s = summary[w]
            phases = sorted(
                {str(c["phase"]) for c in live if str(c.get("week")) == w}, key=int
            )
            bar = "▰" * round(10 * s["done"] / s["total"]) + "▱" * (
                10 - round(10 * s["done"] / s["total"])
            )
            add(
                f"| **{w}** | Phase {', '.join(phases)} | {s['done']} / {s['total']} "
                f"| `{bar}` |"
            )
        add("")

    add(f"## {text(ledger, 'legend_heading')}")
    add("")
    add(text(ledger, "legend_header"))
    add("|---|---|---|---|---|")
    right = [
        (TODO_MARK, vd_labels.get("todo", text(ledger, "todo"))),
        (VERDICT_MARKS["confirmed"], vd_labels.get("confirmed", "")),
        (STATIC_CONFIRMED_MARK, vd_labels.get("static_confirmed", "")),
        (VERDICT_MARKS["refuted"], vd_labels.get("refuted", "")),
        (VERDICT_MARKS["partial"], vd_labels.get("partial", "")),
        (VERDICT_MARKS["na"], vd_labels.get("na", "")),
        ("", ""),
    ]
    for i, (key, mark) in enumerate(EXIT_MARKS.items()):
        r_mark, r_label = right[i] if i < len(right) else ("", "")
        add(f"| {mark} | {ev_labels.get(key, key)} | | {r_mark} | {r_label} |")
    add("")

    for phase in sorted(phase_titles, key=lambda p: (len(p), p)):
        in_phase = [c for c in live if str(c.get("phase")) == phase]
        if not in_phase:
            continue
        add(f"## {phase_titles[phase]}")
        add("")
        add(text(ledger, "table_header"))
        add("|---|---|---|---|---|---|---|---|")
        for c in in_phase:
            res, runs = latest.get(c["id"], (None, 0))
            stars = "★" * c["feasibility"] + "☆" * (5 - c["feasibility"])
            arts = "—"
            if res and res.get("artefacts"):
                arts = " · ".join(
                    f"[{Path(a).name}]({_rel(out_path, a)})" for a in res["artefacts"]
                )
            note = f" {res['note']}" if res and res.get("note") else ""
            cid = f"**{c['id']}**" if c.get("star") else c["id"]
            add(
                f"| {cid} | {c['title']} | {c['section']} | {stars} "
                f"| {EXIT_MARKS[c['exit_evidence']]} | {c['week']} "
                f"| {verdict_cell(ledger, res, runs)}{note} | {arts} |"
            )
        add("")

        predicted = [c for c in in_phase if c.get("refute", "").strip()]
        if predicted:
            summary = text(ledger, "details_summary").format(
                phase=phase, n=len(predicted), total=len(in_phase)
            )
            add(f"<details><summary>{summary}</summary>")
            add("")
            for c in predicted:
                add(f"**{c['id']} — {c['title']}**")
                add("")
                if str(c.get("caution", "")).strip():
                    add(f"- ⚠️ **{c['caution'].strip()}**")
                if str(c.get("predict", "")).strip():
                    add(f"- {text(ledger, 'predict_label')}{c['predict'].strip()}")
                add(f"- **{text(ledger, 'refute_label')}{c['refute'].strip()}**")
                add("")
            add("</details>")
            add("")

        for c in [c for c in in_phase if str(c.get("caution", "")).strip() and c not in predicted]:
            add(f"> ⚠️ **{c['id']}** — {c['caution'].strip()}")
            add("")

        missing = [c for c in in_phase if not c.get("refute", "").strip()]
        if missing:
            ids = text(ledger, "id_join").join(f"`{c['id']}`" for c in missing)
            add(text(ledger, "missing_refute").format(n=len(missing), ids=ids))
            add("")

    if cut:
        # Kept in the ledger rather than deleted from it. A removed row reads as
        # "never considered"; a row with a reason reads as a decision, and the
        # reason is the part a reader can argue with.
        add(f"## {text(ledger, 'cut_heading')}")
        add("")
        intro = text(ledger, "cut_intro").strip()
        if intro:
            add(intro)
            add("")
        add(text(ledger, "cut_header"))
        add("|---|---|---|---|")
        for c in cut:
            add(f"| {c['id']} | {c['title']} | {c['section']} | {c['cut_reason'].strip()} |")
        add("")

    add(str(ledger.get("postamble", "")).strip())
    add("")
    out_path.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {out_path.relative_to(REPO)} - {len(cases)} cases, {executed} executed")
    return 0


# --------------------------------------------------------------------------
# record
# --------------------------------------------------------------------------


def record(args: argparse.Namespace) -> int:
    register_path = Path(args.register)
    results_path = Path(args.results)
    doc = load_register(register_path)
    cases = {c["id"]: c for c in doc.get("case", [])}
    case = cases.get(args.id)
    if case is None:
        raise SystemExit(f"no case {args.id!r} in {register_path}")
    if not case.get("refute", "").strip():
        raise SystemExit(
            f"{args.id} has no refutation condition. Write it into the register and re-freeze "
            "before recording a result - that ordering is the entire point of this file."
        )
    if is_cut(case):
        raise SystemExit(f"{args.id} was cut: {case['cut_reason'].strip()}")
    results_doc = load_results(results_path)
    results_doc.setdefault("producer", "rtcase")
    results_doc["schema_version"] = SCHEMA_VERSION
    resolved = register_path.resolve()
    # The register normally lives in the repository, but the self-test drives
    # this with a temporary copy outside it, and crashing there would mean the
    # suite could only ever exercise the refusal paths.
    rel = resolved.relative_to(REPO) if resolved.is_relative_to(REPO) else resolved
    results_doc["register"] = str(rel).replace("\\", "/")
    results_doc["register_freeze_sha256"] = freeze_hash(doc.get("case", []))
    results_doc.setdefault("results", []).append(
        {
            "id": args.id,
            "date": args.date,
            "verdict": args.verdict,
            "evidence_kind": args.evidence,
            "artefacts": args.artefact or [],
            "note": args.note or "",
            "case_freeze_sha256": case_freeze(case),
        }
    )
    results_path.write_text(
        json.dumps(results_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"recorded {args.id} = {args.verdict} ({args.evidence}) in {results_path.name}")
    return 0


def week_summary(cases: list[dict[str, Any]], latest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Per-week: scheduled, done, and the ids still outstanding.

    This is the whole answer to "what makes W07 actually happen". Nothing here
    triggers anything - the `week` field is data, not a scheduler. What it buys
    is that "W07 is finished" becomes a statement someone can check, instead of
    a feeling. A week whose items are all still ⬜ cannot be written up as done
    without the contradiction being one command away.
    """
    out: dict[str, dict[str, Any]] = {}
    for c in cases:
        if is_cut(c):
            continue
        w = out.setdefault(
            str(c["week"]), {"total": 0, "done": 0, "todo": [], "no_refute": []}
        )
        w["total"] += 1
        if c["id"] in latest:
            w["done"] += 1
        else:
            w["todo"].append(c["id"])
            if not c.get("refute", "").strip():
                w["no_refute"].append(c["id"])
    return out


def todo(register_path: Path, results_path: Path, week: str | None) -> int:
    doc = load_register(register_path)
    cases = doc.get("case", [])
    latest = latest_results(load_results(results_path))
    by_id = {c["id"]: c for c in cases}
    summary = week_summary(cases, latest)

    weeks = [week] if week else sorted(w for w, s in summary.items() if s["todo"])
    for w in weeks:
        s = summary.get(w)
        if s is None:
            print(f"no week {w!r} in the register", file=sys.stderr)
            return 1
        print(f"{w}: {s['done']}/{s['total']} done, {len(s['todo'])} outstanding")
        for cid in s["todo"]:
            c = by_id[cid]
            flag = "  (no refutation condition yet)" if cid in s["no_refute"] else ""
            print(f"   [ ] {cid:6s} §{c['section']:<9s} {c['title']}{flag}")
        print()
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name in ("check", "render", "freeze", "stats"):
        p = sub.add_parser(name)
        p.add_argument("register", nargs="?", default=str(DEFAULT_REGISTER))
        p.add_argument("--results", default=str(DEFAULT_RESULTS))

    p = sub.add_parser("todo")
    p.add_argument("register", nargs="?", default=str(DEFAULT_REGISTER))
    p.add_argument("--results", default=str(DEFAULT_RESULTS))
    p.add_argument("--week", help="e.g. W05; default is every week with outstanding items")

    p = sub.add_parser("record")
    p.add_argument("--register", default=str(DEFAULT_REGISTER))
    p.add_argument("--results", default=str(DEFAULT_RESULTS))
    p.add_argument("--id", required=True)
    p.add_argument("--date", required=True, help="YYYY-MM-DD, the day the test ran")
    p.add_argument("--verdict", required=True, choices=sorted(VERDICT_MARKS))
    p.add_argument("--evidence", required=True, choices=EVIDENCE_KINDS)
    p.add_argument("--artefact", action="append", help="repeatable; repo-relative path")
    p.add_argument("--note", default="")

    args = ap.parse_args(argv[1:])

    if args.cmd == "record":
        return record(args)
    if args.cmd == "todo":
        return todo(Path(args.register), Path(args.results), args.week)
    if args.cmd == "check":
        return check(Path(args.register), Path(args.results))
    if args.cmd == "render":
        return render(Path(args.register), Path(args.results))
    if args.cmd == "freeze":
        print(freeze_hash(load_register(Path(args.register)).get("case", [])))
        return 0
    if args.cmd == "stats":
        doc = load_register(Path(args.register))
        cases = doc.get("case", [])
        latest = latest_results(load_results(Path(args.results)))
        confirmed = sum(1 for r, _ in latest.values() if r.get("verdict") == "confirmed")
        refuted = sum(1 for r, _ in latest.values() if r.get("verdict") == "refuted")
        print(
            f"{len(cases)} registered, "
            f"{sum(1 for c in cases if c.get('refute', '').strip())} frozen, "
            f"{len(latest)} executed, {confirmed} confirmed, {refuted} refuted"
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
