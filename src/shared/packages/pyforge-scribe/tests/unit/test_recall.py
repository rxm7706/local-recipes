"""Unit tests for pyforge.scribe.recall -- the grounded, cited query path
(Story 2.4, AD-8).
"""

from __future__ import annotations

import socket
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pyforge.scribe.graph_store import FlatFileGraphStore
from pyforge.scribe.models import GraphNode
from pyforge.scribe.recall import _answer_semantic, answer


def _node(**overrides) -> GraphNode:
    defaults = dict(
        id="memory:project/kuzu-drop",
        kind="memory",
        title="kuzu-drop",
        text="We dropped Kuzu because it was archived upstream after an acquisition.",
        citation="notes/kuzu-drop.md",
        valid_from=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return GraphNode(**defaults)


@pytest.fixture()
def repo_with_citation(tmp_path: Path) -> Path:
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "kuzu-drop.md").write_text("content", encoding="utf-8")
    return tmp_path


def test_grounded_match_returns_citation(repo_with_citation: Path) -> None:
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(_node())
    store.commit()

    result = answer("why did we drop Kuzu?", store, repo_root=repo_with_citation)

    assert result.grounded is True
    assert result.citation == "notes/kuzu-drop.md"
    assert "archived" in result.text


def test_no_coverage_returns_explicit_no_grounded_answer(repo_with_citation: Path) -> None:
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(_node())
    store.commit()

    result = answer("what is the capital of France", store, repo_root=repo_with_citation)

    assert result.grounded is False
    assert result.text == "no grounded answer found"
    assert result.citation is None


def test_blank_query_returns_no_grounded_answer(repo_with_citation: Path) -> None:
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    result = answer("   ", store, repo_root=repo_with_citation)
    assert result.grounded is False


def test_superseded_node_is_excluded_from_default_answer(repo_with_citation: Path) -> None:
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(_node())
    store.invalidate_edge(
        "memory:project/kuzu-drop",
        ended_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        superseded_by="memory:project/kuzu-drop-v2",
    )
    store.commit()

    result = answer("why did we drop Kuzu?", store, repo_root=repo_with_citation)

    assert result.grounded is False


def test_unresolvable_citation_is_skipped_falls_through(repo_with_citation: Path) -> None:
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(_node(citation="notes/does-not-exist.md"))
    store.commit()

    result = answer("why did we drop Kuzu?", store, repo_root=repo_with_citation)

    assert result.grounded is False


def test_unresolvable_citation_falls_through_to_next_candidate(repo_with_citation: Path) -> None:
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(
        _node(
            id="memory:project/kuzu-drop-ghost",
            citation="notes/does-not-exist.md",
            text="Kuzu was dropped, ghost citation edition.",
        )
    )
    store.upsert_node(_node())  # real, resolvable citation
    store.commit()

    result = answer("why did we drop Kuzu?", store, repo_root=repo_with_citation)

    assert result.grounded is True
    assert result.citation == "notes/kuzu-drop.md"


def test_stale_node_is_excluded_from_default_answer(repo_with_citation: Path) -> None:
    """Story 6.3, AC3: a stale-flagged node is never served, the same way a
    superseded node isn't -- the consumer falls back rather than seeing it."""
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(_node(stale=True))
    store.commit()

    result = answer("why did we drop Kuzu?", store, repo_root=repo_with_citation)

    assert result.grounded is False


def test_stale_node_falls_through_to_next_non_stale_candidate(repo_with_citation: Path) -> None:
    """Mirrors `test_unresolvable_citation_falls_through_to_next_candidate` --
    a stale top candidate does not block a resolvable, non-stale one from
    being served."""
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(
        _node(
            id="memory:project/kuzu-drop-stale",
            citation="notes/kuzu-drop.md",
            text="Kuzu was dropped, stale edition.",
            stale=True,
        )
    )
    store.upsert_node(_node())  # non-stale, resolvable
    store.commit()

    result = answer("why did we drop Kuzu?", store, repo_root=repo_with_citation)

    assert result.grounded is True
    assert result.citation == "notes/kuzu-drop.md"
    assert result.node_id == "memory:project/kuzu-drop"


