"""Story 14.3 — draft estate PRs, allowlist skip, and flag on/off forge shapes."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from pyforge.core import flags as core_flags
from pyforge.core.flags import read_boolean
from pyforge.warden.actuator import (
    FIX_DRAFT_PR_ESTATE_FLAG,
    GitHubForgeClient,
    RemediationProposal,
    run_actuator,
)
from pyforge.warden.manifest_fixup import ManifestFileChange, ManifestFixPlan
from pyforge.warden.models import Finding, Severity, SeverityTier


@pytest.fixture(autouse=True)
def _production_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "production")


def _write_pixi_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pixi.toml").write_text(
        '[project]\nname = "demo"\n\n[pypi-dependencies]\nleftpad = ">=1.2"\n',
        encoding="utf-8",
    )
    (root / "pixi.lock").write_text("lock-version = 1\n", encoding="utf-8")


def _vuln() -> Finding:
    return Finding(
        id="vuln:GHSA-estate:leftpad@1.2.0",
        axis="vulnerability",
        message="leftpad: GHSA-estate",
        subject="leftpad",
        severity=Severity(tier=SeverityTier.HIGH, raw=None),
    )


def _bool_flag_entry(default: str) -> dict[str, object]:
    return {
        "state": "ENABLED",
        "variants": {"on": True, "off": False},
        "defaultVariant": "off",
        "metadata": {
            "owner": "warden",
            "story": "14-3-the-actuator-opens-the-fix-as-a-draft-pr-on-an-estate-repo",
            "created": "2026-09-28",
            "on_everywhere": "",
            "cleanup_by": "",
        },
    }


def _flag_tree(tmp_path: Path, *, draft_on: bool) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    tree = {
        "flags": {
            FIX_DRAFT_PR_ESTATE_FLAG: _bool_flag_entry("on" if draft_on else "off"),
        }
    }
    path = tmp_path / "flags.json"
    path.write_text(json.dumps(tree), encoding="utf-8")
    variant = "on" if draft_on else "off"
    overlays = {
        "dev": {FIX_DRAFT_PR_ESTATE_FLAG: variant},
        "staging": {FIX_DRAFT_PR_ESTATE_FLAG: variant},
        "production": {FIX_DRAFT_PR_ESTATE_FLAG: "off"},
    }
    (tmp_path / core_flags.OVERLAYS_FILE_NAME).write_text(json.dumps(overlays), encoding="utf-8")
    return path


@dataclass
class _RecordedOpen:
    proposal: RemediationProposal
    manifest_fix: ManifestFixPlan | None
    draft: bool


class _RecordingForge:
    repo_slug = "rxm7706/local-recipes"

    def __init__(self) -> None:
        self.opens: list[_RecordedOpen] = []

    def existing_open_pr(self, finding_id: str) -> None:
        return None

    def open_pull_request(
        self,
        proposal: RemediationProposal,
        *,
        manifest_fix: ManifestFixPlan | None = None,
        draft: bool = False,
    ) -> str:
        self.opens.append(_RecordedOpen(proposal, manifest_fix, draft))
        return "https://example.test/pr/1"


class _NonEstateForge(_RecordingForge):
    repo_slug = "acme/app"


def test_non_estate_repo_is_skipped_when_draft_flag_on() -> None:
    forge = _NonEstateForge()
    actuation = run_actuator(
        [_vuln()],
        dry_run=False,
        fix_draft_pr_estate_enabled=True,
        client=forge,
        estate_repos=frozenset({"rxm7706/local-recipes"}),
    )
    (outcome,) = actuation.outcomes
    assert outcome.status == "skipped"
    assert outcome.detail == "not an estate repo"
    assert forge.opens == []


def test_estate_flag_on_records_draft_open_with_manifest_fix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    _write_pixi_repo(repo)
    monkeypatch.setattr(
        "pyforge.warden.manifest_fixup.run_pixi_lock",
        lambda *, cwd: (None, 0),
    )
    forge = _RecordingForge()
    actuation = run_actuator(
        [_vuln()],
        dry_run=False,
        fix_target_resolution_enabled=True,
        fix_manifest_edit_enabled=True,
        fix_draft_pr_estate_enabled=True,
        fixed_version_candidates={_vuln().id: ("1.3.0",)},
        scan_target=repo,
        manifest_locations={"leftpad": ("pixi.toml [pypi-dependencies]",)},
        client=forge,
        solver=lambda **_: "accepted",
        estate_repos=frozenset({"rxm7706/local-recipes"}),
    )
    (outcome,) = actuation.outcomes
    assert outcome.status == "opened"
    assert len(forge.opens) == 1
    recorded = forge.opens[0]
    assert recorded.draft is True
    assert recorded.manifest_fix is not None
    assert "Changed paths:" in recorded.proposal.body


def test_flag_off_uses_non_draft_empty_tree_open() -> None:
    forge = _RecordingForge()
    actuation = run_actuator(
        [_vuln()],
        dry_run=False,
        fix_draft_pr_estate_enabled=False,
        client=forge,
    )
    (outcome,) = actuation.outcomes
    assert outcome.status == "opened"
    assert forge.opens[0].draft is False
    assert forge.opens[0].manifest_fix is None


def test_read_boolean_follows_rendered_flag_tree(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    on_tree = _flag_tree(tmp_path / "on", draft_on=True)
    off_tree = _flag_tree(tmp_path / "off", draft_on=False)
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    assert read_boolean(FIX_DRAFT_PR_ESTATE_FLAG, flags_path=on_tree) is True
    assert read_boolean(FIX_DRAFT_PR_ESTATE_FLAG, flags_path=off_tree) is False
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "production")
    assert read_boolean(FIX_DRAFT_PR_ESTATE_FLAG, flags_path=on_tree) is False


class _Response:
    def __init__(self, body: object) -> None:
        self._raw = b"" if body is None else json.dumps(body).encode("utf-8")

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._raw


class _Transport:
    def __init__(self, *replies: object) -> None:
        self._replies = list(replies)
        self.requests: list[urllib.request.Request] = []

    def __call__(self, request: urllib.request.Request, timeout: object = None) -> _Response:
        self.requests.append(request)
        reply = self._replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return _Response(reply)

    def payload(self, index: int) -> Any:
        data = self.requests[index].data
        assert isinstance(data, bytes)
        return json.loads(data)


_PROPOSAL = RemediationProposal(
    finding_id="vuln:GHSA-estate:leftpad@1.2.0",
    action="upgrade",
    subject="leftpad",
    title="warden: upgrade leftpad",
    body="body",
)
_MANIFEST = ManifestFixPlan(files=(ManifestFileChange(path="pixi.toml", content="edited"),))


def test_github_client_posts_blobs_tree_and_draft_pull(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = _Transport(
        {"default_branch": "main"},
        {"commit": {"sha": "base-sha", "commit": {"tree": {"sha": "tree-sha"}}}},
        {"sha": "blob-sha"},
        {"sha": "new-tree-sha"},
        {"sha": "commit-sha"},
        {},
        {"html_url": "https://forge.example/pull/1"},
    )
    monkeypatch.setattr(urllib.request, "urlopen", transport)
    client = GitHubForgeClient("tok", "rxm7706/local-recipes", "https://api.example")
    url = client.open_pull_request(_PROPOSAL, manifest_fix=_MANIFEST, draft=True)
    assert url == "https://forge.example/pull/1"
    methods = [request.get_method() for request in transport.requests]
    assert methods.count("POST") >= 4
    assert transport.payload(-1)["draft"] is True
    assert transport.payload(2) == {"content": "edited", "encoding": "utf-8"}


def test_github_client_flag_off_shape_uses_empty_tree_without_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = _Transport(
        {"default_branch": "main"},
        {"commit": {"sha": "base-sha", "commit": {"tree": {"sha": "tree-sha"}}}},
        {"sha": "commit-sha"},
        {},
        {"html_url": "https://forge.example/pull/2"},
    )
    monkeypatch.setattr(urllib.request, "urlopen", transport)
    client = GitHubForgeClient("tok", "owner/name", "https://api.example")
    client.open_pull_request(_PROPOSAL)
    assert transport.payload(2) == {
        "message": _PROPOSAL.title,
        "tree": "tree-sha",
        "parents": ["base-sha"],
    }
    assert "draft" not in transport.payload(4)
