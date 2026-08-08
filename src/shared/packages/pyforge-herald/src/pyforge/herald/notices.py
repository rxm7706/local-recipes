"""Notice storage, authoring, and lifecycle (Epic 10, Moment 4 -- Operations
Notices), scaled down per the effort's own scoping decision: local-storage,
CLI-triggered, no server, no live database. The full-spec live-backend
version (a real database index, HTTP redirects, a scheduled draft-review
job) is captured as a Dream at
``docs/dreams/herald-moments-2-4-live-backend.md`` and deliberately not
built here -- Herald has no running server anywhere (a stateless CLI plus a
static web dashboard), so nothing in this module talks to a database or a
socket.

**Storage shape (Story 10.1).** Two files per notice, always written
together and always in lock-step:

* ``notices/YYYY-MM/<type>/<component>.md`` -- the durable, human-readable,
  git-diffable record (``YYYY-MM`` is the notice's *creation* month, never
  re-derived on edit). Frontmatter carries every structured field; the body
  carries the ``what``/``why``/``migration`` prose under their own
  headings. This mirrors ``presentations/<slug>/`` as a top-level,
  git-tracked convention this repo already uses for durable generated
  content.
* ``.herald/notices-index.json`` -- a local index for fast discovery
  (``list``/``get``/category and date-range filtering) without re-globbing
  the whole ``notices/`` tree on every command, mirroring ``state.py``'s
  atomic-write convention (temp file + ``os.replace``). It is a
  **denormalized cache of the same data** the markdown file carries --
  every field on ``Notice`` (including ``what``/``why``/``migration``)
  round-trips through it too, not just filter metadata. That duplication is
  a deliberate simplicity trade: a single writer (this module) keeps both
  representations in lock-step on every call, so ``get`` never has to
  reopen and re-parse a markdown file just to answer "what does this notice
  say" -- and if the index is ever lost or corrupted, it holds no
  information the markdown tree does not already carry (a future
  ``reindex`` command could rebuild it by re-parsing every ``.md`` file's
  frontmatter + headings; not implemented here, out of scope for this
  effort).

**Edit history (Story 10.1's "versioning" AC).** Two complementary trails,
deliberately not one: the index's own ``revisions`` list (a short
``{"edited_at", "summary"}`` per change -- "what kind of edit, when") is
cheap to read for a quick audit without a git checkout; the markdown file's
own git history is the full content diff for any revision, since every
author/publish/close call rewrites it as ordinary tracked text. Neither
alone was judged sufficient: ``revisions`` alone loses the actual before/
after text; git history alone gives no fast in-index answer to "has this
been edited" without a shell out.

**Redirects (Story 10.3, scaled down).** ``notices/redirects`` in the index
document maps an old component name to its new one. This is file-based
bookkeeping only -- **not an HTTP redirect**, since no server exists to
serve one; a renamed component's old name simply resolves through this map
when looked up via ``get_notice``. Documented explicitly here because the
original (unscaled) Epic 10 AC talks about "permanent URLs" and "no
404s", language that presumes a live web backend this effort does not
build.

**Lifecycle (Story 10.6).** ``draft -> published -> closed``, one-way (no
un-publish, no re-opening a closed notice) -- publish requires a draft,
close requires a published notice. ``closed_by`` is a best-effort operator
identity: ``auth.AuthContext`` carries only a ``role``/``source`` pair, not
an operator name or user id (Story 6.3's own scope boundary), so this
module accepts whatever the caller passes and falls back to a placeholder
string when it passes nothing -- a real operator-identity concept is a gap
this module does not attempt to close.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from . import errors

NOTICE_TYPES: tuple[str, ...] = ("deprecation", "fix", "eol")
NOTICE_STATUSES: tuple[str, ...] = ("draft", "published", "closed")

DEFAULT_NOTICES_DIR = Path("notices")
"""Root of the markdown archive tree, relative to a repo root the caller
resolves (mirrors ``state.py``'s ``DEFAULT_STATE_PATH`` convention: this
module never assumes a cwd)."""

DEFAULT_INDEX_PATH = Path(".herald/notices-index.json")

UNKNOWN_OPERATOR = "unknown-operator"
"""Placeholder ``closed_by`` when the caller has no operator identity to
pass -- see the module docstring's Lifecycle section."""

