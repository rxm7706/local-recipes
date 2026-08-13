"""Story 9.3 — `AuditEntry`: CAP-4's durable store.

CAP-4's contract is "who saw how many rows of what, and when" — this model
is that record. `AuditAction` names the four request-time actions CAP-4
requires (`load`/`filter`/`navigate`/`export`) plus `audit_read`, the fifth
action `audit.py::query_audit_entries` writes for its own invocation per
AD-7 ("reading the audit trail is itself a recorded act").

This is the package's first Django model, so it is also the first thing
that exercises AD-13's reusable-app scaffold (`apps.py`'s explicit
`AppConfig` label and `default_auto_field`) for real: no `app_label` is set
here in `Meta` — Django resolves it automatically from this module's
package (`pyforge.steward.dashboard`) being present in `INSTALLED_APPS`,
which is exactly the AD-13 wiring `apps.py` shipped early in Story 9.1 to
receive this model without retrofitting.

Field values are stored verbatim by `audit.py` (never trimmed, case-folded,
or Unicode-normalized here or there) — this module only declares the shape
and the length caps; `audit.py` enforces those caps in Python before any
write reaches this model, since SQLite performs no `VARCHAR(n)` enforcement
at all and PostgreSQL does (see `audit.py`'s module docstring for why that
split matters).

Requires `django`, same tier as `apps.py`/`cache.py` — this module only
imports cleanly with the `pyforge-steward[dashboard]` extra installed.
"""

from __future__ import annotations

from django.db import models


class AuditAction(models.TextChoices):
    """CAP-4's four request-time actions, plus AD-7's audit-of-the-audit action."""

    LOAD = "load", "Load"
    FILTER = "filter", "Filter"
    NAVIGATE = "navigate", "Navigate"
    EXPORT = "export", "Export"
    AUDIT_READ = "audit_read", "Audit read"


class AuditEntry(models.Model):
    """CAP-4: one durable record of who saw how many rows of what, and when.

    ``actor`` is required — CAP-4's "who saw" must never be unanswerable by
    construction, enforced in Python by `audit.py::record_audit_entry`
    before any row is written, not by a DB-level `NOT NULL` guess. ``role``
    is nullable: `None` is Story 9.1's legitimate "no role established"
    scope state, stored as SQL `NULL`, never coerced to `""`. ``target`` is
    optional and defaults to `""`, never `None` — a caller with nothing more
    specific than the action itself may omit it, but the column always
    holds a string. ``occurred_at`` is indexed since every read of the
    trail (`audit.py::query_audit_entries`, and any future retention
    report) filters or orders by it. ``actor`` is indexed too, since
    `query_audit_entries` is exercised filtering by it and the trail is
    expected to accumulate unboundedly between retention purges. `Meta.
    ordering` is most-recent-first, so PostgreSQL (which gives no incidental
    rowid ordering the way SQLite's test suite does) returns the trail in
    the same chronological order every reader expects, without each caller
    having to remember to ask for it.

    That ordering carries ``-id`` as a tiebreaker (review pass 2). Without
    it, rows sharing an ``occurred_at`` fell back to whatever order the
    query plan happened to produce, and the "guaranteed" order was not
    guaranteed at all — reproduced on SQLite, no PostgreSQL required: six
    rows written with one identical timestamp came back in insertion order
    from `.filter(actor=…)` (which uses the `actor` index) and in reverse
    insertion order from `.all()` (which does not). Ties are not exotic
    here: `record_audit_entry` accepts an explicit ``occurred_at``, so any
    caller stamping a batch of rows with one timestamp creates them.
    """

    actor = models.CharField(max_length=255, db_index=True)
    role = models.CharField(max_length=255, null=True, blank=True)
    action = models.CharField(max_length=16, choices=AuditAction.choices)
    target = models.CharField(max_length=255, blank=True, default="")
    row_count = models.PositiveIntegerField()
    occurred_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["-occurred_at", "-id"]
