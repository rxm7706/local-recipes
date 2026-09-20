"""Unit tests for ``pyforge.marshal.seed.verbs.update`` (Story 11.4) --
covers the spec's I/O & Edge-Case Matrix: a never-drifted repo with no
managed content produces an empty plan; an already-conformant managed entry
still receives a wholesale-regenerate action (FR-98) and, for a hybrid
entry, only its marked span is replaced (FR-99); the three-source merge (a
synthetic registered migration + a synthetic ABSENT entry + a synthetic
drifted managed entry, asserting all three appear correctly merged and
sorted); the collision-refusal case; ``--run``/``--yes``/declined
confirmation; ``--force`` bypassing the hand-edited-managed-content
precondition and selecting ``MaterializeVerb.RECOPY``; a migration-offered
``copied-seeded`` action skipped by default and applied with
``--include-seeded``; a migration-chain gap propagating unwrapped; a
never-write target refused at plan time; and the SC-01 end-to-end proof
(mirrors ``test_seed_migrate_registry.py``'s own SC-07 fixture pattern).

Manifest/git-repo builders mirror ``test_seed_verbs_adopt.py``'s
``_manifest``/``_copied_managed``/``_hybrid``/``_git``/``_init_git_repo``/
``_commit_all`` convention (real ``git`` I/O against a ``tmp_path``, never
mocked). A ``commit`` double (``_fake_commit``) mirrors that file's own --
materializes a whole-file class via plain ``Path.write_text`` and a hybrid
class through the REAL ``regions.apply.insert_region``/``substitute_region``
primitives (never faked) -- used for the merge/collision/state-write tests
that are not themselves exercising ``_update_commit``'s own materialize
wiring; two dedicated tests exercise the REAL ``_update_commit`` against the
REAL packaged region fragments and the fixed Genesis-owned
``.bmad-config.user.toml`` allow-listed path, mirroring
``test_seed_verbs_adopt.py``'s own two ``_default_commit`` proof tests."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

from pyforge.marshal.seed.detect.hashes import hash_content
from pyforge.marshal.seed.detect.inventory import ArtifactState
from pyforge.marshal.seed.errors import InternalError, PreconditionFailure
from pyforge.marshal.seed.fs import NeverWrite
from pyforge.marshal.seed.migrate import registry as migrate_registry
from pyforge.marshal.seed.migrate.registry import Migration
from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    Manifest,
    ManifestEntry,
    Region,
)
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.plan.types import Action, Plan, RepoFingerprint
from pyforge.marshal.seed.regions.apply import insert_region, substitute_region
from pyforge.marshal.seed.regions.markers import RegionFormat
from pyforge.marshal.seed.regions.parse import parse_regions
from pyforge.marshal.seed.state import (
    ManagedArtifact,
    RegionSpanRecord,
    SeedState,
    read_state,
    write_state,
)
from pyforge.marshal.seed.verbs import update as update_module
from pyforge.marshal.seed.verbs.update import run_update

_V1 = ModelVersion.parse("1.0.0")
_V2 = ModelVersion.parse("2.0.0")
_NO_NEVER_WRITE = NeverWrite(patterns=())


# --- manifest builders (mirrors test_seed_verbs_adopt.py) -------------------


def _manifest(*entries: ManifestEntry, model_version: ModelVersion = _V1) -> Manifest:
    return Manifest(model_version=model_version, never_write=(), entries=tuple(entries))


def _copied_managed(entry_id: str, path: str, *, applies_to: AppliesTo = AppliesTo.BOTH) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.COPIED_MANAGED,
        path=path,
        applies_to=applies_to,
        rationale="test",
    )


def _generated_derived(entry_id: str, path: str, *, applies_to: AppliesTo = AppliesTo.BOTH) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.GENERATED_DERIVED,
        path=path,
        applies_to=applies_to,
        rationale="test",
    )


def _hybrid(entry_id: str, path: str, *region_names: str, applies_to: AppliesTo = AppliesTo.BOTH) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
        path=path,
        applies_to=applies_to,
        rationale="test",
        format=RegionFormat.HTML,
        regions=tuple(Region(name=name, anchor=("# anchor",)) for name in region_names),
    )


# --- real-git fixtures (mirrors test_seed_verbs_adopt.py) -------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    return result


def _init_git_repo(repo: Path) -> None:
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "initial")


def _commit_all(repo: Path) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "fixture")


@pytest.fixture
def clean_repo(tmp_path: Path) -> Path:
    _init_git_repo(tmp_path)
    return tmp_path


def _unreachable_confirm() -> bool:
    raise AssertionError("confirm() should not have been called")


# --- commit double (mirrors test_seed_verbs_adopt.py::_fake_commit) --------


def _fake_commit(manifest: Manifest, repo_root: Path, calls: list[str] | None = None):
    entries_by_id = {entry.id: entry for entry in manifest.entries}

    def commit(action: Action) -> None:
        if calls is not None:
            calls.append(action.artifact_id)
        entry = entries_by_id[action.artifact_id]
        target = repo_root / action.target_path
        if entry.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION:
            assert entry.format is not None
            for region_name, _matched_anchor in action.chosen_anchor:
                region = next(r for r in entry.regions if r.name == region_name)
                text = target.read_text(encoding="utf-8") if target.is_file() else None
                existing = None
                if text is not None:
                    existing = next((s for s in parse_regions(text, entry.format) if s.name == region_name), None)
                if existing is None:
                    insert_region(
                        text,
                        target,
                        region_name,
                        region.anchor,
                        f"body for {region_name}\n",
                        model_version=manifest.model_version,
                        fmt=entry.format,
                        repo_root=repo_root,
                        never_write=_NO_NEVER_WRITE,
                    )
                else:
                    substitute_region(
                        text,
                        target,
                        existing,
                        f"refreshed body for {region_name}\n",
                        model_version=manifest.model_version,
                        expected_sha=existing.sha,
                        fmt=entry.format,
                        repo_root=repo_root,
                        never_write=_NO_NEVER_WRITE,
                    )
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"content for {entry.id}\n", encoding="utf-8")

    return commit


def _seed_state(
    *,
    model_version: ModelVersion = _V1,
    managed: tuple[ManagedArtifact, ...] = (),
    migrations_applied: tuple[str, ...] = (),
    mode: str = "adopt",
) -> SeedState:
    return SeedState(
        model_version=model_version,
        seed_model_version="0.1.0",
        adopted_at="2026-08-21T00:00:00Z",
        last_update="2026-08-21T00:00:00Z",
        mode=mode,
        agents=(),
        managed=managed,
        skips=(),
        legacy=(),
        migrations_applied=migrations_applied,
        opted_out=(),
    )


# --- Row 1: no flags, repo current, no managed content ----------------------


def test_dry_run_with_no_managed_content_and_no_drift_produces_empty_plan(clean_repo):
    manifest = _manifest()
    write_state(_seed_state(), repo_root=clean_repo, never_write=_NO_NEVER_WRITE)
    _commit_all(clean_repo)

    result = run_update(clean_repo, manifest, confirm=_unreachable_confirm)

    assert result.plan.actions == ()
    assert result.applied is None
    assert not result.declined
    assert (clean_repo / ".marshal" / "plan.json").is_file()


# --- FR-98/FR-99: wholesale regenerate ---------------------------------------


def test_wholesale_regenerate_action_produced_for_a_conformant_hybrid_entry(clean_repo):
    manifest = _manifest(_hybrid("whole", "WHOLE.md", "tiers"))
    (clean_repo / "WHOLE.md").write_text(
        "before\n<!-- marshal-seed:begin region=tiers model-version=1.0.0 sha=deadbeef -->\n"
        "old body\n<!-- marshal-seed:end region=tiers -->\nafter\n",
        encoding="utf-8",
    )
    write_state(
        _seed_state(
            managed=(
                ManagedArtifact(
                    id="whole",
                    path="WHOLE.md",
                    artifact_class="hybrid-managed-region",
                    body_sha=hash_content("old body\n"),
                    inserted_region_span=RegionSpanRecord(name="tiers", start=0, end=0),
                ),
            ),
        ),
        repo_root=clean_repo,
        never_write=_NO_NEVER_WRITE,
    )
    _commit_all(clean_repo)

    result = run_update(clean_repo, manifest, confirm=_unreachable_confirm)

    assert [a.artifact_id for a in result.plan.actions] == ["whole"]
    assert result.plan.actions[0].chosen_anchor == (("tiers", "# anchor"),)


def test_multi_region_hybrid_entry_does_not_refuse_a_plain_dry_run(clean_repo):
    """Review finding, HIGH/blocking: ``state/store.py``'s own pre-existing
    schema limit means ``state.managed[]`` can record at most ONE region
    per hybrid entry, even though the packaged manifest declares several
    for ``AGENTS.md`` (3) and ``CLAUDE.md`` (2) -- exactly what a real
    ``adopt`` produces today for a multi-region entry. Before the fix,
    ``_managed_records`` built ``region_shas`` with only the one recorded
    region, so rung 6 (``verbs/preconditions.py::_region_divergences``)
    flagged every OTHER declared-and-present region as "present in the file
    but never recorded in state" -- a HARD divergence refusing the whole
    run, unconditionally (not gated by ``dry_run``, only ``force`` bypasses
    rung 6). This is a plain, no-flags ``run_update`` call -- it must not
    raise ``PreconditionFailure``."""
    manifest = _manifest(_hybrid("whole", "WHOLE.md", "tiers", "portability-contract"))
    (clean_repo / "WHOLE.md").write_text(
        "before\n"
        "<!-- marshal-seed:begin region=tiers model-version=1.0.0 sha=deadbeef -->\n"
        "tiers body\n<!-- marshal-seed:end region=tiers -->\n"
        "<!-- marshal-seed:begin region=portability-contract model-version=1.0.0 sha=deadbeef -->\n"
        "portability body\n<!-- marshal-seed:end region=portability-contract -->\n"
        "after\n",
        encoding="utf-8",
    )
    write_state(
        _seed_state(
            managed=(
                ManagedArtifact(
                    id="whole",
                    path="WHOLE.md",
                    artifact_class="hybrid-managed-region",
                    body_sha=hash_content("tiers body\n"),
                    # Only ONE region recorded, matching a real adopt's own
                    # `state/store.py` limitation -- "portability-contract"
                    # has no recorded entry at all here.
                    inserted_region_span=RegionSpanRecord(name="tiers", start=0, end=0),
                ),
            ),
        ),
        repo_root=clean_repo,
        never_write=_NO_NEVER_WRITE,
    )
    _commit_all(clean_repo)

    # Must not raise PreconditionFailure -- plain call, no --force.
    result = run_update(clean_repo, manifest, confirm=_unreachable_confirm)

    assert [a.artifact_id for a in result.plan.actions] == ["whole"]


def test_hybrid_wholesale_regenerate_replaces_only_the_marked_span_not_the_whole_file(clean_repo):
    """FR-99: applying a wholesale-regenerate action against an
    already-present hybrid region REPLACES only its marked span --
    everything outside it is byte-identical."""
    manifest = _manifest(_hybrid("whole", "WHOLE.md", "tiers"))
    original = (
        "before-content\n"
        "<!-- marshal-seed:begin region=tiers model-version=1.0.0 sha=deadbeef -->\n"
        "old body\n<!-- marshal-seed:end region=tiers -->\nafter-content\n"
    )
    (clean_repo / "WHOLE.md").write_text(original, encoding="utf-8")
    write_state(
        _seed_state(
            managed=(
                ManagedArtifact(
                    id="whole",
                    path="WHOLE.md",
                    artifact_class="hybrid-managed-region",
                    body_sha=hash_content("old body\n"),
                    inserted_region_span=RegionSpanRecord(name="tiers", start=0, end=0),
                ),
            ),
        ),
        repo_root=clean_repo,
        never_write=_NO_NEVER_WRITE,
    )
    _commit_all(clean_repo)
    calls: list[str] = []

    result = run_update(
        clean_repo,
        manifest,
        run=True,
        yes=True,
        confirm=_unreachable_confirm,
        commit=_fake_commit(manifest, clean_repo, calls),
    )

    assert result.applied == ("whole",)
    assert calls == ["whole"]
    content = (clean_repo / "WHOLE.md").read_text(encoding="utf-8")
    assert content.startswith("before-content\n")
    assert content.endswith("after-content\n")
    assert "refreshed body for tiers" in content
    assert "old body" not in content
    assert content.count("marshal-seed:begin region=tiers") == 1


def test_wholesale_regenerate_skips_copied_seeded_and_referenced_records(clean_repo):
    manifest = _manifest(
        ManifestEntry(
            id="seeded",
            artifact_class=ArtifactClass.COPIED_SEEDED,
            path="SEEDED.md",
            applies_to=AppliesTo.BOTH,
            rationale="test",
        ),
    )
    (clean_repo / "SEEDED.md").write_text("hello\n", encoding="utf-8")
    write_state(
        _seed_state(
            managed=(
                ManagedArtifact(
                    id="seeded",
                    path="SEEDED.md",
                    artifact_class="copied-seeded",
                    body_sha=hash_content("hello\n"),
                    inserted_region_span=None,
                ),
            ),
        ),
        repo_root=clean_repo,
        never_write=_NO_NEVER_WRITE,
    )
    _commit_all(clean_repo)

    result = run_update(clean_repo, manifest, confirm=_unreachable_confirm)

    assert result.plan.actions == ()


def test_wholesale_regenerate_skips_a_record_whose_entry_was_retired(clean_repo):
    manifest = _manifest()  # the manifest no longer declares "gone" at all
    write_state(
        _seed_state(
            managed=(
                ManagedArtifact(
                    id="gone",
                    path="GONE.md",
                    artifact_class="copied-managed",
                    body_sha="abc12345",
                    inserted_region_span=None,
                ),
            ),
        ),
        repo_root=clean_repo,
        never_write=_NO_NEVER_WRITE,
    )
    _commit_all(clean_repo)

    result = run_update(clean_repo, manifest, confirm=_unreachable_confirm)

    assert result.plan.actions == ()


# --- three-source merge + collision refusal ----------------------------------


def _absent_action(artifact_id: str, path: str) -> Action:
    return Action(
        artifact_id=artifact_id,
        artifact_class=ArtifactClass.COPIED_MANAGED,
        current_state=ArtifactState.ABSENT,
        target_state=ArtifactState.PRESENT_CONFORMANT,
        target_path=path,
        chosen_anchor=(),
        rationale="migration action",
    )


def test_three_source_merge_appears_correctly_merged_and_sorted(clean_repo, monkeypatch):
    """A synthetic registered migration (artifact_id ``m-migrated``) + a
    synthetic manifest-only ABSENT entry (``z-absent``, from ``build_plan``)
    + a synthetic already-managed entry (``a-wholesale``, wholesale-
    regenerated) -- all three appear in the merged, id-sorted plan."""
    (clean_repo / "A_WHOLESALE.md").write_text("current\n", encoding="utf-8")
    write_state(
        _seed_state(
            managed=(
                ManagedArtifact(
                    id="a-wholesale",
                    path="A_WHOLESALE.md",
                    artifact_class="copied-managed",
                    body_sha=hash_content("current\n"),
                    inserted_region_span=None,
                ),
            ),
        ),
        repo_root=clean_repo,
        never_write=_NO_NEVER_WRITE,
    )
    _commit_all(clean_repo)

    def migration_fn(view, state):
        return Plan(
            actions=(_absent_action("m-migrated", "M_MIGRATED.md"),),
            repo_fingerprint=RepoFingerprint(git_head=None, dirty=True, artifact_hashes=()),
        )

    migration = Migration(from_version=_V1, to_version=_V2, fn=migration_fn)
    monkeypatch.setattr(migrate_registry, "MIGRATIONS", (migration,))
    # state.model_version is already _V1 (the _seed_state() default above),
    # behind the v2 manifest used for this run -- chain() bridges it via the
    # monkeypatched migration.
    manifest_v2 = _manifest(
        _copied_managed("z-absent", "Z_ABSENT.md"),
        _copied_managed("a-wholesale", "A_WHOLESALE.md"),
        model_version=_V2,
    )

    result = run_update(clean_repo, manifest_v2, confirm=_unreachable_confirm)

    assert [a.artifact_id for a in result.plan.actions] == ["a-wholesale", "m-migrated", "z-absent"]


def test_collision_between_two_sources_raises_internal_error(clean_repo, monkeypatch):
    """A migration re-targeting an artifact ``build_plan`` ALSO independently
    proposes to create is a genuine authoring bug, refused loudly -- unlike
    a migration re-targeting an ALREADY-managed id (the ordinary "renamed
    artifact" case, which ``run_update``'s own exclusion logic resolves
    without a collision at all, see ``test_sc01_...`` and the module
    docstring's own "Making the three sources ACTUALLY disjoint" Design
    Note), ``brand-new`` here has NO ``state.managed[]`` record at all, so
    nothing excludes ``build_plan``'s own action for it."""
    manifest_v2 = _manifest(_copied_managed("brand-new", "BRAND_NEW.md"), model_version=_V2)
    write_state(_seed_state(), repo_root=clean_repo, never_write=_NO_NEVER_WRITE)
    _commit_all(clean_repo)

    def migration_fn(view, state):
        return Plan(
            actions=(_absent_action("brand-new", "BRAND_NEW.md"),),
            repo_fingerprint=RepoFingerprint(git_head=None, dirty=True, artifact_hashes=()),
        )

    migration = Migration(from_version=_V1, to_version=_V2, fn=migration_fn)
    monkeypatch.setattr(migrate_registry, "MIGRATIONS", (migration,))

    with pytest.raises(InternalError, match="update-plan-collision"):
        run_update(clean_repo, manifest_v2, confirm=_unreachable_confirm)


