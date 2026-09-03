"""HTTP face: upload + job status/results (Stories 8.1 / 8.2)."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from django.conf import settings
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.http import HttpResponseNotFound
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST
from django_pyforge.access import require_station_role
from django_pyforge.assertion.client import PortalClient
from django_pyforge.assertion.schema import CLAIM_SUB
from django_pyforge.non_atomic import non_atomic_view
from django_pyforge.roles import claims_from_request
from django_pyforge.roles import roles_from_request
from django_pyforge.supervisor import HandleExpiredError
from django_pyforge.supervisor import HandleNotFoundError
from django_pyforge.supervisor import HandleRefusedError
from django_pyforge.supervisor import RunBoundExceeded
from django_pyforge.supervisor import bound_refusal_payload

from .mcp_asgi import RUN_AUDIT_TOOL
from .mcp_asgi import WARDEN_STATION
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


def _portal_identity(request: HttpRequest) -> tuple[str, list[str]] | None:
    claims = claims_from_request(request) or {}
    sub = claims.get(CLAIM_SUB)
    if not isinstance(sub, str) or not sub:
        return None
    return sub, list(roles_from_request(request))


@require_GET
@require_station_role("warden")
def chrome_home(request: HttpRequest) -> HttpResponse:
    """HTML face that extends django-pyforge chrome (Story 18.1)."""
    return render(request, "warden_fabric/chrome.html")


@require_POST
@require_station_role("warden")
def start_audit(request: HttpRequest) -> HttpResponse:
    """HTMX start: PortalClient only — never a raw HTTP MCP call."""
    identity = _portal_identity(request)
    if identity is None:
        return HttpResponseForbidden()
    sub, roles = identity
    target = request.POST.get("target", ".")
    if not isinstance(target, str) or not target.strip():
        target = "."
    else:
        target = target.strip()
    try:
        handle = PortalClient().start(
            station=WARDEN_STATION,
            sub=sub,
            roles=roles,
            tool=RUN_AUDIT_TOOL,
            payload={"target": target},
        )
    except RunBoundExceeded as exc:
        # Story 42.2: the bound decides the status, not this view, and the body
        # is `bound_refusal_payload` -- the SAME projection the MCP `start`
        # tools carry -- so the two faces refuse one condition identically
        # rather than each describing it their own way.
        return JsonResponse(
            bound_refusal_payload(exc),
            status=int(exc.status),
            headers=exc.headers(),
        )
    return render(request, "warden_fabric/audit_started.html", {"handle": handle})


@require_GET
@require_station_role("warden")
@non_atomic_view
def get_audit(request: HttpRequest) -> HttpResponse:
    """HTMX get after disconnect: same run, new assertion, no recompute."""
    identity = _portal_identity(request)
    if identity is None:
        return HttpResponseForbidden()
    sub, roles = identity
    handle = request.GET.get("handle", "")
    try:
        run = PortalClient().get(
            station=WARDEN_STATION,
            handle=handle,
            sub=sub,
            roles=roles,
        )
    except HandleRefusedError:
        return HttpResponseForbidden()
    except HandleNotFoundError:
        return HttpResponseNotFound()
    except HandleExpiredError:
        return HttpResponse(status=410)
    return render(
        request,
        "warden_fabric/audit_status.html",
        {"handle": handle, "run": run},
    )


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
