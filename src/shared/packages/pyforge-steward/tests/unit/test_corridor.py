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
import json
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

from django.contrib.admin.sites import AdminSite  # noqa: E402
from django.db import DataError, IntegrityError, OperationalError  # noqa: E402

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
from pyforge.steward.dashboard import corridor_load as corridor_load_module  # noqa: E402
from pyforge.steward.dashboard.admin import CorridorLoadAdmin  # noqa: E402
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
    assert CorridorLoad.objects.filter(direction="inbound", batch_sha=sha, waybill="w-fresh").count() == 1


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
    load_extract(direction="inbound", batch_sha=sha, waybill="w-1", transport="app-upload", config=_real_config())
    load_extract(direction="inbound", batch_sha=sha, waybill="w-2", transport="app-upload", config=_real_config())
    assert CorridorLoad.objects.filter(batch_sha=sha).count() == 2


def test_load_extract_repeat_with_declared_off_transport_is_still_idempotent():
    """Idempotent on `(direction, batch_sha, waybill)` ALONE -- the existing-
    record check runs before transport validation, so a repeat drop naming a
    declared-off transport (or an unknown one) must still resolve as
    idempotent, never raise, as long as the record already exists under some
    other, valid transport."""
    sha = "j2" + "e" * 62
    waybill = "w-repeat-off-transport"
    first = load_extract(
        direction="inbound", batch_sha=sha, waybill=waybill, transport="app-upload", config=_real_config()
    )
    assert first.status == "loaded"

    second = load_extract(direction="inbound", batch_sha=sha, waybill=waybill, transport="email", config=_real_config())
    assert second.status == "idempotent"
    assert second.transport == "app-upload"
    assert CorridorLoad.objects.filter(direction="inbound", batch_sha=sha, waybill=waybill).count() == 1


# -- load_extract -- Story 61.4: the outbound signed-slice gate --


def test_load_extract_outbound_without_slice_name_raises():
    """The I/O Matrix's one required scenario: no signer/slice -> refused.
    Exercised here as the `slice_name` half. The dashboard-extra import and
    the idempotency probe both run (and succeed) before this gate fires --
    only the transport-declared check runs after it."""
    with pytest.raises(CorridorLoadError, match="named slice"):
        load_extract(
            direction="outbound",
            batch_sha="m" * 64,
            waybill="w-outbound-no-slice",
            transport="app-upload",
            config=_real_config(),
            slice_name="",
            signer="operator",
        )
    assert CorridorLoad.objects.filter(waybill="w-outbound-no-slice").count() == 0


def test_load_extract_outbound_with_whitespace_only_slice_name_raises():
    """Symmetric with the blank-signer whitespace case below: a
    regression dropping `.strip()` from the slice_name half of the gate
    would let this through."""
    with pytest.raises(CorridorLoadError, match="named slice"):
        load_extract(
            direction="outbound",
            batch_sha="m2" + "a" * 62,
            waybill="w-outbound-whitespace-slice",
            transport="app-upload",
            config=_real_config(),
            slice_name="   ",
            signer="operator",
        )
    assert CorridorLoad.objects.filter(waybill="w-outbound-whitespace-slice").count() == 0


def test_load_extract_outbound_without_signer_raises():
    with pytest.raises(CorridorLoadError, match="signer"):
        load_extract(
            direction="outbound",
            batch_sha="n" * 64,
            waybill="w-outbound-no-signer",
            transport="app-upload",
            config=_real_config(),
            slice_name="vendor-findings",
            signer="   ",
        )
    assert CorridorLoad.objects.filter(waybill="w-outbound-no-signer").count() == 0


def test_load_extract_outbound_with_blank_signer_raises():
    """Symmetric with the whitespace-only-slice_name case above: a
    regression dropping the blank (empty-string) check from the signer
    half of the gate would let this through."""
    with pytest.raises(CorridorLoadError, match="signer"):
        load_extract(
            direction="outbound",
            batch_sha="n2" + "a" * 62,
            waybill="w-outbound-blank-signer",
            transport="app-upload",
            config=_real_config(),
            slice_name="vendor-findings",
            signer="",
        )
    assert CorridorLoad.objects.filter(waybill="w-outbound-blank-signer").count() == 0


