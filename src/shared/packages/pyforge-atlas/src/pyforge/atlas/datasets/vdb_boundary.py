"""VDB read-boundary helpers (Story B2 — Gap G-3 resolution; AC-3 clause (b)).

The AppThreat vulnerability-db (``vulnerability_vdb_store``) is a ~2.5 GB read-only
store. Its FLIP to a real read-only VDB dataset class is genuinely **B5**'s
(external-refresh asset wrapping ``vdb-refresh``, vuln-db env). B2 consumes the interim
store PATH (``MemoryDataset``); the vdb **parse** + the ``_coerce_cvss_score`` ScoreType
unwrap are a **dataset/boundary** concern, kept OUT of the pure ``vulnerability`` node
bodies (Gap G-3). This module carries the pure, IO-free coercion so the AC-3(b)
contract is preserved + fixture-tested at the boundary layer (``tests/datasets/``),
never in a node.

**AC-3(b) — the ``_coerce_cvss_score`` unwrap** (legacy: ``detail_cf_atlas.py:295``,
OUTSIDE the read-only skill include set; Phase G reaches it via
``from detail_cf_atlas import fetch_vdb_data``, CFA:3829). vdb 6.6.2's partial
``model_dump`` leaves the CVSS ``baseScore`` as a pydantic ``ScoreType`` wrapper
(``RootModel``-like: a ``.root`` / ``.value`` attribute, or a ``{"root": <n>}`` /
``{"value": <n>}`` mapping) rather than a bare float. Sorting / thresholding on a raw
ScoreType throws; every consumer must unwrap first. This is a PURE scalar transform on
an already-fetched value (no IO), so it lives at the boundary — the node receives
already-coerced floats.

No HTTP/DB client is imported here (the whole ``datasets/`` subpackage is scanned by
``tests/catalog/test_no_inline_io.py``); the real vdb read + parse is B5's dataset
class.
"""

from __future__ import annotations

import math
from typing import Any


def coerce_cvss_score(value: Any) -> float | None:
    """Unwrap vdb 6.6.2's partial-``model_dump`` ``ScoreType`` into a plain float.

    Handles, in order:
    - ``None`` / empty → ``None`` (no score; the overlay must treat this as
      "unknown", NEVER ``0.0`` — a false clean signal, CFA:3733-3735).
    - a bare number (``int`` / ``float``) → ``float(value)``.
    - a ``RootModel``-like object exposing ``.root`` or ``.value`` → unwrap then coerce.
    - a mapping ``{"root": n}`` / ``{"value": n}`` (the partial-dump shape) → unwrap.
    - a numeric string → ``float(value)``.
    - anything else / unparseable → ``None`` (unknown, not ``0.0``).
    """
    if value is None:
        return None
    if isinstance(value, bool):
        # bool is an int subclass but is never a meaningful CVSS score.
        return None
    if isinstance(value, float) and math.isnan(value):
        # NaN is UNKNOWN, never 0.0 and never a spurious NaN score (AC-3 unknown->None).
        return None
    if isinstance(value, (int, float)):
        return float(value)
    # RootModel-like wrapper: unwrap .root / .value (recurse — the wrapped value
    # may itself be a nested wrapper).
    for attr in ("root", "value"):
        if hasattr(value, attr):
            return coerce_cvss_score(getattr(value, attr))
    # partial-model_dump mapping shape.
    if isinstance(value, dict):
        for key in ("root", "value"):
            if key in value:
                return coerce_cvss_score(value[key])
        return None
    # numeric string.
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
