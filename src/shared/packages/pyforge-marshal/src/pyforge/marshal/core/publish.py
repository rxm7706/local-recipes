"""Pure run-state record shaping for host publish (Story 33.4, AD-4).

No I/O, no env reads, no network imports — supervisors and tests call these
functions to build ``PublishRecord`` / completion payloads before handing
them to ``RunPublisherPort``.
"""

from __future__ import annotations

from collections.abc import Mapping

from ..ports.harness import LayerSavings, RunStatusSnapshot
from ..ports.publisher import PublishRecord

_TERMINAL_PHASES = frozenset({"done", "landed", "completed", "abandoned"})


def active_task_from_snapshot(
    snapshot: RunStatusSnapshot | None,
) -> tuple[str | None, str | None, str | None]:
    """Return ``(story_key, phase, commit_sha)`` for the active harness task."""
    if snapshot is None:
        return None, None, None
    for task in snapshot.tasks:
        if task.phase.lower() not in _TERMINAL_PHASES:
            return task.story_key, task.phase, task.commit_sha
    if snapshot.tasks:
        last = snapshot.tasks[-1]
        return last.story_key, last.phase, last.commit_sha
    return None, None, None


def layer_savings_dict(layer_savings: LayerSavings | None) -> dict[str, object]:
    """Serialize CAP-7 savings fields; absent layers are omitted."""
    if layer_savings is None:
        return {}
    payload: dict[str, object] = {}
    if layer_savings.output_compression_saved is not None:
        payload["output_compression_saved"] = layer_savings.output_compression_saved
    if layer_savings.wire_compression_saved is not None:
        payload["wire_compression_saved"] = layer_savings.wire_compression_saved
    graph_stats = layer_savings.graph_hits_vs_file_reads
    if isinstance(graph_stats, tuple):
        hits, reads = graph_stats
        payload["graph_hits"] = hits
        payload["file_reads"] = reads
    elif isinstance(graph_stats, str):
        payload["graph_hits_vs_file_reads"] = graph_stats
    if layer_savings.derived_context_cache_hits is not None:
        payload["derived_context_cache_hits"] = layer_savings.derived_context_cache_hits
    if layer_savings.planning_graph_tokens_saved is not None:
        payload["planning_graph_tokens_saved"] = layer_savings.planning_graph_tokens_saved
    return payload


def shape_loop_publish(
    *,
    station_slug: str,
    run_id: str,
    harness_run_id: str | None,
    story_key: str | None = None,
    phase: str | None = None,
    commit_sha: str | None = None,
    layer_savings: LayerSavings | None = None,
) -> PublishRecord:
    return PublishRecord(
        station=station_slug,
        run_id=run_id,
        harness_run_id=harness_run_id,
        story_key=story_key,
        phase=phase,
        commit_sha=commit_sha,
        run_kind="loop",
        layer_savings=layer_savings_dict(layer_savings),
    )


def shape_dispatch_publish(
    *,
    station_slug: str,
    run_id: str,
    story_key: str,
    commit_sha: str | None = None,
    phase: str = "dispatch",
    layer_savings: LayerSavings | None = None,
) -> PublishRecord:
    return PublishRecord(
        station=station_slug,
        run_id=run_id,
        story_key=story_key,
        phase=phase,
        commit_sha=commit_sha,
        run_kind="dispatch",
        layer_savings=layer_savings_dict(layer_savings),
    )


def shape_heartbeat(handle: str) -> dict[str, object]:
    return {"handle": handle}


def shape_complete(
    *,
    status: str,
    result: Mapping[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"status": status}
    if result:
        payload["result"] = dict(result)
    return payload


def loop_complete_result(
    *,
    detach_reason: str,
    story_key: str | None = None,
    commit_sha: str | None = None,
    layer_savings: LayerSavings | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {"detach_reason": detach_reason}
    if story_key is not None:
        result["story_key"] = story_key
    if commit_sha is not None:
        result["commit_sha"] = commit_sha
    savings = layer_savings_dict(layer_savings)
    if savings:
        result["layer_savings"] = savings
    return result


def dispatch_complete_result(
    *,
    verdict: str,
    stop_reason: str | None,
    baseline_head_sha: str | None,
    current_head_sha: str | None,
    story_key: str,
    started_at: str | None = None,
    ended_at: str | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "verdict": verdict,
        "story_key": story_key,
    }
    if stop_reason is not None:
        result["stop_reason"] = stop_reason
    if baseline_head_sha is not None:
        result["baseline_head_sha"] = baseline_head_sha
    if current_head_sha is not None:
        result["commit_sha"] = current_head_sha
    if started_at is not None:
        result["started_at"] = started_at
    if ended_at is not None:
        result["ended_at"] = ended_at
    return result
