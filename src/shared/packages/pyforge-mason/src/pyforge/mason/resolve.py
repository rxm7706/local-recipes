"""The CFE-root resolution chain (AD-5, FR-2), and the interpreter-selection
chain (AD-5, FR-3, D-7) that picks a Python capable of running CFE scripts.

Nothing in Mason yet locates a conda-forge-expert installation; `resolve.py`
is the one pure, independently-testable place that answers "where is CFE,
and how did we find it." `resolve_cfe_root` is a pure function over
`(explicit, environ, start_directory)` implementing FR-2's four-step,
first-match-wins chain: explicit flag -> `MASON_CFE_ROOT` environment
variable -> upward filesystem walk from `start_directory` for the CFE
public-wrapper directory -> not-found. The returned `ResolvedCfeRoot` names
which step matched, so a later caller (Stories 1.7, 1.8) never needs to
re-resolve.

Steps 1 and 2 match on the presence of a non-whitespace value alone -- a
whitespace-only value is treated as absent, mirroring `cli.py`'s
`_resolve_str` convention -- and are NOT validated against the marker
directory; only step 3 (the walk) checks for it.

`environ` is always an explicit `Mapping[str, str]` parameter, never a
direct `os.environ` read (AD-5's purity rule): this is what keeps the
function pure and every test hermetic with no monkeypatch/env-isolation
needed. `doctor.py` (Story 1.8) is the actual call site: `cli.py` passes
`getattr(ns, "cfe_root", None)`, `os.environ`, and `Path.cwd()` into
`doctor.build_report`, which calls `resolve_cfe_root` with them as part of
composing the full `mason doctor` report.

`resolve.py` performs filesystem *reads* only -- no writes, network, or
process spawns -- and never raises: an upward walk that reaches the
filesystem root without a match returns a not-found outcome, not an
exception.

`_ENV_CFE_ROOT` duplicates the literal already private to `cli.py` (used
there only for `--cfe-root`'s help text). Dependency direction is
inward-only (AD-2) -- `resolve.py` cannot import a name from `cli.py` --
so this module owns its own copy for the actual env-var lookup: two copies
of one string literal, in exactly two places, both changed together if the
name ever changes.

`resolve_cfe_interpreter` (Story 1.6) is a second, independent pure chain in
this same file: `--cfe-python` flag -> `MASON_CFE_PYTHON` environment
variable -> `sys.executable`. It exists because the process's own
interpreter is wrong for running CFE scripts inside a lean, `mason`-only
environment (D-7) -- CFE needs its own import floor (`pyyaml`, `requests`,
`packaging`, `truststore`, `ruamel.yaml`, `conda-forge-metadata`), which a
`no-default-feature` Mason environment does not carry. Unlike the root
chain, this chain has no not-found case: `sys.executable` always exists and
is always a valid terminal fallback, so `resolve_cfe_interpreter` always
returns a match. Whether that interpreter actually satisfies CFE's import
floor is a *separate*, subprocess-based question answered by
`cfe.py::probe_import_floor` -- AD-5 forbids process spawns here, so that
check cannot live in this module (see `cfe.py`'s module docstring).
`_ENV_CFE_PYTHON` mirrors the `_ENV_CFE_ROOT` duplication pattern above, for
the same inward-only dependency-direction reason.

Story 2.6 adds a third, independent pure function in this same file:
`detect_native_build_config`, mirroring the native build script's own
five-way host-detection table (`uname -s`/`uname -m`, mapped to one of
`linux64`/`linux_aarch64`/`osxarm64`/`osx64`/`win64`) via
`platform.system()`/`platform.machine()` instead of shelling out to `uname`
itself (AD-5 forbids process spawns here; `platform.system`/`platform.
machine` are OS metadata lookups, not subprocess invocations). It has no
not-found terminal *type* the way `resolve_cfe_root` does -- an
unrecognized host simply returns `None` rather than raising, since
`cfe.py`'s `build_native` adapter must still run its script and let it
report its own failure via exit code, never a guessed config.
"""

from __future__ import annotations

import platform
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ResolvedCfeRoot:
    """The outcome of `resolve_cfe_root`: the resolved root, or `None` if
    unresolved, plus which chain step produced it (AD-5)."""

    root: Path | None
    step: str


STEP_FLAG = "flag"
"""`explicit` (the `--cfe-root` flag) was non-whitespace."""

STEP_ENVIRONMENT = "environment"
"""`environ[_ENV_CFE_ROOT]` (`MASON_CFE_ROOT`) was non-whitespace."""

STEP_CWD_WALK = "cwd-walk"
"""The upward walk from `start_directory` found the CFE marker directory."""

STEP_NOT_FOUND = "not-found"
"""No step matched: the walk reached the filesystem root with no marker."""

_ENV_CFE_ROOT = "MASON_CFE_ROOT"

