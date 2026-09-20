"""Story 1.5 -- the CFE-root resolution chain: precedence, whitespace
handling, walk termination, and the marker-must-be-a-directory edge case,
all against synthetic `tmp_path` trees (AD-5).

Story 1.6 extends this file with `resolve_cfe_interpreter`'s coverage: the
same flag -> environment -> fallback precedence, but with no not-found
terminal state -- `sys.executable` is a guaranteed match.

Story 2.6 extends this file with `detect_native_build_config`'s coverage:
the five known `platform.system()`/`platform.machine()` host pairs (plus
alternate machine spellings for the same architecture) and one unrecognized
pair -> `None`, via `monkeypatch` on `platform.system`/`platform.machine`
(never a real `uname` invocation -- the function itself never spawns a
process)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from pyforge.mason.resolve import (
    STEP_CWD_WALK,
    STEP_ENVIRONMENT,
    STEP_FLAG,
    STEP_NOT_FOUND,
    STEP_RUNNING_INTERPRETER,
    ResolvedCfeInterpreter,
    ResolvedCfeRoot,
    detect_native_build_config,
    resolve_cfe_interpreter,
    resolve_cfe_root,
)

_ENV_KEY = "MASON_CFE_ROOT"
_ENV_PYTHON_KEY = "MASON_CFE_PYTHON"


def _make_marker(base: Path) -> None:
    """Create the CFE marker directory under `base`."""
    (base / ".claude" / "scripts" / "conda-forge-expert").mkdir(parents=True)


# --- I/O & Edge-Case Matrix ------------------------------------------------


def test_flag_wins_over_env_and_walk(tmp_path):
    """Flag wins over env and walk."""
    result = resolve_cfe_root("/x", {_ENV_KEY: "/y"}, tmp_path)
    assert result == ResolvedCfeRoot(root=Path("/x"), step=STEP_FLAG)


def test_env_wins_over_walk(tmp_path):
    """Env wins over walk -- even when the walk would otherwise match at
    `start_directory` itself."""
    _make_marker(tmp_path)
    result = resolve_cfe_root(None, {_ENV_KEY: "/y"}, tmp_path)
    assert result == ResolvedCfeRoot(root=Path("/y"), step=STEP_ENVIRONMENT)


def test_whitespace_only_flag_and_env_fall_through_to_walk(tmp_path):
    """Whitespace-only flag/env falls through."""
    _make_marker(tmp_path)
    result = resolve_cfe_root("   ", {_ENV_KEY: ""}, tmp_path)
    assert result == ResolvedCfeRoot(root=tmp_path, step=STEP_CWD_WALK)


def test_walk_finds_the_marker_n_levels_up(tmp_path):
    """Walk finds the marker N levels up."""
    _make_marker(tmp_path)
    start = tmp_path / "a" / "b"
    start.mkdir(parents=True)

    result = resolve_cfe_root(None, {}, start)

    assert result == ResolvedCfeRoot(root=tmp_path, step=STEP_CWD_WALK)


def test_walk_exhausts_to_filesystem_root(tmp_path):
    """Walk exhausts to filesystem root: an isolated synthetic tree with the
    marker absent at every ancestor resolves to not-found, never raising."""
    start = tmp_path / "a" / "b"
    start.mkdir(parents=True)

    result = resolve_cfe_root(None, {}, start)

    assert result == ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND)


def test_marker_path_exists_but_is_a_file_not_a_directory(tmp_path):
    """A regular file at the marker path does not match; the walk continues
    upward past it to a real marker directory higher up."""
    # tmp_path/a/.claude/scripts/conda-forge-expert is a FILE.
    file_level = tmp_path / "a"
    marker_parent = file_level / ".claude" / "scripts"
    marker_parent.mkdir(parents=True)
    (marker_parent / "conda-forge-expert").write_text("not a directory\n")

    # tmp_path itself has a real marker DIRECTORY.
    _make_marker(tmp_path)

    start = file_level / "b"
    start.mkdir(parents=True)

    result = resolve_cfe_root(None, {}, start)

    assert result == ResolvedCfeRoot(root=tmp_path, step=STEP_CWD_WALK)


# --- Additional cases named by the Tasks & Acceptance section -------------


def test_flag_only_match_no_env_no_marker(tmp_path):
    """Flag-only match: no env var present at all, no marker anywhere."""
    result = resolve_cfe_root("/explicit/root", {}, tmp_path)
    assert result == ResolvedCfeRoot(root=Path("/explicit/root"), step=STEP_FLAG)


def test_env_only_match_no_flag(tmp_path):
    """Env-only match: no flag given (`explicit=None`), no marker needed --
    step 2 is not validated against the marker directory."""
    result = resolve_cfe_root(None, {_ENV_KEY: "/env/root"}, tmp_path)
    assert result == ResolvedCfeRoot(root=Path("/env/root"), step=STEP_ENVIRONMENT)


def test_start_directory_itself_has_the_marker_zero_level_walk(tmp_path):
    """A `start_directory` that itself has the marker resolves at that same
    level -- a zero-level walk, no `.parent` traversal needed."""
    _make_marker(tmp_path)
    result = resolve_cfe_root(None, {}, tmp_path)
    assert result == ResolvedCfeRoot(root=tmp_path, step=STEP_CWD_WALK)


@pytest.mark.parametrize(
    ("explicit", "environ"),
    [
        ("/x", {_ENV_KEY: "/y"}),
        (None, {_ENV_KEY: "/y"}),
        ("   ", {_ENV_KEY: ""}),
        (None, {}),
        ("", {}),
        (None, {_ENV_KEY: "   "}),
    ],
)
def test_resolve_cfe_root_never_raises(tmp_path, explicit, environ):
    """No input combination in these scenarios raises -- an exhausted walk
    returns a not-found outcome, not an exception."""
    result = resolve_cfe_root(explicit, environ, tmp_path)
    assert isinstance(result, ResolvedCfeRoot)


def test_relative_start_directory_still_reaches_the_real_filesystem_root(tmp_path, monkeypatch):
    """A relative `start_directory` must not stop at a lexical `.` -- it is
    resolved to absolute first, so the walk still reaches the marker (or the
    real filesystem root) rather than truncating after one or two `.parent`
    hops (`Path("a/b").parent.parent == Path(".") == Path(".").parent`)."""
    _make_marker(tmp_path)
    (tmp_path / "a" / "b").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    result = resolve_cfe_root(None, {}, Path("a/b"))

    assert result == ResolvedCfeRoot(root=tmp_path.resolve(), step=STEP_CWD_WALK)


def test_resolved_cfe_root_is_frozen():
    """`ResolvedCfeRoot` is `@dataclass(frozen=True)` -- immutable once
    constructed, matching every other shared shape in this codebase."""
    result = ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND)
    with pytest.raises(AttributeError):
        result.step = STEP_FLAG  # type: ignore[misc]


# --- Story 1.6: resolve_cfe_interpreter I/O & Edge-Case Matrix -------------


def test_interpreter_flag_wins_over_env_and_default():
    """Flag wins over env and default."""
    result = resolve_cfe_interpreter("/x/py", {_ENV_PYTHON_KEY: "/y/py"})
    assert result == ResolvedCfeInterpreter(path="/x/py", step=STEP_FLAG)


def test_interpreter_env_wins_over_running_interpreter():
    """Env wins over `sys.executable`."""
    result = resolve_cfe_interpreter(None, {_ENV_PYTHON_KEY: "/y/py"})
    assert result == ResolvedCfeInterpreter(path="/y/py", step=STEP_ENVIRONMENT)


def test_interpreter_whitespace_only_flag_and_env_fall_through():
    """Whitespace-only flag/env falls through to `sys.executable`."""
    result = resolve_cfe_interpreter("  ", {_ENV_PYTHON_KEY: ""})
    assert result == ResolvedCfeInterpreter(path=sys.executable, step=STEP_RUNNING_INTERPRETER)


def test_interpreter_nothing_given_falls_through_to_running_interpreter():
    """Nothing given at all falls through to `sys.executable`."""
    result = resolve_cfe_interpreter(None, {})
    assert result == ResolvedCfeInterpreter(path=sys.executable, step=STEP_RUNNING_INTERPRETER)


def test_interpreter_empty_string_flag_and_env_fall_through():
    """An empty string (distinct from whitespace-only) falls through to
    `sys.executable` -- review pass (2026-08-09): this input value was
    previously exercised only by the never-raises parametrization, which
    asserts no crash but not the actual outcome."""
    result = resolve_cfe_interpreter("", {})
    assert result == ResolvedCfeInterpreter(path=sys.executable, step=STEP_RUNNING_INTERPRETER)


def test_interpreter_flag_only_match_no_env():
    """Flag-only match: no env var present at all."""
    result = resolve_cfe_interpreter("/explicit/py", {})
    assert result == ResolvedCfeInterpreter(path="/explicit/py", step=STEP_FLAG)


def test_interpreter_env_only_match_no_flag():
    """Env-only match: no flag given (`explicit=None`)."""
    result = resolve_cfe_interpreter(None, {_ENV_PYTHON_KEY: "/env/py"})
    assert result == ResolvedCfeInterpreter(path="/env/py", step=STEP_ENVIRONMENT)


@pytest.mark.parametrize(
    ("explicit", "environ"),
    [
        ("/x/py", {_ENV_PYTHON_KEY: "/y/py"}),
        (None, {_ENV_PYTHON_KEY: "/y/py"}),
        ("  ", {_ENV_PYTHON_KEY: ""}),
        (None, {}),
        ("", {}),
        (None, {_ENV_PYTHON_KEY: "   "}),
    ],
)
def test_resolve_cfe_interpreter_never_raises(explicit, environ):
    """No input combination raises -- `sys.executable` is a guaranteed-match
    terminal step, so there is no not-found case at all."""
    result = resolve_cfe_interpreter(explicit, environ)
    assert isinstance(result, ResolvedCfeInterpreter)


def test_resolved_cfe_interpreter_is_frozen():
    """`ResolvedCfeInterpreter` is `@dataclass(frozen=True)` -- immutable
    once constructed, matching `ResolvedCfeRoot` and every other shared
    shape in this codebase."""
    result = ResolvedCfeInterpreter(path=sys.executable, step=STEP_RUNNING_INTERPRETER)
    with pytest.raises(AttributeError):
        result.step = STEP_FLAG  # type: ignore[misc]


# --- Story 2.6: detect_native_build_config -- I/O & Edge-Case Matrix -------


@pytest.mark.parametrize(
    ("system", "machine", "expected"),
    [
        ("Linux", "x86_64", "linux64"),
        ("Linux", "amd64", "linux64"),
        ("Linux", "aarch64", "linux_aarch64"),
        ("Linux", "arm64", "linux_aarch64"),
        ("Darwin", "arm64", "osxarm64"),
        ("Darwin", "aarch64", "osxarm64"),
        ("Darwin", "x86_64", "osx64"),
        ("Windows", "AMD64", "win64"),
        ("Windows", "ARM64", "win64"),
    ],
)
def test_detect_native_build_config_maps_every_known_host_pair(
    monkeypatch,
    system,
    machine,
    expected,
):
    monkeypatch.setattr("pyforge.mason.resolve.platform.system", lambda: system)
    monkeypatch.setattr("pyforge.mason.resolve.platform.machine", lambda: machine)

    assert detect_native_build_config() == expected


@pytest.mark.parametrize(
    ("system", "machine"),
    [
        ("SunOS", "sparc64"),
        ("Linux", "sparc64"),
        ("Darwin", "sparc64"),
        ("FreeBSD", "amd64"),
    ],
)
def test_detect_native_build_config_returns_none_for_an_unrecognized_host(
    monkeypatch,
    system,
    machine,
):
    """Never a guess (spec Never boundary): an unmapped `platform.system()`/
    `platform.machine()` pair returns `None` rather than a default config --
    the native build script still runs and reports its own failure via exit
    code."""
    monkeypatch.setattr("pyforge.mason.resolve.platform.system", lambda: system)
    monkeypatch.setattr("pyforge.mason.resolve.platform.machine", lambda: machine)

    assert detect_native_build_config() is None


def test_detect_native_build_config_never_raises(monkeypatch):
    monkeypatch.setattr("pyforge.mason.resolve.platform.system", lambda: "PlanNine")
    monkeypatch.setattr("pyforge.mason.resolve.platform.machine", lambda: "mips")

    assert detect_native_build_config() is None


def test_detect_native_build_config_spawns_no_process(monkeypatch):
    """AD-5: this function must never shell out to `uname` itself -- proven
    by making `platform.system`/`platform.machine` the only two calls
    permitted to answer, with no `subprocess` import anywhere in
    `resolve.py` (also enforced structurally by
    `tests/meta/test_dependency_direction.py`)."""
    calls: list[str] = []
    monkeypatch.setattr(
        "pyforge.mason.resolve.platform.system",
        lambda: calls.append("system") or "Linux",
    )
    monkeypatch.setattr(
        "pyforge.mason.resolve.platform.machine",
        lambda: calls.append("machine") or "x86_64",
    )

    assert detect_native_build_config() == "linux64"
    assert calls == ["system", "machine"]
