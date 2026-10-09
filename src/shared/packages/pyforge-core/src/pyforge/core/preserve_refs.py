"""pyforge.core.preserve_refs -- ONE shared grammar for preserved-work refs (Story 87.3).

Renders and parses ``refs/tags/preserve/…`` and ``refs/tags/archive/…`` names,
snapshots a dirty worktree without moving branch/HEAD/index, writes annotated
preserve tags with seven ``Preserve-*`` trailers, deduplicates by name and by
story tree, and lists preserves with derived ``open`` / ``landed`` state.

Stdlib-only (plus ``pyforge.core.process`` for git); imports no ``pyforge.<station>``.
"""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Literal

from pyforge.core.process import PosixProcess, ProcessError

_PRESERVE_PREFIX = "refs/tags/preserve/"
_ARCHIVE_PREFIX = "refs/tags/archive/"

PRESERVE_PRODUCERS: frozenset[str] = frozenset(
    {
        "bmad-loop",
        "intent-gap",
        "dispatch",
        "build",
        "sweep",
        "workspace",
        "dangling",
        "hand",
    }
)

PRESERVE_TRAILERS: frozenset[str] = frozenset(
    {
        "Preserve-Producer",
        "Preserve-Provenance",
        "Preserve-Reason",
        "Preserve-Source",
        "Preserve-Run",
        "Preserve-Journal",
        "Preserve-Commit",
    }
)

PROVENANCE_VALUES: frozenset[str] = frozenset({"machine", "human"})

ORIGIN_MAIN = "refs/remotes/origin/main"

_DATE_IN_NAME_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_SHA8_RE = re.compile(r"^[0-9a-f]{8}$")
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_STORY_KEY_RE = re.compile(r"^(?P<epic>\d+)\.(?P<seq>\d+)(?P<suffix>[a-z])?$")

_PROCESS = PosixProcess()


class PreserveRefError(ValueError):
    """Base for preserve-ref grammar failures."""


class PreserveRefNameError(PreserveRefError):
    """A refname is not a sanctioned preserve or archive shape."""


class PreserveRefConflictError(PreserveRefError):
    """The same preserve name already points at a different object."""


class PreserveGitError(PreserveRefError):
    """Git refused an operation preserve_refs requested."""


class PreserveState(StrEnum):
    OPEN = "open"
    LANDED = "landed"


@dataclass(frozen=True, slots=True)
class ParsedPreserveRef:
    refname: str
    project_slug: str | None
    story_key: str | None
    producer: str
    sha8: str


@dataclass(frozen=True, slots=True)
class ParsedArchiveRef:
    refname: str
    kind: Literal["heads", "tags"]
    path: str


@dataclass(frozen=True, slots=True)
class PreserveTrailers:
    producer: str
    provenance: str
    reason: str
    source: str
    run: str
    journal: str
    commit: str

    def format_message(self) -> str:
        lines = [
            f"Preserve-Producer: {self.producer}",
            f"Preserve-Provenance: {self.provenance}",
            f"Preserve-Reason: {self.reason}",
            f"Preserve-Source: {self.source}",
            f"Preserve-Run: {self.run}",
            f"Preserve-Journal: {self.journal}",
            f"Preserve-Commit: {self.commit}",
        ]
        return "\n".join(lines) + "\n"


@dataclass(frozen=True, slots=True)
class PreserveRecord:
    refname: str
    object_sha: str
    project_slug: str | None
    story_key: str | None
    producer: str
    sha8: str
    state: PreserveState
    trailers: PreserveTrailers


@dataclass(frozen=True, slots=True)
class TagPreserveResult:
    refname: str
    commit: str
    noop: bool


def _git(repo: Path, *args: str) -> tuple[int, str, str]:
    try:
        result = _PROCESS.run(["git", *args], cwd=repo)
    except ProcessError as exc:
        raise PreserveGitError(str(exc)) from exc
    return result.returncode, result.stdout, result.stderr


def _git_out(repo: Path, *args: str) -> str:
    rc, out, err = _git(repo, *args)
    if rc != 0:
        raise PreserveGitError(err.strip() or out.strip() or f"git {' '.join(args)} failed")
    return out.strip()


