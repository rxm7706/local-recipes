"""Single-directory, fixed-kind-list discovery (Story 1.2, extended 2.6).

OWNERSHIP DECISION (recorded): full FR1 discovery — multi-manifest
enumeration, deterministic selection policy, and the manifest-kind
vocabulary — is Story 1.9's. This module locates each of a FIXED list of
manifest kinds directly in the scan target: ``pyproject.toml`` (1.2),
``pixi.lock`` and ``conda-lock.yml`` (2.6), ``recipe.yaml``, ``meta.yaml``,
``environment.yml``, and ``pixi.toml`` (2.2 — additive, narrow: 4 more
filenames, same stat-honesty pattern; NOT 1.9's precedence/recursive-search
policy — a directory carrying BOTH ``recipe.yaml`` and ``meta.yaml`` is not
this module's concern, it reports both). Every manifest path is recorded
RELATIVE to the target (report paths are target-relative, a determinism
invariant); the kind token equals the filename.

Stat-error honesty (per kind): existence is determined via an EXPLICIT
``stat`` — ``Path.is_file()`` swallows every ``OSError`` (returns
``False``), which would read a permission-denied target as "no manifest"
and green-light a scan that never looked (a false green). ``NotADirectoryError``
FAILS CLOSED: on a POSIX host it is the errno a scan target REPLACED BY A
FILE mid-scan produces (the CLI's gate proved a directory at scan start, so
ENOTDIR here is the TOCTOU state — or a direct API caller passed a
non-directory; either way the manifest state is undeterminable, never
"genuinely absent"). A ``FileNotFoundError`` is disambiguated before it
may claim absence — a dangling symlink (visibly present, target missing)
and a scan target that is gone at discovery time (vanished mid-scan, or
never existed for a direct API caller) FAIL CLOSED with an ``OSError``
instead of reading as "no manifest" → exit 0. A manifest that exists but is
not a regular file (directory, FIFO, socket) also fails closed:
found-but-refused must never be reported as "nothing existed". Every
propagated ``OSError`` surfaces as an ``internal-error`` report in the CLI,
exit via ``exit_code_for(error)``.

This module reads the filesystem (existence check only); no subprocess,
no network.
"""

from __future__ import annotations

import stat
from pathlib import Path

from .models import ScannedManifest

# The manifest-kind tokens this module checks for (vocabulary owned by
# Story 1.9; this is a fixed, narrow list — not the full FR1 vocabulary).
PYPROJECT_KIND = "pyproject.toml"
PIXI_LOCK_KIND = "pixi.lock"
CONDA_LOCK_KIND = "conda-lock.yml"
# Story 2.2: the conda/pixi source-manifest wedge — 4 more fixed filenames.
RECIPE_YAML_KIND = "recipe.yaml"
META_YAML_KIND = "meta.yaml"
ENVIRONMENT_YML_KIND = "environment.yml"
PIXI_TOML_KIND = "pixi.toml"

# Checked in this fixed order; the returned tuple preserves it.
_DISCOVERED_KINDS = (
    PYPROJECT_KIND,
    PIXI_LOCK_KIND,
    CONDA_LOCK_KIND,
    RECIPE_YAML_KIND,
    META_YAML_KIND,
    ENVIRONMENT_YML_KIND,
    PIXI_TOML_KIND,
)


def _discover_one(target: Path, kind: str) -> ScannedManifest | None:
    """The stat-honesty check (see module docstring) for one manifest
    ``kind`` directly under ``target``. ``None`` means genuinely absent (the
    empty-dir case for this kind); every found-but-refused / undeterminable
    state FAILS CLOSED via a raised ``OSError`` instead."""
    candidate = target / kind
    try:
        result = candidate.stat()
    except NotADirectoryError as exc:
        # ``target`` (or a path component under it) is not a directory. The
        # CLI's gate proved a directory at scan start, so ENOTDIR here means
        # the target was REPLACED mid-scan (TOCTOU) — or a direct API caller
        # passed a file. Manifest state undeterminable: FAIL CLOSED, never
        # "no manifest" → exit 0.
        raise OSError(
            f"scan target {target} is not a directory (replaced mid-scan, "
            "or a non-directory was passed); manifest state undeterminable"
        ) from exc
    except FileNotFoundError as exc:
        if candidate.is_symlink():
            # Visibly present but its target is missing: found-but-refused,
            # never "nothing existed".
            raise OSError(
                f"{kind} in {target} is a dangling symlink; "
                "manifest state undeterminable"
            ) from exc
        try:
            target_result = target.stat()
        except FileNotFoundError:
            # Indistinguishable states from here: vanished after the CLI
            # gate (TOCTOU) or never existed (direct API caller) — claim
            # neither as fact.
            raise OSError(
                f"scan target {target} vanished mid-scan or never existed; "
                "manifest state undeterminable"
            ) from exc
        if not stat.S_ISDIR(target_result.st_mode):
            raise OSError(
                f"scan target {target} is no longer a directory; manifest "
                "state undeterminable"
            ) from exc
        return None
    if not stat.S_ISREG(result.st_mode):
        raise OSError(
            f"{kind} in {target} exists but is not a regular "
            f"file (mode {stat.filemode(result.st_mode)!r}); refusing to "
            "read it must never read as absent"
        )
    return ScannedManifest(path=kind, kind=kind)


def discover(target: Path) -> tuple[ScannedManifest, ...]:
    """Return the resolved scan set for ``target``: one entry per manifest
    kind (in ``_DISCOVERED_KINDS`` order) that is found directly in
    ``target``.

    Empty tuple when none of the fixed kinds exist directly in ``target``
    (the empty-dir case: nothing existed to scan). A stat failure other
    than absence (e.g. ``PermissionError``) propagates — "could not look"
    must never be reported as "nothing there" — and found-but-refused
    states (dangling symlink, non-regular file, non-directory/replaced/
    vanished target) fail closed the same way, for any kind."""
    manifests: list[ScannedManifest] = []
    for kind in _DISCOVERED_KINDS:
        manifest = _discover_one(target, kind)
        if manifest is not None:
            manifests.append(manifest)
    return tuple(manifests)
