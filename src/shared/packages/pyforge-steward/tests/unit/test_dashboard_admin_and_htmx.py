"""Unit tests for dashboard admin, models, htmx view, and passport sync (Story 65.1).

Self-sufficient: the two Story 48.6 consumer/routing checks at the bottom put
`django-pyforge/src` on `sys.path` and skip on a missing `django_pyforge` the
way `test_events_stream_consumer.py` does, so they pass in any collection
order. The HTMX view is exercised over FIXTURE ledgers under `tmp_path`
(`settings.PYFORGE_REPO_ROOT` / `$PYFORGE_REPO_ROOT`), never the live tree.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("django", reason="dashboard requires pyforge-steward[dashboard]")

import django  # noqa: E402
from django.conf import settings  # noqa: E402

_PKG_ROOT = Path(__file__).resolve().parents[2]
_DJANGO_PYFORGE_SRC = _PKG_ROOT.parent / "django-pyforge" / "src"
if str(_DJANGO_PYFORGE_SRC) not in sys.path:
    sys.path.insert(0, str(_DJANGO_PYFORGE_SRC))

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

assert _DASHBOARD_APP in settings.INSTALLED_APPS, (
    f"another test module configured Django settings first without {_DASHBOARD_APP!r}"
)

django.setup()

from django.core.management import call_command  # noqa: E402

call_command("migrate", run_syncdb=True, verbosity=0)

from django.contrib.admin.sites import AdminSite  # noqa: E402
from django.test import RequestFactory  # noqa: E402

from pyforge.steward.dashboard.admin import AuditEntryAdmin, WorkPassportAdmin  # noqa: E402
from pyforge.steward.dashboard.models import (  # noqa: E402
    AuditAction,
    AuditEntry,
    CorridorLoad,
    WorkPassport,
)
from pyforge.steward.dashboard.passport_sync import sync_work_passports_db  # noqa: E402
from pyforge.steward.dashboard.views_htmx import (  # noqa: E402
    backlog_htmx_view,
    shipped_htmx_view,
    standup_htmx_view,
)
from pyforge.steward.glass import EMPTY_FILE_SHA256  # noqa: E402
from pyforge.steward.sprint_ledger_query import WorkPassportItem  # noqa: E402

_EPICS_MD = """## Epic 1: Fixture Epic

### Story 1.1: Plain Done Story
**Deps:** —

### Story 1.2: <name> & friends
**Deps:** 1.1
JIRA-FIX-2 GH-22

### Story 1.3: Blocked One
**Deps:** —
"""

_LEDGER_YAML = """development_status:
  1-1-plain-done-story: done
  1-2-name-friends: backlog
  1-3-blocked-one: blocked
  epic-1: in-progress
