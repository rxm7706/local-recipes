"""``marshal seed update``'s verb logic: a two-phase verb (``resolve ->
detect -> plan -> confirm -> apply -> state-write``, mirroring
``verbs/adopt.py``'s already-shipped shape, Story 11.4, PRD FR-94/FR-97/
FR-98/FR-99/FR-100/FR-101, epics AC).

Until this module, ``cli/seed.py::run_update`` was Story 7.1's stub. A repo
that adopted Marshal's seed model had no way to take a later model version:
``seed/migrate/registry.py`` (Story 11.3) can compute and compose migrations
into a ``Plan``, but nothing called it, and nothing regenerated a drifted
``copied-managed``/``generated-derived``/``hybrid-managed-region`` artifact
whose PACKAGED content had simply moved on since the repo's last update -- a
case ``detect.inventory.classify`` cannot see at all (it never compares
against template content; only ``hybrid-managed-region`` can ever reach
``PRESENT_DIVERGENT``, and only when a declared region is structurally
missing -- ``plan/build.py``'s own module docstring: "``PRESENT_CONFORMANT``
... never [produce an Action], for ANY class"). This module is that missing
composition.

**The plan is a merge of THREE action sources, never one.** ``build_plan``
(Story 9.6, unmodified) still only ever emits an ``Action`` for
``ABSENT``/``PRESENT_DIVERGENT`` -- a manifest addition not yet
materialized. Migrations (Story 11.3's ``chain``/``compose``) absorb a
breaking model-version change. Neither ever revisits an artifact that is
already ``PRESENT_CONFORMANT`` and already tracked in ``state.managed[]`` --
which is exactly what FR-98/FR-99 require ``update`` to do unconditionally,
so it needs a THIRD source this module adds: ``_wholesale_regenerate_actions``,
a pass over every ``state.managed[]`` record whose class is
``copied-managed``/``generated-derived``/``hybrid-managed-region``. See that
function's own docstring for why this is a NEW pass rather than a
``build_plan`` change.

**Making the three sources ACTUALLY disjoint, not merely assumed to be**
(review finding, confirmed by execution against the canonical "renamed
managed artifact" migration example this module's own design discussion
cites). ``build_plan`` is entirely state-independent (it classifies off
live disk content only) -- for a genuine rename, the artifact's CURRENT
manifest path is absent on disk (nothing has moved it there yet), so
``build_plan`` proposes an ordinary creation action for the SAME id a
migration -- and, since the id already carries a ``state.managed[]``
record, the wholesale-regenerate pass -- ALSO produce an action for. Three
sources computed independently and merged naively collide on precisely the
scenario the epics AC calls out as the headline migration use case, not on
some rare edge. ``run_update`` therefore ENFORCES disjointness before
merging, symmetrically: (1) any ``build_plan`` action whose id already has a
``state.managed[]`` record is dropped -- that id is wholesale-regenerate
(or migration) territory, never "genuinely new"; (2) any wholesale-
regenerate action whose id the migration plan already claims (in its own
``actions`` OR its own ``copied-seeded`` ``skipped`` offers) is dropped --
the migration's own logic is what actually absorbs the breaking change for
that artifact, and a redundant generic refresh would either collide or race
it. What remains is merged via the same collision-then-sort pattern
``migrate.compose``'s own ``_claim`` and ``verbs/adopt.py::
_augment_plan_with_first_claims`` already establish (``_merge_plan_sources``
below) -- the ``InternalError`` it can still raise is now a genuine
defensive backstop (a manifest/migration inconsistency this exclusion does
not anticipate), not the everyday path a well-formed rename migration would
otherwise hit on every single run.

**Why ``substitute_region``, not only ``insert_region``, for a hybrid
region.** ``insert_region`` (Stories 8.3/8.4, unmodified) is a no-op --
``InsertionOutcome.ALREADY_PRESENT``, no write at all -- the moment its
``name`` is already among the file's parsed spans. That is exactly the
common case a wholesale-regenerate action targets: an already-adopted,
already-conformant hybrid region. Using only ``insert_region`` for this
module's own commit dispatcher would silently do nothing for the one case
FR-99 exists to cover ("only its marked span is REPLACED, never the whole
file"). ``substitute_region`` (Story 8.3, shipped but -- confirmed by
grepping this package's own source tree -- never called from any real,
non-test code path until this module) is that missing "replace" primitive:
this module's commit dispatcher checks, per declared region, whether it is
currently present (a fresh ``parse_regions`` read) and substitutes if so,
inserts if not -- a strict generalization of ``verbs/adopt.py``'s own
insert-only dispatch that behaves identically for an ABSENT/PRESENT_DIVERGENT
action (whose ``chosen_anchor`` only ever names NOT-present regions, so the
"substitute" branch is not reachable for those) and additionally does the
right thing for a wholesale-regenerate action's PRESENT one.

**Why the migration-composed and wholesale-regenerate actions need their own
``artifact_hashes`` entries, computed here.** ``migrate.compose`` shares the
CALLER-SUPPLIED ``repo_fingerprint`` verbatim across every migration's
actions (its own docstring: "the composed ``Plan`` shares exactly ONE
fingerprint, the caller-supplied ``repo_fingerprint`` argument" -- it never
adds a hash pair for anything). ``apply.run.fingerprint_drift`` cross-checks
``actions`` against ``artifact_hashes`` in BOTH directions and refuses the
whole plan as corrupt on any orphan (either module's own docstring). This
module therefore hashes the CURRENT on-disk content at each migration
action's ``target_path`` itself (mirroring ``verbs/adopt.py::
_augment_plan_with_first_claims``'s identical obligation for its own
first-claim actions, and the SC-07 fixture test's own
``_fresh_fingerprint(tmp_path, ("renamed", hash_content("")), ...)``
construction), and does the same for every wholesale-regenerate action
(inside ``_wholesale_regenerate_actions`` itself, alongside the ``Action``
it produces -- one function, one pass, so the two can never drift apart).

**Why a ``_manifest_for_update`` filter, mirroring ``verbs/adopt.py``'s
identical ``_manifest_for_adopt``.** The packaged manifest's two
``applies_to: init``-only entries (``starter-dream``, ``specs-readme``) are
both ``copied-seeded`` with an unrendered ``{{ slug }}`` path segment --
``update`` has no ``--slug`` flag (S-10.7's ``init`` owns that), so an
unfiltered ``build_plan`` pass would propose materializing a literal,
un-rendered ``{{ slug }}.md`` path, exactly the hazard ``verbs/adopt.py``'s
own module docstring already names and fixes for ``adopt``. ``update``
inherits the identical exposure (it calls the identical ``build_plan``), so
it needs the identical fix.

**Why ``state is None`` degrades rather than raises, but never writes new
state.** ``update``'s whole premise (Problem statement) is a repo that
ALREADY adopted the seed model -- but nothing in this story's own I/O
Matrix names a never-adopted repo, so this module treats it the same way
``verbs/adopt.py``'s own ``_managed_records``/``_augment_plan_with_first_
claims`` already tolerate a ``None`` state: no migrations to run (there is
no ``state.model_version`` to bridge FROM), no wholesale-regenerate actions
(``state.managed`` is empty), so only ``build_plan``'s ordinary
``ABSENT``-only actions apply -- a graceful, non-crashing degrade, not a
tested contract. The state-WRITE step is gated on ``state is not None`` in
addition to a non-empty ``plan.actions`` (never on the ``Action`` count
alone): the packaged ``state/schema.json`` restricts ``mode`` to exactly
``{"init", "adopt"}`` and documents WHY in its own words -- "``update``
moves ``model_version`` without RE-ESTABLISHING origin" -- so there is no
schema-valid ``mode`` this module could invent for a repo ``update`` did not
establish. Applying still proceeds (materializing whatever ``ABSENT``
actions exist is harmless), the write of ``.marshal/seed-state.yml`` simply
does not happen for that one, out-of-scope case.

**Fixing ``DW-FU-11-3`` (spec-11-3's own deferred finding).** ``migrate.
compose`` routes a ``copied-seeded`` action to ``Plan.skipped`` with
``pattern=migrate.registry._SEEDED_OFFER_PATTERN`` when ``include_seeded``
is not given. That module's own docstring already fixed the pattern's own
WORDING (it no longer falsely claims a ``--skip`` glob matched), but
``cli/seed.py::_render_plan_text`` -- ``adopt``-only, unmodified by this
story -- still renders EVERY ``SkippedArtifact`` as ``matched --skip
{pattern!r}``, which is simply the wrong sentence shape for a migration
offer. ``cli/seed.py`` gains a NEW renderer for ``update``'s own plan
(``_render_update_plan_text``) that checks ``pattern ==
migrate.registry._SEEDED_OFFER_PATTERN`` and renders an explicit offer
sentence instead -- this module's own contribution is exporting nothing
special for it (the check is entirely on the CLI side, against
``Plan.skipped`` this module already produces via ``migrate.compose``
unchanged).

**Ordering** (the Always bullets' own sequencing, restated as code):
resolve (``_manifest_for_update``) -> detect (``classify``) -> plan (build +
migrate + wholesale, merged via ``_merge_plan_sources``) -> preconditions
(``verbs.preconditions.check_preconditions``, BEFORE any write, ``dry_run=
not run``) -> write ``.marshal/plan.json`` (ALWAYS) -> return early for a
dry-run -> confirm (only when ``run and not yes``; a decline returns without
ever calling ``run_apply``) -> refuse on unexpected dirt
(``_unexpected_dirt_since_plan_write``, the identical mechanism
``verbs/adopt.py`` already established and documented at length) -> refresh
the fingerprint's ``dirty`` flag to the true, unrestricted current value
(``_repo_is_dirty_now``) -> ``apply.run.run_apply`` -> state-write, gated on
``state is not None and plan.actions`` being non-empty.

**Import surface.** Mirrors ``verbs/adopt.py``'s own surface, plus
``migrate.registry`` (the module, imported as ``migrate_registry`` -- Story
11.3's ``chain``/``compose``/``_SEEDED_OFFER_PATTERN``/``RepoView``) and
``regions.apply.substitute_region`` (new to a real, non-test call site
here). No ``seed.cli`` import (the architecture's no-upward-imports rule).
"""

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
    writable_exemptions,
)
from ..detect.referenced_deps import referenced_dep_findings
from ..engine import MaterializeRequest, MaterializeResult, MaterializeVerb, materialize
from ..errors import InternalError, PreconditionFailure
from ..migrate import registry as migrate_registry
from ..model.manifest import AppliesTo, ArtifactClass, Manifest, ManifestEntry
from ..model.version import ModelVersion
from ..plan.build import build_plan, default_plan_path, write_plan
from ..plan.types import Action, Plan, RepoFingerprint
from ..regions.apply import insert_region, substitute_region
from ..regions.markers import MarkerError
from ..regions.parse import RegionParseError, parse_regions
from ..state import (
    LegacyArtifact,
    ManagedArtifact,
    RegionSpanRecord,
    SeedState,
    read_state,
    seed_model_version,
    utc_timestamp,
    write_state,
)
from .preconditions import ManagedRecord, check_preconditions