# --- --run/--yes/declined confirmation ---------------------------------------


def test_run_without_yes_declined_confirmation_applies_nothing(clean_repo):
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    result = run_update(clean_repo, manifest, run=True, confirm=lambda: False)

    assert result.declined
    assert result.applied is None
    assert not (clean_repo / "WHOLE.md").exists()


def test_run_with_yes_applies_and_writes_state(clean_repo):
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))
    calls: list[str] = []

    result = run_update(
        clean_repo,
        manifest,
        run=True,
        yes=True,
        confirm=_unreachable_confirm,
        commit=_fake_commit(manifest, clean_repo, calls),
    )

    assert result.applied == ("whole",)
    assert calls == ["whole"]
    assert (clean_repo / "WHOLE.md").read_text(encoding="utf-8") == "content for whole\n"
    # `state is None` on entry (never adopted) -- see the module docstring's
    # own "state-write gated on state is not None" paragraph: applying still
    # happens, but no `.marshal/seed-state.yml` is written for it.
    assert read_state(clean_repo) is None


def test_run_with_yes_against_an_already_adopted_repo_updates_state(clean_repo):
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))
    (clean_repo / "WHOLE.md").write_text("current\n", encoding="utf-8")
    write_state(
        _seed_state(
            managed=(
                ManagedArtifact(
                    id="whole",
                    path="WHOLE.md",
                    artifact_class="copied-managed",
                    body_sha=hash_content("current\n"),
                    inserted_region_span=None,
                ),
            ),
        ),
        repo_root=clean_repo,
        never_write=_NO_NEVER_WRITE,
    )
    _commit_all(clean_repo)
    before = read_state(clean_repo)

    result = run_update(
        clean_repo,
        manifest,
        run=True,
        yes=True,
        confirm=_unreachable_confirm,
        commit=_fake_commit(manifest, clean_repo),
    )

    assert result.applied == ("whole",)
    after = read_state(clean_repo)
    assert after is not None
    assert after.mode == before.mode
    assert after.adopted_at == before.adopted_at
    assert after.last_update != before.last_update
    assert after.model_version == manifest.model_version


