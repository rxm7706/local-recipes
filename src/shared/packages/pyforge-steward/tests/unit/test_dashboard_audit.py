"""Story 9.3 — `record_audit_entry` / `query_audit_entries` / `purge_expired_entries`
against a REAL migrated SQLite database (no `pytest-django` in this
environment, so `django.setup()` + `call_command("migrate", ...)` are driven
by hand, exactly once per process).

This is also the package's first proof that `pyforge.steward.dashboard`
actually LOADS in Django's app registry and its migration applies with no
error: the prior story's AD-13 test
(`test_dashboard_appconfig_is_ad13_compliant`, `tests/meta/test_invariants.py`)
only ever checked class attributes on `DashboardConfig`, because no model
existed yet to force the question. The `django.setup()` + `migrate` call
below IS that proof — if the app failed to register, or the migration
failed to apply, every test in this module would already have failed at
IMPORT time, before any test body ran. `test_dashboard_app_registers_and_
migration_applied` below makes that implicit proof explicit and
inspectable rather than leaving it merely implied.
"""

from __future__ import annotations

import datetime as dt

import pytest

# `audit.py`/`models.py` are the two modules besides `apps.py`/`cache.py` that
# genuinely need django, so without the `[dashboard]` extra this file must
# SKIP, not raise a collection error (same rationale as test_dashboard_cache.py).
pytest.importorskip("django", reason="audit.py requires pyforge-steward[dashboard]")

import django  # noqa: E402
from django.conf import settings  # noqa: E402

_DASHBOARD_APP = "pyforge.steward.dashboard"
_INSTALLED_APPS = [_DASHBOARD_APP]
_DATABASE_ENGINE = "django.db.backends.sqlite3"
_DATABASE_NAME = ":memory:"

# Django settings can only be configured ONCE per process, and multiple test
# files may collect in the same pytest run. This file collects alphabetically
# BEFORE `test_dashboard_cache.py` (`audit` < `cache`), so in a full-suite run
# it normally wins the one-shot `settings.configure()` race -- but `CACHES`
# is included here too, matching `test_dashboard_cache.py`'s own declaration
# (and vice versa, review pass 1: `test_dashboard_cache.py` declares this
# file's `INSTALLED_APPS`/`DATABASES` right back), so whichever module wins
# the race leaves settings that satisfy both -- not because an audit trail
# test has anything to do with caching.
if not settings.configured:
    settings.configure(
        INSTALLED_APPS=_INSTALLED_APPS,
        DATABASES={"default": {"ENGINE": _DATABASE_ENGINE, "NAME": _DATABASE_NAME}},
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "pyforge-steward-dashboard-test",
            },
        },
        USE_TZ=True,
    )

# Whether this module won the settings-configuration race above or another
# module already configured settings first, assert the configuration ACTUALLY
# IN FORCE is the one this file needs -- a mismatch fails loudly here rather
# than this file's tests silently running against the wrong app registry /
# database (same defensive pattern as test_dashboard_cache.py's
# `_fresh_backend()`).
#
# These asserts run BEFORE `django.setup()`/`migrate` (review pass 2). They
# used to run after, which made them useless as a safety check for the case
# that matters most: if some other module had configured a FILE-BACKED
# sqlite `NAME`, `migrate` had already created tables in that real database
# -- and the autouse `_clean_audit_trail` fixture below would then run
# `DELETE FROM ...auditentry` against it, twice per test -- before any assert
# got a chance to complain. `NAME` is checked too, for the same reason: the
# engine matching says nothing about WHICH sqlite database is about to be
# migrated and truncated.
#
# `INSTALLED_APPS` is checked by containment, not equality: this file needs
# the dashboard app registered, and nothing about it requires that no other
# app be present. The former exact-equality assert coupled this file to
# `test_dashboard_cache.py`'s duplicate `settings.configure()` block by hand
# -- edit the list in one file only and the run either passed or died with a
# module-scope AssertionError during collection, depending on which module
# won the one-shot race.
assert _DASHBOARD_APP in settings.INSTALLED_APPS, (
    f"another test module configured Django settings first: INSTALLED_APPS "
    f"is {list(settings.INSTALLED_APPS)!r}, which does not include "
    f"{_DASHBOARD_APP!r} -- this file needs it registered to migrate and "
    f"query AuditEntry"
)
# Subscripted through `.get()`, not `[...]` (review pass 3): a module that
# calls `settings.configure()` without DATABASES at all -- verbatim the
# scenario the comment above describes, and what `test_dashboard_cache.py`
# itself used to do -- leaves `settings.DATABASES == {}`, so
# `settings.DATABASES["default"]` raised a bare `KeyError: 'default'` before
# either message below could be built. The guards added to name that
# misconfiguration did not name it.
assert settings.DATABASES.get("default", {}).get("ENGINE") == _DATABASE_ENGINE, (
    f"another test module configured Django settings first: "
    f"DATABASES['default']['ENGINE'] is "
    f"{settings.DATABASES.get('default', {}).get('ENGINE')!r}, not "
    f"{_DATABASE_ENGINE!r}"
)
assert settings.DATABASES.get("default", {}).get("NAME") == _DATABASE_NAME, (
    f"another test module configured Django settings first: "
    f"DATABASES['default']['NAME'] is "
    f"{settings.DATABASES.get('default', {}).get('NAME')!r}, not "
    f"{_DATABASE_NAME!r} "
    f"-- this file migrates and truncates whatever database is configured, "
    f"so it refuses to run against anything but an in-memory one"
)
# `USE_TZ` too (review pass 4). The guards above named the app registry and
# the database and stopped there, omitting the one setting this module's
# entire datetime contract turns on: `_check_reference_datetime` matches
# against whatever `timezone.now()` itself returns, so under a `USE_TZ=False`
# configuration won by another module, three tests here
# (`..._rejects_a_naive_occurred_at...`, `..._rejects_a_naive_now...`,
# `..._rejects_a_naive_datetime_filter...`) fail with a bare
# `DID NOT RAISE ValueError` -- verbatim the "nondeterministic failure whose
# cause lives in another file" the INSTALLED_APPS guard above exists to
# prevent, left standing for the setting that matters most here. Simulated by
# execution.
assert settings.USE_TZ is True, (
    f"another test module configured Django settings first: USE_TZ is "
    f"{settings.USE_TZ!r}, not True -- this file's naive/aware refusal tests "
    f"are all written against an aware deployment and silently stop refusing "
    f"anything without it"
)

