"""``marshal factory dispatch``'s policy composition, read against the tracked marshal-policy.toml.

Story 116.1 (spec-pyforge-marshal:CAP-305): the one ``test_dispatch.py`` test that reads the tracked tree moved
here, marked ``live_tree``; it fails, never skips, when the policy file it reads is absent. Every other dispatch
test stays in ``test_dispatch.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.marshal.cli.dispatch import _compose_policy
from pyforge.marshal.core import policy

pytestmark = pytest.mark.live_tree


def test_compose_policy_on_real_repo_enables_all_context_layers_for_dispatch() -> None:
    """Story 33.2 (CAP-1): factory dispatch reads the tracked marshal-policy.toml
    and resolves all six context layers enabled via the single composition site.

    Story 46.4: pyforge-marshal's own marshal-policy.toml no longer declares a
    `[context]` block at all -- the 4 harness-agnostic layers now come from
    the repo-default `_bmad-output/policy-defaults.toml`, and `wire`'s value
    passes through `resolve_context_layers` as the raw `"auto"` tri-state
    (unresolved at this composition-time call site -- no harness profile is
    in scope here yet)."""
    repo_root = Path(__file__).resolve().parents[6]
    policy_path = repo_root / "_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml"
    assert policy_path.is_file(), f"marshal-policy.toml not present in this checkout: {policy_path}"

    effective = _compose_policy("pyforge-marshal")
    resolved = policy.resolve_context_layers(effective)
    assert set(resolved) == set(policy.CONTEXT_LAYER_NAMES)
    for layer in policy.CONTEXT_LAYER_NAMES:
        if layer == "wire":
            assert resolved[layer] == {"enabled": "auto", "aggressiveness": "medium"}
            continue
        assert resolved[layer] == {"enabled": True, "aggressiveness": "medium"}
