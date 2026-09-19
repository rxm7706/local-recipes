"""Story 61.1 — corridor transports: config loading, batch-sha idempotent
load, and the `load` duty.

Needs the real migrated `CorridorLoad` table, so this file drives
`django.setup()` + `migrate` by hand exactly once per process, mirroring
`test_dashboard_admin_and_htmx.py`/`test_dashboard_audit.py`. Its
`settings.configure()` block declares the fuller `INSTALLED_APPS` list (the
one `test_dashboard_admin_and_htmx.py` needs) because this file collects
alphabetically BEFORE every `test_dashboard_*.py` module ("corridor" <
"dashboard") and therefore normally WINS the one-shot settings-configure
race in a full-suite run -- declaring the fuller list keeps it a superset
that satisfies every dashboard test file regardless of collection order,
the same discipline those files already document for each other.
"""

from __future__ import annotations

import hashlib
import sys
import types

import pytest

# `corridor_load.py` is the module that genuinely needs django, so without
# the `[dashboard]` extra this file must SKIP, not raise a collection error
# (same rationale as the sibling dashboard test modules).
pytest.importorskip("django", reason="corridor_load.py requires pyforge-steward[dashboard]")

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

from pyforge.steward.cli import build_parser  # noqa: E402
from pyforge.steward.corridor import (  # noqa: E402
    CorridorConfigError,
    CorridorLoadError,
    LoadDuty,
    compute_batch_sha,
    default_corridor_dir,
    load_config,
    load_extract,
)
from pyforge.steward.dashboard.models import CorridorLoad  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_corridor_loads():
    """Isolate each test against the process-lifetime `:memory:` connection
    (no pytest-django transaction rollback here), mirroring
    `test_dashboard_audit.py`'s `_clean_audit_trail`."""
    CorridorLoad.objects.all().delete()
    yield
    CorridorLoad.objects.all().delete()


def _real_config():
    return load_config(default_corridor_dir() / "corridor.yaml")


# -- load_config --


def test_load_config_missing_file(tmp_path):
    with pytest.raises(CorridorConfigError, match="not found"):
        load_config(tmp_path / "corridor.yaml")


def test_load_config_malformed_yaml(tmp_path):
    path = tmp_path / "corridor.yaml"
    path.write_text("transports: [unbalanced\n", encoding="utf-8")
    with pytest.raises(CorridorConfigError, match="malformed YAML"):
        load_config(path)


def test_load_config_not_a_mapping(tmp_path):
    path = tmp_path / "corridor.yaml"
    path.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(CorridorConfigError, match="must be a mapping"):
        load_config(path)


def test_load_config_missing_transports_key(tmp_path):
    path = tmp_path / "corridor.yaml"
    path.write_text("other: 1\n", encoding="utf-8")
    with pytest.raises(CorridorConfigError, match="'transports' section missing"):
        load_config(path)


def test_load_config_bad_state_value(tmp_path):
    path = tmp_path / "corridor.yaml"
    path.write_text("transports:\n  app-upload:\n    state: maybe\n", encoding="utf-8")
    with pytest.raises(CorridorConfigError, match="state"):
        load_config(path)


def test_load_config_happy_path_real_tracked_corridor_yaml():
    config = _real_config()
    states = {t.name: t.state for t in config.transports}
    assert states == {"app-upload": "on", "shared-folder": "off", "email": "off"}
    assert config.transport("app-upload").state == "on"
    assert config.transport("does-not-exist") is None


# -- compute_batch_sha --


def test_compute_batch_sha_is_sha256_hex():
    data = b"hello corridor"
    assert compute_batch_sha(data) == hashlib.sha256(data).hexdigest()


# -- load_extract --


def test_load_extract_unknown_transport_raises():
    with pytest.raises(CorridorLoadError, match="unknown transport"):
        load_extract(
            direction="inbound",
            batch_sha="a" * 64,
            waybill="w1",
            transport="carrier-pigeon",
            config=_real_config(),
        )


def test_load_extract_declared_off_transport_raises():
    with pytest.raises(CorridorLoadError, match="off"):
        load_extract(
            direction="inbound",
            batch_sha="a" * 64,
            waybill="w1",
            transport="email",
            config=_real_config(),
        )


