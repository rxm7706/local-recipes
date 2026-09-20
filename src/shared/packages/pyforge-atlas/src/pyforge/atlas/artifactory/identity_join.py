"""Identity join and internal flag -- Story 15.2 (CAP-2, CAP-3, Epic 15).

Resolves Story 15.1's raw :class:`~pyforge.atlas.artifactory.aql_adapter.DownloadRow`\\ s
against atlas's identity space: attaches ``conda_name``/``match_source`` from the
already-materialized Phase C/C.5 ``pypi_conda_mapping`` catalog output, and independently
flags ``is_internal`` from Phase D's ``pypi_universe`` catalog output -- true iff the row's
name is absent from the public universe. Both inputs are plain ``pd.DataFrame`` arguments
passed in; nothing is fetched here (no new PyPI-metadata or conda-forge-crossref path).

A plain function over ``pd.DataFrame`` inputs, not a Kedro node -- it lives in
``artifactory/``, a sibling of ``pipelines/`` that ``find_pipelines(raise_errors=True)``
never touches, matching Story 15.1's shape. Story 15.3 (CAP-4) owns wiring this into an
actual pipeline node/catalog entry; that wiring is explicitly out of scope here.

``_normalize_pypi_name``/``_is_missing`` are reimplemented locally rather than imported --
this codebase's established rule is that no pipeline package imports another's ``nodes.py``
module (see ``upstream_discovery/nodes.py::_is_missing``'s docstring for the precedent).

**Provenance-rank collapse.** ``pypi_conda_mapping`` is NOT pre-collapsed to one row per
``pypi_name`` -- the Phase C/C.5 export (``pypi_intelligence/nodes.py::match_source_urls``)
only dedupes on ``["pypi_name", "conda_name"]``, so two rows for the same ``pypi_name`` with
different ``conda_name``/``match_source`` values are a real, reachable shape of the
persisted table. Collapsing to one row per normalized ``pypi_name`` here replicates the
same rank + tie-break RULE ``pypi_intelligence/nodes.py::export_pypi_conda_map`` uses (also
reimplemented locally, same no-cross-import convention): ``_MAP_PROVENANCE_RANK``
(``g10_spelling`` > ``parselmouth``/``recipe_source_url`` > unknown), a strictly-higher rank
always wins, and on an equal-rank collision with a different ``conda_name`` the
lexicographically smaller ``conda_name`` wins -- a deterministic tie-break so the winning
``conda_name`` never depends on DataFrame row order. (Two differences from that precedent,
neither a correctness gap: this module keys the collapse by the PEP-503-NORMALIZED
``pypi_name`` -- required so an Artifactory-observed name matches regardless of casing/
separator variance -- where ``export_pypi_conda_map`` keys by the raw name; and this module
also tracks ``match_source`` per key, which that precedent does not, so it additionally
tie-breaks same-``conda_name``/same-rank rows on ``match_source`` too, below.) A naive
first-seen/``setdefault`` collapse would pick whichever row happens to be first in Parquet
iteration order (not a stable contract) and could resolve to a lower-provenance ``conda_name``
than Phase C/C.5's own canonical export would -- silently diverging from what every other
atlas signal reports for the same package.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from .aql_adapter import DownloadRow

_PEP503_RUN_RE = re.compile(r"[-_.]+")

# Mirrors pypi_intelligence/nodes.py::_MAP_PROVENANCE_RANK exactly -- reimplemented locally
# per the no-cross-package-nodes-import convention (see module docstring).
_MAP_PROVENANCE_RANK = {"g10_spelling": 3, "parselmouth": 2, "recipe_source_url": 2}


def _normalize_pypi_name(name: str) -> str:
    """PEP 503 name normalization: lowercase, collapse runs of ``-``/``_``/``.``
    into a single ``-``. Mirrors ``upstream_discovery/nodes.py::_normalize_pypi_name``
    deliberately rather than importing it (no-cross-package-``nodes.py``-import convention)."""
    return _PEP503_RUN_RE.sub("-", name).lower()


def _is_missing(v) -> bool:
    """Scalar-safe missing check -- ``True`` for ``None``/NaN/``pd.NA``, ``False`` for a
    real value INCLUDING a list/dict cell (``pd.isna`` on a non-scalar returns an array
    whose truth value is ambiguous, so non-scalars are treated as present rather than
    crashing). Mirrors ``upstream_discovery/nodes.py::_is_missing`` /
    ``pypi_intelligence/nodes.py::_is_missing`` deliberately rather than importing either --
    same no-cross-package-``nodes.py``-import convention."""
    if v is None:
        return True
    if isinstance(v, (list, tuple, dict, set)):
        return False
    try:
        return bool(pd.isna(v))
    except ValueError, TypeError:
        return False


@dataclass(frozen=True)
class JoinedDownloadRow:
    """One :class:`~pyforge.atlas.artifactory.aql_adapter.DownloadRow` resolved against
    atlas's identity space. ``conda_name``/``match_source`` are ``None`` when the package
    has no ``pypi_conda_mapping`` match (or that table is unusable). ``is_internal`` is
    ``True`` iff ``pypi_name`` is absent from ``pypi_universe`` (a searchable table) --
    independent of the mapping match."""

    pypi_name: str
    version: str
    download_count: int
    conda_name: str | None
    match_source: str | None
    is_internal: bool


def _normalized_universe_index(pypi_universe: pd.DataFrame) -> set[str]:
    """``{normalized pypi_name}`` from ``pypi_universe.pypi_name`` -- the membership index
    :func:`join_identity` checks ``is_internal`` against, built ONCE and reused across every
    row. An empty/malformed table (missing ``pypi_name``, or carrying zero non-null names)
    degrades to ``set()`` -- never raises. An empty result also signals "unusable" to the
    caller, which must NOT treat that as every name being absent (see :func:`join_identity`'s
    docstring for the ``is_internal`` degradation policy)."""
    if (
        pypi_universe is None
        or getattr(pypi_universe, "empty", True)
        or "pypi_name" not in getattr(pypi_universe, "columns", [])
    ):
        return set()
    index: set[str] = set()
    for name in pypi_universe["pypi_name"]:
        if _is_missing(name):
            continue
        index.add(_normalize_pypi_name(str(name)))
    return index


def _normalized_mapping_index(
    pypi_conda_mapping: pd.DataFrame,
) -> dict[str, tuple[str, str | None]]:
    """``{normalized pypi_name: (conda_name, match_source)}`` collapsed from
    ``pypi_conda_mapping``, built ONCE and reused across every row. ``pypi_conda_mapping``
    can carry multiple rows per ``pypi_name`` (Code Map / module docstring); collapse rule is
    the SAME provenance-rank + lexicographic tie-break as
    ``pypi_intelligence/nodes.py::export_pypi_conda_map``: a strictly-higher-rank row always
    wins; on an equal-rank collision with a different ``conda_name``, the lexicographically
    smaller ``conda_name`` wins (deterministic, order-independent -- never a naive
    first-seen/``setdefault`` collapse). An empty/malformed table (missing ``pypi_name``/
    ``conda_name``) degrades to ``{}`` -- never raises."""
    if (
        pypi_conda_mapping is None
        or getattr(pypi_conda_mapping, "empty", True)
        or not {"pypi_name", "conda_name"} <= set(getattr(pypi_conda_mapping, "columns", []))
    ):
        return {}
    has_source = "match_source" in pypi_conda_mapping.columns
    out: dict[str, tuple[str, str | None]] = {}
    ranks: dict[str, int] = {}
    for row in pypi_conda_mapping.itertuples(index=False):
        pypi_name = getattr(row, "pypi_name", None)
        conda_name = getattr(row, "conda_name", None)
        if _is_missing(pypi_name) or _is_missing(conda_name) or not isinstance(conda_name, str):
            continue
        key = _normalize_pypi_name(str(pypi_name))
        match_source = getattr(row, "match_source", None) if has_source else None
        # match_source may be a non-string / unhashable cell (malformed) -- default rank 1.
        rank = _MAP_PROVENANCE_RANK.get(match_source, 1) if isinstance(match_source, str) else 1
        normalized_source = match_source if isinstance(match_source, str) else None
        existing = out.get(key)
        # no-clobber: replace on STRICTLY higher provenance; on an EQUAL-tier collision, break
        # ties deterministically -- first by the lexicographically smaller conda_name, THEN
        # (same conda_name too, differing only in match_source, e.g. two rank-2 sources) by the
        # lexicographically smaller match_source -- so the result never depends on
        # pypi_conda_mapping row order, for either kind of collision.
        if existing is None or rank > ranks[key]:
            replace = True
        elif rank == ranks[key]:
            if conda_name != existing[0]:
                replace = conda_name < existing[0]
            else:
                replace = (normalized_source or "") < (existing[1] or "")
        else:
            replace = False
        if replace:
            out[key] = (conda_name, normalized_source)
            ranks[key] = rank
    return out


def join_identity(
    rows: list[DownloadRow],
    pypi_conda_mapping: pd.DataFrame,
    pypi_universe: pd.DataFrame,
) -> list[JoinedDownloadRow]:
    """Resolve each ``DownloadRow`` against atlas's identity space (CAP-2/CAP-3).

    Builds the normalized ``pypi_universe`` membership index and the normalized
    ``pypi_conda_mapping`` index ONCE (each collapsed/deduped per the rules in their
    respective builders above), then resolves every row against both:

    - ``conda_name``/``match_source`` come from the (provenance-rank-collapsed)
      ``pypi_conda_mapping`` match for the row's normalized name, or ``None``/``None`` if
      there is no match (or the table is unusable).
    - ``is_internal`` is ``True`` iff the row's normalized name is absent from a USABLE
      ``pypi_universe`` -- independent of the mapping match. An unusable ``pypi_universe``
      (empty, missing ``pypi_name``, or zero searchable names) degrades ``is_internal`` to
      ``False`` for every row rather than confidently claiming every row is internal off a
      signal that was never actually searchable (mirrors
      ``upstream_discovery/nodes.py::classify_trending_candidates``'s ``universe_usable``
      guard).

    Never raises on empty/malformed input DataFrames, or on a ``None``/empty ``rows``."""
    if not rows:
        return []
    universe_index = _normalized_universe_index(pypi_universe)
    universe_usable = bool(universe_index)
    mapping_index = _normalized_mapping_index(pypi_conda_mapping)

    out: list[JoinedDownloadRow] = []
    for row in rows:
        key = _normalize_pypi_name(row.name)
        conda_name, match_source = mapping_index.get(key, (None, None))
        is_internal = universe_usable and key not in universe_index
        out.append(
            JoinedDownloadRow(
                pypi_name=row.name,
                version=row.version,
                download_count=row.download_count,
                conda_name=conda_name,
                match_source=match_source,
                is_internal=is_internal,
            )
        )
    return out
