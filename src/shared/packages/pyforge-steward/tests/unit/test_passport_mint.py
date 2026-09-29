"""Story 61.2 — vendor Work Passport identity: `mint_vendor_passport`,
`record_vendor_passport`, the `passport` duty, and its CLI wiring.

Needs the real migrated `WorkPassport` table (the `vendor_id` column added by
migration `0004_workpassport_vendor_id`), so this file drives `django.setup()`
+ `migrate` by hand exactly once per process, mirroring `test_corridor.py` /
`test_dashboard_admin_and_htmx.py`. Its `settings.configure()` block declares
the same fuller `INSTALLED_APPS` list those files use, since collection order
across an explicit multi-file pytest invocation is not guaranteed to put this
file last -- declaring the fuller list keeps it a superset that satisfies
every dashboard test file regardless of collection order, the same discipline
those files already document for each other.
"""

from __future__ import annotations

import json
import sys
import types

import pytest

# `passport_mint.py` is the module that genuinely needs django, so without the
# `[dashboard]` extra this file must SKIP, not raise a collection error (same
# rationale as the sibling dashboard test modules).
pytest.importorskip("django", reason="passport_mint.py requires pyforge-steward[dashboard]")

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

from django.db import DataError, IntegrityError  # noqa: E402

from pyforge.steward.cli import build_parser  # noqa: E402
from pyforge.steward.dashboard import passport_mint as passport_mint_module  # noqa: E402
from pyforge.steward.dashboard.models import WorkPassport  # noqa: E402
from pyforge.steward.dashboard.passport_sync import sync_work_passports_db  # noqa: E402
from pyforge.steward.passport import (  # noqa: E402
    PassportDuty,
    PassportMintError,
    mint_vendor_passport,
)
from pyforge.steward.sprint_ledger_query import WorkPassportItem  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_work_passports():
    """Isolate each test against the process-lifetime `:memory:` connection
    (no pytest-django transaction rollback here), mirroring
    `test_corridor.py`'s `_clean_corridor_loads`."""
    WorkPassport.objects.all().delete()
    yield
    WorkPassport.objects.all().delete()


# -- mint_vendor_passport --


def test_mint_vendor_passport_blank_vendor_id_raises():
    with pytest.raises(PassportMintError, match="vendor_id"):
        mint_vendor_passport(vendor_id="", jira_key="PROJ-1")


def test_mint_vendor_passport_requires_at_least_one_nickname():
    with pytest.raises(PassportMintError, match="nickname"):
        mint_vendor_passport(vendor_id="acme")


def test_mint_vendor_passport_whitespace_only_jira_key_is_treated_as_absent():
    """A whitespace-only string is not a real nickname -- must raise the same
    as an omitted one, not be accepted as truthy."""
    with pytest.raises(PassportMintError, match="nickname"):
        mint_vendor_passport(vendor_id="acme", jira_key="   ")


def test_mint_vendor_passport_strips_whitespace_padded_vendor_id():
    """`"  acme  "` and `"acme"` must mint under the SAME stored vendor_id --
    a copy-pasted argument with padding must not fragment the 'v1 is one
    vendor' invariant into two never-matching identities."""
    result = mint_vendor_passport(vendor_id="  acme  ", jira_key="PROJ-strip")
    assert result["status"] == "minted"
    assert result["vendor_id"] == "acme"
    row = WorkPassport.objects.get(passport_id=result["passport_id"])
    assert row.vendor_id == "acme"


def test_mint_vendor_passport_refuses_when_dashboard_extra_not_importable(monkeypatch):
    """The spec's stated AC: `[dashboard]` not installed -> `status: refused`,
    exercised through `mint_vendor_passport` itself (not `record_vendor_passport`
    directly) -- `importlib.import_module` is what actually fails here."""
    monkeypatch.setitem(sys.modules, "pyforge.steward.dashboard.passport_mint", None)
    result = mint_vendor_passport(vendor_id="acme", jira_key="PROJ-1")
    assert result["status"] == "refused"


