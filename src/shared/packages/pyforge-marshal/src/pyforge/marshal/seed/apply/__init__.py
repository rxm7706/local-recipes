"""seed/apply -- Genesis's transactional apply runner (Story 10.3).

Re-exports ``run.py``'s public API so callers write
``from pyforge.marshal.seed.apply import run_apply`` rather than reaching
into the submodule directly -- ``seed/engine/__init__.py``'s own front-door
convention. ``run.py`` holds the whole story's behavior; this file adds
none of its own.
"""

from __future__ import annotations

from .run import ApplyResult, CommitAction, run_apply

__all__ = [
    "ApplyResult",
    "CommitAction",
    "run_apply",
]