"""


@pytest.fixture
def fixture_root(tmp_path: Path) -> Path:
    st_dir = tmp_path / "_bmad-output" / "projects" / "fixture-station" / "planning-artifacts"
    st_dir.mkdir(parents=True)
    (st_dir / "epics.md").write_text(_EPICS_MD, encoding="utf-8")
    (st_dir / "sprint-status-ledger.yaml").write_text(_LEDGER_YAML, encoding="utf-8")
    return tmp_path


@pytest.fixture
def env_root(fixture_root: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("PYFORGE_REPO_ROOT", str(fixture_root))
    return fixture_root


@pytest.fixture(autouse=True)
def _clean_db():
    WorkPassport.objects.all().delete()
    AuditEntry.objects.all().delete()
    CorridorLoad.objects.all().delete()
    yield
    WorkPassport.objects.all().delete()
    AuditEntry.objects.all().delete()
    CorridorLoad.objects.all().delete()


def _create_corridor_row(
    *, waybill: str, batch_sha: str, direction: str = "inbound", days_ago: int = 0
) -> CorridorLoad:
    """Story 61.3 fixture helper: `loaded_at` is `auto_now_add`, so an
    "earlier day" row needs a queryset-level `.update()` (bypasses
    `auto_now_add`'s save-time behavior), mirroring `test_glass.py`."""
    from datetime import datetime, timedelta, timezone

    row = CorridorLoad.objects.create(direction=direction, batch_sha=batch_sha, waybill=waybill, transport="app-upload")
    if days_ago:
        earlier = datetime.now(timezone.utc) - timedelta(days=days_ago)
        CorridorLoad.objects.filter(pk=row.pk).update(loaded_at=earlier)
        row.refresh_from_db()
    return row


def _story(**overrides) -> WorkPassportItem:
    base = dict(
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
    base.update(overrides)
    return WorkPassportItem(**base)


# --- models + admin ---


def test_work_passport_model_and_admin() -> None:
    site = AdminSite()
    wp_admin = WorkPassportAdmin(WorkPassport, site)
    audit_admin = AuditEntryAdmin(AuditEntry, site)

    assert wp_admin.list_display == (
        "passport_id",
        "station",
        "story_id",
        "status",
        "jira_key",
        "github_item_id",
        "vendor_id",
        "title",
    )
    assert wp_admin.list_filter == ("station", "status", "vendor_id")
    assert "vendor_id" in wp_admin.search_fields
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


def test_audit_entry_admin_is_read_only() -> None:
    audit_admin = AuditEntryAdmin(AuditEntry, AdminSite())
    request = RequestFactory().get("/admin/")
    assert audit_admin.has_add_permission(request) is False
    assert audit_admin.has_change_permission(request) is False
    assert audit_admin.has_change_permission(request, obj=object()) is False
    assert audit_admin.has_delete_permission(request) is False
    assert audit_admin.has_delete_permission(request, obj=object()) is False
    model_fields = {f.name for f in AuditEntry._meta.get_fields() if f.name != "id"}
    assert set(audit_admin.readonly_fields) == model_fields


# --- HTMX view ---


def test_backlog_htmx_view_renders_fixture_rows_from_the_engine(env_root: Path) -> None:
    res = backlog_htmx_view(RequestFactory().get("/dashboard/backlog/"))
    assert res.status_code == 200
    assert res["Cache-Control"] == "no-store"
    body = res.content.decode("utf-8")
    assert "Found <strong>3</strong> matching stories" in body
    assert body.count('<tr id="story-fixture-station-') == 3
    assert "Plain Done Story" in body and ">DONE<" in body and ">BLOCKED<" in body
    assert 'id="story-fixture-station-1-2"' in body


def test_backlog_htmx_view_filters_via_query_params(env_root: Path) -> None:
    factory = RequestFactory()
    res = backlog_htmx_view(
        factory.get("/dashboard/backlog/?station=fixture-station&unimplemented=true&unlinked=on&search=one")
    )
    body = res.content.decode("utf-8")
    assert res.status_code == 200
    assert "Found <strong>1</strong> matching stories" in body
    assert "Blocked One" in body and "Plain Done Story" not in body

    for truthy in ("true", "1", "on", "yes", "TRUE"):
        body = backlog_htmx_view(factory.get(f"/dashboard/backlog/?unimplemented={truthy}")).content.decode("utf-8")
        assert "Found <strong>2</strong> matching stories" in body, truthy
    for falsy in ("false", "0", "", "off", "maybe"):
        body = backlog_htmx_view(factory.get(f"/dashboard/backlog/?unimplemented={falsy}")).content.decode("utf-8")
        assert "Found <strong>3</strong> matching stories" in body, falsy


def test_backlog_htmx_view_escapes_every_interpolated_field(env_root: Path) -> None:
    body = backlog_htmx_view(RequestFactory().get("/dashboard/backlog/?search=friends")).content.decode("utf-8")
    assert "<name>" not in body
    assert "&lt;name&gt; &amp; friends" in body
    assert "FIX-2" in body and ">22<" in body


@pytest.mark.parametrize("station", ["../pyforge-steward", "a b", "x/y", "st<ation", "%2e%2e"])
def test_backlog_htmx_view_rejects_station_traversal_with_400(env_root: Path, station: str) -> None:
    from django.http import HttpResponseBadRequest

    res = backlog_htmx_view(RequestFactory().get("/dashboard/backlog/", {"station": station}))
    assert isinstance(res, HttpResponseBadRequest)
    assert res.status_code == 400
    assert not (env_root / "_bmad-output" / "projects" / station).exists()


def test_backlog_htmx_view_reads_root_from_settings_before_env(
    fixture_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    empty = tmp_path / "empty-root"
    (empty / "_bmad-output" / "projects").mkdir(parents=True)
    monkeypatch.setenv("PYFORGE_REPO_ROOT", str(empty))
    body = backlog_htmx_view(RequestFactory().get("/dashboard/backlog/")).content.decode("utf-8")
    assert "Found <strong>0</strong>" in body
    monkeypatch.setattr(settings, "PYFORGE_REPO_ROOT", str(fixture_root), raising=False)
    body = backlog_htmx_view(RequestFactory().get("/dashboard/backlog/")).content.decode("utf-8")
    assert "Found <strong>3</strong>" in body


def test_standup_and_shipped_htmx_views_render_fresh() -> None:
    _create_corridor_row(waybill="WB-FRESH", batch_sha="a" * 64)
    for view in (standup_htmx_view, shipped_htmx_view):
        res = view(RequestFactory().get("/dashboard/glass/"))
        assert res.status_code == 200
        assert res["Cache-Control"] == "no-store"
        body = res.content.decode("utf-8")
        assert ">FRESH<" in body
        assert "WB-FRESH" in body


def test_standup_and_shipped_htmx_views_render_stale() -> None:
    _create_corridor_row(waybill="WB-STALE", batch_sha="b" * 64, days_ago=2)
    for view in (standup_htmx_view, shipped_htmx_view):
        body = view(RequestFactory().get("/dashboard/glass/")).content.decode("utf-8")
        assert ">STALE<" in body
        assert "WB-STALE" in body


def test_standup_and_shipped_htmx_views_render_failed() -> None:
    _create_corridor_row(waybill="WB-EMPTY", batch_sha=EMPTY_FILE_SHA256)
    for view in (standup_htmx_view, shipped_htmx_view):
        body = view(RequestFactory().get("/dashboard/glass/")).content.decode("utf-8")
        assert ">FAILED<" in body
        assert "WB-EMPTY" in body


def test_standup_and_shipped_htmx_views_render_unborn() -> None:
    for view in (standup_htmx_view, shipped_htmx_view):
        body = view(RequestFactory().get("/dashboard/glass/")).content.decode("utf-8")
        assert ">UNBORN<" in body
        assert "Waybill: <code>-</code>" in body


def test_standup_and_shipped_htmx_views_render_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "pyforge.steward.dashboard.glass_query", None)
    for view in (standup_htmx_view, shipped_htmx_view):
        body = view(RequestFactory().get("/dashboard/glass/")).content.decode("utf-8")
        assert ">REFUSED<" in body


def test_standup_and_shipped_views_share_the_identical_inbound_reading_labels_only_differ() -> None:
    """Review pass 1 amendment (2026-09-19): both views read
    `compute_glass_reading(direction="inbound")` -- the SAME reading -- and
    differ only in their title/dom_id label text."""
    _create_corridor_row(waybill="WB-SHARED", batch_sha="c" * 64)
    standup_body = standup_htmx_view(RequestFactory().get("/dashboard/glass/")).content.decode("utf-8")
    shipped_body = shipped_htmx_view(RequestFactory().get("/dashboard/glass/")).content.decode("utf-8")

    for body in (standup_body, shipped_body):
        assert "WB-SHARED" in body
        assert ">FRESH<" in body

    assert "Standup — any news from the vendor?" in standup_body
    assert 'id="glass-standup"' in standup_body
    assert "Shipped — what testers can currently rely on" in shipped_body
    assert 'id="glass-shipped"' in shipped_body


def test_backlog_htmx_view_records_one_load_audit_row(env_root: Path) -> None:
    req = RequestFactory().get("/dashboard/backlog/?unimplemented=true")
    req.scope = {"dashboard_identity": "alice", "dashboard_role": "ops"}
    backlog_htmx_view(req)
    entry = AuditEntry.objects.get()
    assert (entry.actor, entry.role, entry.action, entry.target, entry.row_count) == (
        "alice",
        "ops",
        AuditAction.LOAD,
        "sprint-backlog",
        2,
    )
    backlog_htmx_view(RequestFactory().get("/dashboard/backlog/"))
    anonymous = AuditEntry.objects.order_by("-id").first()
    assert (anonymous.actor, anonymous.role, anonymous.row_count) == ("anonymous", None, 3)


# --- passport sync ---


def test_sync_work_passports_db_success() -> None:
    res = sync_work_passports_db([_story()])
    assert res["status"] == "success"
    assert res["synced_count"] == 1
    assert WorkPassport.objects.filter(passport_id="test-uuid-sync-123").exists()


def test_sync_keeps_existing_aliases_when_the_ledger_carries_none() -> None:
    WorkPassport.objects.create(
        passport_id="p-1",
        story_id="1.1",
        station="s",
        epic_id="1",
        title="T",
        status="backlog",
        jira_key="ADMIN-7",
        github_item_id="4242",
    )
    res = sync_work_passports_db(
        [
            _story(
                passport_id="p-1",
                story_id="1.1",
                station="s",
                epic_id="1",
                title="T renamed",
                status="done",
                jira_key=None,
                github_item_id=None,
            )
        ]
    )
    assert res["status"] == "success"
    row = WorkPassport.objects.get(passport_id="p-1")
    assert (row.jira_key, row.github_item_id) == ("ADMIN-7", "4242")
    assert (row.title, row.status) == ("T renamed", "done")

    sync_work_passports_db(
        [
            _story(
                passport_id="p-1",
                story_id="1.1",
                station="s",
                epic_id="1",
                title="T",
                status="done",
                jira_key="LEDGER-1",
                github_item_id=None,
            )
        ]
    )
    row.refresh_from_db()
    assert (row.jira_key, row.github_item_id) == ("LEDGER-1", "4242")


def test_sync_reports_a_data_error_instead_of_a_fallback_payload() -> None:
    res = sync_work_passports_db([_story(story_id=None)])
    assert res["status"] == "error"
    assert "IntegrityError" in res["message"]
    assert "passports" not in res


def test_sync_refuses_when_django_settings_are_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    from django.conf import LazySettings

    monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)
    monkeypatch.setattr(LazySettings, "configured", property(lambda self: False))
    res = sync_work_passports_db([_story()])
    assert res["status"] == "refused"
    assert "DJANGO_SETTINGS_MODULE" in res["message"]
    assert not WorkPassport.objects.filter(passport_id="test-uuid-sync-123").exists()


def test_sync_falls_back_when_the_orm_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    from django.db import OperationalError

    monkeypatch.setattr(
        "pyforge.steward.dashboard.models.WorkPassport.objects.update_or_create",
        lambda *a, **k: (_ for _ in ()).throw(OperationalError("no such table")),
    )
    res = sync_work_passports_db([_story()])
    assert res["status"] == "fallback_payload"
    assert res["passports"] == ["test-uuid-sync-123"]
    assert "OperationalError" in res["message"]


# --- Story 48.6 surfaces (self-sufficient: sys.path + importorskip above) ---


def test_dashboard_asgi_and_routing() -> None:
    pytest.importorskip("channels")
    pytest.importorskip("django_pyforge")
    from pyforge.steward.dashboard import asgi, routing

    assert asgi.application is not None
    assert len(routing.websocket_urlpatterns) == 1


def test_dashboard_consumers_helpers() -> None:
    pytest.importorskip("channels")
    pytest.importorskip("django_pyforge")
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
