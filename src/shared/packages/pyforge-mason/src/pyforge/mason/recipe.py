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
`cfe.ensure_import_floor(resolved_interpreter.path)` before invoking their
own CFE adapter (spec Always boundary). This is the opposite decision from
`diagnose()`'s -- reading the wrapped optimizer and vulnerability-scanner
scripts shows both wrap their third-party imports (`ruamel.yaml`; `requests`
+`pyyaml`) in their own `try/except ImportError` and silently DEGRADE
rather than crash: the optimizer returns a lone low-confidence suggestion,
and the scanner returns a **false-clean** `{"success": true, "scanned": 0,
"results": []}`, indistinguishable from a genuinely clean scan. Gating on
the import floor converts that silent, misleading success into an explicit,
actionable `CfeImportFloorError` before either subprocess ever spawns --
exactly the scenario `ensure_import_floor` exists for (spec Design Notes).
`recipe_path` is passed straight through with no existence check or
interpretation, mirroring `log_path` above: a missing/invalid path surfaces
as CFE's own `{"success": false, "error": ...}` body, exit 1, on the
returned `CfeResult` (AD-1, spec Always boundary). (No CFE script filename
is named here or below -- AD-3's sole-caller guard forbids naming one
anywhere outside `cfe.py`, docstrings included.)
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from . import cfe
from .models import CfeResult
from .resolve import resolve_cfe_interpreter, resolve_cfe_root


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
    -- unlike `diagnose()` -- calls `cfe.ensure_import_floor` on it and lets
    `CfeImportFloorError` propagate before invoking the CFE port (module
    docstring): the wrapped optimizer needs `ruamel.yaml` and silently
    degrades to a lone low-confidence suggestion, rather than crashing, when
    it's absent. `cfe_timeout_arg` is passed straight through as `cfe.
    optimize_recipe`'s own `timeout`; that adapter's own default
    (`_OPTIMIZE_RECIPE_TIMEOUT_SECONDS`) applies only when this resolves to
    `None`.
    """
    resolved_root = resolve_cfe_root(cfe_root_arg, environ, start_directory)
    cfe.ensure_cfe_root(resolved_root)

    resolved_interpreter = resolve_cfe_interpreter(cfe_python_arg, environ)
    cfe.ensure_import_floor(resolved_interpreter.path)

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

    Resolves the CFE root and interpreter and gates on `cfe.
    ensure_import_floor` exactly like `optimize()` above (module docstring):
    the wrapped scanner needs `requests`+`pyyaml` and silently degrades to a
    **false-clean** `{"success": true, "scanned": 0, "results": []}`,
    rather than crashing, when either is absent -- indistinguishable from a
    genuinely clean scan without this gate. `cfe_timeout_arg` is passed
    straight through as `cfe.scan_for_vulnerabilities`'s own `timeout`; that
    adapter's own default (`_SCAN_FOR_VULNERABILITIES_TIMEOUT_SECONDS`)
    applies only when this resolves to `None`.
    """
    resolved_root = resolve_cfe_root(cfe_root_arg, environ, start_directory)
    cfe.ensure_cfe_root(resolved_root)

    resolved_interpreter = resolve_cfe_interpreter(cfe_python_arg, environ)
    cfe.ensure_import_floor(resolved_interpreter.path)

    return cfe.scan_for_vulnerabilities(
        ["--json", recipe_path],
        root=resolved_root.root,
        interpreter=resolved_interpreter.path,
        timeout=cfe_timeout_arg,
    )
