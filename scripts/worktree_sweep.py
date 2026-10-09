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
  python scripts/worktree_sweep.py --remote              # dry run: verdict per origin branch
  python scripts/worktree_sweep.py --remote --execute    # delete DELETE verdicts on origin (manifest first)
  python scripts/worktree_sweep.py --retire branch/name  # explicit-name retirement (never patterns)
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
import tempfile
from dataclasses import asdict, dataclass, field
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

REPO_ROOT = Path(__file__).resolve().parents[1]
_CORE_SRC = REPO_ROOT / "src" / "shared" / "packages" / "pyforge-core" / "src"
if str(_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(_CORE_SRC))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

import _protected_refs_ruleset_lib as pr_rules
from pyforge.core import preserve_refs
from pyforge.core.flags import read_boolean

PRESERVE_REFS_FLAG = "pyforge.marshal.preserve_refs"
# Marshal Story 61.1 (review 3): `main` by its full refname -- a stray tag `main` on a feature
# commit made that feature read as merged, its worktree swept and its branch deleted.
MAIN_REF = "refs/heads/main"
ORIGIN_MAIN_REF = preserve_refs.ORIGIN_MAIN
ROSTER_PATH = REPO_ROOT / "docs" / "governance" / "guild-roster.json"
PROTECTED_CODE_FLOOR = frozenset({"refs/heads/main", "refs/heads/loop/", "refs/tags/"})
RULESET_OPERATOR_ACT = (
    "Protected refs are not deleted from an agent session — hand the operator the branch "
    "to retire, and remove a loop home only after an explicit operator decision."
)
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


@dataclass
class EngineScratchRow:
    refname: str
    commit: str
    verdict: str
    reason: str = ""


@dataclass
class PreserveToTagOutcome:
    refname: str
    pushed: bool
    debt: str = ""


def _flags_path() -> Path:
    return REPO_ROOT / "src/platform/config/flags.json"


def preserve_refs_flag_on() -> bool:
    return read_boolean(PRESERVE_REFS_FLAG, default=False, flags_path=_flags_path())


def _feed_story_key(story_key: str | None) -> str | None:
    if not story_key:
        return None
    m = re.match(r"^(\d+)-(\d+)([a-z])?$", story_key)
    if m:
        suffix = m.group(3) or ""
        return f"{m.group(1)}.{m.group(2)}{suffix}"
    return story_key


def _project_slug(station: str | None) -> str | None:
    return f"pyforge-{station}" if station else None


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


def preserve_worktree_as_tag(wt: Worktree) -> PreserveToTagOutcome:
    """Write a local ``sweep`` preserve tag (and try push) before worktree removal."""
    p = Path(wt.path)
    commit: str | None = None
    try:
        commit = preserve_refs.snapshot_worktree_commit(p)
    except preserve_refs.PreserveGitError:
        commit = None
    if commit is None:
        head, rc = _git("rev-parse", "HEAD", cwd=p)
        if rc != 0:
            raise preserve_refs.PreserveGitError(f"cannot read HEAD in {wt.path}")
        commit = head
    project = _project_slug(wt.station)
    story = _feed_story_key(wt.story_key)
    refname = preserve_refs.render_preserve_ref(
        commit_sha=commit,
        producer="sweep",
        project_slug=project,
        story_key=story,
    )
    source = preserve_refs.normalize_ref(wt.branch)
    trailers = preserve_refs.PreserveTrailers(
        producer="sweep",
        provenance="machine",
        reason=wt.reason or "worktree-sweep PRESERVE-THEN-DELETE",
        source=source,
        run="",
        journal="",
        commit=commit,
    )
    tagged = preserve_refs.tag_preserve(REPO_ROOT, refname=refname, commit=commit, trailers=trailers)
    pushed = False
    debt = ""
    purge_path = preserve_refs.default_purge_list_path(REPO_ROOT)
    try:
        push_result = preserve_refs.push_preserve_ref(REPO_ROOT, tagged.refname, purge_list_path=purge_path)
        pushed = push_result.pushed
        if not pushed:
            debt = "; ".join(f.message for f in push_result.findings) or "content gate refused push"
    except preserve_refs.PreserveGitError as exc:
        debt = str(exc)
    return PreserveToTagOutcome(refname=tagged.refname, pushed=pushed, debt=debt)


