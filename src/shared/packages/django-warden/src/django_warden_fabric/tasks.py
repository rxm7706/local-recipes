"""Celery tasks for warden_fabric — keys-not-blobs (Story 8.1)."""

from __future__ import annotations

import contextlib
import io
import logging
import tempfile
from pathlib import Path

from celery import shared_task
from django.conf import settings

from .models import ComplianceJob
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
        report_json, sbom_json = _run_warden_engines(target)

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


def _run_warden_engines(target: Path) -> tuple[str, str]:
    """Call EXISTING warden CLI scan — never reimplement analyzers."""
    # Lazy: platform host must import without pyforge installed (Story 10.1
    # boundary; Django check/migrate run in the platform-only env).
    from pyforge.warden.cli import main as warden_main  # noqa: PLC0415

    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = warden_main(["scan", str(target), "--format", "json"])
    report_json = out.getvalue().strip() or "{}"
    if code not in (0, 1, 2):
        msg = f"warden scan exited {code}: {err.getvalue()[:500]}"
        raise RuntimeError(msg)
    return report_json, "{}"


_ = PHASES
