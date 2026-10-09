"""Promote bmad-loop engine scratch refs to ``preserve/`` tags (Story 87.4, CAP-287).

Reads the loop-home ``.bmad-loop/runs/<run>/journal.jsonl`` for preserve events,
queues engine refs, and at each stage boundary tags them through
``pyforge.core.preserve_refs`` (resolve commit via ``git rev-parse``, never the
journal's printed sha). A reconcile scan catches unpromoted
``attempt-preserve/*`` and ``refs/attempt-preserve-dirty/*`` refs the events missed.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from pyforge.core.preserve_refs import (
    PreserveGitError,
    PreserveRefError,
    PreserveTrailers,
    normalize_ref,
    observe_preserve_debt,
    push_preserve_ref,
    render_preserve_ref,
    short_ref_name,
    tag_preserve,
)
from pyforge.core.process import PosixProcess, ProcessError

from ..core.identity import MalformedStoryKeyError, normalize, render_feed_key
from ..ports.harness import DeferredStory, TaskPhaseSnapshot

BMAD_LOOP_PRESERVE_EVENT_KINDS = frozenset(
    {
        "attempt-commits-preserved",
        "attempt-worktree-preserved",
        "worktree-kept",
        "story-deferred",
    }
)

_ENGINE_REF_PAYLOAD_KEYS = ("ref", "preserve_ref")


@dataclass(frozen=True, slots=True)
class EnginePreserveTarget:
    """One engine ref to promote, keyed by normalized ref for deduplication."""

    engine_ref: str
    story_key: str | None = None


@dataclass(frozen=True, slots=True)
class EnginePromoteOutcome:
    refname: str
    preserve_tag: str
    engine_ref: str
    pushed: bool
    noop: bool


def bmad_loop_journal_path(home: Path, harness_run_id: str) -> Path:
    return home / ".bmad-loop" / "runs" / harness_run_id / "journal.jsonl"


def read_new_journal_objects(journal_path: Path, *, byte_offset: int) -> tuple[tuple[dict[str, object], ...], int]:
    """Return JSON objects from ``journal_path`` after ``byte_offset``; advance offset."""
    if not journal_path.is_file():
        return (), byte_offset
    data = journal_path.read_bytes()
    if len(data) <= byte_offset:
        return (), byte_offset
    events: list[dict[str, object]] = []
    for line in data[byte_offset:].splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            events.append(parsed)
    return tuple(events), len(data)


def _payload_ref(payload: Mapping[str, object]) -> str | None:
    for key in _ENGINE_REF_PAYLOAD_KEYS:
        raw = payload.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return None


def targets_from_journal_events(events: Iterable[Mapping[str, object]]) -> tuple[EnginePreserveTarget, ...]:
    """Extract preserve targets from bmad-loop journal event dicts."""
    out: list[EnginePreserveTarget] = []
    for event in events:
        kind = event.get("kind")
        if kind not in BMAD_LOOP_PRESERVE_EVENT_KINDS:
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            payload = event
        engine_ref = _payload_ref(payload)
        if kind == "worktree-kept" and not engine_ref:
            continue
        if kind == "story-deferred" and not engine_ref:
            continue
        if not engine_ref:
            continue
        story_raw = payload.get("story_key")
        story_key = story_raw if isinstance(story_raw, str) and story_raw.strip() else None
        out.append(EnginePreserveTarget(engine_ref=engine_ref, story_key=story_key))
    return tuple(out)


def targets_from_run_snapshot(
    tasks: Iterable[TaskPhaseSnapshot],
    deferred: Iterable[DeferredStory],
) -> tuple[EnginePreserveTarget, ...]:
    """Collect ``preserve_ref`` pointers still naming engine scratch refs."""
    out: list[EnginePreserveTarget] = []
    for task in tasks:
        if task.preserve_ref and not is_preserve_tag_ref(task.preserve_ref):
            out.append(EnginePreserveTarget(engine_ref=task.preserve_ref, story_key=task.story_key))
    for story in deferred:
        if story.preserve_ref and not is_preserve_tag_ref(story.preserve_ref):
            out.append(EnginePreserveTarget(engine_ref=story.preserve_ref, story_key=story.story_key))
    return tuple(out)


def is_preserve_tag_ref(ref: str) -> bool:
    cleaned = ref.strip()
    return cleaned.startswith("preserve/") or cleaned.startswith("refs/tags/preserve/")


def _git_rev_parse(repo: Path, ref: str) -> str:
    try:
        result = PosixProcess().run(
            ["git", "-C", str(repo), "rev-parse", normalize_ref(ref)],
            cwd=repo,
            timeout_s=120.0,
        )
    except ProcessError as exc:
        raise PreserveGitError(str(exc)) from exc
    if result.returncode != 0:
        raise PreserveGitError(result.stderr.strip() or "git rev-parse failed")
    return result.stdout.strip()


def _feed_story_key(story_key: str | None) -> str | None:
    if not story_key:
        return None
    try:
        return render_feed_key(normalize(story_key))
    except MalformedStoryKeyError:
        return story_key


def promote_engine_ref(
    repo: Path,
    *,
    engine_ref: str,
    project_slug: str,
    story_key: str | None,
    run_id: str,
    journal_path: str,
    reason: str,
    push: bool = True,
) -> EnginePromoteOutcome | None:
    """Tag ``engine_ref``'s current target as ``preserve/…/bmad-loop-<sha8>``."""
    try:
        commit = _git_rev_parse(repo, engine_ref)
    except PreserveGitError:
        return None
    feed_story = _feed_story_key(story_key)
    slug = project_slug if feed_story else None
    sk = feed_story
    try:
        refname = render_preserve_ref(
            commit_sha=commit,
            producer="bmad-loop",
            project_slug=slug,
            story_key=sk,
        )
        trailers = PreserveTrailers(
            producer="bmad-loop",
            provenance="machine",
            reason=reason,
            source=normalize_ref(engine_ref),
            run=run_id,
            journal=journal_path,
            commit=commit,
        )
        tagged = tag_preserve(repo, refname=refname, commit=commit, trailers=trailers)
    except PreserveRefError, PreserveGitError:
        return None
    pushed = False
    if push:
        try:
            push_result = push_preserve_ref(repo, tagged.refname)
            pushed = push_result.pushed
        except PreserveGitError:
            pushed = False
    return EnginePromoteOutcome(
        refname=tagged.refname,
        preserve_tag=short_ref_name(tagged.refname),
        engine_ref=engine_ref,
        pushed=pushed,
        noop=tagged.noop,
    )


