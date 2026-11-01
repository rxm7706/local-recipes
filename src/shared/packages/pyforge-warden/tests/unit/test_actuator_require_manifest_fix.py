"""Story 16.6 -- ``require_manifest_fix``: no manifest edit, no forge call."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.warden.actuator import FIX_MANIFEST_EDIT_FLAG, RemediationProposal, run_actuator
from pyforge.warden.fix_solver import accepting_solver
from pyforge.warden.manifest_fixup import ManifestFixPlan
from pyforge.warden.models import Finding, Severity, SeverityTier

_VULN_ID = "vuln:GHSA-fleet:leftpad@1.2.0"
_REMOVAL_ID = "hygiene:DEP002:leftpad"
_REPO = "acme/app"


@pytest.fixture(autouse=True)
def _production_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "production")


class _RecordingForge:
    repo_slug = _REPO

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.opened: list[ManifestFixPlan | None] = []

    def existing_open_pr(self, finding_id: str) -> None:
        self.calls.append(f"existing_open_pr:{finding_id}")

    def open_pull_request(
        self,
        proposal: RemediationProposal,
        *,
        manifest_fix: ManifestFixPlan | None = None,
        draft: bool = False,
    ) -> str:
        self.calls.append(f"open_pull_request:{proposal.finding_id}")
        self.opened.append(manifest_fix)
        return "https://forge.invalid/pr/1"


def _finding(finding_id: str) -> Finding:
    return Finding(
        id=finding_id,
        axis="vulnerability" if finding_id.startswith("vuln:") else "hygiene",
        message="fixture",
        subject="leftpad",
        severity=Severity(tier=SeverityTier.HIGH, raw=None),
    )


def _repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "demo"\ndependencies = [\n    "leftpad==1.2.0",\n]\n',
        encoding="utf-8",
    )
    return root


def _act(
    tmp_path: Path,
    finding_id: str,
    *,
    manifest_edit: bool = True,
    manifest_locations: dict[str, tuple[str, ...]] | None = None,
    require_manifest_fix: bool = True,
    forge: _RecordingForge,
):
    if manifest_locations is None:
        manifest_locations = {"leftpad": ("pyproject.toml [project.dependencies]",)}
    return run_actuator(
        [_finding(finding_id)],
        dry_run=False,
        client=forge,
        fixed_version_candidates={_VULN_ID: ("1.3.0",)},
        scan_target=_repo(tmp_path / "clone"),
        solver=accepting_solver,
        fix_target_resolution_enabled=True,
        fix_manifest_edit_enabled=manifest_edit,
        fix_draft_pr_estate_enabled=True,
        manifest_locations=manifest_locations,
        authorized_fleet_repo=_REPO,
        require_manifest_fix=require_manifest_fix,
    )


def test_a_prepared_manifest_fix_opens_one_draft_carrying_it(tmp_path: Path) -> None:
    forge = _RecordingForge()
    (outcome,) = _act(tmp_path, _VULN_ID, forge=forge).outcomes
    assert outcome.status == "opened"
    (plan,) = forge.opened
    assert plan is not None
    (change,) = plan.files
    assert change.path == "pyproject.toml"
    assert '"leftpad>=1.3.0",' in change.content


@pytest.mark.parametrize(
    ("finding_id", "manifest_edit", "reason"),
    [
        (_REMOVAL_ID, True, "no manifest fix: a removal fix has no manifest edit"),
        (_VULN_ID, False, f"no manifest fix: the manifest edit is off ({FIX_MANIFEST_EDIT_FLAG})"),
    ],
    ids=["removal", "manifest-edit-off"],
)
def test_no_manifest_fix_fails_before_any_forge_call(
    tmp_path: Path,
    finding_id: str,
    manifest_edit: bool,
    reason: str,
) -> None:
    forge = _RecordingForge()
    (outcome,) = _act(tmp_path, finding_id, manifest_edit=manifest_edit, forge=forge).outcomes
    assert outcome.status == "failed"
    assert outcome.detail == reason
    assert forge.calls == []


def test_an_undeclared_package_fails_before_any_forge_call(tmp_path: Path) -> None:
    forge = _RecordingForge()
    (outcome,) = _act(tmp_path, _VULN_ID, manifest_locations={}, forge=forge).outcomes
    assert outcome.status == "failed"
    assert outcome.detail == "manifest edit failed: no manifest location for package"
    assert forge.calls == []


def test_without_the_requirement_a_removal_still_opens(tmp_path: Path) -> None:
    """The default (``warden scan --open-fix-prs``) is unchanged."""
    forge = _RecordingForge()
    (outcome,) = _act(tmp_path, _REMOVAL_ID, require_manifest_fix=False, forge=forge).outcomes
    assert outcome.status == "opened"
    assert forge.opened == [None]