class _FakeSimilarStore:
    """Minimal `query_similar`-only double -- `_answer_semantic()` never
    calls anything else on its `store` argument, so this avoids the real
    semantic tests' PostgreSQL dependency (`tests/unit/test_recall_semantic.py`)."""

    def __init__(self, nodes: list[GraphNode]) -> None:
        self._nodes = nodes

    def query_similar(self, query: str, *, limit: int = 8) -> list[GraphNode]:
        return self._nodes


def test_semantic_stale_node_is_excluded_falls_through(repo_with_citation: Path) -> None:
    """Story 6.3, AC3 on the semantic path too -- `_answer_semantic()` skips
    a stale node exactly like `answer()`'s lexical path does."""
    stale_node = _node(citation="notes/kuzu-drop.md", stale=True)
    clean_node = _node(
        id="memory:project/kuzu-drop-clean",
        citation="notes/kuzu-drop.md",
        text="Kuzu, clean edition.",
    )
    store = _FakeSimilarStore([stale_node, clean_node])

    result = _answer_semantic("why did we drop Kuzu?", store, repo_root=repo_with_citation)

    assert result.grounded is True
    assert result.node_id == "memory:project/kuzu-drop-clean"


def test_commit_citation_is_resolvable_if_well_formed_sha(repo_with_citation: Path) -> None:
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(
        _node(
            id="commit:abc1234",
            kind="commit",
            citation="commit:abc1234",
            text="Dropped Kuzu in this commit.",
        )
    )
    store.commit()

    result = answer("why did we drop Kuzu?", store, repo_root=repo_with_citation)

    assert result.grounded is True
    assert result.citation == "commit:abc1234"


def test_transcript_citation_is_resolvable_if_well_formed(repo_with_citation: Path) -> None:
    """A `<jsonl filename>:L<line>` transcript citation (Story 3.2) is
    format-checked only, never re-resolved against a live file -- mirrors
    `test_commit_citation_is_resolvable_if_well_formed_sha` exactly."""
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(
        _node(
            id="transcript:session-a.jsonl:L1",
            kind="transcript",
            citation="session-a.jsonl:L1",
            text="Dropped Kuzu, straight from a transcript.",
        )
    )
    store.commit()

    result = answer("why did we drop Kuzu?", store, repo_root=repo_with_citation)

    assert result.grounded is True
    assert result.citation == "session-a.jsonl:L1"


@pytest.mark.parametrize(
    "citation",
    [
        "nested/dir/session-a.jsonl:L1",  # contract says "no directory path"
        "../../../etc/passwd.jsonl:L1",
        "session-a.jsonl:L",  # no line number
        "session-a.jsonl:L1x",
        "session-a.txt:L1",  # not a transcript at all
        "session-a.jsonl:L١٢",  # `\d` matches non-ASCII digits; `[0-9]` must not
    ],
)
def test_malformed_transcript_citation_is_not_waved_through(
    repo_with_citation: Path, citation: str
) -> None:
    """Review finding: the transcript branch was `.+\\.jsonl:L\\d+`, whose
    `.+` also admitted directory paths and `..` traversal -- and because
    that branch short-circuits the `is_file()` check below it, any such
    citation was declared resolvable WITHOUT existing. Only a bare
    `<jsonl filename>:L<line>` may skip the file check; everything else
    falls through to it and, absent a real file, must not surface."""
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(
        _node(
            id=f"transcript:{citation}",
            kind="transcript",
            citation=citation,
            text="Dropped Kuzu, straight from a transcript.",
        )
    )
    store.commit()

    result = answer("why did we drop Kuzu?", store, repo_root=repo_with_citation)

    assert result.grounded is False
    assert result.citation is None


