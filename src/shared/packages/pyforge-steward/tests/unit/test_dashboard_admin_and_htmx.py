"""Unit tests for dashboard admin, models, htmx views, and passport sync (Story 63.5)."""

from __future__ import annotations

import pytest

pytest.importorskip("django", reason="dashboard requires pyforge-steward[dashboard]")

import django
from django.conf import settings

_DASHBOARD_APP = "pyforge.steward.dashboard"

if not settings.configured:
    settings.configure(
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "django.contrib.admin",
            _DASHBOARD_APP,
        ],
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "pyforge-steward-dashboard-test",
            },
        },
        USE_TZ=True,
    )

django.setup()

from django.core.management import call_command
call_command("migrate", run_syncdb=True, verbosity=0)

from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory
from pyforge.steward.dashboard.admin import AuditEntryAdmin, WorkPassportAdmin
from pyforge.steward.dashboard.models import AuditEntry, WorkPassport
from pyforge.steward.dashboard.passport_sync import sync_work_passports_db
from pyforge.steward.dashboard.views_htmx import backlog_htmx_view
from pyforge.steward.sprint_ledger_query import WorkPassportItem


@pytest.fixture(autouse=True)
def _clean_db():
    WorkPassport.objects.all().delete()
    yield
    WorkPassport.objects.all().delete()


def test_work_passport_model_and_admin() -> None:
    site = AdminSite()
    wp_admin = WorkPassportAdmin(WorkPassport, site)
    audit_admin = AuditEntryAdmin(AuditEntry, site)

    assert wp_admin.list_display == ("passport_id", "station", "story_id", "status", "jira_key", "github_item_id", "title")
    assert audit_admin.list_display == ("actor", "role", "action", "target", "row_count", "occurred_at")

    passport = WorkPassport.objects.create(
        passport_id="test-uuid-12345678",
        story_id="63.5",
        station="pyforge-steward",
        epic_id="63",
        title="Test Title",
        status="done",
        jira_key="JIRA-100",
        github_item_id="GH-200",
        effort="L",
    )
    assert str(passport) == "pyforge-steward:63.5 (test-uui)"


def test_backlog_htmx_view_response() -> None:
    factory = RequestFactory()
    req = factory.get("/dashboard/backlog/?station=pyforge-steward&unimplemented=true&unlinked=true&search=Test")
    res = backlog_htmx_view(req)
    assert res.status_code == 200
    assert b"Found" in res.content

    # Test status badges rendering
    req_all = factory.get("/dashboard/backlog/")
    res_all = backlog_htmx_view(req_all)
    assert res_all.status_code == 200
    assert b"BACKLOG" in res_all.content or b"DONE" in res_all.content or b"Found" in res_all.content


def test_sync_work_passports_db_success() -> None:
    story = WorkPassportItem(
        passport_id="test-uuid-sync-123",
        story_id="63.5",
        station="pyforge-steward",
        epic_id="63",
        title="Sync Story",
        status="done",
        jira_key="JIRA-55",
        github_item_id="GH-99",
        effort="M",
    )
    res = sync_work_passports_db([story])
    assert res["status"] == "success"
    assert res["synced_count"] == 1
    assert WorkPassport.objects.filter(passport_id="test-uuid-sync-123").exists()


def test_dashboard_asgi_and_routing() -> None:
    pytest.importorskip("channels")
    from pyforge.steward.dashboard import asgi, routing
    assert asgi.application is not None
    assert len(routing.websocket_urlpatterns) == 1


def test_dashboard_consumers_helpers() -> None:
    pytest.importorskip("channels")
    from pyforge.steward.dashboard.consumers import (
        EventsStreamConsumer,
        _assertion_public_pem,
        _broker_url,
        _token_from_scope,
    )
    assert _token_from_scope({"query_string": b"token=secret123"}) == "secret123"
    assert _token_from_scope({"query_string": "token=secret456"}) == "secret456"
    assert _token_from_scope({}) is None
    assert _token_from_scope({"query_string": b"foo=bar"}) is None

    assert isinstance(_assertion_public_pem(), str)
    assert isinstance(_broker_url(), str)

    consumer = EventsStreamConsumer()
    assert consumer._subject is None

