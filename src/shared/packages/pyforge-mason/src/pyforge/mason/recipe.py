"""The `recipe` noun's CFE-dependent use-case module (FR-9).

Story 2.6 adds the first `recipe` verb: `build`, which drives CFE's own
local-build tooling through two new STREAM-mode (AD-25) `cfe.py` adapters
-- `build_native` (the default) and `build_docker` (`--docker`, CI-parity,
opt-in) -- reporting the outcome as a `models.BuildResult`. Unlike
`cfe.py::validate_recipe`/`submit_pr` (CAPTURE mode), a build is expected to
run for minutes, so its output streams live rather than buffering to
completion.

`build()` composes `resolve.py`'s pure chains with `cfe.py`'s raising
`ensure_cfe_root` directly, mirroring `doctor.build_report`'s parameter
shape but raising `CfeUnresolvedError` instead of degrading -- `mason
recipe build` cannot proceed at all without a resolved CFE root, since both
of CFE's own build scripts live under it. Unlike a future recipe-generation
verb, `build()` calls no `ensure_import_floor` gate: neither wrapped script
needs CFE's Python import floor (spec Design Notes) -- the native path
never runs under any Python interpreter at all, and the Docker/CI-parity
script imports only the stdlib.

The CFE interpreter is resolved only for the Docker/CI-parity path: the
native path invokes its script through `bash`, never through a Python
interpreter (spec Always boundary), so resolving one for that path would be
dead work -- `resolve_cfe_interpreter` is therefore only ever called inside
the `docker` branch below, not unconditionally.

`cfe` is imported at module level, not lazily (unlike `doctor.py`): AD-6's
lazy-import carve-out is scoped to `package.py`/`environment.py`/`doctor.py`
only (the CFE-independent nouns) -- `recipe` is structurally CFE-dependent
(`doctor.build_report` already reports it in `unavailable_verbs` whenever
CFE cannot be resolved or its import floor has a gap), so there is no
"must import cleanly even when CFE is unusable" requirement to protect here.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TextIO

from . import cfe
from .models import BuildResult
from .resolve import resolve_cfe_interpreter, resolve_cfe_root


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
    the CFE interpreter first) when `docker` is `True`, else straight to
    `cfe.build_native`. `config` is only meaningful for the Docker path
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

    if docker:
        resolved_interpreter = resolve_cfe_interpreter(cfe_python_arg, environ)
        return cfe.build_docker(
            config,
            root=resolved_root.root,
            interpreter=resolved_interpreter.path,
            timeout=cfe_timeout_arg,
            stderr_sink=stderr_sink,
        )

    return cfe.build_native(
        recipe_path,
        root=resolved_root.root,
        timeout=cfe_timeout_arg,
        stderr_sink=stderr_sink,
    )
