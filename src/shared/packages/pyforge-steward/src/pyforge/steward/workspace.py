"""Steward's `workspace` duty — scratch worktrees (Stories 13.1–13.4).

Wraps ``git worktree`` plus a bookkeeping file. CAP-5's own-worktrees-only
rule is HARD: ``ls`` / ``status`` / ``clean`` operate only on entries this
tool recorded — Marshal loop homes and hand-made worktrees are invisible by
construction. Story 13.4 extends that HARD rule set-wide across repo-set
members.

CAP-1 ``start`` (single-repo or repo-set), CAP-2 ``ls``, CAP-3 ``status``
(pays per-worktree git cost), CAP-4 ``clean`` (archive-not-delete).
Story 13.3 adds declarative ``[projects.<slug>]`` repo sets and coordinated
multi-repo ``start`` with ``.code-workspace`` generation.
Story 13.4 adds set-level ``status`` / ``clean`` (dirty refusal naming the
member; ``--merged-only`` archive-not-delete per member).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml
from pyforge.core.atomic_write import atomic_write

from .interfaces import DutyResult

_BMAD_LOOP_WORKTREE_RELATIVE_PATH = Path("scripts/bmad-loop-worktree")
_BOOKKEEPING_RELATIVE_PATH = Path(".steward/workspaces.yaml")
_ARCHIVE_RELATIVE_PATH = Path(".steward/workspace-archive")
_REPO_SETS_RELATIVE_PATH = Path(".steward/repo-sets.yaml")
_CODE_WORKSPACE_RELATIVE_DIR = Path(".steward/workspaces")
_DEFAULT_FROM = "origin/main"
_FEATURE_BRANCH_PREFIX = "f-"
_SLUG_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


class WorkspaceError(RuntimeError):
    """A workspace verb failed in a duty-level (ok=False) way."""


@dataclass(frozen=True)
class WorkspaceRecord:
    """One tool-created scratch worktree — the bookkeeping unit."""

    slug: str
    path: str
    branch: str
    source: str
    created_at: str

    def to_dict(self) -> dict[str, str]:
        return {
            "slug": self.slug,
            "path": self.path,
            "branch": self.branch,
            "source": self.source,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class WorkspaceStatus:
    """CAP-3 live git health for one owned worktree.

    When the path is missing or per-worktree git fails, ``error`` is set and
    the health fields are ``None`` (JSON null) so consumers cannot confuse an
    unreachable row with a clean equal-tip report. Other rows still list.
    """

    slug: str
    path: str
    branch: str
    source: str
    dirty: bool | None
    ahead: int | None
    behind: int | None
    merged: bool | None
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        out: dict[str, object] = {
            "slug": self.slug,
            "path": self.path,
            "branch": self.branch,
            "source": self.source,
            "dirty": self.dirty,
            "ahead": self.ahead,
            "behind": self.behind,
            "merged": self.merged,
        }
        if self.error is not None:
            out["error"] = self.error
        return out


def repo_root() -> Path:
    """Return the local-recipes checkout root (walk-up on ``scripts/bmad-loop-worktree``)."""
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / _BMAD_LOOP_WORKTREE_RELATIVE_PATH).is_file():
            return ancestor
    raise RuntimeError(
        f"workspace.py: could not locate {_BMAD_LOOP_WORKTREE_RELATIVE_PATH} "
        f"by walking up from {here} — this module must live inside a "
        "local-recipes checkout."
    )


def default_bookkeeping_path() -> Path:
    return repo_root() / _BOOKKEEPING_RELATIVE_PATH


def default_archive_dir() -> Path:
    return repo_root() / _ARCHIVE_RELATIVE_PATH


def default_repo_sets_path() -> Path:
    return repo_root() / _REPO_SETS_RELATIVE_PATH


@dataclass(frozen=True)
class RepoSetMember:
    """One registered repo in a declarative ``[projects.<slug>]`` set."""

    name: str
    declared_path: str


@dataclass(frozen=True)
class RepoSet:
    """A named multi-repo feature set from ``.steward/repo-sets.yaml``."""

    feature: str
    members: tuple[RepoSetMember, ...]


@dataclass(frozen=True)
class RepoSetStartResult:
    """Outcome of coordinated multi-repo ``workspace start`` (Story 13.3)."""

    feature: str
    branch: str
    workspace_file: str
    members: tuple[WorkspaceRecord, ...]


@dataclass(frozen=True)
class RepoSetMemberOpen:
    """One open (bookkeeping-recorded) member of a repo-set workspace."""

    name: str
    root: Path
    record: WorkspaceRecord


@dataclass(frozen=True)
class RepoSetMemberStatus:
    """CAP-2 (multi-repo): live status for one open set member."""

    member: str
    status: WorkspaceStatus

    def to_dict(self) -> dict[str, object]:
        out = self.status.to_dict()
        out["member"] = self.member
        return out


def resolve_repo_path(declared: str, *, anchor: Path) -> Path:
    """Expand ``~`` and resolve relative paths against *anchor*."""
    expanded = Path(declared).expanduser()
    if expanded.is_absolute():
        return expanded.resolve()
    return (anchor / expanded).resolve()


def load_repo_sets(path: str | Path | None = None) -> dict[str, RepoSet]:
    """Load declarative repo sets. Missing file → empty mapping."""
    path = Path(path) if path is not None else default_repo_sets_path()
    if not path.is_file():
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise WorkspaceError(f"{path}: invalid YAML: {exc}") from exc
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise WorkspaceError(f"{path}: top-level YAML must be a mapping")
    projects = raw.get("projects") or {}
    if not isinstance(projects, dict):
        raise WorkspaceError(f"{path}: 'projects' must be a mapping")
    out: dict[str, RepoSet] = {}
    for feature, body in projects.items():
        if not isinstance(body, dict):
            raise WorkspaceError(f"{path}: projects[{feature!r}] must be a mapping")
        repos = body.get("repos") or {}
        if not isinstance(repos, dict):
            raise WorkspaceError(f"{path}: projects[{feature!r}].repos must be a mapping")
        members: list[RepoSetMember] = []
        for name, repo_body in repos.items():
            if not isinstance(repo_body, dict):
                raise WorkspaceError(f"{path}: projects[{feature!r}].repos[{name!r}] must be a mapping")
            try:
                declared = str(repo_body["path"])
            except KeyError as exc:
                raise WorkspaceError(f"{path}: projects[{feature!r}].repos[{name!r}] missing path") from exc
            members.append(RepoSetMember(name=str(name), declared_path=declared))
        out[str(feature)] = RepoSet(feature=str(feature), members=tuple(members))
    return out


def feature_branch_name(feature: str) -> str:
    """Shared branch name for a repo-set feature."""
    _validate_slug(feature)
    return f"{_FEATURE_BRANCH_PREFIX}{feature}"


def _bookkeeping_for(root: Path) -> Path:
    return root / _BOOKKEEPING_RELATIVE_PATH


def _write_code_workspace(
    *,
    workspace_file: Path,
    folder_paths: tuple[str, ...],
    feature: str,
) -> None:
    workspace_file.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "folders": [{"name": Path(p).name, "path": p} for p in folder_paths],
        "settings": {},
    }
    workspace_file.write_text(
        json.dumps(document, indent=2) + "\n",
        encoding="utf-8",
    )


def _rollback_repo_set_starts(
    records: tuple[WorkspaceRecord, ...],
    *,
    roots_by_path: dict[str, Path],
) -> None:
    """Best-effort undo of partial multi-repo start."""
    for record in reversed(records):
        wt_root = roots_by_path.get(record.path)
        if wt_root is None:
            continue
        wt = Path(record.path)
        if wt.exists():
            _git_ok("worktree", "remove", "--force", str(wt), cwd=wt_root)
        bookkeeping = _bookkeeping_for(wt_root)
        remaining = tuple(r for r in load_bookkeeping(bookkeeping) if r.slug != record.slug)
        save_bookkeeping(bookkeeping, remaining)
        _git_ok("branch", "-D", record.branch, cwd=wt_root)


def start_repo_set(
    feature: str,
    *,
    from_ref: str = _DEFAULT_FROM,
    repo_sets_path: Path | None = None,
    anchor: Path | None = None,
) -> RepoSetStartResult:
    """Story 13.3: one worktree per registered repo on ``f-<feature>``."""
    _validate_slug(feature)
    anchor = anchor if anchor is not None else repo_root()
    sets = load_repo_sets(repo_sets_path)
    repo_set = sets.get(feature)
    if repo_set is None:
        raise WorkspaceError(f"repo set {feature!r} not found in {repo_sets_path or default_repo_sets_path()}")
    if not repo_set.members:
        raise WorkspaceError(f"repo set {feature!r} has no registered repos")

    branch = feature_branch_name(feature)
    missing: list[str] = []
    resolved: list[tuple[RepoSetMember, Path]] = []
    for member in repo_set.members:
        target = resolve_repo_path(member.declared_path, anchor=anchor)
        if not target.is_dir() or not (target / ".git").exists():
            missing.append(member.name)
        else:
            resolved.append((member, target))

    if missing:
        names = ", ".join(sorted(missing))
        raise WorkspaceError(f"repo set {feature!r}: missing local repos (not guessed): {names}")

    started: list[WorkspaceRecord] = []
    roots_by_path: dict[str, Path] = {}
    try:
        for member, member_root in resolved:
            dest = scratch_path_for(branch, root=member_root)
            record = start_workspace(
                branch,
                from_ref=from_ref,
                root=member_root,
                bookkeeping=_bookkeeping_for(member_root),
                path=dest,
            )
            started.append(record)
            roots_by_path[record.path] = member_root
    except Exception:
        _rollback_repo_set_starts(tuple(started), roots_by_path=roots_by_path)
        raise

    workspace_file = anchor / _CODE_WORKSPACE_RELATIVE_DIR / f"{branch}.code-workspace"
    _write_code_workspace(
        workspace_file=workspace_file,
        folder_paths=tuple(r.path for r in started),
        feature=feature,
    )
    return RepoSetStartResult(
        feature=feature,
        branch=branch,
        workspace_file=str(workspace_file.resolve()),
        members=tuple(started),
    )


def _resolve_member_root(
    member: RepoSetMember,
    *,
    anchor: Path,
) -> Path | None:
    """Return the member checkout root if it exists as a git repo, else None."""
    target = resolve_repo_path(member.declared_path, anchor=anchor)
    if not target.is_dir() or not (target / ".git").exists():
        return None
    return target


def open_repo_set_members(
    feature: str,
    *,
    repo_sets_path: Path | None = None,
    anchor: Path | None = None,
) -> tuple[RepoSetMemberOpen, ...]:
    """Story 13.4: bookkeeping-owned open members of a registered repo set.

    Own-worktrees-only is HARD set-wide: only rows this tool recorded under
    each member's ``.steward/workspaces.yaml`` for branch ``f-<feature>`` are
    returned. Foreign / Marshal loop-home worktrees are never discovered.
    """
    _validate_slug(feature)
    anchor = anchor if anchor is not None else repo_root()
    sets = load_repo_sets(repo_sets_path)
    repo_set = sets.get(feature)
    if repo_set is None:
        raise WorkspaceError(f"repo set {feature!r} not found in {repo_sets_path or default_repo_sets_path()}")
    branch = feature_branch_name(feature)
    opened: list[RepoSetMemberOpen] = []
    for member in repo_set.members:
        member_root = _resolve_member_root(member, anchor=anchor)
        if member_root is None:
            continue
        bookkeeping = _bookkeeping_for(member_root)
        for record in load_bookkeeping(bookkeeping):
            if record.slug == branch or record.branch == branch:
                opened.append(RepoSetMemberOpen(name=member.name, root=member_root, record=record))
                break
    return tuple(opened)


def status_repo_set(
    feature: str,
    *,
    repo_sets_path: Path | None = None,
    anchor: Path | None = None,
) -> tuple[RepoSetMemberStatus, ...]:
    """Story 13.4: dirty/unpushed across every open member of a repo set."""
    opened = open_repo_set_members(feature, repo_sets_path=repo_sets_path, anchor=anchor)
    return tuple(
        RepoSetMemberStatus(
            member=item.name,
            status=status_of(item.record, root=item.root),
        )
        for item in opened
    )


def clean_repo_set(
    feature: str,
    *,
    merged_only: bool = False,
    repo_sets_path: Path | None = None,
    anchor: Path | None = None,
    confirm=None,
) -> dict[str, list[dict[str, str]]]:
    """Story 13.4: tear down an open repo set safely.

    Refuses while any open member is dirty (names the dirty member). Otherwise
    archives each member with 13.1 archive-not-delete discipline; ``--merged-only``
    skips unmerged members per-repo. Own-worktrees-only: foreign trees ignored.
    """
    anchor = anchor if anchor is not None else repo_root()
    opened = open_repo_set_members(feature, repo_sets_path=repo_sets_path, anchor=anchor)
    if not opened:
        return {"archived": [], "skipped": []}

    dirty_names: list[str] = []
    for item in opened:
        st = status_of(item.record, root=item.root)
        if st.error is not None:
            raise WorkspaceError(f"repo set {feature!r}: cannot assess member {item.name!r}: {st.error}")
        if st.dirty:
            dirty_names.append(item.name)
    if dirty_names:
        named = ", ".join(sorted(dirty_names))
        raise WorkspaceError(f"repo set {feature!r}: refuse removal — dirty member(s): {named}")

    archived: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    for item in opened:
        # Re-check immediately before archive (TOCTOU): a member may have
        # become dirty after the set-wide gate above.
        st = status_of(item.record, root=item.root)
        if st.error is not None:
            raise WorkspaceError(f"repo set {feature!r}: cannot assess member {item.name!r}: {st.error}")
        if st.dirty:
            raise WorkspaceError(f"repo set {feature!r}: refuse removal — dirty member(s): {item.name}")
        result = clean_workspaces(
            merged_only=merged_only,
            slug=item.record.slug,
            root=item.root,
            bookkeeping=_bookkeeping_for(item.root),
            archive_dir=item.root / _ARCHIVE_RELATIVE_PATH,
            confirm=confirm,
        )
        for row in result["archived"]:
            archived.append({**row, "member": item.name})
        for row in result["skipped"]:
            skipped.append({**row, "member": item.name})

    # Drop the coordinated .code-workspace when nothing remains open for the set.
    still_open = open_repo_set_members(feature, repo_sets_path=repo_sets_path, anchor=anchor)
    if not still_open:
        branch = feature_branch_name(feature)
        ws_file = anchor / _CODE_WORKSPACE_RELATIVE_DIR / f"{branch}.code-workspace"
        if ws_file.is_file():
            ws_file.unlink()

    return {"archived": archived, "skipped": skipped}


def scratch_path_for(slug: str, *, root: Path | None = None) -> Path:
    """Conventional sibling path: ``<parent>/<repo>-wt-<safe-slug>``."""
    root = root if root is not None else repo_root()
    safe = slug.replace("/", "-")
    return root.parent / f"{root.name}-wt-{safe}"


def _validate_slug(slug: str) -> None:
    if not _SLUG_PATTERN.match(slug):
        raise WorkspaceError(f"invalid slug {slug!r}: expected [A-Za-z0-9][A-Za-z0-9._/-]*")


def load_bookkeeping(path: str | Path) -> tuple[WorkspaceRecord, ...]:
    """Read the tool's own worktree set. Missing file → empty (never an error)."""
    path = Path(path)
    if not path.is_file():
        return ()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise WorkspaceError(f"{path}: invalid YAML: {exc}") from exc
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise WorkspaceError(f"{path}: top-level YAML must be a mapping")
    entries = raw.get("workspaces") or []
    if not isinstance(entries, list):
        raise WorkspaceError(f"{path}: 'workspaces' must be a list")
    out: list[WorkspaceRecord] = []
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise WorkspaceError(f"{path}: workspaces[{i}] must be a mapping")
        try:
            out.append(
                WorkspaceRecord(
                    slug=str(entry["slug"]),
                    path=str(entry["path"]),
                    branch=str(entry["branch"]),
                    source=str(entry["source"]),
                    created_at=str(entry["created_at"]),
                )
            )
        except KeyError as exc:
            raise WorkspaceError(f"{path}: workspaces[{i}] missing {exc}") from exc
    return tuple(out)