def _iter_engine_scratch_refs() -> list[tuple[str, str]]:
    fmt = "%(refname)\x1f%(objectname)"
    out, rc = _git(
        "for-each-ref",
        f"--format={fmt}",
        f"refs/heads/{preserve_refs.ATTEMPT_PRESERVE_BRANCH_PREFIX}",
        preserve_refs.ATTEMPT_PRESERVE_DIRTY_PREFIX,
    )
    if rc != 0:
        return []
    refs: list[tuple[str, str]] = []
    for line in out.splitlines():
        if "\x1f" not in line:
            continue
        refname, commit = line.split("\x1f", 1)
        refname, commit = refname.strip(), commit.strip()
        if refname and commit:
            refs.append((refname, commit))
    return sorted(refs)


def _engine_scratch_promoted(refname: str, commit: str) -> bool:
    want = preserve_refs.normalize_ref(refname)
    short = preserve_refs.short_ref_name(want)
    for rec in preserve_refs.list_preserves(REPO_ROOT):
        src = rec.trailers.source
        if src not in (want, short, refname, preserve_refs.short_ref_name(refname)):
            continue
        _, rc = _git("merge-base", "--is-ancestor", commit, rec.object_sha)
        if rc == 0:
            return True
    return False


def verdict_for_engine_scratch(refname: str, commit: str) -> tuple[str, str]:
    if not preserve_refs_flag_on():
        return "KEEP", "engine scratch (flag off)"
    if _engine_scratch_promoted(refname, commit):
        return "DELETE", "promoted engine scratch"
    return "KEEP", "unpromoted scratch"


def classify_engine_scratch_refs() -> list[EngineScratchRow]:
    rows: list[EngineScratchRow] = []
    for refname, commit in _iter_engine_scratch_refs():
        verdict, reason = verdict_for_engine_scratch(refname, commit)
        rows.append(EngineScratchRow(refname=refname, commit=commit, verdict=verdict, reason=reason))
    return rows


def _delete_local_ref(refname: str) -> bool:
    if refname.startswith("refs/heads/"):
        _, rc = _git("branch", "-D", refname.removeprefix("refs/heads/"))
        return rc == 0
    _, rc = _git("update-ref", "-d", refname)
    return rc == 0


def retire_promoted_engine_scratch(*, apply: bool) -> tuple[list[EngineScratchRow], list[str]]:
    rows = classify_engine_scratch_refs()
    retired: list[str] = []
    for row in rows:
        if row.verdict != "DELETE" or not apply:
            continue
        if _delete_local_ref(row.refname):
            retired.append(row.refname)
    return rows, retired


def _local_ref_is_tag(name: str) -> bool:
    _, rc = _git("rev-parse", "--verify", "--quiet", f"refs/tags/{name}^{{}}")
    return rc == 0


def remove_worktree(wt: Worktree, *, unlock_first: bool = False) -> bool:
    """Re-check the verdict-relevant facts immediately before removal."""
    p = Path(wt.path)
    if not p.is_dir():
        return False
    if unlock_first and wt.locked and not unlock_worktree(wt.path):
        return False
    st, _ = _git("status", "--porcelain", "--untracked-files=normal", cwd=p)
    exec_v = effective_execute_verdict(wt)
    if exec_v == "DELETE" and not wt.dirty_files and st.strip():
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
    try:
        shutil.rmtree(p)
    except OSError:
        return False
    return not p.exists()