_COMPONENT_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
_INDEX_FIELDS = frozenset(
    (
        "type",
        "component",
        "what",
        "why",
        "migration",
        "deadline",
        "reason_link",
        "status",
        "path",
        "created_at",
        "published_at",
        "closed_at",
        "closed_by",
        "close_reason",
        "revisions",
    )
)


@dataclass(frozen=True)
class Notice:
    """One notice, field-for-field what both the markdown file and the
    index entry carry (see module docstring on why both hold the same
    data)."""

    type: str
    component: str
    what: str
    why: str
    migration: str
    deadline: str | None
    reason_link: str | None
    status: str
    path: str
    created_at: str
    published_at: str | None = None
    closed_at: str | None = None
    closed_by: str | None = None
    close_reason: str | None = None
    revisions: tuple[dict[str, str], ...] = ()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _validate_component(component: object) -> str:
    if not isinstance(component, str) or not _COMPONENT_RE.match(component):
        raise errors.HeraldError(
            f"invalid component name {component!r}: must be a non-empty string "
            f"of letters, digits, '.', '_', or '-'"
        )
    return component


def _validate_type(notice_type: object) -> str:
    if notice_type not in NOTICE_TYPES:
        raise errors.HeraldError(
            f"invalid notice type {notice_type!r}; expected one of "
            f"{', '.join(NOTICE_TYPES)}"
        )
    return notice_type  # type: ignore[return-value]


# --- index document I/O (mirrors state.py's atomic-write convention) -----


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError(f"duplicate key {key!r}")
        document[key] = value
    return document


def _load_index_document(index_path: Path) -> dict[str, object]:
    """The whole index file as ``{"notices": {...}, "redirects": {...}}``,
    or a fresh empty shape when the file does not exist yet. Any other
    failure to read it is a structural failure (AD-6): raises
    ``errors.HeraldError`` rather than leaking a bare parse/OS error."""
    try:
        with index_path.open(encoding="utf-8") as fh:
            document = json.load(fh, object_pairs_hook=_reject_duplicate_keys)
    except FileNotFoundError:
        return {"notices": {}, "redirects": {}}
    except (ValueError, OSError, RecursionError) as exc:
        raise errors.HeraldError(
            f"notices index {index_path} could not be read: {exc}"
        ) from exc
    if (
        not isinstance(document, dict)
        or not isinstance(document.get("notices"), dict)
        or not isinstance(document.get("redirects"), dict)
    ):
        raise errors.HeraldError(
            f"notices index {index_path} is malformed: expected an object "
            f"with 'notices' and 'redirects' sub-objects"
        )
    return document


def _write_index_document(index_path: Path, document: dict[str, object]) -> None:
    """Atomic write (temp file in the same directory, then ``os.replace``)
    -- mirrors ``state.write``'s crash-safety, including its limit: neither
    fsyncs, so surviving power loss is the filesystem's business."""
    could_not_write = f"notices index {index_path} could not be written"
    try:
        index_path.parent.mkdir(parents=True, exist_ok=True)
        handle, tmp_name = tempfile.mkstemp(
            dir=index_path.parent, prefix=f".{index_path.name}-", suffix=".tmp"
        )
    except OSError as exc:
        raise errors.HeraldError(f"{could_not_write}: {exc}") from exc
    try:
        try:
            fh = os.fdopen(handle, "w", encoding="utf-8")
        except BaseException:
            os.close(handle)
            raise
        with fh:
            json.dump(document, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp_name, index_path)
    except BaseException as exc:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        if isinstance(exc, (OSError, TypeError, ValueError, RecursionError)):
            raise errors.HeraldError(f"{could_not_write}: {exc}") from exc
        raise


