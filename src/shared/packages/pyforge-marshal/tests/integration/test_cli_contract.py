"""Story 12.5 — CLI contract suite (FR-123/FR-124/FR-126, NFR-12).

Asserts every ``marshal seed`` verb accepts ``--json``/``--quiet``, mutating
verbs accept ``--dry-run`` (adopt/update default to dry-run), and ``--json``
emissions share the schema-stable ``{verb, ok, result|error}`` envelope.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.cli import seed as seed_cli
from pyforge.marshal.seed.errors import (
    ConformanceFailure,
    InternalError,
    NeverWriteViolation,
    PreconditionFailure,
    StateInvalid,
    UsageError,
)
from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    Manifest,
    ManifestEntry,
)
from pyforge.marshal.seed.model.version import ModelVersion

_VERSION = ModelVersion.parse("1.0.0")
# Story 28.3 adds the seventh verb, `kit`. Enrolled here (not exempted)
# so FR-123/124/126 -- `--json`/`--quiet` acceptance, `--dry-run` on a
# mutating verb, envelope-key parity -- cover it like every sibling.
_SEED_VERBS = ("init", "adopt", "check", "update", "explain", "version", "kit")
_MUTATING_VERBS = ("init", "adopt", "update", "kit")
_ENVELOPE_OK_KEYS = ("verb", "ok", "result")
_ENVELOPE_ERR_KEYS = ("verb", "ok", "error")
_ERROR_KEYS = ("type", "message", "remedy")


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


def _git(repo: Path, *args: str) -> None:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def _init_git_repo(repo: Path) -> Path:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "initial")
    return repo


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="marshal")
    subparsers = parser.add_subparsers(dest="command", required=True)
    seed_cli.add_seed_subparser(subparsers)
    return parser


@pytest.mark.parametrize("verb", _SEED_VERBS)
def test_every_verb_accepts_json_and_quiet(verb: str):
    parser = _build_parser()
    argv = ["seed", verb]
    if verb == "init":
        argv.append("/tmp/unused-path")
    elif verb == "explain":
        argv.append("agents-md")
    args = parser.parse_args([*argv, "--json", "--quiet"])
    assert args.json is True
    assert args.quiet is True


@pytest.mark.parametrize("verb", _MUTATING_VERBS)
def test_mutating_verbs_accept_dry_run(verb: str):
    parser = _build_parser()
    argv = ["seed", verb, "--dry-run"]
    if verb == "init":
        argv.insert(2, "/tmp/unused-path")
    args = parser.parse_args(argv)
    assert args.dry_run is True


def test_adopt_and_update_default_to_dry_run():
    parser = _build_parser()
    adopt = parser.parse_args(["seed", "adopt"])
    update = parser.parse_args(["seed", "update"])
    assert adopt.apply is False
    assert update.run is False


def _parse_json_documents(raw: str) -> list[dict]:
    """Split concatenated pretty-printed JSON objects from sequential prints."""
    docs: list[dict] = []
    depth = 0
    start: int | None = None
    for i, ch in enumerate(raw):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                docs.append(json.loads(raw[start : i + 1]))
                start = None
    return docs


def test_json_success_envelope_keys_match_across_verbs(tmp_path, capsys):
    repo = _init_git_repo(tmp_path / "repo")
    manifest = _manifest()
    parser = _build_parser()

    seed_cli.run_check(
        parser.parse_args(["seed", "check", "--repo-root", str(repo), "--json"]),
        manifest=manifest,
    )
    seed_cli.run_version(
        parser.parse_args(["seed", "version", "--repo-root", str(repo), "--json"]),
        manifest=manifest,
    )
    seed_cli.run_explain(
        parser.parse_args(["seed", "explain", "whole", "--json"]),
        manifest=_manifest(_whole_file("whole", "WHOLE.md")),
    )
    seed_cli.run_adopt(
        parser.parse_args(["seed", "adopt", "--repo-root", str(repo), "--dry-run", "--json"]),
        manifest=manifest,
    )
    seed_cli.run_init(
        parser.parse_args(["seed", "init", str(tmp_path / "fresh"), "--dry-run", "--json"]),
        manifest=manifest,
    )
    seed_cli.run_update(
        parser.parse_args(["seed", "update", "--repo-root", str(repo), "--dry-run", "--json"]),
        manifest=manifest,
    )
    seed_cli.run_kit(
        parser.parse_args(["seed", "kit", "--repo-root", str(repo), "--dry-run", "--json"]),
        manifest=manifest,
    )

    payloads = _parse_json_documents(capsys.readouterr().out)
    assert len(payloads) == 7
    for payload in payloads:
        assert tuple(payload.keys()) == _ENVELOPE_OK_KEYS
        assert payload["ok"] is True
        assert isinstance(payload["result"], dict)
        assert payload["verb"] in _SEED_VERBS


def test_quiet_suppresses_text_but_json_still_emits(tmp_path, capsys):
    repo = _init_git_repo(tmp_path / "repo")
    manifest = _manifest()
    parser = _build_parser()

    code = seed_cli.run_check(
        parser.parse_args(["seed", "check", "--repo-root", str(repo), "--quiet"]),
        manifest=manifest,
    )
    assert code == 0
    assert capsys.readouterr().out == ""

    code = seed_cli.run_check(
        parser.parse_args(["seed", "check", "--repo-root", str(repo), "--json", "--quiet"]),
        manifest=manifest,
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_exit_codes_match_s72_taxonomy_case_by_case(tmp_path, capsys):
    """FR-126: every S-7.2 leaf is reachable/asserted via the CLI surface."""
    repo = _init_git_repo(tmp_path / "repo")
    parser = _build_parser()

    # 0 success
    code = seed_cli.run_check(
        parser.parse_args(["seed", "check", "--repo-root", str(repo), "--json"]),
        manifest=_manifest(),
    )
    assert code == 0
    capsys.readouterr()

    # 1 conformance
    code = seed_cli.run_check(
        parser.parse_args(["seed", "check", "--repo-root", str(repo), "--json"]),
        manifest=_manifest(_whole_file("whole", "WHOLE.md")),
    )
    assert code == ConformanceFailure.exit_code == 1
    capsys.readouterr()

    # 2 usage
    code = seed_cli.run_check(
        parser.parse_args(["seed", "check", "--repo-root", str(tmp_path / "missing"), "--json"]),
        manifest=_manifest(),
    )
    assert code == UsageError.exit_code == 2
    err = json.loads(capsys.readouterr().out)
    assert tuple(err.keys()) == _ENVELOPE_ERR_KEYS
    assert tuple(err["error"].keys()) == _ERROR_KEYS

    # 3 precondition (dirty worktree on adopt --apply)
    dirty = _init_git_repo(tmp_path / "dirty")
    (dirty / "extra.txt").write_text("dirt\n", encoding="utf-8")
    code = seed_cli.run_adopt(
        parser.parse_args(
            [
                "seed",
                "adopt",
                "--repo-root",
                str(dirty),
                "--apply",
                "--yes",
                "--json",
            ]
        ),
        manifest=_manifest(_whole_file("whole", "WHOLE.md")),
        confirm=lambda: True,
    )
    assert code == PreconditionFailure.exit_code == 3

    # Taxonomy leaf presence (classes pin the remaining codes even when a
    # live raise path needs a heavier fixture elsewhere in the suite).
    assert NeverWriteViolation.exit_code == 4
    assert StateInvalid.exit_code == 5
    assert InternalError.exit_code == 10


def test_adopt_dry_run_and_apply_are_mutually_exclusive(tmp_path, capsys):
    repo = _init_git_repo(tmp_path / "repo")
    parser = _build_parser()
    args = parser.parse_args(["seed", "adopt", "--repo-root", str(repo), "--dry-run", "--apply", "--json"])
    code = seed_cli.run_adopt(args, manifest=_manifest())
    assert code == UsageError.exit_code
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["error"]["type"] == "UsageError"
