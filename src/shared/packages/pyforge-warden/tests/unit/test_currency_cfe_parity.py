"""Unit test -- the bundled LTS registry matches the CFE canonical source.

Split out of ``test_currency.py`` by Story 27.1 (a relay of
``spec-pyforge-steward:CAP-175``): the canonical registry lives in the
conda-forge-expert skill, outside this package, so the check runs in the
live-tree half. There a missing canonical file is a failure, not a skip: the
half runs only where the tree is, and a guard that skips when its input is
absent cannot fire (the audit's hollow test; CAP-18's proof)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from pyforge.warden.currency import _load_registry

pytestmark = pytest.mark.live_tree

_CANONICAL_REGISTRY = (
    Path(__file__).resolve().parents[6] / ".claude" / "skills" / "conda-forge-expert" / "data" / "lts-registry.yaml"
)


def test_bundled_registry_matches_the_cfe_canonical_source():
    """The bundled registry is regenerated from the CFE canonical source
    (registry header contract): the parsed DATA must stay equal -- only the
    bundled header comment block may differ (review finding, 2026-07-23).
    The canonical file is not part of the installed package; this module is
    marked ``live_tree`` and runs in the repository's live-tree half."""
    assert _CANONICAL_REGISTRY.is_file(), f"the CFE canonical registry is missing at {_CANONICAL_REGISTRY}"
    canonical_doc = yaml.safe_load(_CANONICAL_REGISTRY.read_text(encoding="utf-8"))
    assert canonical_doc == _load_registry(), (
        "bundled data/lts-registry.yaml drifted from the CFE canonical "
        "source -- re-copy it (data verbatim; keep the bundled header "
        "comment block)"
    )
