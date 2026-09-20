"""Meta test -- SC-08 never-write proof through ``run_update`` (Story 12.4).

Proves ``marshal seed update --run`` cannot materialize into Tier-0 Dreams or
Tier-2 planning artifacts:

1. A deliberately malicious **migration** targeting ``docs/dreams/**`` raises
   ``NeverWriteViolation`` during ``migrate.compose`` (plan time) before any
   apply write runs.
2. The same through a **symlinked** ``planning-artifacts`` alias -- the guard
   resolves the real location, matching ``seed/fs.py``'s own symlink-indirect
   test precedent.
3. A deliberately malicious **manifest** wholesale-regenerate action targeting
   ``docs/dreams/**`` is refused before apply with ``PreconditionFailure`` and
   leaves the protected file byte-identical (plan-time gate; ``fs`` would raise
   ``NeverWriteViolation`` if apply were reached).

Bounds (stated, not aspirational): these are fixture-driven integration proofs
living in ``tests/meta/``; they monkeypatch ``migrate_registry.MIGRATIONS``
where a synthetic migration is required, mirroring
``tests/unit/test_seed_verbs_update.py``'s own SC-01 pattern.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.seed.detect.hashes import hash_content
from pyforge.marshal.seed.detect.inventory import ArtifactState
from pyforge.marshal.seed.errors import NeverWriteViolation, PreconditionFailure
from pyforge.marshal.seed.fs import NeverWrite
from pyforge.marshal.seed.migrate import registry as migrate_registry
from pyforge.marshal.seed.migrate.registry import Migration
from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    Manifest,
    ManifestEntry,
)
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.plan.types import Action, Plan, RepoFingerprint
from pyforge.marshal.seed.state import ManagedArtifact, SeedState, write_state
from pyforge.marshal.seed.verbs.update import run_update

_V1 = ModelVersion.parse("1.0.0")
_V1_1 = ModelVersion.parse("1.1.0")
_V2 = ModelVersion.parse("2.0.0")
_NEVER_WRITE = NeverWrite(
    (
        "docs/dreams/*.md",
        "**/planning-artifacts/**",
    )
)


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


def _manifest(*entries: ManifestEntry, model_version: ModelVersion = _V2) -> Manifest:
    return Manifest(
        model_version=model_version,
        never_write=(
            "docs/dreams/*.md",
            "**/planning-artifacts/**",
        ),
        entries=entries,
    )


def _generated_derived(entry_id: str, path: str) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.GENERATED_DERIVED,
        path=path,
        applies_to=AppliesTo.BOTH,
        rationale="meta-test",
    )


def _seed_state(*, managed: tuple[ManagedArtifact, ...] = ()) -> SeedState:
    return SeedState(
        model_version=_V1,
        seed_model_version="0.1.0",
        adopted_at="2026-08-21T00:00:00Z",
        last_update="2026-08-21T00:00:00Z",
        mode="adopt",
        agents=(),
        managed=managed,
        skips=(),
        legacy=(),
        migrations_applied=(str(_V1),),
        opted_out=(),
    )


def _absent_action(artifact_id: str, path: str) -> Action:
    return Action(
        artifact_id=artifact_id,
        artifact_class=ArtifactClass.COPIED_MANAGED,
        current_state=ArtifactState.ABSENT,
        target_state=ArtifactState.PRESENT_CONFORMANT,
        target_path=path,
        chosen_anchor=(),
        rationale="malicious migration",
    )


def _migration_plan(*actions: Action) -> Plan:
    return Plan(
        actions=actions,
        repo_fingerprint=RepoFingerprint(git_head=None, dirty=False, artifact_hashes=()),
    )


@pytest.fixture
def seeded_repo(tmp_path: Path) -> Path:
    _init_git_repo(tmp_path)
    write_state(_seed_state(), repo_root=tmp_path, never_write=_NEVER_WRITE)
    _commit_all(tmp_path)
    return tmp_path


def test_malicious_migration_to_dreams_raises_never_write_violation_via_run_update(
    seeded_repo: Path, monkeypatch: pytest.MonkeyPatch
):
    dream_path = seeded_repo / "docs" / "dreams" / "evil.md"
    dream_path.parent.mkdir(parents=True, exist_ok=True)
    before = dream_path.read_bytes() if dream_path.exists() else b""

    migration = Migration(
        from_version=_V1,
        to_version=_V2,
        fn=lambda _view, _state: _migration_plan(_absent_action("dream", "docs/dreams/evil.md")),
    )
    monkeypatch.setattr(migrate_registry, "MIGRATIONS", (migration,))

    with pytest.raises(NeverWriteViolation) as excinfo:
        run_update(
            seeded_repo,
            _manifest(model_version=_V2),
            run=True,
            yes=True,
            confirm=lambda: True,
        )

    assert "docs/dreams/*.md" in str(excinfo.value)
    after = dream_path.read_bytes() if dream_path.exists() else b""
    assert after == before


def test_malicious_migration_to_symlinked_planning_artifacts_raises_never_write_violation(
    seeded_repo: Path, monkeypatch: pytest.MonkeyPatch
):
    """Symlink case: the *caller* path has no ``planning-artifacts`` segment;
    only resolution into the protected tree must trip the guard (SC-08)."""
    real_dir = seeded_repo / "real" / "planning-artifacts"
    real_dir.mkdir(parents=True)
    alias = seeded_repo / "_bmad-output" / "pa-link"
    alias.parent.mkdir(parents=True)
    alias.symlink_to(real_dir)
    target = real_dir / "evil.md"
    before = b""

    migration = Migration(
        from_version=_V1,
        to_version=_V2,
        fn=lambda _view, _state: _migration_plan(_absent_action("prd", "_bmad-output/pa-link/evil.md")),
    )
    monkeypatch.setattr(migrate_registry, "MIGRATIONS", (migration,))

    with pytest.raises(NeverWriteViolation) as excinfo:
        run_update(
            seeded_repo,
            _manifest(model_version=_V2),
            run=True,
            yes=True,
            confirm=lambda: True,
        )

    assert "planning-artifacts" in str(excinfo.value)
    assert "planning-artifacts" not in "_bmad-output/pa-link/evil.md"
    assert not target.exists() or target.read_bytes() == before


def test_malicious_manifest_wholesale_regenerate_cannot_write_to_dreams(seeded_repo: Path):
    dream_path = seeded_repo / "docs" / "dreams" / "protected.md"
    dream_path.parent.mkdir(parents=True, exist_ok=True)
    dream_path.write_text("original tier-0 content\n", encoding="utf-8")
    before = dream_path.read_text(encoding="utf-8")

    manifest = _manifest(
        _generated_derived("dream", "docs/dreams/protected.md"),
        model_version=_V1,
    )
    write_state(
        _seed_state(
            managed=(
                ManagedArtifact(
                    id="dream",
                    path="docs/dreams/protected.md",
                    artifact_class="generated-derived",
                    body_sha=hash_content(before),
                    inserted_region_span=None,
                ),
            ),
        ),
        repo_root=seeded_repo,
        never_write=_NEVER_WRITE,
    )
    _commit_all(seeded_repo)

    with pytest.raises(PreconditionFailure, match="never-write-target"):
        run_update(
            seeded_repo,
            manifest,
            run=True,
            yes=True,
            confirm=lambda: True,
        )

    assert dream_path.read_text(encoding="utf-8") == before
