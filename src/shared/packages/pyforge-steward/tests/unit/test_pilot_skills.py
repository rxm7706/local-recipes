"""Story 109.2 — the three pilot skills do not depend on the estate environment."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.steward.bootstrap import repo_root

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads docs/foundry/marketplace, so it runs in the
# station's live-tree half and fires on that tree, not on every edit of the package.
pytestmark = pytest.mark.live_tree

_SKILLS = Path("docs/foundry/marketplace/skills")
_PILOTS = ("mason/environment", "mason/package", "warden/scan")


def _texts() -> list[tuple[str, str]]:
    root = repo_root() / _SKILLS
    found: list[tuple[str, str]] = []
    for relative in _PILOTS:
        folder = root / relative
        for name in ("SKILL.md", "steps.md"):
            found.append((f"{relative}/{name}", (folder / name).read_text(encoding="utf-8")))
    return found


def test_each_pilot_has_a_skill_and_steps() -> None:
    names = [path for path, _text in _texts()]
    assert names == [
        "mason/environment/SKILL.md",
        "mason/environment/steps.md",
        "mason/package/SKILL.md",
        "mason/package/steps.md",
        "warden/scan/SKILL.md",
        "warden/scan/steps.md",
    ]


def test_pilot_skills_do_not_invoke_the_estate_environment() -> None:
    for path, text in _texts():
        assert "pixi run -e" not in text, path
        assert "pixi run --frozen -e" not in text, path


def test_pilot_skills_name_the_commands_that_were_verified() -> None:
    by_path = dict(_texts())
    environment = by_path["mason/environment/steps.md"]
    assert "conda-lock lock -f pyproject.toml --lockfile conda-lock.yml" in environment
    assert "env.lock" not in environment
    assert "--conda environment.yml" not in environment
    assert "conda-lock, version 4.0.2" in environment or "conda-lock` 4.0.2" in environment
    # AC3: the station check uses a temporary copy, and the runbook says so.
    assert "temporary copy of the lockfile" in environment
    package = by_path["mason/package/steps.md"]
    assert "pyproject-build --no-isolation" in package
    assert "pixi build --output-dir dist" in package
    # AC4: the two upload commands are named, and the reader is told not to run them.
    assert "twine upload" in package and "pixi upload" in package
    assert "Do not run `twine upload` or `pixi upload`" in package
    warden = by_path["warden/scan/steps.md"]
    assert "warden scan ." in warden
    assert "deptry" in warden
    assert "osv-scanner" in warden
    # AC5: the engines' output is not a warden verdict, in those words.
    assert "`deptry` and `osv-scanner` are not a warden verdict" in warden
    for path, text in _texts():
        # AC6: every file records the 404 and its date.
        assert "404" in text, path
        assert "2026-10-21" in text, path


def test_pilot_skills_read_without_the_station_source() -> None:
    """The review of 2026-10-28 (rows 1 and 7): a teammate's installed copy has no local-recipes checkout, so
    the files name an engine by its module, never by a bare source path, never as "this repo", and the verified
    versions live in ``steps.md`` alone."""
    for path, text in _texts():
        assert "engines/" not in text, path
        assert "this repo" not in text, path
        assert "paper skill card" not in text, path  # provenance moved to listing.yaml's header comment
    for relative in _PILOTS:
        skill = dict(_texts())[f"{relative}/SKILL.md"]
        for version in ("4.0.2", "1.6.1", "0.81.0", "7.0.0", "0.25.1", "2.4.0"):
            assert version not in skill, (relative, version)


def test_pilot_steps_install_the_published_tools_first() -> None:
    """The review of 2026-10-28 (rows 2, 5 and 6): a step 0 names each tool's install source and the version a
    fresh ``--version`` printed; a "Before you start" line names the unpublished packages and the gated steps
    before step 1; the pixi version is the one the host and ``pixi.lock`` agree on."""
    by_path = dict(_texts())
    for relative in _PILOTS:
        steps = by_path[f"{relative}/steps.md"]
        assert "## 0. Install the published tools" in steps, relative
        assert "**Before you start.**" in steps, relative
        assert steps.index("**Before you start.**") < steps.index("## 0."), relative
        assert steps.index("## 0.") < steps.index("## 1."), relative
    environment = by_path["mason/environment/steps.md"]
    assert "conda install -c conda-forge conda-lock" in environment
    assert "-f environment.yml" in environment  # one substitution per manifest the project holds
    package = by_path["mason/package/steps.md"]
    assert "conda install -c conda-forge python-build" in package
    assert "BackendUnavailable" in package
    assert "`pixi` 0.81.0" in package and "0.82.0" not in package
    warden = by_path["warden/scan/steps.md"]
    assert "conda install -c conda-forge deptry" in warden
    assert "conda install -c conda-forge osv-scanner" in warden
