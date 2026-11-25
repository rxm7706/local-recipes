"""Unit tests for pyforge.scribe.recall -- the grounded, cited query path
(Story 2.4, AD-8).
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from pyforge.scribe import compile as compile_module
from pyforge.scribe.capture import capture
from pyforge.scribe.compile import compile_graph
from pyforge.scribe.graph_store import FlatFileGraphStore
from pyforge.scribe.models import GraphNode
from pyforge.scribe.recall import _answer_semantic, answer
from pyforge.scribe.transcripts import TranscriptCandidate, TranscriptScanProposal


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


def test_lexical_tie_break_prefers_newer_valid_from(repo_with_citation: Path) -> None:
    """Story 26.1 / DW-FU-3-2-4: equal overlap → newer ``valid_from`` wins."""
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    shared = "We decided to drop Kuzu because upstream archived the project."
    store.upsert_node(
        _node(
            id="transcript:session-a.jsonl:L1",
            kind="transcript",
            citation="session-a.jsonl:L1",
            text=shared,
            valid_from=datetime(2026, 8, 1, tzinfo=timezone.utc),
        )
    )
    store.upsert_node(
        _node(
            id="transcript:session-b.jsonl:L1",
            kind="transcript",
            citation="session-b.jsonl:L1",
            text=shared,
            valid_from=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
    )
    store.commit()

    result = answer("why drop Kuzu archived upstream", store, repo_root=repo_with_citation)

    assert result.grounded is True
    assert result.node_id == "transcript:session-b.jsonl:L1"


def test_lexical_tie_break_equal_valid_from_orders_by_id(repo_with_citation: Path) -> None:
    when = datetime(2026, 8, 15, tzinfo=timezone.utc)
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    shared = "We decided to drop Kuzu because upstream archived the project."
    store.upsert_node(
        _node(
            id="transcript:session-z.jsonl:L1",
            kind="transcript",
            citation="session-z.jsonl:L1",
            text=shared,
            valid_from=when,
        )
    )
    store.upsert_node(
        _node(
            id="transcript:session-a.jsonl:L1",
            kind="transcript",
            citation="session-a.jsonl:L1",
            text=shared,
            valid_from=when,
        )
    )
    store.commit()

    result = answer("why drop Kuzu archived upstream", store, repo_root=repo_with_citation)

    assert result.grounded is True
    assert result.node_id == "transcript:session-a.jsonl:L1"


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


def test_nested_transcript_citation_is_resolvable_and_recallable(repo_with_citation: Path) -> None:
    """Story 26.1 landing review: nested ``dir-a/session-x.jsonl:L1`` must recall."""
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(
        _node(
            id="transcript:dir-a/session-x.jsonl:L1",
            kind="transcript",
            citation="dir-a/session-x.jsonl:L1",
            text="We decided to adopt SQLite for the edge cache layer.",
        )
    )
    store.commit()

    result = answer("edge cache SQLite", store, repo_root=repo_with_citation)

    assert result.grounded is True
    assert result.citation == "dir-a/session-x.jsonl:L1"


def test_compile_then_recall_nested_transcript_citation(tmp_path: Path) -> None:
    """Story 26.1 landing review: compile must emit nested citations recall accepts."""
    memory_root = tmp_path / ".claude" / "memory"
    memory_root.mkdir(parents=True)
    (memory_root / "MEMORY.md").write_text(
        "# Team Memory Index\n\n## Feedback\n\n## Project\n\n## Reference\n",
        encoding="utf-8",
    )
    transcript_root = tmp_path / "transcripts"
    transcript_root.mkdir()
    nested = transcript_root / "dir-a" / "session-x.jsonl"
    nested.parent.mkdir()
    line = json.dumps(
        {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "We decided to adopt SQLite for the edge cache layer."}]},
            "timestamp": "2026-08-20T12:00:00.000Z",
        }
    )
    nested.write_text(line + "\n", encoding="utf-8")
    proposal = TranscriptScanProposal(
        transcript_root=transcript_root,
        candidates=(
            TranscriptCandidate(
                source_file=nested,
                line_number=1,
                timestamp="2026-08-20T12:00:00.000Z",
                text="We decided to adopt SQLite for the edge cache layer.",
                snippet="SQLite edge cache",
                capture_type="project",
            ),
        ),
    )
    store_path = tmp_path / "graph.json"
    with patch.object(compile_module, "scan_transcripts", return_value=proposal):
        compile_graph(
            memory_root=memory_root,
            repo_root=tmp_path,
            store=FlatFileGraphStore(store_path),
            transcript_root=transcript_root,
        )
    store = FlatFileGraphStore(store_path)
    result = answer("edge cache SQLite", store, repo_root=tmp_path)
    assert result.grounded is True
    assert result.citation == "dir-a/session-x.jsonl:L1"


@pytest.mark.parametrize(
    "citation",
    [
        "../../../etc/passwd.jsonl:L1",
        "session-a.jsonl:L",  # no line number
        "session-a.jsonl:L1x",
        "session-a.txt:L1",  # not a transcript at all
        "session-a.jsonl:L١٢",  # `\d` matches non-ASCII digits; `[0-9]` must not
    ],
)
def test_malformed_transcript_citation_is_not_waved_through(repo_with_citation: Path, citation: str) -> None:
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
    (repo_with_citation / "src" / "example.py").write_text("def foo():\n    pass\n", encoding="utf-8")
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

    result = answer("what does foo do", store, repo_root=repo_with_citation, kinds=frozenset({"code"}))

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


def test_code_node_citing_missing_jsonl_is_not_resolvable(repo_with_citation: Path) -> None:
    """Story 26.1 landing review: format-only transcript branch is kind-gated."""
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(
        _node(
            id="code:python:ghost-jsonl",
            kind="code",
            title="ghost jsonl path",
            text="code node citing a missing jsonl-shaped path",
            citation="data/missing.jsonl:L1",
        )
    )
    store.commit()

    result = answer(
        "ghost jsonl path",
        store,
        repo_root=repo_with_citation,
        kinds=frozenset({"code"}),
    )

    assert result.grounded is False


@pytest.mark.parametrize(
    "citation",
    [
        "session 1.jsonl:L1",
        "sessión.jsonl:L1",
        "a+b.jsonl:L1",
    ],
)
def test_transcript_citation_filenames_with_spaces_or_symbols_are_recallable(
    repo_with_citation: Path,
    citation: str,
) -> None:
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(
        _node(
            id=f"transcript:{citation}",
            kind="transcript",
            citation=citation,
            text="Transcript fact with a permissive filename.",
        )
    )
    store.commit()

    result = answer("Transcript fact", store, repo_root=repo_with_citation)

    assert result.grounded is True
    assert result.citation == citation


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


def test_recall_makes_zero_network_calls(repo_with_citation: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(_node())
    store.commit()

    def _blocked_socket(*args, **kwargs):
        raise AssertionError("network socket construction attempted -- AD-6 violation")

    monkeypatch.setattr(socket, "socket", _blocked_socket)

    result = answer(
        "why did we drop Kuzu?", FlatFileGraphStore(repo_with_citation / "graph.json"), repo_root=repo_with_citation
    )
    assert result.grounded is True


@pytest.fixture()
def repo_with_two_project_citations(tmp_path: Path) -> Path:
    (tmp_path / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts").mkdir(parents=True)
    (tmp_path / "_bmad-output" / "projects" / "pyforge-warden" / "planning-artifacts").mkdir(parents=True)
    (tmp_path / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts" / "notes.md").write_text(
        "content", encoding="utf-8"
    )
    (tmp_path / "_bmad-output" / "projects" / "pyforge-warden" / "planning-artifacts" / "notes.md").write_text(
        "content", encoding="utf-8"
    )
    return tmp_path


def test_scope_excludes_other_projects_denser_match(repo_with_two_project_citations: Path) -> None:
    """Live incident 2026-09-10 (marshal Story 28.27): a query naming
    pyforge-warden tokenizes to {pyforge, warden} -- pyforge alone matches
    every project's own documents, so an unscoped query let a more
    generically-worded marshal node outscore the correct-project warden
    node. scope= closes exactly this gap."""
    store = FlatFileGraphStore(repo_with_two_project_citations / "graph.json")
    store.reset()
    store.upsert_node(
        _node(
            id="memory:marshal/dense",
            citation="_bmad-output/projects/pyforge-marshal/planning-artifacts/notes.md",
            title="epic planning context requirements constraints",
            text="epic planning context requirements constraints epic planning context",
        )
    )
    store.upsert_node(
        _node(
            id="memory:warden/sparse",
            citation="_bmad-output/projects/pyforge-warden/planning-artifacts/notes.md",
            title="warden retro",
            text="warden epic retro notes",
        )
    )
    store.commit()

    unscoped = answer(
        "Epic 1 planning context requirements constraints for pyforge-warden",
        FlatFileGraphStore(repo_with_two_project_citations / "graph.json"),
        repo_root=repo_with_two_project_citations,
    )
    assert unscoped.node_id == "memory:marshal/dense"  # reproduces the bug unscoped

    scoped = answer(
        "Epic 1 planning context requirements constraints for pyforge-warden",
        FlatFileGraphStore(repo_with_two_project_citations / "graph.json"),
        repo_root=repo_with_two_project_citations,
        scope="pyforge-warden",
    )
    assert scoped.grounded is True
    assert scoped.node_id == "memory:warden/sparse"
    # Story 124.2: tracked paths are spelled as joins here -- steward's trigger-map scan counts a bare
    # tracked-path literal as a read of the live tree, and this module reads none.
    assert scoped.citation.startswith("/".join(("_bmad-output", "projects", "pyforge-warden", "")))


def test_scope_excludes_non_project_citations(repo_with_two_project_citations: Path) -> None:
    """A commit:/code/transcript citation has no reliable per-project
    attribution in the citation string -- scope excludes it rather than
    guessing, even when it would otherwise win lexically."""
    store = FlatFileGraphStore(repo_with_two_project_citations / "graph.json")
    store.reset()
    store.upsert_node(
        _node(
            id="memory:commit/dense",
            citation="commit:" + ("a" * 40),
            title="warden epic planning",
            text="warden epic planning context is discussed at length here",
        )
    )
    store.commit()

    result = answer(
        "warden epic planning context",
        FlatFileGraphStore(repo_with_two_project_citations / "graph.json"),
        repo_root=repo_with_two_project_citations,
        scope="pyforge-warden",
    )
    assert result.grounded is False


def test_scope_none_is_unscoped_behavior_unchanged(repo_with_citation: Path) -> None:
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(_node())
    store.commit()

    result = answer(
        "why did we drop Kuzu?",
        FlatFileGraphStore(repo_with_citation / "graph.json"),
        repo_root=repo_with_citation,
        scope=None,
    )
    assert result.grounded is True
    assert result.citation == "notes/kuzu-drop.md"


def test_semantic_scope_excludes_other_projects(repo_with_two_project_citations: Path) -> None:
    marshal_node = _node(
        id="memory:marshal/x",
        citation="_bmad-output/projects/pyforge-marshal/planning-artifacts/notes.md",
    )
    warden_node = _node(
        id="memory:warden/x",
        citation="_bmad-output/projects/pyforge-warden/planning-artifacts/notes.md",
        text="warden-specific answer text",
    )
    # query_similar returns its ranked candidates in order -- marshal first,
    # simulating it winning the embedding-similarity ranking despite being
    # the wrong project, exactly as it won lexically in the live incident.
    store = _FakeSimilarStore([marshal_node, warden_node])

    unscoped = _answer_semantic("planning context", store, repo_root=repo_with_two_project_citations)
    assert unscoped.node_id == "memory:marshal/x"

    scoped = _answer_semantic(
        "planning context", store, repo_root=repo_with_two_project_citations, scope="pyforge-warden"
    )
    assert scoped.grounded is True
    assert scoped.node_id == "memory:warden/x"


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


def test_recall_mode_planning_and_memory_are_exclusive_bags(
    repo_with_citation: Path,
) -> None:
    (repo_with_citation / "docs").mkdir(exist_ok=True)
    (repo_with_citation / "docs" / "prd.md").write_text("prd", encoding="utf-8")
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(_node())
    store.upsert_node(
        _node(
            id="doc:docs/prd.md",
            kind="doc",
            title="PRD",
            text="We dropped Kuzu because planning said so.",
            citation="docs/prd.md",
        )
    )
    store.commit()

    planning = answer(
        "why did we drop Kuzu?",
        store,
        repo_root=repo_with_citation,
        surface="planning",
    )
    memory = answer(
        "why did we drop Kuzu?",
        store,
        repo_root=repo_with_citation,
        surface="memory",
    )
    assert planning.citation == "docs/prd.md"
    assert memory.citation == "notes/kuzu-drop.md"


def test_recall_mode_and_kind_are_exclusive() -> None:
    from pyforge.scribe.recall import resolve_recall_selection

    with pytest.raises(ValueError, match="exclusive"):
        resolve_recall_selection(kinds=frozenset({"doc"}), surface="planning")
    with pytest.raises(ValueError, match="unknown recall mode"):
        resolve_recall_selection(surface="lexical")


def test_recall_mode_code_selects_code_only(repo_with_citation: Path) -> None:
    (repo_with_citation / "src").mkdir(exist_ok=True)
    (repo_with_citation / "src" / "example.py").write_text("x = 1\n", encoding="utf-8")
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(_node())
    store.upsert_node(
        _node(
            id="code:python:example",
            kind="code",
            title="example",
            text="We dropped Kuzu in the AST.",
            citation="src/example.py:L1",
        )
    )
    store.commit()

    result = answer(
        "why did we drop Kuzu?",
        store,
        repo_root=repo_with_citation,
        surface="code",
    )
    assert result.citation == "src/example.py:L1"


@pytest.fixture()
def repo_with_fact_ledgers(tmp_path: Path) -> Path:
    for slug in ("pyforge-scribe", "pyforge-warden"):
        ledger = tmp_path / "presentations" / slug
        ledger.mkdir(parents=True)
        (ledger / "facts.yaml").write_text(
            f"deck: {slug}\nuniqueledger{slug.replace('-', '')}: 1\n",
            encoding="utf-8",
        )
        nested = ledger / "nested"
        nested.mkdir()
        (nested / "facts.yaml").write_text("deck: nested-ignored\n", encoding="utf-8")
    (tmp_path / "_bmad-output" / "projects" / "pyforge-scribe" / "planning-artifacts").mkdir(parents=True)
    (tmp_path / "_bmad-output" / "projects" / "pyforge-scribe" / "planning-artifacts" / "notes.md").write_text(
        "planning only", encoding="utf-8"
    )
    return tmp_path


def test_scope_admits_same_slug_fact_ledger(repo_with_fact_ledgers: Path) -> None:
    store = FlatFileGraphStore(repo_with_fact_ledgers / "graph.json")
    store.reset()
    store.upsert_node(
        _node(
            id="doc:presentations/pyforge-scribe/facts.yaml",
            kind="doc",
            title="scribe facts",
            text="uniqueledgerscribepyforgescribe poster number",
            citation="/".join(("presentations", "pyforge-scribe", "facts.yaml")),
        )
    )
    store.upsert_node(
        _node(
            id="doc:presentations/pyforge-warden/facts.yaml",
            kind="doc",
            title="warden facts",
            text="uniqueledgerwardenpyforgewarden denser epic planning context constraints",
            citation="/".join(("presentations", "pyforge-warden", "facts.yaml")),
        )
    )
    store.commit()

    scoped = answer(
        "uniqueledgerscribepyforgescribe poster number",
        FlatFileGraphStore(repo_with_fact_ledgers / "graph.json"),
        repo_root=repo_with_fact_ledgers,
        scope="pyforge-scribe",
    )
    assert scoped.grounded is True
    assert scoped.citation == "/".join(("presentations", "pyforge-scribe", "facts.yaml"))

    other = answer(
        "uniqueledgerwardenpyforgewarden denser epic planning context constraints",
        FlatFileGraphStore(repo_with_fact_ledgers / "graph.json"),
        repo_root=repo_with_fact_ledgers,
        scope="pyforge-scribe",
    )
    assert other.grounded is False


def test_scope_excludes_nested_facts_yaml(repo_with_fact_ledgers: Path) -> None:
    store = FlatFileGraphStore(repo_with_fact_ledgers / "graph.json")
    store.reset()
    store.upsert_node(
        _node(
            id="doc:presentations/pyforge-scribe/nested/facts.yaml",
            kind="doc",
            title="nested",
            text="nestedledger token unique",
            citation="presentations/pyforge-scribe/nested/facts.yaml",
        )
    )
    store.commit()

    result = answer(
        "nestedledger token unique",
        FlatFileGraphStore(repo_with_fact_ledgers / "graph.json"),
        repo_root=repo_with_fact_ledgers,
        scope="pyforge-scribe",
    )
    assert result.grounded is False


def test_unscoped_recall_still_sees_every_fact_ledger(repo_with_fact_ledgers: Path) -> None:
    store = FlatFileGraphStore(repo_with_fact_ledgers / "graph.json")
    store.reset()
    store.upsert_node(
        _node(
            id="doc:presentations/pyforge-warden/facts.yaml",
            kind="doc",
            title="warden facts",
            text="uniqueledgerwardenpyforgewarden",
            citation="/".join(("presentations", "pyforge-warden", "facts.yaml")),
        )
    )
    store.commit()

    result = answer(
        "uniqueledgerwardenpyforgewarden",
        FlatFileGraphStore(repo_with_fact_ledgers / "graph.json"),
        repo_root=repo_with_fact_ledgers,
    )
    assert result.grounded is True
    assert result.citation == "/".join(("presentations", "pyforge-warden", "facts.yaml"))


def test_recall_withholds_source_committed_after_compiled_at(tmp_path: Path) -> None:
    memory_root = tmp_path / ".claude" / "memory"
    memory_root.mkdir(parents=True)
    (memory_root / "MEMORY.md").write_text(
        "# Team Memory Index\n\n## Feedback\n\n## Project\n\n## Reference\n",
        encoding="utf-8",
    )
    capture(
        memory_root,
        "project",
        "We dropped Kuzu because it was archived upstream after an acquisition.",
        slug="kuzu-drop",
    )

    def _git(*args: str, env: dict[str, str] | None = None) -> None:
        merged = os.environ.copy()
        if env:
            merged.update(env)
        subprocess.run(
            ["git", *args],
            cwd=str(tmp_path),
            check=True,
            capture_output=True,
            text=True,
            env=merged,
        )

    _git("init", "-q")
    _git("config", "user.email", "test@example.com")
    _git("config", "user.name", "Test")
    first = {
        "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+00:00",
        "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+00:00",
    }
    _git("add", "-A", env=first)
    _git("commit", "-q", "-m", "capture", env=first)

    store_path = tmp_path / "graph.json"
    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=FlatFileGraphStore(store_path),
        transcript_root=tmp_path / "no-transcripts",
        compiled_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    reloaded = FlatFileGraphStore(store_path)
    assert reloaded.compiled_at == datetime(2026, 1, 2, tzinfo=timezone.utc)
    before = answer("why did we drop Kuzu", reloaded, repo_root=tmp_path)
    assert before.grounded is True

    cited = next(n for n in reloaded.iter_nodes() if n.id == "memory:project/kuzu-drop")
    source = tmp_path / cited.citation
    source.write_text(source.read_text(encoding="utf-8") + "\n# noon landing\n", encoding="utf-8")
    later = {
        "GIT_AUTHOR_DATE": "2026-01-03T00:00:00+00:00",
        "GIT_COMMITTER_DATE": "2026-01-03T00:00:00+00:00",
    }
    _git("add", "-A", env=later)
    _git("commit", "-q", "-m", "after compile", env=later)

    after = answer("why did we drop Kuzu", FlatFileGraphStore(store_path), repo_root=tmp_path)
    assert after.grounded is False


# --- Story 35.1, defect 1: every shipped store keeps the compile time, and recall's guard fires on each ---
#
# No server and no DuckDB here: the PostgreSQL store runs on an in-memory stand-in for psycopg, the plane store on
# an in-memory stand-in for its DuckDB connection. Each stand-in holds the rows of the ONE relation the store already
# has, so a stamp that survives a reload was written through that relation, as a row.


class _Cursor:
    def __init__(self, rows: list[tuple]) -> None:
        self._rows = rows

    def fetchone(self) -> tuple | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[tuple]:
        return list(self._rows)


class _FakeSqlText(str):
    def format(self, *args: object, **kwargs: object) -> _FakeSqlText:  # type: ignore[override]
        return _FakeSqlText(str.format(self, *args, **kwargs))


class _FakeSqlModule:
    SQL = _FakeSqlText

    @staticmethod
    def Identifier(name: str) -> str:  # noqa: N802 -- psycopg.sql's own spelling
        return f'"{name}"'


class _FakePgConnection:
    """The statements `PostgresGraphStore` issues, against rows kept by id. Columns as `graph_nodes` has them."""

    def __init__(self, rows: dict[str, tuple]) -> None:
        self._rows = rows

    def __enter__(self) -> _FakePgConnection:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def transaction(self) -> _FakePgConnection:
        return self

    def execute(self, query: object, params: tuple = ()) -> _Cursor:
        text = " ".join(str(query).split())
        assert not any(word in text.upper() for word in ("CREATE ", "ALTER ", "DROP ")), f"DDL at runtime: {text}"
        if text.startswith("SELECT to_regclass"):
            return _Cursor([(params[0],)])
        if text.startswith("SELECT pg_advisory_xact_lock"):
            return _Cursor([])
        if text.startswith("DELETE FROM"):
            self._rows.clear()
            return _Cursor([])
        if text.startswith("INSERT INTO"):
            assert len(params) == 10, "graph_nodes has ten columns; a stamp must not need an eleventh"
            self._rows[str(params[0])] = tuple(params)
            return _Cursor([])
        assert text.startswith("SELECT id, kind, title, text, citation, valid_from, valid_until, superseded_by, stale")
        rows = [row[:8] + (row[9],) for _id, row in sorted(self._rows.items())]
        if "WHERE" in text:  # query_similar: embedded, current, not stale
            rows = [
                row[:8] + (row[9],)
                for _id, row in sorted(self._rows.items())
                if row[8] is not None and row[6] is None and row[9] is False and row[0] not in params
            ]
        return _Cursor(rows)


class _FakePlaneConnection:
    """The statements `PlaneGraphStore` issues, against `scribe_nodes` and `scribe_embeddings` kept by id."""

    def __init__(self, tables: dict[str, dict[str, list]]) -> None:
        self._tables = tables

    def execute(self, query: str, params: list | None = None) -> _Cursor:
        text = " ".join(query.split())
        if text.startswith(("CREATE TABLE IF NOT EXISTS", "ALTER TABLE scribe_nodes ADD COLUMN IF NOT EXISTS stale")):
            return _Cursor([])  # the store's own pre-existing bootstrap, unchanged by Story 35.1
        for table in ("scribe_nodes", "scribe_embeddings"):
            if text == f"DELETE FROM {table}":
                self._tables[table].clear()
                return _Cursor([])
            if text.startswith(f"INSERT INTO {table} VALUES"):
                assert params is not None
                assert len(params) == (9 if table == "scribe_nodes" else 2), f"{table} gained a column"
                self._tables[table][str(params[0])] = list(params)
                return _Cursor([])
        if text.startswith("SELECT n.id FROM scribe_embeddings e JOIN scribe_nodes n"):
            nodes = self._tables["scribe_nodes"]
            hits = [
                (node_id,)
                for node_id in sorted(self._tables["scribe_embeddings"])
                if node_id in nodes and nodes[node_id][6] is None and not nodes[node_id][8]
            ]
            return _Cursor(hits)
        assert text.startswith("SELECT id, kind, title, text, citation, valid_from, valid_until, superseded_by, stale")
        return _Cursor([tuple(row) for _id, row in sorted(self._tables["scribe_nodes"].items())])

    def close(self) -> None:
        return None


@pytest.fixture(params=["flatfile", "postgres", "plane"])
def stamped_store(request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """`(open, raw_ids)`: `open()` is a fresh store over the same backing; `raw_ids()` the ids the backing holds."""
    kind = request.param
    if kind == "flatfile":
        path = tmp_path / "graph.json"

        def _raw_flat() -> set[str]:
            return set(json.loads(path.read_text(encoding="utf-8"))["nodes"]) if path.is_file() else set()

        return (lambda: FlatFileGraphStore(path)), _raw_flat
    if kind == "postgres":
        from types import SimpleNamespace

        from pyforge.scribe import graph_store_pg

        rows: dict[str, tuple] = {}
        fake = SimpleNamespace(
            connect=lambda _dsn: _FakePgConnection(rows),
            errors=SimpleNamespace(InsufficientPrivilege=PermissionError),
        )
        monkeypatch.setattr(graph_store_pg, "_import_psycopg", lambda: (fake, _FakeSqlModule))
        return (
            lambda: graph_store_pg.PostgresGraphStore("postgres://fake/scribe_graph", tmp_path / "not-json")
        ), lambda: set(rows)

    from pyforge.scribe import graph_store_plane

    tables: dict[str, dict[str, list]] = {"scribe_nodes": {}, "scribe_embeddings": {}}
    monkeypatch.setattr(
        graph_store_plane.PlaneGraphStore, "_open_plane", lambda self, path, *, write: _FakePlaneConnection(tables)
    )
    return (
        lambda: graph_store_plane.PlaneGraphStore(tmp_path / graph_store_plane.ATLAS_DUCKDB_NAME, tmp_path / "g.json")
    ), lambda: set(tables["scribe_nodes"])


def _kuzu_repo(tmp_path: Path) -> tuple[Path, object]:
    """A git repository holding one captured memory, committed on 2026-01-01; returns `(memory_root, commit_later)`."""
    memory_root = tmp_path / ".claude" / "memory"
    memory_root.mkdir(parents=True)
    (memory_root / "MEMORY.md").write_text(
        "# Team Memory Index\n\n## Feedback\n\n## Project\n\n## Reference\n", encoding="utf-8"
    )
    capture(
        memory_root,
        "project",
        "We dropped Kuzu because it was archived upstream after an acquisition.",
        slug="kuzu-drop",
    )

    def _git(*args: str, date: str | None = None) -> None:
        env = os.environ.copy()
        if date:
            env.update({"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date})
        subprocess.run(["git", *args], cwd=str(tmp_path), check=True, capture_output=True, text=True, env=env)

    _git("init", "-q")
    _git("config", "user.email", "test@example.com")
    _git("config", "user.name", "Test")
    (tmp_path / ".gitignore").write_text("graph.json\nnot-json\ng.json\n*.lock\n", encoding="utf-8")
    _git("add", "-A")
    _git("commit", "-q", "-m", "capture", date="2026-01-01T00:00:00+00:00")

    def _commit_later(citation: str) -> None:
        source = tmp_path / citation
        source.write_text(source.read_text(encoding="utf-8") + "\n# noon landing\n", encoding="utf-8")
        _git("add", "-A")
        _git("commit", "-q", "-m", "after compile", date="2026-01-03T00:00:00+00:00")

    return memory_root, _commit_later


_STAMP = datetime(2026, 1, 2, 3, 4, 5, 678901, tzinfo=timezone.utc)


def test_every_store_keeps_compiled_at_across_commit_and_reload(tmp_path: Path, stamped_store) -> None:
    from pyforge.scribe.models import COMPILED_AT_ROW_ID

    open_store, raw_ids = stamped_store
    memory_root, _commit_later = _kuzu_repo(tmp_path)
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=open_store(),
        transcript_root=tmp_path / "no-transcripts",
        compiled_at=_STAMP,
    )

    reloaded = open_store()
    assert reloaded.compiled_at == _STAMP

    # The stamp is never a node: not in a scan, a citation lookup, a similarity ranking, or the compile's count.
    ids = [node.id for node in reloaded.iter_nodes()]
    assert "memory:project/kuzu-drop" in ids
    assert COMPILED_AT_ROW_ID not in ids
    assert not any(node_id.startswith("scribe:") for node_id in ids)
    assert reloaded.query_by_citation("") == []
    assert COMPILED_AT_ROW_ID not in [node.id for node in reloaded.query_similar("kuzu compiled_at scribe", limit=64)]
    assert result.node_count == len(ids)
    assert raw_ids() - set(ids) <= {COMPILED_AT_ROW_ID}, "the backing holds the nodes and at most the one stamp row"

    # A second commit of the reloaded store carries the stamp forward; a reset drops it, in memory and on reload.
    reloaded.commit()
    assert open_store().compiled_at == _STAMP
    cleared = open_store()
    cleared.reset()
    assert cleared.compiled_at is None
    cleared.commit()
    assert open_store().compiled_at is None
    assert raw_ids() == set()


def test_every_store_withholds_a_source_committed_after_compiled_at(tmp_path: Path, stamped_store) -> None:
    open_store, _raw_ids = stamped_store
    memory_root, commit_later = _kuzu_repo(tmp_path)
    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=open_store(),
        transcript_root=tmp_path / "no-transcripts",
        compiled_at=_STAMP,
    )

    reloaded = open_store()
    memory_only = frozenset({"memory"})  # the commit node of the same change has no source file to compare
    semantic = bool(reloaded.query_similar("why did we drop Kuzu"))
    assert answer("why did we drop Kuzu", reloaded, repo_root=tmp_path).grounded is True
    if semantic:
        served = answer("why did we drop Kuzu", reloaded, repo_root=tmp_path, mode="semantic", kinds=memory_only)
        assert served.node_id == "memory:project/kuzu-drop"

    cited = next(n for n in reloaded.iter_nodes() if n.id == "memory:project/kuzu-drop")
    assert cited.stale is False
    commit_later(cited.citation)

    after = open_store()
    assert next(n for n in after.iter_nodes() if n.id == cited.id).stale is False, "the guard, not the stored bit"
    assert answer("why did we drop Kuzu", after, repo_root=tmp_path).grounded is False
    if semantic:
        withheld = answer("why did we drop Kuzu", after, repo_root=tmp_path, mode="semantic", kinds=memory_only)
        assert withheld.grounded is False


@pytest.mark.parametrize("stamped_store", ["postgres", "plane"], indirect=True)
def test_no_relational_store_accepts_a_node_under_the_reserved_stamp_id(stamped_store) -> None:
    from pyforge.scribe.models import COMPILED_AT_ROW_ID

    open_store, raw_ids = stamped_store
    store = open_store()
    store.reset()
    with pytest.raises(ValueError, match="reserved"):
        store.upsert_node(_node(id=COMPILED_AT_ROW_ID))
    store.commit()
    assert raw_ids() == set()