def delete_merged_local_branches(*, apply: bool = True) -> tuple[int, list[str], list[str]]:
    out, _ = _git("branch", "--merged", MAIN_REF, "--format=%(refname:lstrip=2) %(worktreepath)")
    deleted, kept, patch_equivalent = 0, [], []
    flag_on = preserve_refs_flag_on()
    for line in out.splitlines():
        name, _, wtpath = line.partition(" ")
        if name == "main" or wtpath.strip() or name.startswith(PROTECTED_BRANCH_PREFIXES):
            continue
        if _local_ref_is_tag(name):
            continue
        _, rc = _git("merge-base", "--is-ancestor", f"refs/heads/{name}", MAIN_REF)
        if rc != 0:
            if branch_merged_by_patch_id(name):
                patch_equivalent.append(name)
            else:
                kept.append(name)
            continue
        if apply:
            if flag_on:
                tip, tip_rc = _git("rev-parse", f"refs/heads/{name}")
                if tip_rc == 0 and deletion_would_orphan_commits(tip):
                    archive_ref, err = ensure_local_archive_twin(name, tip)
                    if not archive_ref and err:
                        kept.append(name)
                        continue
            _, rc = _git("branch", "-D", name)
            deleted += 1 if rc == 0 else 0
    return deleted, kept, patch_equivalent


# ---------------------------------------------------------------- remote + retire (Story 87.1)
class PrStateReader(Protocol):
    def __call__(self, branch: str) -> dict[str, str] | None:
        """Return PR facts for ``branch`` (keys: state, head) or None if no PR."""


@dataclass
class RemoteBranchRow:
    branch: str
    sha: str
    verdict: str
    reason: str
    archive_tag: str = ""


@dataclass
class SweepFinding:
    branch: str
    code: str
    message: str


def ref_matches_prefix(refname: str, prefix: str) -> bool:
    if refname == prefix:
        return True
    if prefix.endswith("/") and refname.startswith(prefix):
        return True
    if not prefix.endswith("/") and refname.startswith(prefix + "/"):
        return True
    return False


def ref_matches_any_prefix(refname: str, prefixes: frozenset[str] | set[str]) -> bool:
    return any(ref_matches_prefix(refname, p) for p in prefixes)


def branch_head_refname(branch: str) -> str:
    branch = branch.strip()
    if branch.startswith("refs/heads/"):
        return branch
    return f"refs/heads/{branch}"


