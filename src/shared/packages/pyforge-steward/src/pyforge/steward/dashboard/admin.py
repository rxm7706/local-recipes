"""Django Admin registration for pyforge-steward dashboard models."""

from __future__ import annotations

from django.contrib import admin
from pyforge.steward.dashboard.models import AuditEntry, CorridorLoad, WorkPassport


@admin.register(AuditEntry)
class AuditEntryAdmin(admin.ModelAdmin):
    """Read-only: the audit trail (CAP-4) is written by `audit.record_audit_entry`
    alone and never edited, added to, or deleted through the admin."""

    list_display = ("actor", "role", "action", "target", "row_count", "occurred_at")
    list_filter = ("action", "role", "occurred_at")
    search_fields = ("actor", "target", "role")
    ordering = ("-occurred_at",)
    readonly_fields = ("actor", "role", "action", "target", "row_count", "occurred_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(WorkPassport)
class WorkPassportAdmin(admin.ModelAdmin):
    list_display = (
        "passport_id",
        "station",
        "story_id",
        "status",
        "jira_key",
        "github_item_id",
        "vendor_id",
        "title",
    )
    list_filter = ("station", "status", "vendor_id")
    search_fields = (
        "passport_id",
        "story_id",
        "station",
        "jira_key",
        "github_item_id",
        "vendor_id",
        "title",
    )
    ordering = ("station", "story_id")


@admin.register(CorridorLoad)
class CorridorLoadAdmin(admin.ModelAdmin):
    """Read-only: a corridor load is a durable fact recorded by
    `corridor_load.record_corridor_load` alone and never edited, added to,
    or deleted through the admin."""

    list_display = (
        "direction",
        "waybill",
        "batch_sha",
        "transport",
        "slice_name",
        "signer",
        "loaded_at",
    )
    list_filter = ("direction", "transport")
    search_fields = ("batch_sha", "waybill", "slice_name", "signer")
    ordering = ("-loaded_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
