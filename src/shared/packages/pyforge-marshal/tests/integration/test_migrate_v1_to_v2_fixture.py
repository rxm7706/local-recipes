"""SC-07's end-to-end proof (Story 11.3): a simulated breaking model change
-- a tier-table rule change plus a renamed managed artifact, v1 -> v2 -- is
absorbed by a migration in a fixture repo with ZERO manual edits, and
``marshal seed check``'s own underlying logic (``seed.verbs.check.run_check``,
called directly -- see below) reports green afterward.

The fixture repo starts "adopted" at v1: ``GOVERNANCE.md`` already carries an
inserted ``tier-table`` hybrid-managed-region (the v1 rule), ``OLD_GUIDE.md``
is a plain ``copied-managed`` file, and a real ``.marshal/seed-state.yml``
records both via ``state.store.write_state`` (never hand-written YAML).
Both manifests (v1 and v2) are hand-constructed ``Manifest``/``ManifestEntry``
objects, never loaded from a YAML fixture file -- this story's own migration
mechanism is what is under test here, not manifest loading (that is
``model/manifest.py``'s own, already-shipped surface).

The fixture ``Migration`` produces two actions: rewrite the ``tier-table``
region's body under the v2 rule (``current_state=PRESENT_DIVERGENT``,
``chosen_anchor=()`` -- the region already exists, so there is nothing to
anchor; see ``registry.py``'s own Design Notes on why a rewrite of existing
content never populates ``chosen_anchor``), and remove ``OLD_GUIDE.md``
(``target_state=ArtifactState.ABSENT``). A small, LOCAL ``commit`` callback
-- written once for this fixture's own two action shapes, never wired into
``verbs/adopt.py``'s generic dispatch (that is Story 11.4's surface) --
applies the region rewrite via ``regions.apply.substitute_region`` (the real,
already-shipped primitive built for exactly "replace an existing region's
begin marker and body in one guarded write") and the removal via
``fs.remove``. The migration's own composed ``Plan`` is applied through the
SAME ``apply.run.run_apply`` path every other verb uses.

A SECOND, freshly-computed plan -- ``plan.build.build_plan(v2_manifest,
classify(v2_manifest, repo_root))``, real and UNMODIFIED, run only AFTER the
migration's own plan has been applied -- materializes the new ``new-guide``
artifact the v2 manifest introduces (``OLD_GUIDE.md``'s renamed replacement).
Both applications together are the "zero manual edits" the epics AC names:
nothing here writes to the repo except through a ``Plan``/``run_apply``/
``commit`` triple.

Finally, the post-apply ``SeedState`` is reconstructed locally (mirroring
``verbs/adopt.py::_build_state_after_apply``'s SHAPE -- carry forward what
was not touched, record a fresh ``ManagedArtifact`` per materialized action,
never import the private function itself, per this story's own Never
bullet) and persisted, and ``seed.verbs.check.run_check(repo_root,
v2_manifest)`` -- the same, real, unmodified function ``cli/seed.py``'s
``check`` subcommand delegates every decision to -- is called DIRECTLY
(there is no ``--manifest`` CLI override flag, so a synthetic v2 fixture
manifest cannot be pointed at from the literal CLI binary) and asserted
``failing is False``.
"""

from __future__ import annotations

from pathlib import Path

from pyforge.marshal.seed import fs
from pyforge.marshal.seed.apply.run import run_apply
from pyforge.marshal.seed.detect.hashes import hash_content, region_body_text
from pyforge.marshal.seed.detect.inventory import ArtifactState, classify
from pyforge.marshal.seed.migrate.registry import (
    Migration,
    RepoView,
    _repo_fingerprint,
    run_migrations,
)
from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    Manifest,
    ManifestEntry,
    Region,
)
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.plan.build import build_plan
from pyforge.marshal.seed.plan.types import Action, Plan
from pyforge.marshal.seed.regions.apply import substitute_region
from pyforge.marshal.seed.regions.markers import (
    RegionFormat,
    region_sha,
    render_begin,
    render_end,
)
from pyforge.marshal.seed.regions.parse import parse_regions
from pyforge.marshal.seed.state import (
    SeedState,
    read_state,
    seed_model_version,
    utc_timestamp,
    write_state,
)
from pyforge.marshal.seed.state.store import ManagedArtifact, RegionSpanRecord
from pyforge.marshal.seed.verbs.check import run_check