# -- record_vendor_passport --


def test_record_vendor_passport_happy_path_with_only_jira_key():
    result = passport_mint_module.record_vendor_passport(
        vendor_id="acme", jira_key="PROJ-100", github_item_id=None, title="Only Jira"
    )
    assert result["status"] == "minted"
    assert result["jira_key"] == "PROJ-100"
    assert result["github_item_id"] is None
    row = WorkPassport.objects.get(passport_id=result["passport_id"])
    assert row.vendor_id == "acme"
    assert row.jira_key == "PROJ-100"
    assert row.title == "Only Jira"


def test_record_vendor_passport_happy_path_with_only_github_item_id():
    result = passport_mint_module.record_vendor_passport(
        vendor_id="acme", jira_key=None, github_item_id="GH-200", title="Only GH"
    )
    assert result["status"] == "minted"
    assert result["github_item_id"] == "GH-200"
    assert result["jira_key"] is None
    row = WorkPassport.objects.get(passport_id=result["passport_id"])
    assert row.title == "Only GH"


def test_record_vendor_passport_identical_repeat_creates_two_distinct_rows():
    """The I/O Matrix's one required scenario: two mint calls with the same
    `vendor_id` and `jira_key` never merge -- two rows, two distinct
    `passport_id`s, both present."""
    first = passport_mint_module.record_vendor_passport(
        vendor_id="acme", jira_key="PROJ-DUP", github_item_id=None, title=""
    )
    second = passport_mint_module.record_vendor_passport(
        vendor_id="acme", jira_key="PROJ-DUP", github_item_id=None, title=""
    )
    assert first["status"] == "minted"
    assert second["status"] == "minted"
    assert first["passport_id"] != second["passport_id"]
    rows = WorkPassport.objects.filter(vendor_id="acme", jira_key="PROJ-DUP")
    assert rows.count() == 2
    assert {r.passport_id for r in rows} == {first["passport_id"], second["passport_id"]}


def test_record_vendor_passport_reports_error_on_data_error(monkeypatch):
    """A genuine data error at `.create()` stays `status: error` -- distinct
    from `status: refused`, an environmental failure."""

    def _raise_data_error(**kwargs):
        raise DataError("value too long for type")

    monkeypatch.setattr(WorkPassport.objects, "create", _raise_data_error)
    result = passport_mint_module.record_vendor_passport(
        vendor_id="acme", jira_key="PROJ-dataerr", github_item_id=None, title=""
    )
    assert result["status"] == "error"


def test_record_vendor_passport_reports_error_on_integrity_error(monkeypatch):
    """Unlike `corridor_load.record_corridor_load`'s idempotent-race recovery,
    an `IntegrityError` here is a genuine `status: error` -- there is no
    lookup-then-create to recover from; every call mints a fresh UUID."""

    def _raise_integrity_error(**kwargs):
        raise IntegrityError("constraint violated")

    monkeypatch.setattr(WorkPassport.objects, "create", _raise_integrity_error)
    result = passport_mint_module.record_vendor_passport(
        vendor_id="acme", jira_key="PROJ-integrityerr", github_item_id=None, title=""
    )
    assert result["status"] == "error"


def test_record_vendor_passport_refuses_when_django_is_not_importable(monkeypatch):
    monkeypatch.setitem(sys.modules, "django", None)
    result = passport_mint_module.record_vendor_passport(
        vendor_id="acme", jira_key="PROJ-1", github_item_id=None, title=""
    )
    assert result["status"] == "refused"


def test_record_vendor_passport_refuses_when_settings_unconfigured(monkeypatch):
    monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)
    fake_conf = types.ModuleType("django.conf")
    fake_conf.settings = types.SimpleNamespace(configured=False)
    monkeypatch.setitem(sys.modules, "django.conf", fake_conf)
    result = passport_mint_module.record_vendor_passport(
        vendor_id="acme", jira_key="PROJ-1", github_item_id=None, title=""
    )
    assert result["status"] == "refused"