def test_load_extract_fresh_load_creates_one_row():
    sha = "b" * 64
    outcome = load_extract(
        direction="inbound", batch_sha=sha, waybill="w-fresh", transport="app-upload", config=_real_config()
    )
    assert outcome.status == "loaded"
    assert (
        CorridorLoad.objects.filter(direction="inbound", batch_sha=sha, waybill="w-fresh").count() == 1
    )


def test_load_extract_identical_repeat_is_idempotent():
    """The I/O Matrix's one required scenario: same batch sha + waybill drop
    twice is a no-op, not a duplicate row."""
    sha = "c" * 64
    first = load_extract(
        direction="inbound", batch_sha=sha, waybill="w-dup", transport="app-upload", config=_real_config()
    )
    assert first.status == "loaded"
    second = load_extract(
        direction="inbound", batch_sha=sha, waybill="w-dup", transport="app-upload", config=_real_config()
    )
    assert second.status == "idempotent"
    assert CorridorLoad.objects.filter(direction="inbound", batch_sha=sha, waybill="w-dup").count() == 1


def test_load_extract_different_waybill_same_sha_creates_second_row():
    sha = "d" * 64
    load_extract(
        direction="inbound", batch_sha=sha, waybill="w-1", transport="app-upload", config=_real_config()
    )
    load_extract(
        direction="inbound", batch_sha=sha, waybill="w-2", transport="app-upload", config=_real_config()
    )
    assert CorridorLoad.objects.filter(batch_sha=sha).count() == 2


# -- LoadDuty.run() --


def test_load_duty_bare_invocation_reports_three_transports_no_db_touch():
    ns = build_parser().parse_args(["load"])
    result = LoadDuty().run(ns)
    assert result.ok is True
    assert result.details["transports"] == [
        {"name": "app-upload", "state": "on"},
        {"name": "shared-folder", "state": "off"},
        {"name": "email", "state": "off"},
    ]
    assert CorridorLoad.objects.count() == 0


@pytest.mark.parametrize("direction", ["inbound", "outbound"])
def test_load_duty_first_load_then_repeat_is_idempotent(tmp_path, direction):
    extract = tmp_path / "extract.csv"
    extract.write_text("row,one\n", encoding="utf-8")

    first_ns = build_parser().parse_args(
        ["load", direction, "--file", str(extract), "--waybill", f"w-duty-{direction}"]
    )
    first = LoadDuty().run(first_ns)
    assert first.ok is True
    assert first.details["status"] == "loaded"

    second_ns = build_parser().parse_args(
        ["load", direction, "--file", str(extract), "--waybill", f"w-duty-{direction}"]
    )
    second = LoadDuty().run(second_ns)
    assert second.ok is True
    assert second.details["status"] == "idempotent"


def test_load_duty_missing_file_path_fails():
    ns = build_parser().parse_args(
        ["load", "inbound", "--file", "/nonexistent/path/does-not-exist.csv", "--waybill", "w"]
    )
    result = LoadDuty().run(ns)
    assert result.ok is False
    assert "not found" in result.summary


def test_load_duty_declared_off_transport_fails(tmp_path):
    extract = tmp_path / "extract.csv"
    extract.write_text("row,one\n", encoding="utf-8")
    ns = build_parser().parse_args(
        [
            "load",
            "inbound",
            "--file",
            str(extract),
            "--waybill",
            "w-off",
            "--transport",
            "email",
        ]
    )
    result = LoadDuty().run(ns)
    assert result.ok is False
    assert CorridorLoad.objects.filter(waybill="w-off").count() == 0


# -- CLI parsing --


def test_cli_parses_load_inbound_with_expected_namespace():
    ns = build_parser().parse_args(["load", "inbound", "--file", "x", "--waybill", "w"])
    assert ns.duty == "load"
    assert ns.load_verb == "inbound"
    assert ns.file == "x"
    assert ns.waybill == "w"
    assert ns.transport == "app-upload"
    assert ns.corridor is None
    assert ns.json is False
