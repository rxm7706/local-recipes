"""pyforge.scribe.recall — the grounded, cited query path (Story 2.4, AD-8).

`answer()` is the "read" layer of the architecture's paradigm: it queries
the compiled `GraphStore` projection only, never the raw capture log or any
Story-2.2 source surface directly (Design Paradigm: "recall.py ... queries
the compiled projection only"). Matching is pure deterministic lexical
token-overlap scoring -- no LLM, no network call, matching AD-6's
"no-LLM-required" v1 default (PRD Open Question 3). Every returned answer's
citation is verified resolvable (a real file under `repo_root`, or a
well-formed `commit:<sha>`) before being returned -- an unresolvable
citation is treated as no match and never surfaces (AD-8: "No code path in
recall.py may return synthesized prose without a resolvable citation
attached"). A query with zero coverage, or whose only candidates all fail
citation resolution, returns an explicit "no grounded answer found" result
rather than a fabricated or generic answer.

Determinism (FR-13): scoring and tie-breaking are pure functions of the
compiled graph file's content plus the query string -- no randomness, no
per-session cache, no mutable global state. Two operators (or two
independent `FlatFileGraphStore` instances loading the same file) always get
the identical answer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pyforge.scribe.graph_store import GraphStore
from pyforge.scribe.models import GraphNode

_STOPWORDS = frozenset(
    {
        "a", "an", "the", "did", "do", "does", "we", "i", "is", "are", "was",
        "were", "to", "of", "in", "on", "for", "and", "or", "why", "what",
        "when", "how", "this", "that", "it", "be", "have", "has", "had",
        "with", "at", "by", "from", "our",
    }
)
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_COMMIT_SHA_RE = re.compile(r"[0-9a-f]{7,40}")


@dataclass(frozen=True)
class RecallAnswer:
    """One `scribe recall` result. `grounded=False` means the explicit
    "no grounded answer found" outcome, never a fabricated response
    (AD-8)."""

    grounded: bool
    text: str
    citation: str | None
    node_id: str | None


def _tokenize(text: str) -> set[str]:
    return {token for token in _TOKEN_RE.findall(text.lower()) if token not in _STOPWORDS and len(token) > 1}


def answer(query: str, store: GraphStore, *, repo_root: Path) -> RecallAnswer:
    """Deterministic, cited retrieval over the compiled graph (AD-6/AD-8).

    Only `is_current` nodes are candidates -- a superseded fact (Story 2.3)
    stays queryable via `store.query_by_citation()`/`iter_nodes()`, but
    never surfaces here as if it were still current. Candidates are ranked
    by query/node token-overlap (desc), tie-broken by node id (asc) for
    reproducibility, then filtered by citation resolvability on the way
    out -- an unresolvable top match is skipped, never returned.
    """
    query_tokens = _tokenize(query)
    if not query_tokens:
        return _no_grounded_answer()

    scored: list[tuple[int, GraphNode]] = []
    for node in store.iter_nodes():
        if not node.is_current:
            continue
        node_tokens = _tokenize(f"{node.title} {node.text}")
        overlap = len(query_tokens & node_tokens)
        if overlap > 0:
            scored.append((overlap, node))

    scored.sort(key=lambda pair: (-pair[0], pair[1].id))

    for _score, node in scored:
        if _citation_is_resolvable(node.citation, repo_root):
            return RecallAnswer(grounded=True, text=node.text, citation=node.citation, node_id=node.id)
        # Unresolvable citation -- never surface an uncited/unverifiable answer; try the next candidate.

    return _no_grounded_answer()


def _no_grounded_answer() -> RecallAnswer:
    return RecallAnswer(grounded=False, text="no grounded answer found", citation=None, node_id=None)


def _citation_is_resolvable(citation: str, repo_root: Path) -> bool:
    if citation.startswith("commit:"):
        sha = citation.removeprefix("commit:")
        return bool(_COMMIT_SHA_RE.fullmatch(sha))
    return (repo_root / citation).is_file()
