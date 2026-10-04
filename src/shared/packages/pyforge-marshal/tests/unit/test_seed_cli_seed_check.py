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

from pyforge.marshal.adapters.vcs_git import GitVcs, VcsCommandError
from pyforge.marshal.cli import seed as seed_cli
from pyforge.marshal.ports.vcs import WorktreeEntry
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


def _args(*, repo_root: str | None = None, strict: bool = False, json_flag: bool = False, project: str | None = None):
    return argparse.Namespace(repo_root=repo_root, strict=strict, json=json_flag, project=project)


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


def test_json_kit_entries_carry_the_fields_steward_reads(clean_repo, capsys):
    """Producer pin for a cross-station reader. ``steward session check`` (CAP-5) reads
    ``result.kit`` from this envelope and each entry's ``item``/``layer``/``status``;
    it read a top-level ``kit`` until steward Story 79.1 because nothing here named the
    shape it depends on. Change this shape together with steward's
    ``session.py::_seed_check_kit``."""
    manifest = _manifest(_whole_file("whole", "WHOLE.md"))

    seed_cli.run_check(_args(repo_root=str(clean_repo), json_flag=True), manifest=manifest)

    kit = json.loads(capsys.readouterr().out)["result"]["kit"]
    assert [(entry["item"], entry["layer"]) for entry in kit] == [
        ("caveman-skill", "output"),
        ("ccr-store", "wire"),
        ("codegraph-index", "structure-graph"),
    ]
    assert all(isinstance(entry["status"], str) and entry["status"] for entry in kit)


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

    def _boom(repo_root, manifest, *, strict, context_layers=None, slug=None, in_loop_home=None):
        raise RuntimeError("simulated unanticipated failure deep in the verb")

    monkeypatch.setattr(seed_cli, "_run_check_verb", _boom)
    manifest = _manifest()

    code = seed_cli.run_check(_args(repo_root=str(clean_repo)), manifest=manifest)

    out = capsys.readouterr().out
    assert code == InternalError.exit_code == 10
    assert "simulated unanticipated failure" in out


# --- Story 70.1: the project slug and the loop-home scope -------------------

_TEMPLATED_RENDERED_FOR_DEMO = (
    "docs/dreams/demo.md",
    "_bmad-output/projects/demo/.bmad-config.toml",
    "_bmad-output/projects/demo/planning-artifacts/specs/README.md",
    "presentations/demo/",
    "_bmad-output/projects/demo/",
)
_TEMPLATED_IDS = ("starter-dream", "project-config", "specs-readme", "deck-scaffolding", "project-subtree")


def _lay_out_demo_project(repo: Path, *, without: str | None = None) -> None:
    for rendered in _TEMPLATED_RENDERED_FOR_DEMO:
        if rendered == without:
            continue
        target = repo / rendered
        if rendered.endswith("/"):
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"{rendered}\n", encoding="utf-8")