def _entry_to_notice(entry: dict[str, object]) -> Notice:
    unknown = sorted(set(entry) - _INDEX_FIELDS)
    if unknown:
        raise errors.HeraldError(
            f"notices index entry for {entry.get('component')!r} carries "
            f"unknown field(s): {', '.join(map(repr, unknown))}"
        )
    revisions = entry.get("revisions", [])
    if not isinstance(revisions, list):
        raise errors.HeraldError(
            f"notices index entry for {entry.get('component')!r} has a "
            f"malformed 'revisions' field"
        )
    kwargs = {k: v for k, v in entry.items() if k != "revisions"}
    return Notice(revisions=tuple(revisions), **kwargs)


def _notice_to_entry(notice: Notice) -> dict[str, object]:
    entry = {
        "type": notice.type,
        "component": notice.component,
        "what": notice.what,
        "why": notice.why,
        "migration": notice.migration,
        "deadline": notice.deadline,
        "reason_link": notice.reason_link,
        "status": notice.status,
        "path": notice.path,
        "created_at": notice.created_at,
        "published_at": notice.published_at,
        "closed_at": notice.closed_at,
        "closed_by": notice.closed_by,
        "close_reason": notice.close_reason,
        "revisions": list(notice.revisions),
    }
    return entry


# --- markdown rendering (the durable, git-diffable mirror) ----------------


def _render_markdown(notice: Notice) -> str:
    front_lines = [
        f"type: {notice.type}",
        f"component: {notice.component}",
        f"status: {notice.status}",
        f"deadline: {notice.deadline or ''}",
        f"reason_link: {notice.reason_link or ''}",
        f"created_at: {notice.created_at}",
        f"published_at: {notice.published_at or ''}",
        f"closed_at: {notice.closed_at or ''}",
        f"closed_by: {notice.closed_by or ''}",
        f"close_reason: {notice.close_reason or ''}",
    ]
    front = "\n".join(front_lines)
    return (
        f"---\n{front}\n---\n\n"
        f"# {notice.component}\n\n"
        f"## What\n\n{notice.what}\n\n"
        f"## Why\n\n{notice.why}\n\n"
        f"## Migration\n\n{notice.migration}\n"
    )


def _notice_path(
    notices_dir: Path, notice_type: str, component: str, created_at: str
) -> Path:
    year_month = created_at[:7]  # created_at is ISO 8601; YYYY-MM is its prefix
    return notices_dir / year_month / notice_type / f"{component}.md"


def _write_markdown(repo_root: Path, notice: Notice) -> None:
    """Best-effort write of the durable markdown mirror -- never the sole
    source of truth for a read (the index is), but a failure here is still
    surfaced structurally (AD-6) rather than silently skipped, since a
    notice with no markdown file would silently break the "git-diffable
    record" half of this module's contract."""
    full_path = repo_root / notice.path
    try:
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(_render_markdown(notice), encoding="utf-8")
    except OSError as exc:
        raise errors.HeraldError(
            f"notice markdown file {full_path} could not be written: {exc}"
        ) from exc


# --- redirect resolution ---------------------------------------------------

_MAX_REDIRECT_HOPS = 10


def _resolve_component(redirects: dict[str, object], component: str) -> str:
    """Follow ``redirects`` (old -> new) to the current component name,
    capped at ``_MAX_REDIRECT_HOPS`` hops so a corrupt/cyclic redirect
    chain fails structurally instead of looping forever."""
    seen = {component}
    current = component
    for _ in range(_MAX_REDIRECT_HOPS):
        target = redirects.get(current)
        if target is None:
            return current
        if target in seen:
            raise errors.HeraldError(
                f"notices index has a redirect cycle involving {current!r}"
            )
        seen.add(target)
        current = target
    raise errors.HeraldError(
        f"redirect chain for {component!r} exceeds {_MAX_REDIRECT_HOPS} hops"
    )


# --- public operations (Stories 10.1/10.2/10.3/10.6) -----------------------


