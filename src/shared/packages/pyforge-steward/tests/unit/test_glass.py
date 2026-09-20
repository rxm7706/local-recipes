"""Story 61.3 — as-of glass: standup/shipped freshness over the inbound/
outbound corridor. Cites a waybill; empty on-time file fails; late drop
leaves yesterday stale; unborn before the first waybill.

Needs the real migrated `CorridorLoad` table, so this file drives
`django.setup()` + `migrate` by hand exactly once per process, mirroring
`test_corridor.py`'s settings-configure race-guard idiom.
"""

from __future__ import annotations

import csv
import io
import json
import sys
import types
from datetime import datetime, timedelta, timezone

import pytest

# `glass_query.py` is the module that genuinely needs django, so without the
# `[dashboard]` extra this file must SKIP, not raise a collection error
# (same rationale as the sibling dashboard test modules).
pytest.importorskip("django", reason="glass_query.py requires pyforge-steward[dashboard]")

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

from django.db import DataError  # noqa: E402

from pyforge.steward.cli import build_parser  # noqa: E402
from pyforge.steward.dashboard import glass_query as glass_query_module  # noqa: E402
from pyforge.steward.dashboard.models import CorridorLoad  # noqa: E402
from pyforge.steward.glass import (  # noqa: E402
    EMPTY_FILE_SHA256,
    GlassDuty,
    GlassError,
    compute_glass_reading,
    render_glass_table,
)


@pytest.fixture(autouse=True)
def _clean_corridor_loads():
    """Isolate each test against the process-lifetime `:memory:` connection
    (no pytest-django transaction rollback here), mirroring
    `test_corridor.py`'s `_clean_corridor_loads`."""
    CorridorLoad.objects.all().delete()
    yield
    CorridorLoad.objects.all().delete()


def _make_load(*, direction: str, batch_sha: str, waybill: str = "w-1", transport: str = "app-upload") -> CorridorLoad:
    return CorridorLoad.objects.create(
        direction=direction, batch_sha=batch_sha, waybill=waybill, transport=transport
    )


def _backdate(row: CorridorLoad, when: datetime) -> None:
    """Bypass `auto_now_add` (which only fires on `.save()`) with a bare
    `.update()`, so a fixture row can be planted on an earlier UTC date."""
    CorridorLoad.objects.filter(pk=row.pk).update(loaded_at=when)


# -- compute_glass_reading --


def test_compute_glass_reading_unknown_direction_raises():
    with pytest.raises(GlassError, match="unknown direction"):
        compute_glass_reading(direction="sideways")


def test_compute_glass_reading_naive_now_raises():
    with pytest.raises(GlassError, match="timezone-aware"):
        compute_glass_reading(direction="inbound", now=datetime(2026, 9, 19))


def test_compute_glass_reading_unborn_before_first_waybill():
    """I/O Matrix: no waybill yet -> unborn, not empty-success."""
    reading = compute_glass_reading(direction="inbound")
    assert reading.status == "ok"
    assert reading.state == "unborn"
    assert reading.waybill is None
    assert reading.batch_sha is None
    assert reading.loaded_at is None


def test_compute_glass_reading_fresh_for_a_nonempty_load_today():
    _make_load(direction="inbound", batch_sha="a" * 64, waybill="w-fresh")
    reading = compute_glass_reading(direction="inbound")
    assert reading.state == "fresh"
    assert reading.waybill == "w-fresh"
    assert reading.message == ""


def test_compute_glass_reading_failed_for_an_empty_load_today():
    """I/O Matrix: empty on-time file fails."""
    _make_load(direction="inbound", batch_sha=EMPTY_FILE_SHA256, waybill="w-empty")
    reading = compute_glass_reading(direction="inbound")
    assert reading.state == "failed"
    assert reading.waybill == "w-empty"
    assert "empty" in reading.message


def test_compute_glass_reading_stale_when_nothing_loaded_today():
    """I/O Matrix: late drop leaves yesterday stale, still citing the waybill."""
    row = _make_load(direction="inbound", batch_sha="b" * 64, waybill="w-yesterday")
    _backdate(row, datetime.now(timezone.utc) - timedelta(days=1))
    reading = compute_glass_reading(direction="inbound")
    assert reading.state == "stale"
    assert reading.waybill == "w-yesterday"