# --- --force: bypasses rung 6, selects MaterializeVerb.RECOPY ---------------


def test_hand_edited_managed_content_refuses_apply_without_force(clean_repo):
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))
    (clean_repo / "WHOLE.md").write_text("hand-edited, not what state recorded\n", encoding="utf-8")
    write_state(
        _seed_state(
            managed=(
                ManagedArtifact(
                    id="whole",
                    path="WHOLE.md",
                    artifact_class="copied-managed",
                    body_sha="abc12345",
                    inserted_region_span=None,
                ),
            ),
        ),
        repo_root=clean_repo,
        never_write=_NO_NEVER_WRITE,
    )
    _commit_all(clean_repo)

    with pytest.raises(PreconditionFailure, match="managed-content-modified"):
        run_update(
            clean_repo,
            manifest,
            run=True,
            yes=True,
            confirm=_unreachable_confirm,
            commit=_fake_commit(manifest, clean_repo),
        )


def test_force_bypasses_the_hand_edited_managed_content_precondition(clean_repo):
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))
    (clean_repo / "WHOLE.md").write_text("hand-edited, not what state recorded\n", encoding="utf-8")
    write_state(
        _seed_state(
            managed=(
                ManagedArtifact(
                    id="whole",
                    path="WHOLE.md",
                    artifact_class="copied-managed",
                    body_sha="abc12345",
                    inserted_region_span=None,
                ),
            ),
        ),
        repo_root=clean_repo,
        never_write=_NO_NEVER_WRITE,
    )
    _commit_all(clean_repo)

    result = run_update(
        clean_repo,
        manifest,
        run=True,
        yes=True,
        force=True,
        confirm=_unreachable_confirm,
        commit=_fake_commit(manifest, clean_repo),
    )

    assert result.applied == ("whole",)