# `django.setup()` and `migrate` run UNCONDITIONALLY, never gated behind the
# `settings.configured` guard above (review pass 1): both are idempotent
# (`django.setup()` no-ops once the app registry is ready; a second
# `migrate` reports "no migrations to apply" rather than erroring), and this
# file's own AuditEntry queries need the app registered and the table
# created regardless of which module's `settings.configure()` call actually
# won the race -- gating them the same way `settings.configure()` itself
# must be gated would silently skip both whenever `test_dashboard_cache.py`
# configures first, leaving every query in this file failing with
# `AppRegistryNotReady`/`OperationalError: no such table`.
django.setup()

from django.core.management import call_command  # noqa: E402

call_command("migrate", run_syncdb=True, verbosity=0)

from django.utils import timezone  # noqa: E402

from pyforge.steward.dashboard.audit import (  # noqa: E402
    _FUTURE_NOW_TOLERANCE,
    _max_row_count,
    purge_expired_entries,
    query_audit_entries,
    record_audit_entry,
)
from pyforge.steward.dashboard.declarations import (  # noqa: E402
    _MAX_RETENTION_DAYS,
    AuditRetention,
)
from pyforge.steward.dashboard.models import AuditAction, AuditEntry  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_audit_trail():
    """Isolate each test: the `:memory:` sqlite connection Django opened for
    the `migrate` call above is reused for the whole process (there is no
    pytest-django transaction-rollback fixture here), so rows from one test
    would otherwise leak into the next.
    """
    AuditEntry.objects.all().delete()
    yield
    AuditEntry.objects.all().delete()


def test_dashboard_app_registers_and_migration_applied():
    """Explicit, inspectable version of the proof this module's import-time
    `django.setup()` + `migrate` already gives implicitly (see module
    docstring) -- closes the proof-strength gap the deferred-work ledger
    names against `test_dashboard_appconfig_is_ad13_compliant`.
    """
    from django.apps import apps

    app_config = apps.get_app_config("pyforge_steward_dashboard")
    assert app_config.name == "pyforge.steward.dashboard"
    assert app_config.get_model("AuditEntry") is AuditEntry


# --- record_audit_entry ------------------------------------------------


def test_record_audit_entry_writes_one_row_with_the_given_fields():
    before = timezone.now()
    entry = record_audit_entry("alice", "east", AuditAction.LOAD, 42)
    after = timezone.now()

    assert AuditEntry.objects.count() == 1
    row = AuditEntry.objects.get(pk=entry.pk)
    assert row.actor == "alice"
    assert row.role == "east"
    assert row.action == AuditAction.LOAD
    assert row.target == ""
    assert row.row_count == 42
    assert before <= row.occurred_at <= after


def test_record_audit_entry_stores_a_none_role_as_null():
    entry = record_audit_entry("alice", None, AuditAction.NAVIGATE, 0)

    row = AuditEntry.objects.get(pk=entry.pk)
    assert row.role is None
    assert row.row_count == 0


def test_record_audit_entry_rejects_a_blank_actor():
    with pytest.raises(ValueError, match="actor"):
        record_audit_entry("", "east", AuditAction.LOAD, 1)
    with pytest.raises(ValueError, match="actor"):
        record_audit_entry("   ", "east", AuditAction.LOAD, 1)
    assert AuditEntry.objects.count() == 0


def test_record_audit_entry_accepts_an_actor_at_exactly_the_length_cap():
    # Derived, not the literal 255 (review pass 3): the rejection test below
    # already reads the cap off the column, and hard-coding it here means
    # narrowing `AuditEntry.actor` turns this into a confusing ValueError
    # failure that reads as a guard regression rather than a column change.
    cap = AuditEntry._meta.get_field("actor").max_length
    entry = record_audit_entry("x" * cap, None, AuditAction.LOAD, 1)
    assert AuditEntry.objects.get(pk=entry.pk).actor == "x" * cap


def test_record_audit_entry_rejects_a_negative_row_count():
    with pytest.raises(ValueError, match="row_count"):
        record_audit_entry("alice", "east", AuditAction.LOAD, -1)
    assert AuditEntry.objects.count() == 0


def test_record_audit_entry_accepts_a_zero_row_count():
    entry = record_audit_entry("alice", "east", AuditAction.LOAD, 0)
    assert AuditEntry.objects.get(pk=entry.pk).row_count == 0


def test_record_audit_entry_rejects_a_blank_non_none_role():
    """`role=None` is the legitimate "no role established" state; a blank
    or whitespace-only STRING role is a different, unanswerable spelling of
    the same problem `actor`'s blank check exists to prevent.
    """
    with pytest.raises(ValueError, match="role"):
        record_audit_entry("alice", "   ", AuditAction.LOAD, 1)
    assert AuditEntry.objects.count() == 0


def test_record_audit_entry_stores_actor_role_target_verbatim():
    """CAP-4: the trail records what was actually presented, never a
    normalized reinterpretation -- no trim, case-fold, or Unicode
    normalization of actor/role/target.
    """
    entry = record_audit_entry("  Alice.Admin  ", " East ", AuditAction.FILTER, 5, target=" Sales ")
    row = AuditEntry.objects.get(pk=entry.pk)
    assert row.actor == "  Alice.Admin  "
    assert row.role == " East "
    assert row.target == " Sales "


