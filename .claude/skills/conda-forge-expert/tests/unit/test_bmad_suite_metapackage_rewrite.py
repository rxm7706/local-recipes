"""Unit tests for bmad_suite_metapackage.py's `_rewrite_recipe` splice.

The generator rewrites the `run:` block between the GENERATED-BEGIN /
GENERATED-END markers in ``recipes/bmad-suite/recipe.yaml``. Two defects lived
here undetected because nothing tested the splice:

1. The BEGIN..END regex captured the OLD BODY in group 1 and the replacement
   re-emitted ``\\1`` before the new block, so every run APPENDED a second
   ``run:`` key under ``requirements:`` instead of replacing the first. YAML
   tolerates the duplicate (last-wins on ``safe_load``), so the corruption is
   silent — the recipe still "parses" while carrying two conflicting pin sets.
2. The ``context.version`` regex ended ``\\s*$`` under MULTILINE, which
   swallows the newline(s) after the match and deleted the blank line
   separating ``context:`` from ``package:``.

Both were found on 2026-09-02 while bumping the three stale suite members
(bmad-builder 2.2.2 / CIS 0.3.2 / TEA 1.24.0).
"""
from __future__ import annotations

import re

import pytest
import yaml

RECIPE = """\
# yaml-language-server: $schema=https://example.invalid/schema.json
schema_version: 1

context:
  name: bmad-suite
  # CalVer refresh stamp (unpadded) — bumped by generate-bmad-suite when pins change.
  version: "2026.9.1"

package:
  name: ${{ name }}
  version: ${{ version }}

build:
  number: 0
  noarch: generic

requirements:
  # GENERATED-BEGIN: suite-run-requirements (bmad_suite_metapackage.py — do not edit by hand)
  run:
    - bmad-builder >=2.2.1
    - if: linux or osx
      then:
        - mybmad-dashboard >=0.1.0.dev0
  # GENERATED-END: suite-run-requirements

tests:
  - script:
      - bmad-loop --version
"""

NEW_RUN_LINES = [
    "    - bmad-builder >=2.2.2",
    "    - if: linux or osx",
    "      then:",
    "        - mybmad-dashboard >=0.1.0.dev0",
]


@pytest.fixture
def rewrite(load_module, tmp_path):
    mod = load_module("bmad_suite_metapackage.py")
    path = tmp_path / "recipe.yaml"

    def _run(text: str, *, version: str = "2026.9.2") -> str:
        path.write_text(text, encoding="utf-8")
        _old, new = mod._rewrite_recipe(
            path, run_lines=NEW_RUN_LINES, version=version
        )
        return new

    return _run


def test_replaces_run_block_instead_of_appending(rewrite):
    """The stale pin set must be GONE, not merely followed by a fresh one."""
    out = rewrite(RECIPE)
    assert out.count("run:") == 1, f"duplicate run: key emitted:\n{out}"
    assert "bmad-builder >=2.2.1" not in out
    assert "bmad-builder >=2.2.2" in out


def test_result_has_exactly_one_run_key_after_parsing(rewrite):
    """`safe_load` last-wins hides a duplicate key — assert on the text too."""
    out = rewrite(RECIPE)
    assert len(re.findall(r"^  run:$", out, re.MULTILINE)) == 1
    doc = yaml.safe_load(out)
    assert doc["requirements"]["run"][0] == "bmad-builder >=2.2.2"


def test_preserves_do_not_edit_note_on_begin_marker(rewrite):
    """The BEGIN line's trailing note is load-bearing guidance — keep it."""
    out = rewrite(RECIPE)
    assert (
        "# GENERATED-BEGIN: suite-run-requirements "
        "(bmad_suite_metapackage.py — do not edit by hand)" in out
    )


def test_version_bump_keeps_the_blank_line_before_package(rewrite):
    """`\\s*$` under MULTILINE ate the separator newline; it must survive."""
    out = rewrite(RECIPE)
    assert 'version: "2026.9.2"\n\npackage:' in out
    assert 'version: "2026.9.1"' not in out


def test_rewrite_is_idempotent(rewrite):
    """Re-running over already-generated output must be a no-op."""
    once = rewrite(RECIPE)
    twice = rewrite(once)
    assert once == twice


def test_missing_markers_is_a_hard_error(rewrite):
    """Never silently no-op on a recipe that lost its markers."""
    with pytest.raises(SystemExit):
        rewrite(RECIPE.replace("# GENERATED-BEGIN: suite-run-requirements", "# nope"))
