"""Unit tests for ``pyforge.marshal.cli.seed.run_init`` (Story 10.7) -- the
thin CLI wiring over ``seed.verbs.init.run_init``: ``<path>``/``--slug``/
``--agents``/``--force`` argparse plumbing, and each of the exit codes this
command can actually reach (0 for a successful init -- the ONLY success
outcome, unlike ``adopt``'s three, since ``init`` never dry-runs and never
declines; 2 ``UsageError`` for FR-78's own refusal and for an unresolvable
target; 10 ``InternalError`` for a broken packaged-manifest install and for
an unanticipated failure deep in the verb).

Exercises ``run_init`` through the SAME ``manifest=`` test-injection seam
``run_check``/``run_adopt`` already establish, rather than against the real
43-entry packaged manifest -- mirrors ``test_seed_cli_seed_adopt.py``'s own
identical convention and its own real-``argparse``-parsing test
(``test_init_parser_wires_the_expected_flags``), which separately proves the
production dispatch path (``main.py`` -> ``add_seed_subparser`` ->
``run_init(args)``, no ``manifest=`` supplied) resolves the SAME attributes
this file's direct-``Namespace`` tests construct by hand."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.cli import seed as seed_cli
from pyforge.marshal.seed.errors import InternalError, UsageError
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


def _copied_managed(entry_id: str, path: str, *, applies_to: AppliesTo = AppliesTo.BOTH) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.COPIED_MANAGED,
        path=path,
        applies_to=applies_to,
        rationale="test",
    )


def _hybrid(entry_id: str, path: str, region_name: str) -> ManifestEntry:
    """A hybrid entry whose ``region_name`` matches one of the six REAL
    packaged ``seed/templates/files/*.j2`` fragments -- mirrors ``test_seed_
    cli_seed_adopt.py``'s own identical helper and its own docstring's
    rationale: these tests exercise the CLI's REAL, non-injected default
    commit path, and only a hybrid region's body is read directly off the
    packaged template without depending on any whole-file content (which the
    packaged template tree does not yet ship)."""
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


def _args(
    *,
    path: str,
    slug: str | None = None,
    agents: str | None = None,
    force: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(path=path, slug=slug, agents=agents, force=force)


# --- argparse wiring ---------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="marshal")
    subparsers = parser.add_subparsers(dest="command", required=True)
    seed_cli.add_seed_subparser(subparsers)
    return parser


def test_init_parser_defaults(tmp_path):
    parser = _build_parser()

    args = parser.parse_args(["seed", "init", str(tmp_path)])

    assert args.path == str(tmp_path)
    assert args.slug is None
    assert args.agents is None
    assert args.force is False
    assert args.dry_run is False
    assert args.json is False
    assert args.quiet is False
    assert args.handler is seed_cli.run_init


def test_init_parser_wires_the_expected_flags(tmp_path):
    parser = _build_parser()

    args = parser.parse_args(
        [
            "seed",
            "init",
            str(tmp_path),
            "--slug",
            "pyforge-scribe",
            "--agents",
            "claude,cursor",
            "--force",
            "--dry-run",
            "--json",
            "--quiet",
        ]
    )

    assert args.path == str(tmp_path)
    assert args.slug == "pyforge-scribe"
    assert args.agents == "claude,cursor"
    assert args.force is True
    assert args.dry_run is True
    assert args.json is True
    assert args.quiet is True


def test_init_parser_requires_a_path_positional():
    parser = _build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["seed", "init"])


# --- exit code 0: the one success outcome -----------------------------------


def test_exit_code_0_on_a_successful_init(tmp_path, capsys):
    target = tmp_path / "newproj"
    manifest = _manifest(_hybrid("hybrid", "WHOLE.md", "tiers"))

    code = seed_cli.run_init(_args(path=str(target)), manifest=manifest)

    out = capsys.readouterr().out
    assert code == 0
    assert "applied 1 artifact" in out
    assert "hybrid" in out
    assert "marshal-seed:begin region=tiers" in (target / "WHOLE.md").read_text(encoding="utf-8")
    assert (target / ".git").is_dir()


def test_exit_code_0_on_an_empty_plan_init(tmp_path, capsys):
    target = tmp_path / "newproj"
    manifest = _manifest()

    code = seed_cli.run_init(_args(path=str(target)), manifest=manifest)

    out = capsys.readouterr().out
    assert code == 0
    assert "nothing to do" in out


def test_default_slug_is_the_target_directory_name(tmp_path, capsys):
    target = tmp_path / "pyforge-scribe"
    manifest = _manifest(_hybrid("hybrid", "WHOLE.md", "tiers"))

    code = seed_cli.run_init(_args(path=str(target)), manifest=manifest)

    out = capsys.readouterr().out
    assert code == 0
    assert "'pyforge-scribe'" in out
    state = read_state(target)
    assert state.mode == "init"


# --- --agents/--slug flags reach the verb ------------------------------


def test_agents_and_slug_flags_reach_the_verb(tmp_path, capsys):
    target = tmp_path / "newproj"
    manifest = _manifest(_hybrid("hybrid", "WHOLE.md", "tiers"))

    code = seed_cli.run_init(_args(path=str(target), slug="my-slug", agents="claude,cursor"), manifest=manifest)

    assert code == 0
    state = read_state(target)
    assert state.agents == ("claude", "cursor")


# --- exit code 2: UsageError ------------------------------------------------


def test_exit_code_2_on_a_non_empty_target_without_force(tmp_path, capsys):
    target = tmp_path / "existing"
    target.mkdir()
    (target / "something.txt").write_text("x\n", encoding="utf-8")
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    code = seed_cli.run_init(_args(path=str(target)), manifest=manifest)

    out = capsys.readouterr().out
    assert code == UsageError.exit_code == 2
    assert "adopt" in out
    assert not (target / ".git").exists()


def test_exit_code_2_on_a_target_that_is_a_plain_file(tmp_path, capsys):
    target_file = tmp_path / "not-a-directory"
    target_file.write_text("i am a file\n", encoding="utf-8")
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    code = seed_cli.run_init(_args(path=str(target_file)), manifest=manifest)

    out = capsys.readouterr().out
    assert code == UsageError.exit_code == 2
    assert "not a directory" in out
    assert target_file.read_text() == "i am a file\n"


def test_force_proceeds_onto_an_already_committed_non_empty_target(tmp_path, capsys):
    target = tmp_path / "existing"
    target.mkdir()
    _init_git_repo(target)
    (target / "PREEXISTING.md").write_text("unrelated\n", encoding="utf-8")
    _git(target, "add", "-A")
    _git(target, "commit", "-m", "fixture")
    manifest = _manifest(_copied_managed("gen", "PREEXISTING.md"))

    code = seed_cli.run_init(_args(path=str(target), force=True), manifest=manifest)

    out = capsys.readouterr().out
    assert code == 0
    assert "nothing to do" in out
    assert (target / "PREEXISTING.md").read_text() == "unrelated\n"


# --- exit code 10 (InternalError, the broken-install path) -----------------


def test_a_broken_packaged_manifest_reports_internal_error(tmp_path, monkeypatch, capsys):
    def _broken() -> Manifest:
        raise ManifestError("manifest: simulated packaging failure")

    monkeypatch.setattr(seed_cli, "_load_packaged_manifest", _broken)

    code = seed_cli.run_init(_args(path=str(tmp_path / "newproj")))

    out = capsys.readouterr().out
    assert code == InternalError.exit_code == 10
    assert "reinstall pyforge-marshal" in out


def test_an_unanticipated_failure_from_the_verb_is_never_a_traceback(tmp_path, monkeypatch, capsys):
    """Mirrors ``test_seed_cli_seed_adopt.py``'s identical review-finding
    regression test: the verb call must be INSIDE the ``try``, so a bare
    exception raised deep in the call chain is caught and reported as
    ``InternalError`` (10), never re-raised as a raw traceback."""

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated unanticipated failure deep in the verb")

    monkeypatch.setattr(seed_cli, "_run_init_verb", _boom)
    manifest = _manifest()

    code = seed_cli.run_init(_args(path=str(tmp_path / "newproj")), manifest=manifest)

    out = capsys.readouterr().out
    assert code == InternalError.exit_code == 10
    assert "simulated unanticipated failure" in out
