"""Marshal's suite-wide hooks: the package half's tree-read guard (Story 116.4, spec-pyforge-marshal:CAP-305).

``tests/_support/tree_read_guard.py`` holds the guard and its audit hook; this conftest loads it by path (``tests``
is not a package), installs it once per process (each xdist worker loads this file), names it on the run's header
line, and arms it around the setup, call and teardown of every package-half test (marked neither ``live_tree`` nor
``slow``), so module fixtures count. A phase that read a repository path outside the package fails, naming each
path. An armed test also starts off the tree (``_package_half_off_the_tree``), so the code under test finds no
checkout to fall back to. With no repository around the package the guard is inert, arms nothing and says so.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Generator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

_GUARD_FILE = Path(__file__).resolve().parent / "_support" / "tree_read_guard.py"
_GUARD_MODULE = "pyforge_marshal_tests_support_tree_read_guard"


def _guard_module() -> ModuleType:
    module = sys.modules.get(_GUARD_MODULE)
    if module is None:
        spec = importlib.util.spec_from_file_location(_GUARD_MODULE, _GUARD_FILE)
        assert spec is not None and spec.loader is not None, f"cannot load {_GUARD_FILE}"
        module = importlib.util.module_from_spec(spec)
        sys.modules[_GUARD_MODULE] = module
        spec.loader.exec_module(module)
    assert module.MODULE_NAME == _GUARD_MODULE
    return module


_GUARD = _guard_module().install(_guard_module().TreeReadGuard.around(_GUARD_FILE))


def _package_half(item: pytest.Item) -> bool:
    return item.get_closest_marker("live_tree") is None and item.get_closest_marker("slow") is None


def _guarded(item: pytest.Item, phase: str) -> Generator[None, Any, Any]:
    if _GUARD.inert or not _package_half(item):
        return (yield)
    with _GUARD.window() as reads:
        result = yield
    if reads:
        pytest.fail(_GUARD.failure(item.nodeid, phase, reads), pytrace=False)
    return result


@pytest.fixture(scope="session")
def _off_tree(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """A working directory and a bare checkout outside the repository: the bare checkout holds the package's
    source path down to ``cli/`` and nothing else, as a checkout that is not this one would."""
    from pyforge.marshal.cli import config

    bare_checkout = tmp_path_factory.mktemp("off-tree-checkout")
    (bare_checkout / config._PACKAGE_SOURCE_RELPATH / "src" / "pyforge" / "marshal" / "cli").mkdir(parents=True)
    return tmp_path_factory.mktemp("off-tree-cwd"), bare_checkout


@pytest.fixture
def off_tree_checkout_anchor() -> bool:
    """Whether an armed test's ``repo_root()`` and ``checkout_root()`` answer the bare checkout. A module that moves
    ``cli/config.py``'s checkout anchor itself overrides this fixture with ``False``."""
    return True


@pytest.fixture(autouse=True)
def _package_half_off_the_tree(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch, off_tree_checkout_anchor: bool
) -> None:
    """An armed test runs as it would off the tree: code under test finds no checkout to fall back to.

    Two fallbacks reach the repository at run time: ``pyforge.core``'s flag tree, found by walking up from the
    working directory, and ``cli/config.py``'s ``repo_root()`` and ``checkout_root()``, anchored on that module's
    ``__file__`` through ``_editable_checkout_root()``. The test starts in a working directory outside the
    repository, and ``_editable_checkout_root()`` answers the bare checkout. ``config.__file__`` itself is never
    rebound: coverage.py names a traced file by its frame's ``__file__``, so a rebound one files ``config.py``'s
    lines under a path that does not exist and drops them from the report. A test that sets its own directory or
    root (``monkeypatch.chdir``, ``monkeypatch.setattr``) still does, after this."""
    if _GUARD.inert or not _package_half(request.node):
        return
    from pyforge.marshal.cli import config

    working_directory, bare_checkout = request.getfixturevalue("_off_tree")
    monkeypatch.chdir(working_directory)
    if off_tree_checkout_anchor:
        monkeypatch.setattr(config, "_editable_checkout_root", lambda: bare_checkout)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_setup(item: pytest.Item) -> Generator[None, Any, Any]:
    return (yield from _guarded(item, "setup"))


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item: pytest.Item) -> Generator[None, Any, Any]:
    return (yield from _guarded(item, "call"))


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item: pytest.Item) -> Generator[None, Any, Any]:
    return (yield from _guarded(item, "teardown"))


@pytest.hookimpl(trylast=True)
def pytest_sessionstart(session: pytest.Session) -> None:
    """Name the guard on the run's header line, also under ``-q`` (an xdist worker has no terminal)."""
    if hasattr(session.config, "workerinput"):
        return
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_line(_GUARD.header())
