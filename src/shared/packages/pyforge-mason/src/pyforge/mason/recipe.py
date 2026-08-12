"""`mason recipe` -- the CFE-dependent use-cases (AD-6's CFE-dependent tier,
Epic 2 context).

Story 2.4 adds this module's first function, `new` (FR-7): generate a recipe
from PyPI/GitHub/CRAN/npm through `cfe.py`'s `generate_recipe` adapter (which
wraps CFE's recipe-generator script -- see that adapter's own docstring for
the exact filename, deliberately not repeated here: AD-3 reserves naming a
CFE script to `cfe.py` alone, and `tests/meta/test_adapter_sole_caller.py`
enforces that even inside a docstring), with zero recipe knowledge added in
Mason (AD-1). `cli.py`'s dispatch is the only caller; `new` never touches
`sys.stdout`/`sys.stderr` itself (AD-8 -- only the driving adapter formats).

`new` composes `resolve.py`'s two pure chains with `cfe.py`'s *raising*
siblings (`ensure_cfe_root`, `ensure_import_floor`) directly -- mirroring
`doctor.build_report`'s identical four-argument shape (`cfe_root_arg`,
`cfe_python_arg`, `environ`, `start_directory`) but raising instead of
degrading: `doctor` is a self-diagnosis command that must never fail (AD-6),
while `recipe new` is a CFE-dependent command whose whole point is to fail
loudly and specifically when CFE is unusable, rather than silently reporting
a gap. No `subprocess` import here at all (AD-2): every process spawn goes
through `cfe.py`'s named adapters.

Resolution order is load-bearing, not incidental (spec I/O matrix: "CFE root
unresolved... before any subprocess spawns"): `ensure_cfe_root` runs first
and, unlike `ensure_import_floor`/`generate_recipe`, spawns nothing itself
(it only inspects the already-computed `ResolvedCfeRoot` -- see `cfe.py`'s
own docstring), so an unresolved root is caught before the interpreter is
even probed, let alone before CFE's generator script runs. `resolve_cfe_
interpreter` (called after the root check) is likewise pure -- no subprocess
-- but `ensure_import_floor` immediately after it does spawn one (`cfe.py::
probe_import_floor`'s interpreter probe), so the ordering here is: resolve
root -> raise if unresolved -> resolve interpreter -> raise if the import
floor has a gap -> only then invoke `generate_recipe`, which is this
function's own (second) subprocess spawn.

`source` is CFE's own subcommand vocabulary (`pypi`/`github`/`cran`/`npm`),
selected 1:1 by `cli.py` from which `--from-*` flag the user gave -- this
function applies no judgement about what any of those words mean (AD-1
Design Notes: command routing, not recipe knowledge). `package` and `output`
are forwarded unmodified as `[source, package, "--output", output]`: no
parsing of an embedded `==`/`@` version spec inside `package`, no path
transformation of `output` (spec Always boundary).

A non-zero `CfeResult.returncode` raises `RecipeGenerationError`, built from
`stdout.strip()` first, falling back to `stderr.strip()`, then to a bare
returncode note if both are empty -- the wrapped script prints its
`Error: <e>` failure text to **stdout**, not stderr (`errors.py`'s
`RecipeGenerationError` docstring has the full rationale), so preferring
`stderr` here would silently drop the one string CFE actually wrote. A
zero-returncode result is returned completely unchanged: no field defaults,
no rewriting, no normalization of Mason's own (spec Design Notes: `CfeResult`
is reused as-is, never a `RecipeGenerationResult` wrapper with nothing new to
add).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from . import cfe
from .errors import RecipeGenerationError
from .models import CfeResult
from .resolve import resolve_cfe_interpreter, resolve_cfe_root


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
            result.stdout.strip()
            or result.stderr.strip()
            or f"CFE exited with code {result.returncode} and no output"
        )
        raise RecipeGenerationError(source=source, cfe_message=cfe_message)

    return result
