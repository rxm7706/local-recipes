"""Stories 16.3 / 16.6-16.8 — fleet fix proposals: queue, approval, delivery."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import timedelta
from io import StringIO
from pathlib import Path
from typing import Any
from typing import Protocol
from typing import Self
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.test.utils import override_settings
from django.utils import timezone
from django_pyforge.flags import evaluate_from_source
from django_warden_fabric.fleet import FLEET_APPROVAL_EXPIRY_DEFAULT_SECONDS
from django_warden_fabric.fleet import FLEET_APPROVAL_EXPIRY_SETTING
from django_warden_fabric.fleet import FLEET_FIX_PROPOSALS_FLAG
from django_warden_fabric.fleet import FLEET_SCAN_FLAG
from django_warden_fabric.fleet import mkdtemp_clone_dir
from django_warden_fabric.models import FixProposal
from django_warden_fabric.models import FleetRepo
from django_warden_fabric.models import FleetRepoScan
from django_warden_fabric.models import FleetRun
from django_warden_fabric.models import JobStatus
from django_warden_fabric.proposals import ProposalRefusedError
from django_warden_fabric.proposals import approve_proposal
from django_warden_fabric.proposals import dismiss_proposal
from django_warden_fabric.proposals import queue_proposals_from_scan
from django_warden_fabric.tasks import finalize_fleet_run
from django_warden_fabric.tasks import open_fix_proposal

_PLATFORM_DIR = Path(__file__).resolve().parents[1]
_FLAGS_JSON = _PLATFORM_DIR / "config" / "flags.json"
_REPO_ROOT = Path(__file__).resolve().parents[2]
_CLEAN_PROJECT = (
    _REPO_ROOT
    / "shared"
    / "packages"
    / "pyforge-warden"
    / "tests"
    / "fixtures"
    / "projects"
    / "clean"
)
_ORG = "fixture-org"
_FIXTURE_REPO_COUNT = 3
_EXIT_REFUSED = 2
_FINDING_A = "vuln:PDOS-FIXTURE-0001:pkg-a@1.0.0"
_FINDING_B = "hygiene:DEP002:pkg-b"
_TWO_PROPOSALS = 2
# Story 16.6: a package the clean fixture's pyproject.toml declares, and one it
# does not; the dry-run target is the lowest stored candidate.
_FINDING_REQUESTS = "vuln:PDOS-FIXTURE-0002:requests@2.31.0"
_FINDING_UNDECLARED = "vuln:PDOS-FIXTURE-0003:urllib3@1.26.0"
_CANDIDATES = ("2.32.0", "2.33.0")
_FORGE_PR_URL = "https://forge.invalid/pr/1"
# Warden's actuator flags by key: src/platform never imports pyforge.* (AGENTS.md).
_FIX_TARGET_RESOLUTION_FLAG = "pyforge.warden.fix_target_resolution"
_FIX_MANIFEST_EDIT_FLAG = "pyforge.warden.fix_manifest_edit"
# Story 16.7: the approve's fresh ``warden scan`` of the clone is stubbed here.
_ENGINES = "django_warden_fabric.tasks._run_warden_engines"
_EIGHT_DAYS = 8 * 24 * 60 * 60
_THIRTY_DAYS = 30 * 24 * 60 * 60
_ONE_MINUTE = 60
_TWO_MINUTES = 120


def _init_bare_repo(tmp_path: Path, name: str) -> str:
    work = tmp_path / f"{name}-work"
    bare = tmp_path / f"{name}.git"
    shutil.copytree(_CLEAN_PROJECT, work)
    for cmd in (
        ["git", "init"],
        ["git", "config", "user.email", "fleet@test.local"],
        ["git", "config", "user.name", "fleet"],
        ["git", "add", "-A"],
        ["git", "commit", "-m", "init"],
        ["git", "branch", "-M", "main"],
    ):
        subprocess.run(cmd, cwd=work, check=True, capture_output=True)  # noqa: S603
    subprocess.run(  # noqa: S603
        ["git", "clone", "--bare", str(work), str(bare)],  # noqa: S607
        check=True,
        capture_output=True,
    )
    return f"file://{bare.resolve()}"


def _seed_inventory(tmp_path: Path, *, extra: dict | None = None) -> list[FleetRepo]:
    repos = []
    for idx in range(_FIXTURE_REPO_COUNT):
        url = _init_bare_repo(tmp_path, f"repo-{idx}")
        repos.append(
            FleetRepo.objects.create(
                organisation=_ORG,
                full_name=f"{_ORG}/repo-{idx}",
                default_branch="main",
                clone_url=url,
                archived=False,
            ),
        )
    if extra:
        repos.append(FleetRepo.objects.create(organisation=_ORG, **extra))
    return repos


def _flag_tree(*, fleet_on: bool, proposals_on: bool, fix_on: bool = False) -> dict:
    tree = json.loads(_FLAGS_JSON.read_text(encoding="utf-8"))
    tree["flags"][FLEET_SCAN_FLAG]["defaultVariant"] = "on" if fleet_on else "off"
    tree["flags"][FLEET_FIX_PROPOSALS_FLAG]["defaultVariant"] = (
        "on" if proposals_on else "off"
    )
    for key in (_FIX_TARGET_RESOLUTION_FLAG, _FIX_MANIFEST_EDIT_FLAG):
        tree["flags"][key]["defaultVariant"] = "on" if fix_on else "off"
    return tree


def _dry_run_resolution(candidates: tuple[str, ...]) -> dict[str, Any]:
    """The ``fix_resolution`` a dry-run outcome carries (the solver not run)."""
    return {
        "target": candidates[0],
        "candidates": list(candidates),
        "attempts": [],
        "solver": "not-run",
        "failure_detail": None,
    }


def _report_with_planned(
    *finding_ids: str,
    candidates: tuple[str, ...] | None = None,
) -> str:
    outcomes: list[dict[str, Any]] = [
        {
            "finding_id": fid,
            "action": "upgrade" if fid.startswith("vuln:") else "removal",
            "subject": fid.split(":")[-1].split("@")[0],
            "status": "planned",
            "pr_url": None,
            "detail": None,
        }
        for fid in finding_ids
    ]
    if candidates is not None:
        for outcome in outcomes:
            if outcome["action"] == "upgrade":
                outcome["fix_resolution"] = _dry_run_resolution(candidates)
    findings = [
        {
            "id": fid,
            "axis": "vulnerability" if fid.startswith("vuln:") else "hygiene",
            "message": "fixture",
            "subject": fid.split(":")[-1].split("@")[0],
            "severity": {"tier": "high", "raw": None},
        }
        for fid in finding_ids
    ]
    return json.dumps(
        {
            "schema_version": "1.1.0",
            "status": {
                "value": "warnings",
                "driver": {"axis": "vulnerability", "finding_id": finding_ids[0]},
            },
            "exit_code": 1,
            "findings": findings,
            "actuation": {"dry_run": True, "outcomes": outcomes},
        },
    )


@pytest.fixture
def proposal_flags_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    tree = tmp_path / "flags-on.json"
    tree.write_text(
        json.dumps(_flag_tree(fleet_on=True, proposals_on=True)),
        encoding="utf-8",
    )
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    assert evaluate_from_source(key=FLEET_FIX_PROPOSALS_FLAG, source=tree) is True
    return tree


@pytest.fixture
def proposal_flags_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    tree = tmp_path / "flags-off.json"
    tree.write_text(
        json.dumps(_flag_tree(fleet_on=True, proposals_on=False)),
        encoding="utf-8",
    )
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "production")
    assert evaluate_from_source(key=FLEET_FIX_PROPOSALS_FLAG, source=tree) is False
    return tree


@pytest.fixture
def approve_flags_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Proposals on, and the actuator's fix-target resolution and manifest edit."""
    tree = tmp_path / "flags-approve.json"
    tree.write_text(
        json.dumps(_flag_tree(fleet_on=True, proposals_on=True, fix_on=True)),
        encoding="utf-8",
    )
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    for key in (
        FLEET_FIX_PROPOSALS_FLAG,
        _FIX_TARGET_RESOLUTION_FLAG,
        _FIX_MANIFEST_EDIT_FLAG,
    ):
        assert evaluate_from_source(key=key, source=tree) is True
    return tree