# The classes `_wholesale_regenerate_actions` ever fires for -- FR-98/FR-99's
# own named classes. `copied-seeded` and `referenced` are deliberately
# excluded (the Always bullet's own "never regenerated by update"):
# `copied-seeded` is "materialized once, then repo-owned forever" (the
# opposite of unconditional regeneration), and `referenced` is never
# materialized at all (nothing to regenerate) -- and, in practice, never
# recorded in `state.managed[]` to begin with.
_WHOLESALE_CLASSES = frozenset(
    {ArtifactClass.COPIED_MANAGED, ArtifactClass.GENERATED_DERIVED, ArtifactClass.HYBRID_MANAGED_REGION}
)

# Query-style git call (never a checkout/push) -- the identical value
# `verbs/adopt.py::_GIT_TIMEOUT_S`/`plan/build.py::_GIT_TIMEOUT_S`/
# `verbs/preconditions.py::_GIT_TIMEOUT_S` use for the identical class of
# call, so a hung `git` fails fast here too.
_GIT_TIMEOUT_S = 30.0


@dataclass(frozen=True)
class UpdateResult:
    """``run_update``'s whole return value -- mirrors ``verbs/adopt.py::
    AdoptResult`` field for field (see that class's own docstring for the
    full rationale, identical here): ``plan`` is the FINAL, merged plan
    actually considered (the same one written to ``.marshal/plan.json``);
    ``applied`` is ``None`` for a dry-run or a declined confirmation, else
    ``ApplyResult.applied``; ``declined`` is ``True`` only when ``--run``
    was requested, ``--yes`` was not, and ``confirm()`` returned ``False``."""

    plan: Plan
    applied: tuple[str, ...] | None
    declined: bool
    referenced_dep_findings: tuple[Finding, ...] = ()


