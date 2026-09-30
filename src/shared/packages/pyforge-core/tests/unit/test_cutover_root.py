"""Story 44.12 — pyforge-core cutover_root reader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.core.cutover_root import (
    DEFAULT_CUTOVER_ROOT,
    CutoverRootError,
    read_cutover_root,
)


def _tree(tmp_path: Path, default: str = "local-recipes") -> Path:
    path = tmp_path / "flags.json"
    path.write_text(
        json.dumps(
            {
                "flags": {
                    "pyforge.cutover_root": {
                        "state": "ENABLED",
                        "variants": {
                            "local-recipes": "local-recipes",
                            "foundry": "foundry",
                        },
                        "defaultVariant": default,
                        # Story 76.2: a string flag has no ON variant, so its clock stays empty.
                        "metadata": {
                            "owner": "steward",
                            "story": "44-12-cutover-flag-and-replay-harness",
                            "created": "2026-09-13",
                            "on_everywhere": "",
                            "cleanup_by": "",
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    return path


def test_default_is_local_recipes(tmp_path: Path) -> None:
    assert read_cutover_root(_tree(tmp_path)) == DEFAULT_CUTOVER_ROOT


def test_foundry_variant(tmp_path: Path) -> None:
    assert read_cutover_root(_tree(tmp_path, "foundry")) == "foundry"


def test_unknown_variant_fails(tmp_path: Path) -> None:
    path = _tree(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["flags"]["pyforge.cutover_root"]["defaultVariant"] = "other"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CutoverRootError, match="unknown"):
        read_cutover_root(path)


def test_missing_flag_fails(tmp_path: Path) -> None:
    path = tmp_path / "flags.json"
    path.write_text(json.dumps({"flags": {}}), encoding="utf-8")
    with pytest.raises(CutoverRootError, match="missing"):
        read_cutover_root(path)


# --- Story 76.1: the reader composes the sibling overlay for the environment ----


def _overlay(tmp_path: Path, document: object) -> None:
    (tmp_path / "flag-overlays.json").write_text(json.dumps(document), encoding="utf-8")


def test_the_sibling_overlay_is_composed_for_the_current_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tree = _tree(tmp_path, "local-recipes")
    _overlay(
        tmp_path,
        {
            "dev": {"pyforge.cutover_root": "local-recipes"},
            "staging": {"pyforge.cutover_root": "foundry"},
            "production": {"pyforge.cutover_root": "local-recipes"},
        },
    )
    monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)
    assert read_cutover_root(tree) == "local-recipes"  # unset reads as dev
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "staging")
    assert read_cutover_root(tree) == "foundry"
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "production")
    assert read_cutover_root(tree) == "local-recipes"


def test_the_composed_reading_agrees_with_render(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from pyforge.core import flags

    tree = _tree(tmp_path, "local-recipes")
    _overlay(tmp_path, {"production": {"pyforge.cutover_root": "foundry"}})
    for environment in flags.ENVIRONMENTS:
        monkeypatch.setenv("PYFORGE_ENVIRONMENT", environment)
        rendered = json.loads(flags.render(environment, flags_path=tree))
        assert read_cutover_root(tree) == rendered["flags"]["pyforge.cutover_root"]["defaultVariant"]


def test_a_tree_without_a_sibling_overlay_reads_as_it_is(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tree = _tree(tmp_path, "foundry")
    for environment in ("dev", "staging", "production"):
        monkeypatch.setenv("PYFORGE_ENVIRONMENT", environment)
        assert read_cutover_root(tree) == "foundry"


def test_an_unknown_environment_is_a_named_cutover_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "qa")
    with pytest.raises(CutoverRootError, match="qa"):
        read_cutover_root(_tree(tmp_path))


@pytest.mark.parametrize(
    "document",
    [
        {"production": {"pyforge.nope": "foundry"}},
        {"production": {"pyforge.cutover_root": "maybe"}},
        {"production": {"pyforge.cutover_root": {"variants": {}}}},
        {"qa": {"pyforge.cutover_root": "foundry"}},
        [],
    ],
)
def test_a_bad_overlay_is_a_named_cutover_error(tmp_path: Path, document: object) -> None:
    tree = _tree(tmp_path)
    _overlay(tmp_path, document)
    with pytest.raises(CutoverRootError):
        read_cutover_root(tree)
