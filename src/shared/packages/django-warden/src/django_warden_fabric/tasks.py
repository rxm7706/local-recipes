"""Celery tasks for warden_fabric — keys-not-blobs (Story 8.1)."""

from __future__ import annotations

import contextlib
import io
import logging
import tempfile
from pathlib import Path

from celery import chord
from celery import shared_task
from django.conf import settings

from .fleet import mkdtemp_clone_dir
from .fleet import remove_clone_dir
from .fleet import shallow_clone
from .models import ComplianceJob
from .models import FleetRepo
from .models import FleetRepoScan
from .models import FleetRun
from .models import JobStatus
from .phases import PHASES
from .phases import advance

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = frozenset(
    {
        ".txt",
        ".toml",
        ".yaml",
        ".yml",
        ".lock",
        ".json",
    },
)

_WELL_KNOWN_MANIFEST_NAMES = frozenset(
    {
        "requirements.txt",
        "environment.yaml",
        "pixi.toml",
        "pyproject.toml",
        "pixi.lock",
        "conda-lock.yml",
    },
)


def _blob_path(storage_key: str) -> Path:
    root = Path(getattr(settings, "COMPLIANCE_FACE_BLOB_ROOT", tempfile.gettempdir()))
    path = (root / storage_key).resolve()
    if not str(path).startswith(str(root.resolve())):
        msg = "storage_key escapes blob root"
        raise ValueError(msg)
    return path


def _validate_manifest_blob(path: Path, storage_key: str) -> None:
    if not path.is_file():
        msg = f"missing blob for key {storage_key}"
        raise FileNotFoundError(msg)
    if path.suffix.lower() not in SUPPORTED_SUFFIXES and path.name not in (
        _WELL_KNOWN_MANIFEST_NAMES
    ):
        msg = f"unsupported manifest: {path.name}"
        raise ValueError(msg)


@shared_task(bind=True, name="warden_fabric.run_job")
def run_compliance_job(self, job_id: str) -> str:
    """Execute a job by storage_key only — never receive manifest bytes."""
    job = ComplianceJob.objects.get(pk=job_id)
    job.status = ComplianceJob.Status.RUNNING
    job.save(update_fields=["status", "updated_at"])
    try:
        advance(job, "validate")
        path = _blob_path(job.storage_key)
        _validate_manifest_blob(path, job.storage_key)

        advance(job, "materialize")
        target = path.parent
        advance(job, "scan")
        report_json, sbom_json, _exit = _run_warden_engines(target)

        advance(job, "sbom")
        job.report_json = report_json
        job.sbom_json = sbom_json
        job.save(update_fields=["report_json", "sbom_json", "updated_at"])

        advance(job, "persist")
        advance(job, "complete")
        job.status = ComplianceJob.Status.SUCCEEDED
        job.save(update_fields=["status", "updated_at"])
        return str(job.id)
    except Exception as exc:
        logger.exception("compliance job %s failed", job_id)
        job.status = ComplianceJob.Status.FAILED
        job.error = f"{exc.__class__.__name__}: {exc}"
        job.save(update_fields=["status", "error", "updated_at"])
        raise


def _run_warden_engines(
    target: Path,
    *,
    fix_prs_dry_run: bool = False,
) -> tuple[str, str, int]:
    """Call EXISTING warden CLI scan — never reimplement analyzers."""
    # Lazy: platform host must import without pyforge installed (Story 10.1
    # boundary; Django check/migrate run in the platform-only env).
    from pyforge.warden.cli import main as warden_main  # noqa: PLC0415

    argv = ["scan", str(target), "--format", "json"]
    if fix_prs_dry_run:
        argv.append("--fix-prs-dry-run")
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = warden_main(argv)
    report_json = out.getvalue().strip() or "{}"
    if code not in (0, 1, 2):
        msg = f"warden scan exited {code}: {err.getvalue()[:500]}"
        raise RuntimeError(msg)
    return report_json, "{}", int(code)


@shared_task(bind=True, name="warden_fabric.finalize_fleet_run")
def finalize_fleet_run(self, scan_results: list[object], fleet_run_id: str) -> str:
    """Mark the fleet run complete after all repo sub-tasks finish."""
    run = FleetRun.objects.get(pk=fleet_run_id)
    run.status = JobStatus.SUCCEEDED
    run.save(update_fields=["status", "updated_at"])
    return str(run.id)


@shared_task(bind=True, name="warden_fabric.run_fleet_run")
def run_fleet_run(self, fleet_run_id: str) -> str:
    """Fan out one sub-task per inventoried repo — message carries ids only."""
    run = FleetRun.objects.get(pk=fleet_run_id)
    run.status = JobStatus.RUNNING
    run.save(update_fields=["status", "updated_at"])
    repos = FleetRepo.objects.filter(organisation=run.organisation).order_by("full_name")
    try:
        signatures = []
        for repo in repos:
            if repo.archived:
                FleetRepoScan.objects.update_or_create(
                    fleet_run=run,
                    fleet_repo=repo,
                    defaults={
                        "status": JobStatus.SUCCEEDED,
                        "error": "skipped: archived",
                        "commit_sha": "",
                        "report_json": "{}",
                        "scan_exit_code": None,
                    },
                )
                continue
            signatures.append(scan_fleet_repo.s(fleet_run_id, str(repo.pk)))
        if signatures:
            chord(signatures)(finalize_fleet_run.s(fleet_run_id))
        else:
            finalize_fleet_run.delay(fleet_run_id)
        return str(run.id)
    except Exception as exc:
        logger.exception("fleet run %s failed", fleet_run_id)
        run.status = JobStatus.FAILED
        run.error = f"{exc.__class__.__name__}: {exc}"
        run.save(update_fields=["status", "error", "updated_at"])
        raise


@shared_task(bind=True, name="warden_fabric.scan_fleet_repo")
def scan_fleet_repo(self, fleet_run_id: str, fleet_repo_id: str) -> str:
    """Clone one repo, run ``warden scan``, persist per-repo verdict."""
    run = FleetRun.objects.get(pk=fleet_run_id)
    repo = FleetRepo.objects.get(pk=fleet_repo_id)
    row, _created = FleetRepoScan.objects.get_or_create(
        fleet_run=run,
        fleet_repo=repo,
        defaults={"status": JobStatus.PENDING},
    )
    row.status = JobStatus.RUNNING
    row.save(update_fields=["status", "updated_at"])
    clone_dir = mkdtemp_clone_dir()
    try:
        commit_sha = shallow_clone(
            clone_url=repo.clone_url,
            branch=repo.default_branch,
            dest=clone_dir,
        )
        report_json, _sbom, exit_code = _run_warden_engines(
            clone_dir,
            fix_prs_dry_run=True,
        )
        row.commit_sha = commit_sha
        row.report_json = report_json
        row.scan_exit_code = exit_code
        row.status = JobStatus.SUCCEEDED
        row.error = ""
        row.save(
            update_fields=[
                "commit_sha",
                "report_json",
                "scan_exit_code",
                "status",
                "error",
                "updated_at",
            ],
        )
        return str(row.id)
    except Exception as exc:
        logger.exception("fleet repo scan %s failed", fleet_repo_id)
        row.status = JobStatus.FAILED
        row.error = f"{exc.__class__.__name__}: {exc}"
        row.save(update_fields=["status", "error", "updated_at"])
        return str(row.id)
    finally:
        remove_clone_dir(clone_dir)


_ = PHASES
