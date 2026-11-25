"""Warden Story 29.1: an unscannable upload fails, and the job leaves no blob behind.

The upload admits only the names warden's discovery reads under the current flags
(warden's own accessor, never a second list), a job whose scan read no manifest
ends FAILED, ``?kind=sbom`` is the scan's own SBOM or a 404, and the
stored blob is removed when the job ends, succeeded or failed.
"""

from __future__ import annotations

import json
import shutil
from http import HTTPStatus
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django_pyforge.roles import IDP_TOKEN_CLAIMS_SESSION_KEY
from django_warden_fabric import tasks
from django_warden_fabric import views
from django_warden_fabric.models import ComplianceJob
from django_warden_fabric.tasks import run_compliance_job

UPLOAD_URL = "/stations/warden/upload/"
WARDEN_ROLE = "pyforge:station:warden"
_ENGINES = "django_warden_fabric.tasks._run_warden_engines"
_REPO_ROOT = Path(__file__).resolve().parents[2]
_CLEAN_PYPROJECT = (
    _REPO_ROOT
    / "shared"
    / "packages"
    / "pyforge-warden"
    / "tests"
    / "fixtures"
    / "projects"
    / "clean"
    / "pyproject.toml"
)
# What ``warden scan --format json`` prints for a directory with no manifest it reads.
_NOT_APPLICABLE_REPORT = json.dumps(
    {
        "exit_code": 0,
        "findings": [],
        "resolved_scan_set": [],
        "status": {"driver": None, "value": "not-applicable"},
    },
)
_SCANNED_REPORT = json.dumps(
    {
        "exit_code": 0,
        "findings": [],
        "resolved_scan_set": [{"kind": "pixi.lock", "path": "pixi.lock"}],
        "status": {"driver": None, "value": "clean"},
    },
)
_SBOM = json.dumps({"bomFormat": "CycloneDX", "components": []})
_FLAGS_JSON = Path(__file__).resolve().parents[1] / "config" / "flags.json"
_NON_PYTHON_FLAG = "pyforge.warden.non_python_ecosystems"


def _set_non_python_lockfiles(tmp_path: Path, monkeypatch, *, enabled: bool) -> None:
    """Point the flag tree at a copy of the shipped one, the lockfile flag set."""
    tree = json.loads(_FLAGS_JSON.read_text(encoding="utf-8"))
    tree["flags"][_NON_PYTHON_FLAG]["defaultVariant"] = "on" if enabled else "off"
    path = tmp_path / f"flags-{enabled}.json"
    path.write_text(json.dumps(tree), encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(path))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")


@pytest.fixture(autouse=True)
def _non_python_lockfiles_off(tmp_path: Path, monkeypatch) -> None:
    """The shipped default, pinned: a test that needs the flag on sets it itself."""
    _set_non_python_lockfiles(tmp_path, monkeypatch, enabled=False)


def _authed(client, settings):
    claims = {"sub": "op-1", "groups": [WARDEN_ROLE]}
    settings.IDP_CLAIMS_SNAPSHOT = claims
    session = client.session
    session[IDP_TOKEN_CLAIMS_SESSION_KEY] = claims
    session.save()
    return client


@pytest.fixture
def blob_root(settings, tmp_path: Path) -> Path:
    root = tmp_path / "blobs"
    root.mkdir()
    settings.COMPLIANCE_FACE_BLOB_ROOT = str(root)
    return root


def _stored_job(
    blob_root: Path, name: str, body: bytes = b"version: 6\n"
) -> ComplianceJob:
    """A job as the upload view leaves it: one blob in its own directory."""
    storage_key = f"0123456789abcdef/{name}"
    blob = blob_root / storage_key
    blob.parent.mkdir(parents=True)
    blob.write_bytes(body)
    return ComplianceJob.objects.create(
        storage_key=storage_key,
        original_name=name,
        status=ComplianceJob.Status.PENDING,
    )


class _Engines:
    """The scan seam: one canned ``(report, sbom, exit)``, every call recorded."""

    def __init__(self, report: str, sbom: str = "", exit_code: int = 0) -> None:
        self.result = (report, sbom, exit_code)
        self.targets: list[Path] = []

    def __call__(self, target: Path, **_kwargs: object) -> tuple[str, str, int]:
        # The blob is still there while the scan reads it.
        assert any(target.iterdir())
        self.targets.append(target)
        return self.result


