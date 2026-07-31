"""Per-deck bridge state persistence (Story 1.4, AD-5).

``.herald/bridge-state.json`` is the operational source of truth CAP-3
(status) and CAP-4 (watch) read from, keyed by deck slug. Each slug's entry
holds the ``DeckState`` this module round-trips: the linked Design project
id, one last-seen etag per tracked artifact, and the last-pull timestamp.
The deck README's own section *Design project* (``registry.py``, AD-8,
Story 1.5) stays the human-readable registry -- read only as a bootstrap
fallback when no state file exists for a slug; that fallback lands with
``registry.py``, not this module.

``state_path`` is always an explicit ``Path`` argument -- this module never
assumes a cwd (mirrors ``deck_pipeline.py``'s future explicit-``cwd``
convention, AD-7). Resolving ``DEFAULT_STATE_PATH`` against a real repo root
is the caller's job (Story 1.6+), not this module's.

A corrupt or hand-edited state file is a realistic first failure mode for
exactly this file, and AD-6 requires every bridge command to fail
structurally, never silently -- so malformed or binary-corrupt JSON, an
unreadable file, a non-object document, or a slug entry missing or
mis-typing a required field all raise ``errors.HeraldError`` rather than
leaking a bare ``json.JSONDecodeError``/``UnicodeDecodeError``/``OSError``/
``KeyError``. ``write`` holds its inputs to the same discipline: a
non-string slug or a ``DeckState`` whose fields lie about their declared
types is refused up front, never persisted for ``read`` to reject as
corruption one process later.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from . import errors

DEFAULT_STATE_PATH = Path(".herald/bridge-state.json")
"""AD-5's default location, relative to a repo root the caller resolves."""


@dataclass(frozen=True)
class DeckState:
    """One slug's bridge state: the linked Design project, its tracked
    artifacts' last-seen etags, and the last-pull timestamp.

    ``etags`` keys are artifact identifiers (the prototype, each Marp
    source, the standalone bundle, each derived export file -- AD-5); this
    story stores and round-trips the map without interpreting its keys.
    ``last_pull`` is ``None`` until the first successful pull."""

    project_id: str
    etags: dict[str, str]
    last_pull: str | None = None


_MISSING = object()
"""Sentinel distinguishing an absent slug entry from an explicit JSON
``null`` one -- a plain ``.get(slug)`` reads a hand-edited ``"slug": null``
as silently absent, when it is a malformed entry that must fail
structurally (AD-6)."""


def _fields_problem(project_id: object, etags: object, last_pull: object) -> str | None:
    """Which declared-type constraint the three ``DeckState`` fields break,
    or ``None`` when all hold -- shared by ``read`` (parsed JSON) and
    ``write`` (a caller's ``DeckState``), so both sides of the round-trip
    enforce one shape and a type-lying value is refused where it appears,
    not discovered as "corruption" one process later. String *keys* only
    matter on the write side (JSON object keys are strings by construction,
    but ``json.dump`` silently launders an ``int`` key into one)."""
    if not isinstance(project_id, str):
        return "field 'project_id' must be a string"
    if not isinstance(etags, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in etags.items()
    ):
        return "field 'etags' must be an object with string keys and string values"
    if last_pull is not None and not isinstance(last_pull, str):
        return "field 'last_pull' must be a string or null"
    return None


def _load_document(state_path: Path) -> dict[str, object]:
    """The whole state file as a slug-keyed dict, or ``{}`` when the file
    does not exist yet -- both a missing file and a missing slug are "no
    state yet", never an error (the I/O matrix's read rows).

    Anything else that stops the read is a structural failure (AD-6):
    raises ``errors.HeraldError`` naming ``state_path`` rather than leaking
    ``json.JSONDecodeError``, ``UnicodeDecodeError`` (binary corruption),
    ``RecursionError`` (absurdly nested JSON), an ``OSError`` (unreadable
    file, ``state_path`` being a directory, a parent component that is a
    plain file), or an ``AttributeError`` from treating a non-dict as one.
    There is deliberately no ``exists()`` pre-check: ``Path.exists``
    returns ``False`` whenever the *stat* fails (an unsearchable parent, a
    symlink loop), which would silently misread genuinely unreadable state
    as empty -- ``open()`` is the sole authority, and only its
    ``FileNotFoundError`` means "no state yet"."""
    try:
        with state_path.open(encoding="utf-8") as fh:
            document = json.load(fh)
    except FileNotFoundError:
        return {}
    except (ValueError, OSError, RecursionError) as exc:
        # ValueError covers json.JSONDecodeError and UnicodeDecodeError --
        # the latter is JSONDecodeError's *sibling* under ValueError, not a
        # subclass, so naming only JSONDecodeError would leak it raw.
        # FileNotFoundError is an OSError subclass, so its "no state yet"
        # branch above must stay first.
        raise errors.HeraldError(
            f"bridge state file {state_path} could not be read: {exc}"
        ) from exc
    if not isinstance(document, dict):
        raise errors.HeraldError(
            f"bridge state file {state_path} does not hold a JSON object "
            f"at its top level"
        )
    return document