def test_force_without_run_is_still_a_dry_run(clean_repo):
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))
    (clean_repo / "WHOLE.md").write_text("hand-edited\n", encoding="utf-8")
    write_state(
        _seed_state(
            managed=(
                ManagedArtifact(
                    id="whole",
                    path="WHOLE.md",
                    artifact_class="copied-managed",
                    body_sha="abc12345",
                    inserted_region_span=None,
                ),
            ),
        ),
        repo_root=clean_repo,
        never_write=_NO_NEVER_WRITE,
    )
    _commit_all(clean_repo)

    result = run_update(clean_repo, manifest, force=True, confirm=_unreachable_confirm)

    assert result.applied is None
    assert not result.declined
    assert not (clean_repo / "WHOLE.md").read_text(encoding="utf-8").startswith("content for")


def test_default_commit_selects_recopy_and_confirm_true_when_force(clean_repo, monkeypatch):
    """FR-101: ``--force --run`` materializes whole-file artifacts via
    ``MaterializeVerb.RECOPY`` with ``request.confirm=True`` -- proven by
    monkeypatching ``update.materialize`` to capture the request, rather
    than exercising a real Copier recopy clone (matching this package's
    established "capture the call, don't run the real engine" technique for
    a narrow, isolated claim)."""
    captured = []

    def _fake_materialize(request):
        captured.append(request)
        from pyforge.marshal.seed.engine import MaterializeResult

        return MaterializeResult(staged_paths=(), answers={})

    monkeypatch.setattr(update_module, "materialize", _fake_materialize)
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))
    entries_by_id = {entry.id: entry for entry in manifest.entries}
    commit = update_module._update_commit(
        repo_root=clean_repo,
        never_write=_NO_NEVER_WRITE,
        entries_by_id=entries_by_id,
        model_version=_V1,
        answers={},
        template_path=None,
        force=True,
    )
    action = Action(
        artifact_id="whole",
        artifact_class=ArtifactClass.COPIED_MANAGED,
        current_state=None,
        target_state=None,
        target_path="WHOLE.md",
        chosen_anchor=(),
        rationale="test",
    )

    with pytest.raises(InternalError, match="no staged content"):
        commit(action)

    assert len(captured) == 1
    from pyforge.marshal.seed.engine import MaterializeVerb

    assert captured[0].verb is MaterializeVerb.RECOPY
    assert captured[0].confirm is True
    assert captured[0].dst_path == clean_repo


