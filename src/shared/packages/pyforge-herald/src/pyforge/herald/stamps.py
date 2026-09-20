"""Provenance sidecars for every derived deck artifact (Story 23.3).

Neither the trio derive path (``scripts/deck_trio.py``) nor the export
derive path (``scripts/deck_export.py``/``deck_pipeline.py``'s ``pull_*``
functions) records which git tree or Design prototype revision a derived
artifact was produced at -- so a stale derived file is invisible without
manual inspection (the story's own Problem statement). This module is the
one shared primitive that closes that gap: ``write_stamp`` writes a
``<artifact-path>.stamp.json`` sidecar next to a just-derived artifact,
naming the source tree ref and the deck's current Design prototype etag;
``read_stamp`` reads one back.

**Tree.** ``git rev-parse HEAD`` plus ``git status --porcelain
--untracked-files=no`` (a ``-dirty`` suffix when tracked files are
uncommitted) -- mirrors ``scripts/deck_facts.py::head_info``'s own ``tree``
field exactly, duplicated here rather than imported: this is a package
module, and importing a ``scripts/`` module from it would be a
package -> scripts dependency this codebase does not otherwise have.

**Etag.** The deck's current registered Design prototype etag
(``state.read(...).etags.get("prototype")``), ``None`` when the deck has
never been seeded or has no state file at all -- a single "which Design
revision was live when this was last derived" signal, not a per-artifact
provenance chain (Design Notes: "Etag semantics"). The string literal
``"prototype"`` mirrors ``deck_pipeline.PROTOTYPE_ARTIFACT_KEY`` -- not
imported, to avoid a cycle, since ``deck_pipeline.py`` itself imports this
module.

Every failure (git not runnable, not a git repository, a corrupt bridge
state file) raises ``errors.HeraldError`` naming what failed, mirroring
this package's AD-6 discipline -- never a raw ``subprocess`` or ``OSError``
leak.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pyforge.core.atomic_write import atomic_write_text

from . import errors, state

_PROTOTYPE_ARTIFACT_KEY = "prototype"
"""Mirrors ``deck_pipeline.PROTOTYPE_ARTIFACT_KEY`` -- duplicated, not
imported (see module docstring)."""

_GIT_TIMEOUT_SECONDS = 30.0
"""Bounds ``_git`` the same way ``deck_pipeline._PixiPartialDeckExporter``
bounds its own subprocess call -- a hung ``git`` (lock contention, a
network-mounted ``.git``) must not block a stamp write forever."""


@dataclass(frozen=True)
class Stamp:
    """One artifact's provenance record: the source tree ref, the deck's
    current Design prototype etag (``None`` when unseeded), and when this
    stamp was written (UTC ISO-8601)."""

    tree: str
    etag: str | None
    derived_at: str


def _stamp_path(artifact_path: Path) -> Path:
    """``<artifact-path>.stamp.json`` -- appended to the full original
    filename (never a suffix swap), so ``foo.pptx`` stamps as
    ``foo.pptx.stamp.json``."""
    return artifact_path.with_name(artifact_path.name + ".stamp.json")


def _git(repo_root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise errors.HeraldError(
            f"could not write stamp: 'git {' '.join(args)}' in {repo_root} exceeded {_GIT_TIMEOUT_SECONDS}s ({exc})"
        ) from exc
    except (OSError, subprocess.CalledProcessError) as exc:
        raise errors.HeraldError(
            f"could not write stamp: 'git {' '.join(args)}' failed in {repo_root} ({exc})"
        ) from exc
    return completed.stdout.strip()


def _tree_ref(repo_root: Path) -> str:
    """HEAD's sha, suffixed ``-dirty`` when tracked files are uncommitted
    -- mirrors ``scripts/deck_facts.py::head_info``'s ``tree`` field."""
    sha = _git(repo_root, "rev-parse", "HEAD")
    dirty = bool(_git(repo_root, "status", "--porcelain", "--untracked-files=no"))
    return f"{sha}-dirty" if dirty else sha


