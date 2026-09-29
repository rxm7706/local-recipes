"""Story 28.8 (SPEC-marshal-token-economy CAP-5) -- the pure declaration
and freshness-mapping half of the ``derived-context`` layer.

Everything here is pure: no filesystem, no subprocess. The end-to-end ACs
(zero recompute on unchanged sources, exactly one refresh on a source
edit, off-means-unchanged) are proven in ``test_cli_context.py`` against a
contract double of the scribe grammar; this file pins the pieces those
proofs rest on.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.marshal.core import derived_context as derived
from pyforge.marshal.core.policy import CONTEXT_LAYER_NAMES

_PLANNING = "_bmad-output/projects/pyforge-marshal/planning-artifacts"
_SPECS = f"{_PLANNING}/specs"
_IMPL = "_bmad-output/projects/pyforge-marshal/implementation-artifacts"


def test_layer_name_is_a_member_of_the_closed_context_vocabulary():
    """Story 28.1 owns the closed 5-layer matrix; a renamed layer must not
    silently orphan this story's consumer."""
    assert derived.DERIVED_CONTEXT_LAYER in CONTEXT_LAYER_NAMES


def test_source_patterns_are_the_skills_own_document_vocabulary():
    """``step-01-clarify-and-route.md``'s path-B listing, verbatim -- the
    exact document set ``compile-epic-context.md`` distills from."""
    assert derived.EPIC_CONTEXT_SOURCE_PATTERNS == (
        "*prd*",
        "*architecture*",
        "*ux*",
        "*epic*",
        "*brief*",
    )


class TestSourceSelection:
    def test_selects_the_planning_documents_and_nothing_else(self):
        sources = derived.select_sources(
            _PLANNING,
            [
                "epics.md",
                "PRD.md",
                "architecture.md",
                "integration-architecture.md",
                "ux-spec.md",
                "product-brief.md",
                "sprint-status-ledger.yaml",
                "index.md",
                "deferred-work-ledger.md",
                "prfaq-something.md",
            ],
            derived.EPIC_CONTEXT_SOURCE_PATTERNS,
        )
        assert sources == (
            f"{_PLANNING}/PRD.md",
            f"{_PLANNING}/architecture.md",
            f"{_PLANNING}/epics.md",
            f"{_PLANNING}/integration-architecture.md",
            f"{_PLANNING}/product-brief.md",
            f"{_PLANNING}/ux-spec.md",
        )

    def test_story_specs_and_ledgers_are_not_epic_context_sources(self):
        """The whole point of declaring sources: landing an unrelated story
        spec must not invalidate an epic's distill (today's mtime rule over
        the whole directory does exactly that)."""
        sources = derived.select_sources(
            _PLANNING,
            ["spec-28-8-derived-context.md", "sprint-status-ledger.yaml", "retro.md"],
            derived.EPIC_CONTEXT_SOURCE_PATTERNS,
        )
        assert sources == ()

    def test_matching_is_case_insensitive_and_deduplicated(self):
        sources = derived.select_sources(
            _PLANNING, ["PRD.MD", "epics-and-prd.md"], derived.EPIC_CONTEXT_SOURCE_PATTERNS
        )
        # `epics-and-prd.md` matches BOTH `*prd*` and `*epic*` -- one source.
        assert sources == (f"{_PLANNING}/PRD.MD", f"{_PLANNING}/epics-and-prd.md")

    def test_non_markdown_files_are_never_sources(self):
        assert (
            derived.select_sources(
                _PLANNING,
                ["project-parts.json", "upstream-register.json"],
                ("*",),
            )
            == ()
        )


class TestDeclaration:
    def test_declares_exactly_two_artifacts_with_stable_identities(self):
        declarations = derived.declare_derived_context(
            project_slug="pyforge-marshal",
            epic="28",
            planning_filenames=["epics.md", "PRD.md"],
            planning_spec_filenames=["spec-28-1-a.md", "spec-27-9-b.md"],
            implementation_filenames=["spec-28-8-c.md", "epic-28-context.md"],
        )
        assert [d.name for d in declarations] == [
            "marshal:pyforge-marshal:epic-28-context",
            "marshal:pyforge-marshal:epic-28-continuity",
        ]
        epic_context, continuity = declarations
        assert epic_context.sources == (
            f"{_PLANNING}/PRD.md",
            f"{_PLANNING}/epics.md",
        )
        # Only the SAME epic's specs, from both places this repo keeps them.
        assert continuity.sources == (
            f"{_IMPL}/spec-28-8-c.md",
            f"{_SPECS}/spec-28-1-a.md",
        )

    def test_epic_context_output_is_exactly_where_the_skill_already_writes_it(self):
        """AC 4: what the distill contains, its token target, and WHERE IT
        LIVES are untouched -- only the freshness mechanism changes."""
        epic_context, _continuity = derived.declare_derived_context(
            project_slug="pyforge-marshal", epic="28", planning_filenames=[]
        )
        assert epic_context.output == f"{_IMPL}/epic-28-context.md"

    def test_continuity_output_sits_beside_the_epic_context_distill(self):
        """Same gitignored Tier-3 directory, a distinct filename -- an
        enabled layer keeps the extract there; an off layer writes nothing
        at all (the skill, not this declaration, is what gates the write)."""
        epic_context, continuity = derived.declare_derived_context(
            project_slug="pyforge-marshal", epic="28", planning_filenames=[]
        )
        assert continuity.output == f"{_IMPL}/epic-28-continuity.md"
        assert continuity.output != epic_context.output
        assert Path(continuity.output).parent == Path(epic_context.output).parent

    @pytest.mark.parametrize("epic", ["", "28.8", "twenty-eight", "../28", "28 "])
    def test_a_malformed_epic_is_a_contract_violation(self, epic):
        with pytest.raises(ValueError, match="epic"):
            derived.declare_derived_context(project_slug="pyforge-marshal", epic=epic, planning_filenames=[])

    @pytest.mark.parametrize("slug", ["", "../escape", "a/b", "a\\b"])
    def test_a_malformed_slug_is_a_contract_violation(self, slug):
        with pytest.raises(ValueError, match="slug"):
            derived.declare_derived_context(project_slug=slug, epic="28", planning_filenames=[])