def test_record_audit_entry_defaults_target_to_empty_string_not_none():
    entry = record_audit_entry("alice", "east", AuditAction.NAVIGATE, 0)
    row = AuditEntry.objects.get(pk=entry.pk)
    assert row.target == ""
    assert row.target is not None


def test_record_audit_entry_accepts_an_explicit_occurred_at():
    when = timezone.now() - dt.timedelta(days=5)
    entry = record_audit_entry("alice", "east", AuditAction.LOAD, 1, occurred_at=when)
    row = AuditEntry.objects.get(pk=entry.pk)
    assert row.occurred_at == when


# --- query_audit_entries -------------------------------------------------


def test_query_audit_entries_returns_prior_rows_and_records_its_own_read():
    record_audit_entry("alice", "east", AuditAction.LOAD, 10)
    record_audit_entry("alice", "east", AuditAction.FILTER, 4)
    record_audit_entry("bob", "west", AuditAction.NAVIGATE, 0)

    rows = query_audit_entries(reader_actor="bob", reader_role="auditor")

    assert isinstance(rows, list)
    assert len(rows) == 3
    assert {row.actor for row in rows} == {"alice", "bob"}

    all_rows = list(AuditEntry.objects.all())
    assert len(all_rows) == 4, "reading the trail must itself be recorded as a 4th entry (AD-7)"
    read_entry = AuditEntry.objects.get(action=AuditAction.AUDIT_READ)
    assert read_entry.actor == "bob"
    assert read_entry.role == "auditor"
    assert read_entry.target == "audit_trail"
    assert read_entry.row_count == 3


def test_query_audit_entries_applies_keyword_filters():
    record_audit_entry("alice", "east", AuditAction.LOAD, 10)
    record_audit_entry("bob", "west", AuditAction.LOAD, 5)

    rows = query_audit_entries(reader_actor="carol", reader_role=None, actor="alice")

    assert len(rows) == 1
    assert rows[0].actor == "alice"

    # The read of the filtered subset is still recorded with the FULL
    # returned count (1), not the trail's total row count.
    read_entry = AuditEntry.objects.get(action=AuditAction.AUDIT_READ)
    assert read_entry.row_count == 1
    assert read_entry.actor == "carol"
    assert read_entry.role is None


def test_query_audit_entries_on_an_empty_trail_still_records_a_zero_row_read():
    rows = query_audit_entries(reader_actor="bob", reader_role="auditor")

    assert rows == []
    read_entry = AuditEntry.objects.get()
    assert read_entry.action == AuditAction.AUDIT_READ
    assert read_entry.row_count == 0


# --- purge_expired_entries -------------------------------------------------


def test_purge_expired_entries_deletes_only_rows_older_than_the_cutoff():
    now = timezone.now()
    old = record_audit_entry("alice", "east", AuditAction.LOAD, 1, occurred_at=now - dt.timedelta(days=40))
    recent = record_audit_entry("alice", "east", AuditAction.LOAD, 2, occurred_at=now - dt.timedelta(days=10))

    deleted = purge_expired_entries(AuditRetention(days=30), now=now)

    assert deleted == 1
    remaining = list(AuditEntry.objects.all())
    assert len(remaining) == 1
    assert remaining[0].pk == recent.pk
    assert not AuditEntry.objects.filter(pk=old.pk).exists()


def test_purge_expired_entries_returns_zero_when_nothing_is_older_than_the_cutoff():
    now = timezone.now()
    record_audit_entry("alice", "east", AuditAction.LOAD, 1, occurred_at=now - dt.timedelta(days=1))

    deleted = purge_expired_entries(AuditRetention(days=30), now=now)

    assert deleted == 0
    assert AuditEntry.objects.count() == 1


def test_purge_expired_entries_requires_a_retention_argument():
    """AD-7: no default value anywhere for `retention` -- proves the refusal
    is a property of the function's own SIGNATURE, not a runtime check a
    caller could route around.
    """
    with pytest.raises(TypeError):
        purge_expired_entries()  # type: ignore[call-arg]


def test_purge_expired_entries_rejects_a_non_audit_retention_object():
    with pytest.raises(TypeError, match="AuditRetention"):
        purge_expired_entries(retention=30)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_days", [0, -5])
def test_audit_retention_rejects_a_non_positive_days_value(bad_days):
    """The declaration half of AD-7's refusal -- construction-time
    validation, not caught only once `purge_expired_entries` is called.
    Also pinned in `test_dashboard_declarations.py`; repeated here so this
    file's matrix coverage is self-contained against the real DB context.
    """
    with pytest.raises(ValueError, match="days"):
        AuditRetention(days=bad_days)


def test_purge_expired_entries_leaves_a_row_exactly_at_the_cutoff():
    """`occurred_at__lt=cutoff` is strictly less-than: a row exactly AT the
    cutoff survives one more cycle, by design -- pinned so a future change
    to `__lte` is a deliberate decision, not an accidental off-by-one.
    """
    now = timezone.now()
    cutoff_days = 30
    at_cutoff = record_audit_entry(
        "alice",
        "east",
        AuditAction.LOAD,
        1,
        occurred_at=now - dt.timedelta(days=cutoff_days),
    )

    deleted = purge_expired_entries(AuditRetention(days=cutoff_days), now=now)

    assert deleted == 0
    assert AuditEntry.objects.filter(pk=at_cutoff.pk).exists()


# --- action / row_count / occurred_at validation -------------------------


def test_record_audit_entry_rejects_an_unrecognized_action():
    with pytest.raises(ValueError, match="action"):
        record_audit_entry("alice", "east", "not-a-real-action", 1)
    assert AuditEntry.objects.count() == 0