def test_default_commit_selects_copy_and_confirm_false_when_not_force(clean_repo, monkeypatch):
    captured = []

    def _fake_materialize(request):
        captured.append(request)
        from pyforge.marshal.seed.engine import MaterializeResult

        return MaterializeResult(staged_paths=(), answers={})

    monkeypatch.setattr(update_module, "materialize", _fake_materialize)
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))
    entries_by_id = {entry.id: entry for entry in manifest.entries}
    commit = update_module._update_commit(
        repo_root=clean_repo,
        never_write=_NO_NEVER_WRITE,
        entries_by_id=entries_by_id,
        model_version=_V1,
        answers={},
        template_path=None,
        force=False,
    )
    action = Action(
        artifact_id="whole",
        artifact_class=ArtifactClass.COPIED_MANAGED,
        current_state=None,
        target_state=None,
        target_path="WHOLE.md",
        chosen_anchor=(),
        rationale="test",
    )

    with pytest.raises(InternalError, match="no staged content"):
        commit(action)

    from pyforge.marshal.seed.engine import MaterializeVerb

    assert captured[0].verb is MaterializeVerb.COPY
    assert captured[0].confirm is False


# --- --include-seeded --------------------------------------------------------


def _seeded_action(artifact_id: str, path: str) -> Action:
    return Action(
        artifact_id=artifact_id,
        artifact_class=ArtifactClass.COPIED_SEEDED,
        current_state=ArtifactState.ABSENT,
        target_state=ArtifactState.PRESENT_CONFORMANT,
        target_path=path,
        chosen_anchor=(),
        rationale="migration offer",
    )


