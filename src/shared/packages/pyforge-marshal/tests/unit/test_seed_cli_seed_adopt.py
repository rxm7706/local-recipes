"""Unit tests for ``pyforge.marshal.cli.seed.run_adopt`` (Story 10.6) -- the
thin CLI wiring over ``seed.verbs.adopt.run_adopt``: ``--repo-root``/
``--apply``/``--yes``/``--agents``/``--skip``/``--force`` argparse plumbing,
each of the exit codes this command can actually reach (0 for a dry-run, an
applied run, and a declined confirmation alike -- none of those is an error;
3 ``PreconditionFailure`` for a non-git ``--repo-root``; 10 ``InternalError``
for a broken packaged-manifest install and for an unanticipated failure deep
in the verb), and the real ``input()``-based ``_real_confirm`` default
(exercised through a monkeypatched ``builtins.input``, never a real blocking
read).

Exercises ``run_adopt`` through the SAME ``manifest=``/``confirm=``
test-injection seam ``run_check`` already establishes (``manifest=``) and
this story extends (``confirm=``), rather than against the real 43-entry
packaged manifest, so a scenario's shape is legible from its own fixture
instead of from ``templates/manifest.yaml``'s current, independently-evolving
content. A real-``argparse``-parsing test (``test_adopt_parser_wires_the_
expected_flags``) separately proves the production dispatch path (``main.py``
-> ``add_seed_subparser`` -> ``run_adopt(args)``, no ``manifest=``/``confirm=``
supplied) resolves the SAME attributes this file's direct-``Namespace``
tests construct by hand."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.cli import seed as seed_cli
from pyforge.marshal.seed.errors import InternalError, PreconditionFailure, UsageError
from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    Manifest,
    ManifestEntry,
    ManifestError,
    Region,
)
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.regions.markers import RegionFormat
from pyforge.marshal.seed.state import read_state

_VERSION = ModelVersion.parse("1.0.0")


def _manifest(*entries: ManifestEntry) -> Manifest:
    return Manifest(model_version=_VERSION, never_write=(), entries=tuple(entries))


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
    packaged ``seed/templates/files/*.j2`` fragments -- unlike a whole-file
    class, a hybrid region's body is read directly off the packaged template
    (``verbs/adopt.py``'s own ``_region_body_from_template``), never routed
    through ``engine.copier.materialize()`` at all, so these tests -- which
    exercise the CLI's REAL, non-injected default commit path -- need no
    manifest-boundary-safe path or template content of their own (unlike a
    ``_copied_managed`` entry, for which the packaged template tree ships no
    whole-file content yet; see ``verbs/adopt.py``'s module docstring)."""
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


@pytest.fixture
def clean_repo(tmp_path: Path) -> Path:
    _init_git_repo(tmp_path)
    return tmp_path


