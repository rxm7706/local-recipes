"""Sprint Ledger Query Module (`pyforge-steward`, Story 65.1).

Pluggable, extensible, hookable, and feature-flagged engine for querying and
telemetry-reporting PyForge estate sprint ledgers -- each station's TRACKED
`planning-artifacts/sprint-status-ledger.yaml` and `epics.md` under
`_bmad-output/projects/<station>/` (never the gitignored Tier-3 feed, never
`docs/dashboard/data.js`).

Supports:
- Multi-format exports (markdown, summary, json, table, sync-matrix, herald-facts,
  atlas-dataset, static-dossier, jira-csv, github-json), registered through
  `FormatterRegistry`, never hard-coded in the CLI.
- Ledger sources registered through `SourceRegistry` (`TrackedLedgerSource` is the
  default and wraps the tracked-twin parser below).
- Lifecycle hooks (`LedgerQueryHook`: `pre_query` / `post_query` / `on_export`); a hook
  that raises is reported on stderr and in `QueryResult.warnings`, never aborts the query.
- Feature flags, resolved by `eval_flag()` in this order and with NO SDK dependency
  (nothing here imports `openfeature`; the `flags.json` entry shape is merely
  OpenFeature-shaped): (1) a caller's `flag_overrides` dict -- the CLI's repeatable
  `--flag name=value`; (2) the `FLAGS_<NAME>` environment variable (an empty value
  counts as unset); (3) a `flags.json` file -- the explicit `flags_file_path`, else
  `<repo-root>/.steward/flags.json`; an explicit path that does not exist falls through
  to the default, never to a cwd-relative file; (4) the caller's `default_value`.
  Every optional integration sits behind one of these flags (`FORMATTER_FLAGS`,
  `FLAG_POSTGRES_SYNC`); a flag left off produces no write to its target.
- Work Passports: a deterministic UUIDv5 identity per story (`passport_id`) that
  outlives renames; Jira / GitHub ids are aliases bound to it. `sync_to_postgres()` is
  a thin call into the `pyforge-steward[dashboard]` extra's `passport_sync`.
- `get_runnable_backlog()` for Marshal's dispatch selection, using marshal's own
  dependency grammar (restated below) keyed by `(station, story_id)`.
- Story 65.2 (CAP-150): every story carries a `next` field -- `done`, `running`,
  `ready` (the same predicate `get_runnable_backlog()` uses), `waits on S-x.y[, …]`,
  `blocked`, or `?` (the running fact was unavailable). `--ready`/`--running`
  filter on it. The `running` fact comes from ONE `marshal watch --fleet --format
  json` call per query, via `pyforge.core.process` -- never a `pyforge.marshal`
  import, never a read of marshal's own journal. Unreachable marshal fails open:
  every `next` that would read `running` reads `?` instead, with one warning; the
  fact is this checkout's own (marshal's Tier-3 state is per clone).

stdout carries payload only; every diagnostic this module emits goes to stderr.
"""

from __future__ import annotations

import csv
import html
import io
import json
import os
import re
import sys
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import yaml

from pyforge.core.process import PosixProcess, ProcessError, ProcessPort

# ── Repo-root resolution (mirrors `provision.py`'s walk-up precedent, keyed on
# `scripts/bmad-loop-worktree` -- the one marker path that exists exactly once
# in this repo, at the true root; duplicated per duty module, never imported
# cross-duty) ─────────────────────────────────────────────────────────────────

_BMAD_LOOP_WORKTREE_RELATIVE_PATH = Path("scripts/bmad-loop-worktree")
_FLAGS_RELATIVE_PATH = Path(".steward/flags.json")
_PROJECTS_RELATIVE_PATH = Path("_bmad-output/projects")

# The JSON schema the `json` formatter's `$schema` URN promises.
SCHEMA_URN = "urn:local-recipes:pyforge-steward:sprint-ledger-query-schema"
SCHEMA_PATH = Path(__file__).resolve().parent / "data" / "sprint-ledger-query.schema.json"


def repo_root() -> Path:
    """Return the local-recipes checkout root (walk-up on ``scripts/bmad-loop-worktree``)."""
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / _BMAD_LOOP_WORKTREE_RELATIVE_PATH).is_file():
            return ancestor
    raise RuntimeError(
        f"sprint_ledger_query.py: could not locate {_BMAD_LOOP_WORKTREE_RELATIVE_PATH} "
        f"by walking up from {here} — this module must live inside a "
        "local-recipes checkout."
    )


def _warn(message: str) -> None:
    """Diagnostics go to stderr, never stdout (payload-only)."""
    print(f"sprint-ledger-query: {message}", file=sys.stderr)


# --- Feature Flags ---

FLAG_POSTGRES_SYNC = "enable_postgres_sync"
FLAG_DOSSIER_EXPORT = "enable_dossier_export"
FLAG_VIZRO_DATASET = "enable_vizro_dataset"
FLAG_HERALD_FACTS = "enable_herald_facts"
FLAG_JIRA_GITHUB_MATRIX = "enable_jira_github_matrix"

# Formatter name -> the flag that gates it (every optional integration, CAP-2).
FORMATTER_FLAGS: Dict[str, str] = {
    "static-dossier": FLAG_DOSSIER_EXPORT,
    "herald-facts": FLAG_HERALD_FACTS,
    "atlas-dataset": FLAG_VIZRO_DATASET,
    "sync-matrix": FLAG_JIRA_GITHUB_MATRIX,
    "jira-csv": FLAG_JIRA_GITHUB_MATRIX,
    "github-json": FLAG_JIRA_GITHUB_MATRIX,
}

_TRUTHY = frozenset({"true", "1", "yes", "on"})
_FALSY = frozenset({"false", "0", "no", "off"})


def flag_env_var(flag_name: str) -> str:
    return f"FLAGS_{flag_name.upper().replace('-', '_')}"


def flag_off_message(flag_name: str) -> str:
    return (
        f"flag {flag_name} is off (set {flag_env_var(flag_name)}=true, "
        f"flags.json, or --flag {flag_name}=true)"
    )


def _coerce_flag_value(raw: Any) -> Any:
    """`true/1/yes/on` -> True, `false/0/no/off` -> False, anything else verbatim."""
    if isinstance(raw, str):
        low = raw.strip().lower()
        if low in _TRUTHY:
            return True
        if low in _FALSY:
            return False
    return raw


