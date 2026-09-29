"""Meta test -- Story 28.8's AC 4 (SPEC-marshal-token-economy CAP-5):
"BMAD skill semantics (what the distill contains, its token target, where
it lives) are untouched -- only the freshness mechanism changed."

The freshness consumers named in this story's Code Map live in the
repo-level ``bmad-build-auto`` skill, not in this package. That is exactly
why they need a gated assertion here: nothing else in the fleet would
notice if a later edit quietly moved the epic-context distill, changed its
required heading, dropped its token target, or -- the failure this story
is most exposed to -- rewired the skill onto a freshness verb marshal does
not actually ship.

Skipped (never failed) when the skill directory is absent: this package is
installable and testable standalone, and a missing repo-level skill is a
different repo, not a regression.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import pyforge.marshal
from pyforge.marshal.cli.main import _build_parser
from pyforge.marshal.core import derived_context as derived

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
#: .../src/shared/packages/pyforge-marshal/src/pyforge/marshal/__init__.py
REPO_ROOT = Path(_PACKAGE_FILE).resolve().parents[7]
SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "bmad-build-auto"
STEP_01 = SKILL_DIR / "step-01-clarify-and-route.md"
COMPILE = SKILL_DIR / "compile-epic-context.md"


def _read(path: Path) -> str:
    if not path.is_file():
        pytest.skip(f"repo-level skill file not present: {path}")
    return path.read_text(encoding="utf-8")


class TestEpicContextContractUntouched:
    def test_the_distill_still_lives_where_it_always_did(self):
        text = _read(STEP_01)
        assert "{{.implementation_artifacts}}/epic-<N>-context.md" in text
        # ...and marshal's own declaration names the identical location, so
        # the freshness answer and the file the skill loads cannot diverge.
        assert derived.epic_context_output_relpath("s", "7").endswith("/implementation-artifacts/epic-7-context.md")

    def test_the_required_header_is_unchanged(self):
        assert "# Epic <N> Context:" in _read(STEP_01)

    def test_the_exact_output_format_headings_are_unchanged(self):
        text = _read(COMPILE)
        for heading in (
            "## Goal",
            "## Stories",
            "## Requirements & Constraints",
            "## Technical Decisions",
            "## UX & Interaction Patterns",
            "## Cross-Story Dependencies",
        ):
            assert heading in text

    def test_the_token_target_is_unchanged(self):
        assert "800–1500 tokens" in _read(COMPILE)

    def test_the_generated_provenance_comment_is_unchanged(self):
        """The distill's own bytes are its content contract -- this story
        may not add a fingerprint line to a file BMAD owns."""
        assert (
            "<!-- Generated from planning artifacts. Regenerate with "
            "compile-epic-context if planning docs change. -->" in _read(COMPILE)
        )


class TestFreshnessMechanismIsWiredToWhatMarshalShips:
    def test_step_01_calls_the_verb_marshal_actually_registers(self):
        assert "marshal context refresh" in _read(STEP_01)
        choices = _top_level_choices()
        assert "context" in choices
        assert "refresh" in _nested_choices(choices["context"], "context_command")

    def test_step_01_reads_the_modes_marshal_actually_emits(self):
        text = _read(STEP_01)
        assert derived.MODE_INCREMENTAL in text
        assert derived.MODE_COMPILE_ON_HUNCH in text

    def test_step_01_reads_the_states_marshal_actually_emits(self):
        text = _read(STEP_01)
        for state in (derived.STATE_FRESH, derived.STATE_STALE, derived.STATE_UNKNOWN):
            assert f"state: {state}" in text

    def test_step_01_names_the_artifact_suffixes_marshal_actually_produces(self):
        text = _read(STEP_01)
        for name in (
            derived.epic_context_artifact_name("slug", "<N>"),
            derived.continuity_artifact_name("slug", "<N>"),
        ):
            suffix = name.split("slug", 1)[1]
            assert suffix in text

    def test_the_finding_prefix_step_01_treats_as_advisory_is_a_real_one(self):
        from pyforge.marshal.core.findings import REGISTERED_CODES
        from pyforge.marshal.core.verdict import Verdict, classify

        assert "MRS-CTX-*" in _read(STEP_01)
        ctx_codes = {code for code in REGISTERED_CODES if code.startswith("MRS-CTX-")}
        # Story 46.1 (spec-pyforge-marshal CAP-192) grew the area with the
        # substrate verbs' codes -- emitted only by `context bootstrap` /
        # `context pack`, which step-01 never calls. The set stays pinned
        # exactly, so a NEW code still forces a look at the skill.
        refresh_codes = {"MRS-CTX-001", "MRS-CTX-002"}
        substrate_codes = {f"MRS-CTX-00{n}" for n in range(3, 8)}
        # Story 46.2 (spec-pyforge-marshal CAP-192): `bundle`'s own new
        # code, reachable from neither `refresh` nor the substrate verbs
        # step-01 never calls either.
        bundle_codes = {"MRS-CTX-008"}
        # Story 46.6 (spec-pyforge-marshal CAP-193, fold-remint of
        # spec-marshal-token-economy CAP-20): `advisory`'s own new code,
        # reachable from none of refresh, the substrate verbs or bundle --
        # step-01 never calls `context advisory` either.
        advisory_codes = {"MRS-CTX-009"}
        assert ctx_codes == refresh_codes | substrate_codes | bundle_codes | advisory_codes
        # ...and the verb step-01 does call cannot reach the substrate codes.
        import inspect

        from pyforge.marshal.cli.context import run_context_refresh

        assert "substrate" not in inspect.getsource(run_context_refresh)
        # Advisory in the skill must mean advisory in the lattice: neither
        # code may ever classify a rung that refuses a run.
        assert classify("MRS-CTX-002") is Verdict.WARN


class TestLayerOffKeepsTheOldRule:
    def test_the_previous_mtime_rule_survives_verbatim_as_the_fallback(self):
        """AC 3's "today's compile-on-hunch behavior is unchanged" is only
        true if the old rule is still literally written down."""
        assert "no file in `{{.planning_artifacts}}` is newer" in _read(STEP_01)

    def test_the_continuity_cache_write_is_explicitly_layer_gated(self):
        text = _read(STEP_01)
        marker = text.index(":epic-<N>-continuity")
        window = text[marker - 800 : marker + 900]
        assert re.search(r"`mode: incremental` only", window)
        assert "write nothing at all" in window


def _top_level_choices() -> dict:
    parser = _build_parser()
    for action in parser._actions:
        if getattr(action, "dest", None) == "command" and action.choices:
            return dict(action.choices)
    raise AssertionError("marshal CLI parser has no top-level command choices")


def _nested_choices(parser, dest: str) -> set[str]:
    for action in parser._actions:
        if getattr(action, "dest", None) == dest and action.choices:
            return set(action.choices)
    raise AssertionError(f"no nested {dest!r} choices on {parser.prog!r}")
