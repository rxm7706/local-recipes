"""Story 17.2 — clean-container bootstrap sequence (conformance).

Proves the documented nothing → validate-fast path is a single composed
sequence with zero improvised steps between verbs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.steward.bootstrap import initrepo_steps, setup_steps
from pyforge.steward.cli import EXIT_OK, main


@pytest.fixture
def repo_root() -> Path:
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / "scripts" / "bmad-loop-worktree").is_file():
            return ancestor
    pytest.fail("could not locate local-recipes repo root from test file location")


def test_clean_container_sequence_is_fully_composed(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """init → setup → initrepo → validate-fast, each step delegated — no gaps."""
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "pyforge.steward.bootstrap.shutil.which",
        lambda name: f"/usr/bin/{name}",
    )
    monkeypatch.setattr(
        "pyforge.steward.bootstrap._tool_version",
        lambda _name, _path: "99.0.0",
    )
    monkeypatch.setattr(
        "pyforge.steward.bootstrap.materialize_environment",
        lambda _name, **_: None,
    )
    monkeypatch.setattr(
        "pyforge.steward.bootstrap._run_pre_commit_install",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "pyforge.steward.bootstrap.check_environment_sync",
        lambda **_: (True, ""),
    )
    monkeypatch.setattr(
        "pyforge.steward.bootstrap._run_steward_version",
        lambda **_: "steward 0.1.0",
    )

    assert main(["init"]) == EXIT_OK
    setup = setup_steps(dest=repo_root, url=None, env="local-recipes")
    assert all(step.ok for step in setup)
    onboard = initrepo_steps(root=repo_root, env="local-recipes")
    assert all(step.ok for step in onboard)
    assert main(["validate-fast"]) == EXIT_OK

    # Every phase names its steps — nothing silent between verbs.
    assert {step.name for step in setup} >= {"clone", "pixi-install", "hooks"}
    assert {step.name for step in onboard} >= {"pixi-project", "pixi-install", "prereqs"}