def _git_status_porcelain(repo_root: Path, *extra_pathspec: str) -> str | None:
    """Mirrors ``verbs/adopt.py``'s identical helper verbatim (that
    function is private to a sibling module; duplicated per this package's
    established "small deliberate duplication beats reaching into a
    neighbour's private helper" convention -- see that module's own
    docstring for the full rationale)."""
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
    """Mirrors ``verbs/adopt.py``'s identical helper -- see that module's
    own docstring for why this MUST be the true, unrestricted current dirty
    value (never a selectively-excluded one) before ``run_apply``'s own
    fresh, unrestricted re-check runs."""
    output = _git_status_porcelain(repo_root)
    return output is None or bool(output)


def _unexpected_dirt_since_plan_write(repo_root: Path) -> None:
    """Mirrors ``verbs/adopt.py``'s identical helper -- the mechanism that
    catches an operator dirtying the repo with something UNRELATED to
    ``update``'s own ``.marshal/plan.json`` write while awaiting
    confirmation. See that module's own docstring for the full rationale."""
    output = _git_status_porcelain(repo_root, ".", ":!.marshal/")
    if output is None or output:
        raise PreconditionFailure(
            "dirty-worktree: the repository changed since it was last confirmed clean"
            " (excluding this run's own .marshal/plan.json write) -- an operator or"
            " another process modified it while update was awaiting confirmation",
            remedy="re-run marshal seed update and review the fresh plan before applying it",
        )


def _manifest_for_update(manifest: Manifest) -> Manifest:
    """``manifest``, scoped to ``applies_to in (ADOPT, BOTH)`` -- mirrors
    ``verbs/adopt.py::_manifest_for_adopt`` verbatim (see the module
    docstring's own paragraph on why: an ``init``-only entry's
    ``{{ slug }}``-templated path has no target ``update`` could ever
    materialize correctly, and ``update`` -- like ``adopt`` -- has no
    ``--slug`` flag to resolve it with)."""
    entries = tuple(entry for entry in manifest.entries if entry.applies_to in (AppliesTo.ADOPT, AppliesTo.BOTH))
    return Manifest(model_version=manifest.model_version, never_write=manifest.never_write, entries=entries)


def _read_text_or_blank(target: Path) -> str:
    """Mirrors ``verbs/adopt.py``'s identical helper verbatim."""
    if not target.is_file():
        return ""
    try:
        return target.read_text(encoding="utf-8")
    except OSError, UnicodeDecodeError:
        return ""


def _region_shas_for_record(
    artifact: ManagedArtifact, entry: ManifestEntry, repo_root: Path
) -> tuple[tuple[str, str | None], ...]:
    """``ManagedRecord.region_shas`` for one region-bearing ``artifact`` --
    review finding, HIGH/blocking: ``state/store.py``'s own pre-existing
    schema limit means ``artifact.inserted_region_span`` names AT MOST ONE
    of ``entry.regions`` (the packaged manifest's own ``AGENTS.md``/
    ``CLAUDE.md`` entries declare 3/2), even though a real ``adopt`` inserts
    every declared region into the file. Returning only that ONE recorded
    pair here made rung 6 (``verbs/preconditions.py::_region_divergences``)
    see every OTHER declared-but-present region as "present in the file but
    never recorded in state" -- a HARD divergence -- refusing every
    ``update`` invocation (not gated by ``dry_run``, only ``force`` skips
    rung 6) against ANY multi-region hybrid entry, unconditionally.

    The fix stays entirely inside this module (never ``preconditions.py``/
    ``adopt.py``): the genuinely-recorded region keeps its REAL recorded
    sha unchanged -- real hand-edit protection, not weakened. For every
    OTHER region ``entry`` declares, this reads the target's CURRENT
    on-disk text, parses it, and uses the CURRENT body hash of that region
    (if actually present) as its "recorded" value -- rung 6 then sees it as
    accounted-for and non-divergent. This is a real, stated bound, not a
    silent weakening: state genuinely has no recorded truth for a region it
    never tracked (the same pre-existing ``state/store.py`` limitation
    ``verbs/adopt.py`` already lives with), so a hand-edit to one of THOSE
    regions is not caught by rung 6 -- only the one region state actually
    tracks gets real protection, exactly as before this fix.

    A region ``entry`` declares but that is not actually present in the
    current file is left out entirely (no synthetic pair) -- rung 6 raises
    no "unrecorded" divergence for a region that plainly is not there
    either, so nothing needs representing for it.

    Parse failures (``RegionParseError``/``MarkerError``/
    ``NotImplementedError``, the reserved-format case) degrade to "no
    synthetic pairs added" rather than propagating: rung 6 performs its own
    independent parse of the same file and will surface the failure as its
    own divergence through its own path -- this helper's job is only to
    stop a MULTI-region entry from refusing on regions it cannot itself
    attest to, never to duplicate rung 6's own parse-failure handling."""
    recorded_name = artifact.inserted_region_span.name
    recorded_sha = artifact.body_sha
    region_shas: list[tuple[str, str | None]] = [(recorded_name, recorded_sha)]
    other_names = [region.name for region in entry.regions if region.name != recorded_name]
    if not other_names:
        return tuple(region_shas)
    current_text = _read_text_or_blank(repo_root / artifact.path)
    if not current_text:
        return tuple(region_shas)
    try:
        current_spans = {span.name: span for span in parse_regions(current_text, entry.format)}
    except RegionParseError, MarkerError, NotImplementedError:
        return tuple(region_shas)
    for name in other_names:
        span = current_spans.get(name)
        if span is not None:
            region_shas.append((name, hash_content(region_body_text(current_text, span))))
    return tuple(region_shas)


