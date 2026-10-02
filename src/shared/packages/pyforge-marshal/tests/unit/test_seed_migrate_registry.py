"""Unit tests for ``pyforge.marshal.seed.migrate.registry`` (Story 11.3) --
covers the spec's I/O & Edge-Case Matrix: the simple two-step chain, the
already-at-bundled-version empty chain, a named gap error, the re-run
exclusion (running ``chain`` again after an applied ``to_version`` is
recorded), migration purity (a write-blocking fixture, mirroring
``test_seed_apply_run.py::test_no_fs_call_at_all_when_a_run_succeeds``),
``copied-seeded`` routing to ``Plan.skipped`` (default and opted-in), the
never-write plan-time guard, and SC-07's own end-to-end proof: a simulated
v1->v2 breaking change (a renamed managed artifact plus a tier-rule region
insertion) absorbed via the real ``chain`` -> ``compose`` -> ``run_apply``
pipeline, then re-verified conformant with a fresh ``classify`` pass.

Imports the ``registry`` module itself (not just its functions), mirroring
``test_seed_apply_run.py``'s own precedent, so the purity tests can
monkeypatch ``registry.fs.write``/``replace_span``/``remove``/``symlink``
and prove neither a migration's own ``fn`` nor ``compose`` itself ever calls
one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.marshal.seed import fs
from pyforge.marshal.seed.apply.run import run_apply
from pyforge.marshal.seed.detect.hashes import hash_content
from pyforge.marshal.seed.detect.inventory import ArtifactState, classify
from pyforge.marshal.seed.errors import InternalError, NeverWriteViolation
from pyforge.marshal.seed.fs import NeverWrite
from pyforge.marshal.seed.migrate import registry
from pyforge.marshal.seed.migrate.registry import MIGRATIONS, Migration, chain, compose
from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    Manifest,
    ManifestEntry,
    Region,
)
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.plan.types import Action, Plan, RepoFingerprint
from pyforge.marshal.seed.regions.apply import insert_region
from pyforge.marshal.seed.regions.markers import RegionFormat
from pyforge.marshal.seed.regions.parse import resolve_anchor
from pyforge.marshal.seed.state import SeedState

_V1 = ModelVersion.parse("1.0.0")
_V1_1 = ModelVersion.parse("1.1.0")
_V2 = ModelVersion.parse("2.0.0")

_OPEN = NeverWrite(())


def _state(model_version: ModelVersion, *, migrations_applied: tuple[str, ...] = ()) -> SeedState:
    """A minimal, schema-valid ``SeedState`` -- only ``model_version`` and
    ``migrations_applied`` vary across this file's tests; every other field
    carries an inert placeholder, mirroring ``test_seed_state_store.py``'s
    own ``_sample_state`` convention but pared to what this file needs."""
    return SeedState(
        model_version=model_version,
        seed_model_version="0.1.0",
        adopted_at="2026-08-21T00:00:00Z",
        last_update="2026-08-21T00:00:00Z",
        mode="init",
        agents=(),
        managed=(),
        skips=(),
        legacy=(),
        migrations_applied=migrations_applied,
        opted_out=(),
    )


def _no_op_fn(_view, _state) -> Plan:
    return Plan(
        actions=(),
        repo_fingerprint=RepoFingerprint(git_head=None, dirty=True, artifact_hashes=()),
    )


def _fresh_fingerprint(repo_root: Path, *hashed: tuple[str, str]) -> RepoFingerprint:
    return RepoFingerprint(git_head=None, dirty=True, artifact_hashes=tuple(sorted(hashed)))


def _manifest(*entries: ManifestEntry) -> Manifest:
    return Manifest(model_version=_V1, never_write=(), entries=tuple(entries))


def _whole_file(entry_id: str, path: str, artifact_class: ArtifactClass) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=artifact_class,
        path=path,
        applies_to=AppliesTo.BOTH,
        rationale="test",
    )


def _hybrid(entry_id: str, path: str, region_name: str, anchor: tuple[str, ...]) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
        path=path,
        applies_to=AppliesTo.BOTH,
        rationale="test",
        format=RegionFormat.HTML,
        regions=(Region(name=region_name, anchor=anchor),),
    )


# --- chain(): simple chain / already-at-bundled / gap / re-run -------------


def test_chain_returns_both_steps_in_strict_linked_order(tmp_path):
    mig_1 = Migration(from_version=_V1, to_version=_V1_1, fn=_no_op_fn)
    mig_2 = Migration(from_version=_V1_1, to_version=_V2, fn=_no_op_fn)
    state = _state(_V1)

    result = chain(state, _V2, registry=(mig_2, mig_1))

    assert result == (mig_1, mig_2)


def test_chain_returns_empty_tuple_when_state_is_already_at_bundled_version(tmp_path):
    state = _state(_V2)

    assert chain(state, _V2, registry=(Migration(from_version=_V1, to_version=_V2, fn=_no_op_fn),)) == ()


def test_chain_raises_internal_error_naming_the_missing_from_version_step(tmp_path):
    mig_1 = Migration(from_version=_V1, to_version=_V1_1, fn=_no_op_fn)
    state = _state(_V1)

    with pytest.raises(InternalError) as excinfo:
        chain(state, _V2, registry=(mig_1,))

    assert "migration-chain-gap" in str(excinfo.value)
    assert str(_V1_1) in str(excinfo.value)
    assert excinfo.value.exit_code == 10
    assert excinfo.value.remedy.strip()


def test_chain_excludes_a_migration_already_recorded_in_migrations_applied(tmp_path):
    mig_1 = Migration(from_version=_V1, to_version=_V1_1, fn=_no_op_fn)
    mig_2 = Migration(from_version=_V1_1, to_version=_V2, fn=_no_op_fn)
    state = _state(_V1, migrations_applied=("1.1.0",))

    result = chain(state, _V2, registry=(mig_1, mig_2))

    # The full linear path is still walked (a gap after the applied step
    # would still be reported), but the already-applied step is excluded:
    # only the remaining, unapplied one survives.
    assert result == (mig_2,)


def test_running_chain_twice_against_the_same_updated_state_computes_an_empty_chain(tmp_path):
    mig_1 = Migration(from_version=_V1, to_version=_V1_1, fn=_no_op_fn)
    state = _state(_V1)
    registry_tuple = (mig_1,)

    first = chain(state, _V1_1, registry=registry_tuple)
    assert first == (mig_1,)

    # Simulates "running update twice": the caller recorded the just-applied
    # to_version, state.model_version was NOT independently advanced, and a
    # second chain() call against the same registry computes empty.
    state_after = _state(_V1, migrations_applied=("1.1.0",))
    second = chain(state_after, _V1_1, registry=registry_tuple)
    assert second == ()


def test_chain_default_registry_argument_is_the_module_level_empty_migrations(tmp_path):
    # Pins the default itself (mirrors `test_seed_plan_build.py`'s own
    # "default-argument case" convention for `opted_out`): a caller who
    # never advances the bundled model version at all gets an empty chain
    # for free, with no registry argument at all.
    state = _state(_V1)
    assert chain(state, _V1) == ()
    assert MIGRATIONS == ()


# --- Migration.__post_init__: strict forward progress -----------------------


def test_migration_rejects_a_self_referencing_from_and_to_version():
    with pytest.raises(ValueError, match="strictly less than"):
        Migration(from_version=_V1, to_version=_V1, fn=_no_op_fn)


def test_migration_rejects_a_downgrade_hop():
    with pytest.raises(ValueError, match="strictly less than"):
        Migration(from_version=_V1_1, to_version=_V1, fn=_no_op_fn)


# --- chain(): duplicate from_version and the cycle defense-in-depth --------


def test_chain_raises_on_two_registry_entries_sharing_the_same_from_version():
    mig_a = Migration(from_version=_V1, to_version=_V1_1, fn=_no_op_fn)
    mig_b = Migration(from_version=_V1, to_version=_V2, fn=_no_op_fn)

    with pytest.raises(InternalError, match="migration-registry-ambiguous"):
        chain(_state(_V1), _V2, registry=(mig_a, mig_b))


def test_chain_raises_a_named_error_instead_of_hanging_on_a_cycle(monkeypatch):
    """`Migration.__post_init__` makes a cycle unconstructable through the
    public API (every hop must strictly increase), so this test forces one
    via `object.__setattr__` on an already-constructed, otherwise-valid
    frozen `Migration` -- proving `chain`'s own `visited`-set defense in
    depth actually fires (a named error) rather than looping forever, for
    the case some future change bypasses `__post_init__`'s guard. Bounded
    with a short timeout via `monkeypatch`-free plain execution -- if this
    regresses to a hang, the test process itself would hang, which is the
    point: an explicit, fast-failing assertion is strictly better than that."""
    mig_a = Migration(from_version=_V1, to_version=_V1_1, fn=_no_op_fn)
    mig_b = Migration(from_version=_V1_1, to_version=_V2, fn=_no_op_fn)
    # Bypass __post_init__ (already ran once, successfully, at construction)
    # by mutating the frozen instance directly -- retroactively turns
    # mig_b's own hop into 1.1.0 -> 1.0.0, closing a cycle back to _V1.
    object.__setattr__(mig_b, "to_version", _V1)

    with pytest.raises(InternalError, match="migration-chain-cycle"):
        chain(_state(_V1), _V2, registry=(mig_a, mig_b))


# --- migration purity (P-12): a write-blocking fixture ----------------------


def test_a_migration_function_performs_zero_filesystem_writes(tmp_path, monkeypatch):
    manifest = _manifest(_whole_file("a", "a.txt", ArtifactClass.COPIED_MANAGED))
    view = classify(manifest, tmp_path)
    state = _state(_V1)
    touched: list[str] = []
    monkeypatch.setattr(registry.fs, "write", lambda *a, **k: touched.append("write"))
    monkeypatch.setattr(registry.fs, "replace_span", lambda *a, **k: touched.append("replace_span"))
    monkeypatch.setattr(registry.fs, "remove", lambda *a, **k: touched.append("remove"))
    monkeypatch.setattr(registry.fs, "symlink", lambda *a, **k: touched.append("symlink"))

    def materializing_fn(view, state) -> Plan:
        action = Action(
            artifact_id="a",
            artifact_class=ArtifactClass.COPIED_MANAGED,
            current_state=ArtifactState.ABSENT,
            target_state=ArtifactState.PRESENT_CONFORMANT,
            target_path="a.txt",
            chosen_anchor=(),
            rationale="test migration",
        )
        return Plan(
            actions=(action,),
            repo_fingerprint=RepoFingerprint(git_head=None, dirty=True, artifact_hashes=()),
        )

    migration = Migration(from_version=_V1, to_version=_V1_1, fn=materializing_fn)

    plan = migration.fn(view, state)
    assert plan.actions[0].artifact_id == "a"
    assert touched == []

    composed = compose(
        (migration,),
        view,
        state,
        repo_fingerprint=_fresh_fingerprint(tmp_path, ("a", hash_content(""))),
        repo_root=tmp_path,
        never_write=_OPEN,
    )
    assert composed.actions[0].artifact_id == "a"
    assert touched == []


# --- compose(): concatenation, shared fingerprint, seeded routing ----------


def _absent_action(artifact_id: str, path: str, artifact_class: ArtifactClass) -> Action:
    return Action(
        artifact_id=artifact_id,
        artifact_class=artifact_class,
        current_state=ArtifactState.ABSENT,
        target_state=ArtifactState.PRESENT_CONFORMANT,
        target_path=path,
        chosen_anchor=(),
        rationale="test migration",
    )


def _fn_returning(*actions: Action):
    def fn(_view, _state) -> Plan:
        return Plan(
            actions=actions,
            repo_fingerprint=RepoFingerprint(git_head=None, dirty=True, artifact_hashes=()),
        )

    return fn


def test_compose_concatenates_actions_from_each_migration_and_shares_one_fingerprint(tmp_path):
    manifest = _manifest()
    view = classify(manifest, tmp_path)
    state = _state(_V1)
    mig_a = Migration(
        from_version=_V1,
        to_version=_V1_1,
        fn=_fn_returning(_absent_action("a", "a.txt", ArtifactClass.COPIED_MANAGED)),
    )
    mig_b = Migration(
        from_version=_V1_1,
        to_version=_V2,
        fn=_fn_returning(_absent_action("b", "b.txt", ArtifactClass.COPIED_MANAGED)),
    )
    shared_fingerprint = _fresh_fingerprint(tmp_path, ("a", hash_content("")), ("b", hash_content("")))

    plan = compose(
        (mig_a, mig_b),
        view,
        state,
        repo_fingerprint=shared_fingerprint,
        repo_root=tmp_path,
        never_write=_OPEN,
    )

    assert [action.artifact_id for action in plan.actions] == ["a", "b"]
    assert plan.repo_fingerprint is shared_fingerprint
    assert plan.skipped == ()


def test_compose_routes_a_copied_seeded_action_to_skipped_by_default(tmp_path):
    manifest = _manifest()
    view = classify(manifest, tmp_path)
    state = _state(_V1)
    migration = Migration(
        from_version=_V1,
        to_version=_V1_1,
        fn=_fn_returning(_absent_action("seeded", "seeded.txt", ArtifactClass.COPIED_SEEDED)),
    )

    plan = compose(
        (migration,),
        view,
        state,
        repo_fingerprint=_fresh_fingerprint(tmp_path, ("seeded", hash_content(""))),
        repo_root=tmp_path,
        never_write=_OPEN,
    )

    assert plan.actions == ()
    (skip,) = plan.skipped
    assert skip.artifact_id == "seeded"
    assert skip.target_path == "seeded.txt"
    assert "--include-seeded" in skip.pattern


def test_compose_includes_a_copied_seeded_action_when_include_seeded_is_true(tmp_path):
    manifest = _manifest()
    view = classify(manifest, tmp_path)
    state = _state(_V1)
    migration = Migration(
        from_version=_V1,
        to_version=_V1_1,
        fn=_fn_returning(_absent_action("seeded", "seeded.txt", ArtifactClass.COPIED_SEEDED)),
    )

    plan = compose(
        (migration,),
        view,
        state,
        repo_fingerprint=_fresh_fingerprint(tmp_path, ("seeded", hash_content(""))),
        repo_root=tmp_path,
        never_write=_OPEN,
        include_seeded=True,
    )

    assert plan.skipped == ()
    (action,) = plan.actions
    assert action.artifact_id == "seeded"


def test_compose_raises_never_write_violation_before_returning_for_a_protected_target(tmp_path):
    manifest = _manifest()
    view = classify(manifest, tmp_path)
    state = _state(_V1)
    migration = Migration(
        from_version=_V1,
        to_version=_V1_1,
        fn=_fn_returning(_absent_action("dream", "docs/dreams/x.md", ArtifactClass.COPIED_MANAGED)),
    )
    never_write = NeverWrite(("docs/dreams/*.md",))

    with pytest.raises(NeverWriteViolation) as excinfo:
        compose(
            (migration,),
            view,
            state,
            repo_fingerprint=_fresh_fingerprint(tmp_path, ("dream", hash_content(""))),
            repo_root=tmp_path,
            never_write=never_write,
        )

    assert excinfo.value.exit_code == 4
    assert "docs/dreams/*.md" in str(excinfo.value)


# --- compose(): pass-2 review findings --------------------------------------


@pytest.mark.parametrize("escaping_path", ["/etc/passwd", "../outside.txt", "sub/../../outside.txt"])
def test_compose_refuses_an_absolute_or_escaping_target_path_at_plan_time(tmp_path, escaping_path):
    """Review finding, verified by execution against the pre-fix code: an
    absolute or `..`-traversing target_path passed `compose()` completely
    silently (repo_root / "/etc/passwd" discards repo_root entirely -- a
    documented pathlib behavior), deferring detection to `run_apply`'s own
    separate check -- undercutting this story's own headline "plan time, not
    apply time" claim for exactly this failure class."""
    manifest = _manifest()
    view = classify(manifest, tmp_path)
    state = _state(_V1)
    migration = Migration(
        from_version=_V1,
        to_version=_V1_1,
        fn=_fn_returning(_absent_action("escaper", escaping_path, ArtifactClass.COPIED_MANAGED)),
    )

    with pytest.raises(Exception) as excinfo:  # PreconditionFailure or unusable-target
        compose(
            (migration,),
            view,
            state,
            repo_fingerprint=_fresh_fingerprint(tmp_path, ("escaper", hash_content(""))),
            repo_root=tmp_path,
            never_write=_OPEN,
        )
    assert "escaping-target" in str(excinfo.value) or "unusable-target" in str(excinfo.value)