@pytest.fixture
def demo_repo(clean_repo: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repository on `main` carrying every rendered path of the five
    templated entries for the slug `demo`, with no `.bmad-loop/policy.toml`
    -- and no `BMAD_ACTIVE_PROJECT` leaking in from the shell running the
    suite."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _lay_out_demo_project(clean_repo)
    return clean_repo


def _check_json(repo: Path, capsys: pytest.CaptureFixture[str], **kwargs) -> tuple[int, dict]:
    """`marshal seed check --json` against the REAL packaged manifest."""
    code = seed_cli.run_check(_args(repo_root=str(repo), json_flag=True, **kwargs))
    return code, json.loads(capsys.readouterr().out)["result"]


def _findings_at(result: dict, path: str) -> list[dict]:
    return [finding for finding in result["findings"] if finding["path"] == path]


def test_project_judges_the_five_templated_entries_at_their_rendered_paths(demo_repo, capsys):
    """AC: `marshal seed check --project demo --json` on a repository carrying
    the five rendered paths -- no finding's path contains `{{`, and none of
    the five templated entries is `artifact-missing`."""
    _code, result = _check_json(demo_repo, capsys, project="demo")

    assert not [finding["path"] for finding in result["findings"] if "{{" in finding["path"]]
    for rendered in _TEMPLATED_RENDERED_FOR_DEMO:
        assert not [f for f in _findings_at(result, rendered) if f["type"] == "artifact-missing"], rendered
    assert not [finding for finding in result["findings"] if finding["type"] == "slug-unresolved"]


def test_project_reports_an_absent_rendered_path_hard_missing(clean_repo, monkeypatch, capsys):
    """AC: the same fixture without `docs/dreams/demo.md` -- a HARD
    `artifact-missing` names the rendered path and `failing` is true."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _lay_out_demo_project(clean_repo, without="docs/dreams/demo.md")

    code, result = _check_json(clean_repo, capsys, project="demo")

    assert [(f["severity"], f["type"]) for f in _findings_at(result, "docs/dreams/demo.md")] == [
        ("HARD", "artifact-missing")
    ]
    assert result["failing"] is True
    assert code == ConformanceFailure.exit_code


def test_no_project_env_or_marker_reports_five_slug_unresolved_info_findings(demo_repo, capsys):
    """AC: no `--project`, no `BMAD_ACTIVE_PROJECT`, no marker -- the five
    templated entries yield five INFO `slug-unresolved` findings naming
    `--project`, and nothing is classified at a literal placeholder path."""
    _code, result = _check_json(demo_repo, capsys)

    unresolved = [finding for finding in result["findings"] if finding["type"] == "slug-unresolved"]
    assert len(unresolved) == 5
    assert {finding["severity"] for finding in unresolved} == {"INFO"}
    assert all("--project" in finding["remedy"] for finding in unresolved)
    assert {path for path in (f["path"] for f in unresolved)} == {
        rendered.replace("demo", "{{ slug }}") for rendered in _TEMPLATED_RENDERED_FOR_DEMO
    }
    for entry_id in _TEMPLATED_IDS:
        assert [f for f in unresolved if repr(entry_id) in f["message"]], entry_id
    assert not [f for f in result["findings"] if "{{" in f["path"] and f["type"] != "slug-unresolved"]


def test_slug_unresolved_findings_never_turn_a_passing_check_red(demo_repo, capsys):
    """AC: `failing` is unaffected by the INFO findings -- a manifest of only
    templated entries, checked with no slug, exits 0."""
    manifest = _manifest(
        *(
            ManifestEntry(
                id=entry_id,
                artifact_class=ArtifactClass.COPIED_SEEDED,
                path=f"templated/{{{{ slug }}}}/{entry_id}.md",
                applies_to=AppliesTo.BOTH,
                rationale="test",
            )
            for entry_id in _TEMPLATED_IDS
        )
    )

    code = seed_cli.run_check(_args(repo_root=str(demo_repo), json_flag=True), manifest=manifest)

    result = json.loads(capsys.readouterr().out)["result"]
    assert [finding["type"] for finding in result["findings"]].count("slug-unresolved") == 5
    assert result["failing"] is False
    assert code == 0


@pytest.mark.parametrize("source", ["env", "marker"])
def test_the_env_or_the_marker_supplies_the_slug_without_project(demo_repo, monkeypatch, capsys, source):
    """AC: `BMAD_ACTIVE_PROJECT=demo`, or the target's marker reading `demo`,
    judges the entries at the `demo` paths with no `--project`."""
    if source == "env":
        monkeypatch.setenv("BMAD_ACTIVE_PROJECT", "demo")
    else:
        marker = demo_repo / "_bmad" / "custom" / ".active-project"
        marker.parent.mkdir(parents=True)
        marker.write_text("demo\n", encoding="utf-8")
    (demo_repo / "docs" / "dreams" / "demo.md").unlink()

    _code, result = _check_json(demo_repo, capsys)

    assert not [finding for finding in result["findings"] if finding["type"] == "slug-unresolved"]
    assert [f["type"] for f in _findings_at(result, "docs/dreams/demo.md")] == ["artifact-missing"]
    for rendered in _TEMPLATED_RENDERED_FOR_DEMO[1:]:
        assert not [f for f in _findings_at(result, rendered) if f["type"] == "artifact-missing"], rendered


def test_a_project_that_renders_a_refused_path_is_a_usage_error_naming_the_slug(demo_repo, capsys):
    """A slug is the operator's input: one that renders a path the manifest
    refuses exits 2 as a `UsageError` naming it -- never the broken-install
    `InternalError` (10) a packaged manifest that fails to load is."""
    code = seed_cli.run_check(_args(repo_root=str(demo_repo), json_flag=True, project="../escape"))

    payload = json.loads(capsys.readouterr().out)
    assert code == UsageError.exit_code == 2
    assert payload["error"]["type"] == "UsageError"
    assert "'../escape'" in payload["error"]["message"]
    assert "--project" in payload["error"]["remedy"]


def test_a_project_that_renders_two_owners_of_one_path_is_a_usage_error(demo_repo, capsys):
    """Story 86.1's note, at the CLI: the one-owner rule judges the rendered
    manifest, and a collision the slug causes is the operator's to fix."""
    manifest = _manifest(
        _whole_file("literal-doc", "docs/demo.md"),
        ManifestEntry(
            id="templated-doc",
            artifact_class=ArtifactClass.COPIED_SEEDED,
            path="docs/{{ slug }}.md",
            applies_to=AppliesTo.BOTH,
            rationale="test",
        ),
    )

    code = seed_cli.run_check(_args(repo_root=str(demo_repo), project="demo"), manifest=manifest)

    out = capsys.readouterr().out
    assert code == UsageError.exit_code == 2
    assert "project slug 'demo'" in out
    assert "templated-doc: path 'docs/demo.md' is also declared by 'literal-doc'" in out


def test_off_a_loop_home_no_finding_names_the_loop_policy(demo_repo, capsys):
    """AC (amended 2026-09-28): a repository without `.bmad-loop/policy.toml`
    checked out on `main` -- no finding names it. Removing the scope gate from
    `run_check` reports it missing here (mutation)."""
    assert GitVcs().list_worktrees(demo_repo)[0].branch == "main"

    _code, result = _check_json(demo_repo, capsys, project="demo")

    assert _findings_at(result, ".bmad-loop/policy.toml") == []


def test_in_a_loop_home_the_absent_loop_policy_is_hard_missing(demo_repo, capsys):
    """AC: the same fixture checked out on `loop/demo` -- a loop home -- owes
    the file: HARD `artifact-missing`, `failing` true."""
    _git(demo_repo, "checkout", "-q", "-b", "loop/demo")

    code, result = _check_json(demo_repo, capsys, project="demo")

    assert [(f["severity"], f["type"]) for f in _findings_at(result, ".bmad-loop/policy.toml")] == [
        ("HARD", "artifact-missing")
    ]
    assert result["failing"] is True
    assert code == ConformanceFailure.exit_code


class _FailingVcs:
    def list_worktrees(self, repo_root: Path) -> tuple[WorktreeEntry, ...]:
        raise VcsCommandError("simulated: git worktree list failed")


def test_an_unreadable_branch_still_owes_the_loop_policy(demo_repo, capsys):
    """AC: the worktree listing fails (`in_loop_home` is `None`) -- the absent
    `.bmad-loop/policy.toml` is HARD `artifact-missing`, as before the scope."""
    code = seed_cli.run_check(_args(repo_root=str(demo_repo), json_flag=True, project="demo"), vcs=_FailingVcs())

    result = json.loads(capsys.readouterr().out)["result"]
    assert [(f["severity"], f["type"]) for f in _findings_at(result, ".bmad-loop/policy.toml")] == [
        ("HARD", "artifact-missing")
    ]
    assert code == ConformanceFailure.exit_code


# --- `_target_in_loop_home`: the branch the target is checked out on --------


def test_target_in_loop_home_reads_the_target_worktrees_own_branch(clean_repo, tmp_path_factory):
    """A linked worktree on `loop/<slug>` is a loop home; the primary on
    `main` beside it is not -- each judged by its OWN listing entry."""
    home = tmp_path_factory.mktemp("homes") / "demo"
    _git(clean_repo, "worktree", "add", "-q", "-b", "loop/demo", str(home))
    vcs = GitVcs()

    assert seed_cli._target_in_loop_home(home, vcs) is True
    assert seed_cli._target_in_loop_home(clean_repo, vcs) is False


def test_target_in_loop_home_is_unknown_when_the_branch_cannot_be_read(clean_repo, tmp_path):
    """`None`, never `False`: a non-repository, a subdirectory no listing
    entry names, a detached HEAD, and a failing listing all leave the answer
    unread -- so the scope never passes on them."""
    vcs = GitVcs()
    not_a_repo = tmp_path.parent / f"{tmp_path.name}-plain"
    not_a_repo.mkdir()
    (clean_repo / "sub").mkdir()

    assert seed_cli._target_in_loop_home(not_a_repo, vcs) is None
    assert seed_cli._target_in_loop_home(clean_repo / "sub", vcs) is None
    assert seed_cli._target_in_loop_home(clean_repo, _FailingVcs()) is None
    _git(clean_repo, "checkout", "-q", "--detach")
    assert seed_cli._target_in_loop_home(clean_repo, vcs) is None