def _managed_records(state: SeedState | None, manifest: Manifest, repo_root: Path) -> tuple[ManagedRecord, ...]:
    """Mirrors ``verbs/adopt.py``'s identical helper, EXTENDED (review
    finding): translates ``state.managed`` into rung 6's own input shape,
    excluding a record whose manifest entry has since been retired or
    reclassified away from ``hybrid-managed-region`` (see that module's own
    docstring) -- and, for a region-bearing record, representing every
    OTHER region the CURRENT manifest entry declares via
    ``_region_shas_for_record`` (see that function's own docstring for why
    ``adopt.py``'s single-recorded-region shape is not enough here)."""
    if state is None:
        return ()
    entries_by_id = {entry.id: entry for entry in manifest.entries}
    records: list[ManagedRecord] = []
    for artifact in state.managed:
        entry = entries_by_id.get(artifact.id)
        if artifact.inserted_region_span is not None:
            if entry is None or entry.format is None:
                continue
            records.append(
                ManagedRecord(
                    artifact_id=artifact.id,
                    path=artifact.path,
                    region_shas=_region_shas_for_record(artifact, entry, repo_root),
                    region_format=entry.format,
                )
            )
        else:
            records.append(ManagedRecord(artifact_id=artifact.id, path=artifact.path, body_sha=artifact.body_sha))
    return tuple(records)


def _wholesale_regenerate_actions(
    state: SeedState | None, manifest: Manifest, inventory: Inventory
) -> tuple[tuple[Action, ...], tuple[tuple[str, str], ...]]:
    """FR-98/FR-99's own new pass (see the module docstring's opening
    section): one ``Action`` per ``state.managed[]`` record whose CURRENT
    manifest entry's class is ``copied-managed``/``generated-derived``/
    ``hybrid-managed-region`` -- unconditionally, regardless of what
    ``classify()`` says about it (it is always ``PRESENT_CONFORMANT`` or it
    would already be in ``build_plan``'s own output). Also returns a matching
    ``(artifact_id, sha)`` pair per action, hashing the target's CURRENT
    on-disk content -- the module docstring's own "needs its own
    artifact_hashes entries" paragraph.

    Deliberately keys off the entry's CURRENT ``artifact_class`` (looked up
    fresh in ``manifest``), never the STALE wire string ``record.
    artifact_class`` recorded at the time of the last adopt/update: a
    reclassified entry should be regenerated according to what it is NOW,
    matching this package's general "the manifest is the current contract"
    stance. A record whose id no longer has ANY entry in ``manifest``
    (retired) is skipped -- there is nothing left to regenerate it as,
    mirroring ``_managed_records``'s own identical "stale record" tolerance.

    A hybrid entry's ``chosen_anchor`` names EVERY declared region, paired
    with its manifest ``anchor``'s own first matcher (unused positionally by
    this module's own commit dispatcher -- see the module docstring) --
    unlike ``build_plan``'s own ``_chosen_anchor``, which only ever names the
    NOT-YET-present ones: FR-99 requires every declared region to be
    refreshed, present or not.

    Returns ``((), ())`` when ``state is None`` (nothing has been adopted,
    so ``state.managed`` is empty) or when no record qualifies -- the
    overwhelmingly common "nothing to regenerate against yet" case."""
    if state is None:
        return (), ()
    entries_by_id = {entry.id: entry for entry in manifest.entries}
    actions: list[Action] = []
    hashes: list[tuple[str, str]] = []
    for record in state.managed:
        entry = entries_by_id.get(record.id)
        if entry is None or entry.artifact_class not in _WHOLESALE_CLASSES:
            continue
        chosen_anchor: tuple[tuple[str, str | None], ...] = ()
        is_hybrid = entry.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION
        if is_hybrid:
            chosen_anchor = tuple(
                (region.name, region.anchor[0] if region.anchor else None) for region in entry.regions
            )
        # FR-99 (only the marked span is replaced, never the whole file) is
        # a claim about a REGION -- it does not apply to a whole-file class
        # (review finding), so the rationale cites it only for the hybrid
        # case rather than unconditionally for every wholesale action.
        fr_tag = "FR-98/FR-99" if is_hybrid else "FR-98"
        actions.append(
            Action(
                artifact_id=entry.id,
                artifact_class=entry.artifact_class,
                current_state=ArtifactState.PRESENT_CONFORMANT,
                target_state=ArtifactState.PRESENT_CONFORMANT,
                target_path=entry.path,
                chosen_anchor=chosen_anchor,
                rationale=(
                    f"{entry.path!r} is a managed {entry.artifact_class.value} artifact;"
                    f" wholesale-regenerated by update ({fr_tag})"
                ),
            )
        )
        hashes.append((entry.id, hash_content(_read_text_or_blank(inventory.repo_root / entry.path))))
    return tuple(actions), tuple(hashes)


def _migration_action_hashes(repo_root: Path, migration_actions: tuple[Action, ...]) -> tuple[tuple[str, str], ...]:
    """One ``(artifact_id, sha)`` pair per action in ``migration_actions``,
    hashing the CURRENT on-disk content at each action's ``target_path`` --
    ``migrate.compose`` never does this itself (module docstring's own
    paragraph); mirrors ``verbs/adopt.py::_augment_plan_with_first_claims``'s
    identical obligation for its own first-claim actions, and the SC-07
    fixture test's own ``_fresh_fingerprint(tmp_path, ("renamed",
    hash_content("")), ...)`` construction."""
    return tuple(
        (action.artifact_id, hash_content(_read_text_or_blank(repo_root / action.target_path)))
        for action in migration_actions
    )