def test_compose_raises_on_two_migrations_colliding_on_the_same_artifact_id(tmp_path):
    manifest = _manifest()
    view = classify(manifest, tmp_path)
    state = _state(_V1)
    mig_a = Migration(
        from_version=_V1,
        to_version=_V1_1,
        fn=_fn_returning(_absent_action("dup", "a.txt", ArtifactClass.COPIED_MANAGED)),
    )
    mig_b = Migration(
        from_version=_V1_1,
        to_version=_V2,
        fn=_fn_returning(_absent_action("dup", "b.txt", ArtifactClass.COPIED_MANAGED)),
    )

    with pytest.raises(InternalError, match="migration-plan-collision"):
        compose(
            (mig_a, mig_b),
            view,
            state,
            repo_fingerprint=_fresh_fingerprint(tmp_path, ("dup", hash_content(""))),
            repo_root=tmp_path,
            never_write=_OPEN,
        )


def test_compose_merges_a_migrations_own_declared_skips_into_the_result(tmp_path):
    """Review finding: an earlier draft called `migration.fn(view, state)`
    and only ever read its `.actions`, silently dropping any `.skipped`
    entries the migration function itself had already decided to skip for
    its own reasons (unrelated to the copied-seeded routing this function
    also performs)."""
    manifest = _manifest()
    view = classify(manifest, tmp_path)
    state = _state(_V1)

    def fn(_view, _state) -> Plan:
        return Plan(
            actions=(),
            repo_fingerprint=RepoFingerprint(git_head=None, dirty=True, artifact_hashes=()),
            skipped=(registry.SkippedArtifact(artifact_id="own-skip", target_path="own.txt", pattern="*.txt"),),
        )

    migration = Migration(from_version=_V1, to_version=_V1_1, fn=fn)

    plan = compose(
        (migration,),
        view,
        state,
        repo_fingerprint=_fresh_fingerprint(tmp_path),
        repo_root=tmp_path,
        never_write=_OPEN,
    )

    assert [entry.artifact_id for entry in plan.skipped] == ["own-skip"]