@contextmanager
def _with_env(extra: dict[str, str]) -> Iterator[None]:
    """Temporarily merge ``extra`` into ``os.environ`` for git identity/index overrides."""
    saved = {key: os.environ.get(key) for key in extra}
    os.environ.update(extra)
    try:
        yield
    finally:
        for key, prior in saved.items():
            if prior is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = prior


def _full_sha(repo: Path, ref: str) -> str:
    return _git_out(repo, "rev-parse", ref)


def _short_sha8(sha: str) -> str:
    normalized = sha.lower()
    if len(normalized) < 8 or not all(c in "0123456789abcdef" for c in normalized[:8]):
        raise PreserveRefError(f"commit {sha!r} is not a usable sha")
    return normalized[:8]


def _reject_date_in_name(refname: str) -> None:
    if _DATE_IN_NAME_RE.search(refname):
        raise PreserveRefNameError(f"preserve refnames must not contain a date: {refname!r}")


def _match_producer_suffix(tail: str) -> tuple[str, str]:
    for producer in sorted(PRESERVE_PRODUCERS, key=len, reverse=True):
        prefix = f"{producer}-"
        if tail.startswith(prefix):
            sha8 = tail[len(prefix) :]
            if _SHA8_RE.match(sha8):
                return producer, sha8
    raise PreserveRefNameError(f"cannot parse producer-sha8 suffix {tail!r}")


def render_preserve_ref(
    *,
    commit_sha: str,
    producer: str,
    project_slug: str | None = None,
    story_key: str | None = None,
) -> str:
    """Render a full preserve tag refname for ``commit_sha``."""
    if producer not in PRESERVE_PRODUCERS:
        raise PreserveRefError(f"unknown producer {producer!r}")
    sha8 = _short_sha8(commit_sha)
    tail = f"{producer}-{sha8}"
    if project_slug is None and story_key is None:
        ref = f"{_PRESERVE_PREFIX}unbound/{tail}"
    else:
        if project_slug is None or story_key is None:
            raise PreserveRefError("project_slug and story_key must both be set or both omitted")
        if not _SLUG_RE.match(project_slug):
            raise PreserveRefError(f"invalid project slug {project_slug!r}")
        if _STORY_KEY_RE.match(story_key) is None:
            raise PreserveRefError(f"invalid story key {story_key!r}")
        ref = f"{_PRESERVE_PREFIX}{project_slug}/{story_key}/{tail}"
    _reject_date_in_name(ref)
    return ref


def parse_preserve_ref(refname: str) -> ParsedPreserveRef:
    """Parse a preserve tag refname; reject anything else under ``refs/tags/preserve/``."""
    if not refname.startswith(_PRESERVE_PREFIX):
        raise PreserveRefNameError(f"not a preserve ref: {refname!r}")
    _reject_date_in_name(refname)
    rest = refname[len(_PRESERVE_PREFIX) :]
    if rest.startswith("unbound/"):
        producer, sha8 = _match_producer_suffix(rest[len("unbound/") :])
        return ParsedPreserveRef(refname, None, None, producer, sha8)
    parts = rest.split("/")
    if len(parts) != 3:
        raise PreserveRefNameError(f"malformed preserve ref: {refname!r}")
    slug, story, tail = parts
    if not _SLUG_RE.match(slug):
        raise PreserveRefNameError(f"invalid slug in preserve ref: {refname!r}")
    if _STORY_KEY_RE.match(story) is None:
        raise PreserveRefNameError(f"invalid story key in preserve ref: {refname!r}")
    producer, sha8 = _match_producer_suffix(tail)
    return ParsedPreserveRef(refname, slug, story, producer, sha8)


def render_archive_heads_ref(branch: str) -> str:
    branch = branch.removeprefix("refs/heads/")
    ref = f"{_ARCHIVE_PREFIX}heads/{branch}"
    _reject_date_in_name(ref)
    return ref


