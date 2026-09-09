#!/usr/bin/env python3
"""mason-cfe-surface-check — detect any Mason commit that also touches the
conda-forge-expert (CFE) surface.

FR-45/AD-15 require automated proof that Mason (`src/shared/packages/
pyforge-mason/**`) never modifies the CFE surface, with exactly one sanctioned
exception: Story 5.5's closing retrospective commit. Nothing before this
scanned commit history for that — the guarantee was stated, never checked.

CFE surface = exactly:
    .claude/skills/conda-forge-expert/**
    .claude/scripts/conda-forge-expert/**
    .claude/tools/conda_forge_server.py

Findings:
    unsanctioned-cfe-touch  a non-sanctioned commit's diff touches both the
                            mason path and a CFE-surface path.
    exception-reused        two or more commits both qualify as the sanctioned
                            retro exception — it may fire at most once.

A commit is the sanctioned exception ONLY if its subject starts `retro:` AND
`.claude/skills/conda-forge-expert/CHANGELOG.md` was ADDED or MODIFIED (never
merely deleted/renamed-away) in its diff — subject alone never launders a CFE
touch: a `retro:`-subject commit that touches the CFE surface without adding
to the CHANGELOG is still reported as `unsanctioned-cfe-touch`.

Commit range is derived, never a hardcoded baseline SHA: `git log -- <mason
path>` is self-bounding to the mason-CLI effort already (starts at Story
1.1's commit). Per-commit diffs use plain `diff-tree` (no `-m`/`-c`), which
prints nothing for a real multi-parent merge — the first-parent diff
(`<sha>^1..<sha>`) is the fallback so a conflict-resolving merge is never
silently read as "touches nothing."

Exit codes: 0 clean, 1 findings, 2 could not run -- `git log` itself failed
(e.g. not a git repository), or it succeeded but found zero commits (a wrong
cwd/branch, or a shallow/partial clone missing the range, reads the same as
"clean" unless this is called out separately; it is never treated as proof
of cleanliness).
"""
from __future__ import annotations

# Registry declaration — see scripts/detectors.py. `repo`: reads tracked
# commit history only — runs identically in CI and locally, no local-only
# state.
DETECTOR = {"scope": "repo"}

import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MASON_PATH = "src/shared/packages/pyforge-mason"
CFE_CHANGELOG = ".claude/skills/conda-forge-expert/CHANGELOG.md"
CFE_SURFACE_PREFIXES = (
    ".claude/skills/conda-forge-expert/",
    ".claude/scripts/conda-forge-expert/",
)
CFE_SURFACE_FILES = frozenset({".claude/tools/conda_forge_server.py"})