def _current_etag(repo_root: Path, slug: str) -> str | None:
    """The deck's current registered prototype etag, or ``None`` when the
    deck has never been seeded (no state entry) or the state file does not
    exist at all -- both read as "no etag to record", never an error."""
    deck_state = state.read(repo_root / state.DEFAULT_STATE_PATH, slug)
    if deck_state is None:
        return None
    return deck_state.etags.get(_PROTOTYPE_ARTIFACT_KEY)


def write_stamp(artifact_path: Path, *, repo_root: Path, slug: str) -> None:
    """Write ``<artifact_path>.stamp.json`` next to a just-derived
    artifact, naming the current source tree ref and the deck's current
    Design prototype etag (``None`` when unseeded). Writes atomically
    (``pyforge.core.atomic_write_text``), mirroring every other write in
    this package.

    Raises ``errors.HeraldError`` naming what failed when the source tree
    ref cannot be determined (git not runnable, ``repo_root`` is not a git
    repository), when the bridge state file is corrupt, or when the
    filesystem otherwise refuses the write."""
    artifact_path = Path(artifact_path)
    repo_root = Path(repo_root)
    stamp = Stamp(
        tree=_tree_ref(repo_root),
        etag=_current_etag(repo_root, slug),
        derived_at=datetime.now(timezone.utc).isoformat(),
    )
    payload = {"tree": stamp.tree, "etag": stamp.etag, "derived_at": stamp.derived_at}
    stamp_path = _stamp_path(artifact_path)
    try:
        atomic_write_text(stamp_path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    except (OSError, ValueError) as exc:
        raise errors.HeraldError(f"could not write stamp {stamp_path}: {exc}") from exc


def read_stamp(artifact_path: Path) -> Stamp | None:
    """``artifact_path``'s stamp, or ``None`` when no sidecar exists yet.

    Raises ``errors.HeraldError`` naming the stamp path when it exists but
    is not valid JSON, does not hold a JSON object, is missing or carries
    an extra field beyond ``tree``/``etag``/``derived_at`` (mirrors
    ``state.py``'s own unknown-field discipline), or carries the wrong
    type for one of them (``tree``/``derived_at`` must be a string,
    ``etag`` a string or null) -- a present-but-corrupt stamp is
    corruption, not "no stamp
    yet"."""
    stamp_path = _stamp_path(Path(artifact_path))
    try:
        text = stamp_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError) as exc:
        raise errors.HeraldError(f"stamp {stamp_path} could not be read: {exc}") from exc
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise errors.HeraldError(f"stamp {stamp_path} is not valid JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise errors.HeraldError(f"stamp {stamp_path} does not hold a JSON object at its top level")
    known = {"tree", "etag", "derived_at"}
    missing = sorted(known - set(document))
    if missing:
        raise errors.HeraldError(f"stamp {stamp_path} is missing field(s) {', '.join(missing)}")
    unknown = sorted(set(document) - known)
    if unknown:
        raise errors.HeraldError(f"stamp {stamp_path} carries unknown field(s) {', '.join(map(repr, unknown))}")
    tree = document["tree"]
    etag = document["etag"]
    derived_at = document["derived_at"]
    if not isinstance(tree, str):
        raise errors.HeraldError(f"stamp {stamp_path} field 'tree' must be a string, not {type(tree).__name__}")
    if etag is not None and not isinstance(etag, str):
        raise errors.HeraldError(f"stamp {stamp_path} field 'etag' must be a string or null, not {type(etag).__name__}")
    if not isinstance(derived_at, str):
        raise errors.HeraldError(
            f"stamp {stamp_path} field 'derived_at' must be a string, not {type(derived_at).__name__}"
        )
    return Stamp(tree=tree, etag=etag, derived_at=derived_at)
