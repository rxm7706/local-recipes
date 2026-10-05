"""``marshal seed adopt``'s verb logic: the FIRST mutating verb composition
in this package -- ``resolve -> detect -> plan -> augment -> confirm ->
apply -> state-write`` (Story 10.6, FR-79/FR-80/FR-81/FR-82/FR-83/FR-84/
FR-87, AD-60).

Until this module, ``cli/seed.py::run_adopt`` was Story 7.1's stub: it
printed "not yet implemented" and returned ``EXIT_OK`` unconditionally, so a
brownfield repo had no way to layer the seed model on without a human
hand-wiring every artifact. This module is that layering: it reuses every
already-landed Epic 9/10 primitive (``detect.inventory.classify``,
``plan.build.build_plan``, ``verbs.preconditions.check_preconditions``,
``verbs.skips``, ``apply.run.run_apply``, ``state.store.write_state``)
rather than re-deriving any of their rules, mirroring ``verbs/check.py``'s
own detect+plan composition style but adding the write side that ``check``
deliberately never touches.

**The FR-83/FR-84 interaction, and how this module resolves it.**
``build_plan`` (Story 9.6, already shipped and heavily tested -- **not
modified by this story**) never emits an ``Action`` for a
``PRESENT_CONFORMANT`` classification, for ANY class -- its own module
docstring says so verbatim: "``PRESENT_CONFORMANT`` and ``PRESENT_LEGACY``
never [produce an Action]". ``detect.inventory.classify`` also takes no
``state`` parameter at all, so it cannot distinguish "already adopted, up to
date" from "never adopted, something unrelated already exists at this
path". FR-83 requires the second case -- for ``copied-managed``/
``generated-derived`` artifacts specifically -- to be CLAIMED (overwritten),
not preserved: a brownfield repo may already carry an unrelated file at a
``generated-derived`` artifact's path, and Genesis must not defer to
whatever was already there. FR-84 simultaneously requires a SECOND adopt on
an unchanged repo to produce an EMPTY plan. These two requirements are
compatible, not contradictory, only if the forced-claim behavior fires
EXACTLY ONCE per artifact -- on first adopt -- and never again once the
artifact is tracked. ``_augment_plan_with_first_claims`` below is that gate:
it adds one ``Action`` (mirroring ``build_plan``'s own ``PRESENT_CONFORMANT``
``Action(...)`` construction shape -- ``current_state=target_state=
ArtifactState.PRESENT_CONFORMANT``, ``chosen_anchor=()`` for a whole-file
class) per entry that is ``PRESENT_CONFORMANT``, whose ``artifact_class`` is
``COPIED_MANAGED`` or ``GENERATED_DERIVED`` (the epics AC's own two named
classes -- ``copied-seeded``/``hybrid-managed-region`` are deliberately
excluded), and whose id has NO record in ``state.managed`` (or ``state is
None``). Once an artifact is claimed, ``state.managed`` carries its record,
this gate no longer fires for it, and ordinary ``build_plan`` behavior (no
``Action`` for ``PRESENT_CONFORMANT``) delivers FR-84's idempotence for
free -- with no further code needed to make that true. The augmentation adds
a matching ``RepoFingerprint.artifact_hashes`` entry for every claimed
artifact too (hashing the file's CURRENT, pre-claim content): omitting this
would make ``apply.run.fingerprint_drift`` see an ``Action`` with no
corresponding hash pair and refuse the whole plan as corrupt before it ever
reached ``commit``.

**The confirm seam.** This package's CLI has zero prior interactive-prompt
precedent -- ``--apply`` without ``--yes`` is the first one, and the epics AC
requires it to never block a test on real stdin. ``confirm`` is therefore a
required, keyword-only ``Callable[[], bool]`` parameter on ``run_adopt``
itself (never defaulted here), mirroring ``verbs.check.run_check``'s own
``manifest=`` test-injection convention one level further: the REAL
``input()``-based implementation is ``cli/seed.py``'s to construct and
supply (that module's own test-injection seam defaults IT to ``None`` and
substitutes the real one), exactly as ``cli/seed.py`` already substitutes
the real packaged manifest when its own ``manifest=`` seam is left ``None``.
``confirm`` is consulted only when ``apply and not yes`` -- ``--yes`` and a
dry-run both skip it entirely, so neither ever touches stdin.

**Wrapping ``engine.copier.materialize`` (the ``commit`` callback) -- and
where it deliberately does NOT wrap it.** ``apply.run.run_apply`` imports no
``engine``/``copier`` at all -- its own module docstring is explicit that
materializing content is entirely the caller-supplied ``commit`` callback's
job. ``_default_commit`` below is that callback, and it dispatches on
``artifact_class``/``entry.id`` to THREE different content sources (Story
11.1 added the third; the original two are otherwise unchanged):

* For a whole-file class (``COPIED_MANAGED``/``COPIED_SEEDED``/
  ``GENERATED_DERIVED`` -- including a first-claim augmented ``Action``,
  which this callback does NOT special-case, since its ``artifact_class`` is
  ordinary either way) whose ``id`` is NOT one of ``derive.adapters.
  ADAPTER_COMPOSITION``'s keys, it renders the FULL seed template tree via
  ``engine.materialize`` with ``MaterializeVerb.COPY``, lazily, on the FIRST
  such call, and reuses that one staged result for every subsequent
  whole-file action in the same run -- a deliberate choice, not a literal
  "materialize once per Action" reading of the epics AC: ``engine.copier.
  materialize``'s own module docstring states plainly that it never targets
  ``dst_path`` directly and always renders into a fresh, unmanaged-by-anyone
  staging directory it leaves on disk on success (staging cleanup ownership
  is ALREADY a documented gap ``apply/run.py`` inherits and does not solve,
  since ``MaterializeResult`` exposes no staging root); calling it once per
  ``Action`` in a plan with N whole-file actions would multiply that leak by
  N for a render whose ``data=`` answers do not change within one run. The
  callback then locates the staged file whose relative path TAILS
  ``action.target_path`` and writes its bytes via ``fs.write``.
* For a whole-file entry whose ``id`` IS one of ``derive.adapters.
  ADAPTER_COMPOSITION``'s keys (``cursor-rules``/``gemini-md``/
  ``copilot-instructions``, Story 11.1), content comes from ``derive.
  adapters.render_adapter(entry.id, template_path=template_path)`` instead,
  and ``_materialized()`` is never called for that action at all. See
  ``derive.adapters``'s own module docstring for why: routing these three
  through ``engine.copier.materialize`` was tried against the real packaged
  manifest and fails immediately (``TemplateBoundaryError`` -- the packaged
  tree's own ``manifest.yaml``/``__init__.py``/region fragments all get
  staged too, and none of them corresponds to a manifest entry's ``path``).
  The membership check (`entry.id in derive_adapters.ADAPTER_COMPOSITION`)
  is data-driven, not a per-id branch: a fifth adapter reaches this same
  branch with no change here, once it has a row in that table.
* For a ``HYBRID_MANAGED_REGION`` action, the region's body is read
  DIRECTLY off the packaged (or injected) template root's
  ``files/<region-name>.*`` fragment -- ``_region_body_from_template`` --
  and NEVER routed through ``materialize()`` at all. This is a deliberate
  departure from a literal "commit always wraps materialize" reading,
  reached by direct inspection of the packaged ``seed/templates/files/``
  directory during this story's own development: its six fragments
  (``tiers.md.j2``, ``portability-contract.md.j2``,
  ``dream-first-workflow.md.j2``, ``bmad-multiproject.md.j2``,
  ``model-ignores.gitignore.j2``, ``model-badge.md.j2`` -- one per unique
  region NAME, shared across every manifest entry that declares it) all
  carry a literal ``.j2`` suffix, which is NOT Copier's own default
  ``_templates_suffix`` (``.jinja`` -- confirmed against ``test_seed_
  engine_copier.py``'s own fixture convention, which uses ``.jinja``
  precisely so no ``copier.yml`` override is needed), and the packaged
  ``seed/templates/`` tree carries no ``copier.yml`` to redefine that
  default. Fed through ``copier.run_copy`` as-is, every one of these six
  files would be copied VERBATIM, filename and ``.j2`` suffix both intact,
  unrendered -- concrete evidence that they were never meant to be staged
  and boundary-reconciled through Copier at all. Confirmed further by
  reading every one of the six: none contains a single ``{{`` -- static
  content, not a Jinja template in need of rendering. Reading them directly
  (mirroring ``engine/copier.py``'s own ``resources.files(...)``/
  ``resources.as_file(...)`` idiom for a packaged resource read outside the
  Copier pipeline) is therefore not merely simpler, it is the reading that
  makes the packaged tree's own existing shape make sense. It has one more
  concrete payoff: a hybrid-region insertion (``insert_region``) into each
  pending region, re-reading the target's text fresh between successive
  regions in the SAME action (``regions/apply.py``'s own documented safe
  pattern: "detect -> apply ONE region -> re-detect -> apply the next",
  never parse-once-apply-many). Story 11.2 adds ONE exception to "every
  hybrid region reads its static fragment": the ``projects-table`` region
  (``projects-index``'s only region, ``_bmad-output/PROJECTS.md``) is
  repo-computed, not packaged-static -- its body comes from ``derive.
  projects_index.derive_projects_table(repo_root / "_bmad-output" /
  "projects")`` instead, a data-driven check on ``region_name`` (not on
  ``entry.id``, since a region name is what identifies the fragment/body a
  hybrid entry needs) reached BEFORE ``_region_body_from_template`` is ever
  called for that one region. This is the SAME class of gap Story 11.1
  closed for the three whole-file agent-adapter ids, one region later: the
  packaged template tree ships no static fragment for ``projects-table``
  at all (there is none to ship -- its content depends on the ADOPTING
  repo's own live project set, not on shipped prose), and a prior
  implementation attempt at this story shipped a static placeholder
  fragment purely to satisfy an unrelated conformance test, which would
  have shipped as PROJECTS.md's real, WRONG content on every real
  ``adopt``/``update`` run against a repo with actual projects -- caught
  before landing, and why this dispatch exists here rather than as a
  static fragment under ``templates/files/``. Every OTHER hybrid region
  (``tiers``, ``portability-contract``, ``dream-first-workflow``,
  ``bmad-multiproject``, ``model-ignores``, ``model-badge``) is untouched
  and still reads its packaged fragment via ``_region_body_from_template``
  exactly as before.

**Known, inherited limitations this story does not close** (named rather
than silently worked around, per this package's convention): (1) [Story
11.1 CLOSED THIS for the three whole-file agent-adapter entries --
``cursor-rules``/``gemini-md``/``copilot-instructions`` -- via ``derive.
adapters.render_adapter``; see that module's own docstring and the third
``_default_commit`` dispatch branch above.] The packaged ``seed/templates/``
tree otherwise still ships REGION-body fragments only -- no whole-file
content exists yet for any OTHER ``copied-managed``/``copied-seeded``/
``generated-derived`` entry (there is no ``copier.yml`` at all, and every
file in the tree besides the region fragments and the three new wrapper
templates -- ``manifest.yaml``, ``__init__.py`` -- would themselves fail
``materialize()``'s own manifest-boundary reconciliation if staged), so a
real ``--apply`` against the packaged manifest can only succeed, for those
OTHER entries, once a later template-authoring story supplies content for
them; this module's own tests inject a synthetic ``template_path`` (a
documented test seam, ``run_adopt(..., template_path=...)``) to exercise the
generic whole-file path end to end without depending on that future
content, and rely on the REAL packaged region fragments (``template_path=
None``) for the hybrid-region path, which needs no such workaround (see
above). (2) A directory-shaped artifact (a manifest
``path`` ending in ``/``, e.g. ``docs/dreams/``) is out of this story's
tested scope: ``fs.write`` has no directory-creation primitive, and no
I/O-matrix row names this case. [Story 86.1 pinned what such an entry
MEANS -- create-if-missing, with every entry beneath it governed by its own
class (``ManifestEntry.is_directory``, ``model.artifact.DIRECTORY_BEHAVIOR``)
-- so a directory that already exists is never first-claimed here and never
handed to rung 6; materializing an ABSENT one is still this limitation.]
(3) A ``copied-seeded``/``generated-derived`` entry whose ``path`` still
carries an unrendered ``{{ slug }}``
placeholder (e.g. ``project-config``, ``deck-scaffolding`` -- both
``applies_to: both``) has no ``--slug`` flag to resolve it with here (that
belongs to ``seed init``, Story 10.7) -- ``classify()`` treats the
placeholder as a literal path segment, which is a PRE-EXISTING gap in
``detect.inventory``/``plan.build`` (both already shipped, neither touched
by this story), not one this module introduces or is scoped to close.

**Filtering the manifest by ``applies_to`` (AD-55).** ``AppliesTo`` has three
members -- ``init``/``adopt``/``both`` -- and the packaged manifest already
uses all three (``starter-dream``/``specs-readme`` are ``init``-only,
``specs-dir-legacy`` is ``adopt``-only). No prior consumer of ``Manifest``
has ever filtered by this field (``check.py`` runs the full, unfiltered
manifest against every entry, since a read-only conformance report has no
reason to hide an ``init``-only entry's drift). A MUTATING ``adopt`` run
does: an ``init``-only entry like ``starter-dream`` (``docs/dreams/
{{ slug }}.md``) has no repo-relative target ``adopt`` could ever
materialize correctly (there is no ``--slug`` here), and leaving it in scope
would plan -- and, under ``--apply``, attempt to write -- a literal,
un-rendered ``{{ slug }}.md`` file. ``_manifest_for_adopt`` below is a
one-line, one-time filter to ``applies_to in (ADOPT, BOTH)`` before
``classify``/``build_plan`` ever see the manifest, applied identically on
every call (an entry's ``applies_to`` is a manifest-authored constant, so
the filtered view is the same set on every re-adopt).

**Ordering, and why it is this order** (the Always bullets' own sequencing,
restated as code): resolve (``_manifest_for_adopt``) -> detect (``classify``)
-> record derived opt-outs in memory (``_state_with_opt_outs``, Story 82.13:
a region whose markers were deleted is opted out per FR-112, and the plan and
rung 6 must read that ONE answer, so it is recorded BEFORE the plan is built;
the recorded state is written only where state is written today, below) ->
plan (``build_plan``) -> augment (``_augment_plan_with_first_claims``,
FR-83) -> skip (``skips.apply_skips``) -> preconditions
(``verbs.preconditions.check_preconditions``, BEFORE any write, ``dry_run=
not apply``) -> write ``.marshal/plan.json`` (ALWAYS, both dry-run and
``--apply`` -- FR-82 draws its dry-run contrast against ``check``, which
never writes anything at all, not against ``--apply``) -> return early for a
dry-run -> confirm (only when ``apply and not yes``; a decline returns
without ever calling ``run_apply``) -> refuse on unexpected dirt
(``_unexpected_dirt_since_plan_write``, review finding -- catches an
operator's UNRELATED edit made during the confirm pause, which
``fingerprint_drift``'s own un-selective ``dirty`` re-check cannot) -> refresh
the fingerprint's ``dirty`` flag to the true, unrestricted current value
(``_repo_is_dirty_now``, so ``fingerprint_drift``'s comparison agrees rather
than false-refusing on this run's own known ``plan.json`` write) ->
``apply.run.run_apply`` -> state-write, gated on ``plan.actions``
(post-augmentation, post-skip) being non-empty -- FR-84's "writes nothing" is
read LITERALLY: an empty plan skips the state write entirely, no
``last_update`` refresh, matching ``run_apply``'s own "an empty plan is a
no-op" contract (10.3's AC) one layer up.

**Import surface.** ``derive.adapters`` (the MODULE, imported as
``derive_adapters`` -- Story 11.1's ``ADAPTER_COMPOSITION``/``render_adapter``
for the three whole-file agent-adapter ids), ``derive.projects_index`` (the
MODULE, imported as ``derive_projects_index`` -- Story 11.2's
``derive_projects_table`` for the ``projects-table`` hybrid region),
``detect.inventory``
(``classify``, ``ArtifactState``, ``Inventory``, ``effective_never_write``,
``writable_exemptions``), ``plan.build`` (``build_plan``,
``write_plan``, ``default_plan_path`` -- never modifies ``build_plan``
itself), ``plan.types`` (``Action``, ``Plan``), ``apply.run`` (``run_apply``,
``CommitAction``, ``ApplyResult``), ``verbs.preconditions``
(``check_preconditions``, ``ManagedRecord``), ``verbs.skips``
(``apply_skips``, ``managed_after_skips``), ``state`` (``read_state``,
``write_state``, ``SeedState``, ``ManagedArtifact``, ``LegacyArtifact``,
``RegionSpanRecord``, ``record_opt_out``, ``utc_timestamp``,
``seed_model_version``),
``detect.hashes`` (``hash_content``, ``region_body_text``), ``detect.optout``
(``classify_regions``, ``opt_outs_to_record``, ``opted_out_regions``, Story
82.13), ``regions.parse``
(``parse_regions``), ``regions.apply`` (``insert_region``), ``engine``
(``materialize``, ``MaterializeRequest``, ``MaterializeVerb``,
``MaterializeResult``), ``model.manifest`` (``AppliesTo``, ``ArtifactClass``,
``Manifest``, ``ManifestEntry``), ``model.version`` (``ModelVersion``),
``errors`` (``InternalError``, for the "materialize produced no staged
content" backstop and for a handful of other defensive guards named in
their own docstrings; ``PreconditionFailure``, for
``_unexpected_dirt_since_plan_write`` and a launched-git-process failure),
``fs`` (the MODULE, matching ``apply/run.py``'s own convention, so a test
can monkeypatch ``adopt.fs.write``), and ``pyforge.core.process``
(``PosixProcess``/``ProcessError`` -- a git seam for two narrow,
locally-owned purposes -- see ``_repo_is_dirty_now``'s and
``_unexpected_dirt_since_plan_write``'s own docstrings). No ``seed.cli``
import (the architecture's no-upward-imports rule)."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

from pyforge.core.process import PosixProcess, ProcessError

from .. import fs
from ..apply.run import ApplyResult, CommitAction, run_apply
from ..derive import adapters as derive_adapters
from ..derive import projects_index as derive_projects_index
from ..detect.findings import Finding
from ..detect.hashes import hash_content, region_body_text
from ..detect.inventory import (
    ArtifactState,
    Inventory,
    classify,
    effective_never_write,
    escape_findings,
    writable_exemptions,
)
from ..detect.optout import classify_regions, opt_outs_to_record, opted_out_regions
from ..engine import MaterializeRequest, MaterializeResult, MaterializeVerb, materialize
from ..errors import InternalError, PreconditionFailure
from ..model.manifest import AppliesTo, ArtifactClass, Manifest, ManifestEntry, RequiredIn, render_slug_paths
from ..model.version import ModelVersion
from ..plan.build import build_plan, default_plan_path, write_plan
from ..plan.types import Action, Plan
from ..regions.apply import insert_region
from ..regions.parse import RegionSpan, parse_regions
from ..state import (
    LegacyArtifact,
    ManagedArtifact,
    RegionSpanRecord,
    SeedState,
    read_state,
    record_opt_out,
    seed_model_version,
    utc_timestamp,
    write_state,
)
from .preconditions import ManagedRecord, check_preconditions
from .skips import apply_skips, managed_after_skips, with_recorded_skips

# The classes FR-83's first-claim augmentation ever fires for -- the epics
# AC's own two named classes. ``copied-seeded`` and ``hybrid-managed-region``
# are deliberately excluded: a hybrid entry's "already conformant" state can
# only mean every declared region is already present (there is nothing left
# to claim), and ``copied-seeded``'s whole premise ("materialized once, then
# repo-owned forever") is the opposite of "claim and overwrite".
_FIRST_CLAIM_CLASSES = frozenset({ArtifactClass.COPIED_MANAGED, ArtifactClass.GENERATED_DERIVED})

# The exact phrase every first-claim `Action.rationale` embeds (review
# finding) -- exported so `cli/seed.py::_render_plan_text` can flag a
# first-claim action distinctly in the printed plan (it overwrites a
# pre-existing, unrelated file, unlike an ordinary "create" action) without
# either module re-deriving the other's classification rule. A shared,
# named constant, not two independently-typed copies of the same string.
FIRST_CLAIM_MARKER = "first-claim, tool-owned class"


@dataclass(frozen=True)
class AdoptResult:
    """``run_adopt``'s whole return value -- a plain, inspectable shape,
    never an exception (this module raises nothing of its own; every
    ``SeedError`` a caller sees comes from a primitive it composes --
    ``check_preconditions``, ``read_state`` -- and propagates unchanged).

    ``plan`` is the FINAL plan actually considered -- augmented (FR-83) and
    skip-filtered -- the same one written to ``.marshal/plan.json``, so a
    caller rendering this result never has to reconstruct what was written.

    ``applied`` is ``None`` for a dry-run OR a declined confirmation (apply
    never ran), and ``ApplyResult.applied`` (possibly ``()`` for a no-op
    empty-plan apply) once ``run_apply`` actually returns. ``declined`` is
    ``True`` only when ``--apply`` was requested, ``--yes`` was not, and
    ``confirm()`` returned ``False`` -- distinguishing "nothing was applied
    because the operator said no" from "nothing was applied because this was
    a dry-run", which a renderer needs different words for.

    ``escape_findings`` (Story 82.11) names every manifest entry whose path
    resolves outside the repository: the plan holds no action for it, every
    other action applies, and a renderer reports it here rather than the run
    refusing as a whole."""

    plan: Plan
    applied: tuple[str, ...] | None
    declined: bool
    escape_findings: tuple[Finding, ...] = ()


# Query-style git call (never a checkout/push) -- the identical value
# `plan/build.py::_GIT_TIMEOUT_S`/`verbs/preconditions.py::_GIT_TIMEOUT_S`
# use for the identical class of call, so a hung `git` fails fast here too.
_GIT_TIMEOUT_S = 30.0


def _git_status_porcelain(repo_root: Path, *extra_pathspec: str) -> str | None:
    """The raw ``git status --porcelain --untracked-files=normal`` output
    against ``repo_root``, optionally restricted by ``extra_pathspec``
    (appended after ``--``), or ``None`` if the process could not even be
    launched (missing ``git``, or the call timing out) -- the ONE thing
    both ``_repo_is_dirty_now`` and ``_unexpected_dirt_since_plan_write``
    funnel through, so the two never drift on command shape or on how a
    launch failure is handled."""
    try:
        result = PosixProcess().run(
            [
                "git",
                "status",
                "--porcelain",
                "--untracked-files=normal",
                *(("--", *extra_pathspec) if extra_pathspec else ()),
            ],
            cwd=repo_root,
            timeout_s=_GIT_TIMEOUT_S,
        )
    except ProcessError as exc:
        raise PreconditionFailure(
            f"could not determine whether {repo_root} is a clean git worktree: {exc}",
            remedy="ensure git is installed and on PATH, and that the target is a git repository",
        ) from exc
    if result.returncode != 0:
        return None
    return result.stdout


def _repo_is_dirty_now(repo_root: Path) -> bool:
    """A FRESH, UNRESTRICTED ``True`` iff ``git status --porcelain
    --untracked-files=normal`` produces any output, OR the git call itself
    could not be launched (cannot confirm clean -- the conservative
    direction) -- byte-for-byte the same command and the same
    non-zero-means-dirty rule as ``plan.build._repo_is_dirty`` (which
    ``apply.run.fingerprint_drift`` itself calls) and
    ``verbs.preconditions._is_dirty``.

    **Why unrestricted, deliberately, even though `write_plan` has already
    dirtied the repo (review finding, confirmed by execution).**
    `fingerprint_drift` does NOT consult anything this module computes for
    its OWN `dirty` comparison -- it always re-derives a FRESH, UNRESTRICTED
    reading via its own private `_repo_is_dirty` and compares THAT against
    whatever `RepoFingerprint.dirty` the `Plan` carries. An earlier revision
    of this function tried to exclude `.marshal/` (the self-inflicted
    `plan.json` write) so the STAMPED value would read `False`, reasoning
    that `False` was the "true", narrow answer. That produced the opposite
    of the intended effect: `fingerprint_drift`'s own unrestricted re-check
    still (correctly) sees `plan.json` and reads `True`, so a stamped
    `False` and a re-derived `True` now DISAGREE, and EVERY `--apply` on a
    never-before-adopted repo failed as `stale-plan` unconditionally --
    confirmed by running the full suite. `fingerprint_drift`'s comparison
    can only ever be satisfied by supplying it the SAME unrestricted signal
    it will independently recompute a few lines later; there is no
    parameter or seam on `fingerprint_drift` this module may pass a
    restriction through (out of scope to add one -- `plan/build.py` is not
    modified by this story). This function's ONLY job is to make
    `RepoFingerprint.dirty` describe the repo TRUTHFULLY at the instant
    `run_apply` is about to re-check it (the repo genuinely IS dirty, due
    to `plan.json`) -- never `git_head`/`artifact_hashes`/`actions`/
    `skipped`, which stay exactly what was written to `plan.json` and
    reviewed. The REAL protection against an operator dirtying the repo
    with something UNRELATED during the confirm pause is a separate,
    explicit check this module DOES fully control --
    `_unexpected_dirt_since_plan_write`, below -- not a trick played on
    this value."""
    output = _git_status_porcelain(repo_root)
    return output is None or bool(output)


def _unexpected_dirt_since_plan_write(repo_root: Path) -> None:
    """Raises ``PreconditionFailure`` if anything OTHER than this module's
    own known, self-inflicted ``.marshal/`` write is dirty right now.

    This is the mechanism that actually delivers what a prior revision of
    ``_repo_is_dirty_now`` claimed to (review finding) -- since
    ``fingerprint_drift``'s own ``dirty`` comparison cannot be made
    selective (see ``_repo_is_dirty_now``'s own docstring), the ONLY way to
    catch "an operator edited something unrelated while deciding whether to
    confirm" is a dedicated check this module owns end to end, with its own
    clear, actionable message -- rather than relying on ``fingerprint_
    drift``'s generic ``stale-plan`` wording (which would ALSO fire for the
    self-inflicted ``plan.json`` write alone, giving no way to tell the two
    causes apart). Excludes ``.marshal/`` via a git pathspec
    (``':!.marshal/'``): the ONE thing this module is known to have written
    before this check runs (``write_plan``, ALWAYS, before any confirm
    prompt -- module docstring's "Ordering" section; state is written only
    AFTER a successful ``run_apply`` returns, so it is never yet present
    here). ``--untracked-files=normal`` reports a wholly new untracked
    directory as itself (``?? .marshal/``), never expanding into individual
    file contents, so excluding the directory is exactly equivalent to
    excluding ``plan.json`` for every path reachable today. Called once,
    immediately before ``run_apply`` (after ``confirm()`` has already
    returned, whether via a real prompt or ``--yes``), so it covers the
    entire window since ``check_preconditions``'s own dirty rung last
    confirmed the repo clean."""
    output = _git_status_porcelain(repo_root, ".", ":!.marshal/")
    if output is None or output:
        raise PreconditionFailure(
            "dirty-worktree: the repository changed since it was last confirmed clean"
            " (excluding this run's own .marshal/plan.json write) -- an operator or"
            " another process modified it while adopt was awaiting confirmation",
            remedy="re-run marshal seed adopt and review the fresh plan before applying it",
        )


def _manifest_for_adopt(
    manifest: Manifest,
    slug: str | None = None,
    *,
    in_loop_home: bool | None = None,
) -> Manifest:
    """``manifest``, scoped to the entries this verb ever touches: ``applies_
    to in (ADOPT, BOTH)``, with Story 70.1's slug rendering and loop-home
    scope (Story 86.2) applied before ``classify``/``build_plan`` see it."""
    kept: list[ManifestEntry] = []
    for entry in manifest.entries:
        if entry.applies_to not in (AppliesTo.ADOPT, AppliesTo.BOTH):
            continue
        if entry.required_in is RequiredIn.LOOP_HOME and in_loop_home is False:
            continue
        if slug is None and entry.is_slug_templated:
            continue
        kept.append(entry)
    filtered = Manifest(
        model_version=manifest.model_version,
        never_write=manifest.never_write,
        entries=tuple(kept),
    )
    if slug:
        return render_slug_paths(filtered, slug)
    return filtered


def _read_text_or_blank(target: Path) -> str:
    """The UTF-8 text at ``target``, or ``""`` for anything that is not a
    readable regular file -- mirrors ``verbs/check.py::_read_text_or_blank``'s
    identical degrade rule verbatim (that function is private to a sibling
    module; a small, deliberate duplication of it beats an import across a
    module boundary, matching this package's established stance)."""
    if not target.is_file():
        return ""
    try:
        return target.read_text(encoding="utf-8")
    except OSError, UnicodeDecodeError:
        return ""


def _augment_plan_with_first_claims(
    plan: Plan, inventory: Inventory, manifest: Manifest, state: SeedState | None
) -> Plan:
    """FR-83's own resolution (see the module docstring's opening section):
    one ``Action`` per entry that is ``PRESENT_CONFORMANT``, whose
    ``artifact_class`` is ``COPIED_MANAGED`` or ``GENERATED_DERIVED``, that
    is not a directory entry (create-if-missing, Story 86.1), and whose id
    has no record in ``state.managed`` (or ``state is None``).
    Returns ``plan`` UNCHANGED (the identical object, matching ``skips.
    apply_skips``'s own "nothing moved, return the input" convention) when
    no entry qualifies -- the overwhelmingly common case on a re-adopt,
    where FR-84's idempotence must cost nothing extra."""
    claimed_by_id = {record.id: record for record in state.managed} if state is not None else {}
    entries_by_id = {entry.id: entry for entry in manifest.entries}
    first_claims: list[Action] = []
    claim_hashes: list[tuple[str, str]] = []
    for classification in inventory.classifications:
        if classification.state is not ArtifactState.PRESENT_CONFORMANT:
            continue
        entry = entries_by_id[classification.entry_id]
        if entry.artifact_class not in _FIRST_CLAIM_CLASSES:
            continue
        if entry.is_directory:
            # A directory entry is create-if-missing (Story 86.1,
            # DW-FU-7-5-2): one that already exists is what the entry asks
            # for, so there is nothing to claim -- and "claim and overwrite"
            # a directory reached rung 5 as `directory-target`, refusing the
            # whole adopt of any repo that already had, say, `docs/dreams/`.
            continue
        claimed_record = claimed_by_id.get(entry.id)
        if claimed_record is not None and claimed_record.path == entry.path:
            # Already claimed AT THIS PATH -- the common re-adopt case.
            continue
        # Either never claimed, or claimed at a DIFFERENT path (review
        # finding, mirroring `detect.optout._claims_region`'s and
        # `verbs.check`'s own already-fixed identical trap: AD-55 makes
        # `id`, not `path`, the stable address, so trusting an id-only
        # match here would permanently orphan an artifact whose manifest
        # path has since moved -- it would never be re-claimed at its new
        # path, and no `build_plan` Action exists for it either
        # (`PRESENT_CONFORMANT` never produces one). Falling through and
        # re-claiming at the CURRENT path is the conservative direction:
        # worst case a second `ManagedArtifact` record is written for the
        # same id at its new path, which `_build_state_after_apply`'s own
        # `touched_ids` filter already drops the stale old-path record for
        # (never two records for the same id survive an apply).
        first_claims.append(
            Action(
                artifact_id=entry.id,
                artifact_class=entry.artifact_class,
                current_state=ArtifactState.PRESENT_CONFORMANT,
                target_state=ArtifactState.PRESENT_CONFORMANT,
                target_path=entry.path,
                chosen_anchor=(),
                rationale=(
                    f"{entry.path!r} already exists but is not yet a tool-owned"
                    f" {entry.artifact_class.value} artifact ({FIRST_CLAIM_MARKER});"
                    " adopt claims and overwrites it"
                ),
            )
        )
        claim_hashes.append((entry.id, hash_content(_read_text_or_blank(inventory.repo_root / entry.path))))
    if not first_claims:
        return plan
    merged_actions = tuple(sorted((*plan.actions, *first_claims), key=lambda action: action.artifact_id))
    # A matching `artifact_hashes` pair per claim is not optional (module
    # docstring): `apply.run.fingerprint_drift` cross-checks `actions`
    # against `artifact_hashes` in BOTH directions and refuses the whole
    # plan as corrupt if either side carries an orphan -- omitting this
    # would make every FR-83 claim unappliable.
    merged_hashes = tuple(sorted((*plan.repo_fingerprint.artifact_hashes, *claim_hashes), key=lambda pair: pair[0]))
    fingerprint = dataclasses.replace(plan.repo_fingerprint, artifact_hashes=merged_hashes)
    return dataclasses.replace(plan, actions=merged_actions, repo_fingerprint=fingerprint)


def _managed_records(state: SeedState | None, manifest: Manifest) -> tuple[ManagedRecord, ...]:
    """``state.managed`` translated into ``verbs.preconditions.ManagedRecord``
    -- rung 6's own input shape -- for every record whose manifest entry
    still exists and, for a region-bearing record, still carries a
    ``format`` to parse its region with. A record whose entry has since
    been retired or reclassified away from ``hybrid-managed-region`` is
    EXCLUDED rather than passed through with a null ``region_format``
    (which ``ManagedRecord.__post_init__`` refuses outright): the identical
    "stale record shape" case ``verbs/check.py``'s own module docstring
    already names and defers to a future migration story to reconcile --
    this module detects nothing and repairs nothing either, it only must
    not crash building rung 6's input. A record whose entry is a DIRECTORY
    (``ManifestEntry.is_directory``) is excluded too: a directory carries no
    content of its own to compare (Story 86.1)."""
    if state is None:
        return ()
    entries_by_id = {entry.id: entry for entry in manifest.entries}
    records: list[ManagedRecord] = []
    for artifact in state.managed:
        entry = entries_by_id.get(artifact.id)
        if entry is not None and entry.is_directory:
            # A directory has no content of its own to attest: what sits in it
            # belongs to the entries beneath it, each with its own record
            # (Story 86.1, DW-FU-7-5-2). Handed to rung 6 it read as an
            # unreadable file and refused the run.
            continue
        if artifact.inserted_region_spans:
            if entry is None or entry.format is None:
                continue
            records.append(
                ManagedRecord(
                    artifact_id=artifact.id,
                    path=artifact.path,
                    # One pair per recorded span, each against its OWN hash
                    # (Story 82.13): rung 6 compares every region body to the
                    # value state recorded for that region, so a multi-region
                    # artifact no longer reports its siblings as "never
                    # recorded".
                    region_shas=tuple((span.name, span.body_sha) for span in artifact.inserted_region_spans),
                    region_format=entry.format,
                )
            )
        else:
            records.append(ManagedRecord(artifact_id=artifact.id, path=artifact.path, body_sha=artifact.body_sha))
    return tuple(records)


def _state_with_opt_outs(
    manifest: Manifest, state: SeedState | None, repo_root: Path, escaping_ids: set[str]
) -> tuple[SeedState | None, frozenset[tuple[str, str]]]:
    """``state`` with every DERIVED opt-out recorded in memory, and every
    ``(artifact_id, region)`` the repository has opted out of -- recorded or
    derived -- as pairs (Story 82.13, ``DW-FU-8-5-5``/``DW-FU-8-5-6``).

    This is ``detect/optout.py``'s sequencing contract, applied: a region whose
    markers the maintainer deleted is only a DERIVED opt-out until something
    records it, and ``build_plan`` suppresses insertion on the RECORDED keys
    alone, so a verb that plans first re-inserts the region the operator left
    on purpose (FR-112). The run therefore records every derived pair, via
    ``opt_outs_to_record`` and ``record_opt_out``, BEFORE it plans, and hands
    ONE answer to both consumers -- ``frozenset(state.opted_out)`` of the
    returned state to ``build_plan`` and the returned pairs to
    ``check_preconditions``' rung 6 -- so the plan and the gate cannot disagree.

    Nothing is written here. The returned state is in memory; the run persists
    it exactly where it persists state today (after a non-empty apply), and a
    dry run, a declined run and an empty-plan run write nothing.

    Only HYBRID entries have regions, and an entry in ``escaping_ids`` is not
    read (its target resolves outside the repo and the run refuses to touch
    it); each file is read with this module's own ``_read_text_or_blank``, so an
    absent or unreadable one is ``""`` and derives nothing. A never-adopted
    repo (``state is None``) has no claim to derive from and no opt-out
    recorded, so it reads nothing and records nothing. ``detect.optout`` does
    the classification, so this carries no second spelling of either source."""
    if state is None:
        return None, frozenset()
    hybrids = tuple(
        (entry, _read_text_or_blank(repo_root / entry.path))
        for entry in manifest.entries
        if entry.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION and entry.id not in escaping_ids
    )
    for entry, text in hybrids:
        for artifact_id, region in opt_outs_to_record(classify_regions(entry, text, state), state):
            state = record_opt_out(state, artifact_id, region)
    return state, opted_out_regions(hybrids, state)


def _merge_agents(existing: tuple[str, ...], requested: Sequence[str]) -> tuple[str, ...]:
    """The de-duplicated UNION of ``existing`` (``state.agents``, or ``()``
    on a first adopt) and ``requested`` (this run's ``--agents``), in
    APPEND order -- ``existing`` first, then any of ``requested`` not
    already present, in the order given. Never a replace: FR-116's own
    "idempotent union... never a silent replace that would drop a
    previously requested agent" (module docstring)."""
    merged = list(existing)
    for agent in requested:
        if agent not in merged:
            merged.append(agent)
    return tuple(merged)


def _staged_bytes_for(staged_paths: Sequence[Path], target_path: str) -> bytes:
    """The bytes of whichever ``staged_paths`` entry's relative path TAILS
    ``target_path`` -- e.g. a staged ``.../stage/scripts/bmad-switch``
    satisfies ``target_path == "scripts/bmad-switch"``. Raises
    ``InternalError`` (a broken template, not a problem with the target
    repo) naming the artifact when nothing matches -- see the module
    docstring's "known, inherited limitations" for when this legitimately
    fires against the packaged (currently whole-file-content-free)
    template tree. Also raises ``InternalError``, naming every ambiguous
    candidate, when MORE THAN ONE staged path tails ``target_path`` (review
    finding): silently picking the first match would contradict this
    package's own "ambiguity is refused loudly, never silently resolved"
    convention (duplicate manifest ids, duplicate hashed fingerprint
    entries, and duplicate managed regions all raise elsewhere)."""
    target_parts = Path(target_path).parts
    matches = [candidate for candidate in staged_paths if candidate.parts[-len(target_parts) :] == target_parts]
    if not matches:
        raise InternalError(
            f"materialize() produced no staged content for {target_path!r}",
            remedy=(
                "verify the seed template tree provides content at this path -- this is a"
                " broken template installation, not a problem with the repository being"
                " adopted"
            ),
        )
    if len(matches) > 1:
        raise InternalError(
            f"materialize() produced {len(matches)} staged candidates for {target_path!r}: "
            f"{[str(candidate) for candidate in matches]!r}",
            remedy=(
                "the seed template tree stages more than one file at this relative path --"
                " this is a broken template installation (ambiguous content), not a problem"
                " with the repository being adopted"
            ),
        )
    return matches[0].read_bytes()


def _region_body_from_template(template_path: Path | str | None, region_name: str) -> str:
    """The text of ``<template root>/files/<region_name>.*`` -- a region's
    body content, read DIRECTLY off disk (or the packaged resource, when
    ``template_path`` is ``None``) rather than routed through ``engine.
    copier.materialize`` at all. See the module docstring's own paragraph
    on why: the packaged fragments carry a literal ``.j2`` suffix, which is
    NOT Copier's own default ``_templates_suffix`` (``.jinja``, confirmed
    against ``test_seed_engine_copier.py``'s own fixture convention) and
    the packaged ``seed/templates/`` tree carries no ``copier.yml`` to
    override that default -- concrete evidence that these six fragments
    were never meant to be staged and reconciled through ``copier.run_copy``
    at all, and every one of them is verified (during this story's own
    development) to contain no ``{{`` -- static content, not a Jinja
    template in need of rendering. Mirrors ``engine/copier.py``'s own
    ``resources.files(...)``/``resources.as_file(...)`` idiom for reading a
    packaged resource outside the Copier pipeline (that module's
    ``_load_packaged_manifest``), duplicated rather than imported -- the
    same "small deliberate duplication beats reaching into a neighbour's
    private helper" trade this package makes elsewhere.

    Raises ``InternalError`` (a broken template installation, not a problem
    with the repository being adopted) naming the region when no
    ``files/<region_name>.*`` fragment exists under the resolved root."""
    if template_path is None:
        files_root = resources.files("pyforge.marshal.seed.templates") / "files"
        with resources.as_file(files_root) as real_files_dir:
            return _read_region_fragment(real_files_dir, region_name)
    return _read_region_fragment(Path(template_path) / "files", region_name)


def _read_region_fragment(files_dir: Path, region_name: str) -> str:
    """The one filesystem read both branches of ``_region_body_from_template``
    funnel through -- tolerant of the ``.j2`` suffix (stripped) and of the
    fragment's own extension (``.md``/``.gitignore``/...), since only the
    NAME half before the first ``.`` identifies the region. Raises
    ``InternalError``, naming every candidate, when MORE THAN ONE file
    under ``files_dir`` matches the same region name (review finding --
    matches ``_staged_bytes_for``'s identical "refuse ambiguity loudly"
    fix, for the same reason).

    Also raises ``InternalError`` if the fragment's own text contains
    ``{{`` (review finding): this module's whole justification for reading
    region bodies directly, bypassing ``engine.copier.materialize``
    entirely, rests on a POINT-IN-TIME audit that today's six packaged
    fragments contain no Jinja syntax (see ``_region_body_from_template``'s
    own docstring). That audit is not otherwise enforced anywhere -- a
    future template-authoring story could add a fragment containing
    ``{{ mode }}``/``{{ agents }}`` (this module already builds exactly
    such an ``answers`` dict for the whole-file path, just never threads it
    into this one) and, without this guard, its literal, un-rendered
    ``{{ ... }}`` text would be spliced silently into a real repo file --
    wrong output a human reviewer might not notice in a diff. This
    converts that future silent-wrong-output regression into an immediate,
    loud, actionable failure at read time instead."""
    if files_dir.is_dir():
        matches = [
            candidate
            for candidate in sorted(files_dir.iterdir())
            if candidate.is_file() and candidate.name.removesuffix(".j2").split(".", 1)[0] == region_name
        ]
        if len(matches) > 1:
            raise InternalError(
                f"{len(matches)} files/{region_name}.*.j2 region-body fragments found under"
                f" {files_dir}: {[candidate.name for candidate in matches]!r}",
                remedy=(
                    "the seed template tree ships more than one fragment for this region"
                    " name -- this is a broken template installation (ambiguous content),"
                    " not a problem with the repository being adopted"
                ),
            )
        if matches:
            text = matches[0].read_text(encoding="utf-8")
            if "{{" in text:
                raise InternalError(
                    f"files/{region_name}.*.j2 region-body fragment contains Jinja syntax"
                    " ('{{'), but region bodies are read directly and never rendered",
                    remedy=(
                        "either remove the Jinja syntax from this fragment, or route this"
                        " region's content through engine.copier.materialize instead of"
                        " _region_body_from_template -- this is a broken template"
                        " installation, not a problem with the repository being adopted"
                    ),
                )
            return text
    raise InternalError(
        f"no files/{region_name}.*.j2 region-body fragment found under {files_dir}",
        remedy=(
            "verify the seed template tree provides a files/<region-name>.*.j2 fragment"
            " for this region -- this is a broken template installation, not a problem"
            " with the repository being adopted"
        ),
    )


def _default_commit(
    *,
    repo_root: Path,
    never_write: fs.NeverWrite,
    entries_by_id: dict[str, ManifestEntry],
    model_version: ModelVersion,
    answers: Mapping[str, Any],
    template_path: Path | str | None,
) -> CommitAction:
    """Build the real, production ``commit`` callback ``run_adopt`` supplies
    to ``apply.run.run_apply`` -- see the module docstring's own section for
    the full design and its rationale (lazy, once-per-run materialize for
    whole-file classes; a region-body's content is read directly, never
    routed through ``materialize()`` at all -- see
    ``_region_body_from_template``'s own docstring for why)."""
    staged: list[MaterializeResult] = []

    def _materialized() -> MaterializeResult:
        if not staged:
            staged.append(
                materialize(
                    MaterializeRequest(
                        verb=MaterializeVerb.COPY,
                        dst_path=repo_root,
                        template_path=template_path,
                        data=dict(answers),
                    )
                )
            )
        return staged[0]

    def commit(action: Action) -> None:
        entry = entries_by_id[action.artifact_id]
        target = repo_root / action.target_path
        if entry.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION:
            assert entry.format is not None  # ManifestEntry.__post_init__ guarantees this
            for region_name, _matched_anchor in action.chosen_anchor:
                region = next((candidate for candidate in entry.regions if candidate.name == region_name), None)
                if region is None:
                    # Unreachable via any real `Plan` (`action.chosen_anchor`
                    # is `build_plan`'s own output, always drawn from
                    # `entry.regions`) -- a defensive `InternalError` rather
                    # than a bare `StopIteration` escaping `commit()` mid-apply
                    # (review finding): this package's convention is that
                    # every `seed/` failure is one of the six `SeedError`
                    # leaves, never a raw traceback, and `run_apply` has
                    # already begun writing by the time `commit()` runs.
                    raise InternalError(
                        f"action names region {region_name!r}, which entry {entry.id!r} does not declare",
                        remedy=(
                            "this is a plan/manifest inconsistency -- a broken installation,"
                            " not a problem with the repository being adopted"
                        ),
                    )
                if region_name == "projects-table" and entry.id == "projects-index":
                    # Story 11.2: `projects-table`'s body is repo-computed
                    # (the set of `_bmad-output/projects/*/.bmad-config.toml`
                    # files actually present in THIS repo), never a static
                    # packaged fragment -- `_region_body_from_template` reads
                    # a `files/<region-name>.*.j2` fragment off the template
                    # tree, which is the WRONG source for a region whose
                    # whole point is to reflect the adopting repo's own live
                    # state. Every OTHER hybrid region still reads its static
                    # fragment via `_region_body_from_template` unchanged.
                    # The `entry.id` guard (review finding, pass 2) matters
                    # because region NAMES are a namespace shared across
                    # manifest entries by this package's own design (unlike
                    # `ADAPTER_COMPOSITION`'s membership check just below,
                    # which keys on the genuinely-unique `entry.id` alone) --
                    # without it, a future manifest entry that happened to
                    # reuse "projects-table" as a region name for an
                    # unrelated purpose would be silently hijacked into
                    # rendering the live project index instead of its own
                    # intended content.
                    body = derive_projects_index.derive_projects_table(repo_root / "_bmad-output" / "projects")
                else:
                    body = _region_body_from_template(template_path, region_name)
                text = target.read_text(encoding="utf-8") if target.is_file() else None
                insert_region(
                    text,
                    target,
                    region_name,
                    region.anchor,
                    body,
                    model_version=model_version,
                    fmt=entry.format,
                    repo_root=repo_root,
                    never_write=never_write,
                )
        elif (
            entry.id in derive_adapters.ADAPTER_COMPOSITION and entry.artifact_class is ArtifactClass.GENERATED_DERIVED
        ):
            # Story 11.1: the three whole-file agent-adapter ids
            # (`cursor-rules`/`gemini-md`/`copilot-instructions`) render via
            # `derive.adapters`'s own fragment-composition seam -- NEVER via
            # `_materialized()`/`engine.copier.materialize` (see `derive.
            # adapters`'s own module docstring for the empirically-confirmed
            # `TemplateBoundaryError` that rules that path out). A data-driven
            # membership check, not a per-id branch: a fifth adapter added to
            # `ADAPTER_COMPOSITION` reaches this same line with no change
            # here. The `artifact_class` cross-check (review finding) means
            # an id collision with a differently-classed future manifest
            # entry falls through to the generic `_materialized()` path
            # below instead of being silently rerouted through
            # derive-composition.
            content = derive_adapters.render_adapter(entry.id, template_path=template_path)
            fs.write(target, content.encode("utf-8"), repo_root=repo_root, never_write=never_write)
        else:
            result = _materialized()
            content = _staged_bytes_for(result.staged_paths, action.target_path)
            fs.write(target, content, repo_root=repo_root, never_write=never_write)

    return commit


def _hybrid_record(
    entry: ManifestEntry, text: str, spans: Mapping[str, RegionSpan], *, named: set[str], claim_every_present: bool
) -> ManagedArtifact | None:
    """The ``ManagedArtifact`` for a hybrid ``entry`` whose file now reads
    ``text`` (``spans``, parsed from it): one ``RegionSpanRecord`` per declared
    region present in the file, in declared order, each with its own offsets and
    the ``hash_content`` of its body. A region is claimed when ``named`` holds
    it or ``claim_every_present`` says the tool installed this file; ``None``
    when that leaves nothing, because a hybrid claim with no span is invalid and
    an artifact with no region of its own is not claimed (Story 82.13)."""
    recorded_spans = tuple(
        RegionSpanRecord(
            name=region.name,
            start=spans[region.name].body_span[0],
            end=spans[region.name].body_span[1],
            body_sha=hash_content(region_body_text(text, spans[region.name])),
        )
        for region in entry.regions
        if region.name in spans and (claim_every_present or region.name in named)
    )
    if not recorded_spans:
        return None
    return ManagedArtifact(
        id=entry.id,
        path=entry.path,
        artifact_class=entry.artifact_class.value,
        body_sha=recorded_spans[0].body_sha,
        inserted_region_spans=recorded_spans,
    )


def _carried_hybrid_record(
    prior: ManagedArtifact, entry: ManifestEntry | None, repo_root: Path
) -> ManagedArtifact | None:
    """The record for a hybrid artifact the plan did NOT touch but whose record
    the run's in-memory opt-out recording dropped (Story 82.13): a state in the
    pre-82.13 one-span shape whose only recorded region's markers were deleted,
    while its siblings are still in the file and a ``--skip`` (or a plan with
    nothing to write there) left the artifact alone. Without it the siblings
    would silently lose their claim, where the baseline carried the record over.

    ``prior`` is the record as read. Same rule as ``_managed_artifact_after_apply``
    for a replaced record: every declared region present in the file is claimed
    at its CURRENT hash (nothing was rewritten), and ``None`` when none is -- the
    caller omits the artifact. ``None`` too for an entry that is gone from the
    manifest, is not hybrid, or whose recorded ``path`` moved (that record
    describes another file). The caller never offers an escaping entry: its path
    is not read."""
    if (
        entry is None
        or entry.artifact_class is not ArtifactClass.HYBRID_MANAGED_REGION
        or not prior.inserted_region_spans
    ):
        return None
    assert entry.format is not None
    text = _read_text_or_blank(repo_root / entry.path)
    spans = {span.name: span for span in parse_regions(text, entry.format)}
    return _hybrid_record(entry, text, spans, named=set(), claim_every_present=prior.path == entry.path)


def _carried_back_records(
    state_as_read: SeedState | None,
    state: SeedState | None,
    touched_ids: frozenset[str],
    escaping_ids: set[str],
    entries_by_id: Mapping[str, ManifestEntry],
    repo_root: Path,
) -> tuple[ManagedArtifact, ...]:
    """Every record of ``state_as_read`` that the in-memory ``state`` no longer
    holds (recording a derived opt-out dropped it), the plan did not touch and
    that is not an escaping entry -- rebuilt by ``_carried_hybrid_record``, so a
    hybrid artifact's present siblings keep their claim. An escaping entry is
    never read (Story 82.11); in practice the opt-out recording skips it too, so
    its record is never dropped, and the check here keeps that true on its own."""
    if state_as_read is None:
        return ()
    held = {record.id for record in state.managed} if state is not None else set()
    rebuilt = (
        _carried_hybrid_record(prior, entries_by_id.get(prior.id), repo_root)
        for prior in state_as_read.managed
        if prior.id not in held and prior.id not in touched_ids and prior.id not in escaping_ids
    )
    return tuple(record for record in rebuilt if record is not None)


def _managed_artifact_after_apply(
    action: Action, entry: ManifestEntry, repo_root: Path, prior: ManagedArtifact | None = None
) -> ManagedArtifact | None:
    """One post-apply ``ManagedArtifact`` for ``action`` -- re-reading the
    JUST-MATERIALIZED target from disk (the Always bullet's own "re-read
    each materialized whole-file entry's content and hash it, use regions.
    parse for each materialized hybrid entry's inserted span"), never
    trusting anything the ``commit`` callback might have returned (it
    returns nothing at all -- ``apply.run.CommitAction`` is a bare
    ``Callable[[Action], None]``).

    **A hybrid entry records every region it holds, not the first one**
    (Story 82.13, ``DW-FU-8-5-6``). ``_build_state_after_apply`` replaces a
    touched id's old record outright, so ``prior`` -- the record it replaces,
    from the state AS READ, before the run recorded any derived opt-out in
    memory -- decides what the new one claims:

    * With a ``prior`` at the same ``path`` the tool installed this file, so
      every declared region PRESENT in it after the write is the tool's and is
      recorded, in the manifest's declared order. An old-shape record names ONE
      region although ``adopt`` installed them all in one action, and a
      deleted recorded region leaves nothing to name its present siblings, so
      "the regions ``prior`` carried" would be too few (review pass 2: the
      wedge where an FR-112 deletion of the one recorded region made the run
      exit 10 after it had written). A ``prior`` at a MOVED ``path`` describes
      a different file and counts for nothing.
    * Without one only the regions ``action.chosen_anchor`` named are claimed
      -- the tool does not take ownership of a region a human put there.

    Each recorded region carries its own byte offsets and the ``hash_content``
    of its body, read back from the file. A region carried over from ``prior``
    is recorded at its CURRENT hash: rung 6 has already refused a hand-edit to
    it (no ``--force``), so the hash is the value the repo already held, and
    under ``--force`` the operator chose to discard hand-edits -- a sibling this
    run did not rewrite is adopted as it stands. A declared region the file no
    longer contains (an opt-out, a deleted block) is left out rather than
    invented.

    ``InternalError`` when a region ``action.chosen_anchor`` NAMED is absent
    after the write, whatever else was recorded: ``commit`` was asked to insert
    it and did not. This runs AFTER ``run_apply`` has written, so a bare
    ``ValueError`` out of the constructor would leave a real file change with
    no state. ``None`` when nothing is named and no declared region is present:
    the artifact is no longer claimed (every region was deleted, which FR-112
    makes lawful, not an error), and the caller omits it from state."""
    target = repo_root / action.target_path
    if entry.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION:
        assert entry.format is not None
        text = target.read_text(encoding="utf-8")
        spans = {span.name: span for span in parse_regions(text, entry.format)}
        named = {name for name, _anchor in action.chosen_anchor}
        missing = named - spans.keys()
        if missing:
            raise InternalError(
                f"managed region(s) {sorted(missing)!r} of {entry.path!r} were not found immediately after the"
                f" write (action named {sorted(named)!r})",
                remedy=(
                    "this indicates insert_region silently failed to insert the region it"
                    " was asked to -- a broken installation, not a problem with the"
                    " repository being adopted"
                ),
            )
        installed_by_the_tool = prior is not None and prior.path == entry.path
        return _hybrid_record(entry, text, spans, named=named, claim_every_present=installed_by_the_tool)
    content = target.read_text(encoding="utf-8")
    return ManagedArtifact(
        id=entry.id,
        path=entry.path,
        artifact_class=entry.artifact_class.value,
        body_sha=hash_content(content),
        inserted_region_spans=(),
    )


def _build_state_after_apply(
    *,
    plan: Plan,
    state: SeedState | None,
    state_as_read: SeedState | None,
    inventory: Inventory,
    entries_by_id: dict[str, ManifestEntry],
    repo_root: Path,
    agents: tuple[str, ...],
    manifest: Manifest,
    skip: Sequence[str],
) -> SeedState:
    """The ``SeedState`` ``run_adopt`` writes after a successful, NON-EMPTY
    apply -- see the module docstring's "Ordering" section for the gate
    that keeps this function unreachable for an empty plan.

    Two states are in play (Story 82.13, review pass 2). ``state`` is the run's
    in-memory state, WITH every derived opt-out recorded (``_state_with_opt_outs``):
    it supplies the records carried over untouched and ``opted_out``.
    ``state_as_read`` is the state exactly as ``read_state`` returned it, and it
    supplies the REPLACED records. Recording an opt-out drops a hybrid record's
    span -- and the whole record when that was its only span, as it is in a
    state written before 82.13 -- so reading the replaced record from ``state``
    would leave the siblings of a deleted region with nothing to be claimed by
    (``_managed_artifact_after_apply``). A record it returns ``None`` for (every
    region deleted, nothing named) is omitted: the artifact is no longer
    claimed.

    A hybrid record the in-memory recording dropped that the plan did not touch
    (a ``--skip``, an empty action) is rebuilt by ``_carried_back_records`` from the
    siblings still in the file, so it does not silently leave state."""
    touched_ids = frozenset(action.artifact_id for action in plan.actions)
    carried_over = tuple(
        record for record in (state.managed if state is not None else ()) if record.id not in touched_ids
    )
    carried_back = _carried_back_records(
        state_as_read, state, touched_ids, {escape.entry_id for escape in inventory.escaping}, entries_by_id, repo_root
    )
    prior_by_id = {record.id: record for record in state_as_read.managed} if state_as_read is not None else {}
    built = (
        _managed_artifact_after_apply(
            action, entries_by_id[action.artifact_id], repo_root, prior_by_id.get(action.artifact_id)
        )
        for action in plan.actions
    )
    new_records = tuple(record for record in built if record is not None)
    managed = tuple(sorted((*carried_over, *carried_back, *new_records), key=lambda record: record.id))
    legacy = tuple(
        LegacyArtifact(id=record.entry_id, path=record.path, legacy_of=record.legacy_of) for record in inventory.legacy
    )
    recorded_skips = state.skips if state is not None else ()
    for pattern in skip:
        recorded_skips = tuple(sorted(set(recorded_skips) | {pattern.strip()}))
    now = utc_timestamp()
    return SeedState(
        model_version=manifest.model_version,
        seed_model_version=seed_model_version(),
        adopted_at=state.adopted_at if state is not None else now,
        last_update=now,
        mode="adopt",
        agents=agents,
        managed=managed,
        skips=recorded_skips,
        legacy=legacy,
        migrations_applied=state.migrations_applied if state is not None else (),
        opted_out=state.opted_out if state is not None else (),
    )


def run_adopt(
    repo_root: Path,
    manifest: Manifest,
    *,
    apply: bool = False,
    yes: bool = False,
    agents: Sequence[str] = (),
    skip: Sequence[str] = (),
    force: bool = False,
    confirm: Callable[[], bool],
    template_path: Path | str | None = None,
    commit: CommitAction | None = None,
    slug: str | None = None,
    in_loop_home: bool | None = None,
) -> AdoptResult:
    """Compose ``resolve -> detect -> plan -> augment -> confirm -> apply ->
    state-write`` against ``repo_root``, writing ``.marshal/plan.json``
    unconditionally and ``.marshal/seed-state.yml`` only after a successful,
    non-empty apply -- see the module docstring for the full ordering
    rationale and the FR-83/FR-84 resolution this function implements.

    ``confirm`` has no default: production callers (``cli/seed.py``) always
    supply one (a real ``input()``-based prompt by default, or a test
    double), matching this module's own confirm-seam design (module
    docstring). ``template_path``/``commit`` are additional test-injection
    seams beyond what the epics AC names explicitly: ``commit`` lets a test
    bypass ``engine.copier.materialize`` entirely (the common case, for
    tests that are not themselves exercising the materialize-wrapping
    logic); ``template_path`` lets a test exercise the REAL default
    ``commit`` builder (``_default_commit``) against a synthetic template
    tree without depending on the packaged one's current, still-incomplete
    content (module docstring's "known limitations" (1)). Neither is
    consulted when ``commit`` is explicitly supplied.

    Raises whatever ``read_state``/``check_preconditions``/``run_apply``
    raise, unchanged -- this function adds no ``try``/``except`` of its own;
    a caught ``StateInvalid`` is NOT downgraded to "never adopted" the way
    ``verbs/check.py`` downgrades it for a read-only report: a MUTATING verb
    silently treating corrupted state as absent would let this run overwrite
    hand-edited managed content state itself could no longer attest to --
    exactly the class of risk SC-04 exists to prevent."""
    filtered_manifest = _manifest_for_adopt(manifest, slug, in_loop_home=in_loop_home)
    state = read_state(repo_root)
    # The state exactly as read: the post-apply state takes the records it
    # REPLACES from here, after `state` below has had derived opt-outs recorded
    # (and, for an old-shape record, been stripped of it).
    state_as_read = state
    inventory = classify(filtered_manifest, repo_root)
    escapes = escape_findings(inventory)
    # Rung 6 refuses a record whose path does not resolve inside the repo, so a
    # previously adopted entry that is now an escaping symlink would still
    # refuse the whole run there (Story 82.11) -- it is already reported in
    # `escape_findings` and planned for nothing, so it is neither handed to
    # rung 6 nor read for opt-outs.
    escaping_ids = {escape.entry_id for escape in inventory.escaping}
    # From here `state` is the run's state WITH the derived opt-outs recorded
    # (in memory; see `_state_with_opt_outs`), so the plan, rung 6 and the
    # state this run writes all read the one opt-out set (Story 82.13).
    state, opted_out_pairs = _state_with_opt_outs(filtered_manifest, state, repo_root, escaping_ids)
    opted_out = frozenset(state.opted_out) if state is not None else frozenset()
    plan = build_plan(filtered_manifest, inventory, opted_out=opted_out)
    plan = _augment_plan_with_first_claims(plan, inventory, filtered_manifest, state)
    # The patterns a re-adopt skips are the ones `state.skips` recorded on
    # earlier runs as well as this run's own `--skip` (FR-87: a skip is
    # honoured on every subsequent run; Story 86.1, DW-FU-11-4).
    skip_patterns = with_recorded_skips(state.skips if state is not None else (), skip)
    plan = apply_skips(plan, skip_patterns)

    never_write = fs.NeverWrite(
        patterns=tuple(sorted(effective_never_write(filtered_manifest, inventory))),
        exempt=writable_exemptions(filtered_manifest, inventory),
    )
    # The skip patterns (recorded and this run's) are passed as well as
    # `plan.skipped` carrying the actioned ones: a hand-edited `copied-managed`
    # file has no action to move into `plan.skipped`, so only its path matching
    # a pattern reaches it (Story 82.12, DW-10-4-4).
    managed_records = managed_after_skips(
        tuple(
            record for record in _managed_records(state, filtered_manifest) if record.artifact_id not in escaping_ids
        ),
        plan,
        skip_patterns,
    )

    check_preconditions(
        plan,
        repo_root=repo_root,
        never_write=never_write,
        managed=managed_records,
        opted_out=opted_out_pairs,
        force=force,
        dry_run=not apply,
    )

    write_plan(plan, default_plan_path(repo_root))

    if not apply:
        return AdoptResult(plan=plan, applied=None, declined=False, escape_findings=escapes)

    if not yes and not confirm():
        return AdoptResult(plan=plan, applied=None, declined=True, escape_findings=escapes)

    entries_by_id = {entry.id: entry for entry in filtered_manifest.entries}
    new_agents = _merge_agents(state.agents if state is not None else (), agents)

    effective_commit = commit
    if effective_commit is None:
        effective_commit = _default_commit(
            repo_root=repo_root,
            never_write=never_write,
            entries_by_id=entries_by_id,
            model_version=filtered_manifest.model_version,
            answers={
                "model_version": str(filtered_manifest.model_version),
                "seed_model_version": seed_model_version(),
                "mode": "adopt",
                "agents": list(new_agents),
            },
            template_path=template_path,
        )

    # Refuse loudly if anything OTHER than this run's own known
    # `.marshal/plan.json` write is dirty right now (review finding -- the
    # actual protection against an operator dirtying the repo with
    # something unrelated during the confirm pause; see
    # `_unexpected_dirt_since_plan_write`'s own docstring for why this,
    # not a restricted stamp on `RepoFingerprint.dirty`, is the correct
    # mechanism).
    _unexpected_dirt_since_plan_write(repo_root)

    # Refresh ONLY the fingerprint's `dirty` flag, to account for `write_plan`
    # above having just introduced `.marshal/plan.json` as an untracked file
    # -- see `_repo_is_dirty_now`'s own docstring for why this MUST be the
    # true, unrestricted current value, not a selectively-excluded one,
    # before `run_apply`'s own fresh, unrestricted dirty re-check runs.
    apply_plan = dataclasses.replace(
        plan,
        repo_fingerprint=dataclasses.replace(plan.repo_fingerprint, dirty=_repo_is_dirty_now(repo_root)),
    )

    result: ApplyResult = run_apply(apply_plan, repo_root=repo_root, never_write=never_write, commit=effective_commit)

    if plan.actions:
        new_state = _build_state_after_apply(
            plan=plan,
            state=state,
            state_as_read=state_as_read,
            inventory=inventory,
            entries_by_id=entries_by_id,
            repo_root=repo_root,
            agents=new_agents,
            manifest=filtered_manifest,
            skip=skip,
        )
        write_state(new_state, repo_root=repo_root, never_write=never_write)

    return AdoptResult(plan=plan, applied=result.applied, declined=False, escape_findings=escapes)
