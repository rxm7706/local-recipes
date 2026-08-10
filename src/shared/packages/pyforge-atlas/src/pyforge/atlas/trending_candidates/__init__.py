"""``trending_candidates`` — CAP-3 read-only operator surface (Story 13.3, FR-66).

Package marker only (mirrors ``publish/``'s sibling shape as a new top-level package
beside ``pipelines/``, ``mcp/``, ``nl/``). ``query.py`` holds the one
``query_trending_candidates(...)`` function both the CLI (``__main__.py``) and the MCP
tool (``mcp/tools.py``) delegate to. No new Kedro node/pipeline/catalog dataset here —
this reads ONLY the already-materialized ``trending_candidates_classified`` (Story 13.2).
"""

from __future__ import annotations
