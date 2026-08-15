"""Shared, behaviour-free data shapes returned across a layer boundary
(AD-8, Consistency Conventions: "Data shapes... `@dataclass(frozen=True)`
in `models.py`").

Story 2.1 creates this module. Two shapes land here today:

`CfeResult` is new -- the return type of every CAPTURE-mode invocation
`cfe.py` makes (AD-3, AD-4, FR-4). `DoctorReport` is not new: it moves here
verbatim (unchanged fields) from `doctor.py`, the architecture's one
sanctioned pre-existing-shape move (Consistency Conventions, "the one
landed divergence, `DoctorReport` in `doctor.py`, moves in with a
`doctor.py` re-export so no import or test churns"). `doctor.py` re-exports
it via `from .models import DoctorReport`, so the pre-existing `from
pyforge.mason.doctor import DoctorReport` import (`tests/unit/test_cli.py`)
keeps resolving unchanged.

This module is a dependency-direction *leaf*: nothing under `pyforge/mason/`
may import from it in a way that risks a cycle back through it, so `cli.py`,
`render.py`, and every use-case can import it freely. "Leaf" is about import
*direction*, not import *count* -- this module may still import `EngineStatus`
from `.engines` (itself a leaf with zero internal-package imports), because
that import points further outward, not back inward. Only `DoctorReport`
makes this move; `EngineStatus`, `ImportFloorResult`, `ResolvedCfeRoot`, and
`ResolvedCfeInterpreter` are deliberately left in their owning modules (spec
Never boundary) -- the architecture names `DoctorReport` alone as the
one landed divergence.

Story 2.6 adds `BuildResult`, the second shape in this file, the return
type of both new STREAM-mode (AD-25) build adapters in `cfe.py`
(`build_native`/`build_docker`) -- the first shape in this module NOT
produced by a CAPTURE-mode invocation: unlike `CfeResult`, it carries no
`stderr` (STREAM mode forwards a child's stderr live rather than
accumulating it -- see `cfe.run_streamed`'s own docstring) and no
`json_body` (neither wrapped script has a `--json` mode).

Story 2.9 adds `ShipState`/`ShipTargetResult` -- the third and fourth shapes
in this file (AD-9): the return type of `recipe.py::submit()` (FR-13), and
the shape Epic 3's `package.py`/`environment.py` ship targets will wrap
their own results in later (AD-11, spec Never boundary: no `ShipTarget`
enum or `ShipReceipt` aggregate lands with this story -- both are
explicitly out of scope here). Later stories still add `ShipReceipt` and
`LockResult` here (architecture Structural Seed) -- neither exists yet.

Story 3.2 adds `PackageBuildResult` -- the fifth shape, and the first NOT
produced anywhere near `cfe.py`: `package.py::build()`'s own return type
(FR-15, FR-21, FR-22), composed from `engines.pep517`/`engines.pixi`'s two
independent build outcomes. Its per-engine intermediate result dataclasses
(`Pep517BuildResult`, `PixiBuildResult`) deliberately stay in their own
`engines/*.py` modules rather than landing here -- they cross a layer
boundary too (`engines/*.py` -> `package.py`), but never reach `cli.py`/
`render.py` directly the way `PackageBuildResult` itself does, so widening
this leaf's surface for them is not warranted.

Story 3.3 adds `ShipTargetKind`/`ShipTarget` -- the sixth and seventh
shapes in this file, and the first pair produced nowhere near a subprocess
at all: `package.py::parse_ship_targets`'s own closed parse-result
vocabulary for `--ship`/`--to` (FR-16, FR-19, spec AC1), consumed
immediately afterward by `package.py::plan_ship` to build each target's
`ShipTargetResult` dry-run entry -- AD-9's already-established shape
(Story 2.9, above), reused rather than reinvented (see `ShipTargetResult`'s
own docstring below for why its `target` field stays a plain `str` rather
than adopting this new enum). No `ShipReceipt` aggregate lands with this
story either (spec Never boundary) -- Story 2.9's docstring above already
named that as a later story's addition (Story 3.7), and this story does not
change that.

Story 3.6 extends `DoctorReport` with two more fields,
`conda_forge_ship_ready`/`conda_forge_ship_blockers` (FR-23, D-10):
a recipe-independent PROXY for `package.py::ship_conda_forge`'s shipping
preconditions -- what `mason doctor` can observe without a recipe-path
argument -- and which parts of it are unmet. The proxy also covers the
import floor, which is not one of D-10's two preconditions but gates the
same path (this target delegates to `recipe.py::submit()`, the verb
`unavailable_verbs` already reports on). See `doctor.py::build_report`'s
own module docstring for exactly how the proxy differs from the real
preconditions. No defaults, matching every other
field on this dataclass -- a `DoctorReport` with a forgotten conda-forge-
readiness field is exactly the ambiguity a default would silently paper
over.

Story 3.7 adds `ShipReceipt` -- the eighth shape in this file, and the
aggregate both Story 2.9's and Story 3.3's paragraphs above already named as
a later addition (both said "Story 3.7"): the multi-target ship outcome
`package.py::build_ship_receipt` composes from however many
`ShipTargetResult`s a caller already produced (AD-9). See `ShipReceipt`'s
own docstring below for why `ok` is a plain field, not a property, and what
it does and does not summarize.

Story 4.3 adds `LockResult` -- the ninth shape in this file, and the one
this module's own docstring (above, Story 2.9's paragraph) already named as
a future addition: `environment.py::lock()`'s own return type (FR-25,
FR-27, FR-29), composed from `engines.condalock`'s single `CondaLockResult`
plus the orchestration-level context (`manifest_paths`, `platforms` as
actually requested) that engine-layer shape does not itself carry -- mirrors
`PackageBuildResult` wrapping `engines.pep517`/`engines.pixi`'s independent
outcomes above, the same "engine-layer shape stays in `engines/*.py`,
the layer-boundary-crossing shape lands here" split that shape's own
paragraph documents.

Story 4.4 adds `CheckResult` -- the tenth shape in this file, and
`environment.py::check()`'s own return type (FR-25, FR-27, FR-29):
`engines.condalock.check()`'s `CondaLockCheckResult` wrapped with the same
kind of orchestration-level context `LockResult` above already establishes
the pattern for, plus `lockfile_path` (the EXISTING lockfile `check()` was
told to verify, never a write target like `LockResult.output_path`) and
`stale`, the verdict itself -- the one field neither `LockResult` nor any
other shape in this file carries.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .engines import EngineStatus


@dataclass(frozen=True)
class CfeResult:
    """The outcome of one CAPTURE-mode CFE invocation (AD-3, AD-4, FR-4).

    `returncode` is the child's raw exit code -- a non-zero value is data on
    this dataclass, never raised as an exception (AD-4): the caller decides
    what a given script's failure means, `cfe.py` only reports it. `stdout`
    and `stderr` are the child's full captured text, decoded with
    `encoding="utf-8", errors="replace"` (never a bare `text=True`, whose
    locale-derived default can silently mangle a valid UTF-8 body under
    `LC_ALL=C` -- the same rationale `run_streamed` documents for STREAM
    mode). `json_body` is the value `cfe._extract_json` parsed out of
    `stdout`, or `None` when no parseable JSON body was present at all --
    FR-4 says a parsed body is present "when one is present," so its absence
    is a normal outcome recorded here, not a reason to raise.
    """

    returncode: int
    stdout: str
    stderr: str
    json_body: object | None


@dataclass(frozen=True)
class DoctorReport:
    """`mason doctor`'s full self-diagnosis (FR-34): Mason's own version,
    the resolved CFE root and which chain step found it, the selected
    interpreter and which chain step selected it, the import-floor outcome,
    which verbs are unavailable as a consequence, every known engine's
    presence/version, and (Story 3.6) a recipe-independent proxy for
    whether `package.py::ship_conda_forge`'s shipping preconditions (D-10)
    and the import floor it delegates through are currently met, plus which
    parts of that proxy are unmet."""

    mason_version: str
    cfe_root: str | None
    cfe_root_step: str
    cfe_interpreter: str
    cfe_interpreter_step: str
    cfe_import_floor_satisfied: bool
    cfe_import_floor_missing: tuple[str, ...]
    unavailable_verbs: tuple[str, ...]
    engines: tuple[EngineStatus, ...]
    conda_forge_ship_ready: bool
    conda_forge_ship_blockers: tuple[str, ...]


@dataclass(frozen=True)
class BuildResult:
    """The outcome of one `recipe build` invocation (FR-9, AD-25): a
    STREAM-mode build, native or Docker/CI-parity.

    `mode` is `"native"` or `"docker"` -- which adapter ran. `config` is the
    platform-variant name (e.g. `"linux64"`) -- detected automatically for
    the native path, or the caller's own `--config` value for the Docker
    path -- or `None` when native detection found no match for the current
    host (the build still runs and reports its own failure via
    `returncode`; never guessed). `returncode` is the child's raw exit code
    -- a non-zero value is DATA here, never raised (AD-4): a failed build is
    the routine, expected outcome of the recipe-development iteration loop
    this whole product exists to support, not an exceptional input error.
    `stdout` is the child's captured stdout in full -- STREAM mode never
    accumulates stderr; it is forwarded live instead (see
    `cfe.run_streamed`'s own docstring), so this shape carries no `stderr`
    field at all. `artifact_dir` is `build_artifacts/<config>` (a
    documented build-infrastructure convention, not recipe knowledge) when
    `config` is known, else `None`.
    """

    mode: str
    config: str | None
    returncode: int
    stdout: str
    artifact_dir: str | None


class ShipState(StrEnum):
    """The closed set of states any ship target's result can be in (AD-9):
    `not_attempted` (no confirming flag was given -- a dry run; nothing was
    pushed or opened), `failed` (a confirmed attempt did not reach a
    reportable success), `pending` (a confirmed attempt initiated something
    real -- a pushed branch, an opened PR -- but confirming it reached a
    durable end state requires interrogating the target later, AD-10, out
    of scope for the call that produced this result), `terminal` (a later
    interrogation confirmed the target reached its end state; no code path
    in this story produces it -- AD-10's interrogation-based idempotence,
    not yet built, is the only way a future caller would ever learn it).
    **`pending` is never collapsed into success in any rendering** (AD-9).

    `StrEnum` (stdlib since 3.12, this package's floor), not a plain `Enum`
    (Design Notes): `cli.py`'s dispatch renders every result via
    `render.write` -> `render_json`'s `json.dumps(dataclasses.asdict(result),
    ...)`, with no custom encoder (`render.py`'s own module docstring: only
    a fixed five-key envelope, no schema-driven serialization).
    `dataclasses.asdict` does not special-case `Enum`, so a plain `Enum`
    member would reach `json.dumps` as a non-serializable object and raise.
    `StrEnum` members are real `str` instances the JSON encoder handles
    natively, AND -- unlike a bare `(str, Enum)` mixin pre-3.11 --
    `__str__`/`__format__` return the plain value too, so `render_text`'s
    `f"{data[key]}"` line renders `pending`, never `ShipState.PENDING`."""

    NOT_ATTEMPTED = "not_attempted"
    FAILED = "failed"
    PENDING = "pending"
    TERMINAL = "terminal"


@dataclass(frozen=True)
class ShipTargetResult:
    """One ship target's outcome (AD-9) -- `recipe.py::submit()`'s return
    type (FR-13), and the shape a future `package.py`/`environment.py` ship
    target wraps its own result in (AD-11: `mason package --ship
    conda-forge` calls `recipe.py::submit()` rather than reimplementing it,
    and wraps ITS `ShipTargetResult` -- never produces a second one for the
    same operation).

    `target` is a literal string (e.g. `"conda-forge"`), not a `ShipTarget`
    enum, even though Story 3.3 (below) now defines that closed vocabulary
    -- this field stays a plain `str` deliberately (spec Always boundary:
    "`ShipTargetResult.target` stays a plain `str`... `recipe.py::submit()`
    is untouched"): `recipe.py::submit()`'s own literal `"conda-forge"` is
    not migrated to `ShipTargetKind.CONDA_FORGE.value`, and `package.py::
    plan_ship`'s new dry-run entries reconstruct the same canonical string
    form rather than reaching for the enum here, so every producer of this
    field agrees on its type without this dataclass itself changing shape.
    `reference` is a URL, PR number, branch URL, or channel path (Story 3.5:
    `package.py::ship_channel`'s success `reference` is the bare, caller-
    supplied channel name -- see `engines.pixi`'s own module docstring for
    why no equivalent live-verified URL exists to parse one out of),
    depending on `state`, or `None` when nothing concrete exists yet (a dry
    run, or a failure before anything was produced). `message` is the
    wrapped tool's own `message`/`error` field, verbatim -- no Mason-side
    re-authoring (AD-1)."""

    target: str
    state: ShipState
    reference: str | None
    message: str | None


class ShipTargetKind(StrEnum):
    """The closed set of ship-destination kinds `package.py::parse_ship_
    targets` recognizes (Story 3.3, FR-16, FR-19, spec AC1): `PYPI` (upload
    to PyPI), `CONDA_FORGE` (a staged-recipes pull request), `CHANNEL` (an
    arbitrary named conda channel -- `ShipTarget.channel_name` carries
    which one), and (Story 3.9, FR-24, FR-50, AD-26) `PYPI_TEST` -- a
    TestPyPI rehearsal upload. `PYPI_TEST` is NOT a second upload
    mechanism: it runs through the IDENTICAL code path as `PYPI`
    (`package.py::ship_pypi`), differing only in a `repository_url` knob
    forwarded down to `engines.twine.upload` -- AD-26's own "identical code
    path... differing only in repository configuration."

    `StrEnum`, not a plain `Enum`, mirroring `ShipState`'s own precedent
    above for the same reason: this file's shapes eventually reach
    `render_json`'s bare `json.dumps(dataclasses.asdict(...))` call with no
    custom encoder once a future story wires a ship-related result onto the
    CLI's output envelope, and a plain `Enum` member would raise
    `TypeError` there where a `StrEnum` member serializes natively."""

    PYPI = "pypi"
    CONDA_FORGE = "conda-forge"
    CHANNEL = "channel"
    PYPI_TEST = "pypi-test"


@dataclass(frozen=True)
class ShipTarget:
    """One parsed `--ship`/`--to` token (Story 3.3, FR-16, FR-19, spec
    AC1) -- `package.py::parse_ship_targets`'s own per-token return shape,
    and `package.py::plan_ship`'s per-target input.

    `kind` is the closed `ShipTargetKind`. `channel_name` is the name after
    `channel:` (e.g. `"myorg"` for `"channel:myorg"`) when `kind` is
    `CHANNEL`, or `None` for `PYPI`/`CONDA_FORGE`, whose canonical string
    form carries no further variable data. No default value on either
    field, mirroring `ShipTargetResult`'s own no-defaults field convention
    above: a `ShipTarget` with a forgotten `channel_name` is exactly the
    ambiguity a default would silently paper over."""

    kind: ShipTargetKind
    channel_name: str | None


@dataclass(frozen=True)
class PackageBuildResult:
    """The outcome of one `package build` invocation (FR-15, FR-21, FR-22):
    both a PEP 517 wheel+sdist build (`engines.pep517`) and a `.conda`
    build (`engines.pixi`) run for the same project, in one call.

    `target` is the caller's own `--target` value (`"library"` in v1 --
    `cli.py`'s `choices=("library",)` is the only validation, since a
    closed `ShipTarget`-style enum for this field is out of this story's
    scope, mirroring `ShipTargetResult.target`'s own plain-`str` precedent).
    `project_path` is the resolved, absolute project directory both engines
    actually ran against (`package.py::build()`'s own docstring explains why
    it is resolved before either engine runs). `wheel_path`/`sdist_path`/
    `conda_path` are the produced artifacts' paths, or `None` when that
    artifact was not produced -- an absent engine never reaches this far
    (`require_engine` raises before either subprocess spawns), so `None`
    here means a non-zero build returncode (AD-4: data, never raised) or no
    matching artifact filename was found on disk after a build that
    otherwise reported success. `wheel_version`/`conda_version` are each
    build's own parsed version (`engines.pep517`'s wheel-filename parse,
    `engines.pixi`'s `.conda`-filename parse respectively), or `None` under
    the same "not produced" condition -- `package.py::build()`'s one point
    of comparison between them (FR-22: a disagreement between two known
    values raises `PackageVersionMismatchError` before this dataclass is
    ever constructed). `pep517_returncode`/`pixi_returncode` are each
    engine subprocess's raw exit code -- non-zero is DATA here, never
    raised (AD-4), mirroring `BuildResult.returncode`'s own precedent.
    `pep517_stdout`/`pixi_stdout` are each engine subprocess's captured
    stdout in full (review pass, 2026-08-13) -- mirror `BuildResult.
    stdout`'s own precedent: a build failure investigated outside a live
    terminal needs diagnostic text, not a bare returncode integer."""

    target: str
    project_path: str
    wheel_path: str | None
    sdist_path: str | None
    conda_path: str | None
    wheel_version: str | None
    conda_version: str | None
    pep517_returncode: int
    pixi_returncode: int
    pep517_stdout: str
    pixi_stdout: str


@dataclass(frozen=True)
class ShipReceipt:
    """The aggregate outcome of a multi-target ship (Story 3.7, AD-9): every
    `ShipTargetResult` an invocation produced, plus a pre-computed `ok`
    summary field.

    `targets` is every result IN THE ORDER shipped -- no reordering, no
    deduplication (mirrors `package.py::parse_ship_targets`'s own no-dedup
    precedent for the same reason: deciding what "duplicate" means for two
    identical targets shipped in the same invocation is out of this
    dataclass's own scope). `ok` is a plain FIELD, not a property or method
    (AD-1: "data carries no behaviour" -- every shape in this module is a
    frozen dataclass with fields only), computed ONCE by `package.py::
    build_ship_receipt` as `not any(r.state is ShipState.FAILED for r in
    results)`: `NOT_ATTEMPTED`, `PENDING`, and `TERMINAL` all count as
    success for this aggregate (AD-9) -- only an actual `FAILED` target
    flips `ok` to `False`. A `PENDING` target (an interrogation Story 3.7
    could not complete, or a confirmed attempt whose durable end state is
    still unconfirmed -- `ShipState`'s own docstring, above) is deliberately
    NOT collapsed into failure here any more than it is collapsed into
    success in `render.py`'s own rendering (`ShipState`'s own docstring:
    "`pending` is never collapsed into success in any rendering") -- this
    aggregate's `ok` field answers a narrower question ("did anything
    definitively fail?"), not "did everything definitively succeed?".

    Nothing constructs a `ShipReceipt` in this story except `package.py::
    build_ship_receipt` itself -- no `ship()` multi-target dispatcher and no
    CLI wiring land here (spec Never boundary): `cli.py`'s own `ship` verb
    (Story 3.9) is the future caller that will gather several
    `ShipTargetResult`s from `ship_pypi`/`ship_channel`/(eventually)
    `ship_conda_forge`, once merged, and hand them to `build_ship_receipt`."""

    targets: tuple[ShipTargetResult, ...]
    ok: bool


@dataclass(frozen=True)
class LockResult:
    """The outcome of one `environment lock` invocation (Story 4.3, FR-25,
    FR-27, FR-29): `engines.condalock.lock()`'s own `CondaLockResult`
    wrapped with the orchestration-level context that engine-layer shape
    does not itself carry.

    `manifest_paths`/`output_path`/`platforms` are the caller's own
    resolved inputs, carried straight through unchanged -- `platforms`
    empty means no `--platform` was given, so conda-lock's own default
    applied (never invented by Mason, spec Always boundary). `engine_name`/
    `engine_version` are `CondaLockResult`'s own fields, threaded through so
    a renderer surfaces "which engine ran" (FR-29) with no `render.py`
    change required, mirroring `CondaLockResult`'s own docstring precedent.
    `returncode` is the delegated `conda-lock` subprocess's raw exit code --
    non-zero is DATA here, never raised (AD-4), mirroring
    `PackageBuildResult.pep517_returncode`'s own precedent. `stdout` is the
    subprocess's captured stdout in full (review pass, 2026-08-14) -- mirrors
    `PackageBuildResult.pep517_stdout`/`pixi_stdout`'s own precedent: a
    failed solve (`condalock.py`'s own docstring calls this "the routine
    expected outcome of resolving a real dependency graph") investigated
    outside a live terminal needs diagnostic text, not a bare returncode
    integer -- `CondaLockResult.stdout` already carries it, this field just
    was not threaded through in the first pass."""

    manifest_paths: tuple[str, ...]
    output_path: str
    platforms: tuple[str, ...]
    engine_name: str
    engine_version: str | None
    returncode: int
    stdout: str


@dataclass(frozen=True)
class CheckResult:
    """The outcome of one `environment check` invocation (Story 4.4, FR-25,
    FR-27, FR-29): `engines.condalock.check()`'s own `CondaLockCheckResult`
    wrapped with the orchestration-level context that engine-layer shape
    does not itself carry.

    `lockfile_path` is the EXISTING lockfile the caller asked to verify --
    never written to under any outcome (spec Never boundary), unlike
    `LockResult.output_path`'s write-target semantics above; `--lockfile` is
    deliberately not named `--output` for the same reason (spec Always
    boundary). `manifest_paths`/`platforms` mirror `LockResult`'s own
    identical fields and rationale -- the caller's own resolved inputs,
    carried straight through unchanged. `stale` is the verdict itself
    (Intent): `True` when the lockfile's parsed `metadata.content_hash`
    differs before vs. after conda-lock's own `--check-input-hash` re-run
    against a temporary copy, `False` when it does not -- DATA on this
    dataclass, never raised (AD-4); `check()` itself never raises for a
    stale verdict. `engine_name`/`engine_version`/`returncode`/`stdout`
    mirror `LockResult`'s own identical fields and rationale -- `returncode`
    is the delegated `conda-lock` subprocess's raw exit code, `stdout` its
    captured stdout in full."""

    lockfile_path: str
    manifest_paths: tuple[str, ...]
    platforms: tuple[str, ...]
    stale: bool
    engine_name: str
    engine_version: str | None
    returncode: int
    stdout: str