def _merge_plan_sources(
    *,
    build_actions: tuple[Action, ...],
    build_hashes: tuple[tuple[str, str], ...],
    migration_plan: Plan,
    migration_hashes: tuple[tuple[str, str], ...],
    wholesale_actions: tuple[Action, ...],
    wholesale_hashes: tuple[tuple[str, str], ...],
    repo_fingerprint: RepoFingerprint,
) -> Plan:
    """Merge the three action sources into one ``Plan`` sharing
    ``repo_fingerprint`` -- the SAME collision-then-sort pattern ``migrate.
    compose``'s own ``_claim`` and ``verbs/adopt.py::
    _augment_plan_with_first_claims`` already establish (module docstring).

    Raises ``InternalError`` naming any ``artifact_id`` produced by more
    than one of: ``build_plan``'s absent-entry actions, ``migrate.compose``'s
    migration actions, ``migrate.compose``'s own skipped entries (a
    ``copied-seeded`` offer), and the wholesale-regenerate actions -- a real
    collision here is a genuine authoring bug (see the module docstring's
    own Design Note), never silently resolved by picking one source's
    ``Action`` over another's.

    ``migration_hashes``/``build_hashes``/``wholesale_hashes`` are supplied
    by the caller (``_migration_action_hashes``, ``build_plan``'s own
    ``repo_fingerprint.artifact_hashes``, and ``_wholesale_regenerate_
    actions``'s own second return value, respectively) -- by the time
    ``_claim`` above has confirmed every ``artifact_id`` is unique across
    all three sources, a plain concatenation (never a set) is sufficient and
    cannot silently collapse two different shas for the same id."""
    seen: dict[str, str] = {}

    def _claim(artifact_id: str, collection: str) -> None:
        prior = seen.get(artifact_id)
        if prior is not None:
            raise InternalError(
                f"update-plan-collision: artifact_id {artifact_id!r} appears in both"
                f" {prior} and {collection} across update's merge sources -- an"
                " artifact_id may appear in at most one of build_plan's absent-entry"
                " actions, migrate.compose's migration actions/skipped entries, and"
                " the wholesale-regenerate pass",
                remedy=(
                    "fix the colliding source(s) (most likely a migration re-targeting"
                    " an artifact ordinary regeneration already covers) so no two of"
                    " update's merge sources ever target the same artifact_id"
                ),
            )
        seen[artifact_id] = collection

    for action in build_actions:
        _claim(action.artifact_id, "build_plan's absent-entry actions")
    for action in migration_plan.actions:
        _claim(action.artifact_id, "migrate.compose's migration actions")
    for skipped in migration_plan.skipped:
        _claim(skipped.artifact_id, "migrate.compose's skipped entries")
    for action in wholesale_actions:
        _claim(action.artifact_id, "the wholesale-regenerate pass")

    return Plan(
        actions=tuple(
            sorted((*build_actions, *migration_plan.actions, *wholesale_actions), key=lambda a: a.artifact_id)
        ),
        repo_fingerprint=dataclasses.replace(
            repo_fingerprint,
            artifact_hashes=tuple(
                sorted((*build_hashes, *migration_hashes, *wholesale_hashes), key=lambda pair: pair[0])
            ),
        ),
        skipped=migration_plan.skipped,
    )


def _staged_bytes_for(staged_paths: Sequence[Path], target_path: str) -> bytes:
    """Mirrors ``verbs/adopt.py``'s identical helper verbatim -- the bytes of
    whichever ``staged_paths`` entry's relative path TAILS ``target_path``."""
    target_parts = Path(target_path).parts
    matches = [candidate for candidate in staged_paths if candidate.parts[-len(target_parts) :] == target_parts]
    if not matches:
        raise InternalError(
            f"materialize() produced no staged content for {target_path!r}",
            remedy=(
                "verify the seed template tree provides content at this path -- this is a"
                " broken template installation, not a problem with the repository being"
                " updated"
            ),
        )
    if len(matches) > 1:
        raise InternalError(
            f"materialize() produced {len(matches)} staged candidates for {target_path!r}: "
            f"{[str(candidate) for candidate in matches]!r}",
            remedy=(
                "the seed template tree stages more than one file at this relative path --"
                " this is a broken template installation (ambiguous content), not a problem"
                " with the repository being updated"
            ),
        )
    return matches[0].read_bytes()


def _region_body_from_template(template_path: Path | str | None, region_name: str) -> str:
    """Mirrors ``verbs/adopt.py``'s identical helper verbatim -- see that
    module's own docstring for the full rationale (the packaged
    ``files/*.j2`` fragments are read directly, never routed through
    ``engine.copier.materialize``)."""
    if template_path is None:
        files_root = resources.files("pyforge.marshal.seed.templates") / "files"
        with resources.as_file(files_root) as real_files_dir:
            return _read_region_fragment(real_files_dir, region_name)
    return _read_region_fragment(Path(template_path) / "files", region_name)


def _read_region_fragment(files_dir: Path, region_name: str) -> str:
    """Mirrors ``verbs/adopt.py``'s identical helper verbatim."""
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
                    " not a problem with the repository being updated"
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
                        " installation, not a problem with the repository being updated"
                    ),
                )
            return text
    raise InternalError(
        f"no files/{region_name}.*.j2 region-body fragment found under {files_dir}",
        remedy=(
            "verify the seed template tree provides a files/<region-name>.*.j2 fragment"
            " for this region -- this is a broken template installation, not a problem"
            " with the repository being updated"
        ),
    )


def _region_body_for(template_path: Path | str | None, repo_root: Path, entry_id: str, region_name: str) -> str:
    """The one region-body dispatch every hybrid region in this module
    routes through: the ``projects-table`` region (``projects-index``'s
    only region) is repo-computed (Story 11.2), every other region reads
    its packaged static fragment -- mirrors ``verbs/adopt.py::_default_
    commit``'s identical, inline ``region_name == "projects-table" and
    entry.id == "projects-index"`` dispatch, factored out here as its own
    function since THIS module's commit dispatcher calls it from two
    branches (insert and substitute) rather than adopt's one."""
    if region_name == "projects-table" and entry_id == "projects-index":
        return derive_projects_index.derive_projects_table(repo_root / "_bmad-output" / "projects")
    return _region_body_from_template(template_path, region_name)


def _entry_or_raise(entries_by_id: dict[str, ManifestEntry], artifact_id: str) -> ManifestEntry:
    """``entries_by_id[artifact_id]``, or ``InternalError`` naming it --
    review finding: a bare dict index made a migration bug (an action
    targeting a retired or nonexistent manifest id) escape as an unnamed
    ``KeyError`` traceback instead of this module's own six-leaf-taxonomy
    error. Both call sites this module owns (``_update_commit``'s own
    ``commit()``, and ``_build_state_after_apply``'s post-apply state
    construction) route through this one function so the message and
    remedy cannot drift between them."""
    entry = entries_by_id.get(artifact_id)
    if entry is None:
        raise InternalError(
            f"action names artifact_id {artifact_id!r}, which the manifest does not declare",
            remedy=(
                "this is a plan/manifest inconsistency (most likely a migration targeting"
                " a retired or nonexistent manifest id) -- a broken installation, not a"
                " problem with the repository being updated"
            ),
        )
    return entry


