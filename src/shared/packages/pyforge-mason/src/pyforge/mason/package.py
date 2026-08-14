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

Zero `cfe` reference anywhere in this file (spec Always boundary,
`tests/meta/test_capability_tiers.py` guards it): `build()` never resolves
a CFE root or interpreter, unlike every `recipe.py` verb, and Story 3.3's
two new functions -- and Story 3.4's `ship_pypi()`, and Story 3.5's `ship_
channel()` -- are pure and CFE-independent too.

Story 3.7 adds idempotence-by-interrogation to both `ship_pypi()` and `ship_
channel()` (FR-18, AD-10), plus `build_ship_receipt()` (AD-9). Neither ship
function previously asked its target "is this already shipped?" before
uploading -- a retry of an already-successful ship either crashed on PyPI's
own duplicate-file rejection or silently re-uploaded. Both functions now
interrogate their target strictly AFTER `build()` (the interrogation needs
the just-built version) and strictly BEFORE the upload call, never before
the existing credential check (AD-14 precedent, unchanged) -- `ship_pypi`
calls the new `pypi_index.version_exists()`; `ship_channel` calls the new
`engines.pixi.search()`. Both follow the identical three-way outcome: found
-> skip the upload, return `TERMINAL` with the pre-existing reference;
not-found -> the upload proceeds exactly as before this story; undeterminable
(network error, timeout, absent tool) -> return `PENDING` naming the reason,
the mutating upload call is never made (AD-10: "never an assumption in
either direction"). `build_ship_receipt()` aggregates however many
`ShipTargetResult`s a caller already produced into one `models.ShipReceipt`
-- no `ship()` multi-target dispatcher and no CLI wiring land with this
story either (spec Never boundary); this function is the tested, ready-to-
call primitive for whichever future caller (Story 3.9's `cli.py` `ship`
verb) reaches it after that story's own scope lands.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from packaging.utils import parse_wheel_filename
from packaging.version import InvalidVersion, Version

from . import pypi_index
from .engines import pep517, pixi, twine
from .errors import (
    InvalidShipTargetError, PackageProjectPathError, PackageVersionMismatchError,
    ShipChannelCredentialMissingError, ShipCredentialMissingError,
)
from .models import (
    PackageBuildResult, ShipReceipt, ShipState, ShipTarget, ShipTargetKind, ShipTargetResult,
)


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
    this function proceed at all; otherwise -- one or both engines failed to
    produce an artifact -- it returns a `FAILED` result directly, without
    `twine.upload` ever being called (spec I/O matrix). That "nothing built"
    case's `message` is `build_result.pep517_stdout` -- the wrapped `build`
    engine is the one responsible for the wheel/sdist this ship target
    needs, so its own stdout is the wrapped tool's own field, verbatim
    (AD-1, `models.ShipTargetResult.message`'s own docstring contract).

    Story 3.7 (FR-18, AD-10): once a wheel+sdist exist, BEFORE calling
    `engines.twine.upload`, this function re-derives the PyPI project name
    from `build_result.wheel_path`'s own filename via `packaging.utils.
    parse_wheel_filename` (the same parse `engines.pep517` already trusts --
    `PackageBuildResult` itself carries no separate name field) and calls
    `pypi_index.version_exists(name, build_result.wheel_version)`. Three-way
    outcome: `True` (PyPI already has this exact name/version) -> the upload
    is SKIPPED and this function returns `TERMINAL` with `reference=
    f"https://pypi.org/project/{name}/{version}/"` (mirrors the shape
    `twine`'s own "View at:" URL already produces); `False` (PyPI does not
    have it) -> `twine.upload` runs exactly as before this story; `None`
    (the interrogation itself could not be completed -- a timeout, a DNS
    failure, an unexpected HTTP status) -> this function returns `PENDING`
    naming the reason, and `twine.upload` is NEVER called (AD-10: "never an
    assumption in either direction" -- an undeterminable interrogation must
    not be treated as "not shipped yet").

    Once past that interrogation with a `False` (not yet shipped) result,
    calls `engines.twine.upload((wheel_path, sdist_path))`. On a zero
    `upload()` returncode, returns `ShipTargetResult(target="pypi",
    state=ShipState.TERMINAL, reference=upload_result.url,
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
    for its own two engines). `pypi_index.version_exists` itself never
    raises (its own docstring), so no new exception surface is introduced by
    this story's interrogation step.
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

    pypi_name, _, _, _ = parse_wheel_filename(Path(build_result.wheel_path).name)
    exists = pypi_index.version_exists(str(pypi_name), build_result.wheel_version)
    if exists is True:
        return ShipTargetResult(
            target="pypi",
            state=ShipState.TERMINAL,
            reference=f"https://pypi.org/project/{pypi_name}/{build_result.wheel_version}/",
            message=(
                f"pypi already has {pypi_name} {build_result.wheel_version}; "
                "upload was not attempted"
            ),
        )
    if exists is None:
        return ShipTargetResult(
            target="pypi",
            state=ShipState.PENDING,
            reference=None,
            message=(
                f"could not determine whether pypi already has {pypi_name} "
                f"{build_result.wheel_version} (network error, timeout, or an "
                "unexpected response); upload was not attempted"
            ),
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
    `conda_path` does this function proceed at all; otherwise -- the
    `.conda` engine failed or produced nothing -- it returns a `FAILED`
    result directly, without `pixi.upload` ever being called (spec I/O
    matrix). That "nothing built" case's `message` is `build_result.
    pixi_stdout` -- the wrapped `pixi` build engine is the one responsible
    for the `.conda` artifact this ship target needs, so its own stdout is
    the wrapped tool's own field, verbatim (AD-1, `models.ShipTargetResult.
    message`'s own docstring contract).

    Story 3.7 (FR-18, AD-10): once a `.conda` artifact exists, BEFORE
    calling `engines.pixi.upload`, this function re-derives the package name
    from `build_result.conda_path`'s own filename via the same `stem.
    rsplit("-", 2)` technique `engines.pixi.build` already uses (module
    docstring; `PackageBuildResult` carries no separate name field) and
    calls `engines.pixi.search(name, build_result.conda_version,
    channel_name)`. Three-way outcome: `True` (the channel already has this
    exact name/version) -> the upload is SKIPPED and this function returns
    `TERMINAL` with `reference=channel_name` -- the bare channel name, never
    a constructed URL, matching this function's own existing non-
    interrogation `TERMINAL` precedent below (Story 3.5); `False` (the
    channel does not have it) -> `pixi.upload` runs exactly as before this
    story; `None` (the interrogation itself could not be completed -- `pixi`
    absent, a timeout, an unrecognized failure) -> this function returns
    `PENDING` naming the reason, and `pixi.upload` is NEVER called (AD-10:
    "never an assumption in either direction").

    Once past that interrogation with a `False` (not yet shipped) result,
    calls `engines.pixi.upload(conda_path, channel_name)`. On a zero
    `upload()` returncode, returns `ShipTargetResult(target=
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
    `engines.pixi.search` itself never raises (its own docstring), so no new
    exception surface is introduced by this story's interrogation step.
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

    conda_name, _, _ = Path(build_result.conda_path).name.removesuffix(".conda").rsplit("-", 2)
    exists = pixi.search(conda_name, build_result.conda_version, channel_name)
    if exists is True:
        return ShipTargetResult(
            target=canonical,
            state=ShipState.TERMINAL,
            reference=channel_name,
            message=(
                f"channel {channel_name!r} already has {conda_name} "
                f"{build_result.conda_version}; upload was not attempted"
            ),
        )
    if exists is None:
        return ShipTargetResult(
            target=canonical,
            state=ShipState.PENDING,
            reference=None,
            message=(
                f"could not determine whether channel {channel_name!r} already "
                f"has {conda_name} {build_result.conda_version} (pixi absent, "
                "network error, timeout, or an unexpected response); upload "
                "was not attempted"
            ),
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


def build_ship_receipt(results: Sequence[ShipTargetResult]) -> ShipReceipt:
    """Aggregate `results` -- however many `ShipTargetResult`s a caller
    already produced across one or more ship targets -- into one
    `models.ShipReceipt` (Story 3.7, AD-9).

    `targets` is `results` as given, converted to a `tuple`, in the same
    order and with no deduplication (mirrors `ShipReceipt.targets`'s own
    docstring). `ok` is computed exactly once, here: `not any(r.state is
    ShipState.FAILED for r in results)` -- `NOT_ATTEMPTED`/`PENDING`/
    `TERMINAL` all count as success for this aggregate (AD-9); only an
    actual `FAILED` target flips it to `False`. An empty `results` produces
    `ShipReceipt(targets=(), ok=True)` -- vacuously true, mirroring Python's
    own `not any(())` -- this function performs no minimum-length validation
    of its own (a future `ship()` dispatcher's own zero-target input is not
    this function's business to reject).

    This function is CFE-independent and calls no engine adapter of its own
    (module docstring): it reads the `state` field off each already-built
    `ShipTargetResult` and nothing else.
    """
    targets = tuple(results)
    return ShipReceipt(targets=targets, ok=not any(r.state is ShipState.FAILED for r in targets))
