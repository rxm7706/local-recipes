"""Story 61.3 — the as-of glass: standup/shipped freshness over the inbound
corridor, and the flag-gated CSV/markdown export.

Needs the real migrated `CorridorLoad` table (Story 61.1), so this file
drives `django.setup()` + `migrate` by hand exactly once per process,
mirroring `test_corridor.py`/`test_dashboard_admin_and_htmx.py`. Its
`settings.configure()` block declares the same fuller `INSTALLED_APPS` list
those files use, so whichever test module wins the one-shot settings-configure
race in a full-suite run still satisfies every other dashboard test file.
"""

from __future__ import annotations

import csv
import io
import json
import sys
import types
from datetime import datetime, timedelta, timezone

import pytest

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

from django.db import DataError, OperationalError, ProgrammingError  # noqa: E402

from pyforge.steward.cli import build_parser  # noqa: E402
from pyforge.steward.dashboard import glass_query as glass_query_module  # noqa: E402
from pyforge.steward.dashboard.models import CorridorLoad  # noqa: E402
from pyforge.steward.glass import (  # noqa: E402
    EMPTY_FILE_SHA256,
    FLAG_GLASS_EXPORT,
    GLASS_EXPORT_FORMATS,
    GLASS_STATES,
    GlassDuty,
    GlassError,
    GlassReading,
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


def _create_row(*, waybill: str, batch_sha: str, direction: str = "inbound", days_ago: int = 0) -> CorridorLoad:
    row = CorridorLoad.objects.create(direction=direction, batch_sha=batch_sha, waybill=waybill, transport="app-upload")
    if days_ago:
        earlier = datetime.now(timezone.utc) - timedelta(days=days_ago)
        CorridorLoad.objects.filter(pk=row.pk).update(loaded_at=earlier)
        row.refresh_from_db()
    return row


# -- compute_glass_reading --


def test_compute_glass_reading_unknown_direction_raises():
    with pytest.raises(GlassError, match="unknown direction"):
        compute_glass_reading(direction="lateral")


def test_compute_glass_reading_naive_now_raises():
    with pytest.raises(GlassError, match="timezone-aware"):
        compute_glass_reading(direction="inbound", now=datetime(2026, 9, 19, 12, 0, 0))


def test_compute_glass_reading_unborn_before_first_waybill():
    """I/O Matrix: no waybill yet -> unborn, not empty-success."""
    reading = compute_glass_reading(direction="inbound")
    assert reading.status == "ok"
    assert reading.state == "unborn"
    assert reading.waybill is None
    assert reading.batch_sha is None
    assert reading.loaded_at is None


def test_compute_glass_reading_fresh_for_a_nonempty_todays_load():
    _create_row(waybill="WB-FRESH", batch_sha="a" * 64)
    reading = compute_glass_reading(direction="inbound")
    assert reading.state == "fresh"
    assert reading.waybill == "WB-FRESH"
    assert reading.batch_sha == "a" * 64


def test_compute_glass_reading_failed_for_an_empty_todays_load():
    """I/O Matrix: empty on-time file fails."""
    _create_row(waybill="WB-EMPTY", batch_sha=EMPTY_FILE_SHA256)
    reading = compute_glass_reading(direction="inbound")
    assert reading.state == "failed"
    assert reading.waybill == "WB-EMPTY"


def test_compute_glass_reading_stale_when_last_load_was_not_today():
    """I/O Matrix: late drop leaves yesterday stale, still citing the waybill."""
    _create_row(waybill="WB-STALE", batch_sha="b" * 64, days_ago=2)
    reading = compute_glass_reading(direction="inbound")
    assert reading.state == "stale"
    assert reading.waybill == "WB-STALE"


def test_compute_glass_reading_refused_when_dashboard_extra_not_importable(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyforge.steward.dashboard.glass_query", None)
    reading = compute_glass_reading(direction="inbound")
    assert reading.status == "refused"
    assert reading.state is None
    assert "not installed" in reading.message


def test_compute_glass_reading_refused_when_the_module_itself_refuses(monkeypatch):
    """Distinct from the extra-not-importable case above: the `[dashboard]`
    extra IS installed, but `read_latest_corridor_load` refuses internally
    (e.g. Django settings unconfigured) -- `compute_glass_reading` must pass
    that refusal through unchanged, never raise."""
    import pyforge.steward.dashboard.glass_query as glass_query_module

    monkeypatch.setattr(
        glass_query_module,
        "read_latest_corridor_load",
        lambda *, direction: {"status": "refused", "direction": direction, "message": "settings unconfigured"},
    )
    reading = compute_glass_reading(direction="inbound")
    assert reading.status == "refused"
    assert reading.state is None
    assert reading.message == "settings unconfigured"


# -- dashboard/glass_query.py's own refusal branches --
#
# These call `read_latest_corridor_load` directly (not through
# `compute_glass_reading`) to exercise the environmental-failure paths its
# docstring promises: django missing, settings unconfigured, the model
# import failing, and the ORM exception group -- mirroring
# `test_corridor.py`'s identical precedent for `record_corridor_load`. Each
# uses a scoped `monkeypatch`, restored automatically once the test returns.


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
    assert "DJANGO_SETTINGS_MODULE" in result["message"]


def test_read_latest_corridor_load_refuses_when_model_import_fails(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyforge.steward.dashboard.models", None)
    result = glass_query_module.read_latest_corridor_load(direction="inbound")
    assert result["status"] == "refused"


def test_read_latest_corridor_load_refuses_on_operational_error(monkeypatch):
    def _raise_operational(**kwargs):
        raise OperationalError("db unreachable")

    monkeypatch.setattr(CorridorLoad.objects, "filter", _raise_operational)
    result = glass_query_module.read_latest_corridor_load(direction="inbound")
    assert result["status"] == "refused"


def test_read_latest_corridor_load_refuses_on_data_and_programming_errors(monkeypatch):
    for exc_cls in (DataError, ProgrammingError):

        def _raise(**kwargs):
            raise exc_cls("boom")

        monkeypatch.setattr(CorridorLoad.objects, "filter", _raise)
        result = glass_query_module.read_latest_corridor_load(direction="inbound")
        assert result["status"] == "refused"


def test_read_latest_corridor_load_found_false_when_no_row_exists():
    result = glass_query_module.read_latest_corridor_load(direction="inbound")
    assert result == {"status": "ok", "direction": "inbound", "found": False}


def test_read_latest_corridor_load_returns_the_most_recent_row():
    _create_row(waybill="WB-OLD", batch_sha="3" * 64, days_ago=1)
    _create_row(waybill="WB-NEW", batch_sha="4" * 64)
    result = glass_query_module.read_latest_corridor_load(direction="inbound")
    assert result["status"] == "ok"
    assert result["found"] is True
    assert result["waybill"] == "WB-NEW"


# -- GLASS_STATES --


def test_every_glass_state_literal_used_by_compute_glass_reading_is_a_member():
    for state in ("unborn", "fresh", "stale", "failed"):
        assert state in GLASS_STATES


# -- render_glass_table --


def _fresh_reading(waybill: str = "WB-1") -> GlassReading:
    return GlassReading(
        status="ok",
        direction="inbound",
        state="fresh",
        waybill=waybill,
        batch_sha="c" * 64,
        loaded_at="2026-09-19T00:00:00+00:00",
        message="",
    )


def _stale_reading() -> GlassReading:
    return GlassReading(
        status="ok",
        direction="inbound",
        state="stale",
        waybill="WB-2",
        batch_sha="d" * 64,
        loaded_at="2026-09-17T00:00:00+00:00",
        message="no drop yet today -- showing the last known waybill",
    )


def _refused_reading() -> GlassReading:
    return GlassReading(
        status="refused",
        direction="inbound",
        state=None,
        waybill=None,
        batch_sha=None,
        loaded_at=None,
        message="pyforge-steward[dashboard] extra not installed",
    )


def test_render_glass_table_csv_shape():
    table = render_glass_table({"standup": _fresh_reading(), "shipped": _stale_reading()}, "csv")
    rows = list(csv.reader(io.StringIO(table)))
    assert rows[0] == ["View", "Direction", "State", "Waybill", "Loaded At (UTC)", "Message"]
    assert rows[1][:4] == ["Standup", "inbound", "fresh", "WB-1"]
    assert rows[2][:4] == ["Shipped", "inbound", "stale", "WB-2"]


def test_render_glass_table_markdown_shape():
    table = render_glass_table({"standup": _fresh_reading(), "shipped": _stale_reading()}, "markdown")
    lines = table.splitlines()
    assert lines[0].startswith("| View | Direction | State |")
    assert lines[1] == "|---|---|---|---|---|---|"
    assert "Standup" in lines[2] and "WB-1" in lines[2] and "fresh" in lines[2]
    assert "Shipped" in lines[3] and "WB-2" in lines[3] and "stale" in lines[3]


@pytest.mark.parametrize("fmt", GLASS_EXPORT_FORMATS)
def test_render_glass_table_handles_a_refused_reading(fmt):
    """Blind Hunter (review pass 1): the `reading.state or "refused"` /
    `reading.waybill or ""` fallbacks must actually render, not just exist."""
    table = render_glass_table({"standup": _refused_reading(), "shipped": _fresh_reading()}, fmt)
    assert "None" not in table
    if fmt == "csv":
        rows = list(csv.reader(io.StringIO(table)))
        assert rows[1][2] == "refused"
        assert rows[1][3] == ""
    else:
        lines = table.splitlines()
        cells = [c.strip() for c in lines[2].split("|")][1:-1]
        assert cells == ["Standup", "inbound", "refused", "", "", _refused_reading().message]


def test_render_glass_table_markdown_escapes_pipe_and_newline_in_waybill():
    """Edge Case Hunter (review pass 1): an unescaped `|` or newline in a
    caller-supplied waybill must not corrupt the table's column structure."""
    reading = _fresh_reading(waybill="WB|broken\nwaybill")
    table = render_glass_table({"standup": reading, "shipped": _stale_reading()}, "markdown")
    lines = table.splitlines()
    assert len(lines) == 4  # header + separator + exactly two data rows
    assert "WB\\|broken waybill" in table


def test_render_glass_table_unknown_format_raises():
    with pytest.raises(GlassError, match="unknown format"):
        render_glass_table({"standup": _fresh_reading(), "shipped": _stale_reading()}, "pdf")


# -- GlassDuty.run() --


def test_glass_duty_bare_both_fresh_is_ok():
    _create_row(waybill="WB-A", batch_sha="e" * 64, direction="inbound")
    result = GlassDuty().run(build_parser().parse_args(["glass"]))
    assert result.ok is True
    assert result.details["standup"]["state"] == "fresh"
    assert result.details["shipped"]["state"] == "fresh"
    assert result.details["standup"] == result.details["shipped"]


def test_glass_duty_bare_failed_inbound_is_not_ok():
    _create_row(waybill="WB-EMPTY", batch_sha=EMPTY_FILE_SHA256)
    result = GlassDuty().run(build_parser().parse_args(["glass"]))
    assert result.ok is False
    assert result.details["standup"]["state"] == "failed"


def test_glass_duty_bare_dashboard_extra_unavailable_is_not_ok_via_duty_layer(monkeypatch):
    """Verification Gap Reviewer (review pass 1): force the refusal through
    the DUTY, not `compute_glass_reading` directly -- exercises
    `_direction_ok`'s `status == "ok"` guard at the layer that actually
    matters to a caller."""
    monkeypatch.setitem(sys.modules, "pyforge.steward.dashboard.glass_query", None)
    result = GlassDuty().run(build_parser().parse_args(["glass"]))
    assert result.ok is False
    assert result.details["standup"]["status"] == "refused"
    assert result.details["shipped"]["status"] == "refused"


def test_glass_duty_export_flag_off_by_default_names_the_flag():
    result = GlassDuty().run(build_parser().parse_args(["glass", "export"]))
    assert result.ok is False
    assert FLAG_GLASS_EXPORT in result.summary


@pytest.mark.parametrize("fmt", GLASS_EXPORT_FORMATS)
def test_glass_duty_export_with_flag_on_succeeds(fmt):
    _create_row(waybill="WB-EXPORT", batch_sha="f" * 64)
    ns = build_parser().parse_args(["glass", "export", "--format", fmt, "--flag", "enable_glass_export=true"])
    result = GlassDuty().run(ns)
    assert result.ok is True
    assert "WB-EXPORT" in result.details["table"]


def test_glass_duty_json_on_bare_success():
    _create_row(waybill="WB-B", batch_sha="1" * 64)
    ns = build_parser().parse_args(["glass", "--json"])
    result = GlassDuty().run(ns)
    assert result.ok is True
    payload = json.loads(result.summary)
    assert payload["standup"]["state"] == "fresh"
    assert payload["shipped"]["state"] == "fresh"


def test_glass_duty_json_on_bare_failure():
    _create_row(waybill="WB-EMPTY", batch_sha=EMPTY_FILE_SHA256)
    ns = build_parser().parse_args(["glass", "--json"])
    result = GlassDuty().run(ns)
    assert result.ok is False
    payload = json.loads(result.summary)
    assert payload["standup"]["state"] == "failed"


def test_glass_duty_json_on_export_success():
    _create_row(waybill="WB-C", batch_sha="2" * 64)
    ns = build_parser().parse_args(["glass", "--json", "export", "--flag", "enable_glass_export=true"])
    result = GlassDuty().run(ns)
    assert result.ok is True
    payload = json.loads(result.summary)
    assert payload["format"] == "markdown"
    assert "WB-C" in payload["table"]


def test_glass_duty_json_on_export_failure():
    ns = build_parser().parse_args(["glass", "--json", "export"])
    result = GlassDuty().run(ns)
    assert result.ok is False
    payload = json.loads(result.summary)
    assert "message" in payload


# -- CLI parsing --


def test_cli_parses_bare_glass():
    ns = build_parser().parse_args(["glass"])
    assert ns.duty == "glass"
    assert ns.glass_verb is None
    assert ns.json is False


def test_cli_parses_glass_export_with_explicit_format():
    ns = build_parser().parse_args(["glass", "export", "--format", "csv"])
    assert ns.glass_verb == "export"
    assert ns.format == "csv"


def test_cli_glass_export_default_format_is_markdown():
    ns = build_parser().parse_args(["glass", "export"])
    assert ns.format == "markdown"