def load_roster() -> dict:
    try:
        return json.loads(ROSTER_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def roster_deletion_protected_prefixes(roster: dict | None = None) -> frozenset[str]:
    roster = roster if roster is not None else load_roster()
    entries = roster.get("protected_refs")
    if not isinstance(entries, list):
        return frozenset()
    out: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        refname = entry.get("refname")
        rules = entry.get("rules")
        if not isinstance(refname, str) or not isinstance(rules, list):
            continue
        if "deletion" in rules and refname.startswith("refs/heads/"):
            out.add(refname)
    return frozenset(out)


def effective_protected_prefixes(roster: dict | None = None) -> frozenset[str]:
    return PROTECTED_CODE_FLOOR | roster_deletion_protected_prefixes(roster)


def is_protected_branch_name(branch: str, *, protected_prefixes: frozenset[str] | None = None) -> bool:
    prefixes = protected_prefixes if protected_prefixes is not None else effective_protected_prefixes()
    head = branch_head_refname(branch)
    if ref_matches_any_prefix(head, prefixes):
        return True
    if branch == "main" or branch.startswith("loop/"):
        return True
    if branch.startswith(PROTECTED_BRANCH_PREFIXES):
        return True
    return False


def ruleset_deletion_refusal(branch: str, roster: dict | None = None) -> tuple[str, str] | None:
    """If GitHub ruleset forbids deleting this branch, return (ruleset_name, operator_act)."""
    roster = roster if roster is not None else load_roster()
    head = branch_head_refname(branch)
    for entry in roster.get("protected_refs", []):
        if not isinstance(entry, dict):
            continue
        refname = entry.get("refname")
        if not isinstance(refname, str) or not refname.startswith("refs/heads/"):
            continue
        if not ref_matches_prefix(head, refname):
            continue
        rules = pr_rules.expected_rules_for_entry(entry)
        if "deletion" not in rules:
            continue
        name = pr_rules._ruleset_name_for_branch_rules(rules)
        return name, RULESET_OPERATOR_ACT
    return None


def branches_in_worktrees() -> set[str]:
    branches: set[str] = set()
    for wt in list_worktrees():
        b = wt.branch
        if b and b != "(detached)":
            branches.add(b)
    return branches


def _dispatch_run_terminal_kinds() -> frozenset[str]:
    return frozenset(
        {
            "dispatch-finalize",
            "dispatch-land",
            "dispatch-blocked",
        }
    )


def live_dispatch_branches() -> set[str]:
    """Branches belonging to a dispatch run whose journal has no terminal finalize/land."""
    live: set[str] = set()
    pattern = str(REPO_ROOT / "_bmad-output/projects/pyforge-*/implementation-artifacts/dispatch-runs/*/journal.jsonl")
    terminal = _dispatch_run_terminal_kinds()
    for journal_path in glob.glob(pattern):
        path = Path(journal_path)
        try:
            lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        except OSError:
            continue
        if not lines:
            continue
        run_live = True
        branch: str | None = None
        for line in lines:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = entry.get("kind", "")
            if kind in terminal:
                payload = entry.get("payload") or {}
                if kind == "dispatch-finalize" and payload.get("ok") is True:
                    run_live = False
                if kind == "dispatch-land" and payload.get("verdict") in ("landed", "already_landed"):
                    run_live = False
                if kind == "dispatch-blocked":
                    run_live = False
            if kind == "dispatch-launch":
                payload = entry.get("payload") or {}
                branch = payload.get("worktree_branch") or payload.get("branch")
        if run_live and branch:
            live.add(str(branch).removeprefix("refs/heads/"))
    return live


def flat_ledger() -> dict[str, str]:
    merged: dict[str, str] = {}
    for keys in load_ledgers().values():
        merged.update(keys)
    return merged


def ledger_status_for_branch(branch: str, ledgers: dict[str, dict[str, str]]) -> str:
    story = story_key_of(branch)
    if not story:
        return "not-in-ledger"
    station = station_of("", branch)
    if station:
        return ledgers.get(station, {}).get(story, "not-in-ledger")
    for keys in ledgers.values():
        if story in keys:
            return keys[story]
    return "not-in-ledger"


GITHUB_REPO = "rxm7706/local-recipes"


def load_pr_states_from_github(*, timeout: int = 120) -> dict[str, dict[str, str]]:
    """Head branch name -> ``{state, head}`` for open/merged/closed PRs (operator tool; tests inject instead)."""
    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                GITHUB_REPO,
                "--state",
                "all",
                "--limit",
                "500",
                "--json",
                "headRefName,state",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )
        payload = json.loads(result.stdout or "[]")
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        return {}
    if not isinstance(payload, list):
        return {}
    by_head: dict[str, dict[str, str]] = {}
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        head = entry.get("headRefName")
        state_raw = entry.get("state")
        if not isinstance(head, str) or not head or not isinstance(state_raw, str):
            continue
        normalized = state_raw.lower()
        if normalized not in ("open", "merged", "closed"):
            normalized = "closed"
        by_head[head] = {"state": normalized, "head": head}
    return by_head


def default_pr_reader() -> PrStateReader:
    def _read(branch: str) -> dict[str, str] | None:
        return None

    return _read


def github_pr_reader(states: dict[str, dict[str, str]] | None = None) -> PrStateReader:
    cached = states if states is not None else load_pr_states_from_github()

    def _read(branch: str) -> dict[str, str] | None:
        return cached.get(branch)

    return _read


def tip_is_ancestor_of_origin_main(tip_sha: str) -> bool:
    _, rc = _git("merge-base", "--is-ancestor", tip_sha, ORIGIN_MAIN_REF)
    return rc == 0


def commit_reachable_from_preserve_or_archive_tag(tip_sha: str) -> bool:
    out, rc = _git(
        "for-each-ref",
        "--contains",
        tip_sha,
        "--format=%(refname)",
        preserve_refs.PRESERVE_REF_PREFIX,
        preserve_refs.ARCHIVE_REF_PREFIX,
    )
    return rc == 0 and bool(out.strip())


def deletion_would_orphan_commits(tip_sha: str) -> bool:
    if tip_is_ancestor_of_origin_main(tip_sha):
        return False
    if commit_reachable_from_preserve_or_archive_tag(tip_sha):
        return False
    return True


