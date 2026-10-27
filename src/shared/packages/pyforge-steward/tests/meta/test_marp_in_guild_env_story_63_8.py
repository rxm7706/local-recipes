"""Story 63.8 (spec-pyforge-steward CAP-5, a fix under Story 63.1) -- the Guild env carries ``marp``.

Story 63.1 moved the Guild tasks into ``[feature.guild-tasks.tasks]`` so they run under
``-e pyforge-guild``, the session default. ``deck-export`` -- which herald's ``deck pull`` and
``deck sync-all`` shell as ``pixi run -e pyforge-guild deck-export <slug>`` -- runs the ``marp``
binary, but ``marp-cli`` was declared only in ``[feature.local-recipes.dependencies]``. Under the
Guild env ``scripts/deck_export.py`` exited 1 (``'marp' not on PATH``) and pointed at the
``-e local-recipes`` form, which the session hook refuses as a Guild-task / local-recipes mix-up.

Pinned here: ``marp-cli`` is a ``[feature.pyforge-guild.dependencies]`` member at the same floor
as the ``local-recipes`` site; every ``guild-tasks`` task whose cmd or description names ``marp``
resolves it from that feature; and no ``guild-tasks`` task's usage line sends anyone to
``pixi run -e local-recipes <guild task>`` (the form ``session_denials`` refuses).
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + .claude/skills)")


ROOT = _repo_root()


def _pixi() -> dict:
    return tomllib.loads((ROOT / "pixi.toml").read_text(encoding="utf-8"))


def _guild_tasks(pixi: dict) -> dict[str, dict]:
    tasks = pixi["feature"]["guild-tasks"]["tasks"]
    return {name: (task if isinstance(task, dict) else {"cmd": task}) for name, task in tasks.items()}


def _task_text(task: dict) -> str:
    return f"{task.get('cmd', '')} {task.get('description', '')}"


def test_marp_cli_is_a_guild_feature_dependency_at_the_local_recipes_floor() -> None:
    pixi = _pixi()
    guild = pixi["feature"]["pyforge-guild"]["dependencies"]
    factory = pixi["feature"]["local-recipes"]["dependencies"]
    assert "marp-cli" in guild, "marp-cli must be a [feature.pyforge-guild.dependencies] member (Story 63.8)"
    assert "marp-cli" in factory, "the local-recipes marp-cli site stays (its floor and nodejs-26 note)"
    assert guild["marp-cli"] == factory["marp-cli"], "the Guild and local-recipes marp-cli floors move together"


def test_every_guild_task_that_names_marp_resolves_it_in_the_guild_env() -> None:
    pixi = _pixi()
    naming_marp = sorted(
        name for name, task in _guild_tasks(pixi).items() if re.search(r"\bmarp\b", _task_text(task), re.IGNORECASE)
    )
    assert "deck-export" in naming_marp, "deck-export is the Guild task that runs marp (the gap Story 63.8 closed)"
    assert "marp-cli" in pixi["feature"]["pyforge-guild"]["dependencies"], (
        f"these guild-tasks run marp but the Guild feature does not carry marp-cli: {naming_marp}"
    )


def test_no_guild_task_usage_line_sends_a_guild_task_to_local_recipes() -> None:
    tasks = _guild_tasks(_pixi())
    pattern = re.compile(r"pixi run -e local-recipes (?P<task>[\w-]+)")
    offenders = {
        name: sorted({m.group("task") for m in pattern.finditer(_task_text(task)) if m.group("task") in tasks})
        for name, task in tasks.items()
    }
    offenders = {name: hits for name, hits in offenders.items() if hits}
    assert not offenders, (
        "a Guild task's usage line must read `pixi run -e pyforge-guild <task>` "
        f"(the session hook refuses the -e local-recipes form): {offenders}"
    )