# --- SC-07: simulated v1->v2 breaking change, absorbed end to end ----------


def _v2_manifest() -> Manifest:
    """The "bundled" v2 manifest: a renamed managed artifact
    (``new-name.txt``, replacing a v1-only ``old-name.txt`` this manifest no
    longer declares at all) plus a hybrid-managed-region artifact gaining a
    ``tiers`` region -- the tier-rule-equivalent change."""
    return Manifest(
        model_version=_V2,
        never_write=(),
        entries=(
            _whole_file("renamed", "new-name.txt", ArtifactClass.COPIED_MANAGED),
            _hybrid("tiers-file", "TIERS.md", "tiers", ("<!-- anchor -->",)),
        ),
    )


def _v1_to_v2_test_migration(view, state: SeedState) -> Plan:
    """The story's own SC-07 fixture migration: a pure ``(RepoView, SeedState)
    -> Plan`` function performing the rename (materialize the artifact at
    its NEW path) and the tier-rule change (insert the ``tiers`` region) as
    two ``Action``s -- no filesystem write of its own, only reads (the
    current text of ``TIERS.md``, to resolve the insertion anchor exactly
    like `plan/build.py::_chosen_anchor` does for an ordinary plan)."""
    tiers_path = view.repo_root / "TIERS.md"
    tiers_text = tiers_path.read_text(encoding="utf-8") if tiers_path.is_file() else ""
    resolution = resolve_anchor(tiers_text, RegionFormat.HTML, ("<!-- anchor -->",))

    rename_action = Action(
        artifact_id="renamed",
        artifact_class=ArtifactClass.COPIED_MANAGED,
        current_state=ArtifactState.ABSENT,
        target_state=ArtifactState.PRESENT_CONFORMANT,
        target_path="new-name.txt",
        chosen_anchor=(),
        rationale="v1->v2: renamed from old-name.txt",
    )
    tier_action = Action(
        artifact_id="tiers-file",
        artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
        current_state=ArtifactState.PRESENT_DIVERGENT,
        target_state=ArtifactState.PRESENT_CONFORMANT,
        target_path="TIERS.md",
        chosen_anchor=(("tiers", resolution.matched),),
        rationale="v1->v2: tier rule promoted, insert the 'tiers' region",
    )
    return Plan(
        actions=(rename_action, tier_action),
        repo_fingerprint=RepoFingerprint(git_head=None, dirty=True, artifact_hashes=()),
    )


