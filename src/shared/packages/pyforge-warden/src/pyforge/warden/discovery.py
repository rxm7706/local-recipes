"""Recursive, bounded, deterministic multi-directory discovery (Story 1.9,
completing the single-directory stub from 1.2, extended 2.2/2.6).

FULL FR1 discovery is realized here: ``discover()`` walks the ENTIRE tree
under the scan target (sorted directory order, ``.git`` pruned, bounded by
a ~50,000-entry cap that FAILS CLOSED on overrun rather than silently
truncating), checking every one of the fixed manifest kinds at every
visited directory. Selection stays **union coverage** — architecture.md's
resolved decision: every manifest at every depth scans, there is no
precedence winner, so a directory carrying BOTH ``recipe.yaml`` and
``meta.yaml`` keeps reporting both, unchanged. The manifest-kind vocabulary:
``pyproject.toml`` (1.2), ``pixi.lock``/``conda-lock.yml`` (2.6),
``recipe.yaml``/``meta.yaml``/``environment.yml``/``pixi.toml`` (2.2), and
``environment.yaml`` (1.9 — a first-class kind sharing
``EnvironmentYmlExtractor`` with ``environment.yml``; both spellings
coexisting in one directory scan both). Every manifest path is recorded
RELATIVE to the ORIGINAL target (report paths are target-relative, a
determinism invariant) regardless of how deep it was found; the kind token
equals the filename.

A symlinked SUBDIRECTORY encountered mid-walk FAILS CLOSED with an
``OSError`` instead of being silently skipped: ``os.walk``'s default
``followlinks=False`` still lists a symlinked directory in ``dirnames`` (it
is CLASSIFIED as a directory) but simply never recurses into it, with no
signal at all — exactly the "found-but-refused must never be reported as
nothing existed" failure mode ``_discover_one`` already guards at file
granularity, reproduced here at directory granularity. ``followlinks``
stays ``False`` (never flipped to ``True``, which would need its own
cycle-detection this story does not own) — the guard below detects the
symlink explicitly, before any recursion attempt.

Stat-error honesty (per kind, in ``_discover_one`` — reused UNCHANGED for
every visited directory; recursion is purely an orchestration change in
``discover()``, never a change to how one candidate is checked): existence
is determined via an EXPLICIT ``stat`` — ``Path.is_file()`` swallows every
``OSError`` (returns ``False``), which would read a permission-denied
target as "no manifest" and green-light a scan that never looked (a false
green). ``NotADirectoryError`` FAILS CLOSED: on a POSIX host it is the
errno a scan target REPLACED BY A FILE mid-scan produces (the CLI's gate
proved a directory at scan start, so ENOTDIR here is the TOCTOU state — or
a direct API caller passed a non-directory; either way the manifest state
is undeterminable, never "genuinely absent"). A ``FileNotFoundError`` is
disambiguated before it may claim absence — a dangling symlink (visibly
present, target missing) and a scan target that is gone at discovery time
(vanished mid-scan, or never existed for a direct API caller) FAIL CLOSED
with an ``OSError`` instead of reading as "no manifest" → exit 0. A
manifest that exists but is not a regular file (directory, FIFO, socket)
also fails closed: found-but-refused must never be reported as "nothing
existed". Every propagated ``OSError`` surfaces as an ``internal-error``
report in the CLI, exit via ``exit_code_for(error)``.

This module reads the filesystem (existence + directory-tree walk only); no
subprocess, no network.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from .models import ScannedManifest

# The manifest-kind tokens this module checks for (the full FR1 vocabulary,
# owned here since 1.9).
PYPROJECT_KIND = "pyproject.toml"
PIXI_LOCK_KIND = "pixi.lock"
CONDA_LOCK_KIND = "conda-lock.yml"
# Story 2.2: the conda/pixi source-manifest wedge — 4 more fixed filenames.
RECIPE_YAML_KIND = "recipe.yaml"
META_YAML_KIND = "meta.yaml"
ENVIRONMENT_YML_KIND = "environment.yml"
# Story 1.9: the second environment.yml spelling — a first-class discovered
# kind sharing EnvironmentYmlExtractor/its routing rows with the above; both
# spellings coexisting in one directory scan both (union coverage).
ENVIRONMENT_YAML_KIND = "environment.yaml"
PIXI_TOML_KIND = "pixi.toml"

# Checked in this fixed order at every visited directory; the returned tuple
# preserves it within each directory (the walk visits directories in sorted,
# deterministic DFS-preorder — see discover()).
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

# NFR-S5-style bound (mirrors hygiene.has_adjacent_python_source's own
# entry cap): the max number of directory entries (dirnames + filenames,
# summed per visited directory) examined before giving up. A real project's
# tree is orders of magnitude smaller; this exists so a pathological/huge
# tree can never turn a bounded discovery walk into an unbounded one.
# Unlike that predicate's "can't tell -> assume present" bias, discovery
# FAILS CLOSED on overrun: a silent partial scan is never acceptable here.
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


def _visit_directory(
    directory: Path, root: Path, manifests: list[ScannedManifest]
) -> None:
    """Run the per-kind stat-honesty check (``_discover_one``, unchanged)
    against ``directory``, appending every hit to ``manifests`` with its
    path rewritten relative to ``root`` when ``directory`` is not ``root``
    itself (the root case keeps the pre-1.9 bare-kind path, byte-for-byte)."""
    for kind in _DISCOVERED_KINDS:
        manifest = _discover_one(directory, kind)
        if manifest is None:
            continue
        if directory != root:
            relative_path = (directory.relative_to(root) / manifest.path).as_posix()
            manifest = ScannedManifest(path=relative_path, kind=manifest.kind)
        manifests.append(manifest)


def discover(target: Path) -> tuple[ScannedManifest, ...]:
    """Return the resolved scan set for ``target``: a bounded, deterministic
    recursive walk of the FULL tree under ``target`` (Story 1.9), checking
    every one of the fixed manifest kinds at every visited directory —
    union coverage, never a precedence winner (architecture.md's resolved
    decision). Directories are visited in sorted-dirname DFS-preorder (same
    tree -> same set, always: the AC's determinism requirement); within one
    directory, kinds are checked in ``_DISCOVERED_KINDS`` order. ``.git``
    directories are pruned (never genuinely a project's own manifests).

    ``target`` itself is checked FIRST via the exact pre-1.9 single-
    directory path (``_visit_directory(target, target, ...)``, before any
    ``os.walk`` call) — reproducing every existing "target itself is
    invalid" failure mode (not-a-directory, vanished, permission-denied)
    byte-for-byte, since ``os.walk``'s own first ``scandir`` failure would
    otherwise surface a raw, differently-worded ``OSError``.

    A symlinked SUBDIRECTORY anywhere in the tree FAILS CLOSED with an
    ``OSError`` (see module docstring) instead of being silently skipped —
    checked, and any recursion into it refused, BEFORE that subdirectory is
    ever visited. Exceeding ``_DISCOVERY_ENTRY_CAP`` (summed per visited
    directory) also FAILS CLOSED with an ``OSError`` — never a silent
    partial scan.

    Empty tuple when none of the fixed kinds exist anywhere under
    ``target`` (the empty-tree case: nothing existed to scan). A stat
    failure other than absence (e.g. ``PermissionError`` reaching a nested
    subdirectory mid-walk) propagates — "could not look" must never be
    reported as "nothing there" — and found-but-refused states (dangling
    symlink, non-regular file, non-directory/replaced/vanished target,
    symlinked subdirectory) fail closed the same way, at any depth."""
    manifests: list[ScannedManifest] = []
    _visit_directory(target, target, manifests)

    entries_visited = 0

    def _reraise(exc: OSError) -> None:
        # os.walk's default onerror=None SILENTLY drops a subtree it could
        # not scandir into (permission-denied, vanished mid-walk) — the
        # exact "could not look" reads as "nothing there" false-green this
        # module exists to refuse. Re-raising here propagates it out of the
        # walk instead.
        raise exc

    for dirpath, dirnames, filenames in os.walk(
        target, topdown=True, onerror=_reraise, followlinks=False
    ):
        current = Path(dirpath)
        dirnames[:] = sorted(name for name in dirnames if name != ".git")
        for name in dirnames:
            child = current / name
            if child.is_symlink():
                # os.walk still CLASSIFIES a symlinked directory into
                # dirnames (that classification follows the symlink) but
                # simply never recurses into it when followlinks=False —
                # silently, with no signal at all. Fail closed instead: a
                # manifest reachable only through this subdirectory must
                # never read as "nothing existed" (see module docstring).
                raise OSError(
                    f"{child} is a symlinked subdirectory; recursive "
                    "discovery refuses to silently skip it — manifest "
                    "state under it is undeterminable"
                )
        entries_visited += len(dirnames) + len(filenames)
        if entries_visited > _DISCOVERY_ENTRY_CAP:
            raise OSError(
                f"discovery under {target} exceeded the "
                f"{_DISCOVERY_ENTRY_CAP}-entry bound; refusing a silent "
                "partial scan"
            )
        if current == target:
            continue  # root already handled above
        _visit_directory(current, target, manifests)
    return tuple(manifests)