def test_load_extract_outbound_with_slice_and_signer_records_them():
    sha = "o" * 64
    outcome = load_extract(
        direction="outbound",
        batch_sha=sha,
        waybill="w-outbound-signed",
        transport="app-upload",
        config=_real_config(),
        slice_name="vendor-findings",
        signer="operator",
    )
    assert outcome.status == "loaded"
    assert outcome.slice_name == "vendor-findings"
    assert outcome.signer == "operator"
    row = CorridorLoad.objects.get(direction="outbound", batch_sha=sha, waybill="w-outbound-signed")
    assert row.slice_name == "vendor-findings"
    assert row.signer == "operator"


def test_load_extract_outbound_repeat_reports_originally_recorded_slice_and_signer():
    """Mirrors the transport idempotency provenance rule: a repeat drop
    reports the FIRST slice/signer, never a second call's own values, and
    does not require them to be re-supplied."""
    sha = "p" * 64
    waybill = "w-outbound-repeat"
    first = load_extract(
        direction="outbound",
        batch_sha=sha,
        waybill=waybill,
        transport="app-upload",
        config=_real_config(),
        slice_name="vendor-findings",
        signer="operator",
    )
    assert first.status == "loaded"

    second = load_extract(
        direction="outbound",
        batch_sha=sha,
        waybill=waybill,
        transport="app-upload",
        config=_real_config(),
        slice_name="",
        signer="",
    )
    assert second.status == "idempotent"
    assert second.slice_name == "vendor-findings"
    assert second.signer == "operator"
    assert CorridorLoad.objects.filter(direction="outbound", batch_sha=sha, waybill=waybill).count() == 1


def test_load_extract_inbound_never_requires_slice_or_signer():
    """The gate is outbound-only -- an inbound load with no slice/signer
    given at all succeeds exactly as it did before Story 61.4."""
    outcome = load_extract(
        direction="inbound",
        batch_sha="q" * 64,
        waybill="w-inbound-no-signature-needed",
        transport="app-upload",
        config=_real_config(),
    )
    assert outcome.status == "loaded"
    assert outcome.slice_name == ""
    assert outcome.signer == ""


def test_load_extract_refuses_when_dashboard_extra_not_importable(monkeypatch):
    """The spec's stated AC: `[dashboard]` not installed -> `status: refused`,
    exercised through `load_extract` itself (not `record_corridor_load`
    directly) -- `importlib.import_module` is what actually fails here."""
    monkeypatch.setitem(sys.modules, "pyforge.steward.dashboard.corridor_load", None)
    outcome = load_extract(
        direction="inbound",
        batch_sha="f2" + "a" * 62,
        waybill="w-noextra",
        transport="app-upload",
        config=_real_config(),
    )
    assert outcome.status == "refused"


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

    args = ["load", direction, "--file", str(extract), "--waybill", f"w-duty-{direction}"]
    if direction == "outbound":
        # Story 61.4: outbound alone requires a named slice + recorded signer.
        args += ["--slice", "vendor-findings", "--signer", "operator"]

    first_ns = build_parser().parse_args(args)
    first = LoadDuty().run(first_ns)
    assert first.ok is True
    assert first.details["status"] == "loaded"

    second_ns = build_parser().parse_args(args)
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


def test_load_duty_repeat_with_declared_off_transport_is_still_idempotent(tmp_path):
    """CLI-level twin of `test_load_extract_repeat_with_declared_off_transport_
    is_still_idempotent`: load once via `app-upload`, repeat the same file +
    waybill naming `email` (declared off) -- must still be idempotent, not an
    error."""
    extract = tmp_path / "extract.csv"
    extract.write_text("row,one\n", encoding="utf-8")

    first_ns = build_parser().parse_args(["load", "inbound", "--file", str(extract), "--waybill", "w-cli-repeat-off"])
    first = LoadDuty().run(first_ns)
    assert first.ok is True
    assert first.details["status"] == "loaded"

    second_ns = build_parser().parse_args(
        [
            "load",
            "inbound",
            "--file",
            str(extract),
            "--waybill",
            "w-cli-repeat-off",
            "--transport",
            "email",
        ]
    )
    second = LoadDuty().run(second_ns)
    assert second.ok is True
    assert second.details["status"] == "idempotent"


