"""`gh` engine adapter (AD-12, AD-10, Story 3.7): conda-forge/staged-recipes
open-PR interrogation via `gh pr list` (FR-18).

Mirrors `engines/pixi.py`'s own shape (module-level `name`/`probe()`, list
argv, CAPTURE-mode `subprocess.run` with a mandatory `timeout=`) -- see that
module's docstring for the shared engine-adapter reasoning. Two structural
differences set this adapter apart from every other one in this package:

1. `find_open_pr` is built and unit-tested STANDALONE, never wired into any
   `ship_*` function (spec Never boundary) -- `ship_conda_forge` (Story 3.6)
   does not exist in this branch's lineage (a sibling, not-yet-merged
   worktree branched from the same point). It is ready for that wiring once
   the branches converge.
2. `find_open_pr` uses `probe_engine`, never `require_engine` -- the same
   deliberate deviation `engines.pixi.search` makes from `build()`/
   `upload()`'s own "raise `EngineAbsentError` first" convention. A missing
   `gh` binary is exactly as "cannot be interrogated" as a network timeout
   or an unrecognized `gh` failure (AD-10: "never an assumption in either
   direction"), so it folds into the identical `found=None, url=None`
   outcome rather than raising a structural precondition.

Why `gh pr list --head <branch>` needs no fork-owner lookup (spec Design
Notes): `gh pr list --help` states `"<owner>:<branch>" syntax not
supported` for `--head` -- a BARE branch name is not just accepted, it is
the ONLY accepted form, so this adapter never needs to resolve or hold a
GitHub username. `gh` also owns its own authentication exactly as
`twine`/`pixi` own theirs (AD-14): this module never reads a
`GH_TOKEN`/`GITHUB_TOKEN` value anywhere (spec Never boundary).

No credential handling of any kind lives here -- `gh` reads its own token
from wherever it is configured (`gh auth login`, or a `GH_TOKEN`/
`GITHUB_TOKEN` in its OWN process environment, inherited automatically
since no `env=` kwarg is ever passed to `subprocess.run`), and this module
never inspects, copies, or even names that mechanism.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

from . import probe_engine

name = "gh"
"""`EngineAdapter.name` -- an `engines/__init__.py::_KNOWN_ENGINES` key."""

_BINARY_NAME = "gh"
"""Duplicates `_KNOWN_ENGINES["gh"]` (mirrors `engines/pixi.py`'s own
`_BINARY_NAME` duplication rationale)."""

_GH_PR_LIST_TIMEOUT_SECONDS = 30.0
"""A metadata query against GitHub's own API, not an upload or a
from-source build -- generous enough for a slow connection, without
carrying `engines.pixi.upload`/`engines.twine.upload`'s own 300s allowance
for a real file transfer (mirrors `pypi_index._VERSION_EXISTS_TIMEOUT_
SECONDS`'s identical rationale and value, both added by this same story)."""


def probe() -> str | None:
    """`EngineAdapter.probe()` -- mirrors `engines/pixi.py::probe`."""
    return probe_engine(name, _BINARY_NAME).version


@dataclass(frozen=True)
class OpenPrSearchResult:
    """One `find_open_pr()` call's outcome (AD-10). `found` is `True` when
    at least one open PR matched, `False` when `gh` conclusively reported
    none, or `None` when the search itself could not be completed (`gh`
    absent, a timeout, a nonzero `gh` exit, or unparseable output) -- the
    same three-way "found / conclusively absent / undeterminable" shape
    `pypi_index.version_exists`/`engines.pixi.search` already establish
    (module docstring, AD-10: "never an assumption in either direction").
    `url` is the first matching PR's own URL when `found` is `True`, else
    `None`."""

    found: bool | None
    url: str | None


def find_open_pr(
    repo: str,
    head_branch: str,
    *,
    timeout: float | None = None,
) -> OpenPrSearchResult:
    """Search `repo` (e.g. `"conda-forge/staged-recipes"`) for an OPEN pull
    request whose head branch is `head_branch` (e.g. `"add-recipe-<name>"`)
    via `gh pr list --repo <repo> --head <head_branch> --state open --json
    number,url` (Story 3.7, FR-18, AD-10).

    Uses `probe_engine`, never `require_engine` (module docstring) -- a
    missing `gh` returns `OpenPrSearchResult(found=None, url=None)` rather
    than raising `EngineAbsentError`, before any subprocess is even
    attempted.

    `head_branch` is passed BARE, with no `owner:` prefix (module docstring:
    `gh pr list --help`'s own `"<owner>:<branch>" syntax not supported`
    note) -- this function never resolves or holds a fork owner.

    `timeout` defaults to `_GH_PR_LIST_TIMEOUT_SECONDS` when `None`. Unlike
    every other engine adapter's own timeout handling, a `TimeoutExpired`
    (or any other `OSError` from the spawn itself) here is folded into
    `found=None, url=None` (module docstring) rather than translated to a
    typed `MasonError` -- this is an INTERROGATION, not a ship-target's own
    mutating operation, so its own failure is data on the returned
    dataclass, never a raised structural precondition (mirrors
    `engines.pixi.search`'s identical choice).

    `completed.returncode != 0`, or a `stdout` that does not parse as JSON,
    or a JSON body that is not a list, all fold into the same `found=None,
    url=None` outcome -- an empty list (`gh` ran fine and conclusively found
    no match) is the ONE case that returns `found=False, url=None`.
    """
    status = probe_engine(name, _BINARY_NAME)
    if not status.available:
        return OpenPrSearchResult(found=None, url=None)

    resolved_timeout = timeout if timeout is not None else _GH_PR_LIST_TIMEOUT_SECONDS
    argv = [
        _BINARY_NAME,
        "pr",
        "list",
        "--repo",
        repo,
        "--head",
        head_branch,
        "--state",
        "open",
        "--json",
        "number,url",
    ]
    try:
        completed = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=resolved_timeout,
            check=False,
        )
    except subprocess.TimeoutExpired, OSError:
        return OpenPrSearchResult(found=None, url=None)

    if completed.returncode != 0:
        return OpenPrSearchResult(found=None, url=None)

    try:
        entries = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return OpenPrSearchResult(found=None, url=None)

    if not isinstance(entries, list):
        return OpenPrSearchResult(found=None, url=None)
    if not entries:
        return OpenPrSearchResult(found=False, url=None)

    first = entries[0]
    url = first.get("url") if isinstance(first, dict) else None
    return OpenPrSearchResult(found=True, url=url)