_V1_VERSION = ModelVersion.parse("1.0.0")
_V2_VERSION = ModelVersion.parse("2.0.0")

_OLD_TIER_BODY = "Old tier rule (v1): every recipe ships the same python_min floor.\n"
_NEW_TIER_BODY = "New tier rule (v2): python_min is pinned per platform in the release matrix.\n"
_OLD_GUIDE_TEXT = "This is the old guide.\n"
_NEW_GUIDE_TEXT = "This is the new guide, replacing old-guide in model_version 2.0.0.\n"

_PROSE_MARKER = "Hand-written governance prose that must survive untouched."


def _v1_governance_text() -> str:
    begin_line = render_begin(RegionFormat.HTML, "tier-table", _V1_VERSION, region_sha(_OLD_TIER_BODY))
    end_line = render_end(RegionFormat.HTML, "tier-table")
    return (
        "# Governance\n\n"
        f"{_PROSE_MARKER}\n\n"
        "## Tiers\n\n"
        f"{begin_line}\n{_OLD_TIER_BODY}{end_line}\n\n"
        "More hand-written prose below the region.\n"
    )


def _governance_entry(rationale: str) -> ManifestEntry:
    return ManifestEntry(
        id="governance",
        artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
        path="GOVERNANCE.md",
        applies_to=AppliesTo.BOTH,
        rationale=rationale,
        format=RegionFormat.HTML,
        regions=(Region(name="tier-table", anchor=("## Tiers",)),),
    )


def _v1_manifest() -> Manifest:
    return Manifest(
        model_version=_V1_VERSION,
        never_write=(),
        entries=(
            _governance_entry("v1 governance doc carrying the tier-table managed region"),
            ManifestEntry(
                id="old-guide",
                artifact_class=ArtifactClass.COPIED_MANAGED,
                path="OLD_GUIDE.md",
                applies_to=AppliesTo.BOTH,
                rationale="the v1 guide, renamed away in v2",
            ),
        ),
    )


def _v2_manifest() -> Manifest:
    return Manifest(
        model_version=_V2_VERSION,
        never_write=(),
        entries=(
            _governance_entry("v2 governance doc carrying the tier-table managed region (v2 rule)"),
            ManifestEntry(
                id="new-guide",
                artifact_class=ArtifactClass.COPIED_MANAGED,
                path="NEW_GUIDE.md",
                applies_to=AppliesTo.BOTH,
                rationale="the v2 guide, replacing old-guide",
            ),
        ),
    )


def _migrate_v1_to_v2(repo: RepoView, state: SeedState) -> Plan:
    """The SC-07 fixture migration: rewrite ``GOVERNANCE.md``'s
    ``tier-table`` region body under the v2 rule, and remove
    ``OLD_GUIDE.md`` (renamed to ``new-guide`` -- a fresh
    ``plan.build.build_plan`` call against the v2 manifest, run separately
    AFTER this migration's own ``Plan`` is applied, materializes the new
    artifact; this migration only retires the old one). Pure (P-12): reads
    ``GOVERNANCE.md``'s current text to self-fingerprint via
    ``registry._repo_fingerprint``, performs no write of any kind."""
    governance_path = "GOVERNANCE.md"
    old_guide_path = "OLD_GUIDE.md"
    actions = tuple(
        sorted(
            (
                Action(
                    artifact_id="governance",
                    artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
                    current_state=ArtifactState.PRESENT_DIVERGENT,
                    target_state=ArtifactState.PRESENT_CONFORMANT,
                    target_path=governance_path,
                    chosen_anchor=(),
                    rationale="the v1 tier-table rule is stale under model_version 2.0.0",
                ),
                Action(
                    artifact_id="old-guide",
                    artifact_class=ArtifactClass.COPIED_MANAGED,
                    current_state=ArtifactState.PRESENT_CONFORMANT,
                    target_state=ArtifactState.ABSENT,
                    target_path=old_guide_path,
                    chosen_anchor=(),
                    rationale="old-guide was renamed to new-guide in model_version 2.0.0",
                ),
            ),
            key=lambda action: action.artifact_id,
        )
    )
    fingerprint = _repo_fingerprint(
        repo.repo_root, {"governance": governance_path, "old-guide": old_guide_path}
    )
    return Plan(actions=actions, repo_fingerprint=fingerprint)