@pytest.mark.django_db
@pytest.mark.parametrize(
    "name",
    ["requirements.txt", "notes.txt", "settings.json", "other.toml", "poetry.lock"],
)
def test_upload_of_a_name_discovery_does_not_read_is_refused(
    client,
    settings,
    blob_root: Path,
    monkeypatch,
    name: str,
):
    """A listed suffix is not enough: only a name discovery reads is admitted."""
    enqueued: list[str] = []
    monkeypatch.setattr(views.run_compliance_job, "delay", enqueued.append)
    _authed(client, settings)
    upload = SimpleUploadedFile(name, b"requests==2.31.0\n")
    response = client.post(UPLOAD_URL, {"manifest": upload})
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert name in response.json()["error"]
    assert not ComplianceJob.objects.exists()
    assert enqueued == []
    assert list(blob_root.iterdir()) == []


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["pyproject.toml", "pixi.lock", "environment.yml"])
def test_upload_of_a_name_discovery_reads_is_accepted(
    client,
    settings,
    blob_root: Path,
    monkeypatch,
    name: str,
):
    enqueued: list[str] = []
    monkeypatch.setattr(views.run_compliance_job, "delay", enqueued.append)
    _authed(client, settings)
    response = client.post(UPLOAD_URL, {"manifest": SimpleUploadedFile(name, b"x")})
    assert response.status_code == HTTPStatus.ACCEPTED, response.content
    assert enqueued == [str(ComplianceJob.objects.get().id)]


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["package-lock.json", "go.mod", "Cargo.lock"])
def test_upload_of_a_native_lockfile_follows_the_flag(
    client,
    settings,
    blob_root: Path,
    monkeypatch,
    name: str,
):
    """A non-Python lockfile is admitted only while the flag has discovery read it."""
    enqueued: list[str] = []
    monkeypatch.setattr(views.run_compliance_job, "delay", enqueued.append)
    _authed(client, settings)
    refused = client.post(UPLOAD_URL, {"manifest": SimpleUploadedFile(name, b"{}")})
    assert refused.status_code == HTTPStatus.BAD_REQUEST, refused.content
    assert enqueued == []
    assert list(blob_root.iterdir()) == []

    _set_non_python_lockfiles(blob_root.parent, monkeypatch, enabled=True)
    accepted = client.post(UPLOAD_URL, {"manifest": SimpleUploadedFile(name, b"{}")})
    assert accepted.status_code == HTTPStatus.ACCEPTED, accepted.content
    assert enqueued == [str(ComplianceJob.objects.get().id)]


@pytest.mark.django_db
def test_job_whose_scan_read_no_manifest_fails(client, settings, blob_root: Path):
    """A scan that read nothing says nothing about the upload: the job is FAILED."""
    job = _stored_job(blob_root, "pixi.lock")
    engines = _Engines(_NOT_APPLICABLE_REPORT)
    with patch(_ENGINES, engines), pytest.raises(ValueError, match="no manifest"):
        run_compliance_job(str(job.id))
    assert len(engines.targets) == 1
    job.refresh_from_db()
    assert job.status == ComplianceJob.Status.FAILED
    assert "no manifest" in job.error
    _authed(client, settings)
    report = client.get(f"/stations/warden/jobs/{job.id}/report/")
    assert report.status_code == HTTPStatus.CONFLICT


@pytest.mark.django_db
def test_job_on_a_name_discovery_does_not_read_is_refused_before_any_scan(
    blob_root: Path,
):
    """A blob stored under an unread name is refused at validation; no scan runs."""
    job = _stored_job(blob_root, "requirements.txt", b"requests==2.31.0\n")
    engines = _Engines(_SCANNED_REPORT)
    with (
        patch(_ENGINES, engines),
        pytest.raises(ValueError, match="unsupported manifest"),
    ):
        run_compliance_job(str(job.id))
    assert engines.targets == []
    job.refresh_from_db()
    assert job.status == ComplianceJob.Status.FAILED
    assert "unsupported manifest: requirements.txt" in job.error
    assert job.report_json == ""


@pytest.mark.django_db
def test_job_whose_real_scan_reads_no_manifest_fails(blob_root: Path, monkeypatch):
    """The real ``warden scan``, no engine stub: an unread file is an empty scan set.

    Only the job's own name check is opened (the flag was on at upload and is off
    now): ``package-lock.json`` is stored, the flag is off, discovery reads nothing."""
    monkeypatch.setattr(
        tasks,
        "supported_manifest_names",
        lambda: frozenset({"package-lock.json"}),
    )
    job = _stored_job(blob_root, "package-lock.json", b"{}")
    with pytest.raises(ValueError, match="no manifest"):
        run_compliance_job(str(job.id))
    job.refresh_from_db()
    assert job.status == ComplianceJob.Status.FAILED
    assert "read no manifest" in job.error
    assert job.report_json == ""
    assert job.sbom_json == ""
    assert list(blob_root.iterdir()) == []


