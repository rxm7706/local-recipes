"""CI surfaces tile vs steward ci-status schema (Story 39.1 AC6; the tile is ``docs-site/src/lib/status.ts`` since
Story 43.7)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "meta"))
from pages_astro import DOCS_SITE, REPO_ROOT, needs_node, ts  # noqa: E402 -- the shared Pages helpers

SCHEMA_REL = "src/shared/packages/pyforge-steward/src/pyforge/steward/data/ci-status-schema.json"


@needs_node
def test_row_verdict_enum_matches_tile_known_verdicts() -> None:
    order = ts(DOCS_SITE / "src" / "lib" / "status.ts", "return m.VERDICT_ORDER;")
    schema = json.loads((REPO_ROOT / SCHEMA_REL).read_text(encoding="utf-8"))
    assert set(schema["$defs"]["row"]["properties"]["verdict"]["enum"]) == {*order, "live"}


def test_the_tile_and_the_guild_page_read_only_schema_defined_keys() -> None:
    schema = json.loads((REPO_ROOT / SCHEMA_REL).read_text(encoding="utf-8"))
    allowed = set(schema["$defs"]["row"]["properties"].keys())
    source = (DOCS_SITE / "src" / "lib" / "status.ts").read_text(encoding="utf-8")
    guild = source[source.index("export const GUILD_FIELDS") :].split("\n", 1)[0]
    fields = {name.strip(" '") for name in guild.split("[", 1)[1].split("]", 1)[0].split(",")}
    assert fields <= allowed, fields - allowed
    assert {"review_days_left", "detail", "paused_since", "review_by", "owner", "switch"} <= allowed