def test_migration_offered_copied_seeded_is_skipped_by_default(clean_repo, monkeypatch):
    write_state(_seed_state(), repo_root=clean_repo, never_write=_NO_NEVER_WRITE)
    _commit_all(clean_repo)

    def migration_fn(view, state):
        return Plan(
            actions=(_seeded_action("offer", "OFFER.md"),),
            repo_fingerprint=RepoFingerprint(git_head=None, dirty=True, artifact_hashes=()),
        )

    migration = Migration(from_version=_V1, to_version=_V2, fn=migration_fn)
    monkeypatch.setattr(migrate_registry, "MIGRATIONS", (migration,))
    manifest_v2 = _manifest(model_version=_V2)

    result = run_update(clean_repo, manifest_v2, confirm=_unreachable_confirm)

    assert result.plan.actions == ()
    (skipped,) = result.plan.skipped
    assert skipped.artifact_id == "offer"
    assert skipped.pattern == migrate_registry._SEEDED_OFFER_PATTERN


def test_include_seeded_applies_the_migration_offered_action(clean_repo, monkeypatch):
    write_state(_seed_state(), repo_root=clean_repo, never_write=_NO_NEVER_WRITE)
    _commit_all(clean_repo)

    def migration_fn(view, state):
        return Plan(
            actions=(_seeded_action("offer", "OFFER.md"),),
            repo_fingerprint=RepoFingerprint(git_head=None, dirty=True, artifact_hashes=()),
        )

    migration = Migration(from_version=_V1, to_version=_V2, fn=migration_fn)
    monkeypatch.setattr(migrate_registry, "MIGRATIONS", (migration,))
    manifest_v2 = _manifest(model_version=_V2)

    result = run_update(clean_repo, manifest_v2, include_seeded=True, confirm=_unreachable_confirm)

    assert [a.artifact_id for a in result.plan.actions] == ["offer"]
    assert result.plan.skipped == ()


# --- migration chain gap / never-write --------------------------------------


def test_migration_chain_gap_propagates_unwrapped(clean_repo):
    write_state(_seed_state(), repo_root=clean_repo, never_write=_NO_NEVER_WRITE)
    _commit_all(clean_repo)
    manifest_v2 = _manifest(model_version=_V2)  # no migration registered from _V1 -> _V2

    with pytest.raises(InternalError, match="migration-chain-gap"):
        run_update(clean_repo, manifest_v2, confirm=_unreachable_confirm)


