"""``trending_candidates`` — CAP-3 read-only operator surface (Story 13.3, FR-66) +
CAP-5 downstream handoff to Mason (Story 13.5, FR-68).

Package marker only (mirrors ``publish/``'s sibling shape as a new top-level package
beside ``pipelines/``, ``mcp/``, ``nl/``). ``query.py`` holds the one
``query_trending_candidates(...)`` function both the CLI (``__main__.py``) and the MCP
tool (``mcp/tools.py``) delegate to. ``handoff.py`` holds ``hand_off_candidate(...)``,
which the CLI (``handoff_main.py``) delegates to — no MCP tool for CAP-5 (Boundaries &
Constraints, spec-13-5). No new Kedro node/pipeline/catalog dataset here — everything in
this package reads ONLY the already-materialized ``trending_candidates_classified``
(Story 13.2).
"""

from __future__ import annotations
