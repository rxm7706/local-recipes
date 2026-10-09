#!/usr/bin/env python3
"""Repeatable worktree + branch hygiene sweep for this repo (operator tool).

Dry-run by default: classifies every registered git worktree and prints a
verdict per worktree. ``--execute`` applies the safe verdicts. The rule set is
the one settled in the 2026-09-05 shutdown sweep (memory:
`project_pixi_sweep_and_hygiene_2026-09-05.md`); the permanent home for this
logic is ``scripts/worktree_sweep.py`` (Phase 3 ruling 2026-10-03,
DW-HYGIENE-2026-09-05-1). ``marshal retire`` retires per-story branches; it
does not replace the sweeper.

Protected local branch prefixes (never deleted by ``--delete-merged-local-branches``):
``attempt-preserve/``, ``loop/``, ``recover/``, ``rescue/`` — aligned with
``docs/governance/guild-roster.json`` ``protected_refs`` branch entries. Tag
families ``preserve/``, ``archive/``, ``rescue/`` under ``refs/tags/`` are
server-side rules; this tool never deletes tags.

Verdicts, in priority order (first match wins):

  KEEP        primary checkout, a loop home (``~/.bmad-loops/<station>``), a
              live agent lock, a worktree with a live process cwd inside it,
              or an unmerged story that is not ledger-``done``.
  STALE-LOCK  locked worktree whose lock names a dead pid or a pid whose start
              time no longer matches the lock (merged/unmerged evidence in the
              reason). Merged STALE-LOCK worktrees are removable on ``--execute``;
              unmerged ones downgrade to INSPECT until preserve exists (87.8).
  PRUNE       registered path no longer exists -> ``git worktree prune``.
  DELETE      clean tree AND HEAD is an ancestor of main; or unmerged commits
              whose story is ledger-``done`` AND the branch is on origin; or
              the only dirt is untracked files / lock+manifest churn on a
              merged branch; or a merged STALE-LOCK worktree after unlock.
  PRESERVE-THEN-DELETE
              unmerged commits (story done, branch NOT on origin) or tracked
              uncommitted edits on a done story: ``git format-patch main..HEAD``
              plus ``git diff`` are written under --preserve-dir, then the
              worktree is removed. The branch is never deleted.
  DELETE-WORKTREE-KEEP-BRANCH
              an ``attempt-preserve/*`` branch: the branch is policy-protected,
              the worktree is disposable once the branch is on origin.
  INSPECT     unmerged/dirty with no ledger key to decide against; non-empty
              orphan directories; unmerged STALE-LOCK.
  ORPHAN-DIR  unregistered directory under ``.claude/worktrees/``,
              ``.cursor/worktrees/``, or ``~/.cursor/worktrees/`` (never
              ``~/.bmad-loops/``). Empty -> DELETE on ``--execute``; non-empty
              -> INSPECT.

Never touched: branches (this tool removes WORKTREES only, unless
``--delete-merged-local-branches`` is given, which safe-deletes local branches
that are ancestors of main, excluding protected prefixes), ``loop/<station>``
heads, ``attempt-preserve/*``, and the loop-home remotes (``marshal-home``,
``mason-home``) beyond ``git remote prune``.

Usage:
  python scripts/worktree_sweep.py                 # dry run, text table
  python scripts/worktree_sweep.py --format json   # machine-readable
  python scripts/worktree_sweep.py --format json \\
      > _bmad-output/projects/pyforge-marshal/implementation-artifacts/worktree-verdicts-$(date +%F).json
      # the dated Tier-3 record of a sweep (bmad-drift classifies it `local:sweep-verdicts`)
  python scripts/worktree_sweep.py --execute       # apply DELETE / PRESERVE-THEN-DELETE / D-W-K-B
  python scripts/worktree_sweep.py --execute --delete-merged-local-branches --prune-home-remotes
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
# Marshal Story 61.1 (review 3): `main` by its full refname -- a stray tag `main` on a feature
# commit made that feature read as merged, its worktree swept and its branch deleted.
MAIN_REF = "refs/heads/main"
HOME = Path.home()
LOOP_HOMES_ROOT = HOME / ".bmad-loops"
DEFAULT_PRESERVE_DIR = HOME / ".local" / "state" / "pyforge-marshal" / "worktree-preserve"
STATIONS = ("atlas", "doctor", "herald", "marshal", "mason", "scribe", "steward", "warden")
PROTECTED_BRANCH_PREFIXES = ("attempt-preserve/", "loop/", "recover/", "rescue/")
LIVE_STATUSES = frozenset({"backlog", "ready-for-dev", "in-progress", "blocked", "review", "awaiting-operator"})
CHURN_FILES = ("pixi.lock", "pyproject.toml", "pixi.toml")

# Claude Code agent worktree lock: `claude agent agent-<id> (pid N start T)`
_AGENT_LOCK_RE = re.compile(
    r"^claude agent agent-[^(]+ \(pid (\d+) start (\d+)\)$"
)

# Injected in tests: pid -> starttime from /proc (None = process absent)
ProcessStartLookup = Callable[[int], int | None]


def _default_process_start(pid: int) -> int | None:
    stat_path = Path(f"/proc/{pid}/stat")
    if not stat_path.is_file():
        return None
    try:
        # Field 22 (1-based) is starttime after the comm field in parentheses.
        parts = stat_path.read_text(encoding="utf-8").split()
        return int(parts[21])
    except (OSError, IndexError, ValueError):
        return None


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
    lock_reason: str = ""
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


@dataclass
class OrphanDir:
    path: str
    empty: bool
    verdict: str = ""
    reason: str = ""


# ---------------------------------------------------------------- discovery
def list_worktrees() -> list[Worktree]:
    out, _ = _git("worktree", "list", "--porcelain")
    items: list[Worktree] = []
    for block in [b for b in out.split("\n\n") if b.strip()]:
        d: dict[str, str | bool] = {}
        lock_reason = ""
        for line in block.splitlines():
            if line.startswith("locked "):
                d["locked"] = True
                lock_reason = line[len("locked ") :]
                continue
            k, _, v = line.partition(" ")
            d[k] = v if v else True
        path = str(d.get("worktree", ""))
        branch = str(d.get("branch", "(detached)")).replace("refs/heads/", "")
        items.append(
            Worktree(
                path=path,
                branch=branch,
                category=categorize(path),
                exists=os.path.isdir(path),
                prunable="prunable" in d,
                locked="locked" in d,
                lock_reason=lock_reason,
            )
        )
    return items


def categorize(path: str) -> str:
    p = Path(path)
    if p == REPO_ROOT:
        return "primary"
    if str(p).startswith(str(LOOP_HOMES_ROOT) + "/"):
        rel = str(p)[len(str(LOOP_HOMES_ROOT)) + 1 :]
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


def parse_agent_lock(lock_reason: str) -> tuple[int, int] | None:
    m = _AGENT_LOCK_RE.match(lock_reason.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def lock_is_live(lock_reason: str, lookup: ProcessStartLookup) -> bool | None:
    """True = live lock, False = stale, None = not an agent lock (caller decides)."""
    parsed = parse_agent_lock(lock_reason)
    if parsed is None:
        return None
    pid, recorded_start = parsed
    live_start = lookup(pid)
    if live_start is None:
        return False
    return live_start == recorded_start


def stale_lock_reason(lock_reason: str, lookup: ProcessStartLookup) -> str:
    parsed = parse_agent_lock(lock_reason)
    if parsed is None:
        return "locked (non-agent lock; treated as live)"
    pid, recorded_start = parsed
    live_start = lookup(pid)
    if live_start is None:
        return f"agent lock pid {pid} is not running"
    return f"agent lock pid {pid} start time {live_start} != recorded {recorded_start}"


def orphan_scan_roots() -> list[Path]:
    return [
        REPO_ROOT / ".claude" / "worktrees",
        REPO_ROOT / ".cursor" / "worktrees",
        HOME / ".cursor" / "worktrees",
    ]


def list_orphan_dirs(registered_paths: set[str]) -> list[OrphanDir]:
    orphans: list[OrphanDir] = []
    seen: set[str] = set()
    for root in orphan_scan_roots():
        if not root.is_dir():
            continue
        if str(root).startswith(str(LOOP_HOMES_ROOT)):
            continue
        try:
            children = list(root.iterdir())
        except OSError:
            continue
        for child in sorted(children):
            if not child.is_dir():
                continue
            path = str(child.resolve())
            if path in registered_paths or path in seen:
                continue
            seen.add(path)
            try:
                empty = not any(child.iterdir())
            except OSError:
                empty = False
            orphans.append(OrphanDir(path=path, empty=empty))
    return orphans


def verdict_for_orphan(od: OrphanDir) -> tuple[str, str]:
    if od.empty:
        return "ORPHAN-DIR", "empty unregistered worktree directory"
    return "INSPECT", "non-empty unregistered worktree directory"


# ---------------------------------------------------------------- mapping
def station_of(path: str, branch: str) -> str | None:
    m = (
        re.search(r"\.bmad-loops/pyforge-([a-z]+)/", path)
        or re.match(r"(%s)/" % "|".join(STATIONS), branch)
        or re.match(r"dispatch/pyforge-([a-z]+)/", branch)
        or re.search(r"-(%s)-\d+-\d+" % "|".join(STATIONS), branch)
    )
    return m.group(1) if m else None


def story_key_of(branch: str) -> str | None:
    seg = branch.split("/")[-1]
    m = re.search(r"-(%s)-(\d+)-(\d+)" % "|".join(STATIONS), seg)
    if m:
        return f"{m.group(2)}-{m.group(3)}"
    m = re.match(r"(?:story-)?([a-z]?\d+)[-.](\d+)[a-z]?(?:-|$)", seg)
    return f"{m.group(1)}-{m.group(2)}" if m else None


# ---------------------------------------------------------------- verdict
def verdict_for(wt: Worktree, *, lookup: ProcessStartLookup = _default_process_start) -> tuple[str, str]:
    """Pure rule engine over an already-gathered Worktree."""
    if wt.category in ("primary", "loop-home"):
        return "KEEP", f"{wt.category}: never swept"
    if wt.prunable or not wt.exists:
        return "PRUNE", "registered path no longer exists"
    if wt.locked:
        live = lock_is_live(wt.lock_reason, lookup)
        if live is None or live:
            return "KEEP", "worktree is locked"
        merged_ev = "merged" if wt.merged else "unmerged"
        detail = stale_lock_reason(wt.lock_reason, lookup)
        suffix = "eligible for removal" if wt.merged else "INSPECT until preserve exists (87.8)"
        return "STALE-LOCK", f"{detail}; {merged_ev} ({suffix})"
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


def effective_execute_verdict(wt: Worktree) -> str:
    """Map display verdicts to removal actions."""
    if wt.verdict == "STALE-LOCK" and wt.merged:
        return "DELETE"
    return wt.verdict


def gather(wt: Worktree, cwds: list[str], ledgers: dict, heads: set[str]) -> Worktree:
    if wt.category in ("primary", "loop-home") or not wt.exists or wt.prunable:
        return wt
    p = Path(wt.path)
    wt.live_cwd = any(c == wt.path or c.startswith(wt.path.rstrip("/") + "/") for c in cwds)
    st, _ = _git("status", "--porcelain", "--untracked-files=normal", cwd=p)
    wt.dirty_files = [line for line in st.splitlines() if line.strip()]
    _, rc = _git("merge-base", "--is-ancestor", "HEAD", MAIN_REF, cwd=p)
    wt.merged = rc == 0
    cnt, _ = _git("rev-list", "--count", f"{MAIN_REF}..HEAD", cwd=p)
    wt.unmerged_commits = int(cnt or 0)
    if wt.unmerged_commits:
        subj, _ = _git("log", "--format=%s", f"{MAIN_REF}..HEAD", cwd=p)
        wt.unmerged_subjects = subj.splitlines()[:3]
    wt.last_commit, _ = _git("log", "-1", "--format=%ad", "--date=short", cwd=p)
    wt.station = station_of(wt.path, wt.branch)
    wt.story_key = story_key_of(wt.branch)
    if wt.station and wt.story_key:
        wt.ledger_status = ledgers.get(wt.station, {}).get(wt.story_key, "not-in-ledger")
    wt.branch_on_origin = wt.branch in heads
    return wt


def unlock_worktree(path: str) -> bool:
    _, rc = _git("worktree", "unlock", path)
    return rc == 0


# ---------------------------------------------------------------- patch-id branch check (ancestor fallback only)
def branch_merged_by_patch_id(branch: str) -> bool:
    branch_ref = f"refs/heads/{branch}"
    ancestry, rc = _git("merge-base", "--is-ancestor", branch_ref, MAIN_REF)
    if rc == 0:
        return True
    if rc != 1:
        return False
    merge_base, rc = _git("merge-base", branch_ref, MAIN_REF)
    if rc != 0 or not merge_base:
        return False
    tree, rc = _git("rev-parse", f"{branch_ref}^{{tree}}")
    if rc != 0:
        return False
    base_tree, rc = _git("rev-parse", f"{merge_base}^{{tree}}")
    if rc != 0:
        return False
    if tree == base_tree:
        return True
    r = subprocess.run(
        [
            "git",
            "-c",
            "user.name=worktree-sweep",
            "-c",
            "user.email=worktree-sweep@localhost",
            "-c",
            "commit.gpgsign=false",
            "commit-tree",
            tree,
            "-p",
            merge_base,
            "-m",
            "worktree-sweep patch-id check",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    commit_tree = r.stdout.strip()
    if r.returncode != 0 or not commit_tree:
        return False
    cherry, rc = _git("cherry", MAIN_REF, commit_tree)
    if rc != 0:
        return False
    for line in cherry.splitlines():
        if line.startswith("- "):
            return True
    return False


# ---------------------------------------------------------------- actions
def preserve(wt: Worktree, preserve_dir: Path) -> Path:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", wt.branch)
    dest = preserve_dir / slug
    dest.mkdir(parents=True, exist_ok=True)
    p = Path(wt.path)
    if wt.unmerged_commits:
        subprocess.run(["git", "format-patch", "-o", str(dest), f"{MAIN_REF}..HEAD"], capture_output=True, text=True, cwd=str(p))
    diff, _ = _git("diff", cwd=p)
    if diff:
        (dest / "uncommitted.diff").write_text(diff + "\n", encoding="utf-8")
    untracked, _ = _git("ls-files", "--others", "--exclude-standard", cwd=p)
    if untracked:
        (dest / "untracked-files.txt").write_text(untracked + "\n", encoding="utf-8")
    (dest / "origin.json").write_text(json.dumps(asdict(wt), indent=1), encoding="utf-8")
    return dest


def remove_worktree(wt: Worktree, *, unlock_first: bool = False) -> bool:
    """Re-check the verdict-relevant facts immediately before removal."""
    p = Path(wt.path)
    if not p.is_dir():
        return False
    if unlock_first and wt.locked:
        unlock_worktree(wt.path)
    st, _ = _git("status", "--porcelain", "--untracked-files=normal", cwd=p)
    if wt.verdict == "DELETE" and not wt.dirty_files and st.strip():
        return False  # became dirty since classification
    _, rc = _git("worktree", "remove", "--force", wt.path)
    if rc != 0:
        subprocess.run(["chmod", "-R", "u+w", wt.path], capture_output=True)
        _, rc = _git("worktree", "remove", "--force", wt.path)
    return rc == 0 and not p.exists()


def remove_orphan_dir(od: OrphanDir) -> bool:
    p = Path(od.path)
    if not p.is_dir():
        return False
    try:
        if any(p.iterdir()):
            return False
    except OSError:
        return False
    shutil.rmtree(p)
    return not p.exists()


def delete_merged_local_branches() -> tuple[int, list[str], list[str]]:
    out, _ = _git("branch", "--merged", MAIN_REF, "--format=%(refname:lstrip=2) %(worktreepath)")
    deleted, kept, patch_equivalent = 0, [], []
    for line in out.splitlines():
        name, _, wtpath = line.partition(" ")
        if name == "main" or wtpath.strip() or name.startswith(PROTECTED_BRANCH_PREFIXES):
            continue
        _, rc = _git("merge-base", "--is-ancestor", f"refs/heads/{name}", MAIN_REF)
        if rc != 0:
            if branch_merged_by_patch_id(name):
                patch_equivalent.append(name)
            else:
                kept.append(name)
            continue
        _, rc = _git("branch", "-D", name)
        deleted += 1 if rc == 0 else 0
    return deleted, kept, patch_equivalent


# ---------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--execute", action="store_true", help="apply DELETE / PRESERVE-THEN-DELETE / DELETE-WORKTREE-KEEP-BRANCH / PRUNE")
    ap.add_argument("--delete-merged-local-branches", action="store_true", help="also safe-delete local branches that are ancestors of main (never protected prefixes)")
    ap.add_argument("--prune-home-remotes", action="store_true", help="git remote prune every non-origin remote (loop homes)")
    ap.add_argument("--preserve-dir", type=Path, default=DEFAULT_PRESERVE_DIR)
    ap.add_argument("--format", choices=("text", "json"), default="text")
    args = ap.parse_args(argv)

    cwds, ledgers, heads = live_cwds(), load_ledgers(), origin_heads()
    items = [gather(wt, cwds, ledgers, heads) for wt in list_worktrees()]
    for wt in items:
        wt.verdict, wt.reason = verdict_for(wt)
    registered = {wt.path for wt in items}
    orphans = list_orphan_dirs(registered)
    for od in orphans:
        od.verdict, od.reason = verdict_for_orphan(od)

    actionable = [
        wt
        for wt in items
        if effective_execute_verdict(wt) in ("DELETE", "PRESERVE-THEN-DELETE", "DELETE-WORKTREE-KEEP-BRANCH", "PRUNE")
    ]
    orphan_actionable = [od for od in orphans if od.verdict == "ORPHAN-DIR"]

    results: dict[str, object] = {
        "executed": args.execute,
        "removed": [],
        "preserved": [],
        "failed": [],
        "orphans_removed": [],
        "orphans_failed": [],
        "branches_deleted": 0,
        "patch_equivalent_branches": [],
    }
    if args.execute:
        for wt in actionable:
            if wt.verdict == "PRUNE":
                continue
            exec_v = effective_execute_verdict(wt)
            unlock = wt.verdict == "STALE-LOCK" and wt.merged
            if exec_v == "PRESERVE-THEN-DELETE":
                results["preserved"].append(str(preserve(wt, args.preserve_dir)))  # type: ignore[union-attr]
            removed = remove_worktree(wt, unlock_first=unlock)
            (results["removed"] if removed else results["failed"]).append(wt.path)  # type: ignore[union-attr]
        for od in orphan_actionable:
            (results["orphans_removed"] if remove_orphan_dir(od) else results["orphans_failed"]).append(od.path)  # type: ignore[union-attr]
        _git("worktree", "prune")
        if args.delete_merged_local_branches:
            deleted, _, patch_eq = delete_merged_local_branches()
            results["branches_deleted"] = deleted
            results["patch_equivalent_branches"] = patch_eq
        if args.prune_home_remotes:
            remotes, _ = _git("remote")
            for r in remotes.split():
                if r != "origin":
                    _git("remote", "prune", r)
    elif args.delete_merged_local_branches:
        _, _, patch_eq = delete_merged_local_branches()
        results["patch_equivalent_branches"] = patch_eq

    if args.format == "json":
        print(
            json.dumps(
                {
                    "worktrees": [asdict(w) for w in items],
                    "orphan_dirs": [asdict(o) for o in orphans],
                    "results": results,
                },
                indent=1,
            )
        )
    else:
        counts: dict[str, int] = {}
        for wt in items:
            counts[wt.verdict] = counts.get(wt.verdict, 0) + 1
        for od in orphans:
            counts[od.verdict] = counts.get(od.verdict, 0) + 1
        print(
            f"worktree-sweep: {len(items)} registered, {len(orphans)} orphan dir(s); "
            + ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
        )
        for wt in items:
            if wt.verdict == "KEEP" and wt.category in ("primary", "loop-home"):
                continue
            print(
                f"  {wt.verdict:28s} {wt.category:18s} {wt.last_commit:10s} +{wt.unmerged_commits:<2} "
                f"dirty={len(wt.dirty_files):<2} {(wt.station or '-'):8s} {(wt.story_key or '-'):7s} "
                f"{wt.ledger_status:14s} origin={'y' if wt.branch_on_origin else 'n'} {wt.branch[:56]}"
            )
            print(f"  {'':28s} -> {wt.reason}")
        for od in orphans:
            print(f"  {od.verdict:28s} orphan-dir         {'':10s} empty={'y' if od.empty else 'n'} {od.path}")
            print(f"  {'':28s} -> {od.reason}")
        patch_eq = results.get("patch_equivalent_branches") or []
        if patch_eq:
            print(f"patch-equivalent (reported, not deleted): {', '.join(patch_eq)}")
        if args.execute:
            print(
                f"executed: removed {len(results['removed'])}, preserved {len(results['preserved'])} "
                f"(under {args.preserve_dir}), failed {len(results['failed'])}, "
                f"orphans removed {len(results['orphans_removed'])}, "
                f"local branches deleted {results['branches_deleted']}"
            )
            for f in results["failed"]:  # type: ignore[union-attr]
                print(f"  FAILED: {f}")
        else:
            print(
                f"dry run: {len(actionable)} worktree(s) and {len(orphan_actionable)} orphan(s) "
                f"would be acted on; re-run with --execute"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