def remote_branch_map() -> dict[str, str]:
    out, rc = _git("ls-remote", "--heads", "origin")
    if rc != 0:
        return {}
    mapping: dict[str, str] = {}
    for line in out.splitlines():
        if not line.strip():
            continue
        try:
            sha, ref = line.split(maxsplit=1)
        except ValueError:
            continue
        mapping[ref.removeprefix("refs/heads/")] = sha
    return mapping


def verdict_for_remote_branch(
    branch: str,
    sha: str,
    *,
    pr_reader: PrStateReader,
    checked_out: set[str],
    dispatch_live: set[str],
    ledgers: dict[str, dict[str, str]],
    protected_prefixes: frozenset[str],
) -> tuple[str, str]:
    if branch == "main":
        return "KEEP", "main is never deleted"
    if is_protected_branch_name(branch, protected_prefixes=protected_prefixes):
        return "KEEP", "protected prefix or code floor"
    if branch in checked_out:
        return "KEEP", "branch checked out in a worktree"
    if branch in dispatch_live:
        return "KEEP", "live dispatch run branch"
    pr = pr_reader(branch)
    if pr and pr.get("state") == "open":
        return "KEEP", "open pull request head"
    if tip_is_ancestor_of_origin_main(sha):
        return "DELETE", "tip is an ancestor of origin/main"
    if pr and pr.get("state") == "merged":
        return "DELETE", "pull request merged"
    if pr and pr.get("state") == "closed":
        status = ledger_status_for_branch(branch, ledgers)
        if status == "done":
            return "DELETE", "pull request closed and ledger story is done"
        return "INSPECT", f"pull request closed but story is {status}"
    return "INSPECT", "unmerged with no open PR and no ledger decision"


def classify_remote_branches(
    *,
    pr_reader: PrStateReader | None = None,
    roster: dict | None = None,
) -> list[RemoteBranchRow]:
    reader = pr_reader if pr_reader is not None else github_pr_reader()
    protected = effective_protected_prefixes(roster)
    checked_out = branches_in_worktrees()
    dispatch_live = live_dispatch_branches()
    ledgers = load_ledgers()
    rows: list[RemoteBranchRow] = []
    for branch, sha in sorted(remote_branch_map().items()):
        verdict, reason = verdict_for_remote_branch(
            branch,
            sha,
            pr_reader=reader,
            checked_out=checked_out,
            dispatch_live=dispatch_live,
            ledgers=ledgers,
            protected_prefixes=protected,
        )
        rows.append(RemoteBranchRow(branch=branch, sha=sha, verdict=verdict, reason=reason))
    return rows


def write_sweep_manifest(rows: list[RemoteBranchRow], preserve_dir: Path) -> Path:
    preserve_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = preserve_dir / f"remote-sweep-manifest-{stamp}.json"
    payload = {
        "written_at": stamp,
        "rows": [asdict(r) for r in rows],
    }
    dest.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    return dest


def _archive_tag_message(branch: str, commit: str) -> str:
    trailers = preserve_refs.PreserveTrailers(
        producer="sweep",
        provenance="machine",
        reason="worktree-sweep archive twin before branch delete",
        source=branch,
        run="",
        journal="",
        commit=commit,
    )
    return trailers.format_message()


def ensure_local_archive_twin(branch: str, tip_sha: str) -> tuple[str | None, str]:
    """Create a local ``archive/heads`` twin when deletion would orphan commits."""
    if not deletion_would_orphan_commits(tip_sha):
        return "", ""
    refname = preserve_refs.render_archive_heads_ref(branch)
    short_ref = refname.removeprefix("refs/tags/")
    _, rc = _git("rev-parse", "--verify", f"{refname}^{{commit}}")
    if rc != 0:
        msg = _archive_tag_message(branch, tip_sha)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as tf:
            tf.write(msg)
            msg_path = tf.name
        try:
            _, tag_rc = _git("tag", "-a", "-F", msg_path, short_ref, tip_sha)
        finally:
            try:
                os.unlink(msg_path)
            except OSError:
                pass
        if tag_rc != 0:
            return None, "failed to create local archive tag"
    return refname, ""