@pytest.mark.django_db
def test_sbom_kind_is_the_engine_sbom_or_404(client, settings, blob_root: Path):
    """``?kind=sbom`` answers with the scan's own SBOM, and 404 when there is none."""
    _authed(client, settings)
    with_sbom = _stored_job(blob_root, "pixi.lock")
    with patch(_ENGINES, _Engines(_SCANNED_REPORT, _SBOM)):
        run_compliance_job(str(with_sbom.id))
    response = client.get(f"/stations/warden/jobs/{with_sbom.id}/report/?kind=sbom")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == json.loads(_SBOM)

    for stored in ("", "{}"):
        without = ComplianceJob.objects.create(
            storage_key=f"none-{len(stored)}/pixi.lock",
            original_name="pixi.lock",
            status=ComplianceJob.Status.SUCCEEDED,
            report_json=_SCANNED_REPORT,
            sbom_json=stored,
        )
        url = f"/stations/warden/jobs/{without.id}/report/"
        assert client.get(f"{url}?kind=sbom").status_code == HTTPStatus.NOT_FOUND
        assert client.get(url).status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_a_real_scan_stores_its_own_sbom(client, settings, blob_root: Path):
    """End to end, no stub: the job asks ``warden scan`` for its CycloneDX document."""
    job = _stored_job(blob_root, "pyproject.toml")
    shutil.copyfile(_CLEAN_PYPROJECT, blob_root / job.storage_key)
    run_compliance_job(str(job.id))
    job.refresh_from_db()
    assert job.status == ComplianceJob.Status.SUCCEEDED
    assert json.loads(job.report_json)["resolved_scan_set"]
    _authed(client, settings)
    response = client.get(f"/stations/warden/jobs/{job.id}/report/?kind=sbom")
    assert response.status_code == HTTPStatus.OK
    assert response.json()["bomFormat"] == "CycloneDX"


@pytest.mark.django_db
def test_blob_is_removed_after_a_succeeded_job(blob_root: Path):
    job = _stored_job(blob_root, "pixi.lock")
    with patch(_ENGINES, _Engines(_SCANNED_REPORT, _SBOM)):
        run_compliance_job(str(job.id))
    job.refresh_from_db()
    assert job.status == ComplianceJob.Status.SUCCEEDED
    assert list(blob_root.iterdir()) == []


@pytest.mark.django_db
def test_blob_is_removed_after_a_failed_job(blob_root: Path):
    job = _stored_job(blob_root, "pixi.lock")
    engines = _Engines(_SCANNED_REPORT)
    engines.result = None  # type: ignore[assignment]  # unpacking it raises in the job
    with patch(_ENGINES, engines), pytest.raises(TypeError):
        run_compliance_job(str(job.id))
    job.refresh_from_db()
    assert job.status == ComplianceJob.Status.FAILED
    assert list(blob_root.iterdir()) == []


@pytest.mark.django_db
def test_blob_removal_never_leaves_the_blob_root(settings, tmp_path: Path):
    """A key outside the root, or naming a file directly in it, removes no directory."""
    root = tmp_path / "blobs"
    sibling = tmp_path / "blobs-other"
    for directory in (root, sibling):
        directory.mkdir()
    (sibling / "pixi.lock").write_bytes(b"x")
    (root / "keep.txt").write_bytes(b"x")
    (root / "pixi.lock").write_bytes(b"x")
    settings.COMPLIANCE_FACE_BLOB_ROOT = str(root)
    outside = ComplianceJob.objects.create(
        storage_key="../blobs-other/pixi.lock",
        original_name="pixi.lock",
    )
    with patch(_ENGINES, _Engines(_SCANNED_REPORT)):
        run_compliance_job(str(outside.id))
        flat = ComplianceJob.objects.create(
            storage_key="pixi.lock", original_name="pixi.lock"
        )
        run_compliance_job(str(flat.id))
    assert (sibling / "pixi.lock").is_file()
    assert sorted(path.name for path in root.iterdir()) == ["keep.txt"]
