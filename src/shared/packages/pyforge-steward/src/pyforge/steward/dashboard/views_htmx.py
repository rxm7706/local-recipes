"""HTMX view handlers for the pyforge-steward sprint backlog dashboard (Story
65.1) and the as-of glass (Story 61.3).

Reads through the same `SprintLedgerQueryEngine` as the CLI duty (CAP-5), and
`glass.compute_glass_reading` for `standup_htmx_view`/`shipped_htmx_view`.
Imports `django` lazily, inside each view, so the module itself loads without
the `[dashboard]` extra; calling a view needs it. `glass.py` is a base-package
module (no django), so importing it here at module level is safe. Like
`views.py`, this ships views only -- the adopter wires them into their own
`urlpatterns` (AD-1), and there is no HTTP URLconf in this package to
register them with.
"""

from __future__ import annotations

import html
import os
import re
from pathlib import Path
from typing import Any, Optional

from pyforge.steward.glass import GlassReading, compute_glass_reading
from pyforge.steward.sprint_ledger_query import SprintLedgerQueryEngine

_STATION_RE = re.compile(r"[A-Za-z0-9_-]+")
_TRUTHY = frozenset({"true", "1", "on", "yes"})
_AUDIT_TARGET = "sprint-backlog"


def _truthy(raw: Optional[str]) -> bool:
    return (raw or "").strip().lower() in _TRUTHY


def _engine_root() -> Optional[Path]:
    """`settings.PYFORGE_REPO_ROOT`, else `$PYFORGE_REPO_ROOT`, else the engine's
    own repo-root walk-up -- never the process's cwd."""
    from django.conf import settings

    root = getattr(settings, "PYFORGE_REPO_ROOT", None) or os.environ.get("PYFORGE_REPO_ROOT")
    return Path(root) if root else None


def _record_load(request: Any, row_count: int) -> None:
    """CAP-4: one `load` audit row per render. The actor is the identity
    `DashboardIdentityMiddleware` placed on `request.scope`, else the
    authenticated user, else the literal `anonymous` (never blank)."""
    from pyforge.steward.dashboard.audit import record_audit_entry
    from pyforge.steward.dashboard.models import AuditAction

    scope = getattr(request, "scope", None) or {}
    actor = scope.get("dashboard_identity")
    if not actor:
        user = getattr(request, "user", None)
        actor = getattr(user, "username", None) if getattr(user, "is_authenticated", False) else None
    record_audit_entry(
        actor or "anonymous",
        scope.get("dashboard_role"),
        AuditAction.LOAD,
        row_count,
        target=_AUDIT_TARGET,
    )


def backlog_htmx_view(request: Any) -> Any:
    """Render the HTMX fragment for the interactive estate sprint backlog query.

    Every path returns an `HttpResponse` (a bad `?station=` is a 400), every
    interpolated field is HTML-escaped, and the fragment is `no-store` like
    `views.py::navigation_view` -- it is identity-scoped data.
    """
    from django.http import HttpResponse, HttpResponseBadRequest

    station = request.GET.get("station") or None
    if station is not None and not _STATION_RE.fullmatch(station):
        return HttpResponseBadRequest("invalid station: expected [A-Za-z0-9_-]+")
    unimplemented = _truthy(request.GET.get("unimplemented"))
    unlinked = _truthy(request.GET.get("unlinked"))
    search = request.GET.get("search") or None

    engine = SprintLedgerQueryEngine(root_dir=_engine_root())
    result = engine.query(
        station=station,
        unimplemented_only=unimplemented,
        unlinked_only=unlinked,
        search_term=search,
    )
    _record_load(request, len(result.stories))

    esc = html.escape
    rows = []
    for s in result.stories:
        badge_cls = {
            "done": "background:#238636;color:#fff",
            "in-progress": "background:#1f6feb;color:#fff",
            "backlog": "background:#9e6a03;color:#fff",
            "blocked": "background:#da3633;color:#fff",
        }.get(s.status, "background:#6e7681;color:#fff")

        rows.append(f"""
        <tr id="story-{esc(s.station)}-{esc(s.story_id.replace(".", "-"))}">
          <td><code>{esc(s.station)}</code></td>
          <td><code>{esc(s.story_id)}</code></td>
          <td><span style="padding:2px 8px;border-radius:10px;font-size:11px;font-weight:bold;{badge_cls}">{esc(s.status.upper())}</span></td>
          <td><code>{esc(s.passport_id[:8])}...</code></td>
          <td>{esc(s.jira_key or "-")}</td>
          <td>{esc(s.github_item_id or "-")}</td>
          <td>{esc(s.title)}</td>
        </tr>
        """)

    fragment = f"""
    <div id="backlog-results" class="htmx-fade-in">
      <div style="margin-bottom:1rem;color:#8b949e">
        Found <strong>{len(result.stories)}</strong> matching stories across estate.
      </div>
      <table style="width:100%;border-collapse:collapse">
        <thead>
          <tr style="border-bottom:1px solid #30363d;text-align:left;color:#8b949e">
            <th>Station</th>
            <th>Story</th>
            <th>Status</th>
            <th>Passport</th>
            <th>Jira</th>
            <th>GitHub</th>
            <th>Title</th>
          </tr>
        </thead>
        <tbody>
          {"".join(rows)}
        </tbody>
      </table>
    </div>
    """
    response = HttpResponse(fragment, content_type="text/html")
    response["Cache-Control"] = "no-store"
    return response