def parse_flag_overrides(pairs: Optional[List[str]]) -> Dict[str, Any]:
    """Turn the CLI's repeatable `--flag name=value` into an overrides dict."""
    overrides: Dict[str, Any] = {}
    for pair in pairs or []:
        name, sep, value = pair.partition("=")
        name = name.strip()
        if not name:
            raise ValueError(f"--flag expects name=value, got {pair!r}")
        overrides[name] = _coerce_flag_value(value) if sep else True
    return overrides


def _default_flags_file() -> Optional[Path]:
    try:
        return repo_root() / _FLAGS_RELATIVE_PATH
    except RuntimeError:
        return None


def eval_flag(
    flag_name: str,
    default_value: Any,
    flag_overrides: Optional[Dict[str, Any]] = None,
    flags_file_path: Optional[Path] = None,
) -> Any:
    """Evaluate a feature flag with hierarchical resolution:
    1. Direct CLI / function call override (`flag_overrides`)
    2. Environment variable (`FLAGS_<FLAG_NAME_UPPER>`; empty = unset)
    3. `flags.json` (`flags_file_path`, else `<repo-root>/.steward/flags.json`;
       an explicit path that does not exist is NOT replaced by a cwd fallback)
    4. Provided `default_value`

    A `flags.json` entry is either a bare value or `{"state": "ENABLED"|"DISABLED",
    "value": ...}`; `DISABLED` is False regardless of `value`.
    """
    if flag_overrides and flag_name in flag_overrides:
        return _coerce_flag_value(flag_overrides[flag_name])

    raw_env = os.environ.get(flag_env_var(flag_name))
    if raw_env is not None and raw_env.strip() != "":
        return _coerce_flag_value(raw_env)

    path = flags_file_path if flags_file_path is not None else _default_flags_file()
    if path is not None and path.is_file():
        try:
            flags_data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            _warn(f"ignoring unreadable flags file {path}: {exc}")
            flags_data = {}
        if isinstance(flags_data, dict) and flag_name in flags_data:
            entry = flags_data[flag_name]
            if isinstance(entry, dict) and "state" in entry:
                if str(entry["state"]).upper() == "DISABLED":
                    return False
                return entry.get("value", True)
            return entry

    return default_value


# --- Statuses ---

# Every status the tracked ledgers use, each with its own `StationProgress` bucket;
# anything else lands in `other` so the buckets always sum to `total_stories`.
_STATUS_FIELDS: Dict[str, str] = {
    "done": "done",
    "in-progress": "in_progress",
    "backlog": "backlog",
    "blocked": "blocked",
    "optional": "optional",
    "in-review": "in_review",
    "review": "review",
    "ready-for-dev": "ready_for_dev",
    "ready": "ready",
}
KNOWN_STATUSES: Tuple[str, ...] = tuple(_STATUS_FIELDS)


# --- Dataclasses ---

@dataclass
class WorkPassportItem:
    """Work Passport identity record for a story across systems."""
    passport_id: str
    story_id: str
    station: str
    epic_id: str
    title: str
    status: str  # one of KNOWN_STATUSES, or whatever literal the ledger carries
    jira_key: Optional[str] = None
    github_item_id: Optional[str] = None
    effort: Optional[str] = None
    deps: List[str] = field(default_factory=list)  # canonical `<epic>.<num>` keys
    fr_ad: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    #: Story 65.2 (CAP-150): `done` / `running` / `ready` / `waits on S-x.y[, …]`
    #: / `blocked` / `?`. Set by `SprintLedgerQueryEngine.query()` for every
    #: loaded story -- `""` only ever appears on a `WorkPassportItem` built
    #: directly (e.g. a test fixture), never on one a query returned.
    next: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


StoryItem = WorkPassportItem


@dataclass
class EpicItem:
    """Epic metadata containing owned stories."""
    epic_id: str
    station: str
    title: str
    status: str  # the ledger's `epic-N:` value, or `unknown` when it has none
    stories: List[WorkPassportItem] = field(default_factory=list)


@dataclass
class StationProgress:
    """Completion metrics for a station; the buckets always sum to `total_stories`."""
    station: str
    total_stories: int = 0
    done: int = 0
    in_progress: int = 0
    backlog: int = 0
    blocked: int = 0
    optional: int = 0
    in_review: int = 0
    review: int = 0
    ready_for_dev: int = 0
    ready: int = 0
    other: int = 0
    completion_pct: float = 0.0
    #: Story 65.2 (CAP-150): counts by the COMPUTED `next` field, distinct from
    #: the `ready` bucket above (which counts the literal ledger status
    #: `ready`). `next_ready` is `get_runnable_backlog()`'s predicate;
    #: `next_running` is a live dispatch/loop run confirmed via marshal.
    next_ready: int = 0
    next_running: int = 0


@dataclass
class EstateSummary:
    """Aggregate completion metrics across the estate."""
    stations: Dict[str, StationProgress] = field(default_factory=dict)
    total_stories: int = 0
    total_done: int = 0
    total_in_progress: int = 0
    total_backlog: int = 0
    total_blocked: int = 0
    total_optional: int = 0
    total_in_review: int = 0
    total_review: int = 0
    total_ready_for_dev: int = 0
    total_ready: int = 0
    total_other: int = 0
    overall_completion_pct: float = 0.0
    #: Story 65.2 (CAP-150): estate-wide sums of `StationProgress.next_ready` /
    #: `next_running`.
    total_next_ready: int = 0
    total_next_running: int = 0


@dataclass
class QueryResult:
    """Container for query results and metadata."""
    summary: EstateSummary
    epics: List[EpicItem]
    stories: List[WorkPassportItem]
    query_flags: Dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    warnings: List[str] = field(default_factory=list)


@dataclass
class StationLedger:
    """What a `LedgerSourcePlugin` returns for one station."""
    station: str
    status_map: Dict[str, str] = field(default_factory=dict)
    epics: List[EpicItem] = field(default_factory=list)
    stories: List[WorkPassportItem] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    loaded: bool = True  # False -> the station is skipped (its warnings say why)