def author_notice(
    repo_root: Path,
    *,
    notice_type: str,
    component: str,
    what: str,
    why: str,
    migration: str,
    deadline: str | None,
    reason_link: str | None,
    publish: bool,
    index_path: Path | None = None,
    notices_dir: Path | None = None,
    now: str | None = None,
) -> Notice:
    """Create a new draft notice, or re-author an existing draft (appends a
    revision) -- never a published or closed one (those must go through
    ``publish_notice``/``close_notice`` instead, or the operator authors a
    new notice under a different component). ``publish=True`` publishes
    immediately, same as calling ``publish_notice`` right after."""
    _validate_type(notice_type)
    _validate_component(component)
    index_path = (
        index_path if index_path is not None else repo_root / DEFAULT_INDEX_PATH
    )
    notices_dir = (
        notices_dir if notices_dir is not None else repo_root / DEFAULT_NOTICES_DIR
    )
    timestamp = now if now is not None else _now_iso()

    document = _load_index_document(index_path)
    redirects = document["redirects"]
    if component in redirects:
        raise errors.HeraldError(
            f"component {component!r} is a redirect to "
            f"{redirects[component]!r}; author the notice under that name"
        )

    existing_raw = document["notices"].get(component)
    existing = _entry_to_notice(existing_raw) if existing_raw is not None else None
    if existing is not None and existing.status != "draft":
        raise errors.HeraldError(
            f"notice for {component!r} is already {existing.status}; cannot "
            f"re-author it (author a new notice under a different "
            f"component, or use `herald notice close` first)"
        )

    created_at = existing.created_at if existing is not None else timestamp
    relative_path = str(
        _notice_path(Path("notices"), notice_type, component, created_at)
    )
    revisions = (*(existing.revisions if existing is not None else ()),) + (
        {"edited_at": timestamp, "summary": "re-authored" if existing else "authored"},
    )

    status = "published" if publish else "draft"
    published_at = timestamp if publish else None

    notice = Notice(
        type=notice_type,
        component=component,
        what=what,
        why=why,
        migration=migration,
        deadline=deadline,
        reason_link=reason_link,
        status=status,
        path=relative_path,
        created_at=created_at,
        published_at=published_at,
        revisions=revisions,
    )
    document["notices"][component] = _notice_to_entry(notice)
    _write_index_document(index_path, document)
    _write_markdown(repo_root, notice)
    return notice


def publish_notice(
    repo_root: Path,
    component: str,
    *,
    index_path: Path | None = None,
    now: str | None = None,
) -> Notice:
    """``draft -> published`` (Story 10.6). Refuses a component with no
    notice, an already-published one, or a closed one."""
    index_path = (
        index_path if index_path is not None else repo_root / DEFAULT_INDEX_PATH
    )
    timestamp = now if now is not None else _now_iso()
    document = _load_index_document(index_path)
    resolved = _resolve_component(document["redirects"], component)
    entry = document["notices"].get(resolved)
    if entry is None:
        raise errors.HeraldError(f"no notice found for component {component!r}")
    notice = _entry_to_notice(entry)
    if notice.status == "published":
        raise errors.HeraldError(f"notice for {resolved!r} is already published")
    if notice.status == "closed":
        raise errors.HeraldError(f"notice for {resolved!r} is closed; cannot publish")
    notice = replace(
        notice,
        status="published",
        published_at=timestamp,
        revisions=notice.revisions
        + ({"edited_at": timestamp, "summary": "published"},),
    )
    document["notices"][resolved] = _notice_to_entry(notice)
    _write_index_document(index_path, document)
    _write_markdown(repo_root, notice)
    return notice


def close_notice(
    repo_root: Path,
    component: str,
    *,
    reason: str | None = None,
    closed_by: str | None = None,
    index_path: Path | None = None,
    now: str | None = None,
) -> Notice:
    """``published -> closed`` (Story 10.6). A closed notice stays archived
    and visible (``list``/``get`` still find it) but flagged
    ``status == "closed"`` as no-longer-current. Refuses a draft (must be
    published first) or an already-closed notice."""
    index_path = (
        index_path if index_path is not None else repo_root / DEFAULT_INDEX_PATH
    )
    timestamp = now if now is not None else _now_iso()
    document = _load_index_document(index_path)
    resolved = _resolve_component(document["redirects"], component)
    entry = document["notices"].get(resolved)
    if entry is None:
        raise errors.HeraldError(f"no notice found for component {component!r}")
    notice = _entry_to_notice(entry)
    if notice.status == "draft":
        raise errors.HeraldError(
            f"notice for {resolved!r} is still a draft; publish it before closing"
        )
    if notice.status == "closed":
        raise errors.HeraldError(f"notice for {resolved!r} is already closed")
    notice = replace(
        notice,
        status="closed",
        closed_at=timestamp,
        closed_by=closed_by or UNKNOWN_OPERATOR,
        close_reason=reason,
        revisions=notice.revisions + ({"edited_at": timestamp, "summary": "closed"},),
    )
    document["notices"][resolved] = _notice_to_entry(notice)
    _write_index_document(index_path, document)
    _write_markdown(repo_root, notice)
    return notice