@pytest.mark.parametrize("action", list(AuditAction.values))
def test_record_audit_entry_accepts_every_declared_action(action):
    entry = record_audit_entry("alice", "east", action, 1)
    assert AuditEntry.objects.get(pk=entry.pk).action == action


def test_record_audit_entry_rejects_a_bool_row_count():
    """`bool` is an `int` subclass, and `True < 0`/`False < 0` are both
    `False`, so a boolean flag passed by mistake would otherwise sail
    through the plain `row_count < 0` check as `row_count=1`/`0`.
    """
    with pytest.raises(TypeError, match="row_count"):
        record_audit_entry("alice", "east", AuditAction.LOAD, True)
    with pytest.raises(TypeError, match="row_count"):
        record_audit_entry("alice", "east", AuditAction.LOAD, False)
    assert AuditEntry.objects.count() == 0


def test_record_audit_entry_rejects_a_row_count_over_positiveintegerfields_ceiling():
    with pytest.raises(ValueError, match="row_count"):
        record_audit_entry("alice", "east", AuditAction.LOAD, _max_row_count() + 1)
    assert AuditEntry.objects.count() == 0


def test_record_audit_entry_accepts_a_row_count_at_positiveintegerfields_ceiling():
    ceiling = _max_row_count()
    assert ceiling == 2_147_483_647, "PositiveIntegerField's documented ceiling"
    entry = record_audit_entry("alice", "east", AuditAction.LOAD, ceiling)
    assert AuditEntry.objects.get(pk=entry.pk).row_count == ceiling


def test_the_row_count_ceiling_tracks_the_model_column_it_mirrors():
    """`row_count`'s bound cannot drift from its column, same as the string caps.

    Hand-copied, `2_147_483_647` kept admitting 2-billion values into a
    column narrowed to `PositiveSmallIntegerField` (PostgreSQL ceiling
    32,767) -- SQLite accepts them, PostgreSQL does not, which is the
    dev/prod asymmetry this module's Python-side checks exist to close. This
    swaps the field's own type and asserts the guard follows; with a copied
    constant it fails, because `row_count=40_000` is recorded rather than
    refused.
    """
    field = AuditEntry._meta.get_field("row_count")
    original = field.get_internal_type
    field.get_internal_type = lambda: "PositiveSmallIntegerField"
    try:
        assert _max_row_count() == 32_767
        with pytest.raises(ValueError, match="row_count"):
            record_audit_entry("alice", "east", AuditAction.LOAD, 40_000)
    finally:
        field.get_internal_type = original

    assert AuditEntry.objects.count() == 0
    assert _max_row_count() == 2_147_483_647, "nothing leaks out of this test"


def test_every_declared_action_value_fits_the_column_it_is_written_to():
    """A sixth `AuditAction` longer than the column would pass every test.

    `action` is vocabulary-checked but not length-checked (an over-long
    value is unreachable while every declared value fits), and SQLite
    enforces no `VARCHAR(n)`, so `test_record_audit_entry_accepts_every_
    declared_action` would stay green while PostgreSQL adopters failed at
    runtime on the primitive every load/filter/navigate/export calls. This
    is where that gets caught -- in CI, not in production.
    """
    cap = AuditEntry._meta.get_field("action").max_length
    too_long = [value for value in AuditAction.values if len(value) > cap]
    assert not too_long, (
        f"AuditAction values {too_long!r} exceed AuditEntry.action's "
        f"max_length={cap} -- widen the column (and regenerate the "
        f"migration) or shorten the value"
    )


def test_record_audit_entry_rejects_a_non_string_actor():
    with pytest.raises(TypeError, match="actor"):
        record_audit_entry(123, "east", AuditAction.LOAD, 1)
    assert AuditEntry.objects.count() == 0


def test_record_audit_entry_rejects_a_non_string_role():
    with pytest.raises(TypeError, match="role"):
        record_audit_entry("alice", 123, AuditAction.LOAD, 1)
    assert AuditEntry.objects.count() == 0


def test_record_audit_entry_rejects_a_naive_occurred_at_under_use_tz_true():
    """This suite configures `USE_TZ=True`, so `timezone.now()` returns an
    AWARE datetime -- a naive one passed explicitly must be rejected rather
    than silently misinterpreted (Django would otherwise only emit a
    `RuntimeWarning` and shift the stored instant by the local UTC offset).
    """
    naive = dt.datetime(2026, 1, 1, 12, 0, 0)
    with pytest.raises(ValueError, match="occurred_at"):
        record_audit_entry("alice", "east", AuditAction.LOAD, 1, occurred_at=naive)
    assert AuditEntry.objects.count() == 0


def test_purge_expired_entries_rejects_a_naive_now_under_use_tz_true():
    naive = dt.datetime(2026, 1, 1, 12, 0, 0)
    with pytest.raises(ValueError, match="now"):
        purge_expired_entries(AuditRetention(days=30), now=naive)


# --- ordering --------------------------------------------------------------


def test_query_audit_entries_returns_rows_most_recent_first():
    now = timezone.now()
    oldest = record_audit_entry("alice", "east", AuditAction.LOAD, 1, occurred_at=now - dt.timedelta(days=2))
    middle = record_audit_entry("alice", "east", AuditAction.LOAD, 1, occurred_at=now - dt.timedelta(days=1))
    newest = record_audit_entry("alice", "east", AuditAction.LOAD, 1, occurred_at=now)

    rows = query_audit_entries(reader_actor="bob", reader_role="auditor")

    assert [row.pk for row in rows] == [newest.pk, middle.pk, oldest.pk]


