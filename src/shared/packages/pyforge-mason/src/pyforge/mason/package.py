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
    CfeUnresolvedError,
    InvalidShipTargetError,
    MasonError,
    PackageProjectPathError,
    PackageVersionMismatchError,
    ShipChannelCredentialMissingError,
    ShipCondaForgeRecipeLocationError,
    ShipCondaForgeRecipeMissingError,
    ShipCredentialMissingError,
)
from .models import (
    PackageBuildResult,
    ShipReceipt,
    ShipState,
    ShipTarget,
    ShipTargetKind,
    ShipTargetResult,
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

_TESTPYPI_REPOSITORY_URL = "https://test.pypi.org/legacy/"
"""PyPI's own documented TestPyPI upload URL (Story 3.9, FR-24, FR-50,
AD-26) -- a fixed constant, never a flag or environment variable (D-13
forbids a config file as the alternative twine mechanism; spec Always
boundary: "no flag, no env var"). `ship()`'s own `_ship_one` closure
forwards this verbatim as `ship_pypi`'s `repository_url` argument for every
`PYPI_TEST` target -- the ONE place this constant is read."""


def parse_ship_targets(value: str) -> tuple[ShipTarget, ...]:
    """Parse a comma-separated `--ship`/`--to` value into `ShipTarget`s
    (Story 3.3, FR-16, FR-19, spec AC1; Story 3.9/FR-50 adds the fourth
    form below).

    Splits `value` on `,` and strips whitespace from each resulting token
    (including the substring after a `"channel:"` prefix, review pass,
    2026-08-13), then matches each token INDEPENDENTLY of the others
    against the four valid forms: `"pypi"`/`"pypi-test"`/`"conda-forge"`
    exactly (case-sensitive), or a `"channel:"`-prefixed token whose suffix
    (everything after the colon, stripped) is non-empty, which becomes
    `CHANNEL` with that stripped suffix as `channel_name`. `"pypi-test"` is
    a new bare literal (Story 3.9), mirroring `"pypi"`/`"conda-forge"`'s own
    handling exactly -- no prefix, no dedup, same precedent as the other
    three. Any other token -- including a bare `"channel:"` with nothing
    after the colon, or an empty token from a leading/trailing/doubled
    comma -- raises `InvalidShipTargetError`.

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
        elif stripped == "pypi-test":
            targets.append(ShipTarget(kind=ShipTargetKind.PYPI_TEST, channel_name=None))
        elif stripped == "conda-forge":
            targets.append(ShipTarget(kind=ShipTargetKind.CONDA_FORGE, channel_name=None))
        elif stripped.startswith(_CHANNEL_PREFIX) and stripped[len(_CHANNEL_PREFIX) :].strip():
            targets.append(
                ShipTarget(
                    kind=ShipTargetKind.CHANNEL,
                    channel_name=stripped[len(_CHANNEL_PREFIX) :].strip(),
                )
            )
        else:
            raise InvalidShipTargetError(stripped)
    return tuple(targets)


def _canonical_target_name(target: ShipTarget) -> str:
    """Reconstruct one `ShipTarget`'s canonical string form: `"pypi"`,
    `"pypi-test"`, `"conda-forge"`, or `"channel:<name>"` (extracted from
    `plan_ship`'s own Story 3.3 inline logic, Story 3.9) -- never
    `ShipTargetKind.value` alone, since `ShipTargetResult.target` stays a
    plain `str` (spec Always boundary; see `models.ShipTargetResult`'s own
    docstring).

    The ONE place this reconstruction is written: `plan_ship` (below) calls
    it to build each dry-run entry's `target` field, and `ship()`'s own
    `_ship_one` closure calls it again to name a target whose function
    raised a `MasonError` -- both need the identical canonical string for
    the identical `ShipTarget`, so this is shared rather than
    reimplemented a second time for the dispatcher.
    """
    if target.kind is ShipTargetKind.PYPI:
        return "pypi"
    if target.kind is ShipTargetKind.PYPI_TEST:
        return "pypi-test"
    if target.kind is ShipTargetKind.CONDA_FORGE:
        return "conda-forge"
    if target.kind is ShipTargetKind.CHANNEL:
        return f"{_CHANNEL_PREFIX}{target.channel_name}"
    raise AssertionError(f"unhandled ShipTargetKind: {target.kind!r}")  # pragma: no cover


def plan_ship(
    targets: Sequence[ShipTarget],
    build_result: PackageBuildResult,
) -> tuple[ShipTargetResult, ...]:
    """Produce the dry-run ship plan for `targets` against an already-built
    `build_result` (Story 3.3, FR-16, FR-19, spec AC1; Story 3.9/FR-50 adds
    the `PYPI_TEST` branch below) -- print-only, uploads nothing.

    Reuses `models.ShipTargetResult` (`state=ShipState.NOT_ATTEMPTED,
    reference=None`), the exact dry-run shape `recipe.py::submit()` already
    produces for its own `confirm=False` branch (AD-9, this module's own
    docstring) -- never a second "plan" shape. There is no `confirm`
    parameter here at all, unlike `submit()`'s inversion: this function
    never calls a target adapter, and never spawns a subprocess of its own
    -- `build_result` is already-built data, read only -- so there is
    nothing to invert. (`ship()`, Story 3.9, is the caller that DOES invert
    on `confirm`; this function itself still does not.)

    `target`'s canonical string form is reconstructed via
    `_canonical_target_name` (extracted here, Story 3.9, from this
    function's own former inline logic) rather than `ShipTargetKind.value`
    alone -- `ShipTargetResult.target` stays a plain `str` (spec Always
    boundary; see `models.ShipTargetResult`'s own docstring). Each `message`
    names the relevant `build_result` artifact(s) and destination: `PYPI`
    names `wheel_path`/`sdist_path` and states the upload is irreversible
    (spec Always boundary, epic-3-context Requirements); `PYPI_TEST` names
    the SAME two artifacts and states the upload targets TestPyPI, but
    NEVER claims irreversibility (FR-50) -- that claim stays exclusive to
    the real `PYPI` target, since a TestPyPI upload is trivially
    re-attempted under a fresh version and carries none of the real
    index's permanence; `CONDA_FORGE` names no build artifact at all -- a
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
        canonical = _canonical_target_name(target)
        if target.kind is ShipTargetKind.PYPI:
            message = (
                f"would upload {_describe_artifact(build_result.wheel_path, 'wheel')} and "
                f"{_describe_artifact(build_result.sdist_path, 'sdist')} to PyPI; "
                "this upload is irreversible"
            )
        elif target.kind is ShipTargetKind.PYPI_TEST:
            message = (
                f"would upload {_describe_artifact(build_result.wheel_path, 'wheel')} and "
                f"{_describe_artifact(build_result.sdist_path, 'sdist')} to TestPyPI"
            )
        elif target.kind is ShipTargetKind.CONDA_FORGE:
            message = "would open a conda-forge/staged-recipes pull request"
        elif target.kind is ShipTargetKind.CHANNEL:
            message = (
                f"would upload {_describe_artifact(build_result.conda_path, '.conda package')} "
                f"to channel {target.channel_name!r}"
            )
        else:
            raise AssertionError(f"unhandled ShipTargetKind: {target.kind!r}")
        results.append(
            ShipTargetResult(
                target=canonical,
                state=ShipState.NOT_ATTEMPTED,
                reference=None,
                message=message,
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
    project_path: str,
    *,
    environ: Mapping[str, str],
    target: str = "library",
    repository_url: str | None = None,
) -> ShipTargetResult:
    """Build and upload `project_path`'s wheel+sdist to PyPI -- or, with
    `repository_url` given, to TestPyPI -- via `twine` (Story 3.4, FR-16,
    FR-20, AD-9, AD-14; Story 3.9/FR-24/FR-50/AD-26 adds `repository_url`).

    Checks `TWINE_USERNAME`/`TWINE_PASSWORD` presence in `environ` FIRST, as
    this function's very first action, before `build()` is ever called
    (architecture AD-14: "Credential presence is validated before any
    artifact is built") -- raises `ShipCredentialMissingError` naming
    whichever of the two are absent or empty (stripped). Only presence is
    checked: neither value is ever read into a variable used for anything
    but this truthiness check, logged, or stored on the returned object
    (NFR-2) -- the credentials reach `twine` only via the subprocess's own
    inherited environment, inside `engines.twine.upload` (see that module's
    own docstring). Note: TestPyPI has its own, separate credential pair in
    reality, but this function checks the SAME `TWINE_USERNAME`/
    `TWINE_PASSWORD` names for both -- AD-26's "identical code path" leaves
    credential resolution to the caller's own environment, exactly as it
    was before this story; no new credential vocabulary is introduced here.

    `canonical` -- `"pypi-test"` when `repository_url` is given, else
    `"pypi"` -- is computed ONCE, immediately after the credential check,
    and used at all three `ShipTargetResult(target=...)` construction sites
    below (Story 3.9) -- the ONLY difference between a real PyPI ship and a
    TestPyPI rehearsal anywhere in this function's own logic; every other
    line runs identically for both.

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
    missing = [name for name in _REQUIRED_SHIP_PYPI_CREDENTIALS if not environ.get(name, "").strip()]
    if missing:
        raise ShipCredentialMissingError(missing)

    canonical = "pypi-test" if repository_url is not None else "pypi"

    build_result = build(project_path, target=target)

    if build_result.wheel_path is None or build_result.sdist_path is None:
        return ShipTargetResult(
            target=canonical,
            state=ShipState.FAILED,
            reference=None,
            message=build_result.pep517_stdout,
        )

    pypi_name, _, _, _ = parse_wheel_filename(Path(build_result.wheel_path).name)
    exists = pypi_index.version_exists(str(pypi_name), build_result.wheel_version)
    if exists is True:
        return ShipTargetResult(
            target=canonical,
            state=ShipState.TERMINAL,
            reference=f"https://pypi.org/project/{pypi_name}/{build_result.wheel_version}/",
            message=(f"pypi already has {pypi_name} {build_result.wheel_version}; upload was not attempted"),
        )
    if exists is None:
        return ShipTargetResult(
            target=canonical,
            state=ShipState.PENDING,
            reference=None,
            message=(
                f"could not determine whether pypi already has {pypi_name} "
                f"{build_result.wheel_version} (network error, timeout, or an "
                "unexpected response); upload was not attempted"
            ),
        )

    upload_result = twine.upload(
        (build_result.wheel_path, build_result.sdist_path),
        repository_url=repository_url,
    )

    if upload_result.returncode != 0:
        return ShipTargetResult(
            target=canonical,
            state=ShipState.FAILED,
            reference=None,
            message=upload_result.stdout,
        )

    return ShipTargetResult(
        target=canonical,
        state=ShipState.TERMINAL,
        reference=upload_result.url,
        message=upload_result.stdout,
    )


_REQUIRED_SHIP_CHANNEL_CREDENTIALS = ("PREFIX_API_KEY",)


def ship_channel(
    project_path: str,
    channel_name: str,
    *,
    environ: Mapping[str, str],
    target: str = "library",
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
    missing = [name for name in _REQUIRED_SHIP_CHANNEL_CREDENTIALS if not environ.get(name, "").strip()]
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
            target=canonical,
            state=ShipState.FAILED,
            reference=None,
            message=upload_result.stdout,
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

    Enforces D-10's two shipping preconditions itself -- the CFE root
    resolves (#2 below), and the recipe sits at `<cfe-root>/recipes/<name>/`
    (#3 below) -- behind one precursor check of its own, that a recipe path
    was supplied at all (#1). Three gates, two of them D-10's; all three run
    in this order BEFORE `recipe.py` (and therefore `cfe`) is ever imported:

    1. `recipe_path` must be given (not `None`, not blank) -- raises
       `ShipCondaForgeRecipeMissingError()` otherwise, naming `mason recipe
       new` as the remedy (this module's own docstring: satisfies FR-23's
       "offers... does not generate silently" with no interactive prompt).
       This is `ship_conda_forge`'s own precursor, not one of D-10's two.
    2. The CFE root must resolve (`resolve_cfe_root`) -- raises
       `CfeUnresolvedError()` otherwise, reused rather than a dedicated
       class (its message is already precondition-generic). D-10's first.

    `recipe_dir = Path(recipe_path.strip()).expanduser().resolve()`,
    `root_dir = resolved_root.root.expanduser().resolve()`, and
    `expected_dir = (root_dir / "recipes" / recipe_dir.name).resolve()` are
    all resolved inside one `try`/`except (OSError, ValueError,
    RuntimeError)`: a pathological input returns `ShipTargetResult(
    target="conda-forge", state=ShipState.FAILED, message=str(exc))`
    instead of raising -- mirrors `recipe.py::submit()`'s own established
    precedent for this exact resolve-failure mode (its own docstring,
    review pass 2026-08-12). `OSError` covers a symlink loop, `ValueError`
    an embedded NUL byte, and `RuntimeError` (review pass, 2026-08-13) the
    case `Path.expanduser()` raises -- it is NOT an `OSError` subclass for
    this failure -- when a leading `~`/`~user` cannot be expanded (unknown
    user, or `HOME` unset). That last one is reachable through `root_dir`
    as well as `recipe_path`: `resolve_cfe_root`'s flag/environment steps
    pass a `--cfe-root ~foo/cfe` value straight through unvalidated, and
    the root is expanded HERE and in `doctor.py` only -- `submit()` never
    expands a root, so this trigger has no pre-existing counterpart there.
    `recipe_path` is `.strip()`ped before `Path()` for the same reason gate
    #1 strips before its blank test: without it a leading-space value such
    as `"  /abs/foo"` is not absolute (its first path component is the
    spaces) and would silently resolve relative to the cwd.
    `expected_dir` is independently `.resolve()`d, not merely composed from
    the already-resolved `root_dir` (review pass, 2026-08-13): if
    `<root>/recipes` were itself a symlink, an un-resolved composition
    would not reflect the true physical path, risking a false mismatch
    against the independently-resolved `recipe_dir` for an otherwise-valid
    symlinked placement.

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
        recipe_dir = Path(recipe_path.strip()).expanduser().resolve()
        root_dir = resolved_root.root.expanduser().resolve()
        expected_dir = (root_dir / "recipes" / recipe_dir.name).resolve()
    except (OSError, ValueError, RuntimeError) as exc:
        return ShipTargetResult(
            target="conda-forge",
            state=ShipState.FAILED,
            reference=None,
            message=str(exc),
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


def ship(
    raw_targets: str,
    *,
    confirm: bool,
    environ: Mapping[str, str],
    target: str = "library",
    recipe_path: str | None = None,
    cfe_root_arg: str | None,
    cfe_python_arg: str | None,
    cfe_timeout_arg: float | None,
    start_directory: Path,
) -> tuple[ShipTargetResult, ...]:
    """The multi-target ship dispatcher (Story 3.9, FR-16, FR-24, FR-50,
    AD-9, AD-26) -- the ONE place `--to`/`--ship`'s comma-separated targets
    get turned into calls against `ship_pypi`/`ship_channel`/
    `ship_conda_forge` (Stories 3.4-3.6), each of which existed for three
    stories with nothing on the CLI ever reaching them.

    Parses `raw_targets` via `parse_ship_targets` FIRST, letting
    `InvalidShipTargetError` propagate un-caught -- an invalid TOKEN fails
    the WHOLE command before any target runs at all (spec I/O matrix:
    "whole command fails before any target runs"), a deliberately different
    failure mode from a target's own execution failure below, which is
    caught and reported per-target instead.

    `project_path` is `str(start_directory)` -- there is no separate
    project-path parameter on this function at all (spec Always boundary:
    "Ship's `project_path` is always `Path.cwd()`, never a flag or
    positional" -- `package build` keeps its own explicit positional; ship
    does not adopt it). `start_directory` IS that `Path.cwd()` value,
    already resolved once by the CLI dispatch branch that calls this
    function, and this function never calls `Path.cwd()` a second time --
    it doubles as the same anchor `ship_conda_forge`'s own
    `resolve_cfe_root` call walks upward from for its `conda-forge` target.

    Dry run (`confirm=False`, the default absent `--yes`, FR-19): calls
    `build(project_path, target=target)` exactly ONCE, but ONLY when at
    least one requested target is NOT `conda-forge` (**corrected, review
    pass 2** -- this docstring previously said "calls `build()` exactly
    ONCE regardless of how many targets were requested," unconditionally.
    That was wrong: it contradicted this SAME docstring's own next
    paragraph, which already states the real-ship path's principle that "a
    project shipping only to `conda-forge` must never be forced through
    `pep517`/`pixi` build engines it may not even have installed" --  that
    principle was applied only to the real-ship path below, never carried
    through to this dry-run branch, so `mason package ship --to
    conda-forge` with no `--yes` crashed with `EngineAbsentError` on a host
    missing `pep517`/`pixi` tooling instead of printing the intended plan,
    defeating the exact safe-preview purpose FR-19's dry-run default
    exists for). When every requested target IS `conda-forge`, `build()` is
    never called at all -- a placeholder `PackageBuildResult` with every
    artifact/version field `None` and both subprocess return codes `0` is
    passed to `plan_ship` instead, which is safe because `plan_ship`'s own
    `CONDA_FORGE` branch never reads any `build_result` field (its message
    is a fixed string naming a pull request, not an artifact -- see
    `plan_ship`'s own docstring). Either way, `plan_ship(targets,
    build_result)` is returned verbatim -- print-only, uploads nothing, no
    target function is ever called (mirrors `plan_ship`'s own docstring:
    this function is the caller that inverts on `confirm`; `plan_ship`
    itself still does not).

    Real ship (`confirm=True`): there is NO shared upfront `build()` call
    here at all -- each target kind's own function owns its own
    build-or-none (`ship_pypi`/`ship_channel` each call `build()`
    internally; `ship_conda_forge` builds nothing, unchanged). This is the
    "minor redundancy" `ship_pypi`'s own Story 3.4 docstring already
    accepted as belonging to this story ("this module's own docstring
    explains why `ship_pypi` owns this sequence itself rather than
    accepting an already-built `PackageBuildResult`") -- a project shipping
    only to `conda-forge` must never be forced through `pep517`/`pixi`
    build engines it may not even have installed.

    Every target's own function call runs inside the internal `_ship_one`
    closure below, wrapped in `try`/`except MasonError` -- converting a
    raised structural precondition (a missing credential, an absent
    engine, an unresolved CFE root, a missing/misplaced recipe path, ...)
    into `ShipTargetResult(state=ShipState.FAILED, reference=None,
    message=str(exc))` for THAT target alone, named via
    `_canonical_target_name`, then continuing the rest (spec Always
    boundary; `ship_conda_forge`'s own Story 3.6 docstring already
    anticipated this: "leaving a caller -- a future multi-target
    dispatcher -- free to catch it and continue"). Consequence, spelled
    out because it is the one surprising exit-code behavior in this whole
    file (spec Design Notes): `EXIT_CFE_UNAVAILABLE` NEVER surfaces from
    `ship()`, even for a lone `--to conda-forge` with an unresolved CFE
    root -- the `CfeUnresolvedError` that would otherwise reach `main()`'s
    dedicated exit-code branch is intercepted HERE first, for every
    invocation shape, single- or multi-target alike; only a per-target
    `FAILED` result, never a raised exception, reaches `cli.py`.

    FR-24/FR-50/AD-26's self-hosting rehearsal gate: when both a
    `PYPI_TEST` target and a `PYPI` target are present anywhere in the same
    `targets` tuple, the FIRST `PYPI_TEST` target is run exactly ONCE,
    AHEAD of the main per-target loop below, and its result is reused --
    never re-run -- at its ORIGINAL index in the returned tuple, so OUTPUT
    order still matches INPUT order regardless of which order the caller
    typed the two targets in (`parse_ship_targets`'s own no-reordering
    precedent). Every `PYPI` target in the same invocation is then gated on
    that one cached rehearsal result's `state`: `ShipState.TERMINAL` lets
    it run for real (`ship_pypi` with no `repository_url`); anything else
    -- `FAILED`, `NOT_ATTEMPTED`, `PENDING` -- produces a
    `ShipTargetResult(state=ShipState.NOT_ATTEMPTED)` for that `PYPI`
    target instead, naming the gate and the rehearsal's own actual state,
    and `ship_pypi`/`twine upload` is never called for it. A SECOND (or
    later) `PYPI_TEST` token in the same invocation is NOT the cached one
    -- only the first is ever pre-run and reused; later ones execute
    independently, in their own position in the main loop, exactly like
    any other target. A `PYPI` target with no `PYPI_TEST` sibling anywhere
    in the same `targets` tuple is entirely unaffected by any of this
    (D-11: no cross-invocation memory exists to check against, so there is
    nothing to gate on).
    """
    targets = parse_ship_targets(raw_targets)
    project_path = str(start_directory)

    if not confirm:
        if any(t.kind is not ShipTargetKind.CONDA_FORGE for t in targets):
            build_result = build(project_path, target=target)
        else:
            build_result = PackageBuildResult(
                target=target,
                project_path=project_path,
                wheel_path=None,
                sdist_path=None,
                conda_path=None,
                wheel_version=None,
                conda_version=None,
                pep517_returncode=0,
                pixi_returncode=0,
                pep517_stdout="",
                pixi_stdout="",
            )
        return plan_ship(targets, build_result)

    def _ship_one(t: ShipTarget) -> ShipTargetResult:
        """Run exactly one target's own ship function and catch its
        `MasonError` into a `FAILED` `ShipTargetResult` (see `ship()`'s own
        docstring for the full rationale) -- a closure, not a module-level
        function, since it reads `project_path`/`environ`/`target`/
        `recipe_path`/`cfe_root_arg`/`cfe_python_arg`/`cfe_timeout_arg`/
        `start_directory` straight from the enclosing `ship()` call rather
        than accepting eight more parameters of its own."""
        try:
            if t.kind is ShipTargetKind.PYPI:
                return ship_pypi(project_path, environ=environ, target=target)
            if t.kind is ShipTargetKind.PYPI_TEST:
                return ship_pypi(
                    project_path,
                    environ=environ,
                    target=target,
                    repository_url=_TESTPYPI_REPOSITORY_URL,
                )
            if t.kind is ShipTargetKind.CHANNEL:
                return ship_channel(project_path, t.channel_name, environ=environ, target=target)
            if t.kind is ShipTargetKind.CONDA_FORGE:
                return ship_conda_forge(
                    recipe_path,
                    environ=environ,
                    cfe_root_arg=cfe_root_arg,
                    cfe_python_arg=cfe_python_arg,
                    cfe_timeout_arg=cfe_timeout_arg,
                    start_directory=start_directory,
                )
            raise AssertionError(f"unhandled ShipTargetKind: {t.kind!r}")  # pragma: no cover
        except MasonError as exc:
            return ShipTargetResult(
                target=_canonical_target_name(t),
                state=ShipState.FAILED,
                reference=None,
                message=str(exc),
            )

    results: list[ShipTargetResult | None] = [None] * len(targets)

    # FR-24/FR-50/AD-26 rehearsal pre-run: only when a PYPI target exists
    # anywhere in this invocation is there anything to gate -- find the
    # FIRST PYPI_TEST target (if any) and run it now, ahead of the main
    # loop, caching its result at its own original index.
    rehearsal_result: ShipTargetResult | None = None
    if any(t.kind is ShipTargetKind.PYPI for t in targets):
        for i, t in enumerate(targets):
            if t.kind is ShipTargetKind.PYPI_TEST:
                rehearsal_result = _ship_one(t)
                results[i] = rehearsal_result
                break

    for i, t in enumerate(targets):
        if results[i] is not None:
            continue  # the pre-run rehearsal slot above -- reused, not re-run
        if t.kind is ShipTargetKind.PYPI and rehearsal_result is not None:
            if rehearsal_result.state is not ShipState.TERMINAL:
                results[i] = ShipTargetResult(
                    target=_canonical_target_name(t),
                    state=ShipState.NOT_ATTEMPTED,
                    reference=None,
                    message=(
                        "gated on this invocation's pypi-test rehearsal: rehearsal state "
                        f"is {rehearsal_result.state.value!r}, not terminal -- the pypi "
                        "upload was not attempted"
                    ),
                )
                continue
        results[i] = _ship_one(t)

    return tuple(results)


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
