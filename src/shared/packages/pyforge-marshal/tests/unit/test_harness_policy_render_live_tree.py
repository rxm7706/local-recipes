"""The harness policy's convention layer, read against this checkout (Story 1.10).

Story 116.4 (spec-pyforge-marshal:CAP-305): the tree-read guard runs every package-half test off the tree (a working
directory outside the repository, ``cli/config.py`` anchored in a bare checkout), and these tests fail there:
each resolves ``conventional_project_policy_path`` through ``repo_root()`` and reads this repository's root
and the tracked pyforge-marshal ``marshal-policy.toml``.
They moved here, marked ``live_tree``; each fails, never skips, when what it reads is absent. Every other
test stays in ``test_harness_policy_render.py``, and this module imports the helpers both use from it by name.
"""

from __future__ import annotations

import tomllib

import pytest

from pyforge.marshal.adapters.harness_bmadloop import (
    _SURFACE_RECONCILE_COMMAND,
)

pytestmark = pytest.mark.live_tree


def test_conventional_project_policy_path_lands_on_the_repo_root(tmp_path):
    """An off-by-one in `repo_root()` resolves to `<repo>/src` and every
    convention lookup silently misses -- falling back to bare defaults whose
    `verify_commands` is EMPTY, i.e. no gate at all. Caught exactly that during
    implementation, hence this test."""
    from pyforge.marshal.cli import config as config_cli

    root = config_cli.repo_root()
    assert (root / "pixi.toml").is_file(), (
        f"repo_root() resolved to {root}, which has no pixi.toml -- the parent "
        "index is wrong and every project-policy lookup will miss"
    )
    p = config_cli.conventional_project_policy_path("pyforge-marshal")
    assert p == root / ("_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml")


def test_cli_writes_the_harness_policy_via_the_convention_layer(tmp_path):
    """The whole point: `marshal config --project <slug> --write-harness-policy
    <home>` must find the tracked layer by convention and write a policy carrying
    that project's OWN verify command -- with no --project-policy passed."""
    from pyforge.marshal.cli.main import main

    rc = main(
        [
            "config",
            "--project",
            "pyforge-marshal",
            "--write-harness-policy",
            str(tmp_path),
            "--format",
            "json",
        ]
    )
    assert rc == 0, "a clean composition must exit 0"

    written = tmp_path / ".bmad-loop" / "policy.toml"
    assert written.is_file(), "the CLI did not reach write_policy_toml"
    parsed = tomllib.loads(written.read_text(encoding="utf-8"))
    # Still an EXACT list, deliberately -- this assertion is the only thing standing
    # between a mis-composed layer and a run with no gate, so it is not loosened to a
    # membership check. The list grew to two on 2026-07-31 when marshal absorbed the
    # pyforge-genesis installer as epics 7-12: marshal's own suite cannot gate a story
    # that builds pyforge-genesis (it would pass regardless -- the same false green the
    # 2026-07-30 audit found on six loop homes running warden's suite), so the station
    # layer carries pyforge-deps-test as a second entry. That check discovers
    # src/shared/packages/pyforge-* BY GLOB, so it covers a package the day it lands.
    assert parsed["verify"]["commands"] == [
        "pixi run --frozen -e pyforge-marshal pyforge-marshal-test",
        "pixi run --frozen -e pyforge-ci pyforge-deps-test",
        # S-13.7 (2026-08-09): the repo-wide surface guard, APPENDED at render.
        # Kept inside the exact list on purpose -- this assertion is what stands
        # between a mis-composed layer and a run with no gate, and the guard is
        # now part of what "gated" means.
        _SURFACE_RECONCILE_COMMAND,
    ], "the project layer was not composed in -- verify would be EMPTY (no gate)"
    assert parsed["gates"]["mode"] == "none"
    assert parsed["limits"]["max_followup_reviews"] == 2
