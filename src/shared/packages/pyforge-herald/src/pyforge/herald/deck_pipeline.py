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

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from . import errors, registry, state

if TYPE_CHECKING:
    from .transport.base import DesignTransport, ProjectRef

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
