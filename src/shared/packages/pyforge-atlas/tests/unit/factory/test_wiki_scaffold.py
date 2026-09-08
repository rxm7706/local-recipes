"""Story H1 `kedro-test` gate — the Karpathy-wiki scaffold-layout invariants (FR-22(a), AD-22).

Proves: the three-stage tree materializes; the layout is the SINGLE owner of the stage names;
and the AD-22 write-boundary holds (no factory write can escape the wiki root)."""

from pathlib import Path

import pytest

from pyforge.atlas.factory import wiki
from pyforge.atlas.factory.wiki import WIKI_STAGES, WikiLayout, scaffold_wiki


def test_stage_names_are_the_three_spec_stages_in_order():
    # § 7.4: raw -> compiled -> outputs, in fixed pipeline order.
    assert WIKI_STAGES == ("raw", "compiled", "outputs")


def test_scaffold_creates_the_three_stage_tree(tmp_path: Path):
    layout = scaffold_wiki(tmp_path / "wiki")
    for stage in WIKI_STAGES:
        assert (tmp_path / "wiki" / stage).is_dir()
    # scaffold_wiki returns the layout whose stage_dir agrees with what it created.
    for stage in WIKI_STAGES:
        assert layout.stage_dir(stage) == tmp_path / "wiki" / stage


def test_scaffold_is_idempotent_and_non_destructive(tmp_path: Path):
    layout = scaffold_wiki(tmp_path / "wiki")
    # A pre-existing file in a stage must survive a re-scaffold (AD-22: factory only ADDS).
    marker = layout.stage_path("compiled", "keep.md")
    marker.write_text("keep me", encoding="utf-8")
    scaffold_wiki(tmp_path / "wiki")  # re-run
    assert marker.read_text(encoding="utf-8") == "keep me"


def test_stage_dir_rejects_unknown_stage(tmp_path: Path):
    layout = WikiLayout(tmp_path)
    with pytest.raises(ValueError):
        layout.stage_dir("published")  # not one of the three


def test_stage_path_addresses_files_inside_a_stage(tmp_path: Path):
    layout = scaffold_wiki(tmp_path)
    p = layout.stage_path("outputs", "reports/2026.md")
    assert p == tmp_path / "outputs" / "reports" / "2026.md"


@pytest.mark.parametrize(
    "bad",
    [
        "../escape.md",
        "reports/../../escape.md",
        "/abs/escape.md",
        "..",
        "",
    ],
)
def test_stage_path_refuses_escaping_the_wiki_root(tmp_path: Path, bad: str):
    # AD-22 write-boundary: a crafted document name must not let a wiki write land outside the
    # tree (the emitter._require_safe_name lesson applied to the factory).
    layout = WikiLayout(tmp_path)
    with pytest.raises(ValueError):
        layout.stage_path("raw", bad)


def test_layout_is_single_owner_of_stage_names():
    # No consumer re-lists the stage names: they come only from WIKI_STAGES. This test pins that
    # the module exposes exactly the contract other H-stories import.
    assert set(WIKI_STAGES) == {"raw", "compiled", "outputs"}
    assert hasattr(wiki, "WikiLayout") and hasattr(wiki, "scaffold_wiki")
