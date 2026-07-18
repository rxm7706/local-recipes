"""The Karpathy-wiki storage LAYOUT contract — its SINGLE owner (Story H1, FR-22(a), AD-22).

The AI Software Factory (§ 7) keeps its "brain storage" in a strict three-stage tree
(§ 7.4). This module is the ONE place that tree's shape is defined; every crew (H2), the
Wagtail syncer (H3), and the Dagster orchestration (H4) discover stage paths through
:class:`WikiLayout` / :func:`scaffold_wiki` — they never reconstruct the ``raw/compiled/
outputs`` names themselves (Spine single-owner convention, mirroring ``publish/emitter.py``).

The three stages (§ 7.4), in fixed pipeline order:

* ``raw/``      — the raw Parquet ingestion landing zone (the Ingester writes here).
* ``compiled/`` — knowledge graphs, BSL-mapped concepts, linked-dependency files
  (the Compiler + Linker write here).
* ``outputs/``  — final markdown reports, slide decks, generated visualizations
  (the Oracle writes here; the H3 syncer reads here to push to the CMS).

**AD-22 (factory write-boundary).** The factory layer *reads* pipeline outputs (via the
Kedro catalog / BSL) and *writes* ONLY this wiki tree (and, in H3, the Wagtail CMS). It
never writes an atlas dataset. :func:`scaffold_wiki` therefore only ever creates
directories UNDER its ``root`` — and :func:`stage_path` refuses any key/relative path that
would escape the stage dir, so a crafted document name can't turn a wiki write into a write
outside the tree (the ``publish/emitter.py`` ``_require_safe_name`` lesson, applied here).
"""

from __future__ import annotations

from pathlib import Path

#: The three wiki stages in fixed pipeline order (raw -> compiled -> outputs). DEFINED ONCE
#: HERE; consumers import this tuple, they never re-list the stage names.
WIKI_STAGES: tuple[str, ...] = ("raw", "compiled", "outputs")


def _require_safe_segment(segment: str) -> str:
    """Reject any path segment that is not a single, in-tree name.

    A document/relative name is joined onto a stage dir and may be created — an unsanitized
    ``..``/absolute/separator name would let a factory write escape the wiki root, breaking the
    AD-22 write-boundary. Reject traversal, separators, and absolute paths BEFORE any join.
    """
    if not isinstance(segment, str) or not segment:
        raise ValueError(f"path segment must be a non-empty string, got {segment!r}")
    if segment in (".", "..") or ".." in Path(segment).parts:
        raise ValueError(f"unsafe wiki path {segment!r}: '..' traversal is not allowed")
    p = Path(segment)
    if p.is_absolute() or (p.drive or p.root):
        raise ValueError(f"unsafe wiki path {segment!r}: must be relative to the stage dir")
    return segment


class WikiLayout:
    """The resolved on-disk shape of ONE Karpathy wiki, rooted at ``root``.

    Construct it around a directory ("the wiki root"); it exposes each stage's path and a
    guarded :meth:`stage_path` for addressing a file WITHIN a stage. It performs no IO on
    construction — call :meth:`ensure` (or :func:`scaffold_wiki`) to materialize the tree.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def stage_dir(self, stage: str) -> Path:
        """The directory for ``stage`` (one of :data:`WIKI_STAGES`)."""
        if stage not in WIKI_STAGES:
            raise ValueError(f"unknown wiki stage {stage!r}; expected one of {WIKI_STAGES}")
        return self.root / stage

    def stage_path(self, stage: str, relative: str) -> Path:
        """Resolve ``relative`` INSIDE ``stage`` — the only sanctioned way to address a wiki
        file. ``relative`` may name sub-dirs (``reports/2026.md``) but may never escape the
        stage dir (AD-22 write-boundary; every segment is safety-checked)."""
        base = self.stage_dir(stage)
        if not isinstance(relative, str) or not relative:
            raise ValueError(f"wiki path must be a non-empty string, got {relative!r}")
        parts = Path(relative).parts
        if not parts:  # e.g. "." collapses to no parts — addresses the stage dir itself
            raise ValueError(f"wiki path {relative!r} does not name a file within the stage")
        for part in parts:
            _require_safe_segment(part)
        return base / relative

    def ensure(self) -> "WikiLayout":
        """Create ``root`` and each stage dir (idempotent); return self for chaining."""
        for stage in WIKI_STAGES:
            self.stage_dir(stage).mkdir(parents=True, exist_ok=True)
        return self


def scaffold_wiki(root: str | Path) -> WikiLayout:
    """Materialize the ``raw/ -> compiled/ -> outputs/`` tree under ``root`` and return its
    :class:`WikiLayout`. Idempotent: re-running against an existing wiki is a no-op (never
    destructive — the factory only ever ADDS to the tree, per AD-22)."""
    return WikiLayout(root).ensure()