def get_notice(
    repo_root: Path, component: str, *, index_path: Path | None = None
) -> Notice:
    """Full detail for ``component``, following a redirect if it was
    renamed (Story 10.3)."""
    index_path = (
        index_path if index_path is not None else repo_root / DEFAULT_INDEX_PATH
    )
    document = _load_index_document(index_path)
    resolved = _resolve_component(document["redirects"], component)
    entry = document["notices"].get(resolved)
    if entry is None:
        raise errors.HeraldError(f"no notice found for component {component!r}")
    return _entry_to_notice(entry)


def list_notices(
    repo_root: Path,
    *,
    category: str | None = None,
    date_range: tuple[str, str] | None = None,
    status: str | None = None,
    index_path: Path | None = None,
) -> list[Notice]:
    """Every notice matching the given filters, sorted by ``component``.

    ``status`` mirrors Success's (Epic 9) draft/published distinction: the
    default (``None``) is "everything visible" -- published and closed --
    excluding drafts; pass ``status="draft"`` to see only drafts,
    ``status="all"`` for every status, or an exact status to see only that
    one. ``date_range`` filters on ``created_at``'s date prefix (inclusive,
    ``YYYY-MM-DD`` bounds)."""
    index_path = (
        index_path if index_path is not None else repo_root / DEFAULT_INDEX_PATH
    )
    document = _load_index_document(index_path)
    notices = [_entry_to_notice(entry) for entry in document["notices"].values()]

    if status is None:
        notices = [n for n in notices if n.status in ("published", "closed")]
    elif status != "all":
        if status not in NOTICE_STATUSES:
            raise errors.HeraldError(
                f"invalid status {status!r}; expected one of "
                f"{', '.join(NOTICE_STATUSES)}, or 'all'"
            )
        notices = [n for n in notices if n.status == status]

    if category is not None:
        _validate_type(category)
        notices = [n for n in notices if n.type == category]

    if date_range is not None:
        start, end = date_range
        notices = [n for n in notices if start <= n.created_at[:10] <= end]

    return sorted(notices, key=lambda n: n.component)


def archive_rename(
    repo_root: Path,
    old_component: str,
    new_component: str,
    *,
    index_path: Path | None = None,
) -> None:
    """Record a rename redirect (Story 10.3, scaled down): a later
    ``get_notice``/``publish_notice``/``close_notice`` call for
    ``old_component`` transparently resolves to ``new_component``'s notice.

    File-based bookkeeping only -- **not an HTTP redirect** (no server
    exists to serve one). Requires ``new_component`` to already have a
    notice (nothing to redirect to otherwise) and refuses redirecting a
    component onto itself or overwriting an existing redirect silently."""
    _validate_component(old_component)
    _validate_component(new_component)
    if old_component == new_component:
        raise errors.HeraldError("cannot redirect a component to itself")
    index_path = (
        index_path if index_path is not None else repo_root / DEFAULT_INDEX_PATH
    )
    document = _load_index_document(index_path)
    if new_component not in document["notices"]:
        raise errors.HeraldError(
            f"cannot redirect to {new_component!r}: no notice exists for it yet"
        )
    if old_component in document["redirects"]:
        raise errors.HeraldError(
            f"component {old_component!r} already redirects to "
            f"{document['redirects'][old_component]!r}"
        )
    document["redirects"][old_component] = new_component
    _write_index_document(index_path, document)
