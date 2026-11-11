"""Story 86.5's code-linkage verify, read against the live planning tree.

Story 116.1 (spec-pyforge-marshal:CAP-305): the one ``test_chain_regen.py`` test that reads the tracked tree
moved here, marked ``live_tree``; it fails, never skips, when the planning tree it reads is absent. Every other
chain-regeneration test stays in ``test_chain_regen.py``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pyforge.marshal.core.chain_regen import verify_code_linkage

pytestmark = pytest.mark.live_tree

_REPO_ROOT = Path(__file__).resolve().parents[6]
_DETAIL = re.compile(r"^read-only verify: (\d+) spec cite\(s\); (\d+) missing(?:: (.+))?$")


def test_code_linkage_on_the_live_tree_names_only_story_spec_ids_and_completes():
    """The live tree: marshal's verify completes, and each missing cite it counts is named."""
    epics = _REPO_ROOT / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts" / "epics.md"
    assert epics.is_file(), f"live planning tree not present: {epics}"
    outcome = verify_code_linkage(_REPO_ROOT, "pyforge-marshal")
    assert outcome.status == "complete"
    match = _DETAIL.match(outcome.detail)
    assert match is not None, outcome.detail
    named = match.group(3).split(", ") if match.group(3) else []
    assert len(named) == int(match.group(2))
    assert all(re.match(r"^spec-\d{1,3}-\d{1,3}(?:-|$)", cite) for cite in named), named
    assert "spec-surface" not in outcome.detail
