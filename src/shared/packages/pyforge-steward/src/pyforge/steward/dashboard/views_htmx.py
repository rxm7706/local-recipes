"""HTMX view handlers for pyforge-steward sprint backlog dashboard."""

from __future__ import annotations

from typing import Any
from pyforge.steward.sprint_ledger_query import SprintLedgerQueryEngine


def backlog_htmx_view(request: Any) -> Any:
    """Render HTMX fragment for interactive estate sprint backlog query."""
    try:
        from django.http import HttpResponse
    except ImportError:
        return "Django not installed."

    station = request.GET.get("station") or None
    unimplemented = request.GET.get("unimplemented") == "true"
    unlinked = request.GET.get("unlinked") == "true"
    search = request.GET.get("search") or None

    engine = SprintLedgerQueryEngine()
    result = engine.query(
        station=station,
        unimplemented_only=unimplemented,
        unlinked_only=unlinked,
        search_term=search,
    )

    rows = []
    for s in result.stories:
        badge_cls = {
            "done": "background:#238636;color:#fff",
            "in-progress": "background:#1f6feb;color:#fff",
            "backlog": "background:#9e6a03;color:#fff",
            "blocked": "background:#da3633;color:#fff",
        }.get(s.status, "background:#6e7681;color:#fff")

        rows.append(f"""
        <tr id="story-{s.station}-{s.story_id.replace('.', '-')}">
          <td><code>{s.station}</code></td>
          <td><code>{s.story_id}</code></td>
          <td><span style="padding:2px 8px;border-radius:10px;font-size:11px;font-weight:bold;{badge_cls}">{s.status.upper()}</span></td>
          <td><code>{s.passport_id[:8]}...</code></td>
          <td>{s.jira_key or '-'}</td>
          <td>{s.github_item_id or '-'}</td>
          <td>{s.title}</td>
        </tr>
        """)

    html = f"""
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
    return HttpResponse(html, content_type="text/html")