def test_sc07_a_simulated_v1_to_v2_breaking_change_is_absorbed_via_the_real_pipeline(tmp_path):
    # Fixture repo at a simulated v1 state: the hybrid file exists but has
    # never had the "tiers" region, and the renamed artifact's new path
    # does not exist yet -- both left over from a v1-shaped repo.
    (tmp_path / "TIERS.md").write_text("intro\n<!-- anchor -->\noutro\n", encoding="utf-8")
    (tmp_path / "old-name.txt").write_text("v1 content, no longer tracked\n", encoding="utf-8")

    manifest = _v2_manifest()
    view = classify(manifest, tmp_path)
    (renamed_classification, tiers_classification) = view.classifications
    assert renamed_classification.state == ArtifactState.ABSENT
    assert tiers_classification.state == ArtifactState.PRESENT_DIVERGENT

    state = _state(_V1)
    migration = Migration(from_version=_V1, to_version=_V2, fn=_v1_to_v2_test_migration)

    migrations = chain(state, _V2, registry=(migration,))
    assert migrations == (migration,)

    fingerprint = _fresh_fingerprint(
        tmp_path,
        ("renamed", hash_content("")),
        ("tiers-file", hash_content("intro\n<!-- anchor -->\noutro\n")),
    )
    plan = compose(migrations, view, state, repo_fingerprint=fingerprint, repo_root=tmp_path, never_write=_OPEN)
    assert [action.artifact_id for action in plan.actions] == ["renamed", "tiers-file"]
    assert plan.skipped == ()

    def commit(action: Action) -> None:
        target = tmp_path / action.target_path
        if action.artifact_class is ArtifactClass.COPIED_MANAGED:
            fs.write(target, b"v2 content\n", repo_root=tmp_path, never_write=_OPEN)
        else:
            assert action.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION
            current_text = target.read_text(encoding="utf-8") if target.is_file() else None
            insert_region(
                current_text,
                target,
                "tiers",
                ("<!-- anchor -->",),
                "tier: 1\n",
                model_version=_V2,
                fmt=RegionFormat.HTML,
                repo_root=tmp_path,
                never_write=_OPEN,
            )

    result = run_apply(plan, repo_root=tmp_path, never_write=_OPEN, commit=commit)
    assert result.applied == ("renamed", "tiers-file")

    # SC-07's own proof: a fresh conformance (`classify`) pass against the
    # bundled v2 manifest reports every entry conformant, with zero manual
    # edits -- the whole pipeline (chain -> compose -> the real run_apply)
    # absorbed the breaking change.
    post_inventory = classify(manifest, tmp_path)
    assert all(
        classification.state == ArtifactState.PRESENT_CONFORMANT for classification in post_inventory.classifications
    )
    assert (tmp_path / "new-name.txt").read_text(encoding="utf-8") == "v2 content\n"
    assert "tier: 1" in (tmp_path / "TIERS.md").read_text(encoding="utf-8")
