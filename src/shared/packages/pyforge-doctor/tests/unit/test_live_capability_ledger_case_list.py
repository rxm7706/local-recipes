"""Story 56.2 -- the case-list reader's live proof (``spec-foundry-regenerate-not-fold:CAP-1``'s 54.1 list).

``parse_case_list_ids`` reads the first column of steward's ``case-list.md``; this module proves it on the
repository's own file, read through an explicit path (no repository root is handed to a gather). Every other
capability-ledger test builds its own tree and runs in the package half (``test_capability_ledger.py``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.doctor.sources.capability_ledger import parse_case_list_ids

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


def test_parse_case_list_ids_from_54_1_surface():
    repo = Path(__file__).resolve().parents[6]
    text = (
        repo / "_bmad-output/projects/pyforge-steward/planning-artifacts/"
        "specs/spec-foundry-regenerate-not-fold/case-list.md"
    ).read_text(encoding="utf-8")
    ids = parse_case_list_ids(text)
    assert "k-core-cutover-default" in ids
    assert "k-steward-help" in ids
    assert "k-marshal-no-sysexit" in ids