def test_code_citation_with_line_is_resolvable(repo_with_citation: Path) -> None:
    """Story 6.1 fix: a graphify-ingested `code` node's `<path>:L<line>`
    citation must resolve -- before this fix, every such node was
    unrecallable (the whole `"...py:L120"` string was checked as a literal
    filename and never found)."""
    (repo_with_citation / "src").mkdir()
    (repo_with_citation / "src" / "example.py").write_text(
        "def foo():\n    pass\n", encoding="utf-8"
    )
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(
        _node(
            id="code:python:example.foo",
            kind="code",
            title="foo()",
            text="function foo (src/example.py)",
            citation="src/example.py:L1",
        )
    )
    store.commit()

    missed = answer("what does foo do", store, repo_root=repo_with_citation)
    assert missed.grounded is False

    result = answer(
        "what does foo do", store, repo_root=repo_with_citation, kinds=frozenset({"code"})
    )

    assert result.grounded is True
    assert result.citation == "src/example.py:L1"


def test_code_citation_pointing_at_a_missing_file_is_not_resolvable(
    repo_with_citation: Path,
) -> None:
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(
        _node(
            id="code:python:ghost",
            kind="code",
            title="ghost()",
            text="function ghost nowhere on disk",
            citation="src/does_not_exist.py:L42",
        )
    )
    store.commit()

    result = answer("ghost function", store, repo_root=repo_with_citation)

    assert result.grounded is False


def test_determinism_two_independent_store_instances_same_file_same_answer(
    repo_with_citation: Path,
) -> None:
    store_path = repo_with_citation / "graph.json"
    seed_store = FlatFileGraphStore(store_path)
    seed_store.reset()
    seed_store.upsert_node(_node())
    seed_store.upsert_node(
        _node(id="memory:project/other", citation="notes/kuzu-drop.md", text="Kuzu, unrelated note.")
    )
    seed_store.commit()

    result_one = answer("why did we drop Kuzu?", FlatFileGraphStore(store_path), repo_root=repo_with_citation)
    result_two = answer("why did we drop Kuzu?", FlatFileGraphStore(store_path), repo_root=repo_with_citation)

    assert result_one == result_two


