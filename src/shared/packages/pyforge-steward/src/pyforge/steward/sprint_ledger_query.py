"""Sprint Ledger Query Module (`pyforge-steward`).

Pluggable, extensible, hookable, and feature-flagged engine for querying and
telemetry-reporting PyForge estate sprint ledgers (`sprint-status-ledger.yaml` & `epics.md`).

Supports:
- Multi-format exports (markdown, json, table, sync-matrix, herald-facts, atlas-dataset, static-dossier, jira-csv, github-json)
- Feature flag evaluation via OpenFeature SDK / flags.json / CLI overrides
- Work Passports UUID identity & PostgreSQL sync
- OpenFeature / Plugin registry architecture with pre_query, post_query, on_export hooks
- Runnable backlog selector for PyForge Marshal factory drain
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import yaml

# --- Feature Flag Evaluation ---

def eval_flag(
    flag_name: str,
    default_value: Any,
    flag_overrides: Optional[Dict[str, Any]] = None,
    flags_file_path: Optional[Path] = None,
) -> Any:
    """Evaluate a feature flag with hierarchical resolution:
    1. Direct CLI / function call override (`flag_overrides`)
    2. Environment variable (`FLAGS_<FLAG_NAME_UPPER>`)
    3. OpenFeature SDK or `flags.json` config file
    4. Provided `default_value`
    """
    if flag_overrides and flag_name in flag_overrides:
        return flag_overrides[flag_name]

    env_var = f"FLAGS_{flag_name.upper().replace('-', '_')}"
    if env_var in os.environ:
        val = os.environ[env_var].lower()
        if val in ("true", "1", "yes"):
            return True
        if val in ("false", "0", "no"):
            return False
        return val

    # Check flags.json if available
    path = flags_file_path or Path(".steward/flags.json")
    if not path.exists():
        path = Path("flags.json")
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                flags_data = json.load(f)
                if flag_name in flags_data:
                    flag_entry = flags_data[flag_name]
                    if isinstance(flag_entry, dict) and "state" in flag_entry:
                        return flag_entry["state"] == "ENABLED" or flag_entry.get("value", False)
                    return flag_entry
        except Exception:
            pass

    return default_value


# --- Dataclasses ---

@dataclass
class WorkPassportItem:
    """Work Passport identity record for a story across systems."""
    passport_id: str
    story_id: str
    station: str
    epic_id: str
    title: str
    status: str  # backlog, in-progress, done, blocked
    jira_key: Optional[str] = None
    github_item_id: Optional[str] = None
    effort: Optional[str] = None
    deps: List[str] = field(default_factory=list)
    fr_ad: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


StoryItem = WorkPassportItem


@dataclass
class EpicItem:
    """Epic metadata containing owned stories."""
    epic_id: str
    station: str
    title: str
    status: str
    stories: List[WorkPassportItem] = field(default_factory=list)


@dataclass
class StationProgress:
    """Completion metrics for a station."""
    station: str
    total_stories: int = 0
    done: int = 0
    in_progress: int = 0
    backlog: int = 0
    blocked: int = 0
    completion_pct: float = 0.0


@dataclass
class EstateSummary:
    """Aggregate completion metrics across the estate."""
    stations: Dict[str, StationProgress] = field(default_factory=dict)
    total_stories: int = 0
    total_done: int = 0
    total_in_progress: int = 0
    total_backlog: int = 0
    total_blocked: int = 0
    overall_completion_pct: float = 0.0


@dataclass
class QueryResult:
    """Container for query results and metadata."""
    summary: EstateSummary
    epics: List[EpicItem]
    stories: List[WorkPassportItem]
    query_flags: Dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# --- Interfaces & Plugin Registries ---

class QueryFormatterPlugin(ABC):
    """Abstract interface for formatters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Formatter identifier (e.g. 'markdown', 'json')."""
        pass

    @abstractmethod
    def format(self, result: QueryResult, **kwargs: Any) -> str:
        """Format QueryResult into string output."""
        pass


class LedgerSourcePlugin(ABC):
    """Abstract interface for ledger data loaders."""

    @abstractmethod
    def load_station(self, station: str, project_dir: Path) -> Tuple[Dict[str, str], List[EpicItem]]:
        """Load status ledger and epics for a station."""
        pass


class LedgerQueryHook(ABC):
    """Hook interface for query lifecycle interception."""

    def pre_query(self, filters: Dict[str, Any]) -> None:
        pass

    def post_query(self, result: QueryResult) -> None:
        pass

    def on_export(self, format_name: str, output: str) -> None:
        pass


class FormatterRegistry:
    """Registry for query formatters."""

    def __init__(self) -> None:
        self._formatters: Dict[str, QueryFormatterPlugin] = {}

    def register(self, formatter: QueryFormatterPlugin) -> None:
        self._formatters[formatter.name] = formatter

    def get(self, name: str) -> QueryFormatterPlugin:
        if name not in self._formatters:
            raise KeyError(f"Unknown formatter: '{name}'. Available: {list(self._formatters.keys())}")
        return self._formatters[name]

    def list_formatters(self) -> List[str]:
        return sorted(list(self._formatters.keys()))


class HookRegistry:
    """Registry for execution hooks."""

    def __init__(self) -> None:
        self._hooks: List[LedgerQueryHook] = []

    def register(self, hook: LedgerQueryHook) -> None:
        self._hooks.append(hook)

    def trigger_pre_query(self, filters: Dict[str, Any]) -> None:
        for hook in self._hooks:
            hook.pre_query(filters)

    def trigger_post_query(self, result: QueryResult) -> None:
        for hook in self._hooks:
            hook.post_query(result)

    def trigger_on_export(self, format_name: str, output: str) -> None:
        for hook in self._hooks:
            hook.on_export(format_name, output)


# --- Built-in Formatter Implementations ---

class MarkdownFormatter(QueryFormatterPlugin):
    @property
    def name(self) -> str:
        return "markdown"

    def format(self, result: QueryResult, **kwargs: Any) -> str:
        lines: List[str] = []
        lines.append("# Estate Sprint Ledger Query Report")
        lines.append(f"*Generated at: {result.generated_at}*\n")
        lines.append("## Estate Completion Summary\n")
        lines.append(
            f"- **Total Stories:** {result.summary.total_stories} | "
            f"**Done:** {result.summary.total_done} | "
            f"**In Progress:** {result.summary.total_in_progress} | "
            f"**Backlog:** {result.summary.total_backlog} | "
            f"**Blocked:** {result.summary.total_blocked}"
        )
        lines.append(f"- **Overall Completion:** {result.summary.overall_completion_pct:.1f}%\n")

        lines.append("| Station | Total | Done | In Progress | Backlog | Blocked | % Complete |")
        lines.append("|---|---|---|---|---|---|---|")
        for st_name, st in sorted(result.summary.stations.items()):
            lines.append(
                f"| `{st_name}` | {st.total_stories} | {st.done} | {st.in_progress} | "
                f"{st.backlog} | {st.blocked} | {st.completion_pct:.1f}% |"
            )

        lines.append("\n## Matching Stories\n")
        if not result.stories:
            lines.append("*No stories matched the query filters.*")
        else:
            for s in result.stories:
                status_badge = f"**[{s.status.upper()}]**"
                jira_str = f" Jira: `{s.jira_key}`" if s.jira_key else ""
                gh_str = f" GH: `{s.github_item_id}`" if s.github_item_id else ""
                lines.append(f"- {status_badge} `{s.station}` / Story `{s.story_id}`: **{s.title}**{jira_str}{gh_str}")
                lines.append(f"  - Passport UUID: `{s.passport_id}`")
                if s.effort or s.deps or s.fr_ad:
                    meta_parts = []
                    if s.effort:
                        meta_parts.append(f"Effort: {s.effort}")
                    if s.deps:
                        meta_parts.append(f"Deps: {', '.join(s.deps)}")
                    if s.fr_ad:
                        meta_parts.append(f"FR/AD: {s.fr_ad}")
                    lines.append(f"  - Metadata: {' | '.join(meta_parts)}")

        return "\n".join(lines)


class SummaryFormatter(QueryFormatterPlugin):
    @property
    def name(self) -> str:
        return "summary"

    def format(self, result: QueryResult, **kwargs: Any) -> str:
        s = result.summary
        return (
            f"Estate Sprint Ledger Summary: {s.total_stories} stories across {len(s.stations)} stations. "
            f"Done: {s.total_done} ({s.overall_completion_pct:.1f}%), "
            f"In Progress: {s.total_in_progress}, Backlog: {s.total_backlog}, Blocked: {s.total_blocked}. "
            f"Matching Query Stories: {len(result.stories)}"
        )


class JSONFormatter(QueryFormatterPlugin):
    @property
    def name(self) -> str:
        return "json"

    def format(self, result: QueryResult, **kwargs: Any) -> str:
        payload = {
            "$schema": "urn:local-recipes:pyforge-steward:sprint-ledger-query-schema",
            "generated_at": result.generated_at,
            "summary": asdict(result.summary),
            "matching_stories_count": len(result.stories),
            "stories": [s.to_dict() for s in result.stories],
            "epics": [
                {
                    "epic_id": e.epic_id,
                    "station": e.station,
                    "title": e.title,
                    "status": e.status,
                    "story_ids": [st.story_id for st in e.stories],
                }
                for e in result.epics
            ],
            "query_flags": result.query_flags,
        }
        return json.dumps(payload, indent=2)


class TableFormatter(QueryFormatterPlugin):
    @property
    def name(self) -> str:
        return "table"

    def format(self, result: QueryResult, **kwargs: Any) -> str:
        if not result.stories:
            return "No stories matched."

        headers = ["Station", "Story ID", "Status", "Jira Key", "GitHub Item", "Title"]
        rows = []
        for s in result.stories:
            rows.append([
                s.station,
                s.story_id,
                s.status.upper(),
                s.jira_key or "-",
                s.github_item_id or "-",
                s.title[:45] + ("..." if len(s.title) > 45 else "")
            ])

        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, val in enumerate(row):
                col_widths[i] = max(col_widths[i], len(val))

        sep = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
        header_line = "| " + " | ".join(f"{headers[i]:<{col_widths[i]}}" for i in range(len(headers))) + " |"

        lines = [sep, header_line, sep]
        for row in rows:
            line = "| " + " | ".join(f"{row[i]:<{col_widths[i]}}" for i in range(len(row))) + " |"
            lines.append(line)
        lines.append(sep)
        return "\n".join(lines)


class SyncMatrixFormatter(QueryFormatterPlugin):
    @property
    def name(self) -> str:
        return "sync-matrix"

    def format(self, result: QueryResult, **kwargs: Any) -> str:
        lines = []
        lines.append("# 3-Way Alignment Sync Matrix (Ledger ↔ Jira ↔ GitHub Projects V2)")
        lines.append(f"*Generated at: {result.generated_at}*\n")
        lines.append("| Station | Story ID | Ledger Status | Jira Key | GitHub Item | Passport Alignment Status |")
        lines.append("|---|---|---|---|---|---|")

        unlinked_count = 0
        aligned_count = 0

        for s in result.stories:
            has_jira = bool(s.jira_key)
            has_gh = bool(s.github_item_id)

            if not has_jira or not has_gh:
                unlinked_count += 1
                alignment = "⚠️ UNLINKED (" + (
                    "Missing Jira & GH" if not has_jira and not has_gh else (
                        "Missing Jira" if not has_jira else "Missing GH"
                    )
                ) + ")"
            else:
                aligned_count += 1
                alignment = "✅ ALIGNED"

            lines.append(
                f"| `{s.station}` | `{s.story_id}` | `{s.status}` | "
                f"`{s.jira_key or '-'}` | `{s.github_item_id or '-'}` | {alignment} |"
            )

        lines.append(f"\n- **Total Queried:** {len(result.stories)}")
        lines.append(f"- **Fully Aligned Pairs:** {aligned_count}")
        lines.append(f"- **Unlinked / Partial Items:** {unlinked_count}")
        return "\n".join(lines)


class HeraldFactsFormatter(QueryFormatterPlugin):
    @property
    def name(self) -> str:
        return "herald-facts"

    def format(self, result: QueryResult, **kwargs: Any) -> str:
        s = result.summary
        facts = {
            "kind": "herald_fact_ledger",
            "schema_version": "1.0",
            "generated_at": result.generated_at,
            "title": "Estate Sprint Backlog Facts",
            "metrics": {
                "total_stories": s.total_stories,
                "done_stories": s.total_done,
                "in_progress_stories": s.total_in_progress,
                "backlog_stories": s.total_backlog,
                "blocked_stories": s.total_blocked,
                "overall_completion_pct": round(s.overall_completion_pct, 2),
            },
            "station_breakdown": {
                st_name: {
                    "total": st.total_stories,
                    "done": st.done,
                    "in_progress": st.in_progress,
                    "backlog": st.backlog,
                    "blocked": st.blocked,
                    "completion_pct": round(st.completion_pct, 2),
                }
                for st_name, st in sorted(s.stations.items())
            },
        }
        return yaml.dump(facts, sort_keys=False)


class AtlasDatasetFormatter(QueryFormatterPlugin):
    @property
    def name(self) -> str:
        return "atlas-dataset"

    def format(self, result: QueryResult, **kwargs: Any) -> str:
        dataset = {
            "dataset_id": "sprint_telemetry",
            "generated_at": result.generated_at,
            "records": [
                {
                    "passport_id": s.passport_id,
                    "story_id": s.story_id,
                    "station": s.station,
                    "epic_id": s.epic_id,
                    "title": s.title,
                    "status": s.status,
                    "jira_key": s.jira_key or "",
                    "github_item_id": s.github_item_id or "",
                    "effort": s.effort or "",
                }
                for s in result.stories
            ]
        }
        return json.dumps(dataset, indent=2)


class StaticDossierFormatter(QueryFormatterPlugin):
    @property
    def name(self) -> str:
        return "static-dossier"

    def format(self, result: QueryResult, **kwargs: Any) -> str:
        s = result.summary
        rows_html = []
        for st in result.stories:
            status_cls = {
                "done": "badge-done",
                "in-progress": "badge-progress",
                "backlog": "badge-backlog",
                "blocked": "badge-blocked",
            }.get(st.status, "badge-backlog")

            rows_html.append(f"""
            <tr>
              <td><code>{st.station}</code></td>
              <td><code>{st.story_id}</code></td>
              <td><span class="badge {status_cls}">{st.status.upper()}</span></td>
              <td><code>{st.passport_id[:8]}...</code></td>
              <td>{st.jira_key or '-'}</td>
              <td>{st.github_item_id or '-'}</td>
              <td><strong>{st.title}</strong></td>
            </tr>
            """)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PyForge Sprint Backlog Dossier</title>
  <style>
    :root {{
      --bg-color: #0d1117;
      --card-bg: rgba(22, 27, 34, 0.8);
      --border-color: #30363d;
      --text-color: #c9d1d9;
      --accent-blue: #58a6ff;
      --accent-green: #3fb950;
      --accent-yellow: #d29922;
      --accent-red: #f85149;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg-color);
      color: var(--text-color);
      margin: 0;
      padding: 2rem;
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
    }}
    h1 {{ color: #ffffff; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 1rem;
      backdrop-filter: blur(10px);
    }}
    .card h3 {{ margin: 0 0 0.5rem 0; font-size: 0.9rem; color: #8b949e; text-transform: uppercase; }}
    .card .value {{ font-size: 1.8rem; font-weight: bold; color: #ffffff; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      overflow: hidden;
    }}
    th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid var(--border-color); }}
    th {{ background: rgba(33, 38, 45, 0.9); color: #ffffff; font-size: 0.85rem; text-transform: uppercase; }}
    .badge {{
      display: inline-block;
      padding: 0.25rem 0.5rem;
      border-radius: 12px;
      font-size: 0.75rem;
      font-weight: bold;
    }}
    .badge-done {{ background: rgba(63, 185, 80, 0.2); color: var(--accent-green); border: 1px solid var(--accent-green); }}
    .badge-progress {{ background: rgba(88, 166, 255, 0.2); color: var(--accent-blue); border: 1px solid var(--accent-blue); }}
    .badge-backlog {{ background: rgba(210, 153, 34, 0.2); color: var(--accent-yellow); border: 1px solid var(--accent-yellow); }}
    .badge-blocked {{ background: rgba(248, 81, 73, 0.2); color: var(--accent-red); border: 1px solid var(--accent-red); }}
  </style>
</head>
<body>
  <div class="container">
    <h1>PyForge Estate Sprint Backlog Dossier</h1>
    <p><em>Generated at: {result.generated_at}</em></p>
    
    <div class="grid">
      <div class="card">
        <h3>Total Stories</h3>
        <div class="value">{s.total_stories}</div>
      </div>
      <div class="card">
        <h3>Done</h3>
        <div class="value" style="color: var(--accent-green);">{s.total_done}</div>
      </div>
      <div class="card">
        <h3>In Progress</h3>
        <div class="value" style="color: var(--accent-blue);">{s.total_in_progress}</div>
      </div>
      <div class="card">
        <h3>Backlog</h3>
        <div class="value" style="color: var(--accent-yellow);">{s.total_backlog}</div>
      </div>
      <div class="card">
        <h3>Blocked</h3>
        <div class="value" style="color: var(--accent-red);">{s.total_blocked}</div>
      </div>
    </div>

    <table>
      <thead>
        <tr>
          <th>Station</th>
          <th>Story ID</th>
          <th>Status</th>
          <th>Passport UUID</th>
          <th>Jira</th>
          <th>GitHub</th>
          <th>Title</th>
        </tr>
      </thead>
      <tbody>
        {"".join(rows_html)}
      </tbody>
    </table>
  </div>
</body>
</html>
"""
        return html


