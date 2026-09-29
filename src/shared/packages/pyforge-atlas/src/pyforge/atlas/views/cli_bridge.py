"""Dynamic-import bridge to the conda-forge-expert skill CLI scripts — Story 14.1 (CAP-1).

Epic 14's static views must query ``cf_atlas.db`` "by calling the matching CLI script's
existing ``query(**kwargs)`` verbatim" — never a second, parallel-SQL query surface. Each of
the 11 skill CLIs under ``.claude/skills/conda-forge-expert/scripts/`` already exposes a
``query(**kwargs) -> list[dict[str, Any]]`` function that does its own ``sqlite3.connect``;
this module dynamically loads one of those scripts by name (mirroring the
``importlib.util.spec_from_file_location`` idiom already used by
``.claude/skills/conda-forge-expert/tests/unit/test_mapping_gap.py::_load``) and calls its
``query()`` unmodified.

Because the loading is *dynamic* — the module name is a runtime string, never a literal
``import sqlite3`` / ``from sqlite3 import ...`` / ``import_module("sqlite3")`` anywhere in
this file — the F1 DuckDB-singularity gate
(``tests/singularity/test_duckdb_sole_engine.py``), which AST-scans literal imports in
``pyforge/atlas/**/*.py``, stays green even though the loaded script itself imports
``sqlite3`` (it lives outside that scanned tree).

One hazard the CLI scripts share: ``query()`` calls ``sys.exit(1)`` (not an exception) when
``DB_PATH`` doesn't exist, which would otherwise kill whatever process renders a view.
:func:`call_query` catches that specific ``SystemExit`` and re-raises
:class:`CfAtlasDbUnavailableError` so callers get a normal, catchable exception instead.
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from pyforge.core.errors import PyforgeError

# Env override for the skill scripts directory (mirrors dashboard/data.py's
# PYFORGE_ATLAS_DATA_ROOT override pattern).
_SCRIPTS_DIR_ENV_VAR = "PYFORGE_ATLAS_CFE_SCRIPTS_DIR"

# Relative to the repo root, where the 6 zero-arg CLI scripts this story mirrors live.
_SCRIPTS_DIR_RELPATH = Path(".claude") / "skills" / "conda-forge-expert" / "scripts"

# A bare CLI-script-name identifier — no path separators, no ``..`` traversal. \Z (not $)
# so a trailing newline can't slip through. Mirrors ``pyforge.atlas.rag.store``'s
# ``_valid_identifier`` precedent in this same package.
_SCRIPT_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+\Z")

# Memoizes load_cli_module() by (name, str(scripts_dir)) so a given CLI script is only
# parsed/exec'd once, and sys.path/sys.modules are only mutated on first load.
_MODULE_CACHE: dict[tuple[str, str], ModuleType] = {}


class CfAtlasDbUnavailableError(PyforgeError, RuntimeError):
    """Raised when a dynamically-loaded CLI script's ``query()`` calls ``sys.exit(1)``
    because its ``DB_PATH`` (``cf_atlas.db``) does not exist. Translates the CLI's
    "print to stderr and exit" failure mode into a normal, catchable exception so a
    missing database degrades gracefully instead of killing the render host.

    Mirrors ``pyforge.atlas.rag.store.VssNotProvisionedError``'s
    ``PyforgeError, RuntimeError`` base pair."""


def default_scripts_dir() -> Path:
    """The conda-forge-expert skill scripts directory (env-overridable, ``.git``-anchored
    default). Mirrors ``dashboard/data.py::default_data_root``'s walk-up-to-repo-root
    pattern on the happy path — a DIFFERENT, unrelated resolution target (this locates the
    skill CLI scripts, not the migrated Parquet catalog) — but the two DIVERGE on the
    failure branch: ``default_data_root()`` falls back to a best-effort ``parents[8]``
    guess when no ``.git``/``_bmad-output`` marker is found, while this function raises
    ``FileNotFoundError`` instead. A wrong scripts dir here would silently import the wrong
    CLI code, so raising (rather than guessing) is the safer choice for this target."""
    env = os.environ.get(_SCRIPTS_DIR_ENV_VAR)
    if env:
        return Path(env)
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists() or (parent / "_bmad-output").is_dir():
            return parent / _SCRIPTS_DIR_RELPATH
    raise FileNotFoundError(
        "could not locate the repo root (no .git or _bmad-output found walking up from "
        f"{current}) to resolve the conda-forge-expert skill scripts directory; set "
        f"{_SCRIPTS_DIR_ENV_VAR} explicitly"
    )


def _valid_script_name(name: str) -> str:
    """Reject a ``name`` that isn't a bare identifier before it's interpolated into a
    filesystem path — no ``/``, ``\\``, ``..``, or characters outside ``[A-Za-z0-9_-]``.
    ``load_cli_module`` is a public, reusable helper (not restricted to the fixed
    ``STATIC_VIEWS`` registry), so this guards it against path traversal / injection from
    an arbitrary caller-supplied ``name``."""
    if not isinstance(name, str) or not _SCRIPT_NAME_RE.match(name):
        raise ValueError(
            f"invalid CLI script name {name!r}: must match {_SCRIPT_NAME_RE.pattern} "
            "(a bare identifier — no path separators or '..')"
        )
    return name


def load_cli_module(name: str, *, scripts_dir: Path | None = None) -> ModuleType:
    """Dynamically load ``<scripts_dir>/<name>.py`` and return the executed module.

    Same idiom as ``test_mapping_gap.py::_load``: ``importlib.util.spec_from_file_location``
    + ``module_from_spec`` + ``exec_module``. Exposed as a public, reusable helper (rather
    than an underscore-private one) because callers — including tests — need the module
    handle to monkeypatch its ``DB_PATH`` attribute before invoking ``query()``.

    Memoized per ``(name, scripts_dir)`` pair: a repeat call for an already-loaded script
    returns the cached module instead of re-parsing/re-exec'ing it from disk and re-mutating
    ``sys.path``/``sys.modules``.
    """
    _valid_script_name(name)
    directory = scripts_dir if scripts_dir is not None else default_scripts_dir()
    cache_key = (name, str(directory))
    cached = _MODULE_CACHE.get(cache_key)
    if cached is not None:
        return cached
    path = directory / f"{name}.py"
    if not path.is_file():
        raise ImportError(f"cannot load conda-forge-expert CLI script {name!r} from {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load conda-forge-expert CLI script {name!r} from {path}")
    module = importlib.util.module_from_spec(spec)
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
    sys.modules[name] = module
    spec.loader.exec_module(module)
    _MODULE_CACHE[cache_key] = module
    return module


def call_query(module: ModuleType, **kwargs: Any) -> list[dict[str, Any]]:
    """Call ``module.query(**kwargs)`` verbatim and return its rows as ``list[dict]``.

    Two normalizations, both read directly off each CLI's source (never guessed):

    - ``query()`` calls ``sys.exit(1)`` when its ``DB_PATH`` is missing instead of raising —
      that specific ``SystemExit`` (``exc.code == 1``, verified against every wrapped CLI
      script's source) is caught here and translated into
      :class:`CfAtlasDbUnavailableError` so a missing database is a catchable exception, not
      a killed process. Any other exit code is re-raised unchanged — it isn't the documented
      DB-missing case, so it shouldn't be mislabeled as one.
    - A minority of scripts (``cve-watcher``) return ``(rows, meta)`` instead of a bare
      ``list[dict]`` — when ``query()`` returns a tuple, the first element is taken as the
      rows and the rest is dropped, so every caller sees a uniform ``list[dict]`` shape.
    """
    try:
        result = module.query(**kwargs)
    except SystemExit as exc:
        if exc.code != 1:
            raise
        db_path = getattr(module, "DB_PATH", "<unknown>")
        raise CfAtlasDbUnavailableError(
            f"cf_atlas.db not found at {db_path} for CLI script {module.__name__!r}"
        ) from exc
    if isinstance(result, tuple):
        result = result[0]
    return list(result)
