"""Stories 16.2 / 16.7 / 16.8 — fleet run scans inventoried repos, one verdict each."""

from __future__ import annotations

import ast
import json
import os
import shutil
import stat
import subprocess
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.test.utils import override_settings
from django_pyforge.flags import evaluate_from_source
from django_warden_fabric import fleet
from django_warden_fabric.fleet import FLEET_FIX_PROPOSALS_FLAG
from django_warden_fabric.fleet import FLEET_SCAN_FLAG
from django_warden_fabric.fleet import mkdtemp_clone_dir
from django_warden_fabric.models import FixProposal
from django_warden_fabric.models import FleetRepo
from django_warden_fabric.models import FleetRepoScan
from django_warden_fabric.models import FleetRun
from django_warden_fabric.models import JobStatus
from django_warden_fabric.tasks import FLEET_OSV_DB_CACHE_SETTING
from django_warden_fabric.tasks import open_fix_proposal
from django_warden_fabric.tasks import run_fleet_inventory
from django_warden_fabric.tasks import run_fleet_run
from django_warden_fabric.tasks import scan_fleet_repo

from tests.test_golden_path_promotion_osv_db import _load_osv_db_builder

_PLATFORM_DIR = Path(__file__).resolve().parents[1]
_FLAGS_JSON = _PLATFORM_DIR / "config" / "flags.json"
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
_FIXTURE_REPO_COUNT = 3
_EXIT_REFUSED = 2
_SCAN_EXIT_ERROR = 2
# Story 16.7: the inventory task's bounds (Story 16.1), which the repo tasks reuse.
_SOFT_TIME_LIMIT = 240
_TIME_LIMIT = 300
_HUNG_MARKER = "hung-clone"
_SHORT_CLONE_TIMEOUT = 1.0
# Story 16.8: real scans of warden's npm and PyPI fixtures against fixture offline
# databases built from in-repo records -- never downloaded.
_WARDEN_FIXTURES = (
    _REPO_ROOT / "shared" / "packages" / "pyforge-warden" / "tests" / "fixtures"
)
_NPM_LOCK = _WARDEN_FIXTURES / "projects" / "npm_vuln" / "package-lock.json"
_PYPI_VULN_PROJECT = _WARDEN_FIXTURES / "projects" / "vuln_high"
_OSV_RECORDS = _WARDEN_FIXTURES / "osv-db"
_NON_PYTHON_FLAG = "pyforge.warden.non_python_ecosystems"
_OSV_CACHE_ENV = "OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY"
_NPM_FINDING = "vuln:PDOS-NPM-FIXTURE-0001:pdos-npm-vuln-fixture@1.0.0"
_PYPI_FINDING = "vuln:PDOS-FIXTURE-0002:pdos-vuln-fixture-high@1.0.0"
_DB_MISSING_PREFIX = "indeterminate:offline-db-unavailable-ecosystem:"


def _flag_tree(*, on: bool) -> dict:
    tree = json.loads(_FLAGS_JSON.read_text(encoding="utf-8"))
    entry = tree["flags"][FLEET_SCAN_FLAG]
    entry["defaultVariant"] = "on" if on else "off"
    return tree


def _init_bare_repo(
    tmp_path: Path,
    name: str,
    *,
    project: Path = _CLEAN_PROJECT,
    extra_files: tuple[Path, ...] = (),
) -> str:
    work = tmp_path / f"{name}-work"
    bare = tmp_path / f"{name}.git"
    shutil.copytree(project, work)
    for extra in extra_files:
        shutil.copy2(extra, work / extra.name)
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
        ["git", "clone", "--bare", str(work), str(bare)],  # noqa: S607 -- git from PATH, like the init loop above
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