def test_rows_sharing_an_occurred_at_still_come_back_in_one_stable_order():
    """`Meta.ordering`'s `-id` tiebreaker (review pass 2).

    With `["-occurred_at"]` alone, rows with an identical timestamp fell
    back to whatever the query plan produced: the `.filter(actor=...)` path
    (which can use the `actor` index) and the unfiltered path disagreed on
    SQLite -- so `query_audit_entries()` and
    `query_audit_entries(actor=...)` returned the same rows in OPPOSITE
    orders. Pinned here on the two paths that actually disagreed.
    """
    stamp = timezone.now()
    created = [record_audit_entry("alice", "east", AuditAction.LOAD, i, occurred_at=stamp).pk for i in range(6)]
    newest_first = list(reversed(created))

    assert [row.pk for row in AuditEntry.objects.all()] == newest_first
    assert [row.pk for row in AuditEntry.objects.filter(actor="alice")] == newest_first


# --- audit-of-the-audit integrity ------------------------------------------


def test_query_audit_entries_rejects_a_blank_reader_before_reading_anything():
    """AD-7: a read that cannot be recorded must not happen at all.

    Previously the rows were fetched FIRST and the reader validated only
    once `record_audit_entry` ran, so a blank `reader_actor` produced a
    full read of the trail followed by a `ValueError` -- an unrecorded
    read, repeatable indefinitely by a caller iterating filter shapes.

    Asserting "no `AUDIT_READ` row was written" is NOT enough to pin this:
    that was already true of the broken version, which simply crashed
    before writing. What changed is that the SELECT never executes at all,
    so this counts the queries.
    """
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    record_audit_entry("alice", "east", AuditAction.LOAD, 3)

    with CaptureQueriesContext(connection) as captured:
        with pytest.raises(ValueError, match="actor"):
            query_audit_entries(reader_actor="   ", reader_role=None)

    assert captured.captured_queries == [], "a read that cannot be recorded must not touch the database at all"
    assert not AuditEntry.objects.filter(action=AuditAction.AUDIT_READ).exists()
    assert AuditEntry.objects.count() == 1, "the pre-existing row must be untouched"


def test_query_audit_entries_rejects_a_non_string_reader_actor():
    with pytest.raises(TypeError, match="actor"):
        query_audit_entries(reader_actor=123, reader_role=None)
    assert AuditEntry.objects.count() == 0


def test_query_audit_entries_rejects_a_blank_non_none_reader_role():
    with pytest.raises(ValueError, match="role"):
        query_audit_entries(reader_actor="bob", reader_role="  ")
    assert AuditEntry.objects.count() == 0


def test_a_failed_read_leaves_no_partial_state_behind():
    """A misspelled filter keyword raises `FieldError` from the query itself.

    Reader validation cannot catch this one — the reader is valid — so what
    holds here is that a query that never returned rows also never records
    having returned any, and the `transaction.atomic()` wrapping keeps that
    true for any write a future filter path might add.
    """
    from django.core.exceptions import FieldError

    record_audit_entry("alice", "east", AuditAction.LOAD, 3)

    with pytest.raises(FieldError):
        query_audit_entries(reader_actor="mallory", reader_role=None, actro="alice")

    assert AuditEntry.objects.count() == 1
    assert not AuditEntry.objects.filter(actor="mallory").exists()


# --- dev/prod parity guards -------------------------------------------------


@pytest.mark.parametrize("field", ["actor", "role", "target"])
def test_record_audit_entry_rejects_a_nul_byte_in_any_string_field(field):
    """SQLite stores `\\x00` inside a TEXT value; PostgreSQL refuses the write.

    Left unchecked, a call green in every dev test raises in production --
    on the request path, since this is the primitive every load/filter/
    navigate/export calls.
    """
    kwargs = {"actor": "alice", "role": "east", "target": "sales"}
    kwargs[field] = kwargs[field] + "\x00x"
    with pytest.raises(ValueError, match="NUL"):
        record_audit_entry(kwargs["actor"], kwargs["role"], AuditAction.LOAD, 1, target=kwargs["target"])
    assert AuditEntry.objects.count() == 0


def test_record_audit_entry_rejects_a_non_string_target():
    with pytest.raises(TypeError, match="target"):
        record_audit_entry("alice", "east", AuditAction.LOAD, 1, target=123)
    assert AuditEntry.objects.count() == 0


@pytest.mark.parametrize("field", ["actor", "role", "target"])
def test_record_audit_entry_rejects_a_value_over_the_field_cap(field):
    """Every string field's cap, refused rather than truncated.

    `role` and `target` are covered here alongside `actor`: the three
    checks are structurally identical, so leaving two of them unpinned let
    a future edit drop one with a green suite.
    """
    cap = AuditEntry._meta.get_field(field).max_length
    overlong = "x" * (cap + 1)
    calls = {
        "actor": lambda: record_audit_entry(overlong, None, AuditAction.LOAD, 1),
        "role": lambda: record_audit_entry("alice", overlong, AuditAction.LOAD, 1),
        "target": lambda: record_audit_entry("alice", None, AuditAction.LOAD, 1, target=overlong),
    }

    with pytest.raises(ValueError, match=rf"{field}.*{cap}-character"):
        calls[field]()
    assert AuditEntry.objects.count() == 0


def test_the_python_length_cap_tracks_the_model_column_it_mirrors():
    """The cap in `audit.py` and `AuditEntry`'s column cannot drift apart.

    A hand-copied `255` kept them equal only by comment, and no test could
    tell the difference while both happened to say 255 -- so this narrows
    the model column and asserts the Python guard follows it. With a copied
    constant this fails: a 9-character actor sails past a stale 255 into a
    column PostgreSQL has narrowed to 8, which SQLite would accept and
    PostgreSQL would reject.
    """
    field = AuditEntry._meta.get_field("actor")
    original = field.max_length
    field.max_length = 8
    try:
        with pytest.raises(ValueError, match="8-character"):
            record_audit_entry("x" * 9, None, AuditAction.LOAD, 1)
    finally:
        field.max_length = original

    # ...and the restored cap is back in force, so nothing leaks out of this test.
    assert record_audit_entry("x" * 9, None, AuditAction.LOAD, 1).actor == "x" * 9


