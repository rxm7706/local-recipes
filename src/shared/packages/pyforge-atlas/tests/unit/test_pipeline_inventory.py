"""README.md's pipeline inventory is what ``find_pipelines()`` actually discovers.

Story 27.3, closing DW-FU-20-3-2. README's Status line claimed "8 Kedro pipelines
live" and named eight while eleven were registered: ``artifactory_downloads``,
``query_plane_cache`` and ``semantic_packages`` had been added with no doc edit and
nothing noticed. A hand-maintained inventory needs a gate or it rots again.
"""

from __future__ import annotations

import re
from pathlib import Path

from kedro.framework.project import configure_project

from pyforge.atlas.pipeline_registry import register_pipelines

README = Path(__file__).resolve().parents[2] / "README.md"

# "**Status:** 11 Kedro pipelines live (`a`, `b`, ...)" -- the count and the names
# are parsed separately so a mismatch between THEM also reds.
_STATUS = re.compile(r"\*\*Status:\*\*\s+(\d+)\s+Kedro pipelines live\s+\(([^)]*)\)", re.DOTALL)


def _readme_inventory() -> tuple[int, set[str]]:
    match = _STATUS.search(README.read_text(encoding="utf-8"))
    assert match is not None, "README.md no longer carries a '**Status:** N Kedro pipelines live (...)' line"
    return int(match.group(1)), set(re.findall(r"`([a-z_]+)`", match.group(2)))


def _registered() -> set[str]:
    # register_pipelines() also exposes the "__default__" sum of every pipeline,
    # which is not a pipeline of its own.
    configure_project("pyforge.atlas")
    return {name for name in register_pipelines() if name != "__default__"}


def test_readme_names_every_registered_pipeline_and_no_others() -> None:
    _count, named = _readme_inventory()
    registered = _registered()
    assert named == registered, (
        f"README.md pipeline inventory has drifted -- missing: {sorted(registered - named)}; "
        f"stale: {sorted(named - registered)}"
    )


def test_the_readme_count_matches_the_names_it_lists() -> None:
    count, named = _readme_inventory()
    assert count == len(named)


def test_the_bootstrap_task_runs_a_documented_subset_not_the_whole_registry() -> None:
    """The bootstrap section deliberately runs eight of the eleven (it excludes the
    entry-scoped ``universal_sbom`` and the two downstream composition/cache
    pipelines). Pin that so "eight" there is not read as a drifted count."""
    text = README.read_text(encoding="utf-8")
    assert "Materializes eight self-contained pipelines" in text
    excluded = {"universal_sbom", "semantic_packages", "query_plane_cache"}
    assert excluded <= _registered()
    assert len(_registered() - excluded) == 8
