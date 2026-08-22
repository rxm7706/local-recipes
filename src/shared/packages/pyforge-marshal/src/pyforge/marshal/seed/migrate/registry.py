"""The migration registry and runner (Story 11.3, architecture FR-96/FR-97,
AD-62, P-12).

`plan.build.build_plan` only ever sees the CURRENT manifest's entries (its
version-filter already drops anything retired by `since`/`until`), so it can
materialize a newly-added artifact but has no way to know an old one was
renamed away, and it never re-renders a `hybrid-managed-region`/
`copied-managed` artifact whose STRUCTURE is already present but whose
CONTENT reflects a stale rule -- `classify()` is purely structural
(AD-59/AD-60), never a content comparison against a NEW template. This
module is what turns a breaking change to the bundled seed model into an
executable, reviewable change for an already-adopted repo: a `RepoView`
read-only carrier, a `Migration` record (`from_version`/`to_version`/`migrate`
callable), a semver-ordered chain selector with a named-gap error, and a
runner that composes each selected migration's own self-fingerprinted `Plan`
into one combined `Plan` plus a derived `offered_artifact_ids` set -- handed
to the SAME `apply.run.run_apply` path every other verb uses.

**P-12: pure functions, never a write.** Every `migrate()` implementation is
`def migrate(repo: RepoView, state: SeedState) -> Plan` -- it reads
(`repo.repo_root`, `repo.manifest`, `state`) and RETURNS data; it performs no
write of any kind, directly or through `fs`/`engine.copier`/`regions.apply`.
`run_migrations` itself never imports `seed.fs` (or any of `seed.apply`,
`seed.verbs`, `seed.cli`) for the identical reason -- this module only ever
COMPUTES a `Plan`; nothing under `seed/migrate/` ever writes to a target
repo. `tests/unit/test_seed_migrate_registry.py`'s write-blocking fixture
(monkeypatching `seed.fs.write`/`replace_span`/`remove`/`symlink` to raise)
proves this the same way the rest of this package's purity guarantees are
proven -- by execution, not merely by import-surface inspection.

**`REGISTERED_MIGRATIONS` ships empty.** The packaged `templates/manifest.yaml`
is still at `model_version: "1.0.0"`, so there is no real breaking change to
migrate TOWARD yet -- shipping a fabricated migration into the production
registry would corrupt every real adopting repo the moment a future manifest
bump made it eligible. This story's own SC-07 proof is therefore a
test-local `Migration` passed via `run_migrations(..., migrations=(fixture,))`,
never added here.

**Why `RepoView` is new, minimal data rather than reusing
`detect.inventory.Inventory`.** `Inventory` is `classify()`'s OWN computed
output -- `repo_root` + `tree` + `classifications` + `legacy`, all already
resolved against ONE specific manifest's entries. A migration needs the
manifest itself (to resolve a NEW artifact's declared path/class, or to check
whether a touched id is `copied-seeded`), not a pre-computed classification
against it -- and forcing every `migrate()` author to first run `classify()`
(a `detect`-layer call) just to get a `repo_root` would tie every migration
to running full detection whether or not it needs it. `RepoView` is the
narrower, honest shape: exactly what AD-62's signature `(repo, state) -> Plan`
needs and nothing computed.

**The never-write pre-check is deliberately narrower than `fs.py`'s own
guard.** A composed action whose `target_path` matches one of
`repo.manifest.never_write`'s glob patterns raises `NeverWriteViolation`
before any `Plan` is returned -- a plan-time, best-effort pre-check. It does
NOT replicate `detect.inventory`'s exemption-widening for a manifest-declared
writable path that also matches a broader glob (`fs.NeverWrite.exempt`),
and it never resolves `target_path` against the filesystem the way
`fs._guard` does. `fs.py`'s own guard remains the real, authoritative
enforcement point at actual write time regardless of what this pre-check
catches or misses -- stated here explicitly rather than left to look like an
oversight.

**Never** imports `seed.apply`, `seed.verbs`, or `seed.cli` (upward imports
forbidden; architecture's `cli -> verbs -> (detect, plan, apply, migrate) ->
(model, state, regions, engine, derive) -> fs`). `detect`/`plan` ARE
same-tier siblings and may be imported (`plan.types` for
`Plan`/`Action`/`RepoFingerprint`; `detect.hashes.hash_content` for
fingerprint hashing) -- but never a neighbour's leading-underscore name (this
package's established "duplicate a small private helper rather than reach
across a module boundary for it" convention, e.g. `state/store.py`'s own
`_StrictLoader` docstring): `_git_head`/`_repo_is_dirty` below mirror
`plan.build`'s identically-named private helpers rather than importing them,
and the never-write matcher below is a fresh, narrower spelling rather than a
reach into `fs.py`'s private `_matches`.

**Never** adds a seventh `SeedError` leaf (the six-member taxonomy is closed
and meta-test enforced) -- this module reuses `PreconditionFailure` (a chain
gap, or an ambiguous cross-migration composition) and `NeverWriteViolation`
(a never-write target), matching their existing semantics.

**Never** wires migrations into `cli/seed.py`'s `update` stub,
`verbs/update.py` (does not exist yet), or any `--include-seeded`/`--run`
flag -- that CLI wiring is Story 11.4's declared surface. This story ships
only the registry/runner as a library surface plus `exclude_offers`, a
helper a future `update` verb can call; it does not itself gate anything
behind a flag.

**Never** modifies `plan/build.py`, `apply/run.py`, `state/store.py`,
`plan/types.py`, or `templates/manifest.yaml` -- this module reuses those
types exactly as shipped, including `Action.target_state =
ArtifactState.ABSENT` for a removal (already forward-anticipated by
`plan/types.py`'s own `Action.target_state` docstring).
"""