def write_and_push_archive_twin(branch: str, tip_sha: str) -> tuple[str | None, str]:
    """Create and push archive/heads twin; return (refname, error_reason)."""
    refname, err = ensure_local_archive_twin(branch, tip_sha)
    if err or not refname:
        return refname, err
    if refname == "":
        return "", ""
    purge_path = preserve_refs.default_purge_list_path(REPO_ROOT)
    try:
        push_result = preserve_refs.push_preserve_ref(REPO_ROOT, refname, purge_list_path=purge_path)
    except preserve_refs.PreserveGitError as exc:
        return None, str(exc)
    if not push_result.pushed:
        detail = "; ".join(f.message for f in push_result.findings) or "content gate refused push"
        return None, detail
    return refname, ""


def delete_remote_branch(branch: str) -> tuple[bool, str]:
    ref = branch_head_refname(branch)
    _, rc = _git("push", "origin", f":{ref}")
    if rc == 0:
        return True, ""
    _, verify_rc = _git("ls-remote", "--heads", "origin", ref)
    if verify_rc == 0:
        out, _ = _git("ls-remote", "--heads", "origin", ref)
        if out.strip():
            return False, "git push delete refused (branch still on origin)"
    return False, "git push delete failed"


def execute_remote_deletes(
    rows: list[RemoteBranchRow],
    *,
    apply: bool,
    preserve_dir: Path,
) -> tuple[list[SweepFinding], list[RemoteBranchRow]]:
    """Apply DELETE rows; mutates row archive_tag fields. Returns findings and updated rows."""
    findings: list[SweepFinding] = []
    delete_rows = [r for r in rows if r.verdict == "DELETE"]
    manifest_path: Path | None = None
    if apply and delete_rows:
        manifest_path = write_sweep_manifest(rows, preserve_dir)  # full table before the first delete
    for row in delete_rows:
        if not apply:
            continue
        archive_ref, err = write_and_push_archive_twin(row.branch, row.sha)
        if err:
            row.reason = f"{row.reason}; archive twin refused: {err}"
            findings.append(
                SweepFinding(row.branch, "archive-twin-refused", err),
            )
            continue
        if archive_ref:
            row.archive_tag = archive_ref
        ok, del_err = delete_remote_branch(row.branch)
        if not ok:
            findings.append(SweepFinding(row.branch, "github-delete-refused", del_err or "delete refused"))
    if manifest_path is not None:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        payload["rows"] = [asdict(r) for r in rows]
        manifest_path.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    return findings, rows


def run_retire_branches(
    names: list[str],
    *,
    apply: bool,
    preserve_dir: Path,
    roster: dict | None = None,
) -> tuple[list[RemoteBranchRow], list[SweepFinding]]:
    roster = roster if roster is not None else load_roster()
    remote = remote_branch_map()
    rows: list[RemoteBranchRow] = []
    findings: list[SweepFinding] = []
    for raw in names:
        branch = raw.strip()
        if (
            not branch
            or branch != raw
            or any(c in branch for c in "*?[]\\")
        ):
            findings.append(SweepFinding(branch or raw, "invalid-name", "retire requires an explicit branch name, never a pattern"))
            continue
        if branch not in remote:
            findings.append(SweepFinding(branch, "missing-branch", "branch not found on origin"))
            rows.append(RemoteBranchRow(branch, "", "REFUSE", "branch not found on origin"))
            continue
        sha = remote[branch]
        refusal = ruleset_deletion_refusal(branch, roster)
        if refusal:
            ruleset_name, operator_act = refusal
            msg = f"ruleset {ruleset_name}: {operator_act}"
            findings.append(SweepFinding(branch, ruleset_name, msg))
            rows.append(RemoteBranchRow(branch, sha, "REFUSE", msg))
            continue
        protected = is_protected_branch_name(branch, protected_prefixes=effective_protected_prefixes(roster))
        legacy_protected = branch.startswith(PROTECTED_BRANCH_PREFIXES)
        if not protected and not legacy_protected:
            findings.append(
                SweepFinding(
                    branch,
                    "not-protected",
                    "only protected branches are retired via --retire; use --remote for ordinary branches",
                )
            )
            rows.append(RemoteBranchRow(branch, sha, "REFUSE", "not a protected branch name"))
            continue
        rows.append(RemoteBranchRow(branch, sha, "RETIRE", "explicit --retire"))
    manifest_path: Path | None = None
    if apply and rows:
        manifest_path = write_sweep_manifest(rows, preserve_dir)
    for row in rows:
        if row.verdict != "RETIRE" or not apply:
            continue
        archive_ref, err = write_and_push_archive_twin(row.branch, row.sha)
        if err:
            row.verdict = "REFUSE"
            row.reason = f"archive twin refused: {err}"
            findings.append(SweepFinding(row.branch, "archive-twin-refused", err))
            continue
        if archive_ref:
            row.archive_tag = archive_ref
        ok, del_err = delete_remote_branch(row.branch)
        if not ok:
            row.verdict = "REFUSE"
            row.reason = del_err or "delete refused"
            findings.append(SweepFinding(row.branch, "github-delete-refused", row.reason))
    if manifest_path is not None:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        payload["rows"] = [asdict(r) for r in rows]
        manifest_path.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    return rows, findings


