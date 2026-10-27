"""Two-state tests for steward's CAP-7 retrofit kill switches (Epic 114; ``spec-feature-flag-governance`` CAP-7).

One test per key, each run ON and OFF through ``pyforge.testing_kit.flags.flag_states`` and a flagd FILE tree in
the same state (``test_pages_duty_flag_states.py`` precedent). A duty switch (``cli.RETROFIT_KEY_VERBS``): ON
leaves ``--help`` unmarked and ``require_retrofit_flags`` passes; OFF marks the duty or sub-verb disabled (Q3)
and ``require_retrofit_flags`` refuses naming the key. ``steward budget show`` proves the ``main`` wiring: the
refusal is steward's usage code 2 with a ``flag <key> is off`` message, inside the frozen domain.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pytest
from pyforge.core.flags import FlagOff, read_boolean
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.cli_runner import invoke_cli
from pyforge.testing_kit.flags import flag_states, flagd_tree

from pyforge.steward import cli, frames
from pyforge.steward.cli import EXIT_USAGE, main

flag_provider = make_flag_provider_fixture()


def _tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key: str, on: bool) -> Path:
    path = flagd_tree(tmp_path, {key: "on" if on else "off"})
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(path))
    return path


def _entry_blocks(output: str, verb: str) -> list[str]:
    lines = output.splitlines()
    blocks: list[str] = []
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.split(None, 1)[:1] != [verb]:
            continue
        indent = len(line) - len(stripped)
        block = [line]
        for follow in lines[index + 1 :]:
            if not follow.strip() or len(follow) - len(follow.lstrip()) <= indent:
                break
            block.append(follow)
        blocks.append(" ".join("\n".join(block).split()))
    return blocks


def _namespace(path: tuple[str, ...]) -> argparse.Namespace:
    ns = argparse.Namespace(duty=path[0])
    if len(path) > 1:
        setattr(ns, f"{path[0]}_verb", path[1])
    return ns


def _assert_duty_switch(key: str, on: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _tree(tmp_path, monkeypatch, key, on)
    marker = f"[disabled: flag {key} is off]"
    paths = cli.RETROFIT_KEY_VERBS[key]
    for path in paths:
        listing = invoke_cli(main, [*path[:-1], "--help"]).output
        verb = path[-1]
        assert re.search(rf"(?<![\w-]){re.escape(verb)}(?![\w-])", listing), (key, path)
        blocks = _entry_blocks(listing, verb)
        assert blocks, (key, path, listing)
        if on:
            assert not any(marker in block for block in blocks), (key, path)
            cli.require_retrofit_flags(_namespace(path))
        else:
            assert any(marker in block for block in blocks), (key, path, blocks)
            with pytest.raises(FlagOff) as raised:
                cli.require_retrofit_flags(_namespace(path))
            assert raised.value.key == key


@flag_states("pyforge.steward.budget")
def test_pyforge_steward_budget(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`steward budget`: a declared ceiling and an honest spend signal (spec-pyforge-steward CAP-4, Story 114.1): `steward budget` is listed disabled and refuses with usage code 2."""
    _assert_duty_switch("pyforge.steward.budget", flag_provider["pyforge.steward.budget"], tmp_path, monkeypatch)


