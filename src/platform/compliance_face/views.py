"""HTTP face: upload + job status/results (Stories 8.1 / 8.2)."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from django.conf import settings
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST

from .models import ComplianceJob
from .phases import current_progress
from .tasks import SUPPORTED_SUFFIXES
from .tasks import run_compliance_job

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


def _blob_root() -> Path:
    root = Path(getattr(settings, "COMPLIANCE_FACE_BLOB_ROOT", tempfile.gettempdir()))
    root.mkdir(parents=True, exist_ok=True)
    return root


@require_GET
def chrome_home(request: HttpRequest) -> HttpResponse:
    """HTML face that extends django-pyforge chrome (Story 18.1)."""
    return render(request, "compliance_face/chrome.html")


@csrf_exempt
@require_POST
def upload_manifest(request: HttpRequest) -> HttpResponse:
    """Accept a multipart file upload; store blob; enqueue Celery by key only."""
    uploaded = request.FILES.get("manifest")
    if uploaded is None:
        return JsonResponse({"error": "missing manifest file field"}, status=400)
    name = Path(uploaded.name).name
    suffix = Path(name).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES and name not in _WELL_KNOWN_MANIFEST_NAMES:
        return JsonResponse({"error": f"unsupported format: {name}"}, status=400)

    storage_key = f"{uuid.uuid4().hex}/{name}"
    dest = _blob_root() / storage_key
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as fh:
        for chunk in uploaded.chunks():
            fh.write(chunk)

    job = ComplianceJob.objects.create(
        storage_key=storage_key,
        original_name=name,
        status=ComplianceJob.Status.PENDING,
    )
    run_compliance_job.delay(str(job.id))
    return JsonResponse({"job_id": str(job.id)}, status=202)


@require_GET
def job_status(request: HttpRequest, job_id: str) -> HttpResponse:
    try:
        job = ComplianceJob.objects.get(pk=job_id)
    except ComplianceJob.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)
    progress = current_progress(job)
    return JsonResponse(
        {
            "job_id": str(job.id),
            "status": job.status,
            "phase_index": progress.index,
            "phase": progress.name,
            "phase_total": progress.total,
            "progress": progress.ratio,
            "error": job.error or None,
        },
    )


@require_GET
def job_report(request: HttpRequest, job_id: str) -> HttpResponse:
    try:
        job = ComplianceJob.objects.get(pk=job_id)
    except ComplianceJob.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)
    if job.status != ComplianceJob.Status.SUCCEEDED:
        return JsonResponse(
            {"error": "report not ready", "status": job.status},
            status=409,
        )
    kind = request.GET.get("kind", "report")
    body = job.sbom_json if kind == "sbom" else job.report_json
    return HttpResponse(body, content_type="application/json")
