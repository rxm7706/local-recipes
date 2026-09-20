"""The `recipe` noun's CFE-dependent use-case module (FR-9, AD-6): `mason
recipe <verb>` composes `resolve.py`'s pure chains with `cfe.py`'s named
adapters, adding no recipe semantics of its own (AD-1). Unlike `doctor.py`/
`package.py`/`environment.py` (AD-6's CFE-independent tier, which must
import `cfe` lazily or not at all), `recipe.py` is CFE-dependent by
definition, so `cfe` is imported at module level here --
`tests/meta/test_capability_tiers.py`'s lazy-import guard names only
`package.py`/`environment.py`/`doctor.py`, not this file.

Story 2.4 creates this module -- the first `recipe` verb -- with `new()`
(FR-7): generate a recipe from PyPI/GitHub/CRAN/npm through `cfe.py`'s
`generate_recipe` adapter (which wraps CFE's recipe-generator script -- see
that adapter's own docstring for the exact filename, deliberately not
repeated here: AD-3 reserves naming a CFE script to `cfe.py` alone, and
`tests/meta/test_adapter_sole_caller.py` enforces that even inside a
docstring), with zero recipe knowledge added in Mason. `cli.py`'s dispatch
is the only caller; `new()` never touches `sys.stdout`/`sys.stderr` itself
(AD-8 -- only the driving adapter formats). It composes `resolve.py`'s two
pure chains with `cfe.py`'s *raising* siblings (`ensure_cfe_root`,
`ensure_import_floor`) directly -- mirroring `doctor.build_report`'s
identical four-argument shape (`cfe_root_arg`, `cfe_python_arg`, `environ`,
`start_directory`) but raising instead of degrading: `doctor` is a
self-diagnosis command that must never fail (AD-6), while `recipe new` is a
CFE-dependent command whose whole point is to fail loudly and specifically
when CFE is unusable, rather than silently reporting a gap. Resolution
order is load-bearing, not incidental (spec I/O matrix: "CFE root
unresolved... before any subprocess spawns"): `ensure_cfe_root` runs first
and, unlike `ensure_import_floor`/`generate_recipe`, spawns nothing itself,
so an unresolved root is caught before the interpreter is even probed, let
alone before CFE's generator script runs -- resolve root -> raise if
unresolved -> resolve interpreter -> raise if the import floor has a gap ->
only then invoke `generate_recipe`, this function's own (second) subprocess
spawn. `source` is CFE's own subcommand vocabulary (`pypi`/`github`/`cran`/
`npm`), selected 1:1 by `cli.py` from which `--from-*` flag the user gave
(AD-1 Design Notes: command routing, not recipe knowledge); `package`/
`output` are forwarded unmodified as `[source, package, "--output",
output]` -- no parsing of an embedded `==`/`@` version spec inside
`package`, no path transformation of `output` (spec Always boundary). A
non-zero `CfeResult.returncode` raises `RecipeGenerationError`, built from
`stdout.strip()` first, falling back to `stderr.strip()`, then to a bare
returncode note if both are empty -- the wrapped script prints its
`Error: <e>` failure text to **stdout**, not stderr (`errors.py`'s
`RecipeGenerationError` docstring has the full rationale), so preferring
`stderr` here would silently drop the one string CFE actually wrote. A
zero-returncode result is returned completely unchanged: no field defaults,
no rewriting, no normalization of Mason's own (spec Design Notes: `CfeResult`
is reused as-is, never a `RecipeGenerationResult` wrapper with nothing new
to add).

Story 2.6 adds `build()`, the second `recipe` verb, driving CFE's own
local-build tooling through two new STREAM-mode (AD-25) `cfe.py` adapters:
`build_native` (the default) and `build_docker` (`--docker`, CI-parity,
opt-in), reporting the outcome as a `models.BuildResult`. Unlike
Story 2.5 adds `validate()`, backing `mason recipe validate <recipe_path>`
(FR-8) -- the first `recipe` verb in this module, numerically, even though
`build`/`diagnose`/`optimize`/`scan`/`submit`/`update` (Stories 2.6-2.10)
landed first in this worktree (spec Design Notes: this repository's `main`
branch already reconciled Story 2.4's `new()` into this same first
position, ahead of `build`, after an analogous out-of-order landing --
this file's own final position mirrors that reconciliation: `new()`
(FR-7) precedes `validate()` (FR-8), both ahead of `build()` (FR-9). It mirrors `diagnose()`'s composition shape below exactly
(resolve root -> `ensure_cfe_root` -> resolve interpreter -> call the CFE
port, no import-floor gate: the wrapped validator's only third-party
import, PyYAML, already degrades to an honest failure on its own, the same
"already handles it" exemption `diagnose()` establishes -- not
`optimize()`/`scan()`'s scoped-probe pattern), with one addition neither
`diagnose()` nor `build()` need: `args` is `["--json", recipe_path]`,
mirroring `scan()`'s own `--json` forcing below, not `diagnose()`'s bare
`[log_path]` -- without it the wrapped validator prints human text, leaving
`CfeResult.json_body` empty. `validate()` returns the raw `CfeResult`
verbatim (spec Never boundary), like every sibling verb -- it never raises
for a validation failure. Only `cli.py`'s own `recipe validate` dispatch
branch projects `CfeResult.returncode` onto the process exit code (spec
Always boundary) -- the one verb where that projection happens; this
module's own contract (a non-zero return code is data, never an exception,
AD-4) is unchanged.

Story 2.6 adds `build()`, the next verb after `validate()` above, driving
CFE's own local-build tooling through two new STREAM-mode (AD-25) `cfe.py`
adapters: `build_native` (the default) and `build_docker` (`--docker`,
CI-parity, opt-in), reporting the outcome as a `models.BuildResult`. Unlike
`cfe.py::validate_recipe`/`submit_pr` (CAPTURE mode), a build is expected to
run for minutes, so its output streams live rather than buffering to
completion. `build()` mirrors `doctor.build_report`'s parameter shape but
raises `CfeUnresolvedError` instead of degrading -- `mason recipe build`
cannot proceed at all without a resolved CFE root, since both of CFE's own
build scripts live under it. It calls no `ensure_import_floor` gate:
neither wrapped script needs CFE's Python import floor (spec Design Notes)
-- the native path never runs under any Python interpreter at all, and the
Docker/CI-parity script imports only the stdlib, the same "already handles
it" exemption `diagnose()` below reuses for its own wrapped script. The CFE
interpreter is resolved only for the Docker/CI-parity path: the native path
invokes its script through `bash`, never through a Python interpreter (spec
Always boundary), so resolving one for that path would be dead work --
`resolve_cfe_interpreter` is therefore only ever called inside the `docker`
branch below, not unconditionally.

Story 2.7 adds `diagnose()`, backing `mason recipe diagnose <log_path>`
(FR-10). `diagnose()` mirrors `doctor.build_report`'s composition shape
(resolve root -> resolve interpreter -> call the CFE port) with one
addition: it calls `cfe.ensure_cfe_root` and lets `CfeUnresolvedError`
propagate (spec Always boundary) rather than folding an unresolved root
into report data the way `doctor.py` does -- `recipe diagnose` is a
CFE-dependent command, not a self-diagnosis, so an unresolved root is this
command's own failure, not data about it. It deliberately does NOT call
`cfe.ensure_import_floor` (spec Always boundary): the wrapped
failure-analysis script imports only stdlib modules (confirmed by reading
it), the same import-floor exemption Story 2.6 established for its own
wrapped build script, so gating this operation on CFE's full import floor
would reject a call that would have succeeded.

`log_path` is passed straight through as the one element of `cfe.
diagnose_failure`'s `args` -- no existence check, no interpretation of the
result (AD-1, spec Always boundary): a missing file surfaces as CFE's own
`{"success": false, "error": "Log file not found: ..."}` JSON body on the
returned `CfeResult`, exactly like every other diagnosis outcome. (No CFE
script filename is named here or below -- AD-3's sole-caller guard forbids
naming one anywhere outside `cfe.py`, docstrings included.)

Story 2.8 adds `optimize()`/`scan()`, backing `mason recipe optimize
<recipe_path>` / `mason recipe scan <recipe_path>` (FR-11, FR-12). Both
mirror `diagnose()`'s composition shape (resolve root -> `ensure_cfe_root`
-> resolve interpreter -> call the CFE port) with one addition neither
`diagnose()` nor `build()` needs: after resolving the interpreter, both call
`cfe.probe_import_floor(resolved_interpreter.path)` themselves and raise
`CfeImportFloorError` before invoking their own CFE adapter, but ONLY when
their own operation-relevant subset of `.missing` is non-empty -- never the
whole 6-entry floor (`cfe.ensure_import_floor` is called by neither; spec
Always boundary). This is the opposite decision from `diagnose()`'s, scoped
per operation rather than gated on the whole floor -- reading the wrapped
optimizer and vulnerability-scanner scripts shows both wrap their
third-party imports (`ruamel.yaml`; `requests`+`pyyaml`) in their own
`try/except ImportError` and silently DEGRADE rather than crash: the
optimizer returns a lone suggestion at **maximum confidence (1.0)**, and the
scanner's `pyyaml`-missing path is **false-clean**
(`{"success": true, "mode": "skipped", "scanned": 0, "unpinned_skipped":
[...]}`, no `results` key -- indistinguishable from a genuinely clean scan),
while its `requests`-missing path instead raises inside the script's own API
call and -- when no local CVE database exists yet at the path `pixi run
update-cve-db` populates -- is reported honestly (`{"success": false,
"error": ..., "hint": ...}`) -- not false-clean, but still gated early as a
courtesy so a doomed call fails before spawning the subprocess. Scoping
matters because a working call must not be rejected for lacking a package
the invoked operation never imports (e.g. `optimize()` must not fail over a
missing `truststore`) -- gating on the whole floor would reintroduce, at a
coarser grain, exactly the "reject a call that would have succeeded" failure
`diagnose()`'s own docstring says was deliberately avoided by skipping the
floor gate entirely.
`recipe_path` is passed straight through with no existence check or
interpretation, mirroring `log_path` above (AD-1, spec Always boundary): no
Mason-side reinterpretation of either script's own reporting, so a
missing/invalid path surfaces exactly as each script itself reports it, not
identically between the two. `optimize()`'s wrapped script always prints its
`{"success": false, "error": ...}` body to stdout, so it lands on the
returned `CfeResult.json_body` the same as any other outcome. `scan()`'s
wrapped script instead prints that same shape to *stderr* on a missing
path -- an inconsistency in the wrapped script itself, not introduced here --
so `CfeResult.json_body` is `None` in that one case; the raw error text is
still present on `CfeResult.stderr` (FR-4: a parsed body is present "when
one is present," never invented when absent). (No CFE script filename is
named here or below -- AD-3's sole-caller guard forbids naming one anywhere
outside `cfe.py`, docstrings included.)

Story 2.9 adds `submit()`, backing `mason recipe submit <recipe_path>`
(FR-13, AD-9, AD-11) -- staged-recipes submission's ONE implementation, that
Epic 3's `conda-forge` ship target calls rather than reimplements (AD-11).
It mirrors `diagnose()`'s composition shape (resolve root -> `ensure_cfe_
root` -> resolve interpreter, no import-floor gate: the wrapped submission
script is stdlib-only, confirmed by reading it, the same exemption
`diagnose()` established) with two additions neither
`diagnose()`/`optimize()`/`scan()` need: `recipe_path` IS interpreted here
-- the one narrow, disclosed exception to AD-1's "no Mason-side path
interpretation" precedent every other verb in this module follows, required
because the wrapped script's own positional argument is a bare recipe NAME,
not a path, unlike every other wrapped script (spec Always boundary) -- and
the returned `CfeResult` is reinterpreted into a `ShipTargetResult`
(`models.py`, AD-9) by the private `_ship_target_result_from_cfe_result`
helper below, the one Mason-side reinterpretation of a CFE JSON body this
epic makes (AD-9's own designed shape, not a recipe-knowledge violation of
AD-1: interpreting `success`/`pr_url`/`fork_branch_url` into
`state`/`reference` is what AD-9 exists to standardize across every ship
target, conda-forge included).

Story 2.10 adds `update()`, backing `mason recipe update <recipe_path>`
(FR-14) -- a diff-before-apply upstream version bump for either a PyPI- or
GitHub-Releases-sourced package. It mirrors `diagnose()`'s composition shape
exactly (resolve root -> `ensure_cfe_root` -> resolve interpreter, no
import-floor gate: both wrapped autotick scripts already degrade a missing
dependency to `{"success": false, "error": ...}` JSON data on their own,
confirmed by reading them, the same "already handles it" exemption
`diagnose()` established -- not `optimize()`/`scan()`'s scoped-probe
pattern) and returns the raw `CfeResult` (spec Never boundary: `update` is
not a ship target, so no `ShipTargetResult`/new dataclass is introduced,
unlike `submit()`).

`github` is a Mason-only dispatch flag (AD-1): it selects which of the two
CFE adapters is called and is never itself forwarded as CFE argv -- Mason
never inspects `recipe_path`'s own content to choose a source type, since
that would require parsing recipe YAML the same way the wrapped scripts
already do. `recipe_path` is passed straight through with no existence
check or interpretation, mirroring `log_path`/`optimize()`'s and `scan()`'s
`recipe_path` (AD-1, spec Always boundary) -- not `submit()`'s one disclosed
exception, since neither wrapped script here takes a bare recipe name.

`args` is built as `[recipe_path]`, then `"--dry-run"` appended when
`dry_run` is true -- forwarded to the invoked script's own `--dry-run` flag
verbatim, no inversion (unlike `submit()`'s `confirm` inversion): omitting
it is the confirmed/apply path, since `update`'s local file write is
git-reversible, unlike `submit`'s externally-visible PR (spec Design Notes).
When `github` is true, `"--repo", github_repo` is appended when
`github_repo` is truthy, then `"--pre"` when `allow_prerelease` is true, and
`cfe.update_recipe_from_github` is called; otherwise `cfe.update_recipe` is
called and `github_repo`/`allow_prerelease` never reach CFE argv at all --
inert, not rejected, since neither flag is meaningful to the PyPI script
(spec Always boundary, I/O matrix).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TextIO

from . import cfe
from .engines.build_hooks import select_build_engine_plugin
from .errors import CfeImportFloorError, RecipeGenerationError
from .models import BuildResult, CfeResult, ShipState, ShipTargetResult
from .resolve import (
    _ENV_FACTORY_ROOT,
    _ENV_FOUNDRY_ROOT,
    resolve_cfe_interpreter,
    resolve_cfe_root,
    resolve_factory_island,
)

_OPTIMIZE_RELEVANT_FLOOR: tuple[str, ...] = ("ruamel.yaml",)
"""The subset of `cfe.CFE_IMPORT_FLOOR` the wrapped optimizer actually
imports (confirmed by reading it) -- `optimize()` gates on only this subset,
never the whole floor, so a call is never rejected for lacking a package the
optimizer never imports (e.g. `truststore`). A tuple literal, not a
`frozenset(...)` call: `tests/meta/test_credential_isolation.py`'s AD-14
guard flags a banned HTTP-client name (`requests`) passed as a call
argument anywhere in this package -- `_SCAN_RELEVANT_FLOOR` below is the one
that actually contains that name, but both are declared the same way for
consistency."""

_SCAN_RELEVANT_FLOOR: tuple[str, ...] = ("pyyaml", "requests")
"""The subset of `cfe.CFE_IMPORT_FLOOR` the wrapped scanner actually
imports (confirmed by reading it) -- `scan()` gates on only this subset,
never the whole floor, for the same reason as `_OPTIMIZE_RELEVANT_FLOOR`
above. `requests` here names CFE's own dependency floor entry -- probed
inside the CFE interpreter, never imported by Mason -- not a Mason-side
HTTP client (see this constant's tuple-literal note above)."""

_CFE_RECIPES_ROOT_ENV_VAR = "CFE_RECIPES_ROOT"
"""Sanctioned duplication of CFE's own `_path_guard.ROOT_ENV_VAR` literal
(module docstring) -- the env var `_path_guard.recipes_root()` reads, per
call, to override the confinement root a recipe slug is resolved and
validated against. AD-2's dependency-direction rule forbids importing a CFE
internal, and AD-3 reserves CFE path/invocation knowledge to `cfe.py` alone
in any case -- so this is a local re-declaration of the same literal,
mirroring `resolve.py`'s `_ENV_CFE_ROOT`/`errors.py`'s `_MESSAGE` sanctioned-
duplication pattern (`cfe.py`'s own module docstring names this same
pattern for its `_CFE_SCRIPTS` table). Set, never read, by `submit()` below
-- Mason never reads this variable back."""


def new(
    source: str,
    package: str,
    output: str,
    *,
    cfe_root_arg: str | None,
    cfe_python_arg: str | None,
    cfe_timeout_arg: float | None,
    environ: Mapping[str, str],
    start_directory: Path,
) -> CfeResult:
    """Generate a recipe via CFE's `generate_recipe` adapter and return its
    `CfeResult` unchanged (FR-7).

    `cfe_root_arg`/`cfe_python_arg`/`environ`/`start_directory` are the raw
    `--cfe-root`/`--cfe-python` flag values, `os.environ`, and the CFE-root
    walk's starting directory -- the same shape `doctor.build_report` takes
    (module docstring), passed straight through to `resolve.py`'s two pure
    chains with no resolution logic of its own here. `cfe_timeout_arg` is
    the raw `--cfe-timeout` flag/environment value (`float | None`); `None`
    lets `cfe.generate_recipe` apply its own per-operation default
    (`_GENERATE_RECIPE_TIMEOUT_SECONDS`), exactly like `cfe.validate_recipe`/
    `cfe.submit_pr`'s identical `timeout=None` convention.

    Raises `CfeUnresolvedError` (via `cfe.ensure_cfe_root`) if the CFE root
    cannot be resolved, `CfeImportFloorError` (via `cfe.ensure_import_floor`)
    if the selected interpreter is missing part of CFE's import floor, and
    `RecipeGenerationError` if CFE's own generation attempt exits non-zero --
    see the module docstring for why these checks run in exactly this order.
    `CfeTimeoutError` can also escape from `cfe.generate_recipe` itself if
    the subprocess exceeds its timeout; this function adds no handling of
    its own for that case; it simply propagates.
    """
    resolved_root = resolve_cfe_root(cfe_root_arg, environ, start_directory)
    cfe.ensure_cfe_root(resolved_root)

    resolved_interpreter = resolve_cfe_interpreter(cfe_python_arg, environ)
    cfe.ensure_import_floor(resolved_interpreter.path)

    # resolved_root.root is guaranteed non-None here: ensure_cfe_root above
    # already raised CfeUnresolvedError for the only case (STEP_NOT_FOUND)
    # where it would be None.
    result = cfe.generate_recipe(
        [source, package, "--output", output],
        root=resolved_root.root,
        interpreter=resolved_interpreter.path,
        timeout=cfe_timeout_arg,
    )

    if result.returncode != 0:
        cfe_message = (
            result.stdout.strip() or result.stderr.strip() or f"CFE exited with code {result.returncode} and no output"
        )
        raise RecipeGenerationError(source=source, cfe_message=cfe_message)

    return result


def validate(
    recipe_path: str,
    *,
    cfe_root_arg: str | None,
    cfe_python_arg: str | None,
    cfe_timeout_arg: float | None,
    environ: Mapping[str, str],
    start_directory: Path,
) -> CfeResult:
    """Validate a recipe against conda-forge policy via CFE's validator
    (FR-8) and return the resulting `CfeResult` directly -- no Mason-side
    reinterpretation of its `json_body` (spec Never boundary).

    Resolves the CFE root (`resolve_cfe_root`) and raises
    `CfeUnresolvedError` via `cfe.ensure_cfe_root` before any subprocess
    spawns if it is unresolved (spec Always boundary) -- mirroring
    `build`/`diagnose`/`submit`. Resolves the interpreter (`resolve_cfe_
    interpreter`) with NO import-floor gate (module docstring): the wrapped
    validator's only third-party import, PyYAML, already degrades to an
    honest failure on its own, the same "already handles it" exemption
    `diagnose()` establishes -- not `optimize()`/`scan()`'s scoped-probe
    pattern.

    `args` is `["--json", recipe_path]`, mirroring `scan()`'s own `--json`
    forcing below (spec Always boundary) -- without it the wrapped
    validator prints human text, leaving `CfeResult.json_body` empty.
    `recipe_path` is passed straight through with no existence check or
    interpretation (AD-1), mirroring `diagnose()`/`optimize()`/`scan()`'s
    own `recipe_path`/`log_path`. `cfe_timeout_arg` is passed straight
    through as `cfe.validate_recipe`'s own `timeout`; that adapter's own
    default (`_VALIDATE_RECIPE_TIMEOUT_SECONDS`) applies only when this
    resolves to `None`.

    Unlike every sibling verb, this operation's pass/fail outcome also
    projects onto the process exit code -- but only `cli.py`'s own `recipe
    validate` dispatch branch makes that projection (spec Always boundary):
    this function itself never raises for a validation failure, identical
    to every other verb here and to AD-4's rule.
    """
    resolved_root = resolve_cfe_root(cfe_root_arg, environ, start_directory)
    cfe.ensure_cfe_root(resolved_root)

    resolved_interpreter = resolve_cfe_interpreter(cfe_python_arg, environ)

    return cfe.validate_recipe(
        ["--json", recipe_path],
        root=resolved_root.root,
        interpreter=resolved_interpreter.path,
        timeout=cfe_timeout_arg,
    )


def build(
    recipe_path: str,
    *,
    docker: bool,
    config: str | None,
    cfe_root_arg: str | None,
    cfe_python_arg: str | None,
    cfe_timeout_arg: float | None,
    environ: Mapping[str, str],
    start_directory: Path,
    stderr_sink: TextIO | None = None,
) -> BuildResult:
    """Build `recipe_path`: natively by default, or via CFE's Docker/
    CI-parity tooling when `docker` is `True` (FR-9).

    Resolves the CFE root and calls `cfe.ensure_cfe_root` -- raising
    `CfeUnresolvedError` before any subprocess spawns if it cannot be found
    (spec I/O matrix) -- then dispatches to `cfe.build_docker` (resolving
    the CFE interpreter first) when `docker` is `True`, else to the default
    build-engine plugin's `around` whose `next` is `cfe.build_native`.
    `config` is only meaningful for the Docker path
    (required there by `cli.py`'s own usage check, before this function is
    ever called); the native path always detects its own platform-variant
    config via `resolve.detect_native_build_config` inside `cfe.
    build_native` itself, never from this parameter.

    `cfe_timeout_arg` is forwarded straight through as the adapter's own
    `timeout` -- `None` selects that adapter's per-operation default
    (`cfe.py`'s `_BUILD_NATIVE_TIMEOUT_SECONDS`/`_BUILD_DOCKER_TIMEOUT_
    SECONDS`). A non-zero child return code is never raised here (AD-4) --
    it is data on the returned `BuildResult`.
    """
    resolved_root = resolve_cfe_root(cfe_root_arg, environ, start_directory)
    cfe.ensure_cfe_root(resolved_root)

    foundry_root_arg = environ.get(_ENV_FOUNDRY_ROOT)
    factory_island = resolve_factory_island(
        recipe_path,
        foundry_root_arg=foundry_root_arg,
        environ=environ,
        start_directory=start_directory,
    )
    if factory_island is not None:
        recipe_path = str(factory_island.recipe_path)
        build_env = {
            **environ,
            _ENV_FACTORY_ROOT: str(factory_island.factory_root),
            _ENV_FOUNDRY_ROOT: str(factory_island.foundry_root),
        }
    else:
        build_env = environ

    if docker:
        resolved_interpreter = resolve_cfe_interpreter(cfe_python_arg, environ)
        return cfe.build_docker(
            config,
            root=resolved_root.root,
            interpreter=resolved_interpreter.path,
            timeout=cfe_timeout_arg,
            stderr_sink=stderr_sink,
            env=build_env,
        )

    plugin = select_build_engine_plugin()

    def _native_next(_context: dict) -> BuildResult:
        return cfe.build_native(
            recipe_path,
            root=resolved_root.root,
            timeout=cfe_timeout_arg,
            stderr_sink=stderr_sink,
            env=build_env,
        )

    return plugin.call("around", {"next": _native_next})


def diagnose(
    log_path: str,
    *,
    cfe_root_arg: str | None,
    cfe_python_arg: str | None,
    cfe_timeout_arg: float | None,
    environ: Mapping[str, str],
    start_directory: Path,
) -> CfeResult:
    """Diagnose a build-failure log via CFE's failure analyzer (FR-10) and
    return the resulting `CfeResult` directly -- no Mason-side
    reinterpretation of its `json_body` (spec Never boundary).

    Resolves the CFE root (`resolve_cfe_root`) and raises
    `CfeUnresolvedError` via `cfe.ensure_cfe_root` before any subprocess
    spawns if it is unresolved (spec Always boundary) -- mirroring
    `build`/`validate`/`submit`. Resolves the interpreter
    (`resolve_cfe_interpreter`) with no import-floor gate (see module
    docstring). `cfe_timeout_arg` is passed straight through as `cfe.
    diagnose_failure`'s own `timeout`; that adapter's own default
    (`_DIAGNOSE_FAILURE_TIMEOUT_SECONDS`) applies only when this resolves to
    `None`.
    """
    resolved_root = resolve_cfe_root(cfe_root_arg, environ, start_directory)
    cfe.ensure_cfe_root(resolved_root)

    resolved_interpreter = resolve_cfe_interpreter(cfe_python_arg, environ)

    return cfe.diagnose_failure(
        [log_path],
        root=resolved_root.root,
        interpreter=resolved_interpreter.path,
        timeout=cfe_timeout_arg,
    )


def optimize(
    recipe_path: str,
    *,
    cfe_root_arg: str | None,
    cfe_python_arg: str | None,
    cfe_timeout_arg: float | None,
    environ: Mapping[str, str],
    start_directory: Path,
) -> CfeResult:
    """Lint a recipe for quality findings via CFE's recipe optimizer (FR-11)
    and return the resulting `CfeResult` directly -- no Mason-side
    reinterpretation of its `json_body` (spec Never boundary).

    Resolves the CFE root (`resolve_cfe_root`) and raises
    `CfeUnresolvedError` via `cfe.ensure_cfe_root` before any subprocess
    spawns if it is unresolved (spec Always boundary), mirroring
    `diagnose()`. Resolves the interpreter (`resolve_cfe_interpreter`), then
    -- unlike `diagnose()` -- probes it via `cfe.probe_import_floor` and
    raises `CfeImportFloorError` itself before invoking the CFE port (module
    docstring), but ONLY when `_OPTIMIZE_RELEVANT_FLOOR` (just `ruamel.yaml`)
    intersects the probe's `.missing`: the wrapped optimizer needs
    `ruamel.yaml` and silently degrades to a lone suggestion at maximum
    confidence (1.0), rather than crashing, when it's absent. An interpreter
    missing only an unrelated floor entry (e.g. `truststore`) is NOT
    rejected. `cfe_timeout_arg` is passed straight through as `cfe.
    optimize_recipe`'s own `timeout`; that adapter's own default
    (`_OPTIMIZE_RECIPE_TIMEOUT_SECONDS`) applies only when this resolves to
    `None`.
    """
    resolved_root = resolve_cfe_root(cfe_root_arg, environ, start_directory)
    cfe.ensure_cfe_root(resolved_root)

    resolved_interpreter = resolve_cfe_interpreter(cfe_python_arg, environ)
    probe = cfe.probe_import_floor(resolved_interpreter.path)
    relevant_missing = tuple(m for m in probe.missing if m in _OPTIMIZE_RELEVANT_FLOOR)
    if relevant_missing:
        raise CfeImportFloorError(missing=relevant_missing, interpreter=resolved_interpreter.path)

    return cfe.optimize_recipe(
        [recipe_path],
        root=resolved_root.root,
        interpreter=resolved_interpreter.path,
        timeout=cfe_timeout_arg,
    )


def scan(
    recipe_path: str,
    *,
    cfe_root_arg: str | None,
    cfe_python_arg: str | None,
    cfe_timeout_arg: float | None,
    environ: Mapping[str, str],
    start_directory: Path,
) -> CfeResult:
    """Scan a recipe's dependencies for known vulnerabilities via CFE's
    scanner (FR-12) and return the resulting `CfeResult` directly -- no
    Mason-side reinterpretation of its `json_body` (spec Never boundary).

    Resolves the CFE root and interpreter and probes the floor via `cfe.
    probe_import_floor` exactly like `optimize()` above (module docstring),
    scoped to `_SCAN_RELEVANT_FLOOR` (`requests` and `pyyaml`): the wrapped
    scanner needs both, and degrades differently depending on which is
    absent. A missing `pyyaml` is **false-clean** -- `{"success": true,
    "mode": "skipped", "scanned": 0, "unpinned_skipped": [...]}`, no
    `results` key, indistinguishable from a genuinely clean scan. A missing
    `requests` instead raises inside the scanner's own API call and -- when
    no local CVE database exists yet at the path `pixi run update-cve-db`
    populates -- is reported honestly (`{"success": false, "error": ...,
    "hint": ...}`) -- not false-clean, but still gated here so the call
    fails before spawning the subprocess rather than after. An interpreter
    missing only an unrelated floor entry is NOT rejected. `cfe_timeout_arg`
    is passed straight through as `cfe.scan_for_vulnerabilities`'s own
    `timeout`; that adapter's own default (`_SCAN_FOR_VULNERABILITIES_TIMEOUT_SECONDS`)
    applies only when this resolves to `None`.
    """
    resolved_root = resolve_cfe_root(cfe_root_arg, environ, start_directory)
    cfe.ensure_cfe_root(resolved_root)

    resolved_interpreter = resolve_cfe_interpreter(cfe_python_arg, environ)
    probe = cfe.probe_import_floor(resolved_interpreter.path)
    relevant_missing = tuple(m for m in probe.missing if m in _SCAN_RELEVANT_FLOOR)
    if relevant_missing:
        raise CfeImportFloorError(missing=relevant_missing, interpreter=resolved_interpreter.path)

    return cfe.scan_for_vulnerabilities(
        ["--json", recipe_path],
        root=resolved_root.root,
        interpreter=resolved_interpreter.path,
        timeout=cfe_timeout_arg,
    )


def submit(
    recipe_path: str,
    *,
    confirm: bool,
    prepare_only: bool,
    cfe_root_arg: str | None,
    cfe_python_arg: str | None,
    cfe_timeout_arg: float | None,
    environ: Mapping[str, str],
    start_directory: Path,
) -> ShipTargetResult:
    """Submit a recipe to conda-forge/staged-recipes via CFE's two-phase
    submission flow (FR-13, AD-9, AD-11) and return a `ShipTargetResult`.

    Resolves the CFE root (`resolve_cfe_root`) and raises
    `CfeUnresolvedError` via `cfe.ensure_cfe_root` before any subprocess
    spawns if it is unresolved (spec Always boundary), mirroring
    `diagnose()`/`optimize()`/`scan()`. Resolves the interpreter (`resolve_
    cfe_interpreter`) with NO import-floor gate: the wrapped submission
    script is stdlib-only (confirmed by reading it), the same exemption
    `diagnose()` established (module docstring) -- not `optimize()`/
    `scan()`'s scoped-probe pattern.

    Unlike every other verb in this module, `recipe_path` IS interpreted
    here -- the one narrow, disclosed exception to AD-1's "no Mason-side
    path interpretation" precedent (spec Always boundary): the wrapped
    script's own positional argument is a bare recipe NAME, not a path,
    unlike every other wrapped script. `recipe_dir` is resolved
    (`Path(recipe_path).expanduser().resolve()`) with NO existence check --
    an invalid path surfaces as CFE's own `{"success": false, "error":
    "Recipe not found: ..."}` (AD-4, data not raised, never a Mason-side
    `FileNotFoundError`). `recipe_dir.name` becomes the wrapped script's own
    positional slug, and `recipe_dir.parent` is unconditionally set as
    `_CFE_RECIPES_ROOT_ENV_VAR` in the child's environment: harmless when
    the recipe is already in-tree (parent == the real `recipes/` root, no
    branching needed), and what lets an out-of-tree, user-specified
    generation path (Story 2.4) still submit, with no new CLI flag and no
    CFE surface file touched (epic-2-context.md Technical Decisions).

    `confirm` inverts CFE's own `--dry-run` default (spec Always boundary,
    PRD "`--dry-run` is the default"): `confirm=False` appends `--dry-run`
    to the argv; `confirm=True` omits it -- nothing is pushed or opened
    unless the caller explicitly confirmed. `prepare_only`, when true,
    appends `--prepare-only` unconditionally, composing with `--dry-run`
    exactly as the wrapped script's own argparse already allows (the
    two-phase flow's own "separately addressable" requirement) -- no other
    flag (`--title`/`--body`/`--branch`/`--no-force`) is ever passed (spec
    Never boundary: speculative surface no FR/AC names).

    `env` is built here, once, as the caller -- `run_streamed`'s documented
    contract, mirrored by `cfe.submit_pr`'s own `env=` parameter: the real
    inherited `environ` plus the one `_CFE_RECIPES_ROOT_ENV_VAR` key. No
    credential is read, filtered, or added (AD-14's actual rule: full
    pass-through of the given `environ` plus one non-credential key).

    Returns a `ShipTargetResult`, not the raw `CfeResult` (spec Always
    boundary, unlike every other verb here): see
    `_ship_target_result_from_cfe_result` below for the state mapping.

    `recipe_dir`'s resolution (`.expanduser().resolve()`) is wrapped in its
    own `try`/`except` (review pass, 2026-08-12): a NONEXISTENT path
    resolves cleanly (`Path.resolve()` does not require the target to
    exist) and surfaces as CFE's own `"Recipe not found"` data, per the
    paragraph above -- but a symlink loop or an embedded NUL byte raises
    `OSError`/`ValueError` from `resolve()` itself, before any subprocess
    spawns. Catching that here and returning a `FAILED` `ShipTargetResult`
    keeps this verb's own contract (AD-4: an anticipated failure is data,
    never a raised exception reaching the CLI as a raw traceback) instead
    of falling through to `cli.py`'s generic `except Exception` handler.
    """
    resolved_root = resolve_cfe_root(cfe_root_arg, environ, start_directory)
    cfe.ensure_cfe_root(resolved_root)

    resolved_interpreter = resolve_cfe_interpreter(cfe_python_arg, environ)

    try:
        recipe_dir = Path(recipe_path).expanduser().resolve()
    except (OSError, ValueError) as exc:
        return ShipTargetResult(
            target="conda-forge",
            state=ShipState.FAILED,
            reference=None,
            message=str(exc),
        )
    args = [recipe_dir.name]
    if not confirm:
        args.append("--dry-run")
    if prepare_only:
        args.append("--prepare-only")

    env = {**environ, _CFE_RECIPES_ROOT_ENV_VAR: str(recipe_dir.parent)}

    result = cfe.submit_pr(
        args,
        root=resolved_root.root,
        interpreter=resolved_interpreter.path,
        timeout=cfe_timeout_arg,
        env=env,
    )
    return _ship_target_result_from_cfe_result(result, confirm=confirm)


def _ship_target_result_from_cfe_result(
    result: CfeResult,
    *,
    confirm: bool,
) -> ShipTargetResult:
    """Map a `submit_pr` `CfeResult` onto a `ShipTargetResult` (AD-9) -- the
    one Mason-side reinterpretation of a CFE JSON body this epic makes
    (spec Always boundary), in this order:

    - `confirm=False` -> `NOT_ATTEMPTED`, `reference=None`: a dry run's
      `fork_branch_url` is hypothetical, never rendered as if real.
    - `confirm=True` and the body reports failure (`json_body.get(
      "success")` falsy, or `json_body` is unparseable/not a `dict`, in
      which case `result.returncode == 0` stands in for "success") ->
      `FAILED`, `reference=json_body.get("fork_branch_url")` when a body
      exists (present when the push succeeded but `open_pr` failed
      afterward; `None` otherwise).
    - `confirm=True`, success, `pr_url` present (the full flow) ->
      `PENDING`, `reference=json_body["pr_url"]` -- never `TERMINAL` (a PR
      being open is not a PR being merged; AD-10's interrogation-based
      idempotence is how a later command would ever learn `TERMINAL`, out
      of this story's scope).
    - `confirm=True`, success, no `pr_url` (`--prepare-only`) -> `PENDING`,
      `reference=json_body.get("fork_branch_url")` (AD-10: "if a target
      cannot be interrogated, the result is pending with the reason").

    `message` is `json_body["message"]` when that key is PRESENT (even if
    falsy, e.g. an explicit empty string -- `dict.get(key, default)`'s
    default only applies when the key is absent, review pass, 2026-08-12:
    an `or`-chain would have silently discarded a present-but-empty
    `"message"` in favor of `"error"`), else `json_body.get("error")`,
    verbatim -- no re-authoring (AD-1), computed once and reused across
    every branch above. `target` is the literal string `"conda-forge"`, not
    tied to a `ShipTarget` enum -- that vocabulary is explicitly Story 3.3's
    scope (spec Never boundary).

    `body` treats a `json_body` that parsed to something other than a
    `dict` (or didn't parse at all, `None`) identically -- neither shape
    has fields to read, so both fall back to the `result.returncode`
    stand-in and a `None` reference/message, matching FR-4's "a parsed body
    is present when one is present" (never invented when absent).
    """
    body = result.json_body if isinstance(result.json_body, dict) else None
    message = body.get("message", body.get("error")) if body else None

    if not confirm:
        return ShipTargetResult(
            target="conda-forge",
            state=ShipState.NOT_ATTEMPTED,
            reference=None,
            message=message,
        )

    succeeded = body.get("success") if body is not None else result.returncode == 0
    if not succeeded:
        return ShipTargetResult(
            target="conda-forge",
            state=ShipState.FAILED,
            reference=(body.get("fork_branch_url") if body else None),
            message=message,
        )

    pr_url = body.get("pr_url") if body else None
    reference = pr_url if pr_url else (body.get("fork_branch_url") if body else None)
    return ShipTargetResult(
        target="conda-forge",
        state=ShipState.PENDING,
        reference=reference,
        message=message,
    )


def update(
    recipe_path: str,
    *,
    dry_run: bool,
    github: bool,
    github_repo: str | None,
    allow_prerelease: bool,
    cfe_root_arg: str | None,
    cfe_python_arg: str | None,
    cfe_timeout_arg: float | None,
    environ: Mapping[str, str],
    start_directory: Path,
) -> CfeResult:
    """Bump a recipe to its latest upstream version via CFE's autotick
    scripts (FR-14) and return the resulting `CfeResult` directly -- no
    Mason-side reinterpretation of its `json_body` (spec Never boundary).

    Resolves the CFE root (`resolve_cfe_root`) and raises
    `CfeUnresolvedError` via `cfe.ensure_cfe_root` before any subprocess
    spawns if it is unresolved (spec Always boundary), mirroring
    `diagnose()`/`optimize()`/`scan()`/`submit()`. Resolves the interpreter
    (`resolve_cfe_interpreter`) with NO import-floor gate (module docstring):
    both wrapped autotick scripts already degrade a missing dependency to
    JSON error data on their own, the same exemption `diagnose()`
    established.

    `github` is a Mason-only dispatch flag (module docstring, AD-1): it
    selects which adapter is called and is never itself forwarded as CFE
    argv. `recipe_path` is passed straight through with no existence check
    or interpretation, mirroring `optimize()`/`scan()`'s own `recipe_path`.

    `args` is `[recipe_path]`, then `"--dry-run"` appended when `dry_run` is
    true -- forwarded verbatim to the invoked script's own `--dry-run` flag,
    no inversion (unlike `submit()`'s `confirm` inversion). When `github` is
    true, `"--repo", github_repo` is appended when `github_repo` is truthy,
    then `"--pre"` when `allow_prerelease` is true, and `cfe.
    update_recipe_from_github` is called; otherwise `cfe.update_recipe` is
    called and `github_repo`/`allow_prerelease` never reach CFE argv at all
    (spec Always boundary: inert, not rejected, when `github` is false).
    `cfe_timeout_arg` is passed straight through as the chosen adapter's own
    `timeout`; that adapter's own per-operation default applies only when
    this resolves to `None`.
    """
    resolved_root = resolve_cfe_root(cfe_root_arg, environ, start_directory)
    cfe.ensure_cfe_root(resolved_root)

    resolved_interpreter = resolve_cfe_interpreter(cfe_python_arg, environ)

    args = [recipe_path]
    if dry_run:
        args.append("--dry-run")

    if github:
        if github_repo:
            args.extend(["--repo", github_repo])
        if allow_prerelease:
            args.append("--pre")
        return cfe.update_recipe_from_github(
            args,
            root=resolved_root.root,
            interpreter=resolved_interpreter.path,
            timeout=cfe_timeout_arg,
        )

    return cfe.update_recipe(
        args,
        root=resolved_root.root,
        interpreter=resolved_interpreter.path,
        timeout=cfe_timeout_arg,
    )
