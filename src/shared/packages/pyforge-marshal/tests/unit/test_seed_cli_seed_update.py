"""Unit tests for ``pyforge.marshal.cli.seed.run_update`` (Story 11.4) -- the
thin CLI wiring over ``seed.verbs.update.run_update``: ``--repo-root``/
``--run``/``--force``/``--include-seeded``/``--yes`` argparse plumbing, each
of the exit codes this command can actually reach (0 for a dry-run, an
applied run, and a declined confirmation alike; 10 ``InternalError`` for a
broken packaged-manifest install and for an unanticipated failure deep in
the verb; 2 for an unresolvable ``--repo-root``), the real ``input()``-based
``_real_confirm`` default (exercised through a monkeypatched
``builtins.input``, never a real blocking read), and the DW-FU-11-3 render
fix: a migration-offered ``copied-seeded`` ``SkippedArtifact`` never renders
``matched --skip``.

Mirrors ``test_seed_cli_seed_adopt.py``'s own shape exactly -- exercises
``run_update`` through the SAME ``manifest=``/``confirm=`` test-injection
seam, plus a monkeypatched ``migrate_registry.MIGRATIONS`` where a scenario
needs a synthetic migration."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.cli import seed as seed_cli
from pyforge.marshal.seed.detect.inventory import ArtifactState
from pyforge.marshal.seed.errors import InternalError, PreconditionFailure, UsageError
from pyforge.marshal.seed.fs import NeverWrite
from pyforge.marshal.seed.migrate import registry as migrate_registry
from pyforge.marshal.seed.migrate.registry import Migration
from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    Manifest,
    ManifestEntry,
    ManifestError,
    Region,
)
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.plan.types import Action, Plan, RepoFingerprint
from pyforge.marshal.seed.regions.markers import RegionFormat
from pyforge.marshal.seed.state import (
    ManagedArtifact,
    SeedState,
    write_state,
)

_V1 = ModelVersion.parse("1.0.0")
_V2 = ModelVersion.parse("2.0.0")


def _manifest(*entries: ManifestEntry, model_version: ModelVersion = _V1) -> Manifest:
    return Manifest(model_version=model_version, never_write=(), entries=tuple(entries))


def _copied_managed(entry_id: str, path: str) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.COPIED_MANAGED,
        path=path,
        applies_to=AppliesTo.BOTH,
        rationale="test",
    )


def _hybrid(entry_id: str, path: str, region_name: str) -> ManifestEntry:
    """A hybrid entry whose ``region_name`` matches one of the six REAL
    packaged ``seed/templates/files/*.j2`` fragments -- mirrors
    ``test_seed_cli_seed_adopt.py``'s own ``_hybrid`` helper and its own
    docstring's rationale: exercising the CLI's REAL, non-injected default
    commit path needs no manifest-boundary-safe path or template content of
    its own, unlike a ``_copied_managed`` entry (the packaged template tree
    ships no whole-file content for an arbitrary synthetic id)."""
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
        path=path,
        applies_to=AppliesTo.BOTH,
        rationale="test",
        format=RegionFormat.HTML,
        regions=(Region(name=region_name, anchor=("# anchor",)),),
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


@pytest.fixture
def clean_repo(tmp_path: Path) -> Path:
    _init_git_repo(tmp_path)
    return tmp_path


def _seed_state(*, model_version: ModelVersion = _V1, managed: tuple[ManagedArtifact, ...] = ()) -> SeedState:
    return SeedState(
        model_version=model_version,
        seed_model_version="0.1.0",
        adopted_at="2026-08-21T00:00:00Z",
        last_update="2026-08-21T00:00:00Z",
        mode="adopt",
        agents=(),
        managed=managed,
        skips=(),
        legacy=(),
        migrations_applied=(),
        opted_out=(),
    )


def _args(
    *,
    repo_root: str | None = None,
    run: bool = False,
    force: bool = False,
    include_seeded: bool = False,
    yes: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(
        repo_root=repo_root,
        run=run,
        force=force,
        include_seeded=include_seeded,
        yes=yes,
    )


# --- argparse wiring ---------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="marshal")
    subparsers = parser.add_subparsers(dest="command", required=True)
    seed_cli.add_seed_subparser(subparsers)
    return parser


def test_update_parser_defaults(tmp_path):
    parser = _build_parser()

    args = parser.parse_args(["seed", "update"])

    assert args.repo_root is None
    assert args.run is False
    assert args.force is False
    assert args.include_seeded is False
    assert args.yes is False
    assert args.dry_run is False
    assert args.json is False
    assert args.quiet is False
    assert args.handler is seed_cli.run_update


def test_update_parser_wires_the_expected_flags(tmp_path):
    parser = _build_parser()

    args = parser.parse_args(
        [
            "seed",
            "update",
            "--repo-root",
            str(tmp_path),
            "--run",
            "--force",
            "--include-seeded",
            "--yes",
            "--json",
            "--quiet",
        ]
    )

    assert args.repo_root == str(tmp_path)
    assert args.run is True
    assert args.force is True
    assert args.include_seeded is True
    assert args.yes is True
    assert args.json is True
    assert args.quiet is True


# --- exit code 0: dry-run, applied, and declined are all ordinary outcomes -


def test_exit_code_0_on_a_dry_run_with_no_managed_content(clean_repo, capsys):
    manifest = _manifest()
    write_state(_seed_state(), repo_root=clean_repo, never_write=NeverWrite(patterns=()))

    code = seed_cli.run_update(_args(repo_root=str(clean_repo)), manifest=manifest)

    out = capsys.readouterr().out
    assert code == 0
    assert "empty" in out


def test_exit_code_0_on_an_applied_run(clean_repo, capsys):
    # A hybrid entry, not a whole-file one: the CLI's real, non-injected
    # `run_update` uses the production default commit (`_update_commit`),
    # and a hybrid region's body is read directly off the packaged template
    # (never through `engine.copier.materialize()`) -- see `_hybrid`'s own
    # docstring.
    manifest = _manifest(_hybrid("whole", "WHOLE.md", "tiers"))

    code = seed_cli.run_update(
        _args(repo_root=str(clean_repo), run=True, yes=True),
        manifest=manifest,
        confirm=lambda: (_ for _ in ()).throw(AssertionError("should not be called with --yes")),
    )

    out = capsys.readouterr().out
    assert code == 0
    assert "applied 1 artifact" in out
    assert "whole" in out


def test_exit_code_0_on_a_declined_confirmation(clean_repo, capsys):
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    code = seed_cli.run_update(_args(repo_root=str(clean_repo), run=True), manifest=manifest, confirm=lambda: False)

    out = capsys.readouterr().out
    assert code == 0
    assert "declined" in out
    assert not (clean_repo / "WHOLE.md").exists()


def test_exit_code_0_on_an_empty_plan_apply(clean_repo, capsys):
    manifest = _manifest()

    code = seed_cli.run_update(_args(repo_root=str(clean_repo), run=True, yes=True), manifest=manifest)

    out = capsys.readouterr().out
    assert code == 0
    assert "empty" in out


# --- exit code 3: PreconditionFailure -----------------------------------


def test_exit_code_3_on_a_non_git_repo_root(tmp_path, capsys):
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    code = seed_cli.run_update(_args(repo_root=str(tmp_path), run=True, yes=True), manifest=manifest)

    out = capsys.readouterr().out
    assert code == PreconditionFailure.exit_code == 3
    assert "not-a-git-repo" in out


# --- exit code 10 (InternalError, the broken-install path) -----------------


def test_a_broken_packaged_manifest_reports_internal_error(clean_repo, monkeypatch, capsys):
    def _broken() -> Manifest:
        raise ManifestError("manifest: simulated packaging failure")

    monkeypatch.setattr(seed_cli, "_load_packaged_manifest", _broken)

    code = seed_cli.run_update(_args(repo_root=str(clean_repo)))

    out = capsys.readouterr().out
    assert code == InternalError.exit_code == 10
    assert "reinstall pyforge-marshal" in out


def test_an_unanticipated_failure_from_the_verb_is_never_a_traceback(clean_repo, monkeypatch, capsys):
    def _boom(*args, **kwargs):
        raise RuntimeError("simulated unanticipated failure deep in the verb")

    monkeypatch.setattr(seed_cli, "_run_update_verb", _boom)
    manifest = _manifest()

    code = seed_cli.run_update(_args(repo_root=str(clean_repo)), manifest=manifest)

    out = capsys.readouterr().out
    assert code == InternalError.exit_code == 10
    assert "simulated unanticipated failure" in out


def test_migration_chain_gap_reports_internal_error(clean_repo, monkeypatch, capsys):
    write_state(_seed_state(), repo_root=clean_repo, never_write=NeverWrite(patterns=()))
    manifest_v2 = _manifest(model_version=_V2)
    monkeypatch.setattr(migrate_registry, "MIGRATIONS", ())

    code = seed_cli.run_update(_args(repo_root=str(clean_repo)), manifest=manifest_v2)

    out = capsys.readouterr().out
    assert code == InternalError.exit_code == 10
    assert "migration-chain-gap" in out


# --- exit code 2: --repo-root usage error -------------------------------


def test_exit_code_2_on_an_unresolvable_repo_root(tmp_path, capsys):
    missing = tmp_path / "does-not-exist"
    manifest = _manifest()

    code = seed_cli.run_update(_args(repo_root=str(missing)), manifest=manifest)

    out = capsys.readouterr().out
    assert code == UsageError.exit_code == 2
    assert str(missing) in out


# --- the real, input()-based confirm default ----------------------------


def test_real_confirm_reads_input_and_accepts_yes(clean_repo, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")
    manifest = _manifest(_hybrid("whole", "WHOLE.md", "tiers"))

    code = seed_cli.run_update(_args(repo_root=str(clean_repo), run=True), manifest=manifest)

    out = capsys.readouterr().out
    assert code == 0
    assert "applied 1 artifact" in out


def test_real_confirm_declines_on_eof_never_hangs(clean_repo, monkeypatch, capsys):
    def _raise_eof(_prompt: str) -> str:
        raise EOFError

    monkeypatch.setattr("builtins.input", _raise_eof)
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    code = seed_cli.run_update(_args(repo_root=str(clean_repo), run=True), manifest=manifest)

    out = capsys.readouterr().out
    assert code == 0
    assert "declined" in out
    assert not (clean_repo / "WHOLE.md").exists()


def test_real_confirm_declines_on_a_non_yes_answer(clean_repo, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    code = seed_cli.run_update(_args(repo_root=str(clean_repo), run=True), manifest=manifest)

    out = capsys.readouterr().out
    assert code == 0
    assert "declined" in out


# --- DW-FU-11-3: a migration offer never renders "matched --skip" ----------


def test_migration_offered_copied_seeded_renders_as_an_explicit_offer_never_matched_skip(
    clean_repo, monkeypatch, capsys
):

    write_state(_seed_state(), repo_root=clean_repo, never_write=NeverWrite(patterns=()))
    _commit_all(clean_repo)

    def migration_fn(view, state):
        offer = Action(
            artifact_id="offer",
            artifact_class=ArtifactClass.COPIED_SEEDED,
            current_state=ArtifactState.ABSENT,
            target_state=ArtifactState.PRESENT_CONFORMANT,
            target_path="OFFER.md",
            chosen_anchor=(),
            rationale="migration offer",
        )
        return Plan(
            actions=(offer,),
            repo_fingerprint=RepoFingerprint(git_head=None, dirty=True, artifact_hashes=()),
        )

    migration = Migration(from_version=_V1, to_version=_V2, fn=migration_fn)
    monkeypatch.setattr(migrate_registry, "MIGRATIONS", (migration,))
    manifest_v2 = _manifest(model_version=_V2)

    code = seed_cli.run_update(_args(repo_root=str(clean_repo)), manifest=manifest_v2)

    out = capsys.readouterr().out
    assert code == 0
    assert "offered by a migration; not applied without --include-seeded" in out
    assert "matched --skip" not in out


def test_render_update_plan_text_directly_proves_the_dw_fu_11_3_fix():
    """A direct unit test on the renderer itself, isolated from the verb --
    mirrors this module's own review-finding-regression convention."""
    from pyforge.marshal.seed.plan.types import SkippedArtifact

    plan = Plan(
        actions=(),
        repo_fingerprint=RepoFingerprint(git_head=None, dirty=False, artifact_hashes=()),
        skipped=(
            SkippedArtifact(
                artifact_id="offer",
                target_path="OFFER.md",
                pattern=migrate_registry._SEEDED_OFFER_PATTERN,
            ),
        ),
    )

    text = seed_cli._render_update_plan_text(plan)

    assert "offered by a migration; not applied without --include-seeded" in text
    assert "matched --skip" not in text


def test_render_update_plan_text_still_renders_an_ordinary_skip_pattern():
    from pyforge.marshal.seed.plan.types import SkippedArtifact

    plan = Plan(
        actions=(),
        repo_fingerprint=RepoFingerprint(git_head=None, dirty=False, artifact_hashes=()),
        skipped=(SkippedArtifact(artifact_id="x", target_path="X.md", pattern="X.md"),),
    )

    text = seed_cli._render_update_plan_text(plan)

    assert "matched --skip 'X.md'" in text


# --- --include-seeded reaches the verb -----------------------------------


def test_include_seeded_flag_reaches_the_verb(clean_repo, monkeypatch, capsys):

    write_state(_seed_state(), repo_root=clean_repo, never_write=NeverWrite(patterns=()))
    _commit_all(clean_repo)

    def migration_fn(view, state):
        offer = Action(
            artifact_id="offer",
            artifact_class=ArtifactClass.COPIED_SEEDED,
            current_state=ArtifactState.ABSENT,
            target_state=ArtifactState.PRESENT_CONFORMANT,
            target_path="OFFER.md",
            chosen_anchor=(),
            rationale="migration offer",
        )
        return Plan(
            actions=(offer,),
            repo_fingerprint=RepoFingerprint(git_head=None, dirty=True, artifact_hashes=()),
        )

    migration = Migration(from_version=_V1, to_version=_V2, fn=migration_fn)
    monkeypatch.setattr(migrate_registry, "MIGRATIONS", (migration,))
    manifest_v2 = _manifest(model_version=_V2)

    code = seed_cli.run_update(_args(repo_root=str(clean_repo), include_seeded=True), manifest=manifest_v2)

    out = capsys.readouterr().out
    assert code == 0
    assert "offer" in out
    assert "not applied without --include-seeded" not in out