@pytest.mark.parametrize("bad", ["2026-01-01", dt.date(2026, 1, 1), 1767225600, None])
def test_a_non_datetime_reference_time_raises_a_named_type_error(bad):
    """Previously these died with a bare `AttributeError` from Django's
    internals (`'str' object has no attribute 'utcoffset'`), naming neither
    the parameter nor the expectation -- uniquely among this module's
    parameters. `None` is included because it means "default" for
    `occurred_at`/`now`, so only the other three reach the check.
    """
    if bad is None:
        # `None` is the documented "use the wall clock" default, not an error.
        assert record_audit_entry("alice", None, AuditAction.LOAD, 1, occurred_at=None)
        return
    with pytest.raises(TypeError, match="occurred_at"):
        record_audit_entry("alice", None, AuditAction.LOAD, 1, occurred_at=bad)
    with pytest.raises(TypeError, match="now"):
        purge_expired_entries(AuditRetention(days=30), now=bad)


def test_purge_expired_entries_refuses_a_future_reference_time():
    """A future `now` deletes more than the declared retention allows -- far
    enough ahead, the entire trail, regardless of `retention`. That turns
    AD-7's required declaration into a formality on the one code path that
    destroys evidence.
    """
    record_audit_entry("alice", "east", AuditAction.LOAD, 1)

    with pytest.raises(ValueError, match="future"):
        purge_expired_entries(AuditRetention(days=36500), now=timezone.now() + dt.timedelta(days=100_000))

    assert AuditEntry.objects.count() == 1, "nothing may be deleted by a refused purge"


def test_purge_expired_entries_names_a_retention_this_now_cannot_span():
    """`AuditRetention` rejects only what NO reference time could span; the
    residual band (a value only THIS `now` cannot span) surfaces here as
    this module's own named error rather than a bare `OverflowError`.
    """
    with pytest.raises(ValueError, match="cutoff"):
        purge_expired_entries(AuditRetention(days=_MAX_RETENTION_DAYS))


def test_the_shipped_migration_matches_the_model():
    """Nothing else in this suite detects model/migration drift.

    A NEW field fails loudly (`no such column`), but a changed
    `max_length`, a dropped `db_index`, or a changed `Meta.ordering` does
    not: SQLite enforces none of the three, so the shipped migration could
    silently diverge from the model and only adopters on PostgreSQL would
    find out.
    """
    # `interactive=False` (review pass 3): `--check --dry-run` still PROMPTS
    # for the two rename questions -- `ask_rename`/`ask_rename_model` are the
    # only questioner methods without a `if not self.dry_run` guard. Renaming
    # a field therefore made this test print
    # "Was auditentry.actor renamed to ...? [y/N]" and die with
    # `OSError: pytest: reading from stdin while output is captured`,
    # bypassing the `except SystemExit` branch and the message below
    # entirely -- reproduced by execution. Non-interactively Django answers
    # "no" and emits a drop+add, which still exits non-zero, so drift is
    # still detected and now says so.
    try:
        call_command("makemigrations", "--check", "--dry-run", interactive=False, verbosity=0)
    except SystemExit as exc:  # `--check` exits non-zero when changes exist
        pytest.fail(
            f"makemigrations --check exited {exc.code}: models.py has changes "
            f"not reflected in migrations/ -- regenerate the migration"
        )


def test_record_audit_entry_rejects_a_lone_surrogate_in_any_string_field():
    """A legal `str` no database can encode, refused by name.

    `json.loads('"\\ud800alice"')` produces one, so any identity arriving as
    a JSON field or a JWT claim can carry it. It passed the blank, length
    and NUL checks and then died INSIDE `objects.create()` with a bare
    `UnicodeEncodeError: 'utf-8' codec can't encode character '\\ud800'`,
    naming neither the field nor the caller, on the request path.
    """
    lone_surrogate = "alice\ud800"
    with pytest.raises(ValueError, match="actor"):
        record_audit_entry(lone_surrogate, None, AuditAction.LOAD, 1)
    with pytest.raises(ValueError, match="role"):
        record_audit_entry("alice", lone_surrogate, AuditAction.LOAD, 1)
    with pytest.raises(ValueError, match="target"):
        record_audit_entry("alice", None, AuditAction.LOAD, 1, target=lone_surrogate)
    assert AuditEntry.objects.count() == 0


def test_purge_expired_entries_rechecks_days_a_subclass_could_have_skipped():
    """`isinstance` admits subclasses, and a subclass can skip validation.

    A subclass overriding `__post_init__` without calling `super()`
    constructed with `days=0`, passed the `isinstance` check, produced
    `cutoff = now`, and deleted the ENTIRE trail -- the exact bypass the
    `isinstance` check's own docstring claimed it prevented.
    """
    import dataclasses

    @dataclasses.dataclass(frozen=True)
    class _LabeledRetention(AuditRetention):
        label: str = ""

        def __post_init__(self) -> None:  # deliberately does not call super()
            pass

    record_audit_entry("alice", "east", AuditAction.LOAD, 1)
    record_audit_entry("bob", "west", AuditAction.EXPORT, 2)

    with pytest.raises(ValueError, match="retention.days"):
        purge_expired_entries(_LabeledRetention(days=0, label="skips validation"))

    assert AuditEntry.objects.count() == 2, "a refused purge deletes nothing"


