"""pyforge.scribe.extras — optional `compile_surface` ingest extras (Story
6.1, Dream Grounding 2026-08-30's three CAP-18 ports: `graph_store` /
`compile_surface` / `recall_ranker`).

Off by default (air-gap, AD-6). Each extra module is the ONLY place in this
package that imports its optional third-party dependency -- `compile.py`,
`cli.py`, and every other module call through this package's public
functions, never `import graphify` (or a future extra's engine) directly.
"""

from __future__ import annotations