@pytest.fixture
def forge(monkeypatch: pytest.MonkeyPatch) -> _RecordingForge:
    """The fake forge, at the HTTP seam warden's forge client calls through."""
    monkeypatch.setenv("GITHUB_TOKEN", "fixture-token")
    monkeypatch.setenv("GITHUB_API_URL", "https://forge.invalid")
    recording = _RecordingForge()
    monkeypatch.setattr("urllib.request.urlopen", recording)
    return recording


class _Response:
    def __init__(self, body: object) -> None:
        self._raw = json.dumps(body).encode("utf-8")

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def read(self) -> bytes:
        return self._raw


class _ForgeRequest(Protocol):
    """The slice of a urllib Request the fake forge reads (no raw-HTTP import here)."""

    @property
    def full_url(self) -> str: ...

    @property
    def data(self) -> object: ...

    def get_method(self) -> str: ...


class _RecordingForge:
    """A fake GitHub REST forge: every Git Data call recorded, no socket opened."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def __call__(self, request: _ForgeRequest, timeout: object = None) -> _Response:
        method = request.get_method()
        path = request.full_url.split("?", 1)[0]
        data = request.data
        payload = json.loads(data) if isinstance(data, bytes) else None
        self.calls.append((method, path, payload))
        responses: dict[str, object] = {
            "/pulls": [] if method == "GET" else {"html_url": _FORGE_PR_URL},
            "/git/blobs": {"sha": "blob-sha"},
            "/git/trees": {"sha": "new-tree-sha"},
            "/git/commits": {"sha": "new-commit-sha"},
            "/git/refs": {},
        }
        for suffix, response in responses.items():
            if path.endswith(suffix):
                return _Response(response)
        if "/branches/" in path:
            base = {"sha": "base-sha", "commit": {"tree": {"sha": "base-tree-sha"}}}
            return _Response({"commit": base})
        return _Response({"default_branch": "main"})

    def writes(self, suffix: str = "") -> list[dict[str, Any]]:
        return [
            payload or {}
            for method, path, payload in self.calls
            if method != "GET" and path.endswith(suffix)
        ]


class _FreshScan:
    """The approve's fresh ``warden scan`` of the clone: one report, targets kept."""

    def __init__(self, *finding_ids: str) -> None:
        self.finding_ids = finding_ids
        self.targets: list[Path] = []

    def __call__(
        self, target: Path, *, fix_prs_dry_run: bool = False
    ) -> tuple[str, str, int]:
        # The re-scan reads the fresh clone, never the stored report.
        assert (target / "pyproject.toml").is_file()
        assert fix_prs_dry_run is False
        self.targets.append(target)
        findings = [
            {"id": fid, "axis": "vulnerability", "message": "fixture"}
            for fid in self.finding_ids
        ]
        exit_code = 1 if findings else 0
        return json.dumps({"findings": findings}), "{}", exit_code


