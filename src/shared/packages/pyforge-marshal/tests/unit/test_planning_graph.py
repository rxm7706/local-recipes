"""Story 28.9 (SPEC-marshal-token-economy CAP-6/CAP-13) -- pure planning-graph
retrieval logic."""

from __future__ import annotations

import pytest

from pyforge.marshal.core import planning_graph as planning


class TestParseRecallOutput:
    def test_grounded_answer_with_citation(self):
        parsed = planning.parse_recall_output("Epic 28 token economy goals.\n[source: epics.md:L42]\n")
        assert parsed.grounded is True
        assert parsed.text == "Epic 28 token economy goals."
        assert parsed.citation == "epics.md:L42"

    def test_explicit_miss(self):
        parsed = planning.parse_recall_output("no grounded answer found\n")
        assert parsed.grounded is False
        assert parsed.text == planning.NO_GROUNDED_ANSWER

    def test_empty_output_is_a_miss(self):
        parsed = planning.parse_recall_output("")
        assert parsed.grounded is False


class TestResolveRetrievalMode:
    def test_graph_mode_requires_all_three(self):
        assert planning.resolve_retrieval_mode(layer_enabled=True, recall_ok=True, grounded=True) == planning.MODE_GRAPH

    @pytest.mark.parametrize(
        "layer_enabled,recall_ok,grounded",
        [
            (False, True, True),
            (True, False, True),
            (True, True, False),
        ],
    )
    def test_every_other_shape_falls_back(self, layer_enabled, recall_ok, grounded):
        assert (
            planning.resolve_retrieval_mode(
                layer_enabled=layer_enabled,
                recall_ok=recall_ok,
                grounded=grounded,
            )
            == planning.MODE_EPIC_CONTEXT_FALLBACK
        )


class TestWholesaleDocGuard:
    def test_epics_and_prd_are_wholesale(self):
        assert planning.is_wholesale_planning_doc("_bmad-output/projects/x/planning-artifacts/epics.md")
        assert planning.is_wholesale_planning_doc("_bmad-output/projects/x/planning-artifacts/PRD.md")

    def test_architecture_is_not_wholesale(self):
        assert not planning.is_wholesale_planning_doc("_bmad-output/projects/x/planning-artifacts/architecture.md")


class TestTokenSavings:
    def test_graph_mode_reports_savings(self):
        assert planning.estimate_tokens_saved(mode=planning.MODE_GRAPH) == 109_500

    def test_fallback_reports_none(self):
        assert planning.estimate_tokens_saved(mode=planning.MODE_EPIC_CONTEXT_FALLBACK) is None


class TestRecallArgvScope:
    def test_scope_appends_flag(self):
        argv = planning.render_scribe_recall_argv("/bin/scribe", "a query", scope="pyforge-warden")
        assert argv == (
            "/bin/scribe",
            "recall",
            "a query",
            "--mode",
            "planning",
            "--scope",
            "pyforge-warden",
        )

    def test_no_scope_omits_flag(self):
        argv = planning.render_scribe_recall_argv("/bin/scribe", "a query")
        assert argv == ("/bin/scribe", "recall", "a query", "--mode", "planning")

    def test_empty_scope_omits_flag(self):
        argv = planning.render_scribe_recall_argv("/bin/scribe", "a query", scope="")
        assert argv == ("/bin/scribe", "recall", "a query", "--mode", "planning")

    def test_never_passes_kind(self):
        scoped = planning.render_scribe_recall_argv("/bin/scribe", "a query", scope="pyforge-scribe")
        assert "--kind" not in scoped
        assert "--mode" in scoped
        assert scoped[scoped.index("--mode") + 1] == "planning"

    def test_never_defaults_to_code_mode(self):
        argv = planning.render_scribe_recall_argv("/bin/scribe", "a query")
        assert argv.count("--mode") == 1
        assert "code" not in argv