def test_never_write_target_from_wholesale_regenerate_refused_at_plan_time(clean_repo):
    """``GENERATED_DERIVED``, deliberately -- unlike ``COPIED_MANAGED``/
    ``COPIED_SEEDED``, it is never in ``detect.inventory.
    _WRITABLE_EXEMPTION_CLASSES`` (Story 10.8), so its own declared path
    does not get exempted from a never-write pattern that happens to match
    it (which would otherwise make this test assert the wrong thing)."""
    manifest = Manifest(
        model_version=_V1,
        never_write=("PROTECTED.md",),
        entries=(_generated_derived("protected", "PROTECTED.md"),),
    )
    (clean_repo / "PROTECTED.md").write_text("current\n", encoding="utf-8")
    write_state(
        _seed_state(
            managed=(
                ManagedArtifact(
                    id="protected",
                    path="PROTECTED.md",
                    artifact_class="generated-derived",
                    body_sha=hash_content("current\n"),
                    inserted_region_span=None,
                ),
            ),
        ),
        repo_root=clean_repo,
        never_write=_NO_NEVER_WRITE,
    )
    _commit_all(clean_repo)

    with pytest.raises(PreconditionFailure, match="never-write-target"):
        run_update(clean_repo, manifest, confirm=_unreachable_confirm)


# --- SC-01: fixture repo, registered migration, check -> update -> check ----


def test_sc01_check_update_run_check_end_to_end(clean_repo, monkeypatch):
    """Mirrors ``test_seed_migrate_registry.py``'s own SC-07 pattern, driven
    through the real ``run_update`` verb this time: a v1 fixture repo with a
    registered v1->v2 migration (renaming an artifact) plans, ``--run``
    applies it, and a fresh ``check`` reports the repo conformant afterward."""
    from pyforge.marshal.seed.detect.inventory import ArtifactState, classify
    from pyforge.marshal.seed.verbs.check import run_check

    # Same ID throughout ("renamed"), only its manifest PATH changes v1->v2
    # -- matching test_seed_migrate_registry.py's own SC-07 fixture exactly,
    # and the scenario `run_update`'s own exclusion logic (module docstring)
    # is specifically designed to keep collision-free: "renamed" already has
    # a `state.managed[]` record, so `build_plan`'s own action for it is
    # excluded, and the migration's own claim on it excludes the wholesale-
    # regenerate pass's action too.
    (clean_repo / "old-name.txt").write_text("v1 content\n", encoding="utf-8")
    write_state(
        _seed_state(
            managed=(
                ManagedArtifact(
                    id="renamed",
                    path="old-name.txt",
                    artifact_class="copied-managed",
                    body_sha=hash_content("v1 content\n"),
                    inserted_region_span=None,
                ),
            ),
        ),
        repo_root=clean_repo,
        never_write=_NO_NEVER_WRITE,
    )
    _commit_all(clean_repo)

    v2_manifest = _manifest(_copied_managed("renamed", "new-name.txt"), model_version=_V2)

    def rename_migration(view, state):
        return Plan(
            actions=(_absent_action("renamed", "new-name.txt"),),
            repo_fingerprint=RepoFingerprint(git_head=None, dirty=True, artifact_hashes=()),
        )

    migration = Migration(from_version=_V1, to_version=_V2, fn=rename_migration)
    monkeypatch.setattr(migrate_registry, "MIGRATIONS", (migration,))

    pre_check = run_check(clean_repo, v2_manifest)
    assert pre_check.model_version_status.value != "current"

    plan_result = run_update(clean_repo, v2_manifest, confirm=_unreachable_confirm)
    assert [a.artifact_id for a in plan_result.plan.actions] == ["renamed"]
    _commit_all(clean_repo)

    apply_result = run_update(
        clean_repo,
        v2_manifest,
        run=True,
        yes=True,
        confirm=_unreachable_confirm,
        commit=_fake_commit(v2_manifest, clean_repo),
    )
    assert apply_result.applied == ("renamed",)

    post_inventory = classify(v2_manifest, clean_repo)
    assert all(c.state == ArtifactState.PRESENT_CONFORMANT for c in post_inventory.classifications)

    state_after = read_state(clean_repo)
    assert state_after.model_version == _V2
    assert "2.0.0" in state_after.migrations_applied


# --- REAL _update_commit: whole-file (Genesis-owned allow-listed path) and
# --- hybrid-region (REAL packaged fragment) wiring, mirroring
# --- test_seed_verbs_adopt.py's own two _default_commit proof tests --------


