#!/usr/bin/env python3
"""mason-cfe-surface-check — detect any Mason commit that also touches the
conda-forge-expert (CFE) surface.

FR-45/AD-15 require automated proof that Mason (`src/shared/packages/
pyforge-mason/**`) never modifies the CFE surface except the named exceptions
below. Nothing before this scanned commit history for that — the guarantee
was stated, never checked.

CFE surface = exactly:
    .claude/skills/conda-forge-expert/**
    .claude/scripts/conda-forge-expert/**
    .claude/tools/conda_forge_server.py

Sanctioned exceptions (each is a named class, not a SHA dump):

    5.5 retro     subject starts `retro:` / `retro(<scope>):` AND
                  CHANGELOG.md is ADDED or MODIFIED in the same diff.
                  At most one commit may qualify (`exception-reused`).
    15.1 closeout subject names Story 15.1 *and* the retire/mirror closeout
                  — mason's campaign job was to take down the CFE rebuild
                  mirrors. Subject-only "Story 15.1" never launders a touch.
    44.7 landed   the one mixed commit already on main (Steward 44.7 wired
                  mason to `native-build.sh`). SHA is recorded because that
                  history cannot be split; the waiver is only that SHA and
                  only that CFE path.

Findings:
    unsanctioned-cfe-touch  a non-sanctioned commit's authored diff touches
                            both the mason path and a CFE-surface path.
    exception-reused        two or more commits both qualify as the 5.5 retro
                            exception — it may fire at most once.

Merges: plain `diff-tree` (no `-m`/`-c`) prints nothing for a multi-parent
commit. Importing or 3-way-merging CFE files that already exist on a parent
is not Mason authoring CFE. A merge authors CFE only when it *adds* a CFE
path that no parent has (the "slipped in during conflict resolution" case).

Commit range is derived, never a hardcoded baseline SHA: `git log -- <mason
path>` is self-bounding to the mason-CLI effort already (starts at Story
1.1's commit).

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
# Steward 44.7 — already on main; cannot be split. Waiver is this SHA and
# only native-build.sh (a broader CFE touch on a rewritten hash is a finding).
LANDED_MIXED_44_7 = "f180624fd84581145f65735711507b02fec34017"
LANDED_MIXED_44_7_CFE = frozenset({
    ".claude/scripts/conda-forge-expert/native-build.sh",
})


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


def _parse_name_status(text: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for ln in text.splitlines():
        if not ln.strip():
            continue
        parts = ln.split("\t", 1)
        if len(parts) != 2:
            continue
        rows.append((parts[0], parts[1]))
    return rows


def diff_name_status(root: pathlib.Path, sha: str) -> list[tuple[str, str]]:
    """(status, path) pairs for a single-parent (or root) commit.

    Merges are handled in `authored_cfe_touches` — first-parent fallback
    here would treat `git merge origin/main` as Mason authoring every CFE
    file that arrived from main.
    """
    text = git(root, "diff-tree", "--no-commit-id", "--name-status",
               "-r", "--root", sha)
    return _parse_name_status(text)


def commit_parents(root: pathlib.Path, sha: str) -> list[str]:
    raw = git(root, "rev-list", "--parents", "-n", "1", sha)
    parts = raw.split()
    return parts[1:] if len(parts) > 1 else []


def name_status_between(root: pathlib.Path, a: str, b: str) -> list[tuple[str, str]]:
    return _parse_name_status(git(root, "diff", "--name-status", a, b))


def path_in_commit(root: pathlib.Path, sha: str, path: str) -> bool:
    proc = _run(root, "cat-file", "-e", f"{sha}:{path}")
    return bool(proc and proc.returncode == 0)


def authored_cfe_touches(
    root: pathlib.Path, sha: str,
) -> tuple[list[str], list[tuple[str, str]]]:
    """CFE paths this commit authored, plus name-status rows for sanctions.

    On a merge, 3-way combining of CFE files that already exist on a parent
    is ignored (merge-from-main). A merge authors CFE only when it adds a
    CFE path no parent has. Status rows are the union across parents
    (needed for CHANGELOG A/M on a resolving merge).
    """
    parents = commit_parents(root, sha)
    if len(parents) >= 2:
        seen: set[str] = set()
        status_lines: list[tuple[str, str]] = []
        for parent in parents:
            for row in name_status_between(root, parent, sha):
                status_lines.append(row)
                _status, path = row
                if is_cfe_path(path):
                    seen.add(path)
        authored = sorted(
            path for path in seen
            if not any(path_in_commit(root, parent, path) for parent in parents)
        )
        return authored, status_lines
    status_lines = diff_name_status(root, sha)
    authored = sorted(path for _status, path in status_lines if is_cfe_path(path))
    return authored, status_lines


def commit_subject(root: pathlib.Path, sha: str) -> str:
    return git(root, "log", "-1", "--format=%s", sha)


# `retro:` or `retro(<scope>):` -- kept in step with
# pyforge.testing_kit.branch_diff_guard.unsanctioned_commits, which carries the
# full rationale. The repo's recent retros are all `retro(cfe):`.
_RETRO_SUBJECT = re.compile(r"^retro(\([^)]*\))?:")
# Mason 15.1 — retire the CFE rebuild-campaign mirrors. "Story 15.1" alone
# is not enough; the closeout verbs have to be in the subject too.
_STORY_15_1_CLOSEOUT = re.compile(
    r"Story 15\.1\b.{0,80}\b(retire|mirror)",
    re.IGNORECASE | re.DOTALL,
)


def is_retro_exception(subject: str, status_lines: list[tuple[str, str]]) -> bool:
    changelog_status = next(
        (status[:1] for status, path in status_lines if path == CFE_CHANGELOG),
        None,
    )
    return bool(_RETRO_SUBJECT.match(subject) and changelog_status in ("A", "M"))


def is_story_15_1_closeout(subject: str) -> bool:
    return bool(_STORY_15_1_CLOSEOUT.search(subject))


def is_landed_44_7(sha: str, cfe_touches: list[str]) -> bool:
    if sha != LANDED_MIXED_44_7:
        return False
    return bool(cfe_touches) and set(cfe_touches) <= LANDED_MIXED_44_7_CFE


def scan(root: pathlib.Path, shas: list[str]) -> list[dict]:
    findings: list[dict] = []
    sanctioned: list[str] = []
    for sha in shas:
        cfe_touches, status_lines = authored_cfe_touches(root, sha)
        if not cfe_touches:
            continue
        subject = commit_subject(root, sha)
        if is_retro_exception(subject, status_lines):
            sanctioned.append(sha)
            continue
        if is_story_15_1_closeout(subject):
            continue
        if is_landed_44_7(sha, cfe_touches):
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
          "retrospective, Story 15.1's campaign closeout, or the landed "
          "44.7 native-build.sh commit.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
