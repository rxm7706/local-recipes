"""The migration registry and runner (Story 11.3, architecture AD-62,
FR-96/FR-97, epics P-12/SC-07).

``plan/build.py``'s own docstring already forward-references this module:
``Action.target_state`` is typed as the full ``ArtifactState`` enum rather
than narrowed to ``PRESENT_CONFORMANT`` alone, "so a future story adding a
different target state (e.g. a migration's own plan-producing function,
AD-62) is not a breaking change to this dataclass's shape." Nothing before
this story absorbed a breaking model-version change (a renamed managed
artifact, a tier-rule change) into an installed repo -- that was a manual,
per-repo chore, exactly the drift class the seed installer exists to
eliminate. This module is the registry and the two pure functions
(``chain``, ``compose``) that turn a set of registered migrations into one
reviewable ``Plan``, in the SAME shape ``apply/run.py::run_apply`` already
consumes -- so a future caller (Story 11.4's ``marshal seed update``) hands
this module's output straight to the existing apply path, never a new one.

**Why a strict linear chain, not a general graph.** The epics AC describes
"the chain from ``state.model_version`` to the bundled model version" as a
single path, and "ordered, once-only migrations" implies one migration per
version-hop, not branching alternatives (this story's own Never bullet
rules out a general graph-search resolver). ``chain`` therefore does one
thing: starting at ``state.model_version``, repeatedly look up the
migration whose ``from_version`` equals the CURRENT position, follow it to
its ``to_version``, and repeat until the current position equals
``bundled_version`` -- raising a named, non-silent error the moment no such
migration exists while the current position is still short of the target.
A registry that registers more than one migration sharing a ``from_version``
raises ``InternalError`` naming the duplicate at lookup-table construction
time (review finding, revised from an earlier draft that let a plain
``dict`` comprehension's own last-write-wins semantics silently pick one and
hide the other) -- the epics AC's own "one migration per version-hop" is
enforced here, not merely assumed of the registry's author. ``MIGRATIONS``
is empty in this story, so nothing here can yet violate it, but the guard
exists for the first future story that registers real entries.

**``chain`` walks first, excludes second.** The Always bullet's own
"``chain()`` excludes any migration whose ``to_version`` is already present"
in ``state.migrations_applied[]`` is a SEPARATE filter from the walk itself,
not a short-circuit inside it: the walk always computes the full linear path
from ``state.model_version`` to ``bundled_version`` (so a gap anywhere along
that path is still reported, even if an EARLIER step happens to already be
applied), and only once that full path is known does ``chain`` drop the
steps ``state.migrations_applied`` already names. This is what makes
"running the chain-then-compose sequence twice against the same, now-updated
state computes an EMPTY chain the second time" true even when a caller
never advances ``state.model_version`` itself between the two calls (a
future Story 11.4 concern this module does not assume) -- ``chain`` is
correct against ``migrations_applied`` alone.

**``compose``'s never-write guard runs at PLAN time, never only at apply
time.** ``fs.check_never_write`` (Story 11.3's own addition to ``fs.py``,
wrapping ``_guard``'s existing check-only logic) is called once per proposed
``Action``, inside the same loop that concatenates them -- so a violation
raises immediately, before ``compose`` can return a ``Plan`` that would only
fail once a future caller handed it to ``apply/run.py::run_apply``. This is
the identical rule ``write``/``replace_span``/``remove`` enforce at real
write time, asked one layer earlier.

**Why ``Plan.skipped``/``SkippedArtifact`` for the seeded-offer case,
investigated rather than assumed.** ``plan/types.py``'s ``SkippedArtifact``
was read in full before this decision was made (this story's own Never
bullet requires it): it carries exactly three fields --
``artifact_id``/``target_path``/``pattern`` -- with NO separate "reason"
field to extend, contrary to what a first read of the epics AC's "offered,
never imposed" framing might suggest. It does not need one: ``pattern`` is
already documented as free text a human reads in a reviewed ``plan.json``
("the glob that matched"), not a value anything downstream re-parses as a
real glob -- ``apply_skips``'s own only consumer, in ``seed/verbs/skips.py``,
never round-trips it through ``fnmatch`` again. Reusing that same field with
the literal string ``"--include-seeded"`` communicates the identical fact a
``--skip`` glob does ("here is the reason this artifact is not in
``actions``"), without widening ``Plan``'s shape for every other consumer
(``apply/run.py``, ``verbs/adopt.py``) that already depends on it not
growing a fourth field. No new dataclass field, no new enum value (there is
no enum to extend) -- exactly the Never bullet's own preferred outcome.

**``RepoView`` is ``detect.inventory.Inventory``, reused directly, not a new
parallel type.** ``Inventory`` was read in full before this decision too:
``classify(bundled_manifest, repo_root)`` already answers "what does this
manifest entry actually look like in the target repo right now" -- exactly
what a migration function needs to decide whether a target artifact already
exists at its old path, or already conforms to its new one, without being
handed write access. A migration operates against the SAME repo a normal
``build_plan`` call would (both read the tree once, via ``classify``), so
building a second, narrower read-model here would duplicate ``Inventory``'s
own ``repo_root``/``tree`` fields for no behavioural gain -- ``migrate``
sits beside ``plan`` in the module-dependency chain (``plan/build.py``
already imports ``detect.inventory``; this module does too), so the import
introduces no new layering. A future caller builds ``view`` the same way
``build_plan`` builds its own classification: ``classify(bundled_manifest,
repo_root)``, passed straight through to ``chain``/``compose`` alongside
``state``.

**Why the gap error is ``InternalError`` (exit 10), not ``PreconditionFailure``
(exit 3).** ``PreconditionFailure``'s own docstring frames itself around
properties OF THE REPO (a dirty worktree, a target that is not a git repo,
hand-edited managed content) -- a migration-chain gap is not a fact about
the repo at all, it is a fact about whether the SHIPPED registry can bridge
``state.model_version`` to ``bundled_version``. That is the same class of
failure ``state/store.py``'s ``_schema_text``/``_load_schema``/
``_opt_out_pattern`` already raise ``InternalError`` for: a broken or
incomplete PACKAGED artifact, not a problem with this repository. The
remedy therefore points at upgrading the installed ``pyforge-marshal``
(or filing an issue), never at the repo itself.

Never in this module (mirroring every sibling ``detect``/``plan`` module's
own Never boundary): no CLI wiring, no ``cli/seed.py`` import or edit
(Story 11.4's own surface); no call into ``apply/run.py`` -- ``compose``
returns a ``Plan``, it never applies one; no filesystem WRITE of any kind
(every guarded ``fs`` primitive this module reaches is the read-only
``check_never_write``); no state persistence -- ``chain``/``compose`` both
take ``state`` as an already-read, immutable value and never call
``state.write_state`` or mutate ``state.migrations_applied`` themselves
(recording an applied migration is the future caller's job, exactly like
``plan/build.py``'s own opt-out "record-before-plan" obligation is stated on
its CALLER, not performed here).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .. import fs
from ..detect.inventory import Inventory
from ..errors import InternalError, PreconditionFailure
from ..model.manifest import ArtifactClass
from ..model.version import ModelVersion
from ..plan.types import Action, Plan, RepoFingerprint, SkippedArtifact
from ..state import SeedState

#: A migration function's read-only view of the target repo -- reused
#: directly from ``detect.inventory.Inventory`` rather than a new, parallel
#: type (see the module docstring's own Design Note). A future caller builds
#: it the same way ``plan/build.py::build_plan`` builds its own
#: classification: ``classify(bundled_manifest, repo_root)``.
RepoView = Inventory

#: ``SkippedArtifact.pattern``'s literal value for a ``copied-seeded``
#: action ``compose`` routes to ``Plan.skipped`` (see the module docstring's
#: own Design Note on why this reuses the field rather than widening the
#: dataclass). Named as a flag string, not a real glob -- nothing downstream
#: re-parses it as one. Worded to stay honest even rendered through
#: `cli/seed.py::_render_plan_text`'s existing, UNCHANGED-by-this-story
#: template (`f"matched --skip {pattern!r}"`) -- review finding: the
#: original literal `"--include-seeded"` rendered as `"matched --skip
#: '--include-seeded'"`, falsely implying a `--skip` glob argument was
#: given. This wording still sits inside that same "matched --skip %r"
#: sentence (a proper fix needs a dedicated migration-offer render branch in
#: `cli/seed.py`, outside this story's Never bullet -- filed as
#: DW-FU-11-3), but at least states the real fact plainly.
_SEEDED_OFFER_PATTERN = "* (offered by a migration; not applied without --include-seeded)"


@dataclass(frozen=True)
class Migration:
    """One registered version-hop: a pure ``fn(view, state) -> Plan`` that
    absorbs the breaking change between ``from_version`` and ``to_version``.

    ``fn`` performs reads only -- it never calls ``fs.write``/
    ``replace_span``/``remove``/``symlink`` (P-12; proven by a write-blocking
    fixture test, ``tests/unit/test_seed_migrate_registry.py``). Every
    effect it wants to have is expressed as an ``Action`` inside the ``Plan``
    it returns; ``compose`` (this module) or a future caller (Story 11.4)
    applies those actions through the existing ``apply/run.py::run_apply``
    -- ``fn`` itself never does.

    ``fn``'s own returned ``Plan.repo_fingerprint`` is never read by
    ``compose``: the composed ``Plan`` shares exactly ONE fingerprint, the
    caller-supplied ``repo_fingerprint`` argument, matching the epics AC's
    "composed into a single ``Plan``". ``fn`` may therefore construct any
    well-typed placeholder there (this module's own tests use
    ``RepoFingerprint(git_head=None, dirty=True, artifact_hashes=())``, the
    same non-git-target fallback ``plan/build.py::build_plan`` itself
    produces) -- it is discarded, never validated.

    ``__post_init__`` requires ``from_version < to_version`` (review finding,
    verified by execution): without this, a self-referencing entry
    (``from_version == to_version``) or a registry cycle (A -> B -> A) makes
    ``chain``'s walk loop forever -- reproduced live, an actual hang, not
    merely a logic error. Requiring strict progress on every registered hop
    makes a cycle structurally impossible (a strictly increasing sequence of
    versions can never revisit one it has already passed), so this one check
    is the real fix; ``chain``'s own additional visited-set guard (see its
    docstring) is defense in depth for a hop that somehow reaches it anyway."""

    from_version: ModelVersion
    to_version: ModelVersion
    fn: Callable[[RepoView, SeedState], Plan]

    def __post_init__(self) -> None:
        if not self.from_version < self.to_version:
            raise ValueError(
                f"Migration.from_version ({self.from_version}) must be strictly less than"
                f" Migration.to_version ({self.to_version}) -- a migration must make strict"
                " forward progress, or a chain through it can never terminate"
            )


#: The registry: every migration this installed ``pyforge-marshal`` knows
#: how to run, in no particular order (``chain`` looks each one up by its
#: ``from_version``, never iterates this tuple positionally). Empty by
#: default -- a real migration is a future model-version-bump's own story to
#: register, not this one's: S-11.3 ships the machinery, not a migration.
MIGRATIONS: tuple[Migration, ...] = ()


def chain(
    state: SeedState,
    bundled_version: ModelVersion,
    *,
    registry: tuple[Migration, ...] = MIGRATIONS,
) -> tuple[Migration, ...]:
    """The ordered migrations needed to bring ``state.model_version`` to
    ``bundled_version``, walked strictly linearly through ``registry`` and
    filtered against ``state.migrations_applied[]`` (see the module
    docstring's own two Design Notes for both halves).

    Returns ``()`` when ``state.model_version`` already equals
    ``bundled_version`` -- the walk below never even starts (AD-60's own
    "idempotence is defined as plan-emptiness" pattern, applied here to the
    migration path rather than a whole ``Plan``).

    Raises ``InternalError`` (exit 10; see the module docstring's own Design
    Note on why this is the right leaf) naming the exact missing
    ``from_version`` step the moment the walk reaches a version with no
    registered migration to continue from, while that version is still short
    of ``bundled_version`` -- never a silent partial chain.

    Also raises ``InternalError`` (review finding) when two registry entries
    share the same ``from_version`` -- the module docstring's earlier
    "last-write-wins" framing described a genuine but never-actually-desired
    ambiguity (a duplicate ``from_version`` means the registry's own
    "one migration per version-hop" convention was violated by whoever wrote
    it); reporting it loudly here, at lookup-table construction time, is
    strictly better than silently picking one and hiding the other. And even
    with ``Migration.__post_init__``'s new strict-progress guard making a
    cycle structurally impossible for any WELL-FORMED registry, this walk
    still tracks ``visited`` versions and raises rather than loops if a
    version is ever revisited -- defense in depth, not redundant: it is what
    stands between a future, differently-shaped registry bug and an actual
    process hang, exactly the failure this function existed to prevent from
    ever reaching a caller silently."""
    if len({migration.from_version for migration in registry}) != len(registry):
        seen: set[ModelVersion] = set()
        duplicate = next(
            migration.from_version
            for migration in registry
            if migration.from_version in seen or seen.add(migration.from_version)
        )
        raise InternalError(
            f"migration-registry-ambiguous: more than one migration is registered with"
            f" from_version={duplicate!s} -- the migration registry must register at most"
            " one migration per from_version",
            remedy="fix the registered migrations so each from_version appears at most once",
        )
    by_from = {migration.from_version: migration for migration in registry}
    current = state.model_version
    visited: set[ModelVersion] = {current}
    steps: list[Migration] = []
    while current != bundled_version:
        migration = by_from.get(current)
        if migration is None:
            raise InternalError(
                f"migration-chain-gap: no migration is registered with"
                f" from_version={current!s} -- state is at {state.model_version!s}, the"
                f" bundled model version is {bundled_version!s}, and the registered"
                " migrations do not form a continuous path between them",
                remedy=(
                    "upgrade pyforge-marshal to a version whose migration registry covers"
                    f" this gap (missing step: from_version={current!s}), or file an issue"
                    " against pyforge-marshal naming the gap"
                ),
            )
        steps.append(migration)
        current = migration.to_version
        if current in visited:
            raise InternalError(
                f"migration-chain-cycle: the registered migrations form a cycle back to"
                f" version {current!s} without ever reaching {bundled_version!s} -- this"
                " should be structurally impossible (Migration.__post_init__ requires"
                " strict forward progress) and indicates a bug in the migration registry"
                " itself, not the repository being migrated",
                remedy="file an issue against pyforge-marshal naming the cycle",
            )
        visited.add(current)
    applied = {ModelVersion.parse(entry) for entry in state.migrations_applied}
    return tuple(step for step in steps if step.to_version not in applied)


def compose(
    migrations: tuple[Migration, ...],
    view: RepoView,
    state: SeedState,
    *,
    repo_fingerprint: RepoFingerprint,
    repo_root: Path,
    never_write: fs.NeverWrite,
    include_seeded: bool = False,
) -> Plan:
    """Run every migration in ``migrations``, in order, and concatenate
    their actions into one ``Plan`` sharing ``repo_fingerprint`` -- the same
    ``Plan`` shape ``apply/run.py::run_apply`` already consumes.

    Each migration's own ``fn(view, state)`` is called once, in ``migrations``
    order (``chain``'s own return order -- ``compose`` never re-sorts or
    re-derives it). Every action it returns is validated, in this order,
    BEFORE this function decides where the action belongs:

    1. **Escaping-target refusal** (review finding, verified by execution):
       an absolute or ``..``-traversing ``target_path`` is refused with the
       identical rule ``apply/run.py::run_apply`` already enforces --
       duplicated here rather than imported (``compose`` never imports
       ``apply/run.py``, per this module's own Never boundary; this
       package's established "small deliberate duplication beats an import
       across a module boundary" trade, matching ``derive.adapters.
       _read_fragment``'s own precedent) -- so a migration's own malformed
       path is refused at PLAN time, not only once a future caller hands the
       composed ``Plan`` to ``run_apply``.
    2. **Never-write refusal** via ``fs.check_never_write``, unchanged from
       the original design -- a violation raises ``NeverWriteViolation``
       immediately, so a caller never receives a composed ``Plan`` that would
       only fail once handed to ``run_apply`` (AD-62's own "fails at plan
       time, not apply time").

    An action whose ``artifact_class`` is ``ArtifactClass.COPIED_SEEDED`` is
    routed to ``Plan.skipped`` (as a ``SkippedArtifact``, see the module
    docstring's own Design Note and ``_SEEDED_OFFER_PATTERN``'s own comment)
    rather than ``Plan.actions``, unless ``include_seeded`` is ``True``, in
    which case it is treated like any other action. Every other
    ``artifact_class`` always lands in ``Plan.actions``. A migration's own
    returned ``Plan.skipped`` (entries IT already decided to skip, for its
    own reasons, unrelated to the seeded-offer routing above) is also merged
    into the result unchanged (review finding: an earlier draft silently
    dropped this).

    Raises ``InternalError`` naming the offending id (review finding,
    verified by execution) when the concatenated result would carry the same
    ``artifact_id`` more than once -- across ``actions``, across ``skipped``,
    or split between the two -- mirroring ``Plan.from_json_dict``'s own
    "an artifact_id may appear in actions or skipped, never both" invariant.
    That check only runs at the JSON round-trip boundary; migrations are
    independently authored, in-memory ``Plan`` producers with no such
    boundary of their own, so nothing else would catch two migrations
    (or one migration's own actions) colliding on an id before ``run_apply``
    consumed the contradiction directly.

    Both ``actions`` and ``skipped`` are returned sorted by ``artifact_id``,
    matching ``Plan``'s own general "sorted, deterministic" convention
    (``plan/build.py::build_plan``'s identical re-sort) -- ``migrations``
    order governs which migration's action wins a spot in the pre-sort list,
    but the FINAL ``Plan`` is ordered by id like every other producer's
    output."""
    actions: list[Action] = []
    skipped: list[SkippedArtifact] = []
    seen_ids: dict[str, str] = {}

    def _claim(artifact_id: str, collection: str) -> None:
        prior = seen_ids.get(artifact_id)
        if prior is not None:
            raise InternalError(
                f"migration-plan-collision: artifact_id {artifact_id!r} appears in both"
                f" {prior} and {collection} across the composed migrations -- an"
                " artifact_id may appear at most once in a composed Plan",
                remedy=(
                    "fix the colliding migration(s) so no two actions -- across any"
                    " combination of migrations -- target the same artifact_id"
                ),
            )
        seen_ids[artifact_id] = collection

    resolved_root = repo_root.resolve()
    for migration in migrations:
        migration_plan = migration.fn(view, state)
        for action in migration_plan.actions:
            # Escaping-target refusal -- literal check first, then resolve,
            # mirroring apply/run.py::run_apply's own hardened, execution-
            # verified sequence exactly (see this function's own docstring).
            if Path(action.target_path).is_absolute() or ".." in Path(action.target_path).parts:
                raise PreconditionFailure(
                    f"escaping-target: migration action {action.artifact_id!r} names"
                    f" target_path {action.target_path!r}, which is absolute or traverses"
                    " upward -- a target must be a normalized repo-relative path",
                    remedy="fix the migration function to return a normalized target_path",
                )
            target = repo_root / action.target_path
            try:
                resolved = target.resolve()
            except (OSError, ValueError) as failure:
                raise PreconditionFailure(
                    f"unusable-target: migration action {action.artifact_id!r} names"
                    f" target_path {action.target_path!r}, which cannot be resolved to a"
                    f" path -- {failure!r}",
                    remedy="fix the migration function to return a resolvable target_path",
                ) from failure
            if resolved_root not in resolved.parents:
                raise PreconditionFailure(
                    f"escaping-target: migration action {action.artifact_id!r} names"
                    f" target_path {action.target_path!r}, which resolves to {resolved} --"
                    f" not a path strictly inside {resolved_root}",
                    remedy="fix the migration function to return a normalized target_path",
                )
            fs.check_never_write(target, repo_root=repo_root, never_write=never_write)
            if action.artifact_class is ArtifactClass.COPIED_SEEDED and not include_seeded:
                _claim(action.artifact_id, "skipped")
                skipped.append(
                    SkippedArtifact(
                        artifact_id=action.artifact_id,
                        target_path=action.target_path,
                        pattern=_SEEDED_OFFER_PATTERN,
                    )
                )
            else:
                _claim(action.artifact_id, "actions")
                actions.append(action)
        for entry in migration_plan.skipped:
            _claim(entry.artifact_id, "skipped")
            skipped.append(entry)
    return Plan(
        actions=tuple(sorted(actions, key=lambda action: action.artifact_id)),
        repo_fingerprint=repo_fingerprint,
        skipped=tuple(sorted(skipped, key=lambda entry: entry.artifact_id)),
    )
