"""Doctor Story 58.1 (spec-pyforge-doctor:CAP-97) -- the live-tree half of
``test_sources_chain_dreams_hygiene.py``.

These four tests run ``gather_dreams_hygiene`` over this repository's own
Dream tree, so they run in the station's live-tree half. Every other
dreams-hygiene test builds its own tree and stays in
``test_sources_chain_dreams_hygiene.py`` (the package half).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.doctor.sources import chain

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


def _require_repo_root() -> Path:
    """This repository's root, resolved when a test runs (never at import time)."""
    root = Path(__file__).resolve().parents[6]
    assert (root / ".claude").is_dir(), f"{root} is not the local-recipes checkout root (no .claude/)"
    return root


def test_living_unifying_strategy_has_no_historical_section_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: post-43.1 living Dream must not trip its own detector."""
    repo = Path(__file__).resolve().parents[6]
    monkeypatch.chdir(repo)
    findings = chain.gather_dreams_hygiene(repo)
    hist = [f for f in findings if f.check == "historical-section-too-long"]
    assert not any(f.evidence.get("subject") == "pyforge-unifying-strategy" for f in hist)


def test_live_tree_dream_readme_missing_count() -> None:
    """Measured live 2026-10-24: 0 -- doctor Story 30.4 gave every Dream file a
    README.md table row (64 lacked one on 2026-10-11, 65 on 2026-09-18, 67 on
    2026-09-12). A new Dream lands with its row; this test only tracks the
    live count."""
    repo_root = _require_repo_root()
    findings = chain.gather_dreams_hygiene(repo_root)
    missing = [f for f in findings if f.check == "dream-readme-missing"]
    assert len(missing) == 0


def test_live_tree_specified_spec_not_ready_count() -> None:
    """Measured live 2026-09-18: 0 ``specified`` Dreams whose covering Spec is
    not ``ready`` or beyond (was 3 on 2026-09-11 — those cleared)."""
    repo_root = _require_repo_root()
    findings = chain.gather_dreams_hygiene(repo_root)
    bad = [f for f in findings if f.check == "specified-spec-not-ready"]
    assert len(bad) == 0


def test_live_tree_kinship_wikilink_dead_count() -> None:
    """Measured live 2026-10-26: 0 -- doctor Story 51.1 moved the 158 archived
    Dreams to ``archive/docs/dreams/`` (spec-one-chain-per-station CAP-11) and a
    wikilink naming one now resolves there (``_archived_dream_slugs``); before
    that, doctor Story 30.4 retargeted each dead Kinship wikilink under
    ``docs/dreams/`` to the Dream that absorbed its target, or turned it into
    plain text or a plain link where no Dream did (0 on 2026-10-24; 32 on
    2026-10-04 after Story 41.3 repaired the 34 glued-opener Dreams; 30 on
    2026-09-25)."""
    repo_root = _require_repo_root()
    findings = chain.gather_dreams_hygiene(repo_root)
    dead = [f for f in findings if f.check == "kinship-wikilink-dead"]
    assert len(dead) == 0
