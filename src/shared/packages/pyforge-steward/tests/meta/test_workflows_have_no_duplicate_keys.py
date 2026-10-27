"""Every workflow under ``.github/workflows/`` loads with no duplicate mapping key.

GitHub Actions refuses a workflow file whose mapping repeats a key (``env:`` twice in one job, say) at startup:
the run is named after the file path, concludes ``failure`` with no jobs, and on a pull request the workflow is
simply absent. PyYAML's ``safe_load`` keeps the last value silently, so every local reader of these files -- the
preflight twin, the trigger map, the CI-surface render -- read the file as fine while GitHub did not (Wave 3 of
CAP-175, 2026-10-27: a second ``env:`` on the atlas job). This test loads each file with a loader that refuses a
repeated key at any depth.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.live_tree

REPO_ROOT = Path(__file__).resolve().parents[6]
WORKFLOWS = sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml"))


class _NoDuplicateKeys(yaml.SafeLoader):
    """``safe_load`` that raises on a repeated mapping key instead of keeping the last value."""


def _construct_mapping(loader: yaml.SafeLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    seen: dict[object, int] = {}
    for key_node, _value in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.YAMLError(
                f"duplicate key {key!r} at line {key_node.start_mark.line + 1} (first at line {seen[key] + 1})"
            )
        seen[key] = key_node.start_mark.line
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


_NoDuplicateKeys.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def test_there_are_workflows_to_check() -> None:
    assert len(WORKFLOWS) >= 10, [p.name for p in WORKFLOWS]


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_a_workflow_repeats_no_mapping_key(path: Path) -> None:
    yaml.load(path.read_text(encoding="utf-8"), Loader=_NoDuplicateKeys)  # noqa: S506 -- a SafeLoader subclass


def test_the_loader_refuses_a_repeated_key() -> None:
    with pytest.raises(yaml.YAMLError, match="duplicate key 'env'"):
        yaml.load("jobs:\n  a:\n    env:\n      X: 1\n    env:\n      Y: 2\n", Loader=_NoDuplicateKeys)  # noqa: S506
