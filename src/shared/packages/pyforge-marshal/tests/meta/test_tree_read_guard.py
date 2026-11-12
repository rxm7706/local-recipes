"""Meta test -- Story 116.4 (spec-pyforge-marshal:CAP-305): the package half's tree-read guard.

``tests/_support/tree_read_guard.py`` records a read of a repository path outside the package, and
``tests/conftest.py`` fails the package-half test that made it, naming the path. Proven here on a made-up
repository under ``tmp_path`` (a ``.git`` file, a package, a ``scripts/`` directory), so every case runs the same
inside and outside this checkout:

* the classifier records ``<repo>/scripts/x.py``, ``<repo>/_bmad-output/...`` and
  ``<repo>/src/shared/packages/pyforge-doctor/...``, and never a path under the package, a tmp dir, ``<repo>/.pixi/``,
  ``<repo>/.steward/coverage/``, the installed ``pyforge.core`` or ``pyforge.testing_kit`` source, or outside the
  repository;
* the audit hook records ``open``, ``os.listdir``, ``os.scandir`` and ``glob.glob`` only while armed, never the
  import system's directory listings, never a ``dir_fd``-relative ``os.open``;
* the conftest, run in a child pytest over the made-up repository, names the guard on the header line, fails a
  package-half test (and a module fixture's read) naming each path, never arms a ``live_tree`` or ``slow`` test, and
  is inert with no repository around the package;
* in this process, the conftest arms this module's tests and starts each off the tree.
"""

from __future__ import annotations

import glob
import importlib
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

_TESTS = Path(__file__).resolve().parents[1]
_GUARD_FILE = _TESTS / "_support" / "tree_read_guard.py"
_CONFTEST = _TESTS / "conftest.py"
_PACKAGE = Path("src") / "shared" / "packages" / "pyforge-marshal"


def _guard_module() -> ModuleType:
    """The module the conftest loaded (one per process, so one hook); loaded here by path when it has not been."""
    name = "pyforge_marshal_tests_support_tree_read_guard"
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, _GUARD_FILE)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    assert module.MODULE_NAME == name
    return module


def _made_up_repository(root: Path, *, git: bool = True) -> tuple[Path, Path]:
    """(repository, package): a package laid out as marshal's, a ``.git`` file as a worktree has, and two
    installed-looking modules (``fake_core_116_4`` and ``fake_kit_116_4``) under the repository's ``src/``."""
    repository = root / "repo"
    package = repository / _PACKAGE
    (package / "tests" / "_support").mkdir(parents=True)
    if git:
        (repository / ".git").write_text("gitdir: /elsewhere/.git/worktrees/repo\n", encoding="utf-8")
    for module, station in (("fake_core_116_4", "pyforge-core"), ("fake_kit_116_4", "pyforge-testing-kit")):
        source = repository / "src" / "shared" / "packages" / station / "src" / module
        source.mkdir(parents=True)
        (source / "__init__.py").write_text("", encoding="utf-8")
    return repository, package


_FAKE_MODULES = ("fake_core_116_4", "fake_kit_116_4")


