"""Full FR1 discovery: bounded recursive walk + deterministic selection
(Story 1.9, replacing the single-directory stub from 1.2/2.2/2.6).

``discover()`` walks the WHOLE tree under a scan target (sorted directory
order, ``.git`` pruned, an ~50,000-entry cap mirroring
``hygiene.has_adjacent_python_source``'s existing bound — but, unlike that
predicate's "cap exhaustion is inconclusive -> True" bias, a discovery cap
overrun FAILS CLOSED via a raised ``OSError``: silently truncating the scan
set would under-report ``resolved_scan_set`` without saying so, the exact
false-honesty shape this module exists to prevent). Selection is **union
coverage** (architecture.md's resolved decision, not a precedence winner):
every manifest kind found at every visited directory is reported — a
directory carrying both ``recipe.yaml`` and ``meta.yaml`` (or both
``environment.yml``/``environment.yaml``) keeps scanning both, unchanged
from the single-directory behavior. The manifest-kind vocabulary is now 8
fixed filenames: ``pyproject.toml`` (1.2), ``pixi.lock``/``conda-lock.yml``
(2.6), ``recipe.yaml``/``meta.yaml``/``environment.yml``/``pixi.toml`` (2.2),
and ``environment.yaml`` (1.9 — the equally-valid spelling conda itself
accepts; shares ``EnvironmentYmlExtractor`` with ``environment.yml``, see
``extract/__init__.py``). Every manifest path is recorded RELATIVE to the
original target (a determinism invariant), regardless of depth.

Stat-error honesty (per kind, per visited directory) is delegated
UNCHANGED to ``_discover_one`` — recursion is purely an orchestration
change (which directories get visited, in what order, with what
path-rewriting), never a change to how any single candidate is checked:

* existence is determined via an EXPLICIT ``stat`` — ``Path.is_file()``
  swallows every ``OSError`` (returns ``False``), which would read a
  permission-denied target as "no manifest" and green-light a scan that
  never looked (a false green). ``NotADirectoryError`` FAILS CLOSED: on a
  POSIX host it is the errno a scan target REPLACED BY A FILE mid-scan
  produces (the CLI's gate proved a directory at scan start, so ENOTDIR
  here is the TOCTOU state — or a direct API caller passed a
  non-directory; either way the manifest state is undeterminable, never
  "genuinely absent").
* A ``FileNotFoundError`` is disambiguated before it may claim absence — a
  dangling symlink (visibly present, target missing) and a directory that
  is gone at check time (vanished mid-scan, or never existed for a direct
  API caller) FAIL CLOSED with an ``OSError`` instead of reading as "no
  manifest" -> exit 0.
* A manifest that exists but is not a regular file (directory, FIFO,
  socket) also fails closed: found-but-refused must never be reported as
  "nothing existed".

The root of the walk is checked via ``_discover_one`` directly (BEFORE
``os.walk`` starts) so a bad root (vanished, replaced by a file, a
dangling symlink) still raises ``_discover_one``'s own crafted, tested
message — ``os.walk``'s own internal ``scandir`` failure for an unwalkable
root would otherwise surface a raw, undecorated ``OSError`` instead. A
subdirectory ``os.walk`` cannot even list (permission-denied, vanished
mid-walk) ALSO fails closed: the default ``onerror=None`` otherwise
swallows the failure and silently omits that subtree, which reads
identically to "genuinely nothing there" under it — the same false-green
this module's stat-honesty exists to prevent, now at any depth. Every
propagated ``OSError`` surfaces as an ``internal-error`` report in the CLI,
exit via ``exit_code_for(error)``.

This module reads the filesystem (existence check only); no subprocess,
no network.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from .models import ScannedManifest

# The manifest-kind tokens this module checks for (the full FR1 vocabulary,
# owned by Story 1.9).
PYPROJECT_KIND = "pyproject.toml"
PIXI_LOCK_KIND = "pixi.lock"
CONDA_LOCK_KIND = "conda-lock.yml"
# Story 2.2: the conda/pixi source-manifest wedge.
RECIPE_YAML_KIND = "recipe.yaml"
META_YAML_KIND = "meta.yaml"
ENVIRONMENT_YML_KIND = "environment.yml"
# Story 1.9: the equally-valid `environment.yaml` spelling (deferred-work.md's
# ledgered gap, now closed) — shares EnvironmentYmlExtractor with the `.yml`
# spelling; both coexisting in one directory scan both (union coverage).
ENVIRONMENT_YAML_KIND = "environment.yaml"
PIXI_TOML_KIND = "pixi.toml"

# Checked in this fixed order, at every visited directory; the returned
# tuple preserves (directory-visit order, then this per-directory order).
_DISCOVERED_KINDS = (
    PYPROJECT_KIND,
    PIXI_LOCK_KIND,
    CONDA_LOCK_KIND,
    RECIPE_YAML_KIND,
    META_YAML_KIND,
    ENVIRONMENT_YML_KIND,
    ENVIRONMENT_YAML_KIND,
    PIXI_TOML_KIND,
)

# ~50,000-entry cap mirroring hygiene.has_adjacent_python_source's bound
# (NFR-S5-shaped): a real project tree is orders of magnitude smaller; this
# exists so a pathological/huge tree can never turn a bounded discovery
# walk into unbounded work. Unlike that predicate's cap-exhaustion ->
# inconclusive/True bias, discovery has no honest "assume something"
# fallback of its own -- exceeding the cap FAILS CLOSED (raises), never a
# silently truncated resolved_scan_set.
_DISCOVERY_ENTRY_CAP = 50_000


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
    """Return the resolved scan set for ``target``: the bounded recursive
    walk's union of every manifest kind found at every visited directory
    (sorted order, ``.git`` pruned), each path rewritten RELATIVE to
    ``target``.

    Empty tuple when nothing in ``_DISCOVERED_KINDS`` exists anywhere under
    ``target`` (the empty-tree case: nothing existed to scan — the CLI's D2
    split then decides between ``not-applicable`` and the misconfiguration
    ``error`` guard via ``hygiene.has_adjacent_python_source``). A stat
    failure other than absence (e.g. ``PermissionError``, at any depth)
    propagates — "could not look" must never be reported as "nothing
    there" — and found-but-refused states (dangling symlink, non-regular
    file, non-directory/replaced/vanished target) fail closed the same way,
    for any kind, at any depth. Exceeding ``_DISCOVERY_ENTRY_CAP`` also
    fails closed (never a silently truncated ``resolved_scan_set``)."""
    manifests: list[ScannedManifest] = []

    def _record(current: Path) -> None:
        for kind in _DISCOVERED_KINDS:
            manifest = _discover_one(current, kind)
            if manifest is None:
                continue
            relative_path = (current / kind).relative_to(target).as_posix()
            manifests.append(ScannedManifest(path=relative_path, kind=kind))

    # The root is visited directly first (see module docstring): a bad root
    # must still raise _discover_one's own crafted, tested message, not
    # os.walk's raw internal scandir() failure.
    _record(target)

    entries_visited = 0

    def _on_error(exc: OSError) -> None:
        # A subdirectory os.walk cannot even list (permission-denied,
        # vanished mid-walk) fails CLOSED — see module docstring.
        raise exc

    root_visited = False
    for dirpath, dirnames, filenames in os.walk(target, onerror=_on_error):
        dirnames[:] = sorted(name for name in dirnames if name != ".git")
        entries_visited += len(dirnames) + len(filenames)
        if entries_visited > _DISCOVERY_ENTRY_CAP:
            raise OSError(
                f"discovery under {target} exceeded the "
                f"{_DISCOVERY_ENTRY_CAP}-entry cap; refusing a silently "
                "truncated scan"
            )
        if not root_visited:
            # os.walk's FIRST yielded tuple is always the root, already
            # handled by _record(target) above.
            root_visited = True
            continue
        _record(Path(dirpath))

    return tuple(manifests)