class TestManifest:
    def test_payload_is_json_safe_sorted_and_key_complete(self):
        declarations = derived.declare_derived_context(
            project_slug="pyforge-marshal",
            epic="28",
            planning_filenames=["epics.md"],
        )
        payload = derived.manifest_payload(declarations)
        assert list(payload) == ["artifacts"]
        names = [entry["name"] for entry in payload["artifacts"]]
        assert names == sorted(names)
        for entry in payload["artifacts"]:
            assert set(entry) == {"name", "sources", "output"}
            assert isinstance(entry["sources"], list)


class TestGrammar:
    def test_argv_is_the_declared_scribe_refresh_grammar(self):
        assert derived.render_scribe_refresh_argv("/x/scribe", "/tmp/m.json") == (
            "/x/scribe",
            "index",
            "refresh",
            "--declare",
            "/tmp/m.json",
        )

    def test_parses_scribes_own_report_line(self):
        parsed = derived.parse_refresh_report("refreshed: a, b; skipped (unchanged): c -> /x/cocoindex-index.json\n")
        assert parsed == (("a", "b"), ("c",))

    def test_parses_the_empty_sides(self):
        assert derived.parse_refresh_report("refreshed: (none); skipped (unchanged): (none) -> /x.json") == ((), ())

    def test_strips_the_optional_per_artifact_count_suffix(self):
        parsed = derived.parse_refresh_report("refreshed: graphify-ingest (1 node(s)); skipped (unchanged): move-list")
        assert parsed == (("graphify-ingest",), ("move-list",))

    def test_a_warning_preamble_never_shadows_the_report(self):
        parsed = derived.parse_refresh_report(
            "warning: refreshed: bogus; skipped (unchanged): bogus\n"
            "refreshed: real; skipped (unchanged): (none) -> /x.json\n"
        )
        assert parsed == (("real",), ())

    def test_no_report_line_is_none_not_an_empty_answer(self):
        assert derived.parse_refresh_report("Usage: scribe index refresh") is None


class TestFreshnessMapping:
    def _declarations(self):
        return derived.declare_derived_context(
            project_slug="pyforge-marshal", epic="28", planning_filenames=["epics.md"]
        )

    def test_skipped_reads_fresh_and_refreshed_reads_stale(self):
        declarations = self._declarations()
        result = derived.resolve_freshness(
            declarations,
            refreshed=[declarations[0].name],
            skipped=[declarations[1].name],
        )
        assert [item.state for item in result] == [
            derived.STATE_STALE,
            derived.STATE_FRESH,
        ]

    def test_an_unanswered_artifact_is_unknown_never_fresh(self):
        """Silently reading "the extra said nothing" as current is the
        stale-cache failure this story exists to remove."""
        declarations = self._declarations()
        result = derived.resolve_freshness(declarations, refreshed=[], skipped=[])
        assert {item.state for item in result} == {derived.STATE_UNKNOWN}

    def test_refreshed_wins_over_skipped_for_a_contradictory_answer(self):
        declarations = self._declarations()
        name = declarations[0].name
        result = derived.resolve_freshness(declarations, refreshed=[name], skipped=[name])
        assert result[0].state == derived.STATE_STALE

    def test_result_order_follows_declaration_order(self):
        declarations = self._declarations()
        result = derived.resolve_freshness(declarations, refreshed=[], skipped=[])
        assert [item.name for item in result] == [d.name for d in declarations]


class TestLayerReads:
    def test_absent_layer_reads_off(self):
        assert derived.layer_enabled(None) is False
        assert derived.layer_enabled({}) is False
        assert derived.layer_aggressiveness(None) is None

    def test_declared_layer_reads_through(self):
        layer = {"enabled": True, "aggressiveness": "high"}
        assert derived.layer_enabled(layer) is True
        assert derived.layer_aggressiveness(layer) == "high"

    def test_a_non_string_aggressiveness_is_not_invented(self):
        assert derived.layer_aggressiveness({"enabled": True, "aggressiveness": 3}) is None
