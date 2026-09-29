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