def render_archive_tags_ref(tag: str) -> str:
    tag = tag.removeprefix("refs/tags/")
    ref = f"{_ARCHIVE_PREFIX}tags/{tag}"
    _reject_date_in_name(ref)
    return ref


def parse_archive_ref(refname: str) -> ParsedArchiveRef:
    if not refname.startswith(_ARCHIVE_PREFIX):
        raise PreserveRefNameError(f"not an archive ref: {refname!r}")
    _reject_date_in_name(refname)
    rest = refname[len(_ARCHIVE_PREFIX) :]
    if rest.startswith("heads/"):
        return ParsedArchiveRef(refname, "heads", rest[len("heads/") :])
    if rest.startswith("tags/"):
        return ParsedArchiveRef(refname, "tags", rest[len("tags/") :])
    raise PreserveRefNameError(f"malformed archive ref: {refname!r}")


def _untracked_non_ignored(repo: Path) -> list[str]:
    rc, out, err = _git(repo, "ls-files", "--others", "--exclude-standard", "-z")
    if rc != 0:
        raise PreserveGitError(err.strip() or "git ls-files failed")
    if not out:
        return []
    return [p for p in out.split("\0") if p]


def snapshot_worktree_commit(repo: Path) -> str | None:
    """Commit the working tree (untracked non-ignored included) without moving HEAD or index."""
    head = _git_out(repo, "rev-parse", "HEAD")
    with tempfile.TemporaryDirectory() as td:
        index_file = str(Path(td) / "index")
        with _with_env({"GIT_INDEX_FILE": index_file}):
            rc, _, err = _git(repo, "read-tree", head)
            if rc != 0:
                raise PreserveGitError(err.strip() or "git read-tree failed")
            rc, _, err = _git(repo, "add", "-u")
            if rc != 0:
                raise PreserveGitError(err.strip() or "git add -u failed")
            untracked = _untracked_non_ignored(repo)
            if untracked:
                rc, _, err = _git(repo, "add", "--", *untracked)
                if rc != 0:
                    raise PreserveGitError(err.strip() or "git add (untracked) failed")
            tree = _git_out(repo, "write-tree")
    head_tree = _git_out(repo, "rev-parse", f"{head}^{{tree}}")
    if tree == head_tree:
        return None
    with _with_env(
        {
            "GIT_AUTHOR_NAME": "pyforge-preserve",
            "GIT_AUTHOR_EMAIL": "pyforge-preserve@localhost",
            "GIT_COMMITTER_NAME": "pyforge-preserve",
            "GIT_COMMITTER_EMAIL": "pyforge-preserve@localhost",
        }
    ):
        commit = _git_out(
            repo,
            "commit-tree",
            tree,
            "-p",
            head,
            "-m",
            "pyforge preserve snapshot",
        )
    after_head = _git_out(repo, "rev-parse", "HEAD")
    if after_head != head:
        raise PreserveGitError("snapshot moved HEAD")
    return commit


def _existing_tag_object(repo: Path, refname: str) -> str | None:
    rc, out, _ = _git(repo, "rev-parse", "--verify", f"{refname}^{{object}}")
    if rc != 0:
        return None
    return out.strip()


def _story_prefix(project_slug: str, story_key: str) -> str:
    return f"{_PRESERVE_PREFIX}{project_slug}/{story_key}/"


def _find_story_tree_noop(repo: Path, project_slug: str, story_key: str, tree: str) -> str | None:
    prefix = _story_prefix(project_slug, story_key)
    rc, out, _ = _git(repo, "for-each-ref", "--format=%(refname)", prefix)
    if rc != 0:
        return None
    for line in out.splitlines():
        ref = line.strip()
        if not ref:
            continue
        try:
            obj = _full_sha(repo, ref)
            obj_tree = _git_out(repo, "rev-parse", f"{obj}^{{tree}}")
            if obj_tree == tree:
                return ref
        except PreserveGitError:
            continue
    return None


