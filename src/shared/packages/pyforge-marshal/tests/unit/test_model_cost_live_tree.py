"""Story 28.10 (CAP-11) -- the declared model-cost catalog, read from the tracked marshal-policy.toml.

Story 116.1 (spec-pyforge-marshal:CAP-305): the one ``test_model_cost.py`` test that reads the tracked tree moved
here, marked ``live_tree``; it fails, never skips, when the policy file it reads is absent. Every other model-cost
test stays in ``test_model_cost.py``.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from pyforge.marshal.core import policy
from pyforge.marshal.core.model_cost import catalog_declared

pytestmark = pytest.mark.live_tree


def test_marshal_policy_toml_seed_catalog_parses():
    repo_root = Path(__file__).resolve().parents[6]
    policy_path = repo_root / "_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml"
    assert policy_path.is_file(), f"marshal-policy.toml not present in this checkout: {policy_path}"

    with open(policy_path, "rb") as handle:
        data = tomllib.load(handle)
    catalog = data.get("model_cost_catalog")
    assert catalog is not None
    assert catalog_declared(catalog)
    effective, findings = policy.compose(
        project_slug="pyforge-marshal",
        project={"model_cost_catalog": catalog},
        flags={},
    )
    assert not findings
    assert catalog_declared(effective.model_cost_catalog.value)