@pytest.fixture
def fleet_flags_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    tree = tmp_path / "flags-on.json"
    tree.write_text(json.dumps(_flag_tree(on=True)), encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    assert evaluate_from_source(key=FLEET_SCAN_FLAG, source=tree) is True
    return tree


@pytest.fixture
def fleet_flags_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    tree = tmp_path / "flags-off.json"
    tree.write_text(json.dumps(_flag_tree(on=False)), encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    assert evaluate_from_source(key=FLEET_SCAN_FLAG, source=tree) is False
    return tree


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_fleet_run_three_repos(tmp_path: Path, fleet_flags_on: Path) -> None:
    _seed_inventory(tmp_path)
    run = FleetRun.objects.create(organisation=_ORG, status=JobStatus.PENDING)
    report = json.dumps({"status": "clean", "schemaVersion": "1.1.0"})
    with patch(
        "django_warden_fabric.tasks._run_warden_engines",
        return_value=(report, "{}", 0),
    ):
        run_fleet_run(str(run.pk))
    run.refresh_from_db()
    assert run.status == JobStatus.SUCCEEDED
    scans = FleetRepoScan.objects.filter(fleet_run=run)
    assert scans.count() == _FIXTURE_REPO_COUNT
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
    for model in (FleetRun, FleetRepoScan):
        field = model._meta.get_field("status")  # noqa: SLF001
        assert {c for c, _ in field.choices} <= allowed


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_clone_directory_removed(tmp_path: Path, fleet_flags_on: Path) -> None:
    _seed_inventory(tmp_path)
    seen: list[Path] = []

    def _track_mkdtemp(prefix: str = "warden-fleet-") -> Path:
        path = mkdtemp_clone_dir(prefix=prefix)
        seen.append(path)
        return path

    with patch(
        "django_warden_fabric.tasks.mkdtemp_clone_dir",
        side_effect=_track_mkdtemp,
    ):
        run = FleetRun.objects.create(organisation=_ORG)
        run_fleet_run(str(run.pk))
    assert seen
    for path in seen:
        assert not path.exists()


def test_celery_tasks_are_keys_not_blobs() -> None:
    tree = ast.parse(_TASKS_PATH.read_text(encoding="utf-8"))
    for name in ("run_fleet_run", "scan_fleet_repo", "finalize_fleet_run"):
        fn = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == name
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
    assert exc.value.code == _EXIT_REFUSED


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_clone_failure_repo_failed_run_succeeded(
    tmp_path: Path,
    fleet_flags_on: Path,
) -> None:
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
    row = FleetRepoScan.objects.get(
        fleet_run=run,
        fleet_repo__full_name=f"{_ORG}/archived",
    )
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
    assert row.scan_exit_code == _SCAN_EXIT_ERROR
    assert row.status == JobStatus.SUCCEEDED


def test_fleet_repo_tasks_are_time_bounded() -> None:
    """Story 16.7 AC1: each repo task declares soft < hard, the inventory values."""
    assert run_fleet_inventory.soft_time_limit == _SOFT_TIME_LIMIT
    assert run_fleet_inventory.time_limit == _TIME_LIMIT
    for name, task in (
        ("warden_fabric.scan_fleet_repo", scan_fleet_repo),
        ("warden_fabric.open_fix_proposal", open_fix_proposal),
    ):
        registered = task.app.tasks[name]
        assert registered.soft_time_limit == run_fleet_inventory.soft_time_limit
        assert registered.time_limit == run_fleet_inventory.time_limit
        assert registered.soft_time_limit < registered.time_limit


def _hanging_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A ``git`` on PATH that never returns for a clone of a ``hung-clone`` URL."""
    real_git = shutil.which("git")
    assert real_git
    bin_dir = tmp_path / "fake-bin"
    bin_dir.mkdir()
    stub = bin_dir / "git"
    stub.write_text(
        "#!/bin/sh\n"
        f'case "$*" in *{_HUNG_MARKER}*) exec sleep 60 ;; esac\n'
        f'exec "{real_git}" "$@"\n',
        encoding="utf-8",
    )
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setattr(fleet, "FLEET_CLONE_TIMEOUT_SECONDS", _SHORT_CLONE_TIMEOUT)


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_hung_clone_fails_its_repo_and_the_run_proceeds(
    tmp_path: Path,
    fleet_flags_on: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Story 16.7 AC2: a clone that never returns ends FAILED naming the timeout."""
    _seed_inventory(
        tmp_path,
        extra={
            "full_name": f"{_ORG}/{_HUNG_MARKER}",
            "default_branch": "main",
            "clone_url": f"file:///{_HUNG_MARKER}.git",
            "archived": False,
        },
    )
    _hanging_git(tmp_path, monkeypatch)
    seen: list[Path] = []

    def _track_mkdtemp(prefix: str = "warden-fleet-") -> Path:
        path = mkdtemp_clone_dir(prefix=prefix)
        seen.append(path)
        return path

    run = FleetRun.objects.create(organisation=_ORG, status=JobStatus.PENDING)
    report = json.dumps({"status": "clean", "schemaVersion": "1.1.0"})
    with (
        patch(
            "django_warden_fabric.tasks._run_warden_engines",
            return_value=(report, "{}", 0),
        ),
        patch(
            "django_warden_fabric.tasks.mkdtemp_clone_dir",
            side_effect=_track_mkdtemp,
        ),
    ):
        run_fleet_run(str(run.pk))

    run.refresh_from_db()
    assert run.status == JobStatus.SUCCEEDED
    assert run.failed_repo_count == 1
    hung = FleetRepoScan.objects.get(
        fleet_run=run,
        fleet_repo__full_name=f"{_ORG}/{_HUNG_MARKER}",
    )
    assert hung.status == JobStatus.FAILED
    assert "FleetCloneTimeoutError" in hung.error
    assert f"timed out after {_SHORT_CLONE_TIMEOUT:g} s" in hung.error
    others = FleetRepoScan.objects.filter(fleet_run=run).exclude(pk=hung.pk)
    assert others.count() == _FIXTURE_REPO_COUNT
    assert {row.status for row in others} == {JobStatus.SUCCEEDED}
    # Every throwaway clone is gone, the timed-out one included.
    assert len(seen) == _FIXTURE_REPO_COUNT + 1
    assert not any(path.exists() for path in seen)


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_run_counts_its_failed_and_skipped_repos(
    tmp_path: Path,
    fleet_flags_on: Path,
) -> None:
    """Story 16.7 AC3: one failed clone and one archived repo are the run's misses."""
    for name, url, archived in (
        ("good", _init_bare_repo(tmp_path, "good"), False),
        ("bad", "file:///no-such-repo", False),
        ("archived", "file:///unused", True),
    ):
        FleetRepo.objects.create(
            organisation=_ORG,
            full_name=f"{_ORG}/{name}",
            default_branch="main",
            clone_url=url,
            archived=archived,
        )
    run = FleetRun.objects.create(organisation=_ORG)
    report = json.dumps({"status": "clean", "schemaVersion": "1.1.0"})
    with patch(
        "django_warden_fabric.tasks._run_warden_engines",
        return_value=(report, "{}", 0),
    ):
        run_fleet_run(str(run.pk))

    run.refresh_from_db()
    assert run.status == JobStatus.SUCCEEDED
    assert run.failed_repo_count == 1
    assert run.skipped_repo_count == 1
    allowed = {choice.value for choice in JobStatus}
    statuses = {row.status for row in FleetRepoScan.objects.filter(fleet_run=run)}
    assert statuses <= allowed
    assert run.status in allowed


def _osv_cache(tmp_path: Path, *ecosystems: str) -> Path:
    """Fixture offline OSV databases, one per ecosystem, in osv-scanner's layout."""
    builder = _load_osv_db_builder()
    cache = tmp_path / "osv-cache"
    for ecosystem in ecosystems:
        builder.build_offline_db(
            _OSV_RECORDS / ecosystem.lower(), cache, ecosystem=ecosystem
        )
    return cache


def _fleet_repo(tmp_path: Path, name: str, *, with_pypi: bool) -> FleetRepo:
    """A repo pinning the npm fixture's vulnerable version, and a PyPI one if asked."""
    project = _PYPI_VULN_PROJECT if with_pypi else _NPM_LOCK.parent
    extra = (_NPM_LOCK,) if with_pypi else ()
    return FleetRepo.objects.create(
        organisation=_ORG,
        full_name=f"{_ORG}/{name}",
        default_branch="main",
        clone_url=_init_bare_repo(tmp_path, name, project=project, extra_files=extra),
        archived=False,
    )


def _report(row: FleetRepoScan) -> dict:
    assert row.status == JobStatus.SUCCEEDED, row.error
    return json.loads(row.report_json)


def _finding_ids(report: dict) -> set[str]:
    return {finding["id"] for finding in report["findings"]}


@pytest.fixture
def native_scan_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Fleet, proposal and non-Python flags on; a KEV feed; no inherited OSV cache.

    The osv-scanner on PATH logs each argv, then runs the real one; the log's path
    is returned (Story 16.8 AC5)."""
    tree = _flag_tree(on=True)
    for key in (FLEET_FIX_PROPOSALS_FLAG, _NON_PYTHON_FLAG):
        tree["flags"][key]["defaultVariant"] = "on"
    flags = tmp_path / "flags-native.json"
    flags.write_text(json.dumps(tree), encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flags))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    feeds = tmp_path / "feeds"
    kev = feeds / "kev" / "known_exploited_vulnerabilities.json"
    kev.parent.mkdir(parents=True)
    kev.write_text(json.dumps({"vulnerabilities": []}), encoding="utf-8")
    monkeypatch.setenv("PYFORGE_WARDEN_FEED_CACHE_DIR", str(feeds))
    monkeypatch.delenv(_OSV_CACHE_ENV, raising=False)
    real_osv = shutil.which("osv-scanner")
    assert real_osv, (
        "osv-scanner must be on PATH (platform-ci-test ships pyforge-warden)"
    )
    bin_dir = tmp_path / "osv-bin"
    bin_dir.mkdir()
    argv_log = tmp_path / "osv-argv.log"
    stub = bin_dir / "osv-scanner"
    stub.write_text(
        f'#!/bin/sh\nprintf \'%s\\n\' "$*" >> "{argv_log}"\nexec "{real_osv}" "$@"\n',
        encoding="utf-8",
    )
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return argv_log


@pytest.mark.django_db
def test_worker_scans_npm_lock_against_the_provisioned_db(
    tmp_path: Path,
    native_scan_env: Path,
) -> None:
    """Story 16.8 AC2/AC5: the setting's cache feeds a ``--offline`` scan."""
    cache = _osv_cache(tmp_path, "npm")
    repo = _fleet_repo(tmp_path, "npm-app", with_pypi=False)
    run = FleetRun.objects.create(organisation=_ORG)
    with override_settings(**{FLEET_OSV_DB_CACHE_SETTING: str(cache)}):
        scan_fleet_repo(str(run.pk), str(repo.pk))

    ids = _finding_ids(
        _report(FleetRepoScan.objects.get(fleet_run=run, fleet_repo=repo))
    )
    assert _NPM_FINDING in ids
    assert not [
        finding_id for finding_id in ids if finding_id.startswith(_DB_MISSING_PREFIX)
    ]
    # The worker's own environment is restored after the scan.
    assert _OSV_CACHE_ENV not in os.environ
    scans = [
        line.split()
        for line in native_scan_env.read_text(encoding="utf-8").splitlines()
    ]
    scans = [argv for argv in scans if argv[:1] == ["scan"]]
    assert scans
    for argv in scans:
        assert "--offline" in argv
        assert "--download-offline-databases" not in argv


@pytest.mark.django_db
def test_a_missing_ecosystem_db_stays_indeterminate(
    tmp_path: Path,
    native_scan_env: Path,
) -> None:
    """Story 16.8 AC3: a cache without the npm DB reads indeterminate, never clean."""
    cache = _osv_cache(tmp_path, "PyPI")
    repo = _fleet_repo(tmp_path, "npm-app", with_pypi=False)
    run = FleetRun.objects.create(organisation=_ORG)
    with override_settings(**{FLEET_OSV_DB_CACHE_SETTING: str(cache)}):
        scan_fleet_repo(str(run.pk), str(repo.pk))

    report = _report(FleetRepoScan.objects.get(fleet_run=run, fleet_repo=repo))
    assert report["status"]["value"] == "indeterminate"
    assert report["status"]["driver"] == {
        "axis": "vulnerability",
        "finding_id": f"{_DB_MISSING_PREFIX}npm",
    }
    assert _NPM_FINDING not in _finding_ids(report)


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_an_npm_finding_queues_no_proposal_while_a_pypi_one_does(
    tmp_path: Path,
    native_scan_env: Path,
) -> None:
    """Story 16.8 AC4: finalize queues the PyPI ``vuln:`` outcome, never the npm one."""
    cache = _osv_cache(tmp_path, "PyPI", "npm")
    repo = _fleet_repo(tmp_path, "mixed-app", with_pypi=True)
    run = FleetRun.objects.create(organisation=_ORG)
    with override_settings(**{FLEET_OSV_DB_CACHE_SETTING: str(cache)}):
        run_fleet_run(str(run.pk))

    run.refresh_from_db()
    assert run.status == JobStatus.SUCCEEDED
    report = _report(FleetRepoScan.objects.get(fleet_run=run, fleet_repo=repo))
    assert {_NPM_FINDING, _PYPI_FINDING} <= _finding_ids(report)
    outcomes = {
        outcome["finding_id"]: outcome for outcome in report["actuation"]["outcomes"]
    }
    assert outcomes[_NPM_FINDING]["status"] == "planned"
    assert outcomes[_NPM_FINDING]["ecosystem"] == "npm"
    queued = set(
        FixProposal.objects.filter(fleet_repo_scan__fleet_run=run).values_list(
            "finding_id", flat=True
        )
    )
    assert _PYPI_FINDING in queued
    assert _NPM_FINDING not in queued


@pytest.mark.django_db
def test_warden_fabric_migrations_are_whole() -> None:
    """Story 16.7 AC6: the models and the migrations agree (``0004`` included)."""
    stdout = StringIO()
    call_command(
        "makemigrations",
        "warden_fabric",
        "--check",
        "--dry-run",
        stdout=stdout,
    )
    assert "No changes detected" in stdout.getvalue()
