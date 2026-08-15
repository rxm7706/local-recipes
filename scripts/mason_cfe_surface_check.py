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
its diff includes `.claude/skills/conda-forge-expert/CHANGELOG.md` exactly —
subject alone never launders a CFE touch: a `retro:`-subject commit that
touches the CFE surface without the CHANGELOG.md move is still reported as
`unsanctioned-cfe-touch`.

Commit range is derived, never a hardcoded baseline SHA: `git log -- <mason
path>` is self-bounding to the mason-CLI effort already (starts at Story
1.1's commit). Per-commit diffs use plain `diff-tree` (no `-m`/`-c`), which
prints nothing for a real multi-parent merge — the first-parent diff
(`<sha>^1..<sha>`) is the fallback so a conflict-resolving merge is never
silently read as "touches nothing."

Exit codes: 0 clean, 1 findings, 2 could not run (`git log` failed, e.g. not
a git repository).
"""
from __future__ import annotations

# Registry declaration — see scripts/detectors.py. `repo`: reads tracked
# commit history only — runs identically in CI and locally, no local-only
# state.
DETECTOR = {"scope": "repo"}

import argparse
import json
import pathlib
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
    """git stdout, or "" on any failure — safe for per-commit lookups, where
    an empty result and a failure are handled identically (both mean "no
    signal for this sha")."""
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


def changed_files(root: pathlib.Path, sha: str) -> list[str]:
    """Files touched by `sha`. Falls back to the first-parent diff when plain
    `diff-tree` returns empty (Design Notes: a real 2-parent merge)."""
    files = [ln for ln in git(
        root, "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", sha
    ).splitlines() if ln.strip()]
    if files:
        return files
    return [ln for ln in git(root, "diff", "--name-only", f"{sha}^1", sha).splitlines()
            if ln.strip()]


def commit_subject(root: pathlib.Path, sha: str) -> str:
    return git(root, "log", "-1", "--format=%s", sha)


def is_sanctioned(root: pathlib.Path, sha: str, files: list[str]) -> bool:
    return commit_subject(root, sha).startswith("retro:") and CFE_CHANGELOG in files


def scan(root: pathlib.Path, shas: list[str]) -> list[dict]:
    findings: list[dict] = []
    sanctioned: list[str] = []
    for sha in shas:
        files = changed_files(root, sha)
        cfe_touches = sorted(f for f in files if is_cfe_path(f))
        if not cfe_touches:
            continue
        if is_sanctioned(root, sha, files):
            sanctioned.append(sha)
            continue
        subject = commit_subject(root, sha)
        findings.append({
            "kind": "unsanctioned-cfe-touch",
            "ref": sha[:10],
            "detail": f"{sha[:10]} ({subject!r}) touches CFE surface: "
                      f"{', '.join(cfe_touches)}",
            "remedy": "Mason must never modify the conda-forge-expert surface — "
                      "split the CFE-surface change out of this commit, or revert it",
        })
    if len(sanctioned) > 1:
        findings.append({
            "kind": "exception-reused",
            "ref": ", ".join(s[:10] for s in sanctioned),
            "detail": f"{len(sanctioned)} commits qualify as the sanctioned retro "
                      "exception (subject `retro:` + CFE CHANGELOG.md in diff) — "
                      "at most one is allowed",
            "remedy": "only one closing retrospective commit may claim the "
                      "exception — squash or re-scope the extra commit(s)",
        })
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="mason-cfe-surface-check",
        description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    shas = mason_commits(ROOT)
    if shas is None:
        print("UNKNOWN: `git log` could not run — not a git repository, or "
              f"{MASON_PATH} is unreachable from HEAD.", file=sys.stderr)
        return 2

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
