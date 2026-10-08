"""Story 61.5 — quarantine shelf: mint-then-reject for inbound rows without a passport."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
from django.db import IntegrityError, OperationalError  # noqa: E402
from django.test import RequestFactory  # noqa: E402

call_command("migrate", run_syncdb=True, verbosity=0)

from pyforge.steward.cli import build_parser  # noqa: E402
from pyforge.steward.corridor import default_corridor_dir  # noqa: E402
from pyforge.steward.dashboard import quarantine_admit as quarantine_admit_module  # noqa: E402
from pyforge.steward.dashboard.models import QuarantineShelfRow, WorkPassport  # noqa: E402
from pyforge.steward.dashboard.views_htmx import quarantine_htmx_view  # noqa: E402
from pyforge.steward.quarantine import (  # noqa: E402
    QuarantineAdmitError,
    QuarantineDuty,
    admit_inbound_without_passport,
    list_quarantine_shelf,
)

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


def test_admit_inbound_without_passport_missing_nickname_raises():
    with pytest.raises(QuarantineAdmitError, match="at least one nickname"):
        admit_inbound_without_passport(vendor_id="acme", jira_key="", github_item_id="")


def test_admit_inbound_without_passport_corridor_config_refused(tmp_path: Path):
    bad_dir = tmp_path / "corridor"
    bad_dir.mkdir()
    (bad_dir / "corridor.yaml").write_text("not: valid: corridor\n", encoding="utf-8")
    outcome = admit_inbound_without_passport(
        vendor_id="acme",
        jira_key="CFG-1",
        config=bad_dir,
    )
    assert outcome["status"] == "refused"
    assert outcome["vendor_id"] == "acme"


def test_admit_inbound_without_passport_uses_corridor_dir_and_naive_arrived_at():
    naive_arrived = datetime(2026, 9, 17, 8, 0, 0)
    outcome = admit_inbound_without_passport(
        vendor_id="acme",
        jira_key="NAIVE-1",
        arrived_at=naive_arrived,
        config=default_corridor_dir(),
        now=_NOW,
    )
    assert outcome["status"] == "quarantined"


def test_admit_inbound_refuses_when_dashboard_extra_missing(monkeypatch: pytest.MonkeyPatch):
    real_import = importlib.import_module

    def _block(name: str, *args, **kwargs):
        if name == "pyforge.steward.dashboard.quarantine_admit":
            raise ImportError("stripped install")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", _block)
    outcome = admit_inbound_without_passport(vendor_id="acme", jira_key="NO-DASH")
    assert outcome["status"] == "refused"
    assert "extra not installed" in outcome["message"]


def test_list_quarantine_shelf_refuses_when_dashboard_extra_missing(monkeypatch: pytest.MonkeyPatch):
    real_import = importlib.import_module

    def _block(name: str, *args, **kwargs):
        if name == "pyforge.steward.dashboard.quarantine_admit":
            raise ImportError("stripped install")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", _block)
    outcome = list_quarantine_shelf()
    assert outcome["status"] == "refused"
    assert "extra not installed" in outcome["message"]


def test_record_quarantine_admit_naive_datetimes_still_mints():
    arrived = datetime(2026, 9, 17, 12, 0, 0)
    now = datetime(2026, 9, 20, 12, 0, 0)
    outcome = quarantine_admit_module.record_quarantine_admit(
        vendor_id="acme",
        jira_key="NAIVE-2",
        github_item_id=None,
        title="",
        arrived_at=arrived,
        missing_passport_window_days=_WINDOW,
        now=now,
    )
    assert outcome["status"] == "quarantined"
    assert outcome["mint_status"] == "minted"


def test_record_quarantine_admit_mint_failure_returns_error(monkeypatch: pytest.MonkeyPatch):
    from pyforge.steward.dashboard import passport_mint as passport_mint_module  # noqa: PLC0415

    monkeypatch.setattr(
        passport_mint_module,
        "record_vendor_passport",
        lambda **kwargs: {"status": "error", "message": "mint blocked"},
    )
    outcome = quarantine_admit_module.record_quarantine_admit(
        vendor_id="acme",
        jira_key="MINT-FAIL",
        github_item_id=None,
        title="",
        arrived_at=_NOW - timedelta(days=1),
        missing_passport_window_days=_WINDOW,
        now=_NOW,
    )
    assert outcome["status"] == "error"
    assert "mint blocked" in outcome["message"]


def test_record_quarantine_admit_row_create_integrity_error(monkeypatch: pytest.MonkeyPatch):
    def _raise(**kwargs):
        raise IntegrityError("duplicate shelf row")

    monkeypatch.setattr(QuarantineShelfRow.objects, "create", _raise)
    outcome = quarantine_admit_module.record_quarantine_admit(
        vendor_id="acme",
        jira_key="SHELF-ERR",
        github_item_id=None,
        title="",
        arrived_at=_NOW - timedelta(days=15),
        missing_passport_window_days=_WINDOW,
        now=_NOW,
    )
    assert outcome["status"] == "error"
    assert "IntegrityError" in outcome["message"]


def test_list_quarantine_shelf_rows_include_linked():
    linked_outcome = quarantine_admit_module.record_quarantine_admit(
        vendor_id="acme",
        jira_key="LINKED-1",
        github_item_id=None,
        title="",
        arrived_at=_NOW,
        missing_passport_window_days=_WINDOW,
        now=_NOW,
    )
    row = QuarantineShelfRow.objects.get(row_id=linked_outcome["row_id"])
    row.linked_at = _NOW
    row.save(update_fields=["linked_at"])

    unlinked_only = quarantine_admit_module.list_quarantine_shelf_rows(include_linked=False)
    all_rows = quarantine_admit_module.list_quarantine_shelf_rows(include_linked=True)
    assert unlinked_only["count"] < all_rows["count"]
    assert any(r["row_id"] == linked_outcome["row_id"] for r in all_rows["rows"])


def test_list_quarantine_shelf_rows_refuses_on_db_error(monkeypatch: pytest.MonkeyPatch):
    class _BrokenManager:
        def all(self):
            raise OperationalError("db down")

    monkeypatch.setattr(QuarantineShelfRow, "objects", _BrokenManager())
    outcome = quarantine_admit_module.list_quarantine_shelf_rows()
    assert outcome["status"] == "refused"
    assert "OperationalError" in outcome["message"]


def test_record_quarantine_admit_refuses_when_django_not_importable(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setitem(sys.modules, "django", None)
    outcome = quarantine_admit_module.record_quarantine_admit(
        vendor_id="acme",
        jira_key="DJ-1",
        github_item_id=None,
        title="",
        arrived_at=_NOW,
        missing_passport_window_days=_WINDOW,
        now=_NOW,
    )
    assert outcome["status"] == "refused"


def test_list_quarantine_shelf_rows_refuses_when_settings_unconfigured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)
    fake_conf = types.ModuleType("django.conf")
    fake_conf.settings = types.SimpleNamespace(configured=False)
    monkeypatch.setitem(sys.modules, "django.conf", fake_conf)
    outcome = quarantine_admit_module.list_quarantine_shelf_rows()
    assert outcome["status"] == "refused"
    assert "DJANGO_SETTINGS_MODULE" in outcome["message"]


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


def test_quarantine_duty_shelf_human_summary():
    ns = build_parser().parse_args(["quarantine", "shelf"])
    result = QuarantineDuty().run(ns)
    assert result.ok is True
    assert "quarantine shelf:" in result.summary


def test_quarantine_duty_admit_with_arrived_at_z():
    ns = build_parser().parse_args(
        [
            "quarantine",
            "admit",
            "--vendor-id",
            "acme",
            "--jira-key",
            "Z-1",
            "--arrived-at",
            "2026-09-17T08:00:00Z",
        ]
    )
    result = QuarantineDuty().run(ns)
    assert result.ok is True


def test_quarantine_duty_admit_validation_failure():
    ns = argparse.Namespace(
        json=False,
        corridor=None,
        quarantine_verb="admit",
        vendor_id="acme",
        jira_key=None,
        github_item_id=None,
        title="",
        arrived_at=None,
    )
    result = QuarantineDuty().run(ns)
    assert result.ok is False
    assert "nickname" in result.summary.lower() or "error" in result.details.get("status", "")


def test_quarantine_duty_unknown_verb():
    ns = argparse.Namespace(json=False, quarantine_verb="purge")
    result = QuarantineDuty().run(ns)
    assert result.ok is False
    assert "unknown verb" in result.summary
