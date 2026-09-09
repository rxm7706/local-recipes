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


# --- run-line rendering: trailing member descriptions (2026-09-09) -----------
#
# The descriptions live in suite-members.yaml, NOT in the GENERATED block: a
# comment hand-added between the markers is wiped by the next regeneration.
# These pin the emit contract so that cannot silently regress.


def _pin(mod, name, floor, *, description="", urls=()):
    return mod.MemberPin(
        name=name,
        floor=floor,
        registry="github",
        upstream=None,
        source="recipe-floor",
        description=description,
        urls=tuple(urls),
    )


def test_member_comment_joins_description_and_urls(load_module):
    mod = load_module("bmad_suite_metapackage.py")
    pin = _pin(mod, "bmad-loop", "0.11.1", description="Does a thing.",
               urls=["https://example.invalid/a", "https://example.invalid/b"])
    assert mod._member_comment(pin) == (
        "  # Does a thing. # https://example.invalid/a # https://example.invalid/b"
    )


def test_member_without_description_or_urls_emits_no_comment(load_module):
    mod = load_module("bmad_suite_metapackage.py")
    assert mod._member_comment(_pin(mod, "bmad-loop", "0.11.1")) == ""
    lines = mod._format_run_lines([_pin(mod, "bmad-loop", "0.11.1")])
    # No trailing whitespace and no bare "#" when there is nothing to say.
    assert lines == ["    - bmad-loop >=0.11.1"]


def test_comments_align_to_one_column_including_selector_nested(load_module):
    mod = load_module("bmad_suite_metapackage.py")
    lines = mod._format_run_lines([
        _pin(mod, "bmad-loop", "0.11.1", description="Short.", urls=[]),
        _pin(mod, "bmad-method-test-architecture-enterprise", "1.25.0",
             description="Long name.", urls=[]),
        _pin(mod, "mybmad-dashboard", "0.1.0.dev0", description="Nested.", urls=[]),
    ])
    commented = [ln for ln in lines if "#" in ln]
    assert len(commented) == 3
    columns = {ln.index("#") for ln in commented}
    # One shared absolute column, so the block reads as a table -- and the
    # selector-nested member (deeper indent) still lines up with the rest.
    assert len(columns) == 1
    assert "    - if: linux or osx" in lines and "      then:" in lines


def test_rendered_comment_is_a_yaml_comment_not_part_of_the_spec(load_module):
    """The pin conda sees must stay `name >=version` -- never the comment text."""
    mod = load_module("bmad_suite_metapackage.py")
    lines = mod._format_run_lines([
        _pin(mod, "bmad-method", "6.12.0", description='"Quoted" - dashes — and #hashes',
             urls=["https://example.invalid/x"]),
    ])
    doc = yaml.safe_load("requirements:\n  run:\n" + "\n".join(lines) + "\n")
    assert doc["requirements"]["run"] == ["bmad-method >=6.12.0"]


def test_existing_pin_parser_survives_trailing_comments(load_module):
    """_parse_existing_pins must still read the floor past a trailing comment."""
    mod = load_module("bmad_suite_metapackage.py")
    lines = mod._format_run_lines([
        _pin(mod, "bmad-eval-quality", "1.3.0", description="Desc.",
             urls=["https://example.invalid/e"]),
    ])
    text = (
        "  # GENERATED-BEGIN: suite-run-requirements\n"
        "  run:\n" + "\n".join(lines) + "\n"
        "  # GENERATED-END: suite-run-requirements\n"
    )
    assert mod._parse_existing_pins(text) == {"bmad-eval-quality": "1.3.0"}