def _migration_commit(repo_root: Path, never_write: fs.NeverWrite):
    """A LOCAL ``commit`` callback matching exactly this fixture's two
    action shapes -- never wired into ``verbs/adopt.py``'s generic
    dispatch, which is Story 11.4's surface (see the module docstring)."""

    def commit(action: Action) -> None:
        if action.artifact_id == "governance":
            target = repo_root / action.target_path
            # `newline=""` -- never plain `read_text()` -- so `text`'s byte
            # offsets stay in sync with `parse_regions`'s own byte-offset
            # contract (`substitute_region`'s own documented requirement).
            text = target.read_text(encoding="utf-8", newline="")
            region = next(
                span for span in parse_regions(text, RegionFormat.HTML) if span.name == "tier-table"
            )
            substitute_region(
                text,
                target,
                region,
                _NEW_TIER_BODY,
                model_version=_V2_VERSION,
                expected_sha=region.sha,
                fmt=RegionFormat.HTML,
                repo_root=repo_root,
                never_write=never_write,
            )
        elif action.artifact_id == "old-guide":
            fs.remove(repo_root / action.target_path, repo_root=repo_root, never_write=never_write)
        else:
            raise AssertionError(f"unexpected migration action {action.artifact_id!r}")

    return commit


def _new_guide_commit(repo_root: Path, never_write: fs.NeverWrite):
    def commit(action: Action) -> None:
        assert action.artifact_id == "new-guide"
        fs.write(
            repo_root / action.target_path,
            _NEW_GUIDE_TEXT.encode("utf-8"),
            repo_root=repo_root,
            never_write=never_write,
        )

    return commit


