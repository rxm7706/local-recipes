#!/usr/bin/env python3
"""Repeatable worktree + branch hygiene sweep for this repo (operator tool).

Dry-run by default: classifies every registered git worktree and prints a
verdict per worktree. ``--execute`` applies the safe verdicts. The rule set is
the one settled in the 2026-09-05 shutdown sweep (memory:
`project_pixi_sweep_and_hygiene_2026-09-05.md`); the marshal-native home for
this logic is `marshal retire` (tracked ledger entry DW-HYGIENE-2026-09-05-1).

Verdicts, in priority order (first match wins):

  KEEP        primary checkout, a loop home (`~/.bmad-loops/<station>`), a
              locked worktree, a worktree with a live process cwd inside it,
              or an unmerged story that is not ledger-`done`.
  PRUNE       registered path no longer exists -> `git worktree prune`.
  DELETE      clean tree AND HEAD is an ancestor of main; or unmerged commits
              whose story is ledger-`done` AND the branch is on origin; or
              the only dirt is untracked files / lock+manifest churn on a
              merged branch.
  PRESERVE-THEN-DELETE
              unmerged commits (story done, branch NOT on origin) or tracked
              uncommitted edits on a done story: `git format-patch main..HEAD`
              plus `git diff` are written under --preserve-dir, then the
              worktree is removed. The branch is never deleted.
  DELETE-WORKTREE-KEEP-BRANCH
              an `attempt-preserve/*` branch: the branch is policy-protected,
              the worktree is disposable once the branch is on origin.
  INSPECT     unmerged/dirty with no ledger key to decide against.

Never touched: branches (this tool removes WORKTREES only, unless
--delete-merged-local-branches is given, which safe-deletes local branches
that are ancestors of main, excluding `attempt-preserve/*` and `loop/*`),
`loop/<station>` heads, `attempt-preserve/*`, and the loop-home remotes
(`marshal-home`, `mason-home`) beyond `git remote prune`.

Usage:
  python scripts/worktree_sweep.py                 # dry run, text table
  python scripts/worktree_sweep.py --format json   # machine-readable
  python scripts/worktree_sweep.py --execute       # apply DELETE / PRESERVE-THEN-DELETE / D-W-K-B
  python scripts/worktree_sweep.py --execute --delete-merged-local-branches --prune-home-remotes
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()
LOOP_HOMES_ROOT = HOME / ".bmad-loops"
DEFAULT_PRESERVE_DIR = HOME / ".local" / "state" / "pyforge-marshal" / "worktree-preserve"
STATIONS = ("atlas", "doctor", "herald", "marshal", "mason", "scribe", "steward", "warden")
PROTECTED_BRANCH_PREFIXES = ("attempt-preserve/", "loop/", "recover/", "rescue/")
LIVE_STATUSES = frozenset({"backlog", "ready-for-dev", "in-progress", "blocked", "review", "awaiting-operator"})
CHURN_FILES = ("pixi.lock", "pyproject.toml", "pixi.toml")


def _git(*args: str, cwd: Path | None = None) -> tuple[str, int]:
    r = subprocess.run(["git", *args], capture_output=True, text=True, cwd=str(cwd or REPO_ROOT))
    return r.stdout.strip(), r.returncode


@dataclass
class Worktree:
    path: str
    branch: str
    category: str
    exists: bool = True
    prunable: bool = False
    locked: bool = False
    dirty_files: list[str] = field(default_factory=list)
    merged: bool | None = None
    unmerged_commits: int = 0
    unmerged_subjects: list[str] = field(default_factory=list)
    live_cwd: bool = False
    station: str | None = None
    story_key: str | None = None
    ledger_status: str = "n/a"
    branch_on_origin: bool = False
    last_commit: str = ""
    verdict: str = ""
    reason: str = ""


# ---------------------------------------------------------------- discovery
def list_worktrees() -> list[Worktree]:
    out, _ = _git("worktree", "list", "--porcelain")
    items: list[Worktree] = []
    for block in [b for b in out.split("\n\n") if b.strip()]:
        d: dict[str, str | bool] = {}
        for line in block.splitlines():
            k, _, v = line.partition(" ")
            d[k] = v if v else True
        path = str(d.get("worktree", ""))
        branch = str(d.get("branch", "(detached)")).replace("refs/heads/", "")
        items.append(Worktree(path=path, branch=branch, category=categorize(path),
                              exists=os.path.isdir(path), prunable="prunable" in d, locked="locked" in d))
    return items


def categorize(path: str) -> str:
    p = Path(path)
    if p == REPO_ROOT:
        return "primary"
    if str(p).startswith(str(LOOP_HOMES_ROOT) + "/"):
        rel = str(p)[len(str(LOOP_HOMES_ROOT)) + 1:]
        if "/" not in rel:
            return "loop-home"
        return "loop-run-worktree" if "/.bmad-loop/runs/" in str(p) else "loop-home-other"
    if "/.claude/worktrees/.retired-worktrees" in path:
        return "claude-retired"
    if "/.claude/worktrees/" in path:
        return "claude-worktrees"
    if "/.cursor/worktrees/" in path:
        return "cursor-worktrees"
    if "/.worktrees/" in path:
        return "dispatch"
    if "/local-recipes-wt-" in path:
        return "sibling"
    return "other"


def live_cwds() -> list[str]:
    cwds: set[str] = set()
    for proc in glob.glob("/proc/[0-9]*"):
        try:
            cwds.add(os.readlink(f"{proc}/cwd"))
        except OSError:
            continue
    return sorted(cwds)


def load_ledgers() -> dict[str, dict[str, str]]:
    ledgers: dict[str, dict[str, str]] = {}
    for led in glob.glob(str(REPO_ROOT / "_bmad-output/projects/pyforge-*/planning-artifacts/sprint-status-ledger.yaml")):
        station = led.split("/projects/pyforge-")[1].split("/")[0]
        d: dict[str, str] = {}
        for line in open(led, encoding="utf-8"):
            m = re.match(r"^\s{2}([a-z]?\d+-\d+[a-z]?)-[^:]*:\s*(\S+)", line)
            if m:
                d[m.group(1)] = m.group(2)
        ledgers[station] = d
    return ledgers


def origin_heads() -> set[str]:
    out, rc = _git("ls-remote", "--heads", "origin")
    if rc != 0:
        return set()
    return {line.split()[1].removeprefix("refs/heads/") for line in out.splitlines() if line.strip()}


# ---------------------------------------------------------------- mapping
def station_of(path: str, branch: str) -> str | None:
    m = (re.search(r"\.bmad-loops/pyforge-([a-z]+)/", path)
         or re.match(r"(%s)/" % "|".join(STATIONS), branch)
         or re.match(r"dispatch/pyforge-([a-z]+)/", branch)
         or re.search(r"-(%s)-\d+-\d+" % "|".join(STATIONS), branch))
    return m.group(1) if m else None


def story_key_of(branch: str) -> str | None:
    seg = branch.split("/")[-1]
    m = re.search(r"-(%s)-(\d+)-(\d+)" % "|".join(STATIONS), seg)
    if m:
        return f"{m.group(2)}-{m.group(3)}"
    m = re.match(r"(?:story-)?([a-z]?\d+)[-.](\d+)[a-z]?(?:-|$)", seg)
    return f"{m.group(1)}-{m.group(2)}" if m else None


# ---------------------------------------------------------------- verdict
def verdict_for(wt: Worktree) -> tuple[str, str]:
    """Pure rule engine over an already-gathered Worktree."""
    if wt.category in ("primary", "loop-home"):
        return "KEEP", f"{wt.category}: never swept"
    if wt.prunable or not wt.exists:
        return "PRUNE", "registered path no longer exists"
    if wt.locked:
        return "KEEP", "worktree is locked"
    if wt.live_cwd:
        return "KEEP", "a live process has its cwd inside this worktree"
    dirty = wt.dirty_files
    unmerged = wt.unmerged_commits
    done = wt.ledger_status == "done"
    if wt.branch.startswith("attempt-preserve/"):
        if wt.branch_on_origin:
            return "DELETE-WORKTREE-KEEP-BRANCH", "attempt-preserve branch is policy-protected and already on origin; the worktree is disposable"
        return "KEEP", "attempt-preserve branch not yet on origin; push it before dropping the worktree"
    if not dirty and not unmerged and wt.merged:
        return "DELETE", "clean tree, HEAD is an ancestor of main"
    if unmerged and done and wt.branch_on_origin:
        return "DELETE", "story is ledger-done on main by another path and the branch is on origin, so the commits stay reachable"
    if unmerged and done:
        return "PRESERVE-THEN-DELETE", "story is ledger-done on main by another path; export main..HEAD as patches first"
    if unmerged and wt.ledger_status in LIVE_STATUSES:
        return "KEEP", f"story is {wt.ledger_status}: this may be the live attempt"
    if unmerged:
        return "INSPECT", "unmerged commits with no ledger key to decide against"
    if dirty and all(f.startswith("??") for f in dirty):
        return "DELETE", "only untracked scratch on a merged branch"
    if dirty and all(any(c in f for c in CHURN_FILES) for f in dirty):
        return "DELETE", "only lock/manifest churn on a merged branch"
    if dirty and done:
        return "PRESERVE-THEN-DELETE", "tracked edits on a merged branch of a done story; save the diff first"
    return "INSPECT", "tracked edits whose story is not done or has no ledger key"


def gather(wt: Worktree, cwds: list[str], ledgers: dict, heads: set[str]) -> Worktree:
    if wt.category in ("primary", "loop-home") or not wt.exists or wt.prunable:
        return wt
    p = Path(wt.path)
    wt.live_cwd = any(c == wt.path or c.startswith(wt.path.rstrip("/") + "/") for c in cwds)
    st, _ = _git("status", "--porcelain", "--untracked-files=normal", cwd=p)
    wt.dirty_files = [l for l in st.splitlines() if l.strip()]
    _, rc = _git("merge-base", "--is-ancestor", "HEAD", "main", cwd=p)
    wt.merged = rc == 0
    cnt, _ = _git("rev-list", "--count", "main..HEAD", cwd=p)
    wt.unmerged_commits = int(cnt or 0)
    if wt.unmerged_commits:
        subj, _ = _git("log", "--format=%s", "main..HEAD", cwd=p)
        wt.unmerged_subjects = subj.splitlines()[:3]
    wt.last_commit, _ = _git("log", "-1", "--format=%ad", "--date=short", cwd=p)
    wt.station = station_of(wt.path, wt.branch)
    wt.story_key = story_key_of(wt.branch)
    if wt.station and wt.story_key:
        wt.ledger_status = ledgers.get(wt.station, {}).get(wt.story_key, "not-in-ledger")
    wt.branch_on_origin = wt.branch in heads
    return wt


# ---------------------------------------------------------------- actions
def preserve(wt: Worktree, preserve_dir: Path) -> Path:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", wt.branch)
    dest = preserve_dir / slug
    dest.mkdir(parents=True, exist_ok=True)
    p = Path(wt.path)
    if wt.unmerged_commits:
        subprocess.run(["git", "format-patch", "-o", str(dest), "main..HEAD"], capture_output=True, text=True, cwd=str(p))
    diff, _ = _git("diff", cwd=p)
    if diff:
        (dest / "uncommitted.diff").write_text(diff + "\n", encoding="utf-8")
    untracked, _ = _git("ls-files", "--others", "--exclude-standard", cwd=p)
    if untracked:
        (dest / "untracked-files.txt").write_text(untracked + "\n", encoding="utf-8")
    (dest / "origin.json").write_text(json.dumps(asdict(wt), indent=1), encoding="utf-8")
    return dest


def remove_worktree(wt: Worktree) -> bool:
    """Re-check the verdict-relevant facts immediately before removal."""
    p = Path(wt.path)
    if not p.is_dir():
        return False
    st, _ = _git("status", "--porcelain", "--untracked-files=normal", cwd=p)
    if wt.verdict == "DELETE" and not wt.dirty_files and st.strip():
        return False  # became dirty since classification
    _, rc = _git("worktree", "remove", "--force", wt.path)
    if rc != 0:
        subprocess.run(["chmod", "-R", "u+w", wt.path], capture_output=True)
        _, rc = _git("worktree", "remove", "--force", wt.path)
    return rc == 0 and not p.exists()


def delete_merged_local_branches() -> tuple[int, list[str]]:
    out, _ = _git("branch", "--merged", "main", "--format=%(refname:short) %(worktreepath)")
    deleted, kept = 0, []
    for line in out.splitlines():
        name, _, wtpath = line.partition(" ")
        if name == "main" or wtpath.strip() or name.startswith(PROTECTED_BRANCH_PREFIXES):
            continue
        _, rc = _git("merge-base", "--is-ancestor", name, "main")
        if rc != 0:
            kept.append(name)
            continue
        _, rc = _git("branch", "-D", name)
        deleted += 1 if rc == 0 else 0
    return deleted, kept


# ---------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--execute", action="store_true", help="apply DELETE / PRESERVE-THEN-DELETE / DELETE-WORKTREE-KEEP-BRANCH / PRUNE")
    ap.add_argument("--delete-merged-local-branches", action="store_true", help="also safe-delete local branches that are ancestors of main (never attempt-preserve/*, loop/*)")
    ap.add_argument("--prune-home-remotes", action="store_true", help="git remote prune every non-origin remote (loop homes)")
    ap.add_argument("--preserve-dir", type=Path, default=DEFAULT_PRESERVE_DIR)
    ap.add_argument("--format", choices=("text", "json"), default="text")
    args = ap.parse_args(argv)

    cwds, ledgers, heads = live_cwds(), load_ledgers(), origin_heads()
    items = [gather(wt, cwds, ledgers, heads) for wt in list_worktrees()]
    for wt in items:
        wt.verdict, wt.reason = verdict_for(wt)
    actionable = [wt for wt in items if wt.verdict in ("DELETE", "PRESERVE-THEN-DELETE", "DELETE-WORKTREE-KEEP-BRANCH", "PRUNE")]

    results: dict[str, object] = {"executed": args.execute, "removed": [], "preserved": [], "failed": [], "branches_deleted": 0}
    if args.execute:
        for wt in actionable:
            if wt.verdict == "PRUNE":
                continue
            if wt.verdict == "PRESERVE-THEN-DELETE":
                results["preserved"].append(str(preserve(wt, args.preserve_dir)))  # type: ignore[union-attr]
            (results["removed"] if remove_worktree(wt) else results["failed"]).append(wt.path)  # type: ignore[union-attr]
        _git("worktree", "prune")
        if args.delete_merged_local_branches:
            results["branches_deleted"], _ = delete_merged_local_branches()
        if args.prune_home_remotes:
            remotes, _ = _git("remote")
            for r in remotes.split():
                if r != "origin":
                    _git("remote", "prune", r)

    if args.format == "json":
        print(json.dumps({"worktrees": [asdict(w) for w in items], "results": results}, indent=1))
    else:
        counts: dict[str, int] = {}
        for wt in items:
            counts[wt.verdict] = counts.get(wt.verdict, 0) + 1
        print(f"worktree-sweep: {len(items)} registered; " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
        for wt in items:
            if wt.verdict == "KEEP" and wt.category in ("primary", "loop-home"):
                continue
            print(f"  {wt.verdict:28s} {wt.category:18s} {wt.last_commit:10s} +{wt.unmerged_commits:<2} dirty={len(wt.dirty_files):<2} "
                  f"{(wt.station or '-'):8s} {(wt.story_key or '-'):7s} {wt.ledger_status:14s} origin={'y' if wt.branch_on_origin else 'n'} {wt.branch[:56]}")
            print(f"  {'':28s} -> {wt.reason}")
        if args.execute:
            print(f"executed: removed {len(results['removed'])}, preserved {len(results['preserved'])} (under {args.preserve_dir}), failed {len(results['failed'])}, local branches deleted {results['branches_deleted']}")  # type: ignore[arg-type]
            for f in results["failed"]:  # type: ignore[union-attr]
                print(f"  FAILED: {f}")
        else:
            print(f"dry run: {len(actionable)} worktree(s) would be acted on; re-run with --execute")
    return 0


if __name__ == "__main__":
    sys.exit(main())