def read(state_path: Path, slug: str) -> DeckState | None:
    """``slug``'s stored state, or ``None`` when the file or the slug's
    entry is absent.

    A present entry that is not a JSON object (including an explicit
    ``null`` -- absent and null are different hand-edits), missing
    ``project_id``/``etags``, or carrying the wrong type for any field --
    including a non-string ``etags`` value or a non-string ``last_pull`` --
    is a structural failure (AD-6): raises ``errors.HeraldError`` naming
    the slug and the offending field rather than leaking a bare
    ``KeyError``/``TypeError``, or handing a later story a ``DeckState``
    whose fields lie about their declared types."""
    entry = _load_document(state_path).get(slug, _MISSING)
    if entry is _MISSING:
        return None
    malformed = (
        f"bridge state file {state_path} has a malformed entry for slug {slug!r}"
    )
    if not isinstance(entry, dict):
        raise errors.HeraldError(f"{malformed}: entry is not a JSON object")
    project_id = entry.get("project_id")
    etags = entry.get("etags")
    last_pull = entry.get("last_pull")
    problem = _fields_problem(project_id, etags, last_pull)
    if problem:
        raise errors.HeraldError(f"{malformed}: {problem}")
    return DeckState(project_id=project_id, etags=dict(etags), last_pull=last_pull)


def write(state_path: Path, slug: str, state: DeckState) -> None:
    """Store ``state`` under ``slug``, preserving every other slug already
    in the file. Creates ``state_path``'s parent directory if needed, and
    writes atomically (temp file in the same directory, then
    ``os.replace``) so a *process* crash mid-write can never leave a
    half-written state file behind -- mirrors
    ``pyforge.warden.feeds.write_kev_cache``, including its limit: neither
    fsyncs, so surviving power loss is the filesystem's business, not a
    guarantee this module makes.

    Refuses up front -- as ``errors.HeraldError`` naming the slug -- a
    non-string ``slug`` or a ``DeckState`` whose fields do not match their
    declared types: ``json.dump`` would otherwise either crash raw or
    silently launder the value (an ``int`` key becomes its string), handing
    ``read`` a "corruption" Herald itself manufactured. Also raises
    ``errors.HeraldError`` when the existing file is corrupt or unreadable
    (the same load ``read`` uses -- a corrupt file blocks writes
    deliberately, since clobbering it would destroy every other slug's
    entry; the operator's recovery is deleting the file) and when the
    filesystem refuses the write (a plain file where a directory is
    needed, a read-only tree, ``state_path`` itself being a directory)."""
    could_not_write = (
        f"bridge state for slug {slug!r} could not be written to {state_path}"
    )
    if not isinstance(slug, str):
        raise errors.HeraldError(
            f"{could_not_write}: slug must be a string, not {type(slug).__name__}"
        )
    problem = _fields_problem(state.project_id, state.etags, state.last_pull)
    if problem:
        raise errors.HeraldError(f"{could_not_write}: {problem}")
    document = _load_document(state_path)
    document[slug] = asdict(state)
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        handle, tmp_name = tempfile.mkstemp(
            dir=state_path.parent, prefix=f".{state_path.name}-", suffix=".tmp"
        )
    except OSError as exc:
        raise errors.HeraldError(f"{could_not_write}: {exc}") from exc
    try:
        try:
            fh = os.fdopen(handle, "w", encoding="utf-8")
        except BaseException:
            # os.fdopen raised before taking ownership of the raw fd, so
            # this is the only branch that may close it. Once fdopen
            # returns, the file object owns the fd and the `with` below
            # closes it -- closing here as well would hit whatever a
            # concurrent thread had opened onto the recycled fd number.
            os.close(handle)
            raise
        with fh:
            json.dump(document, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp_name, state_path)
    except BaseException as exc:
        # Unlink the temp file so a failed write never leaks it.
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        if isinstance(exc, (OSError, TypeError, ValueError)):
            # The up-front validation makes a json.dump TypeError /
            # ValueError unreachable for this slug's own entry, and every
            # other entry came from JSON (serializable by construction) --
            # wrapped anyway: a raw leak through the AD-6 contract is worse
            # than a redundant guard.
            raise errors.HeraldError(f"{could_not_write}: {exc}") from exc
        raise