# ---------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--execute", action="store_true", help="apply DELETE / PRESERVE-THEN-DELETE / DELETE-WORKTREE-KEEP-BRANCH / PRUNE")
    ap.add_argument("--delete-merged-local-branches", action="store_true", help="also safe-delete local branches that are ancestors of main (never protected prefixes)")
    ap.add_argument("--prune-home-remotes", action="store_true", help="git remote prune every non-origin remote (loop homes)")
    ap.add_argument("--preserve-dir", type=Path, default=DEFAULT_PRESERVE_DIR)
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--remote", action="store_true", help="classify (and optionally delete) origin branches")
    ap.add_argument(
        "--retire",
        nargs="+",
        default=[],
        metavar="BRANCH",
        help="retire explicit protected branch names on origin (never patterns)",
    )
    args = ap.parse_args(argv)

    remote_results: dict[str, object] | None = None
    retire_results: dict[str, object] | None = None
    if args.remote:
        remote_rows = classify_remote_branches()
        remote_findings, remote_rows = execute_remote_deletes(
            remote_rows, apply=args.execute, preserve_dir=args.preserve_dir
        )
        remote_results = {
            "remote_branches": [asdict(r) for r in remote_rows],
            "findings": [asdict(f) for f in remote_findings],
        }
    if args.retire:
        retire_rows, retire_findings = run_retire_branches(
            args.retire, apply=args.execute, preserve_dir=args.preserve_dir
        )
        retire_results = {
            "retire_branches": [asdict(r) for r in retire_rows],
            "findings": [asdict(f) for f in retire_findings],
        }
    if args.remote or args.retire:
        if args.format == "json":
            print(json.dumps({"remote": remote_results, "retire": retire_results}, indent=1))
        else:
            if remote_results:
                counts: dict[str, int] = {}
                for row in remote_results["remote_branches"]:  # type: ignore[index]
                    v = row["verdict"]
                    counts[v] = counts.get(v, 0) + 1
                print(
                    f"remote-sweep: {len(remote_results['remote_branches'])} origin branch(es); "  # type: ignore[index]
                    + ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
                )
                for row in remote_results["remote_branches"]:  # type: ignore[index]
                    if row["verdict"] == "KEEP" and row["branch"] == "main":
                        continue
                    print(f"  {row['verdict']:8s} {row['branch'][:56]:56s} {row['sha'][:8]}  {row['reason']}")
                for f in remote_results.get("findings") or []:  # type: ignore[union-attr]
                    print(f"  FINDING {f['code']}: {f['branch']} — {f['message']}")
            if retire_results:
                for row in retire_results["retire_branches"]:  # type: ignore[index]
                    print(f"  retire {row['verdict']:8s} {row['branch']} — {row['reason']}")
                for f in retire_results.get("findings") or []:  # type: ignore[union-attr]
                    print(f"  FINDING {f['code']}: {f['branch']} — {f['message']}")
            if not args.execute:
                print("dry run: re-run with --execute to apply remote deletes / retirements")
        remote_findings = (remote_results or {}).get("findings") or []  # type: ignore[union-attr]
        retire_findings = (retire_results or {}).get("findings") or []  # type: ignore[union-attr]
        if args.execute and (remote_findings or retire_findings):
            return 1
        return 0

    cwds, ledgers, heads = live_cwds(), load_ledgers(), origin_heads()
    items = [gather(wt, cwds, ledgers, heads) for wt in list_worktrees()]
    for wt in items:
        wt.verdict, wt.reason = verdict_for(wt)
    registered = {str(Path(wt.path).resolve()) for wt in items}
    orphans = list_orphan_dirs(registered)
    for od in orphans:
        od.verdict, od.reason = verdict_for_orphan(od)

    actionable = [
        wt
        for wt in items
        if effective_execute_verdict(wt) in ("DELETE", "PRESERVE-THEN-DELETE", "DELETE-WORKTREE-KEEP-BRANCH", "PRUNE")
    ]
    orphan_actionable = [od for od in orphans if od.verdict == "ORPHAN-DIR"]

    scratch_rows = classify_engine_scratch_refs() if preserve_refs_flag_on() else []
    results: dict[str, object] = {
        "executed": args.execute,
        "removed": [],
        "preserved": [],
        "preserve_tags": [],
        "preserve_debt": [],
        "failed": [],
        "orphans_removed": [],
        "orphans_failed": [],
        "branches_deleted": 0,
        "patch_equivalent_branches": [],
        "engine_scratch": [asdict(r) for r in scratch_rows],
        "engine_scratch_retired": [],
    }
    if args.execute:
        for wt in actionable:
            if wt.verdict == "PRUNE":
                continue
            exec_v = effective_execute_verdict(wt)
            unlock = wt.verdict == "STALE-LOCK" and wt.merged
            if exec_v == "PRESERVE-THEN-DELETE":
                if preserve_refs_flag_on():
                    try:
                        outcome = preserve_worktree_as_tag(wt)
                        results["preserve_tags"].append(outcome.refname)  # type: ignore[union-attr]
                        if outcome.debt:
                            results["preserve_debt"].append(  # type: ignore[union-attr]
                                {"ref": outcome.refname, "reason": outcome.debt}
                            )
                    except (preserve_refs.PreserveRefError, preserve_refs.PreserveGitError) as exc:
                        results["failed"].append(wt.path)  # type: ignore[union-attr]
                        results["preserve_debt"].append({"ref": wt.branch, "reason": str(exc)})  # type: ignore[union-attr]
                        continue
                else:
                    results["preserved"].append(str(preserve(wt, args.preserve_dir)))  # type: ignore[union-attr]
            removed = remove_worktree(wt, unlock_first=unlock)
            (results["removed"] if removed else results["failed"]).append(wt.path)  # type: ignore[union-attr]
        if preserve_refs_flag_on():
            _, retired = retire_promoted_engine_scratch(apply=True)
            results["engine_scratch_retired"] = retired  # type: ignore[assignment]
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
        _, _, patch_eq = delete_merged_local_branches(apply=False)
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
        if scratch_rows:
            for row in scratch_rows:
                print(
                    f"  scratch {row.verdict:8s} {row.refname} "
                    f"{row.commit[:8]}  {row.reason}"
                )
        if args.execute:
            tag_n = len(results.get("preserve_tags") or [])
            patch_n = len(results.get("preserved") or [])
            debt_n = len(results.get("preserve_debt") or [])
            print(
                f"executed: removed {len(results['removed'])}, "
                f"preserve tags {tag_n}, format-patch dirs {patch_n}, preserve debt {debt_n}, "
                f"failed {len(results['failed'])}, "
                f"orphans removed {len(results['orphans_removed'])}, "
                f"local branches deleted {results['branches_deleted']}, "
                f"engine scratch retired {len(results.get('engine_scratch_retired') or [])}"
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
