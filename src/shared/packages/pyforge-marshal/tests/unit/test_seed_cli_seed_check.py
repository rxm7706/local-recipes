"""Unit tests for ``pyforge.marshal.cli.seed.run_check`` (Story 10.5) -- the
thin CLI wiring over ``seed.verbs.check.run_check``: ``--repo-root``/
``--strict``/``--json`` argparse plumbing, and each of the three exit codes
this command can actually reach (0 clean, 1 ``ConformanceFailure``, 2
``UsageError`` on an unresolvable ``--repo-root``), plus the ``InternalError``
(10) path for a broken packaged-manifest install.

No ``test_seed_cli_seed.py`` file exists yet (every other verb in
``cli/seed.py`` is still Story 7.1's stub, untested) -- this is that file's
first real content, scoped to ``check`` only, per this story's own surface.

Exercises ``run_check`` through the SAME test-injection seam
``cli/adapters.py::run_adapters_sync(args, fs=..., harness=...)`` already
establishes for this package's CLI functions (``manifest=`` here) rather
than against the real 43-entry packaged manifest, so a scenario's shape is
legible from its own fixture instead of from ``templates/manifest.yaml``'s
current, independently-evolving content. A real-``argparse``-parsing test
(``test_check_parser_wires_the_expected_flags``) separately proves the
production dispatch path (``main.py`` -> ``add_seed_subparser`` ->
``run_check(args)``, no ``manifest=`` supplied) resolves the SAME
``args.repo_root``/``args.strict``/``args.json`` attributes this file's
direct-``Namespace`` tests construct by hand.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.cli import seed as seed_cli
from pyforge.marshal.seed.errors import ConformanceFailure, InternalError, UsageError
from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    Manifest,
    ManifestEntry,
    ManifestError,
)
from pyforge.marshal.seed.model.version import ModelVersion

_VERSION = ModelVersion.parse("1.0.0")


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


def _args(*, repo_root: str | None = None, strict: bool = False, json_flag: bool = False):
    return argparse.Namespace(repo_root=repo_root, strict=strict, json=json_flag)


# --- argparse wiring ---------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="marshal")
    subparsers = parser.add_subparsers(dest="command", required=True)
    seed_cli.add_seed_subparser(subparsers)
    return parser


def test_check_parser_defaults(tmp_path):
    parser = _build_parser()

    args = parser.parse_args(["seed", "check"])

    assert args.repo_root is None
    assert args.strict is False
    assert args.json is False
    assert args.quiet is False
    assert args.handler is seed_cli.run_check


def test_check_parser_wires_the_expected_flags(tmp_path):
    parser = _build_parser()

    args = parser.parse_args(["seed", "check", "--repo-root", str(tmp_path), "--strict", "--json", "--quiet"])

    assert args.repo_root == str(tmp_path)
    assert args.strict is True
    assert args.json is True
    assert args.quiet is True


# --- exit code 0 ------------------------------------------------------


def test_exit_code_0_on_a_conformant_repo(clean_repo, capsys):
    # A zero-entry manifest against a never-adopted repo is trivially
    # conformant with respect to exit code: its only finding is
    # ``model-behind`` (DRIFT, no recorded state version at all), which
    # does not fail without --strict.
    manifest = _manifest()

    code = seed_cli.run_check(_args(repo_root=str(clean_repo)), manifest=manifest)

    assert code == 0
    assert "OK" in capsys.readouterr().out


# --- exit code 1 -------------------------------------------------------


def test_exit_code_1_on_a_hard_finding(clean_repo, capsys):
    manifest = _manifest(_whole_file("whole", "WHOLE.md"))

    code = seed_cli.run_check(_args(repo_root=str(clean_repo)), manifest=manifest)

    out = capsys.readouterr().out
    assert code == ConformanceFailure.exit_code == 1
    assert "HARD (" in out
    assert "WHOLE.md" in out
    assert "FAIL" in out


def test_strict_turns_a_drift_only_run_from_0_to_1(clean_repo, capsys):
    """The end-to-end proof that ``--strict`` reaches the verb: a
    never-adopted repo checked against a zero-entry manifest produces
    exactly one finding -- ``model-behind`` (DRIFT, no recorded state
    version to compare) -- so the same invocation exits 0 without
    ``--strict`` and 1 with it."""
    manifest = _manifest()

    non_strict = seed_cli.run_check(_args(repo_root=str(clean_repo), strict=False), manifest=manifest)
    strict = seed_cli.run_check(_args(repo_root=str(clean_repo), strict=True), manifest=manifest)

    assert non_strict == 0
    assert strict == ConformanceFailure.exit_code == 1
    capsys.readouterr()


# --- exit code 2 --------------------------------------------------------


def test_exit_code_2_on_an_unresolvable_repo_root(tmp_path, capsys):
    missing = tmp_path / "does-not-exist"
    manifest = _manifest()

    code = seed_cli.run_check(_args(repo_root=str(missing)), manifest=manifest)

    out = capsys.readouterr().out
    assert code == UsageError.exit_code == 2
    assert str(missing) in out


# --- exit code 10 (InternalError, the broken-install path) -----------------


def test_a_broken_packaged_manifest_reports_internal_error(clean_repo, monkeypatch, capsys):
    def _broken() -> Manifest:
        raise ManifestError("manifest: simulated packaging failure")

    monkeypatch.setattr(seed_cli, "_load_packaged_manifest", _broken)

    code = seed_cli.run_check(_args(repo_root=str(clean_repo)))

    out = capsys.readouterr().out
    assert code == InternalError.exit_code == 10
    assert "reinstall pyforge-marshal" in out


# --- --json ----------------------------------------------------------------


def test_json_flag_emits_valid_json_to_stdout(clean_repo, capsys):
    manifest = _manifest(_whole_file("whole", "WHOLE.md"))

    seed_cli.run_check(_args(repo_root=str(clean_repo), json_flag=True), manifest=manifest)

    payload = json.loads(capsys.readouterr().out)
    assert list(payload.keys()) == ["verb", "ok", "result"]
    assert payload["verb"] == "check"
    assert payload["ok"] is True
    # Story 28.3 adds "kit" between "model_version" and "failing".
    assert list(payload["result"].keys()) == [
        "strict",
        "findings",
        "model_version",
        "kit",
        "failing",
    ]
    assert payload["result"]["failing"] is True


def test_json_flag_is_honored_on_the_usage_error_path(tmp_path, capsys):
    """Review finding: ``--json`` was previously ignored on the
    ``UsageError``/``InternalError`` error paths -- a plain ``print(str(...))``
    ran regardless of ``args.json``, so a CI harness that unconditionally
    parses stdout as JSON whenever ``--json`` was passed broke on this exit
    code. Now every exit code honors ``--json``."""
    missing = tmp_path / "does-not-exist"
    manifest = _manifest()

    code = seed_cli.run_check(_args(repo_root=str(missing), json_flag=True), manifest=manifest)

    payload = json.loads(capsys.readouterr().out)
    assert code == UsageError.exit_code == 2
    assert payload["error"]["type"] == "UsageError"
    assert str(missing) in payload["error"]["message"]


def test_json_flag_is_honored_on_the_internal_error_path(clean_repo, monkeypatch, capsys):
    def _broken() -> Manifest:
        raise ManifestError("manifest: simulated packaging failure")

    monkeypatch.setattr(seed_cli, "_load_packaged_manifest", _broken)

    code = seed_cli.run_check(_args(repo_root=str(clean_repo), json_flag=True))

    payload = json.loads(capsys.readouterr().out)
    assert code == InternalError.exit_code == 10
    assert payload["error"]["type"] == "InternalError"
    assert "reinstall pyforge-marshal" in payload["error"]["remedy"]


# --- the verb call is inside the try/except (review finding) ---------------


def test_an_unanticipated_failure_from_the_verb_is_never_a_traceback(clean_repo, monkeypatch, capsys):
    """Review finding: ``_run_check_verb(...)`` was previously called OUTSIDE
    the ``try``/``except`` block, so any exception raised deep in the call
    chain (a ``SeedError``, or an unguarded OS-level failure such as a
    missing ``git`` executable) escaped ``main.py``'s dispatcher uncaught --
    it only catches ``SystemExit``/``KeyboardInterrupt``. Simulates the
    unanticipated-failure case directly (a bare exception with no
    ``SeedError`` ancestry) and confirms it is caught and reported as
    ``InternalError`` (10), never re-raised."""

    def _boom(repo_root, manifest, *, strict, context_layers=None):
        raise RuntimeError("simulated unanticipated failure deep in the verb")

    monkeypatch.setattr(seed_cli, "_run_check_verb", _boom)
    manifest = _manifest()

    code = seed_cli.run_check(_args(repo_root=str(clean_repo)), manifest=manifest)

    out = capsys.readouterr().out
    assert code == InternalError.exit_code == 10
    assert "simulated unanticipated failure" in out
