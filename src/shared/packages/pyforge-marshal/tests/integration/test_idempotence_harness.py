"""Story 12.5 — AD-60 idempotence harness (SC-03).

Universal shape: run the verb (apply), then detect+plan again and assert
zero actions. Covers ``init``, ``adopt``, and ``update``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from pyforge.marshal.seed.detect.inventory import classify
from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    Manifest,
    ManifestEntry,
)
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.plan.build import build_plan
from pyforge.marshal.seed.verbs.adopt import run_adopt
from pyforge.marshal.seed.verbs.init import run_init
from pyforge.marshal.seed.verbs.update import run_update

_VERSION = ModelVersion.parse("1.0.0")


def _git(repo: Path, *args: str) -> None:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def _commit_all(repo: Path, message: str = "commit") -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message, "--allow-empty")


def _init_git_repo(repo: Path) -> Path:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _commit_all(repo, "initial")
    return repo


def _manifest(*entries: ManifestEntry) -> Manifest:
    return Manifest(model_version=_VERSION, never_write=(), entries=tuple(entries))


def _whole_file(entry_id: str, path: str) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.COPIED_MANAGED,
        path=path,
        applies_to=AppliesTo.BOTH,
        rationale="test",
    )


def _fake_commit(repo: Path):
    def commit(action) -> None:
        target = repo / action.target_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if action.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION:
            body = target.read_text(encoding="utf-8") if target.is_file() else ""
            # Minimal marker wrap so a second detect sees the region present.
            region = "region"
            content = f"{body}<!-- marshal-seed:{region} -->\nbody\n<!-- /marshal-seed:{region} -->\n"
            target.write_text(content, encoding="utf-8")
        else:
            target.write_text(f"# {action.artifact_id}\n", encoding="utf-8")

    return commit


def _plan_after(repo: Path, manifest: Manifest):
    inventory = classify(manifest, repo)
    return build_plan(manifest, inventory, opted_out=frozenset())


def test_init_idempotence_harness(tmp_path: Path):
    target = tmp_path / "fresh"
    manifest = _manifest(_whole_file("whole", "WHOLE.md"))

    first = run_init(target, manifest, commit=_fake_commit(target))
    assert first.applied == ("whole",)
    assert (target / "WHOLE.md").is_file()
    _commit_all(target, "after-init")

    second_plan = _plan_after(target, manifest)
    assert second_plan.actions == ()

    # Second init on the now-non-empty tree needs --force; AD-60 still holds.
    second = run_init(target, manifest, force=True, commit=_fake_commit(target))
    assert second.plan.actions == ()
    assert second.applied == ()


def test_adopt_idempotence_harness_sc03(tmp_path: Path):
    repo = _init_git_repo(tmp_path / "repo")
    manifest = _manifest(_whole_file("whole", "WHOLE.md"))

    first = run_adopt(
        repo,
        manifest,
        apply=True,
        yes=True,
        confirm=lambda: True,
        commit=_fake_commit(repo),
    )
    assert first.applied == ("whole",)
    _commit_all(repo, "after-adopt")

    second = run_adopt(
        repo,
        manifest,
        apply=True,
        yes=True,
        confirm=lambda: True,
        commit=_fake_commit(repo),
    )
    assert second.plan.actions == ()
    assert second.applied == ()


def test_update_idempotence_harness(tmp_path: Path):
    """AD-60 shape for ``update``: after a successful run, detect+plan is empty.

    FR-98 intentionally schedules a wholesale-regenerate action for every
    ``copied-managed``/``hybrid``/``generated-derived`` record in
    ``state.managed[]`` on every update -- that is "always has work by
    design," not an AD-60 failure. The harness therefore exercises the
    empty-managed case (nothing to regenerate): run → detect+plan → zero
    actions, twice.
    """
    from pyforge.marshal.seed.fs import NeverWrite
    from pyforge.marshal.seed.state import seed_model_version, utc_timestamp
    from pyforge.marshal.seed.state.store import SeedState, write_state

    repo = _init_git_repo(tmp_path / "repo")
    manifest = _manifest()
    now = utc_timestamp()
    write_state(
        SeedState(
            model_version=_VERSION,
            seed_model_version=seed_model_version(),
            adopted_at=now,
            last_update=now,
            mode="adopt",
            agents=(),
            managed=(),
            skips=(),
            legacy=(),
            migrations_applied=(),
            opted_out=(),
        ),
        repo_root=repo,
        never_write=NeverWrite(patterns=()),
    )
    _commit_all(repo, "with-empty-state")

    first = run_update(
        repo,
        manifest,
        run=True,
        yes=True,
        confirm=lambda: True,
        commit=_fake_commit(repo),
    )
    assert first.plan.actions == ()
    assert first.applied == ()

    second = run_update(
        repo,
        manifest,
        run=False,
        confirm=lambda: True,
        commit=_fake_commit(repo),
    )
    assert second.plan.actions == ()