def _parse_tag_message(message: str) -> PreserveTrailers:
    fields: dict[str, str] = {}
    for line in message.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    missing = sorted(PRESERVE_TRAILERS - set(fields))
    if missing:
        raise PreserveRefError(f"tag message missing trailers: {', '.join(missing)}")
    provenance = fields["Preserve-Provenance"]
    if provenance not in PROVENANCE_VALUES:
        raise PreserveRefError(f"invalid Preserve-Provenance: {provenance!r}")
    producer = fields["Preserve-Producer"]
    if producer not in PRESERVE_PRODUCERS:
        raise PreserveRefError(f"invalid Preserve-Producer: {producer!r}")
    return PreserveTrailers(
        producer=producer,
        provenance=provenance,
        reason=fields["Preserve-Reason"],
        source=fields["Preserve-Source"],
        run=fields["Preserve-Run"],
        journal=fields["Preserve-Journal"],
        commit=fields["Preserve-Commit"],
    )


def _commit_state(repo: Path, commit: str) -> PreserveState:
    rc, _, _ = _git(repo, "merge-base", "--is-ancestor", commit, ORIGIN_MAIN)
    if rc == 0:
        return PreserveState.LANDED
    return PreserveState.OPEN


def tag_preserve(
    repo: Path,
    *,
    refname: str,
    commit: str,
    trailers: PreserveTrailers,
) -> TagPreserveResult:
    """Write a local annotated preserve tag; dedup by name and story tree."""
    parse_preserve_ref(refname)
    full_commit = _full_sha(repo, commit)
    if trailers.commit != full_commit:
        raise PreserveRefError("Preserve-Commit trailer must match the tagged commit")
    existing = _existing_tag_object(repo, refname)
    if existing is not None:
        if existing == full_commit:
            return TagPreserveResult(refname, full_commit, True)
        raise PreserveRefConflictError(f"{refname} already points at {existing}, not {full_commit}")
    parsed = parse_preserve_ref(refname)
    commit_tree = _git_out(repo, "rev-parse", f"{full_commit}^{{tree}}")
    if parsed.project_slug and parsed.story_key:
        noop_ref = _find_story_tree_noop(repo, parsed.project_slug, parsed.story_key, commit_tree)
        if noop_ref is not None:
            return TagPreserveResult(noop_ref, full_commit, True)
    message = trailers.format_message()
    short_ref = refname.removeprefix("refs/tags/")
    _git_out(repo, "tag", "-a", "-m", message, short_ref, full_commit)
    return TagPreserveResult(refname, full_commit, False)


def list_preserves(
    repo: Path,
    *,
    station: str | None = None,
    story: str | None = None,
    producer: str | None = None,
    state: PreserveState | None = None,
) -> list[PreserveRecord]:
    """List local preserve tags with parsed trailers and derived state."""
    rc, out, err = _git(repo, "for-each-ref", "--format=%(refname)", _PRESERVE_PREFIX)
    if rc != 0:
        raise PreserveGitError(err.strip() or "git for-each-ref failed")
    records: list[PreserveRecord] = []
    for line in out.splitlines():
        refname = line.strip()
        if not refname:
            continue
        try:
            parsed = parse_preserve_ref(refname)
        except PreserveRefNameError:
            continue
        if station is not None and parsed.project_slug != station:
            continue
        if story is not None and parsed.story_key != story:
            continue
        if producer is not None and parsed.producer != producer:
            continue
        short = refname.removeprefix("refs/tags/")
        object_sha = _full_sha(repo, refname)
        msg = _git_out(repo, "cat-file", "-p", object_sha)
        # Annotated tag object: skip header lines to message body
        body = msg.split("\n\n", 1)[-1] if "\n\n" in msg else ""
        trailers = _parse_tag_message(body)
        tagged_commit = _full_sha(repo, f"{refname}^{{commit}}")
        derived = _commit_state(repo, tagged_commit)
        if state is not None and derived != state:
            continue
        records.append(
            PreserveRecord(
                refname=refname,
                object_sha=tagged_commit,
                project_slug=parsed.project_slug,
                story_key=parsed.story_key,
                producer=parsed.producer,
                sha8=parsed.sha8,
                state=derived,
                trailers=trailers,
            )
        )
    records.sort(key=lambda r: r.refname)
    return records
