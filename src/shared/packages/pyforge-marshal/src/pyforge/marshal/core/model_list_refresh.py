"""Operator-run harness model-list refresh (Story 84.1, CAP-285 / FR-232).

Pure parsing, comparison, snapshot diff and report rendering — no I/O (AD-4).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Literal

from .model_cost import catalog_declared

HarnessListStatus = Literal["ok", "unavailable", "unchecked"]

_CURSOR_LINE_RE = re.compile(r"^(\S+)\s+-\s+.+")


@dataclass(frozen=True)
class DeclaredModelRef:
    model_id: str
    harness: str
    source_file: str
    source_key: str


@dataclass(frozen=True)
class NotListedFinding:
    model_id: str
    harness: str
    source_file: str
    source_key: str


@dataclass(frozen=True)
class HarnessListResult:
    harness: str
    status: HarnessListStatus
    live_ids: frozenset[str]
    reason: str | None = None


@dataclass(frozen=True)
class SnapshotDiff:
    added: frozenset[str]
    removed: frozenset[str]


def parse_command_model_lines(text: str) -> frozenset[str]:
    """Each ``id - Display Name`` line yields one id (Cursor ``models`` output)."""
    ids: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = _CURSOR_LINE_RE.match(stripped)
        if match:
            model_id = match.group(1)
            if model_id.lower() == "error":
                continue
            ids.add(model_id)
    return frozenset(ids)


def parse_anthropic_models_page(payload: Mapping[str, object]) -> tuple[frozenset[str], bool, str | None]:
    """One Anthropic ``GET /v1/models`` page; returns ids, has_more, after_id."""
    data = payload.get("data")
    ids: set[str] = set()
    if isinstance(data, list):
        for item in data:
            if isinstance(item, Mapping):
                model_id = item.get("id")
                if isinstance(model_id, str) and model_id:
                    ids.add(model_id)
    has_more = payload.get("has_more") is True
    after_id: str | None = None
    if has_more:
        last_id = payload.get("last_id")
        if isinstance(last_id, str) and last_id:
            after_id = last_id
        elif ids:
            after_id = max(ids)
    return frozenset(ids), has_more, after_id


def parse_gemini_models_page(payload: Mapping[str, object]) -> tuple[frozenset[str], str | None]:
    """One Gemini ``models.list`` page; keeps models with ``generateContent`` support."""
    models = payload.get("models")
    ids: set[str] = set()
    if isinstance(models, list):
        for item in models:
            if not isinstance(item, Mapping):
                continue
            methods = item.get("supportedGenerationMethods")
            if not isinstance(methods, list) or "generateContent" not in methods:
                continue
            name = item.get("name")
            if isinstance(name, str) and name:
                # API returns "models/gemini-..." — store the short id for comparison.
                short = name.split("/")[-1] if "/" in name else name
                ids.add(short)
    next_token = payload.get("nextPageToken")
    token = next_token if isinstance(next_token, str) and next_token else None
    return frozenset(ids), token


def model_absent_from_live_list(
    model_id: str,
    live_ids: frozenset[str],
    aliases: frozenset[str],
) -> bool:
    """True when the id is not listed and not declared as an alias."""
    if model_id in live_ids:
        return False
    if model_id in aliases:
        return False
    return True


def find_not_listed(
    declared: Sequence[DeclaredModelRef],
    harness_results: Mapping[str, HarnessListResult],
    aliases_by_harness: Mapping[str, frozenset[str]],
) -> tuple[NotListedFinding, ...]:
    findings: list[NotListedFinding] = []
    for ref in declared:
        result = harness_results.get(ref.harness)
        if result is None or result.status != "ok":
            continue
        aliases = aliases_by_harness.get(ref.harness, frozenset())
        if model_absent_from_live_list(ref.model_id, result.live_ids, aliases):
            findings.append(
                NotListedFinding(
                    model_id=ref.model_id,
                    harness=ref.harness,
                    source_file=ref.source_file,
                    source_key=ref.source_key,
                )
            )
    return tuple(findings)


def diff_harness_ids(
    previous: Mapping[str, frozenset[str]],
    current: Mapping[str, frozenset[str]],
    *,
    comparable_harnesses: frozenset[str] | None = None,
) -> dict[str, SnapshotDiff]:
    """Ids added/removed per harness since ``previous``.

    Harnesses not in ``comparable_harnesses`` are omitted (unavailable lists
    are not diffed as empty).
    """
    out: dict[str, SnapshotDiff] = {}
    if comparable_harnesses is None:
        harnesses = set(previous.keys()) | set(current.keys())
    else:
        harnesses = {name for name in comparable_harnesses if name in previous or name in current}
    for harness in sorted(harnesses):
        prev = previous.get(harness, frozenset())
        curr = current.get(harness, frozenset())
        out[harness] = SnapshotDiff(added=curr - prev, removed=prev - curr)
    return out


def providers_named_by_profiles(catalog_provider_by_harness: Mapping[str, str]) -> frozenset[str]:
    return frozenset(v for v in catalog_provider_by_harness.values() if v)


def catalog_models_for_provider(catalog: object, provider: str) -> frozenset[str]:
    if not catalog_declared(catalog) or not isinstance(catalog, Mapping):
        return frozenset()
    providers = catalog.get("providers")
    if not isinstance(providers, Mapping):
        return frozenset()
    block = providers.get(provider)
    if not isinstance(block, Mapping):
        return frozenset()
    models = block.get("models")
    if not isinstance(models, Mapping):
        return frozenset()
    return frozenset(k for k in models if isinstance(k, str))


def unchecked_catalog_providers(
    catalog: object,
    named_providers: frozenset[str],
) -> frozenset[str]:
    if not catalog_declared(catalog) or not isinstance(catalog, Mapping):
        return frozenset()
    providers = catalog.get("providers")
    if not isinstance(providers, Mapping):
        return frozenset()
    return frozenset(k for k in providers if isinstance(k, str) and k not in named_providers)


def build_snapshot_payload(
    *,
    snapshot_date: str,
    harness_ids: Mapping[str, frozenset[str]],
    harness_status: Mapping[str, HarnessListStatus],
) -> dict[str, object]:
    return {
        "date": snapshot_date,
        "harnesses": {
            name: {
                "status": harness_status.get(name, "unavailable"),
                "ids": sorted(harness_ids.get(name, frozenset())),
            }
            for name in sorted(harness_ids.keys() | harness_status.keys())
        },
    }


def parse_snapshot_payload(
    raw: Mapping[str, object],
) -> tuple[str, dict[str, frozenset[str]], dict[str, HarnessListStatus]]:
    snapshot_date = raw.get("date")
    if not isinstance(snapshot_date, str):
        raise ValueError("snapshot missing date")
    harnesses = raw.get("harnesses")
    ids_by_harness: dict[str, frozenset[str]] = {}
    status_by_harness: dict[str, HarnessListStatus] = {}
    if isinstance(harnesses, Mapping):
        for name, block in harnesses.items():
            if not isinstance(name, str) or not isinstance(block, Mapping):
                continue
            status_raw = block.get("status")
            if status_raw in ("ok", "unavailable", "unchecked"):
                status_by_harness[name] = status_raw
            id_list = block.get("ids")
            if isinstance(id_list, list):
                ids_by_harness[name] = frozenset(x for x in id_list if isinstance(x, str))
    return snapshot_date, ids_by_harness, status_by_harness


def snapshot_filename_for_date(day: date) -> str:
    return "model-list-" + day.isoformat() + ".json"


def accumulate_last_ok_ids(
    snapshots: Sequence[tuple[date, Mapping[str, frozenset[str]], Mapping[str, HarnessListStatus]]],
) -> dict[str, frozenset[str]]:
    """From oldest to newest snapshot tuples, keep the latest ``ok`` ids per harness."""
    last_ok: dict[str, frozenset[str]] = {}
    for _day, ids_map, status_map in snapshots:
        for harness, status in status_map.items():
            if status == "ok" and harness in ids_map:
                last_ok[harness] = ids_map[harness]
    return last_ok


def merge_snapshot_blocks_for_write(
    *,
    harness_ids: Mapping[str, frozenset[str]],
    harness_status: Mapping[str, HarnessListStatus],
    same_day_existing: Mapping[str, object] | None,
    last_ok_ids: Mapping[str, frozenset[str]],
) -> tuple[dict[str, frozenset[str]], dict[str, HarnessListStatus]]:
    """Preserve last ``ok`` blocks when a re-run is ``unavailable`` (Story 84.1)."""
    out_ids: dict[str, frozenset[str]] = dict(harness_ids)
    out_status: dict[str, HarnessListStatus] = dict(harness_status)
    same_day_ok: dict[str, frozenset[str]] = {}
    if same_day_existing is not None:
        for name, block in same_day_existing.items():
            if not isinstance(name, str) or not isinstance(block, Mapping):
                continue
            if block.get("status") == "ok":
                id_list = block.get("ids")
                if isinstance(id_list, list):
                    same_day_ok[name] = frozenset(x for x in id_list if isinstance(x, str))
    names = set(out_ids) | set(out_status) | set(same_day_ok) | set(last_ok_ids)
    for name in names:
        if out_status.get(name) != "unavailable":
            continue
        if name in same_day_ok:
            out_ids[name] = same_day_ok[name]
            out_status[name] = "ok"
        elif name in last_ok_ids:
            out_ids[name] = last_ok_ids[name]
            out_status[name] = "ok"
    return out_ids, out_status


def _quote_query_value(value: str) -> str:
    out: list[str] = []
    for ch in value:
        code = ord(ch)
        if (48 <= code <= 57) or (65 <= code <= 90) or (97 <= code <= 122) or ch in "-_.~":
            out.append(ch)
        else:
            out.append(f"%{code:02X}")
    return "".join(out)


def append_query_params(base: str, params: Mapping[str, str]) -> str:
    """Pure URL query append without importing urllib (AD-4 / AD-65)."""
    parts = [key + "=" + _quote_query_value(value) for key, value in params.items() if value]
    if not parts:
        return base
    query = "&".join(parts)
    if "?" in base:
        return base + "&" + query
    return base + "?" + query


def anthropic_models_page_url(base: str, after_id: str | None) -> str:
    params: dict[str, str] = {"limit": "1000"}
    if after_id:
        params["after_id"] = after_id
    return append_query_params(base, params)


def gemini_models_page_url(base: str, page_token: str | None) -> str:
    params: dict[str, str] = {"pageSize": "1000"}
    if page_token:
        params["pageToken"] = page_token
    return append_query_params(base, params)


def render_report_text(
    *,
    not_listed: Sequence[NotListedFinding],
    harness_results: Mapping[str, HarnessListResult],
    unchecked_providers: frozenset[str],
    snapshot_diff: Mapping[str, SnapshotDiff] | None,
) -> str:
    lines: list[str] = ["marshal adapters models — advisory model-list report", ""]
    for harness in sorted(harness_results.keys()):
        result = harness_results[harness]
        if result.status == "unavailable":
            lines.append(f"[{harness}] unavailable: {result.reason or 'no source'}")
        elif result.status == "ok":
            lines.append(f"[{harness}] listed {len(result.live_ids)} model id(s)")
        else:
            lines.append(f"[{harness}] unchecked")
    if unchecked_providers:
        lines.append("")
        lines.append("unchecked catalog providers (no profile names them):")
        for provider in sorted(unchecked_providers):
            lines.append(f"  - {provider}")
    if not_listed:
        lines.append("")
        lines.append("declared but not listed (and not an alias):")
        for item in not_listed:
            lines.append(f"  - {item.model_id} ({item.harness}) declared in {item.source_file} key {item.source_key}")
    diff_lines: list[str] = []
    if snapshot_diff:
        for harness, diff in sorted(snapshot_diff.items()):
            if not diff.added and not diff.removed:
                continue
            diff_lines.append(f"  [{harness}]")
            for mid in sorted(diff.added):
                diff_lines.append(f"    + {mid}")
            for mid in sorted(diff.removed):
                diff_lines.append(f"    - {mid}")
    if diff_lines:
        lines.append("")
        lines.append("since previous snapshot:")
        lines.extend(diff_lines)
    compared = sum(1 for r in harness_results.values() if r.status == "ok")
    unavailable = sum(1 for r in harness_results.values() if r.status == "unavailable")
    lines.append("")
    lines.append(f"summary: {compared} harness(es) compared, {unavailable} unavailable")
    has_snapshot_changes = bool(diff_lines)
    can_claim_clean = compared > 0 and unavailable == 0
    if can_claim_clean and not not_listed and not unchecked_providers and not has_snapshot_changes:
        lines.append("no drift detected")
    return "\n".join(lines)


def collect_tier_map_refs(
    *,
    policy_path: str,
    tier_map: Mapping[str, object],
    default_harness: str | None,
) -> tuple[DeclaredModelRef, ...]:
    from .tier_routing import normalize_stage_entries

    refs: list[DeclaredModelRef] = []
    for difficulty, stages in tier_map.items():
        if not isinstance(difficulty, str) or not isinstance(stages, Mapping):
            continue
        normalized = normalize_stage_entries(stages)
        for stage, candidates in normalized.items():
            key = "model_tier_map." + difficulty + "." + stage
            for candidate in candidates:
                harness = candidate.harness if candidate.harness is not None else default_harness
                if harness is None:
                    continue
                refs.append(
                    DeclaredModelRef(
                        model_id=candidate.model,
                        harness=harness,
                        source_file=policy_path,
                        source_key=key,
                    )
                )
    return tuple(refs)


def collect_profile_map_refs(
    *,
    harness: str,
    profile_path: str,
    model_map: Mapping[str, str],
) -> tuple[DeclaredModelRef, ...]:
    return tuple(
        DeclaredModelRef(
            model_id=target,
            harness=harness,
            source_file=profile_path,
            source_key=f"model_map.{tier}",
        )
        for tier, target in model_map.items()
        if target
    )


def collect_catalog_refs(
    *,
    catalog: object,
    catalog_path: str,
    provider: str,
    harness: str,
) -> tuple[DeclaredModelRef, ...]:
    models = catalog_models_for_provider(catalog, provider)
    return tuple(
        DeclaredModelRef(
            model_id=mid,
            harness=harness,
            source_file=catalog_path,
            source_key="model_cost_catalog.providers." + provider + ".models." + mid,
        )
        for mid in sorted(models)
    )


def ensure_no_secret_in_text(text: str, secret: str) -> None:
    if secret and secret in text:
        raise ValueError("credential leaked into output")
