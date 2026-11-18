"""Steward test-tree fixtures.

Story 117.10 (spec-pyforge-steward CAP-175): a CI shard runs this suite with a job-level
``PYTEST_ADDOPTS=--splits N --group K --durations-path …``. The outer pytest consumed those flags at start-up; the
pytest children these tests spawn (the preflight's collections, the scratch-tree runs, the suite-reduction fixtures)
must see the whole fixture suite, not one shard of it -- on the first sharded run three shards red on exactly that.
This session fixture removes the pytest-split flags from the environment the children inherit and puts the original
value back at the end of the session.

Story 125.1: two host capabilities some workspace tests need are probed here, once per session, by doing the thing
itself: holding a file whose name is not UTF-8 (APFS refuses one), and handing ``git`` an argument that is not UTF-8
(a launcher that reads its arguments as text aborts on one). A test that needs one names its fixture, and skips with
the missing capability as its reason on a host that lacks it; the tests run the ``git`` on PATH, as the code does.
A third is probed the same way: a ``bash`` that runs the workflows' own ``changes`` steps, which declare associative
arrays (bash 4 or later; macOS ships 3.2). The code runs those steps with the ``bash`` on PATH and, where one fails,
runs every lane it guards; a test that proves what the steps select needs a ``bash`` that can run them.
"""

from __future__ import annotations

import os
import shlex
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

_SPLIT_FLAGS_WITH_VALUE = ("--splits", "--group", "--durations-path")
_SPLIT_SWITCHES = ("--store-durations", "--clean-durations")


def strip_pytest_split_flags(addopts: str) -> str:
    """``addopts`` without pytest-split's flags (``--splits N``, ``--group K``, ``--durations-path P``, ``--flag=value``,
    ``--store-durations``, ``--clean-durations``); every other token stays in order."""
    tokens = shlex.split(addopts)
    kept: list[str] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in _SPLIT_FLAGS_WITH_VALUE:
            i += 2
            continue
        if token in _SPLIT_SWITCHES or any(token.startswith(f"{flag}=") for flag in _SPLIT_FLAGS_WITH_VALUE):
            i += 1
            continue
        kept.append(token)
        i += 1
    return shlex.join(kept)


@pytest.fixture(autouse=True, scope="session")
def _pytest_children_run_unsharded() -> Iterator[None]:
    raw = os.environ.get("PYTEST_ADDOPTS")
    if raw is None:
        yield
        return
    cleaned = strip_pytest_split_flags(raw)
    if cleaned == shlex.join(shlex.split(raw)):
        yield
        return
    if cleaned:
        os.environ["PYTEST_ADDOPTS"] = cleaned
    else:
        del os.environ["PYTEST_ADDOPTS"]
    try:
        yield
    finally:
        os.environ["PYTEST_ADDOPTS"] = raw


@pytest.fixture(scope="session")
def _host_holds_non_utf8_file_names(tmp_path_factory: pytest.TempPathFactory) -> bool:
    probe = os.fsencode(tmp_path_factory.mktemp("non-utf8-name")) + b"/probe-\xff"
    try:
        Path(os.fsdecode(probe)).write_bytes(b"")
    except OSError:
        return False
    return True


@pytest.fixture(scope="session")
def _git_takes_non_utf8_arguments() -> bool:
    return subprocess.run(["git", "rev-parse", "--sq-quote", b"probe-\xff"], capture_output=True).returncode == 0


@pytest.fixture
def non_utf8_file_names(_host_holds_non_utf8_file_names: bool) -> None:
    """Skip a test that creates a file or directory whose name is not UTF-8 where the file system refuses one."""
    if not _host_holds_non_utf8_file_names:
        pytest.skip("the file system cannot hold a file name that is not UTF-8")


@pytest.fixture
def non_utf8_git_arguments(_git_takes_non_utf8_arguments: bool) -> None:
    """Skip a test that hands git an argument that is not UTF-8 where the git on PATH aborts on one."""
    if not _git_takes_non_utf8_arguments:
        pytest.skip("the git on PATH aborts on an argument that is not UTF-8")


@pytest.fixture(scope="session")
def workflow_changes_bash() -> None:
    """Skip a test that runs a workflow's ``changes`` step where the bash on PATH cannot run it."""
    if subprocess.run(["bash", "-c", "declare -A probe"], capture_output=True).returncode != 0:
        pytest.skip("the bash on PATH cannot run the workflows' changes steps: declare -A needs bash 4 or later")
