"""`mason environment` -- resolve conflicting worlds into one lockfile
(FR-25 - FR-29).

Seeded docstring-only (Story 1.7) solely to prove AD-6's import-safety
invariant: unlike `package.py`, `environment.py` has no CFE-dependent target
at all -- every verb here must import cleanly with no CFE anywhere on the
filesystem. `tests/meta/test_capability_tiers.py` guards this file for
exactly that: no module-level `cfe` import, ever. Importing `engines.
condalock` here does not violate that guard -- that module itself has no
CFE dependency (Story 4.1).

Story 4.3 adds `lock()`, the `mason environment lock` use-case: a thin
wrapper around `engines.condalock.lock()`, mirroring `package.py::build()`'s
own engine-wrapping shape. Manifest auto-discovery (Story 4.2) was not yet
built at that point, so `lock()` required its caller to supply manifest
paths explicitly -- `cli.py`'s own `manifest_path` positional (`nargs="+"`)
enforced "at least one" before this function was ever reached.

Story 4.4 adds `check()`, the `mason environment check` use-case (FR-25,
FR-27, FR-29): CI's own companion to `lock()` above -- a thin wrapper around
`engines.condalock.check()`, mirroring `lock()`'s own platform-parsing/
wrapping shape verbatim. Unlike `lock()`, `check()`'s own engine-layer
counterpart validates `lockfile_path`'s existence itself
(`EnvironmentLockfileMissingError`, raised before any subprocess spawns) --
this function does no additional pre-validation of its own, matching
`lock()`'s established "no Mason-side pre-validation" default for every
other path argument.

Story 4.2 adds `discover_manifests()`: manifest auto-discovery is now built.
`cli.py`'s `manifest_path` positional is `nargs="*"` on both verbs -- when
the caller gives none, `cli.py` calls `discover_manifests(Path.cwd())`
itself and feeds the result into `lock()`/`check()` unchanged; neither
function's own signature changed for this. `discover_manifests` is a pure
function over an explicit `directory` (never `Path.cwd()` internally, no
recursion, no upward walk -- unlike `resolve.py`'s CFE-root walk) that
locates the four manifest kinds in that one directory alone.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from .engines import condalock
from .errors import EnvironmentManifestsNotFoundError
from .models import CheckResult, LockResult

_MANIFEST_FILENAMES: tuple[str, ...] = (
    "pyproject.toml",
    "environment.yml",
    "requirements*.txt",
    "pixi.toml",
)
"""The four literal patterns `discover_manifests` searches for, in the
fixed order it checks them -- also the exact `filenames` named by
`EnvironmentManifestsNotFoundError` when none match."""


def discover_manifests(directory: Path) -> tuple[str, ...]:
    """Locate the four supported manifest kinds in `directory` alone (Story
    4.2, FR-25) -- never recursive, never walking upward, unlike
    `resolve.py::resolve_cfe_root`'s CFE-root walk.

    Checks, in this fixed order (each drawn from `_MANIFEST_FILENAMES`, the
    single source of truth this function and `EnvironmentManifestsNotFoundError`
    both read -- review pass, 2026-08-15): `pyproject.toml`, `environment.yml`,
    then every `directory.glob("requirements*.txt")` match sorted lexically,
    then `pixi.toml`. Existence is `.is_file()` on every match, including the
    glob's -- a directory or symlink-to-directory that happens to match
    `requirements*.txt` is excluded, not silently handed to the engine
    (review pass, 2026-08-15: the glob branch previously skipped this check
    unlike the three literal-name branches). The glob is the only wildcard
    this function ever applies (spec Intent: the one pattern named by the
    AC, not a general glob). Each match is returned as `str(directory / name)`.

    Pure: no I/O beyond reading `directory` itself, and takes an explicit
    `Path` rather than reading `Path.cwd()` internally -- mirrors
    `resolve.py::resolve_cfe_root`'s `start_directory` parameter precedent;
    `cli.py` supplies `Path.cwd()` at its own call site.

    Raises `EnvironmentManifestsNotFoundError` naming `directory` and all
    four literal patterns searched when nothing matches -- the only case
    this function ever raises for.
    """
    pyproject, environment_yml, requirements_glob, pixi = _MANIFEST_FILENAMES

    found: list[str] = []

    if (directory / pyproject).is_file():
        found.append(str(directory / pyproject))
    if (directory / environment_yml).is_file():
        found.append(str(directory / environment_yml))
    found.extend(str(path) for path in sorted(directory.glob(requirements_glob)) if path.is_file())
    if (directory / pixi).is_file():
        found.append(str(directory / pixi))

    if not found:
        raise EnvironmentManifestsNotFoundError(str(directory), _MANIFEST_FILENAMES)

    return tuple(found)


def lock(manifest_paths: Sequence[str], output_path: str, *, platforms: str | None = None) -> LockResult:
    """Resolve `manifest_paths` into a lockfile at `output_path` via
    `engines.condalock.lock()` (FR-25, FR-27, FR-29).

    `platforms` is the caller's own raw `--platform` value: a comma-separated
    string (`cli.py`'s own precedent for a repeatable flag, matching `--to`'s
    established idiom -- spec Always boundary) or `None` when the flag was
    omitted. Split and stripped into a tuple here, in the use-case layer, not
    in `cli.py` -- mirrors `package.py::parse_ship_targets`'s own
    raw-string-in/parsed-in-the-use-case-layer split for `--to`. Empty
    tokens are silently dropped (no closed platform vocabulary exists for
    Mason to validate against, spec Never boundary): an invalid or malformed
    platform value surfaces as `conda-lock`'s own non-zero returncode
    (AD-4), never a Mason-side check. `platforms=None` or `""` both resolve
    to `()`, letting `conda-lock`'s own default apply (FR-27) -- Mason never
    invents one.

    No pre-validation of `manifest_paths` existence or `output_path`'s
    parent directory (spec Always boundary, mirrors `engines.condalock.
    lock()`'s own identical precedent) -- a bad path surfaces as
    `conda-lock`'s own non-zero returncode, never raised here.

    Raises `EngineAbsentError`/`EnvironmentLockTimeoutError` (both already
    defined, Story 4.1), propagated unchanged from `engines.condalock.
    lock()`.
    """
    if platforms:
        parsed_platforms = tuple(stripped for token in platforms.split(",") if (stripped := token.strip()))
    else:
        parsed_platforms = ()

    result = condalock.lock(manifest_paths, output_path, platforms=parsed_platforms)

    return LockResult(
        manifest_paths=tuple(manifest_paths),
        output_path=output_path,
        platforms=parsed_platforms,
        engine_name=result.engine_name,
        engine_version=result.engine_version,
        returncode=result.returncode,
        stdout=result.stdout,
    )


def check(lockfile_path: str, manifest_paths: Sequence[str], *, platforms: str | None = None) -> CheckResult:
    """Report whether `lockfile_path` is stale relative to `manifest_paths`
    via `engines.condalock.check()` (FR-25, FR-27, FR-29).

    `platforms` parsing is IDENTICAL to `lock()`'s own, above (verbatim-
    mirrored, spec Always boundary): the caller's own raw `--platform`
    value, a comma-separated string or `None` when the flag was omitted,
    split and stripped into a tuple here, in the use-case layer -- see
    `lock()`'s own docstring for the full rationale, not repeated here.
    Empty tokens are silently dropped the same way; `platforms=None` or
    `""` both resolve to `()`, letting `conda-lock`'s own default apply,
    never invented by Mason.

    No pre-validation of `manifest_paths` existence (spec Always boundary,
    mirrors `lock()`'s identical precedent) -- a bad manifest path surfaces
    as `conda-lock`'s own non-zero returncode, never raised here.
    `lockfile_path`'s existence IS validated, but by `engines.condalock.
    check()` itself, not here (spec Always boundary: `Environment
    LockfileMissingError` is raised at the engine layer, before any
    subprocess spawns) -- this function does not duplicate that check.

    Raises `EngineAbsentError`/`EnvironmentLockfileMissingError`/
    `EnvironmentLockfileMalformedError`/`EnvironmentCheckTimeoutError` (all
    already defined, Story 4.1/4.4), propagated unchanged from
    `engines.condalock.check()` -- the same four `cli.py`'s own dispatch
    branch documents (review pass, 2026-08-15 second: this list omitted
    `EnvironmentLockfileMalformedError`, so the use-case layer and the
    dispatch layer published different contracts for the same call). Never
    raises for a stale verdict (AD-4) -- `stale` is DATA on the returned
    `CheckResult`.
    """
    if platforms:
        parsed_platforms = tuple(stripped for token in platforms.split(",") if (stripped := token.strip()))
    else:
        parsed_platforms = ()

    result = condalock.check(lockfile_path, manifest_paths, platforms=parsed_platforms)

    return CheckResult(
        lockfile_path=lockfile_path,
        manifest_paths=tuple(manifest_paths),
        platforms=parsed_platforms,
        stale=result.stale,
        engine_name=result.engine_name,
        engine_version=result.engine_version,
        returncode=result.returncode,
        stdout=result.stdout,
    )