from __future__ import annotations

import dataclasses
import fnmatch
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from pyforge.core.process import PosixProcess

from ..detect.hashes import hash_content
from ..errors import NeverWriteViolation, PreconditionFailure
from ..model.manifest import ArtifactClass, Manifest
from ..model.version import ModelVersion
from ..plan.types import Action, Plan, RepoFingerprint, SkippedArtifact
from ..state import SeedState


@dataclass(frozen=True)
class RepoView:
    """The read-only view a migration's `migrate()` callable is handed:
    the target repo's root plus the manifest being migrated TOWARD
    (`repo.manifest.model_version` is the runner's own `target` parameter --
    there is no separate one, matching `run_migrations`'s own signature).
    Deliberately not `detect.inventory.Inventory` -- see the module
    docstring."""

    repo_root: Path
    manifest: Manifest

    def __post_init__(self) -> None:
        if not isinstance(self.repo_root, Path):
            raise ValueError(f"RepoView.repo_root must be a Path, got {self.repo_root!r}")
        if not isinstance(self.manifest, Manifest):
            raise ValueError(f"RepoView.manifest must be a Manifest, got {self.manifest!r}")


@dataclass(frozen=True)
class Migration:
    """One registered migration step: the model-version range it covers, a
    human-reviewable `description`, and the pure `migrate` callable itself
    (AD-62's own signature: `(repo: RepoView, state: SeedState) -> Plan`).

    `__post_init__` requires `from_version < to_version` -- a migration that
    does not move the version forward cannot be a step in an ordered chain --
    and a non-blank `description`, matching `ManifestEntry`'s own
    "identity-bearing string field" discipline for every other hand-authored
    record this package carries."""

    from_version: ModelVersion
    to_version: ModelVersion
    description: str
    migrate: Callable[[RepoView, SeedState], Plan]

    def __post_init__(self) -> None:
        if not isinstance(self.from_version, ModelVersion):
            raise ValueError(
                f"Migration.from_version must be a ModelVersion, got {self.from_version!r}"
            )
        if not isinstance(self.to_version, ModelVersion):
            raise ValueError(
                f"Migration.to_version must be a ModelVersion, got {self.to_version!r}"
            )
        if not self.from_version < self.to_version:
            raise ValueError(
                f"Migration.to_version ({self.to_version}) must be strictly greater than"
                f" from_version ({self.from_version})"
            )
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError(
                f"Migration.description must be a non-empty, non-blank str,"
                f" got {self.description!r}"
            )


#: The production registry -- empty (see the module docstring's own "ships
#: empty" paragraph). A future story that adds a real migration appends a
#: `Migration(...)` here; nothing else in this module changes shape to
#: accommodate one.
REGISTERED_MIGRATIONS: tuple[Migration, ...] = ()


