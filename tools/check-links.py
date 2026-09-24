#!/usr/bin/env python3
"""Every relative link in a committed Markdown file resolves to a committed file.

Why this exists
---------------
`README.md` said, of the gate board:

    The gates below are the acceptance criteria from the week plans in
    [`plan/`](plan/) -- copied, not invented after the fact.

`plan/` is in `.gitignore`. On GitHub that link is a 404, and it is the 404 that
costs the most in this repository, because the credibility of every gate rests
on a reader being able to go and look at the standard that was written first.
The whole argument was addressed to a reader who was then sent to a page that
does not exist.

It survived eleven weeks, and the reason it survived is the interesting part:
**`plan/` exists.** It is on the author's disk, `ls` finds it, every editor
opens it, and any checker built on `os.path.exists` reports it fine. The file
system and the repository disagreed, and only one of them is what a reader gets.

So this checker asks **git**, not the file system. A link target is resolvable
if and only if `git ls-files` knows about it. That single choice is the whole
instrument; everything below is bookkeeping around it.

What it checks
--------------
For every Markdown file tracked in the repository:

  * inline links ``[text](target)`` and reference definitions ``[id]: target``;
  * relative targets only -- ``http:``, ``https:``, ``mailto:``, protocol-
    relative ``//host`` and bare fragments to other documents are external and
    out of scope;
  * the target resolves, relative to the linking file's own directory, to a path
    git tracks. A directory target resolves if git tracks anything beneath it;
  * a fragment-only link ``(#heading)`` names a heading in its own file;
  * an ASCII fragment on a tracked Markdown target names a heading in that file.

What it deliberately does NOT check
-----------------------------------
**Non-ASCII fragments.** GitHub's heading-to-anchor algorithm for CJK text is
not the one documented for ASCII, it has changed at least once, and this
repository's Chinese files are full of headings like
``## 四、A2.4 的收尾規則與 A2.9 的先決條件互相矛盾``. Reimplementing that
slug rule from observation would produce a checker that fires on correct input,
and `tools/check-benchlog.py` already records what that costs: *a checker whose
first run fails on correct input teaches its operator to distrust it, which is
the opposite of the point.* The file half of those links is still checked -- only
the fragment is skipped, and `--report-skips` prints every one, so the number is
visible rather than absent.

**Link text.** Whether `[the runbook](journal/RUNBOOK.md)` points at the runbook
is a question about meaning, and this is a checker, not a reader.

**Untracked files' own links.** `plan/` and `archive/` are gitignored by design.
Their links are not a reader's problem because a reader never sees them.

    python3 tools/check-links.py            # the check
    python3 tools/check-links.py --report-skips
    python3 tools/check-links.py --list     # every resolved link, for a diff
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parent.parent

# `[text](target)` where target is not a fenced or inline-code artefact. The
# lazy `[^]]*` for the text half is deliberate: link text in this repository
# contains backticks, asterisks and full-width punctuation, and a stricter
# pattern silently stopped matching them.
INLINE = re.compile(r"\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
# `[id]: target` at the head of a line -- the reference-definition form.
REFDEF = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*<?([^\s>]+)>?", re.MULTILINE)
# ```lang ... ``` and ~~~ ... ~~~ -- a link inside a fence is an example, not a
# link. This repository's runsheet is mostly fences and several of them contain
# paths that have never existed, on purpose.
FENCE = re.compile(r"^(```|~~~).*?^\1", re.MULTILINE | re.DOTALL)
# `inline code` -- same reason, at a smaller scale.
CODE = re.compile(r"`[^`\n]*`")
EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.IGNORECASE)
ATX = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$", re.MULTILINE)
ASCII_ONLY = re.compile(r"^[\x00-\x7f]*$")


def tracked_paths() -> set[str]:
    """Every path git knows about, as forward-slash strings.

    `git ls-files` rather than a walk, because the entire point of this checker
    is the difference between the two.
    """
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {p for p in out.split("\0") if p}


def tracked_dirs(paths: set[str]) -> set[str]:
    """Every directory that has a tracked file somewhere beneath it."""
    dirs: set[str] = set()
    for p in paths:
        parts = PurePosixPath(p).parts
        for i in range(1, len(parts)):
            dirs.add("/".join(parts[:i]))
    return dirs


def strip_noise(text: str) -> str:
    """Blank out fenced blocks and inline code, preserving line numbers."""

    def blank(m: re.Match[str]) -> str:
        return re.sub(r"[^\n]", " ", m.group(0))

    return CODE.sub(blank, FENCE.sub(blank, text))


def github_slug(heading: str) -> str:
    """GitHub's anchor rule, for the ASCII subset this checker will judge.

    Lower-case, drop everything that is not alphanumeric / space / hyphen, then
    spaces to hyphens. Markdown emphasis and inline code in the heading are
    removed first because GitHub slugs the rendered text, not the source.
    """
    h = re.sub(r"`([^`]*)`", r"\1", heading)
    h = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", h)
    h = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", h)
    h = h.lower()
    h = re.sub(r"[^\w\s-]", "", h, flags=re.UNICODE)
    # One hyphen per space, NOT one per run of spaces. Removing punctuation
    # leaves the gaps behind -- `codes — a` becomes `codes  a` and GitHub
    # anchors it `codes--a`. The first version of this function collapsed runs
    # with `\s+`, and every anchor in this repository that spans an em dash,
    # a slash or a comma came out one hyphen short. It reported fourteen
    # correct links as broken, which is the failure mode this repository has
    # the most of: an instrument that is wrong in the direction of finding
    # something.
    return re.sub(r"\s", "-", h.strip())


def headings_of(path: Path) -> set[str]:
    # Fences are blanked -- a `#` inside a code block is not a heading -- but
    # inline code is NOT, because GitHub slugs the *rendered* heading and
    # `### 7.4 `J2` and the power switch` anchors as `74-j2-and-the-power-switch`.
    # Blanking it here deleted the `J2` before the slugger could render it, and
    # every heading in this repository that names a symbol came out wrong.
    try:
        text = FENCE.sub(
            lambda m: re.sub(r"[^\n]", " ", m.group(0)), path.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeDecodeError):
        return set()
    slugs: set[str] = set()
    seen: dict[str, int] = {}
    for m in ATX.finditer(text):
        base = github_slug(m.group(2))
        if not base:
            continue
        n = seen.get(base, 0)
        seen[base] = n + 1
        slugs.add(base if n == 0 else f"{base}-{n}")
    return slugs


def links_in(text: str) -> list[tuple[int, str]]:
    """(line number, target) for every link in the file, fences excluded."""
    clean = strip_noise(text)
    found: list[tuple[int, str]] = []
    for pattern in (INLINE, REFDEF):
        for m in pattern.finditer(clean):
            found.append((clean.count("\n", 0, m.start()) + 1, m.group(1)))
    return sorted(found)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--report-skips",
        action="store_true",
        help="print the non-ASCII fragments whose anchor half was not judged",
    )
    ap.add_argument(
        "--list",
        action="store_true",
        help="print every resolved link target, one per line",
    )
    ap.add_argument(
        "paths",
        nargs="*",
        help="Markdown files to check (default: every tracked *.md)",
    )
    args = ap.parse_args()

    paths = tracked_paths()
    dirs = tracked_dirs(paths)
    if args.paths:
        targets = [str(Path(p).resolve().relative_to(REPO)).replace("\\", "/") for p in args.paths]
    else:
        targets = sorted(p for p in paths if p.endswith(".md"))

    heading_cache: dict[str, set[str]] = {}
    broken: list[str] = []
    skipped: list[str] = []
    resolved = 0
    checked_files = 0

    for rel in targets:
        f = REPO / rel
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            broken.append(f"{rel}: cannot be read ({exc})")
            continue
        checked_files += 1
        here = PurePosixPath(rel).parent

        for line, raw in links_in(text):
            target = raw.strip()
            if not target or EXTERNAL.match(target):
                continue

            file_part, _, frag = target.partition("#")

            # A bare fragment points into the linking file itself.
            if not file_part:
                if not frag:
                    continue
                if not ASCII_ONLY.match(frag):
                    skipped.append(f"{rel}:{line}: #{frag}")
                    continue
                if rel not in heading_cache:
                    heading_cache[rel] = headings_of(f)
                if frag.lower() not in heading_cache[rel]:
                    broken.append(f"{rel}:{line}: no heading '#{frag}' in this file")
                else:
                    resolved += 1
                continue

            # Resolve relative to the linking file, then normalise `..`.
            joined = (PurePosixPath(here / file_part) if str(here) != "."
                      else PurePosixPath(file_part))
            parts: list[str] = []
            for part in joined.parts:
                if part == ".":
                    continue
                if part == "..":
                    if parts:
                        parts.pop()
                    continue
                parts.append(part)
            dest = "/".join(parts)

            if dest in paths or dest in dirs:
                pass
            elif (REPO / dest).exists():
                # The bug this checker was written for: on disk, not in the
                # repository. Named separately because the fix is different --
                # a missing file is a typo, this one is a .gitignore decision.
                broken.append(
                    f"{rel}:{line}: '{target}' exists on disk but git does not track it "
                    f"-- a reader gets a 404"
                )
                continue
            else:
                broken.append(
                    f"{rel}:{line}: '{target}' resolves to '{dest}', "
                    f"which does not exist")
                continue

            if args.list:
                print(dest)

            if frag and dest.endswith(".md") and dest in paths:
                if not ASCII_ONLY.match(frag):
                    skipped.append(f"{rel}:{line}: {target}")
                else:
                    if dest not in heading_cache:
                        heading_cache[dest] = headings_of(REPO / dest)
                    if frag.lower() not in heading_cache[dest]:
                        broken.append(f"{rel}:{line}: '{dest}' has no heading '#{frag}'")
                        continue
            resolved += 1

    if args.report_skips and skipped:
        print(f"  skipped {len(skipped)} non-ASCII fragments (file half was checked):")
        for s in skipped:
            print(f"    {s}")

    if broken:
        print(f"check-links: {len(broken)} broken link(s)")
        for b in broken:
            print(f"  {b}")
        return 1

    print(
        f"  ok   check-links: {resolved} relative links resolve, "
        f"across {checked_files} tracked Markdown files "
        f"({len(skipped)} non-ASCII fragments not judged)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
