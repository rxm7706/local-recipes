"""seed/engine -- Genesis's rendering seam (Story 10.1).

Re-exports ``copier.py``'s public API so callers write
``from pyforge.marshal.seed.engine import materialize`` rather than
reaching into the submodule directly. ``copier.py`` remains the only module
in this package that imports the ``copier`` library itself (P-02).
"""

from __future__ import annotations

from .copier import (
    CopierEngineError,
    MaterializeRequest,
    MaterializeResult,
    MaterializeVerb,
    TemplateBoundaryError,
    materialize,
)

__all__ = [
    "CopierEngineError",
    "MaterializeRequest",
    "MaterializeResult",
    "MaterializeVerb",
    "TemplateBoundaryError",
    "materialize",
]
