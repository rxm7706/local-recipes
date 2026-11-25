"""Warden Story 28.1: the upload and the job views answer only to the warden role."""

from __future__ import annotations

from http import HTTPStatus

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django_pyforge.roles import IDP_TOKEN_CLAIMS_SESSION_KEY
from django_warden_fabric import views
from django_warden_fabric.models import ComplianceJob

UPLOAD_URL = "/stations/warden/upload/"
WARDEN_ROLE = "pyforge:station:warden"


def _claims(sub: str, *roles: str) -> dict[str, object]:
    return {"sub": sub, "groups": list(roles)}


def _authed(client: Client, settings, *, role: str = WARDEN_ROLE) -> Client:
    settings.IDP_CLAIMS_SNAPSHOT = _claims("op-1", role)
    session = client.session
    session[IDP_TOKEN_CLAIMS_SESSION_KEY] = _claims("op-1", role)
    session.save()
    return client


def _manifest(
    name: str = "pixi.lock", body: bytes = b"version: 6\n"
) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, body, content_type="application/octet-stream")


@pytest.fixture
def enqueued(monkeypatch, settings, tmp_path) -> list[str]:
    """Blobs land under tmp_path and the Celery enqueue is recorded, never run."""
    settings.COMPLIANCE_FACE_BLOB_ROOT = str(tmp_path)
    calls: list[str] = []
    monkeypatch.setattr(views.run_compliance_job, "delay", calls.append)
    return calls


def _job() -> ComplianceJob:
    return ComplianceJob.objects.create(
        storage_key="k/pixi.lock",
        original_name="pixi.lock",
        status=ComplianceJob.Status.SUCCEEDED,
        report_json='{"status": "clean"}',
        sbom_json="{}",
    )


@pytest.mark.django_db
def test_anonymous_upload_is_refused_and_stores_nothing(client, enqueued, tmp_path):
    response = client.post(UPLOAD_URL, {"manifest": _manifest()})
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert not ComplianceJob.objects.exists()
    assert enqueued == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.django_db
def test_upload_with_another_stations_role_is_refused(client, settings, enqueued):
    _authed(client, settings, role="pyforge:station:atlas")
    response = client.post(UPLOAD_URL, {"manifest": _manifest()})
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert not ComplianceJob.objects.exists()
    assert enqueued == []


@pytest.mark.django_db
def test_warden_role_upload_is_accepted_and_enqueued_by_key(client, settings, enqueued):
    _authed(client, settings)
    response = client.post(UPLOAD_URL, {"manifest": _manifest()})
    assert response.status_code == HTTPStatus.ACCEPTED, response.content
    job = ComplianceJob.objects.get()
    assert response.json() == {"job_id": str(job.id)}
    assert enqueued == [str(job.id)]


@pytest.mark.django_db
def test_upload_without_a_csrf_token_is_refused_when_checks_are_enforced(
    settings, enqueued
):
    """No longer csrf-exempt: a cross-site POST on a session cannot enqueue a scan."""
    strict = Client(enforce_csrf_checks=True)
    _authed(strict, settings)
    response = strict.post(UPLOAD_URL, {"manifest": _manifest()})
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert not ComplianceJob.objects.exists()
    assert enqueued == []


@pytest.mark.django_db
def test_oversized_upload_never_reaches_the_blob_root(
    client,
    settings,
    enqueued,
    tmp_path,
):
    """Inside the envelope allowance the file is parsed, then refused on its size."""
    settings.COMPLIANCE_FACE_MAX_UPLOAD_BYTES = 8
    _authed(client, settings)
    response = client.post(UPLOAD_URL, {"manifest": _manifest(body=b"x" * 9)})
    assert response.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    assert not ComplianceJob.objects.exists()
    assert enqueued == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.django_db
def test_a_body_far_over_the_limit_is_refused_before_it_is_parsed(
    client,
    settings,
    enqueued,
    monkeypatch,
    tmp_path,
):
    settings.COMPLIANCE_FACE_MAX_UPLOAD_BYTES = 8
    monkeypatch.setattr(views, "MULTIPART_ENVELOPE_ALLOWANCE", 512)
    _authed(client, settings)
    response = client.post(UPLOAD_URL, {"manifest": _manifest(body=b"x" * 4096)})
    assert response.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    assert not ComplianceJob.objects.exists()
    assert enqueued == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.django_db
@pytest.mark.parametrize("suffix", ["", "report/"])
@pytest.mark.parametrize("role", [None, "pyforge:station:atlas"])
def test_job_views_refuse_a_caller_without_the_warden_role(
    client,
    settings,
    suffix,
    role,
):
    job = _job()
    if role is not None:
        _authed(client, settings, role=role)
    response = client.get(f"/stations/warden/jobs/{job.id}/{suffix}")
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert b"clean" not in response.content


@pytest.mark.django_db
def test_job_views_answer_the_warden_role(client, settings):
    job = _job()
    _authed(client, settings)
    status = client.get(f"/stations/warden/jobs/{job.id}/")
    assert status.status_code == HTTPStatus.OK
    assert status.json()["status"] == ComplianceJob.Status.SUCCEEDED
    report = client.get(f"/stations/warden/jobs/{job.id}/report/")
    assert report.status_code == HTTPStatus.OK
    assert report.json() == {"status": "clean"}