class _RecordingSolver:
    """The stubbed fix-target solver seam: one verdict, every call recorded."""

    def __init__(self, verdict: str) -> None:
        self.verdict = verdict
        self.calls: list[tuple[str, str]] = []

    def __call__(self, *, scan_target: Path, package: str, floor_version: str) -> str:
        assert scan_target.is_dir()
        self.calls.append((package, floor_version))
        return self.verdict


def _fleet_target(tmp_path: Path, name: str) -> FleetRepo:
    return FleetRepo.objects.create(
        organisation=_ORG,
        full_name=f"{_ORG}/{name}",
        default_branch="main",
        clone_url=_init_bare_repo(tmp_path, name),
        archived=False,
    )


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_run_complete_queues_two_proposals_zero_forge_writes(
    tmp_path: Path,
    proposal_flags_on: Path,
) -> None:
    repos = _seed_inventory(tmp_path)
    run = FleetRun.objects.create(organisation=_ORG, status=JobStatus.RUNNING)
    scan_a = FleetRepoScan.objects.create(
        fleet_run=run,
        fleet_repo=repos[0],
        status=JobStatus.SUCCEEDED,
        report_json=_report_with_planned(_FINDING_A, _FINDING_B),
    )
    FleetRepoScan.objects.create(
        fleet_run=run,
        fleet_repo=repos[1],
        status=JobStatus.SUCCEEDED,
        report_json='{"actuation": null}',
    )
    finalize_fleet_run([], str(run.pk))

    queued = FixProposal.objects.filter(
        fleet_repo_scan=scan_a,
        state=FixProposal.State.QUEUED,
    )
    assert queued.count() == _TWO_PROPOSALS


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_queue_stores_the_dry_run_target_and_no_diff(proposal_flags_on: Path) -> None:
    """Story 16.6 AC1: the target is the resolved version, never the package."""
    repo = FleetRepo.objects.create(
        organisation=_ORG,
        full_name=f"{_ORG}/queued",
        default_branch="main",
        clone_url="file:///unused",
        archived=False,
    )
    run = FleetRun.objects.create(organisation=_ORG, status=JobStatus.RUNNING)
    scan = FleetRepoScan.objects.create(
        fleet_run=run,
        fleet_repo=repo,
        status=JobStatus.SUCCEEDED,
        report_json=_report_with_planned(
            _FINDING_A,
            _FINDING_B,
            candidates=("1.3.0", "1.4.0"),
        ),
    )
    finalize_fleet_run([], str(run.pk))

    upgrade = FixProposal.objects.get(fleet_repo_scan=scan, finding_id=_FINDING_A)
    removal = FixProposal.objects.get(fleet_repo_scan=scan, finding_id=_FINDING_B)
    assert upgrade.target == "1.3.0"
    assert removal.target == ""
    for proposal in (upgrade, removal):
        assert json.loads(proposal.planned_paths_json) == []


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_queue_skips_an_outcome_warden_names_a_non_python_ecosystem(
    proposal_flags_on: Path,
) -> None:
    """Story 16.8 AC4: only PyPI or conda findings queue; npm, Go, Cargo do not."""
    native = {
        "vuln:GHSA-npm1-0000-0000:left-pad@1.0.0": "npm",
        "vuln:GO-2026-0001:golang.org/x/text@0.3.0": "golang",
        "vuln:RUSTSEC-2026-0001:smallvec@1.6.0": "cargo",
    }
    conda_finding = "vuln:PDOS-FIXTURE-0003:urllib3@1.26.0"
    document = json.loads(_report_with_planned(_FINDING_A, conda_finding, *native))
    for outcome in document["actuation"]["outcomes"]:
        if outcome["finding_id"] in native:
            outcome["ecosystem"] = native[outcome["finding_id"]]
        elif outcome["finding_id"] == conda_finding:
            outcome["ecosystem"] = "conda"
    repo = FleetRepo.objects.create(
        organisation=_ORG,
        full_name=f"{_ORG}/mixed",
        default_branch="main",
        clone_url="file:///unused",
        archived=False,
    )
    run = FleetRun.objects.create(organisation=_ORG, status=JobStatus.RUNNING)
    scan = FleetRepoScan.objects.create(
        fleet_run=run,
        fleet_repo=repo,
        status=JobStatus.SUCCEEDED,
        report_json=json.dumps(document),
    )
    finalize_fleet_run([], str(run.pk))

    queued = set(
        FixProposal.objects.filter(fleet_repo_scan=scan).values_list(
            "finding_id", flat=True
        )
    )
    assert queued == {_FINDING_A, conda_finding}
    scan.refresh_from_db()
    stored = {finding["id"] for finding in json.loads(scan.report_json)["findings"]}
    assert set(native) <= stored


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_approve_one_delivers_the_manifest_fix_other_stays_queued(
    tmp_path: Path,
    approve_flags_on: Path,
    forge: _RecordingForge,
) -> None:
    """Story 16.6 AC2: the real actuator re-solves on the clone and opens one draft."""
    repo = _fleet_target(tmp_path, "target")
    run = FleetRun.objects.create(organisation=_ORG)
    scan = FleetRepoScan.objects.create(
        fleet_run=run,
        fleet_repo=repo,
        status=JobStatus.SUCCEEDED,
        report_json=_report_with_planned(
            _FINDING_REQUESTS,
            _FINDING_B,
            candidates=_CANDIDATES,
        ),
    )
    assert queue_proposals_from_scan(scan) == _TWO_PROPOSALS
    approved = FixProposal.objects.get(
        fleet_repo_scan=scan, finding_id=_FINDING_REQUESTS
    )
    other = FixProposal.objects.get(fleet_repo_scan=scan, finding_id=_FINDING_B)
    assert approved.target == _CANDIDATES[0]
    solver = _RecordingSolver("accepted")
    fresh = _FreshScan(_FINDING_REQUESTS, _FINDING_B)

    with (
        patch("django_warden_fabric.tasks._fleet_fix_solver", return_value=solver),
        patch(_ENGINES, new=fresh),
        patch("django_warden_fabric.tasks.open_fix_proposal.delay"),
    ):
        approve_proposal(approved.pk, "operator@test")
        open_fix_proposal(str(approved.pk))

    approved.refresh_from_db()
    other.refresh_from_db()
    assert len(fresh.targets) == 1
    assert approved.state == FixProposal.State.OPENED, approved.error
    assert approved.pr_url == _FORGE_PR_URL
    assert other.state == FixProposal.State.QUEUED
    # The stored candidates reached the actuator: the solver tried the lowest.
    assert solver.calls == [("requests", _CANDIDATES[0])]
    # Every forge call targets the one approved repo (its authorization).
    repo_api = f"https://forge.invalid/repos/{repo.full_name}"
    assert all(path.startswith(repo_api) for _m, path, _p in forge.calls)
    # The clone's manifest_locations found pyproject.toml: one blob carries it.
    (blob,) = forge.writes("/git/blobs")
    assert f'"requests>={_CANDIDATES[0]}",' in blob["content"]
    assert "requests==2.31.0" not in blob["content"]
    (tree,) = forge.writes("/git/trees")
    assert [entry["path"] for entry in tree["tree"]] == ["pyproject.toml"]
    (commit,) = forge.writes("/git/commits")
    assert commit["tree"] == "new-tree-sha"
    assert commit["parents"] == ["base-sha"]
    (ref,) = forge.writes("/git/refs")
    assert ref["ref"].startswith("refs/heads/warden/fix/")
    assert ref["sha"] == "new-commit-sha"
    (pull,) = forge.writes("/pulls")
    assert pull["draft"] is True
    assert pull["head"] == ref["ref"].removeprefix("refs/heads/")


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
@pytest.mark.parametrize(
    ("finding_id", "verdict", "reason"),
    [
        (_FINDING_REQUESTS, "rejected", "no candidate was accepted"),
        (_FINDING_UNDECLARED, "accepted", "no manifest location for package"),
        (_FINDING_B, "accepted", "no manifest fix: a removal fix has no manifest edit"),
    ],
    ids=["no-candidate-accepted", "no-declaring-manifest", "removal-has-no-edit"],
)
@pytest.mark.usefixtures("approve_flags_on")
def test_approve_without_a_manifest_fix_fails_with_zero_forge_writes(
    tmp_path: Path,
    forge: _RecordingForge,
    finding_id: str,
    verdict: str,
    reason: str,
) -> None:
    """Story 16.6 AC3: no manifest fix, no PR -- a failed actuation with its reason."""
    repo = _fleet_target(tmp_path, "refused")
    run = FleetRun.objects.create(organisation=_ORG)
    scan = FleetRepoScan.objects.create(
        fleet_run=run,
        fleet_repo=repo,
        status=JobStatus.SUCCEEDED,
        report_json=_report_with_planned(finding_id, candidates=_CANDIDATES),
    )
    queue_proposals_from_scan(scan)
    proposal = FixProposal.objects.get(fleet_repo_scan=scan)

    with (
        patch(
            "django_warden_fabric.tasks._fleet_fix_solver",
            return_value=_RecordingSolver(verdict),
        ),
        patch(_ENGINES, new=_FreshScan(finding_id)),
        patch("django_warden_fabric.tasks.open_fix_proposal.delay"),
    ):
        approve_proposal(proposal.pk, "operator@test")
        open_fix_proposal(str(proposal.pk))

    proposal.refresh_from_db()
    assert proposal.state == FixProposal.State.FAILED
    assert reason in proposal.error
    assert proposal.pr_url == ""
    assert forge.writes() == []
    assert forge.calls == []