def _update_commit(
    *,
    repo_root: Path,
    never_write: fs.NeverWrite,
    entries_by_id: dict[str, ManifestEntry],
    model_version: ModelVersion,
    answers: Mapping[str, Any],
    template_path: Path | str | None,
    force: bool,
) -> CommitAction:
    """Build the real, production ``commit`` callback ``run_update`` supplies
    to ``apply.run.run_apply`` -- see the module docstring's own sections for
    the full design. Duplicates ``verbs/adopt.py::_default_commit``'s small
    materialize/write dispatcher rather than importing it (that function is
    private to a sibling module; this package's established "small
    deliberate duplication beats reaching into a neighbour's private helper"
    convention -- see this module's own docstring), with two differences
    ``update`` genuinely needs and ``adopt`` does not:

    * The materialize verb is ``MaterializeVerb.RECOPY`` (with
      ``request.confirm=True``, FR-101's own explicit confirmation) when
      ``force`` is set, else the ordinary ``MaterializeVerb.COPY`` -- see the
      module docstring's own Always-bullet-derived rule. ``dst_path=
      repo_root`` either way: unused by ``COPY`` (module docstring of
      ``engine/copier.py``), required by ``RECOPY`` (it clones ``repo_root``
      locally to give Copier's own diff-and-merge algorithm real commit
      history to reason against).
    * A hybrid region SUBSTITUTES (``regions.apply.substitute_region``) when
      it is already present, and only INSERTS (``regions.apply.
      insert_region``) when it genuinely is not -- see the module docstring's
      own "Why substitute_region" Design Note. ``adopt``'s own dispatcher
      never needs this because it only ever handles actions whose
      ``chosen_anchor`` names NOT-yet-present regions."""
    staged: list[MaterializeResult] = []

    def _materialized() -> MaterializeResult:
        if not staged:
            staged.append(
                materialize(
                    MaterializeRequest(
                        verb=MaterializeVerb.RECOPY if force else MaterializeVerb.COPY,
                        dst_path=repo_root,
                        template_path=template_path,
                        data=dict(answers),
                        confirm=force,
                    )
                )
            )
        return staged[0]

    def commit(action: Action) -> None:
        entry = _entry_or_raise(entries_by_id, action.artifact_id)
        target = repo_root / action.target_path
        if entry.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION:
            assert entry.format is not None  # ManifestEntry.__post_init__ guarantees this
            for region_name, _matched_anchor in action.chosen_anchor:
                region = next((candidate for candidate in entry.regions if candidate.name == region_name), None)
                if region is None:
                    raise InternalError(
                        f"action names region {region_name!r}, which entry {entry.id!r} does not declare",
                        remedy=(
                            "this is a plan/manifest inconsistency -- a broken installation,"
                            " not a problem with the repository being updated"
                        ),
                    )
                text = target.read_text(encoding="utf-8") if target.is_file() else None
                existing_span = None
                if text is not None:
                    existing_span = next(
                        (span for span in parse_regions(text, entry.format) if span.name == region_name),
                        None,
                    )
                body = _region_body_for(template_path, repo_root, entry.id, region_name)
                if existing_span is None:
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
                else:
                    substitute_region(
                        text,
                        target,
                        existing_span,
                        body,
                        model_version=model_version,
                        expected_sha=existing_span.sha,
                        fmt=entry.format,
                        repo_root=repo_root,
                        never_write=never_write,
                    )
        elif (
            entry.id in derive_adapters.ADAPTER_COMPOSITION and entry.artifact_class is ArtifactClass.GENERATED_DERIVED
        ):
            content = derive_adapters.render_adapter(entry.id, template_path=template_path)
            fs.write(target, content.encode("utf-8"), repo_root=repo_root, never_write=never_write)
        else:
            result = _materialized()
            content = _staged_bytes_for(result.staged_paths, action.target_path)
            fs.write(target, content, repo_root=repo_root, never_write=never_write)

    return commit


def _read_materialized_text(target: Path, artifact_id: str) -> str:
    """The just-materialized ``target``'s UTF-8 text -- ``InternalError``
    naming ``artifact_id`` (review finding, LOW) rather than an unguarded
    ``FileNotFoundError``/``UnicodeDecodeError`` escaping this module's own
    six-leaf taxonomy when ``commit()`` did not actually leave a readable
    regular file there (a broken ``commit`` callback -- its own bug, or a
    caller-injected test double -- rather than a fact about the repository
    being updated)."""
    if not target.is_file():
        raise InternalError(
            f"artifact {artifact_id!r} was not materialized at {target} -- commit() left no regular file there",
            remedy=(
                "this indicates the commit callback silently failed to write the target it"
                " was asked to -- a broken installation, not a problem with the repository"
                " being updated"
            ),
        )
    try:
        return target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise InternalError(
            f"artifact {artifact_id!r} could not be read back from {target} after materialization: {exc}",
            remedy=(
                "this indicates the commit callback wrote unreadable or non-UTF-8 content --"
                " a broken installation, not a problem with the repository being updated"
            ),
        ) from exc


