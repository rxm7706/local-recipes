"""CAP-1 ``seed`` -- Story 1.6, the first bridge-core operation `cli.py`
composes with ``bridge.run`` (``bridge.py``'s own docstring names this
module and names ``seed`` as its first tenant).

Implements ``bridge-protocol.md`` § *Seed (repo -> Design)* exactly: prove
locally, fetch the mandatory design-system prompt, create the project,
declare the write plan, write the runtime + prototype, record the result.
Bridge-core stays transport-agnostic (AD-3) -- every network step below goes
through the ``transport: DesignTransport`` parameter ``bridge.run`` supplies,
never a concrete adapter, and the ``transport.base`` import below is
``TYPE_CHECKING``-only for the identical reason ``bridge.py``'s is.

**Two structural judgment calls this story makes, both recorded here and in
the story spec's Design Notes:**

1. **Conflict detection is pre-flight (state + registry), not
   write-response-based.** ``bridge-protocol.md``'s CAP-1 success criterion
   says re-seeding over existing Design-side edits "is refused with a
   structured conflict and writes nothing". Story 1.2's own deferred-work
   ledger (DW-1-2-5) records that a conflicted ``write_files``/``copy_files``
   answers as an *ordinary success* ``Mapping`` with an unpinned
   structured-conflict shape -- nothing in this repo has observed that wire
   shape yet. This story therefore gates on two cheaper, well-evidenced
   signals instead, both checked *before any transport call at all* (so
   "writes nothing" holds by construction): first ``state.read`` (the
   *operational* source of truth CAP-3/CAP-4 read from); if that finds
   nothing, ``registry.read`` against the deck's own README -- exactly the
   "bootstrap fallback" ``registry.py``'s own module doc names Story 1.6 as
   the wirer of. The fallback matters concretely: the four pilot decks
   (``bridge-protocol.md`` § Pilot evidence) were seeded by hand before
   ``state.py`` existed, so they carry no state entry, only a README
   section -- without the fallback, seeding them again through this CLI
   would silently create a *second* Design project for an already-linked
   deck. A README section present but malformed (DW-1-5-1: all 13 existing
   sections predate the canonical two-line shape) still refuses the seed --
   a corrupt-but-present link is still a link, not "nothing registered yet".
   Detecting a genuine write-level conflict from an unpinned wire shape
   remains out of this story's scope (deferred, ``deferred-work-ledger.md``).
2. **``deck-stage.js`` is copied from a fixed pilot project.** CAP-1 step 6
   is a server-side ``copy_files`` "from an existing deck project" -- the
   bootstrap dependency every *first* seed has. ``PILOT_SUPPORT_SOURCE_PROJECT_ID``
   pins the already-seeded ``pyforge-marshal`` pilot project
   (``bridge-protocol.md`` § Pilot evidence), overridable per call.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from . import errors, registry, state

if TYPE_CHECKING:
    from .transport.base import DesignTransport, FileRead, ListedFile, ProjectRef

PILOT_SUPPORT_SOURCE_PROJECT_ID = "ad84d4f6-c292-42c8-98bf-ede78a567773"
"""The already-seeded ``pyforge-marshal`` Design project (``bridge-protocol.md``
§ Pilot evidence) -- the default source ``deck-stage.js`` is copied from for
a deck's first seed. Overridable via ``seed(..., support_source_project_id=...)``."""

SUPPORT_JS_PATH = "support.js"
DECK_STAGE_JS_PATH = "deck-stage.js"
_FRESH_ETAG = "0"
"""FR-24's marker asserting a write path does not yet exist -- the whole
point of a fresh-project seed."""


def _persona_from_slug(slug: str) -> str:
    """``pyforge-<name>`` -> Title-cased ``<name>`` (``bridge-protocol.md``
    § Conventions: ``PyForge <Persona> deck`` / ``PyForge <Persona>.dc.html``).
    A slug with no ``pyforge-`` prefix is title-cased whole -- a defensible,
    narrow fallback for a slug this convention was not written for, rather
    than refusing outright."""
    name = slug.removeprefix("pyforge-")
    return name.replace("-", " ").replace("_", " ").title()


@dataclass(frozen=True)
class SeedResult:
    """What ``seed`` returns: the new project's reference plus the exact
    persona-derived names it used, so ``cli.py`` can report them without
    re-deriving the naming convention."""

    project: ProjectRef
    persona: str
    prototype_filename: str


@runtime_checkable
class LocalProver(Protocol):
    """The injectable local-prove seam (CAP-1 step 1: "prove locally before
    any Design write"). Real implementation shells ``npm run extract`` then
    ``npm run build``; every test injects a hand-written fake -- mirrors
    Story 1.3's process-launch seam, for the same reason: a subprocess this
    module does not own must never be a hidden dependency of a unit test."""

    def prove(self, deck_dir: Path) -> None:
        """Raise ``errors.HeraldError`` naming what failed; return normally
        on success. Must not write anything to Design -- purely local."""
        ...