# --- Interfaces & Plugin Registries ---

class QueryFormatterPlugin(ABC):
    """Abstract interface for formatters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Formatter identifier (e.g. 'markdown', 'json')."""

    @abstractmethod
    def format(self, result: QueryResult, **kwargs: Any) -> str:
        """Format QueryResult into string output."""


class LedgerSourcePlugin(ABC):
    """Abstract interface for ledger data loaders."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Source identifier (e.g. 'tracked-ledger')."""

    @abstractmethod
    def load_station(self, station: str, project_dir: Path) -> StationLedger:
        """Load status ledger, epics and stories for one station (never raises)."""


class LedgerQueryHook(ABC):
    """Hook interface for query lifecycle interception."""

    def pre_query(self, filters: Dict[str, Any]) -> None:
        """May mutate `filters`; the query uses the dict every hook saw."""

    def post_query(self, result: QueryResult) -> None:
        pass

    def on_export(self, format_name: str, output: str) -> None:
        pass


class FormatterRegistry:
    """Registry for query formatters."""

    def __init__(self) -> None:
        self._formatters: Dict[str, QueryFormatterPlugin] = {}

    def register(self, formatter: QueryFormatterPlugin) -> None:
        if formatter.name in self._formatters:
            raise ValueError(f"formatter {formatter.name!r} is already registered")
        self._formatters[formatter.name] = formatter

    def get(self, name: str) -> QueryFormatterPlugin:
        if name not in self._formatters:
            raise KeyError(f"Unknown formatter: '{name}'. Available: {self.list_formatters()}")
        return self._formatters[name]

    def list_formatters(self) -> List[str]:
        return sorted(self._formatters)


class SourceRegistry:
    """Registry for ledger sources; the engine loads every station through each."""

    def __init__(self) -> None:
        self._sources: Dict[str, LedgerSourcePlugin] = {}

    def register(self, source: LedgerSourcePlugin) -> None:
        if source.name in self._sources:
            raise ValueError(f"source {source.name!r} is already registered")
        self._sources[source.name] = source

    def list_sources(self) -> List[str]:
        return sorted(self._sources)

    def __iter__(self):
        return iter(self._sources.values())


class HookRegistry:
    """Registry for execution hooks.

    Each trigger runs EVERY hook: one that raises is reported on stderr and
    returned as a warning line, and the remaining hooks still run.
    """

    def __init__(self) -> None:
        self._hooks: List[LedgerQueryHook] = []

    def register(self, hook: LedgerQueryHook) -> None:
        self._hooks.append(hook)

    def _run(self, stage: str, call: Callable[[LedgerQueryHook], None]) -> List[str]:
        warnings: List[str] = []
        for hook in self._hooks:
            try:
                call(hook)
            except Exception as exc:  # noqa: BLE001 -- a hook must never abort the query
                message = f"hook {type(hook).__name__}.{stage} raised {type(exc).__name__}: {exc}"
                _warn(message)
                warnings.append(message)
        return warnings

    def trigger_pre_query(self, filters: Dict[str, Any]) -> List[str]:
        return self._run("pre_query", lambda hook: hook.pre_query(filters))

    def trigger_post_query(self, result: QueryResult) -> List[str]:
        return self._run("post_query", lambda hook: hook.post_query(result))

    def trigger_on_export(self, format_name: str, output: str) -> List[str]:
        return self._run("on_export", lambda hook: hook.on_export(format_name, output))


# --- Built-in Formatter Implementations ---

def _uncolumned(total: int, *shown: int) -> int:
    """Stories in buckets a human-facing table has no column for."""
    return total - sum(shown)