def save_bookkeeping(path: str | Path, records: tuple[WorkspaceRecord, ...]) -> None:
    path = Path(path)
    document = {"workspaces": [r.to_dict() for r in records]}

    def _write(tmp: Path) -> None:
        with tmp.open("w", encoding="utf-8") as f:
            yaml.safe_dump(document, f, sort_keys=False)

    atomic_write(path, _write)


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def _git_ok(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def start_workspace(
    slug: str,
    *,
    from_ref: str = _DEFAULT_FROM,
    root: Path | None = None,
    bookkeeping: Path | None = None,
    path: Path | None = None,
) -> WorkspaceRecord:
    """CAP-1: create a scratch worktree and record it."""
    _validate_slug(slug)
    root = root if root is not None else repo_root()
    bookkeeping = bookkeeping if bookkeeping is not None else default_bookkeeping_path()
    dest = path if path is not None else scratch_path_for(slug, root=root)

    existing = load_bookkeeping(bookkeeping)
    if any(r.slug == slug for r in existing):
        raise WorkspaceError(f"workspace {slug!r} already recorded in bookkeeping")
    if dest.exists():
        raise WorkspaceError(f"scratch path already exists: {dest}")

    try:
        _git("worktree", "add", str(dest), "-b", slug, from_ref, cwd=root)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        raise WorkspaceError(f"git worktree add failed: {detail}") from exc

    record = WorkspaceRecord(
        slug=slug,
        path=str(dest.resolve()),
        branch=slug,
        source=from_ref,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    try:
        save_bookkeeping(bookkeeping, existing + (record,))
    except Exception:
        # CAP-1: never leave an orphan worktree outside bookkeeping.
        _git_ok("worktree", "remove", "--force", str(dest), cwd=root)
        raise
    return record


def list_workspaces(
    *,
    bookkeeping: Path | None = None,
) -> tuple[WorkspaceRecord, ...]:
    """CAP-2: cheap enumeration — bookkeeping only, no per-worktree git."""
    bookkeeping = bookkeeping if bookkeeping is not None else default_bookkeeping_path()
    return load_bookkeeping(bookkeeping)


def _worktree_dirty(wt: Path) -> bool:
    result = _git_ok("status", "--porcelain", cwd=wt)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise WorkspaceError(f"git status --porcelain failed in {wt} (exit {result.returncode}): {detail}")
    return bool((result.stdout or "").strip())


def _ahead_behind(wt: Path, source: str, branch: str) -> tuple[int, int]:
    """Return (ahead, behind) of *branch* vs *source* via ``rev-list --left-right``.

    ``git rev-list --left-right --count <source>...<branch>``: left = behind,
    right = ahead (commits on branch not in source).
    """
    range_spec = f"{source}...{branch}"
    result = _git_ok("rev-list", "--left-right", "--count", range_spec, cwd=wt)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise WorkspaceError(
            f"git rev-list --left-right --count {range_spec} failed in {wt} (exit {result.returncode}): {detail}"
        )
    parts = (result.stdout or "").strip().split()
    if len(parts) != 2:
        raise WorkspaceError(f"unexpected rev-list output in {wt}: {result.stdout!r}")
    # left = commits reachable from source not in branch → behind
    # right = commits reachable from branch not in source → ahead
    try:
        behind, ahead = int(parts[0]), int(parts[1])
    except ValueError as exc:
        raise WorkspaceError(f"unexpected rev-list counts in {wt}: {parts!r}") from exc
    return ahead, behind


def _unreachable_status(record: WorkspaceRecord, message: str) -> WorkspaceStatus:
    return WorkspaceStatus(
        slug=record.slug,
        path=record.path,
        branch=record.branch,
        source=record.source,
        dirty=None,
        ahead=None,
        behind=None,
        merged=None,
        error=message,
    )


def status_of(record: WorkspaceRecord, *, root: Path) -> WorkspaceStatus:
    """CAP-3: live dirty / ahead / behind / merged for one owned record.

    Missing path / git failure → ``error`` set (never raises) so a multi-row
    ``status`` can still report reachable siblings.
    """
    wt = Path(record.path)
    try:
        is_dir = wt.is_dir()
    except OSError as exc:
        return _unreachable_status(record, str(exc))
    if not is_dir:
        return _unreachable_status(
            record,
            f"path missing or not a directory: {record.path}",
        )
    try:
        dirty = _worktree_dirty(wt)
        ahead, behind = _ahead_behind(wt, record.source, record.branch)
        merged = _branch_merged_into(root, record.branch, record.source)
    except WorkspaceError as exc:
        return _unreachable_status(record, str(exc))
    return WorkspaceStatus(
        slug=record.slug,
        path=record.path,
        branch=record.branch,
        source=record.source,
        dirty=dirty,
        ahead=ahead,
        behind=behind,
        merged=merged,
    )


def status_workspaces(
    slug: str | None = None,
    *,
    root: Path | None = None,
    bookkeeping: Path | None = None,
) -> tuple[WorkspaceStatus, ...]:
    """CAP-3: pay per-worktree git cost for owned worktrees (optional slug filter)."""
    root = root if root is not None else repo_root()
    bookkeeping = bookkeeping if bookkeeping is not None else default_bookkeeping_path()
    records = list_workspaces(bookkeeping=bookkeeping)
    if slug is not None:
        if not slug:
            raise WorkspaceError("invalid slug ''")
        matches = [r for r in records if r.slug == slug]
        if not matches:
            raise WorkspaceError(f"workspace {slug!r} not in bookkeeping")
        if len(matches) > 1:
            raise WorkspaceError(f"ambiguous slug {slug!r}: {len(matches)} bookkeeping rows")
        records = tuple(matches)
    return tuple(status_of(r, root=root) for r in records)


def _branch_merged_into(root: Path, branch: str, into: str) -> bool:
    """True when ``branch`` is an ancestor of ``into`` (already merged)."""
    result = _git_ok("merge-base", "--is-ancestor", branch, into, cwd=root)
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    detail = (result.stderr or result.stdout or "").strip()
    raise WorkspaceError(f"git merge-base --is-ancestor {branch} {into} failed (exit {result.returncode}): {detail}")


def _archive_worktree(
    record: WorkspaceRecord,
    *,
    root: Path,
    archive_dir: Path,
) -> Path:
    """Archive-not-delete: tar the tree, then ``git worktree remove``.

    After a successful remove/prune, also best-effort deletes the local branch
    so a later ``start`` with the same slug can recreate ``-b`` cleanly. The
    tar (or missing marker) is retained — archive-not-delete of tree content.
    """
    try:
        archive_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe = record.slug.replace("/", "-")
        wt = Path(record.path)
        if wt.is_dir():
            archive_path = archive_dir / f"{safe}-{stamp}.tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(wt, arcname=wt.name)
        else:
            # Path already gone — still write a marker so clean is recoverable.
            archive_path = archive_dir / f"{safe}-{stamp}.missing.txt"
            archive_path.write_text(
                f"workspace {record.slug!r} path missing at clean: {record.path}\n",
                encoding="utf-8",
            )

        if wt.exists():
            result = _git_ok("worktree", "remove", "--force", str(wt), cwd=root)
            if result.returncode != 0:
                # Fall back: detach registration by prune after moving aside.
                retired = archive_dir / f"{safe}-{stamp}-dir"
                try:
                    shutil.move(str(wt), str(retired))
                except OSError as exc:
                    raise WorkspaceError(
                        f"could not archive {record.path}: git remove failed "
                        f"({(result.stderr or '').strip()}) and move failed ({exc})"
                    ) from exc
                _git_ok("worktree", "prune", cwd=root)
        else:
            _git_ok("worktree", "prune", cwd=root)

        # Branch may still exist after worktree remove; drop it so slug reuse works.
        _git_ok("branch", "-D", record.branch, cwd=root)
        return archive_path
    except OSError as exc:
        raise WorkspaceError(f"could not archive {record.path}: {exc}") from exc


def _confirm_archive(slug: str) -> bool:
    if not sys.stdin.isatty():
        return False
    try:
        answer = input(f"archive workspace {slug}? [y/N] ")
    except EOFError:
        return False
    return answer.strip().lower() in ("y", "yes")


def clean_workspaces(
    *,
    merged_only: bool = False,
    slug: str | None = None,
    root: Path | None = None,
    bookkeeping: Path | None = None,
    archive_dir: Path | None = None,
    confirm=None,
) -> dict[str, list[dict[str, str]]]:
    """CAP-4: archive-not-delete owned worktrees; optional ``--merged-only`` / slug."""
    root = root if root is not None else repo_root()
    bookkeeping = bookkeeping if bookkeeping is not None else default_bookkeeping_path()
    archive_dir = archive_dir if archive_dir is not None else default_archive_dir()
    confirm_fn = confirm if confirm is not None else _confirm_archive

    records = list(load_bookkeeping(bookkeeping))
    if slug is not None:
        if not slug:
            raise WorkspaceError("invalid slug ''")
        matches = [r for r in records if r.slug == slug]
        if not matches:
            raise WorkspaceError(f"workspace {slug!r} not in bookkeeping")
        if len(matches) > 1:
            raise WorkspaceError(f"ambiguous slug {slug!r}: {len(matches)} bookkeeping rows")
        # Keep non-matching rows in remaining; only consider the match for archive.
        others = [r for r in records if r.slug != slug]
        records = matches
    else:
        others = []

    archived: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    remaining: list[WorkspaceRecord] = list(others)
    pending = list(records)

    try:
        while pending:
            record = pending.pop(0)
            if merged_only and not _branch_merged_into(root, record.branch, record.source):
                skipped.append({**record.to_dict(), "reason": "not-merged"})
                remaining.append(record)
                continue
            if not merged_only and not confirm_fn(record.slug):
                skipped.append({**record.to_dict(), "reason": "declined"})
                remaining.append(record)
                continue
            archive_path = _archive_worktree(record, root=root, archive_dir=archive_dir)
            archived.append({**record.to_dict(), "archive": str(archive_path)})
    finally:
        # Persist removals already archived even if a later record fails —
        # otherwise archived trees stay listed in bookkeeping.
        save_bookkeeping(bookkeeping, tuple(remaining + pending))

    return {"archived": archived, "skipped": skipped}


def format_start(record: WorkspaceRecord, *, as_json: bool) -> str:
    if as_json:
        return json.dumps(record.to_dict(), indent=2)
    return record.path


def format_repo_set_start(result: RepoSetStartResult, *, as_json: bool) -> str:
    if as_json:
        payload = {
            "feature": result.feature,
            "branch": result.branch,
            "workspace_file": result.workspace_file,
            "members": [r.to_dict() for r in result.members],
        }
        return json.dumps(payload, indent=2)
    lines = [result.workspace_file]
    for record in result.members:
        lines.append(f"{record.path}\t{record.branch}")
    return "\n".join(lines)


def format_ls(records: tuple[WorkspaceRecord, ...], *, as_json: bool) -> str:
    if as_json:
        return json.dumps([r.to_dict() for r in records], indent=2)
    if not records:
        return "workspace ls: no scratch workspaces open"
    lines = [f"{r.slug}\t{r.branch}\t{r.path}" for r in records]
    return "\n".join(lines)


def format_status(statuses: tuple[WorkspaceStatus, ...], *, as_json: bool) -> str:
    if as_json:
        return json.dumps([s.to_dict() for s in statuses], indent=2)
    if not statuses:
        return "workspace status: no scratch workspaces open"
    lines: list[str] = []
    for s in statuses:
        if s.error is not None:
            lines.append(f"{s.slug}\terror\t{s.error}\t{s.path}")
            continue
        dirt = "dirty" if s.dirty else "clean"
        merged = "merged" if s.merged else "unmerged"
        lines.append(f"{s.slug}\t{dirt}\tahead={s.ahead}\tbehind={s.behind}\t{merged}\t{s.path}")
    return "\n".join(lines)


def format_repo_set_status(statuses: tuple[RepoSetMemberStatus, ...], *, as_json: bool) -> str:
    if as_json:
        return json.dumps([s.to_dict() for s in statuses], indent=2)
    if not statuses:
        return "workspace status: no open members for repo set"
    lines: list[str] = []
    for row in statuses:
        s = row.status
        if s.error is not None:
            lines.append(f"{row.member}\t{s.slug}\terror\t{s.error}\t{s.path}")
            continue
        dirt = "dirty" if s.dirty else "clean"
        unpushed = (s.ahead or 0) > 0
        push = "unpushed" if unpushed else "pushed"
        merged = "merged" if s.merged else "unmerged"
        lines.append(f"{row.member}\t{s.slug}\t{dirt}\t{push}\tahead={s.ahead}\tbehind={s.behind}\t{merged}\t{s.path}")
    return "\n".join(lines)


def format_clean(result: dict[str, list[dict[str, str]]], *, as_json: bool) -> str:
    if as_json:
        return json.dumps(result, indent=2)
    archived = result["archived"]
    skipped = result["skipped"]
    if not archived and not skipped:
        return "workspace clean: nothing to do"
    lines: list[str] = []
    for item in archived:
        member = item.get("member")
        prefix = f"archived {member}/" if member else "archived "
        lines.append(f"{prefix}{item['slug']} -> {item['archive']}")
    for item in skipped:
        member = item.get("member")
        prefix = f"skipped {member}/" if member else "skipped "
        lines.append(f"{prefix}{item['slug']} ({item.get('reason', '?')})")
    return "\n".join(lines)


_WORKSPACE_VERBS: tuple[str, ...] = ("start", "ls", "status", "clean")


class WorkspaceDuty:
    """Duty adapter for ``steward workspace start|ls|status|clean``."""

    name = "workspace"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        verb = getattr(ns, "workspace_verb", None)
        if verb not in _WORKSPACE_VERBS:
            return DutyResult(
                ok=True,
                summary=f"workspace: available verbs are {', '.join(_WORKSPACE_VERBS)}",
            )
        as_json = bool(getattr(ns, "json", False))
        try:
            if verb == "start":
                feature = ns.slug
                repo_sets = load_repo_sets()
                if feature in repo_sets:
                    result = start_repo_set(feature, from_ref=ns.from_ref or _DEFAULT_FROM)
                    return DutyResult(
                        ok=True,
                        summary=format_repo_set_start(result, as_json=as_json),
                    )
                record = start_workspace(feature, from_ref=ns.from_ref or _DEFAULT_FROM)
                return DutyResult(ok=True, summary=format_start(record, as_json=as_json))
            if verb == "ls":
                records = list_workspaces()
                return DutyResult(ok=True, summary=format_ls(records, as_json=as_json))
            if verb == "status":
                slug = getattr(ns, "slug", None)
                if slug is not None and slug in load_repo_sets():
                    statuses = status_repo_set(slug)
                    return DutyResult(
                        ok=True,
                        summary=format_repo_set_status(statuses, as_json=as_json),
                    )
                statuses = status_workspaces(slug)
                return DutyResult(ok=True, summary=format_status(statuses, as_json=as_json))
            # clean — optional slug targets a repo set or a single owned worktree
            slug = getattr(ns, "slug", None)
            merged_only = bool(getattr(ns, "merged_only", False))
            if slug is not None and slug in load_repo_sets():
                result = clean_repo_set(slug, merged_only=merged_only)
                return DutyResult(ok=True, summary=format_clean(result, as_json=as_json))
            result = clean_workspaces(merged_only=merged_only, slug=slug)
            return DutyResult(ok=True, summary=format_clean(result, as_json=as_json))
        except WorkspaceError as exc:
            return DutyResult(ok=False, summary=self._render_error(ns, str(exc)))
        except RuntimeError as exc:
            # e.g. repo_root() walk-up failure — duty-level, not an internal crash.
            return DutyResult(ok=False, summary=self._render_error(ns, str(exc)))
        except OSError as exc:
            return DutyResult(ok=False, summary=self._render_error(ns, str(exc)))
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or str(exc)).strip()
            return DutyResult(
                ok=False,
                summary=self._render_error(ns, f"workspace {verb}: git failed: {detail}"),
            )

    @staticmethod
    def _render_error(ns: argparse.Namespace, message: str) -> str:
        if getattr(ns, "json", False):
            return json.dumps({"error": message}, indent=2)
        return message
