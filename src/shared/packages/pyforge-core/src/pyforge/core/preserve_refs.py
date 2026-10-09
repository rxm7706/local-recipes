"""pyforge.core.preserve_refs -- ONE shared grammar for preserved-work refs (Story 87.3).

Renders and parses ``refs/tags/preserve/…`` and ``refs/tags/archive/…`` names,
snapshots a dirty worktree without moving branch/HEAD/index, writes annotated
preserve tags with seven ``Preserve-*`` trailers, deduplicates by name and by
story tree, and lists preserves with derived ``open`` / ``landed`` state.

Story 87.9 adds the READER side -- the helpers every preserve reader (the
``scripts/`` detectors, ``fleet_picture``, ``marshal status``) imports instead of
re-deriving a name or an "is it on origin" answer: ``normalize_ref``,
``ref_on_origin`` (``git ls-remote``, never local tag presence -- a plain fetch
never follows a tag that points off the fetched branches),
``preserve_artifact_reachable``, ``recovery_refs_for_run`` and
``observe_preserve_debt``.

Stdlib-only (plus ``pyforge.core.process`` for git); imports no ``pyforge.<station>``.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pyforge.core.process import PosixProcess, ProcessError, ProcessPort

PRESERVE_REF_PREFIX = "refs/tags/preserve/"
ARCHIVE_REF_PREFIX = "refs/tags/archive/"
_PRESERVE_PREFIX = PRESERVE_REF_PREFIX
_ARCHIVE_PREFIX = ARCHIVE_REF_PREFIX

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
ORIGIN_REMOTE = "origin"

DEFAULT_PER_FILE_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_PUSH_CAP_PER_RUN = 20
DEFAULT_PUSH_CAP_PER_STORY = 20

PREFLIGHT_PRESERVE_TAGS_PROOF_ENV = "PYFORGE_PREFLIGHT_PRESERVE_TAGS_PROOF"

PRESERVE_PURGE_LIST_REL = "docs/governance/preserve-purge-list.json"

_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("anthropic-api-key", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("github-pat", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
    ("pem-private-key-header", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
)

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
    RETIRED = "retired"


class ContentGateReason(StrEnum):
    PURGE_SHA = "purge-listed-sha"
    PURGE_PATH = "purge-listed-path"
    SECRET = "secret-scan"
    SIZE_CAP = "size-cap"
    PUSH_CAP_RUN = "push-cap-run"
    PUSH_CAP_STORY = "push-cap-story"


@dataclass(frozen=True, slots=True)
class ContentGateFinding:
    reason: ContentGateReason
    message: str


@dataclass(frozen=True, slots=True)
class PurgeList:
    commit_shas: frozenset[str]
    paths: frozenset[str]


@dataclass(frozen=True, slots=True)
class PushPreserveResult:
    refname: str
    pushed: bool
    findings: tuple[ContentGateFinding, ...]


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


def _existing_tag_commit(repo: Path, refname: str) -> str | None:
    rc, out, _ = _git(repo, "rev-parse", "--verify", f"{refname}^{{commit}}")
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
    existing = _existing_tag_commit(repo, refname)
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


def _repo_root_from(repo: Path) -> Path:
    return Path(_git_out(repo, "rev-parse", "--show-toplevel"))


def default_purge_list_path(repo: Path) -> Path:
    return _repo_root_from(repo) / PRESERVE_PURGE_LIST_REL


def load_purge_list(path: Path) -> PurgeList:
    raw = json.loads(path.read_text(encoding="utf-8"))
    shas = frozenset(str(s).lower() for s in raw.get("commit_shas", ()))
    paths = frozenset(str(p) for p in raw.get("paths", ()))
    return PurgeList(commit_shas=shas, paths=paths)


def _is_preserve_or_archive_tag(refname: str) -> bool:
    return refname.startswith(PRESERVE_REF_PREFIX) or refname.startswith(ARCHIVE_REF_PREFIX)


def _tree_paths(repo: Path, tree: str) -> set[str]:
    rc, out, err = _git(repo, "ls-tree", "-r", "--name-only", tree)
    if rc != 0:
        raise PreserveGitError(err.strip() or "git ls-tree failed")
    return {line.strip() for line in out.splitlines() if line.strip()}


def _commit_descends_from(repo: Path, commit: str, ancestor: str) -> bool:
    rc, _, _ = _git(repo, "merge-base", "--is-ancestor", ancestor, commit)
    return rc == 0


def _scan_blob_for_secrets(repo: Path, blob: str) -> ContentGateFinding | None:
    rc, out, err = _git(repo, "cat-file", "-p", blob)
    if rc != 0:
        raise PreserveGitError(err.strip() or "git cat-file failed")
    text = out.replace("\x00", "")
    for name, pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            return ContentGateFinding(
                ContentGateReason.SECRET,
                f"secret scan matched {name} (blob {blob[:8]})",
            )
    return None


def _blob_size(repo: Path, blob: str) -> int:
    rc, out, err = _git(repo, "cat-file", "-s", blob)
    if rc != 0:
        raise PreserveGitError(err.strip() or "git cat-file -s failed")
    return int(out.strip())


def run_content_gate(
    repo: Path,
    *,
    commit: str,
    purge_list: PurgeList,
    per_file_max_bytes: int = DEFAULT_PER_FILE_MAX_BYTES,
) -> tuple[ContentGateFinding, ...]:
    """Refuse (a) purge-listed ancestry, (b) purge-listed paths, (c) secrets, (d) oversize blobs."""
    findings: list[ContentGateFinding] = []
    full_commit = _full_sha(repo, commit)
    for listed in purge_list.commit_shas:
        if full_commit.startswith(listed) or listed.startswith(full_commit):
            findings.append(
                ContentGateFinding(ContentGateReason.PURGE_SHA, f"commit matches purge-listed sha {listed[:8]}")
            )
            break
        if _commit_descends_from(repo, full_commit, listed):
            findings.append(
                ContentGateFinding(
                    ContentGateReason.PURGE_SHA,
                    f"commit descends from purge-listed sha {listed[:8]}",
                )
            )
            break
    tree = _git_out(repo, "rev-parse", f"{full_commit}^{{tree}}")
    if purge_list.paths:
        paths_in_tree = _tree_paths(repo, tree)
        for banned in purge_list.paths:
            if banned in paths_in_tree:
                findings.append(
                    ContentGateFinding(ContentGateReason.PURGE_PATH, f"tree carries purge-listed path {banned!r}")
                )
    rc, out, err = _git(repo, "ls-tree", "-r", tree)
    if rc != 0:
        raise PreserveGitError(err.strip() or "git ls-tree failed")
    for line in out.splitlines():
        if not line.strip():
            continue
        _mode, _type, blob, path = line.split(None, 3)
        size = _blob_size(repo, blob)
        if size > per_file_max_bytes:
            findings.append(
                ContentGateFinding(
                    ContentGateReason.SIZE_CAP,
                    f"file {path!r} exceeds cap ({size} > {per_file_max_bytes} bytes)",
                )
            )
        secret_hit = _scan_blob_for_secrets(repo, blob)
        if secret_hit is not None:
            findings.append(secret_hit)
    return tuple(findings)


def _remote_has_ref(repo: Path, refname: str, remote: str = ORIGIN_REMOTE) -> bool:
    rc, out, _ = _git(repo, "ls-remote", remote, refname)
    if rc != 0:
        return False
    return bool(out.strip())


def list_pending_preserve_refs(repo: Path, *, remote: str = ORIGIN_REMOTE) -> list[str]:
    """Local preserve/archive tags not listed on ``remote``."""
    pending: list[str] = []
    for prefix in (PRESERVE_REF_PREFIX, ARCHIVE_REF_PREFIX):
        rc, out, err = _git(repo, "for-each-ref", "--format=%(refname)", prefix)
        if rc != 0:
            raise PreserveGitError(err.strip() or "git for-each-ref failed")
        for line in out.splitlines():
            ref = line.strip()
            if not ref:
                continue
            if not _remote_has_ref(repo, ref, remote=remote):
                pending.append(ref)
    pending.sort()
    return pending


def push_preserve_ref(
    repo: Path,
    refname: str,
    *,
    purge_list_path: Path | None = None,
    remote: str = ORIGIN_REMOTE,
    per_file_max_bytes: int = DEFAULT_PER_FILE_MAX_BYTES,
    run_push_count: int = 0,
    story_push_counts: dict[str, int] | None = None,
    max_per_run: int = DEFAULT_PUSH_CAP_PER_RUN,
    max_per_story: int = DEFAULT_PUSH_CAP_PER_STORY,
) -> PushPreserveResult:
    """Run the content gate, then push one tag refspec (never ``--tags``)."""
    if not _is_preserve_or_archive_tag(refname):
        raise PreserveRefNameError(f"not a preserve or archive tag: {refname!r}")
    story_push_counts = story_push_counts if story_push_counts is not None else {}
    cap_findings: list[ContentGateFinding] = []
    if run_push_count >= max_per_run:
        cap_findings.append(
            ContentGateFinding(ContentGateReason.PUSH_CAP_RUN, f"per-run push cap ({max_per_run}) exceeded")
        )
    story_key: str | None = None
    try:
        if refname.startswith(PRESERVE_REF_PREFIX):
            parsed = parse_preserve_ref(refname)
            if parsed.project_slug and parsed.story_key:
                story_key = f"{parsed.project_slug}/{parsed.story_key}"
    except PreserveRefNameError:
        pass
    if story_key is not None and story_push_counts.get(story_key, 0) >= max_per_story:
        cap_findings.append(
            ContentGateFinding(
                ContentGateReason.PUSH_CAP_STORY,
                f"per-story push cap ({max_per_story}) exceeded for {story_key}",
            )
        )
    if cap_findings:
        return PushPreserveResult(refname, False, tuple(cap_findings))

    commit = _full_sha(repo, f"{refname}^{{commit}}")
    plist_path = purge_list_path if purge_list_path is not None else default_purge_list_path(repo)
    purge_list = load_purge_list(plist_path)
    gate_findings = run_content_gate(repo, commit=commit, purge_list=purge_list, per_file_max_bytes=per_file_max_bytes)
    if gate_findings:
        return PushPreserveResult(refname, False, gate_findings)

    refspec = f"{refname}:{refname}"
    with _with_env({PREFLIGHT_PRESERVE_TAGS_PROOF_ENV: "1"}):
        rc, out, err = _git(repo, "push", remote, refspec)
    if rc != 0:
        raise PreserveGitError(err.strip() or out.strip() or "git push failed")
    if not _remote_has_ref(repo, refname, remote=remote):
        raise PreserveGitError(f"ls-remote did not list {refname} after push")
    return PushPreserveResult(refname, True, ())


# ---------------------------------------------------------------------------
# Story 87.9 -- the reader side: every preserve reader asks these, never git by hand.
# ---------------------------------------------------------------------------

ATTEMPT_PRESERVE_BRANCH_PREFIX = "attempt-preserve/"
ATTEMPT_PRESERVE_DIRTY_PREFIX = "refs/attempt-preserve-dirty/"
_ATTEMPT_PRESERVE_HEADS_PREFIX = "refs/heads/" + ATTEMPT_PRESERVE_BRANCH_PREFIX

# A hung remote must never hang a reader: one bounded ``ls-remote`` per question.
REMOTE_PROBE_TIMEOUT_S = 30.0

_FIELD_SEP = "\x1f"
_RECORD_SEP = "\x1e"


def _git_via(
    process: ProcessPort | None,
    repo: Path,
    args: tuple[str, ...],
    *,
    timeout_s: float | None = None,
) -> tuple[int, str, str]:
    """``git <args>`` through ``process`` (a station's injected port) or the module default."""
    runner = process if process is not None else _PROCESS
    try:
        result = runner.run(["git", *args], cwd=repo, timeout_s=timeout_s)
    except ProcessError as exc:
        raise PreserveGitError(str(exc)) from exc
    return result.returncode, result.stdout, result.stderr


def normalize_ref(ref: str) -> str:
    """The full refname a reader-supplied ``ref`` names.

    ``refs/...`` is kept; a bare ``preserve/...`` / ``archive/...`` is a tag; any other bare
    name is a branch (the shape a journal's ``preserve_ref`` takes: ``attempt-preserve/<run>-<sha8>``).
    """
    cleaned = ref.strip()
    if cleaned.startswith("refs/"):
        return cleaned
    if cleaned.startswith(("preserve/", "archive/")):
        return f"refs/tags/{cleaned}"
    return f"refs/heads/{cleaned}"


def short_ref_name(refname: str) -> str:
    """``refs/heads/x`` -> ``x``, ``refs/tags/x`` -> ``x``; anything else unchanged."""
    for prefix in ("refs/heads/", "refs/tags/"):
        if refname.startswith(prefix):
            return refname[len(prefix) :]
    return refname


def is_preserve_tag_ref(ref: str) -> bool:
    """True when ``ref`` names a tag under the preserve namespace (any spelling ``normalize_ref`` takes)."""
    return normalize_ref(ref).startswith(PRESERVE_REF_PREFIX)


def ref_exists_local(repo: Path, ref: str, *, process: ProcessPort | None = None) -> bool:
    """Whether ``ref`` resolves to a ref in ``repo``'s own ref store (never says anything about origin)."""
    if not ref.strip() or not repo.is_dir():
        return False
    try:
        rc, _, _ = _git_via(process, repo, ("show-ref", "--verify", "--quiet", normalize_ref(ref)), timeout_s=30.0)
    except PreserveGitError:
        return False
    return rc == 0


def remote_ref_names(
    repo: Path,
    patterns: tuple[str, ...] | list[str],
    *,
    remote: str = ORIGIN_REMOTE,
    process: ProcessPort | None = None,
) -> frozenset[str] | None:
    """Full refnames ``git ls-remote`` lists for ``patterns``; ``None`` when the remote could not be read.

    ``None`` is NOT "nothing there": an unreadable remote proves nothing either way, and a
    caller that needs the difference (status's could-not-observe) reads it from here.
    """
    try:
        rc, out, _ = _git_via(process, repo, ("ls-remote", remote, *patterns), timeout_s=REMOTE_PROBE_TIMEOUT_S)
    except PreserveGitError:
        return None
    if rc != 0:
        return None
    names: set[str] = set()
    for line in out.splitlines():
        _sha, _, name = line.partition("\t")
        name = name.strip()
        if name.endswith("^{}"):
            name = name[: -len("^{}")]
        if name:
            names.add(name)
    return frozenset(names)


def ref_on_origin(
    repo: Path,
    ref: str,
    *,
    remote: str = ORIGIN_REMOTE,
    process: ProcessPort | None = None,
) -> bool:
    """Whether ``ref`` is listed on ``remote`` -- read from the remote, never from a local tag.

    A local tag that ``ls-remote`` does not list is NOT on origin; an unreadable remote is
    also ``False`` (not proven present).
    """
    if not ref.strip() or not repo.is_dir():
        return False
    full = normalize_ref(ref)
    names = remote_ref_names(repo, [full], remote=remote, process=process)
    return names is not None and full in names


def preserve_artifact_reachable(
    repo: Path,
    ref: str,
    *,
    remote: str = ORIGIN_REMOTE,
    process: ProcessPort | None = None,
) -> bool:
    """A preserve ref counts as present when it exists locally OR is listed on ``remote``.

    Local first (a ``preserve/`` tag or an ``attempt-preserve/*`` branch, offline-durable per
    AD-29); then ``ls-remote`` for a ref that lives only on origin.
    """
    if not ref.strip():
        return False
    return ref_exists_local(repo, ref, process=process) or ref_on_origin(repo, ref, remote=remote, process=process)


@dataclass(frozen=True, slots=True)
class LocalPreserveTag:
    """One local preserve tag read leniently (a malformed tag is listed, never raised on)."""

    refname: str
    commit: str
    run: str | None
    producer: str | None
    project_slug: str | None
    story_key: str | None
    sha8: str | None


def list_local_preserve_tags(repo: Path, *, process: ProcessPort | None = None) -> list[LocalPreserveTag]:
    """Every local tag under the preserve namespace with its peeled commit and ``Preserve-Run``.

    Unlike ``list_preserves`` this never raises on a tag whose message lacks a trailer or
    whose name does not parse: a reader that crashed on one bad tag would report nothing.
    """
    fmt = f"%(refname){_FIELD_SEP}%(*objectname){_FIELD_SEP}%(objectname){_FIELD_SEP}%(contents){_RECORD_SEP}"
    rc, out, err = _git_via(process, repo, ("for-each-ref", f"--format={fmt}", PRESERVE_REF_PREFIX), timeout_s=60.0)
    if rc != 0:
        raise PreserveGitError(err.strip() or "git for-each-ref failed")
    tags: list[LocalPreserveTag] = []
    for record in out.split(_RECORD_SEP):
        record = record.strip("\n")
        if not record.strip():
            continue
        fields = record.split(_FIELD_SEP, 3)
        if len(fields) != 4:
            continue
        refname, peeled, objectname, contents = (f.strip() for f in fields)
        if not refname.startswith(PRESERVE_REF_PREFIX):
            continue
        run: str | None = None
        for line in contents.splitlines():
            key, _, value = line.partition(":")
            if key.strip() == "Preserve-Run":
                run = value.strip() or None
        try:
            parsed = parse_preserve_ref(refname)
        except PreserveRefNameError:
            parsed = None
        tags.append(
            LocalPreserveTag(
                refname=refname,
                commit=peeled or objectname,
                run=run,
                producer=parsed.producer if parsed else None,
                project_slug=parsed.project_slug if parsed else None,
                story_key=parsed.story_key if parsed else None,
                sha8=parsed.sha8 if parsed else None,
            )
        )
    tags.sort(key=lambda t: t.refname)
    return tags


def _branch_head8(branch_short: str, run_id: str) -> str | None:
    """The ``<head8>`` of ``attempt-preserve/<run_id>-<head8>``, or ``None`` for another shape."""
    prefix = f"{ATTEMPT_PRESERVE_BRANCH_PREFIX}{run_id}-"
    if not branch_short.startswith(prefix):
        return None
    head = branch_short[len(prefix) :]
    return head[:8] if head else None


def recovery_refs_for_run(
    repo: Path,
    run_id: str,
    *,
    remote: str = ORIGIN_REMOTE,
    process: ProcessPort | None = None,
) -> list[str]:
    """Where a baseline-drift defer's work survives for ``run_id``, a ``preserve/`` tag first.

    * a local preserve tag whose ``Preserve-Run`` trailer is ``run_id``;
    * ``attempt-preserve/<run_id>-*`` branches, local and on ``remote`` (an origin-only
      branch is still a recovery source);
    * a bmad-loop preserve tag (local, or listed on ``remote``) named for the same head the
      branch is -- the tag is the durable twin of the engine's scratch branch.

    Names come back short (``preserve/...``, ``attempt-preserve/...``); a tag precedes a branch.
    """
    if not run_id:
        return []
    tags: list[str] = []
    branches: list[str] = []
    try:
        rc, out, _ = _git_via(
            process,
            repo,
            ("for-each-ref", "--format=%(refname:short)", f"{_ATTEMPT_PRESERVE_HEADS_PREFIX}{run_id}-*"),
            timeout_s=30.0,
        )
        if rc == 0:
            branches = [line.strip() for line in out.splitlines() if line.strip()]
        local_tags = list_local_preserve_tags(repo, process=process)
    except PreserveGitError:
        return []
    remote_branches = remote_ref_names(
        repo, [f"{_ATTEMPT_PRESERVE_HEADS_PREFIX}{run_id}-*"], remote=remote, process=process
    )
    for name in sorted(remote_branches or ()):
        short = short_ref_name(name)
        if short not in branches:
            branches.append(short)
    heads8 = {h for h in (_branch_head8(b, run_id) for b in branches) if h}
    for tag in local_tags:
        if tag.run == run_id or (tag.producer == "bmad-loop" and tag.sha8 in heads8):
            tags.append(short_ref_name(tag.refname))
    if heads8:
        remote_tags = remote_ref_names(repo, [f"{PRESERVE_REF_PREFIX}*"], remote=remote, process=process)
        for name in sorted(remote_tags or ()):
            try:
                parsed = parse_preserve_ref(name)
            except PreserveRefNameError:
                continue
            short = short_ref_name(name)
            if parsed.producer == "bmad-loop" and parsed.sha8 in heads8 and short not in tags:
                tags.append(short)
    return [*dict.fromkeys(tags), *branches]


@dataclass(frozen=True, slots=True)
class PreserveObservation:
    """What ``marshal status`` reads of preserve debt for one repository."""

    tags: tuple[LocalPreserveTag, ...]
    local_only_tags: tuple[LocalPreserveTag, ...]
    unpromoted_scratch: tuple[str, ...]


def _scratch_refs(repo: Path, process: ProcessPort | None) -> list[tuple[str, str]]:
    rc, out, err = _git_via(
        process,
        repo,
        (
            "for-each-ref",
            "--format=%(refname)" + _FIELD_SEP + "%(objectname)",
            _ATTEMPT_PRESERVE_HEADS_PREFIX,
            ATTEMPT_PRESERVE_DIRTY_PREFIX,
        ),
        timeout_s=60.0,
    )
    if rc != 0:
        raise PreserveGitError(err.strip() or "git for-each-ref failed")
    refs: list[tuple[str, str]] = []
    for line in out.splitlines():
        refname, sep, commit = line.partition(_FIELD_SEP)
        if sep and refname.strip() and commit.strip():
            refs.append((refname.strip(), commit.strip()))
    return sorted(refs)


def _scratch_is_durable(repo: Path, commit: str, process: ProcessPort | None) -> bool:
    """A scratch ref is promoted when a preserve tag holds its commit; landed work needs none."""
    rc, out, _ = _git_via(
        process, repo, ("for-each-ref", "--contains", commit, "--format=%(refname)", PRESERVE_REF_PREFIX)
    )
    if rc == 0 and out.strip():
        return True
    rc, _, _ = _git_via(process, repo, ("merge-base", "--is-ancestor", commit, ORIGIN_MAIN))
    return rc == 0


def observe_preserve_debt(
    repo: Path,
    *,
    remote: str = ORIGIN_REMOTE,
    process: ProcessPort | None = None,
) -> PreserveObservation | None:
    """Local-only preserve tags and unpromoted engine scratch refs; ``None`` when unobservable.

    ``None`` -- never an empty observation -- when git cannot list refs, or local preserve tags
    exist and ``remote`` cannot be read (whether they are on origin is then unknown).
    """
    try:
        tags = list_local_preserve_tags(repo, process=process)
        scratch = _scratch_refs(repo, process)
        unpromoted = tuple(refname for refname, commit in scratch if not _scratch_is_durable(repo, commit, process))
    except PreserveGitError:
        return None
    local_only: tuple[LocalPreserveTag, ...] = ()
    if tags:
        listed = remote_ref_names(repo, [f"{PRESERVE_REF_PREFIX}*"], remote=remote, process=process)
        if listed is None:
            return None
        local_only = tuple(t for t in tags if t.refname not in listed)
    return PreserveObservation(tags=tuple(tags), local_only_tags=local_only, unpromoted_scratch=unpromoted)
