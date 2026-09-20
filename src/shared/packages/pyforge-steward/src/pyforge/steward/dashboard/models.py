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


class WorkPassport(models.Model):
    """Work Passport identity model (Story 65.1; spec-pyforge-steward CAP-140, fully
    realized as of Story 61.2, which added `vendor_id` and the always-fresh vendor
    mint path, `dashboard/passport_mint.py`).

    Primary identity is a minted UUID (`passport_id`). External system keys
    (Jira key, GitHub item ID) are stored as external aliases. `vendor_id`
    names which vendor an inbound row belongs to (v1 operates exactly one
    vendor) and is null/blank on internal-mint rows, which carry no vendor.
    """

    passport_id = models.CharField(max_length=64, primary_key=True)
    story_id = models.CharField(max_length=64, db_index=True)
    station = models.CharField(max_length=64, db_index=True)
    epic_id = models.CharField(max_length=64, blank=True, default="")
    title = models.CharField(max_length=512)
    status = models.CharField(max_length=32, db_index=True, default="backlog")
    jira_key = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    github_item_id = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    vendor_id = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    effort = models.CharField(max_length=32, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["station", "story_id"]
        verbose_name = "Work Passport"
        verbose_name_plural = "Work Passports"

    def __str__(self) -> str:
        return f"{self.station}:{self.story_id} ({self.passport_id[:8]})"


class CorridorDirection(models.TextChoices):
    INBOUND = "inbound", "Inbound"
    OUTBOUND = "outbound", "Outbound"


class CorridorLoad(models.Model):
    """CAP-139 (spec-work-passports-dated-extracts CAP-1 / spec-pyforge-steward
    CAP-139): one durable record of a corridor drop. Idempotent on
    (direction, batch_sha, waybill) -- see dashboard/corridor_load.py.

    ``slice_name``/``signer`` (Story 61.4, spec-work-passports-dated-extracts
    CAP-4 / spec-pyforge-steward CAP-142 -- the signed-outbound-slice gate)
    are the durable record of what was named and who signed it. Both are
    blank (``""``) on every ``inbound`` row: the gate applies to
    ``direction="outbound"`` only. Like ``transport``, they are set ONCE at
    create time and never overwritten by a later idempotent repeat of the
    same ``(direction, batch_sha, waybill)`` -- see
    ``corridor.py``/``corridor_load.py`` for the gate and the idempotency
    rule.
    """

    direction = models.CharField(max_length=8, choices=CorridorDirection.choices, db_index=True)
    batch_sha = models.CharField(max_length=64, db_index=True)
    waybill = models.CharField(max_length=128, db_index=True)
    transport = models.CharField(max_length=32)
    slice_name = models.CharField(max_length=128, blank=True, default="")
    signer = models.CharField(max_length=255, blank=True, default="")
    loaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-loaded_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["direction", "batch_sha", "waybill"],
                name="corridorload_unique_direction_batch_sha_waybill",
            )
        ]
        verbose_name = "Corridor Load"
        verbose_name_plural = "Corridor Loads"

    def __str__(self) -> str:
        return f"{self.direction}:{self.waybill} ({self.batch_sha[:8]})"

