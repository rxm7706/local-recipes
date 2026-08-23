"""Steward's `workspace` duty — story-scoped scratch worktrees (Story 13.1).

Wraps ``git worktree`` plus a bookkeeping file. CAP-5's own-worktrees-only
rule is HARD: ``ls`` / ``clean`` operate only on entries this tool recorded —
Marshal loop homes and hand-made worktrees are invisible by construction.

CAP-1 ``start``, CAP-2 ``ls``, CAP-4 ``clean`` (archive-not-delete). CAP-3
``status`` is Story 13.2 — deliberately absent here.
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
_DEFAULT_FROM = "origin/main"
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


def scratch_path_for(slug: str, *, root: Path | None = None) -> Path:
    """Conventional sibling path: ``<parent>/<repo>-wt-<safe-slug>``."""
    root = root if root is not None else repo_root()
    safe = slug.replace("/", "-")
    return root.parent / f"{root.name}-wt-{safe}"


def _validate_slug(slug: str) -> None:
    if not _SLUG_PATTERN.match(slug):
        raise WorkspaceError(
            f"invalid slug {slug!r}: expected [A-Za-z0-9][A-Za-z0-9._/-]*"
        )


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


def _branch_merged_into(root: Path, branch: str, into: str) -> bool:
    """True when ``branch`` is an ancestor of ``into`` (already merged)."""
    result = _git_ok("merge-base", "--is-ancestor", branch, into, cwd=root)
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    detail = (result.stderr or result.stdout or "").strip()
    raise WorkspaceError(
        f"git merge-base --is-ancestor {branch} {into} failed "
        f"(exit {result.returncode}): {detail}"
    )


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
    root: Path | None = None,
    bookkeeping: Path | None = None,
    archive_dir: Path | None = None,
    confirm=None,
) -> dict[str, list[dict[str, str]]]:
    """CAP-4: archive-not-delete owned worktrees; optional ``--merged-only``."""
    root = root if root is not None else repo_root()
    bookkeeping = bookkeeping if bookkeeping is not None else default_bookkeeping_path()
    archive_dir = archive_dir if archive_dir is not None else default_archive_dir()
    confirm_fn = confirm if confirm is not None else _confirm_archive

    records = list(load_bookkeeping(bookkeeping))
    archived: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    remaining: list[WorkspaceRecord] = []
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


def format_ls(records: tuple[WorkspaceRecord, ...], *, as_json: bool) -> str:
    if as_json:
        return json.dumps([r.to_dict() for r in records], indent=2)
    if not records:
        return "workspace ls: no scratch workspaces open"
    lines = [f"{r.slug}\t{r.branch}\t{r.path}" for r in records]
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
        lines.append(f"archived {item['slug']} -> {item['archive']}")
    for item in skipped:
        lines.append(f"skipped {item['slug']} ({item.get('reason', '?')})")
    return "\n".join(lines)


_WORKSPACE_VERBS: tuple[str, ...] = ("start", "ls", "clean")


class WorkspaceDuty:
    """Duty adapter for ``steward workspace start|ls|clean``."""

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
                record = start_workspace(ns.slug, from_ref=ns.from_ref or _DEFAULT_FROM)
                return DutyResult(ok=True, summary=format_start(record, as_json=as_json))
            if verb == "ls":
                records = list_workspaces()
                return DutyResult(ok=True, summary=format_ls(records, as_json=as_json))
            # clean
            result = clean_workspaces(merged_only=bool(getattr(ns, "merged_only", False)))
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