def test_recall_makes_zero_network_calls(
    repo_with_citation: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(_node())
    store.commit()

    def _blocked_socket(*args, **kwargs):
        raise AssertionError("network socket construction attempted -- AD-6 violation")

    monkeypatch.setattr(socket, "socket", _blocked_socket)

    result = answer("why did we drop Kuzu?", FlatFileGraphStore(repo_with_citation / "graph.json"), repo_root=repo_with_citation)
    assert result.grounded is True


@pytest.fixture()
def repo_with_two_project_citations(tmp_path: Path) -> Path:
    (tmp_path / '_bmad-output' / 'projects' / 'pyforge-marshal' / 'planning-artifacts').mkdir(parents=True)
    (tmp_path / '_bmad-output' / 'projects' / 'pyforge-warden' / 'planning-artifacts').mkdir(parents=True)
    (tmp_path / '_bmad-output' / 'projects' / 'pyforge-marshal' / 'planning-artifacts' / 'notes.md').write_text('content', encoding='utf-8')
    (tmp_path / '_bmad-output' / 'projects' / 'pyforge-warden' / 'planning-artifacts' / 'notes.md').write_text('content', encoding='utf-8')
    return tmp_path


def test_scope_excludes_other_projects_denser_match(repo_with_two_project_citations: Path) -> None:
    """Live incident 2026-09-10 (marshal Story 28.27): a query naming
    pyforge-warden tokenizes to {pyforge, warden} -- pyforge alone matches
    every project's own documents, so an unscoped query let a more
    generically-worded marshal node outscore the correct-project warden
    node. scope= closes exactly this gap."""
    store = FlatFileGraphStore(repo_with_two_project_citations / 'graph.json')
    store.reset()
    store.upsert_node(_node(
        id='memory:marshal/dense',
        citation='_bmad-output/projects/pyforge-marshal/planning-artifacts/notes.md',
        title='epic planning context requirements constraints',
        text='epic planning context requirements constraints epic planning context',
    ))
    store.upsert_node(_node(
        id='memory:warden/sparse',
        citation='_bmad-output/projects/pyforge-warden/planning-artifacts/notes.md',
        title='warden retro',
        text='warden epic retro notes',
    ))
    store.commit()

    unscoped = answer(
        'Epic 1 planning context requirements constraints for pyforge-warden',
        FlatFileGraphStore(repo_with_two_project_citations / 'graph.json'),
        repo_root=repo_with_two_project_citations,
    )
    assert unscoped.node_id == 'memory:marshal/dense'  # reproduces the bug unscoped

    scoped = answer(
        'Epic 1 planning context requirements constraints for pyforge-warden',
        FlatFileGraphStore(repo_with_two_project_citations / 'graph.json'),
        repo_root=repo_with_two_project_citations,
        scope='pyforge-warden',
    )
    assert scoped.grounded is True
    assert scoped.node_id == 'memory:warden/sparse'
    assert scoped.citation.startswith('_bmad-output/projects/pyforge-warden/')


def test_scope_excludes_non_project_citations(repo_with_two_project_citations: Path) -> None:
    """A commit:/code/transcript citation has no reliable per-project
    attribution in the citation string -- scope excludes it rather than
    guessing, even when it would otherwise win lexically."""
    store = FlatFileGraphStore(repo_with_two_project_citations / 'graph.json')
    store.reset()
    store.upsert_node(_node(
        id='memory:commit/dense',
        citation='commit:' + ('a' * 40),
        title='warden epic planning',
        text='warden epic planning context is discussed at length here',
    ))
    store.commit()

    result = answer(
        'warden epic planning context',
        FlatFileGraphStore(repo_with_two_project_citations / 'graph.json'),
        repo_root=repo_with_two_project_citations,
        scope='pyforge-warden',
    )
    assert result.grounded is False


def test_scope_none_is_unscoped_behavior_unchanged(repo_with_citation: Path) -> None:
    store = FlatFileGraphStore(repo_with_citation / 'graph.json')
    store.reset()
    store.upsert_node(_node())
    store.commit()

    result = answer(
        'why did we drop Kuzu?',
        FlatFileGraphStore(repo_with_citation / 'graph.json'),
        repo_root=repo_with_citation,
        scope=None,
    )
    assert result.grounded is True
    assert result.citation == 'notes/kuzu-drop.md'


def test_semantic_scope_excludes_other_projects(repo_with_two_project_citations: Path) -> None:
    marshal_node = _node(
        id='memory:marshal/x',
        citation='_bmad-output/projects/pyforge-marshal/planning-artifacts/notes.md',
    )
    warden_node = _node(
        id='memory:warden/x',
        citation='_bmad-output/projects/pyforge-warden/planning-artifacts/notes.md',
        text='warden-specific answer text',
    )
    # query_similar returns its ranked candidates in order -- marshal first,
    # simulating it winning the embedding-similarity ranking despite being
    # the wrong project, exactly as it won lexically in the live incident.
    store = _FakeSimilarStore([marshal_node, warden_node])

    unscoped = _answer_semantic(
        'planning context', store, repo_root=repo_with_two_project_citations
    )
    assert unscoped.node_id == 'memory:marshal/x'

    scoped = _answer_semantic(
        'planning context', store, repo_root=repo_with_two_project_citations, scope='pyforge-warden'
    )
    assert scoped.grounded is True
    assert scoped.node_id == 'memory:warden/x'


def test_default_recall_omits_code_even_when_it_is_the_only_overlap(
    repo_with_citation: Path,
) -> None:
    (repo_with_citation / "src").mkdir(exist_ok=True)
    (repo_with_citation / "src" / "example.py").write_text("x = 1\n", encoding="utf-8")
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(
        _node(
            id="code:python:example",
            kind="code",
            title="example",
            text="uniquegraphifytoken function example",
            citation="src/example.py:L1",
        )
    )
    store.commit()

    assert answer("uniquegraphifytoken", store, repo_root=repo_with_citation).grounded is False
    hit = answer(
        "uniquegraphifytoken",
        store,
        repo_root=repo_with_citation,
        kinds=frozenset({"code"}),
    )
    assert hit.grounded is True
    assert hit.citation == "src/example.py:L1"


def test_unknown_recall_kind_raises() -> None:
    from pyforge.scribe.recall import resolve_recall_kinds

    with pytest.raises(ValueError, match="unknown recall kind"):
        resolve_recall_kinds(frozenset({"nope"}))