def test_load_duty_outbound_without_signer_fails(tmp_path):
    """CLI-level twin of the I/O Matrix's "unsigned dump -> refused" row:
    a named slice with no signer is refused, not a raised traceback."""
    extract = tmp_path / "extract.csv"
    extract.write_text("row,one\n", encoding="utf-8")
    ns = build_parser().parse_args(
        [
            "load",
            "outbound",
            "--file",
            str(extract),
            "--waybill",
            "w-cli-no-signer",
            "--slice",
            "vendor-findings",
        ]
    )
    result = LoadDuty().run(ns)
    assert result.ok is False
    assert "signer" in result.summary
    assert CorridorLoad.objects.filter(waybill="w-cli-no-signer").count() == 0


def test_load_duty_outbound_without_slice_fails(tmp_path):
    extract = tmp_path / "extract.csv"
    extract.write_text("row,one\n", encoding="utf-8")
    ns = build_parser().parse_args(
        [
            "load",
            "outbound",
            "--file",
            str(extract),
            "--waybill",
            "w-cli-no-slice",
            "--signer",
            "operator",
        ]
    )
    result = LoadDuty().run(ns)
    assert result.ok is False
    assert "slice" in result.summary
    assert CorridorLoad.objects.filter(waybill="w-cli-no-slice").count() == 0


def test_load_duty_outbound_with_slice_and_signer_succeeds(tmp_path):
    extract = tmp_path / "extract.csv"
    extract.write_text("row,one\n", encoding="utf-8")
    ns = build_parser().parse_args(
        [
            "load",
            "outbound",
            "--file",
            str(extract),
            "--waybill",
            "w-cli-signed",
            "--slice",
            "vendor-findings",
            "--signer",
            "operator",
        ]
    )
    result = LoadDuty().run(ns)
    assert result.ok is True
    assert result.details["status"] == "loaded"
    assert result.details["slice_name"] == "vendor-findings"
    assert result.details["signer"] == "operator"
    assert 'slice="vendor-findings"' in result.summary
    assert 'signer="operator"' in result.summary


def test_load_duty_waybill_over_length_cap_fails(tmp_path):
    """`CorridorLoad.waybill` is `CharField(max_length=128)`; SQLite (every
    test) never enforces that, PostgreSQL (the target deployment) does -- the
    same divergence `dashboard/audit.py` documents for `AuditEntry`. Reject
    in Python before the ORM ever sees it."""
    extract = tmp_path / "extract.csv"
    extract.write_text("row,one\n", encoding="utf-8")
    over_length_waybill = "w" * 129
    ns = build_parser().parse_args(["load", "inbound", "--file", str(extract), "--waybill", over_length_waybill])
    result = LoadDuty().run(ns)
    assert result.ok is False
    assert CorridorLoad.objects.filter(waybill=over_length_waybill).count() == 0


def test_load_duty_broken_corridor_config_fails(tmp_path):
    (tmp_path / "corridor.yaml").write_text("transports: not-a-mapping\n", encoding="utf-8")
    ns = build_parser().parse_args(["load", "--corridor", str(tmp_path)])
    result = LoadDuty().run(ns)
    assert result.ok is False


def test_load_duty_json_on_bare_invocation():
    ns = build_parser().parse_args(["load", "--json"])
    result = LoadDuty().run(ns)
    assert result.ok is True
    payload = json.loads(result.summary)
    assert payload["ok"] is True
    assert payload["transports"] == [
        {"name": "app-upload", "state": "on"},
        {"name": "shared-folder", "state": "off"},
        {"name": "email", "state": "off"},
    ]


def test_load_duty_json_on_missing_file_failure():
    ns = build_parser().parse_args(
        ["load", "--json", "inbound", "--file", "/nonexistent/path/does-not-exist.csv", "--waybill", "w"]
    )
    result = LoadDuty().run(ns)
    assert result.ok is False
    payload = json.loads(result.summary)
    assert payload["ok"] is False
    assert "message" in payload