def select_chain(
    current: ModelVersion, target: ModelVersion, migrations: Sequence[Migration]
) -> tuple[Migration, ...]:
    """The ordered sequence of `migrations` that walks `current` to `target`
    by semver, or `()` when `current == target` (nothing to do -- AD-60's
    idempotence-as-plan-emptiness, applied one layer up).

    Indexes `migrations` by `from_version` and walks forward one step at a
    time: at each position, the step whose `from_version` equals the
    position reached so far is appended and the walk continues from its
    `to_version`. When no registered `Migration` continues from the current
    position AND that position is not yet `target`, raises
    `PreconditionFailure` naming BOTH the version the walk got stuck at and
    the target it could not reach -- the epics AC's own "a gap in the chain
    ... must be a clear error naming the missing step."

    `migrations` sharing a `from_version` is not itself rejected here: the
    last one encountered while indexing wins, silently. No two versions of
    the same migration collide in practice (`REGISTERED_MIGRATIONS` names
    one step per version range by construction), and detecting the
    collision would need either an ordering assumption over `migrations`
    this function does not otherwise require, or a second pass with no
    corresponding row in this story's own I/O matrix -- left as a stated,
    narrow bound rather than silent (see this module's own Design Notes
    addendum)."""
    if current == target:
        return ()
    by_from: dict[ModelVersion, Migration] = {}
    for migration in migrations:
        by_from[migration.from_version] = migration
    chain: list[Migration] = []
    position = current
    while position != target:
        step = by_from.get(position)
        if step is None:
            raise PreconditionFailure(
                f"chain-gap: no registered migration continues from model_version"
                f" {position} toward the target {target} -- the walk reached"
                f" {position} and could not proceed",
                remedy=(
                    f"register a Migration whose from_version is {position} (continuing"
                    f" toward {target}), or install a pyforge-marshal release whose"
                    " bundled migrations cover this repo's recorded model_version"
                ),
            )
        chain.append(step)
        position = step.to_version
    return tuple(chain)


@dataclass(frozen=True)
class MigrationOutcome:
    """`run_migrations`'s whole return value: the composed `Plan` plus the
    DERIVED set of artifact ids it offers rather than imposes (FR-97)."""

    plan: Plan
    offered_artifact_ids: frozenset[str]


_GIT_TIMEOUT_S = 30.0


def _git_head(process: PosixProcess, repo_root: Path) -> str | None:
    """`git rev-parse HEAD`'s stdout, stripped -- `None` on a non-zero exit
    (no commits yet, or `repo_root` is not a git repo at all). Mirrors
    `plan.build._git_head` byte for byte (see the module docstring's Never
    bullet on why this is duplicated rather than imported)."""
    result = process.run(["git", "rev-parse", "HEAD"], cwd=repo_root, timeout_s=_GIT_TIMEOUT_S)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _repo_is_dirty(process: PosixProcess, repo_root: Path) -> bool:
    """`True` iff `git status --porcelain --untracked-files=normal` produces
    any output, OR the command exits non-zero (cannot confirm clean -- the
    conservative direction). Mirrors `plan.build._repo_is_dirty`."""
    result = process.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=repo_root,
        timeout_s=_GIT_TIMEOUT_S,
    )
    if result.returncode != 0:
        return True
    return bool(result.stdout)


def _read_text_or_blank(repo_root: Path, path: str) -> str:
    """The UTF-8 text at `repo_root / path`, or `""` for anything that is
    not a readable regular file -- absent, a directory, unreadable, or
    invalid encoding. Mirrors `plan.build`'s identical degrade rule (that
    function is private to a sibling module this file may not reach into --
    see the module docstring)."""
    target = repo_root / path
    if not target.is_file():
        return ""
    try:
        return target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _repo_fingerprint(repo_root: Path, artifact_paths: Mapping[str, str]) -> RepoFingerprint:
    """A `RepoFingerprint` over exactly `artifact_paths` (`artifact_id ->
    repo-relative path`) -- mirrors `plan.build.build_plan`'s own
    fingerprint composition (`_git_head`/`_repo_is_dirty` plus a
    per-artifact `hash_content` of each target's current whole-file text,
    sorted by artifact id) so a migration's self-fingerprinted `Plan` is
    tamper-evident the same way one `build_plan` produces is (AD-57).

    Public within this package (used by `run_migrations` itself for the
    empty-chain case) and MAY be used by any `migrate()` implementation to
    self-fingerprint its own returned `Plan` over only the artifacts it
    touches -- matching `build_plan`'s own "fingerprint covers only THIS
    plan's actions" convention (see the module docstring)."""
    process = PosixProcess()
    artifact_hashes = tuple(
        sorted(
            (
                (artifact_id, hash_content(_read_text_or_blank(repo_root, path)))
                for artifact_id, path in artifact_paths.items()
            ),
            key=lambda pair: pair[0],
        )
    )
    return RepoFingerprint(
        git_head=_git_head(process, repo_root),
        dirty=_repo_is_dirty(process, repo_root),
        artifact_hashes=artifact_hashes,
    )