def test_purge_expired_entries_tolerates_ordinary_clock_skew_in_now():
    """The future-`now` refusal must not starve the purge it protects.

    Applied with zero tolerance it rejected a reference time a millisecond
    ahead of this process's clock, so a purge cron on a slightly-fast host
    raised instead of purging -- and a job that never purges is the
    unbounded trail AD-7's declaration exists to prevent.
    """
    now = timezone.now()
    record_audit_entry("alice", "east", AuditAction.LOAD, 1, occurred_at=now - dt.timedelta(days=90))

    skewed = now + dt.timedelta(milliseconds=1)
    assert purge_expired_entries(AuditRetention(days=30), now=skewed) == 1

    # ...and the refusal still bites well before any retention this API can
    # express, so the tolerance did not turn the guard off.
    record_audit_entry("bob", "west", AuditAction.LOAD, 1)
    with pytest.raises(ValueError, match="future"):
        purge_expired_entries(AuditRetention(days=30), now=timezone.now() + _FUTURE_NOW_TOLERANCE * 2)
    assert AuditEntry.objects.count() == 1


def test_query_audit_entries_rejects_a_naive_datetime_filter_under_use_tz_true():
    """A value the write path refuses must not silently shift the read window.

    Django only warns on a naive datetime in a filter, so the query ran
    against a window shifted by the local UTC offset AND recorded an
    `AUDIT_READ` row whose `row_count` described that misinterpreted window
    -- while `record_audit_entry` hard-rejects the identical value.
    """
    record_audit_entry("alice", "east", AuditAction.LOAD, 1)

    with pytest.raises(ValueError, match="occurred_at__gte"):
        query_audit_entries(
            reader_actor="bob",
            reader_role="auditor",
            occurred_at__gte=dt.datetime(2026, 1, 1),
        )
    # Refused before anything ran: no AUDIT_READ row, original row intact.
    assert AuditEntry.objects.count() == 1


def test_a_failed_read_names_query_audit_entries_own_parameters():
    """Reader-validation errors must not point at `record_audit_entry`.

    The shared helper hard-coded `record_audit_entry`'s parameter names, so
    a caller debugging `query_audit_entries(reader_actor="")` was told
    "record_audit_entry requires a non-blank actor" -- a function they did
    not call and a parameter their call does not have.
    """
    with pytest.raises(ValueError, match="query_audit_entries requires a non-blank reader_actor"):
        query_audit_entries(reader_actor="  ", reader_role=None)
    with pytest.raises(TypeError, match="query_audit_entries's reader_actor"):
        query_audit_entries(reader_actor=123, reader_role=None)
    with pytest.raises(ValueError, match="query_audit_entries's reader_role"):
        query_audit_entries(reader_actor="bob", reader_role="   ")

    cap = AuditEntry._meta.get_field("actor").max_length
    with pytest.raises(ValueError, match="reader_actor exceeds"):
        query_audit_entries(reader_actor="x" * (cap + 1), reader_role=None)

    assert AuditEntry.objects.count() == 0


def test_an_uncapped_column_does_not_crash_every_audit_write():
    """`max_length is None` is what a `TextField` reports.

    Deriving the cap is precisely what makes such a column change possible,
    but the derivation compared `len(value) > None` and turned every write
    on the request path into a bare
    `TypeError: '>' not supported between instances of 'int' and 'NoneType'`.
    """
    field = AuditEntry._meta.get_field("target")
    original = field.max_length
    field.max_length = None
    try:
        entry = record_audit_entry("alice", None, AuditAction.LOAD, 1, target="x" * 5_000)
        assert AuditEntry.objects.get(pk=entry.pk).target == "x" * 5_000
        # The other guards on that field still apply.
        with pytest.raises(ValueError, match="target"):
            record_audit_entry("alice", None, AuditAction.LOAD, 1, target="a\x00b")
    finally:
        field.max_length = original


# --- review pass 4 -----------------------------------------------------


@pytest.mark.parametrize(
    "bad_value",
    [
        pytest.param("2026-01-01", id="iso-string"),
        pytest.param(dt.date(2026, 1, 1), id="bare-date"),
        pytest.param(dt.datetime(2026, 1, 1), id="naive-datetime"),
    ],
)
def test_a_filter_the_write_path_refuses_is_refused_on_the_read_path_too(bad_value):
    """Every spelling of a bad `occurred_at`, not just the ones recognized.

    The guard dispatched on the VALUE's Python type
    (`isinstance(element, datetime)`), so it caught a naive `datetime` and
    passed an ISO string and a bare `date` -- the archetypal shapes of a
    dashboard query-string parameter -- straight into the query. Reproduced:
    with one row at `2026-01-01 03:00Z`, `occurred_at__gte="2026-01-01"`
    returned 0 rows under `TIME_ZONE="America/New_York"` (the string was read
    as local midnight = `05:00Z`) with only a Django `RuntimeWarning`, and
    wrote an `AUDIT_READ` row recording that misinterpreted window as
    `row_count=0`. `record_audit_entry` refuses all three by name.
    """
    record_audit_entry("alice", "east", AuditAction.LOAD, 1)

    with pytest.raises((TypeError, ValueError), match="occurred_at__gte"):
        query_audit_entries(reader_actor="bob", reader_role="auditor", occurred_at__gte=bad_value)
    # Refused before anything ran: no AUDIT_READ row, original row intact.
    assert AuditEntry.objects.count() == 1


def test_a_date_part_lookup_still_accepts_a_date():
    """The fix must not refuse the one lookup where a `date` is correct.

    A blanket "reject a `date`" rule would have broken `occurred_at__date=`
    and `occurred_at__year=`, which Django compares against a date/int by
    design -- which is why the check dispatches on the target COLUMN plus the
    lookup, not on the value's type.
    """
    stamped = timezone.now()
    record_audit_entry("alice", "east", AuditAction.LOAD, 1, occurred_at=stamped)

    local_date = timezone.localtime(stamped).date()
    assert len(query_audit_entries(reader_actor="bob", reader_role=None, occurred_at__date=local_date)) == 1
    assert len(query_audit_entries(reader_actor="bob", reader_role=None, occurred_at__year=local_date.year)) >= 1


