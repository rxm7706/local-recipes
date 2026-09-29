"""The ``planning-graph`` layer's pure half (Story 28.9,
SPEC-marshal-token-economy CAP-6/CAP-13).

Story 28.8 replaced the epic-context distill's freshness hunch with a
declared, scribe-backed incremental check. This layer replaces the
WHOLESALE planning-document load (``epics.md`` ~65k tokens, ``prd.md`` ~
46k tokens) with a bounded graph query when Scribe's CAP-18 seam is
available -- and falls back to Story 28.8's epic-context file path when
the layer is off, the grammar degrades, or ``scribe recall`` finds no
grounded, non-stale answer (CAP-13: stale nodes are excluded by scribe
itself, so an ungrounded result is the consumer-side stale signal).

Pure -- no filesystem, no subprocess (AD-4). ``cli/context.py`` owns the
boundary I/O; ``adapters/scribe_cli.py`` owns the subprocess.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from fnmatch import fnmatchcase

__all__ = (
    "MODE_EPIC_CONTEXT_FALLBACK",
    "MODE_GRAPH",
    "NO_GROUNDED_ANSWER",
    "PLANNING_GRAPH_LAYER",
    "SCRIBE_RECALL_ARGV",
    "WHOLESALE_PLANNING_DOC_PATTERNS",
    "ParsedRecallAnswer",
    "build_routing_query",
    "estimate_tokens_saved",
    "is_wholesale_planning_doc",
    "layer_aggressiveness",
    "layer_enabled",
    "parse_recall_output",
    "render_scribe_recall_argv",
    "resolve_retrieval_mode",
)

#: The ``CONTEXT_LAYER_NAMES`` member this story makes load-bearing.
PLANNING_GRAPH_LAYER = "planning-graph"

#: Retrieval succeeded through the graph seam.
MODE_GRAPH = "graph"

#: Story 28.8's epic-context file path -- the proven degradation target.
MODE_EPIC_CONTEXT_FALLBACK = "epic-context-fallback"

#: Scribe's explicit miss string (``cli.py::recall_cmd``).
NO_GROUNDED_ANSWER = "no grounded answer found"

#: The scribe CLI grammar marshal binds to for scoped retrieval.
SCRIBE_RECALL_ARGV: tuple[str, ...] = ("recall",)

#: Planning documents step-01 must never load wholesale when graph mode
#: succeeds. Matched case-insensitively against a basename -- the same
#: vocabulary as ``derived_context.EPIC_CONTEXT_SOURCE_PATTERNS``'s
#: heaviest offenders, narrowed to the two named in CAP-6.
WHOLESALE_PLANNING_DOC_PATTERNS: tuple[str, ...] = ("*epic*", "*prd*")

#: Rough token budget for a successful graph answer vs loading both
#: wholesale docs (~111k tokens combined in the integration matrix).
_WHOLESALE_TOKEN_ESTIMATE = 111_000
_GRAPH_ANSWER_TOKEN_ESTIMATE = 1_500

_SOURCE_LINE = re.compile(r"^\[source:\s*(?P<citation>.+)\]\s*$")


@dataclass(frozen=True)
class ParsedRecallAnswer:
    """One ``scribe recall`` parse. ``grounded=False`` is the explicit miss
    -- never fabricated prose (AD-8), including when the only candidates
    were stale (CAP-13)."""

    grounded: bool
    text: str
    citation: str | None = None


def build_routing_query(*, project_slug: str, epic: str, story: str | None = None) -> str:
    """Natural-language query for scoped epic planning context.

    Deliberately names the project and epic (and story when known) so a
    lexical recall over the compiled graph can bind to the right slice
    without marshal importing graph internals."""
    base = f"Epic {epic} planning context requirements constraints for {project_slug}"
    if story:
        return f"Story {story} {base}"
    return base


def render_scribe_recall_argv(binary_path: str, query: str, *, scope: str | None = None) -> tuple[str, ...]:
    """The one place the recall grammar's argv is spelled.

    ``scope`` (Story 28.27, live incident 2026-09-10): binds ``--scope
    <project_slug>`` so scribe's own lexical/semantic candidate filtering
    excludes other projects' citations before scoring -- without it, a
    generic-vocabulary query naming a project slug can still be outscored
    by another project's more lexically-dense document (``pyforge`` alone
    matches every project; the slug's own discriminating suffix is one
    token among several). Always passed when the caller has a resolved
    project slug -- ``run_context_retrieve`` never calls this unscoped.
    Story 12.1: never pass ``--kind``; inherit scribe's default bag.
    Story 18.1: always name ``--mode planning`` so retrieve does not
    compete with memory and commits."""
    argv = (binary_path, *SCRIBE_RECALL_ARGV, query, "--mode", "planning")
    if scope:
        argv = (*argv, "--scope", scope)
    return argv


def parse_recall_output(text: str) -> ParsedRecallAnswer:
    """Scribe's ``recall`` stdout: answer body plus optional ``[source: …]``
    line, or the explicit miss string -- ``None``-safe on empty input."""
    stripped = text.strip()
    if not stripped:
        return ParsedRecallAnswer(grounded=False, text=NO_GROUNDED_ANSWER, citation=None)
    lines = [line.rstrip() for line in stripped.splitlines()]
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ParsedRecallAnswer(grounded=False, text=NO_GROUNDED_ANSWER, citation=None)
    if len(lines) == 1 and lines[0].strip() == NO_GROUNDED_ANSWER:
        return ParsedRecallAnswer(grounded=False, text=NO_GROUNDED_ANSWER, citation=None)
    citation: str | None = None
    body_lines = lines
    source_match = _SOURCE_LINE.match(lines[-1].strip())
    if source_match is not None:
        citation = source_match.group("citation").strip()
        body_lines = lines[:-1]
    body = "\n".join(body_lines).strip()
    if not body:
        return ParsedRecallAnswer(grounded=False, text=NO_GROUNDED_ANSWER, citation=citation)
    return ParsedRecallAnswer(grounded=True, text=body, citation=citation)


def is_wholesale_planning_doc(path: str) -> bool:
    """Whether ``path`` names a wholesale planning document (basename match).

    Used by tests and telemetry to assert step-01 never touched these when
    graph mode succeeded."""
    basename = path.rsplit("/", 1)[-1].lower()
    return any(fnmatchcase(basename, pattern.lower()) for pattern in WHOLESALE_PLANNING_DOC_PATTERNS)


def resolve_retrieval_mode(
    *,
    layer_enabled: bool,
    recall_ok: bool,
    grounded: bool,
) -> str:
    """Which context path step-01 should take.

    Graph mode requires all three: layer on, grammar answered, grounded hit.
    Every other shape degrades to Story 28.8's epic-context file."""
    if layer_enabled and recall_ok and grounded:
        return MODE_GRAPH
    return MODE_EPIC_CONTEXT_FALLBACK


def estimate_tokens_saved(*, mode: str) -> int | None:
    """Conservative savings estimate when graph mode succeeded.

    Returns ``None`` for fallback mode -- no savings to meter."""
    if mode != MODE_GRAPH:
        return None
    return max(0, _WHOLESALE_TOKEN_ESTIMATE - _GRAPH_ANSWER_TOKEN_ESTIMATE)


def layer_enabled(layer: Mapping[str, object] | None) -> bool:
    """Whether the declared ``planning-graph`` layer is on."""
    return bool((layer or {}).get("enabled", False))


def layer_aggressiveness(layer: Mapping[str, object] | None) -> str | None:
    """The declared aggressiveness rung, or ``None`` when omitted."""
    value = (layer or {}).get("aggressiveness")
    return value if isinstance(value, str) else None