def _never_write_match(target_path: str, never_write: Sequence[str]) -> str | None:
    """The first pattern in `never_write` that matches `target_path`, or
    `None` if none does -- a lexical, best-effort pre-check using the same
    `fnmatch.fnmatchcase` matcher `fs._matches`/`verbs.skips.first_match`
    both use, duplicated rather than imported (`fs._matches` is a private
    name; see the module docstring). Unlike `fs.py`'s own guard, this never
    consults an exempt allow-list and never resolves `target_path` against
    the filesystem -- see the module docstring's own paragraph on why this
    narrowing is stated rather than silent."""
    for pattern in never_write:
        if fnmatch.fnmatchcase(target_path, pattern):
            return pattern
    return None


def run_migrations(
    repo: RepoView,
    state: SeedState,
    *,
    migrations: Sequence[Migration] = REGISTERED_MIGRATIONS,
) -> MigrationOutcome:
    """Select the semver-ordered chain from `state.model_version` to
    `repo.manifest.model_version`, skip any step whose `to_version` is
    already recorded in `state.migrations_applied` (FR-96 -- applied exactly
    once, `ModelVersion`-equal comparison, matching
    `SeedState.__post_init__`'s own build-metadata-exclusion rule), run the
    remainder in order, and compose their individual `Plan`s into one --
    handed to the SAME `apply.run.run_apply` path every other verb uses
    (AD-62).

    Composition: `actions` are concatenated across the selected migrations
    and re-sorted by `artifact_id` (raising `PreconditionFailure` on a
    duplicate id across two migrations' actions -- an ambiguous,
    order-dependent composition `plan.types.Plan.from_json_dict` already
    refuses for a hand-edited file, so this refuses it too at construction
    time). The merged `RepoFingerprint` takes `git_head`/`dirty` from the
    FIRST selected migration's own sub-plan (nothing writes between calls,
    so every sub-plan's git snapshot is identical by construction -- an
    invariant, not merely an assumption, and not re-verified at runtime) and
    unions `artifact_hashes` across all of them, with the identical
    duplicate-id refusal `actions` itself gets.

    A composed action whose `target_path` matches one of
    `repo.manifest.never_write`'s glob patterns raises `NeverWriteViolation`
    before this function returns (see the module docstring's own paragraph
    on this pre-check's deliberately narrower scope).

    `offered_artifact_ids` (FR-97) is DERIVED, never self-reported by a
    migration: any composed action whose `artifact_id` names a
    `copied-seeded` entry in `repo.manifest.entries` is an offer -- a plain
    manifest cross-reference. An action naming an id absent from
    `repo.manifest.entries` entirely (a fully-retired, renamed-away
    artifact) is never an offer, regardless of what its class used to be --
    only a PRESENT, `copied-seeded`-classified target can be.

    When no migration needs to run (either `current == target`, or every
    step in the chain is already applied), returns an empty `Plan` --
    `Plan(actions=(), repo_fingerprint=_repo_fingerprint(repo.repo_root, {}))`
    -- and `offered_artifact_ids == frozenset()`, matching AD-60's
    idempotence-as-plan-emptiness."""
    chain = select_chain(state.model_version, repo.manifest.model_version, migrations)
    already_applied = frozenset(
        ModelVersion.parse(version) for version in state.migrations_applied
    )
    to_run = tuple(step for step in chain if step.to_version not in already_applied)

    if not to_run:
        return MigrationOutcome(
            plan=Plan(actions=(), repo_fingerprint=_repo_fingerprint(repo.repo_root, {})),
            offered_artifact_ids=frozenset(),
        )

    sub_plans = tuple(step.migrate(repo, state) for step in to_run)

    actions_by_id: dict[str, Action] = {}
    action_source: dict[str, ModelVersion] = {}
    for step, sub_plan in zip(to_run, sub_plans):
        for action in sub_plan.actions:
            if action.artifact_id in actions_by_id:
                raise PreconditionFailure(
                    f"duplicate-action: artifact_id {action.artifact_id!r} is produced by"
                    f" both the migration to {action_source[action.artifact_id]} and the"
                    f" migration to {step.to_version} -- an ambiguous, order-dependent"
                    " composition",
                    remedy=(
                        "rewrite one of the two migrations so at most one produces an"
                        f" Action for {action.artifact_id!r}"
                    ),
                )
            actions_by_id[action.artifact_id] = action
            action_source[action.artifact_id] = step.to_version

    actions = tuple(sorted(actions_by_id.values(), key=lambda action: action.artifact_id))

    for action in actions:
        matched = _never_write_match(action.target_path, repo.manifest.never_write)
        if matched is not None:
            raise NeverWriteViolation(
                f"migration action {action.artifact_id!r} names target_path"
                f" {action.target_path!r}, which matches never-write pattern {matched!r}",
                remedy=(
                    "choose a different target path in the migration, or update the"
                    " manifest's never-write patterns if this file is meant to be writable"
                ),
            )

    hashes_by_id: dict[str, str] = {}
    hash_source: dict[str, ModelVersion] = {}
    for step, sub_plan in zip(to_run, sub_plans):
        for artifact_id, sha in sub_plan.repo_fingerprint.artifact_hashes:
            if artifact_id in hashes_by_id:
                raise PreconditionFailure(
                    f"duplicate-fingerprint: artifact_id {artifact_id!r} is hashed by both"
                    f" the migration to {hash_source[artifact_id]} and the migration to"
                    f" {step.to_version} -- an ambiguous, order-dependent composition",
                    remedy=(
                        "rewrite one of the two migrations so at most one fingerprints"
                        f" {artifact_id!r}"
                    ),
                )
            hashes_by_id[artifact_id] = sha
            hash_source[artifact_id] = step.to_version

    fingerprint = dataclasses.replace(
        sub_plans[0].repo_fingerprint,
        artifact_hashes=tuple(sorted(hashes_by_id.items(), key=lambda pair: pair[0])),
    )
    plan = Plan(actions=actions, repo_fingerprint=fingerprint)

    copied_seeded_ids = frozenset(
        entry.id
        for entry in repo.manifest.entries
        if entry.artifact_class is ArtifactClass.COPIED_SEEDED
    )
    offered_artifact_ids = frozenset(
        action.artifact_id for action in actions if action.artifact_id in copied_seeded_ids
    )

    return MigrationOutcome(plan=plan, offered_artifact_ids=offered_artifact_ids)


