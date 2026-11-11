"""Story 115.4 (CAP-208): marshal's forge repository is the root of record's.

``adapters/forge_root.py::forge_repo`` is marshal's one consumer of core's seam
(``pyforge.core.cutover_root.root_of_record``). These tests write their own flag tree under
``tmp_path`` and point ``PYFORGE_FLAGS_PATH`` at it, or run in a temp directory with no tree in
reach, so they read nothing of the repository's own tree. Each forge site is driven with the fakes
its own suite already uses (``test_dispatch_landing.py``, ``test_land.py``, ``test_deploy.py``);
a malformed tree must surface through the code that site already uses for a forge it cannot reach.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest
from pyforge.core.cutover_root import (
    CUTOVER_FLAG,
    DEFAULT_CUTOVER_ROOT,
    ENV_FLAGS_PATH,
    FORGE_SLUGS,
    forge_slug_for,
)
from pyforge.core.process import ProcessResult
from test_deploy import _BMADLOOP_WAVE_SUBJECT as _DEPLOY_WAVE_SUBJECT
from test_deploy import _batch_pr_args
from test_deploy import _FakeForge as _DeployForge
from test_deploy import _FakeVcs as _DeployVcs
from test_dispatch_landing import FakeVcs as _DispatchVcs
from test_dispatch_landing import _CreatePrSpyForge, _land_example
from test_land import _BMADLOOP_WAVE_SUBJECT as _LAND_WAVE_SUBJECT
from test_land import _args as _land_args
from test_land import _FakeForge as _LandForge
from test_land import _FakeVcs as _LandVcs
from test_land import _patch_repo as _patch_land_repo

from pyforge.marshal.adapters.forge_root import forge_repo
from pyforge.marshal.adapters.fs_local import LocalFs
from pyforge.marshal.cli import deploy as deploy_module
from pyforge.marshal.cli import land as land_module
from pyforge.marshal.cli import watch as watch_mod
from pyforge.marshal.core.dispatch_landing import DispatchLandingVerdict
from pyforge.marshal.core.model import Finding, Severity
from pyforge.marshal.ports.forge import ForgeCommandError

_GH_PR_LIST_STDOUT = "[]"


def _tree(directory: Path, default_variant: str) -> Path:
    """A flagd tree holding only ``pyforge.cutover_root``, its default variant ``default_variant``."""
    path = directory / "flags.json"
    entry = {
        "state": "ENABLED",
        "variants": {"local-recipes": "local-recipes", "foundry": "foundry"},
        "defaultVariant": default_variant,
    }
    path.write_text(json.dumps({"flags": {CUTOVER_FLAG: entry}}), encoding="utf-8")
    return path


@pytest.fixture
def malformed_tree(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A tree whose ``pyforge.cutover_root`` names a root core does not know, in reach through the env."""
    path = _tree(tmp_path_factory.mktemp("malformed-flag-tree"), "elsewhere")
    monkeypatch.setenv(ENV_FLAGS_PATH, str(path))
    return path


def _no_tree_in_reach(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_FLAGS_PATH, raising=False)
    monkeypatch.chdir(tmp_path)