def test_sc07_v1_to_v2_migration_is_absorbed_with_zero_manual_edits(tmp_path: Path) -> None:
    repo_root = tmp_path
    never_write = fs.NeverWrite(())

    governance_text = _v1_governance_text()
    (repo_root / "GOVERNANCE.md").write_text(governance_text, encoding="utf-8")
    (repo_root / "OLD_GUIDE.md").write_text(_OLD_GUIDE_TEXT, encoding="utf-8")

    tier_span = next(
        span for span in parse_regions(governance_text, RegionFormat.HTML) if span.name == "tier-table"
    )
    v1_state = SeedState(
        model_version=_V1_VERSION,
        seed_model_version=seed_model_version(),
        adopted_at=utc_timestamp(),
        last_update=utc_timestamp(),
        mode="adopt",
        agents=("claude",),
        managed=(
            ManagedArtifact(
                id="governance",
                path="GOVERNANCE.md",
                artifact_class=ArtifactClass.HYBRID_MANAGED_REGION.value,
                body_sha=hash_content(region_body_text(governance_text, tier_span)),
                inserted_region_span=RegionSpanRecord(
                    name=tier_span.name, start=tier_span.body_span[0], end=tier_span.body_span[1]
                ),
            ),
            ManagedArtifact(
                id="old-guide",
                path="OLD_GUIDE.md",
                artifact_class=ArtifactClass.COPIED_MANAGED.value,
                body_sha=hash_content(_OLD_GUIDE_TEXT),
                inserted_region_span=None,
            ),
        ),
        skips=(),
        legacy=(),
        migrations_applied=(),
        opted_out=(),
    )
    write_state(v1_state, repo_root=repo_root, never_write=never_write)
    state = read_state(repo_root)
    assert state is not None

    v1_manifest = _v1_manifest()
    v2_manifest = _v2_manifest()
    assert state.model_version == v1_manifest.model_version

    fixture_migration = Migration(
        from_version=_V1_VERSION,
        to_version=_V2_VERSION,
        description="v1->v2: tier-table rule change + old-guide renamed to new-guide",
        migrate=_migrate_v1_to_v2,
    )

    # RepoView.manifest is the manifest being migrated TOWARD (v2) -- see
    # registry.py's own RepoView docstring.
    outcome = run_migrations(
        RepoView(repo_root=repo_root, manifest=v2_manifest),
        state,
        migrations=(fixture_migration,),
    )
    assert [action.artifact_id for action in outcome.plan.actions] == ["governance", "old-guide"]
    assert outcome.offered_artifact_ids == frozenset()

    run_apply(
        outcome.plan,
        repo_root=repo_root,
        never_write=never_write,
        commit=_migration_commit(repo_root, never_write),
    )

    assert not (repo_root / "OLD_GUIDE.md").exists()
    governance_after_migration = (repo_root / "GOVERNANCE.md").read_text(encoding="utf-8")
    assert _PROSE_MARKER in governance_after_migration
    assert "More hand-written prose below the region." in governance_after_migration
    assert _NEW_TIER_BODY in governance_after_migration

    # A fresh, real, UNMODIFIED build_plan/classify call against the v2
    # manifest -- zero manual edits -- materializes the newly-added
    # `new-guide` artifact. `governance` is already PRESENT_CONFORMANT after
    # the migration above, so it produces no second action here.
    inventory_v2 = classify(v2_manifest, repo_root)
    new_guide_plan = build_plan(v2_manifest, inventory_v2)
    assert [action.artifact_id for action in new_guide_plan.actions] == ["new-guide"]

    run_apply(
        new_guide_plan,
        repo_root=repo_root,
        never_write=never_write,
        commit=_new_guide_commit(repo_root, never_write),
    )

    governance_text_after = (repo_root / "GOVERNANCE.md").read_text(encoding="utf-8")
    tier_span_after = next(
        span
        for span in parse_regions(governance_text_after, RegionFormat.HTML)
        if span.name == "tier-table"
    )
    new_guide_text = (repo_root / "NEW_GUIDE.md").read_text(encoding="utf-8")

    # Reconstruct the post-migration SeedState -- mirroring
    # verbs/adopt.py::_build_state_after_apply's SHAPE (carry forward what
    # was untouched, record a fresh ManagedArtifact per materialized
    # action), written locally per this story's own Never bullet (never
    # import that private function).
    v2_state = SeedState(
        model_version=v2_manifest.model_version,
        seed_model_version=state.seed_model_version,
        adopted_at=state.adopted_at,
        last_update=utc_timestamp(),
        mode="adopt",
        agents=state.agents,
        managed=(
            ManagedArtifact(
                id="governance",
                path="GOVERNANCE.md",
                artifact_class=ArtifactClass.HYBRID_MANAGED_REGION.value,
                body_sha=hash_content(region_body_text(governance_text_after, tier_span_after)),
                inserted_region_span=RegionSpanRecord(
                    name=tier_span_after.name,
                    start=tier_span_after.body_span[0],
                    end=tier_span_after.body_span[1],
                ),
            ),
            ManagedArtifact(
                id="new-guide",
                path="NEW_GUIDE.md",
                artifact_class=ArtifactClass.COPIED_MANAGED.value,
                body_sha=hash_content(new_guide_text),
                inserted_region_span=None,
            ),
        ),
        skips=(),
        legacy=(),
        migrations_applied=(*state.migrations_applied, str(_V2_VERSION)),
        opted_out=(),
    )
    write_state(v2_state, repo_root=repo_root, never_write=never_write)

    # `run_check` is the real, unmodified production logic `cli/seed.py`'s
    # `check` subcommand delegates every decision to -- called directly
    # since there is no `--manifest` CLI override flag to point the literal
    # binary at this synthetic v2 fixture manifest (see the module
    # docstring).
    report = run_check(repo_root, v2_manifest)
    assert report.failing is False, [finding.to_json_dict() for finding in report.findings]