def _queued_upgrade(tmp_path: Path, name: str) -> FixProposal:
    repo = _fleet_target(tmp_path, name)
    run = FleetRun.objects.create(organisation=_ORG)
    scan = FleetRepoScan.objects.create(
        fleet_run=run,
        fleet_repo=repo,
        status=JobStatus.SUCCEEDED,
        report_json=_report_with_planned(_FINDING_REQUESTS, candidates=_CANDIDATES),
    )
    queue_proposals_from_scan(scan)
    return FixProposal.objects.get(fleet_repo_scan=scan)


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
@pytest.mark.usefixtures("approve_flags_on")
def test_approve_refuses_a_finding_a_fresh_scan_no_longer_reports(
    tmp_path: Path,
    forge: _RecordingForge,
) -> None:
    """Story 16.7 AC4: the clone is re-scanned; a vanished finding opens nothing."""
    proposal = _queued_upgrade(tmp_path, "vanished")
    solver = _RecordingSolver("accepted")
    fresh = _FreshScan()

    with (
        patch("django_warden_fabric.tasks._fleet_fix_solver", return_value=solver),
        patch(_ENGINES, new=fresh),
        patch("django_warden_fabric.tasks.open_fix_proposal.delay"),
    ):
        approve_proposal(proposal.pk, "operator@test")
        open_fix_proposal(str(proposal.pk))

    proposal.refresh_from_db()
    assert proposal.state == FixProposal.State.FAILED
    assert f"finding {_FINDING_REQUESTS} vanished" in proposal.error
    assert "fresh warden scan" in proposal.error
    assert proposal.pr_url == ""
    assert len(fresh.targets) == 1
    assert not fresh.targets[0].exists()
    assert solver.calls == []
    assert forge.writes() == []
    assert forge.calls == []


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
@pytest.mark.parametrize(
    ("expiry", "age", "refused"),
    [
        (None, _EIGHT_DAYS, True),
        (_ONE_MINUTE, _TWO_MINUTES, True),
        (_THIRTY_DAYS, _EIGHT_DAYS, False),
    ],
    ids=["default-expiry", "setting-shortened", "setting-lengthened"],
)
@pytest.mark.usefixtures("approve_flags_on")
def test_approve_refuses_a_proposal_older_than_the_expiry(
    tmp_path: Path,
    forge: _RecordingForge,
    expiry: int | None,
    age: int,
    refused: bool,  # noqa: FBT001 -- a parametrized expectation
) -> None:
    """Story 16.7 AC5: an old approval is refused; the setting moves the bound."""
    assert FLEET_APPROVAL_EXPIRY_DEFAULT_SECONDS < _EIGHT_DAYS < _THIRTY_DAYS
    proposal = _queued_upgrade(tmp_path, "aged")
    FixProposal.objects.filter(pk=proposal.pk).update(
        created_at=timezone.now() - timedelta(seconds=age),
    )
    solver = _RecordingSolver("accepted")
    fresh = _FreshScan(_FINDING_REQUESTS)
    overrides = {} if expiry is None else {FLEET_APPROVAL_EXPIRY_SETTING: expiry}

    with (
        override_settings(**overrides),
        patch("django_warden_fabric.tasks._fleet_fix_solver", return_value=solver),
        patch(_ENGINES, new=fresh),
        patch("django_warden_fabric.tasks.open_fix_proposal.delay"),
    ):
        approve_proposal(proposal.pk, "operator@test")
        open_fix_proposal(str(proposal.pk))

    proposal.refresh_from_db()
    if refused:
        assert proposal.state == FixProposal.State.FAILED
        assert "proposal expired" in proposal.error
        assert FLEET_APPROVAL_EXPIRY_SETTING in proposal.error
        assert proposal.pr_url == ""
        assert fresh.targets == []
        assert solver.calls == []
        assert forge.calls == []
    else:
        assert proposal.state == FixProposal.State.OPENED, proposal.error
        assert proposal.pr_url == _FORGE_PR_URL
        assert len(fresh.targets) == 1


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_open_failure_records_failed_and_removes_clone(
    tmp_path: Path,
    proposal_flags_on: Path,
) -> None:
    url = _init_bare_repo(tmp_path, "fail")
    repo = FleetRepo.objects.create(
        organisation=_ORG,
        full_name=f"{_ORG}/fail",
        default_branch="main",
        clone_url=url,
        archived=False,
    )
    run = FleetRun.objects.create(organisation=_ORG)
    scan = FleetRepoScan.objects.create(
        fleet_run=run,
        fleet_repo=repo,
        status=JobStatus.SUCCEEDED,
        report_json=_report_with_planned(_FINDING_A),
    )
    queue_proposals_from_scan(scan)
    proposal = FixProposal.objects.get(fleet_repo_scan=scan)
    proposal.state = FixProposal.State.APPROVED
    proposal.save(update_fields=["state"])
    seen: list[Path] = []

    def _track_mkdtemp(prefix: str = "warden-fleet-open-") -> Path:
        path = mkdtemp_clone_dir(prefix=prefix)
        seen.append(path)
        return path

    with (
        patch(
            "django_warden_fabric.tasks.mkdtemp_clone_dir", side_effect=_track_mkdtemp
        ),
        patch(
            "django_warden_fabric.tasks.shallow_clone",
            side_effect=RuntimeError("forge 5xx"),
        ),
    ):
        open_fix_proposal(str(proposal.pk))

    proposal.refresh_from_db()
    assert proposal.state == FixProposal.State.FAILED
    assert "forge 5xx" in proposal.error
    assert seen
    assert not seen[0].exists()


