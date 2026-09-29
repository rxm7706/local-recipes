"""Story 9.3 — `record_audit_entry` / `query_audit_entries` / `purge_expired_entries`.

CAP-4's write/read/retention API over the `AuditEntry` model (`models.py`):

* `record_audit_entry` is the CAP-4 primitive — every data load, filter,
  navigation, and export lands here, naming the actor, their role, the
  action, and the row count involved.
* `query_audit_entries` reads the trail AND, per AD-7 ("reading the audit
  trail is a recorded act"), calls `record_audit_entry` for its own
  invocation before returning. AD-7's other half — the trail as
  *role-isolated* data — is NOT implemented here; see that function's own
  docstring.
* `purge_expired_entries` requires an `AuditRetention` (`declarations.py`)
  with **no default anywhere** — AD-7's "refused rather than run unbounded",
  enforced the same way AD-6 enforces filter-then-search: by the function's
  own signature, not by a caller's discipline.

**Verbatim storage, enforced in Python, not the column type.** `actor`,
`role`, and `target` are stored exactly as passed — no `.strip()`, no
case-folding, no Unicode normalization. CAP-4's contract is "records what
was actually seen"; normalizing at write time would substitute this
module's own reinterpretation for what was presented (this is the
identity-model decision Story 9.1's review pass 3 explicitly deferred
here). Each of those three fields is length-capped at whatever
`AuditEntry`'s own column declares — read off the model field, not copied
into a constant here (review pass 2) — and that cap is checked here, in
Python, before any DB write, rather than left to the column type: SQLite
(dev) enforces no `VARCHAR(n)` length at all, so a value that overflows the
column is silently accepted there and would only be caught once the same
code ran against PostgreSQL (deployment) — the exact dev/prod asymmetry
AD-14 warns against for a different mechanism. An embedded NUL is refused
for the same reason and on the same line, as is a lone surrogate — a legal
`str` no database can store, which otherwise surfaced as a bare
`UnicodeEncodeError` from inside the ORM. Rejecting an overlong value
outright (never truncating) keeps the trail from being silently corrupted
into a value the caller never actually saw.

Requires `django`, same tier as `apps.py`/`cache.py`/`models.py` — this
module only imports cleanly with the `pyforge-steward[dashboard]` extra
installed.
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Iterator
from datetime import timedelta

from django.core.exceptions import FieldDoesNotExist
from django.db import models, router, transaction
from django.db.backends.base.operations import BaseDatabaseOperations
from django.utils import timezone

from .declarations import AuditRetention
from .models import AuditAction, AuditEntry

# How far a caller's `now` may lead this process's clock before
# `purge_expired_entries` refuses it (review pass 3). The refusal exists to
# stop a *materially* future reference time from widening the purge past the
# declared retention -- pass 2 reproduced that with `now = +100,000 days`.
# Applied with zero tolerance it also refuses ordinary clock skew: a purge
# cron on a host one millisecond ahead of the app host raised instead of
# purging, and a job that never purges is the unbounded trail AD-7's
# declaration exists to prevent -- the guard starving the trail it protects.
# A minute is far below any retention this API can express (`AuditRetention`
# is denominated in whole days), so it cannot meaningfully widen a purge,
# and far above NTP-managed skew -- the same skew argument pass 2 used to
# leave `record_audit_entry`'s `occurred_at` unguarded on the request path.
_FUTURE_NOW_TOLERANCE = timedelta(seconds=60)

# Lookups that turn a `DateTimeField` comparison into a date/int/time one, so
# `query_audit_entries`' datetime rule must NOT apply to their values
# (`occurred_at__date=date(2026, 1, 1)` and `occurred_at__year=2026` are both
# correct as written). Django's own `DateTimeField` transform registry, plus
# `isnull`, whose value is a bool.
_DATE_PART_LOOKUPS = frozenset(
    {
        "date",
        "time",
        "year",
        "iso_year",
        "quarter",
        "month",
        "day",
        "week",
        "week_day",
        "iso_week_day",
        "hour",
        "minute",
        "second",
        "isnull",
    }
)


def _max_row_count() -> int | None:
    """`row_count`'s real ceiling, derived from its own column (review pass 3).

    Hand-copying `2_147_483_647` here is the identical defect review pass 2
    removed for the string caps fifteen lines below: change
    `AuditEntry.row_count` to a `PositiveSmallIntegerField` and a copied
    constant keeps admitting 2-billion values into a column PostgreSQL caps
    at 32,767 -- verified by execution, `row_count=40_000` recorded cleanly
    against a smallint column. `BaseDatabaseOperations.integer_field_ranges`
    is the canonical (backend-independent) range table Django itself uses to
    build these fields' validators; read off the BASE class deliberately,
    since SQLite's subclass overrides the lookup to "no range at all" -- which
    is precisely the dev-side blindness this module exists to close.

    Returns `None` for a column type absent from that table (review pass 4).
    The table covers Django's nine INTEGER field types, so a `row_count`
    changed to anything else has no integer ceiling to enforce -- and the
    unguarded subscript this replaces turned every audit write on the request
    path into a bare `KeyError: '<FieldType>'`, naming neither the field nor
    the caller. That is the identical unnamed-internals failure class the
    `max_length is None` branch below was added to prevent, left standing
    fifteen lines above it because deriving the ceiling is precisely what
    makes such a column change possible.
    """
    internal_type = AuditEntry._meta.get_field("row_count").get_internal_type()
    field_range = BaseDatabaseOperations.integer_field_ranges.get(internal_type)
    return None if field_range is None else field_range[1]


def _check_storable_string(label: str, value: str) -> None:
    """Refuse the two `str` values no database round-trips faithfully.

    Split out of `_check_string_field` (review pass 4) so `query_audit_entries`
    can hold its `**filters` to the same rule. These two checks are about
    whether the *string* can reach a database at all, not about `AuditEntry`'s
    column widths, so they apply identically to a value being written and to
    one being matched against — while the length cap does not (an over-long
    filter value simply matches nothing, which is a legitimate query, not an
    error).
    """
    # NUL is the value that crosses the dev/prod line (review pass 2): SQLite
    # stores `\x00` inside a TEXT value without complaint, while PostgreSQL
    # refuses it outright ("A string literal cannot contain NUL (0x00)
    # characters"). Left unchecked, a call that is green in every dev test
    # raises in production -- on the request path, since this is the primitive
    # every load/filter/navigate/export calls. Rejected here so both backends
    # behave identically.
    if "\x00" in value:
        raise ValueError(
            f"{label} contains a NUL (0x00) character — SQLite would "
            f"store it and PostgreSQL would reject the write outright, so "
            f"it is refused here to keep both backends behaving identically"
        )
    # A lone surrogate is the other value that is a legal `str` but not
    # encodable at all (review pass 3): `json.loads('"\\ud800alice"')` yields
    # one, so any identity arriving via JSON or a JWT claim can carry it. It
    # passed every check above and then died INSIDE the ORM with a bare
    # `UnicodeEncodeError: 'utf-8' codec can't encode character '\ud800':
    # surrogates not allowed` -- naming neither the field nor the caller, on
    # the request path. Refused here, by the same rule and for the same reason
    # as NUL. Verified by execution on both the write and the read path.
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError(
            f"{label} contains an unencodable character (a lone "
            f"surrogate) — no database can store it, so it is refused here "
            f"by name rather than surfacing as a bare UnicodeEncodeError "
            f"from deep inside the ORM"
        ) from None


def _check_string_field(field_name: str, value: str, label: str | None = None) -> None:
    """Enforce `AuditEntry`'s own column contract for a string field, in Python.

    ``field_name`` names the `AuditEntry` column whose contract is being
    enforced; ``label`` names the *parameter* the value arrived as, when the
    two differ (`query_audit_entries`' ``reader_actor`` is checked against
    the ``actor`` column). Messages quote ``label`` so a caller is never
    pointed at a parameter their call does not have (review pass 3).

    The cap is read off the model field itself (review pass 2) rather than
    hand-copied into a constant here: the whole point of checking in Python
    is that `audit.py`'s bound and `AuditEntry`'s column agree, and a
    hand-copied `255` keeps them agreeing only by a comment. Narrow
    `AuditEntry.actor` to `max_length=128` with a copied constant in place and
    every test still passes while PostgreSQL starts rejecting 129-character
    actors in production -- exactly the dev/prod asymmetry this function
    exists to close. Derived, the two cannot drift.
    """
    label = label or field_name
    max_length = AuditEntry._meta.get_field(field_name).max_length
    # `max_length is None` is what an uncapped column (a `TextField`) reports,
    # and deriving the cap is precisely what makes such a change possible
    # (review pass 3). Without this branch the derivation turns every audit
    # write on the request path into a bare
    # `TypeError: '>' not supported between instances of 'int' and 'NoneType'`
    # -- the same unnamed-internals failure class pass 2 removed for
    # `occurred_at`, reintroduced by the fix for the copied constant.
    # Verified by execution against a `max_length=None` field.
    if max_length is not None and len(value) > max_length:
        raise ValueError(
            f"{label} exceeds the {max_length}-character audit "
            f"field cap (got {len(value)} characters) — rejected rather "
            f"than truncated, so the trail never records a value the "
            f"caller did not actually pass"
        )
    _check_storable_string(label, value)


def _check_reference_datetime(field_name: str, value) -> None:
    """Reject a non-datetime, or a naive/aware mismatch against `timezone.now()`.

    The type check comes first (review pass 2): without it, a `str`, a
    `date`, or an epoch `int` reached `timezone.is_aware(value)` and died
    with a bare `AttributeError: 'str' object has no attribute 'utcoffset'`
    -- leaking Django's internals and naming neither the parameter nor the
    expectation, uniquely among this module's parameters.

    `django.utils.timezone.now()` returns an aware `datetime` when
    `settings.USE_TZ` is `True` and a naive one when it is `False` -- so
    "correct" here means matching whatever `now()` itself currently returns,
    not an absolute always-aware rule (a `USE_TZ=False` deployment legitimately
    uses naive datetimes throughout). Passing the wrong shape under
    `USE_TZ=True` degrades to a Django `RuntimeWarning` and a silently
    misinterpreted timestamp rather than a rejection -- the exact
    "unrefused ambiguous input" class every other check in this module exists
    to prevent.
    """
    # `datetime` before `date`: `datetime` is a `date` subclass, so an
    # `isinstance(value, _dt.date)` check would admit a bare `date`.
    if not isinstance(value, _dt.datetime):
        raise TypeError(f"{field_name} must be a datetime, got {type(value).__name__}")
    expected_aware = timezone.is_aware(timezone.now())
    if timezone.is_aware(value) != expected_aware:
        shape = "aware" if expected_aware else "naive"
        raise ValueError(
            f"{field_name} must be {shape} to match this deployment's "
            f"settings.USE_TZ, got {'aware' if timezone.is_aware(value) else 'naive'} "
            f"— a mismatched datetime silently shifts by the local UTC "
            f"offset instead of being rejected"
        )


def _check_actor_and_role(
    actor: str,
    role: str | None,
    *,
    caller: str = "record_audit_entry",
    actor_param: str = "actor",
    role_param: str = "role",
) -> None:
    """Validate the identity half of an audit write.

    Factored out of `record_audit_entry` (review pass 2) so
    `query_audit_entries` can apply the identical rules to its *reader*
    BEFORE touching the database, rather than reading the trail first and
    only then discovering the read cannot be recorded.

    ``caller``/``actor_param``/``role_param`` name the function and the
    parameters the values actually arrived as (review pass 3). Extracting
    this helper left every message hard-coded to `record_audit_entry`'s own
    parameter names, so a failing `query_audit_entries(reader_actor="")`
    raised *"record_audit_entry requires a non-blank actor"* — sending a
    caller to a function they did not call and a parameter their call does
    not have, the same "names neither the parameter nor the expectation"
    defect pass 2 fixed for `occurred_at`.
    """
    if not isinstance(actor, str):
        raise TypeError(f"{caller}'s {actor_param} must be a string, got {type(actor).__name__}")
    if not actor.strip():
        raise ValueError(
            f"{caller} requires a non-blank {actor_param} — CAP-4's 'who "
            f"saw' must never be unanswerable by construction"
        )
    _check_string_field("actor", actor, label=actor_param)

    if role is None:
        return
    if not isinstance(role, str):
        raise TypeError(f"{caller}'s {role_param} must be None or a string, got {type(role).__name__}")
    if not role.strip():
        raise ValueError(
            f"{caller}'s {role_param} must be None (no role "
            f"established) or a non-blank string — a blank/whitespace-"
            f"only role is the same unanswerable state None already "
            f"represents, spelled a different way"
        )
    _check_string_field("role", role, label=role_param)


def _check_filters(filters: dict) -> None:
    """Hold `query_audit_entries`' `**filters` to the write path's own rules.

    Rewritten in review pass 4. The previous form dispatched on the VALUE's
    Python type — `isinstance(element, datetime)`, unwrapping only `list`/
    `tuple` — which checked only the shapes it recognized and silently passed
    every other spelling of the same wrong value straight into the query.
    Reproduced by execution, all three returning the wrong window with a mere
    Django `RuntimeWarning` and an `AUDIT_READ` row whose `row_count`
    described it:

    * ``occurred_at__gte="2026-01-01"`` — an ISO string, the archetypal shape
      of a dashboard query-string parameter
    * ``occurred_at__gte=date(2026, 1, 1)`` — a bare `date`
    * ``occurred_at__in={naive}`` / a generator — legal `__in` values Django
      accepts and the `list`/`tuple` unwrap did not reach

    while ``record_audit_entry(occurred_at=<any of them>)`` hard-rejects each
    one by name. So this dispatches on the TARGET COLUMN instead: whatever a
    filter compares against `occurred_at` must satisfy the identical rule
    `occurred_at` itself does, regardless of how it is spelled. Date-part
    lookups are exempt (`occurred_at__date=<date>` and `occurred_at__year=2026`
    are correct as written), which a blanket "reject a `date`" rule would have
    broken.

    String filters are held to `_check_storable_string` for the same reason on
    the read side: a lone surrogate in ``actor=`` died with a bare
    `UnicodeEncodeError` raised from inside the ORM — verbatim the failure the
    module docstring says that check exists to eliminate, closed on the write
    path and open here. The length cap deliberately does NOT apply: an
    over-long filter value matches nothing, which is a legitimate query.
    """
    for filter_name, filter_value in list(filters.items()):
        parts = filter_name.split("__")
        try:
            field = AuditEntry._meta.get_field(parts[0])
        except FieldDoesNotExist:
            # Django's own `FieldError` names an unknown field better than
            # anything this function could say, and raising it is its job.
            continue

        if isinstance(filter_value, (list, tuple, set, frozenset)):
            elements = list(filter_value)
        elif isinstance(filter_value, Iterator):
            # Iterating a generator CONSUMES it, so it is materialized and
            # written back — otherwise validating it would hand Django an
            # exhausted iterator that silently matches nothing.
            elements = list(filter_value)
            filters[filter_name] = elements
        elif isinstance(filter_value, (str, bytes)) or not hasattr(filter_value, "__iter__"):
            elements = [filter_value]
        else:
            # An opaque iterable (a queryset used as an `__in` subquery, a
            # query expression) — not this function's to interpret.
            continue

        if isinstance(field, models.DateTimeField) and not (set(parts[1:]) & _DATE_PART_LOOKUPS):
            for element in elements:
                _check_reference_datetime(filter_name, element)
        elif isinstance(field, models.CharField):
            for element in elements:
                if isinstance(element, str):
                    _check_storable_string(filter_name, element)


def record_audit_entry(
    actor: str,
    role: str | None,
    action: str,
    row_count: int,
    *,
    target: str = "",
    occurred_at=None,
) -> AuditEntry:
    """CAP-4's write primitive: record that `actor` (as `role`) did `action`
    to `row_count` rows of `target`, at `occurred_at`.

    ``actor`` is required and must not be blank or whitespace-only — CAP-4's
    "who saw" must never be unanswerable by construction. ``role`` may
    legitimately be `None` (Story 9.1's "no role established" scope state)
    and is stored as SQL `NULL`, never coerced to `""`; a non-`None` role
    must not be blank/whitespace-only either, for the same reason as
    ``actor``. ``action`` must be one of `AuditAction`'s declared values — an
    arbitrary string is rejected rather than silently written into a column
    every future reader assumes is a closed vocabulary. ``target`` defaults
    to `""`, never `None`, since a caller with nothing more specific than the
    action itself may omit it but the column always holds a string.
    ``row_count`` must be a non-bool `int` `>= 0` and no larger than
    PostgreSQL's `PositiveIntegerField` ceiling. ``occurred_at`` defaults to
    `django.utils.timezone.now()` when not passed; if passed explicitly, its
    naive/aware-ness must match `timezone.now()`'s own (i.e. this
    deployment's `settings.USE_TZ`).

    Returns the created `AuditEntry`. Never merges or deduplicates against
    an existing row — every call writes exactly one new row.
    """
    _check_actor_and_role(actor, role)

    if not isinstance(target, str):
        raise TypeError(f"record_audit_entry's target must be a string, got {type(target).__name__}")
    _check_string_field("target", target)

    # Wrong TYPE and wrong VALUE are separate errors (review pass 4). `action`
    # was the one parameter left conflating them: `action=None`/`5`/`["load"]`
    # all raised `ValueError` while every other parameter here raises
    # `TypeError` for a wrong type — the same conflation pass 1 split apart
    # for `actor`/`role`, never applied to the last parameter that had it.
    if not isinstance(action, str):
        raise TypeError(
            f"record_audit_entry's action must be a string (an AuditAction value), got {type(action).__name__}"
        )
    if action not in AuditAction.values:
        raise ValueError(
            f"record_audit_entry's action must be one of "
            f"{sorted(AuditAction.values)!r}, got {action!r} — an "
            f"unrecognized action would defeat every future reader's "
            f"assumption that this column is a closed vocabulary"
        )

    # `bool` excluded explicitly (same reasoning as `AuditRetention.days`,
    # `cache.py`'s `lock_timeout`): `isinstance(True, int)` is `True` in
    # Python and `True < 0` is `False`, so a caller passing a boolean flag
    # by mistake would otherwise sail through as `row_count=1`/`0`.
    if not isinstance(row_count, int) or isinstance(row_count, bool):
        raise TypeError(f"record_audit_entry's row_count must be an int, got {type(row_count).__name__}")
    if row_count < 0:
        raise ValueError(
            f"record_audit_entry's row_count must be >= 0, got {row_count} "
            f"— a negative row count cannot describe what was actually "
            f"seen, and is rejected here rather than left to the DB"
        )
    max_row_count = _max_row_count()
    if max_row_count is not None and row_count > max_row_count:
        raise ValueError(
            f"record_audit_entry's row_count must not exceed "
            f"{max_row_count} (the ceiling of the column's own field type "
            f"on a range-enforcing backend), got {row_count} — SQLite would "
            f"silently accept it and PostgreSQL would reject it, the same "
            f"dev/prod asymmetry this module already guards against for the "
            f"string fields"
        )

    if occurred_at is None:
        occurred_at = timezone.now()
    else:
        _check_reference_datetime("occurred_at", occurred_at)

    return AuditEntry.objects.create(
        actor=actor,
        role=role,
        action=action,
        target=target,
        row_count=row_count,
        occurred_at=occurred_at,
    )


def query_audit_entries(*, reader_actor: str, reader_role: str | None, **filters) -> list[AuditEntry]:
    """Read the audit trail, and record that this read happened (AD-7).

    Any keyword filters are applied via `AuditEntry.objects.filter(**filters)`.
    Before returning, this function itself calls `record_audit_entry` with
    `action=AuditAction.AUDIT_READ`, `target="audit_trail"`, and a
    `row_count` equal to the number of rows this call is about to return —
    per AD-7, "reading the audit trail is a recorded act". That write is not
    optional and cannot be skipped by a caller: it is this function's whole
    point, not a side effect of it.

    **Only the recorded-act half of AD-7 is implemented here.** AD-7 also
    calls the trail "role-isolated data", and this function does NOT filter
    its rows by ``reader_role`` — every reader sees every row. ``reader_role``
    is recorded, not enforced; do not read it as an authorization input. The
    row-isolation half needs Story 9.2's `filtering.py`, which does not exist
    in this worktree, and is tracked as a deferred item rather than being
    half-built here (review pass 2 made this explicit, since quoting AD-7's
    isolation clause without saying so implied a guarantee that is not
    delivered).

    A read that cannot be recorded does not happen: ``reader_actor`` and
    ``reader_role`` are validated against `record_audit_entry`'s own rules
    BEFORE the query runs, and the query plus its `AUDIT_READ` write share
    one `transaction.atomic()` block (review pass 2). Previously the rows
    were fetched first, so a caller passing a blank ``reader_actor`` — or a
    misspelled filter keyword — got a full read of the trail followed by an
    exception, leaving no `AUDIT_READ` row behind at all: an unrecorded read
    on demand, repeatable indefinitely, which is precisely what AD-7 forbids.
    ``**filters`` is held to the write path's own rules by column, not by the
    value's Python type (`_check_filters`, review pass 4): anything compared
    against ``occurred_at`` must satisfy the identical naive/aware rule
    ``occurred_at`` itself does — a value the write path rejects outright must
    not silently shift the read window, and with it the ``row_count`` this
    call records, by the local UTC offset — and any string compared against a
    text column must be one a database can actually store.

    **That atomic block is a scope guarantee, not a durability one.** Django's
    `transaction.atomic()` nested inside a caller's open transaction is a
    savepoint, so under `ATOMIC_REQUESTS=True` (or any outer
    `@transaction.atomic`) a rollback discards the `AUDIT_READ` row while the
    rows this function returned are already in the caller's hands — the read
    happened and its record did not. Callers that must not lose the record
    are responsible for not discarding it: read outside the transaction they
    intend to roll back, or commit the audit write separately. Closing this
    inside the function (`durable=True`, or an out-of-band connection) would
    change what deployments may call it, so it is tracked on the
    deferred-work ledger rather than decided here (review pass 3).

    Returns a concrete `list`, not a lazy queryset — inspectable and
    re-iterable by the caller without a second trip to the database,
    matching this package's existing preference (`cache.py`) for concrete
    return types. Rows come back most-recent-first: `AuditEntry.Meta.ordering`
    applies to any queryset (including this one) that does not specify its
    own `.order_by()`, so the order is guaranteed by the model's own
    declaration rather than by an incidental DB rowid order that PostgreSQL
    (unlike SQLite in the test suite) would not actually provide.
    """
    # Validate the reader BEFORE any query: an unrecordable read must not
    # execute at all, rather than execute and then fail to be recorded.
    _check_actor_and_role(
        reader_actor,
        reader_role,
        caller="query_audit_entries",
        actor_param="reader_actor",
        role_param="reader_role",
    )
    _check_filters(filters)

    # Bind the transaction to the alias this model is actually routed to
    # (review pass 3). A bare `transaction.atomic()` opens a transaction on
    # `"default"` — so an adopter routing `AuditEntry` to a dedicated audit
    # database (an entirely ordinary shape for an audit trail) got a
    # transaction on an unrelated database while the SELECT and the
    # `AUDIT_READ` INSERT both ran unprotected on the routed one. Verified by
    # execution. The read is pinned to the write alias so the pair genuinely
    # shares one transaction, which is what the docstring above promises;
    # a compliance read must not come off a replica anyway.
    using = router.db_for_write(AuditEntry)
    with transaction.atomic(using=using):
        rows = list(AuditEntry.objects.using(using).filter(**filters))

        record_audit_entry(
            actor=reader_actor,
            role=reader_role,
            action=AuditAction.AUDIT_READ,
            row_count=len(rows),
            target="audit_trail",
        )

    return rows


def purge_expired_entries(retention: AuditRetention, *, now=None) -> int:
    """Delete every `AuditEntry` older than `retention.days`, and return the count.

    ``retention`` has NO default value — the only way to call this function
    at all is to supply an `AuditRetention`, which is itself
    construction-validated (`declarations.py`) to be a positive number of
    days. This is AD-7's refusal expressed as a property of the function's
    own signature: there is no call path through this module that expires
    audit entries without a retention policy someone actually declared.

    The cutoff is `(now or timezone.now()) - timedelta(days=retention.days)`;
    every row with `occurred_at < cutoff` is deleted (strictly less-than: a
    row exactly at the cutoff survives one more cycle, by design). `now` is
    accepted (defaulting to `timezone.now()`) so callers/tests can pin the
    reference time deterministically rather than racing the wall clock; if
    passed explicitly, its naive/aware-ness must match `timezone.now()`'s own
    (same rule and reason as `record_audit_entry`'s `occurred_at`) and it may
    not lead this process's clock by more than `_FUTURE_NOW_TOLERANCE` — a
    future reference time silently widens the purge past the declared
    retention, up to and including deleting the entire trail, which is the
    one outcome AD-7's required-declaration exists to make impossible (review
    pass 2: `now=<far future>` deleted every row regardless of `retention`).
    The tolerance is what keeps that refusal from also rejecting ordinary
    inter-host clock skew and starving the purge entirely (review pass 3).

    `retention.days` is re-checked here even though `AuditRetention`
    validates it at construction: `isinstance` admits subclasses, and a
    subclass overriding `__post_init__` without calling `super()` skips that
    validation entirely (review pass 3).
    """
    if not isinstance(retention, AuditRetention):
        raise TypeError(
            f"purge_expired_entries requires an AuditRetention, got "
            f"{type(retention).__name__} — its construction-time validation "
            f"is what keeps AD-7's refusal from being bypassed by a "
            f"look-alike object"
        )
    # `isinstance` admits SUBCLASSES, and a subclass that overrides
    # `__post_init__` without calling `super()` skips every construction-time
    # check (review pass 3) — so the sentence above was not true of the code
    # below it. Verified by execution: a subclass adding one field
    # constructed with `days=0`, passed the `isinstance` check, produced
    # `cutoff = now`, and deleted the ENTIRE trail. The value this function
    # actually depends on is re-checked here, at the point of use, so AD-7's
    # refusal does not rest on a check inheritance defeats.
    if not isinstance(retention.days, int) or isinstance(retention.days, bool):
        raise TypeError(
            f"purge_expired_entries' retention.days must be an int, got "
            f"{type(retention.days).__name__} — re-checked at the point of "
            f"use because a subclass can skip AuditRetention's own validation"
        )
    if retention.days <= 0:
        raise ValueError(
            f"purge_expired_entries' retention.days must be positive, got "
            f"{retention.days} — a non-positive retention makes the cutoff "
            f"`now` or later and deletes the whole trail; re-checked here "
            f"because a subclass can skip AuditRetention's own validation"
        )

    if now is None:
        now = timezone.now()
    else:
        _check_reference_datetime("now", now)
        # Tolerated, not exact (review pass 3): see `_FUTURE_NOW_TOLERANCE`.
        # A zero-tolerance comparison refuses a reference time a millisecond
        # ahead of this process's clock, which turns ordinary inter-host skew
        # into a purge job that never purges — the unbounded trail this
        # module exists to prevent, produced by the guard protecting it.
        if now > timezone.now() + _FUTURE_NOW_TOLERANCE:
            raise ValueError(
                f"purge_expired_entries' now must not be more than "
                f"{_FUTURE_NOW_TOLERANCE} in the future, got {now!r} — a "
                f"future reference time deletes more than the declared "
                f"retention allows (far enough ahead, the whole trail), "
                f"turning AD-7's required declaration into a formality"
            )

    # `AuditRetention` already rejects a `days` value no reference time could
    # ever span; this catches the residual band that only THIS `now` cannot
    # span (review pass 2), so the failure is still this module's own named
    # error rather than a bare `OverflowError` from the subtraction.
    try:
        cutoff = now - timedelta(days=retention.days)
    except OverflowError:
        raise ValueError(
            f"purge_expired_entries cannot compute a cutoff: {retention.days} "
            f"days before {now!r} is earlier than the earliest representable "
            f"datetime — declare a retention this reference time can actually "
            f"span"
        ) from None

    deleted_count, _ = AuditEntry.objects.filter(occurred_at__lt=cutoff).delete()
    return deleted_count