#: The glob `exclude_offers` records against every action it moves out of
#: `Plan.actions`, mirroring `SkippedArtifact.pattern`'s "the argument
#: responsible" convention (`verbs.skips.apply_skips` names the literal
#: `--skip` glob; this names the literal future CLI flag a caller would need
#: to pass to include the offer instead).
_INCLUDE_SEEDED_PATTERN = "--include-seeded"


def exclude_offers(plan: Plan, offered_artifact_ids: frozenset[str]) -> Plan:
    """Move every action in `plan.actions` whose `artifact_id` is in
    `offered_artifact_ids` into `plan.skipped`, as a
    `SkippedArtifact(pattern="--include-seeded")` -- mirroring
    `seed.verbs.skips.apply_skips`'s existing "move an action into `skipped`"
    shape rather than inventing a second one (this module may not import
    that function: `verbs` sits ABOVE `migrate` in the architecture's
    module-dependency chain).

    A future `update` verb calls this directly, unconditionally, unless
    `--include-seeded` is passed (this story ships the library surface only;
    wiring the flag is Story 11.4's).

    Pure, like `apply_skips`: reads nothing, mutates nothing, and returns
    `plan` itself (not merely an equal value) when nothing matches, so "no
    offer changes nothing" holds by construction."""
    kept: list[Action] = []
    newly_skipped: list[SkippedArtifact] = []
    for action in plan.actions:
        if action.artifact_id in offered_artifact_ids:
            newly_skipped.append(
                SkippedArtifact(
                    artifact_id=action.artifact_id,
                    target_path=action.target_path,
                    pattern=_INCLUDE_SEEDED_PATTERN,
                )
            )
        else:
            kept.append(action)
    if not newly_skipped:
        return plan
    skipped_ids = {entry.artifact_id for entry in newly_skipped}
    skipped = tuple(
        sorted((*plan.skipped, *newly_skipped), key=lambda entry: entry.artifact_id)
    )
    fingerprint = dataclasses.replace(
        plan.repo_fingerprint,
        artifact_hashes=tuple(
            (artifact_id, sha)
            for artifact_id, sha in plan.repo_fingerprint.artifact_hashes
            if artifact_id not in skipped_ids
        ),
    )
    return dataclasses.replace(
        plan, actions=tuple(kept), repo_fingerprint=fingerprint, skipped=skipped
    )