class JiraCSVFormatter(QueryFormatterPlugin):
    @property
    def name(self) -> str:
        return "jira-csv"

    def format(self, result: QueryResult, **kwargs: Any) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Issue Type", "Key", "Summary", "Status", "Project", "Custom Field (Passport ID)"])
        for s in result.stories:
            jira_status = {
                "done": "Done",
                "in-progress": "In Progress",
                "backlog": "To Do",
                "blocked": "Blocked",
            }.get(s.status, "To Do")
            writer.writerow(["Task", s.jira_key or "", s.title, jira_status, s.station.upper(), s.passport_id])
        return output.getvalue()


class GitHubJSONFormatter(QueryFormatterPlugin):
    @property
    def name(self) -> str:
        return "github-json"

    def format(self, result: QueryResult, **kwargs: Any) -> str:
        items = [
            {
                "content_type": "DraftIssue",
                "item_id": s.github_item_id or "",
                "title": f"[{s.station}] {s.title}",
                "body": f"Story ID: `{s.story_id}`\nPassport UUID: `{s.passport_id}`\nStatus: `{s.status}`",
                "status_field_value": s.status,
            }
            for s in result.stories
        ]
        return json.dumps({"github_project_items": items}, indent=2)


# --- Core Query Engine ---

class SprintLedgerQueryEngine:
    """Engine for loading, filtering, querying, and exporting sprint ledgers."""

    def __init__(self, root_dir: Optional[Path] = None) -> None:
        self.root_dir = root_dir or Path.cwd()
        self.formatters = FormatterRegistry()
        self.hooks = HookRegistry()

        # Register default formatters
        self.formatters.register(MarkdownFormatter())
        self.formatters.register(SummaryFormatter())
        self.formatters.register(JSONFormatter())
        self.formatters.register(TableFormatter())
        self.formatters.register(SyncMatrixFormatter())
        self.formatters.register(HeraldFactsFormatter())
        self.formatters.register(AtlasDatasetFormatter())
        self.formatters.register(StaticDossierFormatter())
        self.formatters.register(JiraCSVFormatter())
        self.formatters.register(GitHubJSONFormatter())

    def _parse_epics_file(self, epics_path: Path, station: str, status_map: Dict[str, str]) -> Tuple[List[EpicItem], List[WorkPassportItem]]:
        epics: List[EpicItem] = []
        stories: List[WorkPassportItem] = []

        if not epics_path.exists():
            return epics, stories

        content = epics_path.read_text(encoding="utf-8")
        current_epic: Optional[EpicItem] = None

        # Regex patterns for story parsing
        story_header_re = re.compile(r"^###\s+Story\s+([\d\.]+):\s*(.+)$", re.MULTILINE)
        epic_header_re = re.compile(r"^##\s+Epic\s+([\d\.]+):\s*(.+)$", re.MULTILINE)

        lines = content.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            m_epic = epic_header_re.match(line)
            if m_epic:
                epic_id = m_epic.group(1).strip()
                title = m_epic.group(2).strip()
                current_epic = EpicItem(
                    epic_id=epic_id,
                    station=station,
                    title=title,
                    status="in-progress",
                    stories=[]
                )
                epics.append(current_epic)
                i += 1
                continue

            m_story = story_header_re.match(line)
            if m_story:
                story_id = m_story.group(1).strip()
                title = m_story.group(2).strip()

                # Search surrounding block for effort/deps/fr_ad
                block_lines = []
                j = i + 1
                while j < len(lines) and not lines[j].startswith("### Story ") and not lines[j].startswith("## Epic "):
                    block_lines.append(lines[j])
                    j += 1

                block_text = "\n".join(block_lines)

                effort = None
                m_eff = re.search(r"\*\*Effort:\*\*\s*([^\s•\n]+)", block_text)
                if m_eff:
                    effort = m_eff.group(1).strip()

                deps: List[str] = []
                m_deps = re.search(r"\*\*Deps:\*\*\s*([^\n•]+)", block_text)
                if m_deps:
                    dep_raw = m_deps.group(1).strip()
                    if dep_raw and dep_raw != "—":
                        deps = [d.strip() for d in dep_raw.split(",") if d.strip()]

                fr_ad = None
                m_fr = re.search(r"\*\*FR/AD:\*\*\s*([^\n•]+)", block_text)
                if m_fr:
                    fr_ad = m_fr.group(1).strip()

                # Status lookup from status_map or block_text
                key_prefix = f"{story_id.replace('.', '-')}-"
                found_status = "backlog"
                for k, v in status_map.items():
                    if k.startswith(key_prefix) or k == story_id.replace(".", "-"):
                        found_status = v
                        break
                else:
                    m_status = re.search(r"\*\*Status:\*\*\s*([^\n•]+)", block_text)
                    if m_status:
                        raw_st = m_status.group(1).strip().lower()
                        if "done" in raw_st:
                            found_status = "done"
                        elif "in-progress" in raw_st or "in progress" in raw_st:
                            found_status = "in-progress"
                        elif "blocked" in raw_st:
                            found_status = "blocked"

                # Generate deterministic UUID v5 for Work Passport identity
                passport_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"pyforge:{station}:{story_id}"))

                # Extract Jira key / GH item id if present in fr_ad or title
                jira_key = None
                m_jira = re.search(r"JIRA-([A-Z0-9]+-\d+)", block_text)
                if m_jira:
                    jira_key = m_jira.group(1)

                github_item_id = None
                m_gh = re.search(r"GH-(\d+)", block_text)
                if m_gh:
                    github_item_id = m_gh.group(1)

                item = WorkPassportItem(
                    passport_id=passport_id,
                    story_id=story_id,
                    station=station,
                    epic_id=current_epic.epic_id if current_epic else "unassigned",
                    title=title,
                    status=found_status,
                    jira_key=jira_key,
                    github_item_id=github_item_id,
                    effort=effort,
                    deps=deps,
                    fr_ad=fr_ad,
                )

                stories.append(item)
                if current_epic:
                    current_epic.stories.append(item)

                i = j
                continue

            i += 1

        return epics, stories

    def query(
        self,
        station: Optional[str] = None,
        statuses: Optional[List[str]] = None,
        unimplemented_only: bool = False,
        unlinked_only: bool = False,
        epic_id: Optional[str] = None,
        search_term: Optional[str] = None,
        flag_overrides: Optional[Dict[str, Any]] = None,
    ) -> QueryResult:
        """Execute a query against estate sprint ledgers."""
        filters = {
            "station": station,
            "statuses": statuses,
            "unimplemented_only": unimplemented_only,
            "unlinked_only": unlinked_only,
            "epic_id": epic_id,
            "search_term": search_term,
        }
        self.hooks.trigger_pre_query(filters)

        projects_dir = self.root_dir / "_bmad-output" / "projects"
        stations_to_scan = []

        if station:
            stations_to_scan = [station]
        elif projects_dir.exists():
            stations_to_scan = [d.name for d in projects_dir.iterdir() if d.is_dir()]

        all_stories: List[WorkPassportItem] = []
        all_epics: List[EpicItem] = []
        station_summaries: Dict[str, StationProgress] = {}

        total_done = 0
        total_in_progress = 0
        total_backlog = 0
        total_blocked = 0

        for st in sorted(stations_to_scan):
            st_dir = projects_dir / st / "planning-artifacts"
            ledger_file = st_dir / "sprint-status-ledger.yaml"
            epics_file = st_dir / "epics.md"

            status_map: Dict[str, str] = {}
            if ledger_file.exists():
                try:
                    with open(ledger_file, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        if isinstance(data, dict) and "development_status" in data:
                            status_map = data["development_status"]
                except Exception:
                    pass

            epics, stories = self._parse_epics_file(epics_file, st, status_map)

            st_done = sum(1 for s in stories if s.status == "done")
            st_prog = sum(1 for s in stories if s.status == "in-progress")
            st_back = sum(1 for s in stories if s.status == "backlog")
            st_block = sum(1 for s in stories if s.status == "blocked")
            st_total = len(stories)
            st_pct = (st_done / st_total * 100.0) if st_total > 0 else 0.0

            station_summaries[st] = StationProgress(
                station=st,
                total_stories=st_total,
                done=st_done,
                in_progress=st_prog,
                backlog=st_back,
                blocked=st_block,
                completion_pct=st_pct,
            )

            total_done += st_done
            total_in_progress += st_prog
            total_backlog += st_back
            total_blocked += st_block

            all_stories.extend(stories)
            all_epics.extend(epics)

        tot_stories = len(all_stories)
        overall_pct = (total_done / tot_stories * 100.0) if tot_stories > 0 else 0.0

        estate_summary = EstateSummary(
            stations=station_summaries,
            total_stories=tot_stories,
            total_done=total_done,
            total_in_progress=total_in_progress,
            total_backlog=total_backlog,
            total_blocked=total_blocked,
            overall_completion_pct=overall_pct,
        )

        # Apply Filters
        filtered_stories = all_stories

        if unimplemented_only:
            filtered_stories = [s for s in filtered_stories if s.status in ("backlog", "in-progress", "blocked")]

        if statuses:
            norm_statuses = [st.lower().strip() for st in statuses]
            filtered_stories = [s for s in filtered_stories if s.status in norm_statuses]

        if unlinked_only:
            filtered_stories = [s for s in filtered_stories if not s.jira_key or not s.github_item_id]

        if epic_id:
            filtered_stories = [s for s in filtered_stories if s.epic_id == epic_id]

        if search_term:
            term = search_term.lower()
            filtered_stories = [
                s for s in filtered_stories
                if term in s.title.lower() or term in s.story_id.lower() or term in (s.jira_key or "").lower()
            ]

        result = QueryResult(
            summary=estate_summary,
            epics=all_epics,
            stories=filtered_stories,
            query_flags=filters,
        )
        self.hooks.trigger_post_query(result)
        return result

    def export(self, result: QueryResult, format_name: str = "markdown", **kwargs: Any) -> str:
        """Export QueryResult using named formatter."""
        formatter = self.formatters.get(format_name)
        output = formatter.format(result, **kwargs)
        self.hooks.trigger_on_export(format_name, output)
        return output


# --- Helpers & Postgres Sync ---

def sync_to_postgres(result: QueryResult, db_connection_url: Optional[str] = None) -> Dict[str, Any]:
    """Sync Work Passports identity records to PostgreSQL database / Django ORM."""
    synced_records = []
    try:
        from pyforge.steward.dashboard.models import WorkPassport
        from django.db import transaction

        with transaction.atomic():
            for s in result.stories:
                obj, created = WorkPassport.objects.update_or_create(
                    passport_id=s.passport_id,
                    defaults={
                        "story_id": s.story_id,
                        "station": s.station,
                        "epic_id": s.epic_id,
                        "title": s.title,
                        "status": s.status,
                        "jira_key": s.jira_key,
                        "github_item_id": s.github_item_id,
                        "effort": s.effort,
                    }
                )
                synced_records.append(obj.passport_id)
        return {"status": "success", "synced_count": len(synced_records), "method": "django-orm"}
    except Exception as exc:
        # Fallback to JSON payload generation if Django DB is uninitialized
        return {
            "status": "fallback_payload",
            "count": len(result.stories),
            "message": f"Django ORM unavailable ({exc}), minted Work Passport UUID payload ready for migration.",
            "passports": [s.passport_id for s in result.stories],
        }


def get_runnable_backlog(engine: SprintLedgerQueryEngine, station: Optional[str] = None) -> List[WorkPassportItem]:
    """Select stories in 'backlog' status whose dependencies are all 'done'."""
    res = engine.query(station=station, statuses=["backlog", "done"])
    done_ids: Set[str] = {s.story_id for s in res.stories if s.status == "done"}
    runnable: List[WorkPassportItem] = []

    for s in res.stories:
        if s.status == "backlog":
            deps_met = all(dep in done_ids for dep in s.deps) if s.deps else True
            if deps_met:
                runnable.append(s)

    return runnable


class LedgerQueryDuty:
    """Duty implementation for 'pyforge steward ledger-query' (Story 63.5)."""

    name = "ledger-query"

    def run(self, ns: Any) -> Any:
        from pyforge.steward.interfaces import DutyResult

        engine = SprintLedgerQueryEngine()

        unimplemented = getattr(ns, "unimplemented", False)
        unlinked = getattr(ns, "unlinked", False)
        station = getattr(ns, "station", None)
        status_raw = getattr(ns, "status", None)
        search = getattr(ns, "search", None)
        format_name = getattr(ns, "format", "markdown")
        output_file = getattr(ns, "output", None)
        sync_pg = getattr(ns, "sync_postgres", False)

        statuses = [s.strip() for s in status_raw.split(",")] if status_raw else None

        result = engine.query(
            station=station,
            statuses=statuses,
            unimplemented_only=unimplemented,
            unlinked_only=unlinked,
            search_term=search,
        )

        output_str = engine.export(result, format_name=format_name)

        if output_file:
            path = Path(output_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(output_str, encoding="utf-8")

        if sync_pg:
            sync_res = sync_to_postgres(result)
            output_str += f"\n\n[PostgreSQL Work Passport Sync Result: {sync_res['status']} ({sync_res.get('synced_count', sync_res.get('count', 0))} records)]"

        return DutyResult(ok=True, summary=output_str)

