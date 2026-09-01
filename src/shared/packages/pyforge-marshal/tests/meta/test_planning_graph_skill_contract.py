"""Meta test -- Story 28.9's AC wiring: step-01 calls what marshal ships."""

from __future__ import annotations

from pathlib import Path

import pytest

import pyforge.marshal
from pyforge.marshal.cli.main import _build_parser
from pyforge.marshal.core import planning_graph as planning
from pyforge.marshal.core.findings import REGISTERED_CODES
from pyforge.marshal.core.verdict import Verdict, classify

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
REPO_ROOT = Path(_PACKAGE_FILE).resolve().parents[7]
SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "bmad-build-auto"
STEP_01 = SKILL_DIR / "step-01-clarify-and-route.md"


def _read(path: Path) -> str:
    if not path.is_file():
        pytest.skip(f"repo-level skill file not present: {path}")
    return path.read_text(encoding="utf-8")


class TestPlanningGraphSkillContract:
    def test_step_01_calls_the_retrieve_verb_marshal_registers(self):
        assert "marshal context retrieve" in _read(STEP_01)
        choices = _top_level_choices()
        assert "context" in choices
        assert "retrieve" in _nested_choices(choices["context"], "context_command")

    def test_step_01_reads_the_modes_marshal_emits(self):
        text = _read(STEP_01)
        assert planning.MODE_GRAPH in text
        assert planning.MODE_EPIC_CONTEXT_FALLBACK in text

    def test_step_01_treats_plan_findings_as_advisory(self):
        assert "MRS-PLAN-*" in _read(STEP_01)
        plan_codes = {code for code in REGISTERED_CODES if code.startswith("MRS-PLAN-")}
        assert plan_codes == {"MRS-PLAN-001"}
        assert classify("MRS-PLAN-001") is Verdict.WARN


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