def reconcile_unpromoted_engine_refs(repo: Path) -> tuple[str, ...]:
    """List engine scratch refs whose commits are not yet held by a preserve tag."""
    observation = observe_preserve_debt(repo)
    if observation is None:
        return ()
    return tuple(short_ref_name(ref) for ref in observation.unpromoted_scratch)


def tag_intent_gap_attempt(
    repo: Path,
    *,
    tip_sha: str,
    project_slug: str,
    story_key: str,
    run_id: str,
    journal_path: str,
    push: bool = False,
) -> EnginePromoteOutcome | None:
    """Write ``preserve/…/intent-gap-<sha8>`` at ``tip_sha`` (no ``attempt-preserve/*`` branch)."""
    feed_story = _feed_story_key(story_key)
    if not feed_story:
        return None
    try:
        refname = render_preserve_ref(
            commit_sha=tip_sha,
            producer="intent-gap",
            project_slug=project_slug,
            story_key=feed_story,
        )
        trailers = PreserveTrailers(
            producer="intent-gap",
            provenance="machine",
            reason="intent-gap escalation preserve",
            source=tip_sha,
            run=run_id,
            journal=journal_path,
            commit=tip_sha,
        )
        tagged = tag_preserve(repo, refname=refname, commit=tip_sha, trailers=trailers)
    except PreserveRefError, PreserveGitError:
        return None
    pushed = False
    if push:
        try:
            push_result = push_preserve_ref(repo, tagged.refname)
            pushed = push_result.pushed
        except PreserveGitError:
            pushed = False
    return EnginePromoteOutcome(
        refname=tagged.refname,
        preserve_tag=short_ref_name(tagged.refname),
        engine_ref="",
        pushed=pushed,
        noop=tagged.noop,
    )
