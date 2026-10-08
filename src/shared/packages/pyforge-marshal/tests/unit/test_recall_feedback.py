"""Story 47.1 (SPEC-marshal-recall-in-the-loop CAP-1): the pure query/format
half of pre-launch recall injection -- ``core/recall_feedback.py``.

No filesystem, no subprocess (AD-4): every assertion here is a plain
string/path computation. The honesty guarantee (CAP-4: a grounded miss is
explicit, never a fabricated "no relevant corrections found" line) is
enforced BY CONSTRUCTION -- ``render_recall_feedback_block`` has no miss
branch at all, so there is no code path to test for producing one; the
caller (``adapters/harness_bmadloop.py::inject_recall_feedback``) decides
whether to call it at all."""

from __future__ import annotations

from pyforge.marshal.core import recall_feedback


class TestBuildRecallQuery:
    def test_names_the_station_slug(self) -> None:
        query = recall_feedback.build_recall_query("pyforge-doctor")
        assert "pyforge-doctor" in query

    def test_is_a_natural_language_query_not_a_bare_slug(self) -> None:
        query = recall_feedback.build_recall_query("pyforge-doctor")
        assert query != "pyforge-doctor"
        assert "feedback" in query


class TestRecallFeedbackOutputRelpath:
    def test_is_a_sibling_of_epic_context_under_implementation_artifacts(self) -> None:
        relpath = recall_feedback.recall_feedback_output_relpath("pyforge-doctor")
        assert relpath == (
            "_bmad-output/projects/pyforge-doctor/implementation-artifacts/recall-feedback.md"
        )

    def test_scopes_by_project_slug(self) -> None:
        acme = recall_feedback.recall_feedback_output_relpath("acme")
        widget = recall_feedback.recall_feedback_output_relpath("widget")
        assert acme != widget
        assert "acme" in acme
        assert "widget" in widget


class TestRenderRecallFeedbackBlock:
    def test_carries_the_distinguishing_header(self) -> None:
        block = recall_feedback.render_recall_feedback_block(text="always run X before Y", citation=None)
        assert block.startswith(recall_feedback.RECALL_FEEDBACK_HEADER)

    def test_header_is_distinguishable_from_a_spec_or_intent_contract_heading(self) -> None:
        # The story's own "clearly labeled ... distinguishable from the
        # story's own spec/intent-contract content" constraint -- the header
        # names scribe and "auto-recalled", never "Intent" or "Spec".
        assert "scribe" in recall_feedback.RECALL_FEEDBACK_HEADER.lower()
        assert "Intent" not in recall_feedback.RECALL_FEEDBACK_HEADER
        assert "Spec" not in recall_feedback.RECALL_FEEDBACK_HEADER

    def test_includes_the_recalled_text(self) -> None:
        block = recall_feedback.render_recall_feedback_block(text="always run X before Y", citation=None)
        assert "always run X before Y" in block

    def test_includes_the_citation_when_present(self) -> None:
        block = recall_feedback.render_recall_feedback_block(
            text="always run X before Y",
            citation=".claude/memory/feedback/example.md",
        )
        assert "Source: .claude/memory/feedback/example.md" in block

    def test_omits_the_source_line_when_citation_is_none(self) -> None:
        block = recall_feedback.render_recall_feedback_block(text="always run X before Y", citation=None)
        assert "Source:" not in block

    def test_strips_surrounding_whitespace_from_the_recalled_text(self) -> None:
        block = recall_feedback.render_recall_feedback_block(text="  padded text  \n", citation=None)
        assert "  padded text  " not in block
        assert "padded text" in block

    def test_ends_with_a_single_trailing_newline(self) -> None:
        block = recall_feedback.render_recall_feedback_block(text="body", citation=None)
        assert block.endswith("\n")
        assert not block.endswith("\n\n")

    def test_has_no_miss_branch_by_construction(self) -> None:
        """CAP-4's honesty guarantee: this function cannot render a
        synthesized "no relevant corrections found" line, because it has no
        parameter or code path that produces one -- only ``text``/``citation``
        of an ALREADY-grounded hit ever reach it. Inspect the executable
        body only (``inspect.getsource`` minus its own docstring, which
        legitimately discusses the miss case in prose) so this assertion
        checks the code, not the comment describing the code."""
        import ast
        import inspect
        import textwrap

        source = inspect.getsource(recall_feedback.render_recall_feedback_block)
        tree = ast.parse(textwrap.dedent(source))
        (func_def,) = tree.body
        body_without_docstring = func_def.body[1:] if ast.get_docstring(func_def) else func_def.body
        body_source = "\n".join(ast.unparse(node) for node in body_without_docstring)
        assert "no grounded" not in body_source.lower()
        assert "no relevant" not in body_source.lower()