_CFE_MARKER = Path(".claude/scripts/conda-forge-expert")
"""Relative to a candidate root: the CFE public-wrapper directory whose
presence (as a directory, not a file) marks that candidate as the CFE root."""


def resolve_cfe_root(
    explicit: str | None,
    environ: Mapping[str, str],
    start_directory: Path,
) -> ResolvedCfeRoot:
    """Resolve the CFE root: flag -> environment -> upward walk -> not-found.

    First-match-wins (FR-2, AD-5). `explicit` and the `MASON_CFE_ROOT` entry
    of `environ` match on the presence of a non-whitespace value alone, with
    no check against the marker directory. Only the walk step tests
    `<level>/.claude/scripts/conda-forge-expert` for `is_dir()` -- which is
    also `False` when nothing exists at that path, so a separate existence
    check would be redundant -- starting at `start_directory` (resolved to
    an absolute path first, so a relative caller-supplied directory still
    reaches the real filesystem root rather than stopping early at a
    lexical `.`) and continuing through each `.parent` until the filesystem
    root is reached (`path.parent == path`) with no match, at which point a
    not-found outcome is returned, never an exception.
    """
    if explicit is not None and explicit.strip():
        return ResolvedCfeRoot(root=Path(explicit.strip()), step=STEP_FLAG)

    env_value = environ.get(_ENV_CFE_ROOT)
    if env_value is not None and env_value.strip():
        return ResolvedCfeRoot(root=Path(env_value.strip()), step=STEP_ENVIRONMENT)

    # .resolve() first: a relative start_directory's .parent chain hits a
    # lexical stopping point (e.g. Path("a/b").parent.parent == Path(".") ==
    # Path(".").parent) long before the real filesystem root, which would
    # silently truncate the walk.
    candidate = start_directory.resolve()
    while True:
        if (candidate / _CFE_MARKER).is_dir():
            return ResolvedCfeRoot(root=candidate, step=STEP_CWD_WALK)
        parent = candidate.parent
        if parent == candidate:
            break
        candidate = parent

    return ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND)


@dataclass(frozen=True)
class ResolvedCfeInterpreter:
    """The outcome of `resolve_cfe_interpreter`: the selected interpreter
    path, plus which chain step produced it (AD-5).

    `path` is `str`, not `Path` -- unlike `ResolvedCfeRoot.root`, it mirrors
    `sys.executable`'s own type and is passed straight through to
    `subprocess.run`'s argv (`cfe.py`), never filesystem-joined."""

    path: str
    step: str


STEP_RUNNING_INTERPRETER = "running-interpreter"
"""Neither the flag nor the environment variable matched: fell through to
`sys.executable`, the guaranteed-match terminal step of this chain."""

_ENV_CFE_PYTHON = "MASON_CFE_PYTHON"


def resolve_cfe_interpreter(
    explicit: str | None,
    environ: Mapping[str, str],
) -> ResolvedCfeInterpreter:
    """Resolve the interpreter used to run CFE scripts: flag -> environment
    -> `sys.executable` (FR-3, D-7).

    First-match-wins, mirroring `resolve_cfe_root`'s whitespace convention:
    `explicit` and `environ[_ENV_CFE_PYTHON]` match on the presence of a
    non-whitespace value alone. Unlike `resolve_cfe_root`, this chain has no
    not-found terminal state -- `sys.executable` always exists, so the
    fallback always matches and this function never raises.
    """
    if explicit is not None and explicit.strip():
        return ResolvedCfeInterpreter(path=explicit.strip(), step=STEP_FLAG)

    env_value = environ.get(_ENV_CFE_PYTHON)
    if env_value is not None and env_value.strip():
        return ResolvedCfeInterpreter(path=env_value.strip(), step=STEP_ENVIRONMENT)

    return ResolvedCfeInterpreter(path=sys.executable, step=STEP_RUNNING_INTERPRETER)


_LINUX_X86_64_MACHINES = frozenset({"x86_64", "amd64"})
_AARCH64_MACHINES = frozenset({"aarch64", "arm64"})
"""Alternate `platform.machine()` spellings for the same architecture,
mirroring the native build script's own `uname -m` alternation (e.g.
`Linux/x86_64|Linux/amd64`) -- different libc/kernel builds report either
spelling for the identical 64-bit x86/ARM architecture."""