class _GhProcess:
    """A ``ProcessPort`` recording each argv; ``gh`` answers an empty PR list."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def run(self, argv, *, cwd=None, timeout_s=None, env=None, **_kwargs):
        self.calls.append(list(argv))
        return ProcessResult(returncode=0, stdout=_GH_PR_LIST_STDOUT, stderr="")


def _watch_repo_arg(tmp_path: Path) -> str:
    process = _GhProcess()
    assert watch_mod._default_ports(process, tmp_path).list_prs("pyforge-marshal") == []
    [argv] = process.calls
    return argv[argv.index("--repo") + 1]


# --- the seam consumer answers each tree ------------------------------------------------------------


def test_the_local_recipes_tree_gives_the_local_recipes_repository(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_FLAGS_PATH, str(_tree(tmp_path, "local-recipes")))
    assert forge_repo() == "rxm7706/local-recipes"
    assert _watch_repo_arg(tmp_path) == "rxm7706/local-recipes"


def test_the_foundry_tree_gives_the_seams_foundry_slug(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_FLAGS_PATH, str(_tree(tmp_path, "foundry")))
    assert forge_repo() == forge_slug_for("foundry") == FORGE_SLUGS["foundry"]
    assert _watch_repo_arg(tmp_path) == FORGE_SLUGS["foundry"]


def test_no_tree_in_reach_gives_the_default_root(tmp_path: Path, monkeypatch) -> None:
    _no_tree_in_reach(tmp_path, monkeypatch)
    assert forge_repo() == forge_slug_for(DEFAULT_CUTOVER_ROOT) == "rxm7706/local-recipes"
    assert _watch_repo_arg(tmp_path) == "rxm7706/local-recipes"


def test_an_explicit_path_is_read_as_given(tmp_path: Path, monkeypatch) -> None:
    _no_tree_in_reach(tmp_path, monkeypatch)
    assert forge_repo(_tree(tmp_path, "foundry")) == FORGE_SLUGS["foundry"]


def test_the_slug_is_read_at_each_use_never_cached(tmp_path: Path, monkeypatch) -> None:
    path = _tree(tmp_path, "local-recipes")
    monkeypatch.setenv(ENV_FLAGS_PATH, str(path))
    assert forge_repo() == FORGE_SLUGS["local-recipes"]
    _tree(tmp_path, "foundry")
    assert forge_repo() == FORGE_SLUGS["foundry"]


def test_a_bad_tree_is_the_forge_ports_own_error(tmp_path: Path, monkeypatch) -> None:
    unreadable = tmp_path / "flags.json"
    unreadable.write_text("{not json", encoding="utf-8")
    monkeypatch.setenv(ENV_FLAGS_PATH, str(unreadable))
    with pytest.raises(ForgeCommandError, match="root of record"):
        forge_repo()
    with pytest.raises(ForgeCommandError, match="unknown cutover_root variant"):
        forge_repo(_tree(tmp_path, "elsewhere"))


# --- a malformed tree surfaces through each site's existing forge-failure code ----------------------


def test_dispatch_land_refuses_a_malformed_tree_as_mrs_disp_018(tmp_path: Path, malformed_tree: Path) -> None:
    forge = _CreatePrSpyForge()

    result, envelope = _land_example(tmp_path, _DispatchVcs(), forge)

    assert result.verdict == DispatchLandingVerdict.REFUSED
    [refusal] = [finding for finding in envelope.findings if finding.code == "MRS-DISP-018"]
    assert refusal.severity == Severity.ERROR
    assert "unknown cutover_root variant 'elsewhere'" in refusal.message
    assert forge.created == []


def test_land_reports_a_malformed_tree_as_mrs_deploy_014_at_both_sites(
    tmp_path: Path, capsys, monkeypatch, malformed_tree: Path
) -> None:
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _patch_land_repo(monkeypatch, tmp_path)

    # The already-landed shortcut: the PR look-up's own MRS-DEPLOY-014.
    landed_vcs = _LandVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_LAND_WAVE_SUBJECT,),
        base_subjects=(_LAND_WAVE_SUBJECT,),
    )
    landed_forge = _LandForge(existing=None)
    landed_exit = land_module.run_land(_land_args(), vcs=landed_vcs, fs=LocalFs(), forge=landed_forge)
    landed = json.loads(capsys.readouterr().out)
    assert landed["data"]["already_landed"] is True
    assert landed["data"]["branch_retired"] is None
    assert [f["code"] for f in landed["findings"] if f["severity"] == "error"] == ["MRS-DEPLOY-014"]
    assert landed_exit != 0
    assert landed_forge.find_calls == []

    # The full path: the read ahead of the hygiene preflight, then an early emit.
    full_vcs = _LandVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_LAND_WAVE_SUBJECT,),
        changed_paths=("pixi.toml",),
    )
    full_forge = _LandForge(existing=None)
    full_exit = land_module.run_land(_land_args(), vcs=full_vcs, fs=LocalFs(), forge=full_forge)
    full = json.loads(capsys.readouterr().out)
    [finding] = full["findings"]
    assert finding["code"] == "MRS-DEPLOY-014"
    assert finding["severity"] == "error"
    assert "unknown cutover_root variant 'elsewhere'" in finding["message"]
    assert full_exit != 0
    assert full_forge.find_calls == [] and full_forge.check_calls == []
    assert full_forge.create_calls == [] and full_forge.merge_calls == []


def test_deploy_batch_pr_reports_a_malformed_tree_as_mrs_deploy_014(
    tmp_path: Path, capsys, monkeypatch, malformed_tree: Path
) -> None:
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    vcs = _DeployVcs(
        existing_branches=frozenset({"loop/acme"}),
        merge_base_sha="base-sha",
        window_subjects=(_DEPLOY_WAVE_SUBJECT,),
        resolve_ref_sha="head-sha-abc",
        changed_paths=("docs/notes.md",),
    )
    forge = _DeployForge(existing=None)

    exit_code = deploy_module.run_batch_pr(_batch_pr_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = json.loads(capsys.readouterr().out)
    [finding] = payload["findings"]
    assert finding["code"] == "MRS-DEPLOY-014"
    assert finding["severity"] == "error"
    assert "unknown cutover_root variant 'elsewhere'" in finding["message"]
    assert payload["data"]["opened"] is False
    assert payload["data"]["updated"] is False
    assert exit_code != 0
    assert forge.find_calls == [] and forge.check_calls == [] and forge.create_calls == []


def test_watch_reports_a_malformed_tree_as_mrs_watch_004_warn(tmp_path: Path, malformed_tree: Path) -> None:
    process = _GhProcess()
    ports = dataclasses.replace(watch_mod._default_ports(process, tmp_path), loop_sha=lambda _slug: None)
    findings: list[Finding] = []

    sha, prs = watch_mod._probe_sha_prs(ports, "pyforge-marshal", findings)

    assert (sha, prs) == (None, [])
    [finding] = findings
    assert finding.code == "MRS-WATCH-004"
    assert finding.severity == Severity.WARN
    assert finding.message.startswith("gh pr list failed -- ")
    assert "unknown cutover_root variant 'elsewhere'" in finding.message
    assert process.calls == []