def test_record_vendor_passport_refuses_when_model_import_fails(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyforge.steward.dashboard.models", None)
    result = passport_mint_module.record_vendor_passport(
        vendor_id="acme", jira_key="PROJ-1", github_item_id=None, title=""
    )
    assert result["status"] == "refused"


# -- the identity rule holds for the pre-existing internal-mint path too --


def test_internal_mint_row_is_unaffected_by_the_new_vendor_id_column():
    """AC: an existing internal-mint `WorkPassport` row (created by
    `sprint_ledger_query.py`'s ledger sync, no `vendor_id`) is unaffected by
    this story's schema addition -- `vendor_id` reads `None` and the row still
    round-trips through `sync_work_passports_db`."""
    story = WorkPassportItem(
        passport_id="internal-uuid-1",
        story_id="1.1",
        station="pyforge-steward",
        epic_id="1",
        title="Internal Story",
        status="done",
        jira_key=None,
        github_item_id=None,
        effort="S",
    )
    res = sync_work_passports_db([story])
    assert res["status"] == "success"
    row = WorkPassport.objects.get(passport_id="internal-uuid-1")
    assert row.vendor_id is None


# -- PassportDuty.run() --


def test_passport_duty_bare_invocation_refuses_without_touching_db():
    ns = build_parser().parse_args(["passport"])
    result = PassportDuty().run(ns)
    assert result.ok is False
    assert "verb is required" in result.summary
    assert WorkPassport.objects.count() == 0


def test_passport_duty_mint_happy_path():
    ns = build_parser().parse_args(["passport", "mint", "--vendor-id", "acme", "--jira-key", "PROJ-9"])
    result = PassportDuty().run(ns)
    assert result.ok is True
    assert "minted passport_id=" in result.summary
    assert WorkPassport.objects.filter(vendor_id="acme", jira_key="PROJ-9").count() == 1


def test_passport_duty_mint_neither_key_fails():
    ns = build_parser().parse_args(["passport", "mint", "--vendor-id", "acme"])
    result = PassportDuty().run(ns)
    assert result.ok is False
    assert "nickname" in result.summary
    assert WorkPassport.objects.count() == 0


def test_passport_duty_mint_blank_vendor_id_fails():
    """The `PassportMintError` path is not just exercised through
    `mint_vendor_passport` directly -- it must also survive `PassportDuty.
    run()`'s try/except-to-`DutyResult` conversion."""
    ns = build_parser().parse_args(["passport", "mint", "--vendor-id", "", "--jira-key", "PROJ-1"])
    result = PassportDuty().run(ns)
    assert result.ok is False


def test_passport_duty_json_on_success():
    ns = build_parser().parse_args(["passport", "--json", "mint", "--vendor-id", "acme", "--jira-key", "PROJ-json-1"])
    result = PassportDuty().run(ns)
    assert result.ok is True
    payload = json.loads(result.summary)
    assert payload["status"] == "minted"
    assert payload["vendor_id"] == "acme"


def test_passport_duty_json_on_failure():
    ns = build_parser().parse_args(["passport", "--json", "mint", "--vendor-id", "acme"])
    result = PassportDuty().run(ns)
    assert result.ok is False
    payload = json.loads(result.summary)
    assert payload["status"] == "error"
    assert "message" in payload


# -- CLI parsing --


def test_cli_parses_passport_mint_with_expected_namespace():
    ns = build_parser().parse_args(["passport", "mint", "--vendor-id", "acme", "--jira-key", "PROJ-1"])
    assert ns.duty == "passport"
    assert ns.passport_verb == "mint"
    assert ns.vendor_id == "acme"
    assert ns.jira_key == "PROJ-1"
    assert ns.github_item_id is None
    assert ns.title == ""
    assert ns.json is False


def test_cli_passport_mint_requires_vendor_id():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["passport", "mint", "--jira-key", "PROJ-1"])