_GLASS_BADGE_CLS = {
    "fresh": "background:#238636;color:#fff",
    "stale": "background:#9e6a03;color:#fff",
    "failed": "background:#da3633;color:#fff",
    "unborn": "background:#484f58;color:#fff",
}


def _render_glass_fragment(reading: GlassReading, title: str, dom_id: str) -> str:
    """Shared renderer for `standup_htmx_view`/`shipped_htmx_view`: pure
    string-building, HTML-escaped (`waybill`/`loaded_at`/`message` are
    caller-supplied or free-text, same discipline `backlog_htmx_view` already
    applies). `unborn` gets its own distinct grey; `refused` (a genuinely
    different situation -- the system itself couldn't answer, not just a
    benign never-happened) falls through to the default grey badge.
    """
    esc = html.escape
    badge_cls = _GLASS_BADGE_CLS.get(reading.state or "", "background:#6e7681;color:#fff")
    state_label = esc((reading.state or "refused").upper())
    waybill = esc(reading.waybill or "-")
    loaded_at = esc(reading.loaded_at or "-")
    message_html = f'<div style="color:#8b949e">{esc(reading.message)}</div>' if reading.message else ""

    return f"""
    <div id="{esc(dom_id)}" class="htmx-fade-in">
      <div style="margin-bottom:0.5rem">
        <strong>{esc(title)}</strong>
        <span style="padding:2px 8px;border-radius:10px;font-size:11px;font-weight:bold;{badge_cls}">{state_label}</span>
      </div>
      <div>Waybill: <code>{waybill}</code></div>
      <div>Loaded at (UTC): <code>{loaded_at}</code></div>
      {message_html}
    </div>
    """


def standup_htmx_view(request: Any) -> Any:
    """Render the "any news from the vendor?" standup fragment — a
    process-facing status over the inbound corridor's most recent load.
    """
    from django.http import HttpResponse

    reading = compute_glass_reading(direction="inbound")
    fragment = _render_glass_fragment(reading, "Standup — any news from the vendor?", "glass-standup")
    response = HttpResponse(fragment, content_type="text/html")
    response["Cache-Control"] = "no-store"
    return response


def shipped_htmx_view(request: Any) -> Any:
    """Render the "what testers can currently rely on" shipped fragment.

    Reads the SAME inbound corridor reading as `standup_htmx_view` (the
    Dream's "Testers pull a shipped shelf from the last inbound extract") --
    the two views differ only in label/framing, never in data source.
    """
    from django.http import HttpResponse

    reading = compute_glass_reading(direction="inbound")
    fragment = _render_glass_fragment(reading, "Shipped — what testers can currently rely on", "glass-shipped")
    response = HttpResponse(fragment, content_type="text/html")
    response["Cache-Control"] = "no-store"
    return response
