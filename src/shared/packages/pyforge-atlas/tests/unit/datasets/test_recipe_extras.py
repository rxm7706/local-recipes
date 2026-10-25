"""Story 37.8 — the local recipes' conda-forge-expert stamps."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pyforge.atlas.datasets import RecipeExtrasDataset
from pyforge.atlas.datasets.recipe_extras import COLUMNS


def _recipe(root: Path, name: str, text: str) -> None:
    (root / name).mkdir(parents=True)
    (root / name / "recipe.yaml").write_text(text, encoding="utf-8")


def test_each_recipe_gives_its_stamps(tmp_path):
    _recipe(
        tmp_path,
        "b-dir",
        "package:\n  name: b-pkg\nextra:\n  cfe-on-conda-forge-status: pending-review\n"
        "  cfe-upstream-registry: pypi\n  cfe-upstream-name: B_Pkg\n",
    )
    _recipe(tmp_path, "a-dir", "package:\n  name: a\nextra:\n  cfe-conda-name: a-conda\n")
    _recipe(tmp_path, "c-dir", "about: {}\n")
    (tmp_path / "meta-only").mkdir()
    (tmp_path / "meta-only" / "meta.yaml").write_text("package: {name: m}\n", encoding="utf-8")
    frame = RecipeExtrasDataset(filepath=str(tmp_path)).load()
    assert list(frame.columns) == COLUMNS
    rows = {r["dir_name"]: r for r in frame.to_dict("records")}
    assert set(rows) == {"a-dir", "b-dir", "c-dir"}
    assert rows["a-dir"]["conda_name"] == "a-conda"
    assert rows["b-dir"]["status"] == "pending-review"
    assert rows["b-dir"]["upstream_registry"] == "pypi"
    assert rows["b-dir"]["upstream_name"] == "B_Pkg"
    assert rows["c-dir"]["conda_name"] == "c-dir"  # no name anywhere: the directory


def test_an_unparseable_recipe_is_a_parse_error_row(tmp_path):
    _recipe(tmp_path, "bad", "package: [unclosed\n")
    row = RecipeExtrasDataset(filepath=str(tmp_path)).load().to_dict("records")[0]
    assert row["parse_error"] is True or bool(row["parse_error"])
    assert row["status"] is None


def test_a_missing_tree_gives_an_empty_frame(tmp_path):
    frame = RecipeExtrasDataset(filepath=str(tmp_path / "nope")).load()
    assert frame.empty and list(frame.columns) == COLUMNS


def test_the_dataset_is_read_only(tmp_path):
    with pytest.raises(Exception, match="read-only"):
        RecipeExtrasDataset(filepath=str(tmp_path)).save(pd.DataFrame())