def _managed_artifact_after_apply(action: Action, entry: ManifestEntry, repo_root: Path) -> ManagedArtifact:
    """Mirrors ``verbs/adopt.py``'s identical helper -- re-reads the
    JUST-MATERIALIZED target from disk rather than trusting anything the
    ``commit`` callback might have returned (it returns nothing), via
    ``_read_materialized_text`` (review finding: a guarded read, not a bare
    ``target.read_text()``)."""
    target = repo_root / action.target_path
    if entry.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION:
        assert entry.format is not None
        text = _read_materialized_text(target, entry.id)
        spans = {span.name: span for span in parse_regions(text, entry.format)}
        if not action.chosen_anchor:
            return ManagedArtifact(
                id=entry.id,
                path=entry.path,
                artifact_class=entry.artifact_class.value,
                body_sha=hash_content(text),
                inserted_region_span=None,
            )
        # `state/store.py`'s own pre-existing schema limit: `ManagedArtifact`
        # carries at most ONE `inserted_region_span`, so this module records
        # the first declared region, matching `verbs/adopt.py`'s identical
        # limitation -- `update`'s own wholesale-regenerate `chosen_anchor`
        # names EVERY declared region (unlike adopt's), but the recorded
        # state can still only ever hold one.
        region_name = action.chosen_anchor[0][0]
        span = spans.get(region_name)
        if span is None:
            raise InternalError(
                f"region {region_name!r} was not found in {entry.path!r} immediately after update",
                remedy=(
                    "this indicates the region write silently failed to insert/substitute"
                    " the region it was asked to -- a broken installation, not a problem"
                    " with the repository being updated"
                ),
            )
        body = region_body_text(text, span)
        return ManagedArtifact(
            id=entry.id,
            path=entry.path,
            artifact_class=entry.artifact_class.value,
            body_sha=hash_content(body),
            inserted_region_span=RegionSpanRecord(name=span.name, start=span.body_span[0], end=span.body_span[1]),
        )
    content = _read_materialized_text(target, entry.id)
    return ManagedArtifact(
        id=entry.id,
        path=entry.path,
        artifact_class=entry.artifact_class.value,
        body_sha=hash_content(content),
        inserted_region_span=None,
    )


def _migration_version_sort_key(version: str) -> tuple[int, object]:
    """A sort key for one ``migrations_applied`` entry that never raises --
    review finding, defense in depth. ``SeedState.__post_init__`` already
    guarantees every entry a NORMALLY-constructed ``SeedState`` carries is
    ``ModelVersion``-parseable, but nothing this function controls prevents
    a hand-built ``SeedState`` (``object.__setattr__``, the same bypass this
    package's own tests use elsewhere) or a future schema revision that
    stops enforcing it at read time. An unparseable entry sorts LAST (by its
    own literal string, deterministic and stable) rather than crashing the
    state WRITE after a successful, already-applied run -- losing sort
    position is a far smaller cost than losing the apply's own result.
    Tuple-first-element separation (``0`` vs ``1``) keeps every comparison
    within one type: two parsed entries compare as ``ModelVersion``, two
    unparseable ones as ``str``, and the two groups never cross-compare."""
    try:
        return (0, ModelVersion.parse(version))
    except ValueError:
        return (1, version)


def _build_state_after_apply(
    *,
    plan: Plan,
    state: SeedState,
    inventory: Inventory,
    entries_by_id: dict[str, ManifestEntry],
    repo_root: Path,
    manifest: Manifest,
    migrations: tuple[migrate_registry.Migration, ...],
) -> SeedState:
    """The ``SeedState`` ``run_update`` writes after a successful, NON-EMPTY
    apply against an ALREADY-established repo (``state is not None`` -- see
    the module docstring's own paragraph on why a never-established repo
    never reaches this function at all).

    ``mode``/``adopted_at``/``agents``/``skips``/``opted_out`` are carried
    over UNCHANGED -- ``update`` "moves ``model_version`` without
    re-establishing origin" (the packaged ``state/schema.json``'s own words
    for ``mode``'s enum). ``model_version`` becomes ``manifest.model_version``
    (the bundled version): reaching this function at all means ``migrate.
    registry.chain`` either found the repo already there or successfully
    walked every step to it. ``migrations_applied`` gains every migration
    JUST applied this run (``migrations``'s own ``to_version``s), unioned
    with what was already recorded, sorted by parsed version."""
    touched_ids = frozenset(action.artifact_id for action in plan.actions)
    carried_over = tuple(record for record in state.managed if record.id not in touched_ids)
    new_records = tuple(
        _managed_artifact_after_apply(action, _entry_or_raise(entries_by_id, action.artifact_id), repo_root)
        for action in plan.actions
    )
    managed = tuple(sorted((*carried_over, *new_records), key=lambda record: record.id))
    legacy = tuple(
        LegacyArtifact(id=record.entry_id, path=record.path, legacy_of=record.legacy_of) for record in inventory.legacy
    )
    newly_applied = {str(migration.to_version) for migration in migrations}
    migrations_applied = tuple(sorted({*state.migrations_applied, *newly_applied}, key=_migration_version_sort_key))
    now = utc_timestamp()
    return SeedState(
        model_version=manifest.model_version,
        seed_model_version=seed_model_version(),
        adopted_at=state.adopted_at,
        last_update=now,
        mode=state.mode,
        agents=state.agents,
        managed=managed,
        skips=state.skips,
        legacy=legacy,
        migrations_applied=migrations_applied,
        opted_out=state.opted_out,
    )


