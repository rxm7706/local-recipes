"""Story 19.2 / spec-pyforge-scribe CAP-28 -- `scribe capture` and `scribe recall` run from the
session default environment.

`pyforge-guild` is the default environment for every harness (steward Story 63.1); until
2026-09-19 the scribe CLI lived only in `-e pyforge-scribe`, so a Copilot, Cursor Cloud or
Claude Code remote session -- whose sandbox installs the Guild default and nothing else --
could not capture a decision or recall one. This pins the core package's membership and
keeps the governance docs from telling sessions the old thing.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + .claude/skills)")


ROOT = _repo_root()
GOVERNANCE_DOCS = ("AGENTS.md", "CLAUDE.md", ".cursor/rules/scribe-recall.mdc")
# The extras are heavy and per-env by design (AD-6 air-gap, pixi.toml comment at feature.pyforge-guild):
# they must NOT ride into the Guild default with the core package.
HEAVY_EXTRAS = ("graphifyy", "cocoindex", "psycopg")


def _pixi() -> dict:
    return tomllib.loads((ROOT / "pixi.toml").read_text(encoding="utf-8"))


def test_scribe_core_is_a_guild_feature_dependency() -> None:
    deps = _pixi()["feature"]["pyforge-guild"]["dependencies"]
    assert "pyforge-scribe" in deps, "pyforge-scribe must be a [feature.pyforge-guild.dependencies] member (CAP-28)"
    assert deps["pyforge-scribe"] == {"path": "src/shared/packages/pyforge-scribe"}


def test_guild_default_environments_carry_the_guild_feature() -> None:
    envs = _pixi()["environments"]
    for name in ("pyforge-guild", "default"):
        assert "pyforge-guild" in envs[name]["features"], f"environment {name!r} must include the pyforge-guild feature"


@pytest.mark.parametrize("extra", HEAVY_EXTRAS)
def test_heavy_scribe_extras_stay_out_of_the_guild_default(extra: str) -> None:
    deps = _pixi()["feature"]["pyforge-guild"]["dependencies"]
    assert extra not in deps, (
        f"{extra} is a per-env compile extra; it belongs to feature.pyforge-scribe, not the Guild default"
    )


@pytest.mark.parametrize("rel", GOVERNANCE_DOCS)
def test_governance_docs_no_longer_route_capture_or_recall_to_the_scribe_env(rel: str) -> None:
    text = (ROOT / rel).read_text(encoding="utf-8")
    stale = re.findall(r"-e pyforge-scribe scribe (?:capture|recall)", text)
    assert not stale, f"{rel} still routes `scribe capture`/`recall` to -e pyforge-scribe: {stale}"
