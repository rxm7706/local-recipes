"""Notice storage, authoring, and lifecycle (Epic 10, Moment 4 -- Operations
Notices), scaled down per the effort's own scoping decision: local-storage,
CLI-triggered, no server, no live database beyond the shared local one
(Story 13.3). The full-spec live-backend version (HTTP redirects, a
scheduled draft-review job) is captured as a Dream at
``docs/dreams/herald-moments-2-4-live-backend.md`` and deliberately not
built here -- Herald has no running server anywhere (a stateless CLI plus
a static web dashboard).

**Storage shape.** Two records per notice, always written together and
always in lock-step:

* ``notices/YYYY-MM/<type>/<component>.md`` -- the durable, human-readable,
  git-diffable record (``YYYY-MM`` is the notice's *creation* month, never
  re-derived on edit). Frontmatter carries every structured field; the body
  carries the ``what``/``why``/``migration`` prose under their own
  headings. This mirrors ``presentations/<slug>/`` as a top-level,
  git-tracked convention this repo already uses for durable generated
  content. Untouched by Story 13.3 -- this stays the git-tracked source of
  truth for content, including its known non-atomicity (``_write_markdown``
  is a plain ``write_text``, not temp-file-then-``os.replace``).
* A row in ``db.py``'s shared ``.herald/herald.db`` (table
  ``notices_index``, plus ``notices_redirects`` for renames) -- a local
  index for fast discovery (``list``/``get``/category and date-range
  filtering) without re-globbing the whole ``notices/`` tree on every
  command. It is a **denormalized copy of the same data** the markdown
  file carries -- every field on ``Notice`` (including
  ``what``/``why``/``migration``) round-trips through it too, not just
  filter metadata. That duplication is a deliberate simplicity trade: a
  single writer (this module) keeps both representations in lock-step on
  every call, so ``get`` never has to reopen and re-parse a markdown file
  just to answer "what does this notice say" -- and if the index is ever
  lost, it holds no information the markdown tree does not already carry
  (a future ``reindex`` command could rebuild it by re-parsing every
  ``.md`` file's frontmatter + headings; not implemented here).

**Concurrency (Story 13.1, closing ``DW-1-4-2``; Story 13.3 moved the
mechanism).** ``author_notice``, ``publish_notice``, ``close_notice``, and
``archive_rename`` each open ``db.transaction`` (SQLite's own
``BEGIN IMMEDIATE``/commit, see ``db.py``'s module docstring) around their
whole read-modify-write span, so the index write and the markdown write for
one notice land inside a single critical section. A second concurrent call
against the same ``index_path`` blocks until the first commits, closing the
writer-vs-writer markdown race as a side effect of closing the index race,
rather than as a second, separate fix.

Two kinds of check deliberately run BEFORE the transaction opens, so the
span above is the read-modify-write, not literally the whole function
body: the pure ``notice_type``/``component`` argument checks (a call that
cannot succeed should not contend on the write lock first), and
``_require_existing_index`` for the three calls that can only operate on
an existing notice (see its docstring -- opening the transaction creates
the database file and its parent directory, which those calls' error
paths never did before Story 13.1). Both are fail-fast only; the
authoritative checks stay inside the transaction.

One limit on that, carried over from Story 13.1: two callers sharing a
``repo_root`` but passing *different* explicit ``index_path`` values
serialize on nothing and can still race the same markdown file -- the
guarantee above holds for callers sharing one index, which is every caller
today. And ``_write_markdown`` is a plain ``write_text``
(truncate-then-write, not the temp-file + ``os.replace`` used for the
index before Story 13.3), so a concurrent *reader* can still observe a
partially written markdown file; serializing writers does not make a
non-atomic write atomic. Both are unchanged, out of this story's scope.

**Edit history (Story 10.1's "versioning" AC).** Two complementary trails,
deliberately not one: the index's own ``revisions`` list (a short
``{"edited_at", "summary"}`` per change -- "what kind of edit, when") is
cheap to read for a quick audit without a git checkout; the markdown file's
own git history is the full content diff for any revision, since every
author/publish/close call rewrites it as ordinary tracked text. Neither
alone was judged sufficient: ``revisions`` alone loses the actual before/
after text; git history alone gives no fast in-index answer to "has this
been edited" without a shell out.

**Redirects (Story 10.3, scaled down).** ``notices_redirects`` maps an old
component name to its new one. This is bookkeeping only -- **not an HTTP
redirect**, since no server exists to serve one; a renamed component's old
name simply resolves through this table when looked up via ``get_notice``.
Documented explicitly here because the original (unscaled) Epic 10 AC talks
about "permanent URLs" and "no 404s", language that presumes a live web
backend this effort does not build.

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
import re
import sqlite3
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from . import db, errors

NOTICE_TYPES: tuple[str, ...] = ("deprecation", "fix", "eol")
NOTICE_STATUSES: tuple[str, ...] = ("draft", "published", "closed")

DEFAULT_NOTICES_DIR = Path("notices")
"""Root of the markdown archive tree, relative to a repo root the caller
resolves (mirrors ``state.py``'s ``DEFAULT_STATE_PATH`` convention: this
module never assumes a cwd)."""

DEFAULT_INDEX_PATH = db.DEFAULT_DB_PATH
"""Redefined to ``db.DEFAULT_DB_PATH`` (Story 13.3) rather than removed, so
every existing call site needs zero changes -- see ``db.py``'s module
docstring on why one shared database, not per-module files."""

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
            f"invalid component name {component!r}: must be a non-empty string of letters, digits, '.', '_', or '-'"
        )
    return component


def _validate_type(notice_type: object) -> str:
    if notice_type not in NOTICE_TYPES:
        raise errors.HeraldError(f"invalid notice type {notice_type!r}; expected one of {', '.join(NOTICE_TYPES)}")
    return notice_type  # type: ignore[return-value]


# --- legacy JSON index reading (one-time migration import only) -----------


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError(f"duplicate key {key!r}")
        document[key] = value
    return document


def _read_legacy_index_document(index_path: Path) -> dict[str, object]:
    """The pre-Story-13.3 JSON-file reader, preserved verbatim (this was
    ``_load_index_document``'s entire body) for the one-time legacy import
    (``db.py``'s ``_import_legacy_v1``) -- so a legacy
    ``notices-index.json`` that fails this exact validation still raises
    the identical ``errors.HeraldError`` at migration time (Boundaries &
    Constraints). Returns ``{"notices": {...}, "redirects": {...}}``, or a
    fresh empty shape when the file does not exist."""
    try:
        with index_path.open(encoding="utf-8") as fh:
            document = json.load(fh, object_pairs_hook=_reject_duplicate_keys)
    except FileNotFoundError:
        return {"notices": {}, "redirects": {}}
    except (ValueError, OSError, RecursionError) as exc:
        raise errors.HeraldError(f"notices index {index_path} could not be read: {exc}") from exc
    if (
        not isinstance(document, dict)
        or not isinstance(document.get("notices"), dict)
        or not isinstance(document.get("redirects"), dict)
    ):
        raise errors.HeraldError(
            f"notices index {index_path} is malformed: expected an object with 'notices' and 'redirects' sub-objects"
        )
    return document


def _require_existing_index(index_path: Path, missing: str) -> None:
    """Refuse, with ``missing`` as the message, when no database file
    exists yet -- for the mutating calls that can only ever operate on an
    existing notice (``publish_notice``/``close_notice``/``archive_rename``,
    unlike ``author_notice``, which legitimately creates the index).

    Exists purely to run BEFORE ``db.transaction``: opening the transaction
    creates ``index_path``'s parent directory and the database file itself,
    so without this an operator running one of those commands from the
    wrong directory would litter it with an empty ``.herald/`` tree on a
    pure error path that had no filesystem side effect at all before Story
    13.1. The message is passed in so each caller keeps the exact refusal
    its own in-transaction check would have produced -- this is a
    fail-fast, not a new error contract. The in-transaction checks stay
    where they are: this one is racy by construction (the database can
    appear between here and the transaction), which only ever means
    falling through to those authoritative checks.

    Deliberately NOT ``index_path.exists()``, for the reason ``state.read``
    spells out: ``Path.exists`` returns ``False`` whenever the *stat* fails
    for any reason (an unsearchable parent, a symlink loop, EACCES, EIO),
    so a database that exists but cannot be read would be reported as "no
    notice found" -- pointing the operator at a missing notice instead of
    the permissions fault they actually have. Only a definitively absent
    path (or a non-directory parent component) fails fast here; every
    other stat failure falls through to the transaction so the
    authoritative in-transaction read produces its own, accurate error.

    An absent database with pre-Story-13.3 legacy JSON beside it is NOT
    absent for this purpose: that store's records are real, they are
    simply still in ``.herald/notices-index.json`` waiting for the first
    connection to import them. Refusing here on the bare stat would make
    the very first command an operator runs after upgrading depend on
    which command it was -- ``herald notice publish`` reported "no notice
    found" for a notice plainly in the legacy index, while running any
    read first (which does open a connection, and so does migrate) made
    the identical call succeed. ``db._has_legacy_data`` is the same
    predicate ``db.connection`` uses for exactly this distinction --
    narrowed here to the NOTICES legacy store, the only one that can carry
    a notice. Asking the unnarrowed question let an unrelated legacy
    ``progress.json``/``claims.json`` suppress this fail-fast, which put
    back the very ``.herald/`` tree it exists to avoid creating on a pure
    error path."""
    if db._has_legacy_data(index_path, "notices-index.json"):
        return
    try:
        index_path.stat()
    except FileNotFoundError, NotADirectoryError:
        raise errors.HeraldError(missing) from None
    except OSError:
        return


_REQUIRED_NOTICE_FIELDS = frozenset(
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
    )
)
"""``Notice`` fields with no dataclass default -- ``_entry_to_notice`` must
check these are present before constructing, or a missing one surfaces as
a raw ``TypeError`` (``Notice.__init__() missing N required positional
argument(s)``) instead of the structural ``errors.HeraldError`` every
other corruption check in this function raises (AD-6)."""


def _entry_to_notice(entry: dict[str, object]) -> Notice:
    unknown = sorted(set(entry) - _INDEX_FIELDS)
    if unknown:
        raise errors.HeraldError(
            f"notices index entry for {entry.get('component')!r} carries "
            f"unknown field(s): {', '.join(map(repr, unknown))}"
        )
    missing = sorted(_REQUIRED_NOTICE_FIELDS - set(entry))
    if missing:
        raise errors.HeraldError(
            f"notices index entry for {entry.get('component')!r} is missing field(s): {', '.join(map(repr, missing))}"
        )
    revisions = entry.get("revisions", [])
    if not isinstance(revisions, list):
        raise errors.HeraldError(
            f"notices index entry for {entry.get('component')!r} has a malformed 'revisions' field"
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


def _to_params(notice: Notice) -> tuple[object, ...]:
    """``notice`` as a positional parameter tuple matching the
    ``notices_index`` table's column order -- shared by every INSERT
    (``_upsert_notice_row`` and ``db.py``'s legacy import)."""
    entry = _notice_to_entry(notice)
    return (
        entry["component"],
        entry["type"],
        entry["what"],
        entry["why"],
        entry["migration"],
        entry["deadline"],
        entry["reason_link"],
        entry["status"],
        entry["path"],
        entry["created_at"],
        entry["published_at"],
        entry["closed_at"],
        entry["closed_by"],
        entry["close_reason"],
        json.dumps(entry["revisions"]),
    )


def _row_to_entry(index_path: Path, row) -> dict[str, object]:
    """One ``notices_index`` row as ``_entry_to_notice``'s expected dict
    shape. Every other ``Notice`` field is a plain, typed SQL column
    (schema-enforced); ``revisions`` stays a JSON TEXT column, so a
    malformed value there is the one corruption still reachable once the
    store is a real database, wrapped into ``errors.HeraldError`` the same
    way every other structural check in this module is (AD-6)."""
    try:
        revisions = json.loads(row["revisions"])
    except ValueError as exc:
        raise errors.HeraldError(
            f"notices index record {row['component']!r} in {index_path} has malformed revisions JSON: {exc}"
        ) from exc
    if not isinstance(revisions, list):
        raise errors.HeraldError(
            f"notices index record {row['component']!r} in {index_path} has malformed revisions: expected a JSON array"
        )
    return {
        "type": row["type"],
        "component": row["component"],
        "what": row["what"],
        "why": row["why"],
        "migration": row["migration"],
        "deadline": row["deadline"],
        "reason_link": row["reason_link"],
        "status": row["status"],
        "path": row["path"],
        "created_at": row["created_at"],
        "published_at": row["published_at"],
        "closed_at": row["closed_at"],
        "closed_by": row["closed_by"],
        "close_reason": row["close_reason"],
        "revisions": revisions,
    }


def _row_to_notice(index_path: Path, row) -> Notice:
    return _entry_to_notice(_row_to_entry(index_path, row))


def _get_entry(conn: sqlite3.Connection, index_path: Path, component: str) -> dict[str, object] | None:
    row = conn.execute("SELECT * FROM notices_index WHERE component = ?", (component,)).fetchone()
    return None if row is None else _row_to_entry(index_path, row)


def _get_redirects(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute("SELECT old_component, new_component FROM notices_redirects").fetchall()
    return {row["old_component"]: row["new_component"] for row in rows}


def _upsert_notice_row(conn: sqlite3.Connection, notice: Notice) -> None:
    params = _to_params(notice)
    conn.execute(
        "INSERT INTO notices_index (component, type, what, why, migration, "
        "deadline, reason_link, status, path, created_at, published_at, "
        "closed_at, closed_by, close_reason, revisions) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(component) DO UPDATE SET type=excluded.type, "
        "what=excluded.what, why=excluded.why, migration=excluded.migration, "
        "deadline=excluded.deadline, reason_link=excluded.reason_link, "
        "status=excluded.status, path=excluded.path, "
        "created_at=excluded.created_at, published_at=excluded.published_at, "
        "closed_at=excluded.closed_at, closed_by=excluded.closed_by, "
        "close_reason=excluded.close_reason, revisions=excluded.revisions",
        params,
    )


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


def _notice_path(notices_dir: Path, notice_type: str, component: str, created_at: str) -> Path:
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
        raise errors.HeraldError(f"notice markdown file {full_path} could not be written: {exc}") from exc


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
            raise errors.HeraldError(f"notices index has a redirect cycle involving {current!r}")
        seen.add(target)
        current = target
    raise errors.HeraldError(f"redirect chain for {component!r} exceeds {_MAX_REDIRECT_HOPS} hops")


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
    immediately, same as calling ``publish_notice`` right after.

    The whole read-modify-write body below runs inside ``db.transaction``
    (Story 13.1/13.3) -- see the module docstring's Concurrency section.
    ``notice_type``/``component`` are pure, no-I/O argument checks
    validated BEFORE the transaction opens -- a call that is going to fail
    on basic validation fails fast without first contending on the write
    lock."""
    _validate_type(notice_type)
    _validate_component(component)
    index_path = index_path if index_path is not None else repo_root / DEFAULT_INDEX_PATH
    notices_dir = notices_dir if notices_dir is not None else repo_root / DEFAULT_NOTICES_DIR
    stale_markdown: Path | None = None
    try:
        with db.transaction(index_path) as conn:
            timestamp = now if now is not None else _now_iso()

            redirects = _get_redirects(conn)
            if component in redirects:
                raise errors.HeraldError(
                    f"component {component!r} is a redirect to "
                    f"{redirects[component]!r}; author the notice under that name"
                )

            existing_entry = _get_entry(conn, index_path, component)
            existing = _entry_to_notice(existing_entry) if existing_entry is not None else None
            if existing is not None and existing.status != "draft":
                raise errors.HeraldError(
                    f"notice for {component!r} is already {existing.status}; cannot "
                    f"re-author it (author a new notice under a different "
                    f"component, or use `herald notice close` first)"
                )

            created_at = existing.created_at if existing is not None else timestamp
            relative_path = str(_notice_path(Path("notices"), notice_type, component, created_at))
            revisions = (*(existing.revisions if existing is not None else ()),) + (
                {
                    "edited_at": timestamp,
                    "summary": "re-authored" if existing else "authored",
                },
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
            # Markdown written BEFORE the index (regression fix): a
            # markdown-write failure here leaves the index untouched -- no
            # phantom "live" entry pointing at a file that was never created.
            # This order's own downside is the opposite, milder one: an
            # orphaned markdown file with no index entry, invisible to every
            # read path, since get/list/the web export only ever consult the
            # index.
            #
            # Story 13.3 widened WHEN that orphan can happen, and the trade
            # is still the right way round. `_write_markdown` is a
            # filesystem write inside `db.transaction`, so the index now
            # rolls back on ANY later failure in this block -- the
            # `_upsert_notice_row`, the COMMIT itself -- not only on a
            # markdown-write failure. The orphan is therefore reachable from
            # more paths than before, and it stays the harmless half: a file
            # with no index entry is inert, whereas the phantom index entry
            # the ordering avoids is one the CLI reports as a live notice.
            # The one operation that could turn a rollback into the phantom
            # half -- deleting the OLD file after a path change -- is
            # deliberately deferred past the commit; see below.
            _write_markdown(repo_root, notice)
            _upsert_notice_row(conn, notice)
            if existing is not None and existing.path != relative_path and (repo_root / existing.path).exists():
                # Regression: re-authoring a draft with a changed
                # `notice_type` relocates its markdown path (the type is part
                # of the path), but the OLD file was never removed -- a
                # stale, git-diffable "record" carrying the old content sat
                # alongside the new one indefinitely, indistinguishable from
                # a real current notice to anyone browsing `notices/`
                # directly. Deleted below, AFTER the commit: deleting it
                # here, inside the transaction, meant a later failure in the
                # block (the COMMIT itself, a Ctrl-C) rolled the index back
                # to a path whose file this call had already removed --
                # producing exactly the phantom entry the write ordering
                # above exists to prevent, and destroying the git-tracked
                # durable record in the process. Under the pre-13.3 JSON
                # store the index write was already durable by this point,
                # so there was nothing to roll back to.
                stale_markdown = repo_root / existing.path
    except errors.HeraldError:
        raise
    except (sqlite3.Error, TypeError, ValueError, RecursionError) as exc:
        raise errors.HeraldError(f"notice for {component!r} could not be written: {exc}") from exc
    if stale_markdown is not None:
        try:
            stale_markdown.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise errors.HeraldError(
                f"stale notice markdown file {stale_markdown} could not be "
                f"removed after re-authoring under a new path: {exc}"
            ) from exc
    return notice


def publish_notice(
    repo_root: Path,
    component: str,
    *,
    index_path: Path | None = None,
    now: str | None = None,
) -> Notice:
    """``draft -> published`` (Story 10.6). Refuses a component with no
    notice, an already-published one, or a closed one.

    The whole body below runs inside ``db.transaction`` -- see
    ``author_notice``'s docstring and the module docstring's Concurrency
    section."""
    index_path = index_path if index_path is not None else repo_root / DEFAULT_INDEX_PATH
    _require_existing_index(index_path, f"no notice found for component {component!r}")
    try:
        with db.transaction(index_path) as conn:
            timestamp = now if now is not None else _now_iso()
            redirects = _get_redirects(conn)
            resolved = _resolve_component(redirects, component)
            entry = _get_entry(conn, index_path, resolved)
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
                revisions=notice.revisions + ({"edited_at": timestamp, "summary": "published"},),
            )
            # Markdown before index -- see author_notice's own comment for why.
            _write_markdown(repo_root, notice)
            _upsert_notice_row(conn, notice)
            return notice
    except errors.HeraldError:
        raise
    except (sqlite3.Error, TypeError, ValueError, RecursionError) as exc:
        raise errors.HeraldError(f"notice for {component!r} could not be written: {exc}") from exc


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
    published first) or an already-closed notice.

    The whole body below runs inside ``db.transaction`` -- see
    ``author_notice``'s docstring and the module docstring's Concurrency
    section."""
    index_path = index_path if index_path is not None else repo_root / DEFAULT_INDEX_PATH
    _require_existing_index(index_path, f"no notice found for component {component!r}")
    try:
        with db.transaction(index_path) as conn:
            timestamp = now if now is not None else _now_iso()
            redirects = _get_redirects(conn)
            resolved = _resolve_component(redirects, component)
            entry = _get_entry(conn, index_path, resolved)
            if entry is None:
                raise errors.HeraldError(f"no notice found for component {component!r}")
            notice = _entry_to_notice(entry)
            if notice.status == "draft":
                raise errors.HeraldError(f"notice for {resolved!r} is still a draft; publish it before closing")
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
            # Markdown before index -- see author_notice's own comment for why.
            _write_markdown(repo_root, notice)
            _upsert_notice_row(conn, notice)
            return notice
    except errors.HeraldError:
        raise
    except (sqlite3.Error, TypeError, ValueError, RecursionError) as exc:
        raise errors.HeraldError(f"notice for {component!r} could not be written: {exc}") from exc


def get_notice(repo_root: Path, component: str, *, index_path: Path | None = None) -> Notice:
    """Full detail for ``component``, following a redirect if it was
    renamed (Story 10.3)."""
    index_path = index_path if index_path is not None else repo_root / DEFAULT_INDEX_PATH
    with db.connection(index_path) as conn:
        redirects = _get_redirects(conn)
        resolved = _resolve_component(redirects, component)
        entry = _get_entry(conn, index_path, resolved)
    if entry is None:
        raise errors.HeraldError(f"no notice found for component {component!r}")
    return _entry_to_notice(entry)


def aliases_for(repo_root: Path, component: str, *, index_path: Path | None = None) -> list[str]:
    """``component``'s resolved (current) name plus every old name whose
    redirect chain resolves to it (Story 10.3 renames) -- Story 11.3's
    cross-Moment backlink needs this: a claim's ``Evidence.url`` for a
    ``type="notice"`` entry stores the LITERAL name an operator cited at
    creation time, never re-resolved after a later rename, so searching
    claims by only the current resolved name silently misses any claim
    that cited an old name before the rename happened. Returns the
    resolved name first, then aliases in no particular order."""
    index_path = index_path if index_path is not None else repo_root / DEFAULT_INDEX_PATH
    with db.connection(index_path) as conn:
        redirects = _get_redirects(conn)
    resolved = _resolve_component(redirects, component)
    aliases = [old for old in redirects if _resolve_component(redirects, old) == resolved]
    return [resolved, *aliases]


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
    index_path = index_path if index_path is not None else repo_root / DEFAULT_INDEX_PATH
    with db.connection(index_path) as conn:
        rows = conn.execute("SELECT * FROM notices_index").fetchall()
    notices = [_row_to_notice(index_path, row) for row in rows]

    if status is None:
        notices = [n for n in notices if n.status in ("published", "closed")]
    elif status != "all":
        if status not in NOTICE_STATUSES:
            raise errors.HeraldError(
                f"invalid status {status!r}; expected one of {', '.join(NOTICE_STATUSES)}, or 'all'"
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
    component onto itself or overwriting an existing redirect silently.

    The whole read-modify-write body below runs inside ``db.transaction`` --
    see ``author_notice``'s docstring and the module docstring's
    Concurrency section. The component-name and self-redirect checks just
    below are pure, no-I/O argument validation, so they run BEFORE the
    transaction opens -- a call that is going to fail on basic validation
    fails fast without first contending on the write lock. The "already
    redirects" / "no notice exists yet" checks below depend on the fresh
    on-disk state, so they stay inside the transaction."""
    _validate_component(old_component)
    _validate_component(new_component)
    if old_component == new_component:
        raise errors.HeraldError("cannot redirect a component to itself")
    index_path = index_path if index_path is not None else repo_root / DEFAULT_INDEX_PATH
    _require_existing_index(
        index_path,
        f"cannot redirect to {new_component!r}: no notice exists for it yet",
    )
    try:
        with db.transaction(index_path) as conn:
            if _get_entry(conn, index_path, new_component) is None:
                raise errors.HeraldError(f"cannot redirect to {new_component!r}: no notice exists for it yet")
            redirects = _get_redirects(conn)
            if old_component in redirects:
                raise errors.HeraldError(
                    f"component {old_component!r} already redirects to {redirects[old_component]!r}"
                )
            conn.execute(
                "INSERT INTO notices_redirects (old_component, new_component) VALUES (?, ?)",
                (old_component, new_component),
            )
    except errors.HeraldError:
        raise
    except (sqlite3.Error, TypeError, ValueError, RecursionError) as exc:
        raise errors.HeraldError(
            f"redirect {old_component!r} -> {new_component!r} could not be written: {exc}"
        ) from exc
