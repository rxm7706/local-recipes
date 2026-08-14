"""`mason package` -- build and ship distributions to PyPI and conda-forge
(FR-15 - FR-24).

Seeded here, docstring-only, solely to prove AD-6's import-safety invariant
(Story 1.7): `package.py` is CFE-independent except for its future
`conda-forge` ship target, which is permitted to import `cfe` *lazily*
(nested inside a function body) but never at module scope -- a `pypi` ship
must succeed with the CFE root absent. `tests/meta/test_capability_tiers.py`
guards this file for exactly that: no module-level `cfe` import, ever.

Epic 3 supplies the real content: wheel/`.conda`/sdist construction
(`engines/pep517`, `engines/pixi`), the `twine` upload path, and the
`conda-forge` ship target that calls into `recipe.py` through the CFE port
(AD-11).

Story 3.2 adds the first real content, `build()` (FR-15, FR-21, FR-22):
drives Story 3.1's engine protocol through two new adapters,
`engines.pep517` (wheel+sdist via `pyproject-build --no-isolation`) and
`engines.pixi` (`.conda` via `pixi build`), and composes their outcomes
into one `models.PackageBuildResult`. Both adapters are called
UNCONDITIONALLY and IN SEQUENCE -- `pep517.build()` first, then
`pixi.build()` -- never gated behind an upfront joint presence check of
both engines: each adapter's own `require_engine` call inside its own
`build()` function is the ONE presence gate (spec Always boundary, mirrors
`recipe.build()`'s own per-branch gating precedent), so a project missing
only `pixi` from `PATH` still runs the (successful) `build`-engine half
before `EngineAbsentError` propagates from the `pixi` half -- "nothing
built" in the spec's own I/O matrix describes the command's overall
reported outcome (no `PackageBuildResult` is ever returned), not a claim
that the PRESENT engine's own subprocess never ran.

`project_path` is resolved to an absolute string ONCE here
(`Path(project_path).expanduser().resolve()`), before either adapter is
called, and that same resolved string is what both receive and what lands
on `PackageBuildResult.project_path` -- NOT an existence/validity check
(`Path.resolve()` succeeds on a path that does not exist, mirroring
`recipe.py::submit()`'s identical `recipe_dir` resolution -- spec Always
boundary: "No Mason-side existence/validity check on PROJECT_PATH"). This
is necessary, not cosmetic: each adapter's own subprocess runs with
`cwd=project_path` AND separately builds its own `--outdir`/`--output-dir`
argument by interpolating that SAME `project_path` string (spec Design
Notes/Tasks) -- so a relative `project_path` would have the child process
interpret that outdir argument relative to ITS OWN cwd (already `project_
path`), doubling the path (`<caller's cwd>/<project_path>/<project_path>/
dist`). Resolving once, up front, to an absolute string makes both
interpolations agree regardless of what the caller passed.

Story 3.3 adds `parse_ship_targets()`/`plan_ship()` (FR-16, FR-19, NFR-9):
the closed `--ship`/`--to` vocabulary parser and the "plan and print,
upload nothing" default -- `recipe.py::submit()`'s already-established
`ShipTargetResult(state=NOT_ATTEMPTED, reference=None, ...)` dry-run
mapping (AD-9), generalized across all three vocabulary kinds rather than
reinvented. Neither function touches an engine or a subprocess: `plan_
ship()` takes an already-built `PackageBuildResult` and reads its fields
only. No CLI wiring lands with this story (spec Never boundary) -- the
`ship` verb and its flags are Story 3.9's scope, built only after the
individual target adapters (Stories 3.4-3.6) exist to dispatch to.

Story 3.4 adds `ship_pypi()` (FR-16, FR-20, AD-9, AD-14): the first ship
target that actually uploads. It checks `TWINE_USERNAME`/`TWINE_PASSWORD`
presence in the caller's own `environ` FIRST, before calling `build()` at
all (AD-14: "Credential presence is validated before any artifact is
built"), then reuses `build()` unconditionally (FR-15, never duplicated)
and, only when both a wheel and an sdist were produced, calls the new
`engines.twine.upload()` adapter and wraps its outcome in a
`ShipTargetResult` -- the same AD-9 shape `plan_ship()`'s own dry-run
entries and `recipe.py::submit()` already use, never a second "real ship"
result shape. See `ship_pypi`'s own docstring, and this module's Design
Notes in its spec, for why it does its own `build()` call rather than
accepting an already-built `PackageBuildResult`.

Story 3.5 adds `ship_channel()` (FR-16, AD-9, AD-14): the second ship
target that actually uploads, mirroring `ship_pypi()`'s structure exactly.
It checks `PREFIX_API_KEY` presence in the caller's own `environ` FIRST,
before calling `build()` at all (same AD-14 precondition-first ordering),
then reuses `build()` unconditionally (FR-15, never duplicated) and, only
when `build_result.conda_path` is non-`None`, calls the new `engines.pixi.
upload()` adapter and wraps its outcome in a `ShipTargetResult` -- the same
AD-9 shape `ship_pypi`'s own upload path already uses. Unlike `ship_pypi`'s
`reference=upload_result.url`, `ship_channel`'s success `reference` is the
bare, caller-supplied `channel_name` (never a constructed URL) -- see
`engines.pixi`'s own module docstring for why no equivalent live-verified
URL exists to parse.

Story 3.6 adds `ship_conda_forge()` (FR-23, D-10, AD-11): the third ship
target, and the first that neither builds nor uploads anything itself --
conda-forge ships the recipe SOURCE, not the `.conda` artifact `build()`
produces (matches `plan_ship`'s own `CONDA_FORGE` message above, spec
Always boundary). It enforces D-10's two shipping preconditions itself,
which nothing else in Mason validated or reported before this story: a
`recipe_path` was given (`ShipCondaForgeRecipeMissingError`, dedicated,
zero-arg, naming `mason recipe new` as the remedy -- FR-23's "offers...
does not generate silently" is satisfied by that message alone, never an
interactive prompt or a call to `recipe.new()`, which is Story 3.9's
scope), the CFE root resolves (`CfeUnresolvedError`, REUSED rather than a
third dedicated class -- its message is already precondition-generic), and
the resolved recipe sits at EXACTLY `<cfe-root>/recipes/<name>/`
(`ShipCondaForgeRecipeLocationError`, naming both the given and the
required path) -- deliberately stricter than `recipe.py::submit()`'s own
`CFE_RECIPES_ROOT`-env-override leniency for an out-of-tree recipe (that
module's own docstring): D-10 narrows this specifically for the
ship-target boundary ("Shipping to `conda-forge` works only from a
repository where... the recipe sits at `<cfe-root>/recipes/<name>/`"), so
`mason recipe submit` stays lenient while `mason package ship --to
conda-forge` does not. All three preconditions RAISE, mirroring
`ship_pypi`/`ship_channel`'s own credential-check precedent that a
structural precondition is raised, not returned as data -- except a
`Path.resolve()` `OSError`/`ValueError` on either the recipe path or the
resolved root, which returns `ShipTargetResult(state=ShipState.FAILED,
message=str(exc))` instead, mirroring `recipe.py::submit()`'s own
established precedent for that exact resolve-failure mode. Once every
precondition passes, `from . import recipe` (lazy, module BODY only --
never module scope, the one `cfe`-adjacent import this file's opening
paragraph already reserved for this ship target, AD-6) and calls the
already-built `recipe.py::submit()` (Story 2.9) unchanged, returning its
`ShipTargetResult` VERBATIM -- no second result object is constructed for
its success/failure/pending paths (AD-11: "wraps ITS `ShipTargetResult` --
never produces a second one").

Zero `cfe` reference anywhere in this file AT MODULE SCOPE (spec Always
boundary, `tests/meta/test_capability_tiers.py` guards it): `build()`
never resolves a CFE root or interpreter, unlike every `recipe.py` verb,
Story 3.3's two new functions -- and Story 3.4's `ship_pypi()`, and Story
3.5's `ship_channel()` -- are pure and CFE-independent too, and Story
3.6's `ship_conda_forge()` above is the one exception this file's opening
paragraph always reserved: it imports `cfe` -- transitively, via `recipe`
-- but only inside its own function body, after every structural
precondition already passed, never at import time.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from packaging.version import InvalidVersion, Version

from .engines import pep517, pixi, twine
from .errors import (
    CfeUnresolvedError, InvalidShipTargetError, PackageProjectPathError,
    PackageVersionMismatchError, ShipChannelCredentialMissingError,
    ShipCondaForgeRecipeLocationError, ShipCondaForgeRecipeMissingError,
    ShipCredentialMissingError,
)
from .models import (
    PackageBuildResult, ShipState, ShipTarget, ShipTargetKind, ShipTargetResult,
)
from .resolve import resolve_cfe_root


def _versions_disagree(wheel_version: str, conda_version: str) -> bool:
    """Compare two version strings via `packaging.version.Version`, never
    raw string equality (architecture Consistency Conventions: "Versions
    are strings, compared via `packaging.version`, never string-compared").

    `wheel_version` is already PEP-440-canonicalized (`engines.pep517`'s
    own `parse_wheel_filename`-derived value), but `conda_version` is the
    RAW, unparsed segment out of the `.conda` filename (`engines.pixi`'s own
    deliberate design -- kept raw so FR-22's comparison sees exactly what
    `pixi build` named, AD-1). Comparing a canonicalized string against a
    raw one with `!=` can false-positive on formatting differences that mean
    the same version (e.g. `"1.0.0"` vs `"1.0"`). Falls back to raw string
    comparison only when either side fails to parse as a `Version`
    (`InvalidVersion`) -- conda version strings are not guaranteed to be
    strict PEP 440, so a parse failure must degrade gracefully, never crash
    the comparison itself.
    """
    try:
        return Version(wheel_version) != Version(conda_version)
    except InvalidVersion:
        return wheel_version != conda_version


def build(project_path: str, *, target: str = "library") -> PackageBuildResult:
    """Build `project_path`'s distributable artifacts: wheel+sdist via PEP
    517 (`engines.pep517`) and a `.conda` package via `pixi build`
    (`engines.pixi`) -- FR-15, FR-21.

    `target` is the caller's own `--target` value; `cli.py`'s own
    `choices=("library",)` restricts it before this function is ever
    reached (v1 scope, FR-21) -- this function applies no validation of its
    own, it is only carried through onto the returned result.

    After both adapters return, when BOTH `wheel_version` and `conda_
    version` are non-`None` and they disagree, raises `PackageVersionMismatchError`
    naming both (FR-22) -- before this function returns a result. Either
    value is `None` when its own engine's build failed (`returncode != 0`)
    or produced no artifact this module's own discovery could find; the
    comparison is skipped entirely in that case (spec I/O matrix: "One
    engine's build fails" reports data, never raises).

    See this module's own docstring for why `project_path` is resolved to
    an absolute string before either adapter runs, and why the two adapters
    are called unconditionally in sequence rather than behind an upfront
    joint presence check.

    Raises `PackageProjectPathError` (review pass, 2026-08-13) when
    `project_path` cannot even be resolved -- `Path.resolve()` itself raises
    `OSError`/`ValueError` for a pathological input (a null byte, an
    unreadable parent directory hit during symlink resolution); the
    ORIGINAL caller-supplied `project_path` names the error, since the
    resolved form was never successfully computed.
    """
    try:
        resolved_project_path = str(Path(project_path).expanduser().resolve())
    except (OSError, ValueError) as exc:
        raise PackageProjectPathError(project_path=project_path, reason=str(exc)) from None

    pep517_result = pep517.build(resolved_project_path)
    pixi_result = pixi.build(resolved_project_path)

    if (
        pep517_result.wheel_version is not None
        and pixi_result.conda_version is not None
        and _versions_disagree(pep517_result.wheel_version, pixi_result.conda_version)
    ):
        raise PackageVersionMismatchError(
            wheel_version=pep517_result.wheel_version,
            conda_version=pixi_result.conda_version,
            wheel_path=pep517_result.wheel_path,
            conda_path=pixi_result.conda_path,
        )

    return PackageBuildResult(
        target=target,
        project_path=resolved_project_path,
        wheel_path=pep517_result.wheel_path,
        sdist_path=pep517_result.sdist_path,
        conda_path=pixi_result.conda_path,
        wheel_version=pep517_result.wheel_version,
        conda_version=pixi_result.conda_version,
        pep517_returncode=pep517_result.returncode,
        pixi_returncode=pixi_result.returncode,
        pep517_stdout=pep517_result.stdout,
        pixi_stdout=pixi_result.stdout,
    )


_CHANNEL_PREFIX = "channel:"


def parse_ship_targets(value: str) -> tuple[ShipTarget, ...]:
    """Parse a comma-separated `--ship`/`--to` value into `ShipTarget`s
    (Story 3.3, FR-16, FR-19, spec AC1).

    Splits `value` on `,` and strips whitespace from each resulting token
    (including the substring after a `"channel:"` prefix, review pass,
    2026-08-13), then matches each token INDEPENDENTLY of the others
    against the three valid forms: `"pypi"`/`"conda-forge"` exactly
    (case-sensitive), or a `"channel:"`-prefixed token whose suffix
    (everything after the colon, stripped) is non-empty, which becomes
    `CHANNEL` with that stripped suffix as `channel_name`. Any other token
    -- including a bare `"channel:"` with nothing after the colon, or an
    empty token from a leading/trailing/doubled comma -- raises
    `InvalidShipTargetError`.

    An empty token is named `"<empty>"` rather than passed to
    `InvalidShipTargetError` as-is (review pass, 2026-08-13):
    `InvalidShipTargetError.__init__` itself rejects an empty `value` with
    a bare `ValueError` (its own validation-rigor guard, matching every
    other error class in `errors.py`), so a genuinely empty token -- `","`,
    `"pypi,"`, `" "` -- previously let that internal guard's `ValueError`
    escape instead of the `InvalidShipTargetError` this function's own
    docstring promises for "any other token." Every other invalid token is
    still named exactly as given.

    Returns one `ShipTarget` per token, in the order given -- no
    deduplication, no reordering: `"pypi,pypi"` returns two identical
    entries, since deciding what "duplicate" means for a future ship
    engine's own per-target output is out of this parser's scope.
    """
    targets = []
    for token in value.split(","):
        stripped = token.strip()
        if not stripped:
            raise InvalidShipTargetError("<empty>")
        if stripped == "pypi":
            targets.append(ShipTarget(kind=ShipTargetKind.PYPI, channel_name=None))
        elif stripped == "conda-forge":
            targets.append(ShipTarget(kind=ShipTargetKind.CONDA_FORGE, channel_name=None))
        elif stripped.startswith(_CHANNEL_PREFIX) and stripped[len(_CHANNEL_PREFIX):].strip():
            targets.append(
                ShipTarget(
                    kind=ShipTargetKind.CHANNEL,
                    channel_name=stripped[len(_CHANNEL_PREFIX):].strip(),
                )
            )
        else:
            raise InvalidShipTargetError(stripped)
    return tuple(targets)


def plan_ship(
    targets: Sequence[ShipTarget], build_result: PackageBuildResult,
) -> tuple[ShipTargetResult, ...]:
    """Produce the dry-run ship plan for `targets` against an already-built
    `build_result` (Story 3.3, FR-16, FR-19, spec AC1) -- print-only,
    uploads nothing.

    Reuses `models.ShipTargetResult` (`state=ShipState.NOT_ATTEMPTED,
    reference=None`), the exact dry-run shape `recipe.py::submit()` already
    produces for its own `confirm=False` branch (AD-9, this module's own
    docstring) -- never a second "plan" shape. There is no `confirm`
    parameter here at all, unlike `submit()`'s inversion: this story's own
    scope has no code path that ever ships for real (Stories 3.4-3.6 add
    the target adapters this plan describes, but this function never calls
    them, and never spawns a subprocess of its own -- `build_result` is
    already-built data, read only), so there is nothing to invert.

    `target`'s canonical string form is reconstructed from each
    `ShipTarget` (`"pypi"`, `"conda-forge"`, or `"channel:<name>"`), not
    `ShipTargetKind.value` alone -- `ShipTargetResult.target` stays a plain
    `str` (spec Always boundary; see `models.ShipTargetResult`'s own
    docstring). Each `message` names the relevant `build_result` artifact(s)
    and destination: `PYPI` names `wheel_path`/`sdist_path` and states the
    upload is irreversible (spec Always boundary, epic-3-context
    Requirements); `CONDA_FORGE` names no build artifact at all -- a
    staged-recipes submission ships the recipe SOURCE, not the built
    `.conda` binary built here -- and states a pull request would be
    opened; `CHANNEL` names `conda_path` and the channel's own name.

    Each artifact is named via `_describe_artifact` (review pass,
    2026-08-13), never a bare `!r}` interpolation of the `PackageBuildResult`
    field directly: `wheel_path`/`sdist_path`/`conda_path` are `str | None`
    (`None` when that engine's own build failed -- `models.
    PackageBuildResult`'s own docstring), and a bare `!r` would render the
    literal text `None` into the printed plan as if it were a real path,
    contradicting this story's own AC ("the plan names every target, every
    artifact, and every destination").
    """
    results = []
    for target in targets:
        if target.kind is ShipTargetKind.PYPI:
            canonical = "pypi"
            message = (
                f"would upload {_describe_artifact(build_result.wheel_path, 'wheel')} and "
                f"{_describe_artifact(build_result.sdist_path, 'sdist')} to PyPI; "
                "this upload is irreversible"
            )
        elif target.kind is ShipTargetKind.CONDA_FORGE:
            canonical = "conda-forge"
            message = "would open a conda-forge/staged-recipes pull request"
        elif target.kind is ShipTargetKind.CHANNEL:
            canonical = f"{_CHANNEL_PREFIX}{target.channel_name}"
            message = (
                f"would upload {_describe_artifact(build_result.conda_path, '.conda package')} "
                f"to channel {target.channel_name!r}"
            )
        else:
            raise AssertionError(f"unhandled ShipTargetKind: {target.kind!r}")
        results.append(
            ShipTargetResult(
                target=canonical, state=ShipState.NOT_ATTEMPTED, reference=None, message=message,
            )
        )
    return tuple(results)


def _describe_artifact(path: str | None, label: str) -> str:
    """Render one `plan_ship` artifact reference: the path itself when
    built, or a `"no {label} was built"` note when `None` (review pass,
    2026-08-13) -- see `plan_ship`'s own docstring for why a bare `!r}` of a
    possibly-`None` path is wrong here."""
    return repr(path) if path is not None else f"no {label} was built"


_REQUIRED_SHIP_PYPI_CREDENTIALS = ("TWINE_USERNAME", "TWINE_PASSWORD")


def ship_pypi(
    project_path: str, *, environ: Mapping[str, str], target: str = "library",
) -> ShipTargetResult:
    """Build and upload `project_path`'s wheel+sdist to PyPI via `twine`
    (Story 3.4, FR-16, FR-20, AD-9, AD-14).

    Checks `TWINE_USERNAME`/`TWINE_PASSWORD` presence in `environ` FIRST, as
    this function's very first action, before `build()` is ever called
    (architecture AD-14: "Credential presence is validated before any
    artifact is built") -- raises `ShipCredentialMissingError` naming
    whichever of the two are absent or empty (stripped). Only presence is
    checked: neither value is ever read into a variable used for anything
    but this truthiness check, logged, or stored on the returned object
    (NFR-2) -- the credentials reach `twine` only via the subprocess's own
    inherited environment, inside `engines.twine.upload` (see that module's
    own docstring).

    When both credentials are present, calls `build(project_path,
    target=target)` unconditionally (FR-15, reused rather than duplicated
    -- this module's own docstring explains why `ship_pypi` owns this
    sequence itself rather than accepting an already-built
    `PackageBuildResult`). Only when the returned `PackageBuildResult`
    carries a non-`None` `wheel_path` AND a non-`None` `sdist_path` does
    this function go on to call `engines.twine.upload((wheel_path,
    sdist_path))`; otherwise -- one or both engines failed to produce an
    artifact -- it returns a `FAILED` result directly, without `twine.
    upload` ever being called (spec I/O matrix). That "nothing built" case's
    `message` is `build_result.pep517_stdout` -- the wrapped `build` engine
    is the one responsible for the wheel/sdist this ship target needs, so
    its own stdout is the wrapped tool's own field, verbatim (AD-1,
    `models.ShipTargetResult.message`'s own docstring contract).

    On a zero `upload()` returncode, returns `ShipTargetResult(target=
    "pypi", state=ShipState.TERMINAL, reference=upload_result.url,
    message=upload_result.stdout)`. On a nonzero `upload()` returncode,
    returns `ShipTargetResult(state=ShipState.FAILED, reference=None,
    message=upload_result.stdout)` -- AD-4: a tool that RAN but failed is
    data, never raised (mirrors `recipe.py::submit()`'s own data-vs-raise
    split).

    `EngineAbsentError` (twine, or either build engine, not on `PATH`),
    `ShipUploadTimeoutError` (the upload exceeds its timeout), and anything
    else `build()` itself already raises (`PackageVersionMismatchError`,
    `PackageProjectPathError`) all propagate un-caught out of this function
    -- these are structural preconditions, not this call's own execution
    outcome (spec Always boundary, same split `build()` already established
    for its own two engines).
    """
    missing = [
        name
        for name in _REQUIRED_SHIP_PYPI_CREDENTIALS
        if not environ.get(name, "").strip()
    ]
    if missing:
        raise ShipCredentialMissingError(missing)

    build_result = build(project_path, target=target)

    if build_result.wheel_path is None or build_result.sdist_path is None:
        return ShipTargetResult(
            target="pypi",
            state=ShipState.FAILED,
            reference=None,
            message=build_result.pep517_stdout,
        )

    upload_result = twine.upload((build_result.wheel_path, build_result.sdist_path))

    if upload_result.returncode != 0:
        return ShipTargetResult(
            target="pypi", state=ShipState.FAILED, reference=None, message=upload_result.stdout,
        )

    return ShipTargetResult(
        target="pypi",
        state=ShipState.TERMINAL,
        reference=upload_result.url,
        message=upload_result.stdout,
    )


_REQUIRED_SHIP_CHANNEL_CREDENTIALS = ("PREFIX_API_KEY",)


def ship_channel(
    project_path: str, channel_name: str, *, environ: Mapping[str, str], target: str = "library",
) -> ShipTargetResult:
    """Build and upload `project_path`'s `.conda` package to the named
    private conda channel `channel_name` via `pixi upload prefix` (Story
    3.5, FR-16, AD-9, AD-14).

    Checks `PREFIX_API_KEY` presence in `environ` FIRST, as this function's
    very first action, before `build()` is ever called (architecture AD-14:
    "Credential presence is validated before any artifact is built") --
    raises `ShipChannelCredentialMissingError` naming it when absent or
    empty (stripped). Only presence is checked: the value is never read
    into a variable used for anything but this truthiness check, logged, or
    stored on the returned object (NFR-2) -- the credential reaches `pixi`
    only via the subprocess's own inherited environment, inside `engines.
    pixi.upload` (see that module's own docstring).

    When the credential is present, calls `build(project_path,
    target=target)` unconditionally (FR-15, reused rather than duplicated
    -- mirrors `ship_pypi`'s own identical rationale for owning this
    sequence itself rather than accepting an already-built
    `PackageBuildResult`). The canonical target string is `f"channel:
    {channel_name}"` (matches `plan_ship`'s own canonical reconstruction).
    Only when the returned `PackageBuildResult` carries a non-`None`
    `conda_path` does this function go on to call `engines.pixi.upload(
    conda_path, channel_name)`; otherwise -- the `.conda` engine failed or
    produced nothing -- it returns a `FAILED` result directly, without
    `pixi.upload` ever being called (spec I/O matrix). That "nothing built"
    case's `message` is `build_result.pixi_stdout` -- the wrapped `pixi`
    build engine is the one responsible for the `.conda` artifact this ship
    target needs, so its own stdout is the wrapped tool's own field,
    verbatim (AD-1, `models.ShipTargetResult.message`'s own docstring
    contract).

    On a zero `upload()` returncode, returns `ShipTargetResult(target=
    f"channel:{channel_name}", state=ShipState.TERMINAL,
    reference=channel_name, message=upload_result.stdout)` -- `reference`
    is the bare `channel_name`, never a constructed URL (spec Always
    boundary; see `engines.pixi`'s own module docstring for why no
    equivalent live-verified URL exists to parse). On a nonzero `upload()`
    returncode, returns `ShipTargetResult(state=ShipState.FAILED,
    reference=None, message=upload_result.stdout)` -- AD-4: a tool that RAN
    but failed is data, never raised (mirrors `ship_pypi`'s own identical
    nonzero-upload handling), so a caller shipping to other targets in the
    same invocation is unaffected by this one's failure.

    `EngineAbsentError` (pixi, or either build engine, not on `PATH`),
    `ShipChannelUploadTimeoutError` (the upload exceeds its timeout), and
    anything else `build()` itself already raises
    (`PackageVersionMismatchError`, `PackageProjectPathError`) all
    propagate un-caught out of this function -- these are structural
    preconditions, not this call's own execution outcome (spec Always
    boundary, same split `build()`/`ship_pypi()` already established).
    """
    missing = [
        name
        for name in _REQUIRED_SHIP_CHANNEL_CREDENTIALS
        if not environ.get(name, "").strip()
    ]
    if missing:
        raise ShipChannelCredentialMissingError(missing)

    build_result = build(project_path, target=target)

    canonical = f"{_CHANNEL_PREFIX}{channel_name}"

    if build_result.conda_path is None:
        return ShipTargetResult(
            target=canonical,
            state=ShipState.FAILED,
            reference=None,
            message=build_result.pixi_stdout,
        )

    upload_result = pixi.upload(build_result.conda_path, channel_name)

    if upload_result.returncode != 0:
        return ShipTargetResult(
            target=canonical, state=ShipState.FAILED, reference=None, message=upload_result.stdout,
        )

    return ShipTargetResult(
        target=canonical,
        state=ShipState.TERMINAL,
        reference=channel_name,
        message=upload_result.stdout,
    )


def ship_conda_forge(
    recipe_path: str | None,
    *,
    environ: Mapping[str, str],
    cfe_root_arg: str | None,
    cfe_python_arg: str | None,
    cfe_timeout_arg: float | None,
    start_directory: Path,
) -> ShipTargetResult:
    """Ship `recipe_path` to conda-forge/staged-recipes by delegating to
    `recipe.py::submit()` (Story 3.6, FR-23, D-10, AD-11).

    Validates D-10's two shipping preconditions itself, in order, BEFORE
    `recipe.py` (and therefore `cfe`) is ever imported:

    1. `recipe_path` must be given (not `None`, not blank) -- raises
       `ShipCondaForgeRecipeMissingError()` otherwise, naming `mason recipe
       new` as the remedy (this module's own docstring: satisfies FR-23's
       "offers... does not generate silently" with no interactive prompt).
    2. The CFE root must resolve (`resolve_cfe_root`) -- raises
       `CfeUnresolvedError()` otherwise, reused rather than a dedicated
       class (its message is already precondition-generic).

    `recipe_dir = Path(recipe_path).expanduser().resolve()`,
    `root_dir = resolved_root.root.expanduser().resolve()`, and
    `expected_dir = (root_dir / "recipes" / recipe_dir.name).resolve()` are
    all resolved inside one `try`/`except (OSError, ValueError)`: a
    pathological input (a symlink loop, an embedded NUL byte) returns
    `ShipTargetResult(target="conda-forge", state=ShipState.FAILED,
    message=str(exc))` instead of raising -- mirrors `recipe.py::submit()`'s
    own established precedent for this exact resolve-failure mode (its own
    docstring, review pass 2026-08-12). `expected_dir` is independently
    `.resolve()`d, not merely composed from the already-resolved `root_dir`
    (review pass, 2026-08-13): if `<root>/recipes` were itself a symlink,
    an un-resolved composition would not reflect the true physical path,
    risking a false mismatch against the independently-resolved
    `recipe_dir` for an otherwise-valid symlinked placement.

    3. `recipe_dir` must equal `expected_dir` exactly -- raises
       `ShipCondaForgeRecipeLocationError(str(recipe_dir), str(expected_dir))`
       otherwise, naming both paths (this module's own docstring:
       deliberately stricter than `submit()`'s own
       `CFE_RECIPES_ROOT`-env-override leniency, per D-10).

    Only once all three preconditions pass does this function `from . import
    recipe` (lazy, AD-6 -- this file's opening paragraph reserves exactly
    this one exception) and call `recipe.submit(str(recipe_dir),
    confirm=True, prepare_only=False, cfe_root_arg=cfe_root_arg,
    cfe_python_arg=cfe_python_arg, cfe_timeout_arg=cfe_timeout_arg,
    environ=environ, start_directory=start_directory)`, returning its
    `ShipTargetResult` UNCHANGED -- no second result object is ever
    constructed here (AD-11). `confirm=True` and `prepare_only=False` are
    both hardcoded: no CLI flag exists yet to set either (spec Never
    boundary -- `prepare_only` wiring and the `--to conda-forge` CLI surface
    are both Story 3.9's scope), and `ship_conda_forge` never builds
    anything itself -- conda-forge ships the recipe SOURCE, not a `.conda`
    artifact (matches `plan_ship`'s own `CONDA_FORGE` message above).
    """
    if not recipe_path or not recipe_path.strip():
        raise ShipCondaForgeRecipeMissingError()

    resolved_root = resolve_cfe_root(cfe_root_arg, environ, start_directory)
    if resolved_root.root is None:
        raise CfeUnresolvedError()

    try:
        recipe_dir = Path(recipe_path).expanduser().resolve()
        root_dir = resolved_root.root.expanduser().resolve()
        expected_dir = (root_dir / "recipes" / recipe_dir.name).resolve()
    except (OSError, ValueError) as exc:
        return ShipTargetResult(
            target="conda-forge", state=ShipState.FAILED, reference=None, message=str(exc),
        )

    if recipe_dir != expected_dir:
        raise ShipCondaForgeRecipeLocationError(str(recipe_dir), str(expected_dir))

    from . import recipe  # lazy -- AD-6, see module docstring

    return recipe.submit(
        str(recipe_dir),
        confirm=True,
        prepare_only=False,
        cfe_root_arg=cfe_root_arg,
        cfe_python_arg=cfe_python_arg,
        cfe_timeout_arg=cfe_timeout_arg,
        environ=environ,
        start_directory=start_directory,
    )
