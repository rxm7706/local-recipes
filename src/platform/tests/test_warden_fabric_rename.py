"""Story 19.1: warden portal rename, prefix redirect, app-label survival."""

from __future__ import annotations

import importlib.util
import re
from http import HTTPStatus
from pathlib import Path

import pytest
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.urls import resolve
from django_warden_fabric.models import ComplianceJob

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLATFORM_ROOT.parents[1]
SRC_ROOT = REPO_ROOT / "src"
_MIG_PATH = (
    REPO_ROOT
    / "src"
    / "shared"
    / "packages"
    / "django-warden"
    / "src"
    / "django_warden_fabric"
    / "migrations"
    / "0001_initial.py"
)
_spec = importlib.util.spec_from_file_location("warden_fabric_0001", _MIG_PATH)
assert _spec is not None
assert _spec.loader is not None
_mig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mig)
NEW_TABLE = _mig.NEW_TABLE
OLD_TABLE = _mig.OLD_TABLE
LEGACY_APP_LABEL = _mig.LEGACY_APP_LABEL
forwards = _mig.forwards
_LEGACY_TOKEN = "_".join(("compliance", "face"))  # noqa: FLY002
IDENTIFIER = re.compile(rf"\b{_LEGACY_TOKEN}\b")
_TEXT_SUFFIXES = {
    ".py",
    ".html",
    ".toml",
    ".yml",
    ".yaml",
    ".txt",
    ".md",
    ".css",
    ".js",
}
_SKIP_PARTS = {".pyc", "__pycache__", ".git"}


@pytest.mark.django_db
def test_prefix_get_preserves_path_and_query(client) -> None:
    response = client.get("/compliance/upload/?kind=sbom")
    assert response.status_code == HTTPStatus.PERMANENT_REDIRECT
    assert response["Location"] == "/stations/warden/upload/?kind=sbom"


@pytest.mark.django_db
def test_prefix_post_is_method_preserving(client) -> None:
    response = client.post("/compliance/upload/")
    assert response.status_code == HTTPStatus.PERMANENT_REDIRECT
    assert response["Location"] == "/stations/warden/upload/"


@pytest.mark.django_db
def test_chrome_and_json_mount_under_stations_warden() -> None:
    assert resolve("/stations/warden/").func.__name__ == "chrome_home"
    assert resolve("/stations/warden/upload/").func.__name__ == "upload_manifest"
    cfg = apps.get_app_config("warden_fabric")
    assert cfg.name == "django_warden_fabric"
    assert cfg.label == "warden_fabric"
    assert ComplianceJob._meta.db_table == NEW_TABLE  # noqa: SLF001


def test_no_legacy_app_identifier_under_src() -> None:
    offenders: list[str] = []
    for path in SRC_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _SKIP_PARTS for part in path.parts):
            continue
        if path.suffix not in _TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if IDENTIFIER.search(text):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == [], "legacy identifier remains: " + ", ".join(offenders)


@pytest.mark.django_db
def test_populated_relabel_keeps_job_and_history() -> None:
    job = ComplianceJob.objects.create(
        storage_key="keep/me.txt",
        original_name="me.txt",
        status=ComplianceJob.Status.PENDING,
    )
    job_id = job.id
    ContentType.objects.get_or_create(
        app_label=LEGACY_APP_LABEL,
        model="compliancejob",
    )
    recorder = MigrationRecorder(connection)
    recorder.record_applied(LEGACY_APP_LABEL, "0001_initial")
    qn = connection.ops.quote_name
    with connection.cursor() as cursor:
        cursor.execute(f"ALTER TABLE {qn(NEW_TABLE)} RENAME TO {qn(OLD_TABLE)}")
    with connection.schema_editor() as schema_editor:
        forwards(apps, schema_editor)
    surviving = ComplianceJob.objects.get(pk=job_id)
    assert surviving.original_name == "me.txt"
    assert surviving._meta.db_table == NEW_TABLE  # noqa: SLF001
    assert not ContentType.objects.filter(app_label=LEGACY_APP_LABEL).exists()
    assert ContentType.objects.filter(
        app_label="warden_fabric",
        model="compliancejob",
    ).exists()
    applied = recorder.applied_migrations()
    assert (LEGACY_APP_LABEL, "0001_initial") in applied
    assert ("warden_fabric", "0001_initial") in applied
    names = set(connection.introspection.table_names())
    assert NEW_TABLE in names
    assert OLD_TABLE not in names


def test_distribution_name_is_django_warden() -> None:
    text = (
        REPO_ROOT / "src" / "shared" / "packages" / "django-warden" / "pyproject.toml"
    ).read_text(encoding="utf-8")
    assert 'name = "django-warden"' in text


def test_warden_planning_artifacts_still_resolve() -> None:
    specs = (
        REPO_ROOT
        / "_bmad-output"
        / "projects"
        / "pyforge-warden"
        / "planning-artifacts"
        / "specs"
    )
    readme = specs / "README.md"
    eight_one = specs / "spec-8-1-upload-runs-the-real-engines-async.md"
    eight_two = specs / "spec-8-2-results-render-with-derived-progress.md"
    assert eight_one.is_file()
    assert eight_two.is_file()
    body = readme.read_text(encoding="utf-8")
    assert "django-warden" in body
    assert "django_warden_fabric" in body
    assert "warden_fabric" in body
    assert _LEGACY_TOKEN in body
    assert _LEGACY_TOKEN in eight_one.read_text(encoding="utf-8")
    assert _LEGACY_TOKEN in eight_two.read_text(encoding="utf-8")