def _args(
    *,
    repo_root: str | None = None,
    apply: bool = False,
    yes: bool = False,
    agents: str | None = None,
    skip: list[str] | None = None,
    force: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(repo_root=repo_root, apply=apply, yes=yes, agents=agents, skip=skip, force=force)


# --- argparse wiring ---------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="marshal")
    subparsers = parser.add_subparsers(dest="command", required=True)
    seed_cli.add_seed_subparser(subparsers)
    return parser


def test_adopt_parser_defaults(tmp_path):
    parser = _build_parser()

    args = parser.parse_args(["seed", "adopt"])

    assert args.repo_root is None
    assert args.apply is False
    assert args.yes is False
    assert args.agents is None
    assert args.skip is None
    assert args.force is False
    assert args.dry_run is False
    assert args.json is False
    assert args.quiet is False
    assert args.handler is seed_cli.run_adopt


def test_adopt_parser_wires_the_expected_flags(tmp_path):
    parser = _build_parser()

    args = parser.parse_args(
        [
            "seed",
            "adopt",
            "--repo-root",
            str(tmp_path),
            "--apply",
            "--yes",
            "--agents",
            "claude,cursor",
            "--skip",
            "docs/*",
            "--skip",
            "scripts/*",
            "--force",
        ]
    )

    assert args.repo_root == str(tmp_path)
    assert args.apply is True
    assert args.yes is True
    assert args.agents == "claude,cursor"
    assert args.skip == ["docs/*", "scripts/*"]
    assert args.force is True


# --- exit code 0: dry-run, applied, and declined are all ordinary outcomes -


def test_exit_code_0_on_a_dry_run(clean_repo, capsys):
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    code = seed_cli.run_adopt(_args(repo_root=str(clean_repo)), manifest=manifest)

    out = capsys.readouterr().out
    assert code == 0
    assert "dry-run" in out
    assert "WHOLE.md" in out
    assert not (clean_repo / "WHOLE.md").exists()


def test_first_claim_action_is_visually_marked_in_the_printed_plan(clean_repo, capsys):
    """Review finding: this feature's whole safety model is "a human
    reviews the plan before anything destructive happens" -- a first-claim
    (FR-83) action that overwrites a pre-existing, unrelated file must be
    visually distinct in the printed plan, not buried in prose
    indistinguishable at a glance from an ordinary "create" action."""
    (clean_repo / "WHOLE.md").write_text("unrelated pre-existing content\n", encoding="utf-8")
    _git(clean_repo, "add", "WHOLE.md")
    _git(clean_repo, "commit", "-m", "pre-existing")
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    code = seed_cli.run_adopt(_args(repo_root=str(clean_repo)), manifest=manifest)

    out = capsys.readouterr().out
    assert code == 0
    assert "[OVERWRITES EXISTING FILE] whole" in out


def test_exit_code_0_on_an_applied_run(clean_repo, capsys):
    # A hybrid entry, not a whole-file one: the CLI's real, non-injected
    # ``run_adopt`` uses the production default ``commit`` (``_default_
    # commit``), and a hybrid region's body is read directly off the
    # packaged template (never through ``engine.copier.materialize()``),
    # so this is exercisable without a boundary-safe path or injected
    # template content -- see ``_hybrid``'s own docstring.
    manifest = _manifest(_hybrid("whole", "WHOLE.md", "tiers"))

    code = seed_cli.run_adopt(
        _args(repo_root=str(clean_repo), apply=True, yes=True),
        manifest=manifest,
        confirm=lambda: (_ for _ in ()).throw(AssertionError("should not be called with --yes")),
    )

    out = capsys.readouterr().out
    assert code == 0
    assert "applied 1 artifact" in out
    assert "whole" in out
    assert "marshal-seed:begin region=tiers" in (clean_repo / "WHOLE.md").read_text(encoding="utf-8")


def test_exit_code_0_on_a_declined_confirmation(clean_repo, capsys):
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    code = seed_cli.run_adopt(_args(repo_root=str(clean_repo), apply=True), manifest=manifest, confirm=lambda: False)

    out = capsys.readouterr().out
    assert code == 0
    assert "declined" in out
    assert not (clean_repo / "WHOLE.md").exists()


def test_exit_code_0_on_an_empty_plan_apply(clean_repo, capsys):
    manifest = _manifest()

    code = seed_cli.run_adopt(_args(repo_root=str(clean_repo), apply=True, yes=True), manifest=manifest)

    out = capsys.readouterr().out
    assert code == 0
    assert "empty" in out


# --- --agents/--skip parsing reaches the verb --------------------------


def test_agents_and_skip_flags_reach_the_verb(clean_repo, capsys):
    # "other" is --skip'd (never committed, so its class does not matter for
    # the boundary/template concern -- see test_exit_code_0_on_an_applied_run's
    # own comment); "whole" IS applied, so it must be a hybrid entry.
    manifest = _manifest(_hybrid("whole", "WHOLE.md", "tiers"), _copied_managed("other", "OTHER.md"))

    code = seed_cli.run_adopt(
        _args(repo_root=str(clean_repo), apply=True, yes=True, agents="claude,cursor", skip=["OTHER.md"]),
        manifest=manifest,
    )

    assert code == 0
    assert not (clean_repo / "OTHER.md").exists()
    state = read_state(clean_repo)
    assert state.agents == ("claude", "cursor")
    assert "OTHER.md" in state.skips


# --- exit code 3: PreconditionFailure ---------------------------------


def test_exit_code_3_on_a_non_git_repo_root(tmp_path, capsys):
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    code = seed_cli.run_adopt(_args(repo_root=str(tmp_path), apply=True, yes=True), manifest=manifest)

    out = capsys.readouterr().out
    assert code == PreconditionFailure.exit_code == 3
    assert "not-a-git-repo" in out


# --- exit code 10 (InternalError, the broken-install path) -----------------


def test_a_broken_packaged_manifest_reports_internal_error(clean_repo, monkeypatch, capsys):
    def _broken() -> Manifest:
        raise ManifestError("manifest: simulated packaging failure")

    monkeypatch.setattr(seed_cli, "_load_packaged_manifest", _broken)

    code = seed_cli.run_adopt(_args(repo_root=str(clean_repo)))

    out = capsys.readouterr().out
    assert code == InternalError.exit_code == 10
    assert "reinstall pyforge-marshal" in out


def test_an_unanticipated_failure_from_the_verb_is_never_a_traceback(clean_repo, monkeypatch, capsys):
    """Mirrors ``test_seed_cli_seed_check.py``'s identical review-finding
    regression test: the verb call must be INSIDE the ``try``, so a bare
    exception raised deep in the call chain is caught and reported as
    ``InternalError`` (10), never re-raised as a raw traceback."""

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated unanticipated failure deep in the verb")

    monkeypatch.setattr(seed_cli, "_run_adopt_verb", _boom)
    manifest = _manifest()

    code = seed_cli.run_adopt(_args(repo_root=str(clean_repo)), manifest=manifest)

    out = capsys.readouterr().out
    assert code == InternalError.exit_code == 10
    assert "simulated unanticipated failure" in out


# --- exit code 2: --repo-root usage error -------------------------------


def test_exit_code_2_on_an_unresolvable_repo_root(tmp_path, capsys):
    missing = tmp_path / "does-not-exist"
    manifest = _manifest()

    code = seed_cli.run_adopt(_args(repo_root=str(missing)), manifest=manifest)

    out = capsys.readouterr().out
    assert code == UsageError.exit_code == 2
    assert str(missing) in out


# --- the real, input()-based confirm default ----------------------------


def test_real_confirm_reads_input_and_accepts_yes(clean_repo, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")
    manifest = _manifest(_hybrid("whole", "WHOLE.md", "tiers"))

    code = seed_cli.run_adopt(_args(repo_root=str(clean_repo), apply=True), manifest=manifest)

    out = capsys.readouterr().out
    assert code == 0
    assert "applied 1 artifact" in out


def test_real_confirm_declines_on_eof_never_hangs(clean_repo, monkeypatch, capsys):
    def _raise_eof(_prompt: str) -> str:
        raise EOFError

    monkeypatch.setattr("builtins.input", _raise_eof)
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    code = seed_cli.run_adopt(_args(repo_root=str(clean_repo), apply=True), manifest=manifest)

    out = capsys.readouterr().out
    assert code == 0
    assert "declined" in out
    assert not (clean_repo / "WHOLE.md").exists()


def test_real_confirm_declines_on_a_non_yes_answer(clean_repo, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    code = seed_cli.run_adopt(_args(repo_root=str(clean_repo), apply=True), manifest=manifest)

    out = capsys.readouterr().out
    assert code == 0
    assert "declined" in out
