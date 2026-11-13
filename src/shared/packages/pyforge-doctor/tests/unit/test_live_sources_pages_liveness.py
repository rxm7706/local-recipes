"""Story 58.2 (spec-pyforge-doctor:CAP-97) -- the live-tree half of ``test_sources_pages_liveness.py``.

The pin reads the repository's own ``.github/workflows/pages.yml``: the source's published inputs are that deploy's
trigger filter less the named exclusions. The named exclusions are tracked paths, so their mutation twin travels with
the pin (one definition of the set). Every test that drives a recorded fixture stays in the package half
(``test_sources_pages_liveness.py``).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from pyforge.doctor.sources import pages_liveness

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree

#: Story 48.3: on pages.yml's filter, these build or deploy the site and publish nothing (Story 48.2's
#: change log); every other filter entry is a published input.
_NOT_PUBLISHED = frozenset(
    {
        ".github/workflows/pages.yml",
        "scripts/pages_*.py",
        "src/shared/packages/pyforge-steward/src/pyforge/steward/pages.py",
        "src/shared/packages/pyforge-steward/src/pyforge/steward/marketplace_pages.py",
        "src/shared/packages/pyforge-herald/src/pyforge/herald/pages_env.py",
    }
)


def _pages_push_paths() -> list[str]:
    pages_workflow = Path(__file__).resolve().parents[6] / ".github" / "workflows" / "pages.yml"
    data = yaml.safe_load(pages_workflow.read_text(encoding="utf-8"))
    # PyYAML (YAML 1.1) reads the bare ``on:`` key as the boolean True.
    triggers = data.get("on", data.get(True))
    paths = triggers["push"]["paths"]
    assert isinstance(paths, list) and paths, f"{pages_workflow} carries no on.push.paths filter"
    return [str(path) for path in paths]


def test_the_published_inputs_are_pages_yml_s_filter_less_the_named_exclusions() -> None:
    """48.3 AC1: the source's inputs are the deploy's own trigger filter (each trailing ``/**``
    dropped) less what builds or deploys the site and publishes nothing; a filter change is
    steward's, and this pin names what the source must follow."""
    filter_paths = [path.removesuffix("/**") for path in _pages_push_paths()]
    missing_exclusions = sorted(_NOT_PUBLISHED - set(filter_paths))
    assert not missing_exclusions, f"named exclusions no longer on pages.yml's filter: {missing_exclusions}"
    expected = set(filter_paths) - _NOT_PUBLISHED
    inputs = pages_liveness.PUBLISHED_INPUTS
    duplicates = sorted({path for path in inputs if inputs.count(path) > 1})
    assert not duplicates, f"PUBLISHED_INPUTS repeats {duplicates}"
    missing_from_source = sorted(expected - set(inputs))
    not_on_filter = sorted(set(inputs) - expected)
    assert not missing_from_source and not not_on_filter, (
        f"PUBLISHED_INPUTS lacks pages.yml filter paths {missing_from_source}; "
        f"PUBLISHED_INPUTS names paths not on the filter (or excluded) {not_on_filter}"
    )


def test_mutation_no_excluded_path_is_a_published_input() -> None:
    """48.3 AC6: adding an excluded path (``scripts/pages_*.py``) to the inputs fails here and in the
    pin above: a build-script edit publishes nothing new."""
    assert not set(pages_liveness.PUBLISHED_INPUTS) & _NOT_PUBLISHED
