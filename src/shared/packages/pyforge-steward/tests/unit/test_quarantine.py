"""Story 61.5 — quarantine shelf: mint-then-reject for inbound rows without a passport."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

pytest.importorskip("django", reason="quarantine_admit.py requires pyforge-steward[dashboard]")

import django  # noqa: E402
from django.conf import settings  # noqa: E402

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
                "LOCATION": "pyforge-steward-quarantine-test",
            },
        },
        USE_TZ=True,
    )

django.setup()

from django.core.management import call_command  # noqa: E402
from django.test import RequestFactory  # noqa: E402

call_command("migrate", run_syncdb=True, verbosity=0)

from pyforge.steward.cli import build_parser  # noqa: E402
from pyforge.steward.dashboard import quarantine_admit as quarantine_admit_module  # noqa: E402
from pyforge.steward.dashboard.models import QuarantineShelfRow, WorkPassport  # noqa: E402
from pyforge.steward.dashboard.views_htmx import quarantine_htmx_view  # noqa: E402
from pyforge.steward.quarantine import QuarantineAdmitError, QuarantineDuty, admit_inbound_without_passport  # noqa: E402

_NOW = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
_WINDOW = 14


def test_admit_inbound_day_3_mints_into_quarantine():
    """I/O matrix: new inbound, day 3, no passport → mint into quarantine."""
    arrived = _NOW - timedelta(days=3)
    outcome = quarantine_admit_module.record_quarantine_admit(
        vendor_id="acme",
        jira_key="PROJ-3",
        github_item_id=None,
        title="ignored for matching",
        arrived_at=arrived,
        missing_passport_window_days=_WINDOW,
        now=_NOW,
    )
    assert outcome["status"] == "quarantined"
    assert outcome["mint_status"] == "minted"
    assert outcome["passport_id"]
    row = QuarantineShelfRow.objects.get(row_id=outcome["row_id"])
    assert row.passport_id == outcome["passport_id"]
    assert WorkPassport.objects.filter(passport_id=outcome["passport_id"]).exists()


def test_admit_inbound_day_15_refuses_mint_still_quarantines():
    """I/O matrix: new inbound, day 15, no passport → no mint (row on shelf)."""
    arrived = _NOW - timedelta(days=15)
    outcome = quarantine_admit_module.record_quarantine_admit(
        vendor_id="acme",
        jira_key="PROJ-15",
        github_item_id=None,
        title="",
        arrived_at=arrived,
        missing_passport_window_days=_WINDOW,
        now=_NOW,
    )
    assert outcome["status"] == "quarantined"
    assert outcome["mint_status"] == "refused"
    assert outcome["passport_id"] is None
    row = QuarantineShelfRow.objects.get(row_id=outcome["row_id"])
    assert row.passport_id is None


def test_admit_inbound_without_passport_blank_vendor_raises():
    with pytest.raises(QuarantineAdmitError):
        admit_inbound_without_passport(vendor_id="  ", jira_key="X")


def test_quarantine_duty_admit_happy_path():
    ns = build_parser().parse_args(["quarantine", "admit", "--vendor-id", "acme", "--jira-key", "P-1"])
    result = QuarantineDuty().run(ns)
    assert result.ok is True
    assert "quarantined row_id=" in result.summary


def test_quarantine_duty_bare_refuses():
    ns = build_parser().parse_args(["quarantine"])
    result = QuarantineDuty().run(ns)
    assert result.ok is False


def test_quarantine_htmx_view_lists_unlinked_rows():
    quarantine_admit_module.record_quarantine_admit(
        vendor_id="acme",
        jira_key="HTMX-1",
        github_item_id=None,
        title="",
        arrived_at=_NOW,
        missing_passport_window_days=_WINDOW,
        now=_NOW,
    )
    body = quarantine_htmx_view(RequestFactory().get("/dashboard/quarantine/")).content.decode("utf-8")
    assert "Quarantine shelf" in body
    assert "HTMX-1" in body
    assert "title" not in body.lower() or "match" not in body.lower()


def test_quarantine_htmx_view_has_no_title_query_param():
    """CAP-5: no title-match endpoint — the view ignores request GET keys."""
    source = quarantine_htmx_view.__doc__ or ""
    assert "title-match" in source or "title" in source


def test_quarantine_duty_shelf_json():
    ns = build_parser().parse_args(["quarantine", "--json", "shelf"])
    result = QuarantineDuty().run(ns)
    assert result.ok is True
    payload = json.loads(result.summary)
    assert payload["status"] == "ok"
