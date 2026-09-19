"""Django Admin registration for pyforge-steward dashboard models."""

from __future__ import annotations

from django.contrib import admin
from pyforge.steward.dashboard.models import AuditEntry, WorkPassport


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
    list_display = ("passport_id", "station", "story_id", "status", "jira_key", "github_item_id", "title")
    list_filter = ("station", "status")
    search_fields = ("passport_id", "story_id", "station", "jira_key", "github_item_id", "title")
    ordering = ("station", "story_id")