def test_compute_glass_reading_stale_generalizes_past_exactly_one_day():
    row = _make_load(direction="outbound", batch_sha="c" * 64, waybill="w-old")
    _backdate(row, datetime.now(timezone.utc) - timedelta(days=5))
    reading = compute_glass_reading(direction="outbound")
    assert reading.state == "stale"


def test_compute_glass_reading_refused_when_dashboard_extra_not_importable(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyforge.steward.dashboard.glass_query", None)
    reading = compute_glass_reading(direction="inbound")
    assert reading.status == "refused"
    assert reading.state is None
    assert reading.waybill is None


# -- dashboard/glass_query.py's own refusal branches --
#
# These call `read_latest_corridor_load` directly (not through
# `compute_glass_reading`) to exercise the environmental-failure paths its
# docstring promises: django missing, settings unconfigured, the model
# import failing, and the ORM exception group -- mirroring `test_corridor.py`'s
# `record_corridor_load` refusal tests. Each uses a scoped `monkeypatch`
# (`sys.modules` entries or a manager method), restored automatically once
# the test returns -- no other test in this process observes the patch.


def test_read_latest_corridor_load_refuses_when_django_is_not_importable(monkeypatch):
    monkeypatch.setitem(sys.modules, "django", None)
    result = glass_query_module.read_latest_corridor_load(direction="inbound")
    assert result["status"] == "refused"


def test_read_latest_corridor_load_refuses_when_settings_unconfigured(monkeypatch):
    monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)
    fake_conf = types.ModuleType("django.conf")
    fake_conf.settings = types.SimpleNamespace(configured=False)
    monkeypatch.setitem(sys.modules, "django.conf", fake_conf)
    result = glass_query_module.read_latest_corridor_load(direction="inbound")
    assert result["status"] == "refused"


