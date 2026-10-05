"""Strip-on-push (G60/G62) — feedstock-shaped fixture + submit path hook."""
from __future__ import annotations

from pathlib import Path

import pytest

from conftest import SKILL_DIR

_REPO_ROOT = SKILL_DIR.parent.parent.parent
_FIXTURE = (
    Path(__file__).resolve().parent.parent / "fixtures" / "ironcalc-feedstock-recipe.yaml"
)
_CFE_EXTRA_BLOCK = """
extra:
  recipe-maintainers:
    - rxm7706

#### CFE metadata AND comments
# CFE metadata
  cfe-conda-name: ironcalc
  cfe-upstream-registry: pypi
  cfe-on-conda-forge-status: confirmed-on-conda-forge
####
# CFE comments
# build:
#    # example parked note
####
"""


class TestCfePushStrip:
    @pytest.fixture
    def strip_mod(self, load_module):
        return load_module("_cfe_push_strip.py")

    def test_feedstock_fixture_has_no_cfe_keys(self):
        text = _FIXTURE.read_text(encoding="utf-8")
        assert "cfe-" not in text
        assert "schema_version: 1" in text
        assert "context:" in text

    def test_local_recipe_with_cfe_block_strips_clean(self, strip_mod):
        raw = (_REPO_ROOT / "recipes" / "ironcalc" / "recipe.yaml").read_text(
            encoding="utf-8"
        )
        assert "cfe-conda-name" in raw
        stripped = strip_mod.strip_recipe_yaml_for_push(raw)
        strip_mod.assert_no_cfe_metadata_surfaces(stripped)
        assert "cfe-" not in stripped
        assert stripped.lstrip().startswith("# yaml-language-server:")
        assert "schema_version: 1" in stripped
        assert "context:" in stripped
        assert "recipe-maintainers:" in stripped

    def test_feedstock_copy_plus_injected_cfe_strips_like_submit(self, strip_mod):
        published = _FIXTURE.read_text(encoding="utf-8")
        local_like = published.rstrip() + _CFE_EXTRA_BLOCK
        stripped = strip_mod.strip_recipe_yaml_for_push(local_like)
        strip_mod.assert_no_cfe_metadata_surfaces(stripped)
        assert "cfe-" not in stripped
        assert "schema_version: 1" in stripped

    def test_submit_pr_apply_push_strip_on_dest(self, load_module, tmp_path):
        mod = load_module("submit_pr.py")
        src = tmp_path / "src"
        src.mkdir()
        (src / "recipe.yaml").write_text(
            (_REPO_ROOT / "recipes" / "ironcalc" / "recipe.yaml").read_text(
                encoding="utf-8"
            ),
            encoding="utf-8",
        )
        dest = tmp_path / "dest"
        import shutil

        shutil.copytree(src, dest)
        mod.apply_push_strip_to_recipe_dir(dest)
        out = (dest / "recipe.yaml").read_text(encoding="utf-8")
        assert "cfe-" not in out