def run_update(
    repo_root: Path,
    manifest: Manifest,
    *,
    run: bool = False,
    force: bool = False,
    include_seeded: bool = False,
    yes: bool = False,
    confirm: Callable[[], bool],
    template_path: Path | str | None = None,
    commit: CommitAction | None = None,
) -> UpdateResult:
    """Compose ``resolve -> detect -> plan -> confirm -> apply -> state-write``
    against ``repo_root``, writing ``.marshal/plan.json`` unconditionally and
    ``.marshal/seed-state.yml`` only after a successful, non-empty apply
    against an already-established repo -- see the module docstring for the
    full ordering rationale and the three-source merge this function
    implements.

    ``confirm`` has no default (production callers, ``cli/seed.py``, always
    supply one) -- mirrors ``verbs/adopt.py::run_adopt``'s identical seam.
    Consulted once, when ``run and not yes`` -- the SAME confirmation seam
    ``--force --run`` relies on for FR-101's explicit recopy confirmation
    (module docstring's own paragraph): there is no second, force-specific
    prompt.

    ``template_path``/``commit`` are the identical test-injection seams
    ``run_adopt`` establishes, for the identical reason (exercising the REAL
    ``_update_commit`` against a synthetic template tree, or bypassing
    materialize/regions entirely).

    Raises whatever ``read_state``/``migrate_registry.chain``/``migrate_
    registry.compose``/``check_preconditions``/``run_apply`` raise,
    unchanged -- this function adds no ``try``/``except`` of its own (the
    I/O Matrix's own "migration chain gap" row: ``InternalError`` propagates
    unwrapped through to ``cli/seed.py``'s widened ``except SeedError``).
    Also raises ``InternalError`` directly, via ``_merge_plan_sources``'s
    own ``_claim`` (``update-plan-collision``, review finding -- omitted
    from an earlier draft of this enumeration) when the three merge sources
    genuinely collide on an ``artifact_id`` despite the disjointness this
    function otherwise enforces before merging (see the module docstring's
    own "Making the three sources ACTUALLY disjoint" Design Note)."""
    filtered_manifest = _manifest_for_update(manifest)
    ref_findings = referenced_dep_findings(filtered_manifest, repo_root)
    state = read_state(repo_root)
    inventory = classify(filtered_manifest, repo_root)

    never_write = fs.NeverWrite(
        patterns=tuple(sorted(effective_never_write(filtered_manifest, inventory))),
        exempt=writable_exemptions(filtered_manifest, inventory),
    )

    opted_out = frozenset(state.opted_out) if state is not None else frozenset()
    base_plan = build_plan(filtered_manifest, inventory, opted_out=opted_out)

    # `build_plan` is entirely state-independent (its own module docstring:
    # "no read of .marshal/seed-state.yml") -- it classifies purely off live
    # disk content, so it can genuinely propose an action for an id that
    # ALREADY has a `state.managed[]` record (a renamed artifact: its
    # CURRENT manifest path is absent on disk because the migration that
    # will populate it has not run yet). The Design Note's own "build_plan's
    # ABSENT-only actions cover entries with NO state.managed[] record" is
    # therefore an invariant THIS function must enforce, not one build_plan
    # already holds -- an id with a managed record belongs to the
    # wholesale-regenerate pass (or, if a migration also claims it this run,
    # to the migration), never to build_plan's "genuinely new" territory.
    managed_ids = frozenset(record.id for record in state.managed) if state is not None else frozenset()
    build_actions = tuple(action for action in base_plan.actions if action.artifact_id not in managed_ids)
    build_action_ids = {action.artifact_id for action in build_actions}
    build_hashes = tuple(pair for pair in base_plan.repo_fingerprint.artifact_hashes if pair[0] in build_action_ids)

    migrations = (
        ()
        if state is None
        else migrate_registry.chain(state, filtered_manifest.model_version, registry=migrate_registry.MIGRATIONS)
    )
    migration_plan = (
        migrate_registry.compose(
            migrations,
            inventory,
            state,
            repo_fingerprint=base_plan.repo_fingerprint,
            repo_root=repo_root,
            never_write=never_write,
            include_seeded=include_seeded,
        )
        if state is not None
        else Plan(actions=(), repo_fingerprint=base_plan.repo_fingerprint, skipped=())
    )
    migration_hashes = _migration_action_hashes(repo_root, migration_plan.actions)

    wholesale_actions_raw, wholesale_hashes_raw = _wholesale_regenerate_actions(state, filtered_manifest, inventory)
    # Symmetric exclusion: a migration this run ALREADY claims an id (in its
    # own actions or its own `copied-seeded` offers) supersedes the generic
    # "refresh to latest template" wholesale-regenerate treatment for that
    # SAME id -- the migration's own logic is what actually absorbs the
    # breaking change; a redundant wholesale action for the identical
    # artifact would either collide outright or silently race it.
    migration_claimed_ids = frozenset(action.artifact_id for action in migration_plan.actions) | frozenset(
        skipped.artifact_id for skipped in migration_plan.skipped
    )
    wholesale_actions = tuple(
        action for action in wholesale_actions_raw if action.artifact_id not in migration_claimed_ids
    )
    wholesale_hashes = tuple(pair for pair in wholesale_hashes_raw if pair[0] not in migration_claimed_ids)

    plan = _merge_plan_sources(
        build_actions=build_actions,
        build_hashes=build_hashes,
        migration_plan=migration_plan,
        migration_hashes=migration_hashes,
        wholesale_actions=wholesale_actions,
        wholesale_hashes=wholesale_hashes,
        repo_fingerprint=base_plan.repo_fingerprint,
    )

    managed_records = _managed_records(state, filtered_manifest, repo_root)
    check_preconditions(
        plan,
        repo_root=repo_root,
        never_write=never_write,
        managed=managed_records,
        force=force,
        dry_run=not run,
    )

    write_plan(plan, default_plan_path(repo_root))

    if not run:
        return UpdateResult(plan=plan, applied=None, declined=False, referenced_dep_findings=ref_findings)

    if not yes and not confirm():
        return UpdateResult(plan=plan, applied=None, declined=True, referenced_dep_findings=ref_findings)

    entries_by_id = {entry.id: entry for entry in filtered_manifest.entries}

    effective_commit = commit
    if effective_commit is None:
        effective_commit = _update_commit(
            repo_root=repo_root,
            never_write=never_write,
            entries_by_id=entries_by_id,
            model_version=filtered_manifest.model_version,
            answers={
                "model_version": str(filtered_manifest.model_version),
                "seed_model_version": seed_model_version(),
                "mode": state.mode if state is not None else "adopt",
                "agents": list(state.agents) if state is not None else [],
            },
            template_path=template_path,
            force=force,
        )

    # Refuse loudly if anything OTHER than this run's own known
    # `.marshal/plan.json` write is dirty right now -- see
    # `_unexpected_dirt_since_plan_write`'s own docstring (mirrors
    # `verbs/adopt.py`'s identical, already-documented-at-length mechanism).
    _unexpected_dirt_since_plan_write(repo_root)

    apply_plan = dataclasses.replace(
        plan,
        repo_fingerprint=dataclasses.replace(plan.repo_fingerprint, dirty=_repo_is_dirty_now(repo_root)),
    )

    result: ApplyResult = run_apply(apply_plan, repo_root=repo_root, never_write=never_write, commit=effective_commit)

    if state is not None and plan.actions:
        new_state = _build_state_after_apply(
            plan=plan,
            state=state,
            inventory=inventory,
            entries_by_id=entries_by_id,
            repo_root=repo_root,
            manifest=filtered_manifest,
            migrations=migrations,
        )
        write_state(new_state, repo_root=repo_root, never_write=never_write)

    return UpdateResult(plan=plan, applied=result.applied, declined=False, referenced_dep_findings=ref_findings)
