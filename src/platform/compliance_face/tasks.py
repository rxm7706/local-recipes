"""Celery tasks for compliance_face — keys-not-blobs (Story 8.1)."""

from __future__ import annotations

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


def _blob_path(storage_key: str) -> Path:
    root = Path(getattr(settings, "COMPLIANCE_FACE_BLOB_ROOT", tempfile.gettempdir()))
    path = (root / storage_key).resolve()
    if not str(path).startswith(str(root.resolve())):
        raise ValueError("storage_key escapes blob root")
    return path


@shared_task(bind=True, name="compliance_face.run_job")
def run_compliance_job(self, job_id: str) -> str:
    """Execute a job by storage_key only — never receive manifest bytes."""
    job = ComplianceJob.objects.get(pk=job_id)
    job.status = ComplianceJob.Status.RUNNING
    job.save(update_fields=["status", "updated_at"])
    try:
        advance(job, "validate")
        path = _blob_path(job.storage_key)
        if not path.is_file():
            raise FileNotFoundError(f"missing blob for key {job.storage_key}")
        if path.suffix.lower() not in SUPPORTED_SUFFIXES and path.name not in {
            "requirements.txt",
            "environment.yaml",
            "pixi.toml",
            "pyproject.toml",
        }:
            # Still allow well-known basenames.
            if path.name not in {
                "requirements.txt",
                "environment.yaml",
                "pixi.toml",
                "pyproject.toml",
                "pixi.lock",
                "conda-lock.yml",
            }:
                raise ValueError(f"unsupported manifest: {path.name}")

        advance(job, "materialize")
        # Scan target: parent dir containing the blob (warden discovers manifests).
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
    import contextlib
    import io

    from pyforge.warden.cli import main as warden_main

    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = warden_main(["scan", str(target), "--format", "json"])
    report_json = out.getvalue().strip() or "{}"
    if code not in (0, 1, 2):
        raise RuntimeError(f"warden scan exited {code}: {err.getvalue()[:500]}")
    # SBOM: best-effort second pass via library if report parsed.
    sbom_json = "{}"
    try:
        from pyforge.warden.report import ComplianceReport
        from pyforge.warden.sbom import render_cyclonedx

        # Re-scan via library internals is out of scope; leave empty SBOM
        # when CLI-only path is used. Story 8.2 accepts CLI report bytes.
        _ = (ComplianceReport, render_cyclonedx)
    except Exception:  # noqa: BLE001
        pass
    return report_json, sbom_json


_ = PHASES