def test_read_latest_corridor_load_refuses_when_model_import_fails(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyforge.steward.dashboard.models", None)
    result = glass_query_module.read_latest_corridor_load(direction="inbound")
    assert result["status"] == "refused"


def test_read_latest_corridor_load_refuses_on_operational_error(monkeypatch):
    def _raise_data_error(**kwargs):
        raise DataError("db unreachable")

    monkeypatch.setattr(CorridorLoad.objects, "filter", _raise_data_error)
    result = glass_query_module.read_latest_corridor_load(direction="inbound")
    assert result["status"] == "refused"


# -- render_glass_table --


def test_render_glass_table_unknown_format_raises():
    standup = compute_glass_reading(direction="inbound")
    shipped = compute_glass_reading(direction="outbound")
    with pytest.raises(GlassError, match="unknown format"):
        render_glass_table({"standup": standup, "shipped": shipped}, "xml")


def test_render_glass_table_csv_shape():
    _make_load(direction="inbound", batch_sha="d" * 64, waybill="w-csv")
    standup = compute_glass_reading(direction="inbound")
    shipped = compute_glass_reading(direction="outbound")
    table = render_glass_table({"standup": standup, "shipped": shipped}, "csv")
    rows = list(csv.reader(io.StringIO(table)))
    assert rows[0] == ["View", "Direction", "State", "Waybill", "Loaded At (UTC)", "Message"]
    assert rows[1][0] == "Standup"
    assert rows[1][2] == "fresh"
    assert rows[1][3] == "w-csv"
    assert rows[2][0] == "Shipped"
    assert rows[2][2] == "unborn"


def test_render_glass_table_markdown_shape():
    standup = compute_glass_reading(direction="inbound")
    shipped = compute_glass_reading(direction="outbound")
    table = render_glass_table({"standup": standup, "shipped": shipped}, "markdown")
    assert "| View | Direction | State | Waybill | Loaded At (UTC) | Message |" in table
    assert "|---|---|---|---|---|---|" in table
    assert "| Standup |" in table and "| Shipped |" in table


# -- GlassDuty.run() --


def test_glass_duty_bare_both_fresh_is_ok():
    _make_load(direction="inbound", batch_sha="e" * 64, waybill="w-in")
    _make_load(direction="outbound", batch_sha="f" * 64, waybill="w-out")
    ns = build_parser().parse_args(["glass"])
    result = GlassDuty().run(ns)
    assert result.ok is True
    assert result.details["standup"]["state"] == "fresh"
    assert result.details["shipped"]["state"] == "fresh"


def test_glass_duty_bare_one_failed_is_not_ok():
    _make_load(direction="inbound", batch_sha=EMPTY_FILE_SHA256, waybill="w-in")
    _make_load(direction="outbound", batch_sha="g" * 64, waybill="w-out")
    ns = build_parser().parse_args(["glass"])
    result = GlassDuty().run(ns)
    assert result.ok is False
    assert result.details["standup"]["state"] == "failed"


def test_glass_duty_bare_stale_is_still_ok():
    """`_direction_ok` treats stale as a legitimate, non-failing answer."""
    row = _make_load(direction="inbound", batch_sha="a2" + "a" * 62, waybill="w-stale")
    _backdate(row, datetime.now(timezone.utc) - timedelta(days=2))
    _make_load(direction="outbound", batch_sha="a3" + "b" * 62, waybill="w-out")
    ns = build_parser().parse_args(["glass"])
    result = GlassDuty().run(ns)
    assert result.ok is True
    assert result.details["standup"]["state"] == "stale"


def test_glass_duty_bare_unborn_is_still_ok():
    ns = build_parser().parse_args(["glass"])
    result = GlassDuty().run(ns)
    assert result.ok is True
    assert result.details["standup"]["state"] == "unborn"
    assert result.details["shipped"]["state"] == "unborn"


def test_glass_duty_export_flag_off_by_default_fails():
    ns = build_parser().parse_args(["glass", "export"])
    result = GlassDuty().run(ns)
    assert result.ok is False
    assert "enable_glass_export" in result.summary
    assert "table" not in result.details


@pytest.mark.parametrize("fmt", ["csv", "markdown"])
def test_glass_duty_export_flag_on_succeeds(fmt):
    _make_load(direction="inbound", batch_sha="a4" + "c" * 62, waybill="w-export")
    ns = build_parser().parse_args(
        ["glass", "export", "--format", fmt, "--flag", "enable_glass_export=true"]
    )
    result = GlassDuty().run(ns)
    assert result.ok is True
    assert "w-export" in result.details["table"]
    assert result.details["format"] == fmt


def test_glass_duty_json_on_bare_invocation():
    ns = build_parser().parse_args(["glass", "--json"])
    result = GlassDuty().run(ns)
    assert result.ok is True
    payload = json.loads(result.summary)
    assert "standup" in payload and "shipped" in payload


def test_glass_duty_json_on_bare_failure():
    _make_load(direction="inbound", batch_sha=EMPTY_FILE_SHA256, waybill="w-in")
    ns = build_parser().parse_args(["glass", "--json"])
    result = GlassDuty().run(ns)
    assert result.ok is False
    payload = json.loads(result.summary)
    assert payload["standup"]["state"] == "failed"


def test_glass_duty_json_on_export_success():
    ns = build_parser().parse_args(
        ["glass", "--json", "export", "--flag", "enable_glass_export=true"]
    )
    result = GlassDuty().run(ns)
    assert result.ok is True
    payload = json.loads(result.summary)
    assert payload["format"] == "markdown"
    assert "table" in payload


def test_glass_duty_json_on_export_flag_off_failure():
    ns = build_parser().parse_args(["glass", "--json", "export"])
    result = GlassDuty().run(ns)
    assert result.ok is False
    payload = json.loads(result.summary)
    assert "message" in payload


# -- CLI parsing --


def test_cli_parses_glass_bare():
    ns = build_parser().parse_args(["glass"])
    assert ns.duty == "glass"
    assert ns.glass_verb is None
    assert ns.json is False


def test_cli_parses_glass_export_default_format():
    ns = build_parser().parse_args(["glass", "export"])
    assert ns.glass_verb == "export"
    assert ns.format == "markdown"
    assert ns.flag is None


def test_cli_parses_glass_export_csv_format_and_flag():
    ns = build_parser().parse_args(
        ["glass", "export", "--format", "csv", "--flag", "enable_glass_export=true"]
    )
    assert ns.format == "csv"
    assert ns.flag == ["enable_glass_export=true"]
