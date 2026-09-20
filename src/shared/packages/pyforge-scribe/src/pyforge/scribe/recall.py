"""pyforge.scribe.recall — the grounded, cited query path (Story 2.4, AD-8).

`answer()` is the "read" layer of the architecture's paradigm: it queries
the compiled `GraphStore` projection only, never the raw capture log or any
Story-2.2 source surface directly (Design Paradigm: "recall.py ... queries
the compiled projection only"). Matching is pure deterministic lexical
token-overlap scoring -- no LLM, no network call, matching AD-6's
"no-LLM-required" v1 default (PRD Open Question 3). Every returned answer's
citation is verified resolvable (a real file under `repo_root`, a
well-formed `commit:<sha>`, a well-formed `<jsonl filename>:L<line>`
transcript citation (Story 3.2), or a well-formed `<path>:L<line>` code
citation whose path resolves under `repo_root` (Story 6.1's graphify
extra)) before being returned -- an unresolvable
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

A `stale`-flagged node (Story 6.3, CAP-13) is excluded from candidacy the
same way an `is_current is False` node already is -- this is the "consumer
falls back to its non-graph path rather than serving the stale node
silently" contract: `scribe recall` never returns a stale node's content as
if it were current, falling through to the next resolvable, non-stale
candidate, or to the explicit "no grounded answer found" result.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pyforge.scribe.compile import source_committed_after
from pyforge.scribe.graph_store import GraphStore
from pyforge.scribe.models import GraphNode, GraphNodeKind

#: Default `answer()` / `scribe recall` candidate kinds (Story 8.5 / CAP-4).
#: `code` stays in the store for `index report` and `--kind code`; it is
#: not a default lexical/semantic peer of memory, Dreams, or SPECs.
DEFAULT_RECALL_KINDS: frozenset[GraphNodeKind] = frozenset({"memory", "memlog", "commit", "doc", "transcript"})
_ALL_RECALL_KINDS: frozenset[str] = frozenset({"memory", "memlog", "commit", "doc", "transcript", "code"})
#: User-facing `--mode` bags (Story 16.1 / CAP-11). Distinct from
#: `answer(..., mode=)` which is lexical vs semantic ranking.
RECALL_MODE_KINDS: dict[str, frozenset[str]] = {
    "planning": frozenset({"doc", "memlog"}),
    "memory": frozenset({"memory"}),
    "code": frozenset({"code"}),
}

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "did",
        "do",
        "does",
        "we",
        "i",
        "is",
        "are",
        "was",
        "were",
        "to",
        "of",
        "in",
        "on",
        "for",
        "and",
        "or",
        "why",
        "what",
        "when",
        "how",
        "this",
        "that",
        "it",
        "be",
        "have",
        "has",
        "had",
        "with",
        "at",
        "by",
        "from",
        "our",
    }
)
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_COMMIT_SHA_RE = re.compile(r"[0-9a-f]{7,40}")
#: A transcript citation is a BARE `<jsonl filename>:L<line>` -- Story 3.2's
#: own format contract is "no directory path". `[^/\\:]+` enforces that
#: literally: an earlier `.+` also admitted `nested/dir/x.jsonl:L1` and
#: `../../../etc/passwd.jsonl:L1`, and because this branch short-circuits
#: the `is_file()` check below, any such citation was declared resolvable
#: without existing (review finding). `[0-9]` rather than `\d` for the same
#: reason: `\d` also matches non-ASCII decimal digits, so `x.jsonl:L١٢`
#: was likewise waved through without existing (review finding: reproduced).
_TRANSCRIPT_CITATION_RE = re.compile(r"[^/\\:]+\.jsonl:L[0-9]+")
#: A `code` node's citation (Story 6.1's graphify extra) is
#: `<repo-relative path>:L<line>` -- e.g. `src/pyforge/scribe/compile.py:L120`,
#: matching graphify's own `source_location` shape. Unlike the transcript
#: format above, this IS re-resolved against a live file: repo source is not
#: per-user/local the way a session transcript is, so the same
#: existence-check `recall.py` already applies to a bare path citation
#: applies here too -- only the PATH portion is checked; the line number is
#: format-only (never re-parsed against the file's actual length).
_CODE_LINE_CITATION_RE = re.compile(r"^(?P<path>.+):L(?P<line>[0-9]+)$")


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


def _scope_prefix(scope: str) -> str:
    return f"_bmad-output/projects/{scope}/"


#: Herald fact ledger compiled by Story 8.3. Scoped retrieve admits the
#: ledger whose directory name equals `--scope` (Story 9.1 / CAP-1).
_FACTS_LEDGER_CITATION_RE = re.compile(r"^presentations/(?P<slug>[^/]+)/facts\.yaml$")


def _citation_in_scope(citation: str, scope: str | None) -> bool:
    """Whether `citation` belongs to `scope` (a project slug).

    `scope=None` admits every citation -- today's unscoped behavior,
    unchanged. A given `scope` admits citations under that project's
    own `_bmad-output/projects/<scope>/` tree, plus exactly
    `presentations/<scope>/facts.yaml` (Story 9.1). Every other citation
    shape (`commit:<sha>`, a transcript `<jsonl>:L<n>`, a bare code path,
    another deck's ledger, or the presentations export tree) has no
    reliable per-project attribution, so it is excluded rather than
    guessed at."""
    if scope is None:
        return True
    if citation.startswith(_scope_prefix(scope)):
        return True
    match = _FACTS_LEDGER_CITATION_RE.fullmatch(citation)
    return bool(match and match.group("slug") == scope)


def resolve_recall_kinds(kinds: frozenset[str] | None) -> frozenset[str]:
    """`None` is the default bag (no `code`). An explicit set is used as-is
    after rejecting unknown kind tokens."""
    if kinds is None:
        return DEFAULT_RECALL_KINDS
    unknown = kinds - _ALL_RECALL_KINDS
    if unknown:
        raise ValueError(f"unknown recall kind(s) {sorted(unknown)!r}; expected one of {sorted(_ALL_RECALL_KINDS)}")
    return kinds


def resolve_recall_selection(
    *,
    kinds: frozenset[str] | None = None,
    surface: str | None = None,
) -> frozenset[str]:
    """Resolve `--mode` or `--kind` to a kind bag (Story 16.1).

    The two flags are exclusive. ``surface`` is the user-facing mode
    (`planning` / `memory` / `code`), not lexical/semantic ranking.
    """
    if surface is not None and kinds is not None:
        raise ValueError("--mode and --kind are exclusive")
    if surface is not None:
        bag = RECALL_MODE_KINDS.get(surface)
        if bag is None:
            raise ValueError(f"unknown recall mode {surface!r}; expected one of {sorted(RECALL_MODE_KINDS)}")
        return bag
    return resolve_recall_kinds(kinds)


def answer(
    query: str,
    store: GraphStore,
    *,
    repo_root: Path,
    mode: str = "lexical",
    scope: str | None = None,
    kinds: frozenset[str] | None = None,
    surface: str | None = None,
) -> RecallAnswer:
    """Deterministic, cited retrieval over the compiled graph (AD-6/AD-8).

    Only `is_current` nodes are candidates -- a superseded fact (Story 2.3)
    stays queryable via `store.query_by_citation()`/`iter_nodes()`, but
    never surfaces here as if it were still current. Lexical candidates are
    ranked by query/node token-overlap (desc), tie-broken by node id (asc).
    Semantic candidates come from `store.query_similar` (Story 28.2) — the
    caller does not select a driver. Then citation resolvability filters
    the ranked list -- an unresolvable top match is skipped, never returned.

    `scope` (marshal Story 28.27's own finding, 2026-09-10): lexical
    token-overlap has no notion of "project" beyond whatever words the
    query happens to share with a node's title/text -- a query naming
    project slug `pyforge-warden` tokenizes to `{pyforge, warden}` (the
    `-` is not a token character), and `pyforge` alone matches every
    project's own documents equally, so a topically-strong wrong-project
    node can outscore a correct-project node using less generic
    vocabulary. `scope` filters candidates to one project's own citation
    tree BEFORE scoring, closing that gap for both lexical and semantic
    modes;     `scope=None` is the prior, unscoped behavior, byte-for-byte.

    `kinds` (Story 8.5): `None` omits `code`. An explicit frozenset is the
    only candidate kinds — `--kind code` is opt-in, not additive.
    `surface` (Story 16.1): named `--mode` bag; exclusive with `kinds`.
    """
    allowed = resolve_recall_selection(kinds=kinds, surface=surface)
    if mode == "semantic":
        return _answer_semantic(query, store, repo_root=repo_root, scope=scope, kinds=allowed)
    if mode != "lexical":
        raise ValueError(f"unknown recall mode {mode!r}; expected 'lexical' or 'semantic'")

    query_tokens = _tokenize(query)
    if not query_tokens:
        return _no_grounded_answer()

    scored: list[tuple[int, GraphNode]] = []
    for node in store.iter_nodes():
        if not node.is_current or node.stale:
            continue
        if node.kind not in allowed:
            continue
        if not _citation_in_scope(node.citation, scope):
            continue
        node_tokens = _tokenize(f"{node.title} {node.text}")
        overlap = len(query_tokens & node_tokens)
        if overlap > 0:
            scored.append((overlap, node))

    scored.sort(key=lambda pair: (-pair[0], pair[1].id))

    for _score, node in scored:
        if _withheld_as_stale(node, store, repo_root):
            continue
        if _citation_is_resolvable(node.citation, repo_root):
            return RecallAnswer(grounded=True, text=node.text, citation=node.citation, node_id=node.id)
        # Unresolvable citation -- never surface an uncited/unverifiable answer; try the next candidate.

    return _no_grounded_answer()


def _answer_semantic(
    query: str,
    store: GraphStore,
    *,
    repo_root: Path,
    scope: str | None = None,
    kinds: frozenset[str] | None = None,
) -> RecallAnswer:
    allowed = resolve_recall_kinds(kinds)
    if not query.strip():
        return _no_grounded_answer()
    for node in store.query_similar(query, limit=16):
        if not node.is_current or node.stale:
            continue
        if node.kind not in allowed:
            continue
        if not _citation_in_scope(node.citation, scope):
            continue
        if _withheld_as_stale(node, store, repo_root):
            continue
        if _citation_is_resolvable(node.citation, repo_root):
            return RecallAnswer(grounded=True, text=node.text, citation=node.citation, node_id=node.id)
    return _no_grounded_answer()


def _withheld_as_stale(node: GraphNode, store: GraphStore, repo_root: Path) -> bool:
    """Stored `stale` bit, plus recall-time compare to `compiled_at`."""
    if node.stale:
        return True
    compiled_at = getattr(store, "compiled_at", None)
    if compiled_at is None:
        return False
    return source_committed_after(repo_root, node, compiled_at)


def _no_grounded_answer() -> RecallAnswer:
    return RecallAnswer(grounded=False, text="no grounded answer found", citation=None, node_id=None)


def _citation_is_resolvable(citation: str, repo_root: Path) -> bool:
    if citation.startswith("commit:"):
        sha = citation.removeprefix("commit:")
        return bool(_COMMIT_SHA_RE.fullmatch(sha))
    if _TRANSCRIPT_CITATION_RE.fullmatch(citation):
        # A transcript citation (`<jsonl filename>:L<line>`) is format-checked
        # only, never re-resolved against a live file: transcripts are
        # per-user/local and can be pruned or rotated outside Scribe's
        # control (Story 3.2), mirroring the `commit:<sha>` precedent above.
        return True
    code_match = _CODE_LINE_CITATION_RE.match(citation)
    if code_match:
        # Story 6.1 fix: before this branch existed, a `code` node's
        # `<path>:L<line>` citation fell straight to the whole-string check
        # below, which looked for a literal file named e.g.
        # `"compile.py:L120"` -- never found it, and so no graphify-ingested
        # code node could ever be recalled. Strip the `:L<line>` suffix and
        # check the PATH portion only.
        return (repo_root / code_match.group("path")).is_file()
    return (repo_root / citation).is_file()
