"""Story 33.1: `pyforge atlas <verb>` reaches every verb its contracts name.

The FR-155 parity gate (`mcp/parity.py`) reads its verbs from Kedro's
`project_group`, and `TOOL_SPECS` declares each `run_*` tool's argv against
that group. Until this story `main` dispatched to the bare `run` command
(`find_run_command`), so `pyforge atlas run …` was an unexpected extra
argument while the gate stayed green: it checked that a verb exists, never
that the binary reaches it. These tests close that gap, and pin the project
root a run sees to the one the MCP face uses, from any cwd.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import click
import pytest
from kedro.framework.cli.project import project_group

from pyforge.atlas.__main__ import PROJECT_ROOT, discover_cli_verbs, main
from pyforge.atlas.mcp import session as mcp_session
from pyforge.atlas.mcp.tools import TOOL_SPECS

# Click >= 8.2 exits 2 when a group is invoked without a command (it prints the
# group's help first, `no_args_is_help`).
BARE_EXIT_CODE = 2


@pytest.fixture
def recorded(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[dict[str, Any]]:
    """Replace every project command's callback with a recorder, from a foreign cwd.

    The recorder captures what the command would have run with: the Click
    `obj` (Kedro's project metadata), the cwd at call time and the parsed
    params. Nothing real runs.
    """
    calls: list[dict[str, Any]] = []
    monkeypatch.chdir(tmp_path)

    def make(verb: str):
        def stub(*_args: Any, **params: Any) -> None:
            calls.append(
                {
                    "verb": verb,
                    "obj": click.get_current_context().obj,
                    "cwd": Path.cwd(),
                    "params": params,
                }
            )

        return stub

    for verb, command in project_group.commands.items():
        monkeypatch.setattr(command, "callback", make(verb))
    return calls


def test_the_parity_gate_counts_exactly_the_group_main_dispatches_to() -> None:
    """The verbs below are parametrized from the group itself, so collection loads no
    Kedro project; this ties them back to what the FR-155 gate reads."""
    assert discover_cli_verbs() == frozenset(project_group.commands)


def test_project_root_is_the_mcp_face_root() -> None:
    """One project root for both faces (AD-23)."""
    assert PROJECT_ROOT == mcp_session.PROJECT_ROOT
    assert (PROJECT_ROOT / "conf" / "base" / "catalog.yml").is_file()


@pytest.mark.parametrize("verb", sorted(project_group.commands))
def test_every_parity_verb_is_reachable_through_main(verb: str, recorded: list[dict[str, Any]]) -> None:
    """Each verb the parity gate counts runs through `main`, against atlas's project.

    Mutations this fails: `main` back on `find_run_command` (the verb becomes
    an unexpected extra argument, exit 2); the `chdir` dropped (the cwd stays
    the foreign `tmp_path`); the metadata not passed as `obj`.
    """
    with pytest.raises(SystemExit) as excinfo:
        main([verb])

    assert excinfo.value.code == 0
    assert [call["verb"] for call in recorded] == [verb]
    call = recorded[0]
    assert call["obj"].package_name == "pyforge.atlas"
    assert call["obj"].project_path == PROJECT_ROOT
    assert call["cwd"] == PROJECT_ROOT


def test_main_gives_the_caller_its_cwd_back(recorded: list[dict[str, Any]], tmp_path: Path) -> None:
    """The member-dir cwd lasts only for the command; an in-process caller stays put."""
    with pytest.raises(SystemExit):
        main(["run"])

    assert recorded[0]["cwd"] == PROJECT_ROOT
    assert Path.cwd() == tmp_path.resolve()


@pytest.mark.parametrize(
    "tool",
    sorted(name for name, spec in TOOL_SPECS.items() if spec.get("cli") is not None),
)
def test_every_declared_tool_argv_parses_through_main(tool: str, recorded: list[dict[str, Any]]) -> None:
    """The argv `TOOL_SPECS` declares is one the binary accepts, naming its pipeline."""
    argv = list(TOOL_SPECS[tool]["cli"])

    with pytest.raises(SystemExit) as excinfo:
        main(argv)

    assert excinfo.value.code == 0
    assert [call["verb"] for call in recorded] == [argv[0]]
    assert list(recorded[0]["params"]["pipelines"]) == [argv[2]]


def test_bare_invocation_lists_the_verbs_and_runs_nothing(
    recorded: list[dict[str, Any]], capsys: pytest.CaptureFixture[str]
) -> None:
    """Operator ruling 2026-10-18: a bare `pyforge atlas` prints help, never a whole-DAG run."""
    with pytest.raises(SystemExit) as excinfo:
        main([])

    assert excinfo.value.code == BARE_EXIT_CODE
    captured = capsys.readouterr()
    text = captured.out + captured.err
    for verb in project_group.commands:
        assert verb in text
    assert recorded == []


def test_bare_cli_in_a_real_process_from_a_foreign_cwd(tmp_path: Path) -> None:
    """The console path end to end: from outside the project, help names the verbs and nothing is written.

    A regression that made the bare call run the DAG again would start a live,
    networked `__default__` run inside the unit suite. The unknown `KEDRO_ENV`
    makes any such run fail at config load, before a node runs; help output does
    not read it. The timeout bounds the rest.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "pyforge.atlas"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "KEDRO_ENV": "__atlas_test_no_such_env__"},
        timeout=60,
    )

    assert proc.returncode == BARE_EXIT_CODE, proc.stderr
    combined = proc.stdout + proc.stderr
    for verb in ("ipython", "package", "run"):
        assert verb in combined
    assert list(tmp_path.iterdir()) == []