def _run(root: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(["git", *args], cwd=root, capture_output=True,
                               text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None


def git(root: pathlib.Path, *args: str) -> str:
    """git stdout, or "" on any failure — matches every sibling detector's
    `git()` wrapper (e.g. unpushed_work_check.py): a failed per-commit lookup
    and a genuinely empty one are handled identically, "no signal for this
    sha", rather than diverging from house convention for this one script."""
    proc = _run(root, *args)
    return proc.stdout.strip() if proc and proc.returncode == 0 else ""


def is_cfe_path(path: str) -> bool:
    return path in CFE_SURFACE_FILES or any(path.startswith(p) for p in CFE_SURFACE_PREFIXES)


def mason_commits(root: pathlib.Path) -> list[str] | None:
    """SHAs (newest first) touching MASON_PATH; None if `git log` itself
    could not run (e.g. `root` is not a git repository) — the exit-2 case."""
    proc = _run(root, "log", "--format=%H", "HEAD", "--", MASON_PATH)
    if proc is None or proc.returncode != 0:
        return None
    return [ln for ln in proc.stdout.splitlines() if ln.strip()]


def diff_name_status(root: pathlib.Path, sha: str) -> list[tuple[str, str]]:
    """(status, path) pairs for `sha`'s diff. Falls back to the first-parent
    diff when plain `diff-tree` returns empty (Design Notes: a real 2-parent
    merge). `--name-status` (not `--name-only`) so callers can tell an added
    or modified path from a deleted one -- fetched once per commit and reused
    for both the CFE-touch scan and the sanction check, rather than shelling
    out twice for the same commit."""
    for args in (
        ("diff-tree", "--no-commit-id", "--name-status", "-r", "--root", sha),
        ("diff", "--name-status", f"{sha}^1", sha),
    ):
        lines = [ln for ln in git(root, *args).splitlines() if ln.strip()]
        if lines:
            return [tuple(ln.split("\t", 1)) for ln in lines]  # type: ignore[misc]
    return []


def commit_subject(root: pathlib.Path, sha: str) -> str:
    return git(root, "log", "-1", "--format=%s", sha)


# `retro:` or `retro(<scope>):` -- kept in step with
# pyforge.testing_kit.branch_diff_guard.unsanctioned_commits, which carries the
# full rationale. The repo's recent retros are all `retro(cfe):`.
_RETRO_SUBJECT = re.compile(r"^retro(\([^)]*\))?:")


def scan(root: pathlib.Path, shas: list[str]) -> list[dict]:
    findings: list[dict] = []
    sanctioned: list[str] = []
    for sha in shas:
        status_lines = diff_name_status(root, sha)
        files = [path for _status, path in status_lines]
        cfe_touches = sorted(f for f in files if is_cfe_path(f))
        if not cfe_touches:
            continue
        subject = commit_subject(root, sha)
        changelog_status = next(
            (status[:1] for status, path in status_lines if path == CFE_CHANGELOG), None)
        if _RETRO_SUBJECT.match(subject) and changelog_status in ("A", "M"):
            sanctioned.append(sha)
            continue
        findings.append({
            "kind": "unsanctioned-cfe-touch",
            "ref": sha[:10],
            "refs": [sha[:10]],
            "detail": f"{sha[:10]} ({subject!r}) touches CFE surface: "
                      f"{', '.join(cfe_touches)}",
            "remedy": "Mason must never modify the conda-forge-expert surface — "
                      "split the CFE-surface change out of this commit, or revert it",
        })
    if len(sanctioned) > 1:
        refs = [s[:10] for s in sanctioned]
        findings.append({
            "kind": "exception-reused",
            "ref": refs[0],
            "refs": refs,
            "detail": f"{len(sanctioned)} commits qualify as the sanctioned retro "
                      "exception (subject `retro:` + CFE CHANGELOG.md added/modified "
                      "in diff) — at most one is allowed",
            "remedy": "only one closing retrospective commit may claim the "
                      "exception — squash or re-scope the extra commit(s)",
        })
    return findings


def _unknown(message: str, as_json: bool) -> int:
    if as_json:
        print(json.dumps({"error": message, "commits_scanned": None, "findings": []}))
    else:
        print(f"UNKNOWN: {message}", file=sys.stderr)
    return 2


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="mason-cfe-surface-check",
        description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    shas = mason_commits(ROOT)
    if shas is None:
        return _unknown("`git log` could not run — not a git repository, or "
                         f"{MASON_PATH} is unreachable from HEAD.", args.json)
    if not shas:
        return _unknown(f"zero commits touch {MASON_PATH} from HEAD — check cwd, "
                         "branch, and clone depth before trusting a clean result; "
                         "this is never treated as proof of cleanliness.", args.json)

    findings = scan(ROOT, shas)

    if args.json:
        print(json.dumps({"commits_scanned": len(shas), "findings": findings}, indent=2))
        return 1 if findings else 0

    print(f"mason-cfe-surface-check: {len(shas)} commit(s) touching {MASON_PATH}\n")
    if not findings:
        print("  clean — no non-sanctioned commit's diff touches the CFE surface "
              "(.claude/skills/conda-forge-expert/**, .claude/scripts/conda-forge-expert/**, "
              ".claude/tools/conda_forge_server.py).")
        return 0

    for f in findings:
        print(f"  ✗ [{f['kind']}] {f['ref']}")
        print(f"      {f['detail']}")
        print(f"      → {f['remedy']}")
    print(f"\nFAIL: {len(findings)} finding(s). Mason must never modify the "
          "conda-forge-expert surface except Story 5.5's single closing "
          "retrospective commit.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