class NpmLocalProver:
    """The real ``LocalProver``: ``npm run extract`` then ``npm run build``
    in ``deck_dir``, each via one bounded subprocess call. Never invoked by
    this package's own tests (every ``deck_pipeline`` test injects a fake)."""

    def __init__(self, *, timeout: float = 300.0) -> None:
        self._timeout = timeout

    def prove(self, deck_dir: Path) -> None:
        for step in ("extract", "build"):
            self._run(deck_dir, step)

    def _run(self, deck_dir: Path, npm_script: str) -> None:
        try:
            completed = subprocess.run(
                ["npm", "run", npm_script],
                cwd=deck_dir,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise errors.HeraldError(
                f"prove-before-cross failed: 'npm run {npm_script}' in "
                f"{deck_dir} exceeded {self._timeout}s ({exc})"
            ) from exc
        except OSError as exc:
            raise errors.HeraldError(
                f"prove-before-cross failed: could not run 'npm run "
                f"{npm_script}' in {deck_dir} ({exc})"
            ) from exc
        if completed.returncode != 0:
            tail = (completed.stderr or completed.stdout or "").strip()[-2000:]
            raise errors.HeraldError(
                f"prove-before-cross failed: 'npm run {npm_script}' in "
                f"{deck_dir} exited {completed.returncode}: {tail}"
            )


def seed(
    transport: DesignTransport,
    *,
    slug: str,
    repo_root: Path,
    support_source_project_id: str = PILOT_SUPPORT_SOURCE_PROJECT_ID,
    state_path: Path | None = None,
    prover: LocalProver | None = None,
) -> SeedResult:
    """CAP-1: seed ``slug`` into Claude Design (``bridge-protocol.md`` §
    Seed, steps 1-8).

    Refuses before any transport call when ``slug`` already has a recorded
    ``state.DeckState``, or -- the bootstrap fallback -- when the deck
    README's own § *Design project* section already names a project
    (``SeedConflictError`` either way; see the module doc's judgment call
    1). A present-but-malformed README section also refuses, naming the
    parse failure, rather than treating "cannot tell" as "nothing seeded
    yet". Otherwise: proves the local prototype (``prover``,
    default ``NpmLocalProver``), fetches the mandatory design-system prompt
    (refusing on an empty answer -- the platform's own pre-write gate did
    not hold), creates the project, declares the three-path write plan,
    writes the runtime + a server-side copy of ``deck-stage.js`` + the
    prototype bytes, then records the result in both ``state.py`` (the
    operational source of truth) and the README's § *Design project*
    section (``registry.py``, human-readable). Returns the new
    ``SeedResult`` on success; raises ``errors.HeraldError`` (or a
    ``TransportError``/``SeedConflictError`` subclass) naming exactly what
    failed on any other path."""
    # Lazy, not module-level: `transport.base` is itself a submodule of the
    # `transport` package, so resolving it runs `transport/__init__.py`,
    # which eagerly imports every concrete adapter. A module-level import
    # here would mean `import pyforge.herald.deck_pipeline` alone loads
    # McpTransport/AgentSdkTransport into sys.modules -- exactly what
    # bridge.py's own TYPE_CHECKING-only import exists to avoid (see its
    # `test_importing_bridge_does_not_load_the_transport_package`). `seed`
    # already requires a real `transport` argument to be called at all, so
    # deferring the import to call time costs nothing and keeps merely
    # *importing* this module free of that side effect.
    from .transport.base import MODERNIST_DESIGN_SYSTEM_ID

    deck_dir = repo_root / "presentations" / slug
    if not deck_dir.is_dir():
        raise errors.HeraldError(
            f"cannot seed {slug!r}: no deck directory at {deck_dir}"
        )
    readme_path = deck_dir / "README.md"
    resolved_state_path = (
        repo_root / state.DEFAULT_STATE_PATH if state_path is None else state_path
    )
    existing_state = state.read(resolved_state_path, slug)
    if existing_state is not None:
        raise errors.SeedConflictError(
            f"{slug!r} is already seeded (linked Design project "
            f"{existing_state.project_id!r} per {resolved_state_path}); "
            f"seed refuses to run again over an existing link -- use pull "
            f"to sync further edits"
        )
    # Bootstrap fallback (registry.py's own module doc names this story as
    # the wirer): a deck seeded by hand before state.py existed carries no
    # state entry, only a README section. Without this check, re-seeding it
    # here would silently create a second Design project.
    try:
        existing_registry = registry.read(readme_path)
    except errors.HeraldError as exc:
        raise errors.SeedConflictError(
            f"{slug!r} appears to already be linked in {readme_path}, but "
            f"its § Design project section is malformed and could not "
            f"be parsed ({exc}); seed refuses to overwrite an existing, "
            f"unparseable link -- resolve the README section by hand"
        ) from exc
    if existing_registry is not None:
        raise errors.SeedConflictError(
            f"{slug!r} is already seeded (linked Design project "
            f"{existing_registry.project_id!r} per {readme_path}); seed "
            f"refuses to run again over an existing link -- use pull to "
            f"sync further edits"
        )

    # Review finding: `registry.register` (called at the end of a
    # successful run) refuses outright against a missing `readme_path` --
    # "this module never fabricates a whole README from nothing" -- but
    # nothing checked for that UNTIL after the remote project was already
    # created and `state.write` had already recorded it. The result: the
    # CLI reported a hard failure, yet a real project existed and state.py
    # called the slug seeded, with no way to complete registration short of
    # a manual `registry.register` call or hand-authoring the README. Moved
    # here, before ANY transport call, so a missing README refuses cleanly
    # up front -- consistent with this function's own "writes nothing
    # before every precondition it can check without I/O is satisfied"
    # design.
    if not readme_path.is_file():
        raise errors.HeraldError(
            f"cannot seed {slug!r}: no README.md at {readme_path} -- "
            f"registry.register requires an existing README to add its "
            f"§ Design project section to; create one before seeding"
        )

    persona = _persona_from_slug(slug)
    prototype_filename = f"PyForge {persona}.dc.html"
    prototype_path = deck_dir / "project" / prototype_filename
    if not prototype_path.is_file():
        raise errors.HeraldError(
            f"cannot seed {slug!r}: no local prototype at {prototype_path} "
            f"to prove and seed"
        )

    (prover or NpmLocalProver()).prove(deck_dir)

    try:
        prototype_text = prototype_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise errors.HeraldError(
            f"cannot seed {slug!r}: could not read {prototype_path} ({exc})"
        ) from exc

    prompt = transport.get_design_prompt(design_system_id=MODERNIST_DESIGN_SYSTEM_ID)
    if not prompt:
        raise errors.HeraldError(
            f"cannot seed {slug!r}: get_design_prompt returned an empty "
            f"design-system prompt; the mandatory pre-write gate did not hold"
        )

    project = transport.create_project(
        name=f"PyForge {persona} deck", design_system_id=MODERNIST_DESIGN_SYSTEM_ID
    )
    # Review finding: recording the new project used to happen only AFTER
    # every subsequent transport call succeeded. A failure anywhere in
    # finalize_plan/create_support_js/copy_files/write_files (an etag
    # conflict, a network error, a malformed plan response -- all real
    # TransportCallError/TransportUnreachableError paths) left the
    # already-created remote project untracked by state.py's own conflict
    # gate, so a retry's `existing_state is not None` check passed cleanly
    # and `create_project` ran AGAIN -- a second, orphaned duplicate
    # project for the same slug. `state.write` is moved here, immediately
    # after the one truly stateful call this pipeline makes, so ANY later
    # failure still leaves the record `seed()`'s own FIRST conflict check
    # reads -- a retry now refuses loudly (naming the already-created
    # project) instead of silently duplicating it.
    state.write(
        resolved_state_path,
        slug,
        state.DeckState(project_id=project.project_id, etags={}, last_pull=None),
    )
    plan = transport.finalize_plan(
        project_id=project.project_id,
        writes=[SUPPORT_JS_PATH, DECK_STAGE_JS_PATH, prototype_filename],
    )
    transport.create_support_js(
        project_id=project.project_id,
        if_match=plan.base_etags.get(SUPPORT_JS_PATH, _FRESH_ETAG),
        path=SUPPORT_JS_PATH,
        plan_token=plan.plan_token,
    )
    transport.copy_files(
        project_id=project.project_id,
        files=[
            {
                "src_project_id": support_source_project_id,
                "src_path": DECK_STAGE_JS_PATH,
                "dest": DECK_STAGE_JS_PATH,
                "if_match": plan.base_etags.get(DECK_STAGE_JS_PATH, _FRESH_ETAG),
            }
        ],
        plan_token=plan.plan_token,
    )
    transport.write_files(
        project_id=project.project_id,
        files=[
            {
                "path": prototype_filename,
                "data": prototype_text,
                "if_match": plan.base_etags.get(prototype_filename, _FRESH_ETAG),
            }
        ],
        plan_token=plan.plan_token,
    )

    registry.register(
        readme_path=readme_path,
        project_name=f"PyForge {persona} deck",
        project_id=project.project_id,
        file_url=project.url,
    )
    return SeedResult(
        project=project, persona=persona, prototype_filename=prototype_filename
    )


# --- CAP-2: pull (Design -> repo), Story 2.1 --------------------------------
#
# `bridge-protocol.md` § *Pull*: `read_file(path, if_none_match: <last-seen
# etag>)` -> `{unchanged: true}` short-circuits (no body transferred, nothing
# written) -> otherwise write the (already entity-decoded -- see
# `_pull_and_land`'s own docstring) body, record the new etag, re-derive
# (`npm run extract` -> `npm run build` -> `deck-export`). `--commit` lands in
# Story 2.2; Marp-source and standalone-bundle pull land in Stories 2.3/2.4.

PROTOTYPE_ARTIFACT_KEY = "prototype"
"""The ``state.DeckState.etags`` key for the main ``.dc.html`` prototype."""

_DEFAULT_EXPORT_TIMEOUT = 300.0


@dataclass(frozen=True)
class PullResult:
    """What a ``pull_*`` function returns: which artifact, whether the pull
    was a no-op (etag short-circuit), where it landed locally when it
    wasn't, the etag now on record, and whether ``--commit`` (Story 2.2)
    actually committed it."""

    slug: str
    artifact: str
    local_path: Path | None
    unchanged: bool
    etag: str | None
    committed: bool = False


def _require_seeded_state(
    state_path: Path, slug: str, *, verb: str = "pull"
) -> state.DeckState:
    """The deck's recorded ``state.DeckState``, or a ``HeraldError`` naming
    ``herald deck seed`` -- pulling (and, since Story 5.1, pushing) needs a
    ``project_id`` to read from, and ``state.py`` is the only source of one
    this module has (unlike ``seed``'s registry-bootstrap fallback, there is
    no analogous "adopt an already-linked deck" path here yet; see the
    story spec's Design Notes). ``verb`` names the calling operation in the
    error message -- ``push_exports`` passes ``"push"`` so the message
    matches the command the operator actually ran."""
    existing = state.read(state_path, slug)
    if existing is None:
        raise errors.HeraldError(
            f"cannot {verb} {slug!r}: no bridge state recorded at {state_path} "
            f"-- run 'herald deck seed {slug}' first"
        )
    return existing


def _atomic_write_text(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` atomically (temp file in ``path``'s own
    directory, then ``os.replace``), mirroring ``state.write`` /
    ``registry.register``'s existing crash-safety convention: a process
    crash mid-write must never leave a corrupt half-written pulled file."""
    could_not = f"could not write {path}"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, tmp_name = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.name}-", suffix=".tmp"
        )
    except OSError as exc:
        raise errors.HeraldError(f"{could_not}: {exc}") from exc
    try:
        try:
            fh = os.fdopen(handle, "w", encoding="utf-8")
        except BaseException:
            os.close(handle)
            raise
        with fh:
            fh.write(text)
        os.replace(tmp_name, path)
    except BaseException as exc:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        if isinstance(exc, (OSError, ValueError)):
            raise errors.HeraldError(f"{could_not}: {exc}") from exc
        raise


def _pull_and_land(
    transport: DesignTransport,
    *,
    slug: str,
    existing: state.DeckState,
    remote_path: str,
    local_path: Path,
    artifact_key: str,
) -> FileRead | None:
    """One ``read_file`` + etag short-circuit + (on change) atomic write.
    Returns ``None`` on an ``{unchanged: true}`` answer -- the caller must
    treat that as "stop here", never running prove/export for a no-op pull.

    Deliberately does NOT touch ``state.py`` (review finding): the caller
    must record the new etag only AFTER prove/export/re-derivation
    genuinely succeeds, via ``_record_pull_etag`` below. Recording it here,
    before that work runs, would make a failed re-derivation permanently
    unrecoverable via retry -- a rerun's ``if_none_match`` would already
    match the just-recorded etag, the server would answer
    ``{unchanged: true}``, and the pull would short-circuit forever,
    silently reporting "unchanged" for a re-derivation that never actually
    completed.

    ``FileRead.body`` is used **verbatim, with no further entity-decoding**:
    ``McpTransport.read_file`` / ``AgentSdkTransport.read_file`` already
    return ``transport.base.parse_read_response(...)``, which decodes the
    wire's ``&amp;``/``&lt;``/``&gt;`` escaping internally. Re-decoding here
    would silently corrupt any pulled file that legitimately contains one of
    those substrings."""
    last_etag = existing.etags.get(artifact_key)
    file_read = transport.read_file(
        project_id=existing.project_id, path=remote_path, if_none_match=last_etag
    )
    if file_read.unchanged:
        return None
    if file_read.truncated:
        raise errors.HeraldError(
            f"cannot pull {slug!r} artifact {artifact_key!r}: read_file "
            f"returned a truncated window for {remote_path!r}; a partial "
            f"read must never be mistaken for the whole file"
        )
    if file_read.body is None:
        raise errors.HeraldError(
            f"cannot pull {slug!r} artifact {artifact_key!r}: read_file "
            f"reported a change for {remote_path!r} but returned no body"
        )
    _atomic_write_text(local_path, file_read.body)
    return file_read


def _record_pull_etag(
    state_path: Path,
    slug: str,
    existing: state.DeckState,
    *,
    artifact_key: str,
    etag: str,
    now: Callable[[], datetime],
) -> None:
    """Record ``artifact_key``'s new etag -- called ONLY after prove/export
    for this pull has genuinely succeeded (review finding: see
    ``_pull_and_land``'s own docstring for why recording it any earlier
    makes a failed re-derivation unrecoverable via retry). Must run before
    ``--commit`` stages this state file, so its own new etag is included in
    the commit."""
    new_etags = dict(existing.etags)
    new_etags[artifact_key] = etag
    state.write(
        state_path,
        slug,
        state.DeckState(
            project_id=existing.project_id,
            etags=new_etags,
            last_pull=now().isoformat(),
        ),
    )


@runtime_checkable
class DeckExporter(Protocol):
    """The injectable ``deck-export`` seam (re-derive step 4:
    ``pixi run -e local-recipes deck-export <slug>``), mirroring
    ``LocalProver``'s pattern: a real implementation shells a bounded
    subprocess; every test injects a hand-written fake."""

    def export(self, *, slug: str, repo_root: Path) -> None:
        """Raise ``errors.HeraldError`` naming what failed; return normally
        on success."""
        ...


class PixiDeckExporter:
    """The real ``DeckExporter``: ``pixi run -e local-recipes deck-export
    <slug>`` in ``repo_root``, one bounded subprocess call. Never invoked by
    this package's own tests (every pull test injects a fake)."""

    def __init__(self, *, timeout: float = _DEFAULT_EXPORT_TIMEOUT) -> None:
        self._timeout = timeout

    def export(self, *, slug: str, repo_root: Path) -> None:
        try:
            completed = subprocess.run(
                ["pixi", "run", "-e", "local-recipes", "deck-export", slug],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise errors.HeraldError(
                f"deck-export failed: 'pixi run -e local-recipes deck-export "
                f"{slug}' in {repo_root} exceeded {self._timeout}s ({exc})"
            ) from exc
        except OSError as exc:
            raise errors.HeraldError(
                f"deck-export failed: could not run 'pixi run -e "
                f"local-recipes deck-export {slug}' in {repo_root} ({exc})"
            ) from exc
        if completed.returncode != 0:
            tail = (completed.stderr or completed.stdout or "").strip()[-2000:]
            raise errors.HeraldError(
                f"deck-export failed: 'pixi run -e local-recipes deck-export "
                f"{slug}' in {repo_root} exited {completed.returncode}: {tail}"
            )


def _default_now() -> datetime:
    return datetime.now(timezone.utc)


# --- CAP-2: --commit, Story 2.2 ----------------------------------------------
#
# `bridge-protocol.md` § *Pull* step 5: "Commit is the operator's (or
# `--commit`'s) move -- never implicit." Herald has no pre-existing
# git-wrapping convention of its own (Epic 1 never touched git); this seam's
# shape (`git add -- <paths>` then `git commit -m <message> -- <paths>`)
# mirrors `pyforge-marshal`'s own `GitVcs.commit_paths` -- the one real,
# persistent git-commit convention already established anywhere in this
# monorepo -- rather than inventing a new one.

_DEFAULT_GIT_TIMEOUT = 60.0


@runtime_checkable
class GitCommitter(Protocol):
    """The injectable git-commit seam, mirroring ``LocalProver`` /
    ``DeckExporter``'s pattern: a real implementation shells two bounded
    subprocess calls; every test injects a hand-written fake."""

    def commit(self, *, repo_root: Path, paths: list[Path], message: str) -> None:
        """Raise ``errors.HeraldError`` naming what failed; return normally
        on success (including when there was nothing new to stage under
        ``paths`` -- callers only invoke this when a real change is known to
        exist)."""
        ...


class SubprocessGitCommitter:
    """The real ``GitCommitter``: ``git add -- <paths>`` then ``git commit
    -m <message> -- <paths>`` in ``repo_root``, using the operator's own git
    identity/signing config -- this commit is meant to survive, unlike
    ``pyforge-marshal``'s throwaway ``commit-tree`` comparisons. Never
    invoked by this package's own tests (every pull test injects a fake)."""

    def __init__(self, *, timeout: float = _DEFAULT_GIT_TIMEOUT) -> None:
        self._timeout = timeout

    def commit(self, *, repo_root: Path, paths: list[Path], message: str) -> None:
        # Review finding: `p.is_absolute()` was the wrong branch condition
        # -- every `paths` entry this module's own callers pass IS already
        # prefixed with `repo_root` (e.g. `repo_root / "presentations" /
        # slug`), whether or not `repo_root` itself happens to be absolute.
        # The subprocess runs with `cwd=repo_root`, so a RELATIVE `p` must
        # still be stripped of that same `repo_root` prefix -- resolving
        # both sides first makes this correct regardless of whether
        # `repo_root` (and therefore `p`) was absolute or relative to begin
        # with, instead of silently doubling the prefix for a relative
        # `repo_root` (e.g. `--repo-root some/subdir`).
        resolved_root = repo_root.resolve()
        rel_paths = [str(p.resolve().relative_to(resolved_root)) for p in paths]
        self._run(repo_root, ["git", "add", "--", *rel_paths])
        self._run(repo_root, ["git", "commit", "-m", message, "--", *rel_paths])

    def _run(self, repo_root: Path, args: list[str]) -> None:
        try:
            completed = subprocess.run(
                args,
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise errors.HeraldError(
                f"git commit failed: {' '.join(args)!r} in {repo_root} "
                f"exceeded {self._timeout}s ({exc})"
            ) from exc
        except OSError as exc:
            raise errors.HeraldError(
                f"git commit failed: could not run {' '.join(args)!r} in "
                f"{repo_root} ({exc})"
            ) from exc
        if completed.returncode != 0:
            tail = (completed.stderr or completed.stdout or "").strip()[-2000:]
            raise errors.HeraldError(
                f"git commit failed: {' '.join(args)!r} in {repo_root} exited "
                f"{completed.returncode}: {tail}"
            )


def pull_prototype(
    transport: DesignTransport,
    *,
    slug: str,
    repo_root: Path,
    commit: bool = False,
    state_path: Path | None = None,
    prover: LocalProver | None = None,
    exporter: DeckExporter | None = None,
    committer: GitCommitter | None = None,
    now: Callable[[], datetime] | None = None,
) -> PullResult:
    """CAP-2, Story 2.1: pull the main prototype (``bridge-protocol.md`` §
    Pull, steps 1-4). Requires a prior ``seed`` (``_require_seeded_state``).

    On ``{unchanged: true}``: returns immediately with
    ``PullResult(unchanged=True)`` -- no write, no state update, no
    extract/build/export, and (Story 2.2) never a commit even when
    ``commit=True``. On a real change: writes the decoded body to
    ``presentations/<slug>/project/PyForge <Persona>.dc.html``, records the
    new etag, then re-derives via ``prover`` (default ``NpmLocalProver``,
    reused from Story 1.6) and ``exporter`` (default ``PixiDeckExporter``).
    When ``commit=True`` and the pull was a real change, stages and commits
    the whole ``presentations/<slug>/`` directory plus the bridge-state file
    via ``committer`` (default ``SubprocessGitCommitter``, Story 2.2) --
    commit is opt-in, never implicit."""
    resolved_now = now or _default_now
    resolved_state_path = (
        repo_root / state.DEFAULT_STATE_PATH if state_path is None else state_path
    )
    existing = _require_seeded_state(resolved_state_path, slug)
    persona = _persona_from_slug(slug)
    prototype_filename = f"PyForge {persona}.dc.html"
    deck_dir = repo_root / "presentations" / slug
    local_path = deck_dir / "project" / prototype_filename

    file_read = _pull_and_land(
        transport,
        slug=slug,
        existing=existing,
        remote_path=prototype_filename,
        local_path=local_path,
        artifact_key=PROTOTYPE_ARTIFACT_KEY,
    )
    if file_read is None:
        return PullResult(
            slug=slug,
            artifact=PROTOTYPE_ARTIFACT_KEY,
            local_path=None,
            unchanged=True,
            etag=existing.etags.get(PROTOTYPE_ARTIFACT_KEY),
            committed=False,
        )

    (prover or NpmLocalProver()).prove(deck_dir)
    (exporter or PixiDeckExporter()).export(slug=slug, repo_root=repo_root)
    # Review finding: the etag is now recorded only after prove+export both
    # succeed -- see `_pull_and_land`'s docstring for why recording it any
    # earlier makes a failed re-derivation unrecoverable via retry.
    _record_pull_etag(
        resolved_state_path,
        slug,
        existing,
        artifact_key=PROTOTYPE_ARTIFACT_KEY,
        etag=file_read.etag,
        now=resolved_now,
    )

    committed = False
    if commit:
        (committer or SubprocessGitCommitter()).commit(
            repo_root=repo_root,
            paths=[deck_dir, resolved_state_path],
            message=f"herald: pull {slug} ({PROTOTYPE_ARTIFACT_KEY})",
        )
        committed = True

    return PullResult(
        slug=slug,
        artifact=PROTOTYPE_ARTIFACT_KEY,
        local_path=local_path,
        unchanged=False,
        etag=file_read.etag,
        committed=committed,
    )


# --- CAP-2: authored-source pull (Marp sources), Story 2.3 -------------------
#
# `bridge-protocol.md` § *Authored-source pull*: same read/etag/decode loop as
# the prototype pull, different landing path, NO extract/build step --
# `deck-export` regenerates the derived set instead.

_MARP_KINDS = ("deck", "executive-summary", "infographic")
"""The three Marp source kinds `bridge-protocol.md`'s own worked example
names (`warden-deck.md`, `warden-executive-summary.md`,
`warden-infographic.md`)."""


def _short_name(slug: str) -> str:
    """`pyforge-<name>` -> `<name>`, the prefix the Design-side Marp source
    filenames themselves carry (`bridge-protocol.md`'s own example: the
    `pyforge-warden` deck's sources are named `warden-deck.md`, not
    `pyforge-warden-deck.md`, inside its own Design project)."""
    return slug.removeprefix("pyforge-")


def pull_marp_source(
    transport: DesignTransport,
    *,
    slug: str,
    repo_root: Path,
    kind: str,
    commit: bool = False,
    state_path: Path | None = None,
    exporter: DeckExporter | None = None,
    committer: GitCommitter | None = None,
    now: Callable[[], datetime] | None = None,
) -> PullResult:
    """CAP-2, Story 2.3: pull one authored Marp source (``bridge-protocol.md``
    § Authored-source pull). ``kind`` must be one of ``_MARP_KINDS``.

    Same read/etag/decode loop as ``pull_prototype`` (``_pull_and_land``,
    Story 2.1) -- no re-decoding, a truncated answer refuses, the write is
    atomic, the etag is recorded under the per-kind key ``f"marp:{kind}"``.
    Unlike ``pull_prototype``, there is no local-prove (extract/build) step:
    ``deck-export`` alone regenerates the derived set from a Marp source.
    ``--commit`` behaves identically to Story 2.2's (opt-in, never on an
    unchanged pull)."""
    if kind not in _MARP_KINDS:
        raise errors.HeraldError(
            f"cannot pull {slug!r}: unknown Marp source kind {kind!r}; "
            f"expected one of {', '.join(sorted(_MARP_KINDS))}"
        )
    resolved_now = now or _default_now
    resolved_state_path = (
        repo_root / state.DEFAULT_STATE_PATH if state_path is None else state_path
    )
    existing = _require_seeded_state(resolved_state_path, slug)
    short = _short_name(slug)
    remote_path = f"{short}-{kind}.md"
    artifact_key = f"marp:{kind}"
    date_str = resolved_now().strftime("%Y-%m-%d")
    deck_dir = repo_root / "presentations" / slug
    local_path = deck_dir / "src" / "marp" / f"{slug}-{kind}-{date_str}.md"

    file_read = _pull_and_land(
        transport,
        slug=slug,
        existing=existing,
        remote_path=remote_path,
        local_path=local_path,
        artifact_key=artifact_key,
    )
    if file_read is None:
        return PullResult(
            slug=slug,
            artifact=artifact_key,
            local_path=None,
            unchanged=True,
            etag=existing.etags.get(artifact_key),
            committed=False,
        )

    (exporter or PixiDeckExporter()).export(slug=slug, repo_root=repo_root)
    # Review finding: see `pull_prototype`'s own note -- record only after
    # export succeeds.
    _record_pull_etag(
        resolved_state_path,
        slug,
        existing,
        artifact_key=artifact_key,
        etag=file_read.etag,
        now=resolved_now,
    )

    committed = False
    if commit:
        (committer or SubprocessGitCommitter()).commit(
            repo_root=repo_root,
            paths=[deck_dir, resolved_state_path],
            message=f"herald: pull {slug} ({artifact_key})",
        )
        committed = True

    return PullResult(
        slug=slug,
        artifact=artifact_key,
        local_path=local_path,
        unchanged=False,
        etag=file_read.etag,
        committed=committed,
    )


# --- CAP-2: authored-source pull (standalone bundle), Story 2.4 -------------
#
# `bridge-protocol.md` § *Authored-source pull*: the Design-authored
# "standalone bundle" (a richer, self-contained infographic HTML poster)
# lands at the export path `src/marp/<slug>-infographic-standalone-<date>.html`,
# superseding any `marp --html` render. That preference is `deck-export`'s
# own responsibility (unmodified by this story, out of this module's code
# map) -- see this story's spec Design Notes for the full boundary. This
# module's ONLY job is landing the bundle file, identically to how
# `pull_marp_source` lands a Marp source: same `_pull_and_land` loop, no
# local-prove step, `exporter.export` after a real change.

STANDALONE_BUNDLE_ARTIFACT_KEY = "standalone-bundle"


def pull_standalone_bundle(
    transport: DesignTransport,
    *,
    slug: str,
    repo_root: Path,
    commit: bool = False,
    state_path: Path | None = None,
    exporter: DeckExporter | None = None,
    committer: GitCommitter | None = None,
    now: Callable[[], datetime] | None = None,
) -> PullResult:
    """CAP-2, Story 2.4: pull the Design-authored standalone infographic
    bundle (``bridge-protocol.md`` § Authored-source pull). Same
    read/etag/decode loop as ``pull_marp_source`` (``_pull_and_land``, Story
    2.1/2.3 reused unchanged) -- no re-decoding, a truncated answer refuses,
    the write is atomic, the etag is recorded under
    ``STANDALONE_BUNDLE_ARTIFACT_KEY``. No local-prove step. Renders no HTML
    itself: landing this bundle at its fixed canonical path is what lets
    ``deck-export`` (unmodified, out of scope here) prefer it over its own
    ``marp --html`` fallback -- see the story spec's Design Notes for why
    that boundary is deliberate. ``--commit`` behaves identically to Stories
    2.2/2.3's (opt-in, never on an unchanged pull)."""
    resolved_now = now or _default_now
    resolved_state_path = (
        repo_root / state.DEFAULT_STATE_PATH if state_path is None else state_path
    )
    existing = _require_seeded_state(resolved_state_path, slug)
    persona = _persona_from_slug(slug)
    remote_path = f"{persona} Infographic standalone.html"
    date_str = resolved_now().strftime("%Y-%m-%d")
    deck_dir = repo_root / "presentations" / slug
    local_path = (
        deck_dir / "src" / "marp" / f"{slug}-infographic-standalone-{date_str}.html"
    )

    file_read = _pull_and_land(
        transport,
        slug=slug,
        existing=existing,
        remote_path=remote_path,
        local_path=local_path,
        artifact_key=STANDALONE_BUNDLE_ARTIFACT_KEY,
    )
    if file_read is None:
        return PullResult(
            slug=slug,
            artifact=STANDALONE_BUNDLE_ARTIFACT_KEY,
            local_path=None,
            unchanged=True,
            etag=existing.etags.get(STANDALONE_BUNDLE_ARTIFACT_KEY),
            committed=False,
        )

    (exporter or PixiDeckExporter()).export(slug=slug, repo_root=repo_root)
    # Review finding: see `pull_prototype`'s own note -- record only after
    # export succeeds.
    _record_pull_etag(
        resolved_state_path,
        slug,
        existing,
        artifact_key=STANDALONE_BUNDLE_ARTIFACT_KEY,
        etag=file_read.etag,
        now=resolved_now,
    )

    committed = False
    if commit:
        (committer or SubprocessGitCommitter()).commit(
            repo_root=repo_root,
            paths=[deck_dir, resolved_state_path],
            message=f"herald: pull {slug} ({STANDALONE_BUNDLE_ARTIFACT_KEY})",
        )
        committed = True

    return PullResult(
        slug=slug,
        artifact=STANDALONE_BUNDLE_ARTIFACT_KEY,
        local_path=local_path,
        unchanged=False,
        etag=file_read.etag,
        committed=committed,
    )


# --- CAP-3: status (Story 3.1/3.2) -------------------------------------------
#
# `bridge-protocol.md`'s pilot table (§ Pilot evidence) names the cautionary
# fixture this pair of stories exists for: the "Local recipes repository
# connection" Design project, a stale hand-mirrored copy of
# `presentations/pyforge-atlas/` -- exactly the shape `stale_mirror` must
# flag. Both stories are read-only: `status` never calls a write-side
# transport method (`write_files`/`copy_files`/`create_project`/
# `create_support_js`/`finalize_plan`) and never calls `state.write`.

_STALE_MIRROR_FILE_COUNT_THRESHOLD = 15
"""A legitimate bridge project holds at most a handful of files: the
runtime pair (`support.js`, `deck-stage.js`), one prototype, up to three
Marp sources, one standalone bundle -- eight at the outside, today. Well
below this threshold, so crossing it is already unusual for a real bridge
project without yet being conclusive on its own (see the nesting check
below)."""

_STALE_MIRROR_NESTED_PATH_THRESHOLD = 5
"""None of `bridge-protocol.md`'s conventions ever puts a '/' in a
Design-side filename -- every legitimate artifact (`support.js`,
`deck-stage.js`, `PyForge <Persona>.dc.html`, `<short>-{kind}.md`, `<Persona>
Infographic standalone.html`) is a flat, project-root name. A hand-mirrored
repo copy looks the opposite: it reproduces the repo's own directory
structure (`src/...`, `.claude/...`), so several of its files carry a
nested path. Five is comfortably above what a stray or transitional file
could produce by accident, comfortably below what a real repo mirror
(dozens of nested paths) would show."""


@dataclass(frozen=True)
class DeckStatus:
    """One deck's status report (CAP-3): whether it is linked to a Design
    project, a fresh etag-based sync classification when it is, the
    last-pull timestamp `state.py` has on record, and the stale-hand-mirror
    flag (FR-12, Story 3.2).

    `sync` is `None` for an unlinked deck (there is nothing to compare) and
    one of `"unchanged"` / `"changed"` / `"conflict"` for a linked one:
    `"unchanged"` when every tracked artifact's fresh etag still matches
    (or the deck has no tracked artifacts yet -- seeded but never pulled);
    `"changed"` when at least one tracked artifact's etag no longer matches
    and every comparison could be made; `"conflict"` when at least one
    comparison itself failed (the transport raised reaching the far end,
    or the tracked file is gone server-side) -- conflict takes precedence
    over changed, since an operator cannot safely decide "pull" is even the
    right action without first resolving the failed comparison."""

    slug: str
    linked: bool
    project_id: str | None
    sync: str | None
    last_pull: str | None
    stale_mirror: bool


def _remote_path_for_artifact(slug: str, artifact_key: str) -> str:
    """The Design-side path a tracked ``state.py`` artifact key names --
    the same per-artifact naming convention ``pull_prototype`` /
    ``pull_marp_source`` / ``pull_standalone_bundle`` already each derive
    for their own single artifact, generalized here since ``status`` must
    resolve whichever keys a deck happens to have recorded."""
    persona = _persona_from_slug(slug)
    if artifact_key == PROTOTYPE_ARTIFACT_KEY:
        return f"PyForge {persona}.dc.html"
    if artifact_key == STANDALONE_BUNDLE_ARTIFACT_KEY:
        return f"{persona} Infographic standalone.html"
    if artifact_key.startswith("marp:"):
        return f"{_short_name(slug)}-{artifact_key.removeprefix('marp:')}.md"
    raise errors.HeraldError(
        f"cannot check status for {slug!r}: unrecognized tracked artifact "
        f"key {artifact_key!r} in {state.DEFAULT_STATE_PATH}"
    )


def _is_stale_mirror(files: Sequence[ListedFile]) -> bool:
    """FR-12's heuristic (Story 3.2): flags a Design project shaped like a
    hand-mirrored repo copy rather than a normal bridge project. Both
    conditions below must hold -- file count alone would false-positive on
    a legitimate deck a future story gives many more tracked artifacts;
    nested-path count alone would false-positive on one stray file. See
    the two threshold constants' own docstrings for the reasoning behind
    each number."""
    if len(files) < _STALE_MIRROR_FILE_COUNT_THRESHOLD:
        return False
    nested = sum(1 for listed in files if "/" in listed.path)
    return nested >= _STALE_MIRROR_NESTED_PATH_THRESHOLD


def _status_for_slug(
    transport: DesignTransport, *, slug: str, state_path: Path
) -> DeckStatus:
    """One deck's ``DeckStatus`` -- read-only throughout: ``state.read`` and
    ``transport.read_file``/``transport.list_files`` only, never a write to
    either surface."""
    existing = state.read(state_path, slug)
    if existing is None:
        return DeckStatus(
            slug=slug,
            linked=False,
            project_id=None,
            sync=None,
            last_pull=None,
            stale_mirror=False,
        )

    saw_conflict = False
    saw_change = False
    for artifact_key, etag in sorted(existing.etags.items()):
        remote_path = _remote_path_for_artifact(slug, artifact_key)
        try:
            file_read = transport.read_file(
                project_id=existing.project_id,
                path=remote_path,
                if_none_match=etag,
            )
        except errors.TransportError:
            # The far end could not be reached, or reported this exact
            # tracked file gone -- either way, "changed" would overclaim an
            # answer this comparison could not actually get.
            saw_conflict = True
            continue
        if not file_read.unchanged:
            saw_change = True
    if saw_conflict:
        sync = "conflict"
    elif saw_change:
        sync = "changed"
    else:
        sync = "unchanged"

    try:
        listed_files = transport.list_files(project_id=existing.project_id)
    except errors.TransportError:
        # Same "the far end could not be reached" treatment as the
        # read_file loop above -- a stale-mirror check that cannot reach
        # Design tells us nothing new; it was already conflicted, or is
        # marked so now, rather than crashing this deck's (and every other
        # known deck's -- see status()'s list comprehension) status report.
        saw_conflict = True
        listed_files = []
    stale_mirror = _is_stale_mirror(listed_files)
    if saw_conflict:
        sync = "conflict"

    return DeckStatus(
        slug=slug,
        linked=True,
        project_id=existing.project_id,
        sync=sync,
        last_pull=existing.last_pull,
        stale_mirror=stale_mirror,
    )


def _known_slugs(repo_root: Path, state_path: Path) -> list[str]:
    """Every deck ``status`` (no slug argument) reports on: the union of
    every slug already recorded in ``state.py`` (seeded) and every
    ``presentations/<slug>/`` directory carrying a ``README.md`` (a deck
    that exists locally but may never have been seeded) -- so an unseeded
    deck is reported as unlinked rather than silently omitted."""
    slugs = set(state.known_slugs(state_path))
    presentations_dir = repo_root / "presentations"
    if presentations_dir.is_dir():
        for entry in presentations_dir.iterdir():
            if entry.is_dir() and (entry / "README.md").is_file():
                slugs.add(entry.name)
    return sorted(slugs)


def status(
    transport: DesignTransport,
    *,
    slug: str | None = None,
    repo_root: Path,
    state_path: Path | None = None,
) -> list[DeckStatus]:
    """CAP-3, Story 3.1/3.2: report every known deck's bridge state (or just
    ``slug``'s, when given), each with a fresh etag comparison against
    Design and the stale-hand-mirror flag (FR-12).

    Read-only end to end (FR-13, NFR-08): reads `state.py` and calls only
    `transport.read_file`/`transport.list_files`, never any write-side
    transport method, and never `state.write`. When ``slug`` is given but
    unlinked (or entirely unknown -- no state entry, no local deck
    directory), returns a single unlinked `DeckStatus` rather than raising:
    unlike `pull_*`, status reporting on an unseeded deck is itself a
    normal, informative answer, not an error."""
    resolved_state_path = (
        repo_root / state.DEFAULT_STATE_PATH if state_path is None else state_path
    )
    if slug is not None:
        # A single explicit slug: a structural failure (e.g. a bogus
        # tracked-artifact key -- AD-6) still raises plainly, matching
        # every other single-deck operation in this module. There is no
        # "rest of the batch" to protect here.
        return [_status_for_slug(transport, slug=slug, state_path=resolved_state_path)]
    slugs = _known_slugs(repo_root, resolved_state_path)
    return [_status_or_conflict(transport, one, resolved_state_path) for one in slugs]


def _status_or_conflict(
    transport: DesignTransport, slug: str, state_path: Path
) -> DeckStatus:
    """``_status_for_slug``, with one deck's structural failure (``state.py``
    is malformed for this slug, or names an artifact key this version does
    not recognize -- both raise ``errors.HeraldError``, AD-6) downgraded to
    a ``"conflict"`` status instead of propagating. Only used for the
    multi-deck (``slug=None``) path in ``status()``: without this, ONE bad
    deck would abort the ENTIRE report, discarding every other deck's
    perfectly valid status -- exactly the "at a glance across the fleet"
    use case this epic exists for. A single-slug request still raises
    plainly (see ``status()``'s own branch), matching every other
    single-deck operation in this module."""
    try:
        return _status_for_slug(transport, slug=slug, state_path=state_path)
    except errors.HeraldError:
        return DeckStatus(
            slug=slug,
            linked=True,
            project_id=None,
            sync="conflict",
            last_pull=None,
            stale_mirror=False,
        )


# --- CAP-5: export push-back, Epic 5 -----------------------------------------
#
# `bridge-protocol.md` § *Export push-back*: after `deck-export` regenerates the
# derived set, push it into the Design project so Design holds the complete set
# too -- `finalize_plan` declaring the export filenames -> `write_files` each
# with its last-known etag (`"0"` for a first push). Unchanged files (compared
# by local content hash against the last-pushed record) are skipped; a
# per-file conflict is refused structurally, without aborting the rest of the
# batch. Design-side names mirror the repo filenames verbatim.
#
# **Scope judgment call (recorded here and in the Story 5.1 spec's Design
# Notes):** `DesignTransport.write_files`'s `data` field is documented as
# inline *text* content ("Write inline file contents") -- exactly the shape
# `seed`/`pull_prototype` already exercise for the `.dc.html` prototype, and
# the only shape any adapter or the wire-format docs in this package have
# ever proven. Of the three derived exports `docs/specs/presentation-deck.md`
# § *Standard export set* names (the standalone HTML poster, and two PPTX
# files), only the HTML is text -- the PPTX pair is binary, and no story in
# this package has observed or proven a binary write_files wire shape (the
# same "unpinned wire shape" caveat `seed`'s own module doc already records
# for a conflicted write, DW-1-2-5). Rather than invent an unverified
# encoding convention, `_discover_export_files` below covers only the
# standalone HTML export for now; pushing the two PPTX companions back is a
# deferred follow-up once a binary `write_files` shape is proven live (see
# the Story 5.1 spec's Verification section).


@dataclass(frozen=True)
class ExportPushResult:
    """What ``push_exports`` returns: which export filenames were actually
    written, and which were skipped because their local content hash
    already matched the last-pushed record. Never populated on a run that
    hit a conflict -- that path raises ``errors.ExportConflictError``
    instead (see ``push_exports``'s own docstring)."""

    slug: str
    pushed: tuple[str, ...]
    skipped: tuple[str, ...]


@dataclass(frozen=True)
class _ExportCandidate:
    """One discovered derived-export file: its Design-side filename (the
    repo basename, mirrored verbatim per ``bridge-protocol.md``), the text
    content to write, and that content's hash -- computed once, reused both
    for the skip comparison and for the post-push state record."""

    filename: str
    local_path: Path
    data: str
    local_hash: str


_EXPORT_ARTIFACT_PREFIX = "export:"
"""``state.DeckState.etags`` keys for push-tracked exports are namespaced
under this prefix (``f"{_EXPORT_ARTIFACT_PREFIX}{filename}"``) so a dated
export filename (e.g. two different ``-2026-08-07``/``-2026-08-08`` runs of
the same kind) never collides with the pull-side artifact keys
(``PROTOTYPE_ARTIFACT_KEY``, ``f"marp:{kind}"``, ``STANDALONE_BUNDLE_ARTIFACT_KEY``)
sharing the same ``etags`` map. Unlike the pull-side keys, the *value*
recorded under an export key is a locally computed content hash, not a
Design-returned etag -- see ``push_exports``'s own docstring for why."""


def _discover_export_files(deck_dir: Path, slug: str) -> list[_ExportCandidate]:
    """The derived export file(s) currently on disk for ``slug``, newest
    first by dated filename. Only the standalone HTML poster is covered
    today -- see this section's own module-level scope note for why the
    PPTX companions are deferred.

    Returns an empty list when ``deck-export`` has never produced the file
    yet (nothing to push, not an error)."""
    marp_dir = deck_dir / "src" / "marp"
    if not marp_dir.is_dir():
        return []
    prefix = f"{slug}-infographic-standalone-"
    dated: list[tuple[str, Path]] = []
    for candidate_path in marp_dir.glob(f"{prefix}*.html"):
        date_segment = candidate_path.stem.removeprefix(prefix)
        try:
            date.fromisoformat(date_segment)
        except ValueError:
            # Not a dated export -- a stray backup/draft/renamed file that
            # happens to share the prefix (e.g. "-old-backup.html",
            # "-FINAL.html"). Plain lexicographic sort would put these
            # AFTER every real dated file (letters sort after digits),
            # silently selecting stale/unrelated content instead of the
            # genuine newest export. Excluded rather than risk pushing it.
            continue
        dated.append((date_segment, candidate_path))
    if not dated:
        return []
    # ISO 8601 dates compare lexicographically in filename order -- the
    # same "newest by name" rule deck_export.py's own `find_source` uses
    # for its Marp sources, now applied only to confirmed-dated matches.
    local_path = max(dated, key=lambda pair: pair[0])[1]
    try:
        text = local_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise errors.HeraldError(
            f"cannot push exports for {slug!r}: could not read {local_path} ({exc})"
        ) from exc
    local_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return [
        _ExportCandidate(
            filename=local_path.name,
            local_path=local_path,
            data=text,
            local_hash=local_hash,
        )
    ]


def push_exports(
    transport: DesignTransport,
    *,
    slug: str,
    repo_root: Path,
    export_dir: Path | None = None,
    state_path: Path | None = None,
) -> ExportPushResult:
    """CAP-5, Story 5.1/5.2: push the derived export set back into Design
    after a pull + ``deck-export`` regeneration (``bridge-protocol.md`` §
    Export push-back). Requires a prior ``seed`` (``_require_seeded_state``,
    reused from CAP-2).

    For each discovered export file (``_discover_export_files``): compares
    its freshly computed content hash against the ``f"export:{filename}"``
    record in ``state.py`` (absent == never pushed, treated as ``"0"``'s
    sentinel meaning at the write-precondition level) and skips it -- no
    ``write_files`` call at all -- when they match (FR-19, NFR-08). Every
    file that changed is declared in one ``finalize_plan`` call (all changed
    filenames together, mirroring ``seed``'s own batch-declare shape), then
    written one ``write_files`` call at a time using that file's current
    server-side etag from ``plan.base_etags`` (``"0"`` for a path that does
    not exist there yet -- FR-18).

    **Conflict handling (Story 5.2, FR-20/NFR-02).** A per-file
    ``write_files`` call that raises ``errors.TransportCallError`` (the
    server was reached and answered with a rejection -- see
    ``transport.base``'s ``require_conditional``/``_call_json`` failure
    path) is treated as a structural conflict for *that file only*: it is
    recorded, and the loop continues to the next candidate rather than
    aborting the whole batch. A broader failure -- ``AuthError``,
    ``TransportUnreachableError`` -- means the transport itself is broken,
    not that Design rejected one write; those propagate immediately and
    halt the whole batch (deliberately narrower than the base
    ``TransportError``, so a mid-batch credential expiry or outage is never
    mistaken for a per-file conflict, and the caller isn't left hammering
    the remaining files against a connection that's still broken).
    ``state.py`` is updated once, after every file has been attempted, and
    only with the files that actually succeeded -- a conflicted file's own
    ``export:`` record is left exactly as it was, so a retry sees it as
    still-changed rather than falsely "already pushed". If any file
    conflicted, ``push_exports`` raises ``errors.ExportConflictError``
    naming every conflicted file (after the state write for the successful
    ones has already landed); otherwise it returns ``ExportPushResult``."""
    resolved_state_path = (
        repo_root / state.DEFAULT_STATE_PATH if state_path is None else state_path
    )
    existing = _require_seeded_state(resolved_state_path, slug, verb="push")
    deck_dir = repo_root / "presentations" / slug
    resolved_export_dir = deck_dir if export_dir is None else export_dir

    candidates = _discover_export_files(resolved_export_dir, slug)

    to_push: list[_ExportCandidate] = []
    skipped: list[str] = []
    for candidate in candidates:
        artifact_key = f"{_EXPORT_ARTIFACT_PREFIX}{candidate.filename}"
        if existing.etags.get(artifact_key) == candidate.local_hash:
            skipped.append(candidate.filename)
            continue
        to_push.append(candidate)

    if not to_push:
        return ExportPushResult(slug=slug, pushed=(), skipped=tuple(skipped))

    plan = transport.finalize_plan(
        project_id=existing.project_id,
        writes=[candidate.filename for candidate in to_push],
    )

    pushed: list[str] = []
    conflicts: list[str] = []
    new_etags = dict(existing.etags)
    for candidate in to_push:
        if_match = plan.base_etags.get(candidate.filename, _FRESH_ETAG)
        try:
            transport.write_files(
                project_id=existing.project_id,
                files=[
                    {
                        "path": candidate.filename,
                        "data": candidate.data,
                        "if_match": if_match,
                    }
                ],
                plan_token=plan.plan_token,
            )
        except errors.TransportCallError as exc:
            conflicts.append(f"{candidate.filename} ({exc})")
            continue
        new_etags[f"{_EXPORT_ARTIFACT_PREFIX}{candidate.filename}"] = (
            candidate.local_hash
        )
        pushed.append(candidate.filename)

    # Persist whichever files actually succeeded -- even when some
    # conflicted -- so a retry never re-pushes a file that already landed.
    # A conflicted file's record is simply absent from `new_etags`'s delta
    # (still whatever it was before this run), so the next attempt sees it
    # as changed and tries again.
    if pushed:
        state.write(
            resolved_state_path,
            slug,
            state.DeckState(
                project_id=existing.project_id,
                etags=new_etags,
                last_pull=existing.last_pull,
            ),
        )

    if conflicts:
        success_note = (
            f" ({len(pushed)} other export(s) pushed successfully)" if pushed else ""
        )
        raise errors.ExportConflictError(
            f"cannot push {len(conflicts)} export(s) for {slug!r}: "
            f"{'; '.join(conflicts)} -- refused rather than risk clobbering "
            f"a Design-side edit{success_note}"
        )

    return ExportPushResult(slug=slug, pushed=tuple(pushed), skipped=tuple(skipped))