@pytest.mark.parametrize("container", [set, frozenset, iter, list, tuple])
def test_a_naive_datetime_is_refused_inside_any_in_filter_container(container):
    """`__in` takes any iterable; the unwrap only reached `list`/`tuple`.

    A set, a frozenset and a generator each carried the byte-identical naive
    datetime past the guard that refused it in a list.
    """
    record_audit_entry("alice", "east", AuditAction.LOAD, 1)

    with pytest.raises(ValueError, match="occurred_at__in"):
        query_audit_entries(
            reader_actor="bob",
            reader_role=None,
            occurred_at__in=container([dt.datetime(2026, 1, 1)]),
        )
    assert AuditEntry.objects.count() == 1


def test_a_generator_filter_is_materialized_rather_than_consumed():
    """Validating a generator consumes it, so it must be written back.

    Without that, the validated call would hand Django an exhausted iterator
    and silently match nothing -- a worse failure than the one being fixed.
    """
    stamped = timezone.now()
    record_audit_entry("alice", "east", AuditAction.LOAD, 1, occurred_at=stamped)

    rows = query_audit_entries(reader_actor="bob", reader_role=None, occurred_at__in=(t for t in [stamped]))
    assert len(rows) == 1


@pytest.mark.parametrize(
    "bad_value",
    [
        pytest.param("alice\ud800", id="lone-surrogate"),
        pytest.param("alice\x00x", id="nul-byte"),
    ],
)
def test_an_unstorable_string_filter_is_refused_by_name(bad_value):
    """The read path let through the two strings the write path refuses.

    `actor="alice\\ud800"` died with a bare
    `UnicodeEncodeError: 'utf-8' codec can't encode character '\\ud800'`
    raised from inside the ORM, naming neither the parameter nor the caller
    -- verbatim the failure `_check_storable_string` exists to eliminate,
    closed on the write path and left open here. The NUL case is the same
    dev/prod split: SQLite matches nothing, PostgreSQL refuses the statement.
    """
    with pytest.raises(ValueError, match="actor"):
        query_audit_entries(reader_actor="bob", reader_role=None, actor=bad_value)
    assert AuditEntry.objects.count() == 0


def test_an_over_long_filter_value_is_still_a_legitimate_query():
    """The length cap is a COLUMN bound, not a query one.

    Applying it to filters would invent a refusal: a 300-character actor
    filter simply matches nothing, which is a legitimate read (and one whose
    AUDIT_READ row correctly records `row_count=0`).
    """
    cap = AuditEntry._meta.get_field("actor").max_length
    rows = query_audit_entries(reader_actor="bob", reader_role=None, actor="x" * (cap + 45))
    assert rows == []
    assert AuditEntry.objects.filter(action=AuditAction.AUDIT_READ).count() == 1


def test_a_row_count_column_with_no_integer_range_does_not_crash_every_write():
    """`integer_field_ranges` covers Django's nine INTEGER field types only.

    The unguarded subscript turned every audit write on the request path into
    a bare `KeyError: '<FieldType>'` -- the identical unnamed-internals
    failure class the `max_length is None` branch fifteen lines below it was
    added to prevent. A column with no integer range has no integer ceiling
    to enforce, so the check is skipped rather than crashing.
    """
    field = AuditEntry._meta.get_field("row_count")
    original = field.get_internal_type
    field.get_internal_type = lambda: "DecimalField"
    try:
        assert _max_row_count() is None
        entry = record_audit_entry("alice", "east", AuditAction.LOAD, 5)
        # The other guards on that parameter still apply.
        with pytest.raises(ValueError, match="row_count"):
            record_audit_entry("alice", "east", AuditAction.LOAD, -1)
    finally:
        field.get_internal_type = original

    # Read back only AFTER restoring: SQLite's result converters dispatch on
    # `get_internal_type()` too, and a `PositiveIntegerField` claiming to be a
    # `DecimalField` dies in `get_decimalfield_converter` on the way out --
    # a property of the stub, not of the code under test.
    assert AuditEntry.objects.get(pk=entry.pk).row_count == 5
    assert _max_row_count() == 2_147_483_647, "nothing leaks out of this test"


@pytest.mark.parametrize("bad_action", [None, 5, ["load"], AuditAction])
def test_record_audit_entry_rejects_a_non_string_action_as_a_type_error(bad_action):
    """Wrong TYPE and wrong VALUE are separate errors everywhere else here.

    `action` was the last parameter conflating them, raising `ValueError` for
    a non-string -- the same conflation review pass 1 split apart for
    `actor`/`role`.
    """
    with pytest.raises(TypeError, match="action"):
        record_audit_entry("alice", "east", bad_action, 1)
    assert AuditEntry.objects.count() == 0


def test_two_byte_identical_calls_write_two_separate_rows():
    """AC-3: "never fewer, never a merged/deduplicated write".

    Every existing write test either makes one call or varies a field between
    calls, so the acceptance criterion's actual claim -- that two calls with
    identical arguments are two rows, not one -- had no direct evidence.
    """
    stamped = timezone.now()
    args = ("alice", "east", AuditAction.EXPORT, 42)
    first = record_audit_entry(*args, target="q3", occurred_at=stamped)
    second = record_audit_entry(*args, target="q3", occurred_at=stamped)

    assert first.pk != second.pk
    assert AuditEntry.objects.count() == 2
    assert (
        AuditEntry.objects.filter(
            actor="alice",
            role="east",
            action=AuditAction.EXPORT,
            target="q3",
            row_count=42,
            occurred_at=stamped,
        ).count()
        == 2
    )
