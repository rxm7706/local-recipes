"""Doctor Story 58.1 (spec-pyforge-doctor:CAP-97) -- the live-tree half of
``test_sources_one_chain_fold_complete.py``.

These tests run the fold-complete gather and the CLI on this checkout and read
its committed baseline (the "today's main" leg), so they run in the station's
live-tree half.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_sources_one_chain_fold_complete import _fails

from pyforge.doctor.models import DoctorStatus
from pyforge.doctor.sources import __main__ as dispatch
from pyforge.doctor.sources import one_chain

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


def _live_root() -> Path:
    """This repository's root, resolved when a test runs (never at import time)."""
    root = Path(__file__).resolve().parents[6]
    assert (root / ".claude").is_dir(), f"{root} is not the local-recipes checkout root (no .claude/)"
    return root


# --- live tree (conformance legs) --------------------------------------------


def test_live_baseline_names_the_seven_non_fold_paths() -> None:
    root = _live_root()
    data = json.loads((root / one_chain.FOLD_COMPLETE_BASELINE_REL).read_text(encoding="utf-8"))
    assert "$comment" in data
    assert data["paths"] == sorted(data["paths"])
    assert set(data["paths"]) <= {
        "archive/docs/dreams/deckcraft.md",
        "archive/docs/dreams/design-code-bridge.md",
        "archive/docs/dreams/herald-pitch-deck-family-expansion.md",
        "archive/docs/dreams/modernist-identity.md",
        "archive/docs/dreams/pyforge-genesis.md",
        "archive/docs/dreams/pyforge-unifying-strategy-2026-08-23-topology.md",
        "archive/docs/dreams/video-scripts.md",
    }  # the baseline only ever shrinks


def test_live_tree_has_no_fail_and_no_stray_baseline_warn() -> None:
    root = _live_root()
    findings = one_chain.gather_fold_complete(root)
    assert not _fails(findings), [f.message for f in _fails(findings)]
    assert not any(f.check == "fold-complete-no-baseline" for f in findings)
    # the only WARN the live tree may carry is the migration countdown
    assert {f.check for f in findings if f.status is DoctorStatus.WARN} <= {"fold-complete-archived-in-live-tree"}


def test_live_cli_exits_0(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(_live_root())
    assert dispatch.main(["fold-complete"]) == 0
