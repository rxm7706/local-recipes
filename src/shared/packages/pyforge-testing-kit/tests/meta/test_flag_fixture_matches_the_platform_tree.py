"""The flag fixture's tree has the platform flag tree's shape (marshal Story 74.1, spec-feature-flag-governance CAP-4).

Live-tree (Story 118.1, spec-pyforge-testing-charter:CAP-7): this comparison reads ``src/platform/config/flags.json``,
outside the kit, so it moved here from ``tests/unit/test_flags.py``, which keeps the fixture's own shape assertions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.testing_kit import flagd_tree

pytestmark = pytest.mark.live_tree

_KEY = "pyforge.example.thing"
# tests/meta -> tests -> pyforge-testing-kit -> packages -> shared -> src -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[6]


def test_flagd_tree_carries_the_platform_trees_keys(tmp_path: Path) -> None:
    written = json.loads(flagd_tree(tmp_path, {_KEY: "off"}).read_text(encoding="utf-8"))
    platform = json.loads((_REPO_ROOT / "src/platform/config/flags.json").read_text(encoding="utf-8"))
    assert platform["flags"], "the platform tree carries no flag to compare the written shape against"
    # The evaluation shape must match. The platform tree's `metadata` block is its governance clock
    # (Story 76.2), checked only when a tree is composed with a flag-overlays.json beside it, which a
    # flagd_tree never has -- so it is the one platform key a test tree does not carry.
    platform_flag = next(iter(platform["flags"].values()))
    assert set(written["flags"][_KEY]) == set(platform_flag) - {"metadata"}
    assert set(written) == set(platform)