class MarkdownFormatter(QueryFormatterPlugin):
    @property
    def name(self) -> str:
        return "markdown"

    def format(self, result: QueryResult, **kwargs: Any) -> str:
        lines: List[str] = []
        lines.append("# Estate Sprint Ledger Query Report")
        lines.append(f"*Generated at: {result.generated_at}*\n")
        lines.append("## Estate Completion Summary\n")
        # "Other" here is every bucket the table has no column for (review-family
        # statuses included), so each row still sums to its Total.
        summary = result.summary
        lines.append(
            f"- **Total Stories:** {summary.total_stories} | "
            f"**Done:** {summary.total_done} | "
            f"**In Progress:** {summary.total_in_progress} | "
            f"**Backlog:** {summary.total_backlog} | "
            f"**Blocked:** {summary.total_blocked} | "
            f"**Optional:** {summary.total_optional} | "
            f"**Other:** {_uncolumned(summary.total_stories, summary.total_done, summary.total_in_progress, summary.total_backlog, summary.total_blocked, summary.total_optional)}"
        )
        lines.append(f"- **Overall Completion:** {summary.overall_completion_pct:.1f}%\n")

        lines.append("| Station | Total | Done | In Progress | Backlog | Blocked | Optional | Other | % Complete |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for st_name, st in sorted(summary.stations.items()):
            other = _uncolumned(st.total_stories, st.done, st.in_progress, st.backlog, st.blocked, st.optional)
            lines.append(
                f"| `{st_name}` | {st.total_stories} | {st.done} | {st.in_progress} | "
                f"{st.backlog} | {st.blocked} | {st.optional} | {other} | {st.completion_pct:.1f}% |"
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
                lines.append(f"  - Next: {s.next}")
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
        lines = [
            f"Estate Sprint Ledger Summary: {s.total_stories} stories across {len(s.stations)} stations. "
            f"Done: {s.total_done} ({s.overall_completion_pct:.1f}%), "
            f"In Progress: {s.total_in_progress}, Backlog: {s.total_backlog}, Blocked: {s.total_blocked}, "
            f"Optional: {s.total_optional}, "
            f"Other: {_uncolumned(s.total_stories, s.total_done, s.total_in_progress, s.total_backlog, s.total_blocked, s.total_optional)}. "
            f"Matching Query Stories: {len(result.stories)}"
        ]
        for st_name, st in sorted(s.stations.items()):
            lines.append(
                f"  {st_name}: {st.total_stories} stories, done {st.done}, backlog {st.backlog}, "
                f"blocked {st.blocked}, in-progress {st.in_progress}, optional {st.optional}, "
                f"ready {st.next_ready}, running {st.next_running}"
            )
        return "\n".join(lines)


class JSONFormatter(QueryFormatterPlugin):
    @property
    def name(self) -> str:
        return "json"

    def format(self, result: QueryResult, **kwargs: Any) -> str:
        payload = {
            "$schema": SCHEMA_URN,
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
            "warnings": list(result.warnings),
        }
        return json.dumps(payload, indent=2)


class TableFormatter(QueryFormatterPlugin):
    @property
    def name(self) -> str:
        return "table"

    def format(self, result: QueryResult, **kwargs: Any) -> str:
        if not result.stories:
            return "No stories matched."

        headers = ["Station", "Story ID", "Status", "Next", "Jira Key", "GitHub Item", "Title"]
        rows = []
        for s in result.stories:
            rows.append([
                s.station,
                s.story_id,
                s.status.upper(),
                s.next,
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


_LEDGER_GLOB = "_bmad-output/projects/*/planning-artifacts/sprint-status-ledger.yaml"
_FACTS_METHOD = (
    "count story keys by status with parse_sprint_status semantics "
    "(steward sprint_ledger_query; epic-N keys excluded)"
)


class HeraldFactsFormatter(QueryFormatterPlugin):
    """Herald's facts-ledger shape (`spec-deck-family-currency/facts-ledger.md`):
    `deck` / `persona` / `derived_at` / `tree` / `facts[{id, value, source, method,
    shown_as}]`. `deck`, `persona` and `tree` come from kwargs (Herald's own
    `deck-facts` derives `tree` from HEAD; this export does not run git)."""

    @property
    def name(self) -> str:
        return "herald-facts"

    @staticmethod
    def _fact(fact_id: str, done: int, total: int, source: str) -> Dict[str, Any]:
        return {
            "id": fact_id,
            "value": f"{done}/{total}",
            "source": source,
            "method": _FACTS_METHOD,
            "shown_as": [f"{done}/{total}", f"{done} of {total}"],
        }

    @staticmethod
    def _count_fact(fact_id: str, count: int, source: str) -> Dict[str, Any]:
        return {
            "id": fact_id,
            "value": str(count),
            "source": source,
            "method": _FACTS_METHOD,
            "shown_as": [str(count)],
        }

    def format(self, result: QueryResult, **kwargs: Any) -> str:
        s = result.summary
        facts: List[Dict[str, Any]] = [
            self._fact("stories_done_total", s.total_done, s.total_stories, _LEDGER_GLOB),
            self._count_fact("stories_backlog_total", s.total_backlog, _LEDGER_GLOB),
            self._count_fact("stories_blocked_total", s.total_blocked, _LEDGER_GLOB),
            self._count_fact("stories_in_progress_total", s.total_in_progress, _LEDGER_GLOB),
        ]
        for st_name, st in sorted(s.stations.items()):
            short = st_name.replace("pyforge-", "").replace("-", "_")
            source = f"_bmad-output/projects/{st_name}/planning-artifacts/sprint-status-ledger.yaml"
            facts.append(self._fact(f"{short}_stories_done", st.done, st.total_stories, source))
            facts.append(self._count_fact(f"{short}_stories_backlog", st.backlog, source))
            facts.append(self._count_fact(f"{short}_stories_blocked", st.blocked, source))
        ledger = {
            "deck": kwargs.get("deck", "sprint-backlog"),
            "persona": kwargs.get("persona", "PyForge Estate"),
            "derived_at": result.generated_at,
            "tree": kwargs.get("tree", "unknown"),
            "facts": facts,
        }
        return yaml.safe_dump(ledger, sort_keys=False, allow_unicode=True)


class AtlasDatasetFormatter(QueryFormatterPlugin):
    """A steward-shaped records payload for Atlas's Vizro connector. Steward exports,
    Atlas renders (canopy:AD-13 / AD-23) -- so this names NO Atlas catalog dataset;
    Atlas declares its own catalog entry over the payload."""

    @property
    def name(self) -> str:
        return "atlas-dataset"

    def format(self, result: QueryResult, **kwargs: Any) -> str:
        dataset = {
            "producer": "pyforge-steward:sprint-ledger-query",
            "shape": "steward.sprint-ledger-query.records",
            "note": (
                "steward-shaped export; Atlas declares its own catalog dataset over "
                "this payload (canopy:AD-13 / AD-23) -- no Atlas dataset name is claimed here"
            ),
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
        esc = html.escape
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
              <td><code>{esc(st.station)}</code></td>
              <td><code>{esc(st.story_id)}</code></td>
              <td><span class="badge {status_cls}">{esc(st.status.upper())}</span></td>
              <td><code>{esc(st.passport_id[:8])}...</code></td>
              <td>{esc(st.jira_key or '-')}</td>
              <td>{esc(st.github_item_id or '-')}</td>
              <td><strong>{esc(st.title)}</strong></td>
            </tr>
            """)

        html_out = f"""<!DOCTYPE html>
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
    <p><em>Generated at: {esc(result.generated_at)}</em></p>

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
        return html_out


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


def default_formatters() -> List[QueryFormatterPlugin]:
    """The built-in formatter set, in registration order."""
    return [
        MarkdownFormatter(),
        SummaryFormatter(),
        JSONFormatter(),
        TableFormatter(),
        SyncMatrixFormatter(),
        HeraldFactsFormatter(),
        AtlasDatasetFormatter(),
        StaticDossierFormatter(),
        JiraCSVFormatter(),
        GitHubJSONFormatter(),
    ]


def default_formatter_names() -> List[str]:
    """Sorted built-in formatter names -- the CLI's `--format` choices."""
    registry = FormatterRegistry()
    for formatter in default_formatters():
        registry.register(formatter)
    return registry.list_formatters()


# --- Tracked-ledger parsing ---

_EPIC_HEADER_RE = re.compile(r"^#{2,3}\s+Epic\s+([\d.]+)\b\s*[:—–-]?\s*(.*)$")
_STORY_HEADER_RE = re.compile(r"^###\s+Story\s+([\d.]+[a-z]?)\s*[:—–-]\s*(.+)$")
_ANY_HEADING_RE = re.compile(r"^#{1,6}\s")
_EFFORT_RE = re.compile(r"\*\*Effort:\*\*\s*([^\s•\n]+)")
_DEPS_FIELD_RE = re.compile(r"\*\*(?:Deps|Depends on):\*\*\s*([^\n•]*)")
_FR_AD_RE = re.compile(r"\*\*FR/AD:\*\*\s*([^\n•]+)")
_STATUS_FIELD_RE = re.compile(r"\*\*Status:\*\*\s*([^\n•]+)")
_JIRA_ALIAS_RE = re.compile(r"\bJIRA-([A-Z0-9]+-\d+)\b")
_GH_ALIAS_RE = re.compile(r"\bGH-(\d+)\b")
_STORY_KEY_RE = re.compile(r"^(\d+)\.(\d+)([a-z]?)$")

# Restated verbatim from `pyforge.marshal.core.spec_deps` (DEP_RE / NO_DEP_RE) so
# `get_runnable_backlog()` agrees with marshal's `ready_backlog` without steward
# importing marshal (stations never import each other) -- the same restatement
# spec_deps.py itself makes of doctor's grammar.
# ``S-28.12`` (genesis form) or bare ``28.12`` (marshal epics form).
DEP_RE = re.compile(
    r"(?:(?P<station>[a-z][a-z0-9-]*):)?(?:S-)?(?P<epic>\d+)\.(?P<num>\d+[a-z]?|\*)",
    re.I,
)
NO_DEP_RE = re.compile(r"^\s*(?:—|–|-|none|nothing|n/?a)(?![\w-])", re.I)


def canonical_story_key(story_id: str) -> str:
    """`01.02a` -> `1.2a` (marshal's `identity.normalize` rendering); other shapes verbatim."""
    m = _STORY_KEY_RE.match(story_id.strip())
    if not m:
        return story_id.strip()
    return f"{int(m.group(1))}.{int(m.group(2))}{m.group(3).lower()}"


def parse_deps_text(deps_text: str) -> List[str]:
    """Machine-readable dependency keys from one story's Deps field text.

    Marshal's grammar: `S-46.4`, bare `46.4`, `steward S-32.1 (note)` all yield
    `46.4` / `32.1` (a station word is not part of the key, exactly as marshal reads
    it -- keys resolve against the story's own station); `—`, `–`, `-`, `none`,
    `nothing`, `n/a` are the no-dependency sentinels; `28.*` wildcards are skipped.
    """
    text = str(deps_text).strip()
    if not text or NO_DEP_RE.match(text):
        return []
    keys: List[str] = []
    for match in DEP_RE.finditer(text):
        num = match.group("num")
        if num == "*":
            continue
        suffix = num[-1] if num[-1].isalpha() else ""
        seq = num[:-1] if suffix else num
        keys.append(f"{int(match.group('epic'))}.{int(seq)}{suffix.lower()}")
    return keys


def _story_status(story_id: str, status_map: Dict[str, str], block_text: str) -> str:
    """Ledger status for a story: `fleet_scan.dashboard_id_to_status`'s prefix match
    (`1.2` -> the first `1-2-*` key), else the exact hyphen key, else the block's own
    `**Status:**` line (which marks `done` only when it says done), else `backlog`."""
    hyphen = story_id.replace(".", "-")
    prefix = hyphen + "-"
    for key, value in status_map.items():
        if key.startswith(prefix):
            return value
    if hyphen in status_map:
        return status_map[hyphen]
    m_status = _STATUS_FIELD_RE.search(block_text)
    if m_status:
        raw = m_status.group(1).strip().lower()
        first = raw.split()[0].rstrip(".,;:") if raw else ""
        if first == "done":
            return "done"
        if first == "in-progress" or raw.startswith("in progress"):
            return "in-progress"
        if first == "blocked":
            return "blocked"
    return "backlog"


def parse_epics_markdown(
    content: str, station: str, status_map: Dict[str, str]
) -> Tuple[List[EpicItem], List[WorkPassportItem]]:
    """Parse one station's `epics.md` into epics and Work Passport stories.

    An epic heading is `## Epic N` or `### Epic N` (a repeated id reuses the
    existing epic rather than duplicating it); a story heading is `### Story E.N:`;
    a story block runs to the NEXT heading of any level, so trailing sections such
    as `## Deferred Work` never fold into the last story. Epic status is the
    ledger's `epic-N:` key (`unknown` when the ledger has none).
    """
    epics: List[EpicItem] = []
    stories: List[WorkPassportItem] = []
    epics_by_id: Dict[str, EpicItem] = {}
    current_epic: Optional[EpicItem] = None

    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m_epic = _EPIC_HEADER_RE.match(line)
        if m_epic:
            epic_id = m_epic.group(1).strip().rstrip(".")
            current_epic = epics_by_id.get(epic_id)
            if current_epic is None:
                current_epic = EpicItem(
                    epic_id=epic_id,
                    station=station,
                    title=m_epic.group(2).strip(),
                    status=str(status_map.get(f"epic-{epic_id}", "unknown")),
                    stories=[],
                )
                epics.append(current_epic)
                epics_by_id[epic_id] = current_epic
            i += 1
            continue

        m_story = _STORY_HEADER_RE.match(line)
        if m_story:
            story_id = m_story.group(1).strip()
            title = m_story.group(2).strip()

            block_lines: List[str] = []
            j = i + 1
            while j < len(lines) and not _ANY_HEADING_RE.match(lines[j]):
                block_lines.append(lines[j])
                j += 1
            block_text = "\n".join(block_lines)

            m_eff = _EFFORT_RE.search(block_text)
            effort = m_eff.group(1).strip() if m_eff else None

            m_deps = _DEPS_FIELD_RE.search(block_text)
            deps = parse_deps_text(m_deps.group(1)) if m_deps else []

            m_fr = _FR_AD_RE.search(block_text)
            fr_ad = m_fr.group(1).strip() if m_fr else None

            m_jira = _JIRA_ALIAS_RE.search(block_text)
            m_gh = _GH_ALIAS_RE.search(block_text)

            item = WorkPassportItem(
                # Deterministic UUID v5 for Work Passport identity (idempotent per key).
                passport_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"pyforge:{station}:{story_id}")),
                story_id=story_id,
                station=station,
                epic_id=current_epic.epic_id if current_epic else "unassigned",
                title=title,
                status=_story_status(story_id, status_map, block_text),
                jira_key=m_jira.group(1) if m_jira else None,
                github_item_id=m_gh.group(1) if m_gh else None,
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


def load_status_map(ledger_file: Path) -> Tuple[Dict[str, str], List[str]]:
    """Read a tracked `sprint-status-ledger.yaml` into `{key: status}` plus warnings.

    A missing file, unparsable YAML, or a `development_status` that is missing /
    null / not a mapping all yield an empty map; a story value that is null or not
    a string counts as `backlog` and is warned about once per ledger.
    """
    warnings: List[str] = []
    if not ledger_file.is_file():
        return {}, warnings
    try:
        data = yaml.safe_load(ledger_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        warnings.append(f"{ledger_file}: unreadable ledger ({type(exc).__name__}: {exc}); treating as empty")
        return {}, warnings
    block = data.get("development_status") if isinstance(data, dict) else None
    if not isinstance(block, dict):
        return {}, warnings
    status_map: Dict[str, str] = {}
    coerced: List[str] = []
    for key, value in block.items():
        key_str = str(key)
        if isinstance(value, str) and value.strip():
            status_map[key_str] = value.strip()
        else:
            status_map[key_str] = "backlog"
            coerced.append(key_str)
    if coerced:
        warnings.append(
            f"{ledger_file}: {len(coerced)} development_status value(s) null/non-string, "
            f"counted as backlog: {', '.join(coerced[:5])}{'…' if len(coerced) > 5 else ''}"
        )
    return status_map, warnings


class TrackedLedgerSource(LedgerSourcePlugin):
    """The default source: a station's tracked twin under `planning-artifacts/`."""

    @property
    def name(self) -> str:
        return "tracked-ledger"

    def load_station(self, station: str, project_dir: Path) -> StationLedger:
        st_dir = project_dir / "planning-artifacts"
        ledger = StationLedger(station=station)
        ledger.status_map, ledger.warnings = load_status_map(st_dir / "sprint-status-ledger.yaml")
        epics_file = st_dir / "epics.md"
        if not epics_file.is_file():
            return ledger
        try:
            content = epics_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            ledger.warnings.append(
                f"{epics_file}: unreadable ({type(exc).__name__}: {exc}); station {station} skipped"
            )
            ledger.loaded = False
            return ledger
        ledger.epics, ledger.stories = parse_epics_markdown(content, station, ledger.status_map)
        return ledger


# --- Running fact (Story 65.2, CAP-150) ---

# Restated, closed vocabulary read off marshal's OWN `watch --fleet --format
# json` output (never its journal, never `pyforge.marshal` internals): a
# project row counts as having a live run "on it" when its `pattern` is set
# and its `status` is not one of these idle/terminal words.
_RUN_INACTIVE_STATUSES = frozenset({"idle", "finished", "complete", "completed", "stopped"})
_MARSHAL_WATCH_ARGV: Tuple[str, ...] = ("marshal", "watch", "--fleet", "--format", "json")
_MARSHAL_WATCH_TIMEOUT_S = 120.0


@dataclass(frozen=True)
class RunningFact:
    """The outcome of one `marshal watch --fleet --format json` call.

    `ok=False` means unreachable/non-zero-exit/non-JSON -- CAP-150's fail-open
    posture: every `next` that would read `running` reads `?` instead, and
    `stations` stays empty. `stations` is this checkout's own -- marshal's
    Tier-3 run state is per clone.
    """

    ok: bool
    stations: frozenset = frozenset()
    warning: Optional[str] = None


def _fleet_running_stations(payload: Any) -> frozenset:
    """Every station slug the payload's `data.projects` reports as having a
    live run on it -- `pattern` set and `status` not idle/terminal."""
    projects = None
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, dict):
            projects = data.get("projects")
    running: set = set()
    if isinstance(projects, list):
        for row in projects:
            if not isinstance(row, dict):
                continue
            slug = row.get("slug")
            pattern = row.get("pattern")
            status = str(row.get("status") or "").strip().lower()
            if isinstance(slug, str) and slug and pattern and status not in _RUN_INACTIVE_STATUSES:
                running.add(slug)
    return frozenset(running)


def fetch_running_stations(process: ProcessPort, root: Path) -> RunningFact:
    """ONE `marshal watch --fleet --format json` call through
    `pyforge.core.process` -- steward never imports `pyforge.marshal` and
    never reads its journal (CAP-150's seam). Fail-open: `marshal` absent
    from PATH, a non-zero exit, or non-JSON/non-object stdout all report
    `RunningFact(ok=False, ...)` rather than raising.
    """
    try:
        result = process.run(list(_MARSHAL_WATCH_ARGV), cwd=root, timeout_s=_MARSHAL_WATCH_TIMEOUT_S)
    except ProcessError as exc:
        return RunningFact(ok=False, warning=f"marshal watch --fleet unreachable: {exc}")
    if result.returncode != 0:
        return RunningFact(
            ok=False,
            warning=f"marshal watch --fleet exited {result.returncode}: {result.stderr.strip()[:200]}",
        )
    try:
        payload = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError, ValueError):
        return RunningFact(ok=False, warning="marshal watch --fleet did not return JSON")
    if not isinstance(payload, dict):
        return RunningFact(ok=False, warning="marshal watch --fleet JSON was not an object")
    return RunningFact(ok=True, stations=_fleet_running_stations(payload))


def _done_ids(stories: List[WorkPassportItem]) -> set:
    """`(station, canonical_story_key)` for every `done` story -- the ONE done
    set both `get_runnable_backlog()` and `_compute_next()` read (never a
    second, divergent ready predicate)."""
    return {(s.station, canonical_story_key(s.story_id)) for s in stories if s.status == "done"}


def _unmet_deps(story: WorkPassportItem, done_ids: set) -> List[str]:
    """This story's own declared deps not yet `done`, within its own station."""
    return [dep for dep in story.deps if (story.station, dep) not in done_ids]


def _compute_next(
    story: WorkPassportItem,
    done_ids: set,
    running_fact: Optional[RunningFact],
) -> str:
    """`done` / `blocked` / `ready` / `waits on S-x.y[, …]` / `running` / `?`
    -- or the story's own ledger status verbatim for anything else (Story
    65.2, CAP-150). `blocked` is checked before any deps computation, so a
    blocked story is never reported `ready`.
    """
    if story.status == "done":
        return "done"
    if story.status == "blocked":
        return "blocked"
    if story.status == "backlog":
        unmet = _unmet_deps(story, done_ids)
        return "ready" if not unmet else "waits on " + ", ".join(unmet)
    if story.status == "in-progress":
        if running_fact is None:
            # No running-fact call was made for this query (library default) --
            # trust the ledger's own claim rather than fabricate unavailability.
            return "running"
        if not running_fact.ok:
            return "?"
        return "running" if story.station in running_fact.stations else story.status
    return story.status


# --- Core Query Engine ---

class SprintLedgerQueryEngine:
    """Engine for loading, filtering, querying, and exporting sprint ledgers."""

    def __init__(
        self,
        root_dir: Optional[Path] = None,
        flags_file_path: Optional[Path] = None,
        process: Optional[ProcessPort] = None,
    ) -> None:
        self.root_dir = Path(root_dir) if root_dir is not None else repo_root()
        self.flags_file_path = flags_file_path
        self.process: ProcessPort = process if process is not None else PosixProcess()
        self.formatters = FormatterRegistry()
        self.sources = SourceRegistry()
        self.hooks = HookRegistry()

        for formatter in default_formatters():
            self.formatters.register(formatter)
        self.sources.register(TrackedLedgerSource())

    @property
    def projects_dir(self) -> Path:
        return self.root_dir / _PROJECTS_RELATIVE_PATH

    def known_stations(self) -> List[str]:
        """Every station directory under `_bmad-output/projects/`, sorted."""
        if not self.projects_dir.is_dir():
            return []
        return sorted(d.name for d in self.projects_dir.iterdir() if d.is_dir())

    def flag(self, flag_name: str, default_value: Any = False, flag_overrides: Optional[Dict[str, Any]] = None) -> Any:
        """`eval_flag` bound to this engine's flags file."""
        return eval_flag(flag_name, default_value, flag_overrides, self.flags_file_path)

    def query(
        self,
        station: Optional[str] = None,
        statuses: Optional[List[str]] = None,
        unimplemented_only: bool = False,
        unlinked_only: bool = False,
        epic_id: Optional[str] = None,
        search_term: Optional[str] = None,
        flag_overrides: Optional[Dict[str, Any]] = None,
        ready_only: bool = False,
        running_only: bool = False,
        resolve_running: bool = False,
    ) -> QueryResult:
        """Execute a query against estate sprint ledgers.

        `resolve_running` (Story 65.2, CAP-150): when true, makes ONE
        `marshal watch --fleet --format json` call (via `self.process`) to
        corroborate every `in-progress` story's `next` as `running`, or `?`
        when marshal is unreachable (fail-open, one warning). Defaults to
        false so the library/API default stays a pure, offline read; the
        `ledger-query` CLI duty always passes `True`.
        """
        filters: Dict[str, Any] = {
            "station": station,
            "statuses": statuses,
            "unimplemented_only": unimplemented_only,
            "unlinked_only": unlinked_only,
            "epic_id": epic_id,
            "search_term": search_term,
            "flag_overrides": dict(flag_overrides or {}),
            "ready_only": ready_only,
            "running_only": running_only,
        }
        warnings = self.hooks.trigger_pre_query(filters)
        # The query uses the dict every pre_query hook saw -- a hook may mutate it.
        station = filters.get("station")
        statuses = filters.get("statuses")
        unimplemented_only = bool(filters.get("unimplemented_only"))
        unlinked_only = bool(filters.get("unlinked_only"))
        epic_id = filters.get("epic_id")
        search_term = filters.get("search_term")
        ready_only = bool(filters.get("ready_only"))
        running_only = bool(filters.get("running_only"))

        stations_to_scan = [station] if station else self.known_stations()

        all_stories: List[WorkPassportItem] = []
        all_epics: List[EpicItem] = []
        station_summaries: Dict[str, StationProgress] = {}

        for st in sorted(stations_to_scan):
            st_stories: List[WorkPassportItem] = []
            loaded = False
            for source in self.sources:
                ledger = source.load_station(st, self.projects_dir / st)
                for message in ledger.warnings:
                    _warn(message)
                    warnings.append(message)
                if not ledger.loaded:
                    continue
                loaded = True
                st_stories.extend(ledger.stories)
                all_epics.extend(ledger.epics)
            if not loaded:
                continue

            progress = StationProgress(station=st, total_stories=len(st_stories))
            for s in st_stories:
                bucket = _STATUS_FIELDS.get(s.status, "other")
                setattr(progress, bucket, getattr(progress, bucket) + 1)
            progress.completion_pct = (
                progress.done / progress.total_stories * 100.0 if progress.total_stories else 0.0
            )
            station_summaries[st] = progress
            all_stories.extend(st_stories)

        estate_summary = EstateSummary(stations=station_summaries)
        for progress in station_summaries.values():
            estate_summary.total_stories += progress.total_stories
            for bucket in (*_STATUS_FIELDS.values(), "other"):
                total_field = f"total_{bucket}"
                setattr(estate_summary, total_field, getattr(estate_summary, total_field) + getattr(progress, bucket))
        estate_summary.overall_completion_pct = (
            estate_summary.total_done / estate_summary.total_stories * 100.0
            if estate_summary.total_stories else 0.0
        )

        # `next` (Story 65.2, CAP-150): computed over the FULL scanned set,
        # before any filter below, so `--ready`/`--running` filter on the
        # resolved value and `done_ids` sees every done story in scope.
        done_ids = _done_ids(all_stories)
        running_fact = fetch_running_stations(self.process, self.root_dir) if resolve_running else None
        if running_fact is not None and not running_fact.ok:
            message = running_fact.warning or "marshal watch --fleet unavailable"
            _warn(message)
            warnings.append(message)
        for s in all_stories:
            s.next = _compute_next(s, done_ids, running_fact)
            progress = station_summaries.get(s.station)
            if progress is not None:
                if s.next == "ready":
                    progress.next_ready += 1
                elif s.next == "running":
                    progress.next_running += 1
        estate_summary.total_next_ready = sum(p.next_ready for p in station_summaries.values())
        estate_summary.total_next_running = sum(p.next_running for p in station_summaries.values())

        # Apply Filters
        filtered_stories = all_stories

        if ready_only:
            filtered_stories = [s for s in filtered_stories if s.next == "ready"]

        if running_only:
            filtered_stories = [s for s in filtered_stories if s.next == "running"]

        if unimplemented_only:
            filtered_stories = [s for s in filtered_stories if s.status != "done"]

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
            warnings=warnings,
        )
        result.warnings.extend(self.hooks.trigger_post_query(result))
        return result

    def export(self, result: QueryResult, format_name: str = "markdown", **kwargs: Any) -> str:
        """Export QueryResult using named formatter."""
        formatter = self.formatters.get(format_name)
        output = formatter.format(result, **kwargs)
        result.warnings.extend(self.hooks.trigger_on_export(format_name, output))
        return output


# --- Helpers & Postgres Sync ---

_DASHBOARD_EXTRA_MISSING = "pyforge-steward[dashboard] extra not installed"


def sync_to_postgres(result: QueryResult) -> Dict[str, Any]:
    """Sync Work Passport records through the `[dashboard]` extra's `passport_sync`.

    A thin call: the extra owns the ORM path and every fallback. Refuses (never
    falls back) when `pyforge.steward.dashboard.passport_sync` is not importable.
    The dynamic import is deliberate -- it is the one sanctioned lazy reach from the
    base package into the optional extra (`tests/meta/test_invariants.py`).
    """
    import importlib

    try:
        sync_module = importlib.import_module("pyforge.steward.dashboard.passport_sync")
    except ImportError:
        return {"status": "refused", "count": len(result.stories), "message": _DASHBOARD_EXTRA_MISSING}
    return sync_module.sync_work_passports_db(result.stories)


def get_runnable_backlog(engine: SprintLedgerQueryEngine, station: Optional[str] = None) -> List[WorkPassportItem]:
    """Select `backlog` stories whose declared dependencies are all `done`.

    Mirrors marshal's `ready_backlog`: dependencies resolve within the story's
    own station, and `done` is keyed by `(station, story_id)` so equal ids across
    stations never collide.
    """
    res = engine.query(station=station)
    done_ids = {(s.station, canonical_story_key(s.story_id)) for s in res.stories if s.status == "done"}
    return [
        s for s in res.stories
        if s.status == "backlog" and all((s.station, dep) in done_ids for dep in s.deps)
    ]


class LedgerQueryDuty:
    """Duty implementation for 'pyforge steward ledger-query' (Story 65.1).

    stdout carries the payload only (`DutyResult.summary`, printed by `cli.main`);
    the `--sync-postgres` outcome and the `--output` confirmation go to stderr and
    `DutyResult.details`.
    """

    name = "ledger-query"

    def run(self, ns: Any) -> Any:
        from pyforge.steward.interfaces import DutyResult

        try:
            flag_overrides = parse_flag_overrides(getattr(ns, "flag", None))
        except ValueError as exc:
            return DutyResult(ok=False, summary=str(exc))

        engine = SprintLedgerQueryEngine()

        unimplemented = getattr(ns, "unimplemented", False)
        unlinked = getattr(ns, "unlinked", False)
        station = getattr(ns, "station", None)
        status_raw = getattr(ns, "status", None)
        epic_id = getattr(ns, "epic", None)
        search = getattr(ns, "search", None)
        format_name = getattr(ns, "format", None) or "markdown"
        output_file = getattr(ns, "output", None)
        sync_pg = getattr(ns, "sync_postgres", False)

        known_stations = engine.known_stations()
        if station and station not in known_stations:
            return DutyResult(
                ok=False,
                summary=f"unknown station {station!r}; known: {', '.join(known_stations) or '(none)'}",
            )

        statuses = [s.strip().lower() for s in status_raw.split(",") if s.strip()] if status_raw else None
        unknown_statuses = [s for s in statuses or [] if s not in KNOWN_STATUSES]
        if unknown_statuses:
            return DutyResult(
                ok=False,
                summary=f"unknown status {', '.join(unknown_statuses)}; known: {', '.join(KNOWN_STATUSES)}",
            )

        if format_name not in engine.formatters.list_formatters():
            return DutyResult(
                ok=False,
                summary=f"unknown format {format_name!r}; known: {', '.join(engine.formatters.list_formatters())}",
            )

        gate = FORMATTER_FLAGS.get(format_name)
        if gate and not engine.flag(gate, False, flag_overrides):
            return DutyResult(ok=False, summary=flag_off_message(gate))
        if sync_pg and not engine.flag(FLAG_POSTGRES_SYNC, False, flag_overrides):
            return DutyResult(ok=False, summary=flag_off_message(FLAG_POSTGRES_SYNC))

        result = engine.query(
            station=station,
            statuses=statuses,
            unimplemented_only=unimplemented,
            unlinked_only=unlinked,
            epic_id=str(epic_id).strip() if epic_id else None,
            search_term=search,
            flag_overrides=flag_overrides,
        )
        output_str = engine.export(result, format_name=format_name)
        details: Dict[str, Any] = {
            "format": format_name,
            "matching_stories": len(result.stories),
            "warnings": list(result.warnings),
        }

        ok = True
        summary = output_str
        if sync_pg:
            sync_res = sync_to_postgres(result)
            details["sync"] = sync_res
            status = sync_res.get("status", "unknown")
            count = sync_res.get("synced_count", sync_res.get("count", 0))
            message = sync_res.get("message", "")
            print(
                f"[PostgreSQL Work Passport Sync] {status} ({count} records){' -- ' + message if message else ''}",
                file=sys.stderr,
            )
            if status != "success":
                ok = False
                summary = f"PostgreSQL Work Passport sync {status}: {message or 'no records synced'}"

        if output_file:
            path = Path(output_file)
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(output_str, encoding="utf-8")
            except OSError as exc:
                return DutyResult(ok=False, summary=f"could not write {path}: {exc}", details=details)
            details["output"] = str(path)
            print(f"wrote {format_name} payload to {path}", file=sys.stderr)
            if ok:
                summary = ""

        return DutyResult(ok=ok, summary=summary, details=details)
