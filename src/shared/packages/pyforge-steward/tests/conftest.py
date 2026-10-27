"""Steward test-tree fixtures.

Story 117.10 (spec-pyforge-steward CAP-175): a CI shard runs this suite with a job-level
``PYTEST_ADDOPTS=--splits N --group K --durations-path …``. The outer pytest consumed those flags at start-up; the
pytest children these tests spawn (the preflight's collections, the scratch-tree runs, the suite-reduction fixtures)
must see the whole fixture suite, not one shard of it -- on the first sharded run three shards red on exactly that.
This session fixture removes the pytest-split flags from the environment the children inherit and puts the original
value back at the end of the session.
"""

from __future__ import annotations

import os
import shlex
from collections.abc import Iterator

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
