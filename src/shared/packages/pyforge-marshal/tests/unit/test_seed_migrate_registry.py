"""Unit tests for ``pyforge.marshal.seed.migrate.registry`` (Story 11.3) --
covers the spec's I/O & Edge-Case Matrix (all rows except SC-07, which is
``tests/integration/test_migrate_v1_to_v2_fixture.py``'s own end-to-end
proof): ``RepoView``/``Migration`` construction validation, ``select_chain``
(ordering, skip-already-applied, gap error, empty chain), ``run_migrations``
composition (action concatenation + re-sort, duplicate-id refusal across
actions AND fingerprints, fingerprint merge, never-write refusal),
``offered_artifact_ids`` derivation (copied-seeded hit, non-offer removal),
``exclude_offers``, and the write-blocking purity fixture (P-12).

Migrations here are constructed directly, each ``migrate`` a closure
returning a pre-built ``Plan`` -- ``run_migrations``'s contract is over an
arbitrary ``Sequence[Migration]``, and a fixed return value is what lets a
test compose two migrations' outputs deterministically without needing a
real repo on disk for most rows. ``tmp_path`` is still threaded through as
``RepoView.repo_root`` everywhere (``run_migrations`` calls
``_repo_fingerprint`` for the empty-chain case, which shells out to git and
must have a real directory to run against)."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from pyforge.marshal.seed import fs
from pyforge.marshal.seed.detect.inventory import ArtifactState
from pyforge.marshal.seed.errors import NeverWriteViolation, PreconditionFailure
from pyforge.marshal.seed.migrate.registry import (
    REGISTERED_MIGRATIONS,
    Migration,
    RepoView,
    exclude_offers,
    run_migrations,
    select_chain,
)
from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    Manifest,
    ManifestEntry,
)
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.plan.types import Action, Plan, RepoFingerprint
from pyforge.marshal.seed.state import SeedState

# --- fixture builders --------------------------------------------------------


def _version(text: str) -> ModelVersion:
    return ModelVersion.parse(text)


def _entry(
    id_: str, *, artifact_class: ArtifactClass = ArtifactClass.COPIED_MANAGED, path: str | None = None
) -> ManifestEntry:
    return ManifestEntry(
        id=id_,
        artifact_class=artifact_class,
        path=path or f"{id_}.txt",
        applies_to=AppliesTo.BOTH,
        rationale=f"test entry {id_!r}",
    )


def _manifest(
    *,
    model_version: str,
    entries: tuple[ManifestEntry, ...] = (),
    never_write: tuple[str, ...] = (),
) -> Manifest:
    return Manifest(model_version=_version(model_version), never_write=never_write, entries=entries)


def _state(model_version: str, *, migrations_applied: tuple[str, ...] = ()) -> SeedState:
    return SeedState(
        model_version=_version(model_version),
        seed_model_version="0.0.0",
        adopted_at="2026-01-01T00:00:00Z",
        last_update="2026-01-01T00:00:00Z",
        mode="adopt",
        agents=(),
        managed=(),
        skips=(),
        legacy=(),
        migrations_applied=migrations_applied,
        opted_out=(),
    )


def _action(artifact_id: str, target_path: str, **overrides) -> Action:
    fields = {
        "artifact_id": artifact_id,
        "artifact_class": ArtifactClass.COPIED_MANAGED,
        "current_state": ArtifactState.ABSENT,
        "target_state": ArtifactState.PRESENT_CONFORMANT,
        "target_path": target_path,
        "chosen_anchor": (),
        "rationale": f"{target_path!r} is absent; materialize it",
    }
    fields.update(overrides)
    return Action(**fields)


def _plan(actions: tuple[Action, ...], **fingerprint_overrides) -> Plan:
    fields = {"git_head": "deadbeef", "dirty": False, "artifact_hashes": ()}
    fields.update(fingerprint_overrides)
    return Plan(actions=actions, repo_fingerprint=RepoFingerprint(**fields))


def _migration(
    from_version: str,
    to_version: str,
    *,
    migrate: Callable[[RepoView, SeedState], Plan],
    description: str = "test migration",
) -> Migration:
    return Migration(
        from_version=_version(from_version),
        to_version=_version(to_version),
        description=description,
        migrate=migrate,
    )


# --- RepoView / Migration construction ---------------------------------------


def test_repo_view_carries_repo_root_and_manifest(tmp_path):
    manifest = _manifest(model_version="1.0.0")
    repo = RepoView(repo_root=tmp_path, manifest=manifest)
    assert repo.repo_root == tmp_path
    assert repo.manifest is manifest


def test_repo_view_rejects_a_non_path_repo_root():
    with pytest.raises(ValueError, match="repo_root"):
        RepoView(repo_root="not-a-path", manifest=_manifest(model_version="1.0.0"))


def test_repo_view_rejects_a_non_manifest():
    with pytest.raises(ValueError, match="manifest"):
        RepoView(repo_root=__import__("pathlib").Path("."), manifest="not-a-manifest")


def test_migration_rejects_from_version_not_strictly_less_than_to_version():
    with pytest.raises(ValueError, match="strictly greater"):
        Migration(
            from_version=_version("2.0.0"),
            to_version=_version("1.0.0"),
            description="bad",
            migrate=lambda repo, state: _plan(()),
        )


def test_migration_rejects_equal_from_and_to_version():
    with pytest.raises(ValueError, match="strictly greater"):
        Migration(
            from_version=_version("1.0.0"),
            to_version=_version("1.0.0"),
            description="bad",
            migrate=lambda repo, state: _plan(()),
        )


def test_migration_rejects_a_blank_description():
    with pytest.raises(ValueError, match="non-empty, non-blank"):
        Migration(
            from_version=_version("1.0.0"),
            to_version=_version("2.0.0"),
            description="   ",
            migrate=lambda repo, state: _plan(()),
        )


def test_registered_migrations_is_empty_in_production():
    assert REGISTERED_MIGRATIONS == ()


# --- select_chain -------------------------------------------------------------


def test_select_chain_returns_empty_when_current_equals_target():
    version = _version("1.0.0")
    assert select_chain(version, version, ()) == ()


def test_select_chain_orders_a_multi_step_chain_regardless_of_registration_order():
    m1 = _migration("1.0.0", "1.1.0", migrate=lambda repo, state: _plan(()))
    m2 = _migration("1.1.0", "2.0.0", migrate=lambda repo, state: _plan(()))
    chain = select_chain(_version("1.0.0"), _version("2.0.0"), (m2, m1))
    assert chain == (m1, m2)


def test_select_chain_raises_a_named_gap_naming_both_versions():
    m1 = _migration("1.0.0", "1.1.0", migrate=lambda repo, state: _plan(()))
    with pytest.raises(PreconditionFailure) as exc_info:
        select_chain(_version("1.0.0"), _version("2.0.0"), (m1,))
    message = str(exc_info.value)
    assert "1.1.0" in message
    assert "2.0.0" in message


def test_select_chain_raises_a_named_gap_with_no_migrations_at_all():
    with pytest.raises(PreconditionFailure) as exc_info:
        select_chain(_version("1.0.0"), _version("2.0.0"), ())
    message = str(exc_info.value)
    assert "1.0.0" in message
    assert "2.0.0" in message


# --- run_migrations: selection + composition ----------------------------------


def test_run_migrations_returns_an_empty_plan_when_no_migration_is_needed(tmp_path):
    manifest = _manifest(model_version="1.0.0")
    repo = RepoView(repo_root=tmp_path, manifest=manifest)
    state = _state("1.0.0")
    outcome = run_migrations(repo, state, migrations=())
    assert outcome.plan.actions == ()
    assert outcome.plan.skipped == ()
    assert outcome.offered_artifact_ids == frozenset()


def test_run_migrations_selects_and_composes_an_ordered_chain(tmp_path):
    plan_a = _plan((_action("a", "a.txt"),))
    plan_b = _plan((_action("b", "b.txt"),))
    migration_1 = _migration("1.0.0", "1.1.0", migrate=lambda repo, state: plan_a)
    migration_2 = _migration("1.1.0", "2.0.0", migrate=lambda repo, state: plan_b)
    manifest = _manifest(model_version="2.0.0", entries=(_entry("a"), _entry("b")))
    repo = RepoView(repo_root=tmp_path, manifest=manifest)
    state = _state("1.0.0")
    outcome = run_migrations(repo, state, migrations=(migration_1, migration_2))
    assert [action.artifact_id for action in outcome.plan.actions] == ["a", "b"]
    assert outcome.offered_artifact_ids == frozenset()


def test_run_migrations_skips_a_step_already_recorded_applied(tmp_path):
    plan_a = _plan((_action("a", "a.txt"),))
    plan_b = _plan((_action("b", "b.txt"),))
    migration_1 = _migration("1.0.0", "1.1.0", migrate=lambda repo, state: plan_a)
    migration_2 = _migration("1.1.0", "2.0.0", migrate=lambda repo, state: plan_b)
    manifest = _manifest(model_version="2.0.0", entries=(_entry("a"), _entry("b")))
    repo = RepoView(repo_root=tmp_path, manifest=manifest)
    state = _state("1.0.0", migrations_applied=("1.1.0",))
    outcome = run_migrations(repo, state, migrations=(migration_1, migration_2))
    assert [action.artifact_id for action in outcome.plan.actions] == ["b"]


def test_run_migrations_selects_nothing_once_every_step_is_recorded_applied(tmp_path):
    """FR-96's own proxy for "never re-run": a second call against a state
    that already records every step in the chain selects zero steps -- the
    real end-to-end "update run twice" proof is Story 11.4's, since the
    update verb does not exist yet."""
    plan_a = _plan((_action("a", "a.txt"),))
    plan_b = _plan((_action("b", "b.txt"),))
    migration_1 = _migration("1.0.0", "1.1.0", migrate=lambda repo, state: plan_a)
    migration_2 = _migration("1.1.0", "2.0.0", migrate=lambda repo, state: plan_b)
    manifest = _manifest(model_version="2.0.0", entries=(_entry("a"), _entry("b")))
    repo = RepoView(repo_root=tmp_path, manifest=manifest)
    state = _state("1.0.0", migrations_applied=("1.1.0", "2.0.0"))
    outcome = run_migrations(repo, state, migrations=(migration_1, migration_2))
    assert outcome.plan.actions == ()
    assert outcome.offered_artifact_ids == frozenset()


def test_run_migrations_merges_fingerprints_taking_git_state_from_the_first_sub_plan(tmp_path):
    plan_a = Plan(
        actions=(_action("a", "a.txt"),),
        repo_fingerprint=RepoFingerprint(
            git_head="first-head", dirty=False, artifact_hashes=(("a", "aaaaaaaa"),)
        ),
    )
    plan_b = Plan(
        actions=(_action("b", "b.txt"),),
        repo_fingerprint=RepoFingerprint(
            git_head="second-head", dirty=True, artifact_hashes=(("b", "bbbbbbbb"),)
        ),
    )
    migration_1 = _migration("1.0.0", "1.1.0", migrate=lambda repo, state: plan_a)
    migration_2 = _migration("1.1.0", "2.0.0", migrate=lambda repo, state: plan_b)
    manifest = _manifest(model_version="2.0.0", entries=(_entry("a"), _entry("b")))
    repo = RepoView(repo_root=tmp_path, manifest=manifest)
    state = _state("1.0.0")
    outcome = run_migrations(repo, state, migrations=(migration_1, migration_2))
    fingerprint = outcome.plan.repo_fingerprint
    assert fingerprint.git_head == "first-head"
    assert fingerprint.dirty is False
    assert fingerprint.artifact_hashes == (("a", "aaaaaaaa"), ("b", "bbbbbbbb"))


def test_run_migrations_raises_on_duplicate_action_artifact_id_across_migrations(tmp_path):
    plan_1 = _plan((_action("shared", "shared.txt"),))
    plan_2 = _plan((_action("shared", "shared.txt"),))
    migration_1 = _migration("1.0.0", "1.1.0", migrate=lambda repo, state: plan_1)
    migration_2 = _migration("1.1.0", "2.0.0", migrate=lambda repo, state: plan_2)
    manifest = _manifest(model_version="2.0.0", entries=(_entry("shared"),))
    repo = RepoView(repo_root=tmp_path, manifest=manifest)
    state = _state("1.0.0")
    with pytest.raises(PreconditionFailure) as exc_info:
        run_migrations(repo, state, migrations=(migration_1, migration_2))
    message = str(exc_info.value)
    assert "shared" in message
    assert "1.1.0" in message
    assert "2.0.0" in message


def test_run_migrations_raises_on_duplicate_fingerprint_artifact_id_across_migrations(tmp_path):
    plan_1 = _plan((_action("a", "a.txt"),), artifact_hashes=(("shared-hash-id", "aaaaaaaa"),))
    plan_2 = _plan((_action("b", "b.txt"),), artifact_hashes=(("shared-hash-id", "bbbbbbbb"),))
    migration_1 = _migration("1.0.0", "1.1.0", migrate=lambda repo, state: plan_1)
    migration_2 = _migration("1.1.0", "2.0.0", migrate=lambda repo, state: plan_2)
    manifest = _manifest(model_version="2.0.0", entries=(_entry("a"), _entry("b")))
    repo = RepoView(repo_root=tmp_path, manifest=manifest)
    state = _state("1.0.0")
    with pytest.raises(PreconditionFailure, match="shared-hash-id"):
        run_migrations(repo, state, migrations=(migration_1, migration_2))


def test_run_migrations_raises_never_write_violation_for_a_matching_target(tmp_path):
    plan = _plan((_action("secret", "secrets/token.txt"),))
    migration = _migration("1.0.0", "2.0.0", migrate=lambda repo, state: plan)
    manifest = _manifest(
        model_version="2.0.0",
        entries=(_entry("secret"),),
        never_write=("secrets/**",),
    )
    repo = RepoView(repo_root=tmp_path, manifest=manifest)
    state = _state("1.0.0")
    with pytest.raises(NeverWriteViolation, match="secrets/token.txt"):
        run_migrations(repo, state, migrations=(migration,))


def test_run_migrations_derives_offered_artifact_ids_from_copied_seeded_entries(tmp_path):
    plan = _plan((_action("seed-me", "seeded.txt"),))
    migration = _migration("1.0.0", "2.0.0", migrate=lambda repo, state: plan)
    manifest = _manifest(
        model_version="2.0.0",
        entries=(_entry("seed-me", artifact_class=ArtifactClass.COPIED_SEEDED),),
    )
    repo = RepoView(repo_root=tmp_path, manifest=manifest)
    state = _state("1.0.0")
    outcome = run_migrations(repo, state, migrations=(migration,))
    assert outcome.offered_artifact_ids == frozenset({"seed-me"})


def test_run_migrations_never_offers_a_non_copied_seeded_entry(tmp_path):
    plan = _plan((_action("plain", "plain.txt"),))
    migration = _migration("1.0.0", "2.0.0", migrate=lambda repo, state: plan)
    manifest = _manifest(
        model_version="2.0.0", entries=(_entry("plain", artifact_class=ArtifactClass.COPIED_MANAGED),)
    )
    repo = RepoView(repo_root=tmp_path, manifest=manifest)
    state = _state("1.0.0")
    outcome = run_migrations(repo, state, migrations=(migration,))
    assert outcome.offered_artifact_ids == frozenset()


def test_run_migrations_never_offers_a_removal_of_an_artifact_absent_from_the_manifest(tmp_path):
    plan = _plan((_action("retired", "retired.txt", target_state=ArtifactState.ABSENT),))
    migration = _migration("1.0.0", "2.0.0", migrate=lambda repo, state: plan)
    # `retired` names no entry at all in the v2 manifest -- fully retired,
    # renamed away -- so it can never be an offer regardless of what class
    # it used to carry.
    manifest = _manifest(model_version="2.0.0", entries=())
    repo = RepoView(repo_root=tmp_path, manifest=manifest)
    state = _state("1.0.0")
    outcome = run_migrations(repo, state, migrations=(migration,))
    assert outcome.offered_artifact_ids == frozenset()


def test_run_migrations_never_writes_even_when_every_fs_write_primitive_raises(tmp_path, monkeypatch):
    """P-12's own proof: monkeypatch every write primitive `seed.fs` exposes
    to raise, hand `run_migrations` a migration producing a non-trivial
    `Plan`, and assert no exception fires -- the absence of a write is the
    assertion, not merely an import-surface inspection."""

    def _boom(*args, **kwargs):
        raise AssertionError("run_migrations must never call an fs write primitive")

    monkeypatch.setattr(fs, "write", _boom)
    monkeypatch.setattr(fs, "replace_span", _boom)
    monkeypatch.setattr(fs, "remove", _boom)
    monkeypatch.setattr(fs, "symlink", _boom)

    plan = _plan(
        (
            _action("a", "a.txt"),
            _action("b", "b.txt", target_state=ArtifactState.ABSENT),
        )
    )
    migration = _migration("1.0.0", "2.0.0", migrate=lambda repo, state: plan)
    manifest = _manifest(model_version="2.0.0", entries=(_entry("a"), _entry("b")))
    repo = RepoView(repo_root=tmp_path, manifest=manifest)
    state = _state("1.0.0")

    outcome = run_migrations(repo, state, migrations=(migration,))
    assert [action.artifact_id for action in outcome.plan.actions] == ["a", "b"]


# --- exclude_offers -----------------------------------------------------------


def test_exclude_offers_returns_the_same_plan_object_when_nothing_matches():
    plan = _plan((_action("a", "a.txt"),))
    result = exclude_offers(plan, frozenset({"nonexistent"}))
    assert result is plan


def test_exclude_offers_moves_matching_actions_into_skipped_and_drops_their_hash():
    plan = Plan(
        actions=(_action("a", "a.txt"), _action("b", "b.txt")),
        repo_fingerprint=RepoFingerprint(
            git_head=None, dirty=True, artifact_hashes=(("a", "aaaaaaaa"), ("b", "bbbbbbbb"))
        ),
    )
    result = exclude_offers(plan, frozenset({"b"}))
    assert [action.artifact_id for action in result.actions] == ["a"]
    assert [entry.artifact_id for entry in result.skipped] == ["b"]
    assert result.skipped[0].pattern == "--include-seeded"
    assert result.skipped[0].target_path == "b.txt"
    assert result.repo_fingerprint.artifact_hashes == (("a", "aaaaaaaa"),)


def test_exclude_offers_is_idempotent(tmp_path):
    plan = Plan(
        actions=(_action("a", "a.txt"), _action("b", "b.txt")),
        repo_fingerprint=RepoFingerprint(
            git_head=None, dirty=True, artifact_hashes=(("a", "aaaaaaaa"), ("b", "bbbbbbbb"))
        ),
    )
    once = exclude_offers(plan, frozenset({"b"}))
    twice = exclude_offers(once, frozenset({"b"}))
    assert twice is once