def test_default_commit_materializes_a_whole_file_entry_via_a_custom_template(clean_repo):
    template_root = Path(tempfile.mkdtemp())
    (template_root / ".bmad-config.user.toml").write_text('[project]\nname = "v2"\n', encoding="utf-8")
    manifest = _manifest(_copied_managed("cfg", ".bmad-config.user.toml"))
    (clean_repo / ".bmad-config.user.toml").write_text('[project]\nname = "v1"\n', encoding="utf-8")
    write_state(
        _seed_state(
            managed=(
                ManagedArtifact(
                    id="cfg",
                    path=".bmad-config.user.toml",
                    artifact_class="copied-managed",
                    body_sha=hash_content('[project]\nname = "v1"\n'),
                    inserted_region_span=None,
                ),
            ),
        ),
        repo_root=clean_repo,
        never_write=_NO_NEVER_WRITE,
    )
    _commit_all(clean_repo)

    result = run_update(
        clean_repo,
        manifest,
        run=True,
        yes=True,
        confirm=_unreachable_confirm,
        template_path=template_root,
    )

    assert result.applied == ("cfg",)
    assert (clean_repo / ".bmad-config.user.toml").read_text(encoding="utf-8") == '[project]\nname = "v2"\n'


def test_default_commit_substitutes_a_hybrid_region_via_the_real_packaged_fragment(clean_repo):
    """No ``template_path`` injection needed (``template_path=None``, the
    production default) -- the packaged ``seed/templates/files/tiers.md.j2``
    fragment is read directly. Unlike ``verbs/adopt.py``'s own version of
    this test (which INSERTS into a file that never had the region), this
    one starts with the region ALREADY present -- proving the wholesale
    SUBSTITUTE path against the real packaged content."""
    (clean_repo / "CLAUDE.md").write_text(
        "# My project\n\n### Spec-driven, framework-neutral layout\n\n"
        "<!-- marshal-seed:begin region=tiers model-version=1.0.0 sha=deadbeef -->\n"
        "stale tiers content\n<!-- marshal-seed:end region=tiers -->\n",
        encoding="utf-8",
    )
    manifest = _manifest(
        ManifestEntry(
            id="claude-md-test",
            artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
            path="CLAUDE.md",
            applies_to=AppliesTo.BOTH,
            rationale="test",
            format=RegionFormat.HTML,
            regions=(Region(name="tiers", anchor=("### Spec-driven, framework-neutral layout",)),),
        )
    )
    write_state(
        _seed_state(
            managed=(
                ManagedArtifact(
                    id="claude-md-test",
                    path="CLAUDE.md",
                    artifact_class="hybrid-managed-region",
                    body_sha=hash_content("stale tiers content\n"),
                    inserted_region_span=RegionSpanRecord(name="tiers", start=0, end=0),
                ),
            ),
        ),
        repo_root=clean_repo,
        never_write=_NO_NEVER_WRITE,
    )
    _commit_all(clean_repo)

    result = run_update(clean_repo, manifest, run=True, yes=True, confirm=_unreachable_confirm)

    assert result.applied == ("claude-md-test",)
    content = (clean_repo / "CLAUDE.md").read_text(encoding="utf-8")
    assert "stale tiers content" not in content
    assert content.count("marshal-seed:begin region=tiers") == 1
    assert "# My project" in content


def test_default_commit_wholesale_regenerates_an_adapter_composition_entry(clean_repo):
    """Review finding: the ``GENERATED_DERIVED``/``derive_adapters.
    ADAPTER_COMPOSITION`` branch inside ``_update_commit``'s ``commit()``
    (the ``cursor-rules``/``gemini-md``/``copilot-instructions`` wholesale-
    regen path) had zero test coverage. ``gemini-md`` here matches the REAL
    packaged manifest's own entry id -- ``derive_adapters.render_adapter``
    reads the packaged fragments directly (never through
    ``engine.copier.materialize``, per that module's own docstring), so
    this needs no ``template_path`` injection either, mirroring the
    hybrid-region proof test just above."""
    from pyforge.marshal.seed.derive import adapters as derive_adapters

    manifest = _manifest(_generated_derived("gemini-md", "GEMINI.md"))
    (clean_repo / "GEMINI.md").write_text("stale, pre-refresh content\n", encoding="utf-8")
    write_state(
        _seed_state(
            managed=(
                ManagedArtifact(
                    id="gemini-md",
                    path="GEMINI.md",
                    artifact_class="generated-derived",
                    body_sha=hash_content("stale, pre-refresh content\n"),
                    inserted_region_span=None,
                ),
            ),
        ),
        repo_root=clean_repo,
        never_write=_NO_NEVER_WRITE,
    )
    _commit_all(clean_repo)
    expected = derive_adapters.render_adapter("gemini-md", template_path=None)

    result = run_update(clean_repo, manifest, run=True, yes=True, confirm=_unreachable_confirm)

    assert result.applied == ("gemini-md",)
    content = (clean_repo / "GEMINI.md").read_text(encoding="utf-8")
    assert content == expected
    assert "stale, pre-refresh content" not in content
