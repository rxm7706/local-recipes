"""CFE-dependent use-cases for the `recipe` noun (AD-6): `mason recipe
<verb>` composes `resolve.py`'s pure chains with `cfe.py`'s named adapters,
adding no recipe semantics of its own (AD-1).

Story 2.7 creates this module -- the first `recipe` verb on this branch --
with `diagnose()`, backing `mason recipe diagnose <log_path>` (FR-10).
Unlike `doctor.py`/`package.py`/`environment.py` (AD-6's CFE-independent
tier, which must import `cfe` lazily or not at all), `recipe.py` is
CFE-dependent by definition, so `cfe` is imported at module level here --
`tests/meta/test_capability_tiers.py`'s lazy-import guard names only
`package.py`/`environment.py`/`doctor.py`, not this file.

`diagnose()` mirrors `doctor.build_report`'s composition shape (resolve root
-> resolve interpreter -> call the CFE port) with one addition: it calls
`cfe.ensure_cfe_root` and lets `CfeUnresolvedError` propagate (spec Always
boundary) rather than folding an unresolved root into report data the way
`doctor.py` does -- `recipe diagnose` is a CFE-dependent command, not a
self-diagnosis, so an unresolved root is this command's own failure, not
data about it. It deliberately does NOT call `cfe.ensure_import_floor`
(spec Always boundary): the wrapped failure-analysis script imports only
stdlib modules (confirmed by reading it), the same import-floor exemption
Story 2.6 established for its own wrapped build script, so gating this
operation on CFE's full import floor would reject a call that would have
succeeded.

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
`diagnose()` nor `build` needs: after resolving the interpreter, both call
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
call and is reported honestly (`{"success": false, "error": ..., "hint":
...}`) -- not false-clean, but still gated early as a courtesy so a doomed
call fails before spawning the subprocess. Scoping matters because a working
call must not be rejected for lacking a package the invoked operation never
imports (e.g. `optimize()` must not fail over a missing `truststore`) --
gating on the whole floor would reintroduce, at a coarser grain, exactly the
"reject a call that would have succeeded" failure `diagnose()`'s own
docstring says was deliberately avoided by skipping the floor gate entirely.
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
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from . import cfe
from .errors import CfeImportFloorError
from .models import CfeResult
from .resolve import resolve_cfe_interpreter, resolve_cfe_root

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
    `requests` instead raises inside the scanner's own API call and is
    reported honestly (`{"success": false, "error": ..., "hint": ...}`) --
    not false-clean, but still gated here so the call fails before spawning
    the subprocess rather than after. An interpreter missing only an
    unrelated floor entry is NOT rejected. `cfe_timeout_arg` is passed
    straight through as `cfe.scan_for_vulnerabilities`'s own `timeout`; that
    adapter's own default (`_SCAN_FOR_VULNERABILITIES_TIMEOUT_SECONDS`)
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