@pytest.mark.django_db
def test_double_approve_refused(proposal_flags_on: Path) -> None:
    run = FleetRun.objects.create(organisation=_ORG)
    repo = FleetRepo.objects.create(
        organisation=_ORG,
        full_name=f"{_ORG}/x",
        default_branch="main",
        clone_url="file:///unused",
        archived=False,
    )
    scan = FleetRepoScan.objects.create(
        fleet_run=run,
        fleet_repo=repo,
        status=JobStatus.SUCCEEDED,
        report_json=_report_with_planned(_FINDING_A),
    )
    queue_proposals_from_scan(scan)
    proposal = FixProposal.objects.get(fleet_repo_scan=scan)
    with patch("django_warden_fabric.tasks.open_fix_proposal.delay"):
        approve_proposal(proposal.pk, "op")
        with pytest.raises(ProposalRefusedError, match="already approved"):
            approve_proposal(proposal.pk, "op")


@pytest.mark.django_db
def test_dismiss_without_forge(proposal_flags_on: Path) -> None:
    run = FleetRun.objects.create(organisation=_ORG)
    repo = FleetRepo.objects.create(
        organisation=_ORG,
        full_name=f"{_ORG}/y",
        default_branch="main",
        clone_url="file:///unused",
        archived=False,
    )
    scan = FleetRepoScan.objects.create(
        fleet_run=run,
        fleet_repo=repo,
        status=JobStatus.SUCCEEDED,
        report_json=_report_with_planned(_FINDING_B),
    )
    queue_proposals_from_scan(scan)
    proposal = FixProposal.objects.get(fleet_repo_scan=scan)
    dismiss_proposal(proposal.pk)
    proposal.refresh_from_db()
    assert proposal.state == FixProposal.State.DISMISSED


@pytest.mark.django_db
def test_flag_off_refuses_exit_2(proposal_flags_off: Path) -> None:
    stderr = StringIO()
    with pytest.raises(SystemExit) as exc:
        call_command(
            "warden_fleet_approve",
            "00000000-0000-0000-0000-000000000001",
            stderr=stderr,
        )
    assert exc.value.code == _EXIT_REFUSED
