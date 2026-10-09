"""Meta-test: BMAD flag mandates live in the correct override tables (Story 74.3).

Parses `_bmad/custom/bmad-{spec,build,build-auto,tea}.toml`, asserts each mandate sits under
the table its skill's `customize.toml` declares, and asserts no leaf key collides with
`_bmad/custom/config.toml` at a different path (render_skill.py's ambiguous-config HALT).
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[6]

_CUSTOM = REPO_ROOT / "_bmad" / "custom"
_BUILDER_SNIPPET = "Feature-flag governance (Builder)"
_ARCHITECT_SNIPPET = "Feature-flag governance (Architect)"
_TEA_SNIPPET = "Feature-flag governance (TEA)"


def _load(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _find_scalar_leaf_paths(data: dict[str, Any], *, prefix: str = "") -> dict[str, list[str]]:
    """Map each scalar leaf key to the dotted paths where it appears."""
    out: dict[str, list[str]] = {}

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                child = f"{path}.{key}" if path else key
                if key == "agents" and not path:
                    continue
                walk(value, child)
        elif isinstance(node, list):
            return
        else:
            out.setdefault(path.rsplit(".", 1)[-1], []).append(path)

    walk(data, prefix)
    return out


def _facts_contain(table: dict[str, Any], snippet: str) -> bool:
    facts = table.get("persistent_facts")
    if not isinstance(facts, list):
        return False
    return any(isinstance(entry, str) and snippet in entry for entry in facts)


def _validate_mandate_tables(
    spec: dict[str, Any], build: dict[str, Any], auto: dict[str, Any], tea: dict[str, Any]
) -> None:
    assert "workflow" in spec and _facts_contain(spec["workflow"], _ARCHITECT_SNIPPET)
    assert "workflow" in build and _facts_contain(build["workflow"], _BUILDER_SNIPPET)
    layers = build.get("workflow", {}).get("review_layers")
    assert isinstance(layers, list) and layers, "bmad-build.toml must carry a review layer"
    flag_layer = next(
        (layer for layer in layers if isinstance(layer, dict) and layer.get("id") == "flag-mandate"), None
    )
    assert flag_layer is not None, "bmad-build.toml must include [[workflow.review_layers]] id=flag-mandate"
    assert "workflow" in auto and _facts_contain(auto["workflow"], _BUILDER_SNIPPET)
    assert "agent" in tea and _facts_contain(tea["agent"], _TEA_SNIPPET)
    assert "workflow" not in tea or not _facts_contain(tea.get("workflow", {}), _TEA_SNIPPET)


def _validate_no_config_collision(*override_paths: Path, config_path: Path) -> None:
    config_leaves = _find_scalar_leaf_paths(_load(config_path))
    for path in override_paths:
        override_leaves = _find_scalar_leaf_paths(_load(path))
        for key, override_paths_list in override_leaves.items():
            if key not in config_leaves:
                continue
            config_paths_list = config_leaves[key]
            for op in override_paths_list:
                for cp in config_paths_list:
                    if op != cp:
                        raise AssertionError(
                            f"ambiguous config value: key {key!r} at {op!r} in {path.name} "
                            f"also at {cp!r} in config.toml"
                        )


def test_flag_mandates_sit_under_declared_tables_and_do_not_collide_with_config() -> None:
    spec_path = _CUSTOM / "bmad-spec.toml"
    build_path = _CUSTOM / "bmad-build.toml"
    auto_path = _CUSTOM / "bmad-build-auto.toml"
    tea_path = _CUSTOM / "bmad-tea.toml"
    config_path = _CUSTOM / "config.toml"

    for path in (spec_path, build_path, auto_path, tea_path, config_path):
        assert path.is_file(), f"missing override layer: {path}"

    _validate_mandate_tables(
        _load(spec_path),
        _load(build_path),
        _load(auto_path),
        _load(tea_path),
    )
    _validate_no_config_collision(spec_path, build_path, auto_path, tea_path, config_path=config_path)


def test_builder_mandate_under_agent_in_bmad_build_fails_validation() -> None:
    build = _load(_CUSTOM / "bmad-build.toml")
    workflow = dict(build.get("workflow", {}))
    agent_facts = list(build.get("agent", {}).get("persistent_facts") or [])
    facts = workflow.pop("persistent_facts", [])
    agent_facts.extend(facts)
    mutated = {**build, "workflow": workflow, "agent": {"persistent_facts": agent_facts}}
    with pytest.raises(AssertionError):
        _validate_mandate_tables(
            _load(_CUSTOM / "bmad-spec.toml"),
            mutated,
            _load(_CUSTOM / "bmad-build-auto.toml"),
            _load(_CUSTOM / "bmad-tea.toml"),
        )