def detect_native_build_config() -> str | None:
    """Detect the native-build platform-variant config name for the CURRENT
    host, mirroring the native build script's own five-way `uname`-based
    case table (FR-9). Pure -- no process spawn, no filesystem I/O -- and
    non-overridable: there is no parameter, matching the spec Never
    boundary that native mode has no `--platform`/config override (the
    wrapped script has no such flag either).

    Returns `None` for a host this table does not recognize -- never a
    guess. `cfe.py`'s `build_native` adapter still runs its script
    unconditionally on an unrecognized host and lets it report its own
    failure via exit code; this function's only job is telling that adapter
    what `build_artifacts/<config>/` to report, and reporting nothing beats
    reporting a directory the script never actually used.
    """
    system = platform.system()
    machine = platform.machine()

    if system == "Linux":
        if machine in _LINUX_X86_64_MACHINES:
            return "linux64"
        if machine in _AARCH64_MACHINES:
            return "linux_aarch64"
        return None
    if system == "Darwin":
        if machine in _AARCH64_MACHINES:
            return "osxarm64"
        if machine == "x86_64":
            return "osx64"
        return None
    if system == "Windows":
        return "win64"
    return None


# --- Story 44.7: factory island path resolution (fnd:CAP-4) ----------------

_FACTORY_RECIPES_PREFIX = "factory/recipes/"
"""Recipe paths under the python-foundry factory island use this prefix."""

_ENV_FOUNDRY_ROOT = "MASON_FOUNDRY_ROOT"
"""Explicit foundry git root when building `factory/recipes/<r>` from local-recipes."""

_ENV_FACTORY_ROOT = "MASON_FACTORY_ROOT"
"""Set by `recipe.build()` for CFE's native-build wrapper — never read by Mason."""

_FACTORY_PIXI = Path("factory/pixi.toml")
_FACTORY_LOCK = Path("factory/pixi.lock")


@dataclass(frozen=True)
class ResolvedFactoryIsland:
    """A resolved factory-island recipe build target (Story 44.7).

    `recipe_path` is the absolute filesystem path passed to CFE's native
    build script; `factory_root` is the island's own root (`…/factory/`)."""

    foundry_root: Path
    factory_root: Path
    recipe_path: Path


def is_factory_recipe_path(recipe_path: str) -> bool:
    """Return ``True`` when ``recipe_path`` names a factory-island recipe."""
    normalized = recipe_path.replace("\\", "/").lstrip("./")
    return normalized.startswith(_FACTORY_RECIPES_PREFIX)


def resolve_foundry_root(
    explicit: str | None,
    environ: Mapping[str, str],
    start_directory: Path,
) -> Path | None:
    """Resolve the python-foundry git root: flag/env -> upward walk -> ``None``.

    The walk marker is ``factory/pixi.toml`` plus ``factory/pixi.lock`` at
    the same directory level — the island lock the spec requires (R-17b).
    """
    if explicit is not None and explicit.strip():
        return Path(explicit.strip()).resolve()

    env_value = environ.get(_ENV_FOUNDRY_ROOT)
    if env_value is not None and env_value.strip():
        return Path(env_value.strip()).resolve()

    candidate = start_directory.resolve()
    while True:
        if (candidate / _FACTORY_PIXI).is_file() and (candidate / _FACTORY_LOCK).is_file():
            return candidate
        parent = candidate.parent
        if parent == candidate:
            break
        candidate = parent
    return None


def resolve_factory_island(
    recipe_path: str,
    *,
    foundry_root_arg: str | None,
    environ: Mapping[str, str],
    start_directory: Path,
) -> ResolvedFactoryIsland | None:
    """Resolve ``factory/recipes/<r>`` to an absolute recipe under foundry.

    Returns ``None`` when ``recipe_path`` is not a factory-island path.
    Raises ``FactoryIslandMissingError`` when the path is factory-shaped but
    the island lock or recipe target is absent.
    """
    if not is_factory_recipe_path(recipe_path):
        return None

    from .errors import FactoryIslandMissingError

    foundry = resolve_foundry_root(foundry_root_arg, environ, start_directory)
    if foundry is None:
        raise FactoryIslandMissingError(
            "the python-foundry root could not be resolved for a factory/recipes/ "
            "build: set --foundry-root, set MASON_FOUNDRY_ROOT, or run from "
            "within a clone that contains factory/pixi.toml and factory/pixi.lock"
        )

    factory_root = foundry / "factory"
    if not (factory_root / "pixi.toml").is_file() or not (factory_root / "pixi.lock").is_file():
        raise FactoryIslandMissingError(
            f"factory island lock missing under {factory_root}: expected "
            "factory/pixi.toml and factory/pixi.lock (Story 44.7 / R-17b)"
        )

    normalized = recipe_path.replace("\\", "/").lstrip("./")
    slug = normalized.removeprefix(_FACTORY_RECIPES_PREFIX)
    if not slug or slug.endswith("/"):
        raise FactoryIslandMissingError(
            f"factory recipe path must name a recipe under factory/recipes/: got {recipe_path!r}"
        )

    abs_recipe = (factory_root / "recipes" / slug).resolve()
    if not abs_recipe.exists():
        raise FactoryIslandMissingError(f"factory recipe not found at {abs_recipe} (resolved from {recipe_path!r})")

    return ResolvedFactoryIsland(
        foundry_root=foundry,
        factory_root=factory_root,
        recipe_path=abs_recipe,
    )
