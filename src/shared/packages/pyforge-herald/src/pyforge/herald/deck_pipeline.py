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

import base64
import hashlib
import re
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from pyforge.core.atomic_write import atomic_write_text as core_atomic_write_text

from . import errors, pptx_pipeline, registry, stamps, state

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
    """Write ``text`` to ``path`` atomically via `pyforge.core.
    atomic_write_text` (Story 14.2, CAP-2 -- the one shared
    temp-file-then-`os.replace` primitive, mkstemp-based), mirroring
    ``state.write`` / ``registry.register``'s existing crash-safety
    convention: a process crash mid-write must never leave a corrupt
    half-written pulled file."""
    could_not = f"could not write {path}"
    try:
        core_atomic_write_text(path, text)
    except (OSError, ValueError) as exc:
        raise errors.HeraldError(f"{could_not}: {exc}") from exc


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
    ``pixi run -e pyforge-guild deck-export <slug>``), mirroring
    ``LocalProver``'s pattern: a real implementation shells a bounded
    subprocess; every test injects a hand-written fake."""

    def export(self, *, slug: str, repo_root: Path) -> None:
        """Raise ``errors.HeraldError`` naming what failed; return normally
        on success."""
        ...


class PixiDeckExporter:
    """The real ``DeckExporter``: ``pixi run -e pyforge-guild deck-export
    <slug>`` in ``repo_root``, one bounded subprocess call. Never invoked by
    this package's own tests (every pull test injects a fake)."""

    def __init__(self, *, timeout: float = _DEFAULT_EXPORT_TIMEOUT) -> None:
        self._timeout = timeout

    def export(self, *, slug: str, repo_root: Path) -> None:
        try:
            completed = subprocess.run(
                ["pixi", "run", "-e", "pyforge-guild", "deck-export", slug],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise errors.HeraldError(
                f"deck-export failed: 'pixi run -e pyforge-guild deck-export "
                f"{slug}' in {repo_root} exceeded {self._timeout}s ({exc})"
            ) from exc
        except OSError as exc:
            raise errors.HeraldError(
                f"deck-export failed: could not run 'pixi run -e "
                f"pyforge-guild deck-export {slug}' in {repo_root} ({exc})"
            ) from exc
        if completed.returncode != 0:
            tail = (completed.stderr or completed.stdout or "").strip()[-2000:]
            raise errors.HeraldError(
                f"deck-export failed: 'pixi run -e pyforge-guild deck-export "
                f"{slug}' in {repo_root} exited {completed.returncode}: {tail}"
            )


class _PixiPartialDeckExporter:
    """``PptxTemplateExporter``'s own subprocess seam: ``pixi run -e
    pyforge-guild deck-export <slug> html infographic-pptx`` -- explicit
    targets that exclude ``deck-pptx`` (Design Notes: "``.potx`` replaces
    only the 'deck' PPTX target"), one bounded subprocess call. Mirrors
    ``PixiDeckExporter``'s subprocess pattern exactly, over a fixed partial
    target list instead of no arguments (which would regenerate all three,
    including the one target this story replaces). A separate class rather
    than a new ``PixiDeckExporter`` parameter, so ``PixiDeckExporter``
    itself (and every existing caller/test of it) stays untouched. Never
    invoked by this package's own tests (every test injects a fake)."""

    def __init__(self, *, timeout: float = _DEFAULT_EXPORT_TIMEOUT) -> None:
        self._timeout = timeout

    def export(self, *, slug: str, repo_root: Path) -> None:
        cmd = [
            "pixi",
            "run",
            "-e",
            "pyforge-guild",
            "deck-export",
            slug,
            "html",
            "infographic-pptx",
        ]
        try:
            completed = subprocess.run(
                cmd,
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise errors.HeraldError(
                f"deck-export failed: {' '.join(cmd)!r} in {repo_root} "
                f"exceeded {self._timeout}s ({exc})"
            ) from exc
        except OSError as exc:
            raise errors.HeraldError(
                f"deck-export failed: could not run {' '.join(cmd)!r} in "
                f"{repo_root} ({exc})"
            ) from exc
        if completed.returncode != 0:
            tail = (completed.stderr or completed.stdout or "").strip()[-2000:]
            raise errors.HeraldError(
                f"deck-export failed: {' '.join(cmd)!r} in {repo_root} "
                f"exited {completed.returncode}: {tail}"
            )


class PptxTemplateExporter:
    """CAP-1's ``.potx`` template-fill path (Story 23.3): routed to in
    place of ``PixiDeckExporter`` only for a deck whose README declares a
    ``.potx`` template (``select_exporter``, below). Replaces ONLY the
    "deck" PPTX target -- the one target whose content shape (a linear
    slide list) matches ``content_plan.json`` (Design Notes) -- with a
    genuinely editable PowerPoint via ``pptx_pipeline.run_fill``, never a
    Marp render. ``html``/``infographic-pptx`` still derive from Marp via
    ``deck-export``, shelled here with explicit targets that exclude
    ``deck-pptx`` (``_PixiPartialDeckExporter``); those two are already
    stamped by ``deck_export.py``'s own subprocess, so this class stamps
    only the filled PPTX it wrote itself."""

    def __init__(
        self,
        *,
        html_exporter: DeckExporter | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._html_exporter = html_exporter or _PixiPartialDeckExporter()
        self._now = now or _default_now

    def export(self, *, slug: str, repo_root: Path) -> None:
        deck_dir = repo_root / "presentations" / slug
        readme_path = deck_dir / "README.md"
        template_rel = registry.read_potx_template(readme_path)
        if template_rel is None:
            raise errors.HeraldError(
                f"cannot export {slug!r} via the .potx path: no PowerPoint "
                f"template registered in {readme_path}"
            )
        content_plan_path = deck_dir / "src" / "content_plan.json"
        if not content_plan_path.is_file():
            raise errors.HeraldError(
                f"cannot export {slug!r} via the .potx path: no content "
                f"plan at {content_plan_path} (hand-authored, looked up by "
                f"convention -- never auto-generated)"
            )
        template_path = repo_root / template_rel
        date_str = self._now().strftime("%Y-%m-%d")
        out_path = deck_dir / "src" / "pptx" / f"{slug}-deck-{date_str}.pptx"

        pptx_pipeline.run_fill(template_path, content_plan_path, out_path)
        self._html_exporter.export(slug=slug, repo_root=repo_root)
        stamps.write_stamp(out_path, repo_root=repo_root, slug=slug)


def select_exporter(slug: str, repo_root: Path) -> DeckExporter:
    """Routes a deck's derive path (Story 23.3): ``PptxTemplateExporter``
    when the deck's README declares a ``.potx`` template
    (``registry.read_potx_template``), else the existing
    ``PixiDeckExporter`` -- routing strictly on that one declaration
    (Boundaries & Constraints: "no other deck's output changes"). Used as
    the default (an explicit ``exporter=`` argument to any ``pull_*``
    function always wins) by each of this module's three pull functions."""
    readme_path = repo_root / "presentations" / slug / "README.md"
    if registry.read_potx_template(readme_path) is not None:
        return PptxTemplateExporter()
    return PixiDeckExporter()


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
    (exporter or select_exporter(slug=slug, repo_root=repo_root)).export(
        slug=slug, repo_root=repo_root
    )
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

    (exporter or select_exporter(slug=slug, repo_root=repo_root)).export(
        slug=slug, repo_root=repo_root
    )
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

    (exporter or select_exporter(slug=slug, repo_root=repo_root)).export(
        slug=slug, repo_root=repo_root
    )
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


# --- CAP-2 (from spec-design-sync-loop): adopt, Story 23.2 -------------------
#
# `_require_seeded_state`'s own docstring names the gap: pulling (and
# pushing) a deck needs a `project_id` `state.py` already has on record, and
# unlike `seed`'s registry-bootstrap fallback there was, until this story,
# "no analogous 'adopt an already-linked deck' path". `docs/dreams/
# design-sync-loop.md`'s own measured evidence is the concrete case: Design
# projects that already exist -- `PyForge six-quarter roadmap`,
# `LLM Knowledge Bases`, `Agentic AI SLDC deck`, plus the three design-system
# libraries (`Modernist`/`Broadsheet`/`Nocturne`) -- with no local twin (or,
# for `agentic-sdlc`, a twin that was never registered). None of these
# follow the `PyForge <Persona> deck` / `PyForge <Persona>.dc.html` naming
# convention `_persona_from_slug` derives (`agentic-sdlc`'s own file is
# `Agentic SDLC.dc.html`; `six-quarter-roadmap`'s are `PyForge Roadmap*.dc.
# html`; a design system has no "prototype" at all, only a library tree) --
# so `adopt`, unlike every `pull_*` function above, never derives a remote
# filename from `slug`. Every artifact is named explicitly by the caller.
#
# `adopt` also pulls double duty as the design-system mirror (CAP-30's other
# half): passing `project_name=None`/`project_url=None` skips the `registry.
# py` §*Design project* section entirely -- that section's own module doc
# frames itself narrowly around a deck's single bridge, and design systems
# are libraries the decks bind to, never decks themselves (`registry.
# DESIGN_SYSTEM_PROJECT_NAMES`'s own docstring). `state_key` still tracks
# per-artifact etags in the same shared `.herald/bridge-state.json` --
# `state.py` treats it as an opaque JSON key, never a deck slug specifically.


@dataclass(frozen=True)
class AdoptedArtifact:
    """One artifact `adopt` considered: its remote path, where it landed
    locally, and whether THIS run actually pulled new bytes (`unchanged`
    mirrors `PullResult`'s own field -- an etag short-circuit is not a
    write, so a fully-synced second `adopt` call reports every artifact
    `unchanged` and touches no file)."""

    remote_path: str
    local_path: Path
    unchanged: bool


@dataclass(frozen=True)
class AdoptResult:
    """What `adopt` returns: whether this run bootstrapped a NEW local
    twin (false on every later, idempotent call), whether it wrote the
    registry section (false when one already existed, or when this
    `adopt` call never registers at all -- the design-system case), and
    one `AdoptedArtifact` per requested artifact, in request order."""

    state_key: str
    bootstrapped: bool
    registered: bool
    artifacts: tuple[AdoptedArtifact, ...]


_TRUNCATION_TRAILER_RE = re.compile(
    r"\n\n…\[\+\d+ bytes truncated at read_file's 256 KiB cap — the body "
    r"ends at a complete line; continue with offset=\d+\]\Z"
)
"""A truncated (non-final) window's ``body`` carries TWO extra lines beyond
its own declared ``lines="A-B"`` span: a blank separator, then a
human-readable resumption hint (e.g. ``…[+58491 bytes truncated at
read_file's 256 KiB cap -- the body ends at a complete line; continue with
offset=2774]``) -- both inside the wrapper, so `parse_read_response`
(which only strips the wrapper's own framing newline) passes them straight
through as if they were file content. Verified live 2026-09-18 pulling
`six-quarter-roadmap`'s 3377-line prototype: window 1's declared
``lines="1-2773"`` is accurate for the real file, but its raw `body` came
back 2775 lines long -- 2773 real lines plus this exact two-line tail. A
window that reaches end-of-file (this repo's own probe: no further call
needed) carries no such tail, so this is stripped unconditionally rather
than only on a still-truncated window -- the pattern cannot occur in real
file content (its own literal text names the mechanism), so a no-op
non-match is the correct outcome everywhere else."""


def _windowed_read(
    transport: DesignTransport,
    *,
    project_id: str,
    path: str,
    if_none_match: str | None = None,
) -> FileRead:
    """`transport.read_file`, reassembled across as many offset-paged calls
    as the server's per-call size cap requires. `_pull_and_land` refuses
    outright on a truncated single read -- every existing deck's prototype
    fits comfortably under the cap. `adopt`'s artifacts make no such
    promise (`docs/dreams/design-sync-loop.md`'s own measured evidence
    includes one that does not: `six-quarter-roadmap`'s primary prototype,
    ~320 KB), so this helper pages through ``offset`` until a window's own
    ``last_line`` reaches its ``total_lines`` -- or, for a file the server
    answered whole (no window metadata at all), after exactly one call.
    ``if_none_match`` is honoured only on the FIRST call: an etag
    precondition is checked against the file's current whole state, never
    any one window of it. Verified live 2026-09-18: the server does NOT
    answer its own ``{unchanged: true}`` short-circuit once a file needs
    windowing at all -- an ``if_none_match`` that exactly matches the
    current etag still comes back as an ordinary (truncated) first
    window, never the short-circuit form `_pull_and_land` relies on for
    every artifact under the cap. This function therefore checks the
    FIRST window's own ``etag`` against ``if_none_match`` itself, right
    after that one call and before requesting any further window --
    without this, a file requiring windowing could never report
    "unchanged" at all, breaking CAP-30's own idempotency requirement for
    exactly the one artifact that needs this helper in the first place.

    Windows are joined on their shared line boundary (``"\\n".join``):
    ``parse_read_response`` already strips exactly the wrapper's own
    framing newline from each window's ``body``, so the real newline that
    separated a window's last line from the next window's first line in
    the original file survives only if this join re-adds it -- never
    doubled (the framing one was already stripped) and never lost (two
    real lines were always either side of it). Each window's body is
    first passed through ``_TRUNCATION_TRAILER_RE`` (see its own
    docstring) to drop the server's resumption-hint tail before the join
    -- otherwise it would be joined into the file as two bogus lines.

    Raises ``errors.HeraldError`` naming ``path`` when a window reports a
    change but returns no body, or reports itself as partial with no
    ``last_line``/``total_lines`` pair to resume from -- the server's own
    contract says a window "ends at a complete line", so a window that
    cannot say where it ended must never be silently treated as the whole
    file. Raises ``errors.PaginationStalledError`` (DW-FU-23-2, Story
    23.2's Edge Case Hunter finding) naming ``path`` and the stalled line
    when a paged-for window's own ``last_line`` does not advance past the
    previous window's -- unreachable in every live call observed so far
    (every one paged forward), but a server that repeated a window would
    otherwise loop here forever."""
    # Lazy, not module-level -- mirrors `seed`'s own `MODERNIST_DESIGN_
    # SYSTEM_ID` import (see its call site's comment): this function
    # constructs a real `FileRead` at call time, unlike every other use of
    # that name in this module, which is a `TYPE_CHECKING`-only
    # annotation. `test_importing_deck_pipeline_does_not_load_the_
    # transport_package` asserts merely importing this module must not
    # load `transport/__init__.py`'s eager adapter imports.
    from .transport.base import FileRead

    first = transport.read_file(
        project_id=project_id, path=path, if_none_match=if_none_match
    )
    if first.unchanged:
        return first
    if if_none_match is not None and first.etag == if_none_match:
        # The server's own short-circuit never fires once a file needs
        # windowing (see this function's own docstring) -- this is that
        # short-circuit's replacement, checked before any further window
        # is requested.
        return FileRead(path=path, etag=first.etag, body=None, unchanged=True)
    parts: list[str] = []
    etag = first.etag
    window: FileRead = first
    previous_last_line: int | None = None
    while True:
        if window.body is None:
            raise errors.HeraldError(
                f"cannot read {path!r}: read_file reported a change but "
                f"returned no body"
            )
        parts.append(_TRUNCATION_TRAILER_RE.sub("", window.body))
        etag = window.etag
        no_window_declared = (
            window.first_line is None
            and window.last_line is None
            and window.total_lines is None
        )
        if no_window_declared:
            break  # the whole file arrived in this one call
        if window.last_line is None or window.total_lines is None:
            raise errors.HeraldError(
                f"cannot read {path!r}: server reported a partial window "
                f"with no last_line/total_lines pair to resume from"
            )
        if previous_last_line is not None and window.last_line <= previous_last_line:
            # DW-FU-23-2: a paged-for window whose own last_line did not
            # advance past the window it was paged FOR (`offset=
            # previous_last_line + 1`) would otherwise be re-requested at
            # the same offset forever -- refuse instead of looping.
            raise errors.PaginationStalledError(
                f"cannot read {path!r}: read_file returned a window ending "
                f"at line {window.last_line} of {window.total_lines}, which "
                f"did not advance past the previous window's line "
                f"{previous_last_line} -- refusing rather than looping "
                f"forever on a stalled window"
            )
        if window.last_line >= window.total_lines:
            break  # this window reached end of file
        previous_last_line = window.last_line
        window = transport.read_file(
            project_id=project_id, path=path, offset=window.last_line + 1
        )
    return FileRead(path=path, etag=etag, body="\n".join(parts), unchanged=False)


def adopt(
    transport: DesignTransport,
    *,
    state_key: str,
    project_id: str,
    artifacts: Sequence[tuple[str, str]],
    dest_dir: Path,
    repo_root: Path,
    project_name: str | None = None,
    project_url: str | None = None,
    state_path: Path | None = None,
    now: Callable[[], datetime] | None = None,
) -> AdoptResult:
    """Story 23.2 (CAP-2): adopt an existing Design project that has no
    local twin (or, `agentic-sdlc`'s case, an unregistered one) -- see the
    module comment above this function for why this cannot reuse `seed`
    (repo -> Design, creates a NEW remote project) or any `pull_*`
    function (bound to the `PyForge <Persona>` naming convention).

    ``artifacts`` is ``(remote_path, local_relative_path)`` pairs, pulled
    in order via ``_windowed_read`` and landed at ``dest_dir /
    local_relative_path``. Idempotent by construction: each artifact's
    last-seen etag (``state.py``, keyed by its own ``remote_path`` under
    ``state_key``) short-circuits exactly like every `pull_*` function's
    `if_none_match`, so a second `adopt` call for an already-adopted
    ``state_key`` against unchanged Design content pulls nothing and
    writes nothing (CAP-30's own success criterion) -- each artifact's new
    etag is recorded immediately after it lands, mirroring
    `_record_pull_etag`'s own "only after the write genuinely succeeds"
    discipline, so a crash mid-loop leaves a retry only re-pulling what
    did not yet land.

    Creates ``dest_dir`` (and a minimal ``README.md`` skeleton, when
    ``project_name``/``project_url`` are both given and no README exists
    yet) on first adoption -- the one structural difference from every
    ``pull_*`` function, which all require a seeded deck directory to
    already exist. When both are given, registers the README's §*Design
    project* section (``registry.register``) exactly once -- skipped on
    every later call once a section already parses (``registry.read``),
    never re-written even though its content would come out identical,
    so a fully-synced second call touches that file not at all. When
    either is ``None`` (the design-system mirror case -- see the module
    comment), no README is created or touched and no registry section is
    ever written.

    Raises ``errors.HeraldError`` when ``artifacts`` is empty, or when
    ``state_key`` was already adopted against a *different*
    ``project_id`` (a caller bug or a slug collision -- silently
    re-pointing an existing twin at a different remote project would
    misattribute every artifact already on record for it)."""
    if not artifacts:
        raise errors.HeraldError(f"cannot adopt {state_key!r}: no artifacts given")
    resolved_now = now or _default_now
    resolved_state_path = (
        repo_root / state.DEFAULT_STATE_PATH if state_path is None else state_path
    )
    existing = state.read(resolved_state_path, state_key)
    bootstrapped = existing is None
    if existing is None:
        existing = state.DeckState(project_id=project_id, etags={}, last_pull=None)
    elif existing.project_id != project_id:
        raise errors.HeraldError(
            f"cannot adopt {state_key!r}: already adopted against Design "
            f"project {existing.project_id!r}, not {project_id!r}"
        )

    dest_dir.mkdir(parents=True, exist_ok=True)
    registered = False
    if project_name is not None and project_url is not None:
        readme_path = dest_dir / "README.md"
        if not readme_path.is_file():
            _atomic_write_text(readme_path, f"# {state_key}\n")
        if registry.read(readme_path) is None:
            registry.register(
                readme_path=readme_path,
                project_name=project_name,
                project_id=project_id,
                file_url=project_url,
            )
            registered = True

    results: list[AdoptedArtifact] = []
    for remote_path, relative_local_path in artifacts:
        local_path = dest_dir / relative_local_path
        file_read = _windowed_read(
            transport,
            project_id=project_id,
            path=remote_path,
            if_none_match=existing.etags.get(remote_path),
        )
        if file_read.unchanged:
            results.append(
                AdoptedArtifact(
                    remote_path=remote_path, local_path=local_path, unchanged=True
                )
            )
            continue
        _atomic_write_text(local_path, file_read.body or "")
        new_etags = dict(existing.etags)
        new_etags[remote_path] = file_read.etag
        existing = state.DeckState(
            project_id=existing.project_id,
            etags=new_etags,
            last_pull=resolved_now().isoformat(),
        )
        state.write(resolved_state_path, state_key, existing)
        results.append(
            AdoptedArtifact(
                remote_path=remote_path, local_path=local_path, unchanged=False
            )
        )

    return AdoptResult(
        state_key=state_key,
        bootstrapped=bootstrapped,
        registered=registered,
        artifacts=tuple(results),
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


# --- Story 23.1: account-wide reconciliation (CAP-1) -------------------------
#
# `herald deck status` above (CAP-3) only ever reports on a deck this repo
# already knows about -- a slug with a `presentations/<slug>/` directory or a
# `state.py` entry. It has no way to see a Design project that exists in the
# signed-in account but has no local twin at all: `docs/dreams/
# design-sync-loop.md`'s own measured evidence is `PyForge six-quarter
# roadmap` and `LLM Knowledge Bases` (no twin, ever) and `Agentic AI SLDC
# deck` (a twin exists, unregistered). `account_status` closes that gap:
# `transport.list_projects()` enumerates the whole account, and every
# project is reconciled against the registry -- `registry.read_exclusions`
# (the family-level exclusion list) and `registry.DESIGN_SYSTEM_PROJECT_NAMES`
# (the known design-system libraries) first, by exact name; every remaining
# project is a presentation, "linked" when some local deck's own § *Design
# project* section (`registry.read`, never `state.py`'s gitignored,
# per-clone cache) names this exact project id, "untwinned" otherwise. Like
# CAP-3's `status`, this is read-only end to end: it never calls a
# write-side transport method and never touches `state.py`.


@dataclass(frozen=True)
class AccountProjectStatus:
    """One Design project's account-wide reconciliation report (Story
    23.1, CAP-1): every project ``transport.list_projects()`` returns,
    classified against the registry so ``herald deck status --account``
    can report on all of them -- no project absent (CAP-1's own success
    signal) -- not just the ones a local README registry section already
    names.

    ``status`` is one of ``"linked"`` (a presentation with a local twin --
    ``slug`` names it), ``"untwinned"`` (a presentation with no local twin
    yet), ``"mirrored"`` (a known design system -- a bound library, never a
    deck), or ``"excluded"`` (recorded by name in ``presentations/
    README.md`` -- ``reason`` names why)."""

    project_id: str
    name: str
    url: str
    status: str
    slug: str | None = None
    reason: str | None = None


def _twinned_project_ids(repo_root: Path) -> dict[str, str]:
    """Every local ``presentations/<slug>/`` deck's own registered Design
    project id, mapped back to its slug -- read from each deck's own README
    § *Design project* section (``registry.read``), the durable, git-tracked
    record CAP-1 reconciles against (never ``state.py``'s gitignored,
    per-clone operational cache, which a fresh clone starts without --
    mirrors Story 20.13's identical "no second registry" ruling). A README
    with no such section, or that fails to parse, contributes nothing for
    that slug rather than aborting the whole reconciliation -- one
    malformed deck must not hide every other project's real status.

    Raises ``errors.HeraldError`` naming both slugs and the project id when
    two local decks are registered against the same Design project id --
    silently letting the later-sorted slug win would misattribute
    ``AccountProjectStatus.slug`` with no error, unlike this module's
    fail-loud handling of every other malformed-registry shape."""
    presentations_dir = repo_root / "presentations"
    by_project_id: dict[str, str] = {}
    if not presentations_dir.is_dir():
        return by_project_id
    for entry in sorted(presentations_dir.iterdir()):
        if not entry.is_dir():
            continue
        try:
            design_project = registry.read(entry / "README.md")
        except errors.HeraldError:
            continue
        if design_project is None:
            continue
        project_id = design_project.project_id
        if project_id in by_project_id:
            raise errors.HeraldError(
                f"cannot reconcile the account: {by_project_id[project_id]!r} "
                f"and {entry.name!r} are both registered against the same "
                f"Design project id {project_id!r}"
            )
        by_project_id[project_id] = entry.name
    return by_project_id


def account_status(
    transport: DesignTransport, *, repo_root: Path
) -> list[AccountProjectStatus]:
    """CAP-1 (Story 23.1): enumerate every Design project the signed-in
    account can see and reconcile it against the registry, so
    ``herald deck status --account`` reports on all of it -- unlike CAP-3's
    ``status`` above, which only ever reports on a slug this repo already
    knows about.

    Classification order (never a name heuristic, the story's own Never
    boundary): an *exact* name match against ``registry.read_exclusions``
    wins first, then an exact name match against
    ``registry.DESIGN_SYSTEM_PROJECT_NAMES``, then a presentation --
    "linked" when some local deck's own registry section names this exact
    project id, "untwinned" otherwise.

    Read-only, like CAP-3's ``status``: calls only
    ``transport.list_projects``, never a write-side transport method, and
    never touches ``state.py``."""
    exclusions = registry.read_exclusions(repo_root / "presentations" / "README.md")
    twinned = _twinned_project_ids(repo_root)
    results: list[AccountProjectStatus] = []
    for project in transport.list_projects():
        if project.name in exclusions:
            results.append(
                AccountProjectStatus(
                    project_id=project.project_id,
                    name=project.name,
                    url=project.url,
                    status="excluded",
                    reason=exclusions[project.name],
                )
            )
        elif project.name in registry.DESIGN_SYSTEM_PROJECT_NAMES:
            results.append(
                AccountProjectStatus(
                    project_id=project.project_id,
                    name=project.name,
                    url=project.url,
                    status="mirrored",
                )
            )
        elif project.project_id in twinned:
            results.append(
                AccountProjectStatus(
                    project_id=project.project_id,
                    name=project.name,
                    url=project.url,
                    status="linked",
                    slug=twinned[project.project_id],
                )
            )
        else:
            results.append(
                AccountProjectStatus(
                    project_id=project.project_id,
                    name=project.name,
                    url=project.url,
                    status="untwinned",
                )
            )
    return results


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
# **Binary write shape, proven live (Story 23.4).**
# `DesignTransport.write_files`'s `data` field is documented as inline
# *text* content ("Write inline file contents") -- exactly the shape
# `seed`/`pull_prototype` already exercise for the `.dc.html` prototype. Of
# the three derived exports `docs/specs/presentation-deck.md` § *Standard
# export set* names (the standalone HTML poster, and two PPTX files), only
# the HTML is text -- the PPTX pair is binary. Story 5.1 deferred pushing
# them until a binary `write_files` wire shape was proven live (the same
# "unpinned wire shape" caveat `seed`'s own module doc already records for a
# conflicted write, DW-1-2-5); Story 23.4 closes that gap -- `write_files`
# accepts `encoding: "base64"` alongside a base64-encoded `data` string, so
# `_discover_export_files` below now also discovers the two PPTX
# companions. The poster's own text push stays byte-for-byte unchanged: it
# never carries an `encoding` key.
#
# **`--prove` (Story 23.4, CAP-6).** `push_exports`'s optional `prove=True`
# mechanizes the manual "curl the serve URL, strip the injected harness,
# diff the bytes" recipe (`docs/specs/presentation-deck.md` § *Large-file
# uploads*) into a read-back assertion run right after a successful push:
# `transport.fetch_rendered_bytes` fetches each just-pushed file's
# currently-rendered bytes, `_strip_serve_harness` removes the
# `data-omelette-injected` harness for an `.html` path (a no-op passthrough
# for anything else), and the result is compared byte-for-byte against what
# was actually sent. Every match appends one row to the deck README's dated
# Ledger (`registry.append_push_ledger_row`); any mismatch raises
# `errors.ReadBackMismatchError` naming every mismatched file, and that
# file's `export:` state entry is left exactly as it was (never marked
# "successfully pushed"), so a retry sees it as still-changed.


@dataclass(frozen=True)
class ExportPushResult:
    """What ``push_exports`` returns: which export filenames were actually
    written, which were skipped because their local content hash already
    matched the last-pushed record, and (only when ``prove=True``) which of
    the pushed files read back byte-identical. ``proven`` is always empty
    when ``prove`` was not passed (Story 23.4) -- no read-back call is ever
    made in that case. Never populated on a run that hit a conflict -- that
    path raises ``errors.ExportConflictError`` instead (see
    ``push_exports``'s own docstring)."""

    slug: str
    pushed: tuple[str, ...]
    skipped: tuple[str, ...]
    proven: tuple[str, ...] = ()


@dataclass(frozen=True)
class _ExportCandidate:
    """One discovered derived-export file: its Design-side filename (the
    repo basename, mirrored verbatim per ``bridge-protocol.md``), the wire
    payload to write, and that payload's hash -- computed once, reused both
    for the skip comparison and for the post-push state record.

    ``data`` is the exact ``write_files`` ``data`` field: the file's own
    text for a text candidate (``binary=False``, the poster), or its bytes
    base64-encoded to ASCII for a binary one (``binary=True``, Story 23.4's
    PPTX pair) -- ``_candidate_raw_bytes`` below undoes that encoding for
    the ``local_hash``/``--prove`` comparisons. ``local_hash`` is always
    ``hashlib.sha256`` of the *raw* bytes (the text UTF-8-encoded, or the
    PPTX's own bytes) -- never of the base64 string, so a binary file's
    hash matches what a byte-for-byte disk comparison would give."""

    filename: str
    local_path: Path
    data: str
    local_hash: str
    binary: bool = False


def _candidate_raw_bytes(candidate: _ExportCandidate) -> bytes:
    """The exact bytes ``push_exports`` sent to Design for ``candidate`` --
    base64-decoded from the wire payload for a binary candidate, UTF-8
    encoded from it otherwise. Shared by the ``--prove`` read-back
    comparison and the Ledger row's byte count (Story 23.4)."""
    if candidate.binary:
        return base64.b64decode(candidate.data)
    return candidate.data.encode("utf-8")


def _newest_dated_match(directory: Path, prefix: str, suffix: str) -> Path | None:
    """The most recent ``{prefix}<ISO-date>{suffix}`` file directly under
    ``directory``, or ``None`` when ``directory`` does not exist or holds no
    such file -- the "newest ISO-dated file per kind" rule Story 5.1
    established for the HTML poster, generalized (Story 23.4) so the PPTX
    pair uses the identical rule rather than a second copy of it.

    A candidate whose date segment does not parse as ``YYYY-MM-DD`` is
    excluded rather than risk a plain lexicographic sort silently picking a
    stray same-prefix file (a hand-copied backup, an aborted draft) over
    the genuine newest export -- letters would otherwise sort after
    digits, putting a file like ``-old-backup{suffix}`` last."""
    if not directory.is_dir():
        return None
    dated: list[tuple[str, Path]] = []
    for candidate_path in directory.glob(f"{prefix}*{suffix}"):
        date_segment = candidate_path.name[len(prefix) : -len(suffix)]
        try:
            date.fromisoformat(date_segment)
        except ValueError:
            continue
        dated.append((date_segment, candidate_path))
    if not dated:
        return None
    # ISO 8601 dates compare lexicographically in filename order.
    return max(dated, key=lambda pair: pair[0])[1]


_EXPORT_ARTIFACT_PREFIX = "export:"
"""``state.DeckState.etags`` keys for push-tracked exports are namespaced
under this prefix (``f"{_EXPORT_ARTIFACT_PREFIX}{filename}"``) so a dated
export filename (e.g. two different ``-2026-08-07``/``-2026-08-08`` runs of
the same kind) never collides with the pull-side artifact keys
(``PROTOTYPE_ARTIFACT_KEY``, ``f"marp:{kind}"``, ``STANDALONE_BUNDLE_ARTIFACT_KEY``)
sharing the same ``etags`` map. Unlike the pull-side keys, the *value*
recorded under an export key is a locally computed content hash, not a
Design-returned etag -- see ``push_exports``'s own docstring for why."""


_PPTX_PREFIXES = (
    "{slug}-deck-",
    "{slug}_infographic_deck-",
)
"""The two ``src/pptx/`` filename kinds ``scripts/deck_export.py`` produces
(``deck-pptx`` / ``infographic-pptx``) -- also the kind Story 23.5's
``PptxTemplateExporter`` writes for the ``.potx`` path, since both routes
write the identical ``{slug}-deck-<date>.pptx`` name for the "deck" target.
``_discover_export_files`` below applies ``_newest_dated_match`` to each,
regardless of which exporter produced it."""


def _discover_export_files(deck_dir: Path, slug: str) -> list[_ExportCandidate]:
    """The derived export file(s) currently on disk for ``slug``: the
    standalone HTML poster plus (Story 23.4) the two PPTX companions --
    each the newest ISO-dated file of its own kind, discovered
    independently, so a deck with only some of the three exports on disk
    still pushes whichever ones exist.

    Returns an empty list when ``deck-export`` has never produced any of
    them yet (nothing to push, not an error)."""
    candidates: list[_ExportCandidate] = []

    html_path = _newest_dated_match(
        deck_dir / "src" / "marp", f"{slug}-infographic-standalone-", ".html"
    )
    if html_path is not None:
        try:
            text = html_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise errors.HeraldError(
                f"cannot push exports for {slug!r}: could not read {html_path} ({exc})"
            ) from exc
        candidates.append(
            _ExportCandidate(
                filename=html_path.name,
                local_path=html_path,
                data=text,
                local_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            )
        )

    pptx_dir = deck_dir / "src" / "pptx"
    for prefix_template in _PPTX_PREFIXES:
        pptx_path = _newest_dated_match(
            pptx_dir, prefix_template.format(slug=slug), ".pptx"
        )
        if pptx_path is None:
            continue
        try:
            raw_bytes = pptx_path.read_bytes()
        except OSError as exc:
            raise errors.HeraldError(
                f"cannot push exports for {slug!r}: could not read {pptx_path} ({exc})"
            ) from exc
        candidates.append(
            _ExportCandidate(
                filename=pptx_path.name,
                local_path=pptx_path,
                data=base64.b64encode(raw_bytes).decode("ascii"),
                local_hash=hashlib.sha256(raw_bytes).hexdigest(),
                binary=True,
            )
        )

    return candidates


_HEAD_OPEN_RE = re.compile(rb"<head\b[^>]*>", re.IGNORECASE)
_WHITESPACE_RE = re.compile(rb"\s*")
_OMELETTE_TAG_RE = re.compile(
    rb"<(style|script)\b[^>]*\bdata-omelette-injected\b[^>]*>.*?</\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
"""One ``<style>``/``<script>`` tag carrying ``data-omelette-injected``
anywhere in its opening tag (``docs/specs/presentation-deck.md`` § *Large-file
uploads*: the host editor injects these into a served HTML document and
marks them so they are "never written back as authored source"). The
non-greedy ``.*?`` body plus a backreferenced closing tag keeps a run of
several such tags from being swallowed as one match."""


def _strip_serve_harness(content: bytes, *, path: str) -> bytes:
    """Undo Design's injected preview harness from ``render_preview``'s
    served bytes for ``path`` (Story 23.4's ``--prove``), so the result can
    be compared byte-for-byte against what was actually pushed.

    Only an ``.html`` path can carry the harness described in
    ``docs/specs/presentation-deck.md``: a contiguous run of
    ``data-omelette-injected`` ``<style>``/``<script>`` tags spliced in
    immediately after the document's ``<head ...>`` opening tag (whitespace
    between tags is tolerated). Every other extension -- including both
    PPTX exports this story adds to the push path -- is returned unchanged;
    a PPTX is a binary zip archive, not an HTML document, so there is no
    ``<head>`` for a host editor to inject into (confirmed live during this
    story's own implementation -- see its spec's Design Notes).

    A match is spliced out and replaced with a single newline, mirroring
    the manual recipe's own "splice with a single newline" step. Content
    with no ``<head>`` tag at all, or an ``<head>`` with nothing injected
    directly after it, is returned unchanged -- this is a targeted removal
    of a known-shaped block, never a heuristic HTML rewrite."""
    if not path.lower().endswith(".html"):
        return content
    head_match = _HEAD_OPEN_RE.search(content)
    if head_match is None:
        return content
    start = head_match.end()
    pos = start
    while True:
        probe = _WHITESPACE_RE.match(content, pos).end()
        tag_match = _OMELETTE_TAG_RE.match(content, probe)
        if tag_match is None:
            break
        pos = tag_match.end()
    if pos == start:
        return content
    return content[:start] + b"\n" + content[pos:]


def push_exports(
    transport: DesignTransport,
    *,
    slug: str,
    repo_root: Path,
    export_dir: Path | None = None,
    state_path: Path | None = None,
    prove: bool = False,
    now: Callable[[], datetime] | None = None,
) -> ExportPushResult:
    """CAP-5, Story 5.1/5.2/23.6: push the derived export set back into
    Design after a pull + ``deck-export`` regeneration (``bridge-protocol.md``
    § Export push-back). Requires a prior ``seed`` (``_require_seeded_state``,
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
    not exist there yet -- FR-18). A binary candidate's entry also carries
    ``"encoding": "base64"``; the poster's own text entry never does.

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

    **``--prove`` (Story 23.4, CAP-6).** When ``prove=True``, every file
    that was actually written this run (never a skipped or conflicted one)
    is read back via ``transport.fetch_rendered_bytes`` and compared,
    after ``_strip_serve_harness``, against the exact bytes just sent. A
    match appends that file to the returned ``proven`` tuple and one row to
    the deck README's dated Ledger (``registry.append_push_ledger_row``); a
    mismatch reverts that file's ``export:`` state entry to whatever it was
    before this run (so a retry sees it as still-changed) and is collected
    for ``errors.ReadBackMismatchError``, raised after every other file has
    been given its own chance to prove -- one file's bad read-back never
    stops another's. ``prove=False`` (the default) makes no read-back call
    at all and never touches the README.

    ``state.py`` is updated once, after every file has been attempted, with
    exactly the files that both pushed successfully and (when ``prove`` is
    set) proved byte-identical -- a conflicted or mismatched file's own
    ``export:`` record is left exactly as it was, so a retry sees it as
    still-changed rather than falsely "already pushed". If any file
    conflicted, ``push_exports`` raises ``errors.ExportConflictError``
    naming every conflicted file; if (with no conflicts) any file
    mismatched on read-back, it raises ``errors.ReadBackMismatchError``
    naming every mismatched file -- both after the state write and any
    Ledger append for the rest of the batch have already landed. Otherwise
    it returns ``ExportPushResult``."""
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
    pushed_candidates: dict[str, _ExportCandidate] = {}
    for candidate in to_push:
        if_match = plan.base_etags.get(candidate.filename, _FRESH_ETAG)
        file_entry: dict[str, Any] = {
            "path": candidate.filename,
            "data": candidate.data,
            "if_match": if_match,
        }
        if candidate.binary:
            file_entry["encoding"] = "base64"
        try:
            transport.write_files(
                project_id=existing.project_id,
                files=[file_entry],
                plan_token=plan.plan_token,
            )
        except errors.TransportCallError as exc:
            conflicts.append(f"{candidate.filename} ({exc})")
            continue
        new_etags[f"{_EXPORT_ARTIFACT_PREFIX}{candidate.filename}"] = (
            candidate.local_hash
        )
        pushed.append(candidate.filename)
        pushed_candidates[candidate.filename] = candidate

    proven: list[str] = []
    mismatches: list[str] = []
    ledger_rows: list[tuple[str, int]] = []
    if prove and pushed:
        for filename in pushed:
            candidate = pushed_candidates[filename]
            expected = _candidate_raw_bytes(candidate)
            try:
                raw = transport.fetch_rendered_bytes(
                    project_id=existing.project_id, path=filename
                )
            except errors.TransportCallError:
                # A transient read-back failure (network/HTTP) is not a byte
                # mismatch, but it must be treated identically: the write
                # already landed, so the file cannot be proven this run and
                # its `export:` record must revert exactly like a genuine
                # mismatch, rather than aborting the whole batch or leaking
                # the new hash for a file nothing ever confirmed.
                mismatches.append(filename)
                key = f"{_EXPORT_ARTIFACT_PREFIX}{filename}"
                if key in existing.etags:
                    new_etags[key] = existing.etags[key]
                else:
                    new_etags.pop(key, None)
                continue
            actual = _strip_serve_harness(raw, path=filename)
            if actual != expected:
                mismatches.append(filename)
                key = f"{_EXPORT_ARTIFACT_PREFIX}{filename}"
                if key in existing.etags:
                    new_etags[key] = existing.etags[key]
                else:
                    new_etags.pop(key, None)
                continue
            proven.append(filename)
            ledger_rows.append((filename, len(expected)))

    # The Ledger append runs BEFORE state.write: if it raises (e.g. a disk
    # error), state must stay uncommitted so a retry legitimately
    # re-pushes/re-proves/re-appends a proven file, rather than state
    # already recording it as unchanged while its Ledger row was lost.
    if ledger_rows:
        resolved_now = now or _default_now
        registry.append_push_ledger_row(
            deck_dir / "README.md",
            date=resolved_now().strftime("%Y-%m-%d"),
            rows=ledger_rows,
        )

    # Persist whichever files actually succeeded -- even when some
    # conflicted or (with `--prove`) mismatched on read-back -- so a retry
    # never re-pushes a file that already landed. A conflicted or
    # mismatched file's record is simply absent from (or reverted in)
    # `new_etags`'s delta (still whatever it was before this run), so the
    # next attempt sees it as changed and tries again.
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

    if mismatches:
        raise errors.ReadBackMismatchError(
            f"read-back after push did not match for {len(mismatches)} "
            f"file(s) in {slug!r}: {', '.join(mismatches)} -- refused rather "
            f"than record an unproven push"
        )

    return ExportPushResult(
        slug=slug, pushed=tuple(pushed), skipped=tuple(skipped), proven=tuple(proven)
    )
