"""Story 16.2 — fleet run scans inventoried repos (one verdict per repo)."""

from __future__ import annotations

import ast
import json
import shutil
import subprocess
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.test.utils import override_settings
from pyforge.core.flags import read_boolean

from django_warden_fabric.fleet import FLEET_SCAN_FLAG
from django_warden_fabric.models import FleetRepo
from django_warden_fabric.models import FleetRepoScan
from django_warden_fabric.models import FleetRun
from django_warden_fabric.models import JobStatus
from django_warden_fabric.tasks import run_fleet_run
from django_warden_fabric.tasks import scan_fleet_repo

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FABRIC_ROOT = (
    _REPO_ROOT
    / "shared"
    / "packages"
    / "django-warden"
    / "src"
    / "django_warden_fabric"
)
_TASKS_PATH = _FABRIC_ROOT / "tasks.py"
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


def _flag_tree(*, on: bool) -> dict:
    return {
        "flags": {
            FLEET_SCAN_FLAG: {
                "state": "ENABLED",
                "variants": {"on": True, "off": False},
                "defaultVariant": "on" if on else "off",
                "metadata": {
                    "owner": "warden",
                    "story": "16-2-a-fleet-run-scans-each-inventoried-repo-one-verdict-per-repo",
                    "created": "2026-09-28",
                    "on_everywhere": "",
                    "cleanup_by": "",
                },
            },
        },
    }


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
        ["git", "clone", "--bare", str(work), str(bare)],
        check=True,
        capture_output=True,
    )
    return f"file://{bare.resolve()}"


def _seed_inventory(tmp_path: Path, *, extra: dict | None = None) -> list[FleetRepo]:
    repos = []
    for idx in range(3):
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


@pytest.fixture
def fleet_flags_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    tree = tmp_path / "flags-on.json"
    tree.write_text(json.dumps(_flag_tree(on=True)), encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    assert read_boolean(FLEET_SCAN_FLAG, flags_path=tree) is True
    return tree


@pytest.fixture
def fleet_flags_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    tree = tmp_path / "flags-off.json"
    tree.write_text(json.dumps(_flag_tree(on=False)), encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    assert read_boolean(FLEET_SCAN_FLAG, flags_path=tree) is False
    return tree


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_fleet_run_three_repos(tmp_path: Path, fleet_flags_on: Path) -> None:
    _seed_inventory(tmp_path)
    run = FleetRun.objects.create(organisation=_ORG, status=JobStatus.PENDING)
    run_fleet_run(str(run.pk))
    run.refresh_from_db()
    assert run.status == JobStatus.SUCCEEDED
    scans = FleetRepoScan.objects.filter(fleet_run=run)
    assert scans.count() == 3
    for row in scans:
        assert row.status == JobStatus.SUCCEEDED
        assert row.scan_exit_code in (0, 1, 2)
        assert row.report_json
        assert "CLEAN" not in row.status
        assert "VULNERABLE" not in row.status


@pytest.mark.django_db
def test_job_status_vocabulary_only() -> None:
    allowed = {c.value for c in JobStatus}
    assert allowed == {"pending", "running", "succeeded", "failed"}
    for field in (FleetRun._meta.get_field("status"), FleetRepoScan._meta.get_field("status")):
        assert {c for c, _ in field.choices} <= allowed


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_clone_directory_removed(tmp_path: Path, fleet_flags_on: Path) -> None:
    _seed_inventory(tmp_path)
    seen: list[Path] = []

    def _track_mkdtemp(prefix: str = "warden-fleet-") -> Path:
        from django_warden_fabric import fleet as fleet_mod

        path = fleet_mod.mkdtemp_clone_dir(prefix=prefix)
        seen.append(path)
        return path

    with patch("django_warden_fabric.tasks.mkdtemp_clone_dir", side_effect=_track_mkdtemp):
        run = FleetRun.objects.create(organisation=_ORG)
        run_fleet_run(str(run.pk))
    assert seen
    for path in seen:
        assert not path.exists()


def test_celery_tasks_are_keys_not_blobs() -> None:
    tree = ast.parse(_TASKS_PATH.read_text(encoding="utf-8"))
    for name in ("run_fleet_run", "scan_fleet_repo", "finalize_fleet_run"):
        fn = next(
            node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name
        )
        arg_names = [a.arg for a in fn.args.args]
        assert "fleet_run_id" in arg_names or name == "finalize_fleet_run"
        for forbidden in ("manifest", "content", "blob", "report_json", "clone_url"):
            assert forbidden not in arg_names


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_scan_uses_fix_prs_dry_run(tmp_path: Path, fleet_flags_on: Path) -> None:
    repos = _seed_inventory(tmp_path)
    run = FleetRun.objects.create(organisation=_ORG)
    with patch("django_warden_fabric.tasks._run_warden_engines") as mock_scan:
        mock_scan.return_value = ('{"status":"clean"}', "{}", 0)
        scan_fleet_repo(str(run.pk), str(repos[0].pk))
        mock_scan.assert_called_once()
        _args, kwargs = mock_scan.call_args
        assert kwargs.get("fix_prs_dry_run") is True


@pytest.mark.django_db
def test_flag_off_refuses_exit_2(fleet_flags_off: Path) -> None:
    stderr = StringIO()
    with pytest.raises(SystemExit) as exc:
        call_command("warden_fleet_run", _ORG, stderr=stderr)
    assert exc.value.code == 2


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_clone_failure_repo_failed_run_succeeded(tmp_path: Path, fleet_flags_on: Path) -> None:
    FleetRepo.objects.create(
        organisation=_ORG,
        full_name=f"{_ORG}/bad",
        default_branch="main",
        clone_url="file:///no-such-repo",
        archived=False,
    )
    FleetRepo.objects.create(
        organisation=_ORG,
        full_name=f"{_ORG}/good",
        default_branch="main",
        clone_url=_init_bare_repo(tmp_path, "good"),
        archived=False,
    )
    run = FleetRun.objects.create(organisation=_ORG)
    run_fleet_run(str(run.pk))
    run.refresh_from_db()
    assert run.status == JobStatus.SUCCEEDED
    bad = FleetRepoScan.objects.get(fleet_run=run, fleet_repo__full_name=f"{_ORG}/bad")
    assert bad.status == JobStatus.FAILED


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_archived_repo_skipped(tmp_path: Path, fleet_flags_on: Path) -> None:
    _seed_inventory(
        tmp_path,
        extra={
            "full_name": f"{_ORG}/archived",
            "default_branch": "main",
            "clone_url": "file:///unused",
            "archived": True,
        },
    )
    run = FleetRun.objects.create(organisation=_ORG)
    run_fleet_run(str(run.pk))
    row = FleetRepoScan.objects.get(fleet_run=run, fleet_repo__full_name=f"{_ORG}/archived")
    assert row.error == "skipped: archived"
    assert row.status == JobStatus.SUCCEEDED


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_scan_exit_code_two_persisted(tmp_path: Path, fleet_flags_on: Path) -> None:
    repos = _seed_inventory(tmp_path)
    run = FleetRun.objects.create(organisation=_ORG)
    with patch("django_warden_fabric.tasks._run_warden_engines") as mock_scan:
        mock_scan.return_value = ('{"status":"error"}', "{}", 2)
        scan_fleet_repo(str(run.pk), str(repos[0].pk))
    row = FleetRepoScan.objects.get(fleet_run=run, fleet_repo=repos[0])
    assert row.scan_exit_code == 2
    assert row.status == JobStatus.SUCCEEDED
