"""Unit tests for ``pyforge.marshal.seed.verbs.version`` (Story 11.6)."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.cli import seed as seed_cli
from pyforge.marshal.seed import fs
from pyforge.marshal.seed.model.manifest import AppliesTo, ArtifactClass, Manifest, ManifestEntry
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.state import SeedState, write_state
from pyforge.marshal.seed.verbs.version import render_version_text, run_version

_VERSION = ModelVersion.parse("1.0.0")
_NO_NEVER_WRITE = fs.NeverWrite(patterns=())


def _manifest() -> Manifest:
    return Manifest(
        model_version=_VERSION,
        never_write=(),
        entries=(
            ManifestEntry(
                id="whole",
                artifact_class=ArtifactClass.COPIED_MANAGED,
                path="WHOLE.md",
                applies_to=AppliesTo.BOTH,
                rationale="test",
            ),
        ),
    )


def _git(repo: Path, *args: str) -> None:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


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


def test_version_reports_cli_and_bundled_without_adopted_state(clean_repo):
    report = run_version(_manifest(), clean_repo)

    assert report.cli_version
    assert report.bundled_model_version == "1.0.0"
    assert report.adopted_model_version is None


def test_version_includes_adopted_model_version_when_state_present(clean_repo):
    write_state(
        SeedState(
            model_version=ModelVersion.parse("0.9.0"),
            seed_model_version="0.1.0",
            adopted_at="2026-08-14T09:15:00Z",
            last_update="2026-08-14T11:42:07Z",
            mode="adopt",
            agents=("claude-code",),
            managed=(),
            skips=(),
            legacy=(),
            migrations_applied=(),
            opted_out=(),
        ),
        repo_root=clean_repo,
        never_write=_NO_NEVER_WRITE,
    )

    report = run_version(_manifest(), clean_repo)

    assert report.adopted_model_version == "0.9.0"


def test_version_text_and_json_agree(clean_repo):
    report = run_version(_manifest(), clean_repo)

    text = render_version_text(report)
    payload = report.to_json_dict()

    assert "cli_version:" in text
    assert payload["cli_version"] == report.cli_version
    assert payload["bundled_model_version"] == report.bundled_model_version
    assert "adopted_model_version" not in payload


def test_version_cli_json_flag(clean_repo, capsys):
    args = argparse.Namespace(repo_root=str(clean_repo), json=True)

    code = seed_cli.run_version(args, manifest=_manifest())

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["verb"] == "version"
    assert payload["ok"] is True
    assert payload["result"]["bundled_model_version"] == "1.0.0"