# -- dashboard/corridor_load.py's own refusal/error branches --
#
# These call `record_corridor_load` directly (not through `load_extract`) to
# exercise the environmental-failure and data-failure paths its docstring
# promises: django missing, settings unconfigured, the model import failing,
# and the two ORM exception groups. Each uses a scoped `monkeypatch` (`sys.
# modules` entries or a manager method), restored automatically once the
# test returns -- no other test in this process observes the patch.


def test_record_corridor_load_refuses_when_django_is_not_importable(monkeypatch):
    monkeypatch.setitem(sys.modules, "django", None)
    result = corridor_load_module.record_corridor_load(
        direction="inbound", batch_sha="e" * 64, waybill="w-noimport", transport="app-upload"
    )
    assert result["status"] == "refused"


def test_record_corridor_load_refuses_when_settings_unconfigured(monkeypatch):
    monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)
    fake_conf = types.ModuleType("django.conf")
    fake_conf.settings = types.SimpleNamespace(configured=False)
    monkeypatch.setitem(sys.modules, "django.conf", fake_conf)
    result = corridor_load_module.record_corridor_load(
        direction="inbound", batch_sha="f" * 64, waybill="w-unset", transport="app-upload"
    )
    assert result["status"] == "refused"


def test_record_corridor_load_refuses_when_model_import_fails(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyforge.steward.dashboard.models", None)
    result = corridor_load_module.record_corridor_load(
        direction="inbound", batch_sha="g" * 64, waybill="w-modelimport", transport="app-upload"
    )
    assert result["status"] == "refused"


def test_record_corridor_load_refuses_on_operational_error(monkeypatch):
    def _raise_operational(**kwargs):
        raise OperationalError("db unreachable")

    monkeypatch.setattr(CorridorLoad.objects, "filter", _raise_operational)
    result = corridor_load_module.record_corridor_load(
        direction="inbound", batch_sha="h" * 64, waybill="w-opfail", transport="app-upload"
    )
    assert result["status"] == "refused"


def test_record_corridor_load_reports_error_on_data_error(monkeypatch):
    """A genuine data error (e.g. a value the DB itself rejects) at `.create()`
    stays `status: error` -- distinct from `IntegrityError`, which the race
    test below shows is recovered as idempotent instead."""

    class _EmptyQuerySet:
        def first(self):
            return None

    def _raise_data_error(**kwargs):
        raise DataError("value too long for type")

    monkeypatch.setattr(CorridorLoad.objects, "filter", lambda **kw: _EmptyQuerySet())
    monkeypatch.setattr(CorridorLoad.objects, "create", _raise_data_error)
    result = corridor_load_module.record_corridor_load(
        direction="inbound", batch_sha="i" * 64, waybill="w-dataerr", transport="app-upload"
    )
    assert result["status"] == "error"


def test_record_corridor_load_idempotent_on_concurrent_create_race(monkeypatch):
    """A genuine concurrent double-drop: `.filter().first()` misses (no row
    yet), but another writer's `.create()` lands first, so THIS call's own
    `.create()` hits the `UniqueConstraint` and raises `IntegrityError`. The
    loser of that race must still report the idempotent outcome the caller
    actually gets -- the WINNER's transport, not this call's -- never a
    generic `status: error`.
    """

    class _Miss:
        def first(self):
            return None

    class _Hit:
        def first(self):
            return types.SimpleNamespace(transport="app-upload", slice_name="", signer="")

    calls = {"n": 0}

    def _filter(**kwargs):
        calls["n"] += 1
        return _Miss() if calls["n"] == 1 else _Hit()

    def _raise_integrity(**kwargs):
        raise IntegrityError("unique constraint violated")

    monkeypatch.setattr(CorridorLoad.objects, "filter", _filter)
    monkeypatch.setattr(CorridorLoad.objects, "create", _raise_integrity)

    result = corridor_load_module.record_corridor_load(
        direction="inbound", batch_sha="k" * 64, waybill="w-race", transport="shared-folder"
    )
    assert result["status"] == "idempotent"
    assert result["transport"] == "app-upload"
    assert calls["n"] == 2


def test_record_corridor_load_persists_slice_name_and_signer():
    """Story 61.4: this module itself does not validate slice_name/signer
    (that is `load_extract`'s job) -- it simply persists and reports
    whatever it is given."""
    result = corridor_load_module.record_corridor_load(
        direction="outbound",
        batch_sha="r" * 64,
        waybill="w-record-signed",
        transport="app-upload",
        slice_name="vendor-findings",
        signer="operator",
    )
    assert result["status"] == "loaded"
    assert result["slice_name"] == "vendor-findings"
    assert result["signer"] == "operator"
    row = CorridorLoad.objects.get(direction="outbound", batch_sha="r" * 64, waybill="w-record-signed")
    assert row.slice_name == "vendor-findings"
    assert row.signer == "operator"


def test_record_corridor_load_idempotent_reports_originally_recorded_slice_and_signer():
    direction, sha, waybill = "outbound", "s" * 64, "w-record-signed-repeat"
    first = corridor_load_module.record_corridor_load(
        direction=direction,
        batch_sha=sha,
        waybill=waybill,
        transport="app-upload",
        slice_name="vendor-findings",
        signer="operator",
    )
    assert first["status"] == "loaded"

    second = corridor_load_module.record_corridor_load(
        direction=direction,
        batch_sha=sha,
        waybill=waybill,
        transport="app-upload",
        slice_name="a-different-slice",
        signer="a-different-signer",
    )
    assert second["status"] == "idempotent"
    assert second["slice_name"] == "vendor-findings"
    assert second["signer"] == "operator"


def test_record_corridor_load_idempotent_reports_originally_recorded_transport():
    """The idempotent payload's `transport` is the ORIGINALLY recorded one,
    never the one this call was invoked with -- a swap of `existing.
    transport` for the incoming parameter would pass every other test here,
    since they all repeat with the SAME transport both times."""
    direction, sha, waybill = "inbound", "l" * 64, "w-transport-provenance"
    first = corridor_load_module.record_corridor_load(
        direction=direction, batch_sha=sha, waybill=waybill, transport="app-upload"
    )
    assert first["status"] == "loaded"

    second = corridor_load_module.record_corridor_load(
        direction=direction, batch_sha=sha, waybill=waybill, transport="shared-folder"
    )
    assert second["status"] == "idempotent"
    assert second["transport"] == "app-upload"


# -- dashboard/admin.py's CorridorLoadAdmin --


def test_corridor_load_admin_is_read_only_with_declared_list_config():
    admin = CorridorLoadAdmin(CorridorLoad, AdminSite())
    assert admin.has_add_permission(None) is False
    assert admin.has_change_permission(None) is False
    assert admin.has_delete_permission(None) is False
    assert admin.list_display == (
        "direction",
        "waybill",
        "batch_sha",
        "transport",
        "slice_name",
        "signer",
        "loaded_at",
    )
    assert admin.list_filter == ("direction", "transport")
    assert admin.search_fields == ("batch_sha", "waybill", "slice_name", "signer")
    assert admin.ordering == ("-loaded_at",)


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


def test_cli_parses_load_outbound_with_slice_and_signer():
    ns = build_parser().parse_args(
        [
            "load",
            "outbound",
            "--file",
            "x",
            "--waybill",
            "w",
            "--slice",
            "vendor-findings",
            "--signer",
            "operator",
        ]
    )
    assert ns.duty == "load"
    assert ns.load_verb == "outbound"
    assert ns.slice_name == "vendor-findings"
    assert ns.signer == "operator"


def test_cli_parses_load_outbound_slice_and_signer_default_to_blank():
    """Default `""`, not argparse `required=True` -- a missing one is the
    duty layer's normal "refused" outcome, not a hard usage error."""
    ns = build_parser().parse_args(["load", "outbound", "--file", "x", "--waybill", "w"])
    assert ns.slice_name == ""
    assert ns.signer == ""