@pytest.fixture
def made_up(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repository, package = _made_up_repository(tmp_path)
    for station in ("pyforge-core", "pyforge-testing-kit"):
        monkeypatch.syspath_prepend(str(repository / "src" / "shared" / "packages" / station / "src"))
    for name in _FAKE_MODULES:
        sys.modules.pop(name, None)
    importlib.invalidate_caches()
    guard = _guard_module().TreeReadGuard.around(
        package / "tests" / "_support" / "tree_read_guard.py", modules=_FAKE_MODULES
    )
    yield repository, package, guard
    for name in _FAKE_MODULES:
        sys.modules.pop(name, None)


def test_the_guard_finds_the_package_and_the_nearest_repository_around_it(made_up) -> None:
    repository, package, guard = made_up

    assert guard.package == package.resolve()
    assert guard.repository == repository.resolve()
    assert not guard.inert
    assert guard.header() == "tree-read guard: armed (package src/shared/packages/pyforge-marshal)"


@pytest.mark.parametrize(
    "parts",
    [
        ("scripts", "x.py"),
        ("_bmad-output", "projects", "pyforge-marshal", "planning-artifacts", "epics.md"),
        ("src", "shared", "packages", "pyforge-doctor", "src", "pyforge", "doctor", "cli.py"),
        ("src", "platform", "config", "flags.json"),
    ],
)
def test_the_classifier_records_a_repository_path_outside_the_package(made_up, parts) -> None:
    repository, _package, guard = made_up
    path = repository.joinpath(*parts)

    assert guard.recorded_path(path) == str(path.resolve())
    assert guard.recorded_path(os.fsencode(path)) == str(path.resolve())
    assert guard.recorded_path(str(path)) == str(path.resolve())


def test_a_relative_path_is_judged_against_the_working_directory(made_up, monkeypatch) -> None:
    repository, package, guard = made_up
    monkeypatch.chdir(repository)

    assert guard.recorded_path(Path("scripts") / "x.py") == str(repository.resolve() / "scripts" / "x.py")
    assert guard.recorded_path(None) == str(repository.resolve())  # os.listdir() lists the working directory
    monkeypatch.chdir(package)
    assert guard.recorded_path(Path("tests") / "x.py") is None


def test_the_classifier_never_records_an_allowed_or_outside_path(made_up, tmp_path) -> None:
    repository, package, guard = made_up
    core = Path(importlib.import_module("fake_core_116_4").__file__).parent
    kit = Path(importlib.import_module("fake_kit_116_4").__file__).parent
    allowed = [
        package / "tests" / "unit" / "test_x.py",
        package / "src" / "pyforge" / "marshal" / "cli" / "main.py",
        repository / ".pixi" / "envs" / "pyforge-marshal" / "lib" / "os.py",
        repository / ".steward" / "coverage" / "marshal-unit.json",
        core / "flags.py",
        kit / "flags.py",
        tmp_path / "elsewhere" / "x.py",
        repository.parent / "repo-sibling" / "x.py",
        Path("/etc/hosts"),
    ]

    assert [path for path in allowed if guard.recorded_path(path) is not None] == []
    assert guard.recorded_path(3) is None  # a file descriptor names no path
    assert guard.recorded_path(object()) is None
    assert guard.recorded_path(repository / ".steward" / "preflight-skips.log") is not None  # only coverage/


def test_the_installed_core_and_kit_are_the_allowed_modules() -> None:
    guard_module = _guard_module()
    dirs = guard_module.installed_module_dirs()

    assert guard_module.INSTALLED_MODULES == ("pyforge.core", "pyforge.testing_kit")
    for name in guard_module.INSTALLED_MODULES:
        spec = importlib.util.find_spec(name)
        assert spec is not None and spec.origin is not None, name
        assert Path(spec.origin).resolve().parent in dirs, name
    assert guard_module.installed_module_dirs(("no_such_module_116_4",)) == ()


def test_with_no_repository_around_the_package_the_guard_is_inert(tmp_path) -> None:
    _repository, package = _made_up_repository(tmp_path, git=False)
    guard = _guard_module().TreeReadGuard.around(package / "tests" / "_support" / "tree_read_guard.py")

    assert guard.repository is None
    assert guard.inert
    assert guard.recorded_path(package.parent.parent / "scripts" / "x.py") is None
    with guard.window() as reads:
        assert not guard.armed
    assert reads == []
    assert guard.header().startswith("tree-read guard: inert (no repository around ")


def test_the_hook_records_each_event_only_while_armed(made_up) -> None:
    repository, package, guard = made_up
    guard_module = _guard_module()
    script = repository / "scripts" / "x.py"
    script.parent.mkdir()
    script.write_text("X = 1\n", encoding="utf-8")
    (repository / "_bmad-output").mkdir()
    doctor = repository / "src" / "shared" / "packages" / "pyforge-doctor"
    doctor.mkdir(parents=True)
    (repository / "docs").mkdir()
    own = package / "tests" / "own.txt"
    own.write_text("own\n", encoding="utf-8")

    with guard_module.activated(guard):
        script.read_text(encoding="utf-8")  # not armed: nothing is recorded
        with guard.window() as reads:
            assert guard.armed
            script.read_text(encoding="utf-8")
            script.read_text(encoding="utf-8")  # recorded once
            os.listdir(repository / "_bmad-output")
            with os.scandir(doctor):
                pass
            glob.glob(str(repository / "docs" / "*.md"))
            own.read_text(encoding="utf-8")
            (package / "tests" / "new.txt").write_text("", encoding="utf-8")
            descriptor = os.open(script.parent, os.O_RDONLY)
            try:
                os.close(os.open(script.name, os.O_RDONLY, dir_fd=descriptor))  # relative to a dir_fd: not judged
            finally:
                os.close(descriptor)
        assert not guard.armed
        script.read_text(encoding="utf-8")

    assert guard_module.active() is not guard
    resolved = repository.resolve()
    assert reads == [
        ("open", str(resolved / "scripts" / "x.py")),
        ("os.listdir", str(resolved / "_bmad-output")),
        ("os.scandir", str(resolved / "src" / "shared" / "packages" / "pyforge-doctor")),
        ("glob.glob", str(resolved / "docs" / "*.md")),
        ("os.scandir", str(resolved / "docs")),  # the glob's own listing
        ("open", str(resolved / "scripts")),
    ]


def test_an_import_reads_its_source_but_the_import_system_listing_is_not_a_read(made_up, monkeypatch) -> None:
    repository, _package, guard = made_up
    guard_module = _guard_module()
    scripts = repository / "scripts"
    scripts.mkdir()
    (scripts / "script_116_4.py").write_text("VALUE = 4\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(scripts))
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    importlib.invalidate_caches()

    try:
        with guard_module.activated(guard), guard.window() as reads:
            assert importlib.import_module("script_116_4").VALUE == 4
    finally:
        sys.modules.pop("script_116_4", None)

    assert ("open", str(repository.resolve() / "scripts" / "script_116_4.py")) in reads
    assert [event for event, _path in reads if event in {"os.listdir", "os.scandir"}] == []


def test_the_failure_names_each_recorded_path(made_up) -> None:
    repository, _package, guard = made_up
    resolved = repository.resolve()
    message = guard.failure(
        "tests/unit/test_x.py::test_y",
        "call",
        [("open", str(resolved / "scripts" / "x.py")), ("os.listdir", str(resolved / "_bmad-output"))],
    )

    assert message.splitlines()[:3] == [
        "tree-read guard: armed: tests/unit/test_x.py::test_y read 2 repository path(s) outside "
        "src/shared/packages/pyforge-marshal during call:",
        "  scripts/x.py (open)",
        "  _bmad-output (os.listdir)",
    ]


def test_the_hook_is_added_once_per_process(monkeypatch, made_up) -> None:
    _repository, _package, guard = made_up
    guard_module = _guard_module()
    added: list[object] = []
    monkeypatch.setattr(guard_module, "_HOOKED", False)
    monkeypatch.setattr(guard_module, "_ACTIVE", guard_module.active())
    monkeypatch.setattr(sys, "addaudithook", added.append)

    guard_module.install(guard)
    guard_module.install(guard)

    assert added == [guard_module._audit]


def test_this_process_runs_under_the_conftest_s_guard_armed_for_this_test() -> None:
    guard = _guard_module().active()

    assert guard is not None, "tests/conftest.py did not install the guard"
    assert guard.package == _TESTS.parent
    assert guard.armed is (not guard.inert)  # a package-half test is armed wherever a repository is around it


def test_an_armed_test_starts_off_the_tree() -> None:
    """The conftest's ``_package_half_off_the_tree``: an armed test's working directory is outside the repository,
    and ``repo_root()`` and ``checkout_root()`` name a bare checkout holding no planning tree and no scripts.
    ``config.__file__`` is never rebound for it: coverage.py files a traced line under its frame's ``__file__``,
    so a rebound one drops ``cli/config.py`` from the coverage report."""
    from pyforge.marshal.cli import config

    guard = _guard_module().active()
    assert guard is not None
    assert config.__spec__ is not None
    assert config.__file__ == config.__spec__.origin
    if guard.inert:  # off the tree: nothing to start away from, and nothing is armed
        assert not guard.armed
        return
    repository = guard.repository
    root = config.repo_root()

    assert not Path.cwd().is_relative_to(repository)
    assert not root.is_relative_to(repository)
    assert config.checkout_root() == root
    assert sorted(path.name for path in root.iterdir()) == ["src"]
    assert (root / _PACKAGE / "src").is_dir()


_CHILD_TESTS = """
import pathlib

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[5] / "scripts" / "x.py"


@pytest.fixture(scope="module")
def module_read():
    return SCRIPT.read_text()


def test_a_package_half_test_reads():
    SCRIPT.read_text()


def test_a_module_fixture_reads(module_read):
    pass


def test_a_package_half_test_reads_nothing():
    pass


@pytest.mark.live_tree
def test_a_live_tree_test_reads():
    SCRIPT.read_text()


@pytest.mark.slow
def test_a_slow_test_reads():
    SCRIPT.read_text()
"""

_CHILD_PYPROJECT = """[tool.pytest.ini_options]
markers = ["slow: slow", "live_tree: reads the repository"]
"""


def _child_suite(tmp_path: Path, *, git: bool) -> subprocess.CompletedProcess[str]:
    """Run a child pytest over a made-up repository holding a copy of this conftest and guard."""
    repository, package = _made_up_repository(tmp_path, git=git)
    (repository / "scripts").mkdir()
    (repository / "scripts" / "x.py").write_text("X = 1\n", encoding="utf-8")
    shutil.copyfile(_GUARD_FILE, package / "tests" / "_support" / "tree_read_guard.py")
    shutil.copyfile(_CONFTEST, package / "tests" / "conftest.py")
    (package / "tests" / "test_reads.py").write_text(_CHILD_TESTS, encoding="utf-8")
    (package / "pyproject.toml").write_text(_CHILD_PYPROJECT, encoding="utf-8")
    env = {key: value for key, value in os.environ.items() if not key.startswith(("COV_CORE", "PYTEST_"))}
    env.pop("COVERAGE_PROCESS_START", None)
    return subprocess.run(  # noqa: S603 - fixed argv, no shell
        [sys.executable, "-m", "pytest", "tests", "-q", "-rfEp", "-p", "no:cacheprovider", "-p", "no:randomly"],
        cwd=package,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )


def test_the_conftest_fails_a_package_half_read_and_never_arms_a_live_tree_test(tmp_path) -> None:
    completed = _child_suite(tmp_path, git=True)
    out = completed.stdout

    assert completed.returncode == 1, out + completed.stderr
    assert out.splitlines()[0] == "tree-read guard: armed (package src/shared/packages/pyforge-marshal)", out
    assert "FAILED tests/test_reads.py::test_a_package_half_test_reads" in out
    assert "ERROR tests/test_reads.py::test_a_module_fixture_reads" in out
    assert "during call:\n  scripts/x.py (open)" in out
    assert "during setup:\n  scripts/x.py (open)" in out
    assert "PASSED tests/test_reads.py::test_a_package_half_test_reads_nothing" in out
    assert "PASSED tests/test_reads.py::test_a_live_tree_test_reads" in out
    assert "PASSED tests/test_reads.py::test_a_slow_test_reads" in out
    assert "1 failed, 3 passed, 1 error" in out


def test_with_no_repository_around_the_package_the_conftest_arms_nothing(tmp_path) -> None:
    completed = _child_suite(tmp_path, git=False)
    out = completed.stdout

    assert completed.returncode == 0, out + completed.stderr
    assert out.splitlines()[0].startswith("tree-read guard: inert (no repository around "), out
    assert "5 passed" in out