@flag_states("pyforge.steward.workspace_clean")
def test_pyforge_steward_workspace_clean(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`workspace clean` removes merged worktrees, archived rather than deleted (spec-pyforge-steward CAP-107, Story 114.3): `steward workspace clean` is listed disabled and refuses with usage code 2."""
    _assert_duty_switch(
        "pyforge.steward.workspace_clean", flag_provider["pyforge.steward.workspace_clean"], tmp_path, monkeypatch
    )


@flag_states("pyforge.steward.workspace_own_worktrees_only")
def test_pyforge_steward_workspace_own_worktrees_only(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """only the worktrees it created; Marshal's loop-homes stay invisible (spec-pyforge-steward CAP-108, Story 114.4): `steward workspace clean` refuses with usage code 2; a loop home is never touched."""
    _assert_duty_switch(
        "pyforge.steward.workspace_own_worktrees_only",
        flag_provider["pyforge.steward.workspace_own_worktrees_only"],
        tmp_path,
        monkeypatch,
    )


@flag_states("pyforge.steward.deploy_perimeter")
def test_pyforge_steward_deploy_perimeter(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """the deployment perimeter ships with the pattern (spec-pyforge-steward CAP-114, Story 114.5): `steward deploy perimeter` is listed disabled and refuses with usage code 2."""
    _assert_duty_switch(
        "pyforge.steward.deploy_perimeter", flag_provider["pyforge.steward.deploy_perimeter"], tmp_path, monkeypatch
    )


@flag_states("pyforge.steward.setup_hooks")
def test_pyforge_steward_setup_hooks(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """the pre-commit set: attribution lines and un-preflighted pushes are refused by hooks, not prose (spec-pyforge-steward CAP-154, Story 114.6): `steward setup` refuses with usage code 2; a machine is never bootstrapped with fewer hooks."""
    _assert_duty_switch(
        "pyforge.steward.setup_hooks", flag_provider["pyforge.steward.setup_hooks"], tmp_path, monkeypatch
    )


@flag_states("pyforge.steward.workspace_full_refs")
def test_pyforge_steward_workspace_full_refs(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """steward reads `origin/main` and its own branches by their full refs (spec-pyforge-steward CAP-158, Story 114.7): `steward workspace start|status|clean` refuse with usage code 2; a short ref is never read."""
    _assert_duty_switch(
        "pyforge.steward.workspace_full_refs",
        flag_provider["pyforge.steward.workspace_full_refs"],
        tmp_path,
        monkeypatch,
    )


@flag_states("pyforge.steward.frame_upstream_check")
def test_pyforge_steward_frame_upstream_check(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Frame draft re-grounding (spec-pyforge-steward CAP-6 (c), Story 114.2): OFF refuses the opt-in upstream
    check with usage code 2 naming the flag; ON reads the switch ON (the network check itself is not run here)."""
    on = flag_provider["pyforge.steward.frame_upstream_check"]
    tree = _tree(tmp_path, monkeypatch, "pyforge.steward.frame_upstream_check", on)
    assert read_boolean(frames.FRAME_UPSTREAM_CHECK_FLAG_KEY, default=True, flags_path=tree) is on
    if on:
        return
    result = invoke_cli(frames.main, ["--repo", str(tmp_path), "--upstream-check"])
    assert result.exit_code == EXIT_USAGE
    assert "frame-upstream-check: flag pyforge.steward.frame_upstream_check is off" in result.output


@flag_states("pyforge.steward.budget")
def test_main_projects_a_flag_off_duty_to_the_usage_code_with_the_message(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    on = flag_provider["pyforge.steward.budget"]
    _tree(tmp_path, monkeypatch, "pyforge.steward.budget", on)
    monkeypatch.chdir(tmp_path)
    result = invoke_cli(main, ["budget", "show"])
    if on:
        assert "is off" not in result.output
        assert result.exit_code != EXIT_USAGE
        return
    assert result.exit_code == EXIT_USAGE
    assert "steward: flag pyforge.steward.budget is off" in result.output


def test_no_tree_reads_every_switch_on_without_a_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("PYFORGE_FLAGS_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    for path in cli.RETROFIT_VERB_FLAGS:
        cli.require_retrofit_flags(_namespace(path))
    assert "WARN" not in capsys.readouterr().err
    listing = " ".join(invoke_cli(main, ["--help"]).output.split())
    for key in cli.RETROFIT_KEY_VERBS:
        assert f"flag {key} is off" not in listing, key
    assert "WARN" not in listing


def test_an_ordinary_invocation_reads_no_switch_for_the_listing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The listing is marked only under --help: a tree lacking every key warns for the invoked duty's keys only."""
    _tree(tmp_path, monkeypatch, "pyforge.steward.unrelated", True)
    monkeypatch.chdir(tmp_path)
    result = invoke_cli(main, ["budget", "show"])
    warned = {key for key in cli.RETROFIT_KEY_VERBS if f"WARN flag {key}:" in result.output}
    assert warned == {key for key in cli.RETROFIT_VERB_FLAGS.get(("budget",), ())}


def test_every_gated_duty_exists_on_the_parser() -> None:
    parser_help = invoke_cli(main, ["--help"]).output
    for key, paths in cli.RETROFIT_KEY_VERBS.items():
        assert key.startswith("pyforge.steward."), key
        for path in paths:
            assert path[0] in cli.DUTIES, (key, path)
            assert path[0] in parser_help, (key, path)
